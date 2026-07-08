"""Shared table/chart rendering for a (group-by, measure, chart-type) view.

Used by both the Analyze builder (live preview) and the Dashboard (saved views), so a view renders
identically in both places. See specs/06-analysis.md.
"""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from src.analysis import ratios as ratios_module
from src.analysis.aggregate import Record, aggregate, pivot


def render_view(filtered: list[Record], group_by: list[str], measure: str, chart_type: str) -> None:
    if not filtered:
        st.caption("No rows match this view's filters.")
        return

    if measure == "Sum of amount":
        render_sum_measure(filtered, group_by, chart_type)
    elif measure == "Group share of spend":
        render_group_share(filtered, chart_type)
    else:
        ratio_fn = (
            ratios_module.savings_rate if measure == "Savings rate" else ratios_module.spend_as_pct_of_income
        )
        render_scalar_ratio(filtered, group_by, ratio_fn, chart_type)


def render_sum_measure(filtered: list[Record], group_by: list[str], chart_type: str) -> None:
    if not group_by:
        st.warning("Pick at least one group-by dimension.")
        return

    df = aggregate(filtered, group_by)

    if chart_type == "table" or len(group_by) == 2:
        table = pivot(df, group_by[0], group_by[1] if len(group_by) == 2 else None)
        st.dataframe(table, use_container_width=True)
        if chart_type == "table":
            return

    color = group_by[1] if len(group_by) == 2 else None
    if chart_type == "bar":
        fig = px.bar(df, x=group_by[0], y="amount", color=color)
    elif chart_type == "stacked bar":
        fig = px.bar(df, x=group_by[0], y="amount", color=color, barmode="relative")
    elif chart_type == "line":
        fig = px.line(df, x=group_by[0], y="amount", color=color)
    elif chart_type == "pie":
        fig = px.pie(df, names=group_by[0], values="amount")
    else:
        return
    st.plotly_chart(fig, use_container_width=True)


def render_group_share(filtered: list[Record], chart_type: str) -> None:
    shares = ratios_module.group_share_of_spend(filtered)
    for currency, by_group in shares.items():
        st.caption(currency)
        if not by_group:
            st.caption("No expense rows.")
            continue
        rows = [{"group": g, "share": float(v)} for g, v in sorted(by_group.items(), key=lambda kv: -kv[1])]
        if chart_type == "pie":
            st.plotly_chart(px.pie(rows, names="group", values="share"), use_container_width=True)
        elif chart_type == "bar":
            st.plotly_chart(px.bar(rows, x="group", y="share"), use_container_width=True)
        else:
            st.dataframe(rows, use_container_width=True)


def render_scalar_ratio(filtered: list[Record], group_by: list[str], ratio_fn, chart_type: str) -> None:
    usable_dims = [d for d in group_by if d in ("year", "month", "currency")]
    if not usable_dims:
        result = ratio_fn(filtered)
        st.write({currency: (float(v) if v is not None else None) for currency, v in result.items()})
        return

    buckets: dict[tuple, list[Record]] = {}
    for r in filtered:
        key = tuple(getattr(r, d) for d in usable_dims)
        buckets.setdefault(key, []).append(r)

    rows = []
    for key, recs in buckets.items():
        for currency, value in ratio_fn(recs).items():
            row = dict(zip(usable_dims, key, strict=True))
            row["currency"] = currency
            row["value"] = float(value) if value is not None else None
            rows.append(row)

    if chart_type == "line":
        st.plotly_chart(
            px.line(rows, x=usable_dims[0], y="value", color="currency"), use_container_width=True
        )
    elif chart_type == "bar":
        st.plotly_chart(px.bar(rows, x=usable_dims[0], y="value", color="currency"), use_container_width=True)
    else:
        st.dataframe(rows, use_container_width=True)
