#!/usr/bin/env python3
"""Create a data home and point the app at it. See specs/08-tech-stack.md §7."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.storage.paths import _is_inside_repo, write_pointer  # noqa: E402

EMPTY_FILTERS: dict[str, list | str] = {
    "years": [],
    "types": [],
    "categories": [],
    "groups": [],
    "currencies": [],
    "text": "",
}

# Starter dashboard views (specs/06-analysis.md §2), editable like any other saved view.
STARTER_VIEWS = [
    {
        "name": "Spend by category",
        "groupBy": ["category"],
        "measure": "Sum of amount",
        "chartType": "table",
        "width": "full",
        "filters": {**EMPTY_FILTERS, "types": ["expense"]},
    },
    {
        "name": "Group share of spend",
        "groupBy": [],
        "measure": "Group share of spend",
        "chartType": "pie",
        "width": "half",
        "filters": dict(EMPTY_FILTERS),
    },
    {
        "name": "Year-over-year by group",
        "groupBy": ["group", "year"],
        "measure": "Sum of amount",
        "chartType": "bar",
        "width": "half",
        "filters": {**EMPTY_FILTERS, "types": ["expense"]},
    },
    {
        "name": "Spend vs income by year",
        "groupBy": ["year", "type"],
        "measure": "Sum of amount",
        "chartType": "line",
        "width": "full",
        "filters": dict(EMPTY_FILTERS),
    },
    {
        "name": "Savings rate by year",
        "groupBy": ["year"],
        "measure": "Savings rate",
        "chartType": "line",
        "width": "half",
        "filters": dict(EMPTY_FILTERS),
    },
    {
        "name": "Monthly spend by group",
        "groupBy": ["month", "group"],
        "measure": "Sum of amount",
        "chartType": "stacked bar",
        "width": "full",
        "filters": {**EMPTY_FILTERS, "types": ["expense"]},
    },
    {
        "name": "Top merchants",
        "groupBy": ["merchant"],
        "measure": "Sum of amount",
        "chartType": "table",
        "width": "half",
        "filters": {**EMPTY_FILTERS, "types": ["expense"]},
    },
]

DEFAULT_CONFIG_FILES: dict[str, list | dict] = {
    "bank-profiles.json": [],
    "category-groups.json": [],
    "rules.json": [],
    "saved-views.json": STARTER_VIEWS,
    "settings.json": {},
}


def scaffold(data_home: Path) -> None:
    if _is_inside_repo(data_home):
        sys.exit(f"Refusing a data home inside the repo working tree: {data_home}")

    config_dir = data_home / "config"
    data_dir = data_home / "data"
    config_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    for name, default in DEFAULT_CONFIG_FILES.items():
        path = config_dir / name
        if not path.exists():
            path.write_text(json.dumps(default, indent=2) + "\n", encoding="utf-8")

    write_pointer(data_home)
    print(f"Data home ready at {data_home}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data_home", type=Path, help="Path to create/use as the data home")
    args = parser.parse_args()
    scaffold(args.data_home.expanduser().resolve())
