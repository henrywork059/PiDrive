from __future__ import annotations

import atexit
import copy
import json
import os
import shlex
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

from .arm_service import ArmService
from .debug_tools import append_event, clamp_float, clamp_int
from .manual_control_config import load_manual_control_config
from .mission1_tflite_detector import Mission1TFLiteDetector
from .models import Detection
from .project_paths import CONFIG_DIR, CUSTOMDRIVE_ROOT, PISERVER_RUNTIME_PATH, ensure_piserver_import_paths

ensure_piserver_import_paths()

from piserver.core.config_store import ConfigStore  # noqa: E402
from piserver.services.camera_service import CameraService  # noqa: E402
from piserver.services.motor_service import MotorService  # noqa: E402

WEB_DIR = Path(__file__).resolve().parent / 'mission1_web'
APP_VERSION = '0_5_9'
MISSION1_CONFIG_PATH = CONFIG_DIR / 'mission1_session.json'
MISSION1_MODEL_DIR = CUSTOMDRIVE_ROOT / 'models' / 'mission1'


def _default_arm_positions() -> dict[str, dict[str, int]]:
    return {
        '1': {'servo0': 110, 'servo1': 110, 'servo2': 130},
        '2': {'servo0': 92, 'servo1': 92, 'servo2': 128},
        '3': {'servo0': 92, 'servo1': 92, 'servo2': 72},
        '4': {'servo0': 62, 'servo1': 62, 'servo2': 72},
        '5': {'servo0': 110, 'servo1': 110, 'servo2': 130},
        '6': {'servo0': 90, 'servo1': 90, 'servo2': 90},
        '7': {'servo0': 90, 'servo1': 90, 'servo2': 90},
        '8': {'servo0': 90, 'servo1': 90, 'servo2': 90},
    }


DEFAULT_MISSION1_CONFIG: dict[str, Any] = {
    'server': {
        'host': '0.0.0.0',
        'port': 5050,
        'refresh_ms': 200,
    },
    'session': {
        'route_text': '--forward 2 --turn-right 5 --forward 5 --turn-right 5',
        'target_class_id': 1,
        'confidence_threshold': 0.25,
        'iou_threshold': 0.45,
        'loop_tick_s': 0.08,
    },
    'drive': {
        'forward_speed': 0.22,
        'turn_k': 0.005,
        'turn_speed_max': 0.75,
        'target_x_deadband_ratio': 0.035,
        # Legacy keys kept for backward compatibility with earlier Mission 1 patches.
        'steer_mix': 0.75,
        'align_kp': 1.0,
        'max_steering': 0.85,
        'center_tolerance_ratio': 0.1,
        'approach_speed': 0.2,
        'target_reached_bottom_ratio': 0.85,
    },
    'camera': {
        'start_after_route': True,
        'preview_enabled': True,
        'processing_enabled': True,
    },
    'mission': {
        'pickup_classes': [1, 2],
        'dropoff_map': {'1': 3, '2': 4},
        'search_rotate_speed': 0.28,
        'reverse_after_release_s': 0.9,
        'reverse_speed': 0.18,
        'route_forward_speed': 0.22,
        'route_backward_speed': 0.18,
        'route_turn_speed': 0.75,
    },
    'ai': {
        'selected_model': '',
        'active_model': '',
    },
    'arm': {
        'enabled': True,
        'pose_settle_s': 0.45,
        'grip_trigger_y_ratio': 0.3,
        'capture_x_tolerance_ratio': 0.05,
        'positions': _default_arm_positions(),
        'roles': {
            'starting_position': 1,
            'grip_ready': 2,
            'grip': 3,
            'grip_and_lift': 4,
            'release': 5,
        },
    },
}

_BOX_TARGET_COLOR = (20, 220, 255)
_BOX_NORMAL_COLOR = (70, 230, 120)
_BOX_TEXT_COLOR = (245, 248, 255)
_CENTER_LINE_COLOR = (140, 150, 170)
_CENTER_BAND_COLOR = (40, 90, 160)
ARM_STAGE_ORDER = {
    'idle': 0,
    'starting_position_loaded': 1,
    'grip_ready_loaded': 2,
    'grip_loaded': 3,
    'grip_and_lift_loaded': 4,
    'release_loaded': 5,
}

