from __future__ import annotations
import streamlit as st
import pandas as pd
from ..core.dataset import session_split
from ..panels.train.hyperparams import render_hyperparams
from ..panels.train.train_controls import render_train_controls
from ..panels.train.metrics_plot import render_metrics

def render(state: dict):
    st.subheader("🧠 Train")

    df: pd.DataFrame = state.get("df", pd.DataFrame())
    if df.empty:
        st.info("Go to Data page first and load sessions.")
        return

    tc = state.get("train_cfg")
    render_hyperparams(tc)

    # Split
    if tc.session_split:
        df_train, df_val = session_split(df, tc.val_ratio, seed=42)
    else:
        df_shuf = df.sample(frac=1.0, random_state=42).reset_index(drop=True)
        n_val = max(1, int(len(df_shuf) * float(tc.val_ratio)))
        df_val = df_shuf.iloc[:n_val].copy()
        df_train = df_shuf.iloc[n_val:].copy()

    state["df_train"] = df_train
    state["df_val"] = df_val

    st.divider()
    render_train_controls(df_train, df_val, tc, state)

    st.divider()
    render_metrics(state.get("history"))
