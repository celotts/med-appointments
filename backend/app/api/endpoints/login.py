from core import crud_user
from core.security import create_access_token
from dependencies import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from schemas.token import Token
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
DB_DEPENDENCY = Depends(get_db)


@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    db: AsyncSession = DB_DEPENDENCY,
    form_data: OAuth2PasswordRequestForm = Depends(),  # noqa: B008
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = await crud_user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }
