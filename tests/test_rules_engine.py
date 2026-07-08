from datetime import date
from decimal import Decimal

from src.categorize.rules_engine import (
    StagedRow,
    categorize_row,
    categorize_rows,
    count_matches,
    find_match,
    normalize,
)
from src.domain.models import CategoryRule, Transaction

# --- normalize: lowercase, collapse whitespace, trim (specs/04-categorization.md) ---


def test_normalize_lowercases_collapses_whitespace_and_trims():
    assert normalize("  CARD   Payment\tSample  ") == "card payment sample"


# --- find_match: substring, longest pattern wins, ties break by rules.json order ---


def test_find_match_requires_substring():
    rules = [CategoryRule(pattern="k-market", type="expense", category="groceries")]
    assert find_match("payment at k-market helsinki", rules) is not None
    assert find_match("payment at other-shop", rules) is None


def test_find_match_longest_pattern_wins():
    rules = [
        CategoryRule(pattern="market", type="expense", category="shopping"),
        CategoryRule(pattern="k-market", type="expense", category="groceries"),
    ]
    match = find_match("K-MARKET HELSINKI", rules)
    assert match.category == "groceries"


def test_find_match_ties_break_by_rules_order():
    rules = [
        CategoryRule(pattern="abc", type="expense", category="first"),
        CategoryRule(pattern="xyz", type="expense", category="second"),
    ]
    # both patterns are length 3 (a tie); "abc" is declared first, so it wins
    match = find_match("abcxyz", rules)
    assert match.category == "first"


def test_find_match_no_rule_matches_returns_none():
    assert find_match("unrelated text", [CategoryRule(pattern="market", type="expense")]) is None


# --- categorize_row / categorize_rows ---


def _transaction(description: str) -> Transaction:
    return Transaction(
        date=date(2026, 1, 1),
        amount=Decimal("-10"),
        currency="EUR",
        type="expense",
        rawDescription=description,
    )


def test_categorize_row_sets_type_and_category_on_match():
    row = StagedRow(transaction=_transaction("SALARY SAMPLE EMPLOYER"))
    rule = CategoryRule(pattern="salary", type="income", category="salary")

    categorize_row(row, [rule])

    assert row.transaction.type == "income"
    assert row.transaction.category == "salary"
    assert row.skip is False


def test_categorize_row_skip_rule_marks_row_skipped_without_touching_category():
    row = StagedRow(transaction=_transaction("INTERNAL TRANSFER"))
    rule = CategoryRule(pattern="internal transfer", type="skip")

    categorize_row(row, [rule])

    assert row.skip is True
    assert row.transaction.category == ""


def test_categorize_row_no_match_leaves_row_uncategorized():
    row = StagedRow(transaction=_transaction("SOMETHING UNKNOWN"))

    categorize_row(row, [CategoryRule(pattern="salary", type="income", category="salary")])

    assert row.transaction.category == ""
    assert row.skip is False


def test_categorize_rows_applies_to_every_row():
    rows = [StagedRow(transaction=_transaction("SALARY")), StagedRow(transaction=_transaction("OTHER"))]
    categorize_rows(rows, [CategoryRule(pattern="salary", type="income", category="salary")])

    assert rows[0].transaction.category == "salary"
    assert rows[1].transaction.category == ""


# --- count_matches: the make-a-rule preview count ---


def test_count_matches_counts_normalized_substring_hits():
    descriptions = ["K-Market Helsinki", "K-Market Turku", "Other Shop"]
    assert count_matches("k-market", descriptions) == 2


def test_count_matches_empty_pattern_matches_nothing():
    assert count_matches("   ", ["anything"]) == 0
