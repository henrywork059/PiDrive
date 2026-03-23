from __future__ import annotations

import copy
import threading
import time
from dataclasses import asdict
from typing import Any, Dict, Optional

from .config import MissionConfig
from .debug_tools import append_event, clamp_int
from .mission_controller import MissionController
from .mission_state import MissionState
from .models import FramePerception
from .perception import build_frame_perception, detections_as_dict, merge_perception_settings, perception_backend_ready
from .picar_bridge import PiCarRobotBridge
from .piserver_integration import load_piserver_symbols, merge_live_settings_with_piserver, sync_custom_settings_to_piserver
from .runtime_settings import load_settings, save_settings


class LiveMissionRuntime:
    mode = 'live'

    def __init__(self, max_cycles: int = 2):
        CameraService, MotorService, _ConfigStore = load_piserver_symbols()
        self.max_cycles = max(1, int(max_cycles))
        self.tick_s = 0.1
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        base_settings = load_settings()
        self.settings, self.piserver_runtime = merge_live_settings_with_piserver(base_settings)
        runtime_cfg = self.settings.get('runtime') or {}
        self.event_history_limit = clamp_int(runtime_cfg.get('event_history_limit', 200), 200, 20, 1000)
        self._runtime_events: list[dict[str, Any]] = []
        self.last_error = ''
        self.last_camera_error = ''
        self.last_frame_timestamp = 0.0
        self.services_started = False
        self.service_state = 'created'
        self.service_detail = 'Waiting to start PiServer camera/motor services.'

        self.perception_settings = merge_perception_settings(self.settings.get('perception'))
        self.camera_service = CameraService()
        self.motor_service = MotorService()
        self._configure_services_from_settings(restart_camera=False)
        self.camera_service.set_preview_enabled(True)
        self.camera_service.set_processing_enabled(True)

        ready, reason = perception_backend_ready()
        self.perception_ready = ready
        self.perception_message = reason

        self.bridge = PiCarRobotBridge(
            motor=self.motor_service,
            arm=None,
            mode_name='custom_drive',
            steer_mix=float(runtime_cfg.get('steer_mix', 0.75)),
            allow_virtual_grab_without_arm=bool(runtime_cfg.get('allow_virtual_grab_without_arm', False)),
        )
        self._record_event('Live runtime created using PiServer CameraService and MotorService.', event_type='runtime', max_cycles=self.max_cycles)
        self.reset(max_cycles=self.max_cycles)

    def _record_event(self, message: str, *, level: str = 'info', event_type: str = 'runtime', **fields: Any) -> None:
        append_event(self._runtime_events, message, level=level, event_type=event_type, limit=self.event_history_limit, **fields)

    def _start_services_if_needed(self) -> None:
        if self.services_started:
            return
        self.service_state = 'starting'
        self.service_detail = 'Starting PiServer camera service.'
        try:
            self.camera_service.start()
            self.services_started = True
            self.service_state = 'ready'
            backend = str(getattr(self.camera_service, 'backend', 'unknown'))
            self.service_detail = f'PiServer services ready. Camera backend: {backend}.'
            self.last_camera_error = str(getattr(self.camera_service, 'last_error', '') or '')
            self._record_event('PiServer services started.', event_type='runtime', backend=backend)
        except Exception as exc:
            self.services_started = False
            self.service_state = 'error'
            self.service_detail = f'Failed to start PiServer services: {exc}'
            self.last_camera_error = str(exc)
            self.last_error = self.last_camera_error
            self._record_event('PiServer services failed to start.', level='error', event_type='runtime', detail=self.last_camera_error)
            raise

    def _configure_services_from_settings(self, restart_camera: bool) -> None:
        camera_cfg = self.settings.get('camera') or {}
        motor_cfg = self.settings.get('motor') or {}
        self.motor_service.apply_settings(motor_cfg)
        ok, message, _ = self.camera_service.apply_settings(camera_cfg, restart=restart_camera and self.services_started)
        if not ok and message:
            self.last_error = str(message)
            self.last_camera_error = str(message)
            self._record_event('Camera settings update reported a warning.', level='warning', event_type='camera', detail=self.last_error)

    def close(self) -> None:
        self.stop_background(join=True)
        try:
            self.bridge.stop('runtime closed')
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
        self.services_started = False
        self.service_state = 'closed'
        self.service_detail = 'Live runtime closed.'
        self._record_event('Live runtime closed.', event_type='runtime')

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
            self.piserver_runtime = sync_custom_settings_to_piserver(self.settings)
            self.perception_settings = merge_perception_settings(self.settings.get('perception'))
            self._configure_services_from_settings(restart_camera=True)
            runtime_cfg = self.settings.get('runtime') or {}
            self.tick_s = float(runtime_cfg.get('tick_s_live', self.tick_s))
            self.event_history_limit = clamp_int(runtime_cfg.get('event_history_limit', self.event_history_limit), self.event_history_limit, 20, 1000)
            self.bridge.steer_mix = float(runtime_cfg.get('steer_mix', self.bridge.steer_mix))
            self.bridge.allow_virtual_grab_without_arm = bool(
                runtime_cfg.get('allow_virtual_grab_without_arm', self.bridge.allow_virtual_grab_without_arm)
            )
            ready, reason = perception_backend_ready()
            self.perception_ready = ready
            self.perception_message = reason
            self.service_detail = 'Live settings saved to CustomDrive and synced to PiServer runtime.json.'
            self._record_event('Live runtime settings saved and synced to PiServer runtime.json.', event_type='settings')
            return copy.deepcopy(self.settings)

    def reset(self, max_cycles: Optional[int] = None) -> None:
        if max_cycles is not None:
            self.max_cycles = max(1, int(max_cycles))
        with self._lock:
            self.stop_background(join=True)
            self.bridge.reset_mission_state()
            self.config = MissionConfig(max_cycles=self.max_cycles)
            self.controller = MissionController(robot=self.bridge, config=self.config)
            self.controller.debug_limit = self.event_history_limit
            frame = self.camera_service.get_latest_frame(copy=False)
            frame_shape = getattr(frame, 'shape', None)
            if frame_shape is not None:
                frame_h = int(frame_shape[0] or 240)
                frame_w = int(frame_shape[1] or 426)
            else:
                camera_cfg = self.settings.get('camera') or {}
                frame_h = int(camera_cfg.get('height', 240) or 240)
                frame_w = int(camera_cfg.get('width', 426) or 426)
            self.last_perception = FramePerception(frame_width=frame_w, frame_height=frame_h, detections=[])
            self.last_snapshot = self.controller.snapshot()
            self.last_camera_error = str(getattr(self.camera_service, 'last_error', '') or self.last_camera_error)
            self.last_frame_timestamp = 0.0
            self.last_error = self.last_camera_error
            self._record_event('Live runtime reset.', event_type='runtime', max_cycles=self.max_cycles)

    def start(self) -> None:
        with self._lock:
            self._start_services_if_needed()
            if self.controller.state in (MissionState.COMPLETE, MissionState.FAILED):
                self.reset(max_cycles=self.max_cycles)
            if self.controller.state == MissionState.IDLE:
                self.controller.start()
                self._record_event('Mission start requested.', event_type='runtime')

    def step(self) -> Dict[str, Any]:
        with self._lock:
            self._start_services_if_needed()
            if self.controller.state not in (MissionState.COMPLETE, MissionState.FAILED):
                frame = self.camera_service.get_latest_frame(copy=True)
                if frame is not None:
                    self.last_perception = build_frame_perception(frame, self.perception_settings)
                    self.last_frame_timestamp = time.time()
                    if self.last_camera_error:
                        self._record_event('Camera recovered.', event_type='camera')
                    self.last_camera_error = ''
                else:
                    self.last_perception = FramePerception(
                        frame_width=int(getattr(self.camera_service, 'width', 426)),
                        frame_height=int(getattr(self.camera_service, 'height', 240)),
                        detections=[],
                        timestamp=time.monotonic(),
                    )
                    self.last_camera_error = str(getattr(self.camera_service, 'last_error', '') or 'No camera frame available.')
                    if self.last_camera_error != self.last_error:
                        self._record_event('No camera frame available.', level='warning', event_type='camera', detail=self.last_camera_error)
                self.last_snapshot = self.controller.update(self.last_perception)
                self.last_error = self.last_camera_error or str(getattr(self.bridge, 'last_error', '') or '')
            return self.status_unlocked()

    def run_blocking(self, tick_s: Optional[float] = None) -> None:
        runtime_cfg = self.settings.get('runtime') or {}
        tick = max(0.02, float(tick_s if tick_s is not None else runtime_cfg.get('tick_s_live', 0.1)))
        self.start()
        try:
            while True:
                status = self.step()
                if status['state'] in (MissionState.COMPLETE.value, MissionState.FAILED.value):
                    return
                time.sleep(tick)
        finally:
            self.bridge.stop('run_blocking finished')
            self._record_event('Blocking live run finished.', event_type='runtime')

    def start_background(self, tick_s: float = 0.1) -> None:
        self.tick_s = max(0.02, float(tick_s))
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self.start()
            self._thread = threading.Thread(target=self._background_loop, name='customdrive-live', daemon=True)
            self._thread.start()
            self._record_event('Background loop started.', event_type='runtime', tick_s=self.tick_s)

    def stop_background(self, join: bool = False) -> None:
        self._stop_event.set()
        thread = self._thread
        if join and thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        if thread is not None and not thread.is_alive():
            self._thread = None

    def _background_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                status = self.step()
                if status['state'] in (MissionState.COMPLETE.value, MissionState.FAILED.value):
                    self._stop_event.set()
                    break
                time.sleep(self.tick_s)
        finally:
            try:
                self.bridge.stop('background loop stopped')
            except Exception:
                pass
            self._record_event('Background loop stopped.', event_type='runtime', final_state=self.last_snapshot.state)
            self._thread = None

    def get_jpeg_frame(self):
        try:
            self._start_services_if_needed()
        except Exception:
            return None
        return self.camera_service.get_jpeg_frame()

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return self.status_unlocked()

    def status_unlocked(self) -> Dict[str, Any]:
        snapshot = self.last_snapshot
        recent_logs = [asdict(item) for item in self.bridge.history[-40:]]
        runtime_cfg = self.settings.get('runtime') or {}
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
            'frame': {
                'width': self.last_perception.frame_width or int(getattr(self.camera_service, 'width', 426)),
                'height': self.last_perception.frame_height or int(getattr(self.camera_service, 'height', 240)),
            },
            'detections': detections_as_dict(self.last_perception.detections),
            'logs': recent_logs,
            'debug_events': debug_events,
            'running': bool(self._thread and self._thread.is_alive() and not self._stop_event.is_set()),
            'max_cycles': self.max_cycles,
            'camera': {
                'backend': str(getattr(self.camera_service, 'backend', 'unknown')),
                'preview_live': bool(getattr(self.camera_service, 'preview_live', False)),
                'fps': float(self.camera_service.get_fps()),
                'error': self.last_camera_error,
                'last_frame_timestamp': self.last_frame_timestamp,
            },
            'motor_error': str(getattr(self.bridge, 'last_error', '') or ''),
            'motor_gpio_available': bool((self.motor_service.get_config() or {}).get('gpio_available', False)),
            'service_state': self.service_state,
            'service_detail': self.service_detail,
            'services_started': bool(self.services_started),
            'steer_mix': float(runtime_cfg.get('steer_mix', self.bridge.steer_mix)),
            'perception_ready': bool(self.perception_ready),
            'perception_message': self.perception_message,
            'arm_bound': bool(self.bridge.arm is not None),
            'virtual_grab': bool(self.bridge.allow_virtual_grab_without_arm),
            'last_error': self.last_error,
        }
