-- Catálogos base: estados de cita y especialidades.
-- Idempotente (se puede ejecutar varias veces).
-- Se carga solo cuando se pide:  make seed   (o   make up-test)
--
-- Los 8 estados de cita deben coincidir con el enum AppointmentStatusCode de
-- backend/app/schemas/appointment.py. Si agregas o quitas uno, actualiza
-- tambien: schemas/appointment.py, la migracion de normalizacion de estados
-- y el frontend. Un estado que no exista aqui rompe /wait, /start y /attend.

INSERT INTO appointment_statuses (code, description) VALUES
    ('PENDIENTE', 'Cita pendiente de confirmacion'),
    ('CONFIRMADA', 'Cita confirmada'),
    ('EN ESPERA', 'Cita en sala de espera'),
    ('EN PROCESO', 'Consulta en curso'),
    ('ATENDIDA', 'Cita atendida'),
    ('CANCELADA', 'Cita cancelada'),
    ('SUSPENDIDA', 'Cita suspendida'),
    ('REAGENDADA', 'Cita reagendada a nueva fecha')
ON CONFLICT (code) DO NOTHING;

INSERT INTO specialties (name, description) VALUES
    ('Medicina General', 'Atención primaria'),
    ('Cardiología', 'Especialidad del corazón'),
    ('Pediatría', 'Atención de niños y adolescentes')
ON CONFLICT (name) DO NOTHING;
