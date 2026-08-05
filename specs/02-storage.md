# 02 — Storage

On-disk layout and runtime data handling. Logical entities are in `01-domain-model.md`.

## 1. In-memory, no database

Volume is small (~1–2k transactions/year; ~10–20k for a decade), so the dataset is held in
memory:

- No database and no SQL engine. Files are the source of truth; aggregation is plain Python over
  in-memory rows.
- Core I/O uses the standard library (`csv`, `json`). pandas is present transitively (via the UI
  stack, `08-tech-stack.md`) and may be used where convenient, but is not the source of truth.
- On load, the relevant year files are read into memory; on change, the whole file is rewritten
  with a safe save. The app tolerates files edited by hand between runs.

## 2. Data home layout

All config and data live in a **data home** — a single folder chosen by the user, outside the app
repo (resolution in `08-tech-stack.md`). The repo ships no config or data.

```text
<data home>/
  config/
    bank-profiles.json     # parsing profiles
    category-groups.json   # shared expense category → group map (current working draft)
    rules.json             # categorization rules (pattern → type[income/expense/skip] + category)
    saved-views.json       # saved analysis views
    settings.json          # small app settings
  data/
    2019/
      summary.csv          # legacy year: annual sums, no transaction file, no snapshot
    2023/
      summary.csv          # closed year: annual sums
      groups.json          # closed year: its own category → group snapshot
    2024/
      transactions.csv     # open year: per-transaction rows
    2025/
      transactions.csv
```

- `config/` is small hand-editable JSON; `data/` is one folder per year.
- A `data/<year>/` folder holds `transactions.csv` (open) and/or `summary.csv` (closed/legacy),
  and — for closed years — a `groups.json` grouping snapshot (see below).
- No staging, archive, or backup directories.

## 3. The per-year files

**`transactions.csv`** (open years) — columns are the `Transaction` fields:
`date,amount,currency,type,rawDescription,category,notes`.

- Committed rows are appended; on every save the file is **rewritten sorted by `date`**, so append
  order never matters and hand-edited files are normalized.
- A row's year (folder) is its `date`'s year; an import spanning a year boundary writes into two
  folders.
- No id/hash column (no dedup); no group column (derived).

**`summary.csv`** (closed / legacy years) — annual sums, rows of `type,category,currency,amount`
(year is the folder).

**`groups.json`** (closed years) — the year's own `category → group` snapshot, same group-first
shape as the shared map. It folds that year's categories so its grouping stays fixed as it was at
close, independent of later edits to the shared map (`01-domain-model.md`). Legacy years have no
snapshot and fold via the shared map.

All are plain files, editable outside the app; changes are picked up on next load.

## 4. Year lifecycle: open → closed (optional)

Two states; closing is optional and never prompted (a year may stay open indefinitely). Its only
purpose is to freeze a settled old year into the same shape as legacy years.

1. **Open** — has `transactions.csv`; edited freely; aggregated live; grouped via the shared map.
2. **Closed** — a user action compiles `summary.csv` (annual sums, no month) into the folder and,
   **if none exists yet**, snapshots the shared map to `groups.json`. `transactions.csv` is kept
   but no longer read. There is no in-app editor for a closed year.
3. **Reopen** — delete `summary.csv`; `transactions.csv` is read live again. `groups.json` is
   **left in place** (dormant while open) so re-closing preserves any hand-edits to it.

Closing **never overwrites an existing `groups.json`** — to regenerate a year's grouping snapshot,
delete it, then close. A row whose `date` lands in an already-closed year prompts a **warn + offer
to reopen** (or retarget), never a silent change. **Legacy** years have only a `summary.csv` (no
snapshot) and fold via the shared map — otherwise identical to closed years
(`05-historical-data.md`).

## 5. Saving

- Single local process; the only safeguard is a **safe save**: write a temp file in the same
  folder, then atomically replace the target, so a crash mid-write cannot corrupt the file.
- No app-managed backups. Files are plain text; external version history (e.g. a synced folder)
  is the user's responsibility.
