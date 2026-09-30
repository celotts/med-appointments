#!/usr/bin/env python3
"""
Large dataset seed script for med-appointments.
Generates 8000+ records per table for performance testing.
Run inside the container: python /app/app/seed_large_dataset.py
"""

import asyncio
import uuid
import random
from datetime import date, datetime, time, timedelta
from faker import Faker

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import engine
from app.core.security import get_password_hash
from app.models import (
    Role,
    User,
    Specialty,
    Branch,
    Doctor,
    Patient,
    Appointment,
    AppointmentStatus,
    ConsultingRoom,
    DoctorSchedule,
    Waitlist,
    Notification,
    MedicalHistory,
)

fake = Faker('es_ES')
fake_en = Faker('en_US')

# Configuration
TARGET_COUNTS = {
    'specialties': 20,
    'branches': 10,
    'roles': 5,
    'users': 10000,
    'doctors': 500,
    'patients': 8000,
    'appointment_statuses': 10,
    'consulting_rooms': 50,
    'appointments': 50000,
    'doctor_schedules': 2500,
    'waitlist': 5000,
    'notifications': 20000,
    'medical_histories': 15000,
}

BATCH_SIZE = 500

# Specialty data
SPECIALTIES_DATA = [
    ("Cardiología", "Especialidad médica del corazón y sistema circulatorio"),
    ("Dermatología", "Especialidad de la piel y sus anexos"),
    ("Ginecología", "Salud reproductiva femenina"),
    ("Pediatría", "Medicina infantil y adolescente"),
    ("Traumatología", "Lesiones del sistema musculoesquelético"),
    ("Neurología", "Trastornos del sistema nervioso"),
    ("Oftalmología", "Salud ocular y visual"),
    ("Psiquiatría", "Salud mental y trastornos psiquiátricos"),
    ("Urología", "Sistema urinario y reproductor masculino"),
    ("Endocrinología", "Trastornos hormonales y metabólicos"),
    ("Gastroenterología", "Sistema digestivo"),
    ("Neumología", "Sistema respiratorio"),
    ("Reumatología", "Enfermedades autoinmunes y articulares"),
    ("Oncología", "Cáncer y tumores"),
    ("Hematología", "Trastornos de la sangre"),
    ("Nefrología", "Enfermedades renales"),
    ("Infectología", "Enfermedades infecciosas"),
    ("Geriatría", "Medicina del adulto mayor"),
    ("Medicina Interna", "Diagnóstico y tratamiento no quirúrgico"),
    ("Cirugía General", "Procedimientos quirúrgicos abdominales"),
]

BRANCHES_DATA = [
    ("Clínica Central", "Av. Principal 123, Centro", "555-0101", "central@clinica.com"),
    ("Clínica Norte", "Av. Norte 456, Zona Norte", "555-0202", "norte@clinica.com"),
    ("Clínica Sur", "Av. Sur 789, Zona Sur", "555-0303", "sur@clinica.com"),
    ("Clínica Este", "Av. Este 321, Zona Este", "555-0404", "este@clinica.com"),
    ("Clínica Oeste", "Av. Oeste 654, Zona Oeste", "555-0505", "oeste@clinica.com"),
    ("Hospital General", "Calle Hospital 100, Centro", "555-0606", "general@hospital.com"),
    ("Centro Médico Norte", "Blvd. Norte 200", "555-0707", "centronorte@medico.com"),
    ("Clínica Pediátrica", "Av. Niños 50", "555-0808", "pediatrica@clinica.com"),
    ("Instituto Cardiovascular", "Calle Corazón 1", "555-0909", "cardio@instituto.com"),
    ("Centro de Especialidades", "Av. Especialistas 99", "555-1010", "especialidades@centro.com"),
]

ROLES_DATA = [
    ("SUPER_ADMIN", "Super Administrador"),
    ("ADMIN", "Administrador"),
    ("DOCTOR", "Médico"),
    ("PATIENT", "Paciente"),
    ("ASSISTANT", "Asistente"),
]

