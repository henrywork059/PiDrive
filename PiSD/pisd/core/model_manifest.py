"""Versioned, backward-compatible PiDrive model manifest (Python stdlib only).

Adjacent file is <model filename>.manifest.json. A missing sidecar is legacy,
not an error; a present invalid/tampered sidecar always blocks deployment.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

KINDS = {"steering_control", "yolo_detection"}
INTERPRETATIONS = {"steering_throttle", "yolo_boxes"}
MAX_MANIFEST_BYTES = 128 * 1024


def manifest_path(model_path: str | Path) -> Path:
    path = Path(model_path)
    return path.with_name(path.name + ".manifest.json")


def sha256_model(model_path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(model_path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_manifest(model_path: str | Path, *, model_kind: str,
                  width: int, height: int, color_order: str = "RGB",
                  normalization: str = "zero_to_one", quantization: str = "float32",
                  output_interpretation: str | None = None,
                  class_names: list[str] | None = None,
                  training_seed: int | None = None,
                  experiment: dict[str, Any] | None = None) -> dict[str, Any]:
    if model_kind not in KINDS:
        raise ValueError("Unknown PiDrive model family.")
    result = {
        "schema_version": 1,
        "model_kind": model_kind,
        "model_sha256": sha256_model(model_path),
        "input": {
            "width": width, "height": height, "channels": 3,
            "channel_order": "NHWC", "color_order": color_order,
            "normalization": normalization,
        },
        "output": {"interpretation": output_interpretation or (
            "steering_throttle" if model_kind == "steering_control" else "yolo_boxes")},
        "quantization": {"mode": quantization},
        "training_seed": training_seed,
        "class_names": list(class_names or []),
    }
    if experiment is not None:
        result['experiment'] = dict(experiment)
    validate_manifest(result, expected_kind=model_kind)
    return result


def validate_manifest(data: Any, expected_kind: str | None = None) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported or malformed model manifest schema.")
    kind = data.get("model_kind")
    if kind not in KINDS:
        raise ValueError("Unrecognized model_kind in manifest.")
    if expected_kind is not None and kind != expected_kind:
        raise ValueError(f"Wrong model family: {kind}; expected {expected_kind}.")
    digest = data.get("model_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Missing or invalid model_sha256.")
    inp = data.get("input")
    if not isinstance(inp, dict):
        raise ValueError("Model input contract missing.")
    width, height = inp.get("width"), inp.get("height")
    if (type(width) is not int or type(height) is not int or
            not 1 <= width <= 4096 or not 1 <= height <= 4096 or width * height > 4096 * 4096):
        raise ValueError("Invalid manifest model input geometry.")
    if inp.get("channels") != 3 or inp.get("channel_order") != "NHWC":
        raise ValueError("Unsupported input channel contract.")
    if inp.get("color_order") != "RGB" or inp.get("normalization") != "zero_to_one":
        raise ValueError("Unsupported color/normalization contract.")
    out = data.get("output")
    interpretation = out.get("interpretation") if isinstance(out, dict) else None
    expected_output = "steering_throttle" if kind == "steering_control" else "yolo_boxes"
    if interpretation != expected_output:
        raise ValueError("Output interpretation does not match model family.")
    quant = data.get("quantization")
    if not isinstance(quant, dict) or quant.get("mode") not in {"float32", "float16", "int8", "uint8", "dynamic", "unknown"}:
        raise ValueError("Unsupported quantization mode.")
    classes = data.get("class_names")
    if not isinstance(classes, list) or not all(isinstance(s, str) and s for s in classes):
        raise ValueError("Invalid class_names metadata.")
    if kind == "steering_control" and classes:
        raise ValueError("Steering models cannot expose YOLO class labels.")
    seed = data.get("training_seed")
    if seed is not None and (type(seed) is not int or seed < 0):
        raise ValueError("Invalid training seed.")
    # Optional v1 provenance: bounded identifiers/counts, never local paths.
    # Model digest verifies bytes, not the author's claimed training history.
    experiment = data.get("experiment")
    if experiment is not None:
        if not isinstance(experiment, dict) or set(experiment) != {
            "run_id", "preprocessing_sha256", "identity_label_sha256",
            "train_rows", "validation_rows", "source_group_count"
        }:
            raise ValueError("Invalid experiment provenance fields.")
        run_id = experiment["run_id"]
        if not isinstance(run_id, str) or len(run_id) != 32 or any(c not in "0123456789abcdef" for c in run_id):
            raise ValueError("Invalid experiment run ID.")
        for key in ("preprocessing_sha256", "identity_label_sha256"):
            value = experiment[key]
            if value is not None and (not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value)):
                raise ValueError("Invalid experiment fingerprint.")
        for key in ("train_rows", "validation_rows", "source_group_count"):
            value = experiment[key]
            if value is not None and (type(value) is not int or not 0 <= value <= 2**53-1):
                raise ValueError("Invalid experiment row/group count.")
    return data


def inspect_manifest(model_path: str | Path, *, expected_kind: str | None = None,
                     input_size: tuple[int, int] | None = None) -> tuple[dict[str, Any] | None, str]:
    """Read and verify contract; missing sidecar remains a warned legacy model."""
    path = manifest_path(model_path)
    if not path.is_file():
        return None, "Legacy model without sidecar; verifying tensor shapes where supported."
    if path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("Model manifest is too large.")
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Model manifest unreadable: {exc}") from exc
    validate_manifest(metadata, expected_kind=expected_kind)
    if metadata["model_sha256"] != sha256_model(model_path):
        raise ValueError("Model checksum mismatch; refusing deployment.")
    if input_size is not None and (
        metadata["input"]["width"], metadata["input"]["height"]
    ) != tuple(input_size):
        raise ValueError("Model manifest input geometry does not match interpreter.")
    return metadata, "Model manifest and SHA-256 verified."


def write_manifest(model_path: str | Path, metadata: dict[str, Any]) -> Path:
    """Atomic sidecar publication after the artifact itself is complete."""
    validate_manifest(metadata)
    if metadata["model_sha256"] != sha256_model(model_path):
        raise ValueError("Refusing to write stale model checksum.")
    destination = manifest_path(model_path)
    contents = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if len(contents) > MAX_MANIFEST_BYTES:
        raise ValueError("Model manifest exceeds size limit.")
    staged = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=destination.parent,
                                         prefix="." + destination.name + ".", suffix=".tmp",
                                         delete=False) as f:
            staged = Path(f.name)
            f.write(contents)
            f.flush()
            os.fsync(f.fileno())
        os.replace(staged, destination)
        staged = None
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)
    return destination
