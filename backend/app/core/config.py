from pydantic import EmailStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str

    # Credenciales para el primer superusuario
    FIRST_SUPERUSER_EMAIL: EmailStr
    FIRST_SUPERUSER_PASSWORD: str
    # Secret key and token expiration time in seconds
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 90000  # 25 horas por defecto

    # Ollama / RAG
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_LLM_MODEL: str = "llama3.2"
    EMBEDDING_DIM: int = 768

    class Config:
        # Look for .env file in the backend root directory (two levels up)
        # from this file's location (app/core/config.py)
        env_file = "../../.env"


settings = Settings()
