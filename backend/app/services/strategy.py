from backend.app.config.strategy import (
    BASELINE_STRATEGY_NAME,
    LOW_DEGRADATION_THRESHOLD,
    MEDIUM_DEGRADATION_THRESHOLD,
    MIN_LAPS_FOR_SLOPE,
    PROJECTION_HORIZON_LAPS,
    URGENCY_MAP,
)
from backend.app.domain.models import DriverStint, StrategyRecommendation


def estimate_pit_window(
    stints: list[DriverStint],
    race_id: str,
    driver_code: str,
) -> StrategyRecommendation:
    """Recommend a pit window based on the most recent stint's degradation.

    Args:
        stints: All computed stints for the driver. Must be non-empty.
        race_id: Identifier of the race.
        driver_code: Three-letter driver code.

    Returns:
        A StrategyRecommendation with pit window and urgency level.

    Raises:
        ValueError: If stints is empty.
    """
    if not stints:
        raise ValueError(
            "At least one stint is required to estimate a pit window"
        )

    latest_stint = max(stints, key=lambda stint: stint.end_lap)
    current_lap = latest_stint.end_lap
    valid_laps = latest_stint.stint_length
    slope = latest_stint.degradation_slope
    projected_lap_delta_seconds = (
        slope * PROJECTION_HORIZON_LAPS if slope is not None else None
    )
    fallback_window = URGENCY_MAP["medium"]
    baseline_pit_lap = (
        latest_stint.start_lap + (latest_stint.stint_length // 2)
    )

    if valid_laps < MIN_LAPS_FOR_SLOPE or slope is None:
        recommended_start = current_lap + fallback_window["start_offset"]
        # This is a heuristic comparison, not a race simulation.
        baseline_delta_seconds = (
            slope * max(0, recommended_start - baseline_pit_lap)
            if slope is not None
            else None
        )
        return StrategyRecommendation(
            race_id=race_id,
            driver_code=driver_code.upper().strip(),
            recommended_pit_window_start=recommended_start,
            recommended_pit_window_end=(
                current_lap + fallback_window["end_offset"]
            ),
            current_stint_avg_pace=latest_stint.avg_lap_time_seconds,
            degradation_slope=slope,
            urgency="unknown",
            explanation=(
                "Insufficient valid laps for a reliable degradation estimate."
            ),
            degradation_slope_used=slope,
            threshold_used=None,
            projected_lap_delta_seconds=projected_lap_delta_seconds,
            confidence="low",
            baseline_strategy=BASELINE_STRATEGY_NAME,
            baseline_delta_seconds=baseline_delta_seconds,
        )

    if valid_laps <= 7:
        confidence = "medium"
    else:
        confidence = "high"

    if slope < LOW_DEGRADATION_THRESHOLD:
        urgency = "low"
        threshold_used = LOW_DEGRADATION_THRESHOLD
        explanation = (
            "Latest stint degradation is mild, "
            "so the pit window can stay later."
        )
    elif slope < MEDIUM_DEGRADATION_THRESHOLD:
        urgency = "medium"
        threshold_used = MEDIUM_DEGRADATION_THRESHOLD
        explanation = (
            "Latest stint degradation is building, "
            "so the pit window should stay nearby."
        )
    else:
        urgency = "high"
        threshold_used = MEDIUM_DEGRADATION_THRESHOLD
        explanation = (
            "Latest stint degradation is high, "
            "so the pit window should be immediate."
        )

    urgency_window = URGENCY_MAP[urgency]
    recommended_start = current_lap + urgency_window["start_offset"]
    # This is a heuristic comparison, not a race simulation.
    baseline_delta_seconds = slope * max(
        0, recommended_start - baseline_pit_lap
    )

    return StrategyRecommendation(
        race_id=race_id,
        driver_code=driver_code.upper().strip(),
        recommended_pit_window_start=recommended_start,
        recommended_pit_window_end=current_lap + urgency_window["end_offset"],
        current_stint_avg_pace=latest_stint.avg_lap_time_seconds,
        degradation_slope=slope,
        urgency=urgency,
        explanation=explanation,
        degradation_slope_used=slope,
        threshold_used=threshold_used,
        projected_lap_delta_seconds=projected_lap_delta_seconds,
        confidence=confidence,
        baseline_strategy=BASELINE_STRATEGY_NAME,
        baseline_delta_seconds=baseline_delta_seconds,
    )
