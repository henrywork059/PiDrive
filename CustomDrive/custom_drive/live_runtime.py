from __future__ import annotations

import copy
import sys
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

from .config import MissionConfig
from .mission_controller import MissionController
from .mission_state import MissionState
from .models import FramePerception
from .perception import build_frame_perception, detections_as_dict, merge_perception_settings, perception_backend_ready
from .picar_bridge import PiCarRobotBridge
from .runtime_settings import DEFAULT_SETTINGS, load_settings, save_settings

REPO_ROOT = Path(__file__).resolve().parents[2]
PISERVER_ROOT = REPO_ROOT / "PiServer"
for _path in (REPO_ROOT, PISERVER_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from piserver.services.camera_service import CameraService  # noqa: E402
from piserver.services.motor_service import MotorService  # noqa: E402


class LiveMissionRuntime:
    mode = "live"

    def __init__(self, max_cycles: int = 2):
        self.max_cycles = max(1, int(max_cycles))
        self.tick_s = 0.1
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self.settings = load_settings()
        self.perception_settings = merge_perception_settings(self.settings.get("perception"))
        self.camera_service = CameraService()
        self.motor_service = MotorService()
        self._configure_services_from_settings(restart_camera=False)
        self.camera_service.set_preview_enabled(True)
        self.camera_service.set_processing_enabled(True)
        self.camera_service.start()

        ready, reason = perception_backend_ready()
        self.perception_ready = ready
        self.perception_message = reason

        runtime_cfg = self.settings.get("runtime") or {}
        self.bridge = PiCarRobotBridge(
            motor=self.motor_service,
            arm=None,
            mode_name="custom_drive",
            steer_mix=float(runtime_cfg.get("steer_mix", 0.75)),
            allow_virtual_grab_without_arm=bool(runtime_cfg.get("allow_virtual_grab_without_arm", False)),
        )
        self.reset(max_cycles=self.max_cycles)

    def _configure_services_from_settings(self, restart_camera: bool) -> None:
        camera_cfg = self.settings.get("camera") or {}
        motor_cfg = self.settings.get("motor") or {}
        self.motor_service.apply_settings(motor_cfg)
        self.camera_service.apply_settings(camera_cfg, restart=restart_camera)

    def close(self) -> None:
        self.stop_background(join=True)
        try:
            self.bridge.stop("runtime closed")
        except Exception:
            pass
        try:
            self.camera_service.close()
        except Exception:
            pass
        try:
            self.motor_service.close()
        except Exception:
            pass

    def get_settings(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self.settings)

    def save_settings(self, data: dict[str, Any] | None) -> dict[str, Any]:
        with self._lock:
            merged = copy.deepcopy(self.settings)
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict) and isinstance(merged.get(key), dict):
                        merged[key].update(value)
                    else:
                        merged[key] = value
            self.settings = save_settings(merged)
            self.perception_settings = merge_perception_settings(self.settings.get("perception"))
            self._configure_services_from_settings(restart_camera=True)
            runtime_cfg = self.settings.get("runtime") or {}
            self.bridge.steer_mix = float(runtime_cfg.get("steer_mix", self.bridge.steer_mix))
            self.bridge.allow_virtual_grab_without_arm = bool(
                runtime_cfg.get("allow_virtual_grab_without_arm", self.bridge.allow_virtual_grab_without_arm)
            )
            ready, reason = perception_backend_ready()
            self.perception_ready = ready
            self.perception_message = reason
            return copy.deepcopy(self.settings)

    def reset(self, max_cycles: Optional[int] = None) -> None:
        if max_cycles is not None:
            self.max_cycles = max(1, int(max_cycles))
        with self._lock:
            self.bridge.reset_mission_state()
            self.config = MissionConfig(max_cycles=self.max_cycles)
            self.controller = MissionController(robot=self.bridge, config=self.config)
            frame = self.camera_service.get_latest_frame(copy=False)
            frame_h = int(getattr(frame, "shape", (240, 426, 3))[0] or 240)
            frame_w = int(getattr(frame, "shape", (240, 426, 3))[1] or 426)
            self.last_perception = FramePerception(frame_width=frame_w, frame_height=frame_h, detections=[])
            self.last_snapshot = self.controller.snapshot()
            self.last_camera_error = str(getattr(self.camera_service, "last_error", "") or "")
            self.last_frame_timestamp = 0.0

    def start(self) -> None:
        with self._lock:
            if self.controller.state == MissionState.IDLE:
                self.controller.start()

    def step(self) -> Dict[str, Any]:
        with self._lock:
            if self.controller.state not in (MissionState.COMPLETE, MissionState.FAILED):
                frame = self.camera_service.get_latest_frame(copy=True)
                if frame is not None:
                    self.last_perception = build_frame_perception(frame, self.perception_settings)
                    self.last_frame_timestamp = time.time()
                else:
                    self.last_perception = FramePerception(
                        frame_width=int(getattr(self.camera_service, "width", 426)),
                        frame_height=int(getattr(self.camera_service, "height", 240)),
                        detections=[],
                        timestamp=time.monotonic(),
                    )
                self.last_camera_error = str(getattr(self.camera_service, "last_error", "") or "")
                self.last_snapshot = self.controller.update(self.last_perception)
            return self.status_unlocked()

    def run_blocking(self, tick_s: Optional[float] = None) -> None:
        runtime_cfg = self.settings.get("runtime") or {}
        tick = max(0.02, float(tick_s if tick_s is not None else runtime_cfg.get("tick_s_live", 0.1)))
        self.start()
        try:
            while True:
                status = self.step()
                if status["state"] in (MissionState.COMPLETE.value, MissionState.FAILED.value):
                    return
                time.sleep(tick)
        finally:
            self.bridge.stop("run_blocking finished")

    def start_background(self, tick_s: float = 0.1) -> None:
        self.tick_s = max(0.02, float(tick_s))
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self.start()
            self._thread = threading.Thread(target=self._background_loop, name="customdrive-live", daemon=True)
            self._thread.start()

    def stop_background(self, join: bool = False) -> None:
        self._stop_event.set()
        thread = self._thread
        if join and thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)

    def _background_loop(self) -> None:
        while not self._stop_event.is_set():
            status = self.step()
            if status["state"] in (MissionState.COMPLETE.value, MissionState.FAILED.value):
                self._stop_event.set()
                break
            time.sleep(self.tick_s)
        self.bridge.stop("background loop stopped")

    def get_jpeg_frame(self):
        return self.camera_service.get_jpeg_frame()

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return self.status_unlocked()

    def status_unlocked(self) -> Dict[str, Any]:
        snapshot = self.last_snapshot
        recent_logs = [asdict(item) for item in self.bridge.history[-40:]]
        runtime_cfg = self.settings.get("runtime") or {}
        return {
            "mode": self.mode,
            "state": snapshot.state,
            "detail": snapshot.detail,
            "retries": snapshot.retries,
            "completed_cycles": snapshot.completed_cycles,
            "active_route_leg": snapshot.active_route_leg,
            "last_command": asdict(snapshot.last_command),
            "frame": {
                "width": self.last_perception.frame_width or int(getattr(self.camera_service, "width", 426)),
                "height": self.last_perception.frame_height or int(getattr(self.camera_service, "height", 240)),
            },
            "detections": detections_as_dict(self.last_perception.detections),
            "logs": recent_logs,
            "running": bool(self._thread and self._thread.is_alive() and not self._stop_event.is_set()),
            "max_cycles": self.max_cycles,
            "camera": {
                "backend": str(getattr(self.camera_service, "backend", "unknown")),
                "preview_live": bool(getattr(self.camera_service, "preview_live", False)),
                "fps": float(self.camera_service.get_fps()),
                "error": self.last_camera_error,
                "last_frame_timestamp": self.last_frame_timestamp,
            },
            "steer_mix": float(runtime_cfg.get("steer_mix", self.bridge.steer_mix)),
            "perception_ready": bool(self.perception_ready),
            "perception_message": self.perception_message,
            "arm_bound": bool(self.bridge.arm is not None),
            "virtual_grab": bool(self.bridge.allow_virtual_grab_without_arm),
        }
