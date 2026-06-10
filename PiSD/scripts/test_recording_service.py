#!/usr/bin/env python3
"""Validate PiSD frame capture/recording metadata without moving motors."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.core.errors import PiSDErrorCodes  # noqa: E402
from pisd.services.recording_service import RecordingService  # noqa: E402

OUTPUT_ROOT = PROJECT_ROOT / "test_outputs" / "recording_service"
SUMMARY_PATH = OUTPUT_ROOT / "summary.json"


@dataclass
class Result:
    label: str
    ok: bool
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"label": self.label, "ok": self.ok, "code": self.code, "message": self.message, "details": self.details}


class FakeCamera:
    def __init__(self):
        self.seq = 0
        self.running = False

    def start(self):
        self.running = True
        return True, "fake camera started"

    def wait_for_jpeg_frame(self, last_seq=None, timeout=1.0):
        self.seq += 1
        return b"\xff\xd8\xff\xd9", self.seq, f"fake-frame-{self.seq}", 4

    def get_config(self):
        return {"running": self.running, "width": 2, "height": 2, "fps": 30, "capture_source": "fake", "frame_seq": self.seq}


class FakeMotor:
    def __init__(self):
        self.n = 0

    def status(self):
        self.n += 1
        return {
            "last_command": {"steering": 0.12, "throttle": 0.18, "steer_mix": 1.0, "timestamp": 123.0 + self.n},
            "last_left": 0.10,
            "last_right": 0.20,
            "left_bias": 0.01,
            "right_bias": 0.02,
            "left_max_speed": 1.0,
            "right_max_speed": 1.0,
            "left_direction": 1,
            "right_direction": -1,
            "steering_direction": 1,
        }


def emit(result: Result) -> None:
    print(f"{'OK' if result.ok else 'FAIL':<4} {result.code:<13} {result.label} - {result.message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test PiSD recording service with fake camera/motor services.")
    parser.add_argument("--output", default=str(SUMMARY_PATH))
    parser.add_argument("--keep-output", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if OUTPUT_ROOT.exists() and not args.keep_output:
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    provider_overlay = {"enabled": True, "curve_strength": 9.87, "sample_count": 77, "path_width_scale": 0.66, "horizon_y": 28}
    capture_overlay = {"enabled": True, "curve_strength": 12.34, "sample_count": 123, "path_width_scale": 0.99, "horizon_y": 29}
    service = RecordingService(
        PROJECT_ROOT,
        root_name="test_outputs/recording_service/recordings",
        settings_provider=lambda: {"manual_drive": {"overlay": provider_overlay}},
    )
    camera = FakeCamera()
    motor = FakeMotor()
    results: list[Result] = []

    capture = service.capture_once(camera, motor, label="unit_capture", overlay_settings=capture_overlay)
    record = capture.get("record") or {}
    frame_file = PROJECT_ROOT / record.get("relative_file", "missing")
    capture_overlay_file = PROJECT_ROOT / record.get("overlay_settings_file", "missing")
    capture_overlay_data = json.loads(capture_overlay_file.read_text(encoding="utf-8")) if capture_overlay_file.exists() else {}
    ok = (
        capture.get("code") == PiSDErrorCodes.OK
        and frame_file.exists()
        and record.get("steering") == 0.12
        and "camera_settings" in record
        and (record.get("overlay_settings") or {}).get("path_width_scale") == capture_overlay["path_width_scale"]
        and (record.get("overlay_settings") or {}).get("horizon_y") == capture_overlay["horizon_y"]
        and capture_overlay_file.exists()
        and (capture_overlay_data.get("overlay_settings") or {}).get("path_width_scale") == capture_overlay["path_width_scale"]
        and capture_overlay_data.get("visual_only") is True
        and "curve_strength" not in (record.get("overlay_settings") or {})
        and "sample_count" not in (record.get("overlay_settings") or {})
    )
    results.append(Result("recording.capture_once", ok, capture.get("code", PiSDErrorCodes.TEST_RECORDING_SERVICE_FAILED), "single capture saved frame and metadata with trainer overlay sidecar" if ok else "single capture failed", {"record": record, "overlay_file": str(capture_overlay_file)}))

    ai_status = {
        "running": True,
        "mode": "preview",
        "drive_output_enabled": False,
        "model_id": "unit_model.tflite",
        "last_prediction_at_utc": "2026-06-10T00:00:00+00:00",
        "last_frame_seq": 42,
        "last_raw_prediction": {"steering": 0.31, "throttle": 0.41},
        "last_corrected_command": {"steering": 0.52, "throttle": 0.62},
        "last_safe_command": {"steering": -0.44, "throttle": 0.27},
    }
    ai_capture = service.capture_once(camera, motor, label="ai_mode_capture", command_source="ai_safe_command", ai_status_provider=lambda: ai_status)
    ai_record = ai_capture.get("record") or {}
    ai_label = ai_record.get("training_label") or {}
    ai_label_ok = (
        ai_capture.get("code") == PiSDErrorCodes.OK
        and ai_record.get("control_label_source") == "ai_safe_command"
        and ai_label.get("control_label_source") == "ai_safe_command"
        and ai_record.get("steering") == -0.44
        and ai_record.get("throttle") == 0.27
        and (ai_record.get("ai_output") or {}).get("safe", {}).get("steering") == -0.44
        and (ai_label.get("ai_output") or {}).get("safe", {}).get("throttle") == 0.27
        and (ai_record.get("manual_command") or {}).get("steering") == 0.12
    )
    results.append(Result(
        "recording.ai_output_labels",
        bool(ai_label_ok),
        ai_capture.get("code", PiSDErrorCodes.TEST_RECORDING_SERVICE_FAILED),
        "AI-mode recording can label frames from the latest safe AI output while preserving manual command trace" if ai_label_ok else "AI-mode recording did not label from AI safe output",
        {"record": ai_record},
    ))

    capture2 = service.capture_once(camera, motor, label="unit_capture", overlay_settings=capture_overlay)
    record2 = capture2.get("record") or {}
    same_folder = (Path(record.get("file", "missing")).parent == Path(record2.get("file", "other")).parent) if record and record2 else False
    ordered = record.get("frame_index") == 1 and record2.get("frame_index") == 3
    single_folder_ok = capture2.get("code") == PiSDErrorCodes.OK and same_folder and ordered and "single_captures" in str(record2.get("relative_file", ""))
    results.append(Result(
        "recording.single_capture_daily_folder",
        single_folder_ok,
        capture2.get("code", PiSDErrorCodes.TEST_RECORDING_SERVICE_FAILED),
        "single captures share the same daily folder and increment frame order" if single_folder_ok else "single capture folder/order policy failed",
        {"first": record.get("relative_file"), "second": record2.get("relative_file"), "same_folder": same_folder, "ordered": ordered},
    ))

    start = service.start(camera, motor, label="unit_record", fps=10)
    time.sleep(0.25)
    stop = service.stop()
    status = stop.get("recording") or {}
    stopped = stop.get("stopped_session") or {}
    records_file = Path(stopped.get("records_file", "")) if stopped else Path("missing")
    if not records_file.is_absolute():
        records_file = PROJECT_ROOT / records_file
    lines = records_file.read_text().strip().splitlines() if records_file.exists() else []
    ok = start.get("code") == PiSDErrorCodes.OK and stop.get("code") == PiSDErrorCodes.OK and len(lines) >= 1
    results.append(Result("recording.start_stop", ok, stop.get("code", PiSDErrorCodes.TEST_RECORDING_SERVICE_FAILED), "recording session saved ordered JSONL records" if ok else "recording session failed", {"records_file": str(records_file), "line_count": len(lines), "status": status}))

    schema_ok = False
    labels_ok = False
    sidecar_ok = False
    if lines:
        item = json.loads(lines[0])
        overlay_file = PROJECT_ROOT / item.get("overlay_settings_file", "missing")
        overlay_history_file = PROJECT_ROOT / item.get("overlay_settings_history_file", "missing")
        overlay_data = json.loads(overlay_file.read_text(encoding="utf-8")) if overlay_file.exists() else {}
        history_lines = overlay_history_file.read_text(encoding="utf-8").strip().splitlines() if overlay_history_file.exists() else []
        schema_ok = (
            all(key in item for key in ("frame_id", "frame_index", "saved_at_utc", "relative_file", "camera_settings", "motor_state", "steering", "throttle", "motor_outputs", "motor_tuning", "training_label", "overlay_settings", "overlay_settings_file", "overlay_settings_history_file", "overlay_schema_version"))
            and (item.get("overlay_settings") or {}).get("path_width_scale") == provider_overlay["path_width_scale"]
            and (item.get("overlay_settings") or {}).get("horizon_y") == provider_overlay["horizon_y"]
            and item.get("overlay_schema_version") == "PiSD_0_8_8_overlay_settings_v2"
            and "curve_strength" not in (item.get("overlay_settings") or {})
            and "sample_count" not in (item.get("overlay_settings") or {})
        )
        sidecar_ok = (
            overlay_file.exists()
            and overlay_history_file.exists()
            and (overlay_data.get("overlay_settings") or {}).get("path_width_scale") == provider_overlay["path_width_scale"]
            and overlay_data.get("overlay_schema_version") == "PiSD_0_8_8_overlay_settings_v2"
            and overlay_data.get("visual_only") is True
            and bool(history_lines)
        )
        labels_file = records_file.with_name("labels.jsonl")
        label_lines = labels_file.read_text().strip().splitlines() if labels_file.exists() else []
        if label_lines:
            label = json.loads(label_lines[0])
            labels_ok = (
                all(key in label for key in ("frame", "relative_file", "steering", "throttle", "timestamp_utc", "source_frame_seq", "session_id", "overlay_settings", "overlay_settings_file", "overlay_settings_history_file", "overlay_schema_version"))
                and label.get("steering") == item.get("steering")
                and label.get("throttle") == item.get("throttle")
                and (label.get("overlay_settings") or {}).get("path_width_scale") == provider_overlay["path_width_scale"]
                and label.get("overlay_settings_file") == "overlay_settings.json"
                and label.get("overlay_schema_version") == "PiSD_0_8_8_overlay_settings_v2"
                and "curve_strength" not in (label.get("overlay_settings") or {})
                and "sample_count" not in (label.get("overlay_settings") or {})
            )
    results.append(Result("recording.metadata_schema", schema_ok, PiSDErrorCodes.OK if schema_ok else PiSDErrorCodes.TEST_RECORDING_SERVICE_FAILED, "metadata includes traceable order/time/camera/motor/training-label/overlay fields" if schema_ok else "metadata schema incomplete"))
    results.append(Result("recording.overlay_sidecar", sidecar_ok, PiSDErrorCodes.OK if sidecar_ok else PiSDErrorCodes.TEST_RECORDING_SERVICE_FAILED, "recording/snapshot folders include overlay_settings.json and overlay_settings_history.jsonl for trainer reuse" if sidecar_ok else "overlay sidecar files missing or incomplete"))
    results.append(Result("recording.training_labels_jsonl", labels_ok, PiSDErrorCodes.OK if labels_ok else PiSDErrorCodes.TEST_RECORDING_SERVICE_FAILED, "labels.jsonl stores trainer-friendly frame/steering/throttle labels plus overlay settings and sidecar path" if labels_ok else "labels.jsonl training labels missing or incomplete"))

    listed = service.list_collections()
    collections = listed.get("collections") or {}
    recordings = collections.get("recordings") or []
    snapshots = collections.get("snapshots") or []
    list_ok = listed.get("code") == PiSDErrorCodes.OK and recordings and snapshots and recordings[0].get("overlay_settings_file") and snapshots[0].get("overlay_settings_file")
    results.append(Result(
        "recording.library_list",
        bool(list_ok),
        listed.get("code", PiSDErrorCodes.TEST_RECORDING_LIBRARY_FAILED),
        "recording and snapshot folders are listed for GUI selection" if list_ok else "recording library list did not include both folder types",
        {"recordings": recordings, "snapshots": snapshots},
    ))

    zip_ok = False
    zip_details: dict[str, Any] = {}
    if recordings:
        err, archive_bytes, download_name = service.build_collection_zip("recording", recordings[0]["id"])
        zip_ok = err is None and bool(archive_bytes and archive_bytes.startswith(b"PK")) and download_name.endswith(".zip")
        zip_details = {"error": err, "download_name": download_name, "bytes": len(archive_bytes or b"")}
    results.append(Result(
        "recording.library_zip",
        bool(zip_ok),
        PiSDErrorCodes.OK if zip_ok else PiSDErrorCodes.TEST_RECORDING_LIBRARY_FAILED,
        "selected recording folder can be zipped for download" if zip_ok else "recording zip build failed",
        zip_details,
    ))

    delete_ok = False
    delete_details: dict[str, Any] = {}
    if snapshots:
        snapshot_id = snapshots[0]["id"]
        delete = service.delete_collection("snapshot", snapshot_id)
        delete_ok = delete.get("code") == PiSDErrorCodes.OK and not (service.root_dir / snapshot_id).exists()
        delete_details = {"delete": delete, "snapshot_id": snapshot_id}
    results.append(Result(
        "recording.library_delete",
        bool(delete_ok),
        PiSDErrorCodes.OK if delete_ok else PiSDErrorCodes.TEST_RECORDING_LIBRARY_FAILED,
        "selected snapshot folder can be deleted" if delete_ok else "snapshot folder delete failed",
        delete_details,
    ))

    unsafe_delete = service.delete_collection("recording", ".")
    root_still_exists = service.root_dir.exists()
    unsafe_ok = unsafe_delete.get("code") == PiSDErrorCodes.RECORDING_ITEM_NOT_FOUND and root_still_exists
    results.append(Result(
        "recording.library_reject_root_delete",
        bool(unsafe_ok),
        PiSDErrorCodes.OK if unsafe_ok else PiSDErrorCodes.TEST_RECORDING_LIBRARY_FAILED,
        "unsafe root-folder delete id was rejected" if unsafe_ok else "unsafe root-folder delete id was not safely rejected",
        {"delete": unsafe_delete, "root_dir_exists": root_still_exists},
    ))

    mismatched_kind = service.build_collection_zip("recording", "single_captures")
    mismatch_ok = mismatched_kind[0] is not None and mismatched_kind[0].get("code") == PiSDErrorCodes.RECORDING_ITEM_NOT_FOUND
    results.append(Result(
        "recording.library_reject_kind_mismatch",
        bool(mismatch_ok),
        PiSDErrorCodes.OK if mismatch_ok else PiSDErrorCodes.TEST_RECORDING_LIBRARY_FAILED,
        "snapshot root cannot be requested through the recording kind" if mismatch_ok else "recording/snapshot kind mismatch was not rejected",
        {"error": mismatched_kind[0]},
    ))

    for result in results:
        emit(result)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"ok": all(r.ok for r in results), "results": [r.as_dict() for r in results]}, indent=2), encoding="utf-8")
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
