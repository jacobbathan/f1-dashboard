from dataclasses import dataclass
from typing import Optional


@dataclass
class NormalizedLap:
    race_id: str
    driver_code: str
    lap_number: int
    lap_time_seconds: Optional[float]
    tyre_compound: Optional[str]
    tyre_life_laps: Optional[int]
    stint_number: Optional[int]
    position: Optional[int]


@dataclass
class DriverStint:
    race_id: str
    driver_code: str
    stint_number: int
    tyre_compound: Optional[str]
    start_lap: int
    end_lap: int
    stint_length: int
    avg_lap_time_seconds: Optional[float]
    degradation_slope: Optional[float]


@dataclass
class StrategyRecommendation:
    race_id: str
    driver_code: str
    recommended_pit_window_start: int
    recommended_pit_window_end: int
    current_stint_avg_pace: Optional[float]
    degradation_slope: Optional[float]
    urgency: str
    explanation: str
