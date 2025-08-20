import os
from pathlib import Path
from datetime import timedelta
from pydantic_settings import BaseSettings, SettingsConfigDict
from authx import AuthXConfig

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


class Settings(BaseSettings):
    DEBUG: bool
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    SECRET: str
    JWT_SECRET_KEY: str

    BASE_DIR: Path = BASE_DIR
    STATIC_DIR: Path = STATIC_DIR

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / "env" / f".env.{os.getenv('ENVIRONMENT', 'dev')}",
        extra="ignore",
    )


class RadisCacheSettings(BaseSettings):
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    CACHE_TTL: int = 3600 * 24

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / "env" / f".env.{os.getenv('ENVIRONMENT', 'dev')}",
        extra="ignore",
    )

class SuperUserSettings(BaseSettings):
    CREATE_SUPERUSER: bool
    SUPERUSER_EMAIL: str
    SUPERUSER_PASSWORD: str
    SUPERUSER_FIRSTNAME: str
    SUPERUSER_LASTNAME: str
    SUPERUSER_USERNAME: str

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / "env" / f".env.{os.getenv('ENVIRONMENT', 'dev')}",
        extra="ignore",
    )

super_user_settings = SuperUserSettings()  # type: ignore
settings = Settings()  # type: ignore


# WARNING: CSRF IS OFF!
authx_config = AuthXConfig(
    JWT_SECRET_KEY=settings.JWT_SECRET_KEY,  # ваш секрет для JWT
    JWT_ALGORITHM="HS256",  # алгоритм подписи
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=30),  # жизнь access‑токена
    JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=15),  # жизнь refresh‑токена
    JWT_TOKEN_LOCATION=["cookies"],  # искать токены именно в куки
    JWT_COOKIE_SECURE=True,  # Secure-флаг для куки (HTTPS)
    JWT_COOKIE_SAMESITE="lax",  # SameSite‑политика
    JWT_COOKIE_CSRF_PROTECT=False,  # включить CSRF‑защиту
    JWT_ACCESS_COOKIE_NAME="access_token",
    JWT_REFRESH_COOKIE_NAME="refresh_token",
)


def get_db_url() -> str:
    return (
        f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@"
        f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )
