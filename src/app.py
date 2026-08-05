"""Streamlit UI entrypoint. Screens per specs/07-ux.md."""

from __future__ import annotations

import streamlit as st

from src.storage.paths import resolve_data_home

st.set_page_config(page_title="spend-trends", layout="wide")

resolve_data_home()  # fail fast with a clear message if no data home is configured

with st.sidebar:
    st.title("spend-trends")

pages = [
    st.Page("pages_ui/page_dashboard.py", title="Dashboard", icon="📊", default=True),
    st.Page("pages_ui/page_analyze.py", title="Analyze", icon="🔍"),
    st.Page("pages_ui/page_data.py", title="Data", icon="🧾"),
    st.Page("pages_ui/page_profiles.py", title="Profiles", icon="🏦"),
    st.Page("pages_ui/page_rules.py", title="Rules", icon="📐"),
    st.Page("pages_ui/page_groups.py", title="Groups", icon="🗂️"),
    st.Page("pages_ui/page_historical.py", title="Historical", icon="📜"),
    st.Page("pages_ui/page_settings.py", title="Settings", icon="⚙️"),
]

st.navigation(pages).run()
