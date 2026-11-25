"""Booth scan / lead exchange: one-tap consent, idempotent, owners-only leads."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy import func, select
from starlette.responses import RedirectResponse

from app.auth import oauth
from app.models import BoothScan
from tests.conftest import api_client, upload_csv

DATA = Path(__file__).resolve().parent.parent / "sample_data"


@pytest.fixture
def expo(client, cdc):
    """CyberDataCon-shaped event with the sample registrants and booths loaded.
    Returns {booth name: qr token}."""
    upload_csv(client, "/admin/events/cdc/registrants/import", (DATA / "registrants_sample.csv").read_bytes())
    upload_csv(client, "/admin/events/cdc/booths/import", (DATA / "booths_sample.csv").read_bytes())
    booths = client.get("/admin/events/cdc/booths").json()
    return {b["name"]: {"token": b["qr_link"].rsplit("/", 1)[1], "id": b["id"]} for b in booths}


@pytest.fixture
def browser(sign_in):
    """A fresh browser, signed in as whoever you say."""
    def _as(email):
        b = api_client()
        assert sign_in(b, email).status_code == 303
        return b
    return _as


ADA = "ada.morgan@example.com"        # registrant (student)
KWAME = "kwame.mensah@example.com"    # registrant AND owner of Harbor Cloud


def test_preview_works_without_sign_in_and_shares_nothing(anon_client, expo, db):
    preview = anon_client.get(f"/scan/{expo['Harbor Cloud']['token']}").json()
    assert preview["booth_name"] == "Harbor Cloud"
    assert preview["location_label"] == "3rd floor, table 2"
    assert preview["signed_in"] is False and preview["already_shared_at"] is None
    assert "preloaded_notes" not in preview  # the reward comes after consent
    assert db.scalar(select(func.count()).select_from(BoothScan)) == 0


def test_unknown_or_rotated_code_is_404(client, anon_client, expo):
    assert anon_client.get("/scan/not-a-real-code").status_code == 404
    old = expo["Lumen Labs"]["token"]
    client.post(f"/admin/booths/{expo['Lumen Labs']['id']}/rotate-qr")
    response = anon_client.get(f"/scan/{old}")
    assert response.status_code == 404 and "isn't active" in response.json()["detail"]


def test_sharing_requires_sign_in(anon_client, expo):
    assert anon_client.post(f"/scan/{expo['Harbor Cloud']['token']}").status_code == 401


def test_people_not_registered_for_the_event_cannot_share(browser, expo):
    walk_in = browser("walk.in@example.com")
    response = walk_in.post(f"/scan/{expo['Harbor Cloud']['token']}")
    assert response.status_code == 403 and "registration" in response.json()["detail"]


def test_one_tap_shares_and_returns_the_booths_notes(browser, expo, db):
    ada = browser(ADA)
    result = ada.post(f"/scan/{expo['Harbor Cloud']['token']}").json()
    assert result["first_time"] is True
    assert "hiring interns" in result["preloaded_notes"]
    assert db.scalar(select(func.count()).select_from(BoothScan)) == 1
    preview = ada.get(f"/scan/{expo['Harbor Cloud']['token']}").json()
    assert preview["signed_in"] is True and preview["already_shared_at"] is not None


def test_sharing_twice_is_still_one_lead(browser, expo, db):
    ada = browser(ADA)
    ada.post(f"/scan/{expo['Harbor Cloud']['token']}")
    again = ada.post(f"/scan/{expo['Harbor Cloud']['token']}").json()
    assert again["first_time"] is False
    assert db.scalar(select(func.count()).select_from(BoothScan)) == 1


def test_double_tap_race_still_makes_one_lead(browser, expo, db):
    # Eight "taps" at the same moment. Check-then-insert could let several
    # through; INSERT ... ON CONFLICT DO NOTHING cannot.
    ada = browser(ADA)
    url = f"/scan/{expo['Harbor Cloud']['token']}"
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: ada.post(url).json(), range(8)))
    assert sum(r["first_time"] for r in results) == 1
    assert db.scalar(select(func.count()).select_from(BoothScan)) == 1


def test_owner_cannot_share_with_their_own_booth(browser, expo):
    response = browser(KWAME).post(f"/scan/{expo['Harbor Cloud']['token']}")
    assert response.status_code == 400


def test_owner_sees_leads_with_profile_and_email(browser, expo):
    browser(ADA).post(f"/scan/{expo['Harbor Cloud']['token']}")
    leads = browser(KWAME).get(f"/my-booths/{expo['Harbor Cloud']['id']}/leads").json()
    assert len(leads) == 1
    lead = leads[0]
    assert (lead["first_name"], lead["email"]) == ("Ada", ADA)
    assert lead["is_student"] is True and lead["university"] == "Lipscomb University"
    assert lead["major"] == "Computer Science"


def test_leads_are_private_to_that_booth(browser, client, expo):
    browser(ADA).post(f"/scan/{expo['Harbor Cloud']['token']}")
    harbor = f"/my-booths/{expo['Harbor Cloud']['id']}/leads"
    # Another booth's owner, an attendee, and someone signed out: all refused.
    assert browser("rita.okafor@example.com").get(harbor).status_code == 403
    assert browser(ADA).get(harbor).status_code == 403
    assert api_client().get(harbor).status_code == 401
    # The event's admin can see them.
    assert client.get(harbor).status_code == 200


def test_leads_download_as_an_excel_friendly_csv(browser, expo):
    browser(ADA).post(f"/scan/{expo['Harbor Cloud']['token']}")
    response = browser(KWAME).get(f"/my-booths/{expo['Harbor Cloud']['id']}/leads.csv")
    assert response.headers["content-type"].startswith("text/csv")
    assert 'filename="leads-harbor-cloud-' in response.headers["content-disposition"]
    assert response.content.startswith(b"\xef\xbb\xbf")  # BOM for Excel
    lines = response.content.decode("utf-8-sig").splitlines()
    assert lines[0].startswith("first_name,last_name,email,")
    assert "ada.morgan@example.com" in lines[1] and ",yes," in lines[1]


def test_my_booths_shows_lead_counts(browser, expo):
    browser(ADA).post(f"/scan/{expo['Harbor Cloud']['token']}")
    mine = browser(KWAME).get("/my-booths").json()
    assert [(b["name"], b["lead_count"]) for b in mine] == [("Harbor Cloud", 1)]


def test_attendee_passport_lists_visits_and_notes(browser, expo):
    ada = browser(ADA)
    ada.post(f"/scan/{expo['Harbor Cloud']['token']}")
    ada.post(f"/scan/{expo['Career Commons']['token']}")
    visits = ada.get("/me/booth-visits").json()
    assert {v["booth_name"] for v in visits} == {"Harbor Cloud", "Career Commons"}
    assert all(v["preloaded_notes"] for v in visits)


# Coming back to the booth after signing in ------------------------------------

@pytest.fixture
def fake_google_redirect(monkeypatch):
    async def fake(request, redirect_uri, **kwargs):
        return RedirectResponse("https://accounts.google.com/o/oauth2/auth")
    monkeypatch.setattr(oauth.google, "authorize_redirect", fake)


def test_sign_in_returns_you_to_the_booth_you_scanned(fake_google_redirect, sign_in):
    b = api_client()
    b.get("/auth/google/login?next=/scan/abc123", follow_redirects=False)
    assert sign_in(b, ADA).headers["location"] == "/scan/abc123"


def test_sign_in_never_redirects_to_another_website(fake_google_redirect, sign_in):
    for evil in ("https://evil.example/phish", "//evil.example", "/\\evil.example"):
        b = api_client()
        b.get("/auth/google/login", params={"next": evil}, follow_redirects=False)
        assert sign_in(b, ADA).headers["location"] == "/api/docs", evil


def test_frontend_pages_are_allowed_as_next(fake_google_redirect, sign_in):
    b = api_client()
    b.get("/auth/google/login", params={"next": "http://localhost:5173/scan/x"}, follow_redirects=False)
    assert sign_in(b, ADA).headers["location"] == "http://localhost:5173/scan/x"
