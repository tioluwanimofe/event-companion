"""Agenda import: local times, rooms, speakers, re-uploads."""
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.models import EventRole, Session, User
from tests.conftest import make_event, upload_csv

DATA = Path(__file__).resolve().parent.parent / "sample_data"
AGENDA = (DATA / "agenda_sample.csv").read_bytes()
HEADER = "Date,Start,End,Title,Room,Speaker,Speaker Email\n"


def upload_agenda(client, content, slug="cdc"):
    return upload_csv(client, f"/admin/events/{slug}/agenda/import", content)


def test_sample_agenda_imports_and_explains_broken_rows(client, cdc):
    report = upload_agenda(client, AGENDA).json()
    assert report["rows_read"] == 15
    assert report["created"] == 13
    assert report["rooms_created"] == 5
    assert report["people_created"] == 8  # the speakers
    reasons = {p["row"]: p["reason"] for p in report["skipped"]}
    assert reasons[15] == "ends before it starts"
    assert reasons[16].startswith("can't read time '25:00'")
    assert report["warnings"] == []


def test_local_time_is_stored_as_utc_and_shown_as_local(client, cdc, db):
    upload_agenda(client, AGENDA)
    keynote = db.scalar(select(Session).where(Session.title.like("Keynote%")))
    # 11:00 AM in Nashville in April (CDT, UTC-5) is 16:00 UTC
    assert keynote.starts_at == datetime(2027, 4, 16, 16, 0, tzinfo=timezone.utc)

    agenda = client.get("/events/cdc/agenda").json()
    shown = next(s for s in agenda["sessions"] if s["title"].startswith("Keynote"))
    assert shown["starts_at"] == "2027-04-16T11:00:00-05:00"


def test_daylight_saving_is_handled_by_the_time_zone_database(client, db):
    # In January Nashville is on CST (UTC-6), so 9:00 AM is 15:00 UTC, not 14:00.
    make_event(client, "winter", "2027-01-15T08:00:00-06:00", "2027-01-15T17:00:00-06:00")
    upload_agenda(client, "Date,Start,End,Title\n2027-01-15,9:00 AM,10:00 AM,Winter Talk\n", "winter")
    talk = db.scalar(select(Session).where(Session.title == "Winter Talk"))
    assert talk.starts_at == datetime(2027, 1, 15, 15, 0, tzinfo=timezone.utc)


def test_many_time_and_date_styles_are_understood(client, cdc):
    report = upload_agenda(client, "Date,Start,End,Title\n"
                                   "4/16/2027,9am,9:30 AM,A\n"
                                   '"April 16, 2027",13:00,14:15,B\n').json()
    assert report["created"] == 2, report


def test_date_column_is_optional_for_one_day_events(client, cdc):
    report = upload_agenda(client, "Start,End,Title\n9:00 AM,10:00 AM,No Date Talk\n").json()
    assert report["created"] == 1
    assert client.get("/events/cdc/agenda").json()["sessions"][0]["starts_at"].startswith("2027-04-16T09:00")


def test_reupload_changes_nothing_and_an_edit_updates_one_session(client, cdc, db):
    upload_agenda(client, AGENDA)
    again = upload_agenda(client, AGENDA).json()
    assert (again["created"], again["updated"], again["unchanged"]) == (0, 0, 13)

    moved = AGENDA.replace(b"Hands-On Pen Testing Lab,Workshop,Pen Testing,Swang 108",
                           b"Hands-On Pen Testing Lab,Workshop,Pen Testing,Ezell 301")
    edit = upload_agenda(client, moved).json()
    assert (edit["updated"], edit["unchanged"]) == (1, 12)
    lab = db.scalar(select(Session).where(Session.title == "Hands-On Pen Testing Lab"))
    assert lab.room.name == "Ezell 301"


def test_speaker_who_also_registered_is_one_person_with_two_roles(client, cdc, db):
    upload_csv(client, "/admin/events/cdc/registrants/import",
               (DATA / "registrants_sample.csv").read_bytes())
    report = upload_agenda(client, AGENDA).json()
    assert report["people_created"] == 6  # Priya and Grace had already registered
    priya = db.scalar(select(User).where(User.email == "priya.raman@example.com"))
    roles = set(db.scalars(select(EventRole.role).where(EventRole.user_id == priya.id)))
    assert roles == {"attendee", "speaker"}


def test_public_agenda_shows_speakers_without_emails(client, cdc):
    upload_agenda(client, AGENDA)
    sessions = client.get("/events/cdc/agenda").json()["sessions"]
    panel = next(s for s in sessions if s["title"] == "Panel: Careers in Cyber")
    assert [p["name"] for p in panel["speakers"]] and len(panel["speakers"]) == 3
    assert all(set(p) == {"name", "company"} for p in panel["speakers"])
    assert sessions[0]["title"] == "Breakfast & Registration"  # time order
    assert sessions[0]["kind"] == "meal"                       # "Breakfast" -> meal


def test_removing_a_speaker_in_the_sheet_removes_them_from_the_session(client, cdc, db):
    upload_agenda(client, HEADER + "2027-04-16,9:00,10:00,Duo Talk,Ezell 301,"
                                   "A One; B Two,a@example.com; b@example.com\n")
    upload_agenda(client, HEADER + "2027-04-16,9:00,10:00,Duo Talk,Ezell 301,A One,a@example.com\n")
    talk = db.scalar(select(Session).where(Session.title == "Duo Talk"))
    assert [link.user.email for link in talk.speakers] == ["a@example.com"]


def test_session_missing_from_new_file_is_kept_with_a_warning(client, cdc):
    upload_agenda(client, "Start,End,Title\n9:00,10:00,Old Talk\n")
    report = upload_agenda(client, "Start,End,Title\n10:00,11:00,New Talk\n").json()
    assert any(w["item"] == "Old Talk" and "kept" in w["reason"] for w in report["warnings"])
    assert len(client.get("/events/cdc/agenda").json()["sessions"]) == 2


def test_problems_that_dont_stop_a_session_are_warnings(client, cdc):
    report = upload_agenda(client, HEADER.replace("Room,", "Type,Room,").replace(",Room", ",Room")
                           + "2027-04-16,9:00,10:00,Odd,Hackathon,Ezell 301,No Email Person,\n").json()
    assert report["created"] == 1
    reasons = " | ".join(w["reason"] for w in report["warnings"])
    assert "not recognised" in reasons and "has no email" in reasons


def test_file_without_title_column_is_rejected(client, cdc):
    response = upload_agenda(client, "Start,End\n9:00,10:00\n")
    assert response.status_code == 422 and "No title column" in response.json()["detail"]
