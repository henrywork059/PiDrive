"""Local R51 preprocessing receipts; metadata only."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ..train.experiment_service import MAX_RECORD_BYTES, RUN_ID_PATTERN, preprocessing_hash


def source_sessions(df):
    if df is None or "session" not in df.columns:
        return []
    pairs = set()
    columns = ["session"] + (["session_dir"] if "session_dir" in df.columns else [])
    for row in df[columns].fillna("").itertuples(index=False, name=None):
        name = str(row[0]).strip()
        if name:
            pairs.add((name, str(row[1]).strip() if len(row) > 1 else ""))
    return [{"session": name, "session_dir": directory or None}
            for name, directory in sorted(pairs)]


def save_preprocessing_receipt(root, recipe, fingerprint, source_df, selected_sessions):
    run_id = uuid4().hex
    record = {
        "schema_version": 1,
        "preprocessing_run_id": run_id,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "preprocessing_sha256": preprocessing_hash(recipe),
        "active_metadata_sha256": fingerprint,
        "source_sessions": source_sessions(source_df),
        "selected_sessions": [str(name) for name in selected_sessions],
    }
    data = (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")
    if len(data) > MAX_RECORD_BYTES:
        raise ValueError("Preprocessing receipt exceeds metadata size limit.")
    path = Path(root).expanduser().resolve() / "preprocessing_runs" / (run_id + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("xb")
    try:
        with handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return {"run_id": run_id, "receipt_path": str(path),
            "receipt_sha256": hashlib.sha256(data).hexdigest(),
            "active_metadata_sha256": fingerprint}


def verified_preprocessing_reference(reference, recipe_hash, selected_sessions):
    """Missing, changed or unassociated local receipts remain unknown."""
    if not isinstance(reference, dict) or not recipe_hash:
        return None
    run_id = reference.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID_PATTERN.fullmatch(run_id):
        return None
    try:
        path = Path(reference["receipt_path"])
        if not path.is_absolute() or path.name != run_id + ".json" or path.parent.name != "preprocessing_runs":
            return None
        with path.open("rb") as handle:
            data = handle.read(MAX_RECORD_BYTES + 1)
        if len(data) > MAX_RECORD_BYTES or hashlib.sha256(data).hexdigest() != reference.get("receipt_sha256"):
            return None
        record = json.loads(data.decode("utf-8"))
        fingerprint = reference.get("active_metadata_sha256")
        if (not isinstance(record, dict) or record.get("schema_version") != 1
                or record.get("preprocessing_run_id") != run_id
                or record.get("preprocessing_sha256") != recipe_hash
                or not isinstance(fingerprint, str) or len(fingerprint) != 64
                or record.get("active_metadata_sha256") != fingerprint
                or not record.get("completed_at_utc")
                or not isinstance(record.get("source_sessions"), list)
                or record.get("selected_sessions") != list(selected_sessions)):
            return None
        return {key: reference[key] for key in
                ("run_id", "receipt_path", "receipt_sha256", "active_metadata_sha256")}
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        return None
