from fastapi import FastAPI
from backend.app.api.routes_races import router as races_router
from backend.app.services.ingestion import load_session, get_raw_laps

app = FastAPI()
app.include_router(races_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/debug/laps")
def debug_laps():
    session = load_session("2024_monza_race")
    laps = get_raw_laps(session)

    return {"columns": list(laps.columns), "row_count": len(laps)}
