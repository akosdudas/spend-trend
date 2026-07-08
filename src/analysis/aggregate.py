"""Aggregation over in-memory rows: the group-by/measure/filter engine behind the builder.

See specs/06-analysis.md. Plain Python over transactions + historical summaries; pandas is used
only to reshape the already-computed sums into a table/chart, per specs/02-storage.md §1.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pandas as pd

from src.analysis.groups import fold_to_group
from src.categorize.rules_engine import normalize
from src.domain.models import Type
from src.storage import config_store, year_store

GROUP_BY_DIMENSIONS = ["type", "category", "group", "merchant", "month", "year", "currency"]


@dataclass(frozen=True)
class Record:
    """An analysis-time projection of one transaction or one historical-summary row.

    Not a domain entity (specs/01-domain-model.md) — purely a computed view for aggregation.
    `amount` is signed (spend negative, income positive), matching Transaction's convention.
    `month`/`merchant` are None for summarized years, which only have annual, category-level sums.
    """

    type: Type
    category: str
    group: str | None
    merchant: str | None
    month: int | None
    year: int
    currency: str
    amount: Decimal


def build_records(data_home: Path) -> list[Record]:
    """One Record per transaction (open years) or per historical-summary row (closed/legacy years)."""
    category_groups = config_store.load_category_groups(data_home)
    records: list[Record] = []

    for year in year_store.list_years(data_home):
        state = year_store.year_state(data_home, year)
        if state == "open":
            for t in year_store.load_transactions(data_home, year):
                records.append(
                    Record(
                        type=t.type,
                        category=t.category,
                        group=fold_to_group(t.category, t.type, category_groups),
                        merchant=normalize(t.rawDescription) if t.rawDescription else None,
                        month=t.date.month,
                        year=year,
                        currency=t.currency,
                        amount=t.amount,
                    )
                )
        elif state == "summarized":
            for s in year_store.load_summary(data_home, year):
                signed_amount = s.amount if s.type == "income" else -s.amount
                records.append(
                    Record(
                        type=s.type,
                        category=s.category,
                        group=fold_to_group(s.category, s.type, category_groups),
                        merchant=None,
                        month=None,
                        year=year,
                        currency=s.currency,
                        amount=signed_amount,
                    )
                )

    return records


def filter_records(
    records: list[Record],
    *,
    years: list[int] | None = None,
    types: list[str] | None = None,
    categories: list[str] | None = None,
    groups: list[str] | None = None,
    merchants: list[str] | None = None,
    currencies: list[str] | None = None,
    min_amount: Decimal | None = None,
    max_amount: Decimal | None = None,
    text: str | None = None,
) -> list[Record]:
    result = records
    if years:
        result = [r for r in result if r.year in years]
    if types:
        result = [r for r in result if r.type in types]
    if categories:
        result = [r for r in result if r.category in categories]
    if groups:
        result = [r for r in result if r.group in groups]
    if merchants:
        result = [r for r in result if r.merchant in merchants]
    if currencies:
        result = [r for r in result if r.currency in currencies]
    if min_amount is not None:
        result = [r for r in result if r.amount >= min_amount]
    if max_amount is not None:
        result = [r for r in result if r.amount <= max_amount]
    if text:
        needle = text.strip().lower()
        result = [r for r in result if needle in r.category.lower() or (r.merchant and needle in r.merchant)]
    return result


def needs_attention_count(records: list[Record]) -> int:
    """Uncategorized rows, across the whole timeline (specs/07-ux.md §2.1)."""
    return sum(1 for r in records if not r.category)


def aggregate(records: list[Record], group_by: list[str]) -> pd.DataFrame:
    """Sum of amount per group-by combination, as a long-format DataFrame (one row per bucket)."""
    sums: dict[tuple, Decimal] = {}
    for r in records:
        key = tuple(getattr(r, dim) for dim in group_by)
        sums[key] = sums.get(key, Decimal("0")) + r.amount

    rows = [dict(zip(group_by, key, strict=True), amount=float(total)) for key, total in sums.items()]
    columns = [*group_by, "amount"]
    return pd.DataFrame(rows, columns=columns)


def pivot(df: pd.DataFrame, rows: str, columns: str | None, value: str = "amount") -> pd.DataFrame:
    """Reshape a long aggregate() result into a table with row/column totals (specs/06-analysis.md)."""
    if columns:
        table = df.pivot_table(
            index=rows,
            columns=columns,
            values=value,
            aggfunc="sum",
            fill_value=0,
            margins=True,
            margins_name="Total",
        )
        table.index = table.index.astype(str)
        table.columns = table.columns.astype(str)
    else:
        table = df.groupby(rows)[value].sum().to_frame()
        table.index = table.index.astype(str)
        table.loc["Total"] = table.sum()
    return table
