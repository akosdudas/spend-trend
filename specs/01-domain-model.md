# 01 — Domain Model

Logical entities and relationships. Physical storage is in `02-storage.md`.

```text
BankProfile ──parses (import)──▶ Transaction ──has──▶ type (income|expense) + category (text)
                                     ▲                        │
                                     │ assigns type+category  │ folds up via
                                CategoryRule                  ▼
                                (matches description)   CategoryGroupMap ──▶ group

HistoricalSummary ──▶ type + category (text)
```

The model is deliberately small. Not modeled as entities:

- **Categories** — plain free text on each transaction, in two pools by `type`. No lifecycle.
- **Groups** — an analytical fold-up: a `category → group` map applied only when rolling up; never
  stored on a transaction.
- **Vendors** — none. The same merchant written differently is just different rows; rules match
  the description text.
- **Import sessions** — import is a workflow, not a stored batch.
- **Income** — not a separate entity; it is `type = income` transactions.
- **Currency zones** — none; currency is recorded per transaction.

## 2. Entities

### 2.1 Type & Category (stored per transaction)

- **`type`** — `income` or `expense`. The primary split; drives spending-vs-income directly.
  Defaults from the amount sign at import and is overridable.
- **`category`** — one free-text value within that type's pool. Income and expense categories are
  separate namespaces (an income "salary" and an expense "groceries" never mix).

Categories have **no entity, no lifecycle, no versioning**: a category is just the text on rows.
Renaming a category, if ever needed, is an **external file edit** — a find-and-replace across the
year CSVs, the historical files, the `category → group` map, and rule targets — not an in-app
operation. The UI offers a dropdown of recently-used values (the distinct categories of that type
seen in about the last year) and allows free typing.

### 2.2 Group — analytical fold-up (expense only)

Groups are higher-level **expense** buckets used only for analysis, defined by a
**`CategoryGroupMap`** stored **group-first** for easy hand-editing — each key is a group, its
value the list of expense categories that fold into it:

```json
{
  "Housing": ["rent", "utilities"],
  "Food": ["groceries", "dining"],
  "Car": ["fuel", "insurance"]
}
```

- These are the headline percentage buckets for spending. **Income is not grouped** — income is
  analyzed by category (and by its `type` total), which is a short list.
- Applied on demand when a view groups by `group`; editing the map never mutates transactions.
- Anything unmapped folds into a default group (**Rest**) and is surfaced so it can be mapped.
- The income/expense split for ratios comes from `type`, not from this map.

**The map is scoped per year** — because each year throws off a few one-off categories (a
specific trip, a one-off purchase) that must not accumulate in one eternal file:

- The shared `config/category-groups.json` is the **current working draft**, holding only
  categories active in **open** years. Prune it freely.
- **Closing** a year snapshots the current map to `data/<year>/groups.json` (sibling to
  `summary.csv`), capturing how that year was grouped at the time.
- **Fold resolution:** a **closed** year folds via its own `data/<year>/groups.json`; **open** and
  **legacy** years (no snapshot) fold via the shared map; unmapped → Rest.
- Regrouping a closed year is a local edit to *its* `groups.json` (1–2 lines) and reshapes only
  that year. Reclassifying a recurring category across years means editing each year's snapshot it
  appears in — scoped and explicit, never one silent edit that reshapes the whole timeline.
- Snapshots are **never auto-overwritten** (see `02-storage.md`): closing preserves an existing
  `groups.json`.

### 2.3 Transaction

One stored row — a real income or expense. Source of truth for recent data. Rows skipped during
import are not stored.

| Field | Type | Notes |
|-------|------|-------|
| `date` | date | Transaction day (no time) |
| `amount` | decimal | Signed; normalized at import (`03-import-and-profiles.md`); rewritable for currency conversion |
| `currency` | string | Recorded per row |
| `type` | `income` \| `expense` | Defaults from amount sign; overridable |
| `rawDescription` | string | Original bank text (empty for manual cash rows) |
| `category` | string | Free-text category within the `type` pool |
| `notes` | string? | Free-text annotation |

