"""App settings, read from environment variables or the backend/.env file.

Secrets (like the database password) live in .env, which Git ignores.
The code only ever sees them through `settings`.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env, no matter which folder you run the app from
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE)

    # Example: postgresql+psycopg://event_app:PASSWORD@localhost:5432/event_companion
    database_url: str


settings = Settings()
