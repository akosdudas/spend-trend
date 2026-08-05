"""The Data spreadsheet: import + inline edit. See specs/07-ux.md §2.3, specs/03, specs/04."""

from __future__ import annotations

from datetime import date as Date
from decimal import Decimal, InvalidOperation
from typing import Literal, cast

import pandas as pd
import streamlit as st

from src.categorize.rules_engine import StagedRow, categorize_rows, count_matches, normalize
from src.domain.models import CategoryRule, Transaction
from src.importer.parse import parse_csv_bytes
from src.storage import config_store, year_store

COLUMNS = ["source", "date", "amount", "currency", "type", "rawDescription", "category", "notes", "skip"]


def _needs_attention(t: Transaction) -> bool:
    return t.category.strip() == ""


def _row_dict(source: str, t: Transaction, skip: bool) -> dict:
    return {
        "source": source,
        "date": t.date,
        "amount": float(t.amount),
        "currency": t.currency,
        "type": t.type,
        "rawDescription": t.rawDescription,
        "category": t.category,
        "notes": t.notes,
        "skip": skip,
    }


def _row_to_transaction(row: dict) -> Transaction:
    date_value = row["date"]
    if hasattr(date_value, "date"):
        date_value = date_value.date()
    try:
        amount = Decimal(str(round(float(row["amount"]), 2)))
    except (InvalidOperation, TypeError, ValueError):
        amount = Decimal("0")
    return Transaction(
        date=date_value,
        amount=amount,
        currency=str(row.get("currency") or "").strip(),
        type=row.get("type") or "expense",
        rawDescription=str(row.get("rawDescription") or ""),
        category=str(row.get("category") or ""),
        notes=str(row.get("notes") or ""),
    )


def _ensure_state() -> None:
    if "staged" not in st.session_state:
        st.session_state.staged = []
    if "grid_version" not in st.session_state:
        st.session_state.grid_version = 0
    if "pending_closed_years" not in st.session_state:
        st.session_state.pending_closed_years = None


def render(data_home) -> None:
    st.header("Data")
    _ensure_state()

    rules = config_store.load_rules(data_home)
    profiles = config_store.load_bank_profiles(data_home)

    _render_import_section(data_home, profiles, rules)
    _render_commit_section(data_home)

    years = sorted(set(year_store.list_years(data_home)) | {Date.today().year})
    default_year = Date.today().year
    year = st.selectbox(
        "Year", years, index=years.index(default_year) if default_year in years else len(years) - 1
    )
    assert year is not None  # a non-empty options list always yields a selection

    year_kind = year_store.year_state(data_home, year)
    if year_kind == "summarized":
        st.warning(f"{year} is closed. Reopen it in Settings to edit its transactions.")
        committed: list[Transaction] = []
    else:
        committed = year_store.load_transactions(data_home, year)

    needs_attention_only = st.checkbox("Needs attention only (uncategorized)")

    df, shown_ids = _build_display_df(committed, needs_attention_only)

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key=f"grid_{year}_{needs_attention_only}_{st.session_state.grid_version}",
        column_config={
            "source": st.column_config.TextColumn("Status", disabled=True),
            "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
            "amount": st.column_config.NumberColumn("Amount", format="%.2f"),
            "currency": st.column_config.TextColumn("Currency"),
            "type": st.column_config.SelectboxColumn("Type", options=["income", "expense"]),
            "rawDescription": st.column_config.TextColumn("Description"),
            "category": st.column_config.TextColumn("Category"),
            "notes": st.column_config.TextColumn("Notes"),
            "skip": st.column_config.CheckboxColumn("Skip"),
        },
    )

    if year_kind != "summarized":
        _reconcile(data_home, year, committed, edited, shown_ids, needs_attention_only)

    _render_row_actions(data_home, committed, year)


def _build_display_df(committed: list[Transaction], needs_attention_only: bool):
    rows: dict[str, dict] = {}
    for i, t in enumerate(committed):
        if needs_attention_only and not _needs_attention(t):
            continue
        rows[f"c{i}"] = _row_dict("committed", t, skip=False)
    for i, s in enumerate(st.session_state.staged):
        if needs_attention_only and not _needs_attention(s.transaction):
            continue
        rows[f"s{i}"] = _row_dict("staged", s.transaction, s.skip)
    df = pd.DataFrame.from_dict(rows, orient="index", columns=COLUMNS)
    # A plain object column of datetime.date can segfault pyarrow's Arrow conversion in
    # st.data_editor; force a proper datetime64 dtype instead.
    df["date"] = pd.to_datetime(df["date"])
    return df, set(rows.keys())


