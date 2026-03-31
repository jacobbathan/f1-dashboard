from typing import List, Optional

from pydantic import BaseModel


class StintItemResponse(BaseModel):
    driver_code: str
    stint_number: int
    tyre_compound: Optional[str] = None
    start_lap: int
    end_lap: int
    stint_length: int
    avg_lap_time_seconds: Optional[float] = None
    degradation_slope: Optional[float] = None


class StintsResponse(BaseModel):
    race_id: str
    driver_code: str
    stints: List[StintItemResponse]
