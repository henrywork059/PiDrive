from __future__ import annotations

import numpy as np
import pandas as pd

from ...app_state import TrainConfig


def split_by_session(df: pd.DataFrame, val_ratio: float, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty or "session" not in df.columns:
        return df.copy(), df.iloc[0:0].copy()
    sessions = sorted(df["session"].dropna().astype(str).unique().tolist())
    if len(sessions) <= 1:
        return split_by_rows(df, val_ratio, seed)
    rng = np.random.default_rng(seed)
    rng.shuffle(sessions)
    n_val = max(1, int(len(sessions) * float(val_ratio)))
    val_sessions = set(sessions[:n_val])
    train_df = df[~df["session"].isin(val_sessions)].copy()
    val_df = df[df["session"].isin(val_sessions)].copy()
    if train_df.empty:
        train_df = val_df.copy(); val_df = val_df.iloc[0:0].copy()
    return train_df.reset_index(drop=True), val_df.reset_index(drop=True)


def split_by_rows(df: pd.DataFrame, val_ratio: float, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return df.copy(), df.copy()
    shuffled = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    n_val = max(1, int(len(shuffled) * float(val_ratio))) if len(shuffled) > 1 else 0
    val_df = shuffled.iloc[:n_val].copy(); train_df = shuffled.iloc[n_val:].copy()
    if train_df.empty:
        train_df = shuffled.copy(); val_df = shuffled.iloc[0:0].copy()
    return train_df.reset_index(drop=True), val_df.reset_index(drop=True)


def split_by_sequential_rows(df: pd.DataFrame, val_ratio: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return df.copy(), df.copy()
    n_val = max(1, int(len(df) * float(val_ratio))) if len(df) > 1 else 0
    if n_val <= 0:
        return df.copy().reset_index(drop=True), df.iloc[0:0].copy()
    split_at = max(1, len(df) - n_val)
    train_df = df.iloc[:split_at].copy()
    val_df = df.iloc[split_at:].copy()
    if train_df.empty:
        train_df = df.copy(); val_df = df.iloc[0:0].copy()
    return train_df.reset_index(drop=True), val_df.reset_index(drop=True)


def split_dataframe(df: pd.DataFrame, config: TrainConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    split_mode = getattr(config, 'split_mode', 'By session')
    seed = int(getattr(config, 'seed', 42) or 42)
    if split_mode == 'Random rows':
        return split_by_rows(df, config.val_ratio, seed)
    if split_mode == 'Sequential rows':
        return split_by_sequential_rows(df, config.val_ratio)
    if getattr(config, 'session_split', True):
        return split_by_session(df, config.val_ratio, seed)
    return split_by_rows(df, config.val_ratio, seed)
