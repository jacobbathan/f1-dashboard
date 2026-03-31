from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, slots=True)
class NormalizedLap:
    """A single race lap with cleaned and validated fields."""

    race_id: str
    driver_code: str
    lap_number: int
    lap_time_seconds: float | None
    tyre_compound: str | None
    tyre_life_laps: int | None
    stint_number: int | None
    position: int | None


@dataclass(frozen=True, slots=True)
class DriverStint:
    """Aggregated metrics for one continuous stint by a single driver."""

    race_id: str
    driver_code: str
    stint_number: int
    tyre_compound: str | None
    start_lap: int
    end_lap: int
    stint_length: int
    avg_lap_time_seconds: float | None
    degradation_slope: float | None


@dataclass(frozen=True, slots=True)
class StrategyRecommendation:
    """Pit-window recommendation derived from current stint degradation."""

    race_id: str
    driver_code: str
    recommended_pit_window_start: int
    recommended_pit_window_end: int
    current_stint_avg_pace: float | None
    degradation_slope: float | None
    urgency: str
    explanation: str
    degradation_slope_used: Optional[float] = None
    threshold_used: Optional[float] = None
    projected_lap_delta_seconds: Optional[float] = None
    confidence: Optional[str] = None
    baseline_strategy: Optional[str] = None
    baseline_delta_seconds: Optional[float] = None
