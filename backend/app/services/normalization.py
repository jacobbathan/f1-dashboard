from dataclasses import dataclass
import logging

import pandas as pd

from backend.app.domain.models import NormalizedLap

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class LapFilterStats:
    """Summary of lap rows kept and filtered during normalization."""

    total_raw_rows: int
    filtered_no_time: int
    filtered_pit_laps: int
    valid_laps_returned: int


def timedelta_to_seconds(value: object) -> float | None:
    """Convert pandas/py timedelta-like values to float seconds."""
    if value is None:
        return None

    if pd.isna(value):
        return None

    if hasattr(value, "total_seconds"):
        try:
            return float(value.total_seconds())
        except (AttributeError, TypeError, ValueError):
            return None

    return None


def safe_int(value: object) -> int | None:
    """Convert a value to int if present and valid."""
    if value is None:
        return None

    if pd.isna(value):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def safe_str(value: object) -> str | None:
    """Convert a value to string if present and valid."""
    if value is None:
        return None

    if pd.isna(value):
        return None

    text = str(value).strip()
    return text if text else None


def normalize_laps(
    raw_laps_df: pd.DataFrame,
    race_id: str,
) -> tuple[list[NormalizedLap], LapFilterStats]:
    """Map raw FastF1 laps dataframe into stable internal lap models."""
    normalized_laps: list[NormalizedLap] = []
    total_rows = len(raw_laps_df)
    filtered_no_time = 0
    filtered_pit_laps = 0

    for _, row in raw_laps_df.iterrows():
        driver_code = safe_str(row.get("Driver"))
        lap_number = safe_int(row.get("LapNumber"))
        lap_time_seconds = timedelta_to_seconds(row.get("LapTime"))

        # Skip rows that do not have the minimum fields needed to identify a lap
        if driver_code is None or lap_number is None:
            continue
        if lap_time_seconds is None:
            filtered_no_time += 1
            continue

        pit_in_time = row.get("PitInTime")
        pit_out_time = row.get("PitOutTime")
        if pit_in_time is not None and not pd.isna(pit_in_time):
            filtered_pit_laps += 1
            continue
        if pit_out_time is not None and not pd.isna(pit_out_time):
            filtered_pit_laps += 1
            continue
        # SAFETY CAR HANDLING
        # FastF1's TrackStatus column can indicate safety car periods, but its
        # reliability varies by session. For now we explicitly skip
        # safety-car-specific filtering. If TrackStatus proves reliable, laps
        # under safety car (status codes 4, 6, 7) could be excluded here.

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

    filter_stats = LapFilterStats(
        total_raw_rows=total_rows,
        filtered_no_time=filtered_no_time,
        filtered_pit_laps=filtered_pit_laps,
        valid_laps_returned=len(normalized_laps),
    )
    logger.info(
        "Normalized %s laps, filtered {'no_time': %s, 'pit_lap': %s}"
        " from %s raw rows",
        filter_stats.valid_laps_returned,
        filter_stats.filtered_no_time,
        filter_stats.filtered_pit_laps,
        filter_stats.total_raw_rows,
    )
    return normalized_laps, filter_stats


def filter_driver_laps(
    laps: list[NormalizedLap],
    driver_code: str,
) -> list[NormalizedLap]:
    """Return laps for a single driver, sorted by lap number."""
    target = driver_code.upper().strip()

    return sorted(
        [lap for lap in laps if lap.driver_code == target],
        key=lambda lap: lap.lap_number,
    )
