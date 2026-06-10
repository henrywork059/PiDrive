from __future__ import annotations

import io
import threading
import time
from collections import deque
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

try:  # Optional Picamera2/libcamera enum access for camera controls.
    from libcamera import Transform as LibcameraTransform  # type: ignore
    from libcamera import controls as libcamera_controls  # type: ignore
except Exception:  # pragma: no cover
    LibcameraTransform = None  # type: ignore
    libcamera_controls = None  # type: ignore


_VALID_CAPTURE_SOURCES = {"request", "array"}
_VALID_ARRAY_COLOR_ORDERS = {"auto", "bgr", "rgb", "bgra", "rgba", "swap_rb", "none"}
_VALID_FORMATS = {"BGR888", "RGB888", "XBGR8888", "XRGB8888", "BGRA8888", "RGBA8888"}

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
_AE_METERING_MODE_MAP = {
    "centre-weighted": "CentreWeighted",
    "center-weighted": "CentreWeighted",
    "centre": "CentreWeighted",
    "center": "CentreWeighted",
    "spot": "Spot",
    "matrix": "Matrix",
    "custom": "Custom",
}
_AE_EXPOSURE_MODE_MAP = {
    "normal": "Normal",
    "short": "Short",
    "long": "Long",
    "custom": "Custom",
}
_AE_CONSTRAINT_MODE_MAP = {
    "normal": "Normal",
    "highlight": "Highlight",
    "highlights": "Highlight",
    "shadows": "Shadows",
    "custom": "Custom",
}
_NOISE_REDUCTION_MODE_MAP = {
    "off": "Off",
    "fast": "Fast",
    "high-quality": "HighQuality",
    "high_quality": "HighQuality",
    "hq": "HighQuality",
    "minimal": "Minimal",
    "zsl": "ZSL",
}

_RESTART_KEYS = {
    "width",
    "height",
    "fps",
    "format",
    "buffer_count",
    "queue",
    "hflip",
    "vflip",
}

_KNOWN_CAMERA_KEYS = {
    "width",
    "height",
    "fps",
    "format",
    "preview_quality",
    "jpeg_quality",
    "capture_source",
    "array_color_order",
    "buffer_count",
    "queue",
    "hflip",
    "vflip",
    "auto_exposure",
    "exposure_us",
    "analogue_gain",
    "exposure_compensation",
    "ae_metering_mode",
    "ae_exposure_mode",
    "ae_constraint_mode",
    "auto_white_balance",
    "awb_mode",
    "colour_gains_red",
    "colour_gains_blue",
    "awb_settle_seconds",
    "brightness",
    "contrast",
    "saturation",
    "sharpness",
    "noise_reduction_mode",
    "scaler_crop",
}


def _clean_choice(value: Any, default: str, valid: set[str]) -> str:
    text = str(value if value is not None else default).strip().lower()
    return text if text in valid else default


def _parse_bool(value: Any, default: bool) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on", "enable", "enabled"}:
        return True
    if text in {"0", "false", "no", "n", "off", "disable", "disabled"}:
        return False
    return bool(default)


def _normalise_mode(value: Any, default: str) -> str:
    text = str(value if value is not None else default).strip().lower().replace(" ", "-")
    return text or default


def _parse_scaler_crop(value: Any) -> list[int] | None:
    if value in (None, "", [], ()):
        return None
    if isinstance(value, str):
        pieces = [piece.strip() for piece in value.split(",")]
    elif isinstance(value, (list, tuple)):
        pieces = list(value)
    else:
        return None
    if len(pieces) != 4:
        return None
    try:
        x, y, w, h = [int(float(piece)) for piece in pieces]
    except Exception:
        return None
    if w <= 0 or h <= 0 or x < 0 or y < 0:
        return None
    return [x, y, w, h]


