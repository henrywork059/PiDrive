from __future__ import annotations

import json
import shutil
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path

from piserver.core.recording_storage import RecordingStorageGuard, RecordingStorageError

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore


class RecorderService:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.recording = False
        self.session_name = ""
        self.session_path = None
        self.images_dir = None
        self.index_file = None
        self.min_interval = 0.1
        self.last_record_time = 0.0
        self.counter = 0
        self.session_started_at = 0.0
        self.last_session_name = ""
        self.last_session_path = None
        self.last_record_relpath = ""
        self.snapshot_dir = self.root / "snapshots"
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.last_snapshot_relpath = ""
        self.last_snapshot_name = ""
        self._lock = threading.RLock()
        self.storage = RecordingStorageGuard(self.root, prefix="PISERVER")
        self._normalize_snapshot_layout()

    def _display_base_dir(self) -> Path:
        if self.root.name == "records" and self.root.parent.name == "data":
            return self.root.parent.parent
        return self.root.parent

    def _display_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self._display_base_dir()))
        except Exception:
            return str(path)

    def _snapshot_metadata_path(self) -> Path:
        return self.snapshot_dir / "snapshots.jsonl"

    def _unique_snapshot_name(self, desired_name: str) -> str:
        desired = Path(desired_name).name or "snapshot.jpg"
        candidate = self.snapshot_dir / desired
        if not candidate.exists():
            return desired
        stem = candidate.stem or "snapshot"
        suffix = candidate.suffix
        index = 1
        while True:
            alt = f"{stem}_{index:03d}{suffix}"
            if not (self.snapshot_dir / alt).exists():
                return alt
            index += 1

    def _move_snapshot_file(self, source: Path) -> str:
        target_name = self._unique_snapshot_name(source.name)
        target = self.snapshot_dir / target_name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
        return target_name

    def _merge_snapshot_metadata(self, source_meta: Path, rename_map: dict[str, str]) -> None:
        target_meta = self._snapshot_metadata_path()
        target_meta.parent.mkdir(parents=True, exist_ok=True)
        with source_meta.open("r", encoding="utf-8") as source_handle, target_meta.open("a", encoding="utf-8") as target_handle:
            for raw_line in source_handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except Exception:
                    target_handle.write(raw_line if raw_line.endswith("\n") else raw_line + "\n")
                    continue
                image_ref = str(record.get("image", "")).strip()
                mapped = rename_map.get(image_ref) or rename_map.get(Path(image_ref).name)
                if mapped:
                    record["image"] = f"snapshots/{mapped}"
                target_handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _normalize_snapshot_layout(self) -> None:
        with self._lock:
            self.snapshot_dir.mkdir(parents=True, exist_ok=True)
            nested_dirs = [path for path in self.snapshot_dir.iterdir() if path.is_dir()]
            if not nested_dirs:
                return
            root_meta = self._snapshot_metadata_path()
            for nested_dir in nested_dirs:
                rename_map: dict[str, str] = {}
                nested_meta = nested_dir / "snapshots.jsonl"
                for file_path in sorted(nested_dir.rglob("*")):
                    if not file_path.is_file():
                        continue
                    if file_path == nested_meta:
                        continue
                    moved_name = self._move_snapshot_file(file_path)
                    relative_ref = str(file_path.relative_to(nested_dir)).replace("\\", "/")
                    rename_map[relative_ref] = moved_name
                    rename_map[file_path.name] = moved_name
                if nested_meta.exists():
                    self._merge_snapshot_metadata(nested_meta, rename_map)
                    try:
                        nested_meta.unlink()
                    except Exception:
                        pass
                for child in sorted(nested_dir.rglob("*"), reverse=True):
                    if child.is_dir():
                        try:
                            child.rmdir()
                        except Exception:
                            pass
                try:
                    nested_dir.rmdir()
                except Exception:
                    pass
            if root_meta.exists() and root_meta.is_dir():
                shutil.rmtree(root_meta, ignore_errors=True)

    def start(self):
        with self._lock:
            if self.recording:
                return
            try:
                self.storage.require_space()
            except RecordingStorageError as exc:
                self.storage.note_error('start', exc)
                raise
            session_name = datetime.now().strftime("%Y%m%d-%H%M%S")
            session_path = self.root / session_name
            images_dir = session_path / "images"
            index_file = None
            try:
                images_dir.mkdir(parents=True, exist_ok=True)
                index_file = (session_path / "records.jsonl").open("a", encoding="utf-8")
            except Exception as exc:
                self.storage.note_error('session_start', exc)
                if index_file is not None:
                    try:
                        index_file.close()
                    except Exception:
                        pass
                raise

            self.session_name = session_name
            self.session_path = session_path
            self.images_dir = images_dir
            self.index_file = index_file
            self.recording = True
            self.last_record_time = 0.0
            self.counter = 0
            self.session_started_at = time.time()
            self.last_session_name = session_name
            self.last_session_path = session_path
            print(f"[REC] session started: {self.session_path}")

    def stop(self):
        with self._lock:
            if not self.recording and self.index_file is None:
                return
            self.recording = False
            try:
                if self.index_file is not None:
                    self.index_file.close()
            except Exception:
                pass
            self.index_file = None
            self.images_dir = None
            self.session_path = None
            self.session_name = ""
            self.session_started_at = 0.0
            print("[REC] session stopped")

    def toggle(self):
        with self._lock:
            currently_recording = self.recording
        if currently_recording:
            self.stop()
        else:
            self.start()

    def maybe_record(self, frame_bgr, snapshot: dict):
        if not self.recording or frame_bgr is None or cv2 is None:
            return
        with self._lock:
            if not self.recording or self.images_dir is None or self.index_file is None:
                return
            now = time.time()
            if now - self.last_record_time < self.min_interval:
                return
            self.counter += 1
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            fname = f"{stamp}_{self.counter:04d}.jpg"
            image_path = self.images_dir / fname
            try:
                self.storage.require_space(estimated_bytes=max(65536, int(getattr(frame_bgr, 'nbytes', 0))))
                ok = cv2.imwrite(str(image_path), frame_bgr)
                if not ok:
                    raise OSError("Camera frame image write failed (possibly full disk).")
                rec = {
                    "frame_id": fname.rsplit(".", 1)[0],
                    "session": self.session_name,
                    "ts": now,
                    "image": f"images/{fname}",
                    "steering": float(snapshot.get("applied_steering", 0.0)),
                    "throttle": float(snapshot.get("applied_throttle", 0.0)),
                    "mode": str(snapshot.get("active_algorithm", "manual")),
                    "camera_width": int(snapshot.get("camera_width", 0)),
                    "camera_height": int(snapshot.get("camera_height", 0)),
                    "camera_format": str(snapshot.get("camera_format", "BGR888")),
                }
                line = json.dumps(rec, ensure_ascii=False) + "\n"
                # Avoid leaving a broken partial JSONL tail after a failed flush.
                previous_size = self.index_file.tell()
                try:
                    self.index_file.write(line)
                    self.index_file.flush()
                except OSError:
                    try:
                        self.index_file.seek(previous_size)
                        self.index_file.truncate(previous_size)
                        self.index_file.flush()
                    except OSError:
                        pass  # Recovery may be needed; keep all historical files.
                    raise
                self.last_record_time = now
                self.last_record_relpath = self._display_path(image_path)
            except Exception as exc:
                self.storage.note_error('record_frame', exc)
                # Recording failure must not escape into the motor controller.
                self.stop()

    def capture_once(self, frame_bgr, snapshot: dict | None = None):
        if frame_bgr is None or cv2 is None:
            return False, "No live frame available to save."
        snapshot = snapshot or {}
        with self._lock:
            try:
                self.storage.require_space(estimated_bytes=max(65536, int(getattr(frame_bgr, 'nbytes', 0))))
                self._normalize_snapshot_layout()
                shots_dir = self.snapshot_dir
                shots_dir.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                image_name = self._unique_snapshot_name(f"{stamp}.jpg")
                image_path = shots_dir / image_name
                if not cv2.imwrite(str(image_path), frame_bgr):
                    raise OSError("Failed to save snapshot image (possibly full disk).")
                meta_path = self._snapshot_metadata_path()
                rec = {
                    "frame_id": Path(image_name).stem,
                    "ts": time.time(),
                    "image": f"snapshots/{image_name}",
                    "steering": float(snapshot.get("applied_steering", 0.0)),
                    "throttle": float(snapshot.get("applied_throttle", 0.0)),
                    "mode": str(snapshot.get("active_algorithm", "manual")),
                    "camera_width": int(snapshot.get("camera_width", 0)),
                    "camera_height": int(snapshot.get("camera_height", 0)),
                    "camera_format": str(snapshot.get("camera_format", "BGR888")),
                }
                with meta_path.open("a", encoding="utf-8") as handle:
                    before = handle.tell()
                    try:
                        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        handle.flush()
                    except OSError:
                        try:
                            handle.truncate(before)
                        except OSError:
                            pass
                        raise
                self.last_snapshot_name = image_name
                self.last_snapshot_relpath = self._display_path(image_path)
                return True, f"Snapshot saved: {image_name}"
            except Exception as exc:
                self.storage.note_error('snapshot', exc)
                return False, f"Snapshot was not saved: {exc}"

    def get_status(self):
        with self._lock:
            self._normalize_snapshot_layout()
            active_session_name = self.session_name or self.last_session_name
            active_session_path = self.session_path or self.last_session_path
            elapsed = 0.0
            if self.recording and self.session_started_at:
                elapsed = max(0.0, time.time() - self.session_started_at)
            data = {
                "record_session_name": active_session_name,
                "record_save_path": self._display_path(active_session_path) if active_session_path else self._display_path(self.root),
                "record_elapsed_seconds": elapsed,
                "record_last_saved": self.last_record_relpath,
                "snapshot_save_path": self._display_path(self.snapshot_dir),
                "snapshot_last_saved": self.last_snapshot_relpath,
                "snapshot_last_name": self.last_snapshot_name,
                "recording": self.recording,
            }
        # Filesystem directory walks may be slow on an SD card. Do not hold
        # the recorder lock while gathering optional size/free-space telemetry.
        data["recording_storage"] = self.storage.status(active_session_path)
        return data

    def _iter_session_dirs(self):
        for path in sorted(self.root.glob("*"), reverse=True):
            if not path.is_dir():
                continue
            if path.name == "snapshots":
                continue
            if not (path / "records.jsonl").exists():
                continue
            yield path

    def _count_files(self, root: Path) -> int:
        try:
            return sum(1 for child in root.rglob("*") if child.is_file())
        except Exception:
            return 0

    def _build_folder_item(self, path: Path, *, kind: str) -> dict:
        try:
            updated_at = datetime.fromtimestamp(path.stat().st_mtime).isoformat()
        except Exception:
            updated_at = ""
        if kind == "snapshots":
            image_count = self._count_files(path)
            label = "Snapshot folder"
        else:
            images_dir = path / "images"
            image_count = self._count_files(images_dir) if images_dir.exists() else 0
            label = "Recorded session"
        return {
            "name": path.name,
            "kind": kind,
            "label": label,
            "image_count": image_count,
            "size_bytes": self.storage.session_size(path),
            "updated_at": updated_at,
            "path": self._display_path(path),
        }

    def _resolve_export_dir(self, session_name: str) -> tuple[Path | None, str]:
        name = str(session_name or "").strip()
        if not name or name in {".", ".."} or "/" in name or "\\" in name:
            return None, ""
        root_resolved = self.root.resolve()
        if name == "snapshots":
            candidate = self.snapshot_dir.resolve()
            try:
                candidate.relative_to(root_resolved)
            except Exception:
                return None, ""
            return (candidate if candidate.is_dir() else None), "snapshots"
        candidate = (self.root / name).resolve()
        try:
            candidate.relative_to(root_resolved)
        except Exception:
            return None, ""
        if not candidate.is_dir() or not (candidate / "records.jsonl").exists():
            return None, ""
        return candidate, "session"

    def _resolve_session_dir(self, session_name: str) -> Path | None:
        path, kind = self._resolve_export_dir(session_name)
        if kind != "session":
            return None
        return path

    def list_sessions(self):
        with self._lock:
            self._normalize_snapshot_layout()
            items = []
            if self.snapshot_dir.exists():
                items.append(self._build_folder_item(self.snapshot_dir, kind="snapshots"))
            for path in self._iter_session_dirs():
                items.append(self._build_folder_item(path, kind="session"))
            return items

    def write_session_zip(self, session_name: str, fileobj):
        with self._lock:
            if str(session_name or "").strip() == "snapshots":
                self._normalize_snapshot_layout()
            folder, _kind = self._resolve_export_dir(session_name)
            if folder is None:
                return False, "Session folder not found."
            with zipfile.ZipFile(fileobj, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for child in sorted(folder.rglob("*")):
                    if not child.is_file():
                        continue
                    archive.write(child, arcname=str(Path(folder.name) / child.relative_to(folder)))
        return True, folder.name

    def delete_folder(self, session_name: str):
        target, kind = self._resolve_export_dir(session_name)
        if target is None:
            return False, "Session folder not found."
        with self._lock:
            if kind == "session" and self.recording and self.session_path is not None and target == self.session_path:
                return False, "Stop recording before deleting the active session."
        removed_files = 0
        removed_dirs = 0
        for child in sorted(target.rglob("*"), reverse=True):
            try:
                if child.is_file() or child.is_symlink():
                    child.unlink(missing_ok=True)
                    removed_files += 1
                elif child.is_dir():
                    child.rmdir()
                    removed_dirs += 1
            except Exception as exc:
                return False, f"Failed to delete {target.name}: {exc}"
        try:
            target.rmdir()
        except Exception as exc:
            return False, f"Failed to delete {target.name}: {exc}"
        if kind == "snapshots":
            self.snapshot_dir.mkdir(parents=True, exist_ok=True)
            with self._lock:
                self.last_snapshot_relpath = ""
                self.last_snapshot_name = ""
        else:
            with self._lock:
                if self.last_session_path == target:
                    self.last_session_path = None
                    self.last_session_name = ""
                    self.last_record_relpath = ""
        return True, f"Deleted {target.name} ({removed_files} files, {removed_dirs} folders)."
