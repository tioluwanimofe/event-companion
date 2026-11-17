"""Sign-in and the /admin lock (ADR 0004).

Google is faked (see `sign_in` in conftest.py). What's tested for real:
our linking rules, the session cookie, and who may do what.
"""
from sqlalchemy import func, select

from app.models import EventRole, User
from tests.conftest import upload_csv

REGISTRANT_CSV = "First Name,Last Name,Email\nAda,Morgan,ada@example.com\n"


# Who are you? (authentication) --------------------------------------------

def test_not_signed_in_gets_401_on_admin_pages(anon_client):
    assert anon_client.get("/admin/events").status_code == 401
    assert anon_client.get("/auth/me").status_code == 401


def test_sign_in_sets_a_cookie_and_redirects_to_docs(anon_client, sign_in):
    response = sign_in(anon_client, "new.person@example.com")

    assert response.status_code == 303
    assert response.headers["location"] == "/docs"
    cookie = response.headers["set-cookie"].lower()
    assert "ec_session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie

    me = anon_client.get("/auth/me").json()
    assert me["email"] == "new.person@example.com"
    assert "google_sub" not in me


def test_csv_registrant_is_linked_on_first_sign_in_not_duplicated(client, event, anon_client,
                                                                   sign_in, db):
    upload_csv(client, "/admin/events/testcon/registrants/import", REGISTRANT_CSV)

    sign_in(anon_client, "ADA@example.com", sub="google-ada")  # Google may send any case

    me = anon_client.get("/auth/me").json()
    assert me["first_name"] == "Ada"  # the CSV's user, not a new one
    assert me["roles"] == [{"event_slug": "testcon", "role": "attendee"}]
    assert db.scalar(select(func.count()).select_from(User).where(User.email == "ada@example.com")) == 1
    assert db.scalar(select(User.google_sub).where(User.email == "ada@example.com")) == "google-ada"


def test_unverified_email_cannot_claim_a_registrant(client, event, anon_client, sign_in, db):
    upload_csv(client, "/admin/events/testcon/registrants/import", REGISTRANT_CSV)

    response = sign_in(anon_client, "ada@example.com", sub="google-impostor", verified=False)

    assert response.status_code == 403
    assert db.scalar(select(User.google_sub).where(User.email == "ada@example.com")) is None
    assert anon_client.get("/auth/me").status_code == 401


def test_email_already_linked_to_another_google_account_is_refused(anon_client, sign_in):
    sign_in(anon_client, "ada@example.com", sub="google-ada")

    other_browser = type(anon_client)(anon_client.app)
    response = sign_in(other_browser, "ada@example.com", sub="google-someone-else")

    assert response.status_code == 403


def test_returning_user_is_found_by_google_id(anon_client, sign_in, db):
    sign_in(anon_client, "ada@example.com", sub="google-ada")
    anon_client.post("/auth/logout")

    sign_in(anon_client, "ada@example.com", sub="google-ada")

    assert db.scalar(select(func.count()).select_from(User)) == 1


def test_unknown_person_gets_an_account_with_no_role(anon_client, sign_in, db):
    sign_in(anon_client, "walk.in@example.com", given_name="Walk", family_name="In")

    me = anon_client.get("/auth/me").json()
    assert (me["first_name"], me["last_name"]) == ("Walk", "In")
    assert me["roles"] == [] and me["is_platform_admin"] is False
    assert db.scalar(select(func.count()).select_from(EventRole)) == 0


def test_logout_forgets_you(anon_client, sign_in):
    sign_in(anon_client, "ada@example.com")
    assert anon_client.post("/auth/logout").status_code == 204
    assert anon_client.get("/auth/me").status_code == 401


def test_a_tampered_cookie_is_ignored(anon_client):
    anon_client.cookies.set("ec_session", "eyJ1c2VyX2lkIjogImhhY2tlciJ9.fake.signature")
    assert anon_client.get("/auth/me").status_code == 401


