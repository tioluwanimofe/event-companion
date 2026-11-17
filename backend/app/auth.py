"""Sign-in and permissions (ADR 0004).

Two separate questions, two separate parts of this file 🧠:

1. AUTHENTICATION, "who are you?"   -> Google answers it. `sign_in_with_google`
   turns Google's answer into one of OUR users.
2. AUTHORIZATION, "what may you do?" -> We answer it, from `event_roles`.
   `current_user`, `require_platform_admin` and `require_event_admin` are
   FastAPI dependencies: put one on a route and it runs before the route does.

After sign-in, the session cookie holds just one thing: the user's id.
The cookie is signed with SESSION_SECRET_KEY, so changing it breaks the
signature and the server ignores it.
"""
import logging
import uuid

from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Booth, Event, EventRole, User

log = logging.getLogger(__name__)

SESSION_USER_KEY = "user_id"

# Authlib reads Google's "discovery document", a public JSON file listing
# Google's login URL, token URL and the keys it signs ID tokens with.
oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    # openid = "tell us who this is", email + profile = "and their email and name"
    client_kwargs={"scope": "openid email profile"},
)


class SignInRefused(Exception):
    """Google said who they are, but we won't let them in. The message is shown to them."""


# 1. Authentication ----------------------------------------------------------

def sign_in_with_google(db: Session, claims: dict) -> User:
    """Turn Google's ID-token claims into our user, creating or linking as needed.

    `claims` is what Google vouches for: `sub` (Google's permanent id for this
    person), `email`, `email_verified`, `given_name`, `family_name`.
    """
    sub = claims.get("sub")
    email = (claims.get("email") or "").strip().lower()
    if not sub or not email:
        raise SignInRefused("Google didn't share an email address for this account.")

    # Best match: we've seen this exact Google account before.
    user = db.scalar(select(User).where(User.google_sub == sub))
    if user is not None:
        return user

    # First sign-in. Only trust the email if Google has checked the person owns it.
    # Without this, anyone could claim a registrant's email and see their data.
    if claims.get("email_verified") is not True:
        raise SignInRefused("Your Google account's email isn't verified yet.")

    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        if user.google_sub is not None:
            # This email already belongs to a *different* Google account.
            raise SignInRefused("This email is already linked to another Google account.")
        user.google_sub = sub  # a CSV registrant signs in for the first time: link them
    else:
        # Not in any CSV. They get an account but no role (ADR 0004, choice 3).
        user = User(
            email=email,
            google_sub=sub,
            first_name=(claims.get("given_name") or email.split("@")[0])[:100],
            last_name=(claims.get("family_name") or "")[:100],
        )
        db.add(user)
    db.commit()
    return user


# 2. Authorization -----------------------------------------------------------

def optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """The signed-in user, or None. For pages that work either way."""
    raw = request.session.get(SESSION_USER_KEY)
    if raw is None:
        return None
    try:
        user = db.get(User, uuid.UUID(raw))
    except ValueError:
        user = None
    if user is None:
        request.session.clear()  # cookie points at a deleted user
    return user


def current_user(user: User | None = Depends(optional_user)) -> User:
    """The signed-in user, or 401 Unauthorized ("we don't know who you are")."""
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "Sign in first: open /auth/google/login")
    return user


def is_platform_admin(user: User) -> bool:
    return user.email in settings.admin_email_set


def is_event_admin(db: Session, user: User, event_id: uuid.UUID) -> bool:
    return is_platform_admin(user) or db.scalar(
        select(EventRole.user_id).where(EventRole.event_id == event_id,
                                        EventRole.user_id == user.id,
                                        EventRole.role == "admin")
    ) is not None


def _forbidden() -> HTTPException:
    # 403 Forbidden = "we know who you are, and the answer is no"
    return HTTPException(status.HTTP_403_FORBIDDEN, "Admins only")


def require_platform_admin(user: User = Depends(current_user)) -> User:
    """For things no single event owns, like creating a new event."""
    if not is_platform_admin(user):
        raise _forbidden()
    return user


def require_event_admin(slug: str, user: User = Depends(current_user),
                        db: Session = Depends(get_db)) -> User:
    """For /admin/events/{slug}/...: an admin OF THIS EVENT (or a platform admin).

    FastAPI fills `slug` from the route's path, the same value the route gets.
    A missing event is a 403, not a 404, for non-admins: we don't tell
    strangers which events exist.
    """
    event_id = db.scalar(select(Event.id).where(Event.slug == slug))
    if is_platform_admin(user) or (event_id is not None and is_event_admin(db, user, event_id)):
        return user
    raise _forbidden()


def require_booth_admin(booth_id: uuid.UUID, user: User = Depends(current_user),
                        db: Session = Depends(get_db)) -> User:
    """For /admin/booths/{booth_id}/...: an admin of the event the booth belongs to."""
    event_id = db.scalar(select(Booth.event_id).where(Booth.id == booth_id))
    if is_platform_admin(user) or (event_id is not None and is_event_admin(db, user, event_id)):
        return user
    raise _forbidden()
