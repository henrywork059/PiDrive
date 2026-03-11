from __future__ import annotations

import json
import time
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
        self.flush_interval = 0.75
        self._last_flush_time = 0.0

    def start(self):
        if self.recording:
            return
        self.session_name = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.session_path = self.root / self.session_name
        self.images_dir = self.session_path / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = (self.session_path / "records.jsonl").open("a", encoding="utf-8", buffering=1)
        self.recording = True
        self.last_record_time = 0.0
        self.counter = 0
        self._last_flush_time = time.time()
        print(f"[REC] session started: {self.session_path}")

    def stop(self):
        if not self.recording:
            return
        self.recording = False
        try:
            if self.index_file is not None:
                self.index_file.flush()
                self.index_file.close()
        except Exception:
            pass
        self.index_file = None
        self.images_dir = None
        self.session_path = None
        print("[REC] session stopped")

    def toggle(self):
        if self.recording:
            self.stop()
        else:
            self.start()

    def maybe_record(self, frame_bgr, snapshot: dict):
        if not self.recording or frame_bgr is None or cv2 is None:
            return
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
        if (now - self._last_flush_time) >= self.flush_interval:
            self.index_file.flush()
            self._last_flush_time = now

    def list_sessions(self):
        items = []
        for path in sorted(self.root.glob("*"), reverse=True):
            if path.is_dir():
                items.append(path.name)
        return items
