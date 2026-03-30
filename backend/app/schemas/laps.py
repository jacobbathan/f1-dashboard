from typing import List, Optional

from pydantic import BaseModel


class LapItemResponse(BaseModel):
    driver_code: str
    lap_number: int
    lap_time_seconds: float
    tyre_compound: Optional[str] = None
    tyre_life_laps: Optional[int] = None
    stint_number: Optional[int] = None
    position: Optional[int] = None


class LapsResponse(BaseModel):
    race_id: str
    driver_code: str
    laps: List[LapItemResponse]
