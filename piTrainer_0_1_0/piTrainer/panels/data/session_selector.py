from __future__ import annotations
from pathlib import Path
import streamlit as st
from ...core.data_io import list_sessions

def render_session_selector(records_root: Path, state: dict):
    sessions = list_sessions(records_root)
    st.caption(f"Found {len(sessions)} session(s)")
    chosen = st.multiselect("Select sessions", sessions, default=sessions if not state.get("chosen_sessions") else state["chosen_sessions"])
    state["chosen_sessions"] = chosen
    return chosen
