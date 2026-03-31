"""Configuration modules for supported race sessions and strategy tuning."""

from typing import TypedDict


class RaceConfig(TypedDict):
    """Configuration entry for a single supported race session."""

    season: int
    event_name: str
    session_name: str


SUPPORTED_RACES: dict[str, RaceConfig] = {
    "2024_monza_race": {
        "season": 2024,
        "event_name": "Italian Grand Prix",
        "session_name": "R",
    },
    "2024_spa_race": {
        "season": 2024,
        "event_name": "Belgian Grand Prix",
        "session_name": "R",
    },
    "2024_silverstone_race": {
        "season": 2024,
        "event_name": "British Grand Prix",
        "session_name": "R",
    },
    "2024_monaco_race": {
        "season": 2024,
        "event_name": "Monaco Grand Prix",
        "session_name": "R",
    },
}
