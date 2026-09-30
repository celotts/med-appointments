#!/usr/bin/env python3
"""
Seed script for testing schedule/agenda behavior with 200 records.
Run: python /app/app/seed_schedule_test.py
"""

import asyncio
import random
from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import engine
from app.models import Doctor, DoctorSchedule, User

async def seed_schedule_test():
    async with AsyncSession(engine, expire_on_commit=False) as db:
        print("Checking current state...")
        
        # Get doctors
        result = await db.execute(select(Doctor))
        doctors = result.scalars().all()
        print(f"Found {len(doctors)} doctors")
        
        # Get admin user
        result = await db.execute(select(User).where(User.email == "admin@clinica.com"))
        admin = result.scalars().first()
        if not admin:
            print("Admin user not found!")
            return
        print(f"Admin user ID: {admin.id}")
        
        # Check existing schedules
        result = await db.execute(select(DoctorSchedule))
        existing = result.scalars().all()
        print(f"Existing schedules: {len(existing)}")
        
        # Create schedules for first 200 doctors (or all if less)
        schedules_created = 0
        target_doctors = min(200, len(doctors))
        
        for doctor in doctors[:target_doctors]:
            for day in range(1, 6):  # Mon-Fri
                # Check if schedule already exists
                result = await db.execute(
                    select(DoctorSchedule).where(
                        DoctorSchedule.doctor_id == doctor.id,
                        DoctorSchedule.day_of_week == day
                    )
                )
                if result.scalars().first():
                    continue
                
                # Random start time: 8:00 or 9:00
                start_time = time(8, 0) if random.random() < 0.5 else time(9, 0)
                # Random end time: 14:00 or 16:00
                end_time = time(14, 0) if random.random() < 0.5 else time(16, 0)
                # Random slot duration
                slot_duration = random.choice([15, 20, 30, 45])
                
                schedule = DoctorSchedule(
                    doctor_id=doctor.id,
                    user_id=admin.id,
                    day_of_week=day,
                    start_time=start_time,
                    end_time=end_time,
                    slot_duration_minutes=slot_duration,
                )
                db.add(schedule)
                schedules_created += 1
        
        await db.commit()
        print(f"Created {schedules_created} schedules for {target_doctors} doctors")
        
        # Verify
        result = await db.execute(select(DoctorSchedule))
        all_schedules = result.scalars().all()
        print(f"Total schedules now: {len(all_schedules)}")
        
        # Show sample
        for s in all_schedules[:10]:
            print(f"  Doctor {s.doctor_id}: Day {s.day_of_week} ({s.start_time}-{s.end_time}), Slot: {s.slot_duration_minutes}min")

if __name__ == "__main__":
    asyncio.run(seed_schedule_test())