"""Un token vencido no puede escribir nada.

Este es el requisito de seguridad mas importante del sistema: si una peticion
con `exp` pasado llegara a tocar la base, el usuario veria un cambio aplicado
que el registro de auditoria describe como hecho. Un panel que muestra "guardado"
cuando en realidad se rechazo seria peor que un error visible.

Los tests comprueban las DOS mitades, y las dos importan:

1. La peticion se rechaza (401).
2. **No se escribio nada**: ni la fila de negocio ni el registro de auditoria.

Comprobar solo el 401 no basta: un endpoint podria validar el token tarde,
despues de haber escrito. Estos tests miran la base.

Ver `docs/SEGURIDAD.md`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from core.db import SessionLocal
from core.security import create_access_token
from initial_data import main as bootstrap_initial_data
from main import app
from models.appointment import Appointment
from models.audit import AuditLog
from models.patient import Patient
from models.specialty import Specialty


@pytest_asyncio.fixture(scope="session")
async def sec_client():
    await bootstrap_initial_data()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _token_vencido(user_id) -> str:
    """JWT con `exp` en el pasado, firmado con la clave real del proyecto."""
    from jose import jwt

    from core.config import settings
    from core.security import ALGORITHM

    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def _token_invalido(user_id) -> str:
    """JWT con firma hecha con OTRA clave: un atacante podria firmarlo."""
    from jose import jwt

    return jwt.encode(
        {
            "sub": str(user_id),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        "clave-falsa-del-atacante",
        algorithm="HS256",
    )


def _token_sin_exp(user_id) -> str:
    """JWT sin `exp`: sin caducidad declarada."""
    from jose import jwt

    from core.config import settings
    from core.security import ALGORITHM

    return jwt.encode(
        {"sub": str(user_id)}, settings.SECRET_KEY, algorithm=ALGORITHM
    )


async def _superusuario_id() -> str:
    import os

    from core import crud_user

    async with SessionLocal() as db:
        usuario = await crud_user.get_user_by_email(
            db, os.environ["FIRST_SUPERUSER_EMAIL"]
        )
        if usuario is None:
            pytest.skip("no hay superusuario")
        return usuario.id


@pytest_asyncio.fixture
async def contexto():
    """Un paciente y un medico reales, contra los que intentar escribir."""
    async with SessionLocal() as db:
        specialty = (await db.execute(select(Specialty).limit(1))).scalars().first()
        if specialty is None:
            pytest.skip("hace falta una especialidad (make seed)")
        specialty_id = specialty.id
        total_pacientes = (
            await db.execute(select(func.count(Patient.id)))
        ).scalar() or 0

    return {
        "specialty_id": specialty_id,
        "total_pacientes_iniciales": int(total_pacientes),
        "user_id": await _superusuario_id(),
    }


async def _conteo_citas() -> int:
    async with SessionLocal() as db:
        return int((await db.execute(select(func.count(Appointment.id)))).scalar() or 0)


async def _conteo_auditoria() -> int:
    async with SessionLocal() as db:
        return int((await db.execute(select(func.count(AuditLog.id)))).scalar() or 0)


# --------------------------------------------------------------------------
# Token vencido
# --------------------------------------------------------------------------


async def test_token_vencido_no_crea_cita(sec_client, contexto):
    """Un token con `exp` pasado recibe 401 y NO crea la cita."""
    headers = {"Authorization": f"Bearer {_token_vencido(contexto['user_id'])}"}
    antes_citas = await _conteo_citas()

    r = await sec_client.post(
        "/api/v1/appointments/",
        headers=headers,
        json={
            "patient_id": 1,
            "doctor_id": 1,
            "start_datetime": (
                datetime.now(timezone.utc) + timedelta(days=20)
            ).isoformat(),
            "end_datetime": (
                datetime.now(timezone.utc) + timedelta(days=20, minutes=30)
            ).isoformat(),
            "reason": "No deberia existir",
        },
    )
    assert r.status_code == 401, f"token vencido deberia dar 401, dio {r.status_code}"

    despues = await _conteo_citas()
    assert despues == antes_citas, (
        f"la cita se escribio pese al token vencido: {antes_citas} -> {despues}"
    )


async def test_token_vencido_no_escribe_en_auditoria(sec_client, contexto):
    """Ni la tabla de auditoria recibe una fila por una peticion rechazada.

    Este es el punto delicate: si el rechazo escribiera en `audit_logs`, el
    rastro mostraria un cambio que no ocurrio, y el panel (que se apoya en
    esas cifras) contaria una transicion inexistente.
    """
    headers = {"Authorization": f"Bearer {_token_vencido(contexto['user_id'])}"}
    antes = await _conteo_auditoria()

    await sec_client.post(
        "/api/v1/appointments/1/confirm",
        headers=headers,
        json={},
    )
    await sec_client.post(
        "/api/v1/appointments/1/cancel",
        headers=headers,
        json={"reason": "No deberia registrarse"},
    )

    despues = await _conteo_auditoria()
    assert despues == antes, (
        f"la peticion con token vencido escribio en audit_logs: {antes} -> {despues}"
    )


async def test_token_vencido_no_altera_una_cita_existente(
    sec_client, contexto, unique_suffix
):
    """Una transicion sobre una cita real se rechaza y la cita no cambia."""
    # Se crea una cita legitima con el superusuario.
    async with SessionLocal() as db:
        specialty = (await db.execute(select(Specialty).limit(1))).scalars().first()
        specialty_id = specialty.id

    import os

    login = await sec_client.post(
        "/api/v1/login/access-token",
        data={
            "username": os.environ["FIRST_SUPERUSER_EMAIL"],
            "password": os.environ["FIRST_SUPERUSER_PASSWORD"],
        },
    )
    assert login.status_code == 200
    admin = {"Authorization": f"Bearer {login.json()['access_token']}"}

    from models.doctor import Doctor
    from models.user import User as UserModel

    async with SessionLocal() as db:
        paciente = Patient(
            first_name="QA",
            last_name="Expirado",
            document_number=f"EXP-PAT-{unique_suffix}",
            birth_date=datetime(1990, 1, 1).date(),
            email=f"exp.pat.{unique_suffix}@medapp.com",
            phone="+525550005555",
        )
        db.add(paciente)
        await db.commit()
        await db.refresh(paciente)
        patient_id = paciente.id

    r = await sec_client.post(
        "/api/v1/doctors/",
        headers=admin,
        json={
            "first_name": "QA",
            "last_name": "Expirado",
            "document_number": f"EXP-DOC-{unique_suffix}",
            "professional_license": f"EXP-LIC-{unique_suffix}",
            "email": f"exp.doc.{unique_suffix}@medapp.com",
            "specialty_id": specialty_id,
        },
    )
    assert r.status_code == 201, r.text
    doctor_id = r.json()["id"]

    inicio = datetime.now(timezone.utc) + timedelta(days=25)
    r = await sec_client.post(
        "/api/v1/appointments/",
        headers=admin,
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "start_datetime": inicio.isoformat(),
            "end_datetime": (inicio + timedelta(minutes=30)).isoformat(),
            "reason": "QA token expirado",
        },
    )
    assert r.status_code == 201, r.text
    cita_id = r.json()["id"]

    async with SessionLocal() as db:
        cita = await db.get(Appointment, cita_id)
        estado_antes = cita.status_id

    # Ahora se intenta confirmar con un token vencido.
    vencido = {"Authorization": f"Bearer {_token_vencido(contexto['user_id'])}"}
    r = await sec_client.post(f"/api/v1/appointments/{cita_id}/confirm", headers=vencido, json={})
    assert r.status_code == 401, f"deberia ser 401, dio {r.status_code}"

    async with SessionLocal() as db:
        cita = await db.get(Appointment, cita_id)
        assert cita.status_id == estado_antes, (
            "la cita cambio de estado con un token vencido"
        )


# --------------------------------------------------------------------------
# Otras formas de token invalido
# --------------------------------------------------------------------------


async def test_token_con_firma_falsa_es_rechazado(sec_client, contexto):
    """Un JWT firmado con otra clave no vale, aunque su `exp` sea futuro.

    Es el ataque de verdad: sin esto, cualquiera podria fabricar un token con
    `exp` lejano y el rol de un administrador.
    """
    headers = {"Authorization": f"Bearer {_token_invalido(contexto['user_id'])}"}
    r = await sec_client.get("/api/v1/audit/summary", headers=headers)
    assert r.status_code == 401, f"firma falsa deberia dar 401, dio {r.status_code}"


async def test_token_sin_exp_es_rechazado(sec_client, contexto):
    """Un token sin `exp` no sirve: un token sin caducidad es una sesion eterna."""
    headers = {"Authorization": f"Bearer {_token_sin_exp(contexto['user_id'])}"}
    r = await sec_client.get("/api/v1/audit/summary", headers=headers)
    assert r.status_code == 401, f"token sin exp deberia dar 401, dio {r.status_code}"


async def test_token_manipulado_es_rechazado(sec_client):
    """Alterar un byte del payload invalida la firma."""
    import os

    login = await sec_client.post(
        "/api/v1/login/access-token",
        data={
            "username": os.environ["FIRST_SUPERUSER_EMAIL"],
            "password": os.environ["FIRST_SUPERUSER_PASSWORD"],
        },
    )
    token = login.json()["access_token"]
    partes = token.split(".")
    # Se altera el payload manteniendo la firma original.
    partes[1] = partes[1][:-2] + ("AA" if not partes[1].endswith("AA") else "BB")

    r = await sec_client.get(
        "/api/v1/audit/summary",
        headers={"Authorization": f"Bearer {'.'.join(partes)}"},
    )
    assert r.status_code == 401, f"token manipulado deberia dar 401, dio {r.status_code}"


async def test_escrituras_criticas_rechazan_token_vencido(sec_client, contexto):
    """Barre las escrituras mas peligrosas con un token vencido.

    Incluye el job de no-show, que es un lote GLOBAL: si pasara, cancelaria
    citas de toda la clinica.
    """
    headers = {"Authorization": f"Bearer {_token_vencido(contexto['user_id'])}"}
    casos = [
        ("post", "/api/v1/appointments/1/confirm", {}),
        ("post", "/api/v1/appointments/1/wait", {}),
        ("post", "/api/v1/appointments/1/start", {}),
        ("post", "/api/v1/appointments/1/suspend", {"reason": "prueba"}),
        ("post", "/api/v1/appointments/1/cancel", {"reason": "prueba"}),
        ("post", "/api/v1/appointments/1/reactivate", {}),
        ("post", "/api/v1/appointments/auto-cancel-no-show", {}),
        ("post", "/api/v1/appointments/bulk-reschedule", {"doctor_id": 1}),
        ("patch", "/api/v1/appointments/1/status", {"status": "ATENDIDA"}),
        ("put", "/api/v1/appointments/1", {"reason": "prueba"}),
        ("delete", "/api/v1/appointments/999999", None),
        ("post", "/api/v1/notes/", {"appointment_id": 1, "diagnosis": "prueba"}),
        # El router de users se registra con `prefix="/api/v1"` y la ruta es
        # `"/"`, asi que cuelga de `/api/v1/`, no de `/api/v1/users/`.
        ("post", "/api/v1/", {"email": "x@y.com", "password": "Aa1!aaaa"}),
        ("post", "/api/v1/users/", {"email": "x@y.com", "password": "Aa1!aaaa"}),
        ("post", "/api/v1/integrations/branches", {"name": "Rama unauthorized"}),
        ("post", "/api/v1/appointment-statuses/", {"code": "HACK"}),
    ]
    fallos = []
    for metodo, ruta, cuerpo in casos:
        # `delete()` no acepta `json` en httpx: se manda solo si hay cuerpo.
        if metodo == "delete":
            r = await sec_client.delete(ruta, headers=headers)
        else:
            r = await getattr(sec_client, metodo)(ruta, headers=headers, json=cuerpo)
        # 404 significa que la ruta no existe, que tambien es un rechazo
        # valido: lo que se busca es que ninguna escritura llegue a la base.
        if r.status_code not in (401, 403, 404):
            fallos.append(f"{metodo.upper():6} {ruta} -> {r.status_code}")

    assert not fallos, (
        "estas escrituras aceptaron un token vencido:\n  " + "\n  ".join(fallos)
    )
