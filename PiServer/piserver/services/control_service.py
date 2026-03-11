from __future__ import annotations

import threading
import time

from piserver.core.runtime_state import RuntimeState, default_calibration, default_mode_profiles


class ControlService:
    MODE_ALGORITHM_MAP = {
        "manual": "manual",
        "lane": "auto_steer",
        "full_auto": "autopilot",
    }
    LEGACY_MODE_MAP = {
        "manual": "manual",
        "training": "lane",
        "lane": "lane",
        "lane_detection": "lane",
        "auto": "full_auto",
        "autopilot": "full_auto",
        "full_auto": "full_auto",
    }
    PAGE_MAP = {
        "manual": "manual",
        "lane": "lane",
        "lane_detection": "lane",
        "training": "lane",
        "full_auto": "full_auto",
        "autopilot": "full_auto",
        "auto": "full_auto",
        "calibration": "calibration",
        "calibrate": "calibration",
        "camera": "camera",
        "camera_settings": "camera",
        "settings": "camera",
    }
    CAMERA_ALGORITHMS = {"auto_steer", "autopilot"}

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
        self._last_camera_needed = None

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
            self.camera_service.set_processing_enabled(False)
            self.motor_service.stop()
        except Exception:
            pass

    def _camera_needed_locked(self) -> bool:
        return bool(self.recorder_service.recording or self.state.active_algorithm in self.CAMERA_ALGORITHMS)

    def _refresh_camera_demand(self, *, force: bool = False) -> None:
        with self.lock:
            needed = self._camera_needed_locked()
        if force or needed != self._last_camera_needed:
            self.camera_service.set_processing_enabled(needed)
            self._last_camera_needed = needed

    def _loop(self):
        period = 1.0 / self.loop_hz
        while self.running:
            start = time.perf_counter()
            self._refresh_camera_demand()
            frame, frame_seq = self.camera_service.get_latest_frame_packet(copy=False)
            with self.lock:
                self.state.fps = self.camera_service.get_fps()
                self.state.camera_backend = getattr(self.camera_service, "backend", "unknown")
                self.state.camera_width = int(getattr(self.camera_service, "width", 0))
                self.state.camera_height = int(getattr(self.camera_service, "height", 0))
                self.state.camera_format = str(getattr(self.camera_service, "camera_format", "unknown"))
                self.state.active_model = self.model_service.get_active_name()

                calibration = self.ensure_calibration()
                effective_max_throttle = min(float(self.state.max_throttle), float(calibration["global_speed_limit"]))

                if self.state.safety_stop:
                    steer, throttle = 0.0, 0.0
                else:
                    algo = self.algorithms.get(self.state.active_algorithm, self.algorithms["manual"])
                    steer, throttle = algo.compute(self.state, frame, self.model_service, frame_seq=frame_seq)

                steer = max(-1.0, min(1.0, float(steer)))
                throttle = max(0.0, min(float(throttle), effective_max_throttle))

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
                recording_enabled = bool(self.recorder_service.recording)
                snapshot = self.state.snapshot() if recording_enabled else None

            if recording_enabled and snapshot is not None:
                self.recorder_service.maybe_record(frame, snapshot)

            elapsed = time.perf_counter() - start
            if elapsed < period:
                time.sleep(period - elapsed)

    def normalize_mode(self, mode: str | None) -> str:
        value = str(mode or "manual").strip().lower()
        return self.LEGACY_MODE_MAP.get(value, "manual")

    def normalize_page(self, page: str | None) -> str:
        value = str(page or "manual").strip().lower()
        return self.PAGE_MAP.get(value, "manual")

    def algorithm_for_mode(self, mode: str) -> str:
        mode = self.normalize_mode(mode)
        return self.MODE_ALGORITHM_MAP.get(mode, "manual")

    def ensure_mode_profiles(self):
        defaults = default_mode_profiles()
        profiles = self.state.mode_profiles if isinstance(self.state.mode_profiles, dict) else {}
        merged = {}
        for mode, values in defaults.items():
            current = profiles.get(mode, {}) if isinstance(profiles.get(mode), dict) else {}
            merged[mode] = {
                "max_throttle": max(0.0, min(1.0, float(current.get("max_throttle", values["max_throttle"])))),
                "steer_mix": max(0.0, min(1.0, float(current.get("steer_mix", values["steer_mix"])))),
            }
        self.state.mode_profiles = merged

    def ensure_calibration(self) -> dict:
        defaults = default_calibration()
        calibration = self.state.calibration if isinstance(self.state.calibration, dict) else {}
        merged = {
            "left_motor_scale": max(0.2, min(1.8, float(calibration.get("left_motor_scale", defaults["left_motor_scale"])))),
            "right_motor_scale": max(0.2, min(1.8, float(calibration.get("right_motor_scale", defaults["right_motor_scale"])))),
            "global_speed_limit": max(0.0, min(1.0, float(calibration.get("global_speed_limit", defaults["global_speed_limit"])))),
            "turn_gain": max(0.1, min(2.0, float(calibration.get("turn_gain", defaults["turn_gain"])))),
            "camera_width": max(160, min(1920, int(calibration.get("camera_width", defaults["camera_width"])))),
            "camera_height": max(120, min(1080, int(calibration.get("camera_height", defaults["camera_height"])))),
            "camera_fps": max(1, min(120, int(calibration.get("camera_fps", defaults["camera_fps"])))),
            "camera_format": str(calibration.get("camera_format", defaults["camera_format"]) or defaults["camera_format"]),
            "auto_exposure": bool(calibration.get("auto_exposure", defaults["auto_exposure"])),
            "exposure_time": max(100, min(200000, int(calibration.get("exposure_time", defaults["exposure_time"])))),
            "analogue_gain": max(1.0, min(16.0, float(calibration.get("analogue_gain", defaults["analogue_gain"])))),
            "exposure_compensation": max(-8.0, min(8.0, float(calibration.get("exposure_compensation", defaults["exposure_compensation"])))),
            "auto_white_balance": bool(calibration.get("auto_white_balance", defaults["auto_white_balance"])),
            "brightness": max(-1.0, min(1.0, float(calibration.get("brightness", defaults["brightness"])))),
            "contrast": max(0.0, min(4.0, float(calibration.get("contrast", defaults["contrast"])))),
            "saturation": max(0.0, min(4.0, float(calibration.get("saturation", defaults["saturation"])))),
            "sharpness": max(0.0, min(4.0, float(calibration.get("sharpness", defaults["sharpness"])))),
        }
        self.state.calibration = merged
        return merged

    def apply_calibration(self, *, reconfigure_camera: bool = True):
        calibration = self.ensure_calibration()
        self.motor_service.update_calibration(
            left_motor_scale=calibration["left_motor_scale"],
            right_motor_scale=calibration["right_motor_scale"],
            global_speed_limit=calibration["global_speed_limit"],
            turn_gain=calibration["turn_gain"],
        )
        if reconfigure_camera:
            self.camera_service.apply_settings(
                width=calibration["camera_width"],
                height=calibration["camera_height"],
                fps=calibration["camera_fps"],
                camera_format=calibration["camera_format"],
                auto_exposure=calibration["auto_exposure"],
                exposure_time=calibration["exposure_time"],
                analogue_gain=calibration["analogue_gain"],
                exposure_compensation=calibration["exposure_compensation"],
                auto_white_balance=calibration["auto_white_balance"],
                brightness=calibration["brightness"],
                contrast=calibration["contrast"],
                saturation=calibration["saturation"],
                sharpness=calibration["sharpness"],
            )

    def apply_mode_profile(self, mode: str):
        self.ensure_mode_profiles()
        mode = self.normalize_mode(mode)
        profile = self.state.mode_profiles.get(mode, default_mode_profiles()[mode])
        self.state.max_throttle = float(profile["max_throttle"])
        self.state.steer_mix = float(profile["steer_mix"])

    def update_mode_profile(self, mode: str, max_throttle=None, steer_mix=None):
        self.ensure_mode_profiles()
        mode = self.normalize_mode(mode)
        profile = self.state.mode_profiles.get(mode, default_mode_profiles()[mode]).copy()
        if max_throttle is not None:
            profile["max_throttle"] = max(0.0, min(1.0, float(max_throttle)))
        if steer_mix is not None:
            profile["steer_mix"] = max(0.0, min(1.0, float(steer_mix)))
        self.state.mode_profiles[mode] = profile
        if self.state.drive_mode == mode:
            self.state.max_throttle = profile["max_throttle"]
            self.state.steer_mix = profile["steer_mix"]

    def select_page(self, page: str) -> dict:
        with self.lock:
            normalized = self.normalize_page(page)
            self.state.current_page = normalized
            if normalized in {"calibration", "camera"}:
                title = "Calibration" if normalized == "calibration" else "Camera settings"
                self.state.system_message = f"{title} tab selected."
            else:
                self.state.drive_mode = normalized
                self.state.active_algorithm = self.algorithm_for_mode(normalized)
                self.apply_mode_profile(normalized)
                self.state.system_message = f"Mode switched to {normalized}."
        self._refresh_camera_demand()
        return self.state.snapshot()

    def set_mode(self, mode: str) -> dict:
        return self.select_page(mode)

    def snapshot(self) -> dict:
        with self.lock:
            return self.state.snapshot()

    def set_manual_controls(self, steering=None, throttle=None):
        with self.lock:
            if steering is not None:
                self.state.manual_steering = max(-1.0, min(1.0, float(steering)))
            if throttle is not None:
                self.state.manual_throttle = max(0.0, min(1.0, float(throttle)))

    def select_algorithm(self, name: str) -> tuple[bool, str]:
        name = str(name or "").strip()
        if name not in self.algorithms:
            return False, "Unknown algorithm."
        with self.lock:
            self.state.active_algorithm = name
            reverse = {v: k for k, v in self.MODE_ALGORITHM_MAP.items()}
            self.state.drive_mode = reverse.get(name, self.state.drive_mode)
            self.state.system_message = f"Algorithm switched to {name}."
        self._refresh_camera_demand()
        return True, name

    def set_runtime_parameters(self, max_throttle=None, steer_mix=None, current_page=None):
        with self.lock:
            if current_page:
                normalized_page = self.normalize_page(current_page)
                self.state.current_page = normalized_page
                if normalized_page not in {"calibration", "camera"}:
                    self.state.drive_mode = normalized_page
                    expected_algo = self.algorithm_for_mode(self.state.drive_mode)
                    if self.state.active_algorithm == expected_algo or self.state.active_algorithm not in self.algorithms:
                        self.state.active_algorithm = expected_algo
            if max_throttle is not None or steer_mix is not None:
                self.update_mode_profile(self.state.drive_mode, max_throttle=max_throttle, steer_mix=steer_mix)
        self._refresh_camera_demand()

    def update_calibration(
        self,
        *,
        left_motor_scale=None,
        right_motor_scale=None,
        global_speed_limit=None,
        turn_gain=None,
        camera_width=None,
        camera_height=None,
        camera_fps=None,
        camera_format=None,
        auto_exposure=None,
        exposure_time=None,
        analogue_gain=None,
        exposure_compensation=None,
        auto_white_balance=None,
        brightness=None,
        contrast=None,
        saturation=None,
        sharpness=None,
    ) -> dict:
        with self.lock:
            calibration = self.ensure_calibration().copy()
            updates = {
                "left_motor_scale": left_motor_scale,
                "right_motor_scale": right_motor_scale,
                "global_speed_limit": global_speed_limit,
                "turn_gain": turn_gain,
                "camera_width": camera_width,
                "camera_height": camera_height,
                "camera_fps": camera_fps,
                "camera_format": camera_format,
                "auto_exposure": auto_exposure,
                "exposure_time": exposure_time,
                "analogue_gain": analogue_gain,
                "exposure_compensation": exposure_compensation,
                "auto_white_balance": auto_white_balance,
                "brightness": brightness,
                "contrast": contrast,
                "saturation": saturation,
                "sharpness": sharpness,
            }
            for key, value in updates.items():
                if value is not None:
                    calibration[key] = value
            self.state.calibration = calibration
            self.apply_calibration(reconfigure_camera=True)
            self.state.system_message = "Calibration updated."
        self._refresh_camera_demand(force=True)
        return self.state.snapshot()

    def toggle_recording(self) -> bool:
        with self.lock:
            self.recorder_service.toggle()
            self.state.recording = bool(self.recorder_service.recording)
            self.state.system_message = "Recording started." if self.state.recording else "Recording stopped."
        self._refresh_camera_demand()
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
                "drive_mode": self.state.drive_mode,
                "current_page": self.state.current_page,
                "max_throttle": self.state.max_throttle,
                "steer_mix": self.state.steer_mix,
                "mode_profiles": self.state.mode_profiles,
                "calibration": self.state.calibration,
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
            incoming_profiles = data.get("mode_profiles")
            if isinstance(incoming_profiles, dict):
                self.state.mode_profiles = incoming_profiles
            self.ensure_mode_profiles()

            incoming_calibration = data.get("calibration")
            if isinstance(incoming_calibration, dict):
                self.state.calibration = incoming_calibration
            self.ensure_calibration()
            self.apply_calibration(reconfigure_camera=not initial)

            drive_mode = self.normalize_mode(data.get("drive_mode") or data.get("current_page"))
            page = self.normalize_page(data.get("current_page") or drive_mode)
            if page in {"calibration", "camera"}:
                self.state.drive_mode = drive_mode
                self.state.current_page = page
            else:
                self.state.drive_mode = page
                self.state.current_page = page
            self.apply_mode_profile(self.state.drive_mode)

            algo = data.get("active_algorithm")
            if algo in self.algorithms:
                self.state.active_algorithm = algo
            else:
                self.state.active_algorithm = self.algorithm_for_mode(self.state.drive_mode)

            if "max_throttle" in data or "steer_mix" in data:
                self.update_mode_profile(
                    self.state.drive_mode,
                    max_throttle=data.get("max_throttle", self.state.max_throttle),
                    steer_mix=data.get("steer_mix", self.state.steer_mix),
                )

            self.state.system_message = "Runtime config loaded." if not initial else "Runtime config applied."
        self._refresh_camera_demand(force=True)

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
