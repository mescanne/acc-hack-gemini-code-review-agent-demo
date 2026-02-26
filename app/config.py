from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Cloud Run environment variables
    PORT: int = 8080
    HOST: str = "0.0.0.0"

    # Database settings
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "appdb"
    DB_USER: str = "appuser"
    DB_PASSWORD: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
