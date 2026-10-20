"""Database tables for v1. See docs/decisions/0003-v1-data-model.md for the why.

Each class = one table. Each `Mapped[...]` attribute = one column.
`Mapped[str | None]` means the column may be empty (NULL).
"""
import secrets
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# Allowed values, enforced by the database with CHECK constraints.
# (Plain text + CHECK is easier to change later than a Postgres ENUM type.)
ROLES = ("admin", "booth_owner", "speaker", "attendee")
ROLE_SOURCES = ("csv_import", "invited", "self")
SCAN_METHODS = ("qr", "manual")
SESSION_KINDS = ("keynote", "breakout", "panel", "meal", "networking", "other")


def _in(column: str, values: tuple[str, ...]) -> str:
    """Builds SQL like: role IN ('admin', 'speaker')"""
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


def new_qr_token() -> str:
    """32 random URL-safe characters. Unguessable (ADR 0003, choice 3)."""
    return secrets.token_urlsafe(24)


# Reusable column helpers --------------------------------------------------

def uuid_pk() -> Mapped[uuid.UUID]:
    # Python makes the UUID (so the phone/offline queue could too);
    # Postgres can also make one if a row is inserted by hand in SQL.
    return mapped_column(primary_key=True, default=uuid.uuid4,
                         server_default=func.gen_random_uuid())


def created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


# People -------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        # Emails are stored lower-case so "Tio@X.com" and "tio@x.com" match.
        CheckConstraint("email = lower(email)", name="email_lowercase"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True)
    # Google's permanent ID for this person. Empty until first Google sign-in
    # (CSV-imported registrants exist before they ever sign in).
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))

    # Profile shared with a booth when this person scans its QR code
    company: Mapped[str | None] = mapped_column(String(200))
    job_title: Mapped[str | None] = mapped_column(String(200))
    is_student: Mapped[bool | None]
    university: Mapped[str | None] = mapped_column(String(200))
    major: Mapped[str | None] = mapped_column(String(200))

    created_at: Mapped[datetime] = created_at()

    roles: Mapped[list["EventRole"]] = relationship(back_populates="user")


# The event and its agenda -------------------------------------------------

class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(100), unique=True)  # cyberdatacon-2027
    name: Mapped[str] = mapped_column(String(200))
    venue: Mapped[str | None] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(64), default="America/Chicago")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    roles: Mapped[list["EventRole"]] = relationship(back_populates="event")
    rooms: Mapped[list["Room"]] = relationship(back_populates="event")
    sessions: Mapped[list["Session"]] = relationship(back_populates="event")
    booths: Mapped[list["Booth"]] = relationship(back_populates="event")


class EventRole(Base):
    """Who is what at which event. One person can hold several roles."""
    __tablename__ = "event_roles"
    __table_args__ = (
        CheckConstraint(_in("role", ROLES), name="role_valid"),
        CheckConstraint(_in("source", ROLE_SOURCES), name="source_valid"),
    )

    # Three-column primary key: the same (event, user, role) can't repeat.
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), primary_key=True)
    source: Mapped[str] = mapped_column(String(20), default="self")
    created_at: Mapped[datetime] = created_at()

    event: Mapped[Event] = relationship(back_populates="roles")
    user: Mapped[User] = relationship(back_populates="roles")


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (UniqueConstraint("event_id", "name"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))          # Ezell 301
    building: Mapped[str | None] = mapped_column(String(100))

    event: Mapped[Event] = relationship(back_populates="rooms")


class Session(Base):
    """A talk, panel, meal etc. on the agenda.

    Careful: this is an *event* session. It has nothing to do with a
    SQLAlchemy database Session (app.db). Same word, different thing.
    """
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint(_in("kind", SESSION_KINDS), name="kind_valid"),
        CheckConstraint("ends_at > starts_at", name="ends_after_start"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True)
    # Rooms are "fluid", so a session can exist before it has a room.
    room_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("rooms.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    track: Mapped[str | None] = mapped_column(String(100))  # Healthcare, IoT...
    kind: Mapped[str] = mapped_column(String(20), default="breakout")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    event: Mapped[Event] = relationship(back_populates="sessions")
    room: Mapped[Room | None] = relationship()
    speakers: Mapped[list["SessionSpeaker"]] = relationship(back_populates="session")


class SessionSpeaker(Base):
    __tablename__ = "session_speakers"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    session: Mapped[Session] = relationship(back_populates="speakers")
    user: Mapped[User] = relationship()


# Booths and the lead exchange --------------------------------------------

class Booth(Base):
    __tablename__ = "booths"

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    # What the attendee receives after scanning
    preloaded_notes: Mapped[str | None] = mapped_column(Text)
    location_label: Mapped[str | None] = mapped_column(String(200))  # 3rd floor, table 4
    # The secret inside the printed QR code. Rotate it if a code leaks.
    qr_token: Mapped[str] = mapped_column(String(64), unique=True, default=new_qr_token)

    event: Mapped[Event] = relationship(back_populates="booths")
    owners: Mapped[list["BoothOwner"]] = relationship(back_populates="booth")
    scans: Mapped[list["BoothScan"]] = relationship(back_populates="booth")


class BoothOwner(Base):
    __tablename__ = "booth_owners"

    booth_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("booths.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    booth: Mapped[Booth] = relationship(back_populates="owners")
    user: Mapped[User] = relationship()


class BoothScan(Base):
    """One lead: this attendee visited this booth.

    Unique per (booth, user), so a retried scan from the offline queue
    can't create a duplicate lead (idempotent, ADR 0003 choice 4).
    """
    __tablename__ = "booth_scans"
    __table_args__ = (
        UniqueConstraint("booth_id", "user_id"),
        CheckConstraint(_in("via", SCAN_METHODS), name="via_valid"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    booth_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("booths.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scanned_at: Mapped[datetime] = created_at()
    via: Mapped[str] = mapped_column(String(10), default="qr")

    booth: Mapped[Booth] = relationship(back_populates="scans")
    user: Mapped[User] = relationship()


class CheckIn(Base):
    """Arrived at the event. One per person per event."""
    __tablename__ = "check_ins"
    __table_args__ = (CheckConstraint(_in("via", SCAN_METHODS), name="via_valid"),)

    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    checked_in_at: Mapped[datetime] = created_at()
    via: Mapped[str] = mapped_column(String(10), default="qr")
