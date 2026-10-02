from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Reads from environment variables, falling back to .env (or ../.env
    when running pytest/alembic from the backend/ folder)."""

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_name: str = "Warden"
    cors_origins: list[str] = ["http://localhost:3000"]
    database_url: str = "postgresql+psycopg://warden:warden@localhost:5432/warden"
    github_token: str = ""
    github_app_id: str = ""
    github_app_private_key: str = ""
    github_app_client_secret: str = ""
    jwt_secret: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    encryption_key: str = "5qW0zXgJ_L4JnHzKpQtV9m2-bE8cDfRsZ0xY1pQrT2s="


settings = Settings()
