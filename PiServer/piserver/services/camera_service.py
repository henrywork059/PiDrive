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


_CALIBRATION_FRAMES = 30


class CameraService:
    """Camera backend used by PiServer.

    This version stays closer to the older working PiCar camera flow:
    - Picamera2 is the preferred backend.
    - Frames are captured in a background loop.
    - A short one-off colour calibration stabilises preview colours.
    - OpenCV fallback is only used when Picamera2 is unavailable.
    """

    def __init__(self, width: int = 426, height: int = 240, fps: int = 30):
        self.width = int(width)
        self.height = int(height)
        self.target_fps = int(fps)
        self.camera_format = "BGR888"
        self.backend = "placeholder"
        self.backend_format = "unknown"

        self.auto_exposure = True
        self.exposure_us = 12000
        self.analogue_gain = 1.0
        self.exposure_compensation = 0.0
        self.auto_white_balance = True
        self.brightness = 0.0
        self.contrast = 1.0
        self.saturation = 1.0
        self.sharpness = 1.0

        self.preview_live = False
        self.last_error = ""
        self._frame = None
        self._raw_frame = None
        self._frame_lock = threading.Lock()
        self._service_lock = threading.RLock()
        self._running = False
        self._fps = 0.0
        self._capture = None
        self._picam2 = None
        self._thread = None
        self._last_open_attempt = 0.0
        self._retry_interval_s = 2.0

        self._color_gains = None
        self._calibration_frames = 0
        self._sum_means = None

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

    def _reset_color_calibration_locked(self) -> None:
        self._color_gains = None
        self._calibration_frames = 0
        self._sum_means = None

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
            self._reset_color_calibration_locked()

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
                "backend_format": str(self.backend_format),
                "preview_live": bool(self.preview_live),
                "last_error": str(self.last_error),
            }

    def _set_picamera_controls_locked(self) -> None:
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
        except Exception as exc:
            self.last_error = f"Failed to apply Picamera2 controls: {exc}"

    def _release_backends_locked(self) -> None:
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

    def _open_picamera2_locked(self) -> tuple[bool, str]:
        if Picamera2 is None:
            return False, "Picamera2 not installed."
        requested = str(self.camera_format or "BGR888").upper()
        formats = [requested]
        for fallback in ("BGR888", "RGB888", "XBGR8888"):
            if fallback not in formats:
                formats.append(fallback)

        last_error = "Unable to configure Picamera2."
        for fmt in formats:
            picam = None
            try:
                picam = Picamera2()
                frame_duration = max(1, int(1_000_000 / max(self.target_fps, 1)))
                cfg = picam.create_video_configuration(
                    main={"size": (self.width, self.height), "format": fmt},
                    controls={"FrameDurationLimits": (frame_duration, frame_duration)},
                )
                picam.configure(cfg)
                picam.start()
                self._picam2 = picam
                self.backend = "picamera2"
                self.backend_format = fmt
                self.preview_live = False
                self.last_error = ""
                self._set_picamera_controls_locked()
                return True, f"Picamera2 started with {fmt}."
            except Exception as exc:
                last_error = f"Picamera2 failed with {fmt}: {exc}"
                try:
                    picam.close()  # type: ignore[name-defined]
                except Exception:
                    pass
                self._picam2 = None
        return False, last_error

    def _open_opencv_locked(self) -> tuple[bool, str]:
        if cv2 is None:
            return False, "OpenCV not available."
        cap = None
        try:
            cap = cv2.VideoCapture(0)
            if cap is None or not cap.isOpened():
                if cap is not None:
                    cap.release()
                return False, "OpenCV camera index 0 did not open."
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            self._capture = cap
            self.backend = "opencv"
            self.backend_format = "BGR"
            self.preview_live = False
            self.last_error = ""
            return True, "OpenCV camera started."
        except Exception as exc:
            try:
                if cap is not None:
                    cap.release()
            except Exception:
                pass
            return False, f"OpenCV failed: {exc}"

    def _open_backend_locked(self) -> None:
        self._release_backends_locked()
        self.backend = "placeholder"
        self.backend_format = "unknown"
        self.preview_live = False
        self._last_open_attempt = time.time()
        self._reset_color_calibration_locked()

        ok, message = self._open_picamera2_locked()
        if ok:
            return
        picam_error = message

        ok, message = self._open_opencv_locked()
        if ok:
            return

        self.last_error = f"{picam_error} | {message}"

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
        config = self.get_config()
        if config.get("preview_live"):
            return True, f"Camera restarted using {self.backend}.", config
        return False, f"Camera restarted but live preview is not available. {config.get('last_error', '').strip()}".strip(), config

    def _maybe_update_gains(self, frame) -> None:
        if np is None or self._color_gains is not None or frame is None:
            return
        self._calibration_frames += 1
        if self._calibration_frames == 1:
            self._sum_means = np.zeros(3, dtype="float64")
        self._sum_means += frame.mean(axis=(0, 1))
        if self._calibration_frames >= _CALIBRATION_FRAMES:
            means = self._sum_means / float(self._calibration_frames)
            means = np.clip(means, 1.0, 1024.0)
            g_ref = means[1]
            gains = np.clip(g_ref / means, 0.5, 2.5)
            self._color_gains = gains

    def _apply_gains(self, frame):
        if np is None or self._color_gains is None or frame is None:
            return frame
        try:
            corrected = frame.astype("float32")
            for idx in range(3):
                corrected[:, :, idx] *= float(self._color_gains[idx])
            return corrected.clip(0, 255).astype("uint8")
        except Exception:
            return frame

    def _normalize_frame(self, frame):
        if cv2 is None or frame is None:
            return frame
        try:
            if getattr(frame, "ndim", 0) == 2:
                return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            if getattr(frame, "ndim", 0) == 3:
                channels = int(frame.shape[2])
                fmt = str(self.backend_format or self.camera_format or "").upper()
                if channels == 4:
                    if "RGB" in fmt and "BGR" not in fmt:
                        return cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
                    return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                if channels == 3 and fmt == "RGB888":
                    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return frame
        except Exception:
            return frame

    def _placeholder_frame(self):
        if cv2 is None or np is None:
            return None
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        frame[:] = (18, 20, 26)
        cv2.putText(frame, "PiServer camera unavailable", (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 210, 240), 2, cv2.LINE_AA)
        cv2.putText(frame, f"Backend: {self.backend}", (20, 86),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (130, 180, 255), 2, cv2.LINE_AA)
        if self.last_error:
            cv2.putText(frame, self.last_error[:64], (20, 122),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 190, 200), 1, cv2.LINE_AA)
        cv2.putText(frame, time.strftime("%Y-%m-%d %H:%M:%S"), (20, 158),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 190, 200), 2, cv2.LINE_AA)
        return frame

    def _capture_one_frame(self):
        picam = None
        capture = None
        with self._service_lock:
            picam = self._picam2
            capture = self._capture
        if picam is not None:
            try:
                frame = picam.capture_array()
                return self._normalize_frame(frame), True, ""
            except Exception as exc:
                return None, False, f"Picamera2 capture failed: {exc}"
        if capture is not None:
            try:
                ok, frame = capture.read()
                if ok and frame is not None:
                    return frame, True, ""
                return None, False, "OpenCV capture returned no frame."
            except Exception as exc:
                return None, False, f"OpenCV capture failed: {exc}"
        return None, False, "No active camera backend."

    def _loop(self):
        fps_count = 0
        fps_window_start = time.time()
        while True:
            with self._service_lock:
                if not self._running:
                    break
                target_fps = max(int(self.target_fps), 1)
                should_retry = self._picam2 is None and self._capture is None and (time.time() - self._last_open_attempt) >= self._retry_interval_s
                if should_retry:
                    self._open_backend_locked()

            frame, live, error_text = self._capture_one_frame()
            if frame is None:
                with self._service_lock:
                    self.preview_live = False
                    self.last_error = error_text
                frame = self._placeholder_frame()
            else:
                self._maybe_update_gains(frame)
                corrected = self._apply_gains(frame)
                with self._service_lock:
                    self.preview_live = bool(live)
                    self.last_error = ""
                with self._frame_lock:
                    self._raw_frame = frame.copy()
                    self._frame = corrected.copy()
                fps_count += 1
                now = time.time()
                elapsed = now - fps_window_start
                if elapsed >= 1.0:
                    self._fps = fps_count / elapsed
                    fps_count = 0
                    fps_window_start = now

            if frame is not None and self._frame is None:
                with self._frame_lock:
                    self._frame = frame.copy()

            time.sleep(1.0 / target_fps)

    def get_latest_frame(self):
        with self._frame_lock:
            if self._frame is None:
                return None
            return self._frame.copy()

    def get_raw_frame(self):
        with self._frame_lock:
            if self._raw_frame is None:
                return None
            return self._raw_frame.copy()

    def get_jpeg_frame(self) -> Optional[bytes]:
        if cv2 is None:
            return None
        frame = self.get_latest_frame()
        if frame is None:
            return None
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except Exception:
            rgb = frame
        ok, buf = cv2.imencode(".jpg", rgb, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
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
            self._release_backends_locked()
            self.preview_live = False
