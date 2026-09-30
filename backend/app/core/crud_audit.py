"""Registro de auditoria.

`audit_logs` existia en el esquema desde el principio pero **nada escribia en
ella**: no habia forma de saber quien cambio el estado de una cita ni cuando.
Para datos clinicos eso no es una mejora pendiente, es un requisito.

Este modulo centraliza las escrituras. Reglas:

1. La auditoria va en la **misma transaccion** que el cambio. Si el cambio se
   revierte, el registro tambien.
2. Nunca rompe la operacion de negocio por un fallo propio: si la escritura
   falla se traga la excepcion y avisa por log. Perder una transicion de estado
   es peor que perder su rastro, y un `raise` desde aqui dejaria al usuario sin
   poder trabajar.
3. Los cambios de estado de cita son el caso obligatorio: cada transicion
   deja un registro con estado origen, destino, actor y motivo.

Formato del `new_value` (JSON) para transiciones:

```json
{
  "from_state": "CONFIRMADA",
  "to_state": "ATENDIDA",
  "reason": "Consulta completada",
  "metadata": {"duration_min": 25}
}
```

Ver `docs/AUDITORIA.md`.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from models.audit import AuditAction
from models.audit import AuditLog as AuditLogModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

TABLA_CITAS = "appointments"

__all__ = [
    "AuditAction",
    "AuditLogModel",
    "registrar",
    "registrar_transicion_cita",
    "registrar_login",
    "listar_auditoria",
    "contar_auditoria",
    "TABLA_CITAS",
    "normalizar_record_id",
    "normalizar_user_id",
]


def _serializar(valor: Any) -> str | None:
    """Convierte un valor a JSON seguro para columnas TEXT."""
    if valor is None:
        return None
    if isinstance(valor, (datetime,)):
        return valor.isoformat()
    try:
        return json.dumps(valor, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return json.dumps({"repr": repr(valor)}, ensure_ascii=False)


async def registrar(
    db: AsyncSession,
    *,
    action: AuditAction,
    table_name: str,
    record_id: int | str | None = None,
    user_id: uuid.UUID | str | None = None,
    old_value: Any = None,
    new_value: Any = None,
    reason: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    commit: bool = False,
) -> AuditLogModel | None:
    """Escribe un registro de auditoria.

    `record_id` se acepta como `int` aunque la columna sea UUID: las tablas de
    negocio usan SERIAL (appointments, patients, doctors). Para esos casos se
    deriva un UUID deterministico del id, de forma que el registro sea
    idempotente y rastreable sin duplicar claves.

    `reason` se guarda dentro de `new_value` bajo la clave `"motivo"`: la tabla
    `audit_logs` no tiene columna para el.

    No lanza excepcion: un fallo aqui no debe tumbar la operacion de negocio.
    """
    if reason:
        # Se copia para no mutar el dict del llamador.
        new_value = {**(new_value or {}), "motivo": reason}

    try:
        entrada = AuditLogModel(
            action=action,
            table_name=table_name,
            record_id=normalizar_record_id(record_id),
            user_id=normalizar_user_id(user_id),
            old_value=_serializar(old_value),
            new_value=_serializar(new_value),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(entrada)
        if commit:
            await db.commit()
            await db.refresh(entrada)
        return entrada
    except Exception as exc:  # noqa: BLE001
        # Se registra y se sigue. La transicion de estado ya es un hecho; el
        # fallo de auditoria no debe revertirla.
        logger.warning(
            "No se pudo escribir el registro de auditoria "
            "(tabla=%s, accion=%s): %s",
            table_name,
            action,
            exc,
        )
        return None


def normalizar_record_id(record_id: int | str | None) -> uuid.UUID | None:
    """Convierte un id de negocio (int) en UUID para `audit_logs.record_id`.

    Las tablas de negocio usan SERIAL, pero `audit_logs.record_id` es UUID.
    Se deriva un UUID v5 del namespace del proyecto mas el id, de modo que el
    mismo registro produce siempre el mismo UUID (idempotente) y dos ids
    distintos nunca colisionan.
    """
    if record_id is None:
        return None
    if isinstance(record_id, uuid.UUID):
        return record_id
    return uuid.uuid5(NAMESPACE_AUDITORIA, f"{record_id}")


def normalizar_user_id(user_id: uuid.UUID | str | None) -> uuid.UUID | None:
    if user_id is None:
        return None
    if isinstance(user_id, uuid.UUID):
        return user_id
    try:
        return uuid.UUID(str(user_id))
    except (ValueError, AttributeError, TypeError):
        return None


# Namespace fijo del proyecto para los UUID derivados.
NAMESPACE_AUDITORIA = uuid.UUID("6f1d4a2e-8b3c-4f5a-9d7e-1c2b3a4d5e6f")


async def registrar_transicion_cita(
    db: AsyncSession,
    *,
    appointment_id: int,
    from_state: str | None,
    to_state: str,
    user_id: uuid.UUID | str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLogModel | None:
    """Registro obligatorio de un cambio de estado de cita.

    `from_state` es None cuando la cita se crea (no hay estado previo).
    """
    payload: dict[str, Any] = {"from_state": from_state, "to_state": to_state}
    if reason:
        payload["reason"] = reason
    if metadata:
        payload["metadata"] = metadata

    return await registrar(
        db,
        action=AuditAction.UPDATE,
        table_name=TABLA_CITAS,
        record_id=appointment_id,
        user_id=user_id,
        old_value={"status": from_state} if from_state else None,
        new_value=payload,
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def registrar_login(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | str,
    ip_address: str | None = None,
    user_agent: str | None = None,
    success: bool = True,
) -> AuditLogModel | None:
    """Registra un intento de inicio de sesion.

    Los intentos fallidos tambien se registran: son los que delatan fuerza
    bruta. No se guarda la contrasena en ningun caso.
    """
    return await registrar(
        db,
        action=AuditAction.LOGIN,
        table_name="users",
        record_id=user_id if success else None,
        user_id=user_id if success else None,
        new_value={"email_login_attempt": success},
        ip_address=ip_address,
        user_agent=user_agent,
    )


async def listar_auditoria(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
    table_name: str | None = None,
    record_id: int | str | None = None,
    user_id: uuid.UUID | str | None = None,
) -> list[AuditLogModel]:
    """Lista registros de auditoria, mas recientes primero."""
    stmt = select(AuditLogModel).order_by(AuditLogModel.created_at.desc())

    if table_name:
        stmt = stmt.where(AuditLogModel.table_name == table_name)
    if record_id is not None:
        stmt = stmt.where(AuditLogModel.record_id == normalizar_record_id(record_id))
    if user_id is not None:
        stmt = stmt.where(AuditLogModel.user_id == normalizar_user_id(user_id))

    result = await db.execute(stmt.offset(skip).limit(limit))
    return list(result.scalars().all())


async def contar_auditoria(
    db: AsyncSession, *, table_name: str | None = None
) -> int:
    """Cuenta registros de auditoria, opcionalmente por tabla."""
    from sqlalchemy import func

    stmt = select(func.count()).select_from(AuditLogModel)
    if table_name:
        stmt = stmt.where(AuditLogModel.table_name == table_name)
    result = await db.execute(stmt)
    return int(result.scalar() or 0)
