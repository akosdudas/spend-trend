from pathlib import Path

import pytest

CSV_SAMPLES_DIR = Path(__file__).resolve().parents[1] / "specs" / "csv-samples"


@pytest.fixture
def csv_samples_dir() -> Path:
    return CSV_SAMPLES_DIR
