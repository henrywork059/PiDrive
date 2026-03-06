from __future__ import annotations
import streamlit as st
import pandas as pd

def render_preview_table(df: pd.DataFrame):
    show_cols = [c for c in ["session", "frame_id", "ts", "steering", "throttle", "mode", "abs_image"] if c in df.columns]
    st.dataframe(df[show_cols].head(300), use_container_width=True)
