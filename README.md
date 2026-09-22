# Team Schedule Manager

A minimal, runnable prototype for **team scheduling**: a per-member timeline
workbench, multi-scale calendar views, and natural-language schedule creation.

There is no login and no permission model. Members are seeded locally and all
data lives in a single SQLite file, so the project runs end to end with no
external services.

> The web UI is in Chinese. All documentation in this repository is in English.

## Features

**Timeline workbench**

- One row per member, with a horizontal axis from 08:00 to 21:00.
- Click empty space to create a schedule at that moment.
- Click a card to edit, copy, drag to another slot, or delete it.
- Overlapping schedules for the same member on the same day are outlined in red.

**Views and filtering**

- Day, week, workweek (the default), and month scales.
- Filter by category, or search across titles and tags.
- Busy-hours total plus a per-category breakdown.

**Shared schedules**

- Adding participants writes one linked row per participant under a common
  `shared_id`. Editing or deleting any one of those rows updates the whole group.

**AI-assisted entry**

- Describe a schedule in one sentence and the backend returns a structured
  record plus conflict warnings, which you review before saving.
- Works against any OpenAI-compatible endpoint and falls back to a local
  rule-based parser, so the demo runs without an API key.

**Team and data management**

- Add or remove members and assign a colour to each.
- An admin-mode switch controls whether editing is allowed.
- Export the current view to ICS or CSV, and import external ICS/CSV files.
- Generate a copy-ready text digest for a single schedule or a member's whole day.

## Tech Stack

| Layer | Choice |
| --- | --- |
| Frontend | Vue 3, TypeScript, Element Plus, Axios, Vite |
| Backend | FastAPI, layered as router / service / repository |
| Storage | SQLite through the Python standard-library `sqlite3` module |
| AI | Any OpenAI-compatible `/chat/completions` endpoint, with a local regex fallback |
| Integrations | Feishu and DingTalk are placeholder stubs |

## Project Structure

```text
backend/
  app/
    main.py              # FastAPI entry point, CORS, startup hooks
    config.py            # Paths and LLM settings, read from the environment
    database.py          # SQLite connections and schema
    seed.py              # Demo members and schedules
    schemas.py           # Pydantic request and response models
    repositories/        # Data access layer, raw SQL
    services/            # Business logic: schedules, AI parsing, integrations
    routers/             # HTTP layer: users, schedules, ai, integration
  data/                  # SQLite file, created on first run and not committed
  requirements.txt
  .env.example
frontend/
  src/
    api/                 # Axios instance and typed endpoint helpers
    components/          # Calendar, member list, timeline, dialogs
    views/HomeView.vue   # Page composition
    types/               # Shared TypeScript types
    utils/date.ts        # Timeline constants and time helpers
  index.html
  vite.config.ts
  package.json
docs/
  API.md                 # Endpoint reference
```

## Getting Started

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

The API then listens on `http://127.0.0.1:8001`, with interactive docs at
`http://127.0.0.1:8001/docs`.

On first start the app creates `backend/data/schedule.db` and seeds six members
along with a few demo schedules.

Use port **8001**: that is the port the Vite dev proxy forwards `/api` to. If you
pick a different port, update the proxy target in `frontend/vite.config.ts`.

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://127.0.0.1:5173
```

Start the backend first. The dev server proxies `/api` to
`http://127.0.0.1:8001`.

Other scripts: `npm run build`, `npm run preview`, `npm run typecheck`.

## Configuration

The backend reads the following environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | Base URL of an OpenAI-compatible API |
| `LLM_API_KEY` | *(empty)* | API key; when empty, AI parsing uses local rules |
| `LLM_MODEL` | `gpt-4o-mini` | Model name sent to the endpoint |
| `LLM_TIMEOUT` | `30` | Request timeout, in seconds |

`backend/.env.example` lists these names, but note that the app reads plain
environment variables and does **not** load a `.env` file automatically. Export
them in your shell before starting the server:

```powershell
$env:LLM_BASE_URL = "https://api.deepseek.com/v1"
$env:LLM_API_KEY  = "sk-..."
$env:LLM_MODEL    = "deepseek-chat"
uvicorn app.main:app --reload --port 8001
```

Without a key, `POST /api/ai/parse` still works through the local parser and
reports `"source": "local"`.

## API Overview

Full request and response details live in [docs/API.md](docs/API.md).

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/health` | Health check |
| GET | `/api/users` | List members |
| POST | `/api/users` | Create a member |
| GET | `/api/users/{id}` | Fetch one member |
| DELETE | `/api/users/{id}` | Delete a member and their schedules |
| GET | `/api/users/{id}/schedules` | Member schedules, with an optional `date` filter |
| POST | `/api/users/{id}/schedules/share` | Share a member's day as text |
| GET | `/api/schedules` | Schedules for a date, with an optional `user_id` filter |
| POST | `/api/schedules` | Create a schedule |
| PUT | `/api/schedules/{id}` | Update a schedule |
| DELETE | `/api/schedules/{id}` | Delete a schedule |
| POST | `/api/schedules/{id}/share` | Share one schedule as text |
| POST | `/api/ai/parse` | Parse natural language into a structured schedule |
| GET | `/api/integration/{channel}/status` | Integration stub status |
| POST | `/api/integration/{channel}/messages/push` | Integration stub message push |
| POST | `/api/integration/{channel}/org/sync` | Integration stub org sync |

`{channel}` is `feishu` or `dingtalk`. Share channels are `internal`, `feishu`,
or `dingtalk`.

## Data Model

### `users`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | integer | Primary key |
| `name` | text | Unique |
| `role` | text | Job title |
| `color` | text | Hex colour used by the UI |
| `created_at` | text | Local timestamp |

### `schedules`

| Column | Type | Notes |
| --- | --- | --- |
| `id` | integer | Primary key |
| `user_id` | integer | Owner, references `users.id` |
| `title` | text | |
| `date` | text | `YYYY-MM-DD` |
| `start_time`, `end_time` | text | `HH:MM` |
| `location`, `note` | text | |
| `category` | text | One of `会议`, `开发`, `评审`, `复盘`, `其他` |
| `recurrence` | text | Persisted only; no repeater engine |
| `participants` | text | JSON array of user IDs |
| `reminder` | integer | Persisted only; no notification job |
| `shared_id` | text | Links rows that were created together |
| `source` | text | `manual` or `seed` |
| `created_at`, `updated_at` | text | Local timestamps |

Indexes: `idx_schedules_date`, `idx_schedules_user_date`.

## Design Notes and Limitations

- This is a prototype. There is no authentication, authorization, or
  multi-tenancy, and CORS is open to all origins.
- Times are compared as `HH:MM` strings. That is correct for same-day ranges but
  does not model schedules that run past midnight.
- Conflict detection is a single interval-overlap query: same member, same date,
  `start_time < other.end_time` and `end_time > other.start_time`.
- The timeline is hand-built CSS rather than a charting library. The display
  range, row height, and hour width are constants in
  `frontend/src/utils/date.ts`.
- `recurrence` and `reminder` are saved from the form, but nothing acts on them
  yet.
- The Feishu and DingTalk endpoints return `code: "PLACEHOLDER"`. The intended
  integration points are marked with TODO comments in
  `backend/app/services/integration_service.py`.
- Persistence is raw SQL over `sqlite3`. The repository layer is deliberately
  small so it can be swapped for SQLAlchemy and Alembic once queries grow.