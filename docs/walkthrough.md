This guide is for newcomers who want to understand how race-strategy terms map to this codebase and API behavior.

It uses the same race/driver examples used across tests:
- `race_id=2024_monza_race`
- `driver=VER`

---

## 0) Quick start

Start dependencies/services:

```bash
docker compose up -d
uv run uvicorn backend.app.main:app --reload
```

(Optional UI)

```bash
uv run streamlit run frontend/app.py
```

---

## 1) Inspect available races

```bash
curl "http://127.0.0.1:8000/races"
```

Purpose:
- Confirm the backend is healthy and your selected race ID is supported.

---

## 2) Pull lap-level data (driver view)

```bash
curl "http://127.0.0.1:8000/race/2024_monza_race/laps?driver=VER"
```

Look at:
- `laps[].lap_number`
- `laps[].lap_time_seconds`
- `laps[].stint_number`
- `metadata` (how many rows were filtered during normalization)

What this teaches:
- The app drops unusable rows (e.g., no time / pit transition laps) before analytics.

---

## 3) Pull stint summaries

```bash
curl "http://127.0.0.1:8000/race/2024_monza_race/stints?driver=VER"
```

Look at:
- `stints[].start_lap` / `end_lap`
- `stints[].avg_lap_time_seconds`
- `stints[].degradation_slope`

What this teaches:
- A **stint** is a continuous tyre run.
- **Degradation slope** is a lap-time trend (seconds/lap).

---

## 4) Ask for strategy on a specific stint

```bash
curl "http://127.0.0.1:8000/race/2024_monza_race/strategy?driver=VER&stint_number=2"
```

Key response fields:
- `recommended_pit_window_start`
- `recommended_pit_window_end`
- `urgency`
- `confidence`
- `projected_lap_delta_seconds`
- `baseline_delta_seconds`

Interpretation:
- `urgency` is derived from degradation thresholds.
- `confidence` reflects data sufficiency and edge-case conditions.

---

## 5) Let backend auto-select stint

```bash
curl "http://127.0.0.1:8000/race/2024_monza_race/strategy?driver=VER"
```

Behavior:
- If `stint_number` is omitted, backend picks the latest "meaningful" stint.

---

## 6) Four demo scenarios to understand behavior

## Scenario A: Mid-race stint => normal recommendation

Test fixture shape:
- stint 2, laps 15→30, slope 0.03, race max lap 53.

Expected:
- Pit window exists.
- `urgency` is `medium`.
- `confidence` is `high`.

## Scenario B: Stint reaches race end => no future pit window

Test fixture shape:
- end lap == race max lap (53).

Expected:
- `recommended_pit_window_start/end` are `null`.
- urgency transitions to terminal state (`none` or `late_race`).

## Scenario C: Very short stint => low confidence

Test fixture shape:
- 3-lap stint, no reliable slope.

Expected:
- `confidence` is `low`.
- fallback logic is used.

## Scenario D: Invalid stint number

Request:

```bash
curl "http://127.0.0.1:8000/race/2024_monza_race/strategy?driver=VER&stint_number=99"
```

Expected:
- HTTP 404 with a clear message (`Stint 99 not found for driver`).

---

## 7) How to read strategy output safely

- Treat recommendation fields as heuristic guidance, not a full race simulator.
- In late-race situations, a valid result can intentionally contain no pit window.
- Always interpret `urgency` together with `confidence`.

---

## 8) Mapping to source files

- API orchestration: `backend/app/api/routes_races.py`
- Strategy logic: `backend/app/services/strategy.py`
- Stint + slope analytics: `backend/app/services/analytics.py`
- Normalization and filtering: `backend/app/services/normalization.py`
- Frontend rendering: `frontend/app.py`

