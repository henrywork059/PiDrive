from __future__ import annotations

import copy
import math
import threading
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from .config import MissionConfig
from .debug_tools import append_event, clamp_int
from .fake_robot import FakeRobot
from .mission_controller import MissionController
from .mission_state import MissionState
from .models import BoundingBox, Detection, FramePerception
from .runtime_settings import load_settings, save_settings

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
        detections = [make_detection('he3', cx_ratio=0.78, bottom_ratio=0.58)]
    elif state == MissionState.ALIGN_TO_TARGET:
        cx_ratio = max(0.5, 0.78 - t * 0.18)
        detections = [make_detection('he3', cx_ratio=cx_ratio, bottom_ratio=0.60)]
    elif state == MissionState.APPROACH_TARGET:
        bottom_ratio = min(0.90, 0.60 + t * 0.15)
        cx_ratio = 0.5 + math.sin(t * 4.0) * 0.015
        detections = [make_detection('he3', cx_ratio=cx_ratio, bottom_ratio=bottom_ratio, box_w=92, box_h=92)]
    elif state == MissionState.SCAN_FOR_DROP_ZONE and t > 1.3:
        detections = [make_detection('he3_zone', cx_ratio=0.25, bottom_ratio=0.45, box_w=110, box_h=70)]
    elif state == MissionState.ALIGN_TO_DROP_ZONE:
        cx_ratio = min(0.5, 0.25 + t * 0.20)
        detections = [make_detection('he3_zone', cx_ratio=cx_ratio, bottom_ratio=0.48, box_w=118, box_h=74)]
    elif state == MissionState.APPROACH_DROP_ZONE:
        bottom_ratio = min(0.82, 0.48 + t * 0.14)
        cx_ratio = 0.5 + math.sin(t * 3.0) * 0.012
        detections = [make_detection('he3_zone', cx_ratio=cx_ratio, bottom_ratio=bottom_ratio, box_w=130, box_h=82)]

    return FramePerception(frame_width=FRAME_W, frame_height=FRAME_H, detections=detections, timestamp=time.monotonic())


class DemoMissionRuntime:
    mode = 'sim'

    def __init__(self, max_cycles: int = 2):
        self.max_cycles = max(1, int(max_cycles))
        self.settings = load_settings()
        self.tick_s = float((self.settings.get('runtime') or {}).get('tick_s_sim', 0.2))
        runtime_cfg = self.settings.get('runtime') or {}
        self.event_history_limit = clamp_int(runtime_cfg.get('event_history_limit', 200), 200, 20, 1000)
        self._runtime_events: list[dict[str, Any]] = []
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.last_error = ''
        self._record_event('Simulation runtime created.', event_type='runtime', max_cycles=self.max_cycles)
        self.reset(max_cycles=max_cycles)

    def _record_event(self, message: str, *, level: str = 'info', event_type: str = 'runtime', **fields: Any) -> None:
        append_event(self._runtime_events, message, level=level, event_type=event_type, limit=self.event_history_limit, **fields)

    def reset(self, max_cycles: Optional[int] = None) -> None:
        if max_cycles is not None:
            self.max_cycles = max(1, int(max_cycles))

        with self._lock:
            self.stop_background(join=True)
            self.robot = FakeRobot()
            self.config = MissionConfig(max_cycles=self.max_cycles)
            self.controller = MissionController(robot=self.robot, config=self.config)
            self.controller.debug_limit = self.event_history_limit
            self.last_perception = FramePerception(frame_width=FRAME_W, frame_height=FRAME_H, detections=[])
            self.last_snapshot = self.controller.snapshot()
            self.last_error = ''
            self._record_event('Runtime reset.', event_type='runtime', max_cycles=self.max_cycles)

    def start(self) -> None:
        with self._lock:
            if self.controller.state in (MissionState.COMPLETE, MissionState.FAILED):
                self.reset(max_cycles=self.max_cycles)
            if self.controller.state == MissionState.IDLE:
                self.controller.start()
                self._record_event('Mission start requested.', event_type='runtime')

    def step(self) -> Dict[str, Any]:
        with self._lock:
            if self.controller.state not in (MissionState.COMPLETE, MissionState.FAILED):
                self.last_perception = scripted_perception(self.controller)
                self.last_snapshot = self.controller.update(self.last_perception)
            return self.status_unlocked()

    def run_blocking(self, tick_s: float | None = None) -> None:
        tick = max(0.02, float(tick_s if tick_s is not None else self.tick_s))
        self.start()
        try:
            while True:
                status = self.step()
                if status['state'] in (MissionState.COMPLETE.value, MissionState.FAILED.value):
                    return
                time.sleep(tick)
        finally:
            self._record_event('Blocking run finished.', event_type='runtime')

    def start_background(self, tick_s: float = 0.2) -> None:
        self.tick_s = max(0.02, float(tick_s))
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self.start()
            self._thread = threading.Thread(target=self._background_loop, name='customdrive-demo', daemon=True)
            self._thread.start()
            self._record_event('Background loop started.', event_type='runtime', tick_s=self.tick_s)

    def stop_background(self, join: bool = False) -> None:
        self._stop_event.set()
        thread = self._thread
        if join and thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        if thread is not None and not thread.is_alive():
            self._thread = None

    def close(self) -> None:
        self.stop_background(join=True)
        self._record_event('Runtime closed.', event_type='runtime')

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
            runtime_cfg = self.settings.get('runtime') or {}
            self.tick_s = float(runtime_cfg.get('tick_s_sim', self.tick_s))
            self.event_history_limit = clamp_int(runtime_cfg.get('event_history_limit', self.event_history_limit), self.event_history_limit, 20, 1000)
            self._record_event('Runtime settings saved.', event_type='settings')
            return copy.deepcopy(self.settings)

    def _background_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                status = self.step()
                if status['state'] in (MissionState.COMPLETE.value, MissionState.FAILED.value):
                    self._stop_event.set()
                    break
                time.sleep(self.tick_s)
        finally:
            self._record_event('Background loop stopped.', event_type='runtime', final_state=self.last_snapshot.state)
            self._thread = None

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return self.status_unlocked()

    def status_unlocked(self) -> Dict[str, Any]:
        snapshot = self.last_snapshot
        detections = []
        for det in self.last_perception.detections:
            detections.append(
                {
                    'label': det.label,
                    'confidence': det.confidence,
                    'box': asdict(det.box),
                }
            )

        recent_logs = [asdict(item) for item in self.robot.history[-25:]]
        debug_events = list(self.controller.get_debug_events(limit=self.event_history_limit // 2)) + list(self._runtime_events[-(self.event_history_limit // 2):])
        debug_events = sorted(debug_events, key=lambda item: float(item.get('timestamp', 0.0)))[-self.event_history_limit:]
        return {
            'mode': self.mode,
            'state': snapshot.state,
            'detail': snapshot.detail,
            'retries': snapshot.retries,
            'completed_cycles': snapshot.completed_cycles,
            'active_route_leg': snapshot.active_route_leg,
            'last_command': asdict(snapshot.last_command),
            'frame': {'width': FRAME_W, 'height': FRAME_H},
            'detections': detections,
            'logs': recent_logs,
            'debug_events': debug_events,
            'running': bool(self._thread and self._thread.is_alive() and not self._stop_event.is_set()),
            'max_cycles': self.max_cycles,
            'last_error': self.last_error,
        }
