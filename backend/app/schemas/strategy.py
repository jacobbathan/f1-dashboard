from typing import Optional

from pydantic import BaseModel


class StrategyResponse(BaseModel):
    race_id: str
    driver_code: str
    recommended_pit_window_start: int
    recommended_pit_window_end: int
    current_stint_avg_pace: Optional[float] = None
    degradation_slope: Optional[float] = None
    urgency: str
    explanation: str
