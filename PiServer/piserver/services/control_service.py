from __future__ import annotations

import threading
import time

from piserver.core.runtime_state import RuntimeState


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

        self.apply_runtime_config(self.config_store.load(), initial=True)

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        try:
            self.motor_service.stop()
        except Exception:
            pass

    def _loop(self):
        period = 1.0 / self.loop_hz
        while self.running:
            start = time.time()
            frame = self.camera_service.get_latest_frame()
            with self.lock:
                self.state.fps = self.camera_service.get_fps()
                self.state.camera_backend = getattr(self.camera_service, "backend", "unknown")
                self.state.camera_width = int(getattr(self.camera_service, "width", 0))
                self.state.camera_height = int(getattr(self.camera_service, "height", 0))
                self.state.camera_format = str(getattr(self.camera_service, "camera_format", "BGR888"))
                self.state.active_model = self.model_service.get_active_name()

                if self.state.safety_stop:
                    steer, throttle = 0.0, 0.0
                else:
                    algo = self.algorithms.get(self.state.active_algorithm, self.algorithms["manual"])
                    steer, throttle = algo.compute(self.state, self.camera_service, self.model_service)

                steer = max(-1.0, min(1.0, float(steer)))
                throttle = max(0.0, min(float(throttle), float(self.state.max_throttle)))

                left, right = self.motor_service.update(
                    steering=steer,
                    throttle=throttle,
                    steer_mix=self.state.steer_mix,
                )
                self.state.applied_steering = steer
                self.state.applied_throttle = throttle
                self.state.motor_left = left
                self.state.motor_right = right
                self.state.recording = bool(self.recorder_service.recording)
                self.state.last_update = time.time()
                snapshot = self.state.snapshot()

            if self.recorder_service.recording:
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
                self.state.manual_steering = max(-1.0, min(1.0, float(steering)))
            if throttle is not None:
                self.state.manual_throttle = max(0.0, min(1.0, float(throttle)))
            self.state.system_message = "Manual controls updated."

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
                self.state.max_throttle = max(0.0, min(1.0, float(max_throttle)))
            if steer_mix is not None:
                self.state.steer_mix = max(0.0, min(1.0, float(steer_mix)))
            if current_page:
                self.state.current_page = str(current_page)
            self.state.system_message = "Runtime parameters updated."

    def toggle_recording(self) -> bool:
        with self.lock:
            self.recorder_service.toggle()
            self.state.recording = bool(self.recorder_service.recording)
            self.state.system_message = "Recording started." if self.state.recording else "Recording stopped."
            return self.state.recording

    def set_safety_stop(self, enabled: bool):
        with self.lock:
            self.state.safety_stop = bool(enabled)
            if enabled:
                self.state.manual_throttle = 0.0
                self.state.system_message = "Emergency stop engaged."
            else:
                self.state.system_message = "Emergency stop cleared."

    def get_runtime_config(self) -> dict:
        with self.lock:
            return {
                "active_algorithm": self.state.active_algorithm,
                "max_throttle": self.state.max_throttle,
                "steer_mix": self.state.steer_mix,
                "current_page": self.state.current_page,
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
        with self.lock:
            algo = data.get("active_algorithm")
            if algo in self.algorithms:
                self.state.active_algorithm = algo
            if "max_throttle" in data:
                self.state.max_throttle = max(0.0, min(1.0, float(data["max_throttle"])))
            if "steer_mix" in data:
                self.state.steer_mix = max(0.0, min(1.0, float(data["steer_mix"])))
            if "current_page" in data:
                self.state.current_page = str(data["current_page"])
            self.state.system_message = "Runtime config loaded." if not initial else "Runtime config applied."

    def reload_runtime_config(self) -> dict:
        data = self.config_store.load()
        self.apply_runtime_config(data)
        return self.get_runtime_config()

    def can_run_system_action(self) -> tuple[bool, str]:
        snap = self.snapshot()
        if snap["recording"]:
            return False, "Stop recording before update/restart."
        if snap["applied_throttle"] > 0.01 or snap["manual_throttle"] > 0.01:
            return False, "Throttle must be zero before update/restart."
        if not snap["safety_stop"]:
            return False, "Engage emergency stop before update/restart."
        return True, "OK"
