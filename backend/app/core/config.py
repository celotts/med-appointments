"""Configuracion de la aplicacion.

## Caducidad de las sesiones

Dos tokens, con vidas distintas y para que el corto exista:

| Token | Vida | Donde vive | Revocable |
|---|---|---|---|
| `access_token` | `ACCESS_TOKEN_EXPIRE_SECONDS` (15 min) | JWT, en el cliente | no (es stateless) |
| `refresh_token` | `REFRESH_TOKEN_EXPIRE_DAYS` (7 días) | opaco, hasheado en BD | **si** |

El access token es corto a proposito: es el que viaja en cada peticion y no se
puede revocar sin una lista de bloqueo, asi que se acota su ventana. El refresh
token es largo, opaco (no es un JWT: no se puede falsificar) y vive hasheado en
la base, asi que cerrar sesion lo elimina de verdad.

Antes: 25 horas de access token, sin refresh. Eso dejaba la sesion abierta
durante una jornada entera sin possibility de cerrarla desde el servidor.

Los valores se validan al arrancar: un `0` o un negativo produciria tokens que
caducan al instante (o nunca), y se descubriria en produccion a las 3am.
"""

from typing import List

from pydantic import EmailStr, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str

    # Credenciales para el primer superusuario
    FIRST_SUPERUSER_EMAIL: EmailStr
    FIRST_SUPERUSER_PASSWORD: str
    SECRET_KEY: str

    # --- Sesion -----------------------------------------------------------
    # 15 minutos: es el token que viaja en cada peticion y no se puede revocar
    # sin una lista de bloqueo. Ventana corta = ventana de robo corta.
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 900

    # 7 dias: se puede revocar (esta en la base), asi que puede ser largo.
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Cuantas sesiones puede tener un usuario abiertas a la vez. Al superarlo
    # se revoca la mas antigua: un token robado tiene menos de una semana de
    # ventana y la lista no crece sin limite.
    MAX_SESIONES_POR_USUARIO: int = 5

    @field_validator("ACCESS_TOKEN_EXPIRE_SECONDS")
    @classmethod
    def _access_token_valido(cls, v: int) -> int:
        """Rechaza valores que dejarian la sesion inservible o eternal.

        `0` y negativos caducan el token al instante: el usuario entra y sale
        solo. Un valor enorme (mas de un dia) es el problema que se venia
        teniendo, y para datos clinicos no es aceptable.
        """
        if v <= 0:
            raise ValueError(
                "ACCESS_TOKEN_EXPIRE_SECONDS debe ser mayor que 0; "
                f"se recibio {v}"
            )
        if v > 86400:
            raise ValueError(
                "ACCESS_TOKEN_EXPIRE_SECONDS no puede superar 86400 (24 h) para "
                f"datos clinicos; se recibio {v} ({v / 3600:.1f} h). "
                "Para sesiones largas esta el refresh token."
            )
        return v

    @field_validator("REFRESH_TOKEN_EXPIRE_DAYS")
    @classmethod
    def _refresh_token_valido(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"REFRESH_TOKEN_EXPIRE_DAYS debe ser > 0; se recibio {v}")
        if v > 365:
            raise ValueError(
                f"REFRESH_TOKEN_EXPIRE_DAYS no puede superar 365; se recibio {v}"
            )
        return v

    @field_validator("MAX_SESIONES_POR_USUARIO")
    @classmethod
    def _max_sesiones_valido(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"MAX_SESIONES_POR_USUARIO debe ser > 0; se recibio {v}")
        return v

    DEBUG: bool = False

    # Ollama / RAG
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_LLM_MODEL: str = "llama3.2"
    EMBEDDING_DIM: int = 768

    # CORS origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ]

    class Config:
        # Look for .env file relative to this file's location
        env_file = "../.env"
        env_file_encoding = "utf-8"
        extra = "allow"


settings = Settings()
