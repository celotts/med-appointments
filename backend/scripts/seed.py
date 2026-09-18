"""
Seed script to initialize the database with initial data.
Run: python -m scripts.seed
"""
from __future__ import annotations

import asyncio
import uuid

from core.db import async_session_factory
from core.security import hash_password
from models.user import User
from models.role import Role
from models.specialty import Specialty
from models.appointment_status import AppointmentStatus

ROLES = [
    {"id": uuid.UUID("00000000-0000-0000-0000-000000000001"), "name": "SYSTEM_ROLE"},
    {"id": uuid.UUID("00000000-0000-0000-0000-000000000002"), "name": "SUPER_ADMIN"},
    {"id": uuid.UUID("00000000-0000-0000-0000-000000000003"), "name": "ADMIN"},
    {"id": uuid.UUID("00000000-0000-0000-0000-000000000004"), "name": "DOCTOR"},
    {"id": uuid.UUID("00000000-0000-0000-0000-000000000005"), "name": "RECEPTIONIST"},
]

SPECIALTIES = [
    {"name": "General Medicine", "description": "General medical practice"},
    {"name": "Cardiology", "description": "Heart and cardiovascular system"},
    {"name": "Dermatology", "description": "Skin, hair, and nails"},
    {"name": "Pediatrics", "description": "Medical care for infants, children, and adolescents"},
    {"name": "Orthopedics", "description": "Musculoskeletal system"},
    {"name": "Neurology", "description": "Nervous system"},
    {"name": "Gynecology", "description": "Female reproductive system"},
    {"name": "Ophthalmology", "description": "Eye care"},
]

APPOINTMENT_STATUSES = [
    {"code": "PENDING", "description": "Appointment requested, pending confirmation"},
    {"code": "CONFIRMED", "description": "Appointment confirmed with doctor"},
    {"code": "CANCELLED", "description": "Appointment cancelled by patient or clinic"},
    {"code": "COMPLETED", "description": "Appointment successfully attended"},
]

SEED_USER = {
    "id": uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
    "email": "admin@medclinic.com",
    "password": hash_password("admin123"),
    "full_name": "System Admin",
    "address": "System Address",
    "phone": "0000000000",
    "phone2": "0000000000",
    "is_active": True,
    "role_id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
}


async def seed():
    async with async_session_factory() as db:
        # Seed roles
        for role_data in ROLES:
            existing = await db.get(Role, role_data["id"])
            if not existing:
                db.add(Role(**role_data))
        await db.commit()

        # Seed specialties
        for spec_data in SPECIALTIES:
            from sqlalchemy.future import select
            result = await db.execute(select(Specialty).where(Specialty.name == spec_data["name"]))
            if not result.scalar_one_or_none():
                db.add(Specialty(**spec_data))
        await db.commit()

        # Seed appointment statuses
        for status_data in APPOINTMENT_STATUSES:
            result = await db.execute(
                select(AppointmentStatus).where(AppointmentStatus.code == status_data["code"])
            )
            if not result.scalar_one_or_none():
                db.add(AppointmentStatus(**status_data))
        await db.commit()

        # Seed admin user
        existing_user = await db.get(User, SEED_USER["id"])
        if not existing_user:
            db.add(User(**SEED_USER))
            await db.commit()

        print("Seed completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
