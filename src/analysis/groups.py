"""Category -> group fold-up, expense only. See specs/01-domain-model.md §2.2."""

from __future__ import annotations

DEFAULT_GROUP = "Rest"


def fold_to_group(category: str, type_: str, mapping: dict[str, str]) -> str | None:
    """Income is not grouped (01-domain-model.md); an unmapped expense category folds to Rest."""
    if type_ != "expense":
        return None
    return mapping.get(category, DEFAULT_GROUP)


def unmapped_categories(categories: set[str], mapping: dict[str, str]) -> set[str]:
    """Expense categories with no entry in the map, to surface for mapping."""
    return categories - set(mapping.keys())
