"""Booth scans: the lead exchange, the heart of the app.

The flow (Tio's decision, 2026-11-18: one-tap consent, profile + email):

1. The attendee's phone camera reads the booth's printed QR code, which opens
   {APP_BASE_URL}/scan/{qr_token}.
2. GET  /scan/{token}   shows WHICH booth this is. Public: nothing is shared yet.
3. The attendee signs in (if they aren't already) and taps
   "Share my profile with <booth>".
4. POST /scan/{token}   saves the visit. Only now does the booth see them, and
   only now does the attendee get the booth's preloaded notes.
5. Booth owners see their leads at /my-booths/{booth_id}/leads (or as a CSV).

Nothing is shared by just opening a link. A forwarded or screenshotted code
can't share anyone's profile without that person tapping the button.
"""
import csv
import io
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth import current_user, is_event_admin, optional_user
from app.db import get_db
from app.models import Booth, BoothOwner, BoothScan, Event, EventRole, User
from app.schemas import LeadOut, MyBoothOut, ScanPreview, ScanResult, VisitOut

router = APIRouter(tags=["Booth visits"])


def booth_for_token(db: Session, token: str) -> Booth:
    booth = db.scalar(select(Booth).where(Booth.qr_token == token))
    if booth is None:
        # Also what a ROTATED (retired) code gets: the old secret matches nothing.
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "This QR code isn't active. Ask the booth for their current code.")
    return booth


def scan_of(db: Session, booth_id: uuid.UUID, user_id: uuid.UUID) -> BoothScan | None:
    return db.scalar(select(BoothScan).where(BoothScan.booth_id == booth_id,
                                             BoothScan.user_id == user_id))


@router.get("/scan/{token}", response_model=ScanPreview)
def preview_scan(token: str, user: User | None = Depends(optional_user),
                 db: Session = Depends(get_db)):
    """What the attendee sees right after scanning: which booth, and whether they've
    already shared. Works without signing in. Shares nothing."""
    booth = booth_for_token(db, token)
    event = db.get(Event, booth.event_id)
    existing = scan_of(db, booth.id, user.id) if user else None
    return ScanPreview(
        booth_name=booth.name, description=booth.description,
        location_label=booth.location_label, event_name=event.name,
        signed_in=user is not None,
        already_shared_at=existing.scanned_at if existing else None,
    )


@router.post("/scan/{token}", response_model=ScanResult)
def share_with_booth(token: str, user: User = Depends(current_user),
                     db: Session = Depends(get_db)):
    """The "Share my profile" button. Safe to tap twice: still one lead."""
    booth = booth_for_token(db, token)

    # Only people registered for THIS event (any role) can share with its booths.
    registered = db.scalar(select(EventRole.user_id).where(
        EventRole.event_id == booth.event_id, EventRole.user_id == user.id).limit(1))
    if registered is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "You're not on the registration list for this event. "
                            "Please check in at the registration desk.")

    if db.scalar(select(BoothOwner.user_id).where(
            BoothOwner.booth_id == booth.id, BoothOwner.user_id == user.id)) is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This is your own booth.")

    # 🧠 Race-proof saving. A double-tap can send two requests at the SAME moment.
    # "Check if it exists, then insert" can let both through (both check, both see
    # nothing, both insert). Instead we ask Postgres to do it in one atomic step:
    # INSERT ... ON CONFLICT DO NOTHING. The UNIQUE(booth_id, user_id) rule from
    # ADR 0003 makes the second insert a no-op. RETURNING tells us if WE created it.
    created_id = db.scalar(
        insert(BoothScan)
        .values(id=uuid.uuid4(), booth_id=booth.id, user_id=user.id, via="qr")
        .on_conflict_do_nothing(index_elements=["booth_id", "user_id"])
        .returning(BoothScan.id)
    )
    db.commit()
    scan = scan_of(db, booth.id, user.id)
    return ScanResult(booth_name=booth.name, preloaded_notes=booth.preloaded_notes,
                      location_label=booth.location_label, shared_at=scan.scanned_at,
                      first_time=created_id is not None)


