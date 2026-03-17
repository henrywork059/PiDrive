from __future__ import annotations

import math
import threading
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from .config import MissionConfig
from .fake_robot import FakeRobot
from .mission_controller import MissionController
from .mission_state import MissionState
from .models import BoundingBox, Detection, FramePerception

FRAME_W = 640
FRAME_H = 360


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
    return Detection(
        label=label,
        confidence=confidence,
        box=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
    )


def scripted_perception(controller: MissionController) -> FramePerception:
    state = controller.state
    t = controller.state_elapsed()
    detections: List[Detection] = []

    if state == MissionState.SCAN_FOR_TARGET and t > 1.5:
        detections = [make_detection("he3", cx_ratio=0.78, bottom_ratio=0.58)]
    elif state == MissionState.ALIGN_TO_TARGET:
        cx_ratio = max(0.5, 0.78 - t * 0.18)
        detections = [make_detection("he3", cx_ratio=cx_ratio, bottom_ratio=0.60)]
    elif state == MissionState.APPROACH_TARGET:
        bottom_ratio = min(0.90, 0.60 + t * 0.15)
        cx_ratio = 0.5 + math.sin(t * 4.0) * 0.015
        detections = [make_detection("he3", cx_ratio=cx_ratio, bottom_ratio=bottom_ratio, box_w=92, box_h=92)]
    elif state == MissionState.SCAN_FOR_DROP_ZONE and t > 1.3:
        detections = [make_detection("he3_zone", cx_ratio=0.25, bottom_ratio=0.45, box_w=110, box_h=70)]
    elif state == MissionState.ALIGN_TO_DROP_ZONE:
        cx_ratio = min(0.5, 0.25 + t * 0.20)
        detections = [make_detection("he3_zone", cx_ratio=cx_ratio, bottom_ratio=0.48, box_w=118, box_h=74)]
    elif state == MissionState.APPROACH_DROP_ZONE:
        bottom_ratio = min(0.82, 0.48 + t * 0.14)
        cx_ratio = 0.5 + math.sin(t * 3.0) * 0.012
        detections = [make_detection("he3_zone", cx_ratio=cx_ratio, bottom_ratio=bottom_ratio, box_w=130, box_h=82)]

    return FramePerception(frame_width=FRAME_W, frame_height=FRAME_H, detections=detections, timestamp=time.monotonic())


class DemoMissionRuntime:
    def __init__(self, max_cycles: int = 2):
        self.max_cycles = max_cycles
        self.tick_s = 0.2
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.reset(max_cycles=max_cycles)

    def reset(self, max_cycles: Optional[int] = None) -> None:
        if max_cycles is not None:
            self.max_cycles = max(1, int(max_cycles))

        with self._lock:
            self.robot = FakeRobot()
            self.config = MissionConfig(max_cycles=self.max_cycles)
            self.controller = MissionController(robot=self.robot, config=self.config)
            self.last_perception = FramePerception(frame_width=FRAME_W, frame_height=FRAME_H, detections=[])
            self.last_snapshot = self.controller.snapshot()

    def start(self) -> None:
        with self._lock:
            if self.controller.state == MissionState.IDLE:
                self.controller.start()

    def step(self) -> Dict[str, Any]:
        with self._lock:
            if self.controller.state not in (MissionState.COMPLETE, MissionState.FAILED):
                self.last_perception = scripted_perception(self.controller)
                self.last_snapshot = self.controller.update(self.last_perception)
            return self.status_unlocked()

    def run_blocking(self, tick_s: float = 0.2) -> None:
        self.start()
        while True:
            status = self.step()
            if status["state"] in (MissionState.COMPLETE.value, MissionState.FAILED.value):
                return
            time.sleep(tick_s)

    def start_background(self, tick_s: float = 0.2) -> None:
        self.tick_s = max(0.02, float(tick_s))
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self.start()
            self._thread = threading.Thread(target=self._background_loop, name="customdrive-demo", daemon=True)
            self._thread.start()

    def stop_background(self) -> None:
        self._stop_event.set()

    def _background_loop(self) -> None:
        while not self._stop_event.is_set():
            status = self.step()
            if status["state"] in (MissionState.COMPLETE.value, MissionState.FAILED.value):
                self._stop_event.set()
                break
            time.sleep(self.tick_s)

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return self.status_unlocked()

    def status_unlocked(self) -> Dict[str, Any]:
        snapshot = self.last_snapshot
        detections = []
        for det in self.last_perception.detections:
            detections.append(
                {
                    "label": det.label,
                    "confidence": det.confidence,
                    "box": asdict(det.box),
                }
            )

        recent_logs = [asdict(item) for item in self.robot.history[-25:]]
        return {
            "state": snapshot.state,
            "detail": snapshot.detail,
            "retries": snapshot.retries,
            "completed_cycles": snapshot.completed_cycles,
            "active_route_leg": snapshot.active_route_leg,
            "last_command": asdict(snapshot.last_command),
            "frame": {"width": FRAME_W, "height": FRAME_H},
            "detections": detections,
            "logs": recent_logs,
            "running": bool(self._thread and self._thread.is_alive() and not self._stop_event.is_set()),
            "max_cycles": self.max_cycles,
        }
