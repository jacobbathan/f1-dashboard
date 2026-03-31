from typing import Optional

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
    race_max_lap: Optional[int] = None,
    stint_number: Optional[int] = None,
) -> StrategyRecommendation:
    """Recommend a pit window based on the most recent stint's degradation.

    Args:
        stints: All computed stints for the driver. Must be non-empty.
        race_id: Identifier of the race.
        driver_code: Three-letter driver code.
        race_max_lap: Final lap of the race, if known.
        stint_number: Specific stint number to analyze, if provided.

    Returns:
        A StrategyRecommendation with pit window and urgency level.

    Raises:
        ValueError: If stints is empty or a requested stint is missing.
    """
    if not stints:
        raise ValueError(
            "At least one stint is required to estimate a pit window"
        )

    if stint_number is not None:
        matching = [
            stint for stint in stints
            if stint.stint_number == stint_number
        ]
        if not matching:
            raise ValueError(
                f"Stint {stint_number} not found for driver"
            )
        target_stint = matching[0]
    else:
        candidates = [
            stint for stint in stints
            if stint.stint_length >= MIN_LAPS_FOR_SLOPE
        ]
        if candidates:
            target_stint = max(candidates, key=lambda stint: stint.end_lap)
        else:
            target_stint = max(stints, key=lambda stint: stint.end_lap)

    current_lap = target_stint.end_lap
    valid_laps = target_stint.stint_length
    slope = target_stint.degradation_slope
    fallback_window = URGENCY_MAP["medium"]
    baseline_pit_lap = (
        target_stint.start_lap + (target_stint.stint_length // 2)
    )
    remaining_race_laps = (
        race_max_lap - current_lap if race_max_lap is not None else None
    )
    projection_horizon = PROJECTION_HORIZON_LAPS
    if remaining_race_laps is not None:
        projection_horizon = min(
            PROJECTION_HORIZON_LAPS,
            remaining_race_laps,
        )

    if slope is None or projection_horizon <= 0:
        projected_lap_delta_seconds = None
    else:
        projected_lap_delta_seconds = slope * projection_horizon

    def build_no_recommendation(
        *,
        urgency: str,
        explanation: str,
        confidence: str,
        threshold_used: float | None = None,
    ) -> StrategyRecommendation:
        """Return a fully populated no-window recommendation."""
        return StrategyRecommendation(
            race_id=race_id,
            driver_code=driver_code.upper().strip(),
            current_stint_avg_pace=target_stint.avg_lap_time_seconds,
            degradation_slope=slope,
            urgency=urgency,
            explanation=explanation,
            recommended_pit_window_start=None,
            recommended_pit_window_end=None,
            stint_number=target_stint.stint_number,
            race_max_lap=race_max_lap,
            degradation_slope_used=slope,
            threshold_used=threshold_used,
            projected_lap_delta_seconds=projected_lap_delta_seconds,
            confidence=confidence,
            baseline_strategy=BASELINE_STRATEGY_NAME,
            baseline_delta_seconds=None,
        )

    def compute_baseline_delta(
        recommended_start: int,
    ) -> float | None:
        """Return the heuristic baseline delta when in-race bounds allow it."""
        if slope is None:
            return None
        if (
            race_max_lap is not None
            and (
                recommended_start > race_max_lap
                or baseline_pit_lap > race_max_lap
            )
        ):
            return None
        return slope * max(0, recommended_start - baseline_pit_lap)

    def clamp_window(
        raw_start: int,
        raw_end: int,
    ) -> tuple[int, int]:
        """Clamp a raw pit window to the known race end when available."""
        if race_max_lap is None:
            return raw_start, raw_end
        return min(raw_start, race_max_lap), min(raw_end, race_max_lap)

    if race_max_lap is not None and current_lap >= race_max_lap:
        return build_no_recommendation(
            urgency="none",
            explanation=(
                "Current stint extends to or beyond race end. "
                "No future pit window."
            ),
            confidence="high",
        )

    if valid_laps < MIN_LAPS_FOR_SLOPE or slope is None:
        raw_start = current_lap + fallback_window["start_offset"]
        raw_end = current_lap + fallback_window["end_offset"]
        recommended_start, recommended_end = clamp_window(
            raw_start,
            raw_end,
        )
        if (
            race_max_lap is not None
            and (
                recommended_start >= race_max_lap
                or recommended_start == recommended_end
            )
        ):
            return build_no_recommendation(
                urgency="late_race",
                explanation=(
                    "Pit window extends beyond race end. "
                    "No meaningful recommendation."
                ),
                confidence="high",
            )

        return StrategyRecommendation(
            race_id=race_id,
            driver_code=driver_code.upper().strip(),
            current_stint_avg_pace=target_stint.avg_lap_time_seconds,
            degradation_slope=slope,
            urgency="unknown",
            explanation=(
                "Insufficient valid laps for a reliable degradation estimate."
            ),
            recommended_pit_window_start=recommended_start,
            recommended_pit_window_end=recommended_end,
            stint_number=target_stint.stint_number,
            race_max_lap=race_max_lap,
            degradation_slope_used=slope,
            threshold_used=None,
            projected_lap_delta_seconds=projected_lap_delta_seconds,
            confidence="low",
            baseline_strategy=BASELINE_STRATEGY_NAME,
            baseline_delta_seconds=compute_baseline_delta(
                recommended_start
            ),
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
    raw_start = current_lap + urgency_window["start_offset"]
    raw_end = current_lap + urgency_window["end_offset"]
    recommended_start, recommended_end = clamp_window(
        raw_start,
        raw_end,
    )
    if (
        race_max_lap is not None
        and (
            recommended_start >= race_max_lap
            or recommended_start == recommended_end
        )
    ):
        return build_no_recommendation(
            urgency="late_race",
            explanation=(
                "Pit window extends beyond race end. "
                "No meaningful recommendation."
            ),
            confidence="high",
            threshold_used=threshold_used,
        )

    return StrategyRecommendation(
        race_id=race_id,
        driver_code=driver_code.upper().strip(),
        current_stint_avg_pace=target_stint.avg_lap_time_seconds,
        degradation_slope=slope,
        urgency=urgency,
        explanation=explanation,
        recommended_pit_window_start=recommended_start,
        recommended_pit_window_end=recommended_end,
        stint_number=target_stint.stint_number,
        race_max_lap=race_max_lap,
        degradation_slope_used=slope,
        threshold_used=threshold_used,
        projected_lap_delta_seconds=projected_lap_delta_seconds,
        confidence=confidence,
        baseline_strategy=BASELINE_STRATEGY_NAME,
        baseline_delta_seconds=compute_baseline_delta(
            recommended_start
        ),
    )
