from __future__ import annotations

import io
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from pisd.core.value_utils import clamp_float, clamp_int

try:  # Optional on non-Pi computers.
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:  # Optional; used for JPEG encoding and simulated frames.
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

try:  # Optional fallback JPEG encoder.
    from PIL import Image, ImageDraw  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore

try:  # Available on Raspberry Pi OS with python3-picamera2.
    from picamera2 import Picamera2  # type: ignore
except Exception:  # pragma: no cover
    Picamera2 = None  # type: ignore


@dataclass
class CameraConfig:
    width: int = 426
    height: int = 240
    fps: int = 12
    format: str = "BGR888"
    preview_quality: int = 65
    auto_exposure: bool = True
    exposure_us: int = 12000
    analogue_gain: float = 1.0
    auto_white_balance: bool = True
    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    sharpness: float = 1.0

    def apply(self, data: dict[str, Any] | None) -> None:
        if not isinstance(data, dict):
            return
        self.width = clamp_int(data.get("width", self.width), 64, 3840, self.width)
        self.height = clamp_int(data.get("height", self.height), 48, 2160, self.height)
        self.fps = clamp_int(data.get("fps", self.fps), 1, 60, self.fps)
        self.format = str(data.get("format", self.format) or self.format).upper()
        self.preview_quality = clamp_int(
            data.get("preview_quality", self.preview_quality), 20, 95, self.preview_quality
        )
        if "auto_exposure" in data:
            self.auto_exposure = bool(data.get("auto_exposure"))
        self.exposure_us = clamp_int(data.get("exposure_us", self.exposure_us), 100, 200000, self.exposure_us)
        self.analogue_gain = clamp_float(
            data.get("analogue_gain", self.analogue_gain), 0.0, 64.0, self.analogue_gain
        )
        if "auto_white_balance" in data:
            self.auto_white_balance = bool(data.get("auto_white_balance"))
        self.brightness = clamp_float(data.get("brightness", self.brightness), -1.0, 1.0, self.brightness)
        self.contrast = clamp_float(data.get("contrast", self.contrast), 0.0, 32.0, self.contrast)
        self.saturation = clamp_float(data.get("saturation", self.saturation), 0.0, 32.0, self.saturation)
        self.sharpness = clamp_float(data.get("sharpness", self.sharpness), 0.0, 16.0, self.sharpness)

    def as_dict(self) -> dict[str, Any]:
        return {
            "width": int(self.width),
            "height": int(self.height),
            "fps": int(self.fps),
            "format": str(self.format),
            "preview_quality": int(self.preview_quality),
            "auto_exposure": bool(self.auto_exposure),
            "exposure_us": int(self.exposure_us),
            "analogue_gain": float(self.analogue_gain),
            "auto_white_balance": bool(self.auto_white_balance),
            "brightness": float(self.brightness),
            "contrast": float(self.contrast),
            "saturation": float(self.saturation),
            "sharpness": float(self.sharpness),
        }


