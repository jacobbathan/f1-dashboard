# F1 Race Analytics System

[Live demo avaliable](https://f1-dashboard-frontend-production.up.railway.app/)

A backend analytics system for ingesting and processing Formula 1 race telemetry, generating driver performance summaries and recommendation outputs through a FastAPI service with a lightweight Streamlit demo interface.

---

## Why this project

I built this project to practice backend API design, data normalization, persistence, and caching on top of a real telemetry dataset. The goal was to create a system that could process race-session data into structured analysis outputs and demonstrate measurable performance improvements on repeated requests.

---

## Features

- Race-session ingestion from FastF1 with local caching
- Data normalization and filtering for lap-by-lap telemetry
- Strategy recommendation API with persisted session reuse
- Lightweight demo UI for inspecting outputs and recommendations

---

## Tradeoffs and Limitations

- Recommendation logic is heuristic and explainable rather than simulation-based
- Benchmarked improvement reflects repeated warm requests
- Frontend is intentionally lightweight and serves as a demo surface rather than a full product UI
- Project scope is focused on one analysis workflow rather than broad race modeling

---

## Architecture

```
FastF1 raw laps
    └── Normalization + filtering (drop missing/pit-transition laps)
        └── Stint aggregation (avg pace + degradation slope)
            └── Strategy estimation (pit window + urgency + delta)
                └── FastAPI REST endpoints
                    └── Streamlit dashboard
```

### Backend (`backend/`)

| Layer         | Location                  | Responsibility                                                          |
| ------------- | ------------------------- | ----------------------------------------------------------------------- |
| App init      | `app/main.py`             | DB schema creation, FastF1 cache setup, route mounting                  |
| Routes        | `app/api/routes_races.py` | `/races`, `/race/{id}/laps`, `/race/{id}/stints`, `/race/{id}/strategy` |
| Ingestion     | data layer                | Fetch session via FastF1, convert to internal models                    |
| Normalization | data layer                | Filter bad laps, produce `NormalizedLap` records, track filter stats    |
| Analytics     | domain layer              | Group laps into stints, filter outliers, compute pace + slope           |
| Strategy      | domain layer              | `estimate_pit_window()` — thresholds → urgency → window → delta         |
| Storage       | `SQLAlchemy` / Postgres   | Persist sessions, lap rows, normalization metadata                      |

### Frontend (`frontend/`)

| File     | Responsibility                                                                                            |
| -------- | --------------------------------------------------------------------------------------------------------- |
| `app.py` | Single-page Streamlit dashboard — race/driver/stint selection, KPIs, charts, tables, recommendation cards |

---

## Request Flow

**`GET /race/{id}/laps`**

1. Validate race + driver query params
2. Check in-memory laps cache
3. Check persisted DB session/laps
4. Fetch from FastF1, normalize, persist, cache, return

**`GET /race/{id}/stints`**
Reuses normalized laps pipeline → filters to one driver → builds stint aggregates (avg pace + slope).

**`GET /race/{id}/strategy`**
Optionally returns cached recommendation. Otherwise computes from driver stints + race max lap, handling edge cases (missing data, late race, insufficient laps).

---

## Performance Benchmark

- Benchmarked endpoint: `GET /race/{id}/strategy?driver=VER`
- Median repeat-request latency before persistence/caching: **3.49s**
- Median repeat-request latency after persistence/caching: **8.6ms**
- Improvement: **99.75%**

  _Note: this benchmark reflects warm repeated requests with persisted/cached state, not guaranteed first-request latency under all conditions_

---

## Analysis Method

The system estimates performance trends from lap-by-lap session data using a simple, explainable pipeline:

1. Filter incomplete or non-representative laps
2. Group valid laps into session segments
3. Remove statistical outliers using an IQR-based rule
4. Fit a linear trend to estimate performance change over time

This keeps the analysis lightweight, reproducible, and easy to inspect, rather than relying on a more complex simulation model.

---

## Recommendation Logic

Recommendation outputs are generated from simple threshold-based rules applied to the analyzed session trends.

The system uses:

- estimated performance change over time
- remaining session length
- available valid data
- configurable thresholds for urgency and recommendation timing

Outputs include:

- recommendation window
- urgency level
- projected short-term performance delta
- confidence level based on available evidence

The logic is intentionally heuristic and explainable rather than simulation-based.

---

## Prerequisites

- Python 3.11+
- PostgreSQL (local or remote)
- [FastF1](https://github.com/theOehrly/Fast-F1)

---

## Installation

```bash
git clone https://github.com/your-org/f1-strategy-analyzer.git
cd f1-strategy-analyzer
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Set up your environment:

```bash
cp .env.example .env
# Edit .env and set DATABASE_URL, e.g.:
# DATABASE_URL=postgresql://user:password@localhost:5432/f1_strategy
```

---

## Running

**Backend:**

```bash
uv run uvicorn backend.app.main:app --reload
```

**Frontend:**

```bash
uv run streamlit run frontend/app.py
```

The Streamlit dashboard expects the backend at `http://localhost:8000` by default. Override with the `BACKEND_URL` environment variable.

---

## API Reference

| Method | Endpoint                   | Description                     |
| ------ | -------------------------- | ------------------------------- |
| `GET`  | `/races`                   | List available races            |
| `GET`  | `/race/{race_id}/laps`     | Lap data for a race/driver      |
| `GET`  | `/race/{race_id}/stints`   | Stint aggregates (pace + slope) |
| `GET`  | `/race/{race_id}/strategy` | Pit-window recommendation       |

Full schema available at `http://localhost:8000/docs` (Swagger UI) when the backend is running.

---

## Configuration

| Variable                       | Default                     | Description                            |
| ------------------------------ | --------------------------- | -------------------------------------- |
| `DATABASE_URL`                 | `postgresql://localhost/f1` | SQLAlchemy connection string           |
| `BACKEND_URL`                  | `http://localhost:8000`     | Backend base URL (frontend)            |
| `MIN_LAPS_FOR_SLOPE`           | `4`                         | Minimum laps required to compute slope |
| `LOW_DEGRADATION_THRESHOLD`    | `0.02`                      | Slope threshold for low urgency        |
| `MEDIUM_DEGRADATION_THRESHOLD` | `0.05`                      | Slope threshold for medium urgency     |
| `PROJECTION_HORIZON_LAPS`      | `4`                         | Lookahead laps for delta projection    |

---

## Project Structure

```
f1-strategy-analyzer/
├── backend/
│   └── app/
│       ├── main.py               # FastAPI app init, lifecycle, DB setup
│       ├── api/
│       │   └── routes_races.py   # All race/lap/stint/strategy endpoints
│       ├── ingestion/            # FastF1 fetch + normalization
│       ├── analytics/            # Stint building + degradation regression
│       ├── strategy/             # estimate_pit_window() + thresholds
│       └── storage/              # SQLAlchemy models + in-memory cache
├── frontend/
│   └── app.py                    # Streamlit dashboard
├── .env.example
├── requirements.txt
└── README.md
```

---

## Testing

- run tests with `pytest`
- benchmark script/tests included for latency verification
- core happy-path and validation behaviors covered

---

## Contributing

1. Fork the repo and create a branch: `git checkout -b feature/your-feature`
2. Run tests: `pytest`
3. Open a pull request with a clear description of the change.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for full guidelines.

---

## License

[MIT](./LICENSE)
