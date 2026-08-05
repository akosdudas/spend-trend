"""Manage the shared expense category -> group map. See specs/07-ux.md §2.6, specs/01-domain-model.md §2.2."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analysis.groups import unmapped_categories
from src.storage import config_store, year_store


def _open_year_expense_categories(data_home) -> set[str]:
    """Categories actually in scope for the shared draft map — open years only."""
    categories: set[str] = set()
    for year in year_store.list_years(data_home):
        if year_store.year_state(data_home, year) != "open":
            continue
        for t in year_store.load_transactions(data_home, year):
            if t.type == "expense" and t.category:
                categories.add(t.category)
    return categories


def render(data_home) -> None:
    st.header("Groups")
    st.caption(
        "The current working draft for open years — prune it freely. A closed year keeps its own "
        "groups.json snapshot instead (Settings). Editing this map never touches transactions."
    )

    mapping = config_store.load_category_groups(data_home)
    expense_categories = sorted(_open_year_expense_categories(data_home))

    unmapped = unmapped_categories(set(expense_categories), mapping)
    if unmapped:
        st.warning(f"Unmapped (fold into Rest until mapped): {', '.join(sorted(unmapped))}")

    rows = [{"category": c, "group": mapping.get(c, "Rest")} for c in expense_categories]
    seen = {r["category"] for r in rows}
    for category, group in mapping.items():
        if category not in seen:
            rows.append({"category": category, "group": group})

    edited = st.data_editor(
        pd.DataFrame(rows, columns=["category", "group"]),
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
    )

    if st.button("Save mapping"):
        new_mapping = {
            str(row["category"]).strip(): str(row["group"]).strip()
            for _, row in edited.iterrows()
            if str(row["category"]).strip() and str(row["group"]).strip()
        }
        config_store.save_category_groups(data_home, new_mapping)
        st.success("Saved.")
        st.rerun()
