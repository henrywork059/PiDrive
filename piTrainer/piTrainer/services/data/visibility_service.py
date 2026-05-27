from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd

HIDDEN_FLAG_KEYS = (
    'hidden_from_training',
    'piTrainer_hidden',
    'pitrainer_hidden',
    'excluded_from_training',
    'exclude_from_training',
    'deleted_by_pitrainer',
    'pitrainer_delete_hidden',
    'is_deleted',
    'deleted',
    'hidden',
)

TRACE_FLAG_VALUES = {
    '1',
    'true',
    'yes',
    'y',
    'on',
    'hidden',
    'deleted',
    'exclude',
    'excluded',
    'training_hidden',
}


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def truthy_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if not isinstance(value, (dict, list, tuple, set)):
        try:
            if bool(pd.isna(value)):
                return False
        except (TypeError, ValueError):
            pass
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    return text in TRACE_FLAG_VALUES


SYNTHETIC_FLAG_KEYS = (
    'is_synthetic',
    'synthetic',
    'created_by_preprocess',
    'pitrainer_synthetic',
)


def is_synthetic_record(record: dict[str, Any]) -> bool:
    """Return True for generated/preprocessed rows that should be hidden from Data review by default.

    Synthetic rows are valid training/validation examples, but they are derived
    from real source frames. The Data page is the raw-label editor, so it should
    normally display the original source rows and redirect synthetic review rows
    back to their source frame.
    """
    if not isinstance(record, dict):
        return False
    for key in SYNTHETIC_FLAG_KEYS:
        if key in record and truthy_flag(record.get(key)):
            return True
    frame_id = str(record.get('frame_id', '') or '').strip().lower()
    if frame_id.startswith('s_'):
        return True
    variant = str(record.get('synthetic_variant', record.get('aug_variant', '')) or '').strip().lower()
    return bool(variant and variant not in {'original', 'none', 'false', '0'})


def synthetic_row_mask(df: pd.DataFrame) -> pd.Series:
    if df is None or df.empty:
        return pd.Series([], dtype=bool)
    mask = pd.Series([False] * len(df), index=df.index)
    for key in SYNTHETIC_FLAG_KEYS:
        if key in df.columns:
            mask |= df[key].map(truthy_flag).fillna(False).astype(bool)
    if 'frame_id' in df.columns:
        mask |= df['frame_id'].fillna('').astype(str).str.strip().str.lower().str.startswith('s_')
    variant_column = 'synthetic_variant' if 'synthetic_variant' in df.columns else ('aug_variant' if 'aug_variant' in df.columns else '')
    if variant_column:
        variants = df[variant_column].fillna('').astype(str).str.strip().str.lower()
        mask |= variants.ne('') & ~variants.isin(['original', 'none', 'false', '0'])
    return mask


def without_synthetic_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows intended for Data-page review/editing, hiding generated copies by default."""
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()
    mask = synthetic_row_mask(df)
    if mask.empty or not mask.any():
        return df.copy()
    return df[~mask].copy().reset_index(drop=True)


def mapping_from_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}
    return {}


def _iter_record_scopes(record: dict[str, Any]):
    yield record
    training_label = record.get('training_label')
    if isinstance(training_label, dict):
        yield training_label


def is_record_hidden(record: dict[str, Any]) -> bool:
    """Return True when a source JSONL record has been hidden from training.

    Hidden records are kept in labels.jsonl/records.jsonl for traceability, but
    must not be loaded into active dataframes, preprocessing, training, or
    validation flows.
    """
    if not isinstance(record, dict):
        return False
    for scope in _iter_record_scopes(record):
        for key in HIDDEN_FLAG_KEYS:
            if key in scope and truthy_flag(scope.get(key)):
                return True
    return False


def mark_record_hidden(record: dict[str, Any], *, hidden_at_utc: str | None = None, reason: str = 'user_hidden_delete') -> dict[str, Any]:
    """Add traceable hide flags without removing the JSONL row or image file."""
    hidden_at = hidden_at_utc or utc_timestamp()
    trace = {
        'hidden_from_training': True,
        'piTrainer_hidden': True,
        'deleted_by_pitrainer': True,
        'hidden_reason': reason,
        'hidden_at_utc': hidden_at,
        'hidden_source': 'piTrainer',
        'hidden_action': 'soft_delete_keep_files',
    }
    record.update(trace)
    training_label = record.get('training_label')
    if isinstance(training_label, dict):
        training_label.update(trace)
    return record


def hidden_row_mask(df: pd.DataFrame) -> pd.Series:
    if df is None or df.empty:
        return pd.Series([], dtype=bool)
    mask = pd.Series([False] * len(df), index=df.index)
    for key in HIDDEN_FLAG_KEYS:
        if key in df.columns:
            mask |= df[key].map(truthy_flag).fillna(False).astype(bool)
    if 'training_label' in df.columns:
        mask |= df['training_label'].map(lambda value: is_record_hidden(mapping_from_value(value))).fillna(False).astype(bool)
    return mask


def without_hidden_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()
    mask = hidden_row_mask(df)
    if mask.empty or not mask.any():
        return df.copy()
    return df[~mask].copy().reset_index(drop=True)
