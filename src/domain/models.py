"""Domain dataclasses. See specs/01-domain-model.md."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as Date
from decimal import Decimal
from typing import Literal

Type = Literal["income", "expense"]
RuleType = Literal["income", "expense", "skip"]


@dataclass
class Transaction:
    date: Date
    amount: Decimal
    currency: str
    type: Type
    rawDescription: str = ""
    category: str = ""
    notes: str = ""


@dataclass
class CategoryRule:
    pattern: str
    type: RuleType
    category: str | None = None


@dataclass
class BankProfile:
    name: str
    defaultCurrency: str
    encoding: str
    delimiter: str
    hasHeader: bool
    skipRows: int
    dateColumn: str
    dateFormat: str
    amountMapping: dict
    amountConvention: Literal["signed_expense_negative", "signed_expense_positive", "debit_credit"]
    numberFormat: Literal["us", "eu", "eu_space", "plain"]
    descriptionColumns: list[str] = field(default_factory=list)
    currencyColumn: str | None = None


@dataclass
class HistoricalSummary:
    year: int
    type: Type
    category: str
    currency: str
    amount: Decimal
