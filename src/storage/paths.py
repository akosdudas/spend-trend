"""Data-home resolution. See specs/08-tech-stack.md §6-7."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "spend-trends"

# The repo working tree this package lives in; a data home must never resolve inside it.
REPO_ROOT = Path(__file__).resolve().parents[2]


def app_support_dir() -> Path:
    """OS per-user app directory holding the pointer file."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path.home() / f".{APP_NAME}"


def pointer_file() -> Path:
    return app_support_dir() / "location"


def _is_inside_repo(path: Path) -> bool:
    try:
        path.resolve().relative_to(REPO_ROOT)
        return True
    except ValueError:
        return False


def resolve_data_home(cli_arg: str | None = None) -> Path:
    """Resolve the data home: --data-dir > SPENDTRENDS_HOME > pointer file.

    Exits with a short message if none is configured, or if the resolved path
    is inside the repo working tree.
    """
    candidate: str | None = cli_arg or os.environ.get("SPENDTRENDS_HOME")

    if candidate is None:
        pf = pointer_file()
        if pf.exists():
            candidate = pf.read_text(encoding="utf-8").strip()

    if not candidate:
        sys.exit(
            "No data home is configured.\n"
            f"Set one by writing its path to {pointer_file()},\n"
            "passing --data-dir <path>, or setting SPENDTRENDS_HOME.\n"
            "Run setup_data_home.py to create one and scaffold it."
        )

    data_home = Path(candidate).expanduser().resolve()

    if _is_inside_repo(data_home):
        sys.exit(
            f"Refusing a data home inside the repo working tree: {data_home}\n"
            "Choose a location outside the repo (specs/08-tech-stack.md)."
        )

    return data_home


def write_pointer(data_home: Path) -> None:
    pf = pointer_file()
    pf.parent.mkdir(parents=True, exist_ok=True)
    pf.write_text(str(Path(data_home).expanduser().resolve()), encoding="utf-8")
