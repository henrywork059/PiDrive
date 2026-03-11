from __future__ import annotations

import threading
import time
from typing import Optional

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:
    from picamera2 import Picamera2  # type: ignore
except Exception:  # pragma: no cover
    Picamera2 = None  # type: ignore


class CameraService:
    def __init__(self, width: int = 426, height: int = 240, fps: int = 30):
        self.width = int(width)
        self.height = int(height)
        self.target_fps = int(fps)
        self.camera_format = "BGR888"
        self.backend = "placeholder"
        self._frame = None
        self._lock = threading.Lock()
        self._running = False
        self._fps = 0.0
        self._capture = None
        self._picam2 = None

    def start(self) -> None:
        if self._running:
            return

        if Picamera2 is not None:
            try:
                self._picam2 = Picamera2()
                cfg = self._picam2.create_video_configuration(
                    main={"size": (self.width, self.height), "format": self.camera_format}
                )
                self._picam2.configure(cfg)
                self._picam2.start()
                self.backend = "picamera2"
            except Exception:
                self._picam2 = None

        if self._picam2 is None and cv2 is not None:
            try:
                cap = cv2.VideoCapture(0)
                if cap is not None and cap.isOpened():
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    cap.set(cv2.CAP_PROP_FPS, self.target_fps)
                    self._capture = cap
                    self.backend = "opencv"
            except Exception:
                self._capture = None

        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _placeholder_frame(self):
        if cv2 is None or np is None:
            return None
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        frame[:] = (18, 20, 26)
        cv2.putText(frame, "PiServer camera placeholder", (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 210, 240), 2, cv2.LINE_AA)
        cv2.putText(frame, f"Backend: {self.backend}", (20, 86),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (130, 180, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, time.strftime("%Y-%m-%d %H:%M:%S"), (20, 122),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 190, 200), 2, cv2.LINE_AA)
        return frame

    def _loop(self):
        min_period = 1.0 / max(self.target_fps, 1)
        last_tick = time.time()
        fps_count = 0
        fps_window_start = time.time()

        while self._running:
            frame = None
            if self._picam2 is not None:
                try:
                    frame = self._picam2.capture_array()
                except Exception:
                    frame = None
            elif self._capture is not None:
                try:
                    ok, frame = self._capture.read()
                    if not ok:
                        frame = None
                except Exception:
                    frame = None

            if frame is None:
                frame = self._placeholder_frame()

            if frame is not None:
                with self._lock:
                    self._frame = frame.copy()

            now = time.time()
            fps_count += 1
            elapsed = now - fps_window_start
            if elapsed >= 1.0:
                self._fps = fps_count / elapsed
                fps_count = 0
                fps_window_start = now

            dt = now - last_tick
            if dt < min_period:
                time.sleep(min_period - dt)
            last_tick = time.time()

    def get_latest_frame(self):
        with self._lock:
            if self._frame is None:
                return None
            return self._frame.copy()

    def get_jpeg_frame(self) -> Optional[bytes]:
        if cv2 is None:
            return None
        frame = self.get_latest_frame()
        if frame is None:
            return None
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        return buf.tobytes() if ok else None

    def get_fps(self) -> float:
        return float(self._fps)

    def close(self) -> None:
        self._running = False
        try:
            if self._picam2 is not None:
                self._picam2.stop()
                self._picam2.close()
        except Exception:
            pass
        try:
            if self._capture is not None:
                self._capture.release()
        except Exception:
            pass
