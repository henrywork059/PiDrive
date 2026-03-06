from __future__ import annotations
import streamlit as st
import pandas as pd

def render_metrics(history: dict | None):
    st.markdown("### Training curves")
    if not history:
        st.info("No training history yet.")
        return
    hist = pd.DataFrame(history)
    cols1 = [c for c in ["loss", "val_loss"] if c in hist.columns]
    if cols1:
        st.line_chart(hist[cols1])
    cols2 = [c for c in hist.columns if "mae" in c]
    if cols2:
        st.line_chart(hist[cols2])
