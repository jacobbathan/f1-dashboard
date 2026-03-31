import fastf1

# Dev-only script for poking at FastF1 data with a known race session.
fastf1.Cache.enable_cache("cache")

session = fastf1.get_session(2024, "Italian Grand Prix", "R")
session.load()

laps = session.laps

print(laps.columns)
print(laps.head())
