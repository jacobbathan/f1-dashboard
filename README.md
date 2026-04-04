# F1 Race Analytics System

[Live demo available](https://f1-dashboard-frontend-production.up.railway.app/)

A FastAPI backend and Streamlit frontend for ingesting Formula 1 race telemetry, normalizing lap data, building stint-level analytics, and returning heuristic pit-window recommendations.

---

## Why this project

This project focuses on backend API design, data normalization, persistence, caching, and lightweight analytics on top of FastF1 race-session data. The goal is to turn raw session data into structured lap, stint, and strategy outputs through a small but inspectable application stack.

---

## Features

- FastF1 session ingestion with local disk caching
- Lap normalization with filter metadata
- Stint aggregation with pace and degradation-slope calculations
- Strategy recommendation endpoint with in-memory and persisted reuse
- Streamlit dashboard for race, driver, and stint exploration

---

## Tradeoffs and Limitations

- Recommendation logic is heuristic and explainable rather than simulation-based.
- Benchmark figures reflect measured repeated requests, not guaranteed first-request latency.
- The frontend is intentionally lightweight and acts as a demo interface over the API.
- Supported race sessions are currently limited to the IDs configured in `backend/app/config/__init__.py`.

---

## Architecture

```text
FastF1 session data
    -> ingestion + local cache
    -> lap normalization
    -> stint analytics
    -> strategy estimation
    -> FastAPI endpoints
    -> Streamlit dashboard
```

### Backend

| Layer | Location | Responsibility |
| --- | --- | --- |
| App entrypoint | `backend/app/main.py` | FastAPI startup, table creation, cache setup, router mounting |
| Routes | `backend/app/api/routes_races.py` | `/health`, `/races`, `/race/{race_id}/laps`, `/race/{race_id}/stints`, `/race/{race_id}/strategy` |
| Config | `backend/app/config/` | Supported race IDs and strategy tuning constants |
| Domain models | `backend/app/domain/models.py` | Internal dataclasses for normalized laps, stints, and recommendations |
| Schemas | `backend/app/schemas/` | API request/response serialization models |
| Services | `backend/app/services/` | Ingestion, normalization, analytics, strategy, cache, and persistence logic |
| Database layer | `backend/app/db/` | SQLAlchemy base, engine, and ORM table mappings |

### Frontend

| File | Responsibility |
| --- | --- |
| `frontend/app.py` | Streamlit dashboard for selecting a race and driver, viewing laps and stints, and rendering strategy output |

---

## Request Flow

**`GET /race/{race_id}/laps`**

1. Validate the requested race ID and driver code.
2. Check the in-memory laps cache.
3. Check persisted session and lap records in the database.
4. On cache miss, load from FastF1, normalize laps, persist results, cache them, and return the filtered driver view.

**`GET /race/{race_id}/stints`**

Reuse the normalized laps pipeline, filter to one driver, and aggregate laps into stint summaries with pace and degradation slope.

**`GET /race/{race_id}/strategy`**

Reuse cached or computed lap data, build driver stints, derive race length from normalized laps, and return a heuristic pit-window recommendation for the requested or latest meaningful stint.

---

## Performance Benchmark

Measured benchmark target: `GET /race/{race_id}/strategy?driver=VER`

- Median repeat-request latency before persistence/caching: **3.49s**
- Median repeat-request latency after persistence/caching: **8.6ms**
- Improvement: **99.75%**

These measurements correspond to the repository benchmark workflow in `scripts/benchmark_latency.py`.

_Note: this benchmark reflects warm repeated requests with persisted and cached state, not guaranteed first-request latency under all conditions._

---

## Analysis Method

The analytics pipeline stays intentionally simple and inspectable:

1. Filter incomplete or non-representative laps.
2. Group valid laps into stints by driver.
3. Remove slower outliers with an IQR-based rule.
4. Fit a linear trend to estimate degradation over lap number.

This keeps the analysis reproducible and explainable without introducing a full race simulation model.

---

## Recommendation Logic

Strategy output is generated from threshold-based rules applied to the selected stint.

Inputs include:

- degradation slope
- current stint length
- current lap and remaining race laps
- configured urgency thresholds and projection horizon

Outputs include:

- recommended pit-window start and end
- urgency and confidence
- projected short-term lap delta
- baseline strategy metadata

The implementation lives in `backend/app/services/strategy.py`, and the tunable constants live in `backend/app/config/strategy.py`.

---

## Prerequisites

- Python 3.12+
- PostgreSQL
- `uv` for the documented install and run commands
- [FastF1](https://github.com/theOehrly/Fast-F1)

---

## Installation

```bash
git clone git@github.com:jacobbathan/f1-dashboard.git
cd f1-dashboard
python -m venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

Set up your environment:

```bash
cp .env.example .env
# Edit .env if needed
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/f1dashboard
```

---

## Running

### Local services

Backend:

```bash
uv run uvicorn backend.app.main:app --reload
```

Frontend:

```bash
uv run streamlit run frontend/app.py
```

The frontend defaults to `http://127.0.0.1:8000` for backend requests. Override this with the `BACKEND_URL` environment variable when needed.

### Docker Compose

To run Postgres, the API, and the frontend together:

```bash
docker compose up --build
```

---

## API Reference

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Health check for the backend |
| `GET` | `/races` | List supported races |
| `GET` | `/race/{race_id}/laps` | Driver lap data and normalization metadata |
| `GET` | `/race/{race_id}/stints` | Driver stint summaries |
| `GET` | `/race/{race_id}/strategy` | Heuristic pit-window recommendation |

Interactive API docs are available at `http://127.0.0.1:8000/docs` while the backend is running.

---

## Configuration

### Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/f1dashboard` | SQLAlchemy connection string used by the backend |
| `BACKEND_URL` | `http://127.0.0.1:8000` | Backend base URL used by the Streamlit frontend |
| `FASTF1_CACHE_DIR` | `cache` | Local directory for FastF1 disk cache |

`.env.example` currently includes `DATABASE_URL`. `BACKEND_URL` and `FASTF1_CACHE_DIR` are optional overrides.

### Code Configuration

| Location | Purpose |
| --- | --- |
| `backend/app/config/__init__.py` | Supported race IDs and their season/session metadata |
| `backend/app/config/strategy.py` | Strategy thresholds, projection horizon, urgency windows, and baseline labels |

---

## Project Structure

```text
f1-dashboard/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI route handlers
│   │   ├── config/       # Supported races and strategy constants
│   │   ├── db/           # SQLAlchemy engine, base, and ORM tables
│   │   ├── domain/       # Internal dataclasses
│   │   ├── schemas/      # API response models
│   │   ├── services/     # Ingestion, normalization, analytics, strategy, cache, persistence
│   │   └── main.py       # FastAPI app entrypoint
│   └── tests/            # Backend-focused tests
├── frontend/
│   └── app.py            # Streamlit dashboard
├── scripts/              # Dev and benchmark scripts
├── tests/                # Test suite and shared fixtures
├── docs/                 # Project and deployment docs
├── railway/              # Railway service configs
├── cache/                # Local FastF1 cache data at runtime; keep untracked
├── main.py               # Root compatibility entrypoint for Railway
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
├── .env.example
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Testing

- Run the main test suite with `pytest`.
- Targeted checks are available in `tests/` and `scripts/`, including `tests/test_strategy.py`, `tests/test_benchmark_latency.py`, `scripts/test_normalization.py`, and `scripts/test_fastf1.py`.
- The benchmark workflow lives in `scripts/benchmark_latency.py`.

---

## Contributing

1. Create a feature branch for your change.
2. Run the relevant tests and checks.
3. Open a pull request with a clear summary and the commands you ran to verify the change.

---

## License

[MIT](./LICENSE)