@dataclass
class CameraConfig:
    width: int = 426
    height: int = 240
    fps: int = 12
    format: str = "BGR888"
    preview_quality: int = 65
    capture_source: str = "request"
    array_color_order: str = "rgb"
    buffer_count: int = 3
    queue: bool = False
    hflip: bool = False
    vflip: bool = False
    auto_exposure: bool = True
    exposure_us: int = 12000
    analogue_gain: float = 1.0
    exposure_compensation: float = 0.0
    ae_metering_mode: str = "centre-weighted"
    ae_exposure_mode: str = "normal"
    ae_constraint_mode: str = "normal"
    # PiSD_0_5_6: default to the hardware-tested OV5647 03/91-style
    # visual profile: request/PIL RGB path with AWB locked after a short
    # settle. This avoids the red/yellow/blue drift seen in AWB-auto
    # diagnostic variants while keeping manual colour gains disabled.
    auto_white_balance: bool = False
    awb_mode: str = "auto"
    colour_gains_red: float = 0.0
    colour_gains_blue: float = 0.0
    awb_settle_seconds: float = 1.0
    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    sharpness: float = 1.0
    noise_reduction_mode: str = "fast"
    scaler_crop: list[int] | None = None

    def apply(self, data: dict[str, Any] | None) -> None:
        if not isinstance(data, dict):
            return
        self.width = clamp_int(data.get("width", self.width), 64, 3840, self.width)
        self.height = clamp_int(data.get("height", self.height), 48, 2160, self.height)
        self.fps = clamp_int(data.get("fps", self.fps), 1, 120, self.fps)
        self.format = str(data.get("format", self.format) or self.format).upper()
        quality_value = data.get("preview_quality", data.get("jpeg_quality", self.preview_quality))
        self.preview_quality = clamp_int(quality_value, 20, 95, self.preview_quality)
        self.capture_source = _clean_choice(data.get("capture_source", self.capture_source), "request", _VALID_CAPTURE_SOURCES)
        self.array_color_order = _clean_choice(
            data.get("array_color_order", self.array_color_order), "rgb", _VALID_ARRAY_COLOR_ORDERS
        )
        self.buffer_count = clamp_int(data.get("buffer_count", self.buffer_count), 1, 12, self.buffer_count)
        if "queue" in data:
            self.queue = _parse_bool(data.get("queue"), self.queue)
        if "hflip" in data:
            self.hflip = _parse_bool(data.get("hflip"), self.hflip)
        if "vflip" in data:
            self.vflip = _parse_bool(data.get("vflip"), self.vflip)
        if "auto_exposure" in data:
            self.auto_exposure = _parse_bool(data.get("auto_exposure"), self.auto_exposure)
        self.exposure_us = clamp_int(data.get("exposure_us", self.exposure_us), 100, 1_000_000, self.exposure_us)
        self.analogue_gain = clamp_float(
            data.get("analogue_gain", self.analogue_gain), 0.0, 64.0, self.analogue_gain
        )
        self.exposure_compensation = clamp_float(
            data.get("exposure_compensation", self.exposure_compensation), -8.0, 8.0, self.exposure_compensation
        )
        self.ae_metering_mode = _normalise_mode(data.get("ae_metering_mode", self.ae_metering_mode), self.ae_metering_mode)
        self.ae_exposure_mode = _normalise_mode(data.get("ae_exposure_mode", self.ae_exposure_mode), self.ae_exposure_mode)
        self.ae_constraint_mode = _normalise_mode(data.get("ae_constraint_mode", self.ae_constraint_mode), self.ae_constraint_mode)
        if "auto_white_balance" in data:
            self.auto_white_balance = _parse_bool(data.get("auto_white_balance"), self.auto_white_balance)
        self.awb_mode = _normalise_mode(data.get("awb_mode", self.awb_mode), self.awb_mode)
        self.colour_gains_red = clamp_float(
            data.get("colour_gains_red", self.colour_gains_red), 0.0, 16.0, self.colour_gains_red
        )
        self.colour_gains_blue = clamp_float(
            data.get("colour_gains_blue", self.colour_gains_blue), 0.0, 16.0, self.colour_gains_blue
        )
        self.awb_settle_seconds = clamp_float(
            data.get("awb_settle_seconds", self.awb_settle_seconds), 0.0, 10.0, self.awb_settle_seconds
        )
        self.brightness = clamp_float(data.get("brightness", self.brightness), -1.0, 1.0, self.brightness)
        self.contrast = clamp_float(data.get("contrast", self.contrast), 0.0, 32.0, self.contrast)
        self.saturation = clamp_float(data.get("saturation", self.saturation), 0.0, 32.0, self.saturation)
        self.sharpness = clamp_float(data.get("sharpness", self.sharpness), 0.0, 16.0, self.sharpness)
        self.noise_reduction_mode = _normalise_mode(
            data.get("noise_reduction_mode", self.noise_reduction_mode), self.noise_reduction_mode
        )
        if "scaler_crop" in data:
            self.scaler_crop = _parse_scaler_crop(data.get("scaler_crop"))

    def as_dict(self) -> dict[str, Any]:
        return {
            "width": int(self.width),
            "height": int(self.height),
            "fps": int(self.fps),
            "format": str(self.format),
            "preview_quality": int(self.preview_quality),
            "capture_source": str(self.capture_source),
            "array_color_order": str(self.array_color_order),
            "buffer_count": int(self.buffer_count),
            "queue": bool(self.queue),
            "hflip": bool(self.hflip),
            "vflip": bool(self.vflip),
            "auto_exposure": bool(self.auto_exposure),
            "exposure_us": int(self.exposure_us),
            "analogue_gain": float(self.analogue_gain),
            "exposure_compensation": float(self.exposure_compensation),
            "ae_metering_mode": str(self.ae_metering_mode),
            "ae_exposure_mode": str(self.ae_exposure_mode),
            "ae_constraint_mode": str(self.ae_constraint_mode),
            "auto_white_balance": bool(self.auto_white_balance),
            "awb_mode": str(self.awb_mode),
            "colour_gains_red": float(self.colour_gains_red),
            "colour_gains_blue": float(self.colour_gains_blue),
            "awb_settle_seconds": float(self.awb_settle_seconds),
            "brightness": float(self.brightness),
            "contrast": float(self.contrast),
            "saturation": float(self.saturation),
            "sharpness": float(self.sharpness),
            "noise_reduction_mode": str(self.noise_reduction_mode),
            "scaler_crop": list(self.scaler_crop) if self.scaler_crop else None,
        }


