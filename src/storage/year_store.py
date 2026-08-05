"""Per-year transactions.csv / summary.csv load+save and year lifecycle. See specs/02-storage.md."""

from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from datetime import date as Date
from decimal import Decimal
from pathlib import Path
from typing import cast

from src.analysis.groups import group_map_from_json, group_map_to_json
from src.domain.models import HistoricalSummary, Transaction, Type
from src.storage import config_store
from src.storage.io_utils import safe_write_text

TRANSACTIONS_FILE = "transactions.csv"
SUMMARY_FILE = "summary.csv"
GROUPS_SNAPSHOT_FILE = "groups.json"

TRANSACTION_FIELDS = ["date", "amount", "currency", "type", "rawDescription", "category", "notes"]
SUMMARY_FIELDS = ["type", "category", "currency", "amount"]


def year_dir(data_home: Path, year: int) -> Path:
    return Path(data_home) / "data" / str(year)


def list_years(data_home: Path) -> list[int]:
    data_dir = Path(data_home) / "data"
    if not data_dir.exists():
        return []
    years = []
    for child in data_dir.iterdir():
        if child.is_dir() and child.name.isdigit():
            years.append(int(child.name))
    return sorted(years)


def year_state(data_home: Path, year: int) -> str:
    """'open' (transactions, live), 'summarized' (closed or legacy), or 'missing'."""
    d = year_dir(data_home, year)
    if (d / SUMMARY_FILE).exists():
        return "summarized"
    if (d / TRANSACTIONS_FILE).exists():
        return "open"
    return "missing"


# --- transactions -------------------------------------------------------------


def load_transactions(data_home: Path, year: int) -> list[Transaction]:
    path = year_dir(data_home, year) / TRANSACTIONS_FILE
    if not path.exists():
        return []
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(
                Transaction(
                    date=Date.fromisoformat(row["date"]),
                    amount=Decimal(row["amount"]),
                    currency=row["currency"],
                    type=cast(Type, row["type"]),
                    rawDescription=row.get("rawDescription", ""),
                    category=row.get("category", ""),
                    notes=row.get("notes", ""),
                )
            )
    return rows


def save_transactions(data_home: Path, year: int, transactions: list[Transaction]) -> None:
    """Rewrite the year's transactions.csv, sorted by date."""
    ordered = sorted(transactions, key=lambda t: t.date)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=TRANSACTION_FIELDS)
    writer.writeheader()
    for t in ordered:
        writer.writerow(
            {
                "date": t.date.isoformat(),
                "amount": str(t.amount),
                "currency": t.currency,
                "type": t.type,
                "rawDescription": t.rawDescription,
                "category": t.category,
                "notes": t.notes,
            }
        )
    path = year_dir(data_home, year) / TRANSACTIONS_FILE
    safe_write_text(path, buf.getvalue())


def append_transactions(data_home: Path, year: int, new_rows: list[Transaction]) -> None:
    existing = load_transactions(data_home, year)
    save_transactions(data_home, year, existing + new_rows)


def commit_transactions(data_home: Path, rows: list[Transaction]) -> None:
    """Append rows to their year files, grouping a multi-year batch by date's year."""
    by_year: dict[int, list[Transaction]] = defaultdict(list)
    for row in rows:
        by_year[row.date.year].append(row)
    for year, year_rows in by_year.items():
        append_transactions(data_home, year, year_rows)


# --- summary (legacy / closed years) -------------------------------------------


def load_summary(data_home: Path, year: int) -> list[HistoricalSummary]:
    path = year_dir(data_home, year) / SUMMARY_FILE
    if not path.exists():
        return []
    rows = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                amount = Decimal(row["amount"])
            except Exception:
                continue  # non-numeric cells are reported and skipped (05-historical-data.md)
            rows.append(
                HistoricalSummary(
                    year=year,
                    type=cast(Type, row["type"]),
                    category=row["category"],
                    currency=row["currency"],
                    amount=amount,
                )
            )
    return rows


def load_summary_malformed_rows(data_home: Path, year: int) -> list[str]:
    """Line-level warnings for rows load_summary() silently skipped (non-numeric amount)."""
    path = year_dir(data_home, year) / SUMMARY_FILE
    if not path.exists():
        return []
    warnings = []
    with path.open(newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=1):
            try:
                Decimal(row["amount"])
            except Exception:
                warnings.append(
                    f"line {i}: non-numeric amount {row.get('amount')!r} for category {row.get('category')!r}"
                )
    return warnings


def save_summary(data_home: Path, year: int, rows: list[HistoricalSummary]) -> None:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=SUMMARY_FIELDS)
    writer.writeheader()
    for r in rows:
        writer.writerow(
            {"type": r.type, "category": r.category, "currency": r.currency, "amount": str(r.amount)}
        )
    path = year_dir(data_home, year) / SUMMARY_FILE
    safe_write_text(path, buf.getvalue())


# --- groups.json: a closed year's own category -> group snapshot (01-domain-model.md §2.2) -----


def load_year_groups_snapshot(data_home: Path, year: int) -> dict[str, str] | None:
    """The year's own snapshot, or None if it has none (open year, or a legacy year)."""
    path = year_dir(data_home, year) / GROUPS_SNAPSHOT_FILE
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return group_map_from_json(json.load(f))


def snapshot_year_groups_if_absent(data_home: Path, year: int, shared_map: dict[str, str]) -> None:
    """Freeze the shared map into this year's groups.json — a no-op if a snapshot already exists."""
    path = year_dir(data_home, year) / GROUPS_SNAPSHOT_FILE
    if path.exists():
        return
    safe_write_text(path, json.dumps(group_map_to_json(shared_map), indent=2) + "\n")


# --- lifecycle: open -> closed -> reopen ---------------------------------------


def close_year(data_home: Path, year: int) -> None:
    """Compile summary.csv (annual sums by type+category+currency) from transactions.csv, and
    snapshot the shared category-groups map into groups.json if this year has none yet."""
    # HistoricalSummary.amount is an unsigned annual magnitude (05-historical-data.md example),
    # unlike Transaction.amount which is signed (spend negative, income positive).
    transactions = load_transactions(data_home, year)
    sums: dict[tuple[Type, str, str], Decimal] = defaultdict(Decimal)
    for t in transactions:
        sums[(t.type, t.category, t.currency)] += abs(t.amount)
    rows = [
        HistoricalSummary(year=year, type=type_, category=category, currency=currency, amount=amount)
        for (type_, category, currency), amount in sums.items()
    ]
    save_summary(data_home, year, rows)
    snapshot_year_groups_if_absent(data_home, year, config_store.load_category_groups(data_home))


def reopen_year(data_home: Path, year: int) -> None:
    """Delete summary.csv so the year reads live again; groups.json is left in place (02-storage.md)."""
    path = year_dir(data_home, year) / SUMMARY_FILE
    if path.exists():
        path.unlink()
