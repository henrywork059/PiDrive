
# data_recorder.py
"""Simple session recorder for Pi-Car.

Goals:
- Keep it **easy to debug** and reason about.
- Record enough information for the PC trainer:
    * image file path
    * steering
    * throttle
    * mode
    * timestamp
- Stay backwards compatible with the existing `control_api.py`,
  which expects a `DataRecorder` class with:
    - attributes: `recording`
    - methods: `start()`, `stop()`, `toggle()`, `maybe_record(camera, control_state)`

Recorded format (per session):

    data/records/
        YYYYMMDD-HHMMSS/
            images/
                20260305-101530-123456_000001.jpg
                20260305-101530-223789_000002.jpg
                ...
            records.jsonl

Each line of `records.jsonl` is a JSON object:

    {
      "frame": 1,
      "frame_id": 1,
      "session": "20260305-101530",
      "ts": 1700000000.123,
      "image": "images/20260305-101530-123456_000001.jpg",
      "image_id": "20260305-101530-123456_000001",
      "cam_w": 426,
      "cam_h": 240,
      "format": "BGR888",
      "steering": 0.12,
      "throttle": 0.45,
      "mode": "manual"
    }

This is intentionally simple so the PC trainer can be adapted easily.
"""

import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import cv2
import numpy as np

try:
    from camera import Camera  # type: ignore
except Exception:  # pragma: no cover
    Camera = object  # dummy for type hints


class DataRecorder:
    """Minimal recorder class used by control_api.

    Public attributes:
        - recording: bool

    Public methods:
        - start()
        - stop()
        - toggle()
        - maybe_record(camera, control_state)
    """

    def __init__(self, root: str = "data/records") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

        self.recording: bool = False
        self.session_path: Optional[Path] = None
        self.images_dir: Optional[Path] = None
        self.index_file = None
        self.frame_id: int = 0

        self.last_record_time: float = 0.0
        # Limit capture rate so we don't flood the Pi SD card
        self.min_interval: float = 0.1  # seconds (~10 Hz max)

    # --------------------------------------------------------------
    # Recording control
    # --------------------------------------------------------------
    def start(self) -> None:
        """Begin recording a new session (if not already)."""
        if self.recording:
            return

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.session_path = self.root / ts
        self.images_dir = self.session_path / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)

        self.index_file = (self.session_path / "records.jsonl").open(
            "a", encoding="utf-8"
        )
        self.frame_id = 0
        self.last_record_time = 0.0
        self.recording = True

        print(f"[REC] Session started: {self.session_path}")

    def stop(self) -> None:
        """Stop recording and close the current session."""
        if not self.recording:
            return

        self.recording = False

        try:
            if self.index_file is not None:
                self.index_file.close()
        except Exception:
            pass

        self.index_file = None
        self.session_path = None
        self.images_dir = None

        print("[REC] Session stopped")

    def toggle(self) -> None:
        """Toggle recording on/off."""
        if self.recording:
            self.stop()
        else:
            self.start()

    # --------------------------------------------------------------
    # Main entry point called from control_api.handle_control_post()
    # --------------------------------------------------------------
    def maybe_record(self, camera: "Camera", control_state: Dict[str, Any]) -> None:
        """Called on each /api/control POST.

        - If not recording: do nothing.
        - If recording and min_interval elapsed:
            * grab current JPEG frame
            * decode & save as images/XXXXXX.jpg
            * append JSON line to records.jsonl
        """
        if not self.recording:
            return

        if self.session_path is None or self.images_dir is None or self.index_file is None:
            # Should not happen, but fail-safe
            print("[REC] WARNING: recording=True but session not initialised")
            return

        now = time.time()
        if now - self.last_record_time < self.min_interval:
            return
        self.last_record_time = now

        # Get JPEG bytes from camera
        frame_bytes = camera.get_jpeg_frame()
        if frame_bytes is None:
            return

        # Decode JPEG to BGR image
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return

        # Camera metadata (requested to be stored in records.jsonl)
        session = self.session_path.name
        cam_w = int(getattr(camera, "width", 0) or 0)
        cam_h = int(getattr(camera, "height", 0) or 0)
        cam_format = str(getattr(camera, "format", "BGR888"))

        # Save image
        # Use a timestamp-based filename so that:
        #   1) frames are naturally sortable by capture time
        #   2) filenames remain unique even if users merge sessions later
        # We still keep a monotonically increasing frame counter for easy debugging.
        self.frame_id += 1
        ts_id = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        fname = f"{ts_id}_{self.frame_id:06d}.jpg"
        img_path = self.images_dir / fname
        cv2.imwrite(str(img_path), frame)

        # Actual stored image size (may differ from camera capture config
        # if we record from a resized preview stream)
        img_h, img_w = frame.shape[:2]

        rec = {
            "frame": self.frame_id,
            "frame_id": self.frame_id,
            "session": session,
            "ts": now,
            "image": f"images/{fname}",
            "image_id": f"{ts_id}_{self.frame_id:06d}",
            "cam_w": cam_w,
            "cam_h": cam_h,
            "format": cam_format,
            "img_w": int(img_w),
            "img_h": int(img_h),
            "image_format": "jpg",
            "steering": float(control_state.get("steering", 0.0)),
            "throttle": float(control_state.get("throttle", 0.0)),
            "mode": str(control_state.get("mode", "manual")),
        }

        line = json.dumps(rec, ensure_ascii=False)
        self.index_file.write(line + "\n")
        self.index_file.flush()

        print(
            f"[REC] frame={self.frame_id:06d} "
            f"steer={rec['steering']:+.2f} thr={rec['throttle']:.2f} mode={rec['mode']}"
        )
