# 04 — Categorization

Rules assign a `type` + `category` to a transaction by matching its description text. There is no
vendor entity. Entities in `01-domain-model.md`; a rule is defined in `01`.

## 1. Normalization (pre-match)

Before matching, both the `rawDescription` and each rule's `pattern` are normalized the same
minimal way (transient, not stored): **lowercase, collapse internal whitespace, trim ends** —
nothing else. A substring match already ignores the volatile noise around the stable merchant
token (store numbers, POS-terminal variants, etc.), so there is nothing to strip.

Because a profile folds the bank's type/label column into `rawDescription` (`03`), a pattern
can key on the nature of a row, not just the merchant: `salary` → an income category; `exchange` /
`topup` / `internal transfer` → `type=skip`.

## 2. Matching — substring, longest wins

- A rule **matches** when its normalized `pattern` is a **substring** of the normalized
 description.
- If several rules match, the one with the **longest pattern** wins; ties break by order in
 `rules.json`.
- The winner sets the row's `type` and (for income/expense) `category`, or — for `type=skip` —
 pre-marks the row to be dropped.
- No match → **uncategorized** (blank category), shown in the needs-attention filter.

No fuzzy matching, scores, thresholds, or priority. Specificity is controlled by how long a
pattern is chosen to be.

### 2.1 Skip rules

A `type=skip` rule pre-marks matching rows (transfers, savings moves, card-bill payments) to be
dropped at commit. Skipped rows are not stored (`01`); they can be un-skipped in review, and a
skip rule re-marks them on any re-import.

## 3. Category values

`category` is free text. The UI offers a dropdown of recently-used values (distinct categories of
that `type` seen in about the last year) and allows free typing. No validity dates, no
merge/split; an unused category simply drops out of the dropdown. Rules and the dropdown deal only
in categories — groups are an analytical fold-up (`01`).

## 4. Manual override

In review the user can set/change `type` and `category` or toggle a row's skip mark by hand; this
wins for that row. Nothing records auto-vs-manual — after commit a value is just a value, edited
by hand thereafter.

## 5. Learning loop (make a rule)

When the user categorizes a row no rule covered, the app offers **"make a rule from this"** in a
modal that:

- pre-fills `pattern` with the normalized description; the user trims it to the stable token
 (e.g. `k-market`) and confirms `type` + `category`;
- shows how many **staged** rows the pattern would match (and how many recent committed rows, for
 awareness of over-broad patterns);
- applies with one of two scopes: **these staged rows only** (apply now, do not save a rule), or
 **save the rule** (applies to these staged rows and all future imports).

Rules are never created silently. (Retroactively rewriting already-committed rows from a new rule
is out of scope for v1; past rows are edited by hand.)

## 6. When rules run

Rules run **at import**, on staged rows only. There is no bulk re-run over stored data.
