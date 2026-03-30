from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.ingestion import load_session, get_raw_laps
from backend.app.services.normalization import normalize_laps, filter_driver_laps

RACE_ID = "2024_monza_race"
DRIVER = "VER"

session = load_session(RACE_ID)
raw_laps = get_raw_laps(session)

print("Raw row count:", len(raw_laps))
print("Raw columns:", list(raw_laps.columns))

normalized_laps = normalize_laps(raw_laps, RACE_ID)
print("Normalized row count:", len(normalized_laps))

driver_laps = filter_driver_laps(normalized_laps, DRIVER)
print(f"{DRIVER} lap count:", len(driver_laps))

print("\nFirst 5 normalized laps:")
for lap in driver_laps[:5]:
    print(lap)
