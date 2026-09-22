-- Datos de demo con fechas HOY (18/09/2025) y 20/09/2025
-- Para probar indicadores visuales: delayed, proximity_rank, etc.
-- Hora actual: 18/09/2025 17:58 (5:58 PM)

-- Cita DEMORADA (empezó 09:00, ya pasó >15 min - son las 17:58)
INSERT INTO appointments (patient_id, doctor_id, status_id, user_id, start_datetime, end_datetime, reason)
SELECT p.id, d.id, st.id, u.id,
       TIMESTAMPTZ '2026-09-18 09:00:00+00',
       TIMESTAMPTZ '2026-09-18 09:30:00+00',
       'Cita DEMORADA 09:00 - prueba delayed'
FROM patients p, doctors d, appointment_statuses st, users u
WHERE p.document_number = 'DEMO-PAT-002'
  AND d.document_number = 'DEMO-DOC-001'
  AND st.code = 'PENDIENTE'
  AND u.email = 'admin@medapp.com'
  AND NOT EXISTS (SELECT 1 FROM appointments a WHERE a.reason = 'Cita DEMORADA 09:00 - prueba delayed');

-- Cita HOY 10:00 - proximity_rank_1 (ya pasó, pero era la más próxima)
INSERT INTO appointments (patient_id, doctor_id, status_id, user_id, start_datetime, end_datetime, reason)
SELECT p.id, d.id, st.id, u.id,
       TIMESTAMPTZ '2026-09-18 10:00:00+00',
       TIMESTAMPTZ '2026-09-18 10:30:00+00',
       'Control HOY 10:00 - prueba proximity_rank_1'
FROM patients p, doctors d, appointment_statuses st, users u
WHERE p.document_number = 'DEMO-PAT-001'
  AND d.document_number = 'DEMO-DOC-001'
  AND st.code = 'PENDIENTE'
  AND u.email = 'admin@medapp.com'
  AND NOT EXISTS (SELECT 1 FROM appointments a WHERE a.reason = 'Control HOY 10:00 - prueba proximity_rank_1');

-- Cita HOY 11:00 - proximity_rank_2
INSERT INTO appointments (patient_id, doctor_id, status_id, user_id, start_datetime, end_datetime, reason)
SELECT p.id, d.id, st.id, u.id,
       TIMESTAMPTZ '2026-09-18 11:00:00+00',
       TIMESTAMPTZ '2026-09-18 11:30:00+00',
       'Control HOY 11:00 - prueba proximity_rank_2'
FROM patients p, doctors d, appointment_statuses st, users u
WHERE p.document_number = 'DEMO-PAT-001'
  AND d.document_number = 'DEMO-DOC-002'
  AND st.code = 'CONFIRMADA'
  AND u.email = 'admin@medapp.com'
  AND NOT EXISTS (SELECT 1 FROM appointments a WHERE a.reason = 'Control HOY 11:00 - prueba proximity_rank_2');

-- Cita FUTURA 20/09/2025 - proximity_rank_3
INSERT INTO appointments (patient_id, doctor_id, status_id, user_id, start_datetime, end_datetime, reason)
SELECT p.id, d.id, st.id, u.id,
       TIMESTAMPTZ '2026-09-20 10:00:00+00',
       TIMESTAMPTZ '2026-09-20 10:30:00+00',
       'Control 20/09 - prueba proximity_rank_3'
FROM patients p, doctors d, appointment_statuses st, users u
WHERE p.document_number = 'DEMO-PAT-002'
  AND d.document_number = 'DEMO-DOC-002'
  AND st.code = 'PENDIENTE'
  AND u.email = 'admin@medapp.com'
  AND NOT EXISTS (SELECT 1 FROM appointments a WHERE a.reason = 'Control 20/09 - prueba proximity_rank_3');

