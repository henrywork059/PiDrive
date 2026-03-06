from __future__ import annotations
from pathlib import Path
import streamlit as st
import pandas as pd
from ...core.utils import safe_filename
from ...core.exporter import save_keras, export_tflite
from ...core.dataset import make_tf_dataset

def render_export_controls(state: dict, out_dir: Path, df_train: pd.DataFrame, tc):
    model = state.get("model", None)
    if model is None:
        st.info("Train a model first (Train page).")
        return

    base_name = st.text_input("Model name", value="picar_model")
    base_name = safe_filename(base_name, "picar_model")
    keras_path = out_dir / f"{base_name}.keras"
    tflite_path = out_dir / f"{base_name}.tflite"

    quantize = st.checkbox("Quantize TFLite", value=False)

    c1, c2 = st.columns(2)
    if c1.button("Save .keras"):
        save_keras(model, keras_path)
        st.success(f"Saved: {keras_path}")

    if c2.button("Export .tflite"):
        rep_ds = None
        if quantize and not df_train.empty:
            rep = df_train.sample(min(len(df_train), 2000), random_state=1)
            rep_ds = make_tf_dataset(rep, tc.img_h, tc.img_w, tc.batch, shuffle=False, augment=False)
        export_tflite(model, tflite_path, quantize=quantize, representative_ds=rep_ds)
        st.success(f"Exported: {tflite_path}")

    st.caption("Tip: Train + export on your PC, then copy the .tflite to the PiCar for inference.")
