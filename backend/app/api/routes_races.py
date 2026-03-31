from fastapi import APIRouter, HTTPException, Query

from backend.app.config import SUPPORTED_RACES
from backend.app.domain.models import DriverStint, NormalizedLap
from backend.app.schemas.laps import LapItemResponse, LapsResponse
from backend.app.schemas.stints import StintItemResponse, StintsResponse
from backend.app.schemas.strategy import StrategyResponse
from backend.app.services.analytics import build_driver_stints
from backend.app.services.ingestion import get_raw_laps, load_session
from backend.app.services.normalization import (
    filter_driver_laps,
    normalize_laps,
)
from backend.app.services.persistence import (
    load_laps_from_db,
    save_session_data,
    session_exists,
)
from backend.app.services.strategy import estimate_pit_window

router = APIRouter()


def _validate_driver_code(driver: str) -> str:
    """Normalise and validate the driver query parameter.

    Raises:
        HTTPException: 400 if the value is blank after stripping.
    """
    driver_code = driver.strip().upper()
    if not driver_code:
        raise HTTPException(
            status_code=400,
            detail="Query parameter 'driver' is required",
        )
    return driver_code


def _load_normalized_laps(race_id: str) -> list[NormalizedLap]:
    """Load normalized laps from cache or FastF1 for a supported race.

    Raises:
        HTTPException: 404 if race_id is unsupported or data is missing.
        HTTPException: 502 if the upstream FastF1 call fails.
    """
    if race_id not in SUPPORTED_RACES:
        raise HTTPException(
            status_code=404,
            detail=f"Unsupported race_id: {race_id}",
        )

    if session_exists(race_id):
        return load_laps_from_db(race_id)

    race_config = SUPPORTED_RACES[race_id]

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

    normalized_laps = normalize_laps(raw_laps, race_id)
    save_session_data(race_id, race_config, normalized_laps)
    return normalized_laps


def _load_driver_stints(
    race_id: str,
    driver_code: str,
) -> list[DriverStint]:
    """Load normalised laps and return computed stints for one driver.

    Raises:
        HTTPException: 404 if the driver has no laps or no stints.
    """
    normalized_laps = _load_normalized_laps(race_id)
    driver_laps = filter_driver_laps(normalized_laps, driver_code)

    if not driver_laps:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No laps found for driver '{driver_code}'"
                f" in race '{race_id}'"
            ),
        )

    driver_stints = build_driver_stints(normalized_laps, race_id, driver_code)

    if not driver_stints:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No stints found for driver '{driver_code}'"
                f" in race '{race_id}'"
            ),
        )

    return driver_stints


@router.get("/race/{race_id}/laps", response_model=LapsResponse)
def get_race_laps(
    race_id: str,
    driver: str = Query(
        ..., description="Three-letter driver code, for example VER"
    ),
) -> LapsResponse:
    """Return lap-by-lap times and tyre compounds for one driver."""
    driver_code = _validate_driver_code(driver)
    normalized_laps = _load_normalized_laps(race_id)
    driver_laps = filter_driver_laps(normalized_laps, driver_code)

    if not driver_laps:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No laps found for driver '{driver_code}'"
                f" in race '{race_id}'"
            ),
        )

    return LapsResponse(
        race_id=race_id,
        driver_code=driver_code,
        laps=[LapItemResponse.model_validate(lap) for lap in driver_laps],
    )


@router.get("/race/{race_id}/stints", response_model=StintsResponse)
def get_race_stints(
    race_id: str,
    driver: str = Query(
        ..., description="Three-letter driver code, for example VER"
    ),
) -> StintsResponse:
    """Return stint summaries with degradation slopes for one driver."""
    driver_code = _validate_driver_code(driver)
    driver_stints = _load_driver_stints(race_id, driver_code)

    return StintsResponse(
        race_id=race_id,
        driver_code=driver_code,
        stints=[
            StintItemResponse.model_validate(stint)
            for stint in driver_stints
        ],
    )


@router.get("/race/{race_id}/strategy", response_model=StrategyResponse)
def get_race_strategy(
    race_id: str,
    driver: str = Query(
        ..., description="Three-letter driver code, for example VER"
    ),
) -> StrategyResponse:
    """Return a pit window recommendation for one driver."""
    driver_code = _validate_driver_code(driver)
    driver_stints = _load_driver_stints(race_id, driver_code)
    recommendation = estimate_pit_window(driver_stints, race_id, driver_code)

    return StrategyResponse(
        race_id=recommendation.race_id,
        driver_code=recommendation.driver_code,
        recommended_pit_window_start=(
            recommendation.recommended_pit_window_start
        ),
        recommended_pit_window_end=(
            recommendation.recommended_pit_window_end
        ),
        current_stint_avg_pace=recommendation.current_stint_avg_pace,
        degradation_slope=recommendation.degradation_slope,
        urgency=recommendation.urgency,
        explanation=recommendation.explanation,
        degradation_slope_used=recommendation.degradation_slope_used,
        threshold_used=recommendation.threshold_used,
        projected_lap_delta_seconds=(
            recommendation.projected_lap_delta_seconds
        ),
        confidence=recommendation.confidence,
        baseline_strategy=recommendation.baseline_strategy,
        baseline_delta_seconds=recommendation.baseline_delta_seconds,
    )
