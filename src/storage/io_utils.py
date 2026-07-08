"""Safe-save helper: write a temp file then atomically replace the target. See specs/02-storage.md §5."""

from __future__ import annotations

import os
from pathlib import Path


def safe_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
