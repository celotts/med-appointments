#!/bin/bash
# Seed script para datos de prueba

echo "Esperando a que PostgreSQL esté listo..."
until podman exec medical_pgvector pg_isready -U root -d appointment >/dev/null 2>&1; do
  sleep 1
done

echo "Insertando datos de prueba..."

podman exec medical_pgvector psql -U root -d appointment << 'EOF'
-- Specialties
INSERT INTO specialties (name, description) VALUES 
('Cardiología', 'Especialidad del corazón'),
('Medicina General', 'Atención primaria'),
('Neurología', 'Sistema nervioso')
ON CONFLICT DO NOTHING;

-- Doctors
INSERT INTO doctors (specialty_id, first_name, last_name, professional_license, email, phone) VALUES 
(1, 'María', 'García', 'LIC-001', 'maria.garcia@clinic.com', '555-1001'),
(2, 'Carlos', 'López', 'LIC-002', 'carlos.lopez@clinic.com', '555-1002')
ON CONFLICT DO NOTHING;

-- Patients
INSERT INTO patients (first_name, last_name, birth_date, email, phone) VALUES 
('Juan', 'Pérez', '1985-03-15', 'juan.perez@email.com', '555-2001'),
('Ana', 'Martínez', '1990-07-22', 'ana.martinez@email.com', '555-2002')
ON CONFLICT DO NOTHING;

-- Appointment Statuses
INSERT INTO appointment_statuses (code, description) VALUES 
('PROGRAMADA', 'Cita programada'),
('CONFIRMADA', 'Cita confirmada'),
('EN_PROGRESO', 'En progreso'),
('COMPLETADA', 'Completada'),
('CANCELADA', 'Cancelada')
ON CONFLICT DO NOTHING;

-- Appointments
INSERT INTO appointments (patient_id, doctor_id, status_id, start_datetime, end_datetime, reason) VALUES 
(1, 1, 1, '2026-09-10 10:00:00', '2026-09-10 10:30:00', 'Control cardiológico'),
(2, 2, 1, '2026-09-10 11:00:00', '2026-09-10 11:30:00', 'Consulta general')
ON CONFLICT DO NOTHING;

-- Waitlist table
CREATE TABLE IF NOT EXISTS waitlist (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    fecha_preferida DATE NOT NULL,
    motivo TEXT,
    estado VARCHAR(20) DEFAULT 'PENDIENTE',
    created_at TIMESTAMP DEFAULT NOW(),
    notified_at TIMESTAMP,
    CONSTRAINT fk_waitlist_patient FOREIGN KEY (patient_id) REFERENCES patients (id) ON DELETE CASCADE,
    CONSTRAINT fk_waitlist_doctor FOREIGN KEY (doctor_id) REFERENCES doctors (id) ON DELETE CASCADE
);

EOF

echo "Datos de prueba insertados."