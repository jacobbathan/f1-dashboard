from typing import Optional

from pydantic import BaseModel, ConfigDict


class StrategyResponse(BaseModel):
    """Serialized strategy recommendation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    race_id: str
    driver_code: str
    recommended_pit_window_start: int
    recommended_pit_window_end: int
    current_stint_avg_pace: float | None = None
    degradation_slope: float | None = None
    urgency: str
    explanation: str
    degradation_slope_used: Optional[float] = None
    threshold_used: Optional[float] = None
    projected_lap_delta_seconds: Optional[float] = None
    confidence: Optional[str] = None
    baseline_strategy: Optional[str] = None
    baseline_delta_seconds: Optional[float] = None
