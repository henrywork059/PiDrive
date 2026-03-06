from __future__ import annotations
import streamlit as st
import pandas as pd
from ...core.dataset import make_tf_dataset
from ...core.model import build_small_cnn, compile_model

def render_train_controls(df_train: pd.DataFrame, df_val: pd.DataFrame, tc, state: dict):
    if df_train.empty or df_val.empty:
        st.warning("Not enough data for training/validation split.")
        return

    st.write(f"Train: **{len(df_train)}**  |  Val: **{len(df_val)}**")

    if st.button("Start training", type="primary"):
        with st.spinner("Training... (TensorFlow)"):
            train_ds = make_tf_dataset(df_train, tc.img_h, tc.img_w, tc.batch, shuffle=True, augment=tc.augment)
            val_ds = make_tf_dataset(df_val, tc.img_h, tc.img_w, tc.batch, shuffle=False, augment=False)

            model = build_small_cnn(tc.img_h, tc.img_w)
            compile_model(model, tc.lr)

            import tensorflow as tf
            callbacks = [
                tf.keras.callbacks.EarlyStopping(patience=3, restore_best_weights=True, monitor="val_loss")
            ]
            history = model.fit(train_ds, validation_data=val_ds, epochs=int(tc.epochs), callbacks=callbacks, verbose=1)

            state["model"] = model
            state["history"] = history.history
            st.success("Training finished. Go to Export page to save / convert.")

    if state.get("model") is not None:
        st.info("Model is ready in memory.")
