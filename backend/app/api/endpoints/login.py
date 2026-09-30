from core import crud_audit, crud_user
from core.security import create_access_token
from dependencies import get_db
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from schemas.token import Token
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
DB_DEPENDENCY = Depends(get_db)


@router.post("/login/access-token", response_model=Token)
async def login_access_token(
    db: AsyncSession = DB_DEPENDENCY,
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
):
    user = await crud_user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    ip = request.client.host if request and request.client else None
    agent = request.headers.get("user-agent") if request else None

    if not user:
        # Los intentos fallidos tambien quedan auditados: son los que delatan
        # un ataque de fuerza bruta. No se registra la contrasena en ningun
        # caso. `user_id` se deja NULL porque el usuario no se pudo validar.
        await crud_audit.registrar(
            db,
            action=crud_audit.AuditAction.LOGIN,
            table_name="users",
            user_id=None,
            new_value={"email": form_data.username, "resultado": "fallido"},
            ip_address=ip,
            user_agent=agent,
        )
        await db.commit()
        raise HTTPException(401, "Incorrect email or password")

    # Se serializan los datos del usuario ANTES de auditar: tras el flush de la
    # auditoria la sesion queda expirada y cualquier acceso a atributos
    # relacionales dispara MissingGreenlet.
    user_id = user.id
    await crud_audit.registrar(
        db,
        action=crud_audit.AuditAction.LOGIN,
        table_name="users",
        record_id=user_id,
        user_id=user_id,
        new_value={"email": form_data.username, "resultado": "ok"},
        ip_address=ip,
        user_agent=agent,
    )
    await db.commit()

    return {"access_token": create_access_token(user_id), "token_type": "bearer"}
