from __future__ import annotations
from pathlib import Path
import streamlit as st
import pandas as pd
from ..panels.export.save_controls import render_export_controls

def render(state: dict):
    st.subheader("📦 Export")
    out_dir = Path(state["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    df_train: pd.DataFrame = state.get("df_train", pd.DataFrame())
    tc = state.get("train_cfg")

    render_export_controls(state, out_dir, df_train, tc)
