from __future__ import annotations
from pathlib import Path
import streamlit as st
import pandas as pd
from ..core.data_io import load_records_jsonl, basic_stats
from ..panels.data.session_selector import render_session_selector
from ..panels.data.preview_table import render_preview_table
from ..panels.data.image_preview import render_image_preview

@st.cache_data(show_spinner=False)
def _cached_load(records_root: str, sessions: tuple[str, ...]) -> pd.DataFrame:
    return load_records_jsonl(Path(records_root), list(sessions))

def render(state: dict):
    st.subheader("📁 Data")
    records_root = Path(state["records_root"])
    chosen_sessions = render_session_selector(records_root, state)

    if not chosen_sessions:
        st.warning("Select at least 1 session.")
        return

    df = _cached_load(str(records_root), tuple(chosen_sessions))

    # Optional filter
    tc = state.get("train_cfg")
    if tc and tc.only_manual and "mode" in df.columns:
        df = df[df["mode"].astype(str) == "manual"].copy()

    state["df"] = df

    stats = basic_stats(df)
    st.write(f"Loaded **{stats.get('n',0)}** frames from **{stats.get('sessions',0)}** session(s).")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Steer mean", f"{stats.get('steering_mean',0.0):+.3f}")
    c2.metric("Steer std", f"{stats.get('steering_std',0.0):.3f}")
    c3.metric("Thr mean", f"{stats.get('throttle_mean',0.0):+.3f}")
    c4.metric("Thr std", f"{stats.get('throttle_std',0.0):.3f}")

    with st.expander("Preview table", expanded=True):
        render_preview_table(df)

    render_image_preview(df)
