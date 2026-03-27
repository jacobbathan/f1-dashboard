import fastf1

fastf1.Cache.enable_cache("cache")

session = fastf1.get_session(2024, "Italian Grand Prix", "R")
session.load()

laps = session.laps

print(laps.columns)
print(laps.head())
