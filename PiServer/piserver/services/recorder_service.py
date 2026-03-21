from __future__ import annotations

import json
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path

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

    def start(self):
        with self._lock:
            if self.recording:
                return
            session_name = datetime.now().strftime("%Y%m%d-%H%M%S")
            session_path = self.root / session_name
            images_dir = session_path / "images"
            index_file = None
            try:
                images_dir.mkdir(parents=True, exist_ok=True)
                index_file = (session_path / "records.jsonl").open("a", encoding="utf-8")
            except Exception:
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
            if self.images_dir is None or self.index_file is None:
                return
            now = time.time()
            if now - self.last_record_time < self.min_interval:
                return
            self.last_record_time = now
            self.counter += 1

            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            fname = f"{stamp}_{self.counter:04d}.jpg"
            image_path = self.images_dir / fname
            ok = cv2.imwrite(str(image_path), frame_bgr)
            if not ok:
                return

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
            self.index_file.write(json.dumps(rec, ensure_ascii=False) + "\n")
            self.index_file.flush()
            self.last_record_relpath = str(Path("records") / self.session_name / "images" / fname)

    def capture_once(self, frame_bgr, snapshot: dict | None = None):
        if frame_bgr is None or cv2 is None:
            return False, "No live frame available to save."
        snapshot = snapshot or {}
        shots_dir = self.snapshot_dir
        shots_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        image_name = f"{stamp}.jpg"
        image_path = shots_dir / image_name
        ok = cv2.imwrite(str(image_path), frame_bgr)
        if not ok:
            return False, "Failed to save snapshot image."

        meta_path = shots_dir / "snapshots.jsonl"
        rec = {
            "frame_id": stamp,
            "ts": time.time(),
            "image": f"snapshots/{image_name}",
            "steering": float(snapshot.get("applied_steering", 0.0)),
            "throttle": float(snapshot.get("applied_throttle", 0.0)),
            "mode": str(snapshot.get("active_algorithm", "manual")),
            "camera_width": int(snapshot.get("camera_width", 0)),
            "camera_height": int(snapshot.get("camera_height", 0)),
            "camera_format": str(snapshot.get("camera_format", "BGR888")),
        }
        with self._lock:
            self.last_snapshot_name = image_name
            self.last_snapshot_relpath = str(Path("records") / "snapshots" / image_name)
            with meta_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return True, f"Snapshot saved: {image_name}"

    def get_status(self):
        with self._lock:
            active_session_name = self.session_name or self.last_session_name
            active_session_path = self.session_path or self.last_session_path
            elapsed = 0.0
            if self.recording and self.session_started_at:
                elapsed = max(0.0, time.time() - self.session_started_at)
            return {
                "record_session_name": active_session_name,
                "record_save_path": str(active_session_path.relative_to(self.root.parent)) if active_session_path else str(Path("records")),
                "record_elapsed_seconds": elapsed,
                "record_last_saved": self.last_record_relpath,
                "snapshot_save_path": str(self.snapshot_dir.relative_to(self.root.parent)),
                "snapshot_last_saved": self.last_snapshot_relpath,
                "snapshot_last_name": self.last_snapshot_name,
            }

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
            "updated_at": updated_at,
            "path": str(path.relative_to(self.root.parent)),
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
        items = []
        if self.snapshot_dir.exists():
            items.append(self._build_folder_item(self.snapshot_dir, kind="snapshots"))
        for path in self._iter_session_dirs():
            items.append(self._build_folder_item(path, kind="session"))
        return items

    def write_session_zip(self, session_name: str, fileobj):
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
