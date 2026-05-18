from __future__ import annotations

import atexit
import json
import math
import shutil
import threading
import time
import uuid
import zipfile
from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pisd.core.errors import ErrorReport, ErrorReporter, PiSDErrorCodes, ok_payload, report_payload
from pisd.core.value_utils import clamp_float


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(dt: datetime | None = None) -> str:
    dt = dt or _utc_now()
    return dt.strftime("%Y%m%dT%H%M%S%fZ")


def _date_folder(dt: datetime | None = None) -> str:
    dt = dt or _utc_now()
    return dt.strftime("%Y-%m-%d")


def _safe_label(value: Any, default: str = "manual") -> str:
    text = str(value or default).strip().lower()
    allowed = []
    for char in text:
        if char.isalnum() or char in {"-", "_"}:
            allowed.append(char)
        elif char.isspace():
            allowed.append("_")
    cleaned = "".join(allowed).strip("_")
    return cleaned[:48] or default


class RecordingService:
    """Filesystem-backed frame recorder for PiSD data collection.

    The service saves JPEG frames and a JSONL record beside each frame so every
    image can be traced back to time, order, camera settings, motor command, and
    motor output values. It intentionally depends on CameraService/MotorService
    instances passed at call time so it can be tested without hardware.
    """

    def __init__(self, project_root: Path | str, root_name: str = "recordings", settings_provider: Callable[[], dict[str, Any]] | None = None):
        self.project_root = Path(project_root)
        self.root_dir = self.project_root / root_name
        self.settings_provider = settings_provider
        self.errors = ErrorReporter("recording")
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._active_session: dict[str, Any] | None = None
        self._frame_count = 0
        self._last_saved_record: dict[str, Any] = {}
        self._last_error = ""
        self._last_error_code = PiSDErrorCodes.OK
        atexit.register(self.close)

    def _record_error(
        self,
        code: str,
        message: str,
        *,
        severity: str = "error",
        context: dict[str, Any] | None = None,
        exc: BaseException | None = None,
    ) -> ErrorReport:
        report = self.errors.report(code, message, severity=severity, context=context, exc=exc)
        self._last_error = report.message
        self._last_error_code = report.code
        return report

    def status(self) -> dict[str, Any]:
        with self._lock:
            session = dict(self._active_session or {})
            data = {
                "root_dir": str(self.root_dir),
                "single_capture_dir_today": str(self.root_dir / "single_captures" / _date_folder()),
                "recording_sessions_dir_today": str(self.root_dir / _date_folder()),
                "running": bool(self._thread and self._thread.is_alive() and self._active_session),
                "active_session": session,
                "frame_count": int(self._frame_count),
                "last_saved_record": dict(self._last_saved_record),
                "last_error": self._last_error,
                "last_error_code": self._last_error_code,
            }
        data.update(self.errors.status_fields(limit=5))
        return data

    def start(self, camera_service: Any, motor_service: Any, *, label: Any = "manual_drive", fps: Any = 6.0, overlay_settings: Any | None = None) -> dict[str, Any]:
        record_fps = clamp_float(fps, 0.2, 30.0, 6.0)
        session_label = _safe_label(label, "manual_drive")
        with self._lock:
            if self._thread and self._thread.is_alive() and self._active_session:
                report = self._record_error(
                    PiSDErrorCodes.RECORDING_ALREADY_RUNNING,
                    "Recording is already running.",
                    severity="warning",
                    context={"session_id": self._active_session.get("session_id")},
                )
                return report_payload(False, report, recording=self.status())
            now = _utc_now()
            overlay_snapshot = self._current_overlay_settings(overlay_settings)
            session_id = f"{now.strftime('%Y%m%d_%H%M%S')}_{session_label}_{uuid.uuid4().hex[:8]}"
            session_dir = self.root_dir / _date_folder(now) / session_id
            frames_dir = session_dir / "frames"
            try:
                frames_dir.mkdir(parents=True, exist_ok=False)
                manifest = {
                    "session_id": session_id,
                    "label": session_label,
                    "started_at_utc": now.isoformat(),
                    "ended_at_utc": "",
                    "record_fps": record_fps,
                    "frames_dir": str(frames_dir.relative_to(self.project_root)),
                    "records_file": str((session_dir / "records.jsonl").relative_to(self.project_root)),
                    "labels_file": str((session_dir / "labels.jsonl").relative_to(self.project_root)),
                    "manifest_file": str((session_dir / "manifest.json").relative_to(self.project_root)),
                    "frame_count": 0,
                    "overlay_settings": overlay_snapshot,
                    "overlay_settings_source": "manual_drive_runtime_overlay",
                    "overlay_schema_version": "PiSD_0_6_7_overlay_settings_v1",
                    "schema": {
                        "frame_id": "unique stable frame id",
                        "frame_index": "1-based session order",
                        "saved_at_utc": "capture save time",
                        "source_frame_seq": "camera service frame sequence",
                        "camera_settings": "full camera status/config at save time",
                        "motor_state": "full motor status/config at save time",
                        "steering": "last manual steering command if available",
                        "throttle": "last manual throttle command if available",
                        "motor_outputs": "left/right effective motor outputs",
                        "overlay_settings": "Manual Drive visual path overlay settings at save time for trainer redraw",
                    },
                    "training_labels_schema": {
                        "frame": "relative frame path used by trainers",
                        "steering": "manual steering label in -1..1",
                        "throttle": "manual throttle label in -1..1",
                        "timestamp_utc": "save time for traceability",
                        "overlay_settings": "Manual Drive visual path overlay settings at save time for trainer redraw",
                    },
                }
                self._write_json(session_dir / "manifest.json", manifest)
            except Exception as exc:
                report = self._record_error(
                    PiSDErrorCodes.RECORDING_START_FAILED,
                    f"Failed to create recording session: {exc}",
                    context={"session_dir": str(session_dir)},
                    exc=exc,
                )
                return report_payload(False, report, recording=self.status())
            self._active_session = {
                "session_id": session_id,
                "label": session_label,
                "session_dir": str(session_dir),
                "frames_dir": str(frames_dir),
                "records_file": str(session_dir / "records.jsonl"),
                "labels_file": str(session_dir / "labels.jsonl"),
                "manifest_file": str(session_dir / "manifest.json"),
                "started_at_utc": now.isoformat(),
                "record_fps": record_fps,
                "overlay_settings": overlay_snapshot,
                "overlay_settings_source": "manual_drive_runtime_overlay",
                "overlay_schema_version": "PiSD_0_6_7_overlay_settings_v1",
            }
            self._frame_count = 0
            self._last_saved_record = {}
            self._last_error = ""
            self._last_error_code = PiSDErrorCodes.OK
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._record_loop,
                args=(camera_service, motor_service, record_fps),
                name="PiSDRecordingThread",
                daemon=True,
            )
            self._thread.start()
        return ok_payload("Recording started.", recording=self.status())

    def stop(self) -> dict[str, Any]:
        with self._lock:
            thread = self._thread
            session = dict(self._active_session or {})
            if not session:
                report = self._record_error(
                    PiSDErrorCodes.RECORDING_NOT_RUNNING,
                    "Recording is not running.",
                    severity="warning",
                )
                return report_payload(False, report, recording=self.status())
            self._stop_event.set()
        if thread is not None:
            thread.join(timeout=3.0)
        with self._lock:
            try:
                self._finalise_manifest_locked()
            except Exception as exc:
                report = self._record_error(
                    PiSDErrorCodes.RECORDING_STOP_FAILED,
                    f"Failed to finalise recording manifest: {exc}",
                    context={"session": session},
                    exc=exc,
                )
                return report_payload(False, report, recording=self.status())
            self._active_session = None
            self._thread = None
        return ok_payload("Recording stopped.", recording=self.status(), stopped_session=session)

    def capture_once(self, camera_service: Any, motor_service: Any, *, label: Any = "capture", overlay_settings: Any | None = None) -> dict[str, Any]:
        label_text = _safe_label(label, "capture")
        try:
            frame, seq, source_frame_at, byte_count = self._get_frame(camera_service)
            if frame is None:
                report = self._record_error(
                    PiSDErrorCodes.RECORDING_NO_FRAME,
                    "No camera frame available to save.",
                    context={"label": label_text},
                )
                return report_payload(False, report, recording=self.status())
            with self._lock:
                if self._active_session:
                    session = dict(self._active_session)
                    frame_index = self._frame_count + 1
                    record = self._save_frame_record_locked(
                        frame,
                        seq,
                        source_frame_at,
                        byte_count,
                        camera_service,
                        motor_service,
                        label=label_text,
                        frame_index=frame_index,
                        session=session,
                        overlay_settings=overlay_settings,
                    )
                    self._frame_count = frame_index
                    self._finalise_manifest_locked(open_session=True)
                    return ok_payload("Frame captured into active recording session.", record=record, recording=self.status())
                session, frame_index = self._single_capture_session(label_text)
                record = self._save_frame_record_locked(
                    frame,
                    seq,
                    source_frame_at,
                    byte_count,
                    camera_service,
                    motor_service,
                    label=label_text,
                    frame_index=frame_index,
                    session=session,
                    overlay_settings=overlay_settings,
                )
                self._write_json(
                    Path(session["manifest_file"]),
                    {
                        **session,
                        "frame_count": frame_index,
                        "last_saved_record": record,
                        "updated_at_utc": record["saved_at_utc"],
                        "overlay_settings": record.get("overlay_settings", {}),
                        "overlay_settings_source": record.get("overlay_settings_source", "manual_drive_runtime_overlay"),
                        "overlay_schema_version": record.get("overlay_schema_version", "PiSD_0_6_7_overlay_settings_v1"),
                        "capture_folder_policy": "All manual single captures for the same day are saved in this one folder.",
                    },
                )
                self._last_saved_record = record
                return ok_payload("Frame captured.", record=record, recording=self.status())
        except Exception as exc:
            report = self._record_error(
                PiSDErrorCodes.RECORDING_WRITE_FAILED,
                f"Failed to capture frame: {exc}",
                context={"label": label_text},
                exc=exc,
            )
            return report_payload(False, report, recording=self.status())

    def list_collections(self) -> dict[str, Any]:
        """List downloadable/deletable recording and single-capture folders."""
        try:
            recordings: list[dict[str, Any]] = []
            snapshots: list[dict[str, Any]] = []
            if self.root_dir.exists():
                for date_dir in sorted(self.root_dir.iterdir(), reverse=True):
                    if not date_dir.is_dir():
                        continue
                    if date_dir.name == "single_captures":
                        continue
                    for session_dir in sorted(date_dir.iterdir(), reverse=True):
                        if session_dir.is_dir():
                            recordings.append(self._collection_summary("recording", session_dir))
                single_root = self.root_dir / "single_captures"
                if single_root.exists():
                    for date_dir in sorted(single_root.iterdir(), reverse=True):
                        if date_dir.is_dir():
                            snapshots.append(self._collection_summary("snapshot", date_dir))
            return ok_payload(
                "Recording folders loaded.",
                collections={"recordings": recordings, "snapshots": snapshots},
                root_dir=str(self.root_dir),
            )
        except Exception as exc:
            report = self._record_error(
                PiSDErrorCodes.RECORDING_INVALID_CONFIG,
                f"Failed to list recording folders: {exc}",
                exc=exc,
            )
            return report_payload(False, report, recording=self.status())

    def delete_collection(self, kind: Any, collection_id: Any) -> dict[str, Any]:
        """Delete a saved recording session folder or daily snapshot folder."""
        try:
            path, safe_id, safe_kind, report = self._resolve_collection(kind, collection_id)
            if report is not None:
                return report_payload(False, report, recording=self.status())
            with self._lock:
                active_dir = Path(self._active_session["session_dir"]).resolve() if self._active_session else None
            if active_dir is not None and path.resolve() == active_dir:
                report = self._record_error(
                    PiSDErrorCodes.RECORDING_DELETE_FAILED,
                    "Cannot delete the active recording session. Stop recording first.",
                    context={"kind": safe_kind, "id": safe_id, "path": str(path)},
                )
                return report_payload(False, report, recording=self.status())
            shutil.rmtree(path)
            return ok_payload(
                "Recording folder deleted.",
                deleted={"kind": safe_kind, "id": safe_id, "path": str(path)},
                collections=(self.list_collections().get("collections") or {}),
            )
        except Exception as exc:
            report = self._record_error(
                PiSDErrorCodes.RECORDING_DELETE_FAILED,
                f"Failed to delete recording folder: {exc}",
                context={"kind": str(kind), "id": str(collection_id)},
                exc=exc,
            )
            return report_payload(False, report, recording=self.status())

    def build_collection_zip(self, kind: Any, collection_id: Any) -> tuple[dict[str, Any] | None, bytes | None, str]:
        """Build a zip archive for a recording/snapshot folder.

        Returns (error_payload, bytes, download_name). The caller can stream the
        zip bytes with Flask send_file. The archive keeps a folder prefix so the
        downloaded data remains traceable on the user's PC.
        """
        try:
            path, safe_id, safe_kind, report = self._resolve_collection(kind, collection_id)
            if report is not None:
                return report_payload(False, report, recording=self.status()), None, ""
            buffer = BytesIO()
            prefix = f"PiSD_{safe_kind}_{safe_id.replace('/', '_')}"
            with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for file_path in sorted(path.rglob("*")):
                    if file_path.is_file():
                        arcname = Path(prefix) / file_path.relative_to(path)
                        archive.write(file_path, arcname.as_posix())
            buffer.seek(0)
            return None, buffer.getvalue(), f"{prefix}.zip"
        except Exception as exc:
            report = self._record_error(
                PiSDErrorCodes.RECORDING_ZIP_FAILED,
                f"Failed to create recording zip: {exc}",
                context={"kind": str(kind), "id": str(collection_id)},
                exc=exc,
            )
            return report_payload(False, report, recording=self.status()), None, ""

    def _resolve_collection(self, kind: Any, collection_id: Any) -> tuple[Path, str, str, ErrorReport | None]:
        safe_kind = str(kind or "").strip().lower().replace("snapshots", "snapshot").replace("single_capture", "snapshot")
        raw_id = str(collection_id or "").strip().replace("\\", "/")
        if safe_kind not in {"recording", "snapshot"} or not raw_id:
            report = self._record_error(
                PiSDErrorCodes.RECORDING_ITEM_NOT_FOUND,
                "Recording item kind/id was missing or invalid.",
                severity="warning",
                context={"kind": str(kind), "id": str(collection_id)},
            )
            return self.root_dir, raw_id, safe_kind, report
        raw_parts = Path(raw_id).parts
        if raw_id in {".", "./"} or raw_id.startswith("/") or ".." in raw_parts:
            report = self._record_error(
                PiSDErrorCodes.RECORDING_ITEM_NOT_FOUND,
                "Recording item id was not a safe relative folder path.",
                severity="warning",
                context={"kind": safe_kind, "id": raw_id},
            )
            return self.root_dir, raw_id, safe_kind, report
        if safe_kind == "snapshot":
            if not raw_id.startswith("single_captures/"):
                raw_id = f"single_captures/{raw_id}"
        elif raw_id == "single_captures" or raw_id.startswith("single_captures/"):
            report = self._record_error(
                PiSDErrorCodes.RECORDING_ITEM_NOT_FOUND,
                "Snapshot folders must be requested with kind=snapshot, not kind=recording.",
                severity="warning",
                context={"kind": safe_kind, "id": raw_id},
            )
            return self.root_dir, raw_id, safe_kind, report
        path = (self.root_dir / raw_id).resolve()
        root = self.root_dir.resolve()
        try:
            relative_path = path.relative_to(root)
        except ValueError:
            report = self._record_error(
                PiSDErrorCodes.RECORDING_ITEM_NOT_FOUND,
                "Recording item path escaped the recordings folder.",
                severity="warning",
                context={"kind": safe_kind, "id": raw_id},
            )
            return path, raw_id, safe_kind, report
        if path == root or str(relative_path) in {".", ""}:
            report = self._record_error(
                PiSDErrorCodes.RECORDING_ITEM_NOT_FOUND,
                "Recording item id resolved to the recordings root and was blocked.",
                severity="warning",
                context={"kind": safe_kind, "id": raw_id},
            )
            return path, raw_id, safe_kind, report
        if not path.exists() or not path.is_dir():
            report = self._record_error(
                PiSDErrorCodes.RECORDING_ITEM_NOT_FOUND,
                "Recording folder was not found.",
                severity="warning",
                context={"kind": safe_kind, "id": raw_id, "path": str(path)},
            )
            return path, raw_id, safe_kind, report
        return path, str(path.relative_to(root)).replace("\\", "/"), safe_kind, None

    def _collection_summary(self, kind: str, folder: Path) -> dict[str, Any]:
        relative_id = str(folder.relative_to(self.root_dir)).replace("\\", "/")
        records_file = folder / "records.jsonl"
        manifest_file = folder / "manifest.json"
        frame_count = self._count_jsonl_records(records_file)
        if frame_count <= 0:
            frame_count = sum(1 for item in (folder / "frames").glob("*.jpg")) if (folder / "frames").exists() else 0
        byte_count = 0
        latest_mtime = folder.stat().st_mtime
        for item in folder.rglob("*"):
            if item.is_file():
                try:
                    stat = item.stat()
                    byte_count += int(stat.st_size)
                    latest_mtime = max(latest_mtime, stat.st_mtime)
                except OSError:
                    continue
        label = folder.name
        started_at = ""
        running = False
        if manifest_file.exists():
            try:
                manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
                label = str(manifest.get("label") or label)
                started_at = str(manifest.get("started_at_utc") or manifest.get("updated_at_utc") or "")
                running = bool(manifest.get("running", False))
            except Exception:
                pass
        safe_name = f"PiSD_{kind}_{relative_id.replace('/', '_')}.zip"
        return {
            "kind": kind,
            "id": relative_id,
            "label": label,
            "date": folder.parent.name if kind == "recording" else folder.name,
            "path": str(folder),
            "relative_path": str(folder.relative_to(self.project_root)).replace("\\", "/"),
            "records_file": str(records_file.relative_to(self.project_root)).replace("\\", "/") if records_file.exists() else "",
            "labels_file": str((folder / "labels.jsonl").relative_to(self.project_root)).replace("\\", "/") if (folder / "labels.jsonl").exists() else "",
            "manifest_file": str(manifest_file.relative_to(self.project_root)).replace("\\", "/") if manifest_file.exists() else "",
            "frame_count": int(frame_count),
            "bytes": int(byte_count),
            "modified_at_utc": datetime.fromtimestamp(latest_mtime, timezone.utc).isoformat(),
            "started_at_utc": started_at,
            "running": running,
            "download_name": safe_name,
            "can_delete": not running,
        }

    def close(self) -> None:
        try:
            if self.status().get("running"):
                self.stop()
        except Exception:
            pass

    def _json_safe_overlay_settings(self, value: Any) -> dict[str, Any]:
        """Return a JSON-safe overlay settings snapshot without clamping user tuning values.

        Overlay settings are visual/training metadata, not motor-safety inputs.
        Preserve finite typed numbers and simple scalar values so piTrainer can
        redraw the same guide later, but discard unserialisable values.
        """
        if not isinstance(value, dict):
            return {}
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if isinstance(item, bool) or item is None or isinstance(item, str):
                cleaned[key_text] = item
            elif isinstance(item, int):
                cleaned[key_text] = item
            elif isinstance(item, float):
                if math.isfinite(item):
                    cleaned[key_text] = item
            else:
                try:
                    numeric = float(item)
                    if math.isfinite(numeric):
                        cleaned[key_text] = numeric
                except Exception:
                    continue
        return cleaned

    def _settings_provider_overlay(self) -> dict[str, Any]:
        if not self.settings_provider:
            return {}
        try:
            settings = self.settings_provider() or {}
            manual = settings.get("manual_drive") if isinstance(settings, dict) else {}
            overlay = manual.get("overlay") if isinstance(manual, dict) else {}
            return self._json_safe_overlay_settings(overlay)
        except Exception:
            return {}

    def _current_overlay_settings(self, explicit: Any | None = None, *, session: dict[str, Any] | None = None) -> dict[str, Any]:
        explicit_overlay = self._json_safe_overlay_settings(explicit)
        if explicit_overlay:
            return explicit_overlay
        provider_overlay = self._settings_provider_overlay()
        if provider_overlay:
            return provider_overlay
        session_overlay = self._json_safe_overlay_settings((session or {}).get("overlay_settings"))
        if session_overlay:
            return session_overlay
        return {}

    def _record_loop(self, camera_service: Any, motor_service: Any, record_fps: float) -> None:
        interval = 1.0 / max(0.2, record_fps)
        last_seq: int | None = None
        next_save_at = time.monotonic()
        while not self._stop_event.is_set():
            now = time.monotonic()
            if now < next_save_at:
                time.sleep(min(0.05, next_save_at - now))
                continue
            try:
                frame, seq, source_frame_at, byte_count = self._get_frame(camera_service, last_seq=last_seq, timeout=1.5)
                if frame is None:
                    next_save_at = time.monotonic() + interval
                    continue
                if last_seq is not None and seq == last_seq:
                    next_save_at = time.monotonic() + interval
                    continue
                last_seq = seq
                with self._lock:
                    if not self._active_session:
                        return
                    frame_index = self._frame_count + 1
                    record = self._save_frame_record_locked(
                        frame,
                        seq,
                        source_frame_at,
                        byte_count,
                        camera_service,
                        motor_service,
                        label="record",
                        frame_index=frame_index,
                        session=dict(self._active_session),
                    )
                    self._frame_count = frame_index
                    self._last_saved_record = record
                    self._finalise_manifest_locked(open_session=True)
            except Exception as exc:
                self._record_error(PiSDErrorCodes.RECORDING_WRITE_FAILED, f"Recording loop failed to save a frame: {exc}", exc=exc)
                time.sleep(0.2)
            next_save_at = time.monotonic() + interval

    def _get_frame(self, camera_service: Any, *, last_seq: int | None = None, timeout: float = 1.0) -> tuple[bytes | None, int, str, int]:
        try:
            camera_service.start()
        except Exception:
            pass
        frame, seq, source_frame_at, byte_count = camera_service.wait_for_jpeg_frame(last_seq=last_seq, timeout=timeout)
        return frame, int(seq or 0), str(source_frame_at or ""), int(byte_count or 0)

    def _single_capture_session(self, label: str) -> tuple[dict[str, Any], int]:
        """Return the shared single-capture folder for today and next frame index.

        Continuous recordings still get their own session folders. Manual single
        captures are intentionally collected into one day folder so the user can
        find quick screenshots in one place instead of one tiny folder per frame.
        """
        now = _utc_now()
        date_name = _date_folder(now)
        session_id = f"single_captures_{date_name}"
        session_dir = self.root_dir / "single_captures" / date_name
        frames_dir = session_dir / "frames"
        records_file = session_dir / "records.jsonl"
        manifest_file = session_dir / "manifest.json"
        frames_dir.mkdir(parents=True, exist_ok=True)
        frame_index = self._count_jsonl_records(records_file) + 1
        session = {
            "session_id": session_id,
            "label": label,
            "session_dir": str(session_dir),
            "frames_dir": str(frames_dir),
            "records_file": str(records_file),
            "labels_file": str(session_dir / "labels.jsonl"),
            "manifest_file": str(manifest_file),
            "started_at_utc": now.isoformat(),
            "record_fps": 0,
            "capture_type": "single_capture_daily_folder",
            "date": date_name,
        }
        return session, frame_index

    def _count_jsonl_records(self, path: Path) -> int:
        try:
            if not path.exists():
                return 0
            with path.open("r", encoding="utf-8") as handle:
                return sum(1 for line in handle if line.strip())
        except Exception:
            return 0

    def _save_frame_record_locked(
        self,
        frame: bytes,
        seq: int,
        source_frame_at: str,
        byte_count: int,
        camera_service: Any,
        motor_service: Any,
        *,
        label: str,
        frame_index: int,
        session: dict[str, Any],
        overlay_settings: Any | None = None,
    ) -> dict[str, Any]:
        saved_at = _utc_now()
        frame_id = f"{session['session_id']}_{frame_index:06d}_{_stamp(saved_at)}_{uuid.uuid4().hex[:8]}"
        filename = f"frame_{frame_index:06d}_{_stamp(saved_at)}_{uuid.uuid4().hex[:8]}.jpg"
        frames_dir = Path(session["frames_dir"])
        frames_dir.mkdir(parents=True, exist_ok=True)
        frame_path = frames_dir / filename
        frame_path.write_bytes(frame)
        camera_status = camera_service.get_config()
        motor_status = motor_service.status()
        last_command = motor_status.get("last_command") or {}
        overlay_snapshot = self._current_overlay_settings(overlay_settings, session=session)
        record = {
            "frame_id": frame_id,
            "frame_index": int(frame_index),
            "label": label,
            "saved_at_utc": saved_at.isoformat(),
            "date": saved_at.strftime("%Y-%m-%d"),
            "time": saved_at.strftime("%H:%M:%S.%fZ"),
            "source_frame_seq": int(seq),
            "source_frame_at": source_frame_at,
            "source_frame_bytes": int(byte_count),
            "file": str(frame_path),
            "relative_file": str(frame_path.relative_to(self.project_root)),
            "session_id": session["session_id"],
            "session_label": session.get("label", ""),
            "camera_settings": camera_status,
            "motor_state": motor_status,
            "manual_command": last_command,
            "steering": float(last_command.get("steering", 0.0) or 0.0),
            "throttle": float(last_command.get("throttle", 0.0) or 0.0),
            "steer_mix": float(last_command.get("steer_mix", motor_status.get("steer_mix", 1.0)) or 1.0),
            "motor_outputs": {
                "left": float(motor_status.get("last_left", 0.0) or 0.0),
                "right": float(motor_status.get("last_right", 0.0) or 0.0),
            },
            "motor_tuning": {
                "left_bias": motor_status.get("left_bias"),
                "right_bias": motor_status.get("right_bias"),
                "left_max_speed": motor_status.get("left_max_speed"),
                "right_max_speed": motor_status.get("right_max_speed"),
                "left_direction": motor_status.get("left_direction"),
                "right_direction": motor_status.get("right_direction"),
                "steering_direction": motor_status.get("steering_direction"),
            },
            "overlay_settings": overlay_snapshot,
            "overlay_settings_source": "manual_drive_runtime_overlay",
            "overlay_schema_version": "PiSD_0_6_7_overlay_settings_v1",
        }
        # PiSD_0_5_2: write a compact trainer-friendly label beside the full
        # trace record. The full records.jsonl remains the source for debugging,
        # while labels.jsonl is intentionally easy for an AI trainer to stream.
        labels_file = Path(session.get("labels_file") or Path(session["records_file"]).with_name("labels.jsonl"))
        training_label = {
            "frame": str(frame_path.relative_to(Path(session["session_dir"]))).replace("\\", "/"),
            "relative_file": str(frame_path.relative_to(self.project_root)).replace("\\", "/"),
            "steering": record["steering"],
            "throttle": record["throttle"],
            "timestamp_utc": record["saved_at_utc"],
            "source_frame_seq": record["source_frame_seq"],
            "session_id": record["session_id"],
            "overlay_settings": overlay_snapshot,
            "overlay_schema_version": record["overlay_schema_version"],
        }
        record["training_label"] = training_label
        records_file = Path(session["records_file"])
        with records_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        with labels_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(training_label, sort_keys=True) + "\n")
        if self._active_session and self._active_session.get("session_id") == session.get("session_id"):
            self._active_session["overlay_settings"] = overlay_snapshot
            self._active_session["overlay_settings_source"] = record["overlay_settings_source"]
            self._active_session["overlay_schema_version"] = record["overlay_schema_version"]
        self._last_saved_record = record
        return record

    def _finalise_manifest_locked(self, *, open_session: bool = False) -> None:
        if not self._active_session:
            return
        manifest_file = Path(self._active_session["manifest_file"])
        session_dir = Path(self._active_session["session_dir"])
        manifest = {
            **self._active_session,
            "session_dir": str(session_dir),
            "frames_dir": str(Path(self._active_session["frames_dir"])),
            "records_file": str(Path(self._active_session["records_file"])),
            "labels_file": str(Path(self._active_session.get("labels_file") or manifest_file.with_name("labels.jsonl"))),
            "manifest_file": str(manifest_file),
            "frame_count": int(self._frame_count),
            "last_saved_record": self._last_saved_record,
            "overlay_settings": self._last_saved_record.get("overlay_settings") or self._active_session.get("overlay_settings", {}),
            "overlay_settings_source": self._last_saved_record.get("overlay_settings_source") or self._active_session.get("overlay_settings_source", "manual_drive_runtime_overlay"),
            "overlay_schema_version": self._last_saved_record.get("overlay_schema_version") or self._active_session.get("overlay_schema_version", "PiSD_0_6_7_overlay_settings_v1"),
            "ended_at_utc": "" if open_session else _utc_now().isoformat(),
            "running": bool(open_session),
            "training_data": {
                "format": "behavioural_cloning_jsonl",
                "labels_file": str(Path(self._active_session.get("labels_file") or manifest_file.with_name("labels.jsonl"))),
                "label_fields": ["frame", "steering", "throttle", "timestamp_utc", "overlay_settings"],
                "overlay_schema_version": "PiSD_0_6_7_overlay_settings_v1",
            },
        }
        self._write_json(manifest_file, manifest)

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
        tmp.replace(path)