class CameraService:
    """PiSD camera service with real Picamera2 path and safe simulation fallback.

    The service intentionally does not require Picamera2 at import time. On a PC,
    it can generate changing simulated frames. On a Raspberry Pi, run PiSD with
    hardware enabled and install python3-picamera2 to use the real camera path.
    """

    def __init__(self, config: dict[str, Any] | None = None, hardware_enabled: bool = False):
        self.config = CameraConfig()
        self.config.apply(config or {})
        self.hardware_enabled = bool(hardware_enabled)
        self.backend = "not_started"
        self.last_error = ""
        self.running = False
        self.frame_seq = 0
        self.last_frame_at = ""
        self._picam2 = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._frame_lock = threading.Lock()
        self._latest_jpeg: Optional[bytes] = None
        self._latest_raw: Any = None

    def get_config(self) -> dict[str, Any]:
        with self._lock:
            data = self.config.as_dict()
            data.update(
                {
                    "hardware_enabled": bool(self.hardware_enabled),
                    "picamera2_available": Picamera2 is not None,
                    "opencv_available": cv2 is not None,
                    "pillow_available": Image is not None,
                    "backend": self.backend,
                    "running": self.running,
                    "frame_seq": self.frame_seq,
                    "last_frame_at": self.last_frame_at,
                    "last_error": self.last_error,
                }
            )
            return data

    def status(self) -> dict[str, Any]:
        return self.get_config()

    def apply_settings(self, data: dict[str, Any] | None, restart: bool = True) -> tuple[bool, str, dict[str, Any]]:
        with self._lock:
            was_running = self.running
            self.config.apply(data or {})
        if restart and was_running:
            self.stop()
            ok, message = self.start()
            return ok, message, self.get_config()
        return True, "Camera settings updated.", self.get_config()

    def start(self) -> tuple[bool, str]:
        with self._lock:
            if self.running:
                return True, f"Camera already running via {self.backend}."
            self._stop_event.clear()
            self.last_error = ""

            if self.hardware_enabled and Picamera2 is not None:
                ok, message = self._open_picamera2_locked()
                if ok:
                    self.backend = "picamera2"
                else:
                    self.last_error = message
                    self.backend = "simulation"
            else:
                if self.hardware_enabled and Picamera2 is None:
                    self.last_error = "Picamera2 not available; using simulation."
                self.backend = "simulation"

            self.running = True
            self._thread = threading.Thread(target=self._capture_loop, name="pisd-camera", daemon=True)
            self._thread.start()
            if self.backend == "picamera2":
                return True, "Camera started with Picamera2."
            if self.last_error:
                return True, f"Camera simulation started. Note: {self.last_error}"
            return True, "Camera simulation started."

    def stop(self) -> tuple[bool, str]:
        thread: threading.Thread | None
        with self._lock:
            if not self.running:
                self._close_picamera2_locked()
                self.backend = "not_started"
                return True, "Camera already stopped."
            self.running = False
            self._stop_event.set()
            thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        with self._lock:
            self._thread = None
            self._close_picamera2_locked()
            self.backend = "not_started"
        return True, "Camera stopped."

    def get_jpeg_frame(self) -> bytes | None:
        with self._frame_lock:
            return self._latest_jpeg

    def get_latest_frame(self, copy: bool = True) -> Any:
        with self._frame_lock:
            frame = self._latest_raw
            if copy and hasattr(frame, "copy"):
                return frame.copy()
            return frame

    def _open_picamera2_locked(self) -> tuple[bool, str]:
        if Picamera2 is None:
            return False, "Picamera2 is not installed."
        try:
            picam2 = Picamera2()
            frame_duration = max(1, int(1_000_000 / max(self.config.fps, 1)))
            video_config = picam2.create_video_configuration(
                main={"size": (self.config.width, self.config.height), "format": self.config.format},
                controls={"FrameDurationLimits": (frame_duration, frame_duration)},
                queue=False,
                buffer_count=2,
            )
            picam2.configure(video_config)
            picam2.start()
            self._picam2 = picam2
            self._apply_picamera_controls_locked()
            return True, "Picamera2 opened."
        except Exception as exc:
            self._picam2 = None
            return False, f"Failed to open Picamera2: {exc}"

    def _apply_picamera_controls_locked(self) -> None:
        if self._picam2 is None:
            return
        controls: dict[str, Any] = {
            "AeEnable": bool(self.config.auto_exposure),
            "AwbEnable": bool(self.config.auto_white_balance),
            "Brightness": float(self.config.brightness),
            "Contrast": float(self.config.contrast),
            "Saturation": float(self.config.saturation),
            "Sharpness": float(self.config.sharpness),
        }
        if not self.config.auto_exposure:
            controls["ExposureTime"] = int(self.config.exposure_us)
            controls["AnalogueGain"] = float(self.config.analogue_gain)
        try:
            self._picam2.set_controls(controls)
        except Exception as exc:
            self.last_error = f"Failed to apply camera controls: {exc}"

    def _close_picamera2_locked(self) -> None:
        try:
            if self._picam2 is not None:
                self._picam2.stop()
                self._picam2.close()
        except Exception:
            pass
        self._picam2 = None

    def _capture_loop(self) -> None:
        while not self._stop_event.is_set():
            start = time.time()
            try:
                if self.backend == "picamera2" and self._picam2 is not None:
                    frame = self._picam2.capture_array("main")
                else:
                    frame = self._make_simulated_frame()
                jpeg = self._encode_jpeg(frame)
                if jpeg:
                    with self._frame_lock:
                        self._latest_raw = frame
                        self._latest_jpeg = jpeg
                    with self._lock:
                        self.frame_seq += 1
                        self.last_frame_at = datetime.now(timezone.utc).isoformat()
            except Exception as exc:
                with self._lock:
                    self.last_error = f"Capture error: {exc}"
                if self.backend == "picamera2":
                    with self._lock:
                        self._close_picamera2_locked()
                        self.backend = "simulation"
                        self.last_error += " Falling back to simulation."
            interval = 1.0 / max(self.config.fps, 1)
            elapsed = time.time() - start
            self._stop_event.wait(max(0.001, interval - elapsed))

    def _make_simulated_frame(self) -> Any:
        width = int(self.config.width)
        height = int(self.config.height)
        seq = int(self.frame_seq)
        if np is not None:
            x = np.linspace(0, 255, width, dtype=np.uint8)
            y = np.linspace(0, 255, height, dtype=np.uint8)[:, None]
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :, 0] = (x[None, :] + seq * 3) % 255
            frame[:, :, 1] = (y + seq * 5) % 255
            frame[:, :, 2] = ((x[None, :] // 2 + y // 2 + seq * 7) % 255).astype(np.uint8)
            if cv2 is not None:
                cv2.putText(
                    frame,
                    f"PiSD SIM {seq}",
                    (12, max(24, height // 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
            return frame
        return None

    def _encode_jpeg(self, frame: Any) -> bytes | None:
        if frame is None:
            return self._encode_pillow_placeholder()
        quality = int(self.config.preview_quality)
        if cv2 is not None:
            try:
                ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
                if ok:
                    return encoded.tobytes()
            except Exception as exc:
                self.last_error = f"OpenCV JPEG encode failed: {exc}"
        if Image is not None:
            try:
                if np is not None and hasattr(frame, "shape"):
                    img = Image.fromarray(frame[:, :, ::-1] if frame.shape[-1] == 3 else frame)
                else:
                    return self._encode_pillow_placeholder()
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=quality)
                return buf.getvalue()
            except Exception as exc:
                self.last_error = f"Pillow JPEG encode failed: {exc}"
        return None

    def _encode_pillow_placeholder(self) -> bytes | None:
        if Image is None:
            return None
        img = Image.new("RGB", (max(64, self.config.width), max(48, self.config.height)), (40, 40, 40))
        if ImageDraw is not None:
            draw = ImageDraw.Draw(img)
            draw.text((12, 12), f"PiSD SIM {self.frame_seq}", fill=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=int(self.config.preview_quality))
        return buf.getvalue()
