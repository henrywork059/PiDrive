import time
import threading
from typing import Optional

import cv2
try:
    import numpy as np
except Exception:  # very low risk on Pi, but be defensive
    np = None

from picamera2 import Picamera2

TFLITE_W = 200
TFLITE_H = 112

# Number of frames to use for one-off colour calibration.
# We assume lighting is roughly constant on the track.
_CALIBRATION_FRAMES = 30


class Camera:
    def __init__(self, width: int = 426, height: int = 240, fps: int = 30) -> None:
        self.width = width
        self.height = height
        self.fps = fps

        # Picamera2 pixel format string (useful to store into recordings)
        self.format = "BGR888"

        self._frame = None          # colour-corrected BGR frame
        self._raw_frame = None      # raw BGR frame from the sensor
        self._lock = threading.Lock()
        self._running = False

        # One-off colour calibration state
        self._color_gains = None    # np.ndarray shape (3,) in BGR order
        self._calibration_frames = 0
        self._sum_means = None

        self.picam2 = Picamera2()
        cfg = self.picam2.create_video_configuration(
            main={"size": (width, height), "format": self.format}
        )
        self.picam2.configure(cfg)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _maybe_update_gains(self, frame) -> None:
        """Accumulate a few frames and estimate simple per-channel gains.

        We treat the green channel as reference (gain 1.0) and scale
        blue/red towards it. This is similar in spirit to a gray-world
        white balance, but we only compute it once at start-up so that
        colours stay stable over time.
        """
        if np is None:
            return
        if self._color_gains is not None:
            return

        self._calibration_frames += 1
        if self._calibration_frames == 1:
            self._sum_means = np.zeros(3, dtype="float64")

        self._sum_means += frame.mean(axis=(0, 1))

        if self._calibration_frames >= _CALIBRATION_FRAMES:
            means = self._sum_means / float(self._calibration_frames)
            # Avoid division by zero and crazy values.
            means = np.clip(means, 1.0, 1024.0)
            # Keep green as reference channel.
            g_ref = means[1]
            gains = g_ref / means
            # Clamp to a sane range.
            gains = np.clip(gains, 0.5, 2.5)
            self._color_gains = gains

    def _apply_gains(self, frame):
        if np is None or self._color_gains is None:
            return frame
        try:
            gains = self._color_gains
            corrected = frame.astype("float32")
            for c in range(3):
                corrected[:, :, c] *= gains[c]
            corrected = corrected.clip(0, 255).astype("uint8")
            return corrected
        except Exception:
            # In case anything goes wrong, just fall back to the raw frame.
            return frame

    # ------------------------------------------------------------------
    # Public API used by the rest of the app
    # ------------------------------------------------------------------
    def start(self) -> None:
        if self._running:
            return
        self.picam2.start()
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self) -> None:
        """Background capture loop.

        We maintain a minimum frame interval so we don't overload the Pi.
        """
        min_dt = 1.0 / max(self.fps, 1)
        last = time.time()
        while self._running:
            f = self.picam2.capture_array()
            if f is not None:
                # Update calibration and corrected frame.
                self._maybe_update_gains(f)
                corrected = self._apply_gains(f)
                with self._lock:
                    self._raw_frame = f
                    self._frame = corrected

            now = time.time()
            dt = now - last
            last = now
            if dt < min_dt:
                time.sleep(min_dt - dt)

    def get_latest_frame(self):
        """Return the colour-corrected BGR frame for model + recording."""
        with self._lock:
            if self._frame is None:
                return None
            return self._frame.copy()

    # Backwards-compat alias
    get_frame = get_latest_frame

    def get_jpeg_frame(self):
        """Return a JPEG-encoded preview frame for the web UI.

        The frame is colour-corrected in BGR, then converted to RGB before
        JPEG encoding so that browsers display it correctly.
        """
        f = self.get_latest_frame()
        if f is None:
            return None
        try:
            f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
        except Exception:
            # If cvtColor fails, just try to continue with the original.
            pass
        try:
            f = cv2.resize(f, (TFLITE_W, TFLITE_H), interpolation=cv2.INTER_AREA)
        except Exception:
            # If resize fails, fall back to the original resolution.
            pass
        ok, buf = cv2.imencode(".jpg", f, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        return buf.tobytes() if ok else None

    # Backwards-compat alias
    get_jpeg_bytes = get_jpeg_frame

    def close(self) -> None:
        self._running = False
        try:
            self.picam2.stop()
        except Exception:
            pass
        try:
            self.picam2.close()
        except Exception:
            pass