-- Cita FUTURA 20/09/2025 14:00
INSERT INTO appointments (patient_id, doctor_id, status_id, user_id, start_datetime, end_datetime, reason)
SELECT p.id, d.id, st.id, u.id,
       TIMESTAMPTZ '2026-09-20 14:00:00+00',
       TIMESTAMPTZ '2026-09-20 14:30:00+00',
       'Consulta 20/09 14:00 - prueba normal'
FROM patients p, doctors d, appointment_statuses st, users u
WHERE p.document_number = 'DEMO-PAT-001'
  AND d.document_number = 'DEMO-DOC-001'
  AND st.code = 'CONFIRMADA'
  AND u.email = 'admin@medapp.com'
  AND NOT EXISTS (SELECT 1 FROM appointments a WHERE a.reason = 'Consulta 20/09 14:00 - prueba normal');

-- Cita demorada en doctor 2 (CONFIRMADA, empezó 08:30, ya pasó >15 min)
INSERT INTO appointments (patient_id, doctor_id, status_id, user_id, start_datetime, end_datetime, reason)
SELECT p.id, d.id, st.id, u.id,
       TIMESTAMPTZ '2026-09-18 08:30:00+00',
       TIMESTAMPTZ '2026-09-18 09:00:00+00',
       'Demorada doctor 2 - 08:30'
FROM patients p, doctors d, appointment_statuses st, users u
WHERE p.document_number = 'DEMO-PAT-002'
  AND d.document_number = 'DEMO-DOC-002'
  AND st.code = 'CONFIRMADA'
  AND u.email = 'admin@medapp.com'
  AND NOT EXISTS (SELECT 1 FROM appointments a WHERE a.reason = 'Demorada doctor 2 - 08:30');

-- Cita COMPLETADA (no debe aparecer en delayed ni proximity)
INSERT INTO appointments (patient_id, doctor_id, status_id, user_id, start_datetime, end_datetime, reason)
SELECT p.id, d.id, st.id, u.id,
       TIMESTAMPTZ '2026-09-17 10:00:00+00',
       TIMESTAMPTZ '2026-09-17 10:30:00+00',
       'Completada ayer - prueba completed'
FROM patients p, doctors d, appointment_statuses st, users u
WHERE p.document_number = 'DEMO-PAT-001'
  AND d.document_number = 'DEMO-DOC-001'
  AND st.code = 'COMPLETADA'
  AND u.email = 'admin@medapp.com'
  AND NOT EXISTS (SELECT 1 FROM appointments a WHERE a.reason = 'Completada ayer - prueba completed');

-- Cita CANCELADA hoy 15:00
INSERT INTO appointments (patient_id, doctor_id, status_id, user_id, start_datetime, end_datetime, reason)
SELECT p.id, d.id, st.id, u.id,
       TIMESTAMPTZ '2026-09-18 15:00:00+00',
       TIMESTAMPTZ '2026-09-18 15:30:00+00',
       'Cancelada hoy 15:00'
FROM patients p, doctors d, appointment_statuses st, users u
WHERE p.document_number = 'DEMO-PAT-002'
  AND d.document_number = 'DEMO-DOC-002'
  AND st.code = 'CANCELADA'
  AND u.email = 'admin@medapp.com'
  AND NOT EXISTS (SELECT 1 FROM appointments a WHERE a.reason = 'Cancelada hoy 15:00');

-- Cita futura 20/09 14:00
INSERT INTO appointments (patient_id, doctor_id, status_id, user_id, start_datetime, end_datetime, reason)
SELECT p.id, d.id, st.id, u.id,
       TIMESTAMPTZ '2026-09-20 14:00:00+00',
       TIMESTAMPTZ '2026-09-20 14:30:00+00',
       'Consulta 20/09 14:00 - prueba normal'
FROM patients p, doctors d, appointment_statuses st, users u
WHERE p.document_number = 'DEMO-PAT-001'
  AND d.document_number = 'DEMO-DOC-001'
  AND st.code = 'CONFIRMADA'
  AND u.email = 'admin@medapp.com'
  AND NOT EXISTS (SELECT 1 FROM appointments a WHERE a.reason = 'Consulta 20/09 14:00 - prueba normal');
