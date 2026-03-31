import logging
import time

from fastapi import APIRouter, HTTPException, Query

from backend.app.config import SUPPORTED_RACES
from backend.app.domain.models import DriverStint, NormalizedLap
from backend.app.schemas.laps import LapItemResponse, LapsResponse
from backend.app.schemas.stints import StintItemResponse, StintsResponse
from backend.app.schemas.strategy import StrategyResponse
from backend.app.services.analytics import build_driver_stints
from backend.app.services.cache import get_cached_laps
from backend.app.services.cache import get_cached_strategy
from backend.app.services.cache import set_cached_laps
from backend.app.services.cache import set_cached_strategy
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
logger = logging.getLogger(__name__)


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
    total_t0 = time.perf_counter()

    if race_id not in SUPPORTED_RACES:
        raise HTTPException(
            status_code=404,
            detail=f"Unsupported race_id: {race_id}",
        )

    try:
        cached_laps = get_cached_laps(race_id)
        if cached_laps is not None:
            logger.info("[%s] using in-memory laps cache", race_id)
            return cached_laps

        if session_exists(race_id):
            logger.info("[%s] loading laps from database", race_id)
            db_t0 = time.perf_counter()
            db_laps = load_laps_from_db(race_id)
            logger.info(
                "[%s] db load: %.3fs",
                race_id,
                time.perf_counter() - db_t0,
            )
            set_cached_laps(race_id, db_laps)
            return db_laps

        logger.info("[%s] cache miss, loading laps from FastF1", race_id)
        race_config = SUPPORTED_RACES[race_id]

        fastf1_t0 = time.perf_counter()
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
        logger.info(
            "[%s] fastf1 load: %.3fs",
            race_id,
            time.perf_counter() - fastf1_t0,
        )

        normalization_t0 = time.perf_counter()
        normalized_laps = normalize_laps(raw_laps, race_id)
        logger.info(
            "[%s] normalization: %.3fs",
            race_id,
            time.perf_counter() - normalization_t0,
        )

        persistence_t0 = time.perf_counter()
        save_session_data(race_id, race_config, normalized_laps)
        logger.info(
            "[%s] persistence: %.3fs",
            race_id,
            time.perf_counter() - persistence_t0,
        )

        set_cached_laps(race_id, normalized_laps)
        return normalized_laps
    finally:
        logger.info(
            "[%s] ingestion total: %.3fs",
            race_id,
            time.perf_counter() - total_t0,
        )


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

    analytics_t0 = time.perf_counter()
    driver_stints = build_driver_stints(normalized_laps, race_id, driver_code)
    logger.info(
        "[%s][%s] analytics: %.3fs",
        race_id,
        driver_code,
        time.perf_counter() - analytics_t0,
    )

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
    total_t0 = time.perf_counter()
    driver_code = _validate_driver_code(driver)

    try:
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
    finally:
        logger.info(
            "[%s][%s] laps endpoint total: %.3fs",
            race_id,
            driver_code,
            time.perf_counter() - total_t0,
        )


@router.get("/race/{race_id}/stints", response_model=StintsResponse)
def get_race_stints(
    race_id: str,
    driver: str = Query(
        ..., description="Three-letter driver code, for example VER"
    ),
) -> StintsResponse:
    """Return stint summaries with degradation slopes for one driver."""
    total_t0 = time.perf_counter()
    driver_code = _validate_driver_code(driver)

    try:
        driver_stints = _load_driver_stints(race_id, driver_code)

        return StintsResponse(
            race_id=race_id,
            driver_code=driver_code,
            stints=[
                StintItemResponse.model_validate(stint)
                for stint in driver_stints
            ],
        )
    finally:
        logger.info(
            "[%s][%s] stints endpoint total: %.3fs",
            race_id,
            driver_code,
            time.perf_counter() - total_t0,
        )


@router.get("/race/{race_id}/strategy", response_model=StrategyResponse)
def get_race_strategy(
    race_id: str,
    driver: str = Query(
        ..., description="Three-letter driver code, for example VER"
    ),
) -> StrategyResponse:
    """Return a pit window recommendation for one driver."""
    total_t0 = time.perf_counter()
    driver_code = _validate_driver_code(driver)

    try:
        cached_recommendation = get_cached_strategy(race_id, driver_code)
        if cached_recommendation is not None:
            logger.info(
                "[%s][%s] using cached strategy recommendation",
                race_id,
                driver_code,
            )
            recommendation = cached_recommendation
        else:
            driver_stints = _load_driver_stints(race_id, driver_code)
            strategy_t0 = time.perf_counter()
            recommendation = estimate_pit_window(
                driver_stints,
                race_id,
                driver_code,
            )
            logger.info(
                "[%s][%s] strategy compute: %.3fs",
                race_id,
                driver_code,
                time.perf_counter() - strategy_t0,
            )
            set_cached_strategy(race_id, driver_code, recommendation)

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
    finally:
        logger.info(
            "[%s][%s] strategy endpoint total: %.3fs",
            race_id,
            driver_code,
            time.perf_counter() - total_t0,
        )
