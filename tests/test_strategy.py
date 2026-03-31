from backend.app.config.strategy import (
    BASELINE_STRATEGY_NAME,
    LOW_DEGRADATION_THRESHOLD,
    MEDIUM_DEGRADATION_THRESHOLD,
    MIN_LAPS_FOR_SLOPE,
    PROJECTION_HORIZON_LAPS,
    URGENCY_MAP,
)
from backend.app.domain.models import DriverStint, StrategyRecommendation
from backend.app.schemas.strategy import StrategyResponse
from backend.app.services.strategy import estimate_pit_window


def expected_baseline_delta(
    stint: DriverStint,
    recommended_start: int,
    slope: float | None,
) -> float | None:
    """Return the expected heuristic baseline delta for a recommendation."""
    if slope is None:
        return None

    baseline_pit_lap = stint.start_lap + (stint.stint_length // 2)
    baseline_remaining = max(0, recommended_start - baseline_pit_lap)
    return slope * baseline_remaining


def build_stint(
    *,
    end_lap: int = 10,
    stint_length: int = MIN_LAPS_FOR_SLOPE,
    slope: float | None = 0.01,
) -> DriverStint:
    """Build a DriverStint fixture for strategy tests."""
    return DriverStint(
        race_id="2024_monza_race",
        driver_code="VER",
        stint_number=2,
        tyre_compound="MEDIUM",
        start_lap=end_lap - stint_length + 1,
        end_lap=end_lap,
        stint_length=stint_length,
        avg_lap_time_seconds=90.5,
        degradation_slope=slope,
    )


def test_estimate_pit_window_returns_low_urgency_metadata() -> None:
    slope = LOW_DEGRADATION_THRESHOLD - 0.005
    stint = build_stint(slope=slope)
    recommendation = estimate_pit_window([stint], "2024_monza_race", "ver")

    assert recommendation.confidence == "medium"
    assert recommendation.urgency == "low"
    assert recommendation.recommended_pit_window_start == (
        10 + URGENCY_MAP["low"]["start_offset"]
    )
    assert recommendation.recommended_pit_window_end == (
        10 + URGENCY_MAP["low"]["end_offset"]
    )
    assert recommendation.degradation_slope_used == (
        LOW_DEGRADATION_THRESHOLD - 0.005
    )
    assert recommendation.threshold_used == LOW_DEGRADATION_THRESHOLD
    assert recommendation.projected_lap_delta_seconds == (
        (LOW_DEGRADATION_THRESHOLD - 0.005) * PROJECTION_HORIZON_LAPS
    )
    assert recommendation.baseline_strategy == BASELINE_STRATEGY_NAME
    assert recommendation.baseline_delta_seconds == expected_baseline_delta(
        stint,
        recommendation.recommended_pit_window_start,
        slope,
    )


def test_estimate_pit_window_returns_medium_urgency_metadata() -> None:
    slope = (LOW_DEGRADATION_THRESHOLD + MEDIUM_DEGRADATION_THRESHOLD) / 2
    stint = build_stint(slope=slope)
    recommendation = estimate_pit_window([stint], "2024_monza_race", "ver")

    assert recommendation.confidence == "medium"
    assert recommendation.urgency == "medium"
    assert recommendation.recommended_pit_window_start == (
        10 + URGENCY_MAP["medium"]["start_offset"]
    )
    assert recommendation.recommended_pit_window_end == (
        10 + URGENCY_MAP["medium"]["end_offset"]
    )
    assert recommendation.degradation_slope_used == slope
    assert recommendation.threshold_used == MEDIUM_DEGRADATION_THRESHOLD
    assert recommendation.projected_lap_delta_seconds == (
        slope * PROJECTION_HORIZON_LAPS
    )
    assert recommendation.baseline_strategy == BASELINE_STRATEGY_NAME
    assert recommendation.baseline_delta_seconds == expected_baseline_delta(
        stint,
        recommendation.recommended_pit_window_start,
        slope,
    )


def test_estimate_pit_window_returns_high_urgency_metadata() -> None:
    slope = MEDIUM_DEGRADATION_THRESHOLD + 0.01
    stint = build_stint(stint_length=8, end_lap=12, slope=slope)
    recommendation = estimate_pit_window([stint], "2024_monza_race", "ver")

    assert recommendation.confidence == "high"
    assert recommendation.urgency == "high"
    assert recommendation.recommended_pit_window_start == (
        12 + URGENCY_MAP["high"]["start_offset"]
    )
    assert recommendation.recommended_pit_window_end == (
        12 + URGENCY_MAP["high"]["end_offset"]
    )
    assert recommendation.degradation_slope_used == slope
    assert recommendation.threshold_used == MEDIUM_DEGRADATION_THRESHOLD
    assert recommendation.projected_lap_delta_seconds == (
        slope * PROJECTION_HORIZON_LAPS
    )
    assert recommendation.baseline_strategy == BASELINE_STRATEGY_NAME
    assert recommendation.baseline_delta_seconds == expected_baseline_delta(
        stint,
        recommendation.recommended_pit_window_start,
        slope,
    )


def test_estimate_pit_window_returns_unknown_for_insufficient_laps() -> None:
    slope = LOW_DEGRADATION_THRESHOLD
    stint = build_stint(stint_length=MIN_LAPS_FOR_SLOPE - 1, slope=slope)
    recommendation = estimate_pit_window([stint], "2024_monza_race", "ver")

    assert recommendation.confidence == "low"
    assert recommendation.urgency == "unknown"
    assert recommendation.recommended_pit_window_start == (
        10 + URGENCY_MAP["medium"]["start_offset"]
    )
    assert recommendation.recommended_pit_window_end == (
        10 + URGENCY_MAP["medium"]["end_offset"]
    )
    assert recommendation.degradation_slope_used == slope
    assert recommendation.threshold_used is None
    assert recommendation.projected_lap_delta_seconds == (
        slope * PROJECTION_HORIZON_LAPS
    )
    assert recommendation.baseline_strategy == BASELINE_STRATEGY_NAME
    assert recommendation.baseline_delta_seconds == expected_baseline_delta(
        stint,
        recommendation.recommended_pit_window_start,
        slope,
    )


def test_estimate_pit_window_returns_unknown_baseline_with_no_slope() -> None:
    recommendation = estimate_pit_window(
        [build_stint(slope=None)],
        "2024_monza_race",
        "ver",
    )

    assert recommendation.confidence == "low"
    assert recommendation.urgency == "unknown"
    assert recommendation.baseline_strategy == BASELINE_STRATEGY_NAME
    assert recommendation.baseline_delta_seconds is None


def test_strategy_response_serializes_new_heuristic_fields() -> None:
    recommendation = StrategyRecommendation(
        race_id="2024_monza_race",
        driver_code="VER",
        recommended_pit_window_start=14,
        recommended_pit_window_end=16,
        current_stint_avg_pace=90.5,
        degradation_slope=0.03,
        urgency="medium",
        explanation="Latest stint degradation is building.",
        degradation_slope_used=0.03,
        threshold_used=MEDIUM_DEGRADATION_THRESHOLD,
        projected_lap_delta_seconds=(
            0.03 * PROJECTION_HORIZON_LAPS
        ),
        confidence="high",
        baseline_strategy=BASELINE_STRATEGY_NAME,
        baseline_delta_seconds=0.06,
    )

    response = StrategyResponse.model_validate(recommendation)

    assert response.degradation_slope_used == 0.03
    assert response.threshold_used == MEDIUM_DEGRADATION_THRESHOLD
    assert response.projected_lap_delta_seconds == (
        0.03 * PROJECTION_HORIZON_LAPS
    )
    assert response.confidence == "high"
    assert response.baseline_strategy == BASELINE_STRATEGY_NAME
    assert response.baseline_delta_seconds == 0.06
