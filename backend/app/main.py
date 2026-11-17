import logging
import secrets

from fastapi import Depends, FastAPI
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.db import get_db
from app.routers import admin, auth, public

app = FastAPI(title="Event Companion API")

secret_key = settings.session_secret_key
if not secret_key:
    logging.getLogger(__name__).warning(
        "SESSION_SECRET_KEY is empty: using a random one, so everyone is signed out "
        "whenever the API restarts. Set it in backend/.env.")
    secret_key = secrets.token_urlsafe(48)

# The session cookie: signed (can't be forged), HttpOnly (JavaScript can't read it),
# SameSite=Lax (other websites can't make your browser send it with a POST).
app.add_middleware(
    SessionMiddleware,
    secret_key=secret_key,
    session_cookie="ec_session",
    max_age=14 * 24 * 60 * 60,  # stay signed in for 14 days
    same_site="lax",
    https_only=settings.session_cookie_secure,
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(public.router)


@app.get("/health")
def health():
    """Is the API running?"""
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    """Can the API reach Postgres, and which tables exist?"""
    db.execute(text("SELECT 1"))
    tables = sorted(inspect(db.get_bind()).get_table_names())
    return {"database": "ok", "tables": tables}
