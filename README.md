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
