from __future__ import annotations

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.waitlist import Waitlist
from .schemas import WaitlistCreate, WaitlistUpdate


async def get_waitlist_entry(db: AsyncSession, entry_id: int) -> Optional[Waitlist]:
    result = await db.execute(select(Waitlist).where(Waitlist.id == entry_id))
    return result.scalar_one_or_none()


async def get_waitlist_entries(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Waitlist]:
    result = await db.execute(select(Waitlist).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_waitlist_entry(db: AsyncSession, entry_in: WaitlistCreate) -> Waitlist:
    db_entry = Waitlist(
        patient_id=entry_in.patient_id,
        doctor_id=entry_in.doctor_id,
        preferred_date=entry_in.preferred_date,
        reason=entry_in.reason,
        status=entry_in.status,
    )
    db.add(db_entry)
    await db.commit()
    await db.refresh(db_entry)
    return db_entry


async def update_waitlist_entry(db: AsyncSession, entry_id: int, entry_in: WaitlistUpdate) -> Optional[Waitlist]:
    db_entry = await get_waitlist_entry(db, entry_id)
    if not db_entry:
        return None
    update_data = entry_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_entry, field, value)
    await db.commit()
    await db.refresh(db_entry)
    return db_entry


async def delete_waitlist_entry(db: AsyncSession, entry_id: int) -> bool:
    db_entry = await get_waitlist_entry(db, entry_id)
    if not db_entry:
        return False
    await db.delete(db_entry)
    await db.commit()
    return True
