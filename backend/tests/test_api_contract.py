"""Tests de contrato del API (certificación del desarrollo).

Certifican las reglas de negocio que garantizan "cero duplicados":

* Identidad única por persona física (`document_number`) en pacientes y doctores.
* Unicidad de email (pacientes/doctores) y licencia profesional (doctores).
* Edición sin falsos positivos (el propio registro no choca consigo mismo).
* Agenda: solapamiento del mismo doctor -> 409, citas adyacentes permitidas,
  validación de rango horario y existencia de paciente/doctor.

Se ejecutan dentro del contenedor:  ``make test``
"""

from datetime import datetime, timedelta, timezone

BASE = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
async def _first_specialty_id(client, headers, suffix):
    """Devuelve (id, creada) de una especialidad existente o recién creada."""
    response = await client.get("/api/v1/specialties/", headers=headers)
    assert response.status_code == 200, response.text
    if response.json():
        return response.json()[0]["id"], False
    response = await client.post(
        "/api/v1/specialties/", headers=headers, json={"name": f"QA Spec {suffix}"}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"], True


def _patient_payload(suffix, document=None, email=None):
    return {
        "first_name": "QA",
        "last_name": f"Paciente {suffix}",
        "document_number": document or f"QA-PAT-{suffix}",
        "birth_date": "1990-01-01",
        "email": email or f"qa.pat.{suffix}@medapp.com",
        "phone": "555-0000",
    }


def _doctor_payload(suffix, specialty_id, document=None, email=None, license_=None):
    return {
        "specialty_id": specialty_id,
        "first_name": "QA",
        "last_name": f"Doctor {suffix}",
        "document_number": document or f"QA-DOC-{suffix}",
        "professional_license": license_ or f"QA-LIC-{suffix}",
        "email": email or f"qa.doc.{suffix}@medapp.com",
        "phone": "555-1111",
    }


async def _create_patient(client, headers, suffix, document=None, email=None):
    payload = _patient_payload(suffix, document, email)
    return await client.post("/api/v1/patients/", headers=headers, json=payload), payload


async def _create_doctor(
    client, headers, suffix, specialty_id, document=None, email=None, license_=None
):
    payload = _doctor_payload(suffix, specialty_id, document, email, license_)
    return await client.post("/api/v1/doctors/", headers=headers, json=payload), payload


# --------------------------------------------------------------------------
# Autenticación y catálogos
# --------------------------------------------------------------------------
async def test_login_rechaza_credenciales_invalidas(client):
    response = await client.post(
        "/api/v1/login/access-token",
        data={"username": "no-existe@medapp.com", "password": "incorrecta"},
    )
    assert response.status_code in (400, 401)


async def test_endpoints_protegidos_requieren_token(client):
    response = await client.get("/api/v1/patients/")
    assert response.status_code == 401


async def test_catalogo_estados_de_cita(client, auth_headers):
    response = await client.get("/api/v1/appointment-statuses/", headers=auth_headers)
    assert response.status_code == 200, response.text
    codes = {item["code"] for item in response.json()}
    assert {"PENDIENTE", "CONFIRMADA", "COMPLETADA", "CANCELADA"} <= codes


# --------------------------------------------------------------------------
# Pacientes: documento y email únicos
# --------------------------------------------------------------------------
async def test_paciente_documento_y_email_unicos(client, auth_headers, unique_suffix):
    suffix = unique_suffix
    response, payload = await _create_patient(client, auth_headers, suffix)
    assert response.status_code == 201, response.text
    patient_id = response.json()["id"]
    assert response.json()["document_number"] == payload["document_number"]

    try:
        # Documento duplicado (email distinto) -> 400
        response = await client.post(
            "/api/v1/patients/",
            headers=auth_headers,
            json={**payload, "email": f"qa.pat.dup.{suffix}@medapp.com"},
        )
        assert response.status_code == 400, response.text
        assert response.json()["detail"]["status"] == "error"

        # Email duplicado (documento distinto) -> 400
        response = await client.post(
            "/api/v1/patients/",
            headers=auth_headers,
            json={**payload, "document_number": f"QA-PAT-EMA-{suffix}"},
        )
        assert response.status_code == 400, response.text

        # Editar conservando el propio documento -> 200 (sin falso positivo)
        response = await client.put(
            f"/api/v1/patients/{patient_id}",
            headers=auth_headers,
            json={"document_number": payload["document_number"], "phone": "555-0009"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["phone"] == "555-0009"

        # Segundo paciente: robar su documento desde el primero -> 400
        response2, payload2 = await _create_patient(
            client, auth_headers, f"{suffix}b", document=f"QA-PAT-2-{suffix}"
        )
        assert response2.status_code == 201, response2.text
        patient2_id = response2.json()["id"]
        try:
            response = await client.put(
                f"/api/v1/patients/{patient_id}",
                headers=auth_headers,
                json={"document_number": payload2["document_number"]},
            )
            assert response.status_code == 400, response.text
        finally:
            await client.delete(f"/api/v1/patients/{patient2_id}", headers=auth_headers)

        # Inexistente -> 404
        response = await client.get("/api/v1/patients/99999999", headers=auth_headers)
        assert response.status_code == 404
    finally:
        await client.delete(f"/api/v1/patients/{patient_id}", headers=auth_headers)


# --------------------------------------------------------------------------
# Doctores: documento, licencia, email y especialidad
# --------------------------------------------------------------------------
async def test_doctor_documento_licencia_y_especialidad(
    client, auth_headers, unique_suffix
):
    suffix = unique_suffix
    specialty_id, specialty_created = await _first_specialty_id(
        client, auth_headers, suffix
    )
    response, payload = await _create_doctor(
        client, auth_headers, suffix, specialty_id
    )
    assert response.status_code == 201, response.text
    doctor_id = response.json()["id"]

    try:
        # Documento duplicado (licencia y email distintos) -> 400
        response = await client.post(
            "/api/v1/doctors/",
            headers=auth_headers,
            json={
                **payload,
                "professional_license": f"QA-LIC-DUP-{suffix}",
                "email": f"qa.doc.dup.{suffix}@medapp.com",
            },
        )
        assert response.status_code == 400, response.text

        # Licencia duplicada (documento y email distintos) -> 400
        response = await client.post(
            "/api/v1/doctors/",
            headers=auth_headers,
            json={
                **payload,
                "document_number": f"QA-DOC-LIC-{suffix}",
                "email": f"qa.doc.lic.{suffix}@medapp.com",
            },
        )
        assert response.status_code == 400, response.text

        # Email duplicado (documento y licencia distintos) -> 400
        response = await client.post(
            "/api/v1/doctors/",
            headers=auth_headers,
            json={
                **payload,
                "document_number": f"QA-DOC-EMA-{suffix}",
                "professional_license": f"QA-LIC-EMA-{suffix}",
            },
        )
        assert response.status_code == 400, response.text

        # Especialidad inexistente -> 404
        response = await client.post(
            "/api/v1/doctors/",
            headers=auth_headers,
            json={
                **payload,
                "document_number": f"QA-DOC-ESP-{suffix}",
                "professional_license": f"QA-LIC-ESP-{suffix}",
                "email": f"qa.doc.esp.{suffix}@medapp.com",
                "specialty_id": 99999999,
            },
        )
        assert response.status_code == 404, response.text

        # Editar conservando el propio documento -> 200
        response = await client.put(
            f"/api/v1/doctors/{doctor_id}",
            headers=auth_headers,
            json={"document_number": payload["document_number"], "phone": "555-1199"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["phone"] == "555-1199"
    finally:
        await client.delete(f"/api/v1/doctors/{doctor_id}", headers=auth_headers)
        if specialty_created:
            await client.delete(
                f"/api/v1/specialties/{specialty_id}", headers=auth_headers
            )


# --------------------------------------------------------------------------
# Agenda: solapamiento y validaciones
# --------------------------------------------------------------------------
async def test_cita_solapamiento_y_validaciones(client, auth_headers, unique_suffix):
    suffix = unique_suffix
    specialty_id, specialty_created = await _first_specialty_id(
        client, auth_headers, suffix
    )
    response, _ = await _create_patient(
        client, auth_headers, suffix, document=f"QA-APT-PAT-{suffix}"
    )
    assert response.status_code == 201, response.text
    patient_id = response.json()["id"]

    response, _ = await _create_doctor(
        client,
        auth_headers,
        suffix,
        specialty_id,
        document=f"QA-APT-DOC-{suffix}",
        email=f"qa.apt.doc.{suffix}@medapp.com",
        license_=f"QA-APT-LIC-{suffix}",
    )
    assert response.status_code == 201, response.text
    doctor_id = response.json()["id"]

    created_appointments: list[int] = []

    def slot(offset_start, offset_end):
        return {
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "start_datetime": (BASE + offset_start).isoformat(),
            "end_datetime": (BASE + offset_end).isoformat(),
            "reason": "QA control",
        }

    try:
        # Cita válida -> 201 en estado PENDIENTE
        response = await client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json=slot(timedelta(0), timedelta(minutes=30)),
        )
        assert response.status_code == 201, response.text
        appointment = response.json()
        created_appointments.append(appointment["id"])
        assert appointment["status"]["code"] == "PENDIENTE"
        assert appointment["status_id"] is not None

        # Solapamiento del mismo doctor -> 409
        response = await client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json=slot(timedelta(minutes=10), timedelta(minutes=40)),
        )
        assert response.status_code == 409, response.text
        assert response.json()["detail"]["status"] == "error"

        # Cita adyacente (empieza justo al terminar la anterior) -> 201
        response = await client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json=slot(timedelta(minutes=30), timedelta(minutes=60)),
        )
        assert response.status_code == 201, response.text
        created_appointments.append(response.json()["id"])

        # Rango inválido (fin <= inicio) -> 400
        response = await client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json=slot(timedelta(hours=3), timedelta(hours=2)),
        )
        assert response.status_code == 400, response.text

        # Paciente inexistente -> 404
        response = await client.post(
            "/api/v1/appointments/",
            headers=auth_headers,
            json={**slot(timedelta(hours=5), timedelta(hours=6)), "patient_id": 99999999},
        )
        assert response.status_code == 404, response.text
    finally:
        for appointment_id in created_appointments:
            await client.delete(
                f"/api/v1/appointments/{appointment_id}", headers=auth_headers
            )
        await client.delete(f"/api/v1/patients/{patient_id}", headers=auth_headers)
        await client.delete(f"/api/v1/doctors/{doctor_id}", headers=auth_headers)
        if specialty_created:
            await client.delete(
                f"/api/v1/specialties/{specialty_id}", headers=auth_headers
            )
