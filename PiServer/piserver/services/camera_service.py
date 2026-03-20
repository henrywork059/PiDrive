from __future__ import annotations

import io
import math
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


_STREAM_QUALITY_PRESETS = {
    "low_latency": {"preview_fps": 10, "preview_quality": 40},
    "balanced": {"preview_fps": 12, "preview_quality": 60},
    "high": {"preview_fps": 15, "preview_quality": 75},
    "manual": {},
}


class CameraService:
    """Camera backend used by PiServer.

    Preview frames now prefer a Picamera2-native JPEG path so the browser sees
    the same colour behaviour as Picamera2's own save/capture helpers.
    """

    def __init__(self, width: int = 426, height: int = 240, fps: int = 30):
        self.width = int(width)
        self.height = int(height)
        self.target_fps = int(fps)
        self.camera_format = "BGR888"
        self.backend = "placeholder"
        self.backend_format = "unknown"

        self.preview_fps = 12
        self.preview_quality = 60
        self.stream_quality = "balanced"
        self.idle_fps = 3

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
        self.preview_enabled = True
        self.processing_enabled = False
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

        self._jpeg_frame: Optional[bytes] = None
        self._jpeg_seq = 0
        self._jpeg_cond = threading.Condition()

    def _clamp_float(self, value, default: float, min_value: float, max_value: float) -> float:
        try:
            value = float(value)
        except Exception:
            value = default
        if not math.isfinite(value):
            value = default
        return max(min_value, min(max_value, value))

    def _clamp_int(self, value, default: int, min_value: int, max_value: int) -> int:
        try:
            value = int(value)
        except Exception:
            value = default
        return max(min_value, min(max_value, value))

    def _parse_bool(self, value, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            text = value.strip().lower()
            if text in {"1", "true", "yes", "on"}:
                return True
            if text in {"0", "false", "no", "off", ""}:
                return False
        return bool(default)

    def _normalize_stream_quality_locked(self) -> None:
        quality = str(self.stream_quality or "balanced").strip().lower()
        if quality not in _STREAM_QUALITY_PRESETS:
            quality = "balanced"
        self.stream_quality = quality
        preset = _STREAM_QUALITY_PRESETS.get(quality, {})
        if preset:
            self.preview_fps = self._clamp_int(
                preset.get("preview_fps", self.preview_fps),
                self.preview_fps,
                1,
                30,
            )
            self.preview_quality = self._clamp_int(
                preset.get("preview_quality", self.preview_quality),
                self.preview_quality,
                20,
                95,
            )

    def get_persisted_config(self) -> dict:
        with self._service_lock:
            return {
                "width": int(self.width),
                "height": int(self.height),
                "fps": int(self.target_fps),
                "format": str(self.camera_format),
                "preview_fps": int(self.preview_fps),
                "preview_quality": int(self.preview_quality),
                "stream_quality": str(self.stream_quality),
                "auto_exposure": bool(self.auto_exposure),
                "exposure_us": int(self.exposure_us),
                "analogue_gain": float(self.analogue_gain),
                "exposure_compensation": float(self.exposure_compensation),
                "auto_white_balance": bool(self.auto_white_balance),
                "brightness": float(self.brightness),
                "contrast": float(self.contrast),
                "saturation": float(self.saturation),
                "sharpness": float(self.sharpness),
            }

    def apply_settings(self, settings: dict | None, restart: bool = True) -> tuple[bool, str, dict]:
        settings = settings or {}
        with self._service_lock:
            self.width = self._clamp_int(settings.get("width", self.width), self.width, 64, 3840)
            self.height = self._clamp_int(settings.get("height", self.height), self.height, 48, 2160)
            self.target_fps = self._clamp_int(settings.get("fps", self.target_fps), self.target_fps, 1, 120)
            self.camera_format = str(settings.get("format", self.camera_format) or self.camera_format)
            self.preview_fps = self._clamp_int(settings.get("preview_fps", self.preview_fps), self.preview_fps, 1, 30)
            self.preview_quality = self._clamp_int(settings.get("preview_quality", self.preview_quality), self.preview_quality, 20, 95)
            self.stream_quality = str(settings.get("stream_quality", self.stream_quality) or self.stream_quality)
            self._normalize_stream_quality_locked()
            self.auto_exposure = self._parse_bool(settings.get("auto_exposure", self.auto_exposure), self.auto_exposure)
            self.exposure_us = self._clamp_int(settings.get("exposure_us", self.exposure_us), self.exposure_us, 100, 200000)
            self.analogue_gain = self._clamp_float(settings.get("analogue_gain", self.analogue_gain), self.analogue_gain, 0.0, 64.0)
            self.exposure_compensation = self._clamp_float(
                settings.get("exposure_compensation", self.exposure_compensation),
                self.exposure_compensation,
                -8.0,
                8.0,
            )
            self.auto_white_balance = self._parse_bool(settings.get("auto_white_balance", self.auto_white_balance), self.auto_white_balance)
            self.brightness = self._clamp_float(settings.get("brightness", self.brightness), self.brightness, -1.0, 1.0)
            self.contrast = self._clamp_float(settings.get("contrast", self.contrast), self.contrast, 0.0, 32.0)
            self.saturation = self._clamp_float(settings.get("saturation", self.saturation), self.saturation, 0.0, 32.0)
            self.sharpness = self._clamp_float(settings.get("sharpness", self.sharpness), self.sharpness, 0.0, 16.0)
            running = self._running

        if restart and running:
            return self.restart()
        return True, "Camera settings updated. Restart the camera to apply format/resolution changes.", self.get_config()

    def get_config(self) -> dict:
        with self._service_lock:
            data = self.get_persisted_config()
            data.update(
                {
                    "backend": str(self.backend),
                    "backend_format": str(self.backend_format),
                    "preview_live": bool(self.preview_live),
                    "preview_enabled": bool(self.preview_enabled),
                    "processing_enabled": bool(self.processing_enabled),
                    "last_error": str(self.last_error),
                }
            )
            return data

    def set_preview_enabled(self, enabled: bool) -> bool:
        enabled = bool(enabled)
        with self._service_lock:
            self.preview_enabled = enabled
        return enabled

    def set_processing_enabled(self, enabled: bool) -> bool:
        enabled = bool(enabled)
        with self._service_lock:
            self.processing_enabled = enabled
        return enabled

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
                try:
                    cfg = picam.create_video_configuration(
                        main={"size": (self.width, self.height), "format": fmt},
                        controls={"FrameDurationLimits": (frame_duration, frame_duration)},
                        queue=False,
                        buffer_count=2,
                    )
                except TypeError:
                    cfg = picam.create_video_configuration(
                        main={"size": (self.width, self.height), "format": fmt},
                        controls={"FrameDurationLimits": (frame_duration, frame_duration)},
                    )
                picam.configure(cfg)
                self._picam2 = picam
                self._capture = None
                self.backend = "picamera2"
                self.backend_format = fmt
                self.last_error = ""
                try:
                    picam.start()
                except TypeError:
                    picam.start(show_preview=False)
                self._set_picamera_controls_locked()
                return True, "Picamera2 started."
            except Exception as exc:
                last_error = f"Picamera2 ({fmt}) failed: {exc}"
                try:
                    if picam is not None:
                        picam.close()
                except Exception:
                    pass
        return False, last_error

    def _open_opencv_locked(self) -> tuple[bool, str]:
        if cv2 is None:
            return False, "OpenCV is not installed."
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                cap.release()
                return False, "OpenCV camera backend is not available."
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            self._capture = cap
            self._picam2 = None
            self.backend = "opencv"
            self.backend_format = "BGR"
            self.last_error = ""
            return True, "OpenCV camera started."
        except Exception as exc:
            return False, f"OpenCV camera failed: {exc}"

    def _open_backend_locked(self) -> tuple[bool, str]:
        self._last_open_attempt = time.time()
        self._release_backends_locked()
        ok, message = self._open_picamera2_locked()
        if ok:
            return ok, message
        opencv_ok, opencv_message = self._open_opencv_locked()
        if opencv_ok:
            return opencv_ok, opencv_message
        self.backend = "placeholder"
        self.backend_format = "generated"
        self.last_error = f"{message} {opencv_message}".strip()
        return False, self.last_error

    def start(self):
        with self._service_lock:
            if self._running:
                return
            self._open_backend_locked()
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True, name="PiServerCameraLoop")
            self._thread.start()

    def stop(self):
        with self._service_lock:
            self._running = False
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        with self._service_lock:
            self._release_backends_locked()
            self.preview_live = False

    def restart(self) -> tuple[bool, str, dict]:
        self.stop()
        self.start()
        return True, "Camera restarted with updated settings.", self.get_config()

    def get_latest_frame(self, copy: bool = True):
        with self._frame_lock:
            if self._frame is None:
                return None
            if copy and hasattr(self._frame, "copy"):
                return self._frame.copy()
            return self._frame

    def get_fps(self) -> float:
        return float(self._fps)

    def get_jpeg_frame(self) -> Optional[bytes]:
        with self._jpeg_cond:
            return self._jpeg_frame

    def wait_for_jpeg(self, last_seq: int, timeout: float = 1.0) -> tuple[Optional[bytes], int]:
        timeout = max(0.0, float(timeout))
        deadline = time.time() + timeout
        with self._jpeg_cond:
            while self._jpeg_seq <= int(last_seq):
                remaining = deadline - time.time()
                if remaining <= 0.0:
                    return None, self._jpeg_seq
                self._jpeg_cond.wait(timeout=remaining)
            return self._jpeg_frame, self._jpeg_seq

    def _encode_preview_jpeg_cv(self, frame):
        if cv2 is None or frame is None:
            return None
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(self.preview_quality)]
        ok, buf = cv2.imencode(".jpg", frame, encode_params)
        if not ok:
            return None
        try:
            return buf.tobytes()
        except Exception:
            return bytes(buf)

    def _capture_picamera_request(self, processing_enabled: bool, preview_due: bool):
        picam = self._picam2
        if picam is None:
            return None, None, False, self.last_error or "Picamera2 backend is not active."
        try:
            request = picam.capture_request()
        except Exception as exc:
            with self._service_lock:
                self._release_backends_locked()
            return None, None, False, f"Picamera2 capture failed: {exc}"

        frame = None
        jpeg_bytes = None
        live = False
        error_text = ""
        try:
            if processing_enabled:
                try:
                    frame = request.make_array("main")
                except Exception:
                    frame = None
            if preview_due:
                try:
                    stream_name = "main"
                    jpeg_io = io.BytesIO()
                    request.save(stream_name, jpeg_io, format="jpeg", quality=int(self.preview_quality))
                    jpeg_bytes = jpeg_io.getvalue()
                    live = True
                except Exception:
                    if frame is None:
                        try:
                            frame = request.make_array("main")
                        except Exception:
                            frame = None
                    jpeg_bytes = self._encode_preview_jpeg_cv(frame)
                    live = jpeg_bytes is not None
            elif not processing_enabled:
                live = True
        except Exception as exc:
            error_text = f"Picamera2 frame processing failed: {exc}"
        finally:
            try:
                request.release()
            except Exception:
                pass
        return frame, jpeg_bytes, live, error_text

    def _capture_opencv_frame(self):
        cap = self._capture
        if cap is None:
            return None, False, self.last_error or "OpenCV backend is not active."
        try:
            ok, frame = cap.read()
        except Exception as exc:
            ok, frame = False, None
            self.last_error = f"OpenCV read failed: {exc}"
        if not ok or frame is None:
            with self._service_lock:
                self._release_backends_locked()
            return None, False, self.last_error or "OpenCV camera disconnected."
        return frame, True, ""

    def _placeholder_frame(self):
        if np is None or cv2 is None:
            return None
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        cv2.putText(img, "PiServer camera placeholder", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(img, f"backend: {self.backend}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (140, 220, 255), 1)
        if self.last_error:
            cv2.putText(img, self.last_error[:60], (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 180, 255), 1)
        return img

    def _publish_jpeg(self, jpeg_bytes: Optional[bytes]) -> None:
        if jpeg_bytes is None:
            return
        with self._jpeg_cond:
            self._jpeg_frame = jpeg_bytes
            self._jpeg_seq += 1
            self._jpeg_cond.notify_all()

    def _desired_capture_fps_locked(self) -> int:
        if self.processing_enabled:
            return max(1, int(self.target_fps))
        if self.preview_enabled:
            return max(1, min(int(self.target_fps), int(self.preview_fps)))
        return max(1, int(self.idle_fps))

    def _loop(self):
        fps_count = 0
        fps_window_start = time.time()
        last_preview_emit = 0.0
        while True:
            start_time = time.time()
            with self._service_lock:
                if not self._running:
                    break
                target_fps = self._desired_capture_fps_locked()
                preview_period = 1.0 / max(int(self.preview_fps), 1)
                preview_enabled = bool(self.preview_enabled)
                processing_enabled = bool(self.processing_enabled)
                preview_due = preview_enabled and ((time.time() - last_preview_emit) >= preview_period)
                should_retry = self._picam2 is None and self._capture is None and (time.time() - self._last_open_attempt) >= self._retry_interval_s
                if should_retry:
                    self._open_backend_locked()
                using_picam = self._picam2 is not None

            frame = None
            jpeg_bytes = None
            if using_picam:
                frame, jpeg_bytes, live, error_text = self._capture_picamera_request(processing_enabled, preview_due)
            else:
                frame, live, error_text = self._capture_opencv_frame()
                if preview_due and frame is not None:
                    jpeg_bytes = self._encode_preview_jpeg_cv(frame)

            preview_source = None
            if frame is None and processing_enabled:
                preview_source = None
            elif frame is None:
                preview_source = self._placeholder_frame()

            if frame is None and not live:
                with self._service_lock:
                    self.preview_live = False
                    self.last_error = error_text
            else:
                with self._service_lock:
                    self.preview_live = bool(live)
                    self.last_error = ""

            if frame is not None:
                with self._frame_lock:
                    self._raw_frame = frame
                    self._frame = frame
                fps_count += 1
                now = time.time()
                elapsed = now - fps_window_start
                if elapsed >= 1.0:
                    self._fps = fps_count / elapsed
                    fps_count = 0
                    fps_window_start = now

            if preview_source is not None:
                if jpeg_bytes is None:
                    jpeg_bytes = self._encode_preview_jpeg_cv(preview_source)
                if jpeg_bytes is not None:
                    last_preview_emit = time.time()
                    self._publish_jpeg(jpeg_bytes)
            elif jpeg_bytes is not None:
                last_preview_emit = time.time()
                self._publish_jpeg(jpeg_bytes)

            sleep_for = max(0.0, (1.0 / max(target_fps, 1)) - (time.time() - start_time))
            time.sleep(sleep_for)
