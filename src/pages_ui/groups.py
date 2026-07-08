"""Manage the expense category -> group map. See specs/07-ux.md §2.6, specs/01-domain-model.md §2.2."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analysis.aggregate import build_records
from src.analysis.groups import unmapped_categories
from src.storage import config_store


def render(data_home) -> None:
    st.header("Groups")
    st.caption("Editing this map never touches transactions — it only affects analysis fold-up.")

    mapping = config_store.load_category_groups(data_home)
    records = build_records(data_home)
    expense_categories = sorted({r.category for r in records if r.type == "expense" and r.category})

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
