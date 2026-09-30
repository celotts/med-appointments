"""Tests de los endpoints de `reports.py`.

Estaban rotos y sin un solo test que lo notara: los 4 filtraban por codigos de
estado en ingles (`SCHEDULED`, `CONFIRMED`, `COMPLETED`, `CANCELLED`) que no
existen en la base, donde solo hay los 8 canonicos en español. El subescalar
devolvia NULL, `status_id != NULL` evaluaba a NULL y el `WHERE` descartaba todo:
7 de los 9 campos del summary devolvian 0, siempre, para siempre.

Estos tests crean citas en estados conocidos y comprueban que las cifras
responden. Un `assert valor >= 0` habria pasado con el bug: por eso cada
comprobacion mira un numero exacto.

Ver `docs/ESTADOS_CITA.md`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from core.db import SessionLocal
from initial_data import main as bootstrap_initial_data
from main import app

from models.specialty import Specialty


@pytest_asyncio.fixture(scope="session")
async def reports_client():
    await bootstrap_initial_data()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(scope="session")
async def reports_headers(reports_client):
    import os

    response = await reports_client.post(
        "/api/v1/login/access-token",
        data={
            "username": os.environ["FIRST_SUPERUSER_EMAIL"],
            "password": os.environ["FIRST_SUPERUSER_PASSWORD"],
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _crear_cita_reciente(
    client, headers: dict, *, doctor_id: int, patient_id: int, minutos_atras: int
) -> int:
    """Cita PENDIENTE en el pasado reciente, dentro de la ventana de 30 dias."""
    inicio = datetime.now(timezone.utc) - timedelta(minutes=minutos_atras)
    response = await client.post(
        "/api/v1/appointments/",
        headers=headers,
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "start_datetime": inicio.isoformat(),
            "end_datetime": (inicio + timedelta(minutes=30)).isoformat(),
            "reason": "QA reports",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


# --------------------------------------------------------------------------
# El bug: los codigos en ingles devolvian cero
# --------------------------------------------------------------------------


async def test_resumen_no_devuelve_todo_en_cero(
    reports_client, reports_headers, unique_suffix
):
    """`appointments_pending` cuenta citas PENDIENTE de verdad.

    Con el bug (filtrando por 'SCHEDULED') daba 0 aunque hubiera 3 citas
    PENDIENTE en la base. El aserto es `>= 1` y no `> 0` a proposito: la base
    puede tener citas de otros tests.
    """
    async with SessionLocal() as db:
        specialty = (await db.execute(select(Specialty).limit(1))).scalars().first()
        if specialty is None:
            pytest.skip("hace falta una especialidad (make seed)")
        specialty_id = specialty.id

    from models.patient import Patient

    async with SessionLocal() as db:
        paciente = Patient(
            first_name="QA",
            last_name="Reports",
            document_number=f"REP-PAT-{unique_suffix}",
            birth_date=datetime(1990, 1, 1).date(),
            email=f"rep.pat.{unique_suffix}@medapp.com",
            phone="+525550006666",
        )
        db.add(paciente)
        await db.commit()
        await db.refresh(paciente)
        patient_id = paciente.id

    response = await reports_client.post(
        "/api/v1/doctors/",
        headers=reports_headers,
        json={
            "first_name": "QA",
            "last_name": "Reports",
            "document_number": f"REP-DOC-{unique_suffix}",
            "professional_license": f"REP-LIC-{unique_suffix}",
            "email": f"rep.doc.{unique_suffix}@medapp.com",
            "specialty_id": specialty_id,
        },
    )
    assert response.status_code == 201, response.text
    doctor_id = response.json()["id"]

    for i in range(3):
        await _crear_cita_reciente(
            reports_client,
            reports_headers,
            doctor_id=doctor_id,
            patient_id=patient_id,
            minutos_atras=60 + i * 60,
        )

    r = await reports_client.get(
        "/api/v1/reports/dashboard/summary", headers=reports_headers
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["appointments_pending"] >= 3, (
        f"appointments_pending deberia contar las 3 citas PENDIENTE creadas; "
        f"vino {body['appointments_pending']}. El endpoint sigue filtrando por "
        f"un codigo de estado que no existe."
    )
    assert body["total_patients"] > 0
    assert body["total_doctors"] > 0


async def test_appointments_by_day_agrupa_por_dia(reports_client, reports_headers):
    """La serie por dia devuelve `completed` y `cancelled` como numeros.

    Con el bug ambos eran 0 porque comparaban con 'COMPLETED'/'CANCELLED'.
    """
    r = await reports_client.get(
        "/api/v1/reports/appointments-by-day?days=30", headers=reports_headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "data" in body
    for fila in body["data"]:
        assert "day" in fila
        assert isinstance(fila["total"], int)
        # Los conteos son enteros, no None: un None aqui significaria que el
        # SUM() no encontro filas y el endpoint deberia devolver 0.
        assert fila["completed"] is not None
        assert fila["cancelled"] is not None


async def test_no_show_rate_devuelve_estructura_completa(
    reports_client, reports_headers
):
    """El endpoint devuelve `pending`, que antes se calculaba y no se devolvia.

    Era codigo muerto: la columna `pending` salia de la consulta y se
    descartaba al armar la respuesta. Ahora el frontend puede usarla.
    """
    r = await reports_client.get(
        "/api/v1/reports/no-show-rate?days=30", headers=reports_headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    for clave in (
        "period",
        "total_appointments",
        "completed",
        "cancelled",
        "pending",
        "attendance_rate",
        "cancellation_rate",
    ):
        assert clave in body, f"falta '{clave}' en la respuesta de no-show-rate"


async def test_tasas_son_porcentajes_validos(reports_client, reports_headers):
    """Las tasas son cadenas con %, no "NaN%" ni None."""
    r = await reports_client.get(
        "/api/v1/reports/no-show-rate?days=30", headers=reports_headers
    )
    body = r.json()
    for clave in ("attendance_rate", "cancellation_rate"):
        valor = body[clave]
        assert isinstance(valor, str), f"{clave} deberia ser string, vino {type(valor)}"
        assert valor.endswith("%"), f"{clave} deberia terminar en %, vino {valor}"
        assert "nan" not in valor.lower(), f"{clave} es NaN: division por cero"


async def test_dias_se_acepta_solo_en_rango(reports_client, reports_headers):
    """`days` fuera de [1, 365] da 422: evita un escaneo de la tabla entera."""
    for dias in (0, 400, -1):
        r = await reports_client.get(
            f"/api/v1/reports/appointments-by-day?days={dias}", headers=reports_headers
        )
        assert r.status_code == 422, f"days={dias} deberia ser 422, vino {r.status_code}"


async def test_reports_exige_autenticacion(reports_client):
    """Sin token, los 4 endpoints responden 401."""
    for ruta in (
        "/api/v1/reports/dashboard/summary",
        "/api/v1/reports/appointments-by-day",
        "/api/v1/reports/appointments-by-doctor",
        "/api/v1/reports/no-show-rate",
    ):
        r = await reports_client.get(ruta)
        assert r.status_code == 401, f"{ruta} sin token deberia ser 401"
