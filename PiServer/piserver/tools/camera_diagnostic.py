from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None  # type: ignore

from piserver.core.config_store import ConfigStore
from piserver.services.camera_service import CameraService

_FORMAT_SWEEP = ("BGR888", "RGB888", "XBGR8888")


def _sanitize_name(name: str) -> str:
    cleaned = []
    for ch in str(name or "case").strip().lower():
        if ch.isalnum():
            cleaned.append(ch)
        elif ch in {"-", "_"}:
            cleaned.append(ch)
        else:
            cleaned.append("_")
    text = "".join(cleaned).strip("_")
    return text or "case"


def _json_safe(value: Any, depth: int = 0):
    if depth > 6:
        return repr(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v, depth + 1) for v in value]
    if isinstance(value, bytes):
        return {"type": "bytes", "length": len(value)}
    shape = getattr(value, "shape", None)
    if shape is not None:
        return {"type": type(value).__name__, "shape": list(shape)}
    return repr(value)


def build_tint_test_cases(base_config: dict | None, include_format_sweep: bool = True) -> list[dict]:
    base = dict(base_config or {})
    cases: list[dict] = []

    def add_case(name: str, description: str, **overrides):
        merged = dict(base)
        merged.update(overrides)
        cases.append(
            {
                "name": _sanitize_name(name),
                "description": description,
                "settings": merged,
            }
        )

    add_case(
        "baseline_runtime",
        "Current PiServer runtime camera settings exactly as stored in runtime.json/defaults.",
    )
    add_case(
        "force_awb_on",
        "Same as runtime settings, but force auto white balance on.",
        auto_white_balance=True,
    )
    add_case(
        "force_awb_off",
        "Same as runtime settings, but force auto white balance off.",
        auto_white_balance=False,
    )
    add_case(
        "awb_on_low_saturation",
        "Same as runtime settings, but force AWB on and lower saturation slightly to reduce red cast if oversaturated.",
        auto_white_balance=True,
        saturation=0.8,
    )

    if include_format_sweep:
        for fmt in _FORMAT_SWEEP:
            add_case(
                f"format_{fmt.lower()}_awb_on",
                f"Force Picamera2 format {fmt} with AWB on to compare colour handling between pipeline formats.",
                format=fmt,
                auto_white_balance=True,
            )

    seen = set()
    unique_cases = []
    for case in cases:
        name = case["name"]
        if name in seen:
            continue
        seen.add(name)
        unique_cases.append(case)
    return unique_cases


def _write_bgr_frame(path: Path, frame, quality: int = 95) -> bool:
    if frame is None:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    quality = max(40, min(100, int(quality)))

    if cv2 is not None:
        params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        ok, buf = cv2.imencode(".jpg", frame, params)
        if ok:
            path.write_bytes(buf.tobytes())
            return True

    if Image is not None and np is not None:
        arr = np.asarray(frame)
        if getattr(arr, "ndim", 0) == 3 and int(arr.shape[2]) >= 3:
            rgb = arr[:, :, :3][:, :, ::-1]
            Image.fromarray(rgb).save(path, format="JPEG", quality=quality)
            return True
    return False


def run_camera_settings_diagnostic(
    base_dir: str | Path,
    output_dir: str | Path | None = None,
    warmup_s: float = 0.8,
    include_format_sweep: bool = True,
) -> dict:
    base_dir = Path(base_dir).resolve()
    if output_dir is None:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        output_dir = base_dir / "data" / "camera_diagnostics" / stamp
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    config_store = ConfigStore(base_dir / "config" / "runtime.json")
    runtime_config = config_store.load()
    runtime_camera = runtime_config.get("camera") if isinstance(runtime_config, dict) else {}
    runtime_camera = runtime_camera if isinstance(runtime_camera, dict) else {}

    service = CameraService()
    if runtime_camera:
        service.apply_settings(runtime_camera, restart=False)
    service.start()
    time.sleep(max(0.0, float(warmup_s)))

    manifest: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "base_dir": str(base_dir),
        "output_dir": str(output_dir),
        "runtime_camera": _json_safe(runtime_camera),
        "cases": [],
    }

    try:
        backend = service.get_config().get("backend", "unknown")
        cases = build_tint_test_cases(runtime_camera, include_format_sweep=include_format_sweep and backend == "picamera2")
        manifest["detected_backend"] = backend
        manifest["cases_planned"] = [case["name"] for case in cases]

        for index, case in enumerate(cases, start=1):
            ok, message, config = service.apply_settings(case["settings"], restart=True)
            time.sleep(max(0.0, float(warmup_s)))
            frame = service.capture_snapshot_frame(retries=10, delay_s=0.08, copy=True)
            image_name = f"{index:02d}_{case['name']}.jpg"
            image_path = output_dir / image_name
            saved = _write_bgr_frame(image_path, frame, quality=int(config.get("preview_quality", 95)))
            if not saved and image_path.exists():
                image_path.unlink(missing_ok=True)
            diagnostics = service.get_diagnostics()
            case_result = {
                "index": index,
                "name": case["name"],
                "description": case["description"],
                "apply_ok": bool(ok),
                "apply_message": str(message),
                "requested_settings": _json_safe(case["settings"]),
                "result_config": _json_safe(config),
                "image_file": image_name if saved else None,
                "diagnostics": _json_safe(diagnostics),
            }
            manifest["cases"].append(case_result)

        manifest["summary"] = {
            "images_saved": sum(1 for case in manifest["cases"] if case.get("image_file")),
            "cases_run": len(manifest["cases"]),
            "backend": service.get_config().get("backend", "unknown"),
        }
    finally:
        try:
            service.stop()
        except Exception:
            pass

    (output_dir / "manifest.json").write_text(json.dumps(_json_safe(manifest), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a PiServer camera tint/settings diagnostic sweep.")
    parser.add_argument("--base-dir", default=Path(__file__).resolve().parents[2], help="PiServer root folder. Defaults to the current PiServer root.")
    parser.add_argument("--output-dir", default=None, help="Optional output directory for captured images and manifest.json.")
    parser.add_argument("--warmup", type=float, default=0.8, help="Seconds to wait after each settings apply/restart before capture.")
    parser.add_argument("--no-format-sweep", action="store_true", help="Skip the BGR888/RGB888/XBGR8888 comparison cases.")
    args = parser.parse_args(argv)

    manifest = run_camera_settings_diagnostic(
        base_dir=args.base_dir,
        output_dir=args.output_dir,
        warmup_s=args.warmup,
        include_format_sweep=not args.no_format_sweep,
    )
    print(f"Camera diagnostic saved to: {manifest['output_dir']}")
    for case in manifest.get("cases", []):
        image_file = case.get("image_file") or "(capture failed)"
        print(f"- {case['name']}: {image_file}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
