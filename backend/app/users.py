import uuid
from typing import Any

from api import dependencies
from core import crud_user
from fastapi import APIRouter, Depends, HTTPException
from models.user import User as UserModel
from schemas.user import User, UserCreate, UserUpdate
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get(
    "/",
    response_model=list[User],
    summary="Get a list of users",
)
async def read_users(
    db: AsyncSession = Depends(dependencies.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: UserModel = Depends(dependencies.get_current_user),
) -> Any:
    """Get a list of users."""
    users = await crud_user.get_users(db, skip=skip, limit=limit)
    return users


@router.post(
    "/",
    response_model=User,
    status_code=201,
    summary="Create a new user",
    responses={
        400: {"description": "The email is already registered in the system."},
    },
)
async def create_user(
    *,
    db: AsyncSession = Depends(dependencies.get_db),
    user_in: UserCreate,
) -> User:
    try:
        user = await crud_user.create_user(db=db, user_in=user_in)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=400, detail="The email is already registered."
        ) from exc
    return user


@router.get(
    "/{user_id}",
    response_model=User,
    summary="Get a user by ID",
    responses={404: {"description": "The user with the specified ID was not found."}},
)
async def read_user_by_id(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(dependencies.get_db),
    current_user: UserModel = Depends(dependencies.get_current_user),
) -> Any:
    """Get a user by ID."""
    user = await crud_user.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.put(
    "/{user_id}",
    response_model=User,
    summary="Update an existing user",
    responses={404: {"description": "The user with the specified ID was not found."}},
)
async def update_user(
    *,
    db: AsyncSession = Depends(dependencies.get_db),
    user_id: uuid.UUID,
    user_in: UserUpdate,
    current_user: UserModel = Depends(dependencies.get_current_user),
) -> Any:
    """Update a user."""
    db_user = await crud_user.get_user(db, user_id=user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found.")
    user = await crud_user.update_user(db=db, db_user=db_user, user_in=user_in)
    return user


@router.delete(
    "/{user_id}",
    response_model=User,
    summary="Delete a user",
    responses={404: {"description": "The user with the specified ID was not found."}},
)
async def delete_user(
    *,
    db: AsyncSession = Depends(dependencies.get_db),
    user_id: uuid.UUID,
    current_user: UserModel = Depends(dependencies.get_current_user),
) -> Any:
    """Delete a user."""
    user = await crud_user.remove_user(db=db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user
