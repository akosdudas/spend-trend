"""Render-smoke coverage: every page (and every st.dialog) mounts without raising.

Unlike the other test modules, this one does exercise the Streamlit UI layer — deliberately, to
catch startup/wiring/rendering crashes that no pure unit test on src/storage, src/importer, or
src/categorize can see, since those modules never touch Streamlit. It asserts *mounting*, not
interaction outcomes: every screen and every dialog must open without an exception, but we don't
click through every control on every screen (that combinatorial surface belongs to unit tests on
the underlying functions, not to this smoke layer). See specs/08-tech-stack.md §3.

Note: AppTest has no supported way to switch pages within a single instance for a
st.navigation()-based app (each multipage screen must be tested via its own AppTest.from_file() of
that page's script) — see the AppTest docstring. `tests/conftest.py` sets
ARROW_DEFAULT_MEMORY_POOL=system, which is required for a second `.run()` of any page rendering a
table to not segfault (a pyarrow/thread interaction on this platform, unrelated to app code).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from streamlit.testing.v1 import AppTest

from src.domain.models import BankProfile, CategoryRule, HistoricalSummary, Transaction
from src.storage import config_store, year_store

PAGE_SCRIPTS = [
    "src/pages_ui/page_dashboard.py",
    "src/pages_ui/page_analyze.py",
    "src/pages_ui/page_data.py",
    "src/pages_ui/page_profiles.py",
    "src/pages_ui/page_rules.py",
    "src/pages_ui/page_groups.py",
    "src/pages_ui/page_historical.py",
    "src/pages_ui/page_settings.py",
]

CURRENT_YEAR = 2026  # arbitrary fixed year — avoids datetime.date.today() drift in fixture data


def _seed_data_home(data_home) -> None:
    config_store.save_bank_profiles(
        data_home,
        {
            "Bank A": BankProfile(
                name="Bank A",
                defaultCurrency="EUR",
                delimiter=";",
                dateColumn="EntryDate",
                dateFormat="%Y-%m-%d",
                amountColumn="Amount EUR",
                decimalSeparator=",",
                descriptionColumns=["Description"],
            )
        },
    )
    config_store.save_rules(data_home, [CategoryRule(pattern="salary", type="income", category="salary")])
    config_store.save_category_groups(data_home, {"groceries": "Food"})
    config_store.save_saved_views(
        data_home,
        [
            {
                "name": "Spend by category",
                "groupBy": ["category"],
                "measure": "Sum of amount",
                "chartType": "table",
                "width": "full",
                "filters": {},
            }
        ],
    )

    year_store.save_transactions(
        data_home,
        CURRENT_YEAR,
        [
            Transaction(
                date=date(CURRENT_YEAR, 1, 15),
                amount=Decimal("-42.50"),
                currency="EUR",
                type="expense",
                rawDescription="K-Market Helsinki",
                category="groceries",
            ),
            Transaction(
                date=date(CURRENT_YEAR, 1, 20),
                amount=Decimal("2000.00"),
                currency="EUR",
                type="income",
                rawDescription="Salary Sample Employer",
                category="salary",
            ),
        ],
    )
    year_store.save_summary(
        data_home,
        CURRENT_YEAR - 2,
        [
            HistoricalSummary(
                year=CURRENT_YEAR - 2, type="expense", category="rent", currency="EUR", amount=Decimal("9600")
            ),
            HistoricalSummary(
                year=CURRENT_YEAR - 2,
                type="income",
                category="salary",
                currency="EUR",
                amount=Decimal("24000"),
            ),
        ],
    )


@pytest.fixture
def seeded_data_home(tmp_path, monkeypatch):
    monkeypatch.setenv("SPENDTRENDS_HOME", str(tmp_path))
    _seed_data_home(tmp_path)
    return tmp_path


@pytest.mark.parametrize("page_script", PAGE_SCRIPTS)
def test_page_mounts_without_exception(page_script, seeded_data_home):
    at = AppTest.from_file(page_script, default_timeout=30)
    at.run()
    assert not list(at.exception), f"{page_script} raised: {list(at.exception)}"


def test_data_page_split_dialog_opens_without_exception(seeded_data_home):
    at = AppTest.from_file("src/pages_ui/page_data.py", default_timeout=30)
    at.run()
    split_button = next(b for b in at.button if b.label == "Split row")
    split_button.click().run()
    assert not list(at.exception)


def test_data_page_make_a_rule_dialog_opens_without_exception(seeded_data_home):
    at = AppTest.from_file("src/pages_ui/page_data.py", default_timeout=30)
    at.run()
    rule_button = next(b for b in at.button if b.label == "Make a rule from this row")
    rule_button.click().run()
    assert not list(at.exception)
