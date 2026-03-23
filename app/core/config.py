from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application runtime settings."""

    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(default="sqlite+aiosqlite:///./phone_validator.db", alias="DATABASE_URL")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_timeout_seconds: int = Field(default=20, alias="OPENAI_TIMEOUT_SECONDS")
    webhook_token: str = Field(default="", alias="WEBHOOK_TOKEN")
    public_host: str = Field(default="localhost", alias="PUBLIC_HOST")
    nginx_port: int = Field(default=8005, alias="NGINX_PORT")
    ip_geo_enabled: bool = Field(default=True, alias="IP_GEO_ENABLED")
    ip_geo_default_country: str = Field(default="US", alias="IP_GEO_DEFAULT_COUNTRY")
    ip_geo_cache_ttl_seconds: int = Field(default=86400, alias="IP_GEO_CACHE_TTL_SECONDS")
    ip_geo_timeout_seconds: float = Field(default=3.0, alias="IP_GEO_TIMEOUT_SECONDS")
    ipapi_token: str = Field(default="", alias="IPAPI_TOKEN")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
