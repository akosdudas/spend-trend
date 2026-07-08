# AGENTS.md

Index for agents working in this repo. The design lives in `specs/` — that is the source of
truth. This file only points to it and states the few repo-wide rules.

## What this is

A local, single-user household spending tracker (import bank CSVs → categorize → analyze). See
`specs/00-overview.md`.

## Where things are

| Topic | Doc |
|-------|-----|
| Goals, principles, scope | `specs/00-overview.md` |
| Entities & relationships | `specs/01-domain-model.md` |
| Storage layout, year lifecycle, saving | `specs/02-storage.md` |
| CSV import & bank-profile format | `specs/03-import-and-profiles.md` |
| Categorization rules | `specs/04-categorization.md` |
| Historical (aggregate) data | `specs/05-historical-data.md` |
| Analysis / dashboards | `specs/06-analysis.md` |
| Screens & workflows | `specs/07-ux.md` |
| Stack, run, app/data separation | `specs/08-tech-stack.md` |
| Desensitized CSV fixtures | `specs/csv-samples/` |

## Working with the specs

Read the relevant spec doc before changing behavior; when behavior changes, update that doc in the
same change and re-check it stays consistent with the others. Keep specs declarative and terse,
and reference other docs by filename (not section number).

## Repo-wide rules

1. **No personal data in the repo, ever** — it is publishable. Real config and data live in an
   external data home; details in `specs/08-tech-stack.md`. Desensitize any sample before
   committing.
2. **Stack and constraints** are defined in `specs/08-tech-stack.md` — follow them rather than
   introducing new dependencies.
