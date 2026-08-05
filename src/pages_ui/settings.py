"""Data folder + year lifecycle. See specs/07-ux.md §2.8, specs/02-storage.md §4."""

from __future__ import annotations

import streamlit as st

from src.storage import year_store


def render(data_home) -> None:
    st.header("Settings")
    st.write(f"Data folder: `{data_home}`")
    st.caption("Changing it is a file edit or launcher argument, not an in-app picker.")

    st.subheader("Close / reopen a year")
    st.caption(
        "Closing compiles summary.csv from transactions.csv and, if none exists yet, snapshots the "
        "shared Groups map into that year's own groups.json. Reversible by reopening; groups.json is "
        "left in place, so re-closing keeps any hand-edits to it."
    )

    years = year_store.list_years(data_home)
    if not years:
        st.info("No years yet.")
        return

    year = st.selectbox("Year", sorted(years, reverse=True))
    assert year is not None  # a non-empty options list always yields a selection
    state = year_store.year_state(data_home, year)
    st.write(f"State: **{state}**")

    if state == "open":
        if st.button("Close year"):
            year_store.close_year(data_home, year)
            st.rerun()
    elif state == "summarized":
        if st.button("Reopen year"):
            year_store.reopen_year(data_home, year)
            st.rerun()
