from typing import Any

from core import crud_user
from dependencies import get_current_user, get_db
from fastapi import APIRouter, Depends, HTTPException
from models.user import User as UserModel
from schemas.user import User, UserCreate
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get(
    "/me",
    response_model=User,
    summary="Get current authenticated user",
)
async def read_current_user(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """Get current authenticated user."""
    return current_user


@router.get(
    "/",
    response_model=list[User],
    summary="Get a list of users",
)
async def read_users(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: UserModel = Depends(get_current_user),
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
    db: AsyncSession = Depends(get_db),
    user_in: UserCreate,
) -> User:
    try:
        user = await crud_user.create_user(db=db, user_in=user_in)
    except IntegrityError as err:
        raise HTTPException(
            status_code=400, detail="The email is already registered."
        ) from err
    return user
