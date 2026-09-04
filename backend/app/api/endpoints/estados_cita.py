from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_db, get_current_user
from core import crud_cita
from models.user import User as UserModel
from schemas.cita import EstadoCitaOut

router = APIRouter()


@router.get(
    "/",
    response_model=list[EstadoCitaOut],
    summary="Obtener el catálogo de estados de cita",
)
async def read_estados(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Lista los estados posibles de una cita (PENDIENTE, CONFIRMADA, etc.)."""
    return await crud_cita.get_estados(db)
