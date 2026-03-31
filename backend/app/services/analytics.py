from collections import defaultdict

import numpy as np

from backend.app.domain.models import DriverStint, NormalizedLap
from backend.app.services.normalization import filter_driver_laps


def filter_timed_laps(laps: list[NormalizedLap]) -> list[NormalizedLap]:
    """Drop laps that do not have a usable lap time before analytics.

    Normalization already drops laps without timings, but analytics keeps
    this guard so direct callers or future pipeline changes do not break
    slope/pace math.
    """
    return [lap for lap in laps if lap.lap_time_seconds is not None]


def filter_outlier_laps(
    laps: list[NormalizedLap],
    threshold: float = 1.5,
) -> list[NormalizedLap]:
    """Remove laps significantly slower than the median using IQR filtering."""
    if len(laps) < 3:
        return laps

    times = [lap.lap_time_seconds for lap in laps if lap.lap_time_seconds is not None]
    if not times:
        return laps

    sorted_times = sorted(times)
    q1 = sorted_times[len(sorted_times) // 4]
    q3 = sorted_times[3 * len(sorted_times) // 4]
    iqr = q3 - q1
    upper_bound = q3 + threshold * iqr
    return [
        lap
        for lap in laps
        if lap.lap_time_seconds is not None
        and lap.lap_time_seconds <= upper_bound
    ]


def average_lap_time_seconds(laps: list[NormalizedLap]) -> float | None:
    """Return the mean lap time in seconds, or None if no timed laps exist."""
    lap_times = [lap.lap_time_seconds for lap in filter_timed_laps(laps)]
    if not lap_times:
        return None

    return sum(lap_times) / len(lap_times)


def stint_lap_time_slope(laps: list[NormalizedLap]) -> float | None:
    """Estimate tyre degradation as the linear slope of lap times per lap.

    Returns:
        Slope in seconds/lap (positive = degrading). None if fewer than
        2 timed laps are available.
    """
    valid_laps = sorted(
        filter_timed_laps(laps),
        key=lambda lap: lap.lap_number,
    )
    if len(valid_laps) < 2:
        return None

    lap_numbers = [lap.lap_number for lap in valid_laps]
    lap_times = [lap.lap_time_seconds for lap in valid_laps]
    slope, _ = np.polyfit(lap_numbers, lap_times, 1)
    return float(slope)


def build_driver_stints(
    laps: list[NormalizedLap],
    race_id: str,
    driver_code: str,
) -> list[DriverStint]:
    """Aggregate per-lap data into stint summaries for one driver.

    Args:
        laps: All normalised laps for the session (any driver).
        race_id: Identifier of the race these laps belong to.
        driver_code: Three-letter code of the driver to analyse.

    Returns:
        List of DriverStint objects ordered by stint number.
    """
    driver_laps = filter_driver_laps(laps, driver_code)
    stints: dict[int, list[NormalizedLap]] = defaultdict(list)

    for lap in driver_laps:
        if lap.stint_number is None:
            continue
        stints[lap.stint_number].append(lap)

    driver_stints: list[DriverStint] = []

    for stint_number, stint_laps in sorted(stints.items()):
        ordered_laps = sorted(stint_laps, key=lambda lap: lap.lap_number)
        filtered_stint_laps = filter_outlier_laps(ordered_laps)
        first_lap = ordered_laps[0]
        last_lap = ordered_laps[-1]

        driver_stints.append(
            DriverStint(
                race_id=race_id,
                driver_code=driver_code.upper().strip(),
                stint_number=stint_number,
                tyre_compound=first_lap.tyre_compound,
                start_lap=first_lap.lap_number,
                end_lap=last_lap.lap_number,
                stint_length=len(ordered_laps),
                avg_lap_time_seconds=average_lap_time_seconds(
                    filtered_stint_laps
                ),
                degradation_slope=stint_lap_time_slope(filtered_stint_laps),
            )
        )

    return driver_stints