No id/hash, no origin, no audit fields, no `group` column (derived), no status. Income "who /
which company" needs no dedicated fields — the `category` carries the person, the `rawDescription`
the payer.

### 2.4 CategoryRule

A text pattern mapped to a type. Three fields:

| Field | Type | Notes |
|-------|------|-------|
| `pattern` | string | Matched as a case-insensitive **substring** of the normalized `rawDescription` (`04-categorization.md`) |
| `type` | `income` \| `expense` \| `skip` | `skip` drops the row at commit; else sets the row's type |
| `category` | string? | Target category when `type` is income/expense |

When several rules match, the **longest pattern wins**; ties break by order in `rules.json`.
Disable a rule by deleting it. There is no match-type, priority, or fuzzy option.

### 2.5 BankProfile

How to parse one bank's CSV format, including how to determine currency. Editable; stored in
`config/bank-profiles.json`. Full field reference and examples in `03-import-and-profiles.md`.

| Field | Type | Notes |
|-------|------|-------|
| `name` | string | Human label |
| `defaultCurrency` | string | ISO code used when no `currencyColumn` |
| `currencyColumn` | string? | Optional source column giving per-row currency |
| `delimiter` | string | field delimiter |
| `dateColumn` / `dateFormat` | string | source column + `strftime` format (datetime truncated to day) |
| `amountColumn` | string | the **signed** amount column (negative = expense) |
| `decimalSeparator` | string | the amount's decimal character, `","` or `"."` (all other non-digit/sign characters are stripped) |
| `descriptionColumns` | string[] | columns concatenated into `rawDescription` |

Files are always read as UTF-8; a byte-order mark, if present, is stripped automatically (no
`encoding` field). A **header row is required** (columns are referenced by name), so there is no
`hasHeader`/`skipRows`. Sign meaning is fixed (negative = expense), not a configured convention.

### 2.6 HistoricalSummary

Aggregate-only past data, by type + category, folding to groups via the map.

| Field | Type | Notes |
|-------|------|-------|
| `year` | int | the year folder |
| `type` | `income` \| `expense` | |
| `category` | string | free-text category |
| `currency` | string | never converted |
| `amount` | decimal | annual sum |

Annual only (no month, no id). Stored one `summary.csv` per year (`02-storage.md`,
`05-historical-data.md`).

### 2.7 Income

Income is a transaction with `type = income` and an income-pool category — no separate entity, no
period field; it aggregates by date like everything else. It comes primarily from bank statements
(imported as ordinary rows); income not on any statement is hand-entered.

## 3. Currency

- A transaction's `currency` comes from the profile's `currencyColumn` when present, else the
  profile's `defaultCurrency`. It is not globally fixed.
- The **amount is validated on parse**: a value that doesn't parse under the profile's
  `decimalSeparator` is **reported and skipped** in review, never silently accepted
  (`03-import-and-profiles.md`). There is no allowed-currency list; the row's currency is whatever
  the column or default gives.
- The app never auto-converts. A foreign-currency row is **rewritten in review** — overwrite its
  `amount` with the converted value and set `currency` to the target. No exchange rate is stored.
- Analysis never sums across currencies; cross-currency comparison uses unitless ratios
  (`06-analysis.md`). In practice each year is a single currency; a one-time mid-year move makes
  exactly that year contain two currencies, read as **two segments** — like two short years.

## 4. Skipping (no deduplication)

- **No deduplication.** No stored id/hash, no duplicate detection. Re-importing the same file
  produces duplicate rows; the remedy is to not do that, or delete a range and re-import.
- **Skipped rows are not stored.** Rows dropped in review (matched by a `type=skip` rule or
  removed by hand) are never written.
- **Rules run at import.** Nothing records auto-vs-manual; after a row is saved its category is
  just a value, edited by hand thereafter.
