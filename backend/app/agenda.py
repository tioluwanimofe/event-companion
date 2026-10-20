"""Import the agenda (sessions, rooms, speakers) from a spreadsheet.

The organizer writes times the way humans do ("9:30 AM") in the event's
local time. We attach the event's time zone, and Postgres stores UTC
(ADR 0003, choice 6). The app shows local time again when displaying.

Re-uploading is safe: a session is matched by its title, so changing the
time or room in the sheet and uploading again UPDATES that session.
The sheet is the source of truth for agenda details: a blank room cell
means "no room yet". Sessions missing from the file are kept, not deleted
(you'll see a warning), so nothing disappears by accident.
"""
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.csv_utils import decode_csv, local_to_aware, parse_date, parse_time, read_rows
from app.models import Event, Room, Session, SessionSpeaker
from app.people import PeopleBook
from app.schemas import AgendaImportReport, RowProblem

HEADER_ALIASES: dict[str, set[str]] = {
    "title": {"title", "session", "session_title", "session_name", "talk"},
    "date": {"date", "day"},
    "start": {"start", "start_time", "starts", "starts_at", "from", "begins", "time"},
    "end": {"end", "end_time", "ends", "ends_at", "to", "until"},
    "room": {"room", "location", "room_name"},
    "building": {"building"},
    "track": {"track", "topic", "stream"},
    "kind": {"kind", "type", "session_type", "format"},
    "description": {"description", "abstract", "details", "summary"},
    "speaker_names": {"speaker", "speakers", "speaker_name", "speaker_names", "presenter", "presenters"},
    "speaker_emails": {"speaker_email", "speaker_emails", "presenter_email", "presenter_emails"},
}

# Words organizers actually write in a "type" column -> our allowed kinds
KIND_WORDS = {
    "keynote": "keynote",
    "breakout": "breakout", "talk": "breakout", "session": "breakout", "workshop": "breakout",
    "panel": "panel",
    "meal": "meal", "breakfast": "meal", "lunch": "meal", "dinner": "meal", "food": "meal",
    "networking": "networking", "mixer": "networking", "reception": "networking",
    "other": "other", "welcome": "other", "closing": "other", "break": "other",
}

MAX_LENGTH = {"title": 300, "room": 100, "building": 100, "track": 100}


def import_agenda(db: DbSession, event: Event, raw: bytes) -> AgendaImportReport:
    rows = read_rows(decode_csv(raw), HEADER_ALIASES, required=["title", "start", "end"])

    # Load what's already there, once.
    sessions = {s.title.lower(): s for s in db.scalars(
        select(Session).where(Session.event_id == event.id))}
    rooms = {r.name.lower(): r for r in db.scalars(select(Room).where(Room.event_id == event.id))}
    people = PeopleBook(db, event)
    # If the sheet has no date column, sessions are on the event's (local) start day.
    event_day = event.starts_at.astimezone(ZoneInfo(event.timezone)).date()

    skipped: list[RowProblem] = []
    warnings: list[RowProblem] = []
    seen_titles: dict[str, int] = {}
    mentioned: set[str] = set()  # every title in the file, even rows we skip
    created = updated = unchanged = rooms_created = rows_read = 0

    for row, v in rows:
        rows_read += 1
        title = v["title"]
        mentioned.add(title.lower())

        def skip(reason: str) -> None:
            skipped.append(RowProblem(row=row, item=title or None, reason=reason))

        def warn(reason: str) -> None:
            warnings.append(RowProblem(row=row, item=title or None, reason=reason))

        # --- check the row ---------------------------------------------------
        if not title:
            skip("missing title")
            continue
        if title.lower() in seen_titles:
            skip(f"same title as row {seen_titles[title.lower()]}: give each session its own title")
            continue
        too_long = [f for f, limit in MAX_LENGTH.items() if len(v.get(f, "")) > limit]
        if too_long:
            skip(f"too long: {', '.join(too_long)}")
            continue
        try:
            day = parse_date(v["date"]) if v.get("date") else event_day
            starts_at = local_to_aware(day, parse_time(v["start"]), event.timezone)
            ends_at = local_to_aware(day, parse_time(v["end"]), event.timezone)
        except ValueError as error:
            skip(str(error))
            continue
        if ends_at <= starts_at:
            skip("ends before it starts")
            continue
        if not (event.starts_at <= starts_at and ends_at <= event.ends_at):
            warn("outside the event's start/end times")

        kind_word = v.get("kind", "").lower()
        kind = KIND_WORDS.get(kind_word, "breakout" if not kind_word else None)
        if kind is None:
            warn(f"type '{v['kind']}' not recognised, saved as 'other'")
            kind = "other"
        seen_titles[title.lower()] = row

        # --- room: created the first time it's mentioned ---------------------
        room = None
        if v.get("room"):
            room = rooms.get(v["room"].lower())
            if room is None:
                room = Room(event=event, name=v["room"], building=v.get("building") or None)
                db.add(room)
                rooms[room.name.lower()] = room
                rooms_created += 1
            elif v.get("building") and room.building != v["building"]:
                room.building = v["building"]

        # --- the session itself ----------------------------------------------
        details = dict(description=v.get("description") or None, track=v.get("track") or None,
                       kind=kind, starts_at=starts_at, ends_at=ends_at, room=room)
        session = sessions.get(title.lower())
        if session is None:
            session = Session(event=event, title=title, **details)
            db.add(session)
            sessions[title.lower()] = session
            created += 1
            changed = None  # counted as created
        else:
            changed = any(getattr(session, k) != val for k, val in details.items())
            for k, val in details.items():
                setattr(session, k, val)

        # --- speakers: only touched if the sheet has a speaker column ----------
        if "speaker_names" in v or "speaker_emails" in v:
            speakers, problems = people.people_from_cells(
                v.get("speaker_names"), v.get("speaker_emails"), "speaker")
            for p in problems:
                warn(p)
            db.flush()
            current = {link.user_id for link in session.speakers}
            wanted = {u.id for u in speakers}
            if current != wanted:
                session.speakers[:] = [l for l in session.speakers if l.user_id in wanted]
                for uid in wanted - current:
                    session.speakers.append(SessionSpeaker(user_id=uid))
                changed = changed if changed is None else True

        if changed is True:
            updated += 1
        elif changed is False:
            unchanged += 1

    missing = [s.title for key, s in sessions.items() if key not in mentioned]
    for title in missing:
        warnings.append(RowProblem(row=0, item=title,
                                   reason="in the database but not in this file (kept, not deleted)"))

    db.commit()
    return AgendaImportReport(event_slug=event.slug, rows_read=rows_read, created=created,
                              updated=updated, unchanged=unchanged, rooms_created=rooms_created,
                              people_created=people.created, skipped=skipped, warnings=warnings)
