import requests
import streamlit as st
import pandas as pd

st.title("F1 Dashboard (MVP)")

BACKEND_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_RACE_ID = "2024_monza_race"
DEFAULT_DRIVER = "VER"


def get_backend_json(path: str, params: dict[str, str]) -> dict:
    response = requests.get(
        f"{BACKEND_BASE_URL}{path}", params=params, timeout=30
    )
    if response.status_code >= 400:
        detail = response.json().get("detail", "Unknown backend error")
        raise requests.HTTPError(detail, response=response)

    return response.json()


driver_code = st.text_input("Driver code", value=DEFAULT_DRIVER).strip().upper()
st.caption(f"Race: {DEFAULT_RACE_ID}")

try:
    laps_data = get_backend_json(
        f"/race/{DEFAULT_RACE_ID}/laps",
        params={"driver": driver_code},
    )
    strategy_data = get_backend_json(
        f"/race/{DEFAULT_RACE_ID}/strategy",
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

    st.subheader("Strategy")
    pit_window = (
        f"Lap {strategy_data['recommended_pit_window_start']}"
        f"-{strategy_data['recommended_pit_window_end']}"
    )
    pit_window_col, urgency_col, pace_col, slope_col = st.columns(4)
    pit_window_col.metric("Recommended pit window", pit_window)
    urgency_col.metric("Urgency", strategy_data["urgency"].upper())
    pace_col.metric(
        "Avg stint pace",
        (
            f"{strategy_data['current_stint_avg_pace']:.3f}s"
            if strategy_data["current_stint_avg_pace"] is not None
            else "N/A"
        ),
    )
    slope_col.metric(
        "Degradation slope",
        (
            f"{strategy_data['degradation_slope']:.3f}"
            if strategy_data["degradation_slope"] is not None
            else "N/A"
        ),
    )
    (
        confidence_col,
        projected_delta_col,
        baseline_strategy_col,
        baseline_delta_col,
    ) = st.columns(4)
    confidence_col.metric(
        "Confidence",
        (
            strategy_data["confidence"].upper()
            if strategy_data["confidence"] is not None
            else "N/A"
        ),
    )
    projected_delta_col.metric(
        "Projected lap delta",
        (
            f"{strategy_data['projected_lap_delta_seconds']:.3f}s"
            if strategy_data["projected_lap_delta_seconds"] is not None
            else "N/A"
        ),
    )
    baseline_strategy_col.write("Baseline strategy")
    baseline_strategy_col.write(
        strategy_data["baseline_strategy"]
        if strategy_data["baseline_strategy"] is not None
        else "N/A"
    )
    baseline_delta_col.metric(
        "Baseline delta",
        (
            f"{strategy_data['baseline_delta_seconds']:.3f}s"
            if strategy_data["baseline_delta_seconds"] is not None
            else "N/A"
        ),
    )
    st.caption(strategy_data["explanation"])

    st.subheader("Stints")
    if stints_df.empty:
        st.warning("No stint data returned.")
    else:
        st.bar_chart(stints_df, x="stint_number", y="avg_lap_time_seconds")
        st.dataframe(
            stints_df[
                [
                    "stint_number",
                    "tyre_compound",
                    "start_lap",
                    "end_lap",
                    "stint_length",
                    "avg_lap_time_seconds",
                    "degradation_slope",
                ]
            ],
            use_container_width=True,
        )
