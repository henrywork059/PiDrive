from __future__ import annotations
import random
import streamlit as st
import pandas as pd

def render_image_preview(df: pd.DataFrame):
    st.markdown("### Random image preview")
    if df.empty:
        st.info("No images to preview.")
        return
    n_preview = st.slider("How many images", 1, 12, 6)
    idxs = random.sample(range(len(df)), k=min(n_preview, len(df)))
    cols = st.columns(min(3, n_preview))
    for i, idx in enumerate(idxs):
        r = df.iloc[idx]
        col = cols[i % len(cols)]
        caption = f"{r.get('session','')}  steer={float(r.get('steering',0.0)):+.2f} thr={float(r.get('throttle',0.0)):.2f}"
        col.image(r["abs_image"], caption=caption, use_container_width=True)
