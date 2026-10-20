"""Admin endpoints: set up an event and load its registrants.

⚠️ No login yet. These are for local development only. Before the app goes
online they must be locked to admins (comes with the Google sign-in ADR).
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Event, EventRole, User
from app.registrants import CsvFormatError, import_registrants
from app.schemas import AttendeeOut, EventCreate, EventOut, ImportReport

router = APIRouter(prefix="/admin", tags=["Admin (no login yet, local use only)"])

MAX_CSV_BYTES = 5 * 1024 * 1024  # 5 MB is tens of thousands of registrants


def get_event_or_404(db: Session, slug: str) -> Event:
    event = db.scalar(select(Event).where(Event.slug == slug))
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No event with slug '{slug}'")
    return event


@router.post("/events", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(body: EventCreate, db: Session = Depends(get_db)):
    """Create an event. The slug is its short name in links."""
    if db.scalar(select(Event).where(Event.slug == body.slug)):
        raise HTTPException(status.HTTP_409_CONFLICT, f"'{body.slug}' already exists")
    event = Event(**body.model_dump())
    db.add(event)
    db.commit()
    return event


@router.get("/events", response_model=list[EventOut])
def list_events(db: Session = Depends(get_db)):
    return db.scalars(select(Event).order_by(Event.starts_at)).all()


@router.post("/events/{slug}/registrants/import", response_model=ImportReport)
def import_registrants_csv(slug: str, file: UploadFile = File(..., description="CSV export from the CRM"),
                           db: Session = Depends(get_db)):
    """Upload the registrants CSV. Safe to run again with an updated file."""
    event = get_event_or_404(db, slug)
    raw = file.file.read(MAX_CSV_BYTES + 1)
    if len(raw) > MAX_CSV_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "File is larger than 5 MB")
    try:
        return import_registrants(db, event, raw)
    except CsvFormatError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))


@router.get("/events/{slug}/attendees", response_model=list[AttendeeOut])
def list_attendees(slug: str, db: Session = Depends(get_db)):
    """Everyone with the attendee role at this event, A to Z by last name."""
    event = get_event_or_404(db, slug)
    return db.scalars(
        select(User)
        .join(EventRole, EventRole.user_id == User.id)
        .where(EventRole.event_id == event.id, EventRole.role == "attendee")
        .order_by(User.last_name, User.first_name)
    ).all()
