from __future__ import annotations

from typing import List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.role import Role
from .schemas import RoleCreate, RoleUpdate


async def get_role(db: AsyncSession, role_id: uuid.UUID) -> Optional[Role]:
    result = await db.execute(select(Role).where(Role.id == role_id))
    return result.scalar_one_or_none()


async def get_roles(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Role]:
    result = await db.execute(select(Role).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_role(db: AsyncSession, role_in: RoleCreate) -> Role:
    db_role = Role(name=role_in.name)
    db.add(db_role)
    await db.commit()
    await db.refresh(db_role)
    return db_role


async def update_role(db: AsyncSession, role_id: uuid.UUID, role_in: RoleUpdate) -> Optional[Role]:
    db_role = await get_role(db, role_id)
    if not db_role:
        return None
    update_data = role_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_role, field, value)
    await db.commit()
    await db.refresh(db_role)
    return db_role


async def delete_role(db: AsyncSession, role_id: uuid.UUID) -> bool:
    db_role = await get_role(db, role_id)
    if not db_role:
        return False
    await db.delete(db_role)
    await db.commit()
    return True
