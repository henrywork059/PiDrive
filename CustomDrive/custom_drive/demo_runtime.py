from __future__ import annotations

import math
import os
import sys
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import MissionConfig
from .fake_robot import FakeRobot
from .interfaces import RobotInterface
from .mission_controller import MissionController
from .mission_state import MissionState
from .models import BoundingBox, Detection, FramePerception
from .runtime_settings import load_settings, save_settings

ROOT = Path(__file__).resolve().parents[2]
PISERVER_DIR = ROOT / "PiServer"
if str(PISERVER_DIR) not in sys.path:
    sys.path.insert(0, str(PISERVER_DIR))

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore

try:
    from piserver.services.camera_service import CameraService
    from piserver.services.motor_service import MotorService
except Exception:  # pragma: no cover
    CameraService = None  # type: ignore
    MotorService = None  # type: ignore

FRAME_W = 640
FRAME_H = 360


@dataclass(slots=True)
class RuntimeLogEntry:
    timestamp: float
    action: str
    detail: str


def make_detection(
    label: str,
    cx_ratio: float,
    bottom_ratio: float,
    box_w: int = 80,
    box_h: int = 80,
    confidence: float = 0.92,
) -> Detection:
    cx = cx_ratio * FRAME_W
    bottom = bottom_ratio * FRAME_H
    x1 = cx - box_w / 2
    x2 = cx + box_w / 2
    y2 = bottom
    y1 = y2 - box_h
    return Detection(label=label, confidence=confidence, box=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2))


def scripted_perception(controller: MissionController) -> FramePerception:
    state = controller.state
    t = controller.state_elapsed()
    detections: List[Detection] = []

    if state == MissionState.SCAN_FOR_TARGET and t > 1.5:
        detections = [make_detection("he3", cx_ratio=0.78, bottom_ratio=0.58)]
    elif state == MissionState.ALIGN_TO_TARGET:
        detections = [make_detection("he3", cx_ratio=max(0.5, 0.78 - t * 0.18), bottom_ratio=0.60)]
    elif state == MissionState.APPROACH_TARGET:
        detections = [
            make_detection(
                "he3",
                cx_ratio=0.5 + math.sin(t * 4.0) * 0.015,
                bottom_ratio=min(0.90, 0.60 + t * 0.15),
                box_w=92,
                box_h=92,
            )
        ]
    elif state == MissionState.SCAN_FOR_DROP_ZONE and t > 1.3:
        detections = [make_detection("he3_zone", cx_ratio=0.25, bottom_ratio=0.45, box_w=110, box_h=70)]
    elif state == MissionState.ALIGN_TO_DROP_ZONE:
        detections = [make_detection("he3_zone", cx_ratio=min(0.5, 0.25 + t * 0.20), bottom_ratio=0.48, box_w=118, box_h=74)]
    elif state == MissionState.APPROACH_DROP_ZONE:
        detections = [
            make_detection(
                "he3_zone",
                cx_ratio=0.5 + math.sin(t * 3.0) * 0.012,
                bottom_ratio=min(0.82, 0.48 + t * 0.14),
                box_w=130,
                box_h=82,
            )
        ]

    return FramePerception(frame_width=FRAME_W, frame_height=FRAME_H, detections=detections, timestamp=time.monotonic())


class PiServerRobotBridge(RobotInterface):
    def __init__(self, motor_service: Any, steer_mix: float = 0.75):
        self.motor_service = motor_service
        self.steer_mix = float(steer_mix)
        self.started_at = time.monotonic()
        self.history: List[RuntimeLogEntry] = []
        self.has_payload = False

    def now(self) -> float:
        return time.monotonic() - self.started_at

    def _log(self, action: str, detail: str) -> None:
        self.history.append(RuntimeLogEntry(self.now(), action, detail))

    def set_drive(self, steering: float, throttle: float, note: str = "") -> None:
        self.motor_service.update(steering=steering, throttle=throttle, steer_mix=self.steer_mix)
        self._log("drive", f"steering={steering:+.2f}, throttle={throttle:+.2f}, note={note}")

    def stop(self, note: str = "") -> None:
        self.motor_service.stop()
        self._log("stop", note)

    def pickup_sequence(self) -> bool:
        self.has_payload = True
        self._log("pickup", "pickup sequence acknowledged")
        return True

    def release_sequence(self) -> bool:
        if not self.has_payload:
            self._log("release", "release blocked: no payload")
            return False
        self.has_payload = False
        self._log("release", "release sequence acknowledged")
        return True


