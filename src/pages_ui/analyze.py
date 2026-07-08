"""The pivot + chart builder. See specs/06-analysis.md, specs/07-ux.md §2.2."""

from __future__ import annotations

import streamlit as st

from src.analysis.aggregate import GROUP_BY_DIMENSIONS, build_records, filter_records
from src.pages_ui.view_rendering import render_view
from src.storage import config_store

MEASURES = ["Sum of amount", "Savings rate", "Spend as % of income", "Group share of spend"]
CHART_TYPES = ["table", "bar", "stacked bar", "line", "pie"]


def render(data_home) -> None:
    st.header("Analyze")

    records = build_records(data_home)
    if not records:
        st.info("No data yet — import some transactions on the Data screen first.")
        return

    years = sorted({r.year for r in records})
    types: list[str] = sorted({r.type for r in records})
    categories = sorted({r.category for r in records if r.category})
    groups = sorted({r.group for r in records if r.group})
    currencies = sorted({r.currency for r in records})

    with st.expander("Filters", expanded=False):
        f_years = st.multiselect("Year(s)", years)
        f_types = st.multiselect("Type", types)
        f_categories = st.multiselect("Category", categories)
        f_groups = st.multiselect("Group", groups)
        f_currencies = st.multiselect("Currency", currencies)
        f_text = st.text_input("Text search (category / merchant)")

    col1, col2, col3 = st.columns(3)
    group_by = col1.multiselect("Group by", GROUP_BY_DIMENSIONS, default=["category"], max_selections=2)
    measure = col2.selectbox("Measure", MEASURES)
    chart_type = col3.selectbox("Chart type", CHART_TYPES)
    assert measure is not None and chart_type is not None  # non-empty options always yield a selection

    filtered = filter_records(
        records,
        years=f_years or None,
        types=f_types or None,
        categories=f_categories or None,
        groups=f_groups or None,
        currencies=f_currencies or None,
        text=f_text or None,
    )

    if not filtered:
        st.warning("No rows match these filters.")
        return

    render_view(filtered, group_by, measure, chart_type)

    st.divider()
    _render_save_view(
        data_home,
        group_by,
        measure,
        chart_type,
        f_years,
        f_types,
        f_categories,
        f_groups,
        f_currencies,
        f_text,
    )


def _render_save_view(
    data_home, group_by, measure, chart_type, f_years, f_types, f_categories, f_groups, f_currencies, f_text
) -> None:
    name = st.text_input("View name")
    width = st.selectbox("Width", ["quarter", "half", "full"], index=1)
    if st.button("Save as view") and name:
        views = config_store.load_saved_views(data_home)
        views.append(
            {
                "name": name,
                "groupBy": group_by,
                "measure": measure,
                "chartType": chart_type,
                "width": width,
                "filters": {
                    "years": f_years,
                    "types": f_types,
                    "categories": f_categories,
                    "groups": f_groups,
                    "currencies": f_currencies,
                    "text": f_text,
                },
            }
        )
        config_store.save_saved_views(data_home, views)
        st.success(f"Saved '{name}'.")
