from __future__ import annotations

import atexit
import importlib.util
import json
import math
import re
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pisd.core.errors import ErrorReport, ErrorReporter, PiSDErrorCodes, ok_payload, report_payload
from pisd.core.value_utils import clamp_float


MODEL_EXTENSIONS = {".tflite", ".keras", ".h5", ".onnx", ".pt"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AIDriveService:
    """AI-mode runtime coordinator for behavioural-cloning style driving.

    PiSD's AI mode deliberately replaces the earlier scripted autopilot concept.
    It expects a trained model generated from Manual Drive recordings where each
    frame has steering/throttle labels. The service owns model selection/loading,
    prediction status, and the safety limiter that must sit between model output
    and motor output.
    """

    def __init__(self, project_root: Path | str, settings: dict[str, Any] | None = None, models_dir_name: str = "models"):
        self.project_root = Path(project_root)
        self.models_dir = self.project_root / models_dir_name
        self.errors = ErrorReporter("ai_mode")
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._settings: dict[str, Any] = {}
        self._model_id = ""
        self._model_path: Path | None = None
        self._backend = "none"
        self._backend_detail = ""
        self._pending_backend_detail = ""
        self._model: Any = None
        self._input_details: Any = None
        self._output_details: Any = None
        self._input_size = (160, 120)  # width, height fallback
        self._input_dtype_name = "float32"
        self._output_names: list[str] = []
        self._model_loaded = False
        self._model_ready = False
        self._running = False
        self._mode = "idle"  # idle | preview | drive
        self._last_raw = {"steering": 0.0, "throttle": 0.0}
        self._last_safe = {"steering": 0.0, "throttle": 0.0}
        self._last_motor = {"left": 0.0, "right": 0.0}
        self._last_prediction_at = ""
        self._last_inference_ms = 0.0
        self._last_loop_hz = 0.0
        self._last_error = ""
        self._last_error_code = PiSDErrorCodes.OK
        self.apply_settings(settings or {})
        atexit.register(self.close)

    def _record_error(
        self,
        code: str,
        message: str,
        *,
        severity: str = "error",
        context: dict[str, Any] | None = None,
        exc: BaseException | None = None,
    ) -> ErrorReport:
        report = self.errors.report(code, message, severity=severity, context=context, exc=exc)
        self._last_error = report.message
        self._last_error_code = report.code
        return report

    def apply_settings(self, settings: dict[str, Any] | None) -> dict[str, Any]:
        data = dict(settings or {})
        with self._lock:
            self._settings = {
                "model_id": str(data.get("model_id", self._settings.get("model_id", "")) or "").strip().replace("\\", "/"),
                "max_throttle": clamp_float(data.get("max_throttle", self._settings.get("max_throttle", 0.22)), 0.0, 1.0, 0.22),
                "max_steering": clamp_float(data.get("max_steering", self._settings.get("max_steering", 0.70)), 0.0, 1.0, 0.70),
                "fixed_throttle": clamp_float(data.get("fixed_throttle", self._settings.get("fixed_throttle", 0.16)), 0.0, 1.0, 0.16),
                "steering_smoothing": clamp_float(data.get("steering_smoothing", self._settings.get("steering_smoothing", 0.35)), 0.0, 1.0, 0.35),
                "throttle_smoothing": clamp_float(data.get("throttle_smoothing", self._settings.get("throttle_smoothing", 0.25)), 0.0, 1.0, 0.25),
                "update_hz": clamp_float(data.get("update_hz", self._settings.get("update_hz", 8.0)), 1.0, 20.0, 8.0),
                "command_timeout_s": clamp_float(data.get("command_timeout_s", self._settings.get("command_timeout_s", 0.75)), 0.2, 3.0, 0.75),
                "output_mode": str(data.get("output_mode", self._settings.get("output_mode", "steering_and_throttle")) or "steering_and_throttle"),
                "preview_only_by_default": str(data.get("preview_only_by_default", self._settings.get("preview_only_by_default", True))).lower() not in {"false", "0", "no", "off"},
                # PiSD_0_5_12: motor output enable is passed to start() as a live safety acknowledgement, not persisted in settings.
                "motor_output_enabled": False,
            }
            if self._settings["output_mode"] not in {"steering_only", "steering_and_throttle"}:
                self._settings["output_mode"] = "steering_and_throttle"
        return self.status()

    def status(self) -> dict[str, Any]:
        with self._lock:
            data = {
                "models_dir": str(self.models_dir),
                "running": bool(self._running and self._thread and self._thread.is_alive()),
                "mode": self._mode,
                "model_id": self._model_id,
                "model_path": str(self._model_path or ""),
                "model_loaded": bool(self._model_loaded),
                "model_ready": bool(self._model_ready),
                "backend": self._backend,
                "backend_detail": self._backend_detail,
                "runtime_support": self.runtime_diagnostics(),
                "input_size": {"width": self._input_size[0], "height": self._input_size[1]},
                "input_dtype": self._input_dtype_name,
                "output_names": list(self._output_names),
                "piTrainer_export_compatible": self._backend in {"tflite", "tensorflow.keras"},
                "settings": dict(self._settings),
                "last_raw_prediction": dict(self._last_raw),
                "last_safe_command": dict(self._last_safe),
                "last_motor_output": dict(self._last_motor),
                "last_prediction_at_utc": self._last_prediction_at,
                "last_inference_ms": float(self._last_inference_ms),
                "loop_hz": float(self._last_loop_hz),
                "last_error": self._last_error,
                "last_error_code": self._last_error_code,
                "safety_layer": {
                    "between_ai_and_motors": True,
                    "max_throttle": self._settings.get("max_throttle"),
                    "max_steering": self._settings.get("max_steering"),
                    "output_mode": self._settings.get("output_mode"),
                    "drive_requires_safety_ack": True,
                    "drive_requires_enable_motor_output": True,
                    "reverse_steering_policy": "same_sign",
                    "reverse_steering_note": "Option A: negative throttle keeps the same steering sign before motor mixing.",
                },
            }
        data.update(self.errors.status_fields(limit=5))
        return data

    @staticmethod
    def _module_available(module_name: str) -> bool:
        try:
            return importlib.util.find_spec(module_name) is not None
        except Exception:
            return False

    def runtime_diagnostics(self) -> dict[str, Any]:
        """Return import-level AI runtime support visible to the UI/status log.

        This does not load a model. It only tells the user whether this Python
        environment appears to have a runnable backend for each model family.
        """
        tflite_runtime = self._module_available("tflite_runtime.interpreter")
        ai_edge_litert = self._module_available("ai_edge_litert.interpreter")
        tensorflow = self._module_available("tensorflow")
        return {
            "tflite_runtime": bool(tflite_runtime),
            "ai_edge_litert": bool(ai_edge_litert),
            "tensorflow": bool(tensorflow),
            "tflite": bool(tflite_runtime or ai_edge_litert or tensorflow),
            "keras": bool(tensorflow),
        }

    def list_models(self) -> dict[str, Any]:
        self.models_dir.mkdir(parents=True, exist_ok=True)
        models: list[dict[str, Any]] = []
        for path in sorted(self.models_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in MODEL_EXTENSIONS:
                continue
            try:
                stat = path.stat()
                models.append({
                    "id": str(path.relative_to(self.models_dir)).replace("\\", "/"),
                    "name": path.name,
                    "extension": path.suffix.lower(),
                    "bytes": int(stat.st_size),
                    "modified_at_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "relative_path": str(path.relative_to(self.project_root)).replace("\\", "/"),
                })
            except OSError:
                continue
        return ok_payload("AI model list loaded.", models=models, supported_extensions=sorted(MODEL_EXTENSIONS), models_dir=str(self.models_dir))

    def upload_model(self, filename: Any, file_obj: Any) -> dict[str, Any]:
        """Save an uploaded model file into PiSD/models with a safe filename.

        piTrainer currently exports .keras and .tflite artifacts. This method also
        keeps the existing extension allow-list for future/backward-compatible
        models while preventing uploaded filenames from escaping the models
        folder.
        """
        original = str(filename or "").strip()
        safe_name = self._safe_upload_filename(original)
        if not safe_name:
            report = self._record_error(
                PiSDErrorCodes.AI_MODEL_LOAD_FAILED,
                "Uploaded model filename was missing or unsafe.",
                severity="warning",
                context={"filename": original},
            )
            return report_payload(False, report, ai=self.status())
        suffix = Path(safe_name).suffix.lower()
        if suffix not in MODEL_EXTENSIONS:
            report = self._record_error(
                PiSDErrorCodes.AI_MODEL_LOAD_FAILED,
                "Uploaded model extension is not supported.",
                severity="warning",
                context={"filename": original, "safe_name": safe_name, "supported_extensions": sorted(MODEL_EXTENSIONS)},
            )
            return report_payload(False, report, ai=self.status())
        self.models_dir.mkdir(parents=True, exist_ok=True)
        target = self._dedupe_upload_path(self.models_dir / safe_name)
        root = self.models_dir.resolve()
        try:
            resolved = target.resolve()
            resolved.relative_to(root)
            with resolved.open("wb") as handle:
                shutil.copyfileobj(file_obj, handle)
            if resolved.stat().st_size <= 0:
                resolved.unlink(missing_ok=True)
                raise RuntimeError("uploaded file was empty")
            model_id = str(resolved.relative_to(root)).replace("\\", "/")
            return ok_payload(
                "AI model uploaded.",
                model={
                    "id": model_id,
                    "name": resolved.name,
                    "extension": resolved.suffix.lower(),
                    "bytes": int(resolved.stat().st_size),
                    "relative_path": str(resolved.relative_to(self.project_root)).replace("\\", "/"),
                },
                models=self.list_models().get("models", []),
                supported_extensions=sorted(MODEL_EXTENSIONS),
                ai=self.status(),
            )
        except Exception as exc:
            report = self._record_error(
                PiSDErrorCodes.AI_MODEL_LOAD_FAILED,
                f"Failed to save uploaded AI model: {exc}",
                context={"filename": original, "target": str(target)},
                exc=exc,
            )
            return report_payload(False, report, ai=self.status())

    def delete_model(self, model_id: Any) -> dict[str, Any]:
        model_path, safe_id, report = self._resolve_model(model_id)
        if report is not None:
            return report_payload(False, report, ai=self.status())
        unloaded = False
        try:
            with self._lock:
                was_selected = safe_id == self._model_id
            if was_selected:
                self.stop(stop_motors=False)
            model_path.unlink()
            if was_selected:
                with self._lock:
                    self._clear_loaded_model_locked()
                    self._settings["model_id"] = ""
                    unloaded = True
            return ok_payload(
                "AI model deleted.",
                deleted_model_id=safe_id,
                unloaded_selected_model=unloaded,
                models=self.list_models().get("models", []),
                ai=self.status(),
            )
        except Exception as exc:
            report = self._record_error(
                PiSDErrorCodes.AI_MODEL_LOAD_FAILED,
                f"Failed to delete AI model: {exc}",
                context={"model_id": safe_id, "path": str(model_path)},
                exc=exc,
            )
            return report_payload(False, report, ai=self.status())

    def load_model(self, model_id: Any) -> dict[str, Any]:
        model_path, safe_id, report = self._resolve_model(model_id)
        if report is not None:
            return report_payload(False, report, ai=self.status())
        with self._lock:
            self.stop(stop_motors=False)
            self._model_id = safe_id
            self._model_path = model_path
            self._model = None
            self._input_details = None
            self._output_details = None
            self._output_names = []
            self._backend = "loading"
            self._backend_detail = ""
            self._model_loaded = False
            self._model_ready = False
            self._settings["model_id"] = safe_id
        try:
            suffix = model_path.suffix.lower()
            if suffix == ".tflite":
                self._load_tflite(model_path)
            elif suffix in {".keras", ".h5"}:
                self._load_keras(model_path)
            elif suffix in {".onnx", ".pt"}:
                report = self._record_error(
                    PiSDErrorCodes.AI_MODEL_LOAD_FAILED,
                    f"{suffix} model file was found, but this PiSD runtime does not have a built-in {suffix} inference backend yet.",
                    severity="warning",
                    context={"model_id": safe_id, "path": str(model_path)},
                )
                return report_payload(False, report, ai=self.status())
            else:
                report = self._record_error(PiSDErrorCodes.AI_MODEL_LOAD_FAILED, "Unsupported AI model extension.", context={"model_id": safe_id})
                return report_payload(False, report, ai=self.status())
        except Exception as exc:
            with self._lock:
                self._model = None
                self._input_details = None
                self._output_details = None
                self._output_names = []
                self._backend = "load_failed"
                self._backend_detail = ""
                self._model_loaded = False
                self._model_ready = False
            report = self._record_error(
                PiSDErrorCodes.AI_MODEL_LOAD_FAILED,
                f"Failed to load AI model: {exc}",
                context={"model_id": safe_id, "path": str(model_path), "runtime_support": self.runtime_diagnostics()},
                exc=exc,
            )
            return report_payload(False, report, ai=self.status())
        with self._lock:
            self._model_loaded = True
            self._model_ready = True
            self._last_error = ""
            self._last_error_code = PiSDErrorCodes.OK
        return ok_payload("AI model loaded.", ai=self.status())

    def _ensure_model_ready_for_run(self) -> dict[str, Any] | None:
        with self._lock:
            if self._model_ready:
                return None
            candidate = str(self._model_id or self._settings.get("model_id", "") or "").strip()
        if candidate:
            result = self.load_model(candidate)
            if not result.get("ok"):
                return result
            return None
        report = self._record_error(
            PiSDErrorCodes.AI_MODEL_NOT_LOADED,
            "No runnable AI model is loaded. Select a model and click Load model first.",
            severity="warning",
            context={"runtime_support": self.runtime_diagnostics()},
        )
        return report_payload(False, report, ai=self.status())

    def start(self, camera_service: Any, motor_service: Any, *, mode: Any = "preview", safety_ack: Any = False, enable_motor_output: Any = False) -> dict[str, Any]:
        load_result = self._ensure_model_ready_for_run()
        if load_result is not None:
            return load_result
        requested_mode = str(mode or "preview").strip().lower()
        if requested_mode not in {"preview", "drive"}:
            requested_mode = "preview"
        with self._lock:
            if not self._model_ready:
                report = self._record_error(PiSDErrorCodes.AI_MODEL_NOT_LOADED, "AI mode cannot start because no runnable model is loaded.", severity="warning", context={"runtime_support": self.runtime_diagnostics()})
                return report_payload(False, report, ai=self.status())
            if self._thread and self._thread.is_alive():
                report = self._record_error(PiSDErrorCodes.AI_RUNTIME_FAILED, "AI mode is already running.", severity="warning")
                return report_payload(False, report, ai=self.status())
            if requested_mode == "drive":
                if not bool(safety_ack):
                    report = self._record_error(PiSDErrorCodes.AI_UNARMED, "AI drive refused because the safety acknowledgement was not checked.", severity="warning")
                    return report_payload(False, report, ai=self.status())
                if motor_service.hardware_enabled and not bool(enable_motor_output):
                    report = self._record_error(PiSDErrorCodes.AI_UNARMED, "AI drive refused because motor output was not enabled.", severity="warning")
                    return report_payload(False, report, ai=self.status())
            self._stop_event.clear()
            self._mode = requested_mode
            self._running = True
            self._thread = threading.Thread(
                target=self._run_loop,
                args=(camera_service, motor_service, requested_mode == "drive"),
                name="PiSDAIDriveThread",
                daemon=True,
            )
            self._thread.start()
        return ok_payload("AI mode started.", ai=self.status())

    def stop(self, motor_service: Any | None = None, *, stop_motors: bool = True) -> dict[str, Any]:
        with self._lock:
            thread = self._thread
            self._stop_event.set()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        with self._lock:
            self._running = False
            self._thread = None
            self._mode = "idle"
            self._last_raw = {"steering": 0.0, "throttle": 0.0}
            self._last_safe = {"steering": 0.0, "throttle": 0.0}
            self._last_loop_hz = 0.0
        if stop_motors and motor_service is not None:
            try:
                motor_service.stop()
                with self._lock:
                    self._last_motor = {"left": 0.0, "right": 0.0}
            except Exception as exc:
                report = self._record_error(PiSDErrorCodes.AI_RUNTIME_FAILED, f"AI stop could not stop motors: {exc}", exc=exc)
                return report_payload(False, report, ai=self.status())
        return ok_payload("AI mode stopped.", ai=self.status())

    def predict_once(self, camera_service: Any, motor_service: Any | None = None, *, drive: bool = False) -> dict[str, Any]:
        load_result = self._ensure_model_ready_for_run()
        if load_result is not None:
            return load_result
        try:
            frame = self._get_frame(camera_service)
            started = time.perf_counter()
            raw_steering, raw_throttle = self._predict_from_jpeg(frame)
            inference_ms = (time.perf_counter() - started) * 1000.0
            safe = self.apply_safety(raw_steering, raw_throttle)
            left = right = 0.0
            left_intended = right_intended = 0.0
            if drive and motor_service is not None:
                left, right = motor_service.update(steering=safe["steering"], throttle=safe["throttle"])
                motor_status = motor_service.status()
                left_intended = float(motor_status.get("last_intended_left", left) or 0.0)
                right_intended = float(motor_status.get("last_intended_right", right) or 0.0)
            with self._lock:
                self._last_raw = {"steering": float(raw_steering), "throttle": float(raw_throttle)}
                self._last_safe = {"steering": float(safe["steering"]), "throttle": float(safe["throttle"])}
                self._last_motor = {"left": float(left_intended), "right": float(right_intended), "left_hardware": float(left), "right_hardware": float(right)}
                self._last_prediction_at = _utc_now()
                self._last_inference_ms = float(inference_ms)
                self._last_error = ""
                self._last_error_code = PiSDErrorCodes.OK
            return ok_payload("AI prediction completed.", raw_prediction=self._last_raw, safe_command=self._last_safe, motor_output=self._last_motor, ai=self.status())
        except Exception as exc:
            report = self._record_error(PiSDErrorCodes.AI_INFERENCE_FAILED, f"AI prediction failed: {exc}", exc=exc)
            if drive and motor_service is not None:
                try:
                    motor_service.stop()
                except Exception:
                    pass
            return report_payload(False, report, ai=self.status())

    def apply_safety(self, raw_steering: Any, raw_throttle: Any) -> dict[str, float]:
        with self._lock:
            settings = dict(self._settings)
            previous = dict(self._last_safe)
        steering = clamp_float(raw_steering, -1.0, 1.0, 0.0)
        throttle = clamp_float(raw_throttle, -1.0, 1.0, 0.0)
        max_steering = clamp_float(settings.get("max_steering", 0.70), 0.0, 1.0, 0.70)
        max_throttle = clamp_float(settings.get("max_throttle", 0.22), 0.0, 1.0, 0.22)
        fixed_throttle = clamp_float(settings.get("fixed_throttle", 0.16), 0.0, 1.0, 0.16)
        if settings.get("output_mode") == "steering_only":
            # Fixed-throttle mode should keep moving straight; do not stop just because steering is near zero.
            throttle = fixed_throttle
        steering = max(-max_steering, min(max_steering, steering))
        throttle = max(-max_throttle, min(max_throttle, throttle))
        # PiSD_0_5_5 Option A: do not invert steering when throttle is negative.
        # MotorService and the preview overlay both receive the same steering sign.
        steer_alpha = clamp_float(settings.get("steering_smoothing", 0.35), 0.0, 1.0, 0.35)
        throttle_alpha = clamp_float(settings.get("throttle_smoothing", 0.25), 0.0, 1.0, 0.25)
        steering = previous.get("steering", 0.0) + (steering - previous.get("steering", 0.0)) * (1.0 - steer_alpha)
        throttle = previous.get("throttle", 0.0) + (throttle - previous.get("throttle", 0.0)) * (1.0 - throttle_alpha)
        return {"steering": float(max(-max_steering, min(max_steering, steering))), "throttle": float(max(-max_throttle, min(max_throttle, throttle)))}

    def close(self) -> None:
        try:
            self.stop(stop_motors=False)
        except Exception:
            pass

    def _clear_loaded_model_locked(self) -> None:
        self._model_id = ""
        self._model_path = None
        self._model = None
        self._input_details = None
        self._output_details = None
        self._output_names = []
        self._backend = "none"
        self._backend_detail = ""
        self._model_loaded = False
        self._model_ready = False
        self._last_raw = {"steering": 0.0, "throttle": 0.0}
        self._last_safe = {"steering": 0.0, "throttle": 0.0}
        self._last_motor = {"left": 0.0, "right": 0.0}

    @staticmethod
    def _safe_upload_filename(filename: str) -> str:
        name = Path(str(filename or "").replace("\\", "/")).name.strip()
        if not name:
            return ""
        stem = Path(name).stem
        suffix = Path(name).suffix.lower()
        safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
        if not safe_stem or suffix not in MODEL_EXTENSIONS:
            return ""
        return f"{safe_stem}{suffix}"

    @staticmethod
    def _dedupe_upload_path(path: Path) -> Path:
        if not path.exists():
            return path
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        candidate = path.with_name(f"{path.stem}_{stamp}{path.suffix}")
        counter = 2
        while candidate.exists():
            candidate = path.with_name(f"{path.stem}_{stamp}_{counter}{path.suffix}")
            counter += 1
        return candidate

    def _resolve_model(self, model_id: Any) -> tuple[Path, str, ErrorReport | None]:
        raw = str(model_id or "").strip().replace("\\", "/")
        if not raw or raw.startswith("/") or ".." in Path(raw).parts:
            report = self._record_error(PiSDErrorCodes.AI_MODEL_NOT_FOUND, "AI model id was missing or unsafe.", severity="warning", context={"model_id": raw})
            return self.models_dir, raw, report
        path = (self.models_dir / raw).resolve()
        root = self.models_dir.resolve()
        try:
            safe_id = str(path.relative_to(root)).replace("\\", "/")
        except ValueError:
            report = self._record_error(PiSDErrorCodes.AI_MODEL_NOT_FOUND, "AI model path escaped the models folder.", severity="warning", context={"model_id": raw})
            return path, raw, report
        if path.suffix.lower() not in MODEL_EXTENSIONS or not path.exists() or not path.is_file():
            report = self._record_error(PiSDErrorCodes.AI_MODEL_NOT_FOUND, "AI model file was not found in the models folder.", severity="warning", context={"model_id": raw, "path": str(path)})
            return path, safe_id, report
        return path, safe_id, None

    @staticmethod
    def _detail_shape_list(detail: dict[str, Any]) -> list[int]:
        """Return a plain Python shape list from a TensorFlow Lite tensor detail.

        TFLite runtimes commonly expose ``detail["shape"]`` as a NumPy array.
        NumPy arrays cannot be used with boolean fallback expressions such as
        ``detail.get("shape") or []`` because multi-value arrays have no single
        truth value.  Keep this conversion explicit so loading piTrainer-exported
        .tflite models does not fail before inference starts.
        """
        raw_shape = detail.get("shape")
        if raw_shape is None:
            return []
        try:
            return [int(value) for value in list(raw_shape)]
        except Exception:
            try:
                return [int(raw_shape)]
            except Exception:
                return []

    @staticmethod
    def _dtype_name(value: Any, fallback: str = "float32") -> str:
        try:
            import numpy as np

            return str(np.dtype(value).name)
        except Exception:
            return str(value or fallback)

    def _load_tflite(self, model_path: Path) -> None:
        interpreter_cls = None
        backend_detail = ""
        import_errors: list[str] = []
        try:
            from tflite_runtime.interpreter import Interpreter  # type: ignore

            interpreter_cls = Interpreter
            backend_detail = "tflite_runtime"
        except Exception as exc:
            import_errors.append(f"tflite_runtime: {type(exc).__name__}: {exc}")
        if interpreter_cls is None:
            try:
                from ai_edge_litert.interpreter import Interpreter  # type: ignore

                interpreter_cls = Interpreter
                backend_detail = "ai_edge_litert"
            except Exception as exc:
                import_errors.append(f"ai_edge_litert: {type(exc).__name__}: {exc}")
        if interpreter_cls is None:
            try:
                import tensorflow as tf  # type: ignore

                interpreter_cls = tf.lite.Interpreter
                backend_detail = "tensorflow.lite"
            except Exception as exc:
                import_errors.append(f"tensorflow: {type(exc).__name__}: {exc}")
        if interpreter_cls is None:
            raise RuntimeError("TFLite runtime is not installed. Install a TFLite runtime backend, then reload the model. Import attempts: " + "; ".join(import_errors))
        self._pending_backend_detail = backend_detail
        interpreter = interpreter_cls(model_path=str(model_path))
        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        if not input_details or not output_details:
            raise RuntimeError("TFLite model did not expose input/output tensors.")
        shape = self._detail_shape_list(input_details[0])
        if len(shape) >= 4:
            # usually NHWC: [1, height, width, channels]
            self._input_size = (int(shape[2] or 160), int(shape[1] or 120))
        self._input_dtype_name = self._dtype_name(input_details[0].get("dtype", "float32"))
        output_names = [str(item.get("name") if item.get("name") is not None else item.get("index", "")) for item in output_details]
        with self._lock:
            self._model = interpreter
            self._input_details = input_details
            self._output_details = output_details
            self._output_names = output_names
            self._backend = "tflite"
            self._backend_detail = getattr(self, "_pending_backend_detail", "") or "tflite"

    def _load_keras(self, model_path: Path) -> None:
        try:
            import tensorflow as tf  # type: ignore
        except Exception as exc:
            raise RuntimeError("TensorFlow is not installed, so .keras/.h5 models cannot be loaded on this PiSD runtime.") from exc
        model = tf.keras.models.load_model(str(model_path), compile=False)
        input_shape = getattr(model, "input_shape", None)
        if isinstance(input_shape, list):
            input_shape = input_shape[0]
        if input_shape is not None and len(input_shape) >= 4:
            self._input_size = (int(input_shape[2] or 160), int(input_shape[1] or 120))
        self._input_dtype_name = "float32"
        output_names = [str(name) for name in (getattr(model, "output_names", None) or [])]
        with self._lock:
            self._model = model
            self._output_names = output_names
            self._backend = "tensorflow.keras"
            self._backend_detail = "tensorflow.keras"

    def _get_frame(self, camera_service: Any) -> bytes:
        try:
            camera_service.start()
        except Exception:
            pass
        frame, _seq, _source_frame_at, _byte_count = camera_service.wait_for_jpeg_frame(timeout=1.0)
        if not frame:
            raise RuntimeError("No camera frame available for AI inference.")
        return frame

    def _prepare_input(self, frame: bytes) -> Any:
        from io import BytesIO

        import numpy as np
        from PIL import Image

        image = Image.open(BytesIO(frame)).convert("RGB")
        image = image.resize(self._input_size)
        array = np.asarray(image).astype("float32") / 255.0
        with self._lock:
            backend = self._backend
        return np.expand_dims(array, axis=0), backend

    @staticmethod
    def _coerce_tflite_input(tensor: Any, input_detail: dict[str, Any]) -> Any:
        import numpy as np

        dtype = input_detail.get("dtype", tensor.dtype)
        if np.issubdtype(dtype, np.floating):
            return tensor.astype(dtype)
        q_scale, q_zero = input_detail.get("quantization", (0.0, 0)) or (0.0, 0)
        if q_scale and float(q_scale) > 0.0:
            quantized = np.round((tensor / float(q_scale)) + float(q_zero))
        elif np.dtype(dtype) == np.dtype("uint8"):
            quantized = np.round(tensor * 255.0)
        else:
            quantized = np.round(tensor)
        info = np.iinfo(dtype)
        return np.clip(quantized, info.min, info.max).astype(dtype)

    @staticmethod
    def _first_scalar(value: Any) -> float | None:
        import numpy as np

        try:
            values = np.asarray(value).reshape(-1).astype("float32")
        except Exception:
            return None
        if values.size <= 0:
            return None
        scalar = float(values[0])
        return scalar if math.isfinite(scalar) else None

    def _commands_from_prediction_output(self, output: Any, output_names: list[str] | None = None) -> tuple[float, float]:
        """Return steering/throttle from piTrainer Keras/TFLite output shapes.

        piTrainer's current CNN exports two named outputs: ``steering`` and
        ``throttle``. Keras may return those as a dict, a list/tuple, or a
        two-column array depending on backend and model format. TFLite may expose
        either one two-value tensor or two separate output tensors. This parser
        accepts all of those forms so PiSD can run models exported by piTrainer.
        """
        import numpy as np

        steering: float | None = None
        throttle: float | None = None

        if isinstance(output, dict):
            lowered = {str(key).lower(): value for key, value in output.items()}
            for key, value in lowered.items():
                if steering is None and "steer" in key:
                    steering = self._first_scalar(value)
                if throttle is None and ("throttle" in key or "throt" in key):
                    throttle = self._first_scalar(value)
            if steering is None and "0" in lowered:
                steering = self._first_scalar(lowered["0"])
            if throttle is None and "1" in lowered:
                throttle = self._first_scalar(lowered["1"])
        elif isinstance(output, (list, tuple)):
            names = [str(name).lower() for name in (output_names or [])]
            for index, value in enumerate(output):
                name = names[index] if index < len(names) else ""
                if steering is None and "steer" in name:
                    steering = self._first_scalar(value)
                if throttle is None and ("throttle" in name or "throt" in name):
                    throttle = self._first_scalar(value)
            if steering is None or throttle is None:
                if len(output) == 1:
                    values = np.asarray(output[0]).reshape(-1).astype("float32")
                    if steering is None and values.size >= 1:
                        steering = float(values[0])
                    if throttle is None and values.size >= 2:
                        throttle = float(values[1])
                else:
                    if steering is None and len(output) >= 1:
                        steering = self._first_scalar(output[0])
                    if throttle is None and len(output) >= 2:
                        throttle = self._first_scalar(output[1])
        else:
            values = np.asarray(output).reshape(-1).astype("float32")
            if values.size >= 1:
                steering = float(values[0])
            if values.size >= 2:
                throttle = float(values[1])

        if steering is None or not math.isfinite(float(steering)):
            steering = 0.0
        if throttle is None or not math.isfinite(float(throttle)):
            throttle = 0.0
        return clamp_float(steering, -1.0, 1.0, 0.0), clamp_float(throttle, -1.0, 1.0, 0.0)

    def _predict_from_jpeg(self, frame: bytes) -> tuple[float, float]:
        tensor, backend = self._prepare_input(frame)
        with self._lock:
            model = self._model
            input_details = self._input_details
            output_details = self._output_details
            output_names = list(self._output_names)
        if backend == "tflite":
            input_detail = input_details[0]
            input_index = input_detail["index"]
            model.set_tensor(input_index, self._coerce_tflite_input(tensor, input_detail))
            model.invoke()
            outputs = [model.get_tensor(detail["index"]) for detail in output_details]
            return self._commands_from_prediction_output(outputs, output_names)
        if backend == "tensorflow.keras":
            output = model.predict(tensor, verbose=0)
            return self._commands_from_prediction_output(output, output_names)
        raise RuntimeError(f"Unsupported AI inference backend: {backend}")

    def _run_loop(self, camera_service: Any, motor_service: Any, drive: bool) -> None:
        last_tick = time.perf_counter()
        try:
            while not self._stop_event.is_set():
                started = time.perf_counter()
                result = self.predict_once(camera_service, motor_service, drive=drive)
                if not result.get("ok"):
                    break
                elapsed = time.perf_counter() - started
                with self._lock:
                    self._last_loop_hz = 1.0 / max(0.001, time.perf_counter() - last_tick)
                last_tick = time.perf_counter()
                interval = 1.0 / max(1.0, float(self._settings.get("update_hz", 8.0)))
                time.sleep(max(0.0, interval - elapsed))
        except Exception as exc:
            self._record_error(PiSDErrorCodes.AI_RUNTIME_FAILED, f"AI runtime loop failed: {exc}", exc=exc)
        finally:
            if drive:
                try:
                    motor_service.stop()
                except Exception:
                    pass
            with self._lock:
                self._running = False
                self._mode = "idle"
                self._thread = None
                if drive:
                    self._last_motor = {"left": 0.0, "right": 0.0}
