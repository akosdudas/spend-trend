# 00 — Overview

A local, single-user application to track household spending and analyze it with ad-hoc tables
and charts. Expenses and income are imported from bank CSV exports, categorized, and analyzed
month-over-month and year-over-year, including spending versus income over multiple years.

## Principles

1. **Local, single-user.** Runs on one machine in a native window; no accounts, auth, cloud, or
 network calls.
2. **File-based, no database.** All data is plain, human-readable files (CSV/JSON) that remain
 usable without the app. Volume is small (~1–2k transactions/year), so everything is held in
 memory; no query engine.
3. **Longevity.** A small, stable dependency set with pinned versions; the app keeps running for
 years without maintenance.
4. **Automatic but overridable.** Categorization runs automatically on import; every automatic
 decision can be changed by hand before it is saved.
5. **Editable like a spreadsheet.** Stored data is edited freely afterward; nothing is locked.

## Goals

- Import bank CSVs of varying formats via per-bank, editable **profiles**.
- **Automatically categorize** transactions by matching the description text (case-insensitive
 substring, longest match wins), with manual override per row.
- Store recent data at **transaction level** (editable) and past data as **annual category sums**.
- Provide **monthly and yearly** views per category and group, with month-over-month and
 year-over-year comparison.
- Track **income alongside spending** for multi-year net/savings views.
- Offer **default dashboards** plus a point-and-click **ad-hoc visualization** builder.

## Non-goals

- No multi-user, authentication, or cloud sync.
- No live bank/API integration — CSV is the only ingest path.
- No mobile or separate native toolkit UI beyond the local window.
- **No currency conversion engine.** Data may span multiple currencies (e.g. after relocating).
 Currency is recorded per row and **never auto-converted or summed across currencies**;
 cross-currency comparison is via unitless ratios (`06-analysis.md`). A foreign-currency row is
 converted by manually rewriting its amount and currency.
- No forecasting/projection engine. The data model keeps multi-year net trends clean as
 groundwork, but projections are out of scope.

## Spec map

| File | Covers |
|------|--------|
| `00-overview.md` | This document |
| `01-domain-model.md` | Entities and relationships |
| `02-storage.md` | On-disk layout, per-year files, year lifecycle, saving |
| `03-import-and-profiles.md` | CSV import, bank profiles, field reference |
| `04-categorization.md` | Rules: substring match, skip, overrides, learning loop |
| `05-historical-data.md` | Aggregate-only past years and how they coexist with transactions |
| `06-analysis.md` | Pivot + chart builder, group fold-up, ratios, dashboard |
| `07-ux.md` | Screens and workflows |
| `08-tech-stack.md` | Stack, run story, app/data separation, data-home resolution |
