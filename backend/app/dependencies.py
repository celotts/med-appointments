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
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = uuid.UUID(payload.get("sub"))
    except (jwt.JWTError, ValidationError, AttributeError) as err:
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
