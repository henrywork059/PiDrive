from __future__ import annotations

import io
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from pisd.core.errors import ErrorReport, ErrorReporter, PiSDErrorCodes
from pisd.core.value_utils import clamp_float, clamp_int

try:  # Optional on non-Pi computers.
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:  # Optional; used for JPEG encoding and simulated frames.
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

try:  # Optional fallback JPEG encoder and Picamera2 request-image path.
    from PIL import Image, ImageDraw  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore

try:  # Available on Raspberry Pi OS with python3-picamera2.
    from picamera2 import Picamera2  # type: ignore
except Exception:  # pragma: no cover
    Picamera2 = None  # type: ignore

try:  # Optional Picamera2/libcamera enum access for AWB mode names.
    from libcamera import controls as libcamera_controls  # type: ignore
except Exception:  # pragma: no cover
    libcamera_controls = None  # type: ignore


_VALID_CAPTURE_SOURCES = {"request", "array"}
_VALID_ARRAY_COLOR_ORDERS = {"auto", "bgr", "rgb", "bgra", "rgba", "swap_rb", "none"}
_AWB_MODE_MAP = {
    "auto": "Auto",
    "normal": "Auto",
    "incandescent": "Incandescent",
    "tungsten": "Tungsten",
    "fluorescent": "Fluorescent",
    "indoor": "Indoor",
    "daylight": "Daylight",
    "cloudy": "Cloudy",
    "custom": "Custom",
}


def _clean_choice(value: Any, default: str, valid: set[str]) -> str:
    text = str(value if value is not None else default).strip().lower()
    return text if text in valid else default


@dataclass
class CameraConfig:
    width: int = 426
    height: int = 240
    fps: int = 12
    format: str = "BGR888"
    preview_quality: int = 65
    capture_source: str = "request"
    array_color_order: str = "auto"
    auto_exposure: bool = True
    exposure_us: int = 12000
    analogue_gain: float = 1.0
    exposure_compensation: float = 0.0
    auto_white_balance: bool = True
    awb_mode: str = "auto"
    colour_gains_red: float = 0.0
    colour_gains_blue: float = 0.0
    awb_settle_seconds: float = 0.5
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
        self.capture_source = _clean_choice(data.get("capture_source", self.capture_source), "request", _VALID_CAPTURE_SOURCES)
        self.array_color_order = _clean_choice(
            data.get("array_color_order", self.array_color_order), "auto", _VALID_ARRAY_COLOR_ORDERS
        )
        if "auto_exposure" in data:
            self.auto_exposure = bool(data.get("auto_exposure"))
        self.exposure_us = clamp_int(data.get("exposure_us", self.exposure_us), 100, 200000, self.exposure_us)
        self.analogue_gain = clamp_float(
            data.get("analogue_gain", self.analogue_gain), 0.0, 64.0, self.analogue_gain
        )
        self.exposure_compensation = clamp_float(
            data.get("exposure_compensation", self.exposure_compensation), -8.0, 8.0, self.exposure_compensation
        )
        if "auto_white_balance" in data:
            self.auto_white_balance = bool(data.get("auto_white_balance"))
        self.awb_mode = str(data.get("awb_mode", self.awb_mode) or self.awb_mode).strip().lower()
        self.colour_gains_red = clamp_float(
            data.get("colour_gains_red", self.colour_gains_red), 0.0, 16.0, self.colour_gains_red
        )
        self.colour_gains_blue = clamp_float(
            data.get("colour_gains_blue", self.colour_gains_blue), 0.0, 16.0, self.colour_gains_blue
        )
        self.awb_settle_seconds = clamp_float(
            data.get("awb_settle_seconds", self.awb_settle_seconds), 0.0, 5.0, self.awb_settle_seconds
        )
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
            "capture_source": str(self.capture_source),
            "array_color_order": str(self.array_color_order),
            "auto_exposure": bool(self.auto_exposure),
            "exposure_us": int(self.exposure_us),
            "analogue_gain": float(self.analogue_gain),
            "exposure_compensation": float(self.exposure_compensation),
            "auto_white_balance": bool(self.auto_white_balance),
            "awb_mode": str(self.awb_mode),
            "colour_gains_red": float(self.colour_gains_red),
            "colour_gains_blue": float(self.colour_gains_blue),
            "awb_settle_seconds": float(self.awb_settle_seconds),
            "brightness": float(self.brightness),
            "contrast": float(self.contrast),
            "saturation": float(self.saturation),
            "sharpness": float(self.sharpness),
        }


