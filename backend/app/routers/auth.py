"""Sign-in endpoints: the OAuth 2.0 "authorization code" flow with Google (ADR 0004).

The dance, step by step 🧠 (the sequence diagram is in the ADR):

1. GET /auth/google/login     We send the browser to Google, with a random
                              `state` value saved in the session cookie.
2. (at Google)                The person picks their account and says yes.
3. GET /auth/google/callback  Google sends the browser back with `code` and
                              `state`. Authlib checks `state` matches (so a
                              stranger can't inject their own login), swaps
                              `code` for tokens, and verifies the ID token's
                              signature. Then we find or link our user.
4. We save the user's id in the signed session cookie. Done.
"""
from authlib.integrations.base_client import OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (SESSION_USER_KEY, SignInRefused, current_user, is_platform_admin,
                      oauth, sign_in_with_google)
from app.config import settings
from app.db import get_db
from app.models import Event, EventRole, User
from app.schemas import MeOut, MyRoleOut

router = APIRouter(prefix="/auth", tags=["Sign-in"])


NEXT_KEY = "next"


def safe_next(target: str | None) -> str | None:
    """Where to go after sign-in, but ONLY if it's one of our own pages.

    🧠 Without this check, /auth/google/login?next=https://evil.example would
    bounce people from a real Google sign-in straight to a fake site: an
    "open redirect", a classic phishing trick. So we allow only paths on this
    API ("/scan/abc", but not "//evil.example") or pages of our own app.
    """
    if not target:
        return None
    if target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    app_base = settings.app_base_url.rstrip("/") + "/"
    if target.startswith(app_base):
        return target
    return None


@router.get("/google/login")
async def google_login(request: Request, next: str | None = None):
    """Open this link in your browser (not with "Try it out") to sign in with Google.

    Add ?next=/scan/<code> to come back to that page afterwards."""
    if not settings.google_sign_in_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "Google sign-in isn't set up: add GOOGLE_CLIENT_ID and "
                            "GOOGLE_CLIENT_SECRET to backend/.env (docs/google-sign-in-setup.md)")
    request.session.pop(NEXT_KEY, None)
    if (target := safe_next(next)) is not None:
        request.session[NEXT_KEY] = target
    redirect_uri = settings.oauth_callback_url or request.url_for("google_callback")
    # prompt=select_account: always show the account picker, handy when testing
    return await oauth.google.authorize_redirect(request, redirect_uri, prompt="select_account")


@router.get("/google/callback", name="google_callback", include_in_schema=False)
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Google sends the browser here. Not for calling yourself."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        # Wrong/missing state, cancelled at Google, expired code...
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Sign-in failed: {error.error}")

    try:
        user = sign_in_with_google(db, token.get("userinfo") or {})
    except SignInRefused as reason:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(reason))

    # A fresh session for a fresh sign-in, so nothing from before carries over
    # (but remember where they wanted to go, e.g. back to the booth they scanned).
    go_to = safe_next(request.session.get(NEXT_KEY)) or settings.after_login_url
    request.session.clear()
    request.session[SESSION_USER_KEY] = str(user.id)
    return RedirectResponse(go_to, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request):
    """Sign out: forget the session."""
    request.session.clear()


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Who am I signed in as, and what am I allowed to do?"""
    roles = db.execute(
        select(Event.slug, EventRole.role)
        .join(Event, Event.id == EventRole.event_id)
        .where(EventRole.user_id == user.id)
        .order_by(Event.slug, EventRole.role)
    ).all()
    return MeOut(
        id=user.id, email=user.email, first_name=user.first_name, last_name=user.last_name,
        is_platform_admin=is_platform_admin(user),
        roles=[MyRoleOut(event_slug=slug, role=role) for slug, role in roles],
    )
