"""Substring rule engine: normalize, longest-pattern-wins. See specs/04-categorization.md."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.domain.models import CategoryRule, Transaction


@dataclass
class StagedRow:
    """A transaction staged in memory during import, plus its pending skip mark."""

    transaction: Transaction
    skip: bool = False


def normalize(text: str) -> str:
    """Lowercase, collapse internal whitespace, trim ends."""
    return re.sub(r"\s+", " ", text.strip().lower())


def find_match(description: str, rules: list[CategoryRule]) -> CategoryRule | None:
    normalized_description = normalize(description)
    matches = [r for r in rules if normalize(r.pattern) and normalize(r.pattern) in normalized_description]
    if not matches:
        return None
    best_length = max(len(normalize(r.pattern)) for r in matches)
    for r in matches:  # original rules.json order — first at best_length wins ties
        if len(normalize(r.pattern)) == best_length:
            return r
    return None  # unreachable


def categorize_row(row: StagedRow, rules: list[CategoryRule]) -> None:
    match = find_match(row.transaction.rawDescription, rules)
    if match is None:
        return
    if match.type == "skip":
        row.skip = True
        return
    row.transaction.type = match.type
    row.transaction.category = match.category or ""


def categorize_rows(rows: list[StagedRow], rules: list[CategoryRule]) -> None:
    for row in rows:
        categorize_row(row, rules)


def count_matches(pattern: str, descriptions: list[str]) -> int:
    """How many descriptions the (trimmed) pattern would match — for the make-a-rule preview."""
    normalized_pattern = normalize(pattern)
    if not normalized_pattern:
        return 0
    return sum(1 for d in descriptions if normalized_pattern in normalize(d))
