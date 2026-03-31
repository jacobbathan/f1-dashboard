from pydantic import BaseModel, ConfigDict


class StintItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    driver_code: str
    stint_number: int
    tyre_compound: str | None = None
    start_lap: int
    end_lap: int
    stint_length: int
    avg_lap_time_seconds: float | None = None
    degradation_slope: float | None = None


class StintsResponse(BaseModel):
    race_id: str
    driver_code: str
    stints: list[StintItemResponse]
