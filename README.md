## Local development

### Run the full stack with Docker

Make sure Docker is installed and running, then build and start Postgres, the FastAPI backend, and the Streamlit frontend:

```bash
docker compose up --build
```

The services will be available at:
- Frontend: `http://127.0.0.1:8501`
- Backend API: `http://127.0.0.1:8000`

To stop the stack:

```bash
docker compose down
```

### Run services manually

If you only want Docker-managed Postgres for local development:

```bash
docker compose up -d db
```

Then start the backend and frontend from your local environment:

```bash
uv run uvicorn backend.app.main:app --reload
```

```bash
uv run streamlit run frontend/app.py
```

### Deploy on Railway

Railway can recover the current auto-connected backend service from the repo-root
config at [railway.toml](/home/antigo/Code/f1-dashboard/railway.toml).

For the cleaner long-term setup, Railway should deploy this repo as separate
Dockerfile-based services, not as a Compose stack.

- Auto-connected backend config: [railway.toml](/home/antigo/Code/f1-dashboard/railway.toml)
- Backend config: [railway/backend/railway.toml](/home/antigo/Code/f1-dashboard/railway/backend/railway.toml)
- Frontend config: [railway/frontend/railway.toml](/home/antigo/Code/f1-dashboard/railway/frontend/railway.toml)
- Deployment guide: [docs/railway.md](/home/antigo/Code/f1-dashboard/docs/railway.md)

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
