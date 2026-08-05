# 03 — Import & Bank Profiles

CSV ingestion and the bank-profile format. Entities in `01-domain-model.md`; categorization in
`04-categorization.md`.

## 1. Bank profiles

A `BankProfile` describes how to parse one bank's CSV format. Profiles are stored as JSON in
`config/bank-profiles.json` in the data home (`08`), **edited by hand** using the field
reference below. The app provides a **Test parse** action: point it at a sample CSV and it shows
the first rows *as the app would normalize them* (parsed date, signed amount, currency, assembled
description) so a profile can be verified before importing for real. (No in-app column-mapping
form — a handful of profiles are set up once, and the JSON + reference is enough.)

Any key starting with `_` (e.g. `_comment`) is ignored on load — a way to annotate a hand-edited
entry without it being treated as a field. This applies to `bank-profiles.json` and `rules.json`.

### 1.1 Field reference

Column names are always the exact header strings from the CSV.

| Field | Meaning |
|-------|---------|
| `name` | Human label |
| `defaultCurrency` | ISO code used when `currencyColumn` is absent |
| `currencyColumn` | Optional source column giving per-row currency |
| `encoding` | Python codec: `utf-8`, `utf-8-sig` (strips a BOM), `latin-1`/`cp1252` (legacy) |
| `delimiter` | One char: `,` `;` `\t` |
| `hasHeader` | `true` if the first non-skipped row is column names |
| `skipRows` | Preamble lines before the header row |
| `dateColumn` / `dateFormat` | Source date column + `strftime` format; datetime is truncated to the day. If several date columns exist, pick one |
| `amountMapping` | `{ "amountColumn": "Amount" }` or `{ "debitColumn": "...", "creditColumn": "..." }` |
| `amountConvention` | How sign maps to spend vs income (below) |
| `numberFormat` | Decimal/thousands punctuation of the amount (below) |
| `descriptionColumns` | Ordered headers joined into `rawDescription`; put the readable type/label column first, then the payee; omit noisy columns |

**`dateFormat`** — `strftime` pattern. Tokens: `%Y` 4-digit year · `%y` 2-digit · `%m` month ·
`%d` day · `%H:%M:%S` time. Examples: `%Y-%m-%d` (`2026-01-02`), `%Y/%m/%d` (`2026/01/23`),
`%Y-%m-%d %H:%M:%S` (datetime), `%d.%m.%Y`, `%m/%d/%Y`.

**`numberFormat`** — punctuation of the amount column (thousands separator optional):

| Value | Decimal | Thousands | Example |
|-------|---------|-----------|---------|
| `us` | `.` | `,` | `1,234.56` |
| `eu` | `,` | `.` | `1.234,56` / `5480,34` |
| `eu_space` | `,` | space | `1 234,56` |
| `plain` | `.` | none | `1234.56` |

**`amountConvention`** — `signed_expense_negative` (single signed column; negative = expense,
positive = income), `signed_expense_positive` (positive = expense), or `debit_credit` (with
`debitColumn`/`creditColumn`; debit = outflow, credit = inflow). The per-row `type` default
follows: outflow → `expense`, inflow → `income` (overridable in review).

**`descriptionColumns`** — concatenated (space-joined) into `rawDescription`; type-label first so
rules can match the *nature* of a row (e.g. a `Type`/`Description` column). Examples:

```json
["Description", "Recipient/Payer"] // "SALARY SAMPLE EMPLOYER OY"
["Type", "Description"] // "Card Payment Sample Merchant"
["Name", "Message"] // counterparty + free-text keywords
```

### 1.2 Sample formats

Three desensitized exports in `specs/csv-samples/` (`bank-a.csv`, `bank-b.csv`, `bank-c.csv`)
exercise the parser. They carry no personal data and use generic bank names.

| Sample | Delimiter | Encoding | Numbers | Date | Currency | Type-label column |
|--------|-----------|----------|---------|------|----------|-------------------|
| Bank A | `;` | `utf-8-sig` | `eu` | `%Y-%m-%d` | default EUR | `Description` |
| Bank B | `;` | `utf-8-sig` | `eu` | `%Y/%m/%d` | `Currency` col | (none — `Message`/`Name`) |
| Bank C | `,` | `utf-8` | `plain` | `%Y-%m-%d %H:%M:%S` | `Currency` col (mixed) | `Type` |

Parser requirements these exercise: BOM (`utf-8-sig`); several date columns / datetime (pick one,
truncate to day); trailing empty column and other unused columns (ignored); a mixed-currency
`Currency` column; and the type-label folded into `rawDescription` so rules can match `salary`,
`exchange`, etc.

## 2. Import

Import is an action **inside the Data spreadsheet** (`07`), not a separate wizard or a stored
batch. Imported rows appear as **staged rows in memory** on the same grid as recent committed
rows and are committed by appending.

1. **Add files** — one or more CSVs, each with a manually-selected profile (no auto-detection).
2. **Parse + normalize** — per profile: signed `amount` (validated against `numberFormat`), `date`
 (day only), assembled `rawDescription`, per-row `currency`, and a default `type` from the
 amount sign. A row whose number fails to parse is **skipped and reported** in review, never
 silently accepted.
3. **Auto-categorize** — run rules (`04`): set `type` + `category`, or pre-mark `type=skip`.
4. **Review inline** — edit `category`/`type`, touch up `amount`, add `notes`, delete a row,
 rewrite a foreign-currency row, split a row, or make a rule from a row (`04`).
 Filter to **needs-attention** (uncategorized) to handle the bulk via rules and focus on the
 few unknowns. No per-row "done" gate.
5. **Commit** — non-skipped rows are appended to the correct year file(s) by date; skipped rows
 are discarded. Committing with some rows still **uncategorized** is allowed — they persist with
 a blank category and stay in the needs-attention filter to resolve later.

Until commit, staged rows are in memory only. A staged row dated into a **closed** year triggers a
warn + offer to reopen (or retarget), never a silent change (`02`).

### 2.1 Foreign-currency rows

A row in a different currency than wanted is **rewritten in review**: overwrite `amount` with the
converted value and set `currency` to the target. No exchange rate is stored; the original
`rawDescription` is kept.

### 2.2 Manual (cash) rows

Costs absent from any CSV are added by typing a new line directly in the grid — same columns as
any row, no dialog.

### 2.3 Split a row

A **Split** action opens a modal to edit the current row (e.g. reduce its amount) and enter a
split-off entry (`date` and `currency` copied, amount + category typed). The new row is appended;
the file re-sorts by date on save. The two rows are independent afterward (no parent/child link).

## 3. Amount & sign normalization

The profile's `amountConvention` makes spend vs income unambiguous. Internally: spend negative,
income positive; the per-row `type` default follows the sign, overridable in review. Number
parsing follows `numberFormat`: thousands separators stripped, decimal normalized, currency
symbols and stray whitespace removed.

## 4. Income

Income is imported as ordinary `type=income` rows (salary, dividends, benefits). Who received it
is in the `category`; the payer is in `rawDescription`. Income not on any statement is
hand-entered. A positive-amount refund is `type=expense` in its expense category (so it nets down
that category's spend), set in review.