# Estados de cita: VOCABULARIO CANONICO.
# Debe coincidir exactamente con el enum AppointmentStatusCode de
# app/schemas/appointment.py. No agregar codigos en ingles ni en otro idioma:
# el enum no los reconoce y cualquier transicion sobre esas citas revienta.
APPOINTMENT_STATUSES = [
    ("PENDIENTE", "Cita pendiente de confirmacion"),
    ("CONFIRMADA", "Cita confirmada"),
    ("EN ESPERA", "Cita en sala de espera"),
    ("EN PROCESO", "Consulta en curso"),
    ("ATENDIDA", "Cita atendida"),
    ("CANCELADA", "Cita cancelada"),
    ("SUSPENDIDA", "Cita suspendida"),
    ("REAGENDADA", "Cita reagendada a nueva fecha"),
]

# Estados que representan una cita aun viva (ocupan agenda).
ESTADOS_ACTIVOS = ["PENDIENTE", "CONFIRMADA", "EN ESPERA", "EN PROCESO", "REAGENDADA"]

# Estados en los que una cita ya no puede volver a un estado activo.
ESTADOS_CERRADOS = ["ATENDIDA", "CANCELADA"]

async def count_records(db, model) -> int:
    r = await db.execute(select(func.count()).select_from(model))
    return r.scalar_one()

async def ensure_roles(db) -> dict:
    existing = {name: rid for name, rid in (await db.execute(select(Role.name, Role.id))).all()}
    for name, desc in ROLES_DATA:
        if name not in existing:
            role = Role(name=name)
            db.add(role)
            await db.flush()
            existing[name] = role.id
    return existing

async def ensure_specialties(db) -> list:
    existing = {name: s for name, s in (await db.execute(select(Specialty.name, Specialty))).all()}
    for name, desc in SPECIALTIES_DATA:
        if name not in existing:
            s = Specialty(name=name, description=desc)
            db.add(s)
            await db.flush()
            existing[name] = s
    return list(existing.values())

async def ensure_branches(db) -> list:
    existing = {name: b for name, b in (await db.execute(select(Branch.name, Branch))).all()}
    for name, addr, phone, email in BRANCHES_DATA:
        if name not in existing:
            b = Branch(name=name, address=addr, phone=phone, email=email)
            db.add(b)
            await db.flush()
            existing[name] = b
    return list(existing.values())

async def ensure_appointment_statuses(db) -> dict:
    existing = {code: s for code, s in (await db.execute(select(AppointmentStatus.code, AppointmentStatus))).all()}
    for code, desc in APPOINTMENT_STATUSES:
        if code not in existing:
            s = AppointmentStatus(code=code, description=desc)
            db.add(s)
            await db.flush()
            existing[code] = s
    return existing

async def ensure_admin_user(db, roles_map) -> User:
    r = await db.execute(select(User).where(User.email == "admin@clinica.com"))
    admin = r.scalars().first()
    if admin is None:
        admin = User(
            id=uuid.uuid4(),
            email="admin@clinica.com",
            full_name="Administrador Clínica",
            password=get_password_hash("admin123"),
            role_id=roles_map.get("SUPER_ADMIN") or roles_map.get("ADMIN") or next(iter(roles_map.values())),
            is_active=True,
            is_specialist=False,
        )
        db.add(admin)
        await db.flush()
        print("admin: created")
    return admin

