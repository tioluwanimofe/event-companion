"""CSV registrant import: the rules from ADR 0003, checked automatically."""
from pathlib import Path

from sqlalchemy import func, select

from app.models import EventRole, User
from app.registrants import normalize_header

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data" / "registrants_sample.csv"


def upload(client, slug, content: bytes | str, name="registrants.csv"):
    if isinstance(content, str):
        content = content.encode("utf-8")
    return client.post(f"/admin/events/{slug}/registrants/import",
                       files={"file": (name, content, "text/csv")})


def test_sample_file_imports_good_rows_and_explains_bad_ones(client, event):
    report = upload(client, "testcon", SAMPLE.read_bytes()).json()

    assert report["rows_read"] == 12
    assert report["created"] == 8
    reasons = {row["row"]: row["reason"] for row in report["skipped"]}
    assert reasons == {
        9: "missing email",
        10: "email doesn't look valid",
        11: "same email as row 2",
        12: "missing first name",
    }


def test_attendees_endpoint_lists_imported_people(client, event):
    upload(client, "testcon", SAMPLE.read_bytes())
    people = client.get("/admin/events/testcon/attendees").json()

    assert len(people) == 8
    kwame = next(p for p in people if p["first_name"] == "Kwame")
    assert kwame["email"] == "kwame.mensah@example.com"  # stored lower-case
    assert kwame["is_student"] is False
    assert kwame["has_signed_in"] is False
    assert "google_sub" not in kwame  # private field never leaves the server


def test_importing_the_same_file_twice_creates_no_duplicates(client, event, db):
    upload(client, "testcon", SAMPLE.read_bytes())
    second = upload(client, "testcon", SAMPLE.read_bytes()).json()

    assert second["created"] == 0
    assert second["unchanged"] == 8
    assert db.scalar(select(func.count()).select_from(User)) == 8
    assert db.scalar(select(func.count()).select_from(EventRole)) == 8


def test_updated_file_updates_people_but_blank_cells_erase_nothing(client, event, db):
    upload(client, "testcon", "first_name,last_name,email,company\n"
                              "Ada,Morgan,ada@example.com,Old Co\n")
    report = upload(client, "testcon", "first_name,last_name,email,company\n"
                                       "Ada,Morgan-Lee,ada@example.com,\n").json()

    assert report["updated"] == 1
    ada = db.scalar(select(User).where(User.email == "ada@example.com"))
    assert ada.last_name == "Morgan-Lee"   # changed value is applied
    assert ada.company == "Old Co"         # blank cell kept the old value


def test_imported_role_is_marked_as_coming_from_csv(client, event, db):
    upload(client, "testcon", "email,first_name,last_name\nada@example.com,Ada,Morgan\n")
    role = db.scalar(select(EventRole))
    assert (role.role, role.source) == ("attendee", "csv_import")


def test_other_header_names_and_full_name_column_work(client, event):
    csv_text = "Name,E-mail,Organization,Student\nChidi Okeke,chidi@example.com,Lipscomb,Y\n"
    report = upload(client, "testcon", csv_text).json()
    assert report["created"] == 1
    person = client.get("/admin/events/testcon/attendees").json()[0]
    assert (person["first_name"], person["last_name"]) == ("Chidi", "Okeke")
    assert person["company"] == "Lipscomb"
    assert person["is_student"] is True


def test_excel_style_files_are_read(client, event):
    # Excel's "CSV UTF-8" adds a hidden BOM; older exports use Windows-1252.
    bom = "﻿email,first_name,last_name\nsofia@example.com,Sofía,Hernández\n".encode("utf-8")
    cp1252 = "email,first_name,last_name\njoao@example.com,João,Silva\n".encode("cp1252")
    assert upload(client, "testcon", bom).json()["created"] == 1
    assert upload(client, "testcon", cp1252).json()["created"] == 1
    names = {p["first_name"] for p in client.get("/admin/events/testcon/attendees").json()}
    assert names == {"Sofía", "João"}


def test_file_without_email_column_is_rejected_with_a_clear_message(client, event):
    response = upload(client, "testcon", "first_name,last_name\nAda,Morgan\n")
    assert response.status_code == 422
    assert "No email column" in response.json()["detail"]


def test_unknown_event_returns_404(client):
    assert upload(client, "nope", "email,first_name\na@b.co,A\n").status_code == 404


def test_header_normalizing():
    assert normalize_header("  Email Address ") == "email_address"
    assert normalize_header("Are you a student?") == "are_you_a_student"
