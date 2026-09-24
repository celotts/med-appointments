#!/usr/bin/env python3
"""Idempotent seed for the med-appointments database.

Run inside the medical_rag_api container:
  docker exec medical_rag_api python /app/seed.py

All model imports live at module level so SQLAlchemy registers every table on
the single shared Base before any query/insert runs (this fixes both the
UnboundLocalError from in-function imports and the consulting_rooms
NoReferencedTableError for the 'users' FK).
"""

import asyncio
import sys
import uuid
from datetime import date, time, timedelta

sys.path.insert(0, "/app/app")
sys.path.insert(0, "/app")

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import engine
from app.core.security import get_password_hash, verify_password
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


async def count(db, model) -> int:
    r = await db.execute(select(func.count()).select_from(model))
    return r.scalar_one()


async def ensure_admin(db) -> User:
    r = await db.execute(select(User).where(User.email == "admin@clinica.com"))
    admin = r.scalars().first()
    if admin is None:
        roles = {name: rid for name, rid in (await db.execute(select(Role.name, Role.id))).all()}
        admin = User(
            id=uuid.uuid4(),
            email="admin@clinica.com",
            full_name="Administrador Clinica",
            password=get_password_hash("admin123"),
            role_id=roles.get("SUPER_ADMIN") or next(iter(roles.values())),
            is_active=True,
            is_specialist=False,
        )
        db.add(admin)
        await db.flush()
        print("admin: created")
    else:
        if not verify_password("admin123", admin.password):
            admin.password = get_password_hash("admin123")
            await db.flush()
            print("admin: password fixed")
        else:
            print("admin: exists")
    return admin


async def seed_consulting_rooms(db, admin_id) -> None:
    existing = set((await db.execute(select(ConsultingRoom.name))).scalars().all())
    for name, addr, phone in [
        ("Consultorio 101", "Piso 1, Ala A", "555-0101"),
        ("Consultorio 102", "Piso 1, Ala A", "555-0102"),
        ("Consultorio 201", "Piso 2, Ala B", "555-0201"),
        ("Consultorio 202", "Piso 2, Ala B", "555-0202"),
        ("Consultorio 301", "Piso 3, Ala C", "555-0301"),
    ]:
        if name in existing:
            continue
        db.add(ConsultingRoom(name=name, address=addr, phone_number=phone, user_id=admin_id))
    await db.flush()
    print(f"consulting_rooms: {await count(db, ConsultingRoom)}")


async def seed_doctor_schedules(db, admin_id) -> None:
    rows = {(d, w) for d, w in (await db.execute(select(DoctorSchedule.doctor_id, DoctorSchedule.day_of_week))).all()}
    doctor_ids = (await db.execute(select(Doctor.id))).scalars().all()
    for doc_id in doctor_ids:
        for day in range(1, 6):  # Lun-Vie
            if (doc_id, day) in rows:
                continue
            db.add(DoctorSchedule(
                doctor_id=doc_id,
                user_id=admin_id,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(14, 0),
                slot_duration_minutes=30,
            ))
    await db.flush()
    print(f"doctor_schedules: {await count(db, DoctorSchedule)}")


async def seed_waitlist(db) -> None:
    n = await count(db, Waitlist)
    if n:
        print(f"waitlist: {n}")
        return
    patients = (await db.execute(select(Patient.id))).scalars().all()
    doctors = (await db.execute(select(Doctor.id))).scalars().all()
    if not patients or not doctors:
        print("waitlist: skipped (no patients/doctors)")
        return
    for i in range(5):
        db.add(Waitlist(
            patient_id=patients[i % len(patients)],
            doctor_id=doctors[i % len(doctors)],
            preferred_date=date.today() + timedelta(days=i + 1),
            reason=f"Consulta urgente #{i + 1}",
            status="PENDING",
        ))
    await db.flush()
    print(f"waitlist: {await count(db, Waitlist)}")


async def seed_notifications(db) -> None:
    n = await count(db, Notification)
    if n:
        print(f"notifications: {n}")
        return
    patients = (await db.execute(select(Patient.id))).scalars().all()
    if not patients:
        print("notifications: skipped (no patients)")
        return
    for i in range(5):
        db.add(Notification(
            patient_id=patients[i % len(patients)],
            type="APPOINTMENT_REMINDER",
            title="Recordatorio de cita",
            message=f"Tiene una cita manana a las 10:00 AM (recordatorio #{i + 1})",
            is_read=False,
        ))
    await db.flush()
    print(f"notifications: {await count(db, Notification)}")


async def seed_medical_histories(db) -> None:
    n = await count(db, MedicalHistory)
    if n:
        print(f"medical_histories: {n}")
        return
    patients = (await db.execute(select(Patient.id))).scalars().all()
    doctors = (await db.execute(select(Doctor.id))).scalars().all()
    rooms = (await db.execute(select(ConsultingRoom.id))).scalars().all()
    if not patients or not doctors:
        print("medical_histories: skipped (no patients/doctors)")
        return
    for i in range(10):
        db.add(MedicalHistory(
            patient_id=patients[i % len(patients)],
            doctor_id=doctors[i % len(doctors)],
            consulting_room_id=rooms[i % len(rooms)] if rooms else None,
            diagnosis="Hipertension arterial",
            prescription="Losartan 50mg",
            treatment="Control mensual",
            ai_summary=f"Paciente estable (historial #{i + 1})",
            date=date.today() - timedelta(days=i * 30),
        ))
    await db.flush()
    print(f"medical_histories: {await count(db, MedicalHistory)}")


async def main() -> None:
    async with AsyncSession(engine, expire_on_commit=False) as db:
        print(f"roles: {await count(db, Role)}")
        print(f"users: {await count(db, User)}")
        print(f"specialties: {await count(db, Specialty)}")
        print(f"branches: {await count(db, Branch)}")
        print(f"doctors: {await count(db, Doctor)}")
        print(f"patients: {await count(db, Patient)}")
        print(f"appointment_statuses: {await count(db, AppointmentStatus)}")
        print(f"appointments: {await count(db, Appointment)}")

        admin = await ensure_admin(db)
        await seed_consulting_rooms(db, admin.id)
        await seed_doctor_schedules(db, admin.id)
        await seed_waitlist(db)
        await seed_notifications(db)
        await seed_medical_histories(db)

        await db.commit()
        print("ALL DONE")


asyncio.run(main())