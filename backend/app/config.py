from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Reads from environment variables, falling back to .env (or ../.env
    when running pytest from the backend/ folder)."""

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_name: str = "Warden"
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