def _reconcile(
    data_home, year, committed, edited: pd.DataFrame, shown_ids: set, needs_attention_only: bool
) -> None:
    edited_ids = set(edited.index)
    deleted_ids = shown_ids - edited_ids

    final_committed: list[Transaction] = []
    for i, t_orig in enumerate(committed):
        rid = f"c{i}"
        if needs_attention_only and rid not in shown_ids:
            final_committed.append(t_orig)  # hidden by filter, untouched
            continue
        if rid in deleted_ids:
            continue
        if rid in edited.index:
            final_committed.append(_row_to_transaction(edited.loc[rid].to_dict()))
        else:
            final_committed.append(t_orig)

    final_staged: list[StagedRow] = []
    for i, s_orig in enumerate(st.session_state.staged):
        rid = f"s{i}"
        if needs_attention_only and rid not in shown_ids:
            final_staged.append(s_orig)
            continue
        if rid in deleted_ids:
            continue
        if rid in edited.index:
            row = edited.loc[rid].to_dict()
            final_staged.append(
                StagedRow(transaction=_row_to_transaction(row), skip=bool(row.get("skip", False)))
            )
        else:
            final_staged.append(s_orig)

    new_ids = edited_ids - shown_ids
    for rid in new_ids:
        row = edited.loc[rid].to_dict()
        final_staged.append(
            StagedRow(transaction=_row_to_transaction(row), skip=bool(row.get("skip", False)))
        )

    st.session_state.staged = final_staged

    same_year = [t for t in final_committed if t.date.year == year]
    by_other_year: dict[int, list[Transaction]] = {}
    for t in final_committed:
        if t.date.year != year:
            by_other_year.setdefault(t.date.year, []).append(t)

    year_store.save_transactions(data_home, year, same_year)
    for other_year, rows in by_other_year.items():
        year_store.append_transactions(data_home, other_year, rows)


def _render_import_section(data_home, profiles: dict, rules: list[CategoryRule]) -> None:
    with st.expander("Import files", expanded=False):
        if not profiles:
            st.info("No bank profiles configured yet — add one on the Profiles screen.")
            return
        uploaded = st.file_uploader(
            "Add CSV files",
            type="csv",
            accept_multiple_files=True,
            key=f"uploader_{st.session_state.grid_version}",
        )
        if not uploaded:
            return
        choices = {}
        for f in uploaded:
            choices[f.name] = st.selectbox(
                f"Profile for {f.name}",
                list(profiles.keys()),
                key=f"profile_{f.name}_{st.session_state.grid_version}",
            )
        if st.button("Stage files"):
            errors = []
            for f in uploaded:
                profile = profiles[choices[f.name]]
                result = parse_csv_bytes(f.getvalue(), profile)
                staged_new = [StagedRow(transaction=t) for t in result.rows]
                categorize_rows(staged_new, rules)
                st.session_state.staged.extend(staged_new)
                errors.extend(result.errors)
            st.session_state.grid_version += 1
            if errors:
                st.session_state["last_import_errors"] = [
                    f"line {e.line_number}: {e.message}" for e in errors
                ]
            st.rerun()

    if st.session_state.get("last_import_errors"):
        st.error(f"{len(st.session_state['last_import_errors'])} row(s) failed to parse and were skipped:")
        for msg in st.session_state["last_import_errors"][:20]:
            st.caption(msg)
        st.session_state["last_import_errors"] = None


