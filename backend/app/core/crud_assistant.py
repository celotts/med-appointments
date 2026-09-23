from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.assistant_specialist import AssistantSpecialist
from models.user import User as UserModel
from models.role import Role as RoleModel


async def get_assistants(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    skip = (page - 1) * page_size
    count_stmt = select(func.count()).select_from(UserModel)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    stmt = (
        select(UserModel)
        .join(RoleModel, UserModel.role_id == RoleModel.id)
        .where(RoleModel.name == 'assistant', UserModel.is_active == True)
        .order_by(UserModel.created_at.desc())
        .offset(skip)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def get_assistant_specialists(
    db: AsyncSession,
    assistant_id: uuid.UUID,
) -> list[UserModel]:
    result = await db.execute(
        select(UserModel)
        .join(AssistantSpecialist, UserModel.id == AssistantSpecialist.specialist_id)
        .where(AssistantSpecialist.assistant_id == assistant_id)
    )
    return list(result.scalars().all())


async def assign_specialist(
    db: AsyncSession,
    assistant_id: uuid.UUID,
    specialist_id: uuid.UUID,
) -> Optional[AssistantSpecialist]:
    existing = await db.get(AssistantSpecialist, (assistant_id, specialist_id))
    if existing:
        return None
    asst = AssistantSpecialist(assistant_id=assistant_id, specialist_id=specialist_id)
    db.add(asst)
    await db.commit()
    await db.refresh(asst)
    return asst


async def remove_specialist(
    db: AsyncSession,
    assistant_id: uuid.UUID,
    specialist_id: uuid.UUID,
) -> bool:
    asst = await db.get(AssistantSpecialist, (assistant_id, specialist_id))
    if not asst:
        return False
    await db.delete(asst)
    await db.commit()
    return True


async def toggle_assistant_active(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> Optional[UserModel]:
    user = await db.get(UserModel, user_id)
    if not user:
        return None
    user.is_active = not user.is_active
    await db.commit()
    await db.refresh(user)
    return user


async def get_specialists(db: AsyncSession) -> list[UserModel]:
    result = await db.execute(
        select(UserModel)
        .where(UserModel.is_active == True)
        .order_by(UserModel.last_name, UserModel.first_name)
    )
    return list(result.scalars().all())


async def get_assistant_by_user_id(
    db: AsyncSession, user_id: uuid.UUID
) -> Optional[UserModel]:
    result = await db.execute(
        select(UserModel).where(UserModel.id == user_id)
    )
    return result.scalars().first()