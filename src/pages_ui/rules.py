"""Manage categorization rules. See specs/07-ux.md §2.5, specs/04-categorization.md."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.domain.models import CategoryRule
from src.storage import config_store


def render(data_home) -> None:
    st.header("Rules")
    st.caption("Substring match, longest pattern wins; ties break by order below. Delete a row to disable.")

    rules = config_store.load_rules(data_home)
    df = pd.DataFrame(
        [{"pattern": r.pattern, "type": r.type, "category": r.category or ""} for r in rules],
        columns=["pattern", "type", "category"],
    )

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "type": st.column_config.SelectboxColumn("Type", options=["income", "expense", "skip"]),
        },
    )

    if st.button("Save rules"):
        new_rules = [
            CategoryRule(
                pattern=str(row["pattern"]).strip(),
                type=row["type"],
                category=str(row["category"]).strip() or None if row["type"] != "skip" else None,
            )
            for _, row in edited.iterrows()
            if str(row["pattern"]).strip()
        ]
        config_store.save_rules(data_home, new_rules)
        st.success("Saved.")
        st.rerun()
