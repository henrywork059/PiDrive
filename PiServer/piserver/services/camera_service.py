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
    def __init__(self, width: int = 426, height: int = 240, fps: int = 30, camera_format: str = "BGR888"):
        self.width = int(width)
        self.height = int(height)
        self.target_fps = int(fps)
        self.camera_format = str(camera_format or "BGR888")
        self.auto_exposure = True
        self.exposure_time = 12000
        self.analogue_gain = 1.5
        self.exposure_compensation = 0.0
        self.auto_white_balance = True
        self.brightness = 0.0
        self.contrast = 1.0
        self.saturation = 1.0
        self.sharpness = 1.0
        self.backend = "idle"
        self._frame = None
        self._jpeg_frame = None
        self._frame_seq = 0
        self._frame_ready = threading.Condition()
        self._io_lock = threading.RLock()
        self._running = False
        self._thread = None
        self._fps = 0.0
        self._capture = None
        self._picam2 = None
        self._jpeg_quality = 76
        self._processing_enabled = False
        self._stream_clients = 0
        self._idle_sleep = 0.25
        self._demand_event = threading.Event()

    def _has_demand(self) -> bool:
        return bool(self._processing_enabled or self._stream_clients > 0)

    def set_processing_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        changed = enabled != self._processing_enabled
        self._processing_enabled = enabled
        if enabled:
            self._demand_event.set()
        elif not self._stream_clients:
            self._demand_event.clear()
        if changed and enabled:
            with self._frame_ready:
                self._frame_ready.notify_all()

    def add_stream_client(self) -> None:
        self._stream_clients += 1
        self._demand_event.set()
        with self._frame_ready:
            self._frame_ready.notify_all()

    def remove_stream_client(self) -> None:
        self._stream_clients = max(0, self._stream_clients - 1)
        if not self._has_demand():
            self._demand_event.clear()

    def _apply_picamera_controls_locked(self) -> None:
        if self._picam2 is None:
            return
        controls = {
            "AeEnable": bool(self.auto_exposure),
            "AwbEnable": bool(self.auto_white_balance),
            "Brightness": float(self.brightness),
            "Contrast": float(self.contrast),
            "Saturation": float(self.saturation),
            "Sharpness": float(self.sharpness),
            "ExposureValue": float(self.exposure_compensation),
        }
        if not self.auto_exposure:
            controls["ExposureTime"] = int(self.exposure_time)
            controls["AnalogueGain"] = float(self.analogue_gain)
        try:
            self._picam2.set_controls(controls)
        except Exception:
            pass

    def _apply_opencv_controls_locked(self) -> None:
        if self._capture is None or cv2 is None:
            return
        pairs = [
            (getattr(cv2, "CAP_PROP_FRAME_WIDTH", None), self.width),
            (getattr(cv2, "CAP_PROP_FRAME_HEIGHT", None), self.height),
            (getattr(cv2, "CAP_PROP_FPS", None), self.target_fps),
            (getattr(cv2, "CAP_PROP_BRIGHTNESS", None), self.brightness),
            (getattr(cv2, "CAP_PROP_CONTRAST", None), self.contrast),
            (getattr(cv2, "CAP_PROP_SATURATION", None), self.saturation),
            (getattr(cv2, "CAP_PROP_SHARPNESS", None), self.sharpness),
        ]
        if hasattr(cv2, "CAP_PROP_AUTO_EXPOSURE"):
            pairs.append((cv2.CAP_PROP_AUTO_EXPOSURE, 0.75 if self.auto_exposure else 0.25))
        if hasattr(cv2, "CAP_PROP_EXPOSURE"):
            pairs.append((cv2.CAP_PROP_EXPOSURE, float(self.exposure_time)))
        if hasattr(cv2, "CAP_PROP_GAIN"):
            pairs.append((cv2.CAP_PROP_GAIN, float(self.analogue_gain)))
        for prop, value in pairs:
            if prop is None:
                continue
            try:
                self._capture.set(prop, value)
            except Exception:
                pass

    def _apply_live_controls_locked(self) -> None:
        self._apply_picamera_controls_locked()
        self._apply_opencv_controls_locked()

    def _open_backend(self) -> None:
        self.backend = "placeholder"
        self._picam2 = None
        self._capture = None

        if Picamera2 is not None:
            try:
                self._picam2 = Picamera2()
                cfg = self._picam2.create_video_configuration(
                    main={"size": (self.width, self.height), "format": self.camera_format}
                )
                self._picam2.configure(cfg)
                self._picam2.start()
                self.backend = "picamera2"
                self._apply_picamera_controls_locked()
                return
            except Exception:
                self._picam2 = None

        if cv2 is not None:
            try:
                cap = cv2.VideoCapture(0)
                if cap is not None and cap.isOpened():
                    self._capture = cap
                    self.backend = "opencv"
                    self._apply_opencv_controls_locked()
                    return
            except Exception:
                self._capture = None

    def _close_backend(self) -> None:
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
        self._picam2 = None
        self._capture = None
        if not self._has_demand():
            self.backend = "idle"
            self._fps = 0.0

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def apply_settings(
        self,
        *,
        width: int | None = None,
        height: int | None = None,
        fps: int | None = None,
        camera_format: str | None = None,
        auto_exposure: bool | None = None,
        exposure_time: int | None = None,
        analogue_gain: float | None = None,
        exposure_compensation: float | None = None,
        auto_white_balance: bool | None = None,
        brightness: float | None = None,
        contrast: float | None = None,
        saturation: float | None = None,
        sharpness: float | None = None,
    ) -> dict:
        reopen_required = False
        changed = False
        with self._io_lock:
            if width is not None:
                width = max(160, min(1920, int(width)))
                reopen_required = reopen_required or width != self.width
                self.width = width
                changed = True
            if height is not None:
                height = max(120, min(1080, int(height)))
                reopen_required = reopen_required or height != self.height
                self.height = height
                changed = True
            if fps is not None:
                fps = max(1, min(120, int(fps)))
                reopen_required = reopen_required or fps != self.target_fps
                self.target_fps = fps
                changed = True
            if camera_format:
                camera_format = str(camera_format)
                reopen_required = reopen_required or camera_format != self.camera_format
                self.camera_format = camera_format
                changed = True
            if auto_exposure is not None:
                self.auto_exposure = bool(auto_exposure)
                changed = True
            if exposure_time is not None:
                self.exposure_time = max(100, min(200000, int(exposure_time)))
                changed = True
            if analogue_gain is not None:
                self.analogue_gain = max(1.0, min(16.0, float(analogue_gain)))
                changed = True
            if exposure_compensation is not None:
                self.exposure_compensation = max(-8.0, min(8.0, float(exposure_compensation)))
                changed = True
            if auto_white_balance is not None:
                self.auto_white_balance = bool(auto_white_balance)
                changed = True
            if brightness is not None:
                self.brightness = max(-1.0, min(1.0, float(brightness)))
                changed = True
            if contrast is not None:
                self.contrast = max(0.0, min(4.0, float(contrast)))
                changed = True
            if saturation is not None:
                self.saturation = max(0.0, min(4.0, float(saturation)))
                changed = True
            if sharpness is not None:
                self.sharpness = max(0.0, min(4.0, float(sharpness)))
                changed = True

            if changed and (self._picam2 is not None or self._capture is not None):
                if reopen_required:
                    self._close_backend()
                    if self._has_demand():
                        self._open_backend()
                else:
                    self._apply_live_controls_locked()
        if changed and self._has_demand():
            self._demand_event.set()
        return {
            "width": self.width,
            "height": self.height,
            "fps": self.target_fps,
            "camera_format": self.camera_format,
            "auto_exposure": self.auto_exposure,
            "exposure_time": self.exposure_time,
            "analogue_gain": self.analogue_gain,
            "exposure_compensation": self.exposure_compensation,
            "auto_white_balance": self.auto_white_balance,
            "brightness": self.brightness,
            "contrast": self.contrast,
            "saturation": self.saturation,
            "sharpness": self.sharpness,
        }

    def _placeholder_frame(self):
        if cv2 is None or np is None:
            return None
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        frame[:] = (18, 20, 26)
        cv2.putText(frame, "PiServer camera placeholder", (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 210, 240), 2, cv2.LINE_AA)
        cv2.putText(frame, f"Backend: {self.backend}", (20, 86),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (130, 180, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, f"{self.width}x{self.height} @ {self.target_fps}fps", (20, 122),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 190, 200), 2, cv2.LINE_AA)
        cv2.putText(frame, f"AE {'on' if self.auto_exposure else 'locked'} | AWB {'on' if self.auto_white_balance else 'locked'}", (20, 158),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (180, 190, 200), 2, cv2.LINE_AA)
        return frame

    def _encode_jpeg(self, frame) -> Optional[bytes]:
        if cv2 is None or frame is None:
            return None
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), self._jpeg_quality])
        return buf.tobytes() if ok else None

    def _normalize_frame(self, frame):
        if frame is None or np is None:
            return frame
        if len(frame.shape) == 3 and frame.shape[2] == 4 and cv2 is not None:
            try:
                return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            except Exception:
                return frame[:, :, :3]
        return frame

    def _publish_frame(self, frame) -> None:
        frame = self._normalize_frame(frame)
        jpeg = self._encode_jpeg(frame)
        with self._frame_ready:
            self._frame = frame
            self._jpeg_frame = jpeg
            self._frame_seq += 1
            self._frame_ready.notify_all()

    def _ensure_backend_open(self) -> None:
        with self._io_lock:
            if self._picam2 is None and self._capture is None:
                self._open_backend()

    def _idle_if_needed(self) -> bool:
        if self._has_demand():
            return False
        with self._io_lock:
            if self._picam2 is not None or self._capture is not None:
                self._close_backend()
        self._demand_event.wait(timeout=self._idle_sleep)
        return True

    def _loop(self):
        last_tick = time.perf_counter()
        fps_count = 0
        fps_window_start = time.perf_counter()
        while self._running:
            if self._idle_if_needed():
                last_tick = time.perf_counter()
                fps_count = 0
                fps_window_start = last_tick
                continue

            self._ensure_backend_open()
            min_period = 1.0 / max(self.target_fps, 1)
            frame = None
            with self._io_lock:
                picam2 = self._picam2
                capture = self._capture
                backend = self.backend

            if picam2 is not None:
                try:
                    frame = picam2.capture_array()
                except Exception:
                    frame = None
            elif capture is not None:
                try:
                    ok, frame = capture.read()
                    if not ok:
                        frame = None
                except Exception:
                    frame = None
            elif self._stream_clients > 0:
                backend = "placeholder"
                self.backend = backend
                frame = self._placeholder_frame()

            if frame is not None:
                self._publish_frame(frame)

            now = time.perf_counter()
            fps_count += 1
            elapsed = now - fps_window_start
            if elapsed >= 1.0:
                self._fps = fps_count / elapsed if fps_count > 0 else 0.0
                fps_count = 0
                fps_window_start = now

            dt = now - last_tick
            if dt < min_period:
                time.sleep(min_period - dt)
            last_tick = time.perf_counter()

    def get_latest_frame_packet(self, *, copy: bool = True):
        with self._frame_ready:
            if self._frame is None:
                return None, int(self._frame_seq)
            frame = self._frame.copy() if copy else self._frame
            return frame, int(self._frame_seq)

    def get_latest_frame(self, *, copy: bool = True):
        with self._frame_ready:
            if self._frame is None:
                return None
            return self._frame.copy() if copy else self._frame

    def get_latest_frame_seq(self) -> int:
        with self._frame_ready:
            return int(self._frame_seq)

    def wait_for_frame(self, last_seq: int = -1, timeout: float = 1.0) -> int:
        with self._frame_ready:
            if self._frame_seq == last_seq:
                self._frame_ready.wait(timeout=timeout)
            return int(self._frame_seq)

    def get_jpeg_frame(self) -> Optional[bytes]:
        with self._frame_ready:
            return self._jpeg_frame

    def get_fps(self) -> float:
        return float(self._fps)

    def close(self) -> None:
        self._running = False
        self._demand_event.set()
        with self._io_lock:
            self._close_backend()
