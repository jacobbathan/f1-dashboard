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
    stint_number: int = 2,
    end_lap: int = 10,
    stint_length: int = MIN_LAPS_FOR_SLOPE,
    slope: float | None = 0.01,
) -> DriverStint:
    """Build a DriverStint fixture for strategy tests."""
    return DriverStint(
        race_id="2024_monza_race",
        driver_code="VER",
        stint_number=stint_number,
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
    assert recommendation.stint_number == stint.stint_number
    assert recommendation.race_max_lap is None
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
    assert recommendation.stint_number == stint.stint_number
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
    assert recommendation.stint_number == stint.stint_number
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
    assert recommendation.stint_number == stint.stint_number
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


def test_estimate_pit_window_uses_requested_stint_number() -> None:
    selected_stint = build_stint(
        stint_number=1,
        end_lap=10,
        stint_length=MIN_LAPS_FOR_SLOPE + 1,
        slope=LOW_DEGRADATION_THRESHOLD - 0.005,
    )
    later_stint = build_stint(
        stint_number=2,
        end_lap=20,
        stint_length=MIN_LAPS_FOR_SLOPE + 2,
        slope=MEDIUM_DEGRADATION_THRESHOLD + 0.01,
    )

    recommendation = estimate_pit_window(
        [selected_stint, later_stint],
        "2024_monza_race",
        "ver",
        stint_number=1,
    )

    assert recommendation.stint_number == 1
    assert recommendation.urgency == "low"
    assert recommendation.recommended_pit_window_start == (
        10 + URGENCY_MAP["low"]["start_offset"]
    )
    assert recommendation.recommended_pit_window_end == (
        10 + URGENCY_MAP["low"]["end_offset"]
    )


def test_estimate_pit_window_defaults_to_latest_meaningful_stint() -> None:
    meaningful_stint = build_stint(
        stint_number=1,
        end_lap=12,
        stint_length=MIN_LAPS_FOR_SLOPE + 1,
        slope=LOW_DEGRADATION_THRESHOLD - 0.005,
    )
    latest_short_stint = build_stint(
        stint_number=2,
        end_lap=20,
        stint_length=MIN_LAPS_FOR_SLOPE - 1,
        slope=MEDIUM_DEGRADATION_THRESHOLD + 0.01,
    )

    recommendation = estimate_pit_window(
        [meaningful_stint, latest_short_stint],
        "2024_monza_race",
        "ver",
    )

    assert recommendation.stint_number == meaningful_stint.stint_number
    assert recommendation.urgency == "low"
    assert recommendation.recommended_pit_window_start == (
        12 + URGENCY_MAP["low"]["start_offset"]
    )


def test_estimate_pit_window_falls_back_to_latest_stint_when_needed() -> None:
    early_short_stint = build_stint(
        stint_number=1,
        end_lap=12,
        stint_length=MIN_LAPS_FOR_SLOPE - 2,
        slope=LOW_DEGRADATION_THRESHOLD - 0.005,
    )
    latest_short_stint = build_stint(
        stint_number=2,
        end_lap=16,
        stint_length=MIN_LAPS_FOR_SLOPE - 1,
        slope=MEDIUM_DEGRADATION_THRESHOLD + 0.01,
    )

    recommendation = estimate_pit_window(
        [early_short_stint, latest_short_stint],
        "2024_monza_race",
        "ver",
    )

    assert recommendation.stint_number == latest_short_stint.stint_number
    assert recommendation.urgency == "unknown"
    assert recommendation.recommended_pit_window_start == (
        16 + URGENCY_MAP["medium"]["start_offset"]
    )


def test_estimate_pit_window_raises_for_unknown_stint_number() -> None:
    try:
        estimate_pit_window(
            [build_stint(stint_number=1)],
            "2024_monza_race",
            "ver",
            stint_number=9,
        )
    except ValueError as exc:
        assert str(exc) == "Stint 9 not found for driver"
    else:
        raise AssertionError("Expected ValueError for unknown stint")


def test_estimate_pit_window_returns_none_when_stint_reaches_race_end() -> None:
    stint = build_stint(end_lap=20, slope=0.03)
    recommendation = estimate_pit_window(
        [stint],
        "2024_monza_race",
        "ver",
        race_max_lap=20,
    )

    assert recommendation.recommended_pit_window_start is None
    assert recommendation.recommended_pit_window_end is None
    assert recommendation.urgency == "none"
    assert recommendation.confidence == "high"
    assert recommendation.explanation == (
        "Current stint extends to or beyond race end. "
        "No future pit window."
    )
    assert recommendation.stint_number == stint.stint_number
    assert recommendation.race_max_lap == 20
    assert recommendation.current_stint_avg_pace == stint.avg_lap_time_seconds
    assert recommendation.degradation_slope == 0.03
    assert recommendation.degradation_slope_used == 0.03
    assert recommendation.projected_lap_delta_seconds is None
    assert recommendation.baseline_strategy == BASELINE_STRATEGY_NAME
    assert recommendation.baseline_delta_seconds is None


def test_estimate_pit_window_returns_late_race_when_window_collapses() -> None:
    slope = MEDIUM_DEGRADATION_THRESHOLD + 0.01
    stint = build_stint(end_lap=19, slope=slope)
    recommendation = estimate_pit_window(
        [stint],
        "2024_monza_race",
        "ver",
        race_max_lap=20,
    )

    assert recommendation.recommended_pit_window_start is None
    assert recommendation.recommended_pit_window_end is None
    assert recommendation.urgency == "late_race"
    assert recommendation.confidence == "high"
    assert recommendation.explanation == (
        "Pit window extends beyond race end. "
        "No meaningful recommendation."
    )
    assert recommendation.threshold_used == MEDIUM_DEGRADATION_THRESHOLD
    assert recommendation.projected_lap_delta_seconds == slope
    assert recommendation.baseline_delta_seconds is None


def test_estimate_pit_window_clamps_projection_horizon_to_race_end() -> None:
    slope = (LOW_DEGRADATION_THRESHOLD + MEDIUM_DEGRADATION_THRESHOLD) / 2
    stint = build_stint(end_lap=18, slope=slope)
    recommendation = estimate_pit_window(
        [stint],
        "2024_monza_race",
        "ver",
        race_max_lap=21,
    )

    assert recommendation.recommended_pit_window_start == 20
    assert recommendation.recommended_pit_window_end == 21
    assert recommendation.projected_lap_delta_seconds == slope * 3
    assert recommendation.baseline_delta_seconds == expected_baseline_delta(
        stint,
        20,
        slope,
    )


def test_estimate_pit_window_keeps_valid_clamped_window() -> None:
    slope = MEDIUM_DEGRADATION_THRESHOLD + 0.01
    stint = build_stint(end_lap=18, slope=slope)
    recommendation = estimate_pit_window(
        [stint],
        "2024_monza_race",
        "ver",
        race_max_lap=20,
    )

    assert recommendation.urgency == "high"
    assert recommendation.recommended_pit_window_start == 19
    assert recommendation.recommended_pit_window_end == 20
    assert recommendation.projected_lap_delta_seconds == slope * 2
    assert recommendation.baseline_delta_seconds == expected_baseline_delta(
        stint,
        19,
        slope,
    )


def test_strategy_response_serializes_new_heuristic_fields() -> None:
    recommendation = StrategyRecommendation(
        race_id="2024_monza_race",
        driver_code="VER",
        current_stint_avg_pace=90.5,
        degradation_slope=0.03,
        urgency="medium",
        explanation="Latest stint degradation is building.",
        recommended_pit_window_start=14,
        recommended_pit_window_end=16,
        stint_number=2,
        race_max_lap=53,
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

    assert response.stint_number == 2
    assert response.race_max_lap == 53
    assert response.degradation_slope_used == 0.03
    assert response.threshold_used == MEDIUM_DEGRADATION_THRESHOLD
    assert response.projected_lap_delta_seconds == (
        0.03 * PROJECTION_HORIZON_LAPS
    )
    assert response.confidence == "high"
    assert response.baseline_strategy == BASELINE_STRATEGY_NAME
    assert response.baseline_delta_seconds == 0.06
