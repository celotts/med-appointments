from typing import Any

from core import crud_appointment
from dependencies import get_current_user, get_db
from dependencies_i18n import get_language, I18nResponse
from fastapi import APIRouter, Depends
from models.user import User as UserModel
from schemas.appointment import AppointmentStatusOut
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get(
    "/",
    response_model=list[AppointmentStatusOut],
    summary="Get the appointment status catalog",
)
async def list_statuses(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Lists the possible statuses of an appointment (PENDING, CONFIRMED, etc.)."""
    return await crud_appointment.get_statuses(db)
