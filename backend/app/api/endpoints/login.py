"""Inicio y cierre de sesion.

## El modelo

| Token | Vida | Revocable |
|---|---|---|
| `access_token` | 15 min (`ACCESS_TOKEN_EXPIRE_SECONDS`) | no |
| `refresh_token` | 7 dias (`REFRESH_TOKEN_EXPIRE_DAYS`) | si |

El access token viaja en cada peticion y no se puede revocar sin una lista de
bloqueo, asi que se acota su ventana. El refresh token es largo y opaco, y
guardar su hash en la base hace que cerrar sesion lo elimine de verdad.

Antes: 25 horas de un solo access token, sin refresh. Cerrar sesion en el
navegador no cerraba nada en el servidor.

## Por que auditar el login

Un intento fallido que no deja rastro no sirve para detectar un ataque: los
exitosos se ven en los estados, los fallidos son los que delatan fuerza bruta.
Y nunca se guarda la contrasena, ni siquiera hasheada: hashear la contrasena de
un intento fallido daria al atacante un oraculo para crackear sin limite.

Ver `docs/SEGURIDAD.md` y `docs/AUDITORIA.md`.
"""

from __future__ import annotations

from typing import Annotated, Any

from core import crud_audit, crud_refresh_token, crud_user
from core.config import settings
from core.security import create_access_token
from dependencies import get_current_user, get_db
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from models.user import User as UserModel
from pydantic import BaseModel, Field
from schemas.token import Token
from sqlalchemy.ext.asyncio import AsyncSession

# Prefijo SOLO del recurso: `main.py` lo registra con `prefix="/api/v1"`, asi
# que la ruta completa es `/api/v1/login/...`, que es la que espera
# `tokenUrl` en dependencies.py y el cliente del frontend.
#
# Poner `prefix="/api/v1/login"` aqui duplicaba el segmento y daba
# `/api/v1/api/v1/login/...`. Ponerlo vacío hacía lo contrario: la ruta se
# quedaba en `/api/v1/access-token` y el login devolvía 404.
router = APIRouter(prefix="/login", tags=["Login"])


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10, description="Refresh token opaco")


class SesionOut(BaseModel):
    """Sesion activa, para la pantalla de seguridad del usuario."""

    id: str
    creada: str
    expira: str
    origen: str
    ip: str | None


def _ip(request: Request) -> str | None:
    return request.client.host if request and request.client else None


async def _auditar_login(
    db: AsyncSession,
    request: Request,
    *,
    email: str,
    ok: bool,
    user_id: Any = None,
) -> None:
    """Deja rastro del intento, con exito o sin el.

    Los datos del actor se copian a variables ANTES de auditar: tras el flush la
    sesion expira los objetos y leerlos lanza MissingGreenlet.
    """
    await crud_audit.registrar(
        db,
        action=crud_audit.AuditAction.LOGIN,
        table_name="users",
        record_id=user_id if ok else None,
        user_id=user_id if ok else None,
        new_value={"email": email, "resultado": "ok" if ok else "fallido"},
        ip_address=_ip(request),
        user_agent=request.headers.get("user-agent") if request else None,
    )
    await db.commit()


@router.post("/access-token", response_model=Token)
async def login_access_token(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """Autentica y devuelve un par de tokens.

    `expires_in` viaja con la respuesta para que el cliente sepa cuando tiene
    que renovar, en vez de calcularlo adivinando.
    """
    user = await crud_user.authenticate(
        db, email=form_data.username, password=form_data.password
    )

    if not user:
        await _auditar_login(db, request, email=form_data.username, ok=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Copiado antes de auditar: ver la nota de MissingGreenlet.
    user_id = user.id
    await _auditar_login(db, request, email=form_data.username, ok=True, user_id=user_id)

    refresh, _fila = await crud_refresh_token.crear(
        db, user_id=user_id, origen="web", ip=_ip(request)
    )
    return Token(
        access_token=create_access_token(user_id),
        refresh_token=refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
    )


@router.post("/refresh", response_model=Token)
async def refrescar_token(
    request: Request,
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """Emite un access token nuevo consumiendo un refresh token valido.

    Rota el refresh token: el usado queda revocado y se entrega otro. Un token
    robado tiene entonces una sola oportunidad, y usarla se detecta porque el
    titular legitimo recibe un fallo.
    """
    rotado = await crud_refresh_token.rotar(db, body.refresh_token, ip=_ip(request))
    if rotado is None:
        # No se distingue entre "no existe", "caducado" y "revocado": esa
        # diferencia le diria al atacante que tokens son reales.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido",
        )

    refresh, fila = rotado
    return Token(
        access_token=create_access_token(fila.user_id),
        refresh_token=refresh,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def cerrar_sesion(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Revoca el refresh token.

    Esto es lo que antes no pasaba: `logout()` solo borraba el localStorage y el
    token seguia sirviendo en el servidor hasta 25 horas despues. Revocar aqui
    deja la sesion muerta en el acto; el access token ya emitido caduca en 15
    minutos como maximo.

    Es idempotente: cerrar sesion dos veces no falla.
    """
    await crud_refresh_token.revocar(db, body.refresh_token)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def cerrar_todas_las_sesiones(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: UserModel = Depends(get_current_user),
) -> None:
    """Cierra todas las sesiones del usuario.

    Es la respuesta al caso en que no se sabe cual robaron: revoca todas, se
    entra de nuevo y solo queda la recien creada.
    """
    await crud_refresh_token.revocar_todas(db, user_id=current_user.id)


@router.get("/sesiones", response_model=list[SesionOut])
async def listar_sesiones(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: UserModel = Depends(get_current_user),
) -> list[SesionOut]:
    """Sesiones activas, para que el usuario vea y cierre las suyas."""
    return [
        SesionOut(**s)
        for s in await crud_refresh_token.sesiones_activas(db, user_id=current_user.id)
    ]