def _deep_merge(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in (incoming or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=path.stem + '_', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(text)
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except OSError:
            pass


def normalize_mission1_config(data: dict[str, Any] | None) -> dict[str, Any]:
    merged = _deep_merge(DEFAULT_MISSION1_CONFIG, data or {})
    server = merged.get('server') if isinstance(merged.get('server'), dict) else {}
    session = merged.get('session') if isinstance(merged.get('session'), dict) else {}
    drive = merged.get('drive') if isinstance(merged.get('drive'), dict) else {}
    camera = merged.get('camera') if isinstance(merged.get('camera'), dict) else {}
    mission = merged.get('mission') if isinstance(merged.get('mission'), dict) else {}
    ai = merged.get('ai') if isinstance(merged.get('ai'), dict) else {}
    arm = merged.get('arm') if isinstance(merged.get('arm'), dict) else {}

    selected_model = str(ai.get('selected_model', '') or '').strip()
    if not selected_model:
        selected_model = str(ai.get('active_model', '') or '').strip()

    deadband_migration_version = clamp_int(drive.get('_target_x_deadband_migration_v', 0), 0, 0, 99)
    raw_target_x_deadband_ratio = clamp_float(drive.get('target_x_deadband_ratio', 0.035), 0.035, 0.01, 0.25)
    if deadband_migration_version < 1:
        raw_target_x_deadband_ratio = clamp_float(raw_target_x_deadband_ratio * 0.7, 0.035, 0.01, 0.25)
        deadband_migration_version = 1

    known_drive_keys = {
        'forward_speed',
        'turn_k',
        'turn_speed_max',
        'target_x_deadband_ratio',
        'steer_mix',
        'align_kp',
        'max_steering',
        'center_tolerance_ratio',
        'approach_speed',
        '_target_x_deadband_migration_v',
        'target_reached_bottom_ratio',
    }
    legacy_drive_keys = {key: copy.deepcopy(value) for key, value in drive.items() if key not in known_drive_keys}

    default_positions = _default_arm_positions()
    positions_in = arm.get('positions') if isinstance(arm.get('positions'), dict) else {}
    position_keys: set[str] = set(default_positions.keys())
    for key in positions_in.keys():
        key_text = str(key).strip()
        if key_text.isdigit():
            position_keys.add(str(max(1, min(99, int(key_text)))))
    positions_out: dict[str, dict[str, int]] = {}
    for key in sorted(position_keys, key=lambda item: int(item)):
        source = positions_in.get(key) if isinstance(positions_in.get(key), dict) else {}
        fallback = default_positions.get(key, {'servo0': 90, 'servo1': 90, 'servo2': 90})
        positions_out[key] = {
            'servo0': clamp_int(source.get('servo0', fallback.get('servo0', 90)), fallback.get('servo0', 90), 0, 180),
            'servo1': clamp_int(source.get('servo1', fallback.get('servo1', 90)), fallback.get('servo1', 90), 0, 180),
            'servo2': clamp_int(source.get('servo2', fallback.get('servo2', 90)), fallback.get('servo2', 90), 0, 180),
        }

    roles_in = arm.get('roles') if isinstance(arm.get('roles'), dict) else {}

    def _role_position(key: str, default_value: int) -> int:
        raw = roles_in.get(key, default_value)
        normalized_value = clamp_int(raw, default_value, 1, 99)
        if str(normalized_value) not in positions_out:
            return int(sorted(positions_out.keys(), key=lambda item: int(item))[0])
        return normalized_value

    normalized = {
        'server': {
            'host': str(server.get('host', '0.0.0.0') or '0.0.0.0').strip() or '0.0.0.0',
            'port': clamp_int(server.get('port', 5050), 5050, 1, 65535),
            'refresh_ms': clamp_int(server.get('refresh_ms', 200), 200, 50, 5000),
        },
        'session': {
            'route_text': str(session.get('route_text', DEFAULT_MISSION1_CONFIG['session']['route_text']) or '').strip(),
            'target_class_id': clamp_int(session.get('target_class_id', 1), 1, 0, 9999),
            'confidence_threshold': round(clamp_float(session.get('confidence_threshold', 0.25), 0.25, 0.01, 0.99), 3),
            'iou_threshold': round(clamp_float(session.get('iou_threshold', 0.45), 0.45, 0.01, 0.99), 3),
            'loop_tick_s': round(clamp_float(session.get('loop_tick_s', 0.08), 0.08, 0.02, 1.0), 3),
        },
        'drive': {
            'forward_speed': round(clamp_float(drive.get('forward_speed', drive.get('approach_speed', 0.22)), 0.22, 0.0, 1.0), 3),
            'turn_k': round(clamp_float(drive.get('turn_k', 0.005), 0.005, 0.0001, 1.0), 5),
            'turn_speed_max': round(clamp_float(drive.get('turn_speed_max', drive.get('max_steering', 0.75)), 0.75, 0.05, 1.0), 3),
            'target_x_deadband_ratio': round(raw_target_x_deadband_ratio, 3),
            '_target_x_deadband_migration_v': deadband_migration_version,
            'steer_mix': round(clamp_float(drive.get('steer_mix', 0.75), 0.75, 0.0, 1.0), 3),
            'align_kp': round(clamp_float(drive.get('align_kp', 1.0), 1.0, 0.1, 4.0), 3),
            'max_steering': round(clamp_float(drive.get('max_steering', 0.85), 0.85, 0.05, 1.0), 3),
            'center_tolerance_ratio': round(clamp_float(drive.get('center_tolerance_ratio', 0.1), 0.1, 0.01, 0.5), 3),
            'approach_speed': round(clamp_float(drive.get('approach_speed', 0.2), 0.2, 0.0, 1.0), 3),
            'target_reached_bottom_ratio': round(clamp_float(drive.get('target_reached_bottom_ratio', 0.85), 0.85, 0.1, 0.99), 3),
        },
        'camera': {
            'start_after_route': bool(camera.get('start_after_route', True)),
            'preview_enabled': bool(camera.get('preview_enabled', True)),
            'processing_enabled': bool(camera.get('processing_enabled', True)),
        },
        'mission': {
            'pickup_classes': [clamp_int(item, 1, 1, 9999) for item in (mission.get('pickup_classes') or [1, 2])][:8] or [1, 2],
            'dropoff_map': {
                '1': clamp_int((mission.get('dropoff_map') or {}).get('1', 3), 3, 0, 9999),
                '2': clamp_int((mission.get('dropoff_map') or {}).get('2', 4), 4, 0, 9999),
            },
            'search_rotate_speed': round(clamp_float(mission.get('search_rotate_speed', 0.28), 0.28, 0.05, 1.0), 3),
            'reverse_after_release_s': round(clamp_float(mission.get('reverse_after_release_s', 0.9), 0.9, 0.0, 5.0), 3),
            'reverse_speed': round(clamp_float(mission.get('reverse_speed', 0.18), 0.18, 0.0, 1.0), 3),
            'route_forward_speed': round(clamp_float(mission.get('route_forward_speed', drive.get('forward_speed', 0.22)), drive.get('forward_speed', 0.22), 0.0, 1.0), 3),
            'route_backward_speed': round(clamp_float(mission.get('route_backward_speed', mission.get('reverse_speed', 0.18)), mission.get('reverse_speed', 0.18), 0.0, 1.0), 3),
            'route_turn_speed': round(clamp_float(mission.get('route_turn_speed', drive.get('turn_speed_max', drive.get('max_steering', 0.75))), drive.get('turn_speed_max', drive.get('max_steering', 0.75)), 0.05, 1.0), 3),
        },
        'ai': {
            'selected_model': selected_model,
            'active_model': selected_model,
        },
        'arm': {
            'enabled': bool(arm.get('enabled', True)),
            'pose_settle_s': round(clamp_float(arm.get('pose_settle_s', 0.45), 0.45, 0.0, 5.0), 3),
            'grip_trigger_y_ratio': round(clamp_float(arm.get('grip_trigger_y_ratio', 0.3), 0.3, 0.05, 0.95), 3),
            'capture_x_tolerance_ratio': round(clamp_float(arm.get('capture_x_tolerance_ratio', 0.05), 0.05, 0.01, 0.25), 3),
            'positions': positions_out,
            'roles': {
                'starting_position': _role_position('starting_position', 1),
                'grip_ready': _role_position('grip_ready', 2),
                'grip': _role_position('grip', 3),
                'grip_and_lift': _role_position('grip_and_lift', 4),
                'release': _role_position('release', 5),
            },
        },
    }
    normalized['drive'].update(legacy_drive_keys)
    return normalized


def load_mission1_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or MISSION1_CONFIG_PATH
    if not cfg_path.exists():
        return copy.deepcopy(DEFAULT_MISSION1_CONFIG)
    try:
        raw = json.loads(cfg_path.read_text(encoding='utf-8'))
        if not isinstance(raw, dict):
            raw = {}
    except Exception:
        raw = {}
    return normalize_mission1_config(raw)


def save_mission1_config(data: dict[str, Any] | None, path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or MISSION1_CONFIG_PATH
    normalized = normalize_mission1_config(data)
    _atomic_write_text(cfg_path, json.dumps(normalized, indent=2, ensure_ascii=False) + '\n')
    return normalized


def parse_route_text(route_text: str) -> list[dict[str, Any]]:
    tokens = shlex.split(str(route_text or '').strip())
    if not tokens:
        raise ValueError('Start route is empty.')
    steps: list[dict[str, Any]] = []
    index = 0
    while index < len(tokens):
        flag = str(tokens[index]).strip().lower()
        index += 1
        if index >= len(tokens):
            raise ValueError(f'Missing duration for {flag}.')
        raw_value = tokens[index]
        index += 1
        try:
            duration = float(raw_value)
        except Exception as exc:
            raise ValueError(f'Invalid duration for {flag}: {raw_value}') from exc
        if duration <= 0:
            raise ValueError(f'Duration for {flag} must be greater than zero.')

        if flag == '--forward':
            steps.append({'flag': flag, 'name': 'forward', 'duration_s': duration, 'motion': 'forward'})
        elif flag == '--backward':
            steps.append({'flag': flag, 'name': 'backward', 'duration_s': duration, 'motion': 'backward'})
        elif flag == '--turn-right':
            steps.append({'flag': flag, 'name': 'turn-right', 'duration_s': duration, 'motion': 'turn_right'})
        elif flag == '--turn-left':
            steps.append({'flag': flag, 'name': 'turn-left', 'duration_s': duration, 'motion': 'turn_left'})
        else:
            raise ValueError(f'Unsupported route flag: {flag}')
    return steps


class Mission1SessionContext:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self.config_store = ConfigStore(PISERVER_RUNTIME_PATH)
        self.config = load_mission1_config()
        self.detector = Mission1TFLiteDetector(MISSION1_MODEL_DIR)
        self.motor_service = MotorService()
        self.camera_service: CameraService | None = None
        self.arm_service = ArmService(load_manual_control_config().get('arm', {}))

        self.events: list[dict[str, Any]] = []
        self.current_phase = 'idle'
        self.detail = 'Mission 1 session ready.'
        self.last_command = {'mode': 'stop', 'steering': 0.0, 'throttle': 0.0, 'left': 0.0, 'right': 0.0, 'note': 'idle'}
        self.last_detections: list[dict[str, Any]] = []
        self.last_frame = {'width': 640, 'height': 360}
        self.route_steps: list[dict[str, Any]] = []
        self.route_text = str(self.config.get('session', {}).get('route_text', '') or '')
        self.active_leg_index = -1
        self.active_leg_name = ''
        self.target_found = False
        self.target_side = 'none'
        self.car_turn_direction = 'stopped'
        self.last_error = ''
        self.started_at = 0.0
        self.control_target: dict[str, Any] | None = None
        self.annotated_jpeg: bytes | None = None
        self.pipeline_fps = 0.0
        self.pipeline_cycle_time_ms = 0.0
        self.loaded_model_name = 'none'
        self.selected_model_name = self._selected_model_name()
        self.last_output_summary = ''
        self.arm_sequence_state = 'idle'
        self.arm_last_pose_role = ''
        self.arm_last_pose_number = 0
        self.arm_sequence_note = 'Mission arm sequence idle.'
        self.arm_target_lock_engaged = False
        self.held_class_id: int | None = None
        self.dropoff_target_class_id: int | None = None
        self.pickup_target_class_id: int | None = None
        self.mission_state = 'pickup_search'
        self._last_pickup_gate_log_at = 0.0
        self._last_dropoff_gate_log_at = 0.0

        self._apply_motor_defaults()
        ready, message = self.detector.backend_ready()
        self._record(message, event_type='model', level='info' if ready else 'warning')
        arm_status = self.arm_service.status()
        self._record(arm_status.get('last_message', 'Mission arm ready.'), event_type='arm', level='info' if arm_status.get('available') else 'warning')

    def _record(self, message: str, *, level: str = 'info', event_type: str = 'runtime', **fields: Any) -> None:
        append_event(self.events, message, level=level, event_type=event_type, limit=250, **fields)

    def _selected_model_name(self) -> str:
        ai_cfg = self.config.get('ai') if isinstance(self.config.get('ai'), dict) else {}
        selected = str(ai_cfg.get('selected_model', '') or '').strip()
        if not selected:
            selected = str(ai_cfg.get('active_model', '') or '').strip()
        return selected

    def _reload_arm_backend(self) -> dict[str, Any]:
        manual_cfg = load_manual_control_config()
        arm_cfg = manual_cfg.get('arm') if isinstance(manual_cfg.get('arm'), dict) else {}
        return self.arm_service.reload(arm_cfg)

    def _arm_config(self) -> dict[str, Any]:
        cfg = self.get_config().get('arm')
        return cfg if isinstance(cfg, dict) else {}

    def _arm_positions(self) -> dict[str, dict[str, int]]:
        positions = self._arm_config().get('positions')
        return positions if isinstance(positions, dict) else {}

    def _arm_pose_for_role(self, role: str) -> tuple[int, dict[str, int]] | tuple[None, None]:
        arm_cfg = self._arm_config()
        roles = arm_cfg.get('roles') if isinstance(arm_cfg.get('roles'), dict) else {}
        positions = self._arm_positions()
        role_value = roles.get(role, 0)
        try:
            pose_number = int(role_value)
        except Exception:
            pose_number = 0
        pose = positions.get(str(pose_number)) if pose_number > 0 else None
        if not isinstance(pose, dict):
            return None, None
        return pose_number, {
            'servo0': clamp_int(pose.get('servo0', 90), 90, 0, 180),
            'servo1': clamp_int(pose.get('servo1', 90), 90, 0, 180),
            'servo2': clamp_int(pose.get('servo2', 90), 90, 0, 180),
        }

    def _arm_stage_at_least(self, stage_name: str) -> bool:
        return ARM_STAGE_ORDER.get(self.arm_sequence_state, 0) >= ARM_STAGE_ORDER.get(stage_name, 0)

    def _mission_config(self) -> dict[str, Any]:
        cfg = self.get_config().get('mission')
        return cfg if isinstance(cfg, dict) else {}

    def _pickup_classes(self) -> list[int]:
        mission_cfg = self._mission_config()
        pickup_classes = mission_cfg.get('pickup_classes') if isinstance(mission_cfg.get('pickup_classes'), list) else [1, 2]
        out: list[int] = []
        for item in pickup_classes:
            try:
                class_id = int(item)
            except Exception:
                continue
            if class_id >= 0 and class_id not in out:
                out.append(class_id)
        return out or [1, 2]

    def _dropoff_class_for(self, held_class_id: int | None) -> int | None:
        if held_class_id is None:
            return None
        mapping = self._mission_config().get('dropoff_map')
        if isinstance(mapping, dict):
            try:
                return int(mapping.get(str(int(held_class_id))))
            except Exception:
                return None
        return None

    def _search_rotate_speed(self) -> float:
        mission_cfg = self._mission_config()
        return float(mission_cfg.get('search_rotate_speed', 0.28) or 0.28)

    def _route_forward_speed(self) -> float:
        mission_cfg = self._mission_config()
        drive_cfg = self.get_config().get('drive', {})
        return float(mission_cfg.get('route_forward_speed', drive_cfg.get('forward_speed', drive_cfg.get('approach_speed', 0.22))) or drive_cfg.get('forward_speed', drive_cfg.get('approach_speed', 0.22)) or 0.22)

    def _route_backward_speed(self) -> float:
        mission_cfg = self._mission_config()
        return float(mission_cfg.get('route_backward_speed', mission_cfg.get('reverse_speed', 0.18)) or mission_cfg.get('reverse_speed', 0.18) or 0.18)

    def _route_turn_speed(self) -> float:
        mission_cfg = self._mission_config()
        drive_cfg = self.get_config().get('drive', {})
        return float(mission_cfg.get('route_turn_speed', drive_cfg.get('turn_speed_max', drive_cfg.get('max_steering', 0.75))) or drive_cfg.get('turn_speed_max', drive_cfg.get('max_steering', 0.75)) or 0.75)

    def _reverse_after_release(self) -> None:
        mission_cfg = self._mission_config()
        duration_s = float(mission_cfg.get('reverse_after_release_s', 0.9) or 0.9)
        reverse_speed = float(mission_cfg.get('reverse_speed', 0.18) or 0.18)
        if duration_s <= 0.0 or reverse_speed <= 0.0:
            self._stop_with_note('release complete -> reverse skipped by mission config')
            return
        deadline = time.monotonic() + duration_s
        self.current_phase = 'ai_reverse_reset'
        self.mission_state = 'reverse_reset'
        self.target_side = 'reverse'
        self.car_turn_direction = 'backward'
        self.detail = f'Release complete. Reversing for {duration_s:.2f}s before pickup search restart.'
        self.last_output_summary = self.detail
        self._record(self.detail, event_type='mission', reverse_speed=reverse_speed, duration_s=duration_s)
        while time.monotonic() < deadline and not self._stop_event.is_set():
            self._apply_direct_motor_command(-reverse_speed, -reverse_speed, 'release complete -> reverse reset')
            time.sleep(0.05)
        self._stop_with_note('reverse reset complete')

    def _class_id_int(self, item: dict[str, Any]) -> int | None:
        try:
            return int(item.get('class_id'))
        except Exception:
            return None

    def _best_detection_for_classes(
        self,
        detections: list[dict[str, Any]],
        class_ids: list[int],
        *,
        preferred_class_id: int | None = None,
    ) -> dict[str, Any] | None:
        if not class_ids:
            return None
        matches = [item for item in detections if self._class_id_int(item) in class_ids]
        if not matches:
            return None
        if preferred_class_id is not None:
            preferred_matches = [item for item in matches if self._class_id_int(item) == int(preferred_class_id)]
            if preferred_matches:
                matches = preferred_matches
        return max(matches, key=lambda item: (float(item['box']['width']) * float(item['box']['height']), float(item.get('confidence', 0.0))))

    def _mark_active_target(self, detections: list[dict[str, Any]], target: dict[str, Any] | None) -> None:
        for item in detections:
            item['is_target_class'] = False
        if isinstance(target, dict):
            target['is_target_class'] = True

    def _tracking_deadband_px(self, frame_w: int) -> float:
        return max(1.0, float(frame_w) * float(self.get_config().get('drive', {}).get('target_x_deadband_ratio', 0.05)))

    def _capture_deadband_px(self, frame_w: int) -> float:
        return max(1.0, float(frame_w) * float(self._arm_config().get('capture_x_tolerance_ratio', 0.05) or 0.05))

    def _grip_trigger_y_px(self, frame_h: int) -> float:
        return -float(frame_h) * float(self._arm_config().get('grip_trigger_y_ratio', 0.3) or 0.3)

    def _target_close_enough(self, target_x: float, target_y: float, frame_w: int, frame_h: int) -> tuple[bool, float, float]:
        capture_deadband_px = self._capture_deadband_px(frame_w)
        grip_trigger_y_px = self._grip_trigger_y_px(frame_h)
        return abs(target_x) < capture_deadband_px and target_y < grip_trigger_y_px, capture_deadband_px, grip_trigger_y_px

    def _maybe_log_gate_status(
        self,
        gate_name: str,
        *,
        class_id: int,
        target_x: float,
        target_y: float,
        tracking_deadband_px: float,
        capture_deadband_px: float,
        grip_trigger_y_px: float,
        close_enough: bool,
    ) -> None:
        attr_name = '_last_pickup_gate_log_at' if gate_name == 'pickup' else '_last_dropoff_gate_log_at'
        now = time.time()
        last_at = float(getattr(self, attr_name, 0.0) or 0.0)
        if now - last_at < 1.0:
            return
        setattr(self, attr_name, now)
        self._record(
            f'{gate_name} gate check for class {class_id}: target=({target_x:.1f}, {target_y:.1f})px '
            f'track_deadband={tracking_deadband_px:.1f}px capture_deadband={capture_deadband_px:.1f}px '
            f'grip_trigger_y={grip_trigger_y_px:.1f}px close_enough={close_enough}.',
            event_type='mission',
            level='info',
            class_id=int(class_id),
            target_x=round(float(target_x), 2),
            target_y=round(float(target_y), 2),
            tracking_deadband_px=round(float(tracking_deadband_px), 2),
            capture_deadband_px=round(float(capture_deadband_px), 2),
            grip_trigger_y_px=round(float(grip_trigger_y_px), 2),
            close_enough=bool(close_enough),
        )

    def _drive_toward_target(self, target_x: float, deadband_px: float, forward_speed: float, turn_k: float, turn_speed_max: float, note_prefix: str) -> None:
        turn_speed = min(turn_speed_max, abs(target_x) * turn_k)
        self.target_side = self._update_target_side(target_x, deadband_px)
        if abs(target_x) < deadband_px:
            self.car_turn_direction = 'forward'
            self._drive_forward(forward_speed, f'{note_prefix} -> forward')
        elif target_x < 0.0:
            self.car_turn_direction = 'left'
            self._turn_in_place('left', turn_speed, f'{note_prefix} -> left turn')
        else:
            self.car_turn_direction = 'right'
            self._turn_in_place('right', turn_speed, f'{note_prefix} -> right turn')

    def _load_arm_role_pose(self, role: str, *, reason: str, settle: bool = True) -> tuple[bool, str]:
        arm_cfg = self._arm_config()
        if not bool(arm_cfg.get('enabled', True)):
            message = 'Mission arm auto sequence disabled in Mission 1 config.'
            self.arm_sequence_note = message
            return False, message

        pose_number, pose = self._arm_pose_for_role(role)
        if pose_number is None or pose is None:
            message = f'No saved arm pose is mapped for role: {role}'
            self.arm_sequence_note = message
            self._record(message, event_type='arm', level='warning', role=role)
            return False, message

        ok, message = self.arm_service.set_pose(pose, note=f'{role.replace("_", " ")} pose #{pose_number}')
        level = 'info' if ok else 'warning'
        self._record(message, event_type='arm', level=level, role=role, pose_number=pose_number, reason=reason, pose=pose)
        if ok:
            self.arm_sequence_state = f'{role}_loaded'
            self.arm_last_pose_role = role
            self.arm_last_pose_number = int(pose_number)
            self.arm_sequence_note = f'{role.replace("_", " ")} pose #{pose_number} loaded ({reason}).'
            if settle:
                settle_s = float(arm_cfg.get('pose_settle_s', 0.45) or 0.45)
                if settle_s > 0.0:
                    time.sleep(min(5.0, max(0.0, settle_s)))
        else:
            self.arm_sequence_note = message
        return ok, message

    def _stop_with_note(self, note: str) -> None:
        self.motor_service.stop()
        self.last_command = {'mode': 'stop', 'steering': 0.0, 'throttle': 0.0, 'left': 0.0, 'right': 0.0, 'note': str(note)}

    def _apply_motor_defaults(self) -> None:
        runtime_cfg = self.config_store.load()
        motor_cfg = runtime_cfg.get('motor') if isinstance(runtime_cfg, dict) else None
        if isinstance(motor_cfg, dict):
            try:
                self.motor_service.apply_settings(motor_cfg)
            except Exception as exc:
                self._record(f'Failed to apply PiServer motor config: {exc}', level='warning', event_type='motor')

    def _ensure_camera_started(self) -> tuple[bool, str]:
        with self._lock:
            if self.camera_service is not None:
                return True, 'Camera already running.'
            camera_cfg = {}
            runtime_cfg = self.config_store.load()
            if isinstance(runtime_cfg, dict) and isinstance(runtime_cfg.get('camera'), dict):
                camera_cfg = copy.deepcopy(runtime_cfg.get('camera') or {})
            camera_service = CameraService()
            try:
                camera_service.apply_settings(camera_cfg, restart=False)
                camera_service.set_preview_enabled(bool(self.config.get('camera', {}).get('preview_enabled', True)))
                camera_service.set_processing_enabled(bool(self.config.get('camera', {}).get('processing_enabled', True)))
                camera_service.start()
            except Exception as exc:
                try:
                    camera_service.close()
                except Exception:
                    pass
                self.last_error = str(exc)
                return False, f'Failed to start camera: {exc}'
            self.camera_service = camera_service
            return True, 'Camera started.'

    def _shutdown_camera(self) -> None:
        with self._lock:
            camera_service = self.camera_service
            self.camera_service = None
        if camera_service is None:
            return
        try:
            camera_service.close()
        except Exception:
            pass

    def close(self) -> None:
        self.stop_session(join=True)
        self._shutdown_camera()
        try:
            self.motor_service.close()
        except Exception:
            pass
        try:
            self.arm_service.shutdown()
        except Exception:
            pass

    def get_config(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self.config)

    def save_config(self, updates: dict[str, Any] | None) -> dict[str, Any]:
        with self._lock:
            self.config = save_mission1_config(_deep_merge(self.config, updates or {}))
            self.route_text = str(self.config.get('session', {}).get('route_text', '') or '')
            self.selected_model_name = self._selected_model_name()
            return copy.deepcopy(self.config)

    def list_models(self) -> list[str]:
        return self.detector.list_models()

    def upload_model(self, file_storage) -> tuple[bool, str]:
        ok, message = self.detector.save_uploaded_model(file_storage)
        self._record(message, event_type='model', level='info' if ok else 'warning')
        if ok:
            self.save_config({'ai': {'selected_model': message, 'active_model': message}})
            self.selected_model_name = message
            return True, f'Uploaded model and selected it for the next Mission 1 run: {message}'
        return ok, message

    def select_model(self, name: str) -> tuple[bool, str]:
        safe_name = Path(str(name or '')).name
        if not safe_name:
            return False, 'Model name is required.'
        if safe_name not in self.list_models():
            return False, 'Model file does not exist.'
        self.save_config({'ai': {'selected_model': safe_name, 'active_model': safe_name}})
        self.selected_model_name = safe_name
        self._record(f'Selected Mission 1 model for the next run: {safe_name}', event_type='model')
        return True, f'Selected Mission 1 model: {safe_name}'

    def start_session(self, route_text: str | None = None) -> tuple[bool, str]:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return False, 'Mission 1 session is already running.'
        route_text = str(route_text or self.get_config().get('session', {}).get('route_text', '') or '').strip()
        try:
            steps = parse_route_text(route_text)
        except Exception as exc:
            return False, str(exc)

        selected_model = self._selected_model_name()
        if not selected_model:
            return False, 'No Mission 1 model is selected.'
        if selected_model not in self.list_models():
            return False, f'Selected model does not exist: {selected_model}'

        self.stop_session(join=True)
        arm_status = self._reload_arm_backend()
        self._record(arm_status.get('last_message', 'Mission arm backend refreshed.'), event_type='arm', level='info' if arm_status.get('available') else 'warning')
        with self._lock:
            self.route_text = route_text
            self.route_steps = copy.deepcopy(steps)
            self.active_leg_index = -1
            self.active_leg_name = ''
            self.current_phase = 'route_pending'
            self.detail = 'Mission 1 route queued.'
            self.last_command = {'mode': 'stop', 'steering': 0.0, 'throttle': 0.0, 'left': 0.0, 'right': 0.0, 'note': 'queued'}
            self.last_detections = []
            self.target_found = False
            self.target_side = 'none'
            self.car_turn_direction = 'stopped'
            self.last_error = ''
            self.control_target = None
            self.annotated_jpeg = None
            self.pipeline_fps = 0.0
            self.pipeline_cycle_time_ms = 0.0
            self.last_output_summary = ''
            self.loaded_model_name = 'none'
            self.arm_sequence_state = 'idle'
            self.arm_last_pose_role = ''
            self.arm_last_pose_number = 0
            self.arm_sequence_note = 'Mission arm sequence queued.'
            self.arm_target_lock_engaged = False
            self.held_class_id = None
            self.dropoff_target_class_id = None
            self.pickup_target_class_id = None
            self.mission_state = 'pickup_search'
            self.started_at = time.monotonic()
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_session, name='mission1-session', daemon=True)
            self._thread.start()
        self.save_config({'session': {'route_text': route_text}})
        self._record('Mission 1 session started.', event_type='session', route_text=route_text, selected_model=selected_model)
        return True, 'Mission 1 session started.'

    def stop_session(self, join: bool = True) -> tuple[bool, str]:
        self._stop_event.set()
        thread = self._thread
        if join and thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=3.0)
        self._thread = None
        try:
            self.motor_service.stop()
        except Exception:
            pass
        self._shutdown_camera()
        self.detector.unload()
        self.loaded_model_name = 'none'
        if self.current_phase not in {'idle', 'complete', 'stopped', 'failed'}:
            self.current_phase = 'stopped'
            self.detail = 'Mission 1 session stopped.'
            self.target_side = 'none'
            self.car_turn_direction = 'stopped'
            self.last_command = {'mode': 'stop', 'steering': 0.0, 'throttle': 0.0, 'left': 0.0, 'right': 0.0, 'note': 'stopped'}
        return True, 'Mission 1 session stopped.'

    def _set_route_drive(self, steering: float, throttle: float, note: str) -> None:
        steer_mix = float(self.get_config().get('drive', {}).get('steer_mix', 0.75))
        left, right = self.motor_service.update(steering=steering, throttle=throttle, steer_mix=steer_mix)
        self.last_command = {
            'mode': 'route_mix',
            'steering': float(steering),
            'throttle': float(throttle),
            'left': float(left),
            'right': float(right),
            'note': str(note),
        }

    def _apply_direct_motor_command(self, left_target: float, right_target: float, note: str) -> tuple[float, float]:
        with self.motor_service._lock:  # type: ignore[attr-defined]
            left_value = self.motor_service._apply_motor_tuning(  # type: ignore[attr-defined]
                float(left_target),
                float(self.motor_service.left_max_speed),
                float(self.motor_service.left_bias),
                int(self.motor_service.left_direction),
            )
            right_value = self.motor_service._apply_motor_tuning(  # type: ignore[attr-defined]
                float(right_target),
                float(self.motor_service.right_max_speed),
                float(self.motor_service.right_bias),
                int(self.motor_service.right_direction),
            )
            self.motor_service.left.set_speed(left_value)
            self.motor_service.right.set_speed(right_value)
            self.motor_service.last_left = left_value
            self.motor_service.last_right = right_value
        self.last_command = {
            'mode': 'direct_motor',
            'steering': 0.0,
            'throttle': 0.0,
            'left': float(left_value),
            'right': float(right_value),
            'note': str(note),
        }
        return left_value, right_value

    def _drive_forward(self, speed: float, note: str) -> None:
        speed = clamp_float(speed, 0.0, 0.0, 1.0)
        self._apply_direct_motor_command(speed, speed, note)

    def _drive_backward(self, speed: float, note: str) -> None:
        speed = clamp_float(speed, 0.0, 0.0, 1.0)
        self._apply_direct_motor_command(-speed, -speed, note)

    def _turn_in_place(self, direction: str, magnitude: float, note: str) -> None:
        magnitude = clamp_float(magnitude, 0.0, 0.0, 1.0)
        if direction == 'left':
            steering = -magnitude
        elif direction == 'right':
            steering = magnitude
        else:
            self.motor_service.stop()
            self.last_command = {'mode': 'stop', 'steering': 0.0, 'throttle': 0.0, 'left': 0.0, 'right': 0.0, 'note': str(note)}
            return

        left, right = self.motor_service.update(steering=steering, throttle=0.0, steer_mix=1.0)
        self.last_command = {
            'mode': 'turn_in_place',
            'steering': float(steering),
            'throttle': 0.0,
            'left': float(left),
            'right': float(right),
            'note': str(note),
        }

    def _update_target_side(self, target_x: float, deadband_px: float) -> str:
        if abs(target_x) < deadband_px:
            return 'center'
        return 'left' if target_x < 0.0 else 'right'

    def _run_arm_follow_sequence(
        self,
        *,
        target_class_id: int,
        target_x: float,
        target_y: float,
        frame_w: int,
        frame_h: int,
        deadband_px: float,
    ) -> bool:
        arm_cfg = self._arm_config()
        if not bool(arm_cfg.get('enabled', True)):
            return False

        if not self._arm_stage_at_least('grip_ready_loaded'):
            self._load_arm_role_pose('grip_ready', reason=f'class {target_class_id} detected', settle=True)

        grip_trigger_y_px = -float(frame_h) * float(arm_cfg.get('grip_trigger_y_ratio', 0.3) or 0.3)
        centered = abs(target_x) < deadband_px
        close_enough = target_y < grip_trigger_y_px

        if self._arm_stage_at_least('grip_and_lift_loaded'):
            self.arm_target_lock_engaged = True
            self.target_side = self._update_target_side(target_x, deadband_px)
            self.car_turn_direction = 'stopped'
            self._stop_with_note(f'class {target_class_id} captured -> holding after grip and lift')
            self.detail = (
                f'Target class {target_class_id} aligned at x={target_x:.1f}, y={target_y:.1f}. '
                f'Grip and lift pose already loaded; motors held stopped.'
            )
            self.last_output_summary = self.detail
            return True

        if centered and close_enough:
            self.arm_target_lock_engaged = True
            self.target_side = 'center'
            self.car_turn_direction = 'stopped'
            self._stop_with_note(f'class {target_class_id} centered and low in frame -> arm grip sequence')
            if not self._arm_stage_at_least('grip_loaded'):
                self._load_arm_role_pose('grip', reason=f'class {target_class_id} centered and y={target_y:.1f}', settle=True)
            if not self._arm_stage_at_least('grip_and_lift_loaded'):
                self._load_arm_role_pose('grip_and_lift', reason=f'class {target_class_id} grip complete', settle=True)
            self.detail = (
                f'Target class {target_class_id} is in the forward path and y={target_y:.1f} px '
                f'(< -{float(frame_h) * float(arm_cfg.get("grip_trigger_y_ratio", 0.3) or 0.3):.1f}). '
                'Grip then grip-and-lift pose loaded.'
            )
            self.last_output_summary = self.detail
            return True

        return False

    def _run_session(self) -> None:
        try:
            self._load_arm_role_pose('starting_position', reason='mission start', settle=True)
            if self._stop_event.is_set():
                return
            self._run_start_route()
            if self._stop_event.is_set():
                return
            self._run_camera_boot()
            if self._stop_event.is_set():
                return
            self._run_model_boot()
            if self._stop_event.is_set():
                return
            self._run_detection_loop()
        except Exception as exc:
            self.last_error = str(exc)
            self.current_phase = 'failed'
            self.detail = f'Mission 1 session failed: {exc}'
            self._record(self.detail, level='error', event_type='session')
        finally:
            try:
                self.motor_service.stop()
            except Exception:
                pass
            self._shutdown_camera()
            self.detector.unload()
            self.loaded_model_name = 'none'
            if self._stop_event.is_set() and self.current_phase not in {'complete', 'failed'}:
                self.current_phase = 'stopped'
                self.detail = 'Mission 1 session stopped.'
                self.target_side = 'none'
                self.car_turn_direction = 'stopped'
                self.last_command = {'mode': 'stop', 'steering': 0.0, 'throttle': 0.0, 'left': 0.0, 'right': 0.0, 'note': 'stopped'}
            self._thread = None

    def _run_start_route(self) -> None:
        self.current_phase = 'start_route'
        self.target_side = 'route'
        self.car_turn_direction = 'route'
        route_forward_speed = clamp_float(self._route_forward_speed(), 0.0, 0.0, 1.0)
        route_backward_speed = clamp_float(self._route_backward_speed(), 0.0, 0.0, 1.0)
        route_turn_speed = clamp_float(self._route_turn_speed(), 0.75, 0.05, 1.0)
        for index, step in enumerate(self.route_steps):
            if self._stop_event.is_set():
                return
            self.active_leg_index = index
            self.active_leg_name = str(step.get('name', ''))
            motion = str(step.get('motion', '') or '')
            duration_s = float(step.get('duration_s', 0.0) or 0.0)
            self.detail = f"Running route step {index + 1}/{len(self.route_steps)}: {self.active_leg_name}"
            self._record(
                self.detail,
                event_type='route',
                duration_s=duration_s,
                motion=motion,
                route_forward_speed=route_forward_speed,
                route_backward_speed=route_backward_speed,
                route_turn_speed=route_turn_speed,
            )
            deadline = time.monotonic() + duration_s
            while time.monotonic() < deadline and not self._stop_event.is_set():
                if motion == 'forward':
                    self.target_side = 'route'
                    self.car_turn_direction = 'forward'
                    self._drive_forward(route_forward_speed, f'route forward @ {route_forward_speed:.2f}')
                elif motion == 'backward':
                    self.target_side = 'route'
                    self.car_turn_direction = 'backward'
                    self._drive_backward(route_backward_speed, f'route backward @ {route_backward_speed:.2f}')
                elif motion == 'turn_left':
                    self.target_side = 'route'
                    self.car_turn_direction = 'left'
                    self._turn_in_place('left', route_turn_speed, f'route turn left @ {route_turn_speed:.2f}')
                elif motion == 'turn_right':
                    self.target_side = 'route'
                    self.car_turn_direction = 'right'
                    self._turn_in_place('right', route_turn_speed, f'route turn right @ {route_turn_speed:.2f}')
                else:
                    self._stop_with_note(f'unsupported route motion: {motion or self.active_leg_name}')
                    raise RuntimeError(f'Unsupported route motion: {motion or self.active_leg_name}')
                time.sleep(0.05)
        self.motor_service.stop()
        self.active_leg_name = ''
        self.active_leg_index = -1
        self.target_side = 'none'
        self.car_turn_direction = 'stopped'
        self.detail = 'Start route complete. Turning on camera next.'
        self._record(self.detail, event_type='route')

    def _run_camera_boot(self) -> None:
        self.current_phase = 'camera_boot'
        self.detail = 'Start route complete. Turning on camera.'
        self._record(self.detail, event_type='camera')
        ok, message = self._ensure_camera_started()
        if not ok:
            raise RuntimeError(message)
        self._record(message, event_type='camera')

        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and not self._stop_event.is_set():
            frame = self.camera_service.get_latest_frame(copy=True) if self.camera_service is not None else None
            if frame is not None:
                frame_h = int(getattr(frame, 'shape', (360, 640, 3))[0] or 360)
                frame_w = int(getattr(frame, 'shape', (360, 640, 3))[1] or 640)
                self.last_frame = {'width': frame_w, 'height': frame_h}
                self.detail = 'Camera is live. Loading AI model next.'
                return
            time.sleep(0.05)
        if self._stop_event.is_set():
            return
        self.detail = 'Camera started. Waiting for first frame.'

    def _run_model_boot(self) -> None:
        self.current_phase = 'model_boot'
        self.selected_model_name = self._selected_model_name()
        if not self.selected_model_name:
            raise RuntimeError('No Mission 1 model is selected.')
        self.detail = f'Loading AI model: {self.selected_model_name}'
        self._record(self.detail, event_type='model')
        ok, message = self.detector.load_model(self.selected_model_name)
        if not ok:
            raise RuntimeError(message)
        self.loaded_model_name = self.detector.get_active_name()
        self.detail = f'AI model loaded: {self.loaded_model_name}. Detection loop starting.'
        self._record(self.detail, event_type='model')

    def _run_detection_loop(self) -> None:
        ready, message = self.detector.backend_ready()
        if not ready:
            raise RuntimeError(message)
        session_cfg = self.get_config().get('session', {})
        drive_cfg = self.get_config().get('drive', {})
        pickup_classes = self._pickup_classes()
        confidence_threshold = float(session_cfg.get('confidence_threshold', 0.25))
        iou_threshold = float(session_cfg.get('iou_threshold', 0.45))
        tick_s = float(session_cfg.get('loop_tick_s', 0.08))
        forward_speed = float(drive_cfg.get('forward_speed', drive_cfg.get('approach_speed', 0.22)))
        turn_k = float(drive_cfg.get('turn_k', 0.005))
        turn_speed_max = float(drive_cfg.get('turn_speed_max', drive_cfg.get('max_steering', 0.75)))
        search_rotate_speed = float(self._search_rotate_speed())

        last_cycle_start = None
        fps_window_start = time.monotonic()
        fps_window_count = 0

        while not self._stop_event.is_set():
            loop_started = time.monotonic()
            camera_service = self.camera_service
            if camera_service is None:
                raise RuntimeError('Camera service is not available.')

            frame = camera_service.get_latest_frame(copy=True)
            if frame is None:
                self.current_phase = 'ai_wait_frame'
                self.mission_state = 'wait_frame'
                self.target_found = False
                self.target_side = 'no frame'
                self.car_turn_direction = 'stopped'
                self.last_detections = []
                self.control_target = None
                self.last_output_summary = 'No camera frame received yet.'
                self.detail = 'Camera is on. Waiting for frame for AI inference.'
                self.motor_service.stop()
                self.last_command = {'mode': 'stop', 'steering': 0.0, 'throttle': 0.0, 'left': 0.0, 'right': 0.0, 'note': 'waiting for frame'}
                time.sleep(tick_s)
                continue

            frame_h = int(getattr(frame, 'shape', (360, 640, 3))[0] or 360)
            frame_w = int(getattr(frame, 'shape', (360, 640, 3))[1] or 640)
            self.last_frame = {'width': frame_w, 'height': frame_h}

            detections = self.detector.detect(frame, conf_threshold=confidence_threshold, iou_threshold=iou_threshold)
            detection_rows = self._build_detection_rows(detections, frame_w, frame_h)
            target: dict[str, Any] | None = None

            if self.held_class_id in pickup_classes:
                desired_dropoff = self._dropoff_class_for(self.held_class_id)
                self.dropoff_target_class_id = desired_dropoff
                if desired_dropoff is None:
                    raise RuntimeError(f'No drop-off class is mapped for held class {self.held_class_id}.')
                target = self._best_detection_for_classes(detection_rows, [desired_dropoff])
                self.control_target = copy.deepcopy(target)
                self._mark_active_target(detection_rows, target)
                self.last_detections = detection_rows

                if target is None:
                    self.current_phase = 'ai_dropoff_search'
                    self.mission_state = 'dropoff_search'
                    self.target_found = False
                    self.target_side = 'search'
                    self.car_turn_direction = 'right'
                    self.arm_target_lock_engaged = False
                    self._turn_in_place('right', search_rotate_speed, f'holding class {self.held_class_id} -> rotate clockwise for class {desired_dropoff}')
                    self.last_output_summary = (
                        f'Holding class {self.held_class_id}. No class {desired_dropoff} detected. '
                        'Rotating clockwise to search the drop-off area.'
                    )
                    self.detail = self.last_output_summary
                else:
                    self.current_phase = 'ai_dropoff_track'
                    self.mission_state = 'dropoff_track'
                    self.target_found = True
                    target_x = float(target['center']['x'])
                    target_y = float(target['center']['y'])
                    tracking_deadband_px = self._tracking_deadband_px(frame_w)
                    close_enough, capture_deadband_px, grip_trigger_y_px = self._target_close_enough(target_x, target_y, frame_w, frame_h)
                    self.target_side = self._update_target_side(target_x, tracking_deadband_px)
                    if close_enough:
                        self.arm_target_lock_engaged = True
                        self.target_side = 'center'
                        self.car_turn_direction = 'stopped'
                        self._stop_with_note(f'class {desired_dropoff} centered and low in frame -> release sequence')
                        self._load_arm_role_pose('release', reason=f'drop-off class {desired_dropoff} reached', settle=True)
                        self._record(
                            f'Released held class {self.held_class_id} at drop-off class {desired_dropoff}.',
                            event_type='mission',
                            held_class_id=self.held_class_id,
                            dropoff_class_id=desired_dropoff,
                        )
                        self.last_output_summary = (
                            f'Drop-off class {desired_dropoff} is centered and close enough. '
                            f'Release pose loaded for held class {self.held_class_id}.'
                        )
                        self.detail = self.last_output_summary
                        released_class = self.held_class_id
                        self.held_class_id = None
                        self.dropoff_target_class_id = None
                        self.pickup_target_class_id = None
                        self._reverse_after_release()
                        if self._stop_event.is_set():
                            break
                        self._load_arm_role_pose('starting_position', reason='pickup search restart after release', settle=True)
                        self.current_phase = 'ai_pickup_search'
                        self.mission_state = 'pickup_search'
                        self.detail = f'Release and reverse complete. Restarting pickup search after dropping class {released_class}.'
                        self.last_output_summary = self.detail
                    else:
                        self.arm_target_lock_engaged = True
                        self._maybe_log_gate_status(
                            'dropoff',
                            class_id=desired_dropoff,
                            target_x=target_x,
                            target_y=target_y,
                            tracking_deadband_px=tracking_deadband_px,
                            capture_deadband_px=capture_deadband_px,
                            grip_trigger_y_px=grip_trigger_y_px,
                            close_enough=close_enough,
                        )
                        self._drive_toward_target(
                            target_x,
                            tracking_deadband_px,
                            forward_speed,
                            turn_k,
                            turn_speed_max,
                            f'drop-off class {desired_dropoff} x={target_x:.1f}',
                        )
                        self.last_output_summary = (
                            f'Holding class {self.held_class_id}. Tracking drop-off class {desired_dropoff} center=({target_x:.1f}, {target_y:.1f})px '
                            f'box={target["box"]["width"]:.1f}x{target["box"]["height"]:.1f}px conf={target["confidence"]:.3f}.'
                        )
                        self.detail = self.last_output_summary
            else:
                target = self._best_detection_for_classes(detection_rows, pickup_classes, preferred_class_id=self.pickup_target_class_id)
                self.control_target = copy.deepcopy(target)
                self._mark_active_target(detection_rows, target)
                self.last_detections = detection_rows

                if target is None:
                    self.current_phase = 'ai_pickup_search'
                    self.mission_state = 'pickup_search'
                    self.target_found = False
                    self.target_side = 'search'
                    self.car_turn_direction = 'right'
                    self.pickup_target_class_id = None
                    self.arm_target_lock_engaged = False
                    self._turn_in_place('right', search_rotate_speed, 'pickup search -> rotate clockwise for class 1/2')
                    self.last_output_summary = 'No class 1/2 detected. Rotating clockwise to search the pickup area.'
                    self.detail = self.last_output_summary
                else:
                    locked_class = self._class_id_int(target)
                    self.pickup_target_class_id = locked_class
                    target_x = float(target['center']['x'])
                    target_y = float(target['center']['y'])
                    tracking_deadband_px = self._tracking_deadband_px(frame_w)
                    close_enough, capture_deadband_px, grip_trigger_y_px = self._target_close_enough(target_x, target_y, frame_w, frame_h)
                    self.target_found = True
                    self.target_side = self._update_target_side(target_x, tracking_deadband_px)
                    if not self._arm_stage_at_least('grip_ready_loaded') or self.arm_last_pose_role == 'starting_position':
                        self._load_arm_role_pose('grip_ready', reason=f'pickup class {locked_class} detected', settle=True)
                    if close_enough:
                        self.current_phase = 'ai_pickup_capture'
                        self.mission_state = 'pickup_capture'
                        self.arm_target_lock_engaged = True
                        self.target_side = 'center'
                        self.car_turn_direction = 'stopped'
                        self._stop_with_note(f'class {locked_class} centered and low in frame -> grip sequence')
                        if not self._arm_stage_at_least('grip_loaded'):
                            self._load_arm_role_pose('grip', reason=f'pickup class {locked_class} centered and y={target_y:.1f}', settle=True)
                        if not self._arm_stage_at_least('grip_and_lift_loaded'):
                            self._load_arm_role_pose('grip_and_lift', reason=f'pickup class {locked_class} grip complete', settle=True)
                        self.held_class_id = locked_class
                        self.dropoff_target_class_id = self._dropoff_class_for(locked_class)
                        self.pickup_target_class_id = None
                        self._record(
                            f'Picked up class {locked_class}. Now searching for drop-off class {self.dropoff_target_class_id}.',
                            event_type='mission',
                            held_class_id=self.held_class_id,
                            dropoff_class_id=self.dropoff_target_class_id,
                        )
                        self.current_phase = 'ai_dropoff_search'
                        self.mission_state = 'dropoff_search'
                        self.target_found = False
                        self.target_side = 'search'
                        self.car_turn_direction = 'right'
                        self.arm_target_lock_engaged = False
                        self.last_output_summary = (
                            f'Class {locked_class} is centered and close enough. Grip and lift pose loaded. '
                            f'Holding class {locked_class}; next search class {self.dropoff_target_class_id}.'
                        )
                        self.detail = self.last_output_summary
                        if self.dropoff_target_class_id is not None:
                            self._turn_in_place(
                                'right',
                                search_rotate_speed,
                                f'pickup class {locked_class} secured -> start clockwise search for class {self.dropoff_target_class_id}',
                            )
                            self.last_output_summary = (
                                f'Picked up class {locked_class}. Starting clockwise search for drop-off class '
                                f'{self.dropoff_target_class_id} immediately.'
                            )
                            self.detail = self.last_output_summary
                    else:
                        self.current_phase = 'ai_pickup_track'
                        self.mission_state = 'pickup_track'
                        self.arm_target_lock_engaged = True
                        self._maybe_log_gate_status(
                            'pickup',
                            class_id=locked_class,
                            target_x=target_x,
                            target_y=target_y,
                            tracking_deadband_px=tracking_deadband_px,
                            capture_deadband_px=capture_deadband_px,
                            grip_trigger_y_px=grip_trigger_y_px,
                            close_enough=close_enough,
                        )
                        self._drive_toward_target(
                            target_x,
                            tracking_deadband_px,
                            forward_speed,
                            turn_k,
                            turn_speed_max,
                            f'pickup class {locked_class} x={target_x:.1f}',
                        )
                        self.last_output_summary = (
                            f'Locked pickup target class {locked_class}. center=({target_x:.1f}, {target_y:.1f})px '
                            f'box={target["box"]["width"]:.1f}x{target["box"]["height"]:.1f}px conf={target["confidence"]:.3f}.'
                        )
                        self.detail = self.last_output_summary

            annotated = self._annotate_frame(frame, detection_rows)
            self.annotated_jpeg = self._encode_jpeg(annotated)

            now = time.monotonic()
            if last_cycle_start is not None:
                delta = max(1e-6, now - last_cycle_start)
                self.pipeline_cycle_time_ms = delta * 1000.0
            last_cycle_start = now
            fps_window_count += 1
            elapsed = now - fps_window_start
            if elapsed >= 1.0:
                self.pipeline_fps = fps_window_count / max(elapsed, 1e-6)
                fps_window_count = 0
                fps_window_start = now

            sleep_time = max(0.0, tick_s - (time.monotonic() - loop_started))
            time.sleep(sleep_time)

    def _build_detection_rows(self, detections: list[Detection], frame_w: int, frame_h: int) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        frame_cx = float(frame_w) * 0.5
        frame_cy = float(frame_h) * 0.5
        for det in detections:
            class_text = str(det.label).strip()
            try:
                class_id = int(float(class_text))
            except Exception:
                class_id = class_text
            center_x_raw = float(det.box.center_x)
            center_y_raw = float(det.box.center_y)
            center_x = center_x_raw - frame_cx
            center_y = frame_cy - center_y_raw
            row = {
                'class_id': class_id,
                'label': class_text,
                'confidence': round(float(det.confidence), 4),
                'center': {
                    'x': round(center_x, 2),
                    'y': round(center_y, 2),
                    'x_raw': round(center_x_raw, 2),
                    'y_raw': round(center_y_raw, 2),
                },
                'box': {
                    'x1': round(float(det.box.x1), 2),
                    'y1': round(float(det.box.y1), 2),
                    'x2': round(float(det.box.x2), 2),
                    'y2': round(float(det.box.y2), 2),
                    'width': round(float(det.box.width), 2),
                    'height': round(float(det.box.height), 2),
                },
                'is_target_class': False,
            }
            rows.append(row)
        rows.sort(key=lambda item: (float(item['confidence']), float(item['box']['width']) * float(item['box']['height'])), reverse=True)
        return rows

    def _annotate_frame(self, frame_bgr, detections: list[dict[str, Any]]):
        if frame_bgr is None or cv2 is None:
            return frame_bgr
        canvas = frame_bgr.copy()
        frame_h, frame_w = canvas.shape[:2]
        band = max(1, int(round(float(frame_w) * float(self.get_config().get('drive', {}).get('target_x_deadband_ratio', 0.05)))))
        frame_cx = frame_w // 2
        left_band = max(0, int(frame_cx - band))
        right_band = min(frame_w - 1, int(frame_cx + band))
        cv2.rectangle(canvas, (left_band, 0), (right_band, frame_h - 1), _CENTER_BAND_COLOR, 1)
        cv2.line(canvas, (frame_cx, 0), (frame_cx, frame_h - 1), _CENTER_LINE_COLOR, 1)
        cv2.line(canvas, (0, frame_h // 2), (frame_w - 1, frame_h // 2), _CENTER_LINE_COLOR, 1)

        for item in detections:
            box = item.get('box', {})
            x1 = int(round(float(box.get('x1', 0.0))))
            y1 = int(round(float(box.get('y1', 0.0))))
            x2 = int(round(float(box.get('x2', 0.0))))
            y2 = int(round(float(box.get('y2', 0.0))))
            is_target = bool(item.get('is_target_class'))
            color = _BOX_TARGET_COLOR if is_target else _BOX_NORMAL_COLOR
            thickness = 3 if is_target else 2
            cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 0, 0), thickness + 2)
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, thickness)

            center_raw = item.get('center', {})
            cx = int(round(float(center_raw.get('x_raw', (x1 + x2) / 2.0))))
            cy = int(round(float(center_raw.get('y_raw', (y1 + y2) / 2.0))))
            cv2.circle(canvas, (cx, cy), 5 if is_target else 4, (0, 0, 0), -1)
            cv2.circle(canvas, (cx, cy), 3 if is_target else 2, color, -1)

            caption = f"id {item.get('class_id')} {float(item.get('confidence', 0.0)):.2f}"
            coord_text = f"({float(item['center']['x']):.0f}, {float(item['center']['y']):.0f})"
            label_y1 = max(0, y1 - 42)
            label_y2 = min(frame_h - 1, label_y1 + 38)
            label_x2 = min(frame_w - 1, x1 + max(124, int((x2 - x1) * 0.7)))
            cv2.rectangle(canvas, (x1, label_y1), (label_x2, label_y2), (0, 0, 0), -1)
            cv2.rectangle(canvas, (x1, label_y1), (label_x2, label_y2), color, 1)
            cv2.putText(canvas, caption, (max(4, x1 + 6), min(frame_h - 18, label_y1 + 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)
            cv2.putText(canvas, coord_text, (max(4, x1 + 6), min(frame_h - 6, label_y1 + 31)), cv2.FONT_HERSHEY_SIMPLEX, 0.46, _BOX_TEXT_COLOR, 1, cv2.LINE_AA)

        footer = (
            f"FPS {self.pipeline_fps:.1f} | state={self.mission_state} | "
            f"holding={self.held_class_id if self.held_class_id is not None else '-'} | "
            f"dropoff={self.dropoff_target_class_id if self.dropoff_target_class_id is not None else '-'} | "
            f"model={self.loaded_model_name}"
        )
        cv2.putText(canvas, footer, (10, max(24, frame_h - 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, _BOX_TEXT_COLOR, 2, cv2.LINE_AA)
        return canvas

    def _encode_jpeg(self, frame_bgr) -> bytes | None:
        if cv2 is None or frame_bgr is None:
            return None
        try:
            ok, buffer = cv2.imencode('.jpg', frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if ok:
                return buffer.tobytes()
        except Exception:
            return None
        return None

    def status_payload(self) -> dict[str, Any]:
        thread = self._thread
        camera_service = self.camera_service
        ready, backend_message = self.detector.backend_ready()
        target = copy.deepcopy(self.control_target)
        return {
            'running': bool(thread and thread.is_alive() and not self._stop_event.is_set()),
            'phase': self.current_phase,
            'detail': self.detail,
            'last_output_summary': self.last_output_summary,
            'last_command': copy.deepcopy(self.last_command),
            'route_text': self.route_text,
            'route_steps': copy.deepcopy(self.route_steps),
            'active_leg_index': self.active_leg_index,
            'active_leg_name': self.active_leg_name,
            'target_found': bool(self.target_found),
            'target_side': self.target_side,
            'car_turn_direction': self.car_turn_direction,
            'mission_state': self.mission_state,
            'held_class_id': self.held_class_id,
            'dropoff_target_class_id': self.dropoff_target_class_id,
            'pickup_target_class_id': self.pickup_target_class_id,
            'pickup_classes': self._pickup_classes(),
            'detections': copy.deepcopy(self.last_detections),
            'target_detection': target,
            'frame': copy.deepcopy(self.last_frame),
            'frame_origin': {
                'x_center': 0,
                'y_center': 0,
                'left_is_negative_x': True,
                'down_is_negative_y': True,
            },
            'events': copy.deepcopy(self.events[-80:]),
            'config': self.get_config(),
            'models': self.list_models(),
            'selected_model': self._selected_model_name(),
            'active_model': self._selected_model_name(),
            'loaded_model': self.loaded_model_name,
            'ai_ready': bool(ready),
            'ai_message': str(self.detector.last_message or backend_message),
            'camera': {
                'running': bool(camera_service is not None),
                'backend': str(getattr(camera_service, 'backend', 'offline')) if camera_service is not None else 'offline',
                'preview_live': bool(getattr(camera_service, 'preview_live', False)) if camera_service is not None else False,
                'fps': float(camera_service.get_fps()) if camera_service is not None else 0.0,
                'error': str(getattr(camera_service, 'last_error', '') or '') if camera_service is not None else '',
            },
            'pipeline': {
                'fps': round(float(self.pipeline_fps), 3),
                'cycle_time_ms': round(float(self.pipeline_cycle_time_ms), 2),
            },
            'arm_sequence': {
                'state': self.arm_sequence_state,
                'last_pose_role': self.arm_last_pose_role,
                'last_pose_number': self.arm_last_pose_number,
                'note': self.arm_sequence_note,
                'target_lock_engaged': bool(self.arm_target_lock_engaged),
            },
            'arm_status': self.arm_service.status(),
            'motor_config': self.motor_service.get_config(),
            'last_error': self.last_error,
            'app_version': APP_VERSION,
        }



def create_mission1_session_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(WEB_DIR / 'templates'),
        static_folder=str(WEB_DIR / 'static'),
    )
    ctx = Mission1SessionContext()
    app.config['mission1_ctx'] = ctx

    @app.route('/')
    def index():
        return render_template('index.html', app_version=APP_VERSION)

    @app.route('/api/status')
    def api_status():
        return jsonify(ctx.status_payload())

    @app.route('/api/frame.jpg')
    def api_frame_jpg():
        frame = ctx.annotated_jpeg
        if frame is None:
            return ('', 204)
        response = Response(frame, mimetype='image/jpeg')
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.route('/api/config', methods=['GET'])
    def api_config_get():
        return jsonify({'ok': True, 'config': ctx.get_config()})

    @app.route('/api/config', methods=['POST'])
    def api_config_save():
        data = request.get_json(silent=True) or {}
        try:
            config = ctx.save_config(data)
        except Exception as exc:
            return jsonify({'ok': False, 'message': f'Failed to save Mission 1 config: {exc}'}), 400
        return jsonify({'ok': True, 'config': config, 'status': ctx.status_payload(), 'message': 'Mission 1 config saved.'})

    @app.route('/api/models', methods=['GET'])
    def api_models_list():
        return jsonify(
            {
                'ok': True,
                'models': ctx.list_models(),
                'selected_model': ctx._selected_model_name(),
                'loaded_model': ctx.loaded_model_name,
            }
        )

    @app.route('/api/models/upload', methods=['POST'])
    def api_models_upload():
        file_storage = request.files.get('model')
        if file_storage is None:
            return jsonify({'ok': False, 'message': 'No model file uploaded.'}), 400
        ok, message = ctx.upload_model(file_storage)
        code = 200 if ok else 400
        return jsonify({'ok': ok, 'message': message, 'status': ctx.status_payload()}), code

    @app.route('/api/model/select', methods=['POST'])
    def api_model_select():
        data = request.get_json(silent=True) or {}
        name = str(data.get('name') or '').strip()
        if not name:
            return jsonify({'ok': False, 'message': 'Model name is required.'}), 400
        ok, message = ctx.select_model(name)
        code = 200 if ok else 400
        return jsonify({'ok': ok, 'message': message, 'status': ctx.status_payload()}), code

    @app.route('/api/arm/load_role', methods=['POST'])
    def api_arm_load_role():
        data = request.get_json(silent=True) or {}
        role = str(data.get('role') or '').strip()
        if not role:
            return jsonify({'ok': False, 'message': 'Arm role is required.', 'status': ctx.status_payload()}), 400
        arm_status = ctx._reload_arm_backend()
        ctx._record(arm_status.get('last_message', 'Mission arm backend refreshed.'), event_type='arm', level='info' if arm_status.get('available') else 'warning')
        ok, message = ctx._load_arm_role_pose(role, reason='manual web load', settle=True)
        code = 200 if ok else 400
        return jsonify({'ok': ok, 'message': message, 'status': ctx.status_payload()}), code

    @app.route('/api/session/start', methods=['POST'])
    def api_session_start():
        data = request.get_json(silent=True) or {}
        ok, message = ctx.start_session(route_text=data.get('route_text'))
        code = 200 if ok else 400
        return jsonify({'ok': ok, 'message': message, 'status': ctx.status_payload()}), code

    @app.route('/api/session/stop', methods=['POST'])
    def api_session_stop():
        ok, message = ctx.stop_session(join=True)
        return jsonify({'ok': ok, 'message': message, 'status': ctx.status_payload()})

    @atexit.register
    def _cleanup() -> None:
        try:
            ctx.close()
        except Exception:
            pass

    return app
