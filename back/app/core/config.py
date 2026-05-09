from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "InterHack API"
    database_url: str = "sqlite+aiosqlite:///./app.db"
    frontend_origin: str = "http://localhost:5173"
    jwt_secret_key: str = "change-me-in-development"
    access_token_expire_minutes: int = 1440
    gemini_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
