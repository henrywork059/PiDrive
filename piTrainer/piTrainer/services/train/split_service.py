from __future__ import annotations

import os

import numpy as np
import pandas as pd

from ...app_state import TrainConfig


def _identity_text(value: object) -> str:
    """Ignore missing/blank metadata rather than grouping every blank row."""
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"", "nan", "none", "<na>"} else text


def _source_group_ids(df: pd.DataFrame, *, by_session: bool = False) -> list[int]:
    """Find connected rows sharing an image path or a session-scoped source frame.

    Synthetic rows keep the source_frame_id in PiSD/piTrainer preprocessing. They
    often reuse the source image path, but these two identifiers are both checked
    so saved augmentation variants cannot leak into a different partition.
    """
    count = len(df)
    parent = list(range(count))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(a: int, b: int) -> None:
        parent[find(a)] = find(b)

    cols = {
        name: df[name].tolist() if name in df.columns else [None] * count
        for name in ("session", "abs_image", "source_frame_id", "frame_id", "frame_number")
    }
    first_seen: dict[tuple[str, ...], int] = {}
    for index in range(count):
        session = _identity_text(cols["session"][index])
        image_text = _identity_text(cols["abs_image"][index])
        image = os.path.normcase(os.path.normpath(image_text.replace("\\", "/"))) if image_text else ""
        source = (
            _identity_text(cols["source_frame_id"][index])
            or _identity_text(cols["frame_id"][index])
            or _identity_text(cols["frame_number"][index])
        )
        keys: list[tuple[str, ...]] = []
        if image:
            keys.append(("image", image))
        if source:
            keys.append(("source", session, source))
        if by_session and session:
            keys.append(("session", session))
        for key in keys:
            previous = first_seen.setdefault(key, index)
            union(index, previous)
    return [find(i) for i in range(count)]


def _group_partition(df: pd.DataFrame, val_ratio: float, *, seed: int | None = None,
                     sequential: bool = False, by_session: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return df.copy(), df.copy()

    group_ids = _source_group_ids(df, by_session=by_session)
    group_sizes: dict[int, int] = {}
    for group in group_ids:
        group_sizes[group] = group_sizes.get(group, 0) + 1
    ordered_groups = list(group_sizes)
    if len(ordered_groups) < 2:
        return df.reset_index(drop=True).copy(), df.iloc[0:0].copy().reset_index(drop=True)

    # The order of groups is the first occurrence of their source frame. When
    # synthetic rows are appended after original frames, sequential mode still
    # preserves the original frame ordering instead of splitting a source family.
    if sequential:
        candidates = list(reversed(ordered_groups))
    else:
        candidates = ordered_groups.copy()
        np.random.default_rng(seed).shuffle(candidates)

    desired = max(1, int(len(df) * float(val_ratio)))
    validation_groups: set[int] = set()
    selected_rows = 0
    for group in candidates[:-1]:  # Keep at least one complete source group for training.
        validation_groups.add(group)
        selected_rows += group_sizes[group]
        if selected_rows >= desired:
            break

    validation_mask = np.fromiter((g in validation_groups for g in group_ids), dtype=bool, count=len(df))
    train_df = df.iloc[np.flatnonzero(~validation_mask)].copy()
    val_df = df.iloc[np.flatnonzero(validation_mask)].copy()
    if not sequential:
        # Keep the existing randomly ordered training/validation row experience.
        train_df = train_df.sample(frac=1.0, random_state=seed)
        val_df = val_df.sample(frac=1.0, random_state=seed)
    return train_df.reset_index(drop=True), val_df.reset_index(drop=True)


def split_by_session(df: pd.DataFrame, val_ratio: float, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty or "session" not in df.columns:
        return df.copy(), df.iloc[0:0].copy()
    sessions = df["session"].dropna().astype(str).unique().tolist()
    if len(sessions) <= 1:
        return split_by_rows(df, val_ratio, seed)
    # Keep sessions together, including sessions referencing the same image.
    return _group_partition(df, val_ratio, seed=seed, by_session=True)


def split_by_rows(df: pd.DataFrame, val_ratio: float, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    return _group_partition(df, val_ratio, seed=seed)


def split_by_sequential_rows(df: pd.DataFrame, val_ratio: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    return _group_partition(df, val_ratio, sequential=True)


def split_dataframe(df: pd.DataFrame, config: TrainConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    split_mode = getattr(config, 'split_mode', 'Random rows') or 'Random rows'
    seed = int(getattr(config, 'seed', 42) or 42)
    if split_mode == 'Random rows':
        return split_by_rows(df, config.val_ratio, seed)
    if split_mode == 'Sequential rows':
        return split_by_sequential_rows(df, config.val_ratio)
    if split_mode == 'By session' or getattr(config, 'session_split', False):
        return split_by_session(df, config.val_ratio, seed)
    return split_by_rows(df, config.val_ratio, seed)
