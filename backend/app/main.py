from fastapi import FastAPI
from backend.app.api.routes_races import router as races_router

app = FastAPI()
app.include_router(races_router)


@app.get("/health")
def health():
    return {"status": "ok"}
