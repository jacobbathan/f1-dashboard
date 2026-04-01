import html

import pandas as pd
import requests
import streamlit as st
import os

st.set_page_config(page_title="F1 Strategy Dashboard", layout="wide")

st.markdown(
    """
    <style>
    @import url("https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap");
    div[data-testid="stMetric"] {
        background: #1a1a2e;
        border: 1px solid #333;
        border-radius: 8px;
        min-height: 7rem;
        padding: 0.85rem;
    }
    div[data-testid="stMetricLabel"] p {
        color: #aaa;
        white-space: normal;
    }
    div[data-testid="stMetricValue"] {
        color: #fff;
        font-family: "JetBrains Mono", monospace;
        font-size: 1.15rem;
        line-height: 1.3;
        overflow-wrap: anywhere;
        white-space: normal;
    }
    .text-card {
        background: #1a1a2e;
        border: 1px solid #333;
        border-radius: 8px;
        min-height: 7rem;
        padding: 0.85rem;
    }
    .text-card__label {
        color: #aaa;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    .text-card__value {
        color: #fff;
        font-family: "JetBrains Mono", monospace;
        font-size: 1rem;
        line-height: 1.35;
        overflow-wrap: anywhere;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

BACKEND_BASE_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
DEFAULT_DRIVER = "VER"


def get_backend_json(
    path: str,
    params: dict[str, str | int] | None = None,
) -> dict:
    """Fetch JSON data from the backend API."""
    response = requests.get(f"{BACKEND_BASE_URL}{path}", params=params, timeout=30)
    if response.status_code >= 400:
        detail = response.json().get("detail", "Unknown backend error")
        raise requests.HTTPError(detail, response=response)

    return response.json()


def format_optional_float(
    value: float | int | None,
    precision: int,
    suffix: str = "",
) -> str:
    """Format an optional numeric value for display."""
    if value is None or pd.isna(value):
        return "N/A"
    return f"{float(value):.{precision}f}{suffix}"


def format_optional_text(value: object | None) -> str:
    """Format an optional value as display text."""
    if value is None or pd.isna(value):
        return "N/A"
    return str(value)


def render_text_card(label: str, value: str) -> None:
    """Render a wrapped text card for longer non-metric values."""
    safe_label = html.escape(label)
    safe_value = html.escape(value)
    st.markdown(
        f"""
        <div class="text-card">
            <div class="text-card__label">{safe_label}</div>
            <div class="text-card__value">{safe_value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_lap_chart_spec(
    laps_df: pd.DataFrame,
    stints_df: pd.DataFrame,
) -> dict:
    """Build a lap-time chart with stint-start markers."""
    stint_markers = (
        stints_df[["start_lap"]]
        .dropna()
        .drop_duplicates()
        .rename(columns={"start_lap": "lap_number"})
        .sort_values("lap_number")
    )
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "height": 360,
        "data": {"values": laps_df.to_dict("records")},
        "layer": [
            {
                "mark": {
                    "type": "line",
                    "color": "#ff5c5c",
                    "strokeWidth": 3,
                    "point": False,
                },
                "encoding": {
                    "x": {
                        "field": "lap_number",
                        "type": "quantitative",
                        "title": "Lap",
                    },
                    "y": {
                        "field": "lap_time_seconds",
                        "type": "quantitative",
                        "title": "Lap Time (s)",
                    },
                    "tooltip": [
                        {"field": "lap_number", "title": "Lap"},
                        {
                            "field": "lap_time_seconds",
                            "title": "Lap Time (s)",
                            "format": ".3f",
                        },
                        {
                            "field": "tyre_compound",
                            "title": "Compound",
                        },
                    ],
                },
            },
            {
                "data": {"values": stint_markers.to_dict("records")},
                "mark": {
                    "type": "rule",
                    "color": "#ffd166",
                    "strokeDash": [6, 4],
                    "strokeWidth": 2,
                },
                "encoding": {
                    "x": {
                        "field": "lap_number",
                        "type": "quantitative",
                    }
                },
            },
        ],
    }


st.title("F1 Strategy Dashboard")

with st.spinner("Loading session data..."):
    try:
        races_response = get_backend_json("/races", params={})
        race_options = {
            race["race_id"]: race["label"] for race in races_response["races"]
        }
    except Exception:
        race_options = {"2024_monza_race": "Italian Grand Prix"}

st.sidebar.header("Session Controls")
selected_race_id = st.sidebar.selectbox(
    "Race",
    options=race_options.keys(),
    format_func=lambda race_id: race_options[race_id],
)
driver_code = st.sidebar.text_input("Driver code", value=DEFAULT_DRIVER).strip().upper()

with st.spinner("Loading session data..."):
    try:
        laps_data = get_backend_json(
            f"/race/{selected_race_id}/laps",
            params={"driver": driver_code},
        )
        stints_data = get_backend_json(
            f"/race/{selected_race_id}/stints",
            params={"driver": driver_code},
        )
    except requests.RequestException as exc:
        st.error(f"Failed to fetch data from backend: {exc}")
        st.stop()

strategy_data: dict | None = None
strategy_error_message: str | None = None
stint_numbers = [stint["stint_number"] for stint in stints_data.get("stints", [])]
selected_stint: int | None = None

if stint_numbers:
    selected_stint = st.sidebar.selectbox(
        "Stint to analyze",
        options=stint_numbers,
        index=len(stint_numbers) - 1,
    )

    with st.spinner("Loading session data..."):
        try:
            strategy_data = get_backend_json(
                f"/race/{selected_race_id}/strategy",
                params={
                    "driver": driver_code,
                    "stint_number": selected_stint,
                },
            )
        except requests.HTTPError as exc:
            if str(exc) == "Strategy is only available for race sessions.":
                strategy_error_message = str(exc)
            else:
                strategy_error_message = f"Failed to fetch strategy from backend: {exc}"
        except requests.RequestException as exc:
            strategy_error_message = f"Failed to fetch strategy from backend: {exc}"

laps_df = pd.DataFrame(laps_data.get("laps", []))
stints_df = pd.DataFrame(stints_data.get("stints", []))

selected_stint_data = next(
    (
        stint
        for stint in stints_data.get("stints", [])
        if stint["stint_number"] == selected_stint
    ),
    None,
)
latest_stint_data = max(
    stints_data.get("stints", []),
    key=lambda stint: stint["end_lap"],
    default=None,
)

best_lap = None
avg_lap = None
total_laps = 0
if not laps_df.empty:
    best_lap = laps_df["lap_time_seconds"].min()
    avg_lap = laps_df["lap_time_seconds"].mean()
    total_laps = len(laps_df)

pit_window_text = "N/A"
has_recommendation = (
    strategy_data is not None
    and strategy_data.get("recommended_pit_window_start") is not None
    and strategy_data.get("recommended_pit_window_end") is not None
)
if strategy_data is not None:
    if has_recommendation:
        pit_window_text = (
            f"Lap {strategy_data['recommended_pit_window_start']}"
            f"-{strategy_data['recommended_pit_window_end']}"
        )
    else:
        pit_window_text = "None"

kpi_top_left, kpi_top_mid, kpi_top_right = st.columns(3)
kpi_top_left.metric("Best Lap", format_optional_float(best_lap, 3, "s"))
kpi_top_mid.metric("Avg Lap", format_optional_float(avg_lap, 3, "s"))
kpi_top_right.metric("Total Laps", str(total_laps))

kpi_bottom_left, kpi_bottom_mid, kpi_bottom_right = st.columns(3)
kpi_bottom_left.metric(
    "Current Compound",
    format_optional_text(
        None if latest_stint_data is None else latest_stint_data["tyre_compound"]
    ),
)
kpi_bottom_mid.metric(
    "Deg Rate",
    format_optional_float(
        (
            None
            if selected_stint_data is None
            else selected_stint_data["degradation_slope"]
        ),
        4,
    ),
)
kpi_bottom_right.metric("Pit Window", pit_window_text)

st.divider()
st.header("Lap Analysis")
if laps_df.empty:
    st.warning("No lap data returned.")
else:
    st.vega_lite_chart(
        build_lap_chart_spec(laps_df, stints_df),
        use_container_width=True,
    )
    with st.expander("Lap Data Table"):
        st.dataframe(
            laps_df,
            use_container_width=True,
            column_config={
                "lap_number": st.column_config.NumberColumn("Lap"),
                "lap_time_seconds": st.column_config.NumberColumn(
                    "Lap Time (s)",
                    format="%.3f",
                ),
                "driver_code": st.column_config.TextColumn("Driver"),
            },
        )

st.divider()
st.header("Stint Analysis")
if stints_df.empty:
    st.warning("No stint data returned.")
else:
    st.bar_chart(stints_df, x="stint_number", y="avg_lap_time_seconds")
    with st.expander("Stint Data Table"):
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
            column_config={
                "stint_number": st.column_config.NumberColumn("Stint"),
                "tyre_compound": st.column_config.TextColumn("Compound"),
                "start_lap": st.column_config.NumberColumn("Start Lap"),
                "end_lap": st.column_config.NumberColumn("End Lap"),
                "stint_length": st.column_config.NumberColumn("Stint Length"),
                "avg_lap_time_seconds": st.column_config.NumberColumn(
                    "Avg Lap Time (s)",
                    format="%.3f",
                ),
                "degradation_slope": st.column_config.NumberColumn(
                    "Degradation Slope",
                    format="%.4f",
                ),
            },
        )

