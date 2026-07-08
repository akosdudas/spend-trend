"""Bank profiles: hand-edited JSON + Test parse. See specs/07-ux.md §2.4, specs/03-import-and-profiles.md."""

from __future__ import annotations

import json

import streamlit as st

from src.domain.models import BankProfile
from src.importer.parse import parse_csv_bytes
from src.storage import config_store

PROFILES_FILE = "bank-profiles.json"


def render(data_home) -> None:
    st.header("Profiles")
    profiles = config_store.load_bank_profiles(data_home)
    st.write(f"{len(profiles)} profile(s) configured.")

    path = data_home / "config" / PROFILES_FILE
    current_text = path.read_text(encoding="utf-8") if path.exists() else "[]"
    edited_text = st.text_area("bank-profiles.json", value=current_text, height=320)
    if st.button("Save profiles"):
        try:
            raw = json.loads(edited_text)
            new_profiles = {p["name"]: BankProfile(**p) for p in raw}
        except Exception as exc:  # noqa: BLE001 - surfaced to the user, not a programming error
            st.error(f"Invalid profiles JSON: {exc}")
        else:
            config_store.save_bank_profiles(data_home, new_profiles)
            st.success("Saved.")
            st.rerun()

    st.subheader("Test parse")
    if not profiles:
        st.info("Add a profile above to test-parse a sample CSV against it.")
        return

    profile_name = st.selectbox("Profile", list(profiles.keys()))
    assert profile_name is not None  # a non-empty options list always yields a selection
    sample = st.file_uploader("Sample CSV", type="csv")
    if sample is None:
        return

    result = parse_csv_bytes(sample.getvalue(), profiles[profile_name])
    st.write(f"{len(result.rows)} row(s) parsed, {len(result.errors)} error(s).")
    preview = [
        {
            "date": r.date.isoformat(),
            "amount": str(r.amount),
            "currency": r.currency,
            "type": r.type,
            "rawDescription": r.rawDescription,
        }
        for r in result.rows[:20]
    ]
    st.dataframe(preview, use_container_width=True, hide_index=True)
    for e in result.errors[:20]:
        st.caption(f"line {e.line_number}: {e.message}")
