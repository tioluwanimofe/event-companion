"""Import booths (and their owners) from a spreadsheet, and make their QR codes.

A booth is matched by its name, so re-uploading updates it. The booth's
secret qr_token is created once and NEVER changed by an import, so QR codes
you've already printed keep working. To retire a leaked code, use the
"rotate QR" endpoint instead (ADR 0003, choice 3).
"""
import io

import segno
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.csv_utils import decode_csv, read_rows
from app.models import Booth, BoothOwner, Event
from app.people import PeopleBook
from app.schemas import BoothOut, PersonBrief, RowProblem, ScheduleImportReport

HEADER_ALIASES: dict[str, set[str]] = {
    "name": {"name", "booth", "booth_name", "organization", "organisation", "company", "exhibitor"},
    "description": {"description", "about"},
    "location_label": {"location", "location_label", "table", "booth_location", "where", "spot"},
    "preloaded_notes": {"notes", "preloaded_notes", "handout", "message", "attendee_notes",
                        "notes_for_attendees", "info_for_attendees"},
    "owner_names": {"owner", "owners", "owner_name", "owner_names", "contact", "contact_name"},
    "owner_emails": {"owner_email", "owner_emails", "contact_email", "contact_emails", "email"},
}

MAX_LENGTH = {"name": 200, "location_label": 200}
FIELDS = ("description", "location_label", "preloaded_notes")


def import_booths(db: Session, event: Event, raw: bytes) -> ScheduleImportReport:
    rows = read_rows(decode_csv(raw), HEADER_ALIASES, required=["name"])
    booths = {b.name.lower(): b for b in db.scalars(select(Booth).where(Booth.event_id == event.id))}
    people = PeopleBook(db, event)
    skipped: list[RowProblem] = []
    warnings: list[RowProblem] = []
    seen: dict[str, int] = {}
    mentioned: set[str] = set()
    created = updated = unchanged = rows_read = 0

    for row, v in rows:
        rows_read += 1
        name = v["name"]
        mentioned.add(name.lower())
        if not name:
            skipped.append(RowProblem(row=row, item=None, reason="missing booth name"))
            continue
        if name.lower() in seen:
            skipped.append(RowProblem(row=row, item=name, reason=f"same booth name as row {seen[name.lower()]}"))
            continue
        too_long = [f for f, limit in MAX_LENGTH.items() if len(v.get(f, "")) > limit]
        if too_long:
            skipped.append(RowProblem(row=row, item=name, reason=f"too long: {', '.join(too_long)}"))
            continue
        seen[name.lower()] = row

        details = {f: v.get(f) or None for f in FIELDS}
        booth = booths.get(name.lower())
        if booth is None:
            booth = Booth(event=event, name=name, **details)  # qr_token made here
            db.add(booth)
            booths[name.lower()] = booth
            created += 1
            changed = None
        else:
            changed = any(getattr(booth, f) != val for f, val in details.items())
            for f, val in details.items():
                setattr(booth, f, val)

        if "owner_names" in v or "owner_emails" in v:
            owners, problems = people.people_from_cells(
                v.get("owner_names"), v.get("owner_emails"), "booth_owner")
            warnings += [RowProblem(row=row, item=name, reason=p) for p in problems]
            db.flush()
            current = {link.user_id for link in booth.owners}
            wanted = {u.id for u in owners}
            if current != wanted:
                booth.owners[:] = [l for l in booth.owners if l.user_id in wanted]
                for uid in wanted - current:
                    booth.owners.append(BoothOwner(user_id=uid))
                changed = changed if changed is None else True

        if changed is True:
            updated += 1
        elif changed is False:
            unchanged += 1

    for key, booth in booths.items():
        if key not in mentioned:
            warnings.append(RowProblem(row=0, item=booth.name,
                                       reason="in the database but not in this file (kept, not deleted)"))
    db.commit()
    return ScheduleImportReport(event_slug=event.slug, rows_read=rows_read, created=created,
                                updated=updated, unchanged=unchanged,
                                people_created=people.created, skipped=skipped, warnings=warnings)


# QR codes -----------------------------------------------------------------

def qr_link(booth: Booth) -> str:
    """What's inside the printed code: a link that opens the attendee app.
    Only the random token is in it, never the booth's id."""
    return f"{settings.app_base_url.rstrip('/')}/scan/{booth.qr_token}"


def qr_png(booth: Booth) -> bytes:
    buffer = io.BytesIO()
    # error="h": still scans with up to ~30% of the code damaged or covered
    segno.make(qr_link(booth), error="h").save(buffer, kind="png", scale=12, border=4)
    return buffer.getvalue()


def qr_svg(booth: Booth) -> str:
    # omitsize=True adds a viewBox, so CSS can resize the code without cropping it
    return segno.make(qr_link(booth), error="h").svg_inline(border=4, omitsize=True)


def booth_out(booth: Booth) -> BoothOut:
    return BoothOut(
        id=booth.id, name=booth.name, description=booth.description,
        location_label=booth.location_label, preloaded_notes=booth.preloaded_notes,
        owners=[PersonBrief(name=f"{o.user.first_name} {o.user.last_name}".strip(),
                            email=o.user.email) for o in booth.owners],
        qr_link=qr_link(booth), qr_image=f"/admin/booths/{booth.id}/qr.png",
    )
