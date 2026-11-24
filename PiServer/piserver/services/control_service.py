from __future__ import annotations

import math
import threading
import time
from typing import Any

from piserver.core.runtime_state import RuntimeState
from piserver.core.latency_metrics import RollingLatency
from piserver.core.value_utils import parse_finite_float


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, float(value)))


def _parse_input_float(value: Any) -> float:
    """Strict parser for controls; malformed/non-finite inputs must not energize motors."""
    if isinstance(value, bool):
        raise ValueError("Boolean is not a numeric control value.")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Invalid numeric control value.") from exc
    if not math.isfinite(result):
        raise ValueError("Control values must be finite.")
    return result


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
        # A manual command is a short lease, not a persistent motor setpoint.
        # Deliberately not written to the user's runtime.json.
        self.performance = RollingLatency(('controller_loop', 'motor_apply'))
        self.manual_command_timeout_s = 0.85
        self._manual_command_at: float | None = None
        self._manual_command_timed_out = False
        self.camera_frame_timeout_s = 0.75
        self._camera_wait_started = None
        self._camera_seen_fresh = False
        self._camera_fault_latched = False

        self.apply_runtime_config(self.config_store.load(), initial=True)

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True, name="PiServerControlLoop")
        self.thread.start()

    def stop(self):
        self.running = False
        self._hard_stop_outputs()
        thread = self.thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)

    def invalidate_processing_state_cache(self):
        with self.lock:
            self._processing_enabled_cached = None

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
        self.state.motor_steering_direction = int(cfg.get("steering_direction", 1))
        self.state.motor_left_max_speed = float(cfg.get("left_max_speed", 1.0))
        self.state.motor_right_max_speed = float(cfg.get("right_max_speed", 1.0))
        self.state.motor_left_bias = float(cfg.get("left_bias", 0.0))
        self.state.motor_right_bias = float(cfg.get("right_bias", 0.0))

    def _fresh_camera_sample(self):
        try:
            frame, captured_at = self.camera_service.get_raw_frame_sample()
            age = time.monotonic() - float(captured_at)
            if frame is not None and math.isfinite(age) and 0.0 <= age <= self.camera_frame_timeout_s:
                return frame, captured_at
        except (AttributeError, TypeError, ValueError, OverflowError, RuntimeError):
            pass
        return None, None

    def _latch_camera_fault_locked(self):
        self._camera_fault_latched = True
        self.state.safety_stop = True
        self._apply_safe_stop_locked()
        self._manual_command_at = None
        self._manual_command_timed_out = False
        self.state.system_message = "Autonomous camera frame missing or stale; emergency stop engaged. Verify camera and explicitly rearm."
        self._hard_stop_outputs()

    def _loop(self):
        period = 1.0 / self.loop_hz
        while self.running:
            start = time.time()
            cycle_started = self.performance.start()
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

                # Keep real raw capture active during a camera-fault latch so
                # the explicit rearm check can observe actual recovery.
                processing_needed = self._camera_fault_latched or ((not self.state.safety_stop) and (
                    self.state.active_algorithm != "manual" or bool(self.recorder_service.recording)
                ))
                if processing_needed != self._processing_enabled_cached:
                    try:
                        self.camera_service.set_processing_enabled(processing_needed)
                        self._processing_enabled_cached = processing_needed
                    except Exception:
                        pass

                force_zero = bool(self.state.safety_stop)
                if self.state.active_algorithm == "manual":
                    now = time.monotonic()
                    if self._manual_command_at is None or now - self._manual_command_at > self.manual_command_timeout_s:
                        if self._manual_command_at is not None:
                            was_moving = abs(self.state.manual_steering) > 1e-4 or abs(self.state.manual_throttle) > 1e-4
                            self._manual_command_timed_out = was_moving
                            if was_moving:
                                self.state.system_message = "Manual control timed out; motors stopped."
                            self._apply_safe_stop_locked()
                            self._manual_command_at = None
                        force_zero = True

                steer, throttle = 0.0, 0.0
                autonomous = self.state.active_algorithm in {"auto_steer", "autopilot"}
                frame, captured_at = None, None
                if not autonomous:
                    self._camera_wait_started = None
                    self._camera_seen_fresh = False
                elif not force_zero:
                    now = time.monotonic()
                    if self._camera_wait_started is None:
                        self._camera_wait_started = now
                    frame, captured_at = self._fresh_camera_sample()
                    if frame is None:
                        # Initial processing can need a new frame. Hold zero
                        # during that short grace period; never infer on a cache.
                        force_zero = True
                        if self._camera_seen_fresh or now - self._camera_wait_started >= self.camera_frame_timeout_s:
                            self._latch_camera_fault_locked()
                    else:
                        self._camera_seen_fresh = True
                if not force_zero:
                    algo = self.algorithms.get(self.state.active_algorithm, self.algorithms["manual"])
                    try:
                        if autonomous:
                            steer, throttle = algo.compute_from_frame(self.state, frame, self.model_service)
                            age = time.monotonic() - float(captured_at)
                            current_frame, _ = self._fresh_camera_sample()
                            if current_frame is None or not math.isfinite(age) or not 0.0 <= age <= self.camera_frame_timeout_s:
                                force_zero = True
                                self._latch_camera_fault_locked()
                        else:
                            steer, throttle = algo.compute(self.state, self.camera_service, self.model_service)
                        if not (math.isfinite(float(steer)) and math.isfinite(float(throttle))):
                            raise ValueError("non-finite algorithm output")
                    except Exception as exc:
                        force_zero = True
                        self.state.system_message = f"Algorithm error: {exc}"

                # Never apply steer bias after a safety stop, timeout, or algorithm error.
                if force_zero or (abs(steer) < 1e-4 and abs(throttle) < 1e-4):
                    steer, throttle = 0.0, 0.0
                else:
                    steer = _clamp(parse_finite_float(steer, 0.0) + parse_finite_float(self.state.steer_bias, 0.0), -1.0, 1.0)
                    throttle = _clamp(
                        parse_finite_float(throttle, 0.0),
                        -parse_finite_float(self.state.max_throttle, 0.0),
                        parse_finite_float(self.state.max_throttle, 0.0),
                    )

                try:
                    motor_started = self.performance.start()
                    left, right = self.motor_service.update(
                        steering=steer,
                        throttle=throttle,
                        steer_mix=self.state.steer_mix,
                    )
                    self.performance.observe_elapsed('motor_apply', motor_started)
                except Exception as exc:
                    left, right = 0.0, 0.0
                    steer, throttle = 0.0, 0.0
                    self._hard_stop_outputs()
                    self.state.safety_stop = True
                    self._apply_safe_stop_locked()
                    self._manual_command_at = None
                    self.state.system_message = f"Motor update failed; emergency stop engaged: {exc}"
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

            self.performance.observe_elapsed('controller_loop', cycle_started)
            elapsed = time.time() - start
            if elapsed < period:
                time.sleep(period - elapsed)

    def snapshot(self) -> dict:
        with self.lock:
            data = self.state.snapshot()
            data["performance"] = self.performance.snapshot()
            data["manual_command_timeout_s"] = self.manual_command_timeout_s
            data["manual_command_age_s"] = (
                round(max(0.0, time.monotonic() - self._manual_command_at), 3)
                if self._manual_command_at is not None else None
            )
            data["manual_command_timed_out"] = self._manual_command_timed_out
            data["camera_frame_timeout_s"] = self.camera_frame_timeout_s
            data["camera_fault_latched"] = self._camera_fault_latched
            # One lock-held view keeps legacy safety_stop and the U28 contract consistent.
            data["safety"] = self.safety_status()
        try:
            data.update(self.recorder_service.get_status())
        except Exception:
            pass
        return data

    def apply_control_update(self, data: dict) -> tuple[bool, str]:
        """Validate an entire command before applying any changes to runtime state."""
        if not isinstance(data, dict):
            return False, "Expected a JSON object."

        limits = {
            "steering": (-1.0, 1.0),
            "throttle": (-1.0, 1.0),
            "max_throttle": (0.0, 1.0),
            "steer_mix": (0.0, 1.0),
            "steer_bias": (-0.5, 0.5),
        }
        with self.lock:
            algorithm = None
            if "algorithm" in data:
                algorithm = str(data.get("algorithm") or "").strip()
                if algorithm not in self.algorithms:
                    return False, "Unknown algorithm."

            values: dict[str, float] = {}
            for key, (low, high) in limits.items():
                if key not in data or data[key] is None:
                    continue
                try:
                    values[key] = _clamp(_parse_input_float(data[key]), low, high)
                except ValueError:
                    # An invalid motion-affecting value is a fail-safe event.
                    self.state.safety_stop = True
                    self._apply_safe_stop_locked()
                    self._manual_command_at = None
                    self._manual_command_timed_out = False
                    self.state.system_message = f"Invalid {key}; emergency stop engaged."
                    self._hard_stop_outputs()
                    return False, f"Invalid {key}; emergency stop engaged."

            if algorithm is not None:
                if algorithm != self.state.active_algorithm and algorithm == "manual":
                    self._apply_safe_stop_locked()
                    self._manual_command_at = None
                    self._manual_command_timed_out = False
                self.state.active_algorithm = algorithm
            if "steering" in values:
                self.state.manual_steering = values["steering"]
            if "throttle" in values:
                self.state.manual_throttle = values["throttle"]
            if "steering" in values or "throttle" in values:
                # No implicit rearm: an emergency stop remains engaged until cleared.
                if not self.state.safety_stop:
                    self._manual_command_at = time.monotonic()
                    self._manual_command_timed_out = False
            for key in ("max_throttle", "steer_mix", "steer_bias"):
                if key in values:
                    setattr(self.state, key, values[key])
            if data.get("current_page"):
                self.state.current_page = str(data["current_page"])
            self.state.system_message = "Controls and runtime parameters updated."
        return True, "OK"

    def set_manual_controls(self, steering=None, throttle=None):
        return self.apply_control_update({"steering": steering, "throttle": throttle})

    def select_algorithm(self, name: str) -> tuple[bool, str]:
        return self.apply_control_update({"algorithm": name})

    def set_runtime_parameters(self, max_throttle=None, steer_mix=None, steer_bias=None, current_page=None):
        return self.apply_control_update({
            "max_throttle": max_throttle,
            "steer_mix": steer_mix,
            "steer_bias": steer_bias,
            "current_page": current_page,
        })

    def toggle_recording(self) -> tuple[bool, bool, str]:
        with self.lock:
            try:
                self.recorder_service.toggle()
            except (OSError, ValueError, RuntimeError) as exc:
                # Recording storage is independent from motor ownership and
                # must not trip E-stop or interrupt the control-loop thread.
                self.state.recording = bool(self.recorder_service.recording)
                self.state.system_message = f"Recording unavailable: {exc}"
                return False, self.state.recording, self.state.system_message
            self.state.recording = bool(self.recorder_service.recording)
            self.state.system_message = "Recording started." if self.state.recording else "Recording stopped."
            return True, self.state.recording, self.state.system_message

    def safety_status(self) -> dict:
        """U28 additive status contract; does not change existing snapshot fields."""
        with self.lock:
            latched = bool(self.state.safety_stop)
            return {
                "schema_version": 1,
                "component": "PiServer",
                "state": "latched" if latched else ("ready" if self.running else "stopped"),
                "latched": latched,
                "motion_allowed": bool(self.running and not latched),
                "rearm_required": latched,
                "rearm_available": bool(latched and self.running),
                "reason": ("Autonomous camera fault; fresh raw frame and explicit rearm required." if getattr(self, "_camera_fault_latched", False) else str(self.state.system_message)) if latched else "",
            }

    def rearm_safety(self, *, confirm: Any = False) -> tuple[bool, str]:
        """Explicitly clear the emergency latch with zero commands and manual ownership.

        A mere clear flag cannot silently resume an autonomous algorithm or replay
        manual setpoints. Failures leave the latch engaged.
        """
        if confirm is not True:
            return False, "Explicit confirm=true is required to rearm."
        with self.lock:
            if not self.state.safety_stop:
                return True, "No active safety stop."
            if not self.running:
                return False, "Control loop is not running; safety stop remains latched."
            if getattr(self, "_camera_fault_latched", False):
                frame, _ = self._fresh_camera_sample()
                if frame is None:
                    return False, "Camera recovery not verified; safety stop remains latched."
            self.state.active_algorithm = "manual"
            self._apply_safe_stop_locked()
            self._manual_command_at = None
            self._manual_command_timed_out = False
            self._processing_enabled_cached = None
            try:
                self.motor_service.stop()
            except Exception as exc:
                self.state.system_message = f"Rearm refused: motor zero-stop failed: {exc}"
                self.state.safety_stop = True
                return False, self.state.system_message
            self._camera_fault_latched = False
            self._camera_wait_started = None
            self._camera_seen_fresh = False
            self.state.safety_stop = False
            self.state.system_message = "Safety rearmed at zero. New manual commands required."
        return True, "Safety rearmed at zero. New manual commands required."

    def set_safety_stop(self, enabled: bool):
        # Clearing a latch must go through the explicit checked rearm path.
        if not enabled:
            return False
        with self.lock:
            self.state.safety_stop = True
            # Clear both the motor setpoint and the lease on engage AND release.
            # Releasing e-stop must not replay a previous manual command.
            self._apply_safe_stop_locked()
            self._manual_command_at = None
            self._manual_command_timed_out = False
            if enabled:
                self.state.system_message = "Emergency stop engaged."
            else:
                self.state.system_message = "Emergency stop cleared."
        self._hard_stop_outputs()
        return True

    def get_runtime_config(self) -> dict:
        with self.lock:
            return {
                "active_algorithm": self.state.active_algorithm,
                "max_throttle": self.state.max_throttle,
                "steer_mix": self.state.steer_mix,
                "steer_bias": self.state.steer_bias,
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
                self.state.max_throttle = _clamp(parse_finite_float(data["max_throttle"], self.state.max_throttle), 0.0, 1.0)
            if "steer_mix" in data:
                self.state.steer_mix = _clamp(parse_finite_float(data["steer_mix"], self.state.steer_mix), 0.0, 1.0)
            if "steer_bias" in data:
                self.state.steer_bias = _clamp(parse_finite_float(data["steer_bias"], self.state.steer_bias), -0.5, 0.5)
            if "current_page" in data:
                self.state.current_page = str(data["current_page"])
            self._update_motor_state_locked()
            self.state.system_message = "Runtime config loaded." if not initial else "Runtime config applied."
        camera_cfg = data.get("camera")
        if isinstance(camera_cfg, dict):
            self.camera_service.apply_settings(camera_cfg, restart=not initial)
            self.invalidate_processing_state_cache()

    def reload_runtime_config(self) -> dict:
        data = self.config_store.load()
        recovery = getattr(self.config_store, "recovery_status", lambda: {})()
        if recovery.get("load_failed"):
            raise ValueError("Runtime configuration is damaged or unreadable; current settings retained.")
        self.apply_runtime_config(data)
        return self.get_runtime_config()
