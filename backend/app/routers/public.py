"""Public endpoints: what any attendee (or the event website) can read.

No emails or private details here. Speakers show name and company only.
"""
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Event, Session as AgendaSession, SessionSpeaker
from app.schemas import AgendaOut, SessionOut, SpeakerOut

router = APIRouter(prefix="/events", tags=["Public"])


@router.get("/{slug}/agenda", response_model=AgendaOut)
def get_agenda(slug: str, db: Session = Depends(get_db)):
    """The event's sessions in time order, with times in the event's local time."""
    event = db.scalar(select(Event).where(Event.slug == slug))
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No event with slug '{slug}'")
    local = ZoneInfo(event.timezone)
    sessions = db.scalars(
        select(AgendaSession).where(AgendaSession.event_id == event.id)
        .order_by(AgendaSession.starts_at, AgendaSession.title)
        .options(selectinload(AgendaSession.room),
                 selectinload(AgendaSession.speakers).selectinload(SessionSpeaker.user))
    ).all()
    return AgendaOut(
        event_slug=event.slug, event_name=event.name, timezone=event.timezone,
        sessions=[SessionOut(
            id=s.id, title=s.title, description=s.description, track=s.track, kind=s.kind,
            room=s.room.name if s.room else None, building=s.room.building if s.room else None,
            # Stored as UTC; shown as Nashville time (ADR 0003, choice 6)
            starts_at=s.starts_at.astimezone(local), ends_at=s.ends_at.astimezone(local),
            speakers=[SpeakerOut(name=f"{l.user.first_name} {l.user.last_name}".strip(),
                                 company=l.user.company) for l in s.speakers],
        ) for s in sessions],
    )
