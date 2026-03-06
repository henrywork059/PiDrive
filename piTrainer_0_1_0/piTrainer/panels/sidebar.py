from __future__ import annotations
from pathlib import Path
import streamlit as st
from ..core.utils import expand_path
from ..core.config import TrainConfig

PAGES = [
    ("Data", "📁"),
    ("Train", "🧠"),
    ("Export", "📦"),
]

def render_sidebar(state: dict):
    st.sidebar.title("PiCar Trainer (PC)")
    page_names = [f"{icon} {name}" for name, icon in PAGES]
    default_idx = int(state.get("page_idx", 0))
    sel = st.sidebar.radio("Pages", page_names, index=min(default_idx, len(page_names)-1))
    page_idx = page_names.index(sel)
    state["page_idx"] = page_idx

    st.sidebar.divider()
    st.sidebar.subheader("Paths")
    records_root_str = st.sidebar.text_input("records root folder", value=str(state.get("records_root", Path('data/records').resolve())))
    out_dir_str = st.sidebar.text_input("output folder", value=str(state.get("out_dir", Path('trainer_out').resolve())))

    state["records_root"] = str(expand_path(records_root_str))
    state["out_dir"] = str(expand_path(out_dir_str))

    st.sidebar.divider()
    st.sidebar.subheader("Train defaults")
    tc: TrainConfig = state.get("train_cfg", TrainConfig())

    tc.img_h = int(st.sidebar.number_input("Image height", min_value=48, max_value=480, value=int(tc.img_h), step=8))
    tc.img_w = int(st.sidebar.number_input("Image width", min_value=64, max_value=640, value=int(tc.img_w), step=8))
    tc.batch = int(st.sidebar.number_input("Batch size", min_value=4, max_value=256, value=int(tc.batch), step=4))
    tc.epochs = int(st.sidebar.number_input("Epochs", min_value=1, max_value=200, value=int(tc.epochs), step=1))
    tc.lr = float(st.sidebar.number_input("Learning rate", min_value=1e-6, max_value=1e-2, value=float(tc.lr), format="%.6f"))
    tc.val_ratio = float(st.sidebar.slider("Validation ratio", 0.05, 0.5, float(tc.val_ratio), 0.05))
    tc.only_manual = bool(st.sidebar.checkbox("Use only mode == manual", value=bool(tc.only_manual)))
    tc.augment = bool(st.sidebar.checkbox("Augment images", value=bool(tc.augment)))
    tc.session_split = bool(st.sidebar.checkbox("Split by session (recommended)", value=bool(tc.session_split)))

    state["train_cfg"] = tc

    return PAGES[page_idx][0]