def test_login_link_explains_when_google_is_not_set_up(anon_client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "google_client_id", "")
    response = anon_client.get("/auth/google/login", follow_redirects=False)
    assert response.status_code == 503
    assert "GOOGLE_CLIENT_ID" in response.json()["detail"]


def test_login_link_sends_you_to_google(anon_client, monkeypatch):
    from app.auth import oauth
    from starlette.responses import RedirectResponse

    async def fake_redirect(request, redirect_uri, **kwargs):
        return RedirectResponse(f"https://accounts.google.com/o/oauth2/auth?redirect_uri={redirect_uri}")

    monkeypatch.setattr(oauth.google, "authorize_redirect", fake_redirect)
    response = anon_client.get("/auth/google/login", follow_redirects=False)
    assert response.headers["location"].startswith("https://accounts.google.com/")
    assert "/auth/google/callback" in response.headers["location"]


# What may you do? (authorization) -----------------------------------------

def test_attendee_gets_403_on_admin_pages(client, event, anon_client, sign_in):
    upload_csv(client, "/admin/events/testcon/registrants/import", REGISTRANT_CSV)
    sign_in(anon_client, "ada@example.com")

    assert anon_client.get("/admin/events").status_code == 403
    assert anon_client.get("/admin/events/testcon/attendees").status_code == 403
    assert upload_csv(anon_client, "/admin/events/testcon/registrants/import",
                      REGISTRANT_CSV).status_code == 403


def test_event_admin_can_manage_their_event_but_not_others(client, event, anon_client, sign_in, db):
    other = client.post("/admin/events", json={
        "slug": "othercon", "name": "OtherCon",
        "starts_at": "2027-05-01T08:00:00-05:00", "ends_at": "2027-05-01T17:00:00-05:00"})
    assert other.status_code == 201

    sign_in(anon_client, "organizer@example.com")
    organizer = db.scalar(select(User).where(User.email == "organizer@example.com"))
    db.add(EventRole(event_id=event["id"], user_id=organizer.id, role="admin", source="invited"))
    db.commit()

    assert anon_client.get("/admin/events/testcon/attendees").status_code == 200
    assert anon_client.get("/admin/events/othercon/attendees").status_code == 403
    # Creating events is for platform admins (ADMIN_EMAILS) only
    assert anon_client.get("/admin/events").status_code == 403


def test_booth_pages_follow_the_booths_event(client, event, anon_client, sign_in):
    upload_csv(client, "/admin/events/testcon/booths/import",
               "Booth,Location\nAcme,Table 1\n")
    booth_id = client.get("/admin/events/testcon/booths").json()[0]["id"]

    assert client.get(f"/admin/booths/{booth_id}/qr.png").status_code == 200

    sign_in(anon_client, "stranger@example.com")
    assert anon_client.get(f"/admin/booths/{booth_id}/qr.png").status_code == 403
    assert anon_client.post(f"/admin/booths/{booth_id}/rotate-qr").status_code == 403


def test_non_admins_cannot_tell_which_events_exist(anon_client, sign_in):
    sign_in(anon_client, "stranger@example.com")
    assert anon_client.get("/admin/events/does-not-exist/attendees").status_code == 403


def test_every_admin_route_is_locked(anon_client):
    """If someone adds an /admin route and forgets the guard, this fails."""
    from app.main import app
    # The OpenAPI schema (what /docs shows) lists every route and method.
    admin_paths = {p: ops for p, ops in app.openapi()["paths"].items() if p.startswith("/admin")}
    assert len(admin_paths) >= 9
    for path, operations in admin_paths.items():
        url = (path.replace("{slug}", "testcon")
               .replace("{booth_id}", "00000000-0000-0000-0000-000000000000"))
        for method in operations:
            response = anon_client.request(method.upper(), url)
            assert response.status_code == 401, f"{method.upper()} {path} is not locked"


def test_public_agenda_still_needs_no_sign_in(client, event, anon_client):
    assert anon_client.get("/events/testcon/agenda").status_code == 200
