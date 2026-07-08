"""Unitless, cross-currency-comparable ratios. See specs/06-analysis.md §5.1.

Each is computed per currency segment (same-currency numerator and denominator), so a mid-year
currency move reads as two segments rather than a mixed total.
"""

from __future__ import annotations

from decimal import Decimal

from src.analysis.aggregate import Record


def _income_and_spend(records: list[Record]) -> tuple[Decimal, Decimal]:
    income = sum((r.amount for r in records if r.type == "income"), Decimal("0"))
    spend = -sum((r.amount for r in records if r.type == "expense"), Decimal("0"))  # positive magnitude
    return income, spend


def _by_currency(records: list[Record]) -> dict[str, list[Record]]:
    by_currency: dict[str, list[Record]] = {}
    for r in records:
        by_currency.setdefault(r.currency, []).append(r)
    return by_currency


def savings_rate(records: list[Record]) -> dict[str, Decimal | None]:
    """(income - spend) / income, per currency."""
    result: dict[str, Decimal | None] = {}
    for currency, rows in _by_currency(records).items():
        income, spend = _income_and_spend(rows)
        result[currency] = (income - spend) / income if income else None
    return result


def spend_as_pct_of_income(records: list[Record]) -> dict[str, Decimal | None]:
    """spend / income, per currency."""
    result: dict[str, Decimal | None] = {}
    for currency, rows in _by_currency(records).items():
        income, spend = _income_and_spend(rows)
        result[currency] = spend / income if income else None
    return result


def group_share_of_spend(records: list[Record]) -> dict[str, dict[str, Decimal]]:
    """group spend / total spend, per currency; expense records only."""
    result: dict[str, dict[str, Decimal]] = {}
    for currency, rows in _by_currency(records).items():
        expense_rows = [r for r in rows if r.type == "expense"]
        total = -sum((r.amount for r in expense_rows), Decimal("0"))
        shares: dict[str, Decimal] = {}
        if total:
            per_group: dict[str, Decimal] = {}
            for r in expense_rows:
                group = r.group or "Rest"
                per_group[group] = per_group.get(group, Decimal("0")) - r.amount
            shares = {group: amount / total for group, amount in per_group.items()}
        result[currency] = shares
    return result
