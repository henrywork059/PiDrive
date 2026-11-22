from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
import importlib.resources as resources

from custom_trainer.services.model_manifest import (
    inspect_manifest, make_manifest, write_manifest,
)


def _copy_asset(package: str, name: str, destination: Path) -> None:
    text = resources.files(package).joinpath(name).read_text(encoding="utf-8")
    destination.write_text(text, encoding="utf-8")


def build_pi_bundle(
    model_path: Path,
    labels_path: Path | None,
    output_dir: Path,
    image_size: int,
    conf_threshold: float,
    iou_threshold: float,
    model_type: str = "yolo_detect",
) -> Path:
    model_path = Path(model_path)
    if model_path.suffix.lower() != ".tflite" or not model_path.is_file():
        raise ValueError("Pi bundle requires an existing .tflite detector model.")
    if model_type != "yolo_detect":
        raise ValueError("Only YOLO object detection models are supported in the Pi bundle.")
    image_size = int(image_size)
    if not 1 <= image_size <= 4096:
        raise ValueError("Pi bundle image size must be between 1 and 4096.")
    # Verify an existing producer manifest BEFORE replacing the current
    # deployable bundle; a steering model must never become a YOLO bundle.
    source_meta, _warning = inspect_manifest(model_path, expected_kind="yolo_detection",
                                              input_size=(image_size, image_size))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_dir = output_dir / "pi_bundle"
    staging_dir = Path(tempfile.mkdtemp(prefix=".pi_bundle.", dir=output_dir))
    backup_dir = output_dir / f".pi_bundle.previous.{uuid.uuid4().hex}"
    saved_old = False
    try:
        model_dst = staging_dir / model_path.name
        shutil.copy2(model_path, model_dst)
        labels_dst = staging_dir / "labels.txt"
        if labels_path and Path(labels_path).is_file():
            shutil.copy2(labels_path, labels_dst)
        else:
            labels_dst.write_text("he3\\nmineral\\nradiation\\nhe3_zone\\n", encoding="utf-8")
        classes = [line.strip() for line in labels_dst.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not classes:
            raise ValueError("YOLO class label file is empty.")
        # Training seed and quantization are copied from a verified producer
        # sidecar when known; never guess them from the output filename.
        meta = make_manifest(
            model_dst, model_kind="yolo_detection", width=image_size, height=image_size,
            output_interpretation="yolo_boxes", class_names=classes,
            quantization=source_meta["quantization"]["mode"] if source_meta else "unknown",
            training_seed=source_meta["training_seed"] if source_meta else None,
        )
        write_manifest(model_dst, meta)
        config = {
            "model_filename": model_dst.name,
            "labels_filename": labels_dst.name,
            "image_size": image_size,
            "confidence_threshold": conf_threshold,
            "iou_threshold": iou_threshold,
            "model_type": model_type,
            "model_manifest_filename": model_dst.name + ".manifest.json",
        }
        (staging_dir / "model_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
        for asset in ("run_tflite_detect.py", "benchmark_tflite.py", "requirements_pi.txt", "README_PI.md"):
            _copy_asset("custom_trainer.assets.pi_runtime", asset, staging_dir / asset)
        shutil.copy2(Path(__file__).with_name("model_manifest.py"), staging_dir / "model_manifest.py")
        # Do not delete the previous working bundle until the new one is
        # fully assembled, and restore it if publication fails.
        if bundle_dir.exists():
            os.replace(bundle_dir, backup_dir)
            saved_old = True
        try:
            os.replace(staging_dir, bundle_dir)
        except BaseException:
            if saved_old and not bundle_dir.exists():
                os.replace(backup_dir, bundle_dir)
                saved_old = False
            raise
        if saved_old:
            shutil.rmtree(backup_dir)
        return bundle_dir
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