async def seed_users_and_doctors_patients(db, roles_map, specialties, branches, admin_id, target_users=10000):
    current_users = await count_records(db, User)
    current_doctors = await count_records(db, Doctor)
    current_patients = await count_records(db, Patient)
    
    print(f"Current: users={current_users}, doctors={current_doctors}, patients={current_patients}")
    
    # Get existing user emails to avoid duplicates
    existing_emails = set((await db.execute(select(User.email))).scalars().all())
    
    # Calculate how many more we need
    users_needed = max(0, target_users - current_users)
    doctors_needed = max(0, 500 - current_doctors)
    patients_needed = max(0, 8000 - current_patients)
    
    print(f"Need to create: users={users_needed}, doctors={doctors_needed}, patients={patients_needed}")
    
    # Create users in batches
    doctor_role_id = roles_map.get("DOCTOR")
    patient_role_id = roles_map.get("PATIENT")
    assistant_role_id = roles_map.get("ASSISTANT")
    
    doctor_emails = []
    patient_data_list = []
    
    for batch_start in range(0, users_needed, BATCH_SIZE):
        batch_size = min(BATCH_SIZE, users_needed - batch_start)
        users_batch = []
        
        for i in range(batch_size):
            idx = batch_start + i + current_users
            is_doctor = len(doctor_emails) < doctors_needed and random.random() < 0.1
            is_patient = len(patient_data_list) < patients_needed and (not is_doctor or random.random() < 0.9)
            
            if is_doctor:
                role_id = doctor_role_id
                email = f"doctor{idx}@clinica.com"
                full_name = f"Dr. {fake.name()}"
                is_specialist = True
            elif is_patient:
                role_id = patient_role_id
                email = f"paciente{idx}@email.com"
                full_name = fake.name()
                is_specialist = False
            else:
                role_id = assistant_role_id
                email = f"asistente{idx}@clinica.com"
                full_name = fake.name()
                is_specialist = False
            
            if email in existing_emails:
                continue
            existing_emails.add(email)
            
            user = User(
                id=uuid.uuid4(),
                email=email,
                full_name=full_name,
                password=get_password_hash("password123"),
                role_id=role_id,
                is_active=True,
                is_specialist=is_specialist,
            )
            users_batch.append(user)
            
            if is_doctor:
                spec = random.choice(specialties)
                branch = random.choice(branches)
                doctor_emails.append((email, full_name, spec.id, branch.id))
            elif is_patient:
                doc_num = f"{random.randint(10000000, 99999999)}"
                birth = fake.date_of_birth(minimum_age=18, maximum_age=90)
                phone = fake.phone_number()[:20]
                patient_data_list.append((email, full_name, doc_num, birth, phone))
        
        if users_batch:
            db.add_all(users_batch)
            await db.flush()
            print(f"  Created {len(users_batch)} users (batch {batch_start//BATCH_SIZE + 1})")
    
    await db.commit()
    
    # Create Doctors
    if doctor_emails:
        doctor_objects = []
        for i, (email, full_name, spec_id, branch_id) in enumerate(doctor_emails):
            first_names = full_name.split()
            first_name = first_names[1] if len(first_names) > 1 else full_name
            last_name = first_names[-1]
            
            d = Doctor(
                specialty_id=spec_id,
                branch_id=branch_id,
                first_name=first_name,
                last_name=last_name,
                document_number=f"DOC{100000 + i}",
                professional_license=f"LIC{100000 + i}",
                email=email,
                phone=f"555-{random.randint(2000, 9999)}",
            )
            doctor_objects.append(d)
        
        db.add_all(doctor_objects)
        await db.commit()
        print(f"Created {len(doctor_objects)} doctors")
    
    # Create Patients
    if patient_data_list:
        patient_objects = []
        for i, (email, full_name, doc_num, birth, phone) in enumerate(patient_data_list):
            first_names = full_name.split()
            first_name = first_names[0]
            last_name = " ".join(first_names[1:]) if len(first_names) > 1 else ""
            
            p = Patient(
                first_name=first_name,
                last_name=last_name,
                document_number=doc_num,
                birth_date=birth,
                email=email,
                phone=phone,
            )
            patient_objects.append(p)
        
        # Batch insert patients
        for i in range(0, len(patient_objects), BATCH_SIZE):
            batch = patient_objects[i:i+BATCH_SIZE]
            db.add_all(batch)
            await db.flush()
        
        await db.commit()
        print(f"Created {len(patient_objects)} patients")

