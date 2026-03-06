from __future__ import annotations
import streamlit as st
from pathlib import Path

from .panels.sidebar import render_sidebar
from .pages import data as page_data
from .pages import train as page_train
from .pages import export as page_export
from .core.config import TrainConfig

def init_state():
    if "app_state" not in st.session_state:
        st.session_state.app_state = {
            "page_idx": 0,
            "records_root": str(Path("data/records").resolve()),
            "out_dir": str(Path("trainer_out").resolve()),
            "train_cfg": TrainConfig(),
            "df": None,
            "df_train": None,
            "df_val": None,
            "model": None,
            "history": None,
            "chosen_sessions": [],
        }

def main():
    st.set_page_config(page_title="PiCar Trainer (PC)", layout="wide")
    init_state()
    state = st.session_state.app_state

    st.title("🚗 PiCar Training App (runs on your PC)")
    page = render_sidebar(state)

    if page == "Data":
        page_data.render(state)
    elif page == "Train":
        page_train.render(state)
    elif page == "Export":
        page_export.render(state)

    # small footer
    st.caption("Data format: data/records/<session>/{records.jsonl, images/}. Train on PC, export .tflite for PiCar.")

if __name__ == "__main__":
    main()
