from __future__ import annotations

import uuid
from typing import Any

from core import crud_assistant
from dependencies import get_db, require_admin
from dependencies_i18n import get_language
from fastapi import APIRouter, Depends, HTTPException, Query
from models.user import User as UserModel
from sqlalchemy.ext.asyncio import AsyncSession

# Todos los endpoints de este router son de administracion.
# Se usa `require_admin` (core.rbac) en lugar del chequeo inline
# `role.name not in ("admin", "super_admin")`, que nunca coincidia con los
# roles reales de la BD (SUPER_ADMIN / ADMIN) y devolvia 403 siempre.
router = APIRouter(prefix="/api/v1/assistants", tags=["Assistants"])


@router.get("/", response_model=list[dict])
async def list_assistants(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UserModel = Depends(require_admin),
    language: str = Depends(get_language),
) -> Any:
    result = await crud_assistant.get_assistants(db, page=page, page_size=page_size)
    return result


@router.post("/{assistant_id}/specialists")
async def assign_specialist(
    assistant_id: uuid.UUID,
    specialist_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_admin),
    language: str = Depends(get_language),
) -> Any:
    asst = await crud_assistant.assign_specialist(db, assistant_id, specialist_id)
    if not asst:
        raise HTTPException(status_code=409, detail="Specialist already assigned")
    return {"message": "Specialist assigned"}


@router.delete("/{assistant_id}/specialists/{specialist_id}")
async def remove_specialist(
    assistant_id: uuid.UUID,
    specialist_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_admin),
    language: str = Depends(get_language),
) -> Any:
    removed = await crud_assistant.remove_specialist(db, assistant_id, specialist_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return {"message": "Specialist removed"}


@router.get("/{assistant_id}/specialists")
async def get_assistant_specialists(
    assistant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_admin),
    language: str = Depends(get_language),
) -> Any:
    specialists = await crud_assistant.get_assistant_specialists(db, assistant_id)
    return [{"id": s.id, "full_name": s.full_name, "email": s.email} for s in specialists]


@router.patch("/{assistant_id}/toggle")
async def toggle_assistant_active(
    assistant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_admin),
    language: str = Depends(get_language),
) -> Any:
    user = await crud_assistant.toggle_assistant_active(db, assistant_id)
    if not user:
        raise HTTPException(status_code=404, detail="Assistant not found")
    return {"id": user.id, "is_active": user.is_active, "full_name": user.full_name}


@router.get("/specialists", response_model=list[dict])
async def list_specialists(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_admin),
    language: str = Depends(get_language),
) -> Any:
    specialists = await crud_assistant.get_specialists(db)
    return [{"id": s.id, "full_name": s.full_name, "email": s.email} for s in specialists]
