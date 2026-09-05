import logging
import uuid

from core import crud_user
from core.config import settings
from core.db import SessionLocal
from schemas.user import UserCreate
from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ID del rol SUPER_ADMIN definido en init.sql
SUPER_ADMIN_ROLE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


async def init_db(db: AsyncSession) -> None:
    # Esta función es llamada al iniciar la aplicación para crear el primer superusuario
    user = await crud_user.get_user_by_email(db, email=settings.FIRST_SUPERUSER_EMAIL)
    if not user:
        logger.info("Creando el primer superusuario")
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER_EMAIL,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            full_name="Super Admin",
            role_id=SUPER_ADMIN_ROLE_ID,
        )
        await crud_user.create_user(db, user_in=user_in)
        logger.info("Superusuario creado")
    else:
        logger.info("El superusuario ya existe, omitiendo creación.")


async def main() -> None:
    logger.info("Iniciando la creación de datos iniciales")
    async with SessionLocal() as session:
        await init_db(session)
    logger.info("Datos iniciales creados")
