from typing import List, Optional

import pandas as pd

from backend.app.domain.models import NormalizedLap


def timedelta_to_seconds(value) -> Optional[float]:
    """Convert pandas/py timedelta-like values to float seconds."""
    if value is None:
        return None

    if pd.isna(value):
        return None

    if hasattr(value, "total_seconds"):
        try:
            return float(value.total_seconds())
        except Exception:
            return None

    return None


def safe_int(value) -> Optional[int]:
    """Convert a value to int if present and valid."""
    if value is None:
        return None

    if pd.isna(value):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def safe_str(value) -> Optional[str]:
    """Convert a value to string if present and valid."""
    if value is None:
        return None

    if pd.isna(value):
        return None

    text = str(value).strip()
    return text if text else None


def normalize_laps(raw_laps_df: pd.DataFrame, race_id: str) -> List[NormalizedLap]:
    """Map raw FastF1 laps dataframe into stable internal lap models."""
    normalized_laps: List[NormalizedLap] = []

    for _, row in raw_laps_df.iterrows():
        driver_code = safe_str(row.get("Driver"))
        lap_number = safe_int(row.get("LapNumber"))
        lap_time_seconds = timedelta_to_seconds(row.get("LapTime"))

        # Skip rows that do not have the minimum fields needed to identify a lap
        if driver_code is None or lap_number is None:
            continue
        if lap_time_seconds is None:
            continue

        lap = NormalizedLap(
            race_id=race_id,
            driver_code=driver_code,
            lap_number=lap_number,
            lap_time_seconds=lap_time_seconds,
            tyre_compound=safe_str(row.get("Compound")),
            tyre_life_laps=safe_int(row.get("TyreLife")),
            stint_number=safe_int(row.get("Stint")),
            position=safe_int(row.get("Position")),
        )
        normalized_laps.append(lap)

    return normalized_laps


def filter_driver_laps(
    laps: List[NormalizedLap], driver_code: str
) -> List[NormalizedLap]:
    """Return laps for a single driver, sorted by lap number."""
    target = driver_code.upper().strip()

    return sorted(
        [lap for lap in laps if lap.driver_code == target],
        key=lambda lap: lap.lap_number,
    )
