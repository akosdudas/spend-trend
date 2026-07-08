# spend-trends

A local, single-user household spending tracker: import bank CSVs, categorize transactions, and
analyze spend over time. See `specs/00-overview.md` for the full design.

## Setup

1. **Install dependencies** (creates `.venv` with Python 3.11 and installs everything, including
   dev tooling):
   ```
   make init
   ```
   Requires `python3.11` on `PATH` (see `.python-version`); install it if missing, e.g.
   `brew install python@3.11` on macOS.
2. **Create a data home** — a folder outside this repo that holds your real (private) config and
   data:
   ```
   .venv/bin/python setup_data_home.py ~/path/to/data-home
   ```
   This writes a pointer file so the app always finds it. The repo itself never contains personal
   data.

## Running the app

```
make run
```

If no data home is configured yet, the app exits with instructions to run `setup_data_home.py` or
pass `--data-dir <path>` / set `SPENDTRENDS_HOME`.

Once running, import a bank CSV under a bank profile (Data screen), set up categorization rules
(Rules screen), and explore spend on the Dashboard/Analyze screens.

## Development

- `make check` — lint, typecheck, and test (runs `ruff`, `mypy`, `pytest`)
- `make lint` / `make format` — `ruff check` / `ruff format`
- `make typecheck` — `mypy`
- `make test` — `pytest`

See `AGENTS.md` and `specs/` for design docs and repo-wide rules.
