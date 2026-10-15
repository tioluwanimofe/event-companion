\# 0002: Database access layer: SQLAlchemy + Alembic



\## Status

Accepted, 2026-10-15



\## Context

The FastAPI backend needs a way to read and write data in PostgreSQL

(users, booths, sessions, booth scans). The structure of the database

will also change as the app grows, so those changes need to be tracked.



There were two options:

\- \*\*SQLModel + Alembic:\*\* one class describes both the database table

&#x20; and the data the API accepts or returns. Less code, but it hides

&#x20; where the database ends and the API begins.

\- \*\*SQLAlchemy + Alembic:\*\* database classes and API classes (Pydantic)

&#x20; are written separately. More code, but each one has a clear job.



Alembic handles migrations in both options.



\## Decision

Use SQLAlchemy for database access and Alembic for migrations.

API data shapes are defined separately with Pydantic.



\## Reasons

\- SQLAlchemy is older and widely used, so there is far more

&#x20; documentation and help online when I get stuck.

\- It keeps database classes and API classes separate, so I always

&#x20; know where data is stored and exactly what the API sends out.



\## Consequences

\*\*Costs\*\*

\- More code to write: usually a database class and an API class

&#x20; for each thing.

\- A slower start while I learn how SQLAlchemy works.

\- Every change to a table needs an Alembic migration.



\*\*Gains\*\*

\- Database changes are versioned, so every machine ends up with the

&#x20; same tables and a bad change can be rolled back.

\- Separate API classes help prevent private attendee data (like

&#x20; emails or Google IDs) from being sent out by accident.

