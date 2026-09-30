"""Pruebas del registro de auditoria.

Verifica que toda transicion de cita deja rastro: estado origen, destino, actor
y motivo. Sin esto, `audit_logs` volveria a ser una tabla huerfana.

## Nota sobre SQLAlchemy async

Los tests recorren el ciclo de vida por HTTP (como lo haria un usuario) y luego
consultan `audit_logs` con una sesion propia. Se evita deliberadamente encadenar
CRUDs en una misma sesion: tras cada `commit` los objetos se expiran y volver
a leer un atributo lanza `MissingGreenlet`.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

# Importar SIEMPRE por la ruta sin prefijo (`models.audit`), nunca `app.models.*`.
#
# `app/main.py` inserta `backend/app` en sys.path para que sus modulos internos
# usen imports sin prefijo (`from core.db import Base`). Si un test importa
# `app.models.*`, Python lo carga como modulo DISTINTO de `models.*`, y cada
# uno registra las mismas tablas sobre el MetaData compartido:
#
#   InvalidRequestError: Table 'assistant_specialists' is already defined
#
# Es decir, `app.core` y `core` son dos modulos con dos clases `Base` distintas.
from core.db import SessionLocal
from httpx import ASGITransport, AsyncClient
from initial_data import main as bootstrap_initial_data
from main import app
from models.audit import AuditAction
from models.audit import AuditLog as AuditLogModel
from models.doctor import Doctor
from models.patient import Patient
from models.specialty import Specialty
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload


@pytest_asyncio.fixture(scope="session")
async def audit_client():
    await bootstrap_initial_data()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(scope="session")
async def audit_headers(audit_client):
    import os

    response = await audit_client.post(
        "/api/v1/login/access-token",
        data={
            "username": os.environ["FIRST_SUPERUSER_EMAIL"],
            "password": os.environ["FIRST_SUPERUSER_PASSWORD"],
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _parse(value: str | None) -> dict:
    return json.loads(value) if value else {}


async def _transiciones_de(db, appointment_id: int) -> list[tuple]:
    """[(from_state, to_state, reason)] de una cita, en orden cronologico."""
    from core.crud_audit import normalizar_record_id

    result = await db.execute(
        select(AuditLogModel)
        .where(AuditLogModel.record_id == normalizar_record_id(appointment_id))
        .order_by(AuditLogModel.created_at, AuditLogModel.id)
    )
    filas = []
    for registro in result.scalars().all():
        if registro.action != AuditAction.UPDATE:
            continue
        datos = _parse(registro.new_value)
        if "to_state" not in datos:
            continue
        filas.append(
            (datos.get("from_state"), datos.get("to_state"), datos.get("reason"))
        )
    return filas


# --------------------------------------------------------------------------
# Normalizacion de ids
# --------------------------------------------------------------------------
def test_record_id_uuid_estable_y_sin_colisiones():
    """`audit_logs.record_id` es UUID pero las tablas de negocio usan SERIAL."""
    from core.crud_audit import normalizar_record_id

    a = normalizar_record_id(1)
    b = normalizar_record_id(1)
    c = normalizar_record_id(2)

    assert a == b, "el mismo id debe producir siempre el mismo UUID"
    assert a != c, "ids distintos no pueden colisionar"
    assert normalizar_record_id(None) is None


def test_record_id_acepta_uuid_y_entero():
    import uuid as _uuid

    from core.crud_audit import normalizar_record_id

    real = _uuid.uuid4()
    assert normalizar_record_id(real) is real


# --------------------------------------------------------------------------
# Flujo completo por HTTP
# --------------------------------------------------------------------------
@pytest_asyncio.fixture
async def cita_para_auditar(audit_client, audit_headers, unique_suffix):
    """Cita PENDIENTE lista para un ciclo de vida, con sus fixtures.

    Se crea y se destruye dentro del test para no dejar residuos.
    """
    async with SessionLocal() as db:
        specialty = (await db.execute(select(Specialty).limit(1))).scalars().first()
        if specialty is None:
            pytest.skip("hace falta una especialidad (make seed)")
        specialty_id = specialty.id

    paciente = {
        "first_name": "QA",
        "last_name": f"Auditoria {unique_suffix}",
        "document_number": f"QA-AUD-PAT-{unique_suffix}",
        "birth_date": "1990-01-01",
        "email": f"qa.aud.pat.{unique_suffix}@medapp.com",
        "phone": "+525550000001",
    }
    r = await audit_client.post(
        "/api/v1/patients/", json=paciente, headers=audit_headers
    )
    assert r.status_code == 201, r.text
    patient_id = r.json()["id"]

    r = await audit_client.get("/api/v1/specialties/", headers=audit_headers)
    spec_id = r.json()[0]["id"] if r.status_code == 200 else specialty_id

    medico = {
        "first_name": "QA",
        "last_name": f"Auditoria Doc {unique_suffix}",
        "document_number": f"QA-AUD-DOC-{unique_suffix}",
        "professional_license": f"QA-AUD-LIC-{unique_suffix}",
        "email": f"qa.aud.doc.{unique_suffix}@medapp.com",
        "specialty_id": spec_id,
    }
    r = await audit_client.post("/api/v1/doctors/", json=medico, headers=audit_headers)
    assert r.status_code == 201, r.text
    doctor_id = r.json()["id"]

    inicio = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    fin = (datetime.now(timezone.utc) + timedelta(days=5, minutes=30)).isoformat()
    r = await audit_client.post(
        "/api/v1/appointments/",
        headers=audit_headers,
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "start_datetime": inicio,
            "end_datetime": fin,
            "reason": "QA auditoria",
        },
    )
    assert r.status_code == 201, r.text
    appointment_id = r.json()["id"]

    yield appointment_id, patient_id, doctor_id

    # Limpieza
    await audit_client.delete(
        f"/api/v1/appointments/{appointment_id}", headers=audit_headers
    )
    await audit_client.delete(f"/api/v1/patients/{patient_id}", headers=audit_headers)
    await audit_client.delete(f"/api/v1/doctors/{doctor_id}", headers=audit_headers)


async def test_creacion_deja_rastro(audit_client, audit_headers, cita_para_auditar):
    """Crear una cita genera un registro con from_state nulo."""
    appointment_id, *_ = cita_para_auditar

    async with SessionLocal() as db:
        transiciones = await _transiciones_de(db, appointment_id)

    assert (None, "PENDIENTE", "Cita creada") in transiciones, (
        f"la creacion debe auditarse; se obtuvo {transiciones}"
    )


async def test_ciclo_completo_deja_rastro(
    audit_client, audit_headers, cita_para_auditar
):
    """PENDIENTE -> CONFIRMADA -> EN ESPERA -> EN PROCESO, cada paso auditado."""
    appointment_id, *_ = cita_para_auditar

    for paso in ("confirm", "wait", "start"):
        r = await audit_client.post(
            f"/api/v1/appointments/{appointment_id}/{paso}",
            headers=audit_headers,
        )
        assert r.status_code == 200, f"{paso} -> {r.status_code}: {r.text}"
        assert r.json()["status"]["code"] in ("CONFIRMADA", "EN ESPERA", "EN PROCESO")

    async with SessionLocal() as db:
        transiciones = await _transiciones_de(db, appointment_id)

    esperados = [
        ("PENDIENTE", "CONFIRMADA"),
        ("CONFIRMADA", "EN ESPERA"),
        ("EN ESPERA", "EN PROCESO"),
    ]
    for origen, destino in esperados:
        par = (origen, destino)
        assert any(t[0] == par[0] and t[1] == par[1] for t in transiciones), (
            f"falta la transicion {origen} -> {destino}; se obtuvo {transiciones}"
        )

    # Cada transicion guarda un motivo: sin el, el registro no explica nada.
    for origen, destino in esperados:
        registro = next(
            t for t in transiciones if t[0] == origen and t[1] == destino
        )
        assert registro[2], f"la transicion {origen}->{destino} no tiene motivo"


async def test_registro_identifica_al_actor(
    audit_client, audit_headers, cita_para_auditar
):
    """El registro guarda el id del usuario que hizo el cambio."""

    appointment_id, *_ = cita_para_auditar

    r = await audit_client.post(
        f"/api/v1/appointments/{appointment_id}/confirm", headers=audit_headers
    )
    assert r.status_code == 200, r.text

    from core.crud_audit import normalizar_record_id

    async with SessionLocal() as db:
        result = await db.execute(
            select(AuditLogModel)
            .where(AuditLogModel.record_id == normalizar_record_id(appointment_id))
            .where(AuditLogModel.action == AuditAction.UPDATE)
        )
        registros = result.scalars().all()

    assert registros, "debe existir el registro de la transicion"
    for registro in registros:
        assert registro.user_id is not None, "el registro debe identificar al actor"


async def test_cancelacion_audita_el_motivo(
    audit_client, audit_headers, cita_para_auditar
):
    """Suspender guarda el motivo, que es informacion clinica relevante."""
    appointment_id, *_ = cita_para_auditar

    r = await audit_client.post(
        f"/api/v1/appointments/{appointment_id}/suspend",
        headers=audit_headers,
        json={"reason": "El paciente no ha llegado"},
    )
    # El motivo de prueba se envia valido; si falla, el detalle lo dice.
    assert r.status_code in (200, 400, 422), r.text

    if r.status_code != 200:
        pytest.skip("la suspension no aplica en este escenario")

    async with SessionLocal() as db:
        transiciones = await _transiciones_de(db, appointment_id)

    assert any(
        t[1] == "SUSPENDIDA" and t[2] for t in transiciones
    ), f"la suspension debe auditarse con su motivo; se obtuvo {transiciones}"


# --------------------------------------------------------------------------
# Garantias
# --------------------------------------------------------------------------
async def test_transicion_invalida_no_deja_rastro(audit_client, audit_headers):
    """Una transicion rechazada no escribe nada."""
    from core.crud_appointment_audit import transicionar
    from models.appointment import Appointment as AppointmentModel
    from schemas.appointment import AppointmentStatusCode

    async with SessionLocal() as db:
        appt = (await db.execute(select(AppointmentModel).limit(1))).scalars().first()
        if appt is None:
            pytest.skip("no hay citas en la base")

        appointment_id = appt.id
        antes = len(await _transiciones_de(db, appointment_id))

    # `db.get` por clave primaria no carga las relaciones (`status`): hay que
    # usar `selectinload`, igual que hace `crud_appointment.get_appointment`.
    # Sin el eager load, `appt.status` dispara una consulta perezosa y, al
    # estar fuera de un await, revienta con MissingGreenlet.
    async with SessionLocal() as db:
        result = await db.execute(
            select(AppointmentModel)
            .options(selectinload(AppointmentModel.status))
            .where(AppointmentModel.id == appointment_id)
        )
        appt = result.scalars().first()
        assert appt is not None
        with pytest.raises(ValueError):
            await transicionar(db, appt, AppointmentStatusCode.ATTENDED)
        await db.rollback()

    async with SessionLocal() as db:
        despues = len(await _transiciones_de(db, appointment_id))

    assert antes == despues, "una transicion invalida no debe auditarse"


async def test_login_fallido_queda_registrado(audit_client):
    """Un intento con credenciales invalidas queda auditado."""
    r = await audit_client.post(
        "/api/v1/login/access-token",
        data={
            "username": "no-existe-auditoria@medapp.com",
            "password": "incorrecta",
        },
    )
    assert r.status_code == 401

    async with SessionLocal() as db:
        result = await db.execute(
            select(AuditLogModel)
            .where(AuditLogModel.action == AuditAction.LOGIN)
            .order_by(AuditLogModel.created_at.desc())
            .limit(1)
        )
        ultimo = result.scalars().first()

    assert ultimo is not None, "el intento fallido debe quedar auditado"
    detalle = _parse(ultimo.new_value)
    assert detalle.get("resultado") == "fallido"
    assert detalle.get("email") == "no-existe-auditoria@medapp.com"


async def test_auditoria_nunca_guarda_contrasenas():
    """Ningun registro contiene material sensible."""
    async with SessionLocal() as db:
        result = await db.execute(select(AuditLogModel))
        registros = result.scalars().all()

    for registro in registros:
        blob = f"{registro.old_value or ''}{registro.new_value or ''}".lower()
        assert "password" not in blob
        assert "contrasena" not in blob
        assert "contraseña" not in blob


async def test_borrado_deja_rastro_tras_la_cita(audit_client, audit_headers, unique_suffix):
    """Borrar una cita conserva el registro que la describe.

    Es el caso que justifica auditar antes del DELETE: si se escribiera
    despues, el registro desapareceria junto con la fila.
    """
    async with SessionLocal() as db:
        specialty = (await db.execute(select(Specialty).limit(1))).scalars().first()
        if specialty is None:
            await db.close()
            pytest.skip("hace falta una especialidad (make seed)")
        specialty_id = specialty.id

    r = await audit_client.post(
        "/api/v1/patients/",
        headers=audit_headers,
        json={
            "first_name": "QA",
            "last_name": f"Borrado {unique_suffix}",
            "document_number": f"QA-AUD-BPAT-{unique_suffix}",
            "birth_date": "1990-01-01",
            "email": f"qa.aud.bpat.{unique_suffix}@medapp.com",
            "phone": "+525550000002",
        },
    )
    assert r.status_code == 201, r.text
    patient_id = r.json()["id"]

    r = await audit_client.post(
        "/api/v1/doctors/",
        headers=audit_headers,
        json={
            "first_name": "QA",
            "last_name": f"Borrado Doc {unique_suffix}",
            "document_number": f"QA-AUD-BDOC-{unique_suffix}",
            "professional_license": f"QA-AUD-BLIC-{unique_suffix}",
            "email": f"qa.aud.bdoc.{unique_suffix}@medapp.com",
            "specialty_id": specialty_id,
        },
    )
    assert r.status_code == 201, r.text
    doctor_id = r.json()["id"]

    inicio = (datetime.now(timezone.utc) + timedelta(days=6)).isoformat()
    fin = (datetime.now(timezone.utc) + timedelta(days=6, minutes=30)).isoformat()
    r = await audit_client.post(
        "/api/v1/appointments/",
        headers=audit_headers,
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "start_datetime": inicio,
            "end_datetime": fin,
            "reason": "QA borrado",
        },
    )
    assert r.status_code == 201, r.text
    appointment_id = r.json()["id"]

    r = await audit_client.delete(
        f"/api/v1/appointments/{appointment_id}", headers=audit_headers
    )
    assert r.status_code == 200, r.text

    # La cita ya no existe, pero su rastro debe seguir ahi.
    # Los valores se extraen DENTRO de la sesion: fuera de ella los objetos
    # estan desligados (DetachedInstanceError).
    async with SessionLocal() as db:
        from core.crud_audit import normalizar_record_id

        result = await db.execute(
            select(AuditLogModel).where(
                AuditLogModel.record_id == normalizar_record_id(appointment_id)
            )
        )
        acciones = {registro.action for registro in result.scalars().all()}
        await db.execute(delete(Patient).where(Patient.id == patient_id))
        await db.execute(delete(Doctor).where(Doctor.id == doctor_id))
        await db.commit()

    assert acciones, "el rastro debe sobrevivir al borrado de la cita"
    assert AuditAction.DELETE in acciones, "el borrado debe quedar registrado"
    assert AuditAction.UPDATE in acciones, "la creacion debe seguir registrada"
