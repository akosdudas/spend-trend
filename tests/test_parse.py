from decimal import Decimal

import pytest

from src.domain.models import BankProfile
from src.importer.parse import parse_amount, parse_csv_bytes

# --- parse_amount: one behavior per numberFormat, per specs/03-import-and-profiles.md ---


@pytest.mark.parametrize(
    "raw, number_format, expected",
    [
        ("1,234.56", "us", Decimal("1234.56")),
        ("-1,234.56", "us", Decimal("-1234.56")),
        ("1.234,56", "eu", Decimal("1234.56")),
        ("5480,34", "eu", Decimal("5480.34")),
        ("1 234,56", "eu_space", Decimal("1234.56")),
        ("1234.56", "plain", Decimal("1234.56")),
        ("-2.51", "plain", Decimal("-2.51")),
    ],
)
def test_parse_amount(raw, number_format, expected):
    assert parse_amount(raw, number_format) == expected


# --- parse_csv_bytes against the desensitized fixtures (specs/csv-samples/) ---

BANK_A_PROFILE = BankProfile(
    name="Bank A",
    defaultCurrency="EUR",
    encoding="utf-8-sig",
    delimiter=";",
    hasHeader=True,
    skipRows=0,
    dateColumn="EntryDate",
    dateFormat="%Y-%m-%d",
    amountMapping={"amountColumn": "Amount EUR"},
    amountConvention="signed_expense_negative",
    numberFormat="eu",
    descriptionColumns=["Description", "Recipient/Payer"],
)

BANK_B_PROFILE = BankProfile(
    name="Bank B",
    defaultCurrency="EUR",
    currencyColumn="Currency",
    encoding="utf-8-sig",
    delimiter=";",
    hasHeader=True,
    skipRows=0,
    dateColumn="Booking date",
    dateFormat="%Y/%m/%d",
    amountMapping={"amountColumn": "Amount"},
    amountConvention="signed_expense_negative",
    numberFormat="eu",
    descriptionColumns=["Name", "Message"],
)

BANK_C_PROFILE = BankProfile(
    name="Bank C",
    defaultCurrency="EUR",
    currencyColumn="Currency",
    encoding="utf-8",
    delimiter=",",
    hasHeader=True,
    skipRows=0,
    dateColumn="Completed Date",
    dateFormat="%Y-%m-%d %H:%M:%S",
    amountMapping={"amountColumn": "Amount"},
    amountConvention="signed_expense_negative",
    numberFormat="plain",
    descriptionColumns=["Type", "Description"],
)


def test_bank_a_bom_and_eu_numbers(csv_samples_dir):
    result = parse_csv_bytes((csv_samples_dir / "bank-a.csv").read_bytes(), BANK_A_PROFILE)

    assert not result.errors
    salary = next(r for r in result.rows if "SALARY" in r.rawDescription)
    assert salary.amount == Decimal("5480.34")
    assert salary.type == "income"
    assert salary.currency == "EUR"
    assert "SALARY" in salary.rawDescription
    assert "SAMPLE EMPLOYER OY" in salary.rawDescription  # descriptionColumns joined in order


def test_bank_b_date_format_and_currency_column(csv_samples_dir):
    result = parse_csv_bytes((csv_samples_dir / "bank-b.csv").read_bytes(), BANK_B_PROFILE)

    assert not result.errors
    assert all(r.currency == "EUR" for r in result.rows)  # from the Currency column, not default
    assert result.rows[0].date.isoformat() == "2025-01-10"  # %Y/%m/%d parsed correctly
    assert result.rows[0].type == "expense"


def test_bank_c_datetime_truncated_and_mixed_currency(csv_samples_dir):
    result = parse_csv_bytes((csv_samples_dir / "bank-c.csv").read_bytes(), BANK_C_PROFILE)

    assert not result.errors
    currencies = {r.currency for r in result.rows}
    assert currencies == {"EUR", "USD", "HUF"}  # mixed-currency column, no conversion
    card_payment = result.rows[0]
    assert card_payment.date.isoformat() == "2026-01-01"  # datetime truncated to day
    assert card_payment.rawDescription == "Card Payment Sample Merchant"  # Type + Description joined


def test_unparseable_amount_is_reported_and_skipped():
    content = (
        b"EntryDate;ValueDate;Amount EUR;Code;Description;Recipient/Payer\n"
        b"2026-01-02;2026-01-02;not-a-number;162;CARD PAYMENT;Sample Merchant\n"
    )
    result = parse_csv_bytes(content, BANK_A_PROFILE)

    assert result.rows == []
    assert len(result.errors) == 1
    assert result.errors[0].line_number == 1
