"""App settings, read from environment variables or the backend/.env file.

Secrets (like the database password) live in .env, which Git ignores.
The code only ever sees them through `settings`.
"""
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env, no matter which folder you run the app from
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    # extra="ignore": other lines in .env (like TEST_DATABASE_URL) are not app settings
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    # Example: postgresql+psycopg://event_app:PASSWORD@localhost:5432/event_companion
    # A plain postgresql://... link (what Neon and Render hand you) works too.
    database_url: str

    # Where the attendee app lives. Booth QR codes point here:
    # {app_base_url}/scan/{qr_token}. Becomes https://app.cyberdatacon.com later.
    app_base_url: str = "http://localhost:5173"

    # --- Sign-in (ADR 0004) -------------------------------------------------
    # From Google Cloud Console -> APIs & Services -> Credentials -> OAuth client.
    # Empty = sign-in is switched off (the login link explains what's missing).
    google_client_id: str = ""
    google_client_secret: str = ""

    # Signs the session cookie so nobody can forge "I am user X".
    # Empty = a random key is made at startup, which signs everyone out on restart.
    session_secret_key: str = ""

    # Send the cookie over HTTPS only. False for http://127.0.0.1 on your PC,
    # True as soon as the API is online.
    session_cookie_secure: bool = False

    # Where to send people after they sign in. The API docs are handy until React exists.
    after_login_url: str = "/api/docs"

    # The exact address Google sends people back to after sign-in. Leave it empty on
    # your PC (it's worked out from the request). Online, set it to
    # https://<your-netlify-site>/api/auth/google/callback: behind Netlify's proxy,
    # the request looks like it came to the Render address, which Google doesn't know.
    oauth_callback_url: str = ""

    # Comma-separated. These people can manage every event, even before any
    # roles exist (that's how the very first admin gets in).
    admin_emails: str = ""

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, url: str) -> str:
        """Hosting dashboards give postgres:// or postgresql:// links. SQLAlchemy needs
        to be told which Python driver to use, so we add "+psycopg" for you."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url.removeprefix(prefix)
        return url

    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}

    @property
    def google_sign_in_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)


settings = Settings()
