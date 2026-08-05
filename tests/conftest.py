import os
from pathlib import Path

import pytest

# Must be set before pyarrow initializes its default memory pool (first import), so it has to
# happen at conftest module load time, not inside a fixture. Without this, a second Streamlit
# AppTest .run() of any page that renders a table (st.dataframe/st.data_editor) segfaults —
# a thread/memory-pool interaction specific to pyarrow's default allocator on this platform.
os.environ.setdefault("ARROW_DEFAULT_MEMORY_POOL", "system")

CSV_SAMPLES_DIR = Path(__file__).resolve().parents[1] / "specs" / "csv-samples"


@pytest.fixture
def csv_samples_dir() -> Path:
    return CSV_SAMPLES_DIR
