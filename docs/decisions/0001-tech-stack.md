# ADR 0001: Tech stack — React + TypeScript, FastAPI, PostgreSQL

- **Status:** Accepted
- **Date:** 2026-10-13
- **Decider:** Tioluwanimofe Adesanya

## Context

Event Companion is being built for CyberDataCon (April 2027). The app is due February 2027, which leaves about two months for pilot and load testing.

Two stacks were on the table:

1. **Next.js + TypeScript + Supabase.** This is what the September product spec (`docs/product-spec.md`) recommended. Supabase provides Postgres, auth, row-level security, realtime and storage. Most of the backend would be configuration, with the frontend talking to the database directly.
2. **React + TypeScript → REST API → FastAPI (Python) → PostgreSQL.** The frontend and backend are separate, and the API is code we write and own.

What matters for this project:

- **Reliability under load.** A previous event app crashed at about 300 of 500 expected users. The system has to be load-tested before April.
- **Clear authorization rules.** There are four roles (admin/organizer, booth owner, speaker, attendee). When an attendee scans a booth's QR code, their profile is shared with that booth owner. Who can see what has to be explicit and testable.
- **Learning and ownership.** This is a portfolio project. The goal is to understand and defend every layer, not to assemble a black box.
- **Existing skills.** Python is the strongest language here, so a Python backend means less ramp-up on the server side.

## Decision

We will use:

| Layer | Choice |
|---|---|
| Frontend | React + TypeScript, delivered as a PWA (installable web app, no app store) |
| API style | REST over HTTPS, JSON |
| Backend | Python + FastAPI |
| Database | PostgreSQL |

The frontend never talks to the database directly. Every read and write goes through the FastAPI backend, and all authorization (role checks, who can see an attendee's profile) is enforced there.

## Why

- **React + TypeScript.** It's widely used professionally. Types catch mistakes before runtime and make the API contract visible in the frontend code. The PWA approach covers the needs (camera for QR scanning, home-screen install) without an app store.
- **FastAPI.** It's Python. It generates OpenAPI docs automatically from the code, so `API.md` can stay in sync with the real endpoints. Pydantic models validate every request. It supports async, which matters for load. And it makes the backend explicit code that can be unit-tested and reasoned about, instead of database policies spread across a hosted service.
- **PostgreSQL.** The data is relational: users, events, booths, sessions, booth visits, roles. It's mature and well-supported by hosting providers. If the venue map comes back later, PostGIS is available.
- **REST.** It's simple, cacheable, and easy to load-test and debug. Realtime features (e.g. "speaker, you're on in 15 minutes") can be added later where they're needed, without changing the whole API style.

## Alternatives considered

- **Next.js + Supabase.** It's faster to get running, and auth and realtime come built in. It was rejected because most of the backend would live inside Supabase configuration and row-level-security policies rather than in code we own and test, and that works against the learning and ownership goal. *Note:* this decision is about where the application logic lives. A hosted Postgres from Supabase (or similar) is still an option for *hosting* the database (see open decisions below).
- **SQLite.** It's simpler for development, but it isn't suited to many people writing at the same time at a live event, and it has no clear path to PostGIS.
- **Flutter / native apps.** Dr. Simmons asked about this. It was rejected for v1 because it means app-store installs, which add friction at a one-day event. A PWA covers the camera and offline needs.

## Consequences

**Good**
- Each layer can be tested on its own (API tests with pytest, UI tests with the frontend tooling).
- Authorization rules sit in one place, in Python, under test.
- The architecture is easy to explain: browser → API → database.

**Costs we accept**
- **More to build ourselves:** authorization logic, database migrations, API endpoints.
- **More to host:** the frontend (static site), the backend (a server process) and the database are deployed separately.
- **Realtime is not free.** Live updates need their own work (polling, server-sent events, or WebSockets) when we get there.

## Follow-up decisions (open)

These are not decided yet and each gets its own ADR:

1. **Google sign-in approach.** Verify Google ID tokens directly in FastAPI, or use an auth provider (e.g. Firebase Auth, Auth0, Supabase Auth) and verify its tokens in FastAPI. Either way, FastAPI does the authorization.
2. **Frontend build tool:** Vite + React is the likely default.
3. **Database access in Python:** SQLAlchemy + Alembic for migrations, or SQLModel.
4. **Hosting:** where the frontend, the backend and Postgres each live, and how `app.cyberdatacon.com` points to them.
5. **Offline/sync strategy:** how the prototype's `dispatch → queue → flush` model maps onto IndexedDB, a service worker and the REST API.
