"""Booth import, QR codes, and the printable sheet."""
from pathlib import Path

from sqlalchemy import select

from app.models import EventRole, User
from tests.conftest import upload_csv

DATA = Path(__file__).resolve().parent.parent / "sample_data"
BOOTHS = (DATA / "booths_sample.csv").read_bytes()


def upload_booths(client, content=BOOTHS):
    return upload_csv(client, "/admin/events/cdc/booths/import", content)


def booths_by_name(client):
    return {b["name"]: b for b in client.get("/admin/events/cdc/booths").json()}


def test_sample_booths_import_and_explain_problems(client, cdc):
    report = upload_booths(client).json()
    assert report["rows_read"] == 8
    assert report["created"] == 6
    assert report["people_created"] == 6
    reasons = {p["row"]: p["reason"] for p in report["skipped"]}
    assert reasons == {8: "same booth name as row 3", 9: "missing booth name"}
    assert any(w["item"] == "Voltline Compute" and "no email" in w["reason"] for w in report["warnings"])


def test_booth_owners_are_listed(client, cdc):
    upload_booths(client)
    keystone = booths_by_name(client)["Keystone Security"]
    assert {o["email"] for o in keystone["owners"]} == {"sofia.hernandez@example.com", "leo.park@example.com"}


def test_qr_link_holds_the_secret_token_not_the_booth_id(client, cdc):
    upload_booths(client)
    booth = booths_by_name(client)["Harbor Cloud"]
    assert booth["qr_link"].startswith("http://localhost:5173/scan/")
    assert booth["id"] not in booth["qr_link"]
    assert len(booth["qr_link"].rsplit("/", 1)[1]) == 32


def test_reupload_never_changes_printed_qr_codes(client, cdc):
    upload_booths(client)
    before = {n: b["qr_link"] for n, b in booths_by_name(client).items()}
    edited = BOOTHS.replace(b"Cloud security engineering.", b"Cloud security, now with AI.")
    report = upload_booths(client, edited).json()
    assert (report["updated"], report["unchanged"]) == (1, 5)
    assert {n: b["qr_link"] for n, b in booths_by_name(client).items()} == before


def test_rotating_a_qr_code_gives_a_new_secret(client, cdc):
    upload_booths(client)
    booth = booths_by_name(client)["Lumen Labs"]
    rotated = client.post(f"/admin/booths/{booth['id']}/rotate-qr").json()
    assert rotated["qr_link"] != booth["qr_link"]


def test_qr_image_is_a_png(client, cdc):
    upload_booths(client)
    booth = booths_by_name(client)["Career Commons"]
    image = client.get(booth["qr_image"])
    assert image.headers["content-type"] == "image/png"
    assert image.content.startswith(b"\x89PNG")


def test_printable_sheet_has_every_booth(client, cdc):
    upload_booths(client)
    page = client.get("/admin/events/cdc/booths/qr-sheet")
    assert page.headers["content-type"].startswith("text/html")
    assert page.text.count("<svg") == 6
    # Regression: without a viewBox the browser CROPS the code when resizing it,
    # cutting off a corner square, and phones can't read it.
    assert page.text.count("viewBox") == 6
    assert "Keystone Security" in page.text and "3rd floor, table 3" in page.text


def test_registrant_who_owns_a_booth_has_both_roles(client, cdc, db):
    upload_csv(client, "/admin/events/cdc/registrants/import", (DATA / "registrants_sample.csv").read_bytes())
    upload_booths(client)
    kwame = db.scalar(select(User).where(User.email == "kwame.mensah@example.com"))
    assert set(db.scalars(select(EventRole.role).where(EventRole.user_id == kwame.id))) == {"attendee", "booth_owner"}
