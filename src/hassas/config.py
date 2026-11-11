from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

    app_name: str = "My Project"
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
