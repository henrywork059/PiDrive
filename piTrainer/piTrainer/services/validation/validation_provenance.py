"""Read-only validation run context; missing provenance is explicitly unknown."""
from __future__ import annotations

from ..train.experiment_service import inspect_model_experiment


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
    if record is None or record.get("status") != "succeeded":
        return {"run_id": None, "status": status if record is None else "Unknown — run was not successful."}
    return {"run_id": record.get("run_id"), "status": status,
            "model_sha256": record["model_binding"].get("model_sha256")}


def stable_file_context(before: dict, after: dict) -> dict:
    if before != after:
        return {"run_id": None, "status": "Unknown — model association changed during validation."}
    return before
