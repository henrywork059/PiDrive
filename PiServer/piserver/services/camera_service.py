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

        self.auto_exposure = True
        self.exposure_us = 12000
        self.analogue_gain = 1.0
        self.exposure_compensation = 0.0
        self.auto_white_balance = True
        self.brightness = 0.0
        self.contrast = 1.0
        self.saturation = 1.0
        self.sharpness = 1.0

        self._frame = None
        self._frame_lock = threading.Lock()
        self._service_lock = threading.RLock()
        self._running = False
        self._fps = 0.0
        self._capture = None
        self._picam2 = None
        self._thread = None

    def _clamp_float(self, value, default: float, min_value: float, max_value: float) -> float:
        try:
            value = float(value)
        except Exception:
            value = default
        return max(min_value, min(max_value, value))

    def _clamp_int(self, value, default: int, min_value: int, max_value: int) -> int:
        try:
            value = int(value)
        except Exception:
            value = default
        return max(min_value, min(max_value, value))

    def apply_settings(self, settings: dict | None, restart: bool = True) -> tuple[bool, str, dict]:
        settings = settings or {}
        with self._service_lock:
            self.width = self._clamp_int(settings.get("width", self.width), self.width, 64, 3840)
            self.height = self._clamp_int(settings.get("height", self.height), self.height, 48, 2160)
            self.target_fps = self._clamp_int(settings.get("fps", self.target_fps), self.target_fps, 1, 120)
            self.camera_format = str(settings.get("format", self.camera_format) or self.camera_format)
            self.auto_exposure = bool(settings.get("auto_exposure", self.auto_exposure))
            self.exposure_us = self._clamp_int(settings.get("exposure_us", self.exposure_us), self.exposure_us, 100, 200000)
            self.analogue_gain = self._clamp_float(settings.get("analogue_gain", self.analogue_gain), self.analogue_gain, 0.0, 64.0)
            self.exposure_compensation = self._clamp_float(
                settings.get("exposure_compensation", self.exposure_compensation),
                self.exposure_compensation,
                -8.0,
                8.0,
            )
            self.auto_white_balance = bool(settings.get("auto_white_balance", self.auto_white_balance))
            self.brightness = self._clamp_float(settings.get("brightness", self.brightness), self.brightness, -1.0, 1.0)
            self.contrast = self._clamp_float(settings.get("contrast", self.contrast), self.contrast, 0.0, 32.0)
            self.saturation = self._clamp_float(settings.get("saturation", self.saturation), self.saturation, 0.0, 32.0)
            self.sharpness = self._clamp_float(settings.get("sharpness", self.sharpness), self.sharpness, 0.0, 16.0)
            running = self._running

        if restart and running:
            return self.restart()
        return True, "Camera settings updated.", self.get_config()

    def get_config(self) -> dict:
        with self._service_lock:
            return {
                "width": int(self.width),
                "height": int(self.height),
                "fps": int(self.target_fps),
                "format": str(self.camera_format),
                "auto_exposure": bool(self.auto_exposure),
                "exposure_us": int(self.exposure_us),
                "analogue_gain": float(self.analogue_gain),
                "exposure_compensation": float(self.exposure_compensation),
                "auto_white_balance": bool(self.auto_white_balance),
                "brightness": float(self.brightness),
                "contrast": float(self.contrast),
                "saturation": float(self.saturation),
                "sharpness": float(self.sharpness),
                "backend": str(self.backend),
            }

    def _set_picamera_controls(self) -> None:
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
            controls["ExposureTime"] = int(self.exposure_us)
            controls["AnalogueGain"] = float(self.analogue_gain)
        try:
            self._picam2.set_controls(controls)
        except Exception:
            pass

    def _open_backend_locked(self) -> None:
        self.backend = "placeholder"
        self._picam2 = None
        self._capture = None

        if Picamera2 is not None:
            try:
                self._picam2 = Picamera2()
                cfg = self._picam2.create_video_configuration(
                    main={"size": (self.width, self.height), "format": self.camera_format},
                    controls={"FrameDurationLimits": (int(1_000_000 / max(self.target_fps, 1)), int(1_000_000 / max(self.target_fps, 1)))},
                )
                self._picam2.configure(cfg)
                self._picam2.start()
                self._set_picamera_controls()
                self.backend = "picamera2"
                return
            except Exception:
                try:
                    if self._picam2 is not None:
                        self._picam2.close()
                except Exception:
                    pass
                self._picam2 = None

        if cv2 is not None:
            cap = None
            try:
                cap = cv2.VideoCapture(0)
                if cap is not None and cap.isOpened():
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    cap.set(cv2.CAP_PROP_FPS, self.target_fps)
                    try:
                        cap.set(cv2.CAP_PROP_BRIGHTNESS, self.brightness)
                        cap.set(cv2.CAP_PROP_CONTRAST, self.contrast)
                        cap.set(cv2.CAP_PROP_SATURATION, self.saturation)
                        if not self.auto_exposure:
                            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
                            cap.set(cv2.CAP_PROP_EXPOSURE, float(self.exposure_us))
                        else:
                            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
                    except Exception:
                        pass
                    self._capture = cap
                    self.backend = "opencv"
                    return
            except Exception:
                try:
                    if cap is not None:
                        cap.release()
                except Exception:
                    pass
                self._capture = None

    def start(self) -> None:
        with self._service_lock:
            if self._running:
                return
            self._open_backend_locked()
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def restart(self) -> tuple[bool, str, dict]:
        self.close()
        self.start()
        return True, f"Camera restarted using {self.backend}.", self.get_config()

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
        cv2.putText(frame, time.strftime("%Y-%m-%d %H:%M:%S"), (20, 158),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 190, 200), 2, cv2.LINE_AA)
        return frame

    def _loop(self):
        last_tick = time.time()
        fps_count = 0
        fps_window_start = time.time()

        while True:
            with self._service_lock:
                if not self._running:
                    break
                picam = self._picam2
                capture = self._capture
                target_fps = max(int(self.target_fps), 1)

            frame = None
            if picam is not None:
                try:
                    frame = picam.capture_array()
                except Exception:
                    frame = None
            elif capture is not None:
                try:
                    ok, frame = capture.read()
                    if not ok:
                        frame = None
                except Exception:
                    frame = None

            if frame is None:
                frame = self._placeholder_frame()

            if frame is not None:
                with self._frame_lock:
                    self._frame = frame.copy()

            now = time.time()
            fps_count += 1
            elapsed = now - fps_window_start
            if elapsed >= 1.0:
                self._fps = fps_count / elapsed
                fps_count = 0
                fps_window_start = now

            min_period = 1.0 / target_fps
            dt = now - last_tick
            if dt < min_period:
                time.sleep(min_period - dt)
            last_tick = time.time()

    def get_latest_frame(self):
        with self._frame_lock:
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
        thread = None
        with self._service_lock:
            self._running = False
            thread = self._thread
            self._thread = None

        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)

        with self._service_lock:
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
