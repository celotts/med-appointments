"""Auditoria de notas medicas.

Las notas clinicas contienen diagnostico, tratamiento y observaciones: el dato
mas sensible del sistema. Estos tests comprueban que crear, editar y borrar una
nota deja rastro completo, incluido el contenido previo.

Ver `docs/AUDITORIA.md`.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from core.crud_medical_note_audit import TABLA_NOTAS
from core.db import SessionLocal
from httpx import ASGITransport, AsyncClient
from initial_data import main as bootstrap_initial_data
from main import app
from models.audit import AuditAction
from models.audit import AuditLog as AuditLogModel
from models.specialty import Specialty
from sqlalchemy import select


@pytest_asyncio.fixture(scope="session")
async def notes_client():
    await bootstrap_initial_data()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(scope="session")
async def notes_headers(notes_client):
    import os

    response = await notes_client.post(
        "/api/v1/login/access-token",
        data={
            "username": os.environ["FIRST_SUPERUSER_EMAIL"],
            "password": os.environ["FIRST_SUPERUSER_PASSWORD"],
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _parse(valor: str | None) -> dict:
    return json.loads(valor) if valor else {}


async def _registros(db, note_id: int) -> list:
    """Registros de una nota clinica, en orden cronologico."""
    from core.crud_audit import normalizar_record_id

    result = await db.execute(
        select(AuditLogModel)
        .where(AuditLogModel.record_id == normalizar_record_id(note_id))
        .where(AuditLogModel.table_name == TABLA_NOTAS)
        .order_by(AuditLogModel.created_at, AuditLogModel.id)
    )
    # Los valores se extraen aqui: fuera de la sesion los objetos estan
    # desligados (DetachedInstanceError).
    return [
        {
            "action": r.action,
            "old": _parse(r.old_value),
            "new": _parse(r.new_value),
            "user_id": r.user_id,
        }
        for r in result.scalars().all()
    ]


@pytest_asyncio.fixture
async def cita_con_nota(notes_client, notes_headers, unique_suffix):
    """Cita PENDIENTE con una nota clinica, mas sus fixtures."""
    async with SessionLocal() as db:
        specialty = (await db.execute(select(Specialty).limit(1))).scalars().first()
        if specialty is None:
            pytest.skip("hace falta una especialidad (make seed)")
        specialty_id = specialty.id

    r = await notes_client.post(
        "/api/v1/patients/",
        headers=notes_headers,
        json={
            "first_name": "QA",
            "last_name": f"Nota {unique_suffix}",
            "document_number": f"QA-NOTE-PAT-{unique_suffix}",
            "birth_date": "1990-01-01",
            "email": f"qa.note.pat.{unique_suffix}@medapp.com",
            "phone": "+525550000010",
        },
    )
    assert r.status_code == 201, r.text
    patient_id = r.json()["id"]

    r = await notes_client.post(
        "/api/v1/doctors/",
        headers=notes_headers,
        json={
            "first_name": "QA",
            "last_name": f"Nota Doc {unique_suffix}",
            "document_number": f"QA-NOTE-DOC-{unique_suffix}",
            "professional_license": f"QA-NOTE-LIC-{unique_suffix}",
            "email": f"qa.note.doc.{unique_suffix}@medapp.com",
            "specialty_id": specialty_id,
        },
    )
    assert r.status_code == 201, r.text
    doctor_id = r.json()["id"]

    inicio = (datetime.now(timezone.utc) + timedelta(days=8)).isoformat()
    fin = (datetime.now(timezone.utc) + timedelta(days=8, minutes=30)).isoformat()
    r = await notes_client.post(
        "/api/v1/appointments/",
        headers=notes_headers,
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "start_datetime": inicio,
            "end_datetime": fin,
            "reason": "QA nota clinica",
        },
    )
    assert r.status_code == 201, r.text
    appointment_id = r.json()["id"]

    r = await notes_client.post(
        "/api/v1/notes/",
        headers=notes_headers,
        json={
            "appointment_id": appointment_id,
            "diagnosis": "Hipertension leve",
            "treatment": "Losartan 50mg",
            "observations": "Controlar tension semanal",
        },
    )
    assert r.status_code == 201, r.text
    note_id = r.json()["id"]

    yield appointment_id, note_id, patient_id, doctor_id

    await notes_client.delete(f"/api/v1/appointments/{appointment_id}", headers=notes_headers)
    await notes_client.delete(f"/api/v1/patients/{patient_id}", headers=notes_headers)
    await notes_client.delete(f"/api/v1/doctors/{doctor_id}", headers=notes_headers)


# --------------------------------------------------------------------------
# Creacion
# --------------------------------------------------------------------------
async def test_crear_nota_audita_el_contenido(cita_con_nota):
    """Crear una nota deja el contenido clinico completo en el registro."""
    _, note_id, *_ = cita_con_nota

    async with SessionLocal() as db:
        registros = await _registros(db, note_id)

    assert registros, "crear una nota debe auditarse"
    creacion = registros[0]
    assert creacion["action"] == AuditAction.INSERT
    assert creacion["old"] == {}, "la creacion no tiene estado previo"
    assert creacion["new"]["diagnosis"] == "Hipertension leve"
    assert creacion["new"]["treatment"] == "Losartan 50mg"
    assert creacion["new"]["observations"] == "Controlar tension semanal"
    assert creacion["new"]["evento"] == "nota_creada"


async def test_crear_nota_identifica_al_actor(cita_con_nota):
    _, note_id, *_ = cita_con_nota

    async with SessionLocal() as db:
        registros = await _registros(db, note_id)

    assert registros[0]["user_id"] is not None, "el registro debe identificar al actor"


# --------------------------------------------------------------------------
# Edicion: el contenido previo es lo que hace el rastro util
# --------------------------------------------------------------------------
async def test_editar_nota_conserva_el_valor_anterior(notes_client, notes_headers, cita_con_nota):
    """Una correccion debe dejar constancia de que decia antes."""
    _, note_id, *_ = cita_con_nota

    r = await notes_client.put(
        f"/api/v1/notes/{note_id}",
        headers=notes_headers,
        json={"diagnosis": "Hipertension moderada", "treatment": "Losartan 100mg"},
    )
    assert r.status_code == 200, r.text

    async with SessionLocal() as db:
        registros = await _registros(db, note_id)

    assert len(registros) == 2, "debe existir creacion + edicion"
    edicion = registros[1]
    assert edicion["action"] == AuditAction.UPDATE

    # Lo que decia antes.
    assert edicion["old"]["antes"]["diagnosis"] == "Hipertension leve"
    assert edicion["old"]["antes"]["treatment"] == "Losartan 50mg"
    # Lo que dice ahora.
    assert edicion["new"]["despues"]["diagnosis"] == "Hipertension moderada"
    assert edicion["new"]["despues"]["treatment"] == "Losartan 100mg"
    # Los campos tocados.
    assert sorted(edicion["new"]["campos_modificados"]) == ["diagnosis", "treatment"]
    # `observations` no se toco: no debe aparecer como modificado.
    assert "observations" not in edicion["new"]["campos_modificados"]


async def test_editar_una_nota_tres_veces_deja_historial_completo(
    notes_client, notes_headers, cita_con_nota
):
    """Cada edicion guarda su propio par antes/despues."""
    _, note_id, *_ = cita_con_nota

    for diagnostico in ("Version 2", "Version 3", "Version 4"):
        r = await notes_client.put(
            f"/api/v1/notes/{note_id}", headers=notes_headers, json={"diagnosis": diagnostico}
        )
        assert r.status_code == 200, r.text

    async with SessionLocal() as db:
        registros = await _registros(db, note_id)

    # 1 creacion + 3 ediciones
    assert len(registros) == 4

    # La cadena de diagnosticos se puede reconstruir.
    cadena = [registros[0]["new"]["diagnosis"]]
    for registro in registros[1:]:
        assert registro["new"]["despues"]["diagnosis"] == registro["new"]["despues"]["diagnosis"]
        cadena.append(registro["new"]["despues"]["diagnosis"])

    assert cadena == [
        "Hipertension leve",
        "Version 2",
        "Version 3",
        "Version 4",
    ], f"la cadena de versiones debe ser reconstruible; se obtuvo {cadena}"


# --------------------------------------------------------------------------
# Borrado
# --------------------------------------------------------------------------
async def test_borrar_nota_conserva_el_contenido(
    notes_client, notes_headers, unique_suffix
):
    """Tras borrar la nota, el registro conserva lo que decía."""
    async with SessionLocal() as db:
        specialty = (await db.execute(select(Specialty).limit(1))).scalars().first()
        if specialty is None:
            pytest.skip("hace falta una especialidad (make seed)")
        specialty_id = specialty.id

    r = await notes_client.post(
        "/api/v1/patients/",
        headers=notes_headers,
        json={
            "first_name": "QA",
            "last_name": f"Borrar nota {unique_suffix}",
            "document_number": f"QA-BNOTE-PAT-{unique_suffix}",
            "birth_date": "1990-01-01",
            "email": f"qa.bnote.pat.{unique_suffix}@medapp.com",
            "phone": "+525550000011",
        },
    )
    assert r.status_code == 201, r.text
    patient_id = r.json()["id"]

    r = await notes_client.post(
        "/api/v1/doctors/",
        headers=notes_headers,
        json={
            "first_name": "QA",
            "last_name": f"Borrar Doc {unique_suffix}",
            "document_number": f"QA-BNOTE-DOC-{unique_suffix}",
            "professional_license": f"QA-BNOTE-LIC-{unique_suffix}",
            "email": f"qa.bnote.doc.{unique_suffix}@medapp.com",
            "specialty_id": specialty_id,
        },
    )
    assert r.status_code == 201, r.text
    doctor_id = r.json()["id"]

    inicio = (datetime.now(timezone.utc) + timedelta(days=9)).isoformat()
    fin = (datetime.now(timezone.utc) + timedelta(days=9, minutes=30)).isoformat()
    r = await notes_client.post(
        "/api/v1/appointments/",
        headers=notes_headers,
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "start_datetime": inicio,
            "end_datetime": fin,
            "reason": "QA borrar nota",
        },
    )
    assert r.status_code == 201, r.text
    appointment_id = r.json()["id"]

    r = await notes_client.post(
        "/api/v1/notes/",
        headers=notes_headers,
        json={
            "appointment_id": appointment_id,
            "diagnosis": "Diagnostico que debe sobrevivir al borrado",
            "treatment": "Tratamiento confidencial",
            "observations": "Observacion sensible",
        },
    )
    assert r.status_code == 201, r.text
    note_id = r.json()["id"]

    r = await notes_client.delete(f"/api/v1/notes/{note_id}", headers=notes_headers)
    assert r.status_code == 200, r.text

    # La nota ya no existe...
    r = await notes_client.get(f"/api/v1/notes/{note_id}", headers=notes_headers)
    assert r.status_code == 404, "la nota debe estar borrada"

    # ...pero su contenido sigue en la auditoria.
    async with SessionLocal() as db:
        registros = await _registros(db, note_id)
        await notes_client.delete(
            f"/api/v1/appointments/{appointment_id}", headers=notes_headers
        )
        await notes_client.delete(f"/api/v1/patients/{patient_id}", headers=notes_headers)
        await notes_client.delete(f"/api/v1/doctors/{doctor_id}", headers=notes_headers)

    borrados = [r for r in registros if r["action"] == AuditAction.DELETE]
    assert borrados, "el borrado debe quedar auditado"
    assert borrados[0]["old"]["diagnosis"] == "Diagnostico que debe sobrevivir al borrado"
    assert borrados[0]["old"]["treatment"] == "Tratamiento confidencial"
    assert borrados[0]["old"]["observations"] == "Observacion sensible"


# --------------------------------------------------------------------------
# Garantias
# --------------------------------------------------------------------------
async def test_crear_nota_dos_veces_falla_y_no_audita(
    notes_client, notes_headers, cita_con_nota
):
    """Una nota duplicada se rechaza y no genera un segundo registro."""
    appointment_id, note_id, *_ = cita_con_nota

    async with SessionLocal() as db:
        antes = len(await _registros(db, note_id))

    r = await notes_client.post(
        "/api/v1/notes/",
        headers=notes_headers,
        json={
            "appointment_id": appointment_id,
            "diagnosis": "Intento duplicado",
        },
    )
    assert r.status_code == 400, f"debe rechazar la segunda nota: {r.text}"

    async with SessionLocal() as db:
        despues = len(await _registros(db, note_id))

    assert antes == despues, "un intento fallido no debe auditarse"


async def test_endpoint_historial_de_nota_requiere_admin(notes_client, notes_headers, cita_con_nota):
    """El historial de una nota clinica no es accesible sin rol admin."""
    _, note_id, *_ = cita_con_nota

    # Sin token
    r = await notes_client.get(f"/api/v1/audit/notes/{note_id}")
    assert r.status_code == 401, "sin token debe ser 401"

    # Con token de admin si funciona
    r = await notes_client.get(
        f"/api/v1/audit/notes/{note_id}", headers=notes_headers
    )
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)
