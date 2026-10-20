"""Find-or-create people who arrive through spreadsheets (speakers, booth owners).

Everyone is matched by email, the same rule as the registrant import, so a
speaker who also registered is ONE user with two roles (ADR 0003, choice 2).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.csv_utils import EMAIL_PATTERN, split_list
from app.models import Event, EventRole, User


class PeopleBook:
    """Remembers users and roles already loaded, so a big file doesn't
    query the database again for every row."""

    def __init__(self, db: Session, event: Event):
        self.db = db
        self.event = event
        self.users: dict[str, User] = {}
        self.roles: set[tuple] = set(db.execute(
            select(EventRole.user_id, EventRole.role).where(EventRole.event_id == event.id)
        ).tuples())
        self.created = 0

    def person(self, email: str, full_name: str | None) -> User:
        """The user with this email, created if new. Existing names are kept:
        the registration data is more trustworthy than an agenda sheet."""
        email = email.lower()
        if email not in self.users:
            user = self.db.scalar(select(User).where(User.email == email))
            if user is None:
                first, _, last = (full_name or email.split("@")[0]).strip().partition(" ")
                user = User(email=email, first_name=first[:100], last_name=last.strip()[:100])
                self.db.add(user)
                self.db.flush()  # get the new id now
                self.created += 1
            self.users[email] = user
        return self.users[email]

    def give_role(self, user: User, role: str) -> None:
        if (user.id, role) not in self.roles:
            self.db.add(EventRole(event_id=self.event.id, user_id=user.id,
                                  role=role, source="csv_import"))
            self.roles.add((user.id, role))

    def people_from_cells(self, names_cell: str | None, emails_cell: str | None,
                          role: str) -> tuple[list[User], list[str]]:
        """'Ada Morgan; Tunde Bakare' + 'ada@x.com; tunde@x.com' -> two users with `role`.
        Names pair with emails by position. Returns (users, problems)."""
        names, emails = split_list(names_cell), split_list(emails_cell)
        users, problems = [], []
        if names and not emails:
            problems.append(f"{role.replace('_', ' ')} '{names_cell}' has no email, so they weren't linked")
            return users, problems
        for i, email in enumerate(emails):
            if not EMAIL_PATTERN.match(email.lower()):
                problems.append(f"'{email}' doesn't look like an email, skipped")
                continue
            user = self.person(email, names[i] if i < len(names) else None)
            self.give_role(user, role)
            if user not in users:
                users.append(user)
        return users, problems
