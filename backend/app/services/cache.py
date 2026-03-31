"""Simple in-memory caches for laps and strategy recommendations."""

from __future__ import annotations

import logging

from backend.app.domain.models import NormalizedLap
from backend.app.domain.models import StrategyRecommendation

logger = logging.getLogger(__name__)

_session_cache: dict[str, list[NormalizedLap]] = {}
_strategy_cache: dict[str, StrategyRecommendation] = {}
_cache_counters: dict[str, int] = {
    "laps_hits": 0,
    "laps_misses": 0,
    "strategy_hits": 0,
    "strategy_misses": 0,
}


def _strategy_cache_key(race_id: str, driver_code: str) -> str:
    """Build a stable cache key for one driver strategy lookup."""
    normalized_driver_code = driver_code.upper().strip()
    return f"{race_id}:{normalized_driver_code}"


def get_cached_laps(race_id: str) -> list[NormalizedLap] | None:
    """Return cached laps for a race, if present."""
    laps = _session_cache.get(race_id)
    if laps is None:
        _cache_counters["laps_misses"] += 1
        logger.info("lap cache miss for race_id=%s", race_id)
        return None

    _cache_counters["laps_hits"] += 1
    logger.info("lap cache hit for race_id=%s", race_id)
    return laps


def set_cached_laps(race_id: str, laps: list[NormalizedLap]) -> None:
    """Store normalized laps in the in-memory session cache."""
    _session_cache[race_id] = laps


def get_cached_strategy(
    race_id: str,
    driver_code: str,
) -> StrategyRecommendation | None:
    """Return a cached strategy recommendation, if present."""
    cache_key = _strategy_cache_key(race_id, driver_code)
    recommendation = _strategy_cache.get(cache_key)
    if recommendation is None:
        _cache_counters["strategy_misses"] += 1
        logger.info(
            "strategy cache miss for race_id=%s driver_code=%s",
            race_id,
            driver_code.upper().strip(),
        )
        return None

    _cache_counters["strategy_hits"] += 1
    logger.info(
        "strategy cache hit for race_id=%s driver_code=%s",
        race_id,
        driver_code.upper().strip(),
    )
    return recommendation


def set_cached_strategy(
    race_id: str,
    driver_code: str,
    rec: StrategyRecommendation,
) -> None:
    """Store a strategy recommendation in the in-memory cache."""
    cache_key = _strategy_cache_key(race_id, driver_code)
    _strategy_cache[cache_key] = rec


def cache_stats() -> dict[str, int]:
    """Return cache entry counts and aggregate hit/miss counters."""
    return {
        "lap_cache_entries": len(_session_cache),
        "strategy_cache_entries": len(_strategy_cache),
        "lap_cache_hits": _cache_counters["laps_hits"],
        "lap_cache_misses": _cache_counters["laps_misses"],
        "strategy_cache_hits": _cache_counters["strategy_hits"],
        "strategy_cache_misses": _cache_counters["strategy_misses"],
    }
