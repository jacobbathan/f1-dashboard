from typing import List

from backend.app.domain.models import DriverStint, StrategyRecommendation


def estimate_pit_window(
    stints: List[DriverStint], race_id: str, driver_code: str
) -> StrategyRecommendation:
    if not stints:
        raise ValueError("At least one stint is required to estimate a pit window")

    latest_stint = max(stints, key=lambda stint: stint.end_lap)
    current_lap = latest_stint.end_lap
    slope = latest_stint.degredation_slope

    if latest_stint.stint_length < 4 or slope is None:
        return StrategyRecommendation(
            race_id=race_id,
            driver_code=driver_code.upper().strip(),
            recommended_pit_window_start=current_lap + 2,
            recommended_pit_window_end=current_lap + 4,
            current_stint_avg_pace=latest_stint.avg_lap_time_seconds,
            degradation_slope=slope,
            urgency="unknown",
            explanation="Insufficient valid laps for a reliable degradation estimate.",
        )

    if slope < 0.02:
        urgency = "low"
        start_offset = 4
        end_offset = 6
        explanation = "Latest stint degradation is mild, so the pit window can stay later."
    elif slope < 0.05:
        urgency = "medium"
        start_offset = 2
        end_offset = 4
        explanation = "Latest stint degradation is building, so the pit window should stay nearby."
    else:
        urgency = "high"
        start_offset = 1
        end_offset = 2
        explanation = "Latest stint degradation is high, so the pit window should be immediate."

    return StrategyRecommendation(
        race_id=race_id,
        driver_code=driver_code.upper().strip(),
        recommended_pit_window_start=current_lap + start_offset,
        recommended_pit_window_end=current_lap + end_offset,
        current_stint_avg_pace=latest_stint.avg_lap_time_seconds,
        degradation_slope=slope,
        urgency=urgency,
        explanation=explanation,
    )
