import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_password_hash, verify_password
from models.user import User as UserModel
from schemas.user import (
    UserCreate as UserCreateSchema,
    UserUpdate as UserUpdateSchema,
)


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> UserModel | None:
    """Obtiene un usuario por su ID."""
    result = await db.execute(select(UserModel).filter(UserModel.id == user_id))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str) -> UserModel | None:
    """Obtiene un usuario por su email."""
    result = await db.execute(select(UserModel).filter(UserModel.email == email))
    return result.scalars().first()


async def get_users(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[UserModel]:
    """Obtiene una lista de usuarios con paginación."""
    result = await db.execute(select(UserModel).offset(skip).limit(limit))
    return result.scalars().all()


async def authenticate(
    db: AsyncSession, *, email: str, password: str
) -> UserModel | None:
    user = await get_user_by_email(db, email=email)
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user


async def create_user(db: AsyncSession, *, user_in: UserCreateSchema) -> UserModel:
    hashed_password = get_password_hash(user_in.password)
    db_user = UserModel(
        email=user_in.email,
        full_name=user_in.full_name,
        password=hashed_password,
        # Los campos address, phone, phone2, is_active usan sus valores por defecto del modelo
        role_id=user_in.role_id,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def update_user(
    db: AsyncSession, *, db_user: UserModel, user_in: UserUpdateSchema
) -> UserModel:
    """Actualiza un usuario."""
    user_data = user_in.model_dump(exclude_unset=True)

    # Si se proporciona una nueva contraseña, hashearla
    if password := user_data.get("password"):
        hashed_password = get_password_hash(password)
        db_user.password = hashed_password
        del user_data["password"]

    for field, value in user_data.items():
        setattr(db_user, field, value)

    await db.commit()
    await db.refresh(db_user)
    return db_user


async def remove_user(db: AsyncSession, *, user_id: uuid.UUID) -> UserModel | None:
    """Elimina un usuario por su ID."""
    result = await db.execute(select(UserModel).filter(UserModel.id == user_id))
    user_to_delete = result.scalars().first()
    if user_to_delete:
        await db.delete(user_to_delete)
        await db.commit()
    return user_to_delete
