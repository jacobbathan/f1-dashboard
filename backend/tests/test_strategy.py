import pytest

from backend.app.config.strategy import (
    MEDIUM_DEGRADATION_THRESHOLD,
    MIN_LAPS_FOR_SLOPE,
)
from backend.app.domain.models import DriverStint
from backend.app.services.strategy import estimate_pit_window


def build_stint(
    *,
    stint_number: int,
    start_lap: int,
    end_lap: int,
    stint_length: int,
    degradation_slope: float | None,
    avg_lap_time_seconds: float | None = 82.5,
) -> DriverStint:
    """Build a strategy test fixture with explicit stint boundaries."""
    return DriverStint(
        race_id="2024_monza_race",
        driver_code="VER",
        stint_number=stint_number,
        tyre_compound="MEDIUM",
        start_lap=start_lap,
        end_lap=end_lap,
        stint_length=stint_length,
        avg_lap_time_seconds=avg_lap_time_seconds,
        degradation_slope=degradation_slope,
    )


def test_normal_mid_race_stint_returns_recommendation() -> None:
    stint = build_stint(
        stint_number=2,
        start_lap=15,
        end_lap=30,
        stint_length=16,
        degradation_slope=0.03,
        avg_lap_time_seconds=82.5,
    )

    recommendation = estimate_pit_window(
        [stint],
        "2024_monza_race",
        "VER",
        race_max_lap=53,
    )

    assert recommendation.recommended_pit_window_start is not None
    assert recommendation.recommended_pit_window_end is not None
    assert recommendation.recommended_pit_window_start <= 53
    assert recommendation.recommended_pit_window_end <= 53
    assert recommendation.urgency == "medium"
    assert recommendation.confidence == "high"


def test_late_race_stint_at_race_end_returns_no_window() -> None:
    stint = build_stint(
        stint_number=3,
        start_lap=40,
        end_lap=53,
        stint_length=14,
        degradation_slope=0.04,
    )

    recommendation = estimate_pit_window(
        [stint],
        "2024_monza_race",
        "VER",
        race_max_lap=53,
    )

    assert recommendation.recommended_pit_window_start is None
    assert recommendation.urgency in {"none", "late_race"}


def test_stint_with_insufficient_laps_has_low_confidence() -> None:
    stint = build_stint(
        stint_number=1,
        start_lap=1,
        end_lap=3,
        stint_length=3,
        degradation_slope=None,
    )

    recommendation = estimate_pit_window(
        [stint],
        "2024_monza_race",
        "VER",
        race_max_lap=53,
    )

    assert recommendation.confidence == "low"


def test_invalid_stint_number_raises_value_error() -> None:
    stint = build_stint(
        stint_number=1,
        start_lap=15,
        end_lap=30,
        stint_length=16,
        degradation_slope=0.03,
    )

    with pytest.raises(ValueError, match="Stint 99 not found for driver"):
        estimate_pit_window(
            [stint],
            "2024_monza_race",
            "VER",
            stint_number=99,
        )


def test_collapsed_high_degradation_window_returns_late_race_state() -> None:
    stint = build_stint(
        stint_number=4,
        start_lap=35,
        end_lap=50,
        stint_length=16,
        degradation_slope=MEDIUM_DEGRADATION_THRESHOLD + 0.01,
    )

    recommendation = estimate_pit_window(
        [stint],
        "2024_monza_race",
        "VER",
        race_max_lap=51,
    )

    assert recommendation.urgency == "late_race"
    assert recommendation.recommended_pit_window_end is None


def test_invalid_stint_is_checked_before_default_selection() -> None:
    short_stint = build_stint(
        stint_number=1,
        start_lap=1,
        end_lap=3,
        stint_length=MIN_LAPS_FOR_SLOPE - 1,
        degradation_slope=None,
    )
    later_stint = build_stint(
        stint_number=2,
        start_lap=15,
        end_lap=30,
        stint_length=16,
        degradation_slope=0.03,
    )

    with pytest.raises(ValueError, match="Stint 99 not found for driver"):
        estimate_pit_window(
            [short_stint, later_stint],
            "2024_monza_race",
            "VER",
            stint_number=99,
        )
