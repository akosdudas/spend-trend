"""Saved views in a flow grid. See specs/07-ux.md §2.1, specs/06-analysis.md §2."""

from __future__ import annotations

import streamlit as st

from src.analysis.aggregate import build_records, filter_records, needs_attention_count
from src.pages_ui.view_rendering import render_view
from src.storage import config_store

WIDTH_SPAN = {"quarter": 1, "half": 2, "full": 4}


def render(data_home) -> None:
    st.header("Dashboard")

    records = build_records(data_home)
    st.caption(f"Needs attention: {needs_attention_count(records)} uncategorized row(s)")

    views = config_store.load_saved_views(data_home)
    if not views:
        st.info("No saved views yet — build one on the Analyze screen and click 'Save as view'.")
        return

    rows: list[list[int]] = []
    current_row: list[int] = []
    total = 0
    for idx, view in enumerate(views):
        span = WIDTH_SPAN.get(view.get("width", "half"), 2)
        if current_row and total + span > 4:
            rows.append(current_row)
            current_row = []
            total = 0
        current_row.append(idx)
        total += span
    if current_row:
        rows.append(current_row)

    for row in rows:
        cols = st.columns([WIDTH_SPAN.get(views[idx].get("width", "half"), 2) for idx in row])
        for col, idx in zip(cols, row, strict=True):
            with col:
                _render_view_card(data_home, records, views, idx)


def _render_view_card(data_home, records, views: list[dict], idx: int) -> None:
    view = views[idx]
    st.subheader(view.get("name", "View"))

    filters = view.get("filters", {})
    filtered = filter_records(
        records,
        years=filters.get("years") or None,
        types=filters.get("types") or None,
        categories=filters.get("categories") or None,
        groups=filters.get("groups") or None,
        currencies=filters.get("currencies") or None,
        text=filters.get("text") or None,
    )
    render_view(
        filtered,
        view.get("groupBy", []),
        view.get("measure", "Sum of amount"),
        view.get("chartType", "table"),
    )

    c1, c2, c3 = st.columns(3)
    if c1.button("↑", key=f"up_{idx}", disabled=idx == 0):
        views[idx - 1], views[idx] = views[idx], views[idx - 1]
        config_store.save_saved_views(data_home, views)
        st.rerun()
    if c2.button("↓", key=f"down_{idx}", disabled=idx == len(views) - 1):
        views[idx + 1], views[idx] = views[idx], views[idx + 1]
        config_store.save_saved_views(data_home, views)
        st.rerun()
    if c3.button("Remove", key=f"del_{idx}"):
        views.pop(idx)
        config_store.save_saved_views(data_home, views)
        st.rerun()
