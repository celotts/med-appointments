import logging
import uuid

from core import crud_user
from core.config import settings
from core.db import SessionLocal
from schemas.user import UserCreate
from sqlalchemy.ext.asyncio import AsyncSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SUPER_ADMIN role ID defined in init.sql
SUPER_ADMIN_ROLE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


async def init_db(db: AsyncSession) -> None:
    # This function is called on application startup to create the first superuser
    user = await crud_user.get_user_by_email(db, email=settings.FIRST_SUPERUSER_EMAIL)
    if not user:
        logger.info("Creating the first superuser")
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER_EMAIL,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            full_name="Super Admin",
            role_id=SUPER_ADMIN_ROLE_ID,
        )
        await crud_user.create_user(db, user_in=user_in)
        logger.info("Superuser created")
    else:
        logger.info("Superuser already exists, skipping creation.")


async def main() -> None:
    logger.info("Starting initial data creation")
    async with SessionLocal() as session:
        await init_db(session)
    logger.info("Initial data created")
