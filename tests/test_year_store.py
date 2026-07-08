from datetime import date
from decimal import Decimal

from src.domain.models import Transaction, Type
from src.storage import year_store


def _tx(
    d: str, amount: str, type_: Type = "expense", category: str = "", currency: str = "EUR"
) -> Transaction:
    return Transaction(
        date=date.fromisoformat(d), amount=Decimal(amount), currency=currency, type=type_, category=category
    )


# --- transactions.csv: rewritten sorted by date on every save (specs/02-storage.md) ---


def test_save_transactions_rewrites_sorted_by_date(tmp_path):
    rows = [_tx("2026-03-01", "-10"), _tx("2026-01-15", "-20"), _tx("2026-02-01", "-30")]

    year_store.save_transactions(tmp_path, 2026, rows)
    loaded = year_store.load_transactions(tmp_path, 2026)

    assert [t.date.isoformat() for t in loaded] == ["2026-01-15", "2026-02-01", "2026-03-01"]


def test_load_transactions_missing_file_returns_empty_list(tmp_path):
    assert year_store.load_transactions(tmp_path, 2026) == []


# --- commit: a multi-year batch is split into the correct year folders (specs/02-storage.md) ---


def test_commit_transactions_splits_batch_by_date_year(tmp_path):
    rows = [_tx("2025-12-31", "-5"), _tx("2026-01-01", "-6")]

    year_store.commit_transactions(tmp_path, rows)

    assert len(year_store.load_transactions(tmp_path, 2025)) == 1
    assert len(year_store.load_transactions(tmp_path, 2026)) == 1


def test_commit_transactions_appends_to_existing_rows(tmp_path):
    year_store.save_transactions(tmp_path, 2026, [_tx("2026-01-01", "-1")])
    year_store.commit_transactions(tmp_path, [_tx("2026-06-01", "-2")])

    assert len(year_store.load_transactions(tmp_path, 2026)) == 2


# --- year lifecycle: open -> closed -> reopen (specs/02-storage.md) ---


def test_year_state_open_closed_missing(tmp_path):
    assert year_store.year_state(tmp_path, 2026) == "missing"

    year_store.save_transactions(tmp_path, 2026, [_tx("2026-01-01", "-1")])
    assert year_store.year_state(tmp_path, 2026) == "open"

    year_store.close_year(tmp_path, 2026)
    assert year_store.year_state(tmp_path, 2026) == "summarized"

    year_store.reopen_year(tmp_path, 2026)
    assert year_store.year_state(tmp_path, 2026) == "open"


def test_close_year_compiles_unsigned_annual_sums(tmp_path):
    year_store.save_transactions(
        tmp_path,
        2026,
        [
            _tx("2026-01-01", "-100", type_="expense", category="groceries"),
            _tx("2026-02-01", "-50", type_="expense", category="groceries"),
            _tx("2026-03-01", "2000", type_="income", category="salary"),
        ],
    )

    year_store.close_year(tmp_path, 2026)
    summary = {(s.type, s.category): s.amount for s in year_store.load_summary(tmp_path, 2026)}

    # unsigned magnitudes, per the specs/05-historical-data.md summary.csv example
    assert summary[("expense", "groceries")] == Decimal("150")
    assert summary[("income", "salary")] == Decimal("2000")


def test_load_summary_skips_non_numeric_amount_rows(tmp_path):
    config_dir = tmp_path / "data" / "2019"
    config_dir.mkdir(parents=True)
    (config_dir / "summary.csv").write_text(
        "type,category,currency,amount\nexpense,housing,EUR,26000\nexpense,broken,EUR,not-a-number\n"
    )

    rows = year_store.load_summary(tmp_path, 2019)

    assert len(rows) == 1
    assert rows[0].category == "housing"
