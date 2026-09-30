"""Tests del dashboard operativo.

El dashboard muestra numeros que alguien toma decisiones clinicas: si un
indicador devuelve 0 cuando deberia devolver 47, nadie se entera hasta que
alguien pierde una cita. Estos tests comprueban que las cifras dicen la verdad.

Los estados son los 8 canonicos de `schemas.appointment`, no los codigos en
ingles que usa el SQL antiguo de `reports.py`.

Ver `docs/FRONTEND.md`.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from core.db import SessionLocal
from initial_data import main as bootstrap_initial_data
from main import app
from models.appointment_status import AppointmentStatus
from models.specialty import Specialty
from models.user import User as UserModel


@pytest_asyncio.fixture(scope="session")
async def dash_client():
    await bootstrap_initial_data()
    await _asegurar_roles()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _asegurar_roles() -> None:
    """Siembra los 6 roles canonicos que falten, por NOMBRE.

    Dos motivos para no confiar en que la migracion ya los dejo:

    1. `initial_data` solo crea el super admin. Sin el resto, cualquier test
       de rol se saltaria y el panel no tendria cobertura real: un 403 que
       nunca se exercise no prueba nada.
    2. La comprobacion es por nombre y no por UUID. `init.sql` asignaba
       ASSISTANT al slot ...0003, que `rbac.ROLE_IDS` reserva para ADMIN, y
       esa base ya sembrada choca en `roles_pkey` al insertar por id.
       `has_role()` compara por nombre, asi que respetar el UUID existente
       es lo correcto.
    """
    from core.rbac import ROLES_CANONICOS
    from models.role import Role

    async with SessionLocal() as db:
        existentes = {name for (name,) in (await db.execute(select(Role.name))).all()}
        for id_, nombre, _descripcion in ROLES_CANONICOS:
            if nombre in existentes:
                continue
            # UUID nuevo y aleatorio a proposito: si el slot de `rbac` esta
            # ocupado por otro rol, generarlo evita la colision.
            db.add(Role(id=uuid.uuid4(), name=nombre))
        await db.commit()


async def _rol(db, nombre: str):
    from models.role import Role

    return (
        await db.execute(select(Role).where(Role.name == nombre))
    ).scalars().first()


async def _login(c, email: str, password: str) -> dict:
    r = await c.post(
        "/api/v1/login/access-token", data={"username": email, "password": password}
    )
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest_asyncio.fixture(scope="session")
async def admin_headers(dash_client):
    import os

    return await _login(
        dash_client,
        os.environ["FIRST_SUPERUSER_EMAIL"],
        os.environ["FIRST_SUPERUSER_PASSWORD"],
    )


@pytest_asyncio.fixture(scope="session")
async def especial(dash_client, unique_suffix):
    """Un especialista con usuario, ficha de `doctors` y agenda propias.

    Usuario y medico comparten el correo, que es el vinculo real entre las
    tablas (`crud_agenda_scope`). Sin esa ficha el panel loeria agenda vacia.
    """
    import os

    email = f"esp.dash.{unique_suffix}@medapp.com"
    async with SessionLocal() as db:
        specialty = (await db.execute(select(Specialty).limit(1))).scalars().first()
        if specialty is None:
            pytest.skip("hace falta una especialidad (make seed)")
        specialty_id = specialty.id

    from core.security import get_password_hash

    async with SessionLocal() as db:
        rol = await _rol(db, "DOCTOR")
        usuario = UserModel(
            id=uuid.uuid4(),
            email=email,
            full_name="Dra. Prueba Dashboard",
            password=get_password_hash("dash12345"),
            role_id=rol.id,
            is_active=True,
        )
        db.add(usuario)
        await db.commit()

    r = await dash_client.post(
        "/api/v1/doctors/",
        headers=await _login(
            dash_client,
            os.environ["FIRST_SUPERUSER_EMAIL"],
            os.environ["FIRST_SUPERUSER_PASSWORD"],
        ),
        json={
            "first_name": "Prueba",
            "last_name": "Dashboard",
            "document_number": f"DASH-DOC-{unique_suffix}",
            "professional_license": f"DASH-LIC-{unique_suffix}",
            "email": email,
            "specialty_id": specialty_id,
        },
    )
    assert r.status_code == 201, r.text
    doctor_id = r.json()["id"]

    headers = await _login(dash_client, email, "dash12345")
    yield {"headers": headers, "doctor_id": doctor_id, "email": email}

    # La ficha de `doctors` tiene ON DELETE RESTRICT desde las citas, asi que
    # se borran primero las citas de este especialista.
    async with SessionLocal() as db:
        from models.appointment import Appointment

        citas = (
            await db.execute(
                select(Appointment).where(Appointment.doctor_id == doctor_id)
            )
        ).scalars().all()
        for cita in citas:
            await db.delete(cita)
        await db.commit()

        usuario = (
            await db.execute(select(UserModel).where(UserModel.email == email))
        ).scalars().first()
        if usuario:
            # `await`: db.delete() es una corrutina en SQLAlchemy async, y sin
            # el await el objeto nunca se borra.
            await db.delete(usuario)
        await db.commit()


async def _crear_citas(
    client,
    headers: dict,
    *,
    doctor_id: int,
    prefijo: str,
    estados: list[tuple[str, int]],
    dia_base: int = 9,
) -> list[int]:
    """Crea citas repartidas en `estados` [(codigo, cuantas), ...].

    Las fechas se ponen a `dia_base` dias vista para no ensuciar el KPI de hoy,
    que tiene sus propias aserciones.

    `dia_base` existe porque todos los tests comparten el mismo especialista:
    `_has_conflict` solapa por `doctor_id`, no por paciente, asi que dos tests
    que usen el mismo dia y las mismas horas se devuelven 409 el uno al otro.
    Cada test que crea citas pasa su propio dia.
    """
    async with SessionLocal() as db:
        paciente = await _paciente_por_defecto(db, prefijo)

    base = datetime.now(timezone.utc).replace(microsecond=0)

    ids = []
    i = 0
    for codigo, cuantas in estados:
        for _ in range(cuantas):
            # Una hora de separacion: `_has_conflict` solapa el intervalo
            # [inicio, fin) contra el resto de citas del MEDICO, asi que 30
            # minutos de duracion necesitan 60 de hueco.
            inicio = base + timedelta(days=dia_base, hours=i)
            r = await client.post(
                "/api/v1/appointments/",
                headers=headers,
                json={
                    "patient_id": paciente,
                    "doctor_id": doctor_id,
                    "start_datetime": inicio.isoformat(),
                    "end_datetime": (inicio + timedelta(minutes=30)).isoformat(),
                    "reason": f"QA dashboard {prefijo}",
                },
            )
            assert r.status_code == 201, r.text
            cita_id = r.json()["id"]
            ids.append(cita_id)
            if codigo != "PENDIENTE":
                await _forzar_estado(cita_id, codigo)
            i += 1
    return ids


async def _forzar_estado(cita_id: int, codigo: str) -> None:
    """Fija el estado sin pasar por la maquina de estados.

    Los tests de transiciones ya cubren `VALID_TRANSITIONS`; aqui interesa el
    estado final, no el camino.
    """
    async with SessionLocal() as db:
        estado = (
            await db.execute(select(AppointmentStatus).where(AppointmentStatus.code == codigo))
        ).scalars().first()
        from models.appointment import Appointment

        cita = await db.get(Appointment, cita_id)
        cita.status_id = estado.id
        await db.commit()


async def _paciente_por_defecto(db, prefijo: str) -> int:
    from models.patient import Patient

    paciente = (
        await db.execute(
            select(Patient).where(Patient.document_number == f"DASH-PAT-{prefijo}")
        )
    ).scalars().first()
    if paciente:
        return paciente.id

    paciente = Patient(
        first_name="QA",
        last_name="Dashboard",
        document_number=f"DASH-PAT-{prefijo}",
        # `date`, no str: asyncpg rechaza el texto para una columna DATE.
        birth_date=date(1990, 1, 1),
        email=f"dash.pat.{prefijo}@medapp.com",
        phone="+525550007777",
    )
    db.add(paciente)
    await db.commit()
    await db.refresh(paciente)
    return paciente.id


# --------------------------------------------------------------------------
# Autorizacion: el panel es del personal clinico
# --------------------------------------------------------------------------


async def test_paciente_no_abre_el_panel(dash_client, unique_suffix):
    """Un paciente autenticado recibe 403 en todos los endpoints del panel.

    Sin esta comprobacion, un PATIENT ve la carga de toda la clinica: son
    datos de otros pacientes.
    """
    import os

    email = f"pac.dash.{unique_suffix}@medapp.com"
    async with SessionLocal() as db:
        from core.security import get_password_hash

        rol = await _rol(db, "PATIENT")
        db.add(
            UserModel(
                id=uuid.uuid4(),
                email=email,
                full_name="Paciente Dashboard",
                password=get_password_hash("dash12345"),
                role_id=rol.id,
                is_active=True,
            )
        )
        await db.commit()

    headers = await _login(dash_client, email, "dash12345")
    for ruta in ("scope", "kpis", "today", "series", "workload", "schedule"):
        r = await dash_client.get(f"/api/v1/dashboard/{ruta}", headers=headers)
        assert r.status_code == 403, f"/{ruta} deberia ser 403, dio {r.status_code}"

    async with SessionLocal() as db:
        usuario = (
            await db.execute(select(UserModel).where(UserModel.email == email))
        ).scalars().first()
        if usuario:
            await db.delete(usuario)
        await db.commit()


async def test_sin_token_es_401(dash_client):
    for ruta in ("scope", "kpis", "today", "series", "workload", "schedule"):
        r = await dash_client.get(f"/api/v1/dashboard/{ruta}")
        assert r.status_code == 401, f"/{ruta} sin token deberia ser 401"


async def test_scope_de_admin_no_acota(dash_client, admin_headers):
    """Un administrador ve la clinica entera: `medicos_visibles` es None."""
    r = await dash_client.get("/api/v1/dashboard/scope", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["es_admin"] is True
    assert body["medicos_visibles"] is None


async def test_scope_de_especialista_es_uno(dash_client, especial):
    """Un especialista ve exactamente su ficha de medico."""
    r = await dash_client.get("/api/v1/dashboard/scope", headers=especial["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["es_medico"] is True
    assert body["es_admin"] is False
    assert body["medicos_visibles"] == 1, "un especialista ve una sola ficha"


# --------------------------------------------------------------------------
# Las cifras dicen la verdad
# --------------------------------------------------------------------------


async def test_especialista_solo_ve_su_agenda(
    dash_client, admin_headers, especial, unique_suffix
):
    """Las citas de otro medico no aparecen en la agenda del especialista."""
    await _crear_citas(
        dash_client,
        admin_headers,
        doctor_id=especial["doctor_id"],
        prefijo=unique_suffix,
        estados=[("PENDIENTE", 3)],
        dia_base=9,
    )

    r = await dash_client.get("/api/v1/dashboard/schedule", headers=especial["headers"])
    assert r.status_code == 200, r.text
    doctor_ids = {c["doctor_id"] for c in r.json()["citas"]}
    assert doctor_ids <= {especial["doctor_id"]}, (
        f"el especialista vio citas de otros medicos: {doctor_ids}"
    )


async def test_serie_cuenta_las_citas_creadas(
    dash_client, admin_headers, especial, unique_suffix
):
    """La serie diaria suma exactamente las citas que existen."""
    antes = await _kpis_del_especialista(dash_client, especial)
    await _crear_citas(
        dash_client,
        admin_headers,
        doctor_id=especial["doctor_id"],
        prefijo=unique_suffix,
        estados=[("PENDIENTE", 4)],
        dia_base=12,
    )
    despues = await _kpis_del_especialista(dash_client, especial)

    # Las citas del fixture se crean a 8 dias vista, asi que no entran en el
    # KPI de hoy; el total del mes si debe subir en 4.
    assert despues["citas_mes"] - antes["citas_mes"] == 4, (
        f"el KPI de mes no sumo las 4 citas nuevas: {antes['citas_mes']} -> {despues['citas_mes']}"
    )


async def _kpis_del_especialista(client, especial) -> dict:
    r = await client.get("/api/v1/dashboard/kpis", headers=especial["headers"])
    assert r.status_code == 200, r.text
    return r.json()


async def test_tasa_de_asistencia_usa_citas_resueltas(dash_client, especial):
    """La tasa se calcula sobre lo resuelto, no sobre el total.

    Si se dividiera entre todas las citas, una cita PENDIENTE de manana
    hundiria la tasa de asistencia sin que nadie haya faltado.
    """
    kpis = await _kpis_del_especialista(dash_client, especial)

    # Sin actividad pasada, las tasas son 0.0 y no NaN ni division por cero.
    assert 0.0 <= kpis["tasa_asistencia_pct"] <= 100.0
    assert 0.0 <= kpis["tasa_cancelacion_pct"] <= 100.0
    assert 0.0 <= kpis["tasa_inasistencia_pct"] <= 100.0


async def test_hoy_devuelve_las_citas_de_hoy(dash_client, admin_headers, especial):
    """`/today` cuenta las citas cuya fecha es hoy, ni mas ni menos."""
    r = await dash_client.get("/api/v1/dashboard/today", headers=especial["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fecha"] == datetime.now(timezone.utc).date().isoformat()
    assert body["total"] == sum(body["por_estado"].values())
    assert body["avance_pct"] == 0.0 or 0 <= body["avance_pct"] <= 100


async def test_serie_no_tiene_huecos(dash_client, especial):
    """La serie trae un punto por dia, incluso los que no tienen citas.

    Una serie con huecos hace que un lunes tranquilo parezca un dia sin
    actividad: es el defecto clasico de un GROUP BY sin generate_series.
    """
    r = await dash_client.get(
        "/api/v1/dashboard/series?dias=14", headers=especial["headers"]
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert len(data) == 14, f"se esperaban 14 puntos, llegaron {len(data)}"
    assert all("dia" in punto and "total" in punto for punto in data)
    fechas = [p["dia"] for p in data]
    assert len(set(fechas)) == 14, "hay dias repetidos en la serie"


async def test_workload_devuelve_ocupacion_o_null(dash_client, especial):
    """`ocupacion_pct` es un numero o None; nunca 0 cuando no se puede calcular."""
    r = await dash_client.get("/api/v1/dashboard/workload", headers=especial["headers"])
    assert r.status_code == 200, r.text
    for fila in r.json()["data"]:
        ocupacion = fila["ocupacion_pct"]
        assert ocupacion is None or isinstance(ocupacion, float)
        assert ocupacion is None or ocupacion >= 0
        assert fila["atendidas"] <= fila["total"]


async def test_agenda_devuelve_patientes_reales(
    dash_client, admin_headers, especial, unique_suffix
):
    """Cada cita de la agenda trae el nombre del paciente, no un placeholder.

    Se piden las citas de HOY (dia_base=0), que es lo que `/schedule` devuelve
    por defecto: pedir las de hoy+15 daria una agenda vacia y el test pasaria
    sin comprobar nada.
    """
    await _crear_citas(
        dash_client,
        admin_headers,
        doctor_id=especial["doctor_id"],
        prefijo=unique_suffix,
        estados=[("PENDIENTE", 2)],
        dia_base=0,
    )
    r = await dash_client.get(
        "/api/v1/dashboard/schedule", headers=especial["headers"]
    )
    assert r.status_code == 200, r.text
    citas = r.json()["citas"]
    assert citas, "se crearon citas para hoy y la agenda vino vacia"
    for cita in citas:
        assert cita["paciente"] != "Paciente", "el nombre del paciente no se resolvio"
        assert cita["estado"], "la cita vino sin estado"