def _render_commit_section(data_home) -> None:
    staged = st.session_state.staged
    if not staged:
        return
    to_commit = [s.transaction for s in staged if not s.skip]
    skipped_count = len(staged) - len(to_commit)
    st.write(f"**{len(staged)} staged row(s)** — {len(to_commit)} to commit, {skipped_count} marked skip.")

    if st.session_state.pending_closed_years:
        closed_years = st.session_state.pending_closed_years
        st.warning(f"Target year(s) {', '.join(map(str, closed_years))} are closed.")
        col1, col2 = st.columns(2)
        if col1.button("Reopen and commit"):
            for y in closed_years:
                year_store.reopen_year(data_home, y)
            year_store.commit_transactions(data_home, to_commit)
            st.session_state.staged = [s for s in staged if s.skip]
            st.session_state.pending_closed_years = None
            st.rerun()
        if col2.button("Cancel commit"):
            st.session_state.pending_closed_years = None
            st.rerun()
        return

    if st.button(f"Commit {len(to_commit)} row(s)"):
        closed_years = sorted(
            {t.date.year for t in to_commit if year_store.year_state(data_home, t.date.year) == "summarized"}
        )
        if closed_years:
            st.session_state.pending_closed_years = closed_years
            st.rerun()
        else:
            year_store.commit_transactions(data_home, to_commit)
            st.session_state.staged = [s for s in staged if s.skip]
            st.rerun()


def _render_row_actions(data_home, committed: list[Transaction], year: int) -> None:
    options = {f"c{i}": t for i, t in enumerate(committed)}
    options.update({f"s{i}": s.transaction for i, s in enumerate(st.session_state.staged)})
    if not options:
        return

    with st.expander("Row actions (split / make a rule)", expanded=False):
        labels = {
            rid: f"[{rid[0]}] {t.date} {t.amount} {t.rawDescription[:40]}" for rid, t in options.items()
        }
        selected = st.selectbox("Row", list(labels.keys()), format_func=lambda rid: labels[rid])
        assert selected is not None  # a non-empty options list always yields a selection
        col1, col2 = st.columns(2)
        if col1.button("Split row"):
            _open_split_dialog(data_home, selected, year)
        if col2.button("Make a rule from this row"):
            _open_make_rule_dialog(data_home, selected)


@st.dialog("Split row")
def _open_split_dialog(data_home, rid: str, year: int) -> None:
    is_committed = rid.startswith("c")
    idx = int(rid[1:])
    orig = (
        year_store.load_transactions(data_home, year)[idx]
        if is_committed
        else st.session_state.staged[idx].transaction
    )

    st.write(f"Original: {orig.date} {orig.amount} {orig.currency} — {orig.rawDescription}")
    remaining = st.number_input("Remaining amount on original row", value=float(orig.amount), format="%.2f")
    split_amount = st.number_input("Split-off amount", value=0.0, format="%.2f")
    split_category = st.text_input("Split-off category")

    if st.button("Confirm split"):
        new_row = Transaction(
            date=orig.date,
            amount=Decimal(str(round(split_amount, 2))),
            currency=orig.currency,
            type=orig.type,
            rawDescription=orig.rawDescription,
            category=split_category,
            notes=orig.notes,
        )
        orig.amount = Decimal(str(round(remaining, 2)))
        if is_committed:
            rows = year_store.load_transactions(data_home, year)
            rows[idx] = orig
            rows.append(new_row)
            year_store.save_transactions(data_home, year, rows)
        else:
            st.session_state.staged[idx].transaction = orig
            st.session_state.staged.append(StagedRow(transaction=new_row))
        st.session_state.grid_version += 1
        st.rerun()


@st.dialog("Make a rule from this row")
def _open_make_rule_dialog(data_home, rid: str) -> None:
    is_committed = rid.startswith("c")
    idx = int(rid[1:])
    orig = (
        year_store.load_transactions(data_home, Date.today().year)[idx]
        if is_committed
        else st.session_state.staged[idx].transaction
    )

    pattern = st.text_input("Pattern", value=normalize(orig.rawDescription))
    type_ = st.selectbox("Type", ["expense", "income", "skip"], index=0 if orig.type == "expense" else 1)
    assert type_ is not None  # a non-empty options list always yields a selection
    category = None
    if type_ != "skip":
        category = st.text_input("Category", value=orig.category)

    staged_descs = [s.transaction.rawDescription for s in st.session_state.staged]
    st.caption(f"Matches {count_matches(pattern, staged_descs)} staged row(s).")

    scope = st.radio("Apply to", ["These staged rows only", "Save the rule (future imports too)"])

    if st.button("Apply"):
        rule = CategoryRule(
            pattern=pattern.strip(), type=cast(Literal["income", "expense", "skip"], type_), category=category
        )
        categorize_rows(st.session_state.staged, [rule])
        if scope == "Save the rule (future imports too)":
            all_rules = config_store.load_rules(data_home)
            all_rules.append(rule)
            config_store.save_rules(data_home, all_rules)
        st.rerun()
