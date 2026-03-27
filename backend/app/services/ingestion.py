import fastf1
from backend.app.config import SUPPORTED_RACES

fastf1.Cache.enable_cache("cache")


def load_session(race_id: str):
    race = SUPPORTED_RACES.get(race_id)
    if not race:
        raise ValueError(f"Unknown race_id: {race_id}")

    session = fastf1.get_session(
        race["season"],
        race["event_name"],
        race["session_name"],
    )

    session.load()
    return session


def get_raw_laps(session):
    return session.laps
