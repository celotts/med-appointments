-- Datos de ejemplo (pacientes, doctores y citas).
-- Idempotente. Se carga solo cuando se pide:  make seed   (o   make up-test)
-- Requiere los catálogos (seed_catalogs.sql).

INSERT INTO specialties (name, description)
VALUES ('Medicina General', 'Atención primaria')
ON CONFLICT (name) DO NOTHING;

-- ---------- Doctores ----------
INSERT INTO doctors (specialty_id, first_name, last_name, document_number, professional_license, email, phone)
SELECT s.id, 'María', 'García', 'DEMO-DOC-001', 'DEMO-LIC-001', 'maria.garcia@clinic.com', '555-1001'
FROM specialties s
WHERE s.name = 'Medicina General'
  AND NOT EXISTS (SELECT 1 FROM doctors d WHERE d.document_number = 'DEMO-DOC-001');

INSERT INTO doctors (specialty_id, first_name, last_name, document_number, professional_license, email, phone)
SELECT s.id, 'Carlos', 'López', 'DEMO-DOC-002', 'DEMO-LIC-002', 'carlos.lopez@clinic.com', '555-1002'
FROM specialties s
WHERE s.name = 'Medicina General'
  AND NOT EXISTS (SELECT 1 FROM doctors d WHERE d.document_number = 'DEMO-DOC-002');

-- ---------- Pacientes ----------
INSERT INTO patients (first_name, last_name, document_number, birth_date, email, phone)
SELECT 'Juan', 'Pérez', 'DEMO-PAT-001', DATE '1985-03-15', 'juan.perez@email.com', '555-2001'
WHERE NOT EXISTS (SELECT 1 FROM patients p WHERE p.document_number = 'DEMO-PAT-001');

INSERT INTO patients (first_name, last_name, document_number, birth_date, email, phone)
SELECT 'Ana', 'Martínez', 'DEMO-PAT-002', DATE '1990-07-22', 'ana.martinez@email.com', '555-2002'
WHERE NOT EXISTS (SELECT 1 FROM patients p WHERE p.document_number = 'DEMO-PAT-002');

-- ---------- Citas ----------
-- Se asignan al superusuario (la API filtra las citas por usuario creador).
INSERT INTO appointments (patient_id, doctor_id, status_id, user_id, start_datetime, end_datetime, reason)
SELECT p.id, d.id, st.id, u.id, TIMESTAMPTZ '2026-10-01 10:00:00+00', TIMESTAMPTZ '2026-10-01 10:30:00+00', 'Control cardiológico demo'
FROM patients p, doctors d, appointment_statuses st, users u
WHERE p.document_number = 'DEMO-PAT-001'
  AND d.document_number = 'DEMO-DOC-001'
  AND st.code = 'PENDIENTE'
  AND u.email = 'admin@medapp.com'
  AND NOT EXISTS (SELECT 1 FROM appointments a WHERE a.reason = 'Control cardiológico demo');

INSERT INTO appointments (patient_id, doctor_id, status_id, user_id, start_datetime, end_datetime, reason)
SELECT p.id, d.id, st.id, u.id, TIMESTAMPTZ '2026-10-01 11:00:00+00', TIMESTAMPTZ '2026-10-01 11:30:00+00', 'Consulta general demo'
FROM patients p, doctors d, appointment_statuses st, users u
WHERE p.document_number = 'DEMO-PAT-002'
  AND d.document_number = 'DEMO-DOC-002'
  AND st.code = 'PENDIENTE'
  AND u.email = 'admin@medapp.com'
  AND NOT EXISTS (SELECT 1 FROM appointments a WHERE a.reason = 'Consulta general demo');