@router.get("/me/booth-visits", response_model=list[VisitOut])
def my_booth_visits(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """The attendee's "passport": every booth they've shared with, and the notes they got."""
    rows = db.execute(
        select(Booth, BoothScan.scanned_at, Event.slug)
        .join(BoothScan, BoothScan.booth_id == Booth.id)
        .join(Event, Event.id == Booth.event_id)
        .where(BoothScan.user_id == user.id)
        .order_by(BoothScan.scanned_at.desc())
    ).all()
    return [VisitOut(event_slug=slug, booth_name=b.name, location_label=b.location_label,
                     preloaded_notes=b.preloaded_notes, shared_at=at) for b, at, slug in rows]


# Booth owners -------------------------------------------------------------------

def require_booth_lead_access(booth_id: uuid.UUID, user: User = Depends(current_user),
                              db: Session = Depends(get_db)) -> Booth:
    """Leads are visible to that booth's owners, and to admins of its event. Nobody else."""
    booth = db.get(Booth, booth_id)
    if booth is not None:
        owns = db.scalar(select(BoothOwner.user_id).where(
            BoothOwner.booth_id == booth.id, BoothOwner.user_id == user.id)) is not None
        if owns or is_event_admin(db, user, booth.event_id):
            return booth
    # Same answer for "no such booth" and "not yours": don't reveal which booths exist.
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Only this booth's owners can see its leads")


@router.get("/my-booths", response_model=list[MyBoothOut])
def my_booths(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Booths I run, with how many people have shared their profile with each."""
    lead_count = (select(func.count()).select_from(BoothScan)
                  .where(BoothScan.booth_id == Booth.id).scalar_subquery())
    rows = db.execute(
        select(Booth, Event.slug, lead_count)
        .join(BoothOwner, BoothOwner.booth_id == Booth.id)
        .join(Event, Event.id == Booth.event_id)
        .where(BoothOwner.user_id == user.id)
        .order_by(Booth.name)
    ).all()
    return [MyBoothOut(id=b.id, event_slug=slug, name=b.name, location_label=b.location_label,
                       lead_count=n, leads_csv=f"/my-booths/{b.id}/leads.csv")
            for b, slug, n in rows]


def booth_leads(db: Session, booth: Booth) -> list[LeadOut]:
    rows = db.execute(
        select(User, BoothScan.scanned_at)
        .join(BoothScan, BoothScan.user_id == User.id)
        .where(BoothScan.booth_id == booth.id)
        .order_by(BoothScan.scanned_at.desc())
    ).all()
    return [LeadOut(first_name=u.first_name, last_name=u.last_name, email=u.email,
                    company=u.company, job_title=u.job_title, is_student=u.is_student,
                    university=u.university, major=u.major, shared_at=at) for u, at in rows]


@router.get("/my-booths/{booth_id}/leads", response_model=list[LeadOut])
def leads(booth: Booth = Depends(require_booth_lead_access), db: Session = Depends(get_db)):
    """Everyone who tapped "Share my profile" at this booth, newest first."""
    return booth_leads(db, booth)


@router.get("/my-booths/{booth_id}/leads.csv", response_class=Response,
            responses={200: {"content": {"text/csv": {}}}})
def leads_csv(booth: Booth = Depends(require_booth_lead_access), db: Session = Depends(get_db)):
    """The same leads as a spreadsheet, for the booth's own CRM or follow-up emails."""
    columns = ["first_name", "last_name", "email", "company", "job_title",
               "is_student", "university", "major", "shared_at"]
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=columns)
    writer.writeheader()
    for lead in booth_leads(db, booth):
        row = lead.model_dump()
        row["is_student"] = {True: "yes", False: "no", None: ""}[row["is_student"]]
        row["shared_at"] = row["shared_at"].isoformat(timespec="minutes")
        writer.writerow(row)
    # utf-8-sig adds the BOM, so Excel shows names like "Sofía" correctly
    safe_name = "".join(c if c.isalnum() else "-" for c in booth.name).strip("-").lower()
    stamp = datetime.now().strftime("%Y%m%d")
    return Response(out.getvalue().encode("utf-8-sig"), media_type="text/csv",
                    headers={"Content-Disposition":
                             f'attachment; filename="leads-{safe_name}-{stamp}.csv"'})
