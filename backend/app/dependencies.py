import uuid

from core import crud_user, rbac
from core.config import settings
from core.db import SessionLocal
from core.security import ALGORITHM
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from models.user import User
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/login/access-token")


async def get_db():
    async with SessionLocal() as session:
        yield session


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    """Valida el access token y devuelve su usuario.

    ## Por que se exige `exp`

    `jwt.decode` comprueba la caducidad **solo si el claim existe**: un JWT sin
    `exp` se aceptaba con un 200, y era una sesion eterna. No es un token
    valido, es un token que nunca caduca, y con el access token corto de ahora
    (15 min) cabia en un payload para saltarse la caducidad por completo.

    `options={"require": [...]}` hace que el decodificador rechace el token si
    le faltan esos claims.

    ## Por que 404 y no 401 si el usuario no existe

    El 401 se reserva para "token invalido". Un 404 en ese caso evita que un
    atacante distinga un id de usuario real de uno inventado probando tokens.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        # `exp` obligatorio. NO se usa `options={"require": [...]}` porque
        # python-jose 3.5.0 acepta el argumento y lo ignora: un JWT sin `exp`
        # pasaba la validacion con un 200. Comprobado, no supuesto.
        if "exp" not in payload:
            raise jwt.JWTError("Token sin claim 'exp'")
        if "sub" not in payload:
            raise jwt.JWTError("Token sin claim 'sub'")
        user_id = uuid.UUID(payload["sub"])
    except (jwt.JWTError, ValidationError, AttributeError, KeyError) as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err
    user = await crud_user.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive.")
    return user


def require_roles(*roles: str):
    """Dependencia reusable que exige uno de los roles indicados.

    Usa la comparacion normalizada de `core.rbac`, de modo que
    "super-admin", "super_admin" y "SUPER_ADMIN" son el mismo rol.

    Uso:
        @router.get("/", current_user=Depends(require_roles(ADMIN_ROLES)))

    Devuelve el usuario autenticado para poder usar `current_user`.
    """

    async def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if not rbac.has_role(current_user, roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para realizar esta accion.",
            )
        return current_user

    return _dependency


# Atajo de uso frecuente: exigir rol administrativo.
require_admin = require_roles(*rbac.ADMIN_ROLES)
