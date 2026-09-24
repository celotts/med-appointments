#!/usr/bin/env python3
"""Seed script to populate medical appointment database with test data."""

import asyncio

# Use the app's database setup
import sys
import uuid
from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, "/app/backend")

from app.core.db import engine
from app.core.security import get_password_hash
from app.models.appointment import Appointment as AppointmentModel
from app.models.appointment_status import AppointmentStatus as AppointmentStatusModel
from app.models.branch import Branch as BranchModel
from app.models.consulting_room import ConsultingRoom as ConsultingRoomModel
from app.models.doctor import Doctor as DoctorModel
from app.models.patient import Patient as PatientModel
from app.models.role import Role as RoleModel
from app.models.specialty import Specialty as SpecialtyModel
from app.models.user import User as UserModel


async def seed_data():
    async with AsyncSession(engine) as db:
        # Check if data already exists
        from sqlalchemy import select

        r = await db.execute(select(SpecialtyModel))
        if r.scalars().first():
            print("Database already has medical data, skipping seed.")
            return

        print("Seeding medical data...")

        # 1. Appointment Statuses
        statuses = [
            AppointmentStatusModel(code="SCHEDULED", description="Programada"),
            AppointmentStatusModel(code="CONFIRMED", description="Confirmada"),
            AppointmentStatusModel(code="IN_PROGRESS", description="En curso"),
            AppointmentStatusModel(code="COMPLETED", description="Completada"),
            AppointmentStatusModel(code="CANCELLED", description="Cancelada"),
            AppointmentStatusModel(code="NO_SHOW", description="No se presentó"),
        ]
        for s in statuses:
            db.add(s)
        await db.commit()
        print(f"Created {len(statuses)} appointment statuses")

        # 2. Specialties
        specialties = [
            SpecialtyModel(
                name="Cardiología",
                description="Especialidad médica del corazón y sistema circulatorio",
            ),
            SpecialtyModel(
                name="Dermatología", description="Especialidad de la piel y sus anexos"
            ),
            SpecialtyModel(
                name="Ginecología", description="Salud reproductiva femenina"
            ),
            SpecialtyModel(
                name="Pediatría", description="Medicina infantil y adolescente"
            ),
            SpecialtyModel(
                name="Traumatología",
                description="Lesiones del sistema musculoesquelético",
            ),
            SpecialtyModel(
                name="Neurología", description="Trastornos del sistema nervioso"
            ),
            SpecialtyModel(name="Oftalmología", description="Salud ocular y visual"),
            SpecialtyModel(
                name="Psiquiatría",
                description="Salud mental y trastornos psiquiátricos",
            ),
        ]
        for s in specialties:
            db.add(s)
        await db.commit()
        print(f"Created {len(specialties)} specialties")

        # 3. Branches
        branches = [
            BranchModel(
                name="Clínica Central",
                address="Av. Principal 123, Centro",
                phone="555-0101",
                email="central@clinica.com",
            ),
            BranchModel(
                name="Clínica Norte",
                address="Av. Norte 456, Zona Norte",
                phone="555-0202",
                email="norte@clinica.com",
            ),
            BranchModel(
                name="Clínica Sur",
                address="Av. Sur 789, Zona Sur",
                phone="555-0303",
                email="sur@clinica.com",
            ),
        ]
        for b in branches:
            db.add(b)
        await db.commit()
        print(f"Created {len(branches)} branches")

        # 4. Appointment Statuses IDs for reference
        status_map = {}
        r = await db.execute(select(AppointmentStatusModel))
        for s in r.scalars().all():
            status_map[s.code] = s.id

        # 5. Roles (already exist, get them)
        r = await db.execute(select(RoleModel))
        roles = {r.name: r for r in r.scalars().all()}

        # 5. Users (Doctors + Admin + Patients)
        # Get admin user (first superuser)
        from sqlalchemy import select

        r = await db.execute(
            select(UserModel).where(UserModel.email == "admin@clinica.com")
        )
        admin_user = r.scalars().first()

        if not admin_user:
            admin_user = UserModel(
                id=uuid.uuid4(),
                email="admin@clinica.com",
                full_name="Administrador Clínica",
                password=get_password_hash("admin123"),
                role_id=roles["admin"].id
                if "admin" in roles
                else list(roles.values())[0].id,
                is_active=True,
                is_specialist=False,
            )
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)

        # Create doctor users
        doctor_users = []
        doctor_data = [
            {
                "email": "cardio@clinica.com",
                "full_name": "Dr. Carlos Mendoza",
                "specialty_idx": 0,
                "branch_idx": 0,
            },
            {
                "email": "derma@clinica.com",
                "full_name": "Dra. Ana Torres",
                "specialty_idx": 1,
                "branch_idx": 1,
            },
            {
                "email": "gine@clinica.com",
                "full_name": "Dr. Roberto Silva",
                "specialty_idx": 2,
                "branch_idx": 0,
            },
            {
                "email": "pedia@clinica.com",
                "full_name": "Dra. Laura Gómez",
                "specialty_idx": 3,
                "branch_idx": 2,
            },
            {
                "email": "trauma@clinica.com",
                "full_name": "Dr. Miguel Ruiz",
                "specialty_idx": 4,
                "branch_idx": 1,
            },
            {
                "email": "neuro@clinica.com",
                "full_name": "Dra. Patricia Vega",
                "specialty_idx": 5,
                "branch_idx": 2,
            },
            {
                "email": "oftal@clinica.com",
                "full_name": "Dr. Fernando Cruz",
                "specialty_idx": 6,
                "branch_idx": 0,
            },
            {
                "email": "psiqu@clinica.com",
                "full_name": "Dra. Elena Ramos",
                "specialty_idx": 7,
                "branch_idx": 1,
            },
        ]

        r = await db.execute(select(SpecialtyModel))
        specialties_list = r.scalars().all()
        r = await db.execute(select(BranchModel))
        branches_list = r.scalars().all()

        for i, dd in enumerate(doctor_data):
            r = await db.execute(
                select(UserModel).where(UserModel.email == dd["email"])
            )
            u = r.scalars().first()
            if not u:
                u = UserModel(
                    id=uuid.uuid4(),
                    email=dd["email"],
                    full_name=dd["full_name"],
                    password=get_password_hash("doctor123"),
                    role_id=roles["doctor"].id
                    if "doctor" in roles
                    else list(roles.values())[1].id,
                    is_active=True,
                    is_specialist=True,
                )
                db.add(u)
                await db.flush()
            doctor_users.append((u, dd["specialty_idx"], dd["branch_idx"]))

        # Create patient users
        patient_users = []
        patient_data = [
            {
                "email": "paciente1@email.com",
                "full_name": "María González",
                "doc": "12345678",
                "birth": date(1990, 5, 15),
                "phone": "555-1001",
            },
            {
                "email": "paciente2@email.com",
                "full_name": "Juan Pérez",
                "doc": "87654321",
                "birth": date(1985, 8, 22),
                "phone": "555-1002",
            },
            {
                "email": "paciente3@email.com",
                "full_name": "Ana Martínez",
                "doc": "11223344",
                "birth": date(2000, 3, 10),
                "phone": "555-1003",
            },
            {
                "email": "paciente4@email.com",
                "full_name": "Carlos López",
                "doc": "44332211",
                "birth": date(1975, 11, 30),
                "phone": "555-1004",
            },
            {
                "email": "paciente5@email.com",
                "full_name": "Sofía Rodríguez",
                "doc": "55667788",
                "birth": date(2010, 7, 25),
                "phone": "555-1005",
            },
            {
                "email": "paciente6@email.com",
                "full_name": "Pedro Sánchez",
                "doc": "99887766",
                "birth": date(1988, 1, 18),
                "phone": "555-1006",
            },
            {
                "email": "paciente7@email.com",
                "full_name": "Lucía Fernández",
                "doc": "33445566",
                "birth": date(1995, 9, 3),
                "phone": "555-1007",
            },
            {
                "email": "paciente8@email.com",
                "full_name": "Roberto Díaz",
                "doc": "77889900",
                "birth": date(1982, 4, 12),
                "phone": "555-1008",
            },
        ]

        for pd in patient_data:
            r = await db.execute(
                select(UserModel).where(UserModel.email == pd["email"])
            )
            u = r.scalars().first()
            if not u:
                u = UserModel(
                    id=uuid.uuid4(),
                    email=pd["email"],
                    full_name=pd["full_name"],
                    password=get_password_hash("paciente123"),
                    role_id=roles["patient"].id
                    if "patient" in roles
                    else list(roles.values())[2].id,
                    is_active=True,
                    is_specialist=False,
                )
                db.add(u)
                await db.flush()
            patient_users.append(u)

        await db.commit()
        print(f"Created {len(doctor_users)} doctors, {len(patient_users)} patients")

        # 6. Specialties (already created above)
        r = await db.execute(select(SpecialtyModel))
        specialties_list = r.scalars().all()

        # 7. Doctors
        doctors = []
        for i, (u, spec_idx, branch_idx) in enumerate(doctor_users):
            spec = specialties_list[spec_idx]
            branch = branches_list[branch_idx]
            r = await db.execute(select(DoctorModel).where(DoctorModel.user_id == u.id))
            d = r.scalars().first()
            if not d:
                d = DoctorModel(
                    specialty_id=spec.id,
                    branch_id=branch.id,
                    first_name=u.full_name.split()[1]
                    if len(u.full_name.split()) > 1
                    else u.full_name,
                    last_name=u.full_name.split()[-1],
                    document_number=f"DOC{10000 + i}",
                    professional_license=f"LIC{10000 + i}",
                    email=u.email,
                    phone=f"555-200{i}",
                )
                db.add(d)
                await db.flush()
            doctors.append((d, spec.id, branch.id))

        await db.commit()
        print(f"Created {len(doctors)} doctors")

        # 8. Patients
        patients = []
        for i, u in enumerate(patient_users):
            pd = patient_data[i]
            r = await db.execute(
                select(PatientModel).where(PatientModel.document_number == pd["doc"])
            )
            p = r.scalars().first()
            if not p:
                p = PatientModel(
                    first_name=pd["full_name"].split()[0],
                    last_name=" ".join(pd["full_name"].split()[1:]),
                    document_number=pd["doc"],
                    birth_date=pd["birth"],
                    email=u.email,
                    phone=pd["phone"],
                )
                db.add(p)
                await db.flush()
            patients.append(p)

        await db.commit()
        print(f"Created {len(patients)} patients")

        # 9. Consulting Rooms
        rooms = [
            ConsultingRoomModel(
                name="Consultorio 101",
                address="Piso 1, Ala A",
                phone_number="555-0101",
                user_id=admin_user.id,
            ),
            ConsultingRoomModel(
                name="Consultorio 102",
                address="Piso 1, Ala A",
                phone_number="555-0102",
                user_id=admin_user.id,
            ),
            ConsultingRoomModel(
                name="Consultorio 201",
                address="Piso 2, Ala B",
                phone_number="555-0201",
                user_id=admin_user.id,
            ),
            ConsultingRoomModel(
                name="Consultorio 202",
                address="Piso 2, Ala B",
                phone_number="555-0202",
                user_id=admin_user.id,
            ),
            ConsultingRoomModel(
                name="Consultorio 301",
                address="Piso 3, Ala C",
                phone_number="555-0301",
                user_id=admin_user.id,
            ),
        ]
        for r in rooms:
            db.add(r)
        await db.commit()
        print(f"Created {len(rooms)} consulting rooms")

        # 10. Appointments
        r = await db.execute(select(AppointmentStatusModel))
        status_list = {s.code: s.id for s in r.scalars().all()}

        r = await db.execute(select(DoctorModel))
        doctors_list = r.scalars().all()

        r = await db.execute(select(PatientModel))
        patients_list = r.scalars().all()

        # Create appointments for the next 30 days
        base_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        appointments = []
        for i in range(50):
            doctor = doctors_list[i % len(doctors_list)]
            patient = patients_list[i % len(patients_list)]
            status_code = list(status_map.keys())[i % len(status_map)]

            start_dt = base_date + timedelta(days=i // 3, hours=(i % 3) * 2)
            end_dt = start_dt + timedelta(minutes=30)

            appt = AppointmentModel(
                patient_id=patients_list[i % len(patients_list)].id,
                doctor_id=doctor.id,
                user_id=admin_user.id,
                status_id=status_map[status_code],
                start_datetime=start_dt,
                end_datetime=end_dt,
                reason=f"Consulta de rutina - {doctor.first_name} {doctor.last_name} - {patient.first_name} {patient.last_name}",
            )
            db.add(appt)

        await db.commit()
        print("Created 50 appointments")

        print("\n✅ Seed completed successfully!")
        print("Summary:")
        print("  - 8 appointment statuses")
        print("  - 8 specialties")
        print("  - 3 branches")
        print("  - 8 doctors")
        print("  - 8 patients")
        print("  - 5 consulting rooms")
        print("  - 50 appointments")


if __name__ == "__main__":
    asyncio.run(seed_data())
