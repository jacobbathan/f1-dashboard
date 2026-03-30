import streamlit as st
import requests
import pandas as pd

st.title("F1 Dashboard (MVP)")

BACKEND_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_RACE_ID = "2024_monza_race"
default_driver = "VER"


def get_backend_json(path: str, params: dict[str, str]) -> dict:
    response = requests.get(f"{BACKEND_BASE_URL}{path}", params=params, timeout=30)
    if response.status_code >= 400:
        detail = response.json().get("detail", "Unknown backend error")
        raise requests.HTTPError(detail, response=response)

    return response.json()


driver_code = st.text_input("Driver code", value=default_driver).strip().upper()
st.caption(f"Race: {DEFAULT_RACE_ID}")

try:
    laps_data = get_backend_json(
        f"/race/{DEFAULT_RACE_ID}/laps",
        params={"driver": driver_code},
    )
    stints_data = get_backend_json(
        f"/race/{DEFAULT_RACE_ID}/stints",
        params={"driver": driver_code},
    )
except requests.RequestException as exc:
    st.error(f"Failed to fetch data from backend: {exc}")
else:
    laps_df = pd.DataFrame(laps_data["laps"])
    stints_df = pd.DataFrame(stints_data["stints"])

    st.subheader(f"{laps_data['driver_code']} lap times")
    if laps_df.empty:
        st.warning("No lap data returned.")
    else:
        st.line_chart(laps_df, x="lap_number", y="lap_time_seconds")
        st.dataframe(laps_df, use_container_width=True)

    st.subheader("Stints")
    if stints_df.empty:
        st.warning("No stint data returned.")
    else:
        st.bar_chart(stints_df, x="stint_number", y="avg_lap_time_seconds")
        st.dataframe(stints_df, use_container_width=True)