class RealPerceptionAdapter:
    def __init__(self, camera_service: Any, target_label: str, drop_label: str):
        self.camera_service = camera_service
        self.target_label = target_label
        self.drop_label = drop_label
        self._jpeg: Optional[bytes] = None

    def _bgr_from_camera(self):
        frame = self.camera_service.get_latest_frame()
        if frame is not None:
            return frame
        jpeg = self.camera_service.get_jpeg_frame()
        if jpeg is None or cv2 is None or np is None:
            return None
        return cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)

    def _detect_color(self, hsv, lower: Tuple[int, int, int], upper: Tuple[int, int, int], label: str, min_area: int = 180) -> List[Detection]:
        if cv2 is None or np is None:
            return []
        mask = cv2.inRange(hsv, np.array(lower, dtype=np.uint8), np.array(upper, dtype=np.uint8))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        out: List[Detection] = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if (w * h) < min_area:
                continue
            conf = min(0.99, 0.45 + min(0.5, (w * h) / (hsv.shape[0] * hsv.shape[1])))
            out.append(Detection(label=label, confidence=float(conf), box=BoundingBox(x1=x, y1=y, x2=x + w, y2=y + h)))
        return out

    def get_perception(self) -> Tuple[FramePerception, Optional[bytes]]:
        frame = self._bgr_from_camera()
        if frame is None:
            return FramePerception(frame_width=FRAME_W, frame_height=FRAME_H, detections=[], timestamp=time.monotonic()), None

        h, w = frame.shape[:2]
        detections: List[Detection] = []
        if cv2 is not None and np is not None:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            detections.extend(self._detect_color(hsv, (35, 80, 60), (85, 255, 255), self.target_label))
            detections.extend(self._detect_color(hsv, (95, 80, 50), (130, 255, 255), self.drop_label))
            overlay = frame.copy()
            for det in detections:
                x1, y1, x2, y2 = int(det.box.x1), int(det.box.y1), int(det.box.x2), int(det.box.y2)
                color = (0, 200, 0) if det.label == self.target_label else (220, 100, 20)
                cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
                cv2.putText(overlay, f"{det.label} {det.confidence:.2f}", (x1, max(16, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
            ok, enc = cv2.imencode(".jpg", overlay, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            self._jpeg = enc.tobytes() if ok else None

        return FramePerception(frame_width=w, frame_height=h, detections=detections, timestamp=time.monotonic()), self._jpeg


class DemoMissionRuntime:
    def __init__(self, max_cycles: int = 2, mode: str = "sim"):
        self.settings = load_settings()
        self.max_cycles = max_cycles
        self.mode = mode if mode in {"sim", "live"} else "sim"
        rt = self.settings.get("runtime", {})
        self.tick_s = float(rt.get("tick_s_live", 0.1) if self.mode == "live" else rt.get("tick_s_sim", 0.2))
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_frame_jpeg: Optional[bytes] = None
        self._logs: List[RuntimeLogEntry] = []
        self.camera_service = None
        self.motor_service = None
        self.real_perception = None
        self.reset(max_cycles=max_cycles)

    def _log(self, action: str, detail: str) -> None:
        now = self.controller.robot.now() if hasattr(self, "controller") else 0.0
        self._logs.append(RuntimeLogEntry(now, action, detail))

    def get_settings(self) -> dict[str, Any]:
        with self._lock:
            return load_settings()

    def save_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            saved = save_settings(settings)
            self.settings = saved
            self._log("settings", "saved runtime settings")
            return saved

    def apply_saved_settings(self) -> None:
        if self.camera_service is not None:
            cam_cfg = self.settings.get("camera", {})
            self.camera_service.apply_settings(cam_cfg, restart=True)
        if self.motor_service is not None:
            mot_cfg = self.settings.get("motor", {})
            self.motor_service.apply_settings(mot_cfg)

    def reset(self, max_cycles: Optional[int] = None) -> None:
        if max_cycles is not None:
            self.max_cycles = max(1, int(max_cycles))

        with self._lock:
            self.settings = load_settings()
            self._stop_event.set()
            self._thread = None
            self._logs.clear()

            if self.mode == "live" and CameraService is not None and MotorService is not None:
                cam_cfg = self.settings.get("camera", {})
                if self.camera_service is None:
                    self.camera_service = CameraService(
                        width=int(cam_cfg.get("width", 426)),
                        height=int(cam_cfg.get("height", 240)),
                        fps=int(cam_cfg.get("fps", 30)),
                    )
                    self.camera_service.start()
                if self.motor_service is None:
                    self.motor_service = MotorService()
                self.apply_saved_settings()

                steer_mix = float(self.settings.get("runtime", {}).get("steer_mix", 0.75))
                robot = PiServerRobotBridge(self.motor_service, steer_mix=steer_mix)
                self.config = MissionConfig(max_cycles=self.max_cycles)
                self.controller = MissionController(robot=robot, config=self.config)
                self.real_perception = RealPerceptionAdapter(self.camera_service, self.config.target_label, self.config.drop_zone_label)
                self._log("runtime", "initialized in live mode")
            else:
                self.mode = "sim"
                self.robot = FakeRobot()
                self.config = MissionConfig(max_cycles=self.max_cycles)
                self.controller = MissionController(robot=self.robot, config=self.config)
                self.real_perception = None
                self._log("runtime", "initialized in simulation mode")

            self.last_perception = FramePerception(frame_width=FRAME_W, frame_height=FRAME_H, detections=[])
            self.last_snapshot = self.controller.snapshot()

    def shutdown(self) -> None:
        self.stop_background()
        with self._lock:
            if self.motor_service is not None:
                try:
                    self.motor_service.stop()
                except Exception:
                    pass
            if self.camera_service is not None:
                try:
                    self.camera_service.stop()
                except Exception:
                    pass

    def start(self) -> None:
        with self._lock:
            if self.controller.state == MissionState.IDLE:
                self.controller.start()
                self._log("mission", "started")

    def _next_perception(self) -> FramePerception:
        if self.real_perception is not None:
            self.last_perception, self._last_frame_jpeg = self.real_perception.get_perception()
            return self.last_perception
        self._last_frame_jpeg = None
        return scripted_perception(self.controller)

    def step(self) -> Dict[str, Any]:
        with self._lock:
            if self.controller.state not in (MissionState.COMPLETE, MissionState.FAILED):
                self.last_perception = self._next_perception()
                self.last_snapshot = self.controller.update(self.last_perception)
            return self.status_unlocked()

    def start_background(self, tick_s: float = 0.2) -> None:
        self.tick_s = max(0.02, float(tick_s))
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self.start()
            self._thread = threading.Thread(target=self._background_loop, name="customdrive-runtime", daemon=True)
            self._thread.start()

    def stop_background(self) -> None:
        self._stop_event.set()
        if self.motor_service is not None:
            try:
                self.motor_service.stop()
            except Exception:
                pass

    def _background_loop(self) -> None:
        while not self._stop_event.is_set():
            status = self.step()
            if status["state"] in (MissionState.COMPLETE.value, MissionState.FAILED.value):
                self._stop_event.set()
                break
            time.sleep(self.tick_s)

    def latest_frame_jpeg(self) -> Optional[bytes]:
        with self._lock:
            return self._last_frame_jpeg

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return self.status_unlocked()

    def status_unlocked(self) -> Dict[str, Any]:
        snapshot = self.last_snapshot
        detections = [{"label": d.label, "confidence": d.confidence, "box": asdict(d.box)} for d in self.last_perception.detections]
        robot_logs: List[Dict[str, Any]] = []
        if hasattr(self.controller.robot, "history"):
            robot_logs = [asdict(item) for item in getattr(self.controller.robot, "history")[-20:]]
        recent_logs = [asdict(item) for item in self._logs[-20:]] + robot_logs
        return {
            "mode": self.mode,
            "state": snapshot.state,
            "detail": snapshot.detail,
            "retries": snapshot.retries,
            "completed_cycles": snapshot.completed_cycles,
            "active_route_leg": snapshot.active_route_leg,
            "last_command": asdict(snapshot.last_command),
            "frame": {"width": self.last_perception.frame_width, "height": self.last_perception.frame_height},
            "detections": detections,
            "logs": recent_logs[-30:],
            "running": bool(self._thread and self._thread.is_alive() and not self._stop_event.is_set()),
            "max_cycles": self.max_cycles,
            "settings": self.settings,
        }


def runtime_mode_from_env(default: str = "sim") -> str:
    mode = os.getenv("CUSTOMDRIVE_MODE", default).strip().lower()
    return mode if mode in {"sim", "live"} else default
