from __future__ import annotations

import io
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
        self.auto_white_balance = False
        self.brightness = 0.0
        self.contrast = 1.0
        self.saturation = 1.0
        self.sharpness = 1.0
        self.color_gain_red = 1.0
        self.color_gain_blue = 1.0

        self.preview_live = False
        self.preview_enabled = True
        self.processing_enabled = False
        self.last_error = ""
        self._frame = None
        self._raw_frame = None
        self._raw_frame_time = 0.0
        self._frame_lock = threading.Lock()
        self._capture_lock = threading.Lock()
        self._service_lock = threading.RLock()
        self._running = False
        self._fps = 0.0
        self._capture = None
        self._picam2 = None
        self._thread = None
        self._last_open_attempt = 0.0
        self._retry_interval_s = 2.0
        self._capture_failures = 0
        self._reopen_after_failures = 2

        self._jpeg_frame: Optional[bytes] = None
        self._jpeg_seq = 0
        self._jpeg_cond = threading.Condition()

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
            self.auto_exposure = bool(settings.get("auto_exposure", self.auto_exposure))
            self.exposure_us = self._clamp_int(settings.get("exposure_us", self.exposure_us), self.exposure_us, 100, 200000)
            self.analogue_gain = self._clamp_float(settings.get("analogue_gain", self.analogue_gain), self.analogue_gain, 0.0, 64.0)
            self.exposure_compensation = self._clamp_float(
                settings.get("exposure_compensation", self.exposure_compensation),
                self.exposure_compensation,
                -8.0,
                8.0,
            )
            awb_value = settings.get("auto_white_balance")
            if awb_value is None and "awb" in settings:
                awb_value = settings.get("awb")
            if awb_value is not None:
                self.auto_white_balance = bool(awb_value)
            self.brightness = self._clamp_float(settings.get("brightness", self.brightness), self.brightness, -1.0, 1.0)
            self.contrast = self._clamp_float(settings.get("contrast", self.contrast), self.contrast, 0.0, 32.0)
            self.saturation = self._clamp_float(settings.get("saturation", self.saturation), self.saturation, 0.0, 32.0)
            self.sharpness = self._clamp_float(settings.get("sharpness", self.sharpness), self.sharpness, 0.0, 16.0)

            red_gain_value = settings.get("color_gain_red")
            if red_gain_value is None:
                red_gain_value = settings.get("colour_gain_red")
            if red_gain_value is None:
                red_gain_value = settings.get("red_gain")
            if red_gain_value is not None:
                self.color_gain_red = self._clamp_float(red_gain_value, self.color_gain_red, 0.0, 32.0)

            blue_gain_value = settings.get("color_gain_blue")
            if blue_gain_value is None:
                blue_gain_value = settings.get("colour_gain_blue")
            if blue_gain_value is None:
                blue_gain_value = settings.get("blue_gain")
            if blue_gain_value is not None:
                self.color_gain_blue = self._clamp_float(blue_gain_value, self.color_gain_blue, 0.0, 32.0)
            running = self._running

        if restart and running:
            return self.restart()
        return True, "Camera settings updated. Restart the camera to apply format/resolution changes.", self.get_config()

    def get_config(self) -> dict:
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
                "awb": bool(self.auto_white_balance),
                "brightness": float(self.brightness),
                "contrast": float(self.contrast),
                "saturation": float(self.saturation),
                "sharpness": float(self.sharpness),
                "color_gain_red": float(self.color_gain_red),
                "color_gain_blue": float(self.color_gain_blue),
                "backend": str(self.backend),
                "backend_format": str(self.backend_format),
                "preview_live": bool(self.preview_live),
                "preview_enabled": bool(self.preview_enabled),
                "processing_enabled": bool(self.processing_enabled),
                "last_error": str(self.last_error),
            }

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
        if not self.auto_white_balance:
            controls["ColourGains"] = (float(self.color_gain_red), float(self.color_gain_blue))
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
                    if picam is not None:
                        picam.close()
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
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass
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

        ok, message = self._open_picamera2_locked()
        if ok:
            self._capture_failures = 0
            return
        picam_error = message

        ok, message = self._open_opencv_locked()
        if ok:
            self._capture_failures = 0
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
            return True, f"Camera restarted using {self.backend}. New settings are live.", config
        return False, f"Camera restarted but live preview is not available. {config.get('last_error', '').strip()}".strip(), config

    def _frame_from_pil(self, pil_image):
        if pil_image is None or np is None:
            return None
        try:
            arr = np.array(pil_image)
            if getattr(arr, "ndim", 0) == 2:
                if cv2 is not None:
                    return cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
                return np.stack([arr, arr, arr], axis=-1)
            if getattr(arr, "ndim", 0) == 3:
                channels = int(arr.shape[2])
                if channels >= 3:
                    rgb = arr[:, :, :3]
                    return rgb[:, :, ::-1].copy()
            return arr.copy()
        except Exception:
            return None

    def _jpeg_from_pil(self, pil_image) -> Optional[bytes]:
        if pil_image is None:
            return None
        try:
            img = pil_image
            if tuple(getattr(img, "size", (self.width, self.height))) != (int(self.width), int(self.height)):
                img = img.resize((int(self.width), int(self.height)))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=int(self.preview_quality), optimize=False)
            return buf.getvalue()
        except Exception:
            return None

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

    def _capture_picamera_request(self, need_frame: bool, need_preview: bool):
        with self._service_lock:
            picam = self._picam2
        if picam is None:
            return None, None, False, "No active Picamera2 backend."

        request = None
        try:
            with self._capture_lock:
                request = picam.capture_request()
                pil_image = None
                if need_frame or need_preview:
                    pil_image = request.make_image("main")

                frame = self._frame_from_pil(pil_image) if need_frame else None
                jpeg_bytes = self._jpeg_from_pil(pil_image) if need_preview else None
                return frame, jpeg_bytes, True, ""
        except Exception as exc:
            return None, None, False, f"Picamera2 request capture failed: {exc}"
        finally:
            if request is not None:
                with self._capture_lock:
                    try:
                        request.release()
                    except Exception:
                        pass

    def _capture_opencv_frame(self):
        with self._service_lock:
            capture = self._capture
        if capture is None:
            return None, False, "No active OpenCV backend."
        try:
            with self._capture_lock:
                ok, frame = capture.read()
            if ok and frame is not None:
                return frame, True, ""
            return None, False, "OpenCV capture returned no frame."
        except Exception as exc:
            return None, False, f"OpenCV capture failed: {exc}"

    def _encode_preview_jpeg_cv(self, frame) -> Optional[bytes]:
        if cv2 is None or frame is None:
            return None
        try:
            preview = frame
            target_size = (int(self.width), int(self.height))
            if tuple(frame.shape[1::-1]) != target_size:
                preview = cv2.resize(frame, target_size, interpolation=cv2.INTER_AREA)
            params = [int(cv2.IMWRITE_JPEG_QUALITY), int(self.preview_quality)]
            ok, buf = cv2.imencode(".jpg", preview, params)
            return buf.tobytes() if ok else None
        except Exception:
            return None

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
                    self._capture_failures += 1
                    should_reopen = (
                        (self._picam2 is not None or self._capture is not None)
                        and self._capture_failures >= self._reopen_after_failures
                    )
                    if should_reopen:
                        self._release_backends_locked()
                        self.backend = "placeholder"
                        self.backend_format = "unknown"
                        self._last_open_attempt = 0.0
            else:
                with self._service_lock:
                    self.preview_live = bool(live)
                    self.last_error = ""
                    self._capture_failures = 0

            if frame is not None:
                now = time.time()
                with self._frame_lock:
                    self._raw_frame = frame
                    self._raw_frame_time = now
                    self._frame = frame
                fps_count += 1
                now = time.time()
                elapsed = now - fps_window_start
                if elapsed >= 1.0:
                    self._fps = fps_count / elapsed
                    fps_count = 0
                    fps_window_start = now

            if preview_due:
                if jpeg_bytes is not None:
                    self._publish_jpeg(jpeg_bytes)
                    last_preview_emit = time.time()
                elif preview_source is not None:
                    fallback_jpeg = self._encode_preview_jpeg_cv(preview_source)
                    self._publish_jpeg(fallback_jpeg)
                    last_preview_emit = time.time()

            if preview_source is not None and self._frame is None:
                with self._frame_lock:
                    self._frame = preview_source

            elapsed = time.time() - start_time
            sleep_time = max(0.0, (1.0 / max(target_fps, 1)) - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)


    def _json_safe(self, value, depth: int = 0):
        if depth > 6:
            return repr(value)
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        if isinstance(value, dict):
            return {str(k): self._json_safe(v, depth + 1) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(v, depth + 1) for v in value]
        if isinstance(value, bytes):
            return {"type": "bytes", "length": len(value)}
        shape = getattr(value, "shape", None)
        if shape is not None:
            return {"type": type(value).__name__, "shape": list(shape)}
        return repr(value)

    def get_diagnostics(self) -> dict:
        details = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "config": self.get_config(),
            "fps": float(self._fps),
            "raw_frame_age_s": self.get_raw_frame_age(),
        }
        with self._service_lock:
            picam = self._picam2
            capture = self._capture
        if picam is not None:
            picam_details = {}
            try:
                controls = getattr(picam, "camera_controls", None)
                if controls is not None:
                    picam_details["camera_controls"] = self._json_safe(controls)
            except Exception as exc:
                picam_details["camera_controls_error"] = str(exc)
            try:
                props = getattr(picam, "camera_properties", None)
                if props is not None:
                    picam_details["camera_properties"] = self._json_safe(props)
            except Exception as exc:
                picam_details["camera_properties_error"] = str(exc)
            try:
                with self._capture_lock:
                    metadata = picam.capture_metadata()
                picam_details["metadata"] = self._json_safe(metadata)
            except Exception as exc:
                picam_details["metadata_error"] = str(exc)
            details["picamera2"] = picam_details
        elif capture is not None:
            opencv_details = {}
            if cv2 is not None:
                try:
                    opencv_details["frame_width"] = float(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
                    opencv_details["frame_height"] = float(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    opencv_details["fps"] = float(capture.get(cv2.CAP_PROP_FPS))
                except Exception as exc:
                    opencv_details["readback_error"] = str(exc)
            details["opencv"] = opencv_details
        return details
    def capture_snapshot_frame(self, retries: int = 4, delay_s: float = 0.05, copy: bool = True, max_cache_age_s: float = 0.5):
        attempts = max(1, int(retries) + 1)
        max_cache_age_s = max(0.0, float(max_cache_age_s))
        for attempt in range(attempts):
            with self._service_lock:
                using_picam = self._picam2 is not None
                using_opencv = self._capture is not None

            direct_frame = None
            live = False
            error_text = ""
            if using_picam:
                direct_frame, _jpeg, live, error_text = self._capture_picamera_request(True, False)
            elif using_opencv:
                direct_frame, live, error_text = self._capture_opencv_frame()

            if direct_frame is not None:
                now = time.time()
                with self._frame_lock:
                    self._raw_frame = direct_frame
                    self._raw_frame_time = now
                    self._frame = direct_frame
                with self._service_lock:
                    self.preview_live = bool(live)
                    if error_text:
                        self.last_error = error_text
                    elif live:
                        self.last_error = ""
                if copy and hasattr(direct_frame, "copy"):
                    return direct_frame.copy()
                return direct_frame

            cached_frame = None
            with self._frame_lock:
                raw_frame = self._raw_frame
                raw_frame_time = float(self._raw_frame_time or 0.0)
                if raw_frame is not None and (time.time() - raw_frame_time) <= max_cache_age_s:
                    cached_frame = raw_frame.copy() if copy and hasattr(raw_frame, "copy") else raw_frame
            if cached_frame is not None:
                return cached_frame

            if error_text:
                with self._service_lock:
                    self.last_error = error_text
            if attempt + 1 < attempts:
                time.sleep(max(0.0, float(delay_s)))
        return None

    def get_latest_frame(self, copy: bool = True):
        with self._frame_lock:
            if self._frame is None:
                return None
            return self._frame.copy() if copy else self._frame

    def get_raw_frame(self, copy: bool = True):
        with self._frame_lock:
            if self._raw_frame is None:
                return None
            return self._raw_frame.copy() if copy else self._raw_frame

    def get_raw_frame_age(self) -> float | None:
        with self._frame_lock:
            if self._raw_frame is None or not self._raw_frame_time:
                return None
            return max(0.0, time.time() - float(self._raw_frame_time))

    def get_jpeg_frame(self) -> Optional[bytes]:
        with self._jpeg_cond:
            return self._jpeg_frame

    def wait_for_jpeg(self, last_seq: int = 0, timeout: float = 1.0) -> tuple[Optional[bytes], int]:
        with self._jpeg_cond:
            if self._jpeg_seq == last_seq and self._running:
                self._jpeg_cond.wait(timeout=max(0.0, float(timeout)))
            return self._jpeg_frame, self._jpeg_seq

    def get_fps(self) -> float:
        return float(self._fps)

    def stop(self) -> None:
        self.close()

    def close(self) -> None:
        thread = None
        with self._service_lock:
            self._running = False
            thread = self._thread
            self._thread = None

        with self._jpeg_cond:
            self._jpeg_cond.notify_all()

        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)

        with self._service_lock:
            self._release_backends_locked()
            self.preview_live = False
