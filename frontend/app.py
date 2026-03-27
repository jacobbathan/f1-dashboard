import streamlit as st
import requests

st.title("F1 Dashboard (MVP)")

try:
    response = requests.get("http://127.0.0.1:8000/debug/laps", timeout=10)
    response.raise_for_status()
    data = response.json()
except requests.RequestException as exc:
    st.error(f"Failed to fetch data from backend: {exc}")
else:
    st.write("Columns:", data["columns"])
    st.write("Row Count:", data["row_count"])
