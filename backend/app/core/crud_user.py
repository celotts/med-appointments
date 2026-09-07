import uuid

from core.security import get_password_hash, verify_password
from models.user import User as UserModel
from schemas.user import (
    UserCreate as UserCreateSchema,
)
from schemas.user import (
    UserUpdate as UserUpdateSchema,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> UserModel | None:
    """Get a user by their ID."""
    result = await db.execute(select(UserModel).filter(UserModel.id == user_id))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str) -> UserModel | None:
    """Get a user by their email."""
    result = await db.execute(select(UserModel).filter(UserModel.email == email))
    return result.scalars().first()


async def get_users(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[UserModel]:
    """Get a paginated list of users."""
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
        # Fields address, phone, phone2, is_active use their model defaults
        role_id=user_in.role_id,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def update_user(
    db: AsyncSession, *, db_user: UserModel, user_in: UserUpdateSchema
) -> UserModel:
    """Update a user."""
    user_data = user_in.model_dump(exclude_unset=True)

    # If a new password is provided, hash it
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
    """Remove a user by their ID."""
    result = await db.execute(select(UserModel).filter(UserModel.id == user_id))
    user_to_delete = result.scalars().first()
    if user_to_delete:
        await db.delete(user_to_delete)
        await db.commit()
    return user_to_delete