class CameraService:
    """PiSD camera service with real Picamera2 path and safe simulation fallback.

    The default Picamera2 path now uses request.make_image("main") for JPEG
    preview output. This intentionally avoids the common RGB/BGR channel-order
    trap that can happen when raw arrays are sent through OpenCV JPEG encoding.
    The array path remains available for computer-vision diagnostics.
    """

    def __init__(self, config: dict[str, Any] | None = None, hardware_enabled: bool = False):
        self.config = CameraConfig()
        self.config.apply(config or {})
        self.hardware_enabled = bool(hardware_enabled)
        self.backend = "not_started"
        self.last_error = ""
        self.last_error_code = PiSDErrorCodes.OK
        self.running = False
        self.frame_seq = 0
        self.last_frame_at = ""
        self.errors = ErrorReporter("camera")
        self._picam2 = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._frame_lock = threading.Lock()
        self._latest_jpeg: Optional[bytes] = None
        self._latest_raw: Any = None
        self._last_metadata: dict[str, Any] = {}
        self._last_capture_source = ""
        self._last_array_color_order = ""

    def _record(
        self,
        code: str,
        message: str,
        *,
        severity: str = "error",
        context: dict[str, Any] | None = None,
        exc: BaseException | None = None,
    ) -> ErrorReport:
        report = self.errors.report(code, message, severity=severity, context=context, exc=exc)
        self.last_error = report.message
        self.last_error_code = report.code
        return report

    def get_config(self) -> dict[str, Any]:
        with self._lock:
            data = self.config.as_dict()
            data.update(
                {
                    "hardware_enabled": bool(self.hardware_enabled),
                    "picamera2_available": Picamera2 is not None,
                    "opencv_available": cv2 is not None,
                    "pillow_available": Image is not None,
                    "libcamera_controls_available": libcamera_controls is not None,
                    "backend": self.backend,
                    "running": self.running,
                    "frame_seq": self.frame_seq,
                    "last_frame_at": self.last_frame_at,
                    "last_capture_source": self._last_capture_source,
                    "last_array_color_order": self._last_array_color_order,
                    "last_metadata": dict(self._last_metadata),
                    "last_error": self.last_error,
                    "last_error_code": self.last_error_code,
                }
            )
            data.update(self.errors.status_fields(limit=5))
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

            if self.hardware_enabled and Picamera2 is not None:
                ok, message = self._open_picamera2_locked()
                if ok:
                    self.backend = "picamera2"
                    self.last_error = ""
                    self.last_error_code = PiSDErrorCodes.OK
                else:
                    self.backend = "simulation"
            else:
                if self.hardware_enabled and Picamera2 is None:
                    self._record(
                        PiSDErrorCodes.CAMERA_PICAMERA2_MISSING,
                        "Picamera2 is not available; camera service is using simulation.",
                        severity="warning",
                    )
                self.backend = "simulation"

            self.running = True
            self._thread = threading.Thread(target=self._capture_loop, name="pisd-camera", daemon=True)
            self._thread.start()
            if self.backend == "picamera2":
                return True, "Camera started with Picamera2."
            if self.last_error:
                return True, f"Camera simulation started. Code {self.last_error_code}: {self.last_error}"
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
            self._record(PiSDErrorCodes.CAMERA_PICAMERA2_MISSING, "Picamera2 is not installed.", severity="warning")
            return False, "Picamera2 is not installed."
        try:
            picam2 = Picamera2()
            frame_duration = max(1, int(1_000_000 / max(self.config.fps, 1)))
            video_config = picam2.create_video_configuration(
                main={"size": (self.config.width, self.config.height), "format": self.config.format},
                controls={"FrameDurationLimits": (frame_duration, frame_duration)},
                queue=False,
                buffer_count=3,
            )
            picam2.configure(video_config)
            picam2.start()
            self._picam2 = picam2
            if (
                not self.config.auto_white_balance
                and self.config.colour_gains_red <= 0.0
                and self.config.colour_gains_blue <= 0.0
                and self.config.awb_settle_seconds > 0
            ):
                time.sleep(float(self.config.awb_settle_seconds))
            self._apply_picamera_controls_locked()
            return True, "Picamera2 opened."
        except Exception as exc:
            self._picam2 = None
            self._record(
                PiSDErrorCodes.CAMERA_OPEN_FAILED,
                f"Failed to open Picamera2: {exc}",
                context={"width": self.config.width, "height": self.config.height, "format": self.config.format},
                exc=exc,
            )
            return False, f"Failed to open Picamera2: {exc}"

    def _resolve_awb_mode(self) -> Any | None:
        mode_key = str(self.config.awb_mode or "auto").strip().lower()
        enum_name = _AWB_MODE_MAP.get(mode_key)
        if enum_name is None:
            self._record(
                PiSDErrorCodes.CAMERA_COLOR_CONTROL_FAILED,
                f"Unsupported AWB mode '{self.config.awb_mode}'. Keeping default auto AWB mode.",
                severity="warning",
                context={"awb_mode": self.config.awb_mode},
            )
            return None
        if enum_name == "Auto" and mode_key in {"auto", "normal"}:
            return None
        if libcamera_controls is None or not hasattr(libcamera_controls, "AwbModeEnum"):
            self._record(
                PiSDErrorCodes.CAMERA_COLOR_CONTROL_FAILED,
                "libcamera AWB mode enum is unavailable; AWB mode name was ignored.",
                severity="warning",
                context={"awb_mode": self.config.awb_mode},
            )
            return None
        try:
            return getattr(libcamera_controls.AwbModeEnum, enum_name)
        except Exception as exc:
            self._record(
                PiSDErrorCodes.CAMERA_COLOR_CONTROL_FAILED,
                f"AWB mode '{self.config.awb_mode}' could not be resolved: {exc}",
                severity="warning",
                context={"awb_mode": self.config.awb_mode, "enum_name": enum_name},
                exc=exc,
            )
            return None

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
            "ExposureValue": float(self.config.exposure_compensation),
        }
        if not self.config.auto_exposure:
            controls["ExposureTime"] = int(self.config.exposure_us)
            controls["AnalogueGain"] = float(self.config.analogue_gain)
        awb_mode = self._resolve_awb_mode()
        if awb_mode is not None and self.config.auto_white_balance:
            controls["AwbMode"] = awb_mode
        if not self.config.auto_white_balance:
            controls["AwbEnable"] = False
            if self.config.colour_gains_red > 0.0 and self.config.colour_gains_blue > 0.0:
                controls["ColourGains"] = (float(self.config.colour_gains_red), float(self.config.colour_gains_blue))
        try:
            self._picam2.set_controls(controls)
        except Exception as exc:
            self._record(
                PiSDErrorCodes.CAMERA_CONTROL_APPLY_FAILED,
                f"Failed to apply camera controls: {exc}",
                severity="warning",
                context={"controls": {k: str(v) for k, v in controls.items()}},
                exc=exc,
            )

    def _close_picamera2_locked(self) -> None:
        try:
            if self._picam2 is not None:
                self._picam2.stop()
                self._picam2.close()
        except Exception as exc:
            self._record(PiSDErrorCodes.CAMERA_STOP_FAILED, f"Failed to stop/close Picamera2: {exc}", exc=exc)
        self._picam2 = None

    def _capture_loop(self) -> None:
        while not self._stop_event.is_set():
            start = time.time()
            try:
                if self.backend == "picamera2" and self._picam2 is not None:
                    if self.config.capture_source == "request":
                        frame, jpeg = self._capture_picamera_request()
                    else:
                        frame = self._picam2.capture_array("main")
                        frame = self._normalize_array_frame(frame)
                        jpeg = self._encode_jpeg(frame)
                        with self._lock:
                            self._last_capture_source = "array"
                            self._last_array_color_order = self.config.array_color_order
                else:
                    frame = self._make_simulated_frame()
                    jpeg = self._encode_jpeg(frame)
                    with self._lock:
                        self._last_capture_source = "simulation"
                        self._last_array_color_order = "bgr"
                if jpeg:
                    with self._frame_lock:
                        self._latest_raw = frame
                        self._latest_jpeg = jpeg
                    with self._lock:
                        self.frame_seq += 1
                        self.last_frame_at = datetime.now(timezone.utc).isoformat()
                else:
                    self._record(
                        PiSDErrorCodes.CAMERA_ENCODE_FAILED,
                        "Camera frame could not be JPEG encoded.",
                        context={"backend": self.backend, "capture_source": self.config.capture_source},
                    )
            except Exception as exc:
                self._record(
                    PiSDErrorCodes.CAMERA_CAPTURE_FAILED,
                    f"Capture error: {exc}",
                    context={"backend": self.backend, "capture_source": self.config.capture_source},
                    exc=exc,
                )
                if self.backend == "picamera2":
                    with self._lock:
                        self._close_picamera2_locked()
                        self.backend = "simulation"
                        self._record(
                            PiSDErrorCodes.CAMERA_CAPTURE_FAILED,
                            "Picamera2 capture failed; falling back to simulation.",
                            severity="warning",
                        )
            interval = 1.0 / max(self.config.fps, 1)
            elapsed = time.time() - start
            self._stop_event.wait(max(0.001, interval - elapsed))

    def _capture_picamera_request(self) -> tuple[Any, bytes | None]:
        if self._picam2 is None:
            return None, None
        request = None
        try:
            request = self._picam2.capture_request()
            pil_image = request.make_image("main")
            metadata = request.get_metadata() or {}
            frame = self._frame_from_pil(pil_image)
            jpeg = self._jpeg_from_pil(pil_image)
            with self._lock:
                self._last_metadata = self._safe_metadata(metadata)
                self._last_capture_source = "request"
                self._last_array_color_order = "pil_rgb"
            return frame, jpeg
        finally:
            if request is not None:
                try:
                    request.release()
                except Exception as exc:
                    self._record(
                        PiSDErrorCodes.CAMERA_CAPTURE_FAILED,
                        f"Failed to release Picamera2 request: {exc}",
                        severity="warning",
                        exc=exc,
                    )

    def _safe_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        selected = {}
        for key in (
            "ExposureTime",
            "AnalogueGain",
            "ColourGains",
            "AwbEnable",
            "AeEnable",
            "ColourTemperature",
            "Lux",
            "FrameDuration",
        ):
            if key in metadata:
                value = metadata.get(key)
                if isinstance(value, (str, int, float, bool)) or value is None:
                    selected[key] = value
                elif isinstance(value, (tuple, list)):
                    selected[key] = [float(item) if isinstance(item, (int, float)) else str(item) for item in value]
                else:
                    selected[key] = str(value)
        return selected

    def _frame_from_pil(self, pil_image: Any) -> Any:
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
        except Exception as exc:
            self._record(
                PiSDErrorCodes.CAMERA_CAPTURE_FAILED,
                f"Failed to convert Picamera2 PIL image to frame array: {exc}",
                severity="warning",
                exc=exc,
            )
            return None

    def _jpeg_from_pil(self, pil_image: Any) -> bytes | None:
        if pil_image is None:
            return None
        try:
            img = pil_image
            target_size = (int(self.config.width), int(self.config.height))
            if tuple(getattr(img, "size", target_size)) != target_size:
                img = img.resize(target_size)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=int(self.config.preview_quality), optimize=False)
            return buf.getvalue()
        except Exception as exc:
            self._record(
                PiSDErrorCodes.CAMERA_ENCODE_FAILED,
                f"Picamera2 request-image JPEG encode failed: {exc}",
                severity="warning",
                exc=exc,
            )
            return None

    def _normalize_array_frame(self, frame: Any) -> Any:
        if frame is None or np is None or not hasattr(frame, "shape"):
            return frame
        try:
            order = str(self.config.array_color_order or "auto").lower()
            if order == "auto":
                fmt = str(self.config.format or "BGR888").upper()
                if fmt.startswith("RGB"):
                    order = "rgb"
                elif fmt.startswith("BGR"):
                    order = "bgr"
                elif fmt.startswith("XBGR") or fmt.startswith("BGRA"):
                    order = "bgra"
                elif fmt.startswith("XRGB") or fmt.startswith("RGBA"):
                    order = "rgba"
                else:
                    order = "bgr"
            if len(frame.shape) == 2:
                if cv2 is not None:
                    return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                return np.stack([frame, frame, frame], axis=-1)
            if len(frame.shape) != 3:
                return frame
            channels = int(frame.shape[2])
            if channels < 3:
                return frame
            if order == "none":
                return frame.copy()
            if order in {"rgb", "swap_rb"}:
                return frame[:, :, :3][:, :, ::-1].copy()
            if order == "bgr":
                return frame[:, :, :3].copy()
            if order == "rgba":
                if cv2 is not None and channels >= 4:
                    return cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
                return frame[:, :, [2, 1, 0]].copy()
            if order == "bgra":
                if cv2 is not None and channels >= 4:
                    return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                return frame[:, :, :3].copy()
            return frame[:, :, :3].copy()
        except Exception as exc:
            self._record(
                PiSDErrorCodes.CAMERA_COLOR_CONTROL_FAILED,
                f"Failed to normalize camera array colour order: {exc}",
                severity="warning",
                context={"array_color_order": self.config.array_color_order, "format": self.config.format},
                exc=exc,
            )
            return frame

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
                self._record(
                    PiSDErrorCodes.CAMERA_ENCODE_FAILED,
                    f"OpenCV JPEG encode failed: {exc}",
                    severity="warning",
                    exc=exc,
                )
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
                self._record(
                    PiSDErrorCodes.CAMERA_ENCODE_FAILED,
                    f"Pillow JPEG encode failed: {exc}",
                    severity="warning",
                    exc=exc,
                )
        return None

    def _encode_pillow_placeholder(self) -> bytes | None:
        if Image is None:
            self._record(
                PiSDErrorCodes.CAMERA_ENCODE_FAILED,
                "No JPEG encoder is available. Install opencv-python or Pillow.",
            )
            return None
        img = Image.new("RGB", (max(64, self.config.width), max(48, self.config.height)), (40, 40, 40))
        if ImageDraw is not None:
            draw = ImageDraw.Draw(img)
            draw.text((12, 12), f"PiSD SIM {self.frame_seq}", fill=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=int(self.config.preview_quality))
        return buf.getvalue()