st.divider()
st.header("Strategy Recommendation")
if strategy_error_message == "Strategy is only available for race sessions.":
    st.warning("Strategy is only available for race sessions.")
elif strategy_error_message is not None:
    st.error(strategy_error_message)
elif strategy_data is not None:
    urgency_text = (
        strategy_data["urgency"].upper()
        if strategy_data["urgency"] is not None
        else "N/A"
    )
    confidence_text = (
        strategy_data["confidence"].upper()
        if strategy_data["confidence"] is not None
        else "N/A"
    )
    avg_pace_text = format_optional_float(
        strategy_data["current_stint_avg_pace"], 3, "s"
    )
    slope_text = format_optional_float(strategy_data["degradation_slope"], 3)
    explanation_text = strategy_data.get("explanation", "No recommendation available.")

    if has_recommendation:
        pit_window_col, urgency_col, pace_col = st.columns([1.6, 1, 1])
        pit_window_col.metric("Recommended pit window", pit_window_text)
        urgency_col.metric("Urgency", urgency_text)
        pace_col.metric("Avg stint pace", avg_pace_text)

        slope_col, confidence_col, projected_delta_col = st.columns(3)
        slope_col.metric("Degradation slope", slope_text)
        confidence_col.metric("Confidence", confidence_text)
        projected_delta_col.metric(
            "Projected lap delta",
            format_optional_float(strategy_data["projected_lap_delta_seconds"], 3, "s"),
        )

        baseline_strategy_col, baseline_delta_col = st.columns([1.6, 1])
        with baseline_strategy_col:
            render_text_card(
                "Baseline strategy",
                format_optional_text(strategy_data["baseline_strategy"]),
            )
        baseline_delta_col.metric(
            "Baseline delta",
            format_optional_float(strategy_data["baseline_delta_seconds"], 3, "s"),
        )
    else:
        st.info(explanation_text)
        urgency_col, confidence_col = st.columns(2)
        urgency_col.metric("Urgency", urgency_text)
        confidence_col.metric("Confidence", confidence_text)

        pace_col, slope_col = st.columns(2)
        pace_col.metric("Avg stint pace", avg_pace_text)
        slope_col.metric("Degradation slope", slope_text)

    st.caption(
        "Stint analyzed: "
        f"{format_optional_text(strategy_data['stint_number'])} | "
        "Race max lap: "
        f"{format_optional_text(strategy_data['race_max_lap'])}"
    )
    st.caption(explanation_text)
