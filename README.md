## Local development

### Start Postgres with Docker

Make sure Docker is installed and running, then start the local database:

```bash
docker compose up -d
```

```bash
uv run uvicorn backend.app.main:app --reload
```

```bash
uv run streamlit run frontend/app.py
```

to run them
im working on containerizing this eventually.

---

## F1 terms for software engineers (quick glossary)

If you're new to Formula One, these are the domain terms that show up in this codebase and can be easy to misread from a pure software perspective.

### Core strategy terms

- **Stint**: A continuous run of laps between pit stops. In this project, a stint is grouped by a driver's `stint_number` and used to compute averages and degradation slope.
- **Pit window**: A recommended lap range where pitting is expected to be advantageous (for example, lap 20-22), rather than a single exact lap.
- **Undercut**: Pitting **earlier** than a nearby rival to gain time on fresher tyres while they stay out.
- **Overcut**: Pitting **later** than a nearby rival, hoping your pace on older tyres remains strong enough to gain track position once both stops complete.
- **Delta**: A time difference. In live timing/radio it can be your gap to another car, or your difference vs a target pace/time.

### Tyre/performance terms

- **Tyre degradation ("deg")**: Tyre performance dropping as laps accumulate (less grip, slower lap time).
- **"Falling off a cliff"**: A sharp tyre drop-off where pace suddenly gets much worse and recovery is unlikely.
- **Tyre compound**: Hard/medium/soft dry-weather compounds with different grip vs longevity trade-offs.

### Race-rule context that impacts strategy

- In normal dry races, drivers must use at least two different dry-weather tyre specifications during the race (unless wet/suspended-race exceptions apply).
- This rule is one reason pit strategy is central: teams are balancing tyre life, traffic, pace drop-off, and race position.

### How this maps to code in this repo

- `backend/app/services/analytics.py` computes per-stint averages and degradation slopes.
- `backend/app/services/strategy.py` turns degradation and stint state into urgency + recommended pit window.
- `frontend/app.py` surfaces stint metrics and recommendation outputs.
