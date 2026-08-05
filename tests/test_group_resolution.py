"""Per-year group fold resolution: closed -> own snapshot, open/legacy -> shared map, unmapped -> Rest.

See specs/01-domain-model.md §2.2, specs/02-storage.md §4, specs/06-analysis.md §1.
"""

from datetime import date
from decimal import Decimal

from src.analysis.aggregate import build_records
from src.domain.models import HistoricalSummary, Transaction
from src.storage import config_store, year_store


def _tx(d: str, category: str) -> Transaction:
    return Transaction(
        date=date.fromisoformat(d), amount=Decimal("-10"), currency="EUR", type="expense", category=category
    )


def test_fold_resolution_per_year_state(tmp_path):
    # A closed year freezes the shared map as it was at close time.
    config_store.save_category_groups(tmp_path, {"groceries": "Food"})
    year_store.save_transactions(tmp_path, 2024, [_tx("2024-01-01", "groceries")])
    year_store.close_year(tmp_path, 2024)

    # The shared map changes afterward — must not reshape the already-closed year.
    config_store.save_category_groups(tmp_path, {"groceries": "Shopping"})

    # A legacy year (summary.csv only, no snapshot) follows the *current* shared map.
    year_store.save_summary(
        tmp_path,
        2025,
        [
            HistoricalSummary(
                year=2025, type="expense", category="groceries", currency="EUR", amount=Decimal("50")
            )
        ],
    )

    # An open year also follows the current shared map, and an unmapped category folds to Rest.
    year_store.save_transactions(
        tmp_path, 2026, [_tx("2026-01-01", "groceries"), _tx("2026-01-02", "mystery")]
    )

    records = build_records(tmp_path)
    by_year: dict[int, list] = {}
    for r in records:
        by_year.setdefault(r.year, []).append(r)

    closed_groceries = next(r for r in by_year[2024] if r.category == "groceries")
    assert closed_groceries.group == "Food"  # frozen at close, independent of the later shared-map edit

    legacy_groceries = next(r for r in by_year[2025] if r.category == "groceries")
    assert legacy_groceries.group == "Shopping"  # no snapshot -> current shared map

    open_groceries = next(r for r in by_year[2026] if r.category == "groceries")
    assert open_groceries.group == "Shopping"  # open year -> current shared map

    open_mystery = next(r for r in by_year[2026] if r.category == "mystery")
    assert open_mystery.group == "Rest"  # unmapped -> default group
