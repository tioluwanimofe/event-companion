# Event Companion: backend

FastAPI + SQLAlchemy + PostgreSQL. Why these: see `docs/decisions/` (ADRs 0001–0003).

## Run it (VS Code, no typing)

**Terminal → Run Task…**, then:

| Task | What it does |
|---|---|
| 1. Install / update Python packages | Installs `requirements.txt` into `.venv` |
| 1b. Install test tools | Installs pytest (once) |
| 2. Build / update database tables | Alembic applies new migrations |
| 3. Start the API | Then open <http://127.0.0.1:8000/docs> |
| 4. Run tests | Runs `tests/` against your `_test` database |

Settings live in `backend/.env` (ignored by Git). See `.env.example`.

## Folder map

```
app/
  main.py          # creates the FastAPI app, health checks
  config.py        # reads .env
  db.py            # database connection + Base class
  models.py        # database tables (SQLAlchemy)
  schemas.py       # API shapes (Pydantic): what goes in and out
  csv_utils.py     # shared spreadsheet reading: encodings, headers, dates, times
  people.py        # find-or-create speakers/booth owners by email
  registrants.py   # registrant CSV import
  agenda.py        # agenda CSV import (rooms, sessions, speakers)
  booths.py        # booth CSV import + QR codes
  routers/admin.py # /admin endpoints
  routers/public.py# public endpoints (agenda)
migrations/        # Alembic: versioned changes to the tables
tests/             # pytest, runs on a real Postgres _test database
sample_data/       # fake registrants, agenda and booths CSVs for trying the imports
```

## Endpoints so far

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | API is up |
| GET | `/health/db` | API can reach Postgres; lists tables |
| POST | `/admin/events` | Create an event |
| GET | `/admin/events` | List events |
| POST | `/admin/events/{slug}/registrants/import` | Upload the CRM's registrants CSV |
| GET | `/admin/events/{slug}/attendees` | List an event's attendees |
| POST | `/admin/events/{slug}/agenda/import` | Upload the agenda spreadsheet |
| POST | `/admin/events/{slug}/booths/import` | Upload the booths spreadsheet |
| GET | `/admin/events/{slug}/booths` | List booths, owners and QR links |
| GET | `/admin/events/{slug}/booths/qr-sheet` | Printable page of every booth QR code |
| GET | `/admin/booths/{id}/qr.png` | One booth's QR code image |
| POST | `/admin/booths/{id}/rotate-qr` | New secret for a leaked QR code |
| GET | `/events/{slug}/agenda` | **Public** agenda, local times, no emails |

⚠️ `/admin` has no login yet. Local development only until the Google sign-in work lands.
