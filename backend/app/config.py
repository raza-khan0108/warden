from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Reads from environment variables, falling back to .env (or ../.env
    when running pytest/alembic from the backend/ folder)."""

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_name: str = "Warden"
    cors_origins: list[str] = ["http://localhost:3000"]
    database_url: str = "postgresql+psycopg://warden:warden@localhost:5432/warden"


settings = Settings()
