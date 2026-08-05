# 05 — Historical Data

Past years for which only aggregate sums exist (no transaction detail), and how they coexist with
transaction-level years. Entities in `01-domain-model.md`; storage in `02-storage.md`.

## 1. What it is

Past data is **annual sums by type + category**, stored as `HistoricalSummary` rows. It folds up
to groups and feeds the same analysis as transaction data — only the time granularity differs
(annual, no month). Grouping is scoped per year: a **closed** year folds via its own
`data/<year>/groups.json` snapshot; a **legacy** year (no snapshot) folds via the shared map
(`01-domain-model.md`).

## 2. Storage

A legacy year is a `data/<year>/` folder with a `summary.csv` and no `transactions.csv`. Each row
is `type,category,currency,amount`:

```text
type,category,currency,amount
expense,housing,EUR,26000
expense,groceries,EUR,9400
income,salary,EUR,110000
```

- `category` folds to a group when rolling up; income stays by category.
- `currency` tags the row and is never converted. A category present in two currencies in one
 year has one row per currency.
- Hand-written, one `summary.csv` per year; this is the source of truth for that year. No
 bulk-import format.

On load: categories not covered by the year's grouping (its own snapshot, or the shared map for a
legacy year) fold into the default group and are surfaced; non-numeric cells are reported and
skipped. Regrouping a closed year is a local edit to its `data/<year>/groups.json` and affects
only that year.

## 3. Coexistence with transaction years

A year is read as **either open or summarised, never both**:

- **Open** years have `transactions.csv`, aggregated live, and can show monthly detail.
- **Closed / legacy** years are read from `summary.csv` (annual). If a year has both files, the
 summary is used and the transactions ignored (the closed state, `02`).

Both planes are **by category**, so category and its group fold-up work across the whole timeline;
only time granularity falls back to **annual** for views that include summarised years. Views
restricted to open years may use monthly detail.

A one-time mid-year currency move appears as **two segments** in that year (one row set per
currency), read like two short years — no conversion (`01`, `06`).
