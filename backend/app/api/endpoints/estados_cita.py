from typing import Any

from core import crud_cita
from dependencies import get_current_user, get_db
from fastapi import APIRouter, Depends
from models.user import User as UserModel
from schemas.cita import EstadoCitaOut
from sqlalchemy.ext.asyncio import AsyncSession

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
