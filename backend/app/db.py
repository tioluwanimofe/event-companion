"""Database connection: one engine for the whole app, one session per request."""
from collections.abc import Iterator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# The engine manages a pool of connections to Postgres.
# pool_pre_ping checks a connection is still alive before using it.
engine = create_engine(settings.database_url, pool_pre_ping=True)

# A factory that hands out Sessions. A Session is one "conversation"
# with the database: you add/change objects, then commit them together.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


# Predictable names for indexes and constraints, e.g. "uq_users_email".
# Alembic needs exact names to change or drop a constraint in a later
# migration; without this, Postgres would invent names for us.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Every table class in models.py inherits from this."""
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: open a session for one request, always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
