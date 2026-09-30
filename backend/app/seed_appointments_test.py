#!/usr/bin/env python3
"""
Seed appointments for schedule/agenda testing - 200 appointments.
Run: python /app/app/seed_appointments_test.py
"""

import asyncio
import random
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import engine
from app.models import Appointment, AppointmentStatus, Doctor, Patient, User

async def seed_appointments_test():
    async with AsyncSession(engine, expire_on_commit=False) as db:
        print("Checking current state...")
        
        # Get doctors, patients, statuses, admin
        result = await db.execute(select(Doctor))
        doctors = result.scalars().all()
        print(f"Doctors: {len(doctors)}")
        
        result = await db.execute(select(Patient))
        patients = result.scalars().all()
        print(f"Patients: {len(patients)}")
        
        result = await db.execute(select(AppointmentStatus))
        statuses = {s.code: s.id for s in result.scalars().all()}
        print(f"Statuses: {list(statuses.keys())}")
        
        result = await db.execute(select(User).where(User.email == "admin@clinica.com"))
        admin = result.scalars().first()
        print(f"Admin: {admin.id if admin else None}")
        
        # Check existing appointments
        result = await db.execute(select(Appointment))
        existing = result.scalars().all()
        print(f"Existing appointments: {len(existing)}")
        
        # Create 200 appointments
        status_codes = list(statuses.keys())
        base_date = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        
        reasons = [
            "Consulta de rutina", "Control presión arterial", "Revisión laboratorio",
            "Control diabetes", "Chequeo anual", "Síntomas gripales", "Dolor abdominal",
            "Dolor cabeza", "Control post-operatorio", "Seguimiento tratamiento",
            "Renovación receta", "Vacunación", "Evaluación pre-operatoria",
            "Consulta ansiedad", "Control peso", "Revisión dermatológica",
        ]
        
        appointments_created = 0
        for i in range(200):
            doctor = random.choice(doctors)
            patient = random.choice(patients)
            status_code = random.choice(status_codes)
            
            # Distribute: 30% past, 20% today, 50% future
            r = random.random()
            if r < 0.3:
                days_offset = random.randint(-30, -1)
            elif r < 0.5:
                days_offset = 0
            else:
                days_offset = random.randint(1, 60)
            
            hour = random.randint(8, 17)
            minute = random.choice([0, 15, 30, 45])
            start_dt = base_date + timedelta(days=days_offset, hours=hour-8, minutes=minute)
            end_dt = start_dt + timedelta(minutes=random.choice([15, 20, 30, 45, 60]))
            
            # Adjust status for past appointments
            if start_dt < datetime.now() and status_code in ['SCHEDULED', 'CONFIRMED', 'WAITING']:
                status_code = random.choice(['COMPLETED', 'CANCELLED', 'NO_SHOW'])
            
            appt = Appointment(
                patient_id=patient.id,
                doctor_id=doctor.id,
                user_id=admin.id,
                status_id=statuses[status_code],
                start_datetime=start_dt,
                end_datetime=end_dt,
                reason=f"{random.choice(reasons)} - {doctor.first_name} {doctor.last_name}",
            )
            db.add(appt)
            appointments_created += 1
        
        await db.commit()
        print(f"Created {appointments_created} appointments")
        
        # Verify
        result = await db.execute(select(Appointment))
        all_appts = result.scalars().all()
        print(f"Total appointments now: {len(all_appts)}")
        
        # Status breakdown
        status_counts = {}
        for a in all_appts:
            for code, sid in statuses.items():
                if a.status_id == sid:
                    status_counts[code] = status_counts.get(code, 0) + 1
                    break
        print("Status breakdown:")
        for code, count in status_counts.items():
            print(f"  {code}: {count}")

if __name__ == "__main__":
    asyncio.run(seed_appointments_test())