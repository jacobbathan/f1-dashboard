from collections import defaultdict
from typing import Dict, List, Optional

import numpy as np

from backend.app.domain.models import DriverStint, NormalizedLap
from backend.app.services.normalization import filter_driver_laps


def filter_timed_laps(laps: List[NormalizedLap]) -> List[NormalizedLap]:
    """Drop laps that do not have a usable lap time before analytics."""
    return [lap for lap in laps if lap.lap_time_seconds is not None]


def average_lap_time_seconds(laps: List[NormalizedLap]) -> Optional[float]:
    lap_times = [lap.lap_time_seconds for lap in filter_timed_laps(laps)]
    if not lap_times:
        return None

    return sum(lap_times) / len(lap_times)


def stint_lap_time_slope(laps: List[NormalizedLap]) -> Optional[float]:
    valid_laps = sorted(filter_timed_laps(laps), key=lambda lap: lap.lap_number)
    if len(valid_laps) < 2:
        return None

    lap_numbers = [lap.lap_number for lap in valid_laps]
    lap_times = [lap.lap_time_seconds for lap in valid_laps]
    slope, _ = np.polyfit(lap_numbers, lap_times, 1)
    return float(slope)


def build_driver_stints(
    laps: List[NormalizedLap], race_id: str, driver_code: str
) -> List[DriverStint]:
    driver_laps = filter_driver_laps(laps, driver_code)
    stints: Dict[int, List[NormalizedLap]] = defaultdict(list)

    for lap in driver_laps:
        if lap.stint_number is None:
            continue
        stints[lap.stint_number].append(lap)

    driver_stints: List[DriverStint] = []

    for stint_number, stint_laps in sorted(stints.items()):
        ordered_laps = sorted(stint_laps, key=lambda lap: lap.lap_number)
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
                avg_lap_time_seconds=average_lap_time_seconds(ordered_laps),
                degredation_slope=stint_lap_time_slope(ordered_laps),
            )
        )

    return driver_stints
