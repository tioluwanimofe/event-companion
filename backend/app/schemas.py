"""API data shapes (Pydantic). What the API accepts and sends back.

Kept separate from app/models.py on purpose (ADR 0002): the database has
columns like google_sub that must never leave the server.
"""
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


# Events -----------------------------------------------------------------------

class EventCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=100,
                      examples=["cyberdatacon-2027"],
                      description="Short id used in links: lower-case letters, numbers, dashes")
    name: str = Field(max_length=200, examples=["CyberDataCon 2027"])
    venue: str | None = Field(None, max_length=200, examples=["Lipscomb University"])
    timezone: str = Field("America/Chicago", examples=["America/Chicago"])
    # AwareDatetime = must include a time zone offset, e.g. -05:00
    starts_at: AwareDatetime = Field(examples=["2027-04-16T07:30:00-05:00"])
    ends_at: AwareDatetime = Field(examples=["2027-04-16T18:00:00-05:00"])

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("unknown time zone, use a name like 'America/Chicago'")
        return value

    @model_validator(mode="after")
    def ends_after_start(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # read from a SQLAlchemy object

    id: uuid.UUID
    slug: str
    name: str
    venue: str | None
    timezone: str
    starts_at: datetime
    ends_at: datetime


# Attendees --------------------------------------------------------------------

class AttendeeOut(BaseModel):
    """What an admin sees about an attendee. No google_sub, on purpose."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    company: str | None
    job_title: str | None
    is_student: bool | None
    university: str | None
    major: str | None
    has_signed_in: bool = Field(description="True once they've signed in with Google")


# CSV import -------------------------------------------------------------------

class SkippedRow(BaseModel):
    row: int = Field(description="Row number as shown in Excel (row 1 is the header)")
    email: str | None
    reason: str


class ImportReport(BaseModel):
    event_slug: str
    rows_read: int
    created: int = Field(description="New people added")
    updated: int = Field(description="People already here whose details changed")
    unchanged: int = Field(description="People already here, nothing new")
    skipped: list[SkippedRow]


# Agenda and booth imports -------------------------------------------------------

class RowProblem(BaseModel):
    row: int = Field(description="Row number as shown in Excel (row 1 is the header)")
    item: str | None = Field(description="Session title or booth name, if we could read it")
    reason: str


class ScheduleImportReport(BaseModel):
    event_slug: str
    rows_read: int
    created: int = Field(description="New sessions or booths")
    updated: int = Field(description="Already here, details changed")
    unchanged: int = Field(description="Already here, nothing new")
    people_created: int = Field(description="New users made for speakers or booth owners")
    skipped: list[RowProblem] = Field(description="Rows NOT saved, and why")
    warnings: list[RowProblem] = Field(description="Rows saved, but something needs a look")


class AgendaImportReport(ScheduleImportReport):
    rooms_created: int


# Public agenda ---------------------------------------------------------------

class SpeakerOut(BaseModel):
    """Public: name and company only. No email."""
    name: str
    company: str | None


class SessionOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    track: str | None
    kind: str
    room: str | None
    building: str | None
    starts_at: datetime = Field(description="In the event's local time zone")
    ends_at: datetime
    speakers: list[SpeakerOut]


class AgendaOut(BaseModel):
    event_slug: str
    event_name: str
    timezone: str
    sessions: list[SessionOut]


# Booths (admin view) ---------------------------------------------------------------

class PersonBrief(BaseModel):
    name: str
    email: str


class BoothOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    location_label: str | None
    preloaded_notes: str | None
    owners: list[PersonBrief]
    qr_link: str = Field(description="What the printed QR code contains")
    qr_image: str = Field(description="Open this path to see/print the QR code")
