from decimal import Decimal

import pytest

from src.domain.models import BankProfile
from src.importer.parse import _normalize_cell, parse_amount, parse_csv_bytes

# --- parse_amount: keep digits/sign/decimalSeparator, strip everything else (specs/03) ---


@pytest.mark.parametrize(
    "raw, decimal_separator, expected",
    [
        ("1,234.56", ".", Decimal("1234.56")),
        ("-1,234.56", ".", Decimal("-1234.56")),
        ("1.234,56", ",", Decimal("1234.56")),
        ("5480,34", ",", Decimal("5480.34")),
        ("1 234,56", ",", Decimal("1234.56")),
        ("1234.56", ".", Decimal("1234.56")),
        ("-2.51", ".", Decimal("-2.51")),
        ("+1234.56", ".", Decimal("1234.56")),  # a leading "+" is stripped
        ("EUR -3,99", ",", Decimal("-3.99")),  # currency symbol stripped
    ],
)
def test_parse_amount(raw, decimal_separator, expected):
    assert parse_amount(raw, decimal_separator) == expected


# --- _normalize_cell: the generic per-cell cleanup applied to every field (specs/03 §1.2) ---


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("  hello   world  ", "hello world"),  # trim + collapse internal whitespace
        ("-", ""),  # a lone "-" means empty
        ("'quoted note'", "quoted note"),  # surrounding single quotes stripped
        ("'  spaced  inside  '", "spaced inside"),  # collapse whitespace after unquoting too
        ("plain", "plain"),
        (None, ""),
        ("", ""),
    ],
)
def test_normalize_cell(raw, expected):
    assert _normalize_cell(raw) == expected


# --- parse_csv_bytes against the desensitized fixtures (specs/csv-samples/) ---

BANK_A_PROFILE = BankProfile(
    name="Bank A",
    defaultCurrency="EUR",
    delimiter=";",
    dateColumn="EntryDate",
    dateFormat="%Y-%m-%d",
    amountColumn="Amount EUR",
    decimalSeparator=",",
    descriptionColumns=["Description", "Recipient/Payer"],
)

BANK_B_PROFILE = BankProfile(
    name="Bank B",
    defaultCurrency="EUR",
    currencyColumn="Currency",
    delimiter=";",
    dateColumn="Booking date",
    dateFormat="%Y/%m/%d",
    amountColumn="Amount",
    decimalSeparator=",",
    descriptionColumns=["Name", "Message"],
)

BANK_C_PROFILE = BankProfile(
    name="Bank C",
    defaultCurrency="EUR",
    currencyColumn="Currency",
    delimiter=",",
    dateColumn="Completed Date",
    dateFormat="%Y-%m-%d %H:%M:%S",
    amountColumn="Amount",
    decimalSeparator=".",
    descriptionColumns=["Type", "Description"],
)


def test_bank_a_bom_and_comma_decimal(csv_samples_dir):
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


def test_dash_only_field_is_treated_as_empty():
    content = (
        b"EntryDate;ValueDate;Amount EUR;Code;Description;Recipient/Payer\n"
        b"2026-01-02;2026-01-02;-3,99;162;CARD PAYMENT;-\n"
    )
    result = parse_csv_bytes(content, BANK_A_PROFILE)

    assert not result.errors
    assert result.rows[0].rawDescription == "CARD PAYMENT"  # the "-" recipient contributed nothing
