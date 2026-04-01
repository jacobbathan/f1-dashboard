# Railway deployment

## Fastest recovery for an auto-connected service

If Railway auto-created a single Python service from the repo root, it may try
to boot `uvicorn main:app`. This repo now supports that recovery path:

- Root compatibility entrypoint: `main.py`
- Root Railway config: `/railway.toml`

That root config forces Dockerfile-based backend deploys with
`Dockerfile.backend` and a `/health` healthcheck, so Railway does not need to
guess a Python start command.

This project should be deployed to Railway as three services in one project:

- `backend`: FastAPI service built from `Dockerfile.backend`
- `frontend`: Streamlit service built from `Dockerfile.frontend`
- `postgres`: Railway PostgreSQL service

Do not deploy `docker-compose.yml` to Railway. Railway should build each app service directly from its Dockerfile.

## Required service names

Use these service names exactly:

- `backend`
- `frontend`
- `postgres`

The frontend config below assumes the backend private hostname will be `backend.railway.internal`.

## Config-as-code paths

Set each Railway service to use the matching repo config file:

- Backend service config path: `/railway/backend/railway.toml`
- Frontend service config path: `/railway/frontend/railway.toml`

## Environment variables

### Backend

Set these variables on the `backend` service:

- `DATABASE_URL`: reference the `postgres` service `DATABASE_URL`
- `PORT=8000`

### Frontend

Set these variables on the `frontend` service:

- `BACKEND_URL=http://backend.railway.internal:8000`
- `PORT=8501`

## Networking

- Generate a public Railway domain only for the `frontend` service.
- Leave the `backend` service private.
- Internal service-to-service traffic should use `http`, not `https`.

## Deploy flow

1. Create a Railway project.
2. Add a PostgreSQL service and rename it to `postgres`.
3. Add a service from this repo, rename it to `backend`, and set its config path to `/railway/backend/railway.toml`.
4. Add another service from this repo, rename it to `frontend`, and set its config path to `/railway/frontend/railway.toml`.
5. Set the environment variables listed above.
6. Deploy both services.
7. Generate a public domain for `frontend`.

## Runtime notes

- The backend exposes a health endpoint at `/health`.
- The backend creates tables on startup, so no separate migration command is required for the current schema.
- FastF1 cache is ephemeral on Railway in this setup.