async def seed_consulting_rooms(db, admin_id):
    current = await count_records(db, ConsultingRoom)
    needed = max(0, 50 - current)
    
    if needed > 0:
        existing_names = set((await db.execute(select(ConsultingRoom.name))).scalars().all())
        rooms = []
        
        for i in range(needed):
            floor = (i // 5) + 1
            wing = chr(ord('A') + (i % 5))
            room_num = 100 + i
            name = f"Consultorio {room_num}"
            
            if name in existing_names:
                continue
            existing_names.add(name)
            
            rooms.append(ConsultingRoom(
                name=name,
                address=f"Piso {floor}, Ala {wing}",
                phone_number=f"555-{random.randint(1000, 9999)}",
                user_id=admin_id,
            ))
        
        if rooms:
            db.add_all(rooms)
            await db.commit()
            print(f"Created {len(rooms)} consulting rooms")

async def seed_doctor_schedules(db):
    current = await count_records(db, DoctorSchedule)
    needed = max(0, 2500 - current)
    
    if needed > 0:
        existing = {(d, w) for d, w in (await db.execute(select(DoctorSchedule.doctor_id, DoctorSchedule.day_of_week))).all()}
        doctor_ids = (await db.execute(select(Doctor.id))).scalars().all()
        
        # Get admin user ID for user_id field
        admin_user = (await db.execute(select(User).where(User.email == "admin@clinica.com"))).scalars().first()
        admin_user_id = admin_user.id if admin_user else None
        
        schedules = []
        for doc_id in doctor_ids:
            for day in range(1, 6):  # Mon-Fri
                if (doc_id, day) in existing:
                    continue
                existing.add((doc_id, day))
                schedules.append(DoctorSchedule(
                    doctor_id=doc_id,
                    user_id=admin_user_id,
                    day_of_week=day,
                    start_time=time(8, 0) if random.random() < 0.5 else time(9, 0),
                    end_time=time(14, 0) if random.random() < 0.5 else time(16, 0),
                    slot_duration_minutes=random.choice([15, 20, 30, 45]),
                ))
                if len(schedules) >= needed:
                    break
            if len(schedules) >= needed:
                break
        
        if schedules:
            db.add_all(schedules)
            await db.commit()
            print(f"Created {len(schedules)} doctor schedules")

async def seed_waitlist(db):
    current = await count_records(db, Waitlist)
    needed = max(0, 5000 - current)
    
    if needed > 0:
        patients = (await db.execute(select(Patient.id))).scalars().all()
        doctors = (await db.execute(select(Doctor.id))).scalars().all()
        
        if not patients or not doctors:
            print("waitlist: skipped (no patients/doctors)")
            return
        
        waitlist_items = []
        for i in range(needed):
            waitlist_items.append(Waitlist(
                patient_id=random.choice(patients),
                doctor_id=random.choice(doctors),
                preferred_date=date.today() + timedelta(days=random.randint(1, 60)),
                reason=fake.sentence(nb_words=6)[:100],
                status=random.choice(["PENDING", "CONTACTED", "SCHEDULED", "CANCELLED"]),
            ))
        
        # Batch insert
        for i in range(0, len(waitlist_items), BATCH_SIZE):
            batch = waitlist_items[i:i+BATCH_SIZE]
            db.add_all(batch)
            await db.flush()
        
        await db.commit()
        print(f"Created {len(waitlist_items)} waitlist entries")

async def seed_notifications(db):
    current = await count_records(db, Notification)
    needed = max(0, 20000 - current)
    
    if needed > 0:
        patients = (await db.execute(select(Patient.id))).scalars().all()
        
        if not patients:
            print("notifications: skipped (no patients)")
            return
        
        notif_types = ["APPOINTMENT_REMINDER", "APPOINTMENT_CONFIRMED", "APPOINTMENT_CANCELLED", 
                       "PRESCRIPTION_READY", "LAB_RESULTS", "FOLLOW_UP", "BILLING", "GENERAL"]
        
        notifications = []
        for i in range(needed):
            notifications.append(Notification(
                patient_id=random.choice(patients),
                type=random.choice(notif_types),
                title=fake.sentence(nb_words=4)[:50],
                message=fake.paragraph(nb_sentences=2)[:200],
                is_read=random.random() < 0.3,
                created_at=fake.date_time_between(start_date='-30d', end_date='now'),
            ))
        
        # Batch insert
        for i in range(0, len(notifications), BATCH_SIZE):
            batch = notifications[i:i+BATCH_SIZE]
            db.add_all(batch)
            await db.flush()
        
        await db.commit()
        print(f"Created {len(notifications)} notifications")

async def seed_medical_histories(db):
    current = await count_records(db, MedicalHistory)
    needed = max(0, 15000 - current)
    
    if needed > 0:
        patients = (await db.execute(select(Patient.id))).scalars().all()
        doctors = (await db.execute(select(Doctor.id))).scalars().all()
        rooms = (await db.execute(select(ConsultingRoom.id))).scalars().all()
        
        if not patients or not doctors:
            print("medical_histories: skipped (no patients/doctors)")
            return
        
        diagnoses = [
            "Hipertensión arterial", "Diabetes mellitus tipo 2", "Dislipidemia", "Obesidad",
            "Asma bronquial", "EPOC", "Hipotiroidismo", "Artrosis", "Lumbalgia", "Cefalea tensional",
            "Gastritis", "Reflujo gastroesofágico", "Ansiedad", "Depresión", "Insomnio",
            "Arritmia cardíaca", "Insuficiencia cardíaca", "Enfermedad renal crónica", "Anemia",
            "Infección urinaria", "Sinusitis", "Faringitis", "Bronquitis", "Neumonía"
        ]
        
        prescriptions = [
            "Losartan 50mg c/24h", "Metformina 850mg c/12h", "Atorvastatina 20mg nocturna",
            "Levotiroxina 100mcg en ayunas", "Salbutamol inhalador c/6h PRN", "Omeprazol 20mg c/24h",
            "Ibuprofeno 600mg c/8h", "Paracetamol 1g c/6h", "Amlodipino 5mg c/24h",
            "Sertralina 50mg c/24h", "Clonazepam 0.5mg nocturna", "Vitamina D 2000 UI diaria"
        ]
        
        histories = []
        for i in range(needed):
            hist_date = fake.date_between(start_date='-2y', end_date='today')
            histories.append(MedicalHistory(
                patient_id=random.choice(patients),
                doctor_id=random.choice(doctors),
                consulting_room_id=random.choice(rooms) if rooms else None,
                diagnosis=random.choice(diagnoses),
                prescription=random.choice(prescriptions),
                treatment=fake.sentence(nb_words=8)[:100],
                ai_summary=fake.paragraph(nb_sentences=3)[:300],
                date=hist_date,
            ))
        
        # Batch insert
        for i in range(0, len(histories), BATCH_SIZE):
            batch = histories[i:i+BATCH_SIZE]
            db.add_all(batch)
            await db.flush()
        
        await db.commit()
        print(f"Created {len(histories)} medical histories")

async def seed_appointments(db):
    current = await count_records(db, Appointment)
    needed = max(0, 50000 - current)
    
    if needed > 0:
        # Solo estados canonicos: nunca tomar TODOS los que haya en la BD,
        # porque una base sembrada con datos viejos puede tener codigos que
        # el enum no reconoce y las citas born invalidas.
        status_map = {
            code: ident
            for code, ident in (
                await db.execute(
                    select(AppointmentStatus.code, AppointmentStatus.id).where(
                        AppointmentStatus.code.in_([c for c, _ in APPOINTMENT_STATUSES])
                    )
                )
            ).all()
        }
        doctors = (await db.execute(select(Doctor.id))).scalars().all()
        patients = (await db.execute(select(Patient.id))).scalars().all()
        
        if not doctors or not patients or not status_map:
            print("appointments: skipped (missing dependencies)")
            return
        
        status_codes = list(status_map.keys())
        admin_user = (await db.execute(select(User).where(User.email == "admin@clinica.com"))).scalars().first()
        admin_id = admin_user.id if admin_user else doctors[0]
        
        reasons = [
            "Consulta de rutina", "Control de presión arterial", "Revisión de laboratorio",
            "Control de diabetes", "Chequeo anual", "Síntomas gripales", "Dolor abdominal",
            "Dolor de cabeza", "Control post-operatorio", "Seguimiento de tratamiento",
            "Renovación de receta", "Vacunación", "Evaluación pre-operatoria",
            "Consulta por ansiedad", "Control de peso", "Revisión dermatológica",
            "Control cardiológico", "Consulta ginecológica", "Control pediátrico",
            "Evaluación traumatológica", "Consulta neurológica", "Examen oftalmológico",
            "Evaluación psiquiátrica", "Consulta urológica", "Control endocrinológico"
        ]
        
        # Generate appointments over 180 days (past and future)
        base_date = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        
        appointments = []
        for i in range(needed):
            doctor_id = random.choice(doctors)
            patient_id = random.choice(patients)
            status_code = random.choice(status_codes)
            
            # Distribute: 30% past, 20% today, 50% future
            if random.random() < 0.3:
                days_offset = random.randint(-180, -1)
            elif random.random() < 0.5:
                days_offset = 0
            else:
                days_offset = random.randint(1, 90)
            
            hour = random.randint(8, 18)
            minute = random.choice([0, 15, 30, 45])
            start_dt = base_date + timedelta(days=days_offset, hours=hour-8, minutes=minute)
            end_dt = start_dt + timedelta(minutes=random.choice([15, 20, 30, 45, 60]))
            
            # Una cita en el pasado no puede seguir activa: cerrarla.
            if start_dt < datetime.now() and status_code in ESTADOS_ACTIVOS:
                status_code = random.choice(ESTADOS_CERRADOS)
            
            appt = Appointment(
                patient_id=patient_id,
                doctor_id=doctor_id,
                user_id=admin_id,
                status_id=status_map[status_code],
                start_datetime=start_dt,
                end_datetime=end_dt,
                reason=f"{random.choice(reasons)} - {fake.sentence(nb_words=4)[:50]}",
            )
            appointments.append(appt)
        
        # Batch insert
        for i in range(0, len(appointments), BATCH_SIZE):
            batch = appointments[i:i+BATCH_SIZE]
            db.add_all(batch)
            await db.flush()
            if i % 5000 == 0:
                print(f"  Appointments progress: {i}/{len(appointments)}")
        
        await db.commit()
        print(f"Created {len(appointments)} appointments")

async def main():
    print("=" * 60)
    print("LARGE DATASET SEED FOR MED-APPOINTMENTS")
    print("=" * 60)
    print(f"Target counts: {TARGET_COUNTS}")
    print()
    
    async with AsyncSession(engine, expire_on_commit=False) as db:
        # Check current state
        print("Current database state:")
        for model_name, model in [
            ('roles', Role), ('users', User), ('specialties', Specialty),
            ('branches', Branch), ('doctors', Doctor), ('patients', Patient),
            ('appointment_statuses', AppointmentStatus), ('appointments', Appointment),
            ('consulting_rooms', ConsultingRoom), ('doctor_schedules', DoctorSchedule),
            ('waitlist', Waitlist), ('notifications', Notification),
            ('medical_histories', MedicalHistory),
        ]:
            cnt = await count_records(db, model)
            target = TARGET_COUNTS.get(model_name, 0)
            print(f"  {model_name}: {cnt} / {target} ({cnt/target*100:.1f}%)" if target else f"  {model_name}: {cnt}")
        print()
        
        # Ensure base data
        print("Ensuring base reference data...")
        roles_map = await ensure_roles(db)
        specialties = await ensure_specialties(db)
        branches = await ensure_branches(db)
        status_map = await ensure_appointment_statuses(db)
        admin = await ensure_admin_user(db, roles_map)
        await db.commit()
        print("  Base data ready\n")
        
        # Seed main entities
        print("Seeding users, doctors, patients...")
        await seed_users_and_doctors_patients(db, roles_map, specialties, branches, admin.id)
        
        print("\nSeeding consulting rooms...")
        await seed_consulting_rooms(db, admin.id)
        
        print("\nSeeding doctor schedules...")
        await seed_doctor_schedules(db)
        
        print("\nSeeding waitlist...")
        await seed_waitlist(db)
        
        print("\nSeeding notifications...")
        await seed_notifications(db)
        
        print("\nSeeding medical histories...")
        await seed_medical_histories(db)
        
        print("\nSeeding appointments (this may take a moment)...")
        await seed_appointments(db)
        
        # Final summary
        print("\n" + "=" * 60)
        print("FINAL SUMMARY")
        print("=" * 60)
        for model_name, model in [
            ('roles', Role), ('users', User), ('specialties', Specialty),
            ('branches', Branch), ('doctors', Doctor), ('patients', Patient),
            ('appointment_statuses', AppointmentStatus), ('appointments', Appointment),
            ('consulting_rooms', ConsultingRoom), ('doctor_schedules', DoctorSchedule),
            ('waitlist', Waitlist), ('notifications', Notification),
            ('medical_histories', MedicalHistory),
        ]:
            cnt = await count_records(db, model)
            target = TARGET_COUNTS.get(model_name, 0)
            pct = f"({cnt/target*100:.1f}%)" if target else ""
            print(f"  {model_name}: {cnt:,} {pct}")
        
        print("\n✅ Large dataset seed completed!")

if __name__ == "__main__":
    asyncio.run(main())