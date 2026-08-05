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


def group_map_to_json(mapping: dict[str, str]) -> dict[str, list[str]]:
    """Flat category -> group dict to the group-first on-disk shape (01-domain-model.md §2.2)."""
    grouped: dict[str, list[str]] = {}
    for category, group in mapping.items():
        grouped.setdefault(group, []).append(category)
    return {group: sorted(categories) for group, categories in sorted(grouped.items())}


def group_map_from_json(raw: dict[str, list[str]]) -> dict[str, str]:
    """The group-first on-disk shape back to a flat category -> group dict."""
    return {category: group for group, categories in raw.items() for category in categories}
