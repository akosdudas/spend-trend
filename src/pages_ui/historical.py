"""Read-only view of closed/legacy years. See specs/07-ux.md §2.7, specs/05-historical-data.md."""

from __future__ import annotations

import streamlit as st

from src.analysis.groups import unmapped_categories
from src.storage import config_store, year_store


def render(data_home) -> None:
    st.header("Historical")

    years = [
        y for y in year_store.list_years(data_home) if year_store.year_state(data_home, y) == "summarized"
    ]
    if not years:
        st.info("No closed or legacy years yet.")
        return

    shared_map = config_store.load_category_groups(data_home)

    for year in sorted(years, reverse=True):
        with st.expander(str(year), expanded=False):
            for warning in year_store.load_summary_malformed_rows(data_home, year):
                st.warning(warning)

            rows = year_store.load_summary(data_home, year)
            expense_categories = {r.category for r in rows if r.type == "expense"}
            snapshot = year_store.load_year_groups_snapshot(data_home, year)
            unmapped = unmapped_categories(
                expense_categories, snapshot if snapshot is not None else shared_map
            )
            if unmapped:
                st.warning(f"Unmapped categories (fold into Rest): {', '.join(sorted(unmapped))}")

            st.dataframe(
                [
                    {"type": r.type, "category": r.category, "currency": r.currency, "amount": str(r.amount)}
                    for r in rows
                ],
                use_container_width=True,
                hide_index=True,
            )
