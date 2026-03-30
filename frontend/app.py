import streamlit as st
import requests
import pandas as pd

st.title("F1 Dashboard (MVP)")

BACKEND_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_RACE_ID = "2024_monza_race"
default_driver = "VER"

driver_code = st.text_input("Driver code", value=default_driver).strip().upper()
st.caption(f"Race: {DEFAULT_RACE_ID}")

try:
    response = requests.get(
        f"{BACKEND_BASE_URL}/race/{DEFAULT_RACE_ID}/laps",
        params={"driver": driver_code},
        timeout=30,
    )
    if response.status_code >= 400:
        detail = response.json().get("detail", "Unknown backend error")
        st.error(f"Backend error: {detail}")
        st.stop()

    data = response.json()
except requests.RequestException as exc:
    st.error(f"Failed to fetch data from backend: {exc}")
else:
    laps_df = pd.DataFrame(data["laps"])

    st.subheader(f"{data['driver_code']} lap times")
    if laps_df.empty:
        st.warning("No lap data returned.")
    else:
        st.line_chart(laps_df, x="lap_number", y="lap_time_seconds")
        st.dataframe(laps_df, use_container_width=True)
