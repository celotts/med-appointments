-- 1. Enable vector extension for pgvector
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;


-- ============================================================================
-- AUDIT TRIGGER FUNCTION
-- ============================================================================
CREATE OR REPLACE FUNCTION set_audit_role_id()
RETURNS TRIGGER AS $$
DECLARE
    v_role_id UUID;
BEGIN
    IF (TG_OP = 'INSERT') THEN
        NEW.created_at = COALESCE(NEW.created_at, NOW());
        IF (NEW.created_by_user_id IS NOT NULL) THEN
            SELECT role_id INTO v_role_id FROM users WHERE id = NEW.created_by_user_id;
            NEW.created_by_role_id = v_role_id;
        END IF;
    ELSIF (TG_OP = 'UPDATE') THEN
        NEW.updated_at = NOW();
        IF (NEW.updated_by_user_id IS NOT NULL AND (OLD.updated_by_user_id IS NULL OR NEW.updated_by_user_id <> OLD.updated_by_user_id)) THEN
            SELECT role_id INTO v_role_id FROM users WHERE id = NEW.updated_by_user_id;
            NEW.updated_by_role_id = v_role_id;
        END IF;
        IF (NEW.deleted_at IS NOT NULL AND OLD.deleted_at IS NULL) OR (NEW.deleted_by_user_id IS NOT NULL AND OLD.deleted_by_user_id IS NULL) THEN
            NEW.deleted_at = COALESCE(NEW.deleted_at, NOW());
            IF (NEW.deleted_by_user_id IS NOT NULL) THEN
                SELECT role_id INTO v_role_id FROM users WHERE id = NEW.deleted_by_user_id;
                NEW.deleted_by_role_id = v_role_id;
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- ROLES AND USERS
-- ============================================================================
CREATE TABLE roles (
    id UUID PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    created_by_user_id UUID,
    updated_by_user_id UUID,
    deleted_by_user_id UUID,
    created_by_role_id UUID,
    updated_by_role_id UUID,
    deleted_by_role_id UUID
);


CREATE TRIGGER trigger_roles_audit
BEFORE INSERT OR UPDATE ON roles
FOR EACH ROW EXECUTE FUNCTION set_audit_role_id();


CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password TEXT NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    address VARCHAR(255) NOT NULL DEFAULT 'N/A',
    phone VARCHAR(255) NOT NULL,
    phone2 VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_specialist BOOLEAN DEFAULT FALSE,
    role_id UUID NOT NULL REFERENCES roles(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    created_by_user_id UUID REFERENCES users(id),
    updated_by_user_id UUID REFERENCES users(id),
    deleted_by_user_id UUID REFERENCES users(id),
    created_by_role_id UUID REFERENCES roles(id),
    updated_by_role_id UUID REFERENCES roles(id),
    deleted_by_role_id UUID REFERENCES roles(id)
);


CREATE TRIGGER trigger_users_audit
BEFORE INSERT OR UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_audit_role_id();


-- ============================================================================
-- AUDIT LOGS
-- ============================================================================
CREATE TYPE audit_action AS ENUM ('INSERT', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT');


CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    action audit_action NOT NULL,
    table_name VARCHAR(100) NOT NULL,
    record_id UUID,
    old_value TEXT,
    new_value TEXT,
    user_id UUID,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);


-- ============================================================================
-- MEDICAL DOMAIN TABLES
-- ============================================================================

