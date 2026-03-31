"""Tunable heuristic constants used by the strategy recommendation logic."""

MIN_LAPS_FOR_SLOPE = 4
LOW_DEGRADATION_THRESHOLD = 0.02
MEDIUM_DEGRADATION_THRESHOLD = 0.05
PROJECTION_HORIZON_LAPS = 4

URGENCY_MAP = {
    "low": {"start_offset": 4, "end_offset": 6},
    "medium": {"start_offset": 2, "end_offset": 4},
    "high": {"start_offset": 1, "end_offset": 2},
}

BASELINE_STRATEGY_NAME = "pit_at_stint_midpoint"
