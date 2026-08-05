"""Load/save the small hand-editable JSON config files. See specs/02-storage.md §2."""

from __future__ import annotations

import dataclasses
import json
from dataclasses import asdict
from pathlib import Path

from src.analysis.groups import group_map_from_json, group_map_to_json
from src.domain.models import BankProfile, CategoryRule
from src.storage.io_utils import safe_write_text

BANK_PROFILES_FILE = "bank-profiles.json"
RULES_FILE = "rules.json"
CATEGORY_GROUPS_FILE = "category-groups.json"
SAVED_VIEWS_FILE = "saved-views.json"
SETTINGS_FILE = "settings.json"


def _config_dir(data_home: Path) -> Path:
    return Path(data_home) / "config"


def _read_json(data_home: Path, filename: str, default):
    path = _config_dir(data_home) / filename
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(data_home: Path, filename: str, value) -> None:
    path = _config_dir(data_home) / filename
    safe_write_text(path, json.dumps(value, indent=2) + "\n")


def _without_comment_keys(entry: dict) -> dict:
    """Drop underscore-prefixed keys (e.g. "_comment") — a hand-editing convention, not a field."""
    return {k: v for k, v in entry.items() if not k.startswith("_")}


def _validated_fields(dataclass_type: type, entry: dict, label: str) -> dict:
    """Drop comment keys, then fail clearly on unknown or missing-required fields."""
    cleaned = _without_comment_keys(entry)
    fields = dataclasses.fields(dataclass_type)
    known = {f.name for f in fields}
    required = {
        f.name
        for f in fields
        if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING
    }

    unknown = sorted(set(cleaned) - known)
    missing = sorted(required - set(cleaned))
    if unknown or missing:
        problems = []
        if unknown:
            problems.append(f"unknown field(s): {', '.join(unknown)}")
        if missing:
            problems.append(f"missing required field(s): {', '.join(missing)}")
        raise ValueError(f"Invalid {label}: {'; '.join(problems)}")
    return cleaned


# --- bank profiles ---------------------------------------------------------


def validated_bank_profile_fields(entry: dict) -> dict:
    return _validated_fields(BankProfile, entry, f"bank profile {entry.get('name', '<unnamed>')!r}")


def load_bank_profiles(data_home: Path) -> dict[str, BankProfile]:
    raw = _read_json(data_home, BANK_PROFILES_FILE, [])
    return {p["name"]: BankProfile(**validated_bank_profile_fields(p)) for p in raw}


def save_bank_profiles(data_home: Path, profiles: dict[str, BankProfile]) -> None:
    _write_json(data_home, BANK_PROFILES_FILE, [asdict(p) for p in profiles.values()])


# --- rules ------------------------------------------------------------------


def load_rules(data_home: Path) -> list[CategoryRule]:
    raw = _read_json(data_home, RULES_FILE, [])
    return [
        CategoryRule(**_validated_fields(CategoryRule, r, f"rule {r.get('pattern', '<unnamed>')!r}"))
        for r in raw
    ]


def save_rules(data_home: Path, rules: list[CategoryRule]) -> None:
    _write_json(data_home, RULES_FILE, [asdict(r) for r in rules])


# --- category -> group map ---------------------------------------------------
# The shared map is the current working draft for OPEN years only (01-domain-model.md §2.2);
# closed years fold via their own data/<year>/groups.json snapshot instead (src/storage/year_store.py).
# Stored group-first on disk (group -> [category, ...]) for easy hand-editing; kept as a flat
# category -> group dict in memory, since every consumer looks up by category.


def load_category_groups(data_home: Path) -> dict[str, str]:
    raw = _read_json(data_home, CATEGORY_GROUPS_FILE, {})
    return group_map_from_json(raw)


def save_category_groups(data_home: Path, mapping: dict[str, str]) -> None:
    _write_json(data_home, CATEGORY_GROUPS_FILE, group_map_to_json(mapping))


# --- saved views --------------------------------------------------------------


def load_saved_views(data_home: Path) -> list[dict]:
    return _read_json(data_home, SAVED_VIEWS_FILE, [])


def save_saved_views(data_home: Path, views: list[dict]) -> None:
    _write_json(data_home, SAVED_VIEWS_FILE, views)


# --- settings -----------------------------------------------------------------


def load_settings(data_home: Path) -> dict:
    return _read_json(data_home, SETTINGS_FILE, {})


def save_settings(data_home: Path, settings: dict) -> None:
    _write_json(data_home, SETTINGS_FILE, settings)
