# hi clott
from api import dependencies
from core import crud_user
from core.security import create_access_token
from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel


class FormData(BaseModel):
    username: str
    password: str
from schemas.token import Token
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(dependencies.get_db),
    form_data: dict = Body(...),
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = await crud_user.authenticate(
        db, email=form_data["username"], password=form_data["password"]
    )
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = await crud_user.authenticate(
        db, email=form_data["username"], password=form_data["password"]
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }
