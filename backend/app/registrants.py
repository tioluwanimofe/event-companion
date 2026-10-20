"""Import registrants from a CSV file (exported from the event's CRM).

Each good row becomes (or updates) a `User`, plus an `attendee` role at the
event with source="csv_import" (ADR 0003). Running the same file twice is
safe: people already in the database are updated, never duplicated.

The steps, in order:
  1. decode_csv      bytes from the upload  -> text
  2. map_headers     the file's column names -> our field names
  3. parse_rows      each line -> a clean Registrant, or a reason to skip it
  4. import_registrants  save to the database and count what happened
"""
import csv
import io
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Event, EventRole, User
from app.schemas import ImportReport, SkippedRow

# Different CRMs name the same column differently. Every name on the right
# (after normalizing: lower-case, punctuation -> "_") maps to our field.
HEADER_ALIASES: dict[str, set[str]] = {
    "email": {"email", "email_address", "e_mail", "emailaddress", "work_email"},
    "first_name": {"first_name", "firstname", "first", "given_name"},
    "last_name": {"last_name", "lastname", "last", "surname", "family_name"},
    "full_name": {"name", "full_name", "fullname"},
    "company": {"company", "company_name", "organization", "organisation", "employer"},
    "job_title": {"job_title", "jobtitle", "title", "role", "position"},
    "is_student": {"is_student", "student", "are_you_a_student"},
    "university": {"university", "school", "college", "institution"},
    "major": {"major", "field_of_study", "program", "programme"},
}

# Longest value each column accepts (must match app/models.py)
MAX_LENGTH = {
    "email": 320, "first_name": 100, "last_name": 100,
    "company": 200, "job_title": 200, "university": 200, "major": 200,
}

PROFILE_FIELDS = ("company", "job_title", "is_student", "university", "major")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
YES = {"yes", "y", "true", "1", "student"}
NO = {"no", "n", "false", "0"}


class CsvFormatError(ValueError):
    """The file as a whole can't be used (wrong encoding, no email column...)."""


@dataclass
class Registrant:
    """One clean, validated row."""
    row: int
    email: str
    first_name: str
    last_name: str
    company: str | None = None
    job_title: str | None = None
    is_student: bool | None = None
    university: str | None = None
    major: str | None = None


# 1. decode ------------------------------------------------------------------

def decode_csv(raw: bytes) -> str:
    """Excel adds an invisible "BOM" to UTF-8 files ("utf-8-sig" removes it).
    Older Windows exports use cp1252, so we try that second."""
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise CsvFormatError("Couldn't read the file. Save it as 'CSV UTF-8' and try again.")


# 2. headers -----------------------------------------------------------------

def normalize_header(name: str) -> str:
    """'Email Address' -> 'email_address', 'Are you a student?' -> 'are_you_a_student'"""
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def map_headers(fieldnames: list[str] | None) -> dict[str, str]:
    """Returns {our_field: column name in the file}."""
    if not fieldnames:
        raise CsvFormatError("The file is empty or has no header row.")
    mapping: dict[str, str] = {}
    for column in fieldnames:
        key = normalize_header(column or "")
        for field, aliases in HEADER_ALIASES.items():
            if key in aliases and field not in mapping:
                mapping[field] = column
    if "email" not in mapping:
        raise CsvFormatError(
            f"No email column found. Columns in the file: {', '.join(fieldnames)}")
    if "first_name" not in mapping and "full_name" not in mapping:
        raise CsvFormatError("No first name (or full name) column found.")
    return mapping


# 3. rows --------------------------------------------------------------------

def parse_yes_no(value: str | None) -> bool | None:
    if not value:
        return None
    v = value.strip().lower()
    return True if v in YES else False if v in NO else None


def parse_rows(text: str) -> tuple[list[Registrant], list[SkippedRow], int]:
    """Returns (good rows, skipped rows, number of non-blank rows read)."""
    reader = csv.DictReader(io.StringIO(text))
    columns = map_headers(reader.fieldnames)
    good: list[Registrant] = []
    skipped: list[SkippedRow] = []
    first_seen: dict[str, int] = {}  # email -> row number, to catch repeats
    rows_read = 0

    # Row numbers match what you see in Excel: row 1 is the header.
    for row_number, raw in enumerate(reader, start=2):
        values = {f: (raw.get(col) or "").strip() for f, col in columns.items()}
        if not any(values.values()):
            continue  # completely blank line
        rows_read += 1

        def skip(reason: str, email: str | None = None) -> None:
            skipped.append(SkippedRow(row=row_number, email=email, reason=reason))

        email = values["email"].lower()
        if not email:
            skip("missing email")
            continue
        if not EMAIL_PATTERN.match(email):
            skip("email doesn't look valid", email)
            continue
        if email in first_seen:
            skip(f"same email as row {first_seen[email]}", email)
            continue

        first, last = values.get("first_name", ""), values.get("last_name", "")
        if not first and values.get("full_name"):
            first, _, last = values["full_name"].partition(" ")
            last = last.strip()
        if not first:
            skip("missing first name", email)
            continue

        reg = Registrant(
            row=row_number, email=email, first_name=first, last_name=last,
            company=values.get("company") or None,
            job_title=values.get("job_title") or None,
            is_student=parse_yes_no(values.get("is_student")),
            university=values.get("university") or None,
            major=values.get("major") or None,
        )
        too_long = [f for f, limit in MAX_LENGTH.items()
                    if len(getattr(reg, f) or "") > limit]
        if too_long:
            skip(f"too long: {', '.join(too_long)}", email)
            continue

        first_seen[email] = row_number
        good.append(reg)

    return good, skipped, rows_read


# 4. save --------------------------------------------------------------------

def import_registrants(db: Session, event: Event, raw: bytes) -> ImportReport:
    registrants, skipped, rows_read = parse_rows(decode_csv(raw))

    # Two queries total, not two per row: fetch everyone we might need up front.
    emails = [r.email for r in registrants]
    existing = {u.email: u for u in db.scalars(select(User).where(User.email.in_(emails)))}
    already_attendee = set(db.scalars(
        select(EventRole.user_id).where(
            EventRole.event_id == event.id, EventRole.role == "attendee")))

    created = updated = unchanged = 0
    for reg in registrants:
        user = existing.get(reg.email)
        changed = False

        if user is None:
            user = User(email=reg.email, first_name=reg.first_name,
                        last_name=reg.last_name)
            db.add(user)
            created += 1
        else:
            for field in ("first_name", "last_name"):
                if getattr(user, field) != getattr(reg, field):
                    setattr(user, field, getattr(reg, field))
                    changed = True

        # Blank cells never erase what we already know about someone.
        for field in PROFILE_FIELDS:
            new = getattr(reg, field)
            if new is not None and getattr(user, field) != new:
                setattr(user, field, new)
                changed = True

        db.flush()  # gives a new user its id, so we can link the role
        if user.id not in already_attendee:
            db.add(EventRole(event_id=event.id, user_id=user.id,
                             role="attendee", source="csv_import"))
            already_attendee.add(user.id)
            changed = True

        if user.email in existing:
            updated += changed
            unchanged += not changed

    db.commit()  # all rows saved together, or none if something crashes
    return ImportReport(event_slug=event.slug, rows_read=rows_read, created=created,
                        updated=updated, unchanged=unchanged, skipped=skipped)
