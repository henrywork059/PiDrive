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

from .debug_tools import append_event, clamp_float, clamp_int
from .mission1_tflite_detector import Mission1TFLiteDetector
from .models import Detection
from .project_paths import CONFIG_DIR, CUSTOMDRIVE_ROOT, PISERVER_RUNTIME_PATH, ensure_piserver_import_paths

ensure_piserver_import_paths()

from piserver.core.config_store import ConfigStore  # noqa: E402
from piserver.services.camera_service import CameraService  # noqa: E402
from piserver.services.motor_service import MotorService  # noqa: E402

WEB_DIR = Path(__file__).resolve().parent / 'mission1_web'
APP_VERSION = '0_4_6'
MISSION1_CONFIG_PATH = CONFIG_DIR / 'mission1_session.json'
MISSION1_MODEL_DIR = CUSTOMDRIVE_ROOT / 'models' / 'mission1'

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
    'ai': {
        'active_model': '',
    },
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
    server = merged.get('server') or {}
    session = merged.get('session') or {}
    drive = merged.get('drive') or {}
    camera = merged.get('camera') or {}
    ai = merged.get('ai') or {}

    merged['server'] = {
        'host': str(server.get('host', '0.0.0.0') or '0.0.0.0').strip() or '0.0.0.0',
        'port': clamp_int(server.get('port', 5050), 5050, 1, 65535),
        'refresh_ms': clamp_int(server.get('refresh_ms', 200), 200, 50, 5000),
    }
    merged['session'] = {
        'route_text': str(session.get('route_text', DEFAULT_MISSION1_CONFIG['session']['route_text']) or '').strip(),
        'target_class_id': clamp_int(session.get('target_class_id', 1), 1, 0, 9999),
        'confidence_threshold': round(clamp_float(session.get('confidence_threshold', 0.25), 0.25, 0.01, 0.99), 3),
        'iou_threshold': round(clamp_float(session.get('iou_threshold', 0.45), 0.45, 0.01, 0.99), 3),
        'loop_tick_s': round(clamp_float(session.get('loop_tick_s', 0.08), 0.08, 0.02, 1.0), 3),
    }
    merged['drive'] = {
        'steer_mix': round(clamp_float(drive.get('steer_mix', 0.75), 0.75, 0.0, 1.0), 3),
        'align_kp': round(clamp_float(drive.get('align_kp', 1.0), 1.0, 0.1, 4.0), 3),
        'max_steering': round(clamp_float(drive.get('max_steering', 0.85), 0.85, 0.05, 1.0), 3),
        'center_tolerance_ratio': round(clamp_float(drive.get('center_tolerance_ratio', 0.1), 0.1, 0.01, 0.5), 3),
        'approach_speed': round(clamp_float(drive.get('approach_speed', 0.2), 0.2, 0.0, 1.0), 3),
        'target_reached_bottom_ratio': round(clamp_float(drive.get('target_reached_bottom_ratio', 0.85), 0.85, 0.1, 0.99), 3),
    }
    merged['camera'] = {
        'start_after_route': bool(camera.get('start_after_route', True)),
        'preview_enabled': bool(camera.get('preview_enabled', True)),
        'processing_enabled': bool(camera.get('processing_enabled', True)),
    }
    merged['ai'] = {
        'active_model': str(ai.get('active_model', '') or '').strip(),
    }
    return merged


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
            steps.append({'flag': flag, 'name': 'forward', 'duration_s': duration, 'steering': 0.0, 'throttle': 0.22})
        elif flag == '--backward':
            steps.append({'flag': flag, 'name': 'backward', 'duration_s': duration, 'steering': 0.0, 'throttle': -0.18})
        elif flag == '--turn-right':
            steps.append({'flag': flag, 'name': 'turn-right', 'duration_s': duration, 'steering': 0.9, 'throttle': 0.0})
        elif flag == '--turn-left':
            steps.append({'flag': flag, 'name': 'turn-left', 'duration_s': duration, 'steering': -0.9, 'throttle': 0.0})
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
        self.events: list[dict[str, Any]] = []
        self.current_phase = 'idle'
        self.detail = 'Mission 1 session ready.'
        self.last_command = {'steering': 0.0, 'throttle': 0.0, 'note': 'idle'}
        self.last_detections: list[Detection] = []
        self.last_frame = {'width': 640, 'height': 360}
        self.route_steps: list[dict[str, Any]] = []
        self.route_text = str(self.config.get('session', {}).get('route_text', '') or '')
        self.active_leg_index = -1
        self.active_leg_name = ''
        self.target_found = False
        self.last_error = ''
        self.started_at = 0.0
        self._apply_motor_defaults()
        active_model = str(self.config.get('ai', {}).get('active_model', '') or '').strip()
        if active_model:
            ok, message = self.detector.load_model(active_model)
            self._record(message, event_type='model', level='info' if ok else 'warning')
        else:
            ready, message = self.detector.backend_ready()
            self._record(message, event_type='model', level='info' if ready else 'warning')

    def _record(self, message: str, *, level: str = 'info', event_type: str = 'runtime', **fields: Any) -> None:
        append_event(self.events, message, level=level, event_type=event_type, limit=200, **fields)

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

    def get_config(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self.config)

    def save_config(self, updates: dict[str, Any] | None) -> dict[str, Any]:
        with self._lock:
            self.config = save_mission1_config(_deep_merge(self.config, updates or {}))
            self.route_text = str(self.config.get('session', {}).get('route_text', '') or '')
            return copy.deepcopy(self.config)

    def list_models(self) -> list[str]:
        return self.detector.list_models()

    def upload_model(self, file_storage) -> tuple[bool, str]:
        ok, message = self.detector.save_uploaded_model(file_storage)
        self._record(message, event_type='model', level='info' if ok else 'warning')
        if ok:
            self.save_config({'ai': {'active_model': message}})
            loaded, load_message = self.detector.load_model(message)
            self._record(load_message, event_type='model', level='info' if loaded else 'warning')
            if loaded:
                return True, load_message
            return False, load_message
        return ok, message

    def select_model(self, name: str) -> tuple[bool, str]:
        ok, message = self.detector.load_model(name)
        self._record(message, event_type='model', level='info' if ok else 'warning')
        if ok:
            self.save_config({'ai': {'active_model': str(name or '').strip()}})
        return ok, message

    def start_session(self, route_text: str | None = None) -> tuple[bool, str]:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return False, 'Mission 1 session is already running.'
        session_cfg = self.get_config().get('session', {})
        route_text = str(route_text or session_cfg.get('route_text', '') or '').strip()
        try:
            steps = parse_route_text(route_text)
        except Exception as exc:
            return False, str(exc)

        active_model = self.detector.get_active_name()
        if active_model == 'none':
            configured_model = str(self.get_config().get('ai', {}).get('active_model', '') or '').strip()
            if configured_model:
                ok, message = self.select_model(configured_model)
                if not ok:
                    return False, message
            else:
                return False, 'No active AI model selected.'

        self.stop_session(join=True)
        with self._lock:
            self.route_text = route_text
            self.route_steps = copy.deepcopy(steps)
            self.active_leg_index = -1
            self.active_leg_name = ''
            self.current_phase = 'route_pending'
            self.detail = 'Mission 1 route queued.'
            self.last_command = {'steering': 0.0, 'throttle': 0.0, 'note': 'queued'}
            self.last_detections = []
            self.target_found = False
            self.last_error = ''
            self.started_at = time.monotonic()
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_session, name='mission1-session', daemon=True)
            self._thread.start()
        self.save_config({'session': {'route_text': route_text}})
        self._record('Mission 1 session started.', event_type='session', route_text=route_text)
        return True, 'Mission 1 session started.'

    def stop_session(self, join: bool = True) -> tuple[bool, str]:
        self._stop_event.set()
        thread = self._thread
        if join and thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        self._thread = None
        try:
            self.motor_service.stop()
        except Exception:
            pass
        self._shutdown_camera()
        if self.current_phase not in {'idle', 'complete', 'stopped', 'failed'}:
            self.current_phase = 'stopped'
            self.detail = 'Mission 1 session stopped.'
            self.last_command = {'steering': 0.0, 'throttle': 0.0, 'note': 'stopped'}
        return True, 'Mission 1 session stopped.'

    def _set_drive(self, steering: float, throttle: float, note: str) -> None:
        drive_cfg = self.get_config().get('drive', {})
        steer_mix = float(drive_cfg.get('steer_mix', 0.75))
        self.motor_service.update(steering=steering, throttle=throttle, steer_mix=steer_mix)
        self.last_command = {'steering': float(steering), 'throttle': float(throttle), 'note': str(note)}

    def _run_session(self) -> None:
        try:
            self._run_start_route()
            if self._stop_event.is_set():
                return
            self._run_ai_phase()
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
            if self._stop_event.is_set() and self.current_phase not in {'complete', 'failed'}:
                self.current_phase = 'stopped'
                self.detail = 'Mission 1 session stopped.'
                self.last_command = {'steering': 0.0, 'throttle': 0.0, 'note': 'stopped'}
            self._thread = None

    def _run_start_route(self) -> None:
        self.current_phase = 'start_route'
        for index, step in enumerate(self.route_steps):
            if self._stop_event.is_set():
                return
            self.active_leg_index = index
            self.active_leg_name = str(step.get('name', ''))
            self.detail = f"Running route step {index + 1}/{len(self.route_steps)}: {self.active_leg_name}"
            self._record(self.detail, event_type='route', duration_s=float(step.get('duration_s', 0.0)))
            deadline = time.monotonic() + float(step.get('duration_s', 0.0))
            while time.monotonic() < deadline and not self._stop_event.is_set():
                self._set_drive(float(step.get('steering', 0.0)), float(step.get('throttle', 0.0)), self.active_leg_name)
                time.sleep(0.05)
        self.motor_service.stop()
        self.active_leg_name = ''
        self.active_leg_index = -1
        self.detail = 'Start route complete. Turning on camera and deploying AI model.'
        self._record(self.detail, event_type='route')

    def _run_ai_phase(self) -> None:
        self.current_phase = 'ai_boot'
        ready, message = self.detector.backend_ready()
        if not ready:
            raise RuntimeError(message)
        if self.detector.get_active_name() == 'none':
            raise RuntimeError('No active AI model selected.')
        ok, camera_message = self._ensure_camera_started()
        if not ok:
            raise RuntimeError(camera_message)
        self._record(camera_message, event_type='camera')

        self.current_phase = 'ai_tracking'
        session_cfg = self.get_config().get('session', {})
        drive_cfg = self.get_config().get('drive', {})
        target_class_id = int(session_cfg.get('target_class_id', 1))
        target_label = str(target_class_id)
        confidence_threshold = float(session_cfg.get('confidence_threshold', 0.25))
        iou_threshold = float(session_cfg.get('iou_threshold', 0.45))
        tick_s = float(session_cfg.get('loop_tick_s', 0.08))
        align_kp = float(drive_cfg.get('align_kp', 1.0))
        max_steering = float(drive_cfg.get('max_steering', 0.85))
        center_tolerance = float(drive_cfg.get('center_tolerance_ratio', 0.1))
        approach_speed = float(drive_cfg.get('approach_speed', 0.2))
        target_reached_bottom_ratio = float(drive_cfg.get('target_reached_bottom_ratio', 0.85))

        while not self._stop_event.is_set():
            camera_service = self.camera_service
            if camera_service is None:
                raise RuntimeError('Camera service is not available.')
            frame = camera_service.get_latest_frame(copy=True)
            if frame is None:
                self.target_found = False
                self.last_detections = []
                self.detail = 'Waiting for camera frame.'
                time.sleep(tick_s)
                continue
            frame_h = int(getattr(frame, 'shape', (360, 640, 3))[0] or 360)
            frame_w = int(getattr(frame, 'shape', (360, 640, 3))[1] or 640)
            self.last_frame = {'width': frame_w, 'height': frame_h}
            detections = self.detector.detect(frame, conf_threshold=confidence_threshold, iou_threshold=iou_threshold)
            self.last_detections = detections
            target = self._best_target_detection(detections, target_label)
            if target is None:
                self.target_found = False
                self.motor_service.stop()
                self.last_command = {'steering': 0.0, 'throttle': 0.0, 'note': 'waiting for class 1'}
                self.detail = f'AI running. Waiting for class {target_class_id}.'
                time.sleep(tick_s)
                continue

            self.target_found = True
            error_ratio = self._x_error_ratio(target, frame_w)
            bottom_ratio = target.box.bottom_center_y / max(1.0, float(frame_h))
            # Positive x error means the target is to the right side of the frame.
            # MotorService's differential-drive mixing expects negative steering for a rightward arc,
            # so invert the image-space error when generating steering.
            steering = max(-max_steering, min(max_steering, -error_ratio * align_kp))

            # Keep moving toward the target while steering instead of stopping whenever the target is off-centre.
            # Slow down a little during larger heading corrections, but keep forward motion active.
            if abs(error_ratio) > center_tolerance:
                throttle = max(0.08, approach_speed * 0.55)
            else:
                throttle = approach_speed

            if bottom_ratio >= target_reached_bottom_ratio:
                self.motor_service.stop()
                self.current_phase = 'complete'
                self.detail = f'Class {target_class_id} reached.'
                self.last_command = {'steering': 0.0, 'throttle': 0.0, 'note': 'target reached'}
                self._record(self.detail, event_type='session', confidence=round(float(target.confidence), 3))
                return

            self._set_drive(steering, throttle, f'class {target_class_id} tracking')
            self.detail = (
                f'Class {target_class_id} detected at {target.confidence:.2f}. '
                f'x_err={error_ratio:+.3f} bottom={bottom_ratio:.3f}'
            )
            time.sleep(tick_s)

    def _best_target_detection(self, detections: list[Detection], target_label: str) -> Detection | None:
        matches = [det for det in detections if str(det.label).strip() == target_label]
        if not matches:
            return None
        return max(matches, key=lambda det: float(det.confidence) * max(1.0, det.box.area))

    def _x_error_ratio(self, det: Detection, frame_width: int) -> float:
        frame_center_x = float(frame_width) * 0.5
        x_err = float(det.box.bottom_center_x) - frame_center_x
        return x_err / max(1.0, frame_center_x)

    def status_payload(self) -> dict[str, Any]:
        thread = self._thread
        camera_service = self.camera_service
        ready, backend_message = self.detector.backend_ready()
        return {
            'running': bool(thread and thread.is_alive() and not self._stop_event.is_set()),
            'phase': self.current_phase,
            'detail': self.detail,
            'last_command': copy.deepcopy(self.last_command),
            'route_text': self.route_text,
            'route_steps': copy.deepcopy(self.route_steps),
            'active_leg_index': self.active_leg_index,
            'active_leg_name': self.active_leg_name,
            'target_found': bool(self.target_found),
            'detections': [
                {
                    'label': det.label,
                    'confidence': det.confidence,
                    'box': {
                        'x1': det.box.x1,
                        'y1': det.box.y1,
                        'x2': det.box.x2,
                        'y2': det.box.y2,
                    },
                }
                for det in self.last_detections
            ],
            'frame': copy.deepcopy(self.last_frame),
            'events': copy.deepcopy(self.events[-60:]),
            'config': self.get_config(),
            'models': self.list_models(),
            'active_model': self.detector.get_active_name(),
            'ai_ready': bool(ready),
            'ai_message': str(self.detector.last_message or backend_message),
            'camera': {
                'running': bool(camera_service is not None),
                'backend': str(getattr(camera_service, 'backend', 'offline')) if camera_service is not None else 'offline',
                'preview_live': bool(getattr(camera_service, 'preview_live', False)) if camera_service is not None else False,
                'fps': float(camera_service.get_fps()) if camera_service is not None else 0.0,
                'error': str(getattr(camera_service, 'last_error', '') or '') if camera_service is not None else '',
            },
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
        camera_service = ctx.camera_service
        if camera_service is None:
            return ('', 204)
        frame = camera_service.get_jpeg_frame()
        if frame is None:
            frame, _ = camera_service.wait_for_jpeg(0, timeout=0.25)
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
        return jsonify({'ok': True, 'models': ctx.list_models(), 'active_model': ctx.detector.get_active_name()})

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
