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
| `delimiter` | One char: `,` `;` `\t` |
| `dateColumn` / `dateFormat` | Source date column + `strftime` format; datetime is truncated to the day. If several date columns exist, pick one |
| `amountColumn` | The signed amount column, **negative = expense** (name it directly, e.g. `"Amount"`) |
| `decimalSeparator` | The amount's decimal character, `","` or `"."` (below) |
| `descriptionColumns` | Ordered headers joined into `rawDescription`; put the readable type/label column first, then the payee; omit noisy columns |

Files are read as UTF-8; a byte-order mark, if present, is stripped automatically. A header row is
required (columns are referenced by name), so there is no `encoding`, `skipRows`, or `hasHeader`
field.

**`dateFormat`** — `strftime` pattern. Tokens: `%Y` 4-digit year · `%y` 2-digit · `%m` month ·
`%d` day · `%H:%M:%S` time. Examples: `%Y-%m-%d` (`2026-01-02`), `%Y/%m/%d` (`2026/01/23`),
`%Y-%m-%d %H:%M:%S` (datetime), `%d.%m.%Y`, `%m/%d/%Y`.

**`decimalSeparator`** — the amount column's decimal character: `","` (e.g. `1.234,56`,
`5480,34`) or `"."` (e.g. `1,234.56`, `1234.56`). Parsing keeps digits, the sign, and this
character and strips everything else (thousands separators, spaces, currency symbols, a leading
`+`), then reads it as a number. **Sign meaning is fixed** — negative is an expense, positive
income — so nothing to configure; the per-row `type` default follows (overridable in review).

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

| Sample | Delimiter | Decimal | Date | Currency | Type-label column |
|--------|-----------|---------|------|----------|-------------------|
| Bank A | `;` | `,` | `%Y-%m-%d` | default EUR | `Description` |
| Bank B | `;` | `,` | `%Y/%m/%d` | `Currency` col | (none — `Message`/`Name`) |
| Bank C | `,` | `.` | `%Y-%m-%d %H:%M:%S` | `Currency` col (mixed) | `Type` |

Parser requirements these exercise: a BOM (stripped automatically); several date columns /
datetime (pick one, truncate to day); trailing empty column and other unused columns (ignored); a
mixed-currency `Currency` column; and the type-label folded into `rawDescription` so rules can
match `salary`, `exchange`, etc. Real profiles may add per-cell quirks (e.g. an explicit leading
`+` on positive amounts, empty fields written as `-`, single-quoted free-text) — normalized on
parse and noted in that profile's own entry.

## 2. Import

Import is an action **inside the Data spreadsheet** (`07`), not a separate wizard or a stored
batch. Imported rows appear as **staged rows in memory** on the same grid as recent committed
rows and are committed by appending.

1. **Add files** — one or more CSVs, each with a manually-selected profile (no auto-detection).
2. **Parse + normalize** — per profile: signed `amount` (parsed via `decimalSeparator`), `date`
 (day only), assembled `rawDescription`, per-row `currency`, and a default `type` from the
 amount sign. A row whose amount fails to parse is **skipped and reported** in review, never
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

The `amountColumn` is a **signed** number: **negative = expense, positive = income** (fixed, not
configured); the per-row `type` default follows the sign, overridable in review. Number parsing
keeps digits, the sign, and the profile's `decimalSeparator` and strips everything else (thousands
separators, spaces, currency symbols, a leading `+`), then normalizes the decimal to a dot.

## 4. Income

Income is imported as ordinary `type=income` rows (salary, dividends, benefits). Who received it
is in the `category`; the payer is in `rawDescription`. Income not on any statement is
hand-entered. A positive-amount refund is `type=expense` in its expense category (so it nets down
that category's spend), set in review.
