from pydantic import BaseModel, ConfigDict


class LapItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    driver_code: str
    lap_number: int
    lap_time_seconds: float
    tyre_compound: str | None = None
    tyre_life_laps: int | None = None
    stint_number: int | None = None
    position: int | None = None


class LapsResponse(BaseModel):
    race_id: str
    driver_code: str
    laps: list[LapItemResponse]
