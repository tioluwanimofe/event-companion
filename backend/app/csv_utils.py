"""Shared helpers for reading spreadsheets exported as CSV.

Used by every importer (registrants, agenda, booths), so the "messy real
world" rules live in one place: Excel's hidden BOM, old Windows encodings,
column names spelled ten different ways, dates like 4/16/2027 and times
like "9:30 AM".
"""
import csv
import io
import re
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class CsvFormatError(ValueError):
    """The file as a whole can't be used (wrong encoding, missing column...)."""


def decode_csv(raw: bytes) -> str:
    """Excel adds an invisible "BOM" to UTF-8 files ("utf-8-sig" removes it).
    Older Windows exports use cp1252, so we try that second."""
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise CsvFormatError("Couldn't read the file. Save it as 'CSV UTF-8' and try again.")


def normalize_header(name: str) -> str:
    """'Email Address' -> 'email_address', 'Are you a student?' -> 'are_you_a_student'"""
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def map_headers(fieldnames: list[str] | None, aliases: dict[str, set[str]],
                required: list[str | tuple[str, ...]]) -> dict[str, str]:
    """Match the file's column names to our field names.

    `required` lists fields that must be present; a tuple means "at least
    one of these" (e.g. first_name or full_name).
    Returns {our_field: column name in the file}.
    """
    if not fieldnames:
        raise CsvFormatError("The file is empty or has no header row.")
    mapping: dict[str, str] = {}
    for column in fieldnames:
        key = normalize_header(column or "")
        for field, names in aliases.items():
            if key in names and field not in mapping:
                mapping[field] = column
    for need in required:
        options = need if isinstance(need, tuple) else (need,)
        if not any(o in mapping for o in options):
            wanted = " or ".join(o.replace("_", " ") for o in options)
            raise CsvFormatError(
                f"No {wanted} column found. Columns in the file: {', '.join(fieldnames)}")
    return mapping


def read_rows(text: str, aliases: dict[str, set[str]], required):
    """Yields (row_number, {field: stripped value}) for every non-blank row.
    Row numbers match Excel: row 1 is the header."""
    reader = csv.DictReader(io.StringIO(text))
    columns = map_headers(reader.fieldnames, aliases, required)
    for row_number, raw in enumerate(reader, start=2):
        values = {f: (raw.get(col) or "").strip() for f, col in columns.items()}
        if any(values.values()):
            yield row_number, values


def split_list(value: str | None) -> list[str]:
    """'a@x.com; b@x.com' -> ['a@x.com', 'b@x.com'] (also accepts commas)."""
    return [part.strip() for part in re.split(r"[;,]", value or "") if part.strip()]


# Dates and times ------------------------------------------------------------

DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y")
TIME_FORMATS = ("%H:%M", "%I:%M %p", "%I:%M%p", "%I %p", "%I%p", "%H:%M:%S")


def parse_date(value: str) -> date:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"can't read date '{value}' (try 2027-04-16 or 4/16/2027)")


def parse_time(value: str) -> time:
    cleaned = re.sub(r"\s+", " ", value.strip().upper().replace(".", ""))
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"can't read time '{value}' (try 9:30 AM or 14:30)")


def local_to_aware(day: date, clock: time, timezone: str) -> datetime:
    """'April 16, 9:30 AM in Nashville' -> a datetime that knows its time zone.
    Postgres then stores it as UTC (ADR 0003, choice 6), and daylight saving
    is handled by the time-zone database, not by us."""
    return datetime.combine(day, clock, tzinfo=ZoneInfo(timezone))
