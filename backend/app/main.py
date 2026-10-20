from fastapi import Depends, FastAPI
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db import get_db
from app.routers import admin, public

app = FastAPI(title="Event Companion API")
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
