"""R40 training experiment provenance, standalone from U27 deployment manifests.

JSON summaries are saved under <working-folder>/training_runs/<run_id>.json.
Each model can additionally receive <model>.experiment.json, which binds its
training run to the verified U27 model checksum. No database is required.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ...utils.model_manifest import inspect_manifest, sha256_model

SCHEMA_VERSION = 1
MAX_RECORD_BYTES = 256 * 1024
RUN_ID_PATTERN = re.compile(r"[0-9a-f]{32}\Z")
METRIC_KEYS = ("loss", "val_loss", "steering_loss", "throttle_loss",
               "val_steering_loss", "val_throttle_loss")


def _clean(value):
    if value is None:
        return None
    if isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _clean(item())
        except (TypeError, ValueError):
            pass
    return str(value)


def _json_bytes(payload: dict) -> bytes:
    content = (json.dumps(_clean(payload), sort_keys=True, indent=2,
                          ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    if len(content) > MAX_RECORD_BYTES:
        raise ValueError("Experiment metadata exceeds the 256 KiB safety limit.")
    return content


def preprocessing_hash(recipe: dict | None) -> str | None:
    if not recipe:
        return None  # Missing recipe metadata is not proof of default settings.
    encoded = json.dumps(_clean(recipe), sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_counts(df) -> dict[str, int] | None:
    if df is None or "session" not in df.columns:
        return None
    counts: dict[str, int] = {}
    for value in df["session"]:
        name = str(value).strip()
        if name and name.lower() not in ("nan", "none", "<na>"):
            counts[name] = counts.get(name, 0) + 1
    return counts


def _partition_fingerprint(train_df, val_df) -> str | None:
    """Hash available row identities/labels, NOT image file bytes."""
    rows = []
    columns = ("session", "abs_image", "source_frame_id", "frame_id",
               "steering", "throttle")
    for partition, df in (("train", train_df), ("validation", val_df)):
        if df is None or "abs_image" not in df.columns:
            return None
        selected = [column for column in columns if column in df.columns]
        for values in df[selected].itertuples(index=False, name=None):
            row = dict(zip(selected, (_clean(value) for value in values)))
            rows.append(json.dumps([partition, row], sort_keys=True, ensure_ascii=False))
    digest = hashlib.sha256()
    for row in sorted(rows):
        digest.update(row.encode("utf-8") + b"\n")
    return digest.hexdigest()


def create_run_snapshot(train_df, val_df, config, recipe: dict | None,
                        selected_sessions=(), preprocess_path: str = "",
                        preprocessing_run: dict | None = None) -> dict:
    from ..preprocess.preprocessing_receipts import verified_preprocessing_reference

    selected_sessions = [str(name) for name in selected_sessions]
    preprocessing_run = verified_preprocessing_reference(
        preprocessing_run, preprocessing_hash(recipe), selected_sessions)
    settings = _clean(vars(config))
    train_counts = _source_counts(train_df)
    val_counts = _source_counts(val_df)
    groups = None
    if train_counts is not None and val_counts is not None:
        groups = [
            {"session": name, "train_rows": train_counts.get(name, 0),
             "validation_rows": val_counts.get(name, 0)}
            for name in sorted(set(train_counts) | set(val_counts))
        ]
    # Match the current split_service/TrainingWorker fallback: seed=0 uses 42.
    # Sequential splitting does not use a random seed, while training still does.
    configured_seed = settings.get("seed")
    effective_seed = int(configured_seed or 42)
    split_mode = settings.get("split_mode")
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": uuid4().hex,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "finished_at_utc": None,
        "status": "running",
        "source_groups": groups,
        "selected_sessions": [str(name) for name in selected_sessions],
        "train_rows": len(train_df),
        "validation_rows": len(val_df),
        "split": {
            "mode": split_mode,
            "configured_seed": configured_seed,
            "seed": None if split_mode == "Sequential rows" else effective_seed,
            "training_seed_effective": effective_seed,
            "validation_ratio": settings.get("val_ratio"),
            "identity_label_sha256": _partition_fingerprint(train_df, val_df),
        },
        "preprocessing_sha256": preprocessing_hash(recipe),
        "preprocessed_dataset_path": str(preprocess_path) if preprocess_path else None,
        "preprocessing_run": preprocessing_run,
        "model_settings": settings,
        "metrics": {},
        "artifacts": [],
        "error": None,
    }


def _numbers(values) -> list[float]:
    output = []
    if not isinstance(values, (list, tuple)):
        return output
    for item in values:
        try:
            number = float(item)
        except (ValueError, TypeError):
            continue
        if math.isfinite(number):
            output.append(number)
    return output


def summarize_metrics(history: dict | None) -> dict:
    values = history if isinstance(history, dict) else {}
    metrics = {"epochs_ran": len(values.get("loss", []) or [])}
    for key in METRIC_KEYS:
        numeric = _numbers(values.get(key, ()))
        metrics["final_" + key] = numeric[-1] if numeric else None
        metrics["best_" + key] = min(numeric) if numeric else None
    return metrics


def finish_run(snapshot: dict, status: str, history: dict | None = None,
               error: str | None = None) -> dict:
    if status not in ("succeeded", "failed", "cancelled"):
        raise ValueError("Run outcome must be succeeded, failed or cancelled.")
    result = copy.deepcopy(snapshot)
    result["status"] = status
    result["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    result["metrics"] = summarize_metrics(history)
    result["metrics_partial"] = status != "succeeded"
    result["error"] = str(error) if error else None
    return result


def portable_experiment(record: dict | None) -> dict | None:
    """Transfer only run identifiers and counts, never desktop paths or session names."""
    if not isinstance(record, dict) or record.get("status") != "succeeded" or not _valid_run_id(record.get("run_id")):
        return None
    groups = record.get("source_groups")
    return {
        "run_id": record["run_id"],
        "preprocessing_sha256": record.get("preprocessing_sha256"),
        "identity_label_sha256": (record.get("split") or {}).get("identity_label_sha256"),
        "train_rows": record.get("train_rows"),
        "validation_rows": record.get("validation_rows"),
        "source_group_count": len(groups) if isinstance(groups, list) else None,
    }


def _valid_run_id(run_id: object) -> bool:
    return isinstance(run_id, str) and RUN_ID_PATTERN.fullmatch(run_id) is not None


def run_record_path(root: Path | str, run_id: str) -> Path:
    if not _valid_run_id(run_id):
        raise ValueError("Invalid training run ID.")
    return Path(root).expanduser().resolve() / "training_runs" / f"{run_id}.json"


def _write_json_atomic(destination: Path, payload: dict) -> None:
    data = _json_bytes(payload)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=destination.parent,
                                         prefix=f".{destination.name}.",
                                         suffix=".tmp", delete=False) as handle:
            staged = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staged, destination)
        staged = None
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def save_run_record(root: Path | str, record: dict) -> Path:
    destination = run_record_path(root, record.get("run_id"))
    _write_json_atomic(destination, record)
    return destination


def _read_record(path: Path) -> dict | None:
    try:
        if not path.is_file() or path.stat().st_size > MAX_RECORD_BYTES:
            return None
        data = json.loads(path.read_text(encoding="utf-8"),
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (OSError, UnicodeError, ValueError):
        return None
    if (not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION
            or not _valid_run_id(data.get("run_id"))):
        return None
    return data


def load_runs(root: Path | str, limit: int = 100) -> list[dict]:
    folder = Path(root).expanduser().resolve() / "training_runs"
    if not folder.is_dir():
        return []
    results = []
    for path in folder.glob("*.json"):
        if not RUN_ID_PATTERN.fullmatch(path.stem):
            continue
        record = _read_record(path)
        if record is not None and record["run_id"] == path.stem:
            results.append(record)
    results.sort(key=lambda row: (str(row.get("started_at_utc") or ""),
                                  row["run_id"]), reverse=True)
    return results[:max(0, min(500, int(limit)))]


def attach_model_artifact(root: Path | str, record: dict,
                          model_path: Path | str) -> tuple[dict, Path]:
    """Write a separate experiment sidecar; never alter the U27 manifest."""
    model = Path(model_path).expanduser().resolve()
    manifest, _ = inspect_manifest(model, expected_kind="steering_control")
    if manifest is None:
        raise ValueError(f"Model has no verified deployment manifest: {model}")
    linked = copy.deepcopy(record)
    if not _valid_run_id(linked.get("run_id")) or linked.get("status") != "succeeded":
        raise ValueError("Only a completed successful run can be linked to a model.")
    artifacts = list(linked.get("artifacts") or [])
    entry = {"model_path": str(model), "model_sha256": manifest["model_sha256"]}
    if entry not in artifacts:
        artifacts.append(entry)
    linked["artifacts"] = artifacts
    sidecar = Path(str(model) + ".experiment.json")
    if sidecar.exists():
        raise FileExistsError(f"Experiment sidecar already exists: {sidecar}")
    bound = dict(linked)
    bound["model_binding"] = entry
    _write_json_atomic(sidecar, bound)
    try:
        save_run_record(root, linked)
    except Exception:
        sidecar.unlink(missing_ok=True)
        raise
    return linked, sidecar


def inspect_model_experiment(model_path: Path | str) -> tuple[dict | None, str]:
    model = Path(model_path).expanduser().resolve()
    sidecar = Path(str(model) + ".experiment.json")
    if not sidecar.is_file():
        return None, "Unknown — no R40 experiment sidecar for this historical model."
    result = _read_record(sidecar)
    if result is None or not isinstance(result.get("model_binding"), dict):
        return None, "Unknown — experiment sidecar is unreadable or invalid."
    binding = result["model_binding"]
    if binding.get("model_path") != str(model):
        return None, "Unknown — experiment sidecar refers to a different model path."
    try:
        manifest, _ = inspect_manifest(model, expected_kind="steering_control")
    except (OSError, ValueError) as exc:
        return None, f"Unknown — model verification failed: {exc}"
    if manifest is None or binding.get("model_sha256") != manifest["model_sha256"]:
        return None, "Unknown — model checksum does not match experiment provenance."
    return result, "Verified model/run association."


def inspect_model_provenance(model_path: Path | str) -> tuple[dict | None, str]:
    """Read-only inspection; portable claims never become local training runs."""
    model = Path(model_path).expanduser().resolve()
    sidecar = Path(str(model) + ".experiment.json")
    if sidecar.exists():
        record, message = inspect_model_experiment(model)
        if record is None or record.get("status") != "succeeded":
            return None, message if record is None else "Unknown — local run was not successful."
        return record, message
    try:
        manifest, _ = inspect_manifest(model, expected_kind="steering_control")
        checksum = manifest["model_sha256"] if manifest else sha256_model(model)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return None, f"Unknown — model inspection failed: {exc}"
    binding = {"model_path": str(model), "model_sha256": checksum}
    claim = (manifest or {}).get("experiment")
    if claim:
        return {
            "run_id": claim["run_id"], "status": "Portable claim — local run unverified",
            "source_group_count": claim.get("source_group_count"),
            "train_rows": claim.get("train_rows"), "validation_rows": claim.get("validation_rows"),
            "split": {"identity_label_sha256": claim.get("identity_label_sha256")},
            "preprocessing_sha256": claim.get("preprocessing_sha256"),
            "artifacts": [binding], "model_binding": binding,
        }, "Portable experiment claim; model bytes checksum verified. Local run history not established."
    status = ("Unknown — manifest verified, no experiment claim." if manifest else
              "Unknown — legacy file hash observed; no verified manifest or run.")
    return {"status": status, "artifacts": [binding], "model_binding": binding}, status


def _display(value) -> str:
    if value is None or value == "":
        return "Unknown"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value) if value else "Unknown"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _field(run: dict | None, *path):
    value = run
    for part in path:
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def comparison_rows(left: dict | None, right: dict | None) -> list[tuple[str, str, str]]:
    from ..preprocess.preprocessing_receipts import verified_preprocessing_reference

    def receipt_field(run, key):
        sessions = _field(run, "selected_sessions")
        if not isinstance(sessions, list):
            return None
        reference = verified_preprocessing_reference(
            _field(run, "preprocessing_run"), _field(run, "preprocessing_sha256"), sessions)
        return reference.get(key) if reference else None

    def source_names(run):
        groups = _field(run, "source_groups")
        if groups is None:
            return None
        return [g["session"] for g in groups if isinstance(g, dict) and "session" in g]

    def models(run):
        artifacts = _field(run, "artifacts")
        if not artifacts:
            return None
        return [item["model_path"] for item in artifacts if isinstance(item, dict) and item.get("model_path")]

    fields = [
        ("Run ID", ("run_id",)), ("Status", ("status",)),
        ("Started UTC", ("started_at_utc",)),
        ("Training rows", ("train_rows",)), ("Validation rows", ("validation_rows",)),
        ("Configured split mode", ("split", "mode")),
        ("Effective split seed", ("split", "seed")),
        ("Training seed", ("split", "training_seed_effective")),
        ("Validation ratio", ("split", "validation_ratio")),
        ("Split identity/label SHA-256", ("split", "identity_label_sha256")),
        ("Preprocessing SHA-256", ("preprocessing_sha256",)),
        ("Model size", ("model_settings", "model_size")),
        ("Learning rate", ("model_settings", "learning_rate")),
        ("Batch size", ("model_settings", "batch_size")),
        ("Epochs requested", ("model_settings", "epochs")),
        ("Epochs completed", ("metrics", "epochs_ran")),
        ("Metrics partial", ("metrics_partial",)),
        ("Final training loss", ("metrics", "final_loss")),
        ("Best training loss", ("metrics", "best_loss")),
        ("Final validation loss", ("metrics", "final_val_loss")),
        ("Best validation loss", ("metrics", "best_val_loss")),
        ("Final val steering loss", ("metrics", "final_val_steering_loss")),
        ("Final val throttle loss", ("metrics", "final_val_throttle_loss")),
        ("Preprocessed dataset", ("preprocessed_dataset_path",)),
    ]
    def source_count(run):
        groups = _field(run, "source_groups")
        return len(groups) if isinstance(groups, list) else _field(run, "source_group_count")

    result = [("Source sessions", _display(source_names(left)), _display(source_names(right))),
              ("Source group count", _display(source_count(left)), _display(source_count(right)))]
    result.extend((label, _display(_field(left, *path)), _display(_field(right, *path)))
                  for label, path in fields)
    for label, key in (("Preprocessing run ID", "run_id"),
                       ("Preprocessing receipt", "receipt_path")):
        result.append((label, _display(receipt_field(left, key)), _display(receipt_field(right, key))))
    result.append(("Model artifacts", _display(models(left)), _display(models(right))))
    return result
