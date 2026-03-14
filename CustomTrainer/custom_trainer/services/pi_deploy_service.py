from __future__ import annotations

import json
import shutil
from pathlib import Path
import importlib.resources as resources


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
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_dir = output_dir / "pi_bundle"
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    model_dst = bundle_dir / model_path.name
    shutil.copy2(model_path, model_dst)

    labels_dst = bundle_dir / "labels.txt"
    if labels_path and labels_path.exists():
        shutil.copy2(labels_path, labels_dst)
    else:
        labels_dst.write_text("he3\nmineral\nradiation\nhe3_zone\n", encoding="utf-8")

    config = {
        "model_filename": model_dst.name,
        "labels_filename": labels_dst.name,
        "image_size": image_size,
        "confidence_threshold": conf_threshold,
        "iou_threshold": iou_threshold,
        "model_type": model_type,
    }
    (bundle_dir / "model_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    _copy_asset("custom_trainer.assets.pi_runtime", "run_tflite_detect.py", bundle_dir / "run_tflite_detect.py")
    _copy_asset("custom_trainer.assets.pi_runtime", "benchmark_tflite.py", bundle_dir / "benchmark_tflite.py")
    _copy_asset("custom_trainer.assets.pi_runtime", "requirements_pi.txt", bundle_dir / "requirements_pi.txt")
    _copy_asset("custom_trainer.assets.pi_runtime", "README_PI.md", bundle_dir / "README_PI.md")

    return bundle_dir