class CameraService:
    """PiSD camera service with real Picamera2 path and safe simulation fallback.

    Visual preview and saved test frames use the Picamera2 request/PIL image path
    by default. The raw array path remains available as a diagnostic/computer-
    vision path, but it should not be treated as the visual reference when colour
    tests show RGB/BGR mismatches.
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
        # Each camera start owns its own stop event.  Reusing one Event caused
        # an old capture thread to wake back up if the camera was restarted
        # before the previous thread had fully exited.
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._frame_lock = threading.Lock()
        self._frame_condition = threading.Condition(self._frame_lock)
        self._latest_jpeg: Optional[bytes] = None
        self._latest_raw: Any = None
        self._last_metadata: dict[str, Any] = {}
        self._last_capture_source = ""
        self._last_array_color_order = ""
        self._last_applied_controls: dict[str, Any] = {}
        self._last_video_config: dict[str, Any] = {}
        self._frame_times: deque[float] = deque(maxlen=180)
        self._last_loop_ms = 0.0
        self._avg_loop_ms = 0.0
        self._last_encode_ms = 0.0
        self._avg_encode_ms = 0.0
        self._last_frame_bytes = 0
        self._frames_dropped_or_empty = 0

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

    def _clear_last_error_if_ok(self) -> None:
        self.last_error = ""
        self.last_error_code = PiSDErrorCodes.OK

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
                    "libcamera_transform_available": LibcameraTransform is not None,
                    "backend": self.backend,
                    "running": self.running,
                    "frame_seq": self.frame_seq,
                    "last_frame_at": self.last_frame_at,
                    "last_capture_source": self._last_capture_source,
                    "last_array_color_order": self._last_array_color_order,
                    "last_metadata": dict(self._last_metadata),
                    "last_applied_controls": dict(self._last_applied_controls),
                    "last_video_config": dict(self._last_video_config),
                    "last_error": self.last_error,
                    "last_error_code": self.last_error_code,
                }
            )
        data.update(self.get_fps_stats())
        data.update(self.errors.status_fields(limit=5))
        return data

    def status(self) -> dict[str, Any]:
        return self.get_config()

    def get_capabilities(self) -> dict[str, Any]:
        """Return camera capabilities without requiring the service to be running."""
        base: dict[str, Any] = {
            "code": PiSDErrorCodes.OK,
            "hardware_enabled": bool(self.hardware_enabled),
            "picamera2_available": Picamera2 is not None,
            "supported_settings": sorted(_KNOWN_CAMERA_KEYS),
            "valid_capture_sources": sorted(_VALID_CAPTURE_SOURCES),
            "valid_array_color_orders": sorted(_VALID_ARRAY_COLOR_ORDERS),
            "recommended_visual_capture_source": "request",
            "recommended_array_color_order": "rgb",
            "verified_colour_reference": "03_request_awb_off_lock",
            "verified_array_reference": "91_array_rgb",
            "note": "Use capture_source=request with the 03_request_awb_off_lock profile for visual colour/training reference. For raw array/CV paths, this OV5647 test setup matched array_color_order=rgb.",
            "fps_pipeline": {
                "recommended_display_endpoint": "/video_feed",
                "snapshot_endpoint": "/api/camera/frame.jpg",
                "stats_endpoint": "/api/camera/fps-stats",
                "fast_preview_preset": {
                    "capture_source": "array",
                    "array_color_order": "rgb",
                    "width": 426,
                    "height": 240,
                    "fps": 30,
                    "preview_quality": 50,
                    "buffer_count": 4,
                    "queue": True,
                },
            },
        }
        if not self.hardware_enabled or Picamera2 is None:
            base.update({"camera_controls": {}, "camera_properties": {}, "sensor_modes": [], "warning": "Hardware not requested or Picamera2 missing."})
            return base

        picam2 = None
        try:
            picam2 = self._picam2 if self._picam2 is not None else Picamera2()
            base["camera_controls"] = self._serialise_camera_controls(getattr(picam2, "camera_controls", {}) or {})
            base["camera_properties"] = self._serialise_simple_dict(getattr(picam2, "camera_properties", {}) or {})
            base["sensor_modes"] = self._serialise_sensor_modes(getattr(picam2, "sensor_modes", []) or [])
            return base
        except Exception as exc:
            report = self._record(
                PiSDErrorCodes.CAMERA_CAPABILITY_QUERY_FAILED,
                f"Failed to query camera capabilities: {exc}",
                severity="warning",
                exc=exc,
            )
            base.update({"code": report.code, "warning": report.message, "camera_controls": {}, "camera_properties": {}, "sensor_modes": []})
            return base
        finally:
            if picam2 is not None and picam2 is not self._picam2:
                try:
                    picam2.close()
                except Exception:
                    pass

    def _serialise_camera_controls(self, controls: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in controls.items():
            if isinstance(value, (list, tuple)):
                result[str(key)] = [self._serialise_value(item) for item in value]
            else:
                result[str(key)] = self._serialise_value(value)
        return result

    def _serialise_simple_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        return {str(key): self._serialise_value(value) for key, value in data.items()}

    def _serialise_sensor_modes(self, modes: list[Any]) -> list[Any]:
        output = []
        for mode in modes:
            if isinstance(mode, dict):
                output.append(self._serialise_simple_dict(mode))
            else:
                output.append(self._serialise_value(mode))
        return output

    def _serialise_value(self, value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, (tuple, list)):
            return [self._serialise_value(item) for item in value]
        return str(value)

    def apply_settings(self, data: dict[str, Any] | None, restart: bool = True) -> tuple[bool, str, dict[str, Any]]:
        warnings = self._validate_settings_input(data)
        with self._lock:
            was_running = self.running
            before = self.config.as_dict()
            self.config.apply(data or {})
            after = self.config.as_dict()
        restart_needed = any(before.get(key) != after.get(key) for key in _RESTART_KEYS)
        for warning in warnings:
            self._record(
                PiSDErrorCodes.CAMERA_SETTING_INVALID,
                warning,
                severity="warning",
                context={"settings": data or {}},
            )
        if was_running and restart and restart_needed:
            self.stop()
            ok, message = self.start()
            return ok, f"Camera settings updated with restart. {message}", self.get_config()
        if was_running and not restart_needed:
            with self._lock:
                self._apply_picamera_controls_locked()
            return True, "Camera runtime controls updated without restart.", self.get_config()
        if was_running and restart:
            with self._lock:
                self._apply_picamera_controls_locked()
            return True, "Camera settings updated.", self.get_config()
        return True, "Camera settings updated.", self.get_config()

    def _validate_settings_input(self, data: dict[str, Any] | None) -> list[str]:
        warnings: list[str] = []
        if data is None:
            return warnings
        if not isinstance(data, dict):
            return ["Camera settings payload must be a JSON object/dict."]
        unknown = sorted(set(data) - _KNOWN_CAMERA_KEYS)
        if unknown:
            warnings.append(f"Unknown camera setting key(s) ignored: {', '.join(unknown)}")
        if "format" in data and str(data.get("format", "")).upper() not in _VALID_FORMATS:
            warnings.append(f"Camera format '{data.get('format')}' is not in the known PiSD preview list; Picamera2 may reject it.")
        if "capture_source" in data and str(data.get("capture_source", "")).lower() not in _VALID_CAPTURE_SOURCES:
            warnings.append("capture_source must be 'request' or 'array'; PiSD kept the previous/default value.")
        if "array_color_order" in data and str(data.get("array_color_order", "")).lower() not in _VALID_ARRAY_COLOR_ORDERS:
            warnings.append("array_color_order is invalid; PiSD kept the previous/default value.")
        if "scaler_crop" in data and _parse_scaler_crop(data.get("scaler_crop")) is None and data.get("scaler_crop") not in (None, "", [], ()):  # noqa: E501
            warnings.append("scaler_crop must be four values: x,y,width,height.")
        if "auto_white_balance" in data and _parse_bool(data.get("auto_white_balance"), True) and (
            float(data.get("colour_gains_red", 0) or 0) > 0 or float(data.get("colour_gains_blue", 0) or 0) > 0
        ):
            warnings.append("Manual colour gains only apply when auto_white_balance is false.")
        if "auto_exposure" in data and _parse_bool(data.get("auto_exposure"), True) and (
            "exposure_us" in data or "analogue_gain" in data
        ):
            warnings.append("Manual exposure_us/analogue_gain only apply when auto_exposure is false.")
        return warnings

    def start(self) -> tuple[bool, str]:
        stale_thread: threading.Thread | None = None
        with self._lock:
            if self.running:
                return True, f"Camera already running via {self.backend}."
            stale_thread = self._thread if self._thread and self._thread.is_alive() else None
            if stale_thread is not None:
                self._stop_event.set()

        if stale_thread is not None:
            stale_thread.join(timeout=2.0)

        with self._lock:
            if self.running:
                return True, f"Camera already running via {self.backend}."
            # If a previous Picamera2 instance or capture thread did not close
            # cleanly, clean it up before opening hardware again.  This prevents
            # Stop camera -> Start live from falling back to simulation because
            # the old camera object was still holding the device.
            self._close_picamera2_locked()
            self._thread = None
            self._stop_event = threading.Event()
            stop_event = self._stop_event
            self._reset_fps_metrics()

            if self.hardware_enabled and Picamera2 is not None:
                ok, message = self._open_picamera2_locked()
                if ok:
                    self.backend = "picamera2"
                    self._clear_last_error_if_ok()
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
            self._thread = threading.Thread(target=self._capture_loop, args=(stop_event,), name="pisd-camera", daemon=True)
            self._thread.start()
            if self.backend == "picamera2":
                return True, "Camera started with Picamera2."
            if self.last_error:
                return True, f"Camera simulation started. Code {self.last_error_code}: {self.last_error}"
            return True, "Camera simulation started."

    def stop(self) -> tuple[bool, str]:
        thread: threading.Thread | None
        stop_event: threading.Event
        with self._lock:
            if not self.running:
                self._stop_event.set()
                self._close_picamera2_locked()
                self.backend = "not_started"
                with self._frame_condition:
                    self._latest_jpeg = None
                    self._latest_raw = None
                    self._last_frame_bytes = 0
                    self._frame_condition.notify_all()
                return True, "Camera already stopped."
            self.running = False
            stop_event = self._stop_event
            stop_event.set()
            thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        with self._lock:
            if self._thread is thread:
                self._thread = None
            self._close_picamera2_locked()
            self.backend = "not_started"
        with self._frame_condition:
            self._latest_jpeg = None
            self._latest_raw = None
            self._last_frame_bytes = 0
            self._frame_condition.notify_all()
        return True, "Camera stopped."

    def get_jpeg_frame(self) -> bytes | None:
        with self._frame_lock:
            return self._latest_jpeg

    def get_jpeg_frame_info(self) -> tuple[bytes | None, int, str, int]:
        """Return the cached JPEG plus lightweight metadata without building full status()."""
        with self._frame_lock:
            return self._latest_jpeg, int(self.frame_seq), str(self.last_frame_at), int(self._last_frame_bytes)

    def wait_for_jpeg_frame(self, last_seq: int | None = None, timeout: float = 1.0) -> tuple[bytes | None, int, str, int]:
        """Wait until a new JPEG frame is available, then return frame, seq, timestamp, and byte count."""
        deadline = time.monotonic() + max(0.0, float(timeout))
        with self._frame_condition:
            while True:
                has_frame = self._latest_jpeg is not None
                is_new = last_seq is None or int(self.frame_seq) != int(last_seq)
                if has_frame and is_new:
                    return self._latest_jpeg, int(self.frame_seq), str(self.last_frame_at), int(self._last_frame_bytes)
                if not self.running and has_frame:
                    return self._latest_jpeg, int(self.frame_seq), str(self.last_frame_at), int(self._last_frame_bytes)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return self._latest_jpeg, int(self.frame_seq), str(self.last_frame_at), int(self._last_frame_bytes)
                self._frame_condition.wait(timeout=min(remaining, 0.5))

    def get_fps_stats(self) -> dict[str, Any]:
        with self._frame_lock:
            times = list(self._frame_times)
            measured = 0.0
            if len(times) >= 2:
                elapsed = max(0.000001, times[-1] - times[0])
                measured = (len(times) - 1) / elapsed
            return {
                "target_fps": int(self.config.fps),
                "measured_capture_fps": round(measured, 2),
                "last_capture_loop_ms": round(float(self._last_loop_ms), 3),
                "average_capture_loop_ms": round(float(self._avg_loop_ms), 3),
                "last_encode_ms": round(float(self._last_encode_ms), 3),
                "average_encode_ms": round(float(self._avg_encode_ms), 3),
                "last_frame_bytes": int(self._last_frame_bytes),
                "frames_dropped_or_empty": int(self._frames_dropped_or_empty),
                "frame_seq": int(self.frame_seq),
                "last_frame_at": str(self.last_frame_at),
                "stream_endpoint": "/video_feed",
                "snapshot_endpoint": "/api/camera/frame.jpg",
            }

    def _reset_fps_metrics(self) -> None:
        with self._frame_condition:
            self._frame_times.clear()
            self._last_loop_ms = 0.0
            self._avg_loop_ms = 0.0
            self._last_encode_ms = 0.0
            self._avg_encode_ms = 0.0
            self._last_frame_bytes = 0
            self._frames_dropped_or_empty = 0
            self._frame_condition.notify_all()

    def _note_encode_time(self, encode_ms: float) -> None:
        with self._frame_lock:
            self._last_encode_ms = float(encode_ms)
            if self._avg_encode_ms <= 0:
                self._avg_encode_ms = float(encode_ms)
            else:
                self._avg_encode_ms = (self._avg_encode_ms * 0.85) + (float(encode_ms) * 0.15)

    def _publish_frame(self, frame: Any, jpeg: bytes, loop_ms: float) -> None:
        now_monotonic = time.monotonic()
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._frame_condition:
            self._latest_raw = frame
            self._latest_jpeg = jpeg
            self.frame_seq += 1
            self.last_frame_at = now_iso
            self._last_frame_bytes = len(jpeg)
            self._last_loop_ms = float(loop_ms)
            if self._avg_loop_ms <= 0:
                self._avg_loop_ms = float(loop_ms)
            else:
                self._avg_loop_ms = (self._avg_loop_ms * 0.85) + (float(loop_ms) * 0.15)
            self._frame_times.append(now_monotonic)
            self._frame_condition.notify_all()

    def get_latest_frame(self, copy: bool = True) -> Any:
        with self._frame_lock:
            frame = self._latest_raw
            if copy and hasattr(frame, "copy"):
                return frame.copy()
            return frame

    def _should_settle_awb_before_lock(self) -> bool:
        return (
            not bool(self.config.auto_white_balance)
            and float(self.config.awb_settle_seconds) > 0.0
            and float(self.config.colour_gains_red) <= 0.0
            and float(self.config.colour_gains_blue) <= 0.0
        )

    def _build_startup_controls_for_awb_lock(self, controls: dict[str, Any]) -> dict[str, Any]:
        """Allow AWB to settle briefly before the locked-AWB default is applied."""
        if not self._should_settle_awb_before_lock():
            return controls
        startup_controls = dict(controls)
        startup_controls["AwbEnable"] = True
        awb_mode = self._resolve_control_enum("AwbModeEnum", self.config.awb_mode, _AWB_MODE_MAP, "awb_mode")
        if awb_mode is not None:
            startup_controls["AwbMode"] = awb_mode
        return startup_controls

    def _open_picamera2_locked(self) -> tuple[bool, str]:
        if Picamera2 is None:
            self._record(PiSDErrorCodes.CAMERA_PICAMERA2_MISSING, "Picamera2 is not installed.", severity="warning")
            return False, "Picamera2 is not installed."
        try:
            picam2 = Picamera2()
            frame_duration = max(1, int(1_000_000 / max(self.config.fps, 1)))
            controls = self._build_picamera_controls(include_frame_duration=True)
            startup_controls = self._build_startup_controls_for_awb_lock(controls)
            transform = self._build_transform()
            kwargs: dict[str, Any] = {
                "main": {"size": (self.config.width, self.config.height), "format": self.config.format},
                "controls": {"FrameDurationLimits": (frame_duration, frame_duration), **startup_controls},
                "queue": bool(self.config.queue),
                "buffer_count": int(self.config.buffer_count),
            }
            if transform is not None:
                kwargs["transform"] = transform
            video_config = picam2.create_video_configuration(**kwargs)
            picam2.configure(video_config)
            picam2.start()
            self._picam2 = picam2
            with self._lock:
                self._last_video_config = {
                    "size": [self.config.width, self.config.height],
                    "format": self.config.format,
                    "fps": self.config.fps,
                    "frame_duration_us": frame_duration,
                    "buffer_count": self.config.buffer_count,
                    "queue": self.config.queue,
                    "hflip": self.config.hflip,
                    "vflip": self.config.vflip,
                    "awb_lock_after_settle": self._should_settle_awb_before_lock(),
                }
            if self.config.awb_settle_seconds > 0:
                time.sleep(float(self.config.awb_settle_seconds))
            self._apply_picamera_controls_locked()
            return True, "Picamera2 opened."
        except Exception as exc:
            self._picam2 = None
            self._record(
                PiSDErrorCodes.CAMERA_OPEN_FAILED,
                f"Failed to open Picamera2: {exc}",
                context={
                    "width": self.config.width,
                    "height": self.config.height,
                    "format": self.config.format,
                    "buffer_count": self.config.buffer_count,
                    "queue": self.config.queue,
                },
                exc=exc,
            )
            return False, f"Failed to open Picamera2: {exc}"

    def _build_transform(self) -> Any | None:
        if not (self.config.hflip or self.config.vflip):
            return None
        if LibcameraTransform is None:
            self._record(
                PiSDErrorCodes.CAMERA_CONTROL_APPLY_FAILED,
                "libcamera Transform is unavailable; hflip/vflip could not be applied.",
                severity="warning",
                context={"hflip": self.config.hflip, "vflip": self.config.vflip},
            )
            return None
        try:
            return LibcameraTransform(hflip=int(self.config.hflip), vflip=int(self.config.vflip))
        except Exception as exc:
            self._record(
                PiSDErrorCodes.CAMERA_CONTROL_APPLY_FAILED,
                f"Failed to create libcamera transform: {exc}",
                severity="warning",
                exc=exc,
            )
            return None

    def _resolve_control_enum(self, class_name: str, label: str, mapping: dict[str, str], control_name: str) -> Any | None:
        key = str(label or "").strip().lower().replace(" ", "-")
        enum_member = mapping.get(key)
        if enum_member is None:
            self._record(
                PiSDErrorCodes.CAMERA_CONTROL_APPLY_FAILED,
                f"Unsupported {control_name} value '{label}'.",
                severity="warning",
                context={control_name: label},
            )
            return None
        if libcamera_controls is None:
            self._record(
                PiSDErrorCodes.CAMERA_CONTROL_APPLY_FAILED,
                f"libcamera controls are unavailable; {control_name} was ignored.",
                severity="warning",
                context={control_name: label},
            )
            return None
        enum_class = getattr(libcamera_controls, class_name, None)
        if enum_class is None and hasattr(libcamera_controls, "draft"):
            enum_class = getattr(libcamera_controls.draft, class_name, None)
        if enum_class is None:
            self._record(
                PiSDErrorCodes.CAMERA_CONTROL_APPLY_FAILED,
                f"libcamera enum {class_name} is unavailable; {control_name} was ignored.",
                severity="warning",
                context={control_name: label},
            )
            return None
        try:
            return getattr(enum_class, enum_member)
        except Exception as exc:
            self._record(
                PiSDErrorCodes.CAMERA_CONTROL_APPLY_FAILED,
                f"{control_name} '{label}' could not be resolved: {exc}",
                severity="warning",
                context={control_name: label, "enum_member": enum_member},
                exc=exc,
            )
            return None

    def _build_picamera_controls(self, *, include_frame_duration: bool = False) -> dict[str, Any]:
        controls: dict[str, Any] = {
            "AeEnable": bool(self.config.auto_exposure),
            "AwbEnable": bool(self.config.auto_white_balance),
            "Brightness": float(self.config.brightness),
            "Contrast": float(self.config.contrast),
            "Saturation": float(self.config.saturation),
            "Sharpness": float(self.config.sharpness),
            "ExposureValue": float(self.config.exposure_compensation),
        }
        if include_frame_duration:
            frame_duration = max(1, int(1_000_000 / max(self.config.fps, 1)))
            controls["FrameDurationLimits"] = (frame_duration, frame_duration)
        if not self.config.auto_exposure:
            controls["ExposureTime"] = int(self.config.exposure_us)
            controls["AnalogueGain"] = float(self.config.analogue_gain)
        awb_mode = self._resolve_control_enum("AwbModeEnum", self.config.awb_mode, _AWB_MODE_MAP, "awb_mode")
        if awb_mode is not None and self.config.auto_white_balance:
            controls["AwbMode"] = awb_mode
        metering_mode = self._resolve_control_enum(
            "AeMeteringModeEnum", self.config.ae_metering_mode, _AE_METERING_MODE_MAP, "ae_metering_mode"
        )
        if metering_mode is not None:
            controls["AeMeteringMode"] = metering_mode
        exposure_mode = self._resolve_control_enum(
            "AeExposureModeEnum", self.config.ae_exposure_mode, _AE_EXPOSURE_MODE_MAP, "ae_exposure_mode"
        )
        if exposure_mode is not None:
            controls["AeExposureMode"] = exposure_mode
        constraint_mode = self._resolve_control_enum(
            "AeConstraintModeEnum", self.config.ae_constraint_mode, _AE_CONSTRAINT_MODE_MAP, "ae_constraint_mode"
        )
        if constraint_mode is not None:
            controls["AeConstraintMode"] = constraint_mode
        noise_reduction = self._resolve_control_enum(
            "NoiseReductionModeEnum", self.config.noise_reduction_mode, _NOISE_REDUCTION_MODE_MAP, "noise_reduction_mode"
        )
        if noise_reduction is not None:
            controls["NoiseReductionMode"] = noise_reduction
        if not self.config.auto_white_balance:
            controls["AwbEnable"] = False
            if self.config.colour_gains_red > 0.0 and self.config.colour_gains_blue > 0.0:
                controls["ColourGains"] = (float(self.config.colour_gains_red), float(self.config.colour_gains_blue))
        if self.config.scaler_crop:
            controls["ScalerCrop"] = tuple(int(item) for item in self.config.scaler_crop)
        return controls

    def _apply_picamera_controls_locked(self) -> None:
        if self._picam2 is None:
            return
        controls = self._build_picamera_controls(include_frame_duration=True)
        try:
            self._picam2.set_controls(controls)
            self._last_applied_controls = {key: self._serialise_value(value) for key, value in controls.items()}
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

    def _capture_loop(self, stop_event: threading.Event | None = None) -> None:
        local_stop_event = stop_event or self._stop_event
        while not local_stop_event.is_set():
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
                    self._publish_frame(frame, jpeg, (time.time() - start) * 1000.0)
                else:
                    with self._frame_lock:
                        self._frames_dropped_or_empty += 1
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
            local_stop_event.wait(max(0.001, interval - elapsed))

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
            "DigitalGain",
            "ColourGains",
            "AwbEnable",
            "AeEnable",
            "AeLocked",
            "LensPosition",
            "ColourTemperature",
            "Lux",
            "FrameDuration",
            "SensorTimestamp",
            "ScalerCrop",
        ):
            if key in metadata:
                selected[key] = self._serialise_value(metadata.get(key))
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
        start = time.monotonic()
        try:
            img = pil_image
            target_size = (int(self.config.width), int(self.config.height))
            if tuple(getattr(img, "size", target_size)) != target_size:
                img = img.resize(target_size)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=int(self.config.preview_quality), optimize=False)
            data = buf.getvalue()
            self._note_encode_time((time.monotonic() - start) * 1000.0)
            return data
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
        encode_start = time.monotonic()
        if cv2 is not None:
            try:
                ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
                if ok:
                    data = encoded.tobytes()
                    self._note_encode_time((time.monotonic() - encode_start) * 1000.0)
                    return data
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
                data = buf.getvalue()
                self._note_encode_time((time.monotonic() - encode_start) * 1000.0)
                return data
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
        data = buf.getvalue()
        self._note_encode_time(0.0)
        return data
