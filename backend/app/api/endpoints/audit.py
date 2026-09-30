"""Consulta del registro de auditoria.

Solo administradores. La auditoria puede contener motivos clinicos (motivo de
suspension, notas de la consulta) y datos de personal, asi que no se expone al
resto de usuarios.

Ver `docs/AUDITORIA.md`.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from core import crud_audit
from core.crud_medical_note_audit import TABLA_NOTAS
from dependencies import get_db, require_admin
from fastapi import APIRouter, Depends, Query
from models.audit import AuditLog as AuditLogModel
from models.user import User as UserModel
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/audit", tags=["Audit"])


class AuditEntryOut(BaseModel):
    """Un registro de auditoria, con el JSON ya parseado."""

    id: uuid.UUID
    action: str
    table_name: str
    record_id: uuid.UUID | None
    old_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    user_id: uuid.UUID | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


def _a_salida(registro: AuditLogModel) -> AuditEntryOut:
    """Convierte el modelo en el schema de salida, parseando el JSON."""

    def parse(valor: str | None) -> dict[str, Any] | None:
        if not valor:
            return None
        try:
            return json.loads(valor)
        except (TypeError, ValueError):
            return {"raw": valor}

    return AuditEntryOut(
        id=registro.id,
        action=registro.action.value,
        table_name=registro.table_name,
        record_id=registro.record_id,
        old_value=parse(registro.old_value),
        new_value=parse(registro.new_value),
        user_id=registro.user_id,
        ip_address=registro.ip_address,
        user_agent=registro.user_agent,
        created_at=registro.created_at,
    )


@router.get(
    "/",
    response_model=list[AuditEntryOut],
    summary="Listar registros de auditoria (solo admin)",
)
async def listar(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    table_name: str | None = Query(None, description="Filtrar por tabla"),
    record_id: int | None = Query(None, description="Filtrar por id de registro"),
    user_id: uuid.UUID | None = Query(None, description="Filtrar por usuario"),
    current_user: UserModel = Depends(require_admin),
) -> list[AuditEntryOut]:
    registros = await crud_audit.listar_auditoria(
        db,
        skip=skip,
        limit=limit,
        table_name=table_name,
        record_id=record_id,
        user_id=user_id,
    )
    return [_a_salida(r) for r in registros]


@router.get(
    "/notes/{note_id}",
    response_model=list[AuditEntryOut],
    summary="Historial de una nota clinica (solo admin)",
)
async def historial_nota(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_admin),
) -> list[AuditEntryOut]:
    """Rastro de una nota medica: creacion, modificaciones y borrado.

    Incluye el contenido previo y el nuevo de cada edicion, que es lo que hace
    falta para reconstruir que se corrigio.
    """
    registros = await crud_audit.listar_auditoria(
        db,
        skip=0,
        limit=500,
        table_name=TABLA_NOTAS,
        record_id=note_id,
    )
    return [_a_salida(r) for r in registros]


@router.get(
    "/appointments/{appointment_id}",
    response_model=list[AuditEntryOut],
    summary="Historial de auditoria de una cita (solo admin)",
)
async def historial_cita(
    appointment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_admin),
) -> list[AuditEntryOut]:
    """Rastro completo de una cita: creacion, transiciones y borrado."""
    registros = await crud_audit.listar_auditoria(
        db, skip=0, limit=500, table_name=crud_audit.TABLA_CITAS, record_id=appointment_id
    )
    return [_a_salida(r) for r in registros]


@router.get(
    "/summary",
    summary="Resumen por accion y tabla (solo admin)",
)
async def resumen(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(require_admin),
) -> dict[str, Any]:
    """Totales de registros, agrupados por accion."""
    from sqlalchemy import func, select

    result = await db.execute(
        select(
            AuditLogModel.action,
            AuditLogModel.table_name,
            func.count(),
        ).group_by(AuditLogModel.action, AuditLogModel.table_name)
    )
    return {
        f"{accion.value}:{tabla}": total for accion, tabla, total in result.all()
    }
