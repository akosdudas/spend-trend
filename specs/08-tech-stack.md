# 08 — Tech Stack

## 1. Summary

| Concern | Choice |
|---------|--------|
| Language | **Python 3** (pinned minor) |
| UI | **Streamlit** — pure Python; no templates, no hand-written JS, no build step |
| Window | **`pywebview`** — a native window wrapping the local Streamlit server |
| Editable grid | `st.data_editor` |
| Charts | **Plotly** via `st.plotly_chart` (bar / pie / line / table) |
| Core I/O | stdlib `csv` + `json` (pandas available transitively, used where convenient) |
| Categorization | stdlib — case-insensitive substring, longest pattern wins |
| Run | venv + pinned `requirements.txt`; a double-click launcher opens the window |

## 2. Rationale

The data work is trivial and stays stdlib (CSV/JSON I/O, substring categorization, aggregation
over ~10–20k rows — no DB, no SQL, no fuzzy lib). The UI is where code and fragility concentrate,
so it is generated from plain Python by Streamlit — the grid (`st.data_editor`), import
(`st.file_uploader`), modals (`st.dialog`), and the chart builder — with no HTML/Jinja/JS. The
instant rerun-on-change model suits ad-hoc analysis. `pywebview` presents the local server as a
native window.

Streamlit brings a transitive dependency tree (pandas, pyarrow, numpy, …); that is accepted in
exchange for minimal UI code, and versions are pinned.

## 3. Dependencies & version policy

Direct third-party dependencies:

```text
streamlit    # the UI
plotly       # charts
pywebview    # native window
```

Everything else is transitive or stdlib. Pin **exact** versions, chosen for maturity over
recency:

- **Python:** a stable minor still in security support (not the newest); match what is readily
  available on the machine.
- **Streamlit / Plotly / pywebview:** none publish an LTS, so pin a release that has been out long
  enough to be widely used, not `.0` of the newest major.
- Upgrade only deliberately, with a smoke test; a pinned set runs offline for years.

## 4. Run

A venv with the three deps and a double-click launcher (`run.command` on macOS) that starts
Streamlit on a fixed localhost port and opens the `pywebview` window. No external services, no
network, no auth.

## 5. Project shape (indicative)

The repo holds only code, specs, and samples — no config or data.

```text
spendtrends/
  __main__.py            # launcher: start Streamlit + open the window
  app.py                 # Streamlit UI (Dashboard, Analyze, Data, Profiles, Rules, Groups, …)
  storage/               # CSV/JSON load+save, safe-save, data-home resolution, year lifecycle
  domain/                # dataclasses
  importer/              # CSV parse per profile, currency parse
  categorize/            # substring rule engine
  analysis/              # aggregation, category→group fold-up, ratios
specs/                   # incl. csv-samples/
.gitignore               # ignores /config, /data, .env, *.local
requirements.txt
run.command
```

## 6. App / data separation

The repo is publishable and contains **zero personal data**. Config and data live in an external
**data home** (`02-storage.md`), enforced by: the data home defaulting outside the repo; a
`.gitignore` ignoring `/config/`, `/data/`, `.env`, `*.local`; and the app **refusing a data home
inside the repo working tree**.

## 7. Locating the data home

The data home location is a one-line **pointer file** in the OS per-user app directory (macOS
`~/Library/Application Support/spend-trends/`, `~/.spend-trends/` fallback elsewhere) — outside
the repo, so it is never committed.

- **Setup (no in-app picker — that would be extra UI code):** create the data home folder and the
  pointer file by hand, or run a small bundled setup script, or pass `--data-dir <path>` (or set
  `SPENDTRENDS_HOME`). The setup script scaffolds `config/` + `data/`.
- If no data home is configured, the app **exits with a short message** explaining how to set one
  (edit the pointer file or pass `--data-dir`).
- Once configured, every run reads the pointer and loads from the data home.
