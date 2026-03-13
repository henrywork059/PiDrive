from __future__ import annotations

import threading
import time

from piserver.core.runtime_state import RuntimeState


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))


def _parse_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


class ControlService:
    def __init__(
        self,
        camera_service,
        motor_service,
        model_service,
        recorder_service,
        algorithms: dict,
        config_store,
        loop_hz: int = 20,
    ):
        self.camera_service = camera_service
        self.motor_service = motor_service
        self.model_service = model_service
        self.recorder_service = recorder_service
        self.algorithms = algorithms
        self.config_store = config_store
        self.state = RuntimeState()
        self.loop_hz = max(1, int(loop_hz))
        self.lock = threading.RLock()
        self.running = False
        self.thread = None
        self._processing_enabled_cached = None

        self.apply_runtime_config(self.config_store.load(), initial=True)

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self._hard_stop_outputs()

    def _hard_stop_outputs(self):
        try:
            self.motor_service.stop()
        except Exception:
            pass

    def _apply_safe_stop_locked(self):
        self.state.manual_steering = 0.0
        self.state.manual_throttle = 0.0
        self.state.applied_steering = 0.0
        self.state.applied_throttle = 0.0
        self.state.motor_left = 0.0
        self.state.motor_right = 0.0

    def _update_motor_state_locked(self):
        cfg = self.motor_service.get_config()
        self.state.motor_left_direction = int(cfg.get("left_direction", 1))
        self.state.motor_right_direction = int(cfg.get("right_direction", 1))
        self.state.motor_left_max_speed = float(cfg.get("left_max_speed", 1.0))
        self.state.motor_right_max_speed = float(cfg.get("right_max_speed", 1.0))
        self.state.motor_left_bias = float(cfg.get("left_bias", 0.0))
        self.state.motor_right_bias = float(cfg.get("right_bias", 0.0))

    def _loop(self):
        period = 1.0 / self.loop_hz
        while self.running:
            start = time.time()
            with self.lock:
                self.state.fps = self.camera_service.get_fps()
                self.state.camera_backend = getattr(self.camera_service, "backend", "unknown")
                self.state.camera_width = int(getattr(self.camera_service, "width", 0))
                self.state.camera_height = int(getattr(self.camera_service, "height", 0))
                self.state.camera_format = str(getattr(self.camera_service, "camera_format", "BGR888"))
                self.state.camera_preview_live = bool(getattr(self.camera_service, "preview_live", False))
                self.state.camera_error = str(getattr(self.camera_service, "last_error", "") or "")
                self.state.active_model = self.model_service.get_active_name()
                self._update_motor_state_locked()

                processing_needed = (not self.state.safety_stop) and (
                    self.state.active_algorithm != "manual" or bool(self.recorder_service.recording)
                )
                if processing_needed != self._processing_enabled_cached:
                    try:
                        self.camera_service.set_processing_enabled(processing_needed)
                        self._processing_enabled_cached = processing_needed
                    except Exception:
                        pass

                if self.state.safety_stop:
                    steer, throttle = 0.0, 0.0
                else:
                    algo = self.algorithms.get(self.state.active_algorithm, self.algorithms["manual"])
                    try:
                        steer, throttle = algo.compute(self.state, self.camera_service, self.model_service)
                    except Exception as exc:
                        steer, throttle = 0.0, 0.0
                        self.state.system_message = f"Algorithm error: {exc}"

                steer = _clamp(float(steer), -1.0, 1.0)
                throttle = _clamp(float(throttle), -float(self.state.max_throttle), float(self.state.max_throttle))

                try:
                    left, right = self.motor_service.update(
                        steering=steer,
                        throttle=throttle,
                        steer_mix=self.state.steer_mix,
                    )
                except Exception as exc:
                    left, right = 0.0, 0.0
                    self._hard_stop_outputs()
                    self.state.system_message = f"Motor update failed: {exc}"
                self.state.applied_steering = steer
                self.state.applied_throttle = throttle
                self.state.motor_left = left
                self.state.motor_right = right
                self.state.recording = bool(self.recorder_service.recording)
                self.state.last_update = time.time()
                snapshot = self.state.snapshot()

            if self.recorder_service.recording:
                frame = self.camera_service.get_latest_frame(copy=True)
                self.recorder_service.maybe_record(frame, snapshot)

            elapsed = time.time() - start
            if elapsed < period:
                time.sleep(period - elapsed)

    def snapshot(self) -> dict:
        with self.lock:
            return self.state.snapshot()

    def set_manual_controls(self, steering=None, throttle=None):
        with self.lock:
            if steering is not None:
                self.state.manual_steering = _clamp(_parse_float(steering, self.state.manual_steering), -1.0, 1.0)
            if throttle is not None:
                self.state.manual_throttle = _clamp(_parse_float(throttle, self.state.manual_throttle), -1.0, 1.0)
            self.state.system_message = "Manual controls updated."
        return True, "OK"

    def select_algorithm(self, name: str) -> tuple[bool, str]:
        name = str(name or "").strip()
        if name not in self.algorithms:
            return False, "Unknown algorithm."
        with self.lock:
            self.state.active_algorithm = name
            self.state.system_message = f"Algorithm switched to {name}."
        return True, name

    def set_runtime_parameters(self, max_throttle=None, steer_mix=None, current_page=None):
        with self.lock:
            if max_throttle is not None:
                self.state.max_throttle = _clamp(_parse_float(max_throttle, self.state.max_throttle), 0.0, 1.0)
            if steer_mix is not None:
                self.state.steer_mix = _clamp(_parse_float(steer_mix, self.state.steer_mix), 0.0, 1.0)
            if current_page:
                self.state.current_page = str(current_page)
            self.state.system_message = "Runtime parameters updated."
        return True, "OK"

    def toggle_recording(self) -> tuple[bool, bool, str]:
        with self.lock:
            self.recorder_service.toggle()
            self.state.recording = bool(self.recorder_service.recording)
            self.state.system_message = "Recording started." if self.state.recording else "Recording stopped."
            return True, self.state.recording, self.state.system_message

    def set_safety_stop(self, enabled: bool):
        with self.lock:
            self.state.safety_stop = bool(enabled)
            if enabled:
                self._apply_safe_stop_locked()
                self.state.system_message = "Emergency stop engaged."
            else:
                self.state.system_message = "Emergency stop cleared."
        if enabled:
            self._hard_stop_outputs()

    def get_runtime_config(self) -> dict:
        with self.lock:
            return {
                "active_algorithm": self.state.active_algorithm,
                "max_throttle": self.state.max_throttle,
                "steer_mix": self.state.steer_mix,
                "current_page": self.state.current_page,
                "camera": self.camera_service.get_config(),
                "motor": self.motor_service.get_config(),
            }

    def save_runtime_config(self) -> dict:
        data = self.get_runtime_config()
        self.config_store.save(data)
        with self.lock:
            self.state.system_message = "Runtime config saved."
        return data

    def apply_runtime_config(self, data: dict, initial: bool = False):
        if not isinstance(data, dict):
            return
        motor_cfg = data.get("motor")
        if isinstance(motor_cfg, dict):
            self.motor_service.apply_settings(motor_cfg)

        with self.lock:
            algo = data.get("active_algorithm")
            if algo in self.algorithms:
                self.state.active_algorithm = algo
            if "max_throttle" in data:
                self.state.max_throttle = _clamp(_parse_float(data["max_throttle"], self.state.max_throttle), 0.0, 1.0)
            if "steer_mix" in data:
                self.state.steer_mix = _clamp(_parse_float(data["steer_mix"], self.state.steer_mix), 0.0, 1.0)
            if "current_page" in data:
                self.state.current_page = str(data["current_page"])
            self._update_motor_state_locked()
            self.state.system_message = "Runtime config loaded." if not initial else "Runtime config applied."
        camera_cfg = data.get("camera")
        if isinstance(camera_cfg, dict):
            self.camera_service.apply_settings(camera_cfg, restart=not initial)

    def reload_runtime_config(self) -> dict:
        data = self.config_store.load()
        self.apply_runtime_config(data)
        return self.get_runtime_config()
