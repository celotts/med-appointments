from typing import Any

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
from schemas.notification import NotificationOut

router = APIRouter(prefix="/api/v1", tags=["Notifications"])


@router.get("/notifications/", response_model=list[NotificationOut])
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    return await get_patient_notifications(db, current_user.id)


@router.get("/notifications/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, int]:
    return {"unread": await get_unread_count(db, current_user.id)}


@router.patch("/notifications/{notification_id}", response_model=NotificationOut)
async def read_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    notification = await mark_as_read(db, notification_id)
    if not notification or notification.patient_id != current_user.id:
        i18n = I18nResponse(language)
        raise HTTPException(status_code=404, detail=i18n.get("not_found"))
    return notification
