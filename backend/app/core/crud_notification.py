from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.db import SessionLocal
from models.notification import Notification as NotificationModel
from schemas.notification import NotificationOut, NotificationUpdate


async def create_notification(
    patient_id: int,
    type: str,
    title: str,
    message: str,
) -> NotificationModel:
    notification = NotificationModel(
        patient_id=patient_id,
        type=type,
        title=title,
        message=message,
    )
    async with SessionLocal() as session:
        session.add(notification)
        await session.commit()
        await session.refresh(notification)
    return notification


async def get_patient_notifications(
    db: AsyncSession,
    patient_id: int,
    limit: int = 20,
    offset: int = 0,
) -> list[NotificationModel]:
    result = await db.execute(
        select(NotificationModel)
        .where(NotificationModel.patient_id == patient_id)
        .order_by(NotificationModel.created_at.desc())
        .offset(offset)
        .limit(limit)
        .options(selectinload(NotificationModel.patient))
    )
    return list(result.scalars().all())


async def mark_as_read(db: AsyncSession, notification_id: int) -> Optional[NotificationModel]:
    notification = await db.get(NotificationModel, notification_id)
    if not notification:
        return None
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return notification


async def get_unread_count(db: AsyncSession, patient_id: int) -> int:
    result = await db.execute(
        select(func.count()).where(
            NotificationModel.patient_id == patient_id,
            NotificationModel.is_read == False,
        )
    )
    return result.scalar() or 0
