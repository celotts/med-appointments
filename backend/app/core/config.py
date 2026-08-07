from pydantic_settings import BaseSettings
from pydantic import EmailStr


class Settings(BaseSettings):
    DATABASE_URL: str

    # Credenciales para el primer superusuario
    FIRST_SUPERUSER_EMAIL: EmailStr
    FIRST_SUPERUSER_PASSWORD: str
    # Clave secreta y tiempo de expiración del token en segundos
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 90000  # 25 horas por defecto

    class Config:
        # Busca el archivo .env en el directorio raíz del backend (dos niveles arriba)
        # desde la ubicación de este archivo (app/core/config.py)
        env_file = "../../.env"


settings = Settings()
