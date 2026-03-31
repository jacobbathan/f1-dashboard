from fastapi import APIRouter, HTTPException, Query

from backend.app.config import SUPPORTED_RACES
from backend.app.domain.models import NormalizedLap
from backend.app.schemas.laps import LapsResponse
from backend.app.schemas.stints import StintsResponse
from backend.app.schemas.strategy import StrategyResponse
from backend.app.services.analytics import build_driver_stints
from backend.app.services.ingestion import get_raw_laps, load_session
from backend.app.services.normalization import filter_driver_laps, normalize_laps
from backend.app.services.strategy import estimate_pit_window

router = APIRouter()


def _validate_driver_code(driver: str) -> str:
    driver_code = driver.strip().upper()
    if not driver_code:
        raise HTTPException(status_code=400, detail="Query parameter 'driver' is required")

    return driver_code


def _load_normalized_laps(race_id: str) -> list[NormalizedLap]:
    if race_id not in SUPPORTED_RACES:
        raise HTTPException(status_code=404, detail=f"Unsupported race_id: {race_id}")

    try:
        session = load_session(race_id)
        raw_laps = get_raw_laps(session)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to load session data for race_id '{race_id}'",
        ) from exc

    return normalize_laps(raw_laps, race_id)


@router.get("/race/{race_id}/laps", response_model=LapsResponse)
def get_race_laps(
    race_id: str,
    driver: str = Query(..., description="Three-letter driver code, for example VER"),
) -> LapsResponse:
    driver_code = _validate_driver_code(driver)
    normalized_laps = _load_normalized_laps(race_id)
    driver_laps = filter_driver_laps(normalized_laps, driver_code)

    if not driver_laps:
        raise HTTPException(
            status_code=404,
            detail=f"No laps found for driver '{driver_code}' in race '{race_id}'",
        )

    return LapsResponse(
        race_id=race_id,
        driver_code=driver_code,
        laps=[
            {
                "driver_code": lap.driver_code,
                "lap_number": lap.lap_number,
                "lap_time_seconds": lap.lap_time_seconds,
                "tyre_compound": lap.tyre_compound,
                "tyre_life_laps": lap.tyre_life_laps,
                "stint_number": lap.stint_number,
                "position": lap.position,
            }
            for lap in driver_laps
        ],
    )


@router.get("/race/{race_id}/stints", response_model=StintsResponse)
def get_race_stints(
    race_id: str,
    driver: str = Query(..., description="Three-letter driver code, for example VER"),
) -> StintsResponse:
    driver_code = _validate_driver_code(driver)
    normalized_laps = _load_normalized_laps(race_id)
    driver_laps = filter_driver_laps(normalized_laps, driver_code)

    if not driver_laps:
        raise HTTPException(
            status_code=404,
            detail=f"No laps found for driver '{driver_code}' in race '{race_id}'",
        )

    driver_stints = build_driver_stints(normalized_laps, race_id, driver_code)

    if not driver_stints:
        raise HTTPException(
            status_code=404,
            detail=f"No stints found for driver '{driver_code}' in race '{race_id}'",
        )

    return StintsResponse(
        race_id=race_id,
        driver_code=driver_code,
        stints=[
            {
                "driver_code": stint.driver_code,
                "stint_number": stint.stint_number,
                "tyre_compound": stint.tyre_compound,
                "start_lap": stint.start_lap,
                "end_lap": stint.end_lap,
                "stint_length": stint.stint_length,
                "avg_lap_time_seconds": stint.avg_lap_time_seconds,
                "degredation_slope": stint.degredation_slope,
            }
            for stint in driver_stints
        ],
    )


@router.get("/race/{race_id}/strategy", response_model=StrategyResponse)
def get_race_strategy(
    race_id: str,
    driver: str = Query(..., description="Three-letter driver code, for example VER"),
) -> StrategyResponse:
    driver_code = _validate_driver_code(driver)
    normalized_laps = _load_normalized_laps(race_id)
    driver_laps = filter_driver_laps(normalized_laps, driver_code)

    if not driver_laps:
        raise HTTPException(
            status_code=404,
            detail=f"No laps found for driver '{driver_code}' in race '{race_id}'",
        )

    driver_stints = build_driver_stints(normalized_laps, race_id, driver_code)

    if not driver_stints:
        raise HTTPException(
            status_code=404,
            detail=f"No stints found for driver '{driver_code}' in race '{race_id}'",
        )

    recommendation = estimate_pit_window(driver_stints, race_id, driver_code)

    return StrategyResponse(
        race_id=recommendation.race_id,
        driver_code=recommendation.driver_code,
        recommended_pit_window_start=recommendation.recommended_pit_window_start,
        recommended_pit_window_end=recommendation.recommended_pit_window_end,
        current_stint_avg_pace=recommendation.current_stint_avg_pace,
        degradation_slope=recommendation.degradation_slope,
        urgency=recommendation.urgency,
        explanation=recommendation.explanation,
    )
