from __future__ import annotations
import streamlit as st
from ...core.config import TrainConfig

def render_hyperparams(tc: TrainConfig):
    st.markdown("### Current hyperparameters")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Input", f"{tc.img_h}×{tc.img_w}")
    c2.metric("Batch", str(tc.batch))
    c3.metric("Epochs", str(tc.epochs))
    c4.metric("LR", f"{tc.lr:.6f}")

    st.caption("Change these from the left sidebar.")
