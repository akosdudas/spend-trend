# 06 — Analysis

A point-and-click pivot + chart builder plus saved dashboards. Aggregation is plain Python over
in-memory rows (no SQL).

## 1. The builder

Creating a visualization takes no code or config editing: the user makes four choices with
on-screen controls and the result redraws instantly; **Save as view** is a button.

1. **Group-by** — one or more of: `type`, `category`, `group` (derived via the map, `01`),
 merchant (normalized description), month, year, currency. Two dimensions form a grid (e.g.
 group × month).
2. **Measure** — **sum of amount** (v1), or a ratio measure. (Count/average are possible
 later.)
3. **Filters** — year(s)/date range, `type`, `category`, `group`, merchant, currency, amount
 range, text.
4. **Chart type** — table, bar, stacked bar, line, pie.

**Tables carry totals.** A table shows row/column totals, and — when it spans both `type`s — a
**net (income − expense) = savings** line and the **savings rate**. That turns a category list
into a running summary.

Investigating a spike is done by **filtering the Data grid** (`07`) to the category/period in
question — there is no chart-click drill-down.

## 2. Saved views & dashboard

- A saved view is a small JSON config (the four choices) plus a **`width`** (`quarter` | `half` |
 `full`).
- The dashboard renders saved views **in list order** in a flow grid: each at its width,
 left-to-right, wrapping top-to-bottom (CSS only; charts size to their cell). Reorder via up/down
 or by editing `saved-views.json`.
- Pre-seeded starter views (editable like any other):
 - **Current-year summary** — a table of expense categories/groups and income categories with
 sums, plus **total expenditure, total income, net savings, savings rate**; toggle category ↔
 group granularity; switch year.
 - Year-over-year by group.
 - Spend vs income by year, with net and savings rate — the **trend** view.
 - Group share of spend (the headline percentages).
 - Monthly spend by group (current year).
 - This month vs same month last year.
 - Top merchants (month / year).
 - Uncategorized / needs-attention queue.

## 3. Comparisons

Comparisons are expressed in the builder: time on an axis for a trend; multiple periods as series
for year-over-year; a delta table (period A vs B per group). Views spanning summarised years fall
back to annual granularity (`05`).

## 4. No outlier detection

The app does not compute or flag outliers. An outlier is something the user notices on a chart and
then acts on (re-categorize, investigate) — this keeps the app simple and avoids misleading
automatic flags.

## 5. Currency

Currency is a per-row column; the engine **never sums across currencies**. In practice each year
is a single currency, so this is invisible — except the one mid-year move year, which contains two
currencies and reads as **two segments** (like two short years). A value total is always within a
single currency; the move year yields one total per segment. No conversion is performed.

### 5.1 Ratio measures (unitless, cross-currency-comparable)

Computed within a currency-segment (same-currency numerator and denominator), so they form one
continuous series across the move:

| Measure | Definition |
|---------|------------|
| Savings rate | (income − spend) / income |
| Spend as % of income | spend / income |
| Group share of spend | group spend / total spend |

Income and spend are split by the explicit `type` (`01`). Group shares are over expense
groups. These are the cross-year, cross-currency workhorses.

## 6. Planning groundwork

Spend-vs-income and multi-year savings-rate trends are groundwork for later
sabbatical/retirement projection (out of scope now). Combining multi-currency balances into a
single net-worth figure would need a manually entered rate at that time; no live FX is planned.
