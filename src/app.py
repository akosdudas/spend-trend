"""Streamlit UI entrypoint. Screens per specs/07-ux.md."""

from __future__ import annotations

import streamlit as st

from src.pages_ui import analyze, dashboard, data_grid, groups, historical, profiles, rules, settings
from src.storage.paths import resolve_data_home

st.set_page_config(page_title="spend-trends", layout="wide")

data_home = resolve_data_home()

PAGES = {
    "Dashboard": dashboard,
    "Analyze": analyze,
    "Data": data_grid,
    "Profiles": profiles,
    "Rules": rules,
    "Groups": groups,
    "Historical": historical,
    "Settings": settings,
}

with st.sidebar:
    st.title("spend-trends")
    choice = st.radio("Section", list(PAGES.keys()), label_visibility="collapsed")
    assert choice is not None  # a non-empty options list always yields a selection

PAGES[choice].render(data_home)
