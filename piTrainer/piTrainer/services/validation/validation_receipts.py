"""Local R51 validation summaries; no image bytes, model mutation or deployment claims."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ..train.experiment_service import MAX_RECORD_BYTES, RUN_ID_PATTERN


def _finite(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError, OverflowError):
        return None


def evaluated_rows_hash(result: dict) -> str | None:
    """Hash actual evaluated row identities, flip flags and labels, not image bytes."""
    count = int(result.get("rows_used") or 0)
    keys = ("sessions", "frame_ids", "source_frame_ids", "abs_images",
            "aug_flip_lr", "steering_true", "throttle_true")
    columns = [result.get(key, ()) for key in keys]
    if count <= 0 or any(len(col) != count for col in columns):
        return None
    digest = hashlib.sha256()
    for session, frame, source, image, flip, steer, speed in zip(*columns):
        if not str(image).strip() or _finite(steer) is None or _finite(speed) is None:
            return None
        row = [str(session), str(frame), str(source), str(image), bool(flip),
               _finite(steer), _finite(speed)]
        digest.update(json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n")
    return digest.hexdigest()


def save_validation_receipt(root: Path | str, result: dict) -> tuple[dict, Path]:
    context = result.get("experiment_context") or {}
    run_id = context.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID_PATTERN.fullmatch(run_id):
        run_id = None
    check_id = uuid4().hex
    record = {
        "schema_version": 1, "validation_id": check_id,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "training_run_id": run_id,
        "association": str(context.get("status") or "Unknown"),
        "model_sha256": context.get("model_sha256") or None,
        "model_kind": result.get("model_kind") or None,
        "model_path": result.get("model_path") or None,
        "dataset_source": result.get("dataset_source") or None,
        "rows_used": int(result.get("rows_used") or 0),
        "evaluated_rows_sha256": evaluated_rows_hash(result),
        "prediction_backend": result.get("prediction_backend") or None,
        "metrics": {key: _finite(result.get(key)) for key in (
            "steering_mae", "throttle_mae", "steering_rmse", "throttle_rmse",
            "steering_bias", "throttle_bias")},
    }
    data = (json.dumps(record, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    if len(data) > MAX_RECORD_BYTES:
        raise ValueError("Validation summary exceeds metadata size limit.")
    path = Path(root).expanduser().resolve() / "validation_runs" / (check_id + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation: never replace a preexisting receipt, even on ID collision.
    handle = path.open("xb")
    try:
        with handle:
            handle.write(data)
            handle.flush()
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return record, path


def load_validation_receipts(root: Path | str, limit: int = 100) -> list[dict]:
    folder = Path(root).expanduser().resolve() / "validation_runs"
    if not folder.is_dir():
        return []
    records = []
    for path in folder.glob("*.json"):
        if not RUN_ID_PATTERN.fullmatch(path.stem):
            continue
        try:
            if path.stat().st_size > MAX_RECORD_BYTES:
                continue
            record = json.loads(path.read_text(encoding="utf-8"),
                                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
            if not isinstance(record, dict) or record.get("schema_version") != 1 or record.get("validation_id") != path.stem:
                continue
            record["receipt_path"] = str(path)
            records.append(record)
        except (OSError, UnicodeError, ValueError):
            continue
    records.sort(key=lambda row: (str(row.get("completed_at_utc") or ""), row["validation_id"]), reverse=True)
    return records[:max(0, min(500, int(limit)))]
