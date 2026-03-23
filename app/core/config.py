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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
