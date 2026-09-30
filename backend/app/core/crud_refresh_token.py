"""Ciclo de vida de los refresh tokens.

Un token opaco hasheado en `refresh_tokens`. Ver `models/refresh_token.py` para
por que no es un JWT.

## Rotacion

Cada refresh consume el token usado y emite uno nuevo. Es lo que hace que un
refresh token robado tenga una ventana de un solo uso:

1. El atacante roba el token R1.
2. El titular legitimo refresca: R1 se marca revocado y se emite R2.
3. El atacante intenta usar R1: rechazado.

El caso inverso (el atacante refresca primero) se detecta porque el titular
legitimo recibe un fallo; ahi toca cerrar todas las sesiones, que es lo que hace
`revocar_todas`.

## Limite de sesiones

Un usuario no puede tener mas de `MAX_SESIONES_POR_USUARIO` sesiones abiertas.
Al superarlo se revoca la mas antigua: una lista que crece sin limite es una
lista que nadie va a revisar.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.refresh_token import RefreshToken as RefreshTokenModel
from models.refresh_token import caducidad, generar_token, hashear_token


async def crear(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    origen: str = "web",
    ip: str | None = None,
) -> tuple[str, RefreshTokenModel]:
    """Emite un refresh token. Devuelve el token EN CLARO (una sola vez) y la fila.

    El claro existe unicamente en esta respuesta: la base guarda el hash.
    """
    token = generar_token()
    fila = RefreshTokenModel(
        user_id=user_id,
        hashed_token=hashear_token(token),
        expires_at=caducidad(settings.REFRESH_TOKEN_EXPIRE_DAYS),
        origen=origen[:32],
        last_ip=ip,
    )
    db.add(fila)
    await db.commit()
    await db.refresh(fila)

    # DESPUES de insertar: el recorte tiene en cuenta esta sesion, de modo que
    # al superar el limite se revoca la mas antigua y se conservan las
    # recientes. Si se hiciera antes, el limite acabaria siendo `limite + 1`.
    await _apurar_sesiones(db, user_id=user_id)
    return token, fila


async def _apurar_sesiones(db: AsyncSession, *, user_id: uuid.UUID) -> None:
    """Revoca las sesiones mas antiguas cuando se supera el limite.

    Se ejecuta DESPUES de insertar el token nuevo, asi que la cuenta ya
    incluye esa sesion: si hay `limite + 1`, sobra exactamente una.

    El desempate por `id` no es cosmetico. `created_at` es `NOW()`, que en
    PostgreSQL devuelve el mismo instante para todas las filas de una
    transaccion: varios logins seguidos comparten timestamp y el
    `ORDER BY created_at` los deja en un orden arbitrario, con lo que el corte
    puede conservar la sesion antigua y revocar la nueva. `id` es un UUID
    aleatorio, no monotonico, asi que se usa `created_at` y, a igualdad,
    `random()`: el objetivo es un orden estable, no importar cual de los
    empates sobrevive.
    """
    limite = settings.MAX_SESIONES_POR_USUARIO
    vigentes = (
        await db.execute(
            select(RefreshTokenModel.id)
            .where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.revoked_at.is_(None),
                RefreshTokenModel.expires_at > datetime.now(timezone.utc),
            )
            .order_by(
                RefreshTokenModel.created_at.desc(), func.random().desc()
            )
        )
    ).scalars().all()

    # Solo hay que actuar si, contando la nueva, se pasa del limite.
    if len(vigentes) <= limite:
        return

    a_revocar = vigentes[limite:]
    await db.execute(
        update(RefreshTokenModel)
        .where(RefreshTokenModel.id.in_(a_revocar))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()


async def obtener_vigente(
    db: AsyncSession, token: str
) -> RefreshTokenModel | None:
    """Busca el token y lo devuelve solo si sigue vigente.

    Devuelve None en los tres casos de fallo (no existe, revocado, caducado)
    a proposito: quien llama no necesita saber cual fue, y no se le da esa
    informacion a quien intenta usarlo.
    """
    if not token:
        return None
    result = await db.execute(
        select(RefreshTokenModel).where(
            RefreshTokenModel.hashed_token == hashear_token(token)
        )
    )
    fila = result.scalars().first()
    if fila is None:
        return None
    return fila if fila.esta_vigente() else None


async def rotar(
    db: AsyncSession, token: str, *, ip: str | None = None
) -> tuple[str, RefreshTokenModel] | None:
    """Consume el token usado y emite otro. None si no era valido."""
    fila = await obtener_vigente(db, token)
    if fila is None:
        return None

    # Se revoca ANTES de emitir el siguiente: si el commit falla, el token viejo
    # sigue siendo valido y el usuario puede reintentar. Al reves, se pierde la
    # sesion sin motivo.
    fila.revoked_at = datetime.now(timezone.utc)
    if ip:
        fila.last_ip = ip
    await db.flush()

    nuevo_token, nueva_fila = await crear(db, user_id=fila.user_id, ip=ip)
    return nuevo_token, nueva_fila


async def revocar(db: AsyncSession, token: str) -> bool:
    """Revoca un token concreto (logout). True si estaba vigente."""
    if not token:
        return False
    result = await db.execute(
        update(RefreshTokenModel)
        .where(
            RefreshTokenModel.hashed_token == hashear_token(token),
            RefreshTokenModel.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return result.rowcount > 0


async def revocar_todas(db: AsyncSession, *, user_id: uuid.UUID) -> int:
    """Cierra TODAS las sesiones del usuario. Devuelve cuantas cerro."""
    result = await db.execute(
        update(RefreshTokenModel)
        .where(
            RefreshTokenModel.user_id == user_id,
            RefreshTokenModel.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return result.rowcount or 0


async def sesiones_activas(db: AsyncSession, *, user_id: uuid.UUID) -> list[dict]:
    """Sesiones vivas del usuario, para la pantalla de seguridad."""
    result = await db.execute(
        select(
            RefreshTokenModel.id,
            RefreshTokenModel.created_at,
            RefreshTokenModel.expires_at,
            RefreshTokenModel.origen,
            RefreshTokenModel.last_ip,
        )
        .where(
            RefreshTokenModel.user_id == user_id,
            RefreshTokenModel.revoked_at.is_(None),
            RefreshTokenModel.expires_at > datetime.now(timezone.utc),
        )
        .order_by(RefreshTokenModel.created_at.desc())
    )
    return [
        {
            "id": str(id_),
            "creada": creada.isoformat(),
            "expira": expira.isoformat(),
            "origen": origen,
            "ip": ip,
        }
        for id_, creada, expira, origen, ip in result.all()
    ]


async def purgar_caducados(db: AsyncSession) -> int:
    """Borra tokens ya vencidos. Lo llamara el job de mantenimiento."""
    result = await db.execute(
        delete(RefreshTokenModel).where(
            RefreshTokenModel.expires_at < datetime.now(timezone.utc)
        )
    )
    await db.commit()
    return result.rowcount or 0


__all__ = [
    "crear",
    "obtener_vigente",
    "rotar",
    "revocar",
    "revocar_todas",
    "sesiones_activas",
    "purgar_caducados",
]
