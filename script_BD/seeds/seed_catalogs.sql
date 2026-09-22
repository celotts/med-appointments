-- Catálogos base: estados de cita y especialidades.
-- Idempotente (se puede ejecutar varias veces).
-- Se carga solo cuando se pide:  make seed   (o   make up-test)

INSERT INTO appointment_statuses (code, description) VALUES
    ('PENDIENTE', 'Cita pendiente'),
    ('CONFIRMADA', 'Cita confirmada'),
    ('COMPLETADA', 'Cita completada'),
    ('CANCELADA', 'Cita cancelada'),
    ('SUSPENDIDA', 'Cita suspendida'),
    ('REAGENDADA', 'Cita reagendada')
ON CONFLICT (code) DO NOTHING;

INSERT INTO specialties (name, description) VALUES
    ('Medicina General', 'Atención primaria'),
    ('Cardiología', 'Especialidad del corazón'),
    ('Pediatría', 'Atención de niños y adolescentes')
ON CONFLICT (name) DO NOTHING;
