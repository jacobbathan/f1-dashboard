# F1 Strategy Analyzer

A full-stack pipeline for analyzing Formula 1 race data, computing per-driver tire degradation, and generating heuristic pit-stop window recommendations — served via a FastAPI backend and visualized in a Streamlit dashboard.

---

## Features

- **Live + historical race data** pulled from [FastF1](https://github.com/theOehrly/Fast-F1) with on-disk caching
- **Tire degradation modeling** — linear regression (slope in s/lap) per stint, with IQR-based outlier filtering
- **Pit strategy recommendations** — urgency classification, pit-window start/end, projected lap-time delta, and confidence score
- **Three-tier data layer** — in-memory cache → Postgres persistence → upstream FastF1 fallback
- **Interactive dashboard** — KPIs, lap-time charts, stint tables, and recommendation cards

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

## Tire Degradation Methodology

Degradation is expressed as the **slope of lap time vs. lap number** (seconds/lap). A positive slope = tires getting slower.

1. **Filter** — drop laps with no recorded time; drop pit-in/pit-out transition laps.
2. **Group** — split remaining laps into stints by `stint_number`.
3. **Outlier removal** — for stints with ≥ 3 laps, compute IQR quartiles and discard laps above `Q3 + 1.5 × IQR`.
4. **Regression** — run `np.polyfit(lap_numbers, lap_times, 1)` on the filtered set; the leading coefficient is the degradation slope.

---

## Strategy Estimation

Calls `estimate_pit_window(stints, race_max_lap, stint_number?)`.

**Urgency thresholds:**

| Slope (s/lap) | Urgency  | Pit window offset |
| ------------- | -------- | ----------------- |
| < 0.02        | `low`    | +4 to +6 laps     |
| 0.02 – 0.05   | `medium` | +2 to +4 laps     |
| ≥ 0.05        | `high`   | +1 to +2 laps     |

**Confidence:**

- `low` — fewer than `MIN_LAPS_FOR_SLOPE` (4) laps, or slope is `None`
- `medium` — stint length ≤ 7 laps
- `high` — stint length > 7 laps

**Edge cases:**

- Already past race end → urgency `none`
- Insufficient data → fallback medium window, urgency `unknown`, confidence `low`
- Window beyond race end → urgency `late_race`

**Delta outputs:**

- _Projected lap delta_: `slope × min(PROJECTION_HORIZON_LAPS, remaining_laps)` (horizon = 4 laps)
- _Baseline delta_: compares recommended pit start vs. a `pit_at_stint_midpoint` baseline

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

## Contributing

1. Fork the repo and create a branch: `git checkout -b feature/your-feature`
2. Run tests: `pytest`
3. Open a pull request with a clear description of the change.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for full guidelines.

---

## License

[MIT](./LICENSE)
