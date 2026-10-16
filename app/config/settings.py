from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str
    app_env: str
    app_version: str

    host: str
    port: int

    google_api_key: str

    gemini_model: str
    gemini_temperature: float
    gemini_max_retries: int

    # OIDC resource-server settings. They intentionally default to empty so
    # application configuration can load in development, while authentication
    # itself fails closed until all three values are configured.
    auth_jwt_issuer: str = ""
    auth_jwt_audience: str = ""
    auth_jwks_url: str = ""
    auth_chat_scope: str = "rwa:chat"
    # JWT_SECRET is retained as the environment variable name because it is
    # already used by the RWA application. Do not log this setting.
    jwt_secret: SecretStr | None = None
    auth_chat_roles: str = "investor"

    redis_url: str
    rwa_api_url: str

    log_level: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
