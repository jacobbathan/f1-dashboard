from pathlib import Path

import fastf1
import pandas as pd

from backend.app.config import SUPPORTED_RACES

CACHE_DIR = Path("cache")


def enable_cache() -> None:
    """Enable the FastF1 disk cache at CACHE_DIR.

    Separated from module-level execution so tests can patch or skip it.
    Should be called once at application startup via the FastAPI lifespan.
    """
    fastf1.Cache.enable_cache(str(CACHE_DIR))


def load_session(race_id: str) -> fastf1.core.Session:
    """Load and return a FastF1 session for the given race identifier.

    Args:
        race_id: Key from SUPPORTED_RACES (e.g. ``"2024_monza_race"``).

    Returns:
        A fully loaded FastF1 Session object.

    Raises:
        ValueError: If race_id is not in SUPPORTED_RACES.
    """
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


def get_raw_laps(session: fastf1.core.Session) -> pd.DataFrame:
    """Return the raw laps DataFrame from a loaded FastF1 session.

    Args:
        session: A fully loaded FastF1 Session object.

    Returns:
        DataFrame containing all lap records for the session.
    """
    return session.laps
