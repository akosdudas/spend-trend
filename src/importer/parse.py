"""CSV parsing per bank profile. See specs/03-import-and-profiles.md."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from src.domain.models import BankProfile, Transaction, Type


@dataclass
class ParseError:
    line_number: int
    raw_row: dict
    message: str


@dataclass
class ParseResult:
    rows: list[Transaction]
    errors: list[ParseError]


def _normalize_cell(raw: str | None) -> str:
    """Generic per-cell cleanup applied to every field of every profile (03-import-and-profiles.md §1.2).

    Trims whitespace, collapses internal whitespace runs, strips a surrounding pair of single
    quotes, and treats a lone "-" as empty. Not bank-specific — the same pass covers every profile.
    """
    text = re.sub(r"\s+", " ", (raw or "").strip())
    if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
        text = re.sub(r"\s+", " ", text[1:-1].strip())
    if text == "-":
        return ""
    return text


def parse_amount(raw: str, decimal_separator: str) -> Decimal:
    """Keep digits, a leading sign, and the decimal separator; strip everything else."""
    text = raw.replace("+", "")
    kept = re.sub(r"[^\d\-" + re.escape(decimal_separator) + "]", "", text)
    if decimal_separator != ".":
        kept = kept.replace(decimal_separator, ".")
    return Decimal(kept)


def _read_dict_rows(text: str, profile: BankProfile) -> list[dict]:
    reader = csv.DictReader(text.splitlines(), delimiter=profile.delimiter)
    rows = []
    for row in reader:
        normalized = {key: _normalize_cell(value) for key, value in row.items() if key is not None}
        if any(normalized.values()):
            rows.append(normalized)
    return rows


def _amount_and_type(row: dict, profile: BankProfile) -> tuple[Decimal, Type]:
    value = parse_amount(row[profile.amountColumn], profile.decimalSeparator)
    type_: Type = "expense" if value < 0 else "income"
    return value, type_


def parse_csv_bytes(content: bytes, profile: BankProfile) -> ParseResult:
    text = content.decode("utf-8-sig")  # always UTF-8; strips a BOM if present, else a no-op
    dict_rows = _read_dict_rows(text, profile)

    rows: list[Transaction] = []
    errors: list[ParseError] = []

    for i, row in enumerate(dict_rows, start=1):
        try:
            date_value = datetime.strptime(row[profile.dateColumn], profile.dateFormat).date()
            amount, type_ = _amount_and_type(row, profile)
            currency = row[profile.currencyColumn] if profile.currencyColumn else profile.defaultCurrency
            raw_description = " ".join(row.get(col, "") for col in profile.descriptionColumns).strip()
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
