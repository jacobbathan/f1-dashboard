"""Persist and reload normalized race data via SQLAlchemy ORM."""

from __future__ import annotations

from sqlalchemy import select

from backend.app.config import RaceConfig
from backend.app.db.engine import SessionLocal
from backend.app.db.tables import LapRecord
from backend.app.db.tables import SessionRecord
from backend.app.domain.models import NormalizedLap


def save_session_data(
    race_id: str,
    race_config: RaceConfig,
    laps: list[NormalizedLap],
) -> None:
    """Persist one session and its normalized lap records.

    Args:
        race_id: Stable race/session identifier.
        race_config: Supported-race config with season, event_name,
            and session_name fields.
        laps: Normalized lap rows to persist.
    """
    with SessionLocal() as session:
        session.add(
            SessionRecord(
                id=race_id,
                season=int(race_config["season"]),
                event_name=str(race_config["event_name"]),
                session_name=str(race_config["session_name"]),
            )
        )
        session.flush()
        session.add_all(
            [
                LapRecord(
                    session_id=race_id,
                    driver_code=lap.driver_code,
                    lap_number=lap.lap_number,
                    lap_time_seconds=lap.lap_time_seconds,
                    compound=lap.tyre_compound,
                    tyre_life_laps=lap.tyre_life_laps,
                    stint_number=lap.stint_number,
                    position=lap.position,
                )
                for lap in laps
            ]
        )
        session.commit()


def session_exists(race_id: str) -> bool:
    """Return whether a persisted session exists for the given race ID."""
    with SessionLocal() as session:
        return session.get(SessionRecord, race_id) is not None


def load_laps_from_db(race_id: str) -> list[NormalizedLap]:
    """Load all persisted laps for a session and map them to domain models.

    Args:
        race_id: Stable race/session identifier.

    Returns:
        All stored laps for the session, ordered by lap then driver.
    """
    statement = (
        select(LapRecord)
        .where(LapRecord.session_id == race_id)
        .order_by(LapRecord.lap_number, LapRecord.driver_code, LapRecord.id)
    )

    with SessionLocal() as session:
        rows = session.scalars(statement).all()

    return [
        NormalizedLap(
            race_id=row.session_id,
            driver_code=row.driver_code,
            lap_number=row.lap_number,
            lap_time_seconds=row.lap_time_seconds,
            tyre_compound=row.compound,
            tyre_life_laps=row.tyre_life_laps,
            stint_number=row.stint_number,
            position=row.position,
        )
        for row in rows
    ]
