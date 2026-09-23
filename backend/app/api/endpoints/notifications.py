from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.crud_notification import (
    get_patient_notifications,
    mark_as_read,
    get_unread_count,
)
from dependencies import get_current_user, get_db
from dependencies_i18n import I18nResponse, get_language
from fastapi import APIRouter, Depends, HTTPException
from models.user import User as UserModel
from models.patient import Patient
from schemas.notification import NotificationOut

router = APIRouter(prefix="/api/v1", tags=["Notifications"])


async def get_patient_id_for_user(db: AsyncSession, user: UserModel) -> Optional[int]:
    """Find patient ID associated with the current user by email."""
    result = await db.execute(
        select(Patient.id).where(Patient.email == user.email)
    )
    return result.scalar_one_or_none()


@router.get("/notifications/", response_model=list[NotificationOut])
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    patient_id = await get_patient_id_for_user(db, current_user)
    if not patient_id:
        return []
    return await get_patient_notifications(db, patient_id)


@router.get("/notifications/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, int]:
    patient_id = await get_patient_id_for_user(db, current_user)
    if not patient_id:
        return {"unread": 0}
    return {"unread": await get_unread_count(db, patient_id)}


@router.patch("/notifications/{notification_id}", response_model=NotificationOut)
async def read_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    patient_id = await get_patient_id_for_user(db, current_user)
    if not patient_id:
        i18n = I18nResponse(language)
        raise HTTPException(status_code=404, detail=i18n.get("not_found"))
    
    from core.crud_notification import mark_as_read
    notification = await mark_as_read(db, notification_id)
    if not notification or notification.patient_id != patient_id:
        i18n = I18nResponse(language)
        raise HTTPException(status_code=404, detail=i18n.get("not_found"))
    return notification