CREATE TABLE specialties (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE doctors (
    id SERIAL PRIMARY KEY,
    specialty_id INT NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    document_number VARCHAR(50) NOT NULL UNIQUE,
    professional_license VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_doctors_specialty FOREIGN KEY (specialty_id)
        REFERENCES specialties (id) ON DELETE RESTRICT
);


CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    document_number VARCHAR(50) NOT NULL UNIQUE,
    birth_date DATE NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE appointment_statuses (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    description VARCHAR(100)
);


CREATE TABLE appointments (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    status_id INT NOT NULL,
    start_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    end_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    reason TEXT NOT NULL,
    user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_appointments_patient FOREIGN KEY (patient_id)
        REFERENCES patients (id) ON DELETE RESTRICT,
    CONSTRAINT fk_appointments_doctor FOREIGN KEY (doctor_id)
        REFERENCES doctors (id) ON DELETE RESTRICT,
    CONSTRAINT fk_appointments_status FOREIGN KEY (status_id)
        REFERENCES appointment_statuses (id) ON DELETE RESTRICT,
    CONSTRAINT fk_appointments_user FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE SET NULL
);


CREATE TABLE medical_notes (
    id SERIAL PRIMARY KEY,
    appointment_id INT NOT NULL UNIQUE,
    diagnosis TEXT NOT NULL,
    treatment TEXT,
    observations TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notes_appointment FOREIGN KEY (appointment_id)
        REFERENCES appointments (id) ON DELETE CASCADE
);


-- ============================================================================
-- VECTOR TABLES (RAG)
-- ============================================================================
CREATE TABLE vector_documents (
    id SERIAL PRIMARY KEY,
    reference_type VARCHAR(50) NOT NULL,
    reference_id INT,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================================
-- BOOTSTRAP DATA (mínimo para que la API arranque y cree el superusuario)
-- ============================================================================
INSERT INTO roles (id, name, created_by_user_id)
VALUES ('00000000-0000-0000-0000-000000000001', 'SYSTEM_ROLE', NULL);


INSERT INTO users (id, email, password, full_name, address, phone, phone2, is_active, role_id, created_by_user_id)
VALUES (
    'ffffffff-ffff-ffff-ffff-ffffffffffff',
    'system@script.com',
    'n/a',
    'SYSTEM_INIT',
    'System Address',
    '0000000000',
    '0000000000',
    TRUE,
    '00000000-0000-0000-0000-000000000001',
    NULL
);


UPDATE users SET created_by_user_id = 'ffffffff-ffff-ffff-ffff-ffffffffffff' WHERE id = 'ffffffff-ffff-ffff-ffff-ffffffffffff';
UPDATE roles SET created_by_user_id = 'ffffffff-ffff-ffff-ffff-ffffffffffff' WHERE id = '00000000-0000-0000-0000-000000000001';


INSERT INTO roles (id, name, created_by_user_id)
VALUES ('00000000-0000-0000-0000-000000000002', 'SUPER_ADMIN', 'ffffffff-ffff-ffff-ffff-ffffffffffff');


-- Los catálogos (estados de cita, especialidades) y los datos de ejemplo NO se
-- cargan aquí: la BD queda con las tablas vacías. Se cargan solo cuando se
-- piden, con:  make up-test   (levanta + datos)   o   make seed   (solo datos)


-- ============================================================================
-- PERFORMANCE INDEXES
-- ============================================================================
CREATE INDEX idx_vector_documents_embedding
ON vector_documents
USING hnsw (embedding vector_cosine_ops);


CREATE INDEX idx_appointments_patient ON appointments(patient_id);
CREATE INDEX idx_appointments_doctor ON appointments(doctor_id);
CREATE INDEX idx_appointments_start ON appointments(start_datetime);
CREATE INDEX idx_doctors_specialty ON doctors(specialty_id);


-- ============================================================================
-- ADDITIONAL TABLES (WAITLIST, BRANCHES)
-- ============================================================================
CREATE TABLE waitlist (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    preferred_date DATE NOT NULL,
    reason TEXT,
    status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notified_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_waitlist_patient FOREIGN KEY (patient_id)
        REFERENCES patients (id) ON DELETE CASCADE,
    CONSTRAINT fk_waitlist_doctor FOREIGN KEY (doctor_id)
        REFERENCES doctors (id) ON DELETE CASCADE
);


CREATE INDEX idx_waitlist_doctor ON waitlist(doctor_id);
CREATE INDEX idx_waitlist_status ON waitlist(status);


CREATE TABLE branches (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    address TEXT,
    phone VARCHAR(20),
    email VARCHAR(150),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE
);


ALTER TABLE doctors ADD COLUMN branch_id INT;
ALTER TABLE doctors ADD CONSTRAINT fk_doctors_branch
    FOREIGN KEY (branch_id) REFERENCES branches (id) ON DELETE SET NULL;


CREATE INDEX idx_doctors_branch ON doctors(branch_id);


-- ============================================================================
-- VISUAL INDICATOR CONFIG
-- (requerida por el API para enriquecer las citas con indicadores visuales)
-- ============================================================================
CREATE TABLE visual_indicator_config (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    label VARCHAR(100) NOT NULL,
    hex_color VARCHAR(7) NOT NULL DEFAULT '#6B7280',
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

INSERT INTO visual_indicator_config (code, label, hex_color, sort_order, is_active) VALUES
    ('delayed',          'Demorada',    '#EF4444', 0,  TRUE),
    ('proximity_rank_1', 'Próxima 1',   '#10B981', 1,  TRUE),
    ('proximity_rank_2', 'Próxima 2',   '#3B82F6', 2,  TRUE),
    ('proximity_rank_3', 'Próxima 3',   '#F59E0B', 3,  TRUE),
    ('confirmed',        'Confirmada',  '#3B82F6', 5,  TRUE),
    ('pending',          'Pendiente',   '#6B7280', 10, TRUE),
    ('rescheduled',      'Reagendada',  '#F59E0B', 15, TRUE),
    ('completed',        'Completada',  '#10B981', 20, TRUE),
    ('cancelled',        'Cancelada',   '#EF4444', 30, TRUE);


-- ============================================================================
-- CONSULTING ROOMS, DOCTOR SCHEDULES, MEDICAL HISTORIES
-- (requeridas por los endpoints /consulting-rooms, /doctor-schedules
--  y /medical-histories; el initdb anterior no las incluía y rompía los tests)
-- ============================================================================
CREATE TABLE consulting_rooms (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    address VARCHAR(200),
    phone_number VARCHAR(15),
    user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_consulting_rooms_user FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE SET NULL
);


CREATE TABLE doctor_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doctor_id INT NOT NULL,
    user_id UUID,
    day_of_week INT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    slot_duration_minutes INT NOT NULL DEFAULT 30,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_doctor_schedules_doctor FOREIGN KEY (doctor_id)
        REFERENCES doctors (id) ON DELETE CASCADE
);


CREATE TABLE medical_histories (
    id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    consulting_room_id INT,
    diagnosis TEXT,
    prescription TEXT,
    treatment TEXT,
    ai_summary TEXT,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_medical_histories_patient FOREIGN KEY (patient_id)
        REFERENCES patients (id) ON DELETE RESTRICT,
    CONSTRAINT fk_medical_histories_doctor FOREIGN KEY (doctor_id)
        REFERENCES doctors (id) ON DELETE RESTRICT,
    CONSTRAINT fk_medical_histories_room FOREIGN KEY (consulting_room_id)
        REFERENCES consulting_rooms (id) ON DELETE SET NULL
);


CREATE INDEX idx_doctor_schedules_doctor ON doctor_schedules(doctor_id);
CREATE INDEX idx_medical_histories_patient ON medical_histories(patient_id);
CREATE INDEX idx_medical_histories_doctor ON medical_histories(doctor_id);