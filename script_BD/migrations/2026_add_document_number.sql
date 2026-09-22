-- Agrega el número de documento legal (único) a pacientes y médicos.
-- Idempotente: puede ejecutarse varias veces sin error.
-- Ejecutar:  docker exec -i medical_pgvector psql -U postgres -d appointment < script_BD/2026_add_document_number.sql

BEGIN;

-- ---------- Pacientes ----------
ALTER TABLE patients ADD COLUMN IF NOT EXISTS document_number VARCHAR(50);

UPDATE patients
SET document_number = 'LEGACY-PAT-' || id
WHERE document_number IS NULL;

ALTER TABLE patients ALTER COLUMN document_number SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'patients_document_number_key'
    ) THEN
        ALTER TABLE patients
            ADD CONSTRAINT patients_document_number_key UNIQUE (document_number);
    END IF;
END $$;

-- ---------- Médicos ----------
ALTER TABLE doctors ADD COLUMN IF NOT EXISTS document_number VARCHAR(50);

UPDATE doctors
SET document_number = 'LEGACY-DOC-' || id
WHERE document_number IS NULL;

ALTER TABLE doctors ALTER COLUMN document_number SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'doctors_document_number_key'
    ) THEN
        ALTER TABLE doctors
            ADD CONSTRAINT doctors_document_number_key UNIQUE (document_number);
    END IF;
END $$;

COMMIT;
