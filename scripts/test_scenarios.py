"""Manual QA scenarios for the running backend API.

Run the backend with ``uvicorn backend.app.main:app`` and then execute this
script to hit the key endpoints and print responses for human review.
"""

import json

import requests

BASE = "http://127.0.0.1:8000"


def run_scenario(
    label: str,
    url: str,
    params: dict[str, str | int],
) -> dict:
    """Call one API endpoint and print a truncated response payload."""
    print(f"\n{'=' * 60}")
    print(f"TEST: {label}")
    print(f"GET {url} {params}")

    response = requests.get(f"{BASE}{url}", params=params, timeout=30)
    print(f"STATUS: {response.status_code}")

    data = response.json()
    print(json.dumps(data, indent=2)[:1000])
    return data


run_scenario(
    "Normal stint",
    "/race/2024_monza_race/strategy",
    {"driver": "VER", "stint_number": 2},
)

stints = run_scenario(
    "Get stints",
    "/race/2024_monza_race/stints",
    {"driver": "VER"},
)
last_stint = max(stint["stint_number"] for stint in stints["stints"])
run_scenario(
    "Late-race stint",
    "/race/2024_monza_race/strategy",
    {"driver": "VER", "stint_number": last_stint},
)

run_scenario(
    "First stint",
    "/race/2024_monza_race/strategy",
    {"driver": "VER", "stint_number": 1},
)

run_scenario(
    "Invalid stint",
    "/race/2024_monza_race/strategy",
    {"driver": "VER", "stint_number": 99},
)

run_scenario(
    "Default stint",
    "/race/2024_monza_race/strategy",
    {"driver": "VER"},
)

run_scenario("List races", "/races", {})

print(f"\n{'=' * 60}")
print("QA COMPLETE — review output above for correctness")
