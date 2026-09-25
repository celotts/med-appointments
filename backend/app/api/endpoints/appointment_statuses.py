from typing import Any

from core import crud_appointment
from dependencies import get_current_user, get_db
from dependencies_i18n import get_language
from fastapi import APIRouter, Depends, HTTPException, status
from models.user import User as UserModel
from schemas.appointment import AppointmentStatusCreate, AppointmentStatusOut, AppointmentStatusUpdateSchema
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


@router.post(
    "/",
    response_model=AppointmentStatusOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new appointment status",
)
async def create_status(
    status_in: AppointmentStatusCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Create a new appointment status."""
    try:
        return await crud_appointment.create_status(
            db, code=status_in.code, description=status_in.description
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/{status_id}",
    response_model=AppointmentStatusOut,
    summary="Update an appointment status",
)
async def update_status(
    status_id: int,
    status_in: AppointmentStatusUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Update an appointment status."""
    try:
        return await crud_appointment.update_status(
            db, status_id=status_id, code=status_in.code, description=status_in.description
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise


@router.delete(
    "/{status_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an appointment status",
)
async def delete_status(
    status_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    """Delete an appointment status. Fails if status is used by appointments."""
    try:
        deleted = await crud_appointment.delete_status(db, status_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Status not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise
