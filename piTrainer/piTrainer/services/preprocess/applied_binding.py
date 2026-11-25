"""Capture applied preprocessing separately from editable recipe controls."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from ..train.experiment_service import preprocessing_hash
from ..task_outputs import confirmed_dataset_paths


def dataset_fingerprint(df) -> str | None:
    # Ordered active metadata only; this does not hash image bytes.
    if df is None or df.empty:
        return None
    try:
        payload = df.to_json(orient="split", index=False, date_format="iso",
                             double_precision=15, force_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
    except (TypeError, ValueError, OverflowError):
        return None


class AppliedPreprocessBinding:
    def __init__(self):
        self.clear()

    def clear(self):
        self._fingerprint = None
        self._recipe = None
        self._saved_path = None

    def capture(self, df, recipe):
        self.clear()
        self._fingerprint = dataset_fingerprint(df)
        if self._fingerprint and recipe:
            self._recipe = copy.deepcopy(recipe)

    def matching_recipe(self, df):
        fingerprint = dataset_fingerprint(df) if self._recipe else None
        if fingerprint and fingerprint == self._fingerprint:
            return copy.deepcopy(self._recipe)
        return None

    def note_saved(self, df, recipe, folder):
        matched = self.matching_recipe(df)
        if matched is None or preprocessing_hash(matched) != preprocessing_hash(recipe):
            return
        try:
            confirmed_dataset_paths(folder)
        except (OSError, RuntimeError, ValueError):
            return
        self._saved_path = str(Path(folder).expanduser().resolve())

    def training_context(self, df):
        recipe = self.matching_recipe(df)
        if recipe is None:
            return None, ""
        path = self._saved_path or ""
        if path:
            try:
                confirmed_dataset_paths(path)
            except (OSError, RuntimeError, ValueError):
                path = ""
        return recipe, path
