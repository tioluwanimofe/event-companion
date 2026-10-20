"""App settings, read from environment variables or the backend/.env file.

Secrets (like the database password) live in .env, which Git ignores.
The code only ever sees them through `settings`.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env, no matter which folder you run the app from
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    # extra="ignore": other lines in .env (like TEST_DATABASE_URL) are not app settings
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    # Example: postgresql+psycopg://event_app:PASSWORD@localhost:5432/event_companion
    database_url: str

    # Where the attendee app lives. Booth QR codes point here:
    # {app_base_url}/scan/{qr_token}. Becomes https://app.cyberdatacon.com later.
    app_base_url: str = "http://localhost:5173"


settings = Settings()
