"""Read-only validation run context; missing provenance is explicitly unknown."""
from __future__ import annotations

from pathlib import Path
from ..train.experiment_service import inspect_model_experiment
from ...utils.model_manifest import inspect_manifest, sha256_model


def in_memory_context(run: dict | None) -> dict:
    # The caller supplies only TrainPage.provenance_for_model(model), which
    # checks the actual model object identity and the tracked successful run.
    if not isinstance(run, dict) or run.get("status") != "succeeded" or not run.get("run_id"):
        return {"run_id": None, "status": "Unknown — no tracked successful training run."}
    return {"run_id": run["run_id"], "status": "Tracked in-memory training run."}


def file_context(path: str) -> dict:
    if not path:
        return {"run_id": None, "status": "Unknown — no model file selected."}
    try:
        record, status = inspect_model_experiment(path)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return {"run_id": None, "status": f"Unknown — provenance unavailable: {exc}"}
    if record is None and not Path(str(Path(path).expanduser().resolve()) + ".experiment.json").is_file():
        try:
            manifest, _ = inspect_manifest(path, expected_kind="steering_control")
        except (OSError, ValueError):
            manifest = None
        experiment = (manifest or {}).get("experiment")
        if experiment:
            return {"run_id": experiment["run_id"], "status": "Portable experiment claim; model bytes checksum verified.",
                    "model_sha256": manifest["model_sha256"]}
    if record is None or record.get("status") != "succeeded":
        # Identify the observed file without claiming a verified manifest or run.
        # Before/after comparison also catches legacy file replacement.
        message = status if record is None else "Unknown — run was not successful."
        try:
            observed = sha256_model(Path(path).expanduser().resolve())
        except (OSError, ValueError):
            return {"run_id": None, "status": message}
        return {"run_id": None, "status": message + " Observed file hash only; run unverified.",
                "model_sha256": observed}
    return {"run_id": record.get("run_id"), "status": status,
            "model_sha256": record["model_binding"].get("model_sha256")}


def stable_file_context(before: dict, after: dict) -> dict:
    if before != after:
        return {"run_id": None, "status": "Unknown — model association changed during validation."}
    return before
