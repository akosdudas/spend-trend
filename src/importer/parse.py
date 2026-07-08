"""CSV parsing per bank profile. See specs/03-import-and-profiles.md."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from src.domain.models import BankProfile, Transaction, Type

_NUMBER_FORMATS = {
    "us": {"decimal": ".", "thousands": ","},
    "eu": {"decimal": ",", "thousands": "."},
    "eu_space": {"decimal": ",", "thousands": " "},
    "plain": {"decimal": ".", "thousands": ""},
}


@dataclass
class ParseError:
    line_number: int
    raw_row: dict
    message: str


@dataclass
class ParseResult:
    rows: list[Transaction]
    errors: list[ParseError]


def parse_amount(raw: str, number_format: str) -> Decimal:
    spec = _NUMBER_FORMATS[number_format]
    text = raw.strip()
    text = re.sub(r"[^\d,.\-+ ]", "", text)  # strip currency symbols and stray characters
    text = text.strip()
    if spec["thousands"]:
        text = text.replace(spec["thousands"], "")
    text = text.replace(" ", "")
    if spec["decimal"] != ".":
        text = text.replace(spec["decimal"], ".")
    return Decimal(text)


def _read_dict_rows(text: str, profile: BankProfile) -> list[dict]:
    lines = text.splitlines()
    lines = lines[profile.skipRows :]
    reader = csv.reader(lines, delimiter=profile.delimiter)
    all_rows = list(reader)
    if not all_rows:
        return []
    if profile.hasHeader:
        header = all_rows[0]
        data_rows = all_rows[1:]
    else:
        header = [str(i) for i in range(len(all_rows[0]))]
        data_rows = all_rows
    return [dict(zip(header, row, strict=False)) for row in data_rows if any(cell.strip() for cell in row)]


def _amount_and_type(row: dict, profile: BankProfile) -> tuple[Decimal, Type]:
    mapping = profile.amountMapping
    number_format = profile.numberFormat

    if profile.amountConvention == "debit_credit":
        debit_raw = row.get(mapping["debitColumn"], "").strip()
        credit_raw = row.get(mapping["creditColumn"], "").strip()
        if debit_raw:
            value = -abs(parse_amount(debit_raw, number_format))
        else:
            value = abs(parse_amount(credit_raw, number_format))
    else:
        raw = row[mapping["amountColumn"]]
        value = parse_amount(raw, number_format)
        if profile.amountConvention == "signed_expense_positive":
            value = -value
        # signed_expense_negative: already in internal convention (spend negative, income positive)

    type_: Type = "expense" if value < 0 else "income"
    return value, type_


def parse_csv_bytes(content: bytes, profile: BankProfile) -> ParseResult:
    text = content.decode(profile.encoding)
    dict_rows = _read_dict_rows(text, profile)

    rows: list[Transaction] = []
    errors: list[ParseError] = []

    for i, row in enumerate(dict_rows, start=1):
        try:
            date_value = datetime.strptime(row[profile.dateColumn], profile.dateFormat).date()
            amount, type_ = _amount_and_type(row, profile)
            currency = (
                row[profile.currencyColumn].strip() if profile.currencyColumn else profile.defaultCurrency
            )
            raw_description = " ".join(row.get(col, "").strip() for col in profile.descriptionColumns).strip()
        except (InvalidOperation, ValueError, KeyError) as exc:
            errors.append(ParseError(line_number=i, raw_row=row, message=str(exc)))
            continue

        rows.append(
            Transaction(
                date=date_value,
                amount=amount,
                currency=currency,
                type=type_,
                rawDescription=raw_description,
                category="",
                notes="",
            )
        )

    return ParseResult(rows=rows, errors=errors)
