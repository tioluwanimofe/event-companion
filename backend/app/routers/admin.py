"""Admin endpoints: set up an event and load its registrants.

⚠️ No login yet. These are for local development only. Before the app goes
online they must be locked to admins (comes with the Google sign-in ADR).
"""
import html
import secrets
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.agenda import import_agenda
from app.booths import booth_out, import_booths, qr_png, qr_svg
from app.csv_utils import CsvFormatError
from app.models import Booth, BoothOwner, Event, EventRole, User
from app.registrants import import_registrants
from app.schemas import (AgendaImportReport, AttendeeOut, BoothOut, EventCreate, EventOut,
                         ImportReport, ScheduleImportReport)

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
    return run_import(import_registrants, db, event, file)


def run_import(importer, db: Session, event: Event, file: UploadFile):
    """Shared by every CSV upload: size limit + turn file problems into a 422."""
    raw = file.file.read(MAX_CSV_BYTES + 1)
    if len(raw) > MAX_CSV_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "File is larger than 5 MB")
    try:
        return importer(db, event, raw)
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


# Agenda --------------------------------------------------------------------

@router.post("/events/{slug}/agenda/import", response_model=AgendaImportReport)
def import_agenda_csv(slug: str, file: UploadFile = File(..., description="Agenda spreadsheet saved as CSV"),
                      db: Session = Depends(get_db)):
    """Upload the agenda. Times are local to the event. Re-upload to update."""
    return run_import(import_agenda, db, get_event_or_404(db, slug), file)


# Booths --------------------------------------------------------------------

def get_booth_or_404(db: Session, booth_id: uuid.UUID) -> Booth:
    booth = db.get(Booth, booth_id)
    if booth is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No booth with that id")
    return booth


def event_booths(db: Session, event: Event) -> list[Booth]:
    return db.scalars(
        select(Booth).where(Booth.event_id == event.id).order_by(Booth.name)
        .options(selectinload(Booth.owners).selectinload(BoothOwner.user))
    ).all()


@router.post("/events/{slug}/booths/import", response_model=ScheduleImportReport)
def import_booths_csv(slug: str, file: UploadFile = File(..., description="Booths spreadsheet saved as CSV"),
                      db: Session = Depends(get_db)):
    """Upload booths and their owners. Re-upload to update; QR codes never change."""
    return run_import(import_booths, db, get_event_or_404(db, slug), file)


@router.get("/events/{slug}/booths", response_model=list[BoothOut])
def list_booths(slug: str, db: Session = Depends(get_db)):
    return [booth_out(b) for b in event_booths(db, get_event_or_404(db, slug))]


@router.get("/booths/{booth_id}/qr.png", response_class=Response,
            responses={200: {"content": {"image/png": {}}}})
def booth_qr_png(booth_id: uuid.UUID, db: Session = Depends(get_db)):
    """The booth's QR code as an image."""
    booth = get_booth_or_404(db, booth_id)
    return Response(qr_png(booth), media_type="image/png",
                    headers={"Content-Disposition": f'inline; filename="qr-{booth.name}.png"'})


@router.post("/booths/{booth_id}/rotate-qr", response_model=BoothOut)
def rotate_booth_qr(booth_id: uuid.UUID, db: Session = Depends(get_db)):
    """Give the booth a new secret. Old printed codes stop working: reprint!"""
    booth = get_booth_or_404(db, booth_id)
    booth.qr_token = secrets.token_urlsafe(24)
    db.commit()
    return booth_out(booth)


@router.get("/events/{slug}/booths/qr-sheet", response_class=HTMLResponse)
def booth_qr_sheet(slug: str, db: Session = Depends(get_db)):
    """A printable page with every booth's QR code. Open it in a new tab, then Ctrl+P."""
    event = get_event_or_404(db, slug)
    cards = "".join(
        f"""<section class="card">
              <h2>{html.escape(b.name)}</h2>
              <p class="where">{html.escape(b.location_label or "")}</p>
              {qr_svg(b)}
              <p class="hint">Scan with your phone camera to check in at this booth</p>
            </section>"""
        for b in event_booths(db, event)
    ) or "<p>No booths yet. Upload the booths CSV first.</p>"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{html.escape(event.name)} · Booth QR codes</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 24px; color: #15191c; background: #fff; }}
  header h1 {{ margin: 0 0 4px; }} header p {{ margin: 0 0 24px; color: #555; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }}
  .card {{ border: 2px solid #15191c; border-radius: 12px; padding: 16px; text-align: center;
           break-inside: avoid; page-break-inside: avoid; }}
  .card h2 {{ margin: 0; font-size: 22px; }} .where {{ margin: 4px 0 8px; color: #d4430e; font-weight: 600; }}
  .card svg {{ width: 200px; height: 200px; }} .hint {{ font-size: 12px; color: #555; margin: 8px 0 0; }}
  @media print {{ header p {{ display: none; }} body {{ margin: 0; }} }}
</style></head><body>
<header><h1>{html.escape(event.name)}: booth QR codes</h1>
<p>Press Ctrl+P to print. Each code holds a secret link; if one leaks, rotate it and reprint.</p></header>
<div class="grid">{cards}</div></body></html>"""
