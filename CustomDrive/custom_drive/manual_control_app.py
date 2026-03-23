from __future__ import annotations

import atexit
import time
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

from .debug_tools import clamp_float
from .manual_control_config import load_manual_control_config, save_manual_control_config
from .project_paths import CUSTOMDRIVE_ROOT, DATA_DIR, PISERVER_ROOT, PISERVER_RUNTIME_PATH, ensure_piserver_import_paths

ensure_piserver_import_paths()

from piserver.algorithms import build_registry  # noqa: E402
from piserver.core.config_store import ConfigStore  # noqa: E402
from piserver.services.camera_service import CameraService  # noqa: E402
from piserver.services.control_service import ControlService  # noqa: E402
from piserver.services.model_service import ModelService  # noqa: E402
from piserver.services.motor_service import MotorService  # noqa: E402
from piserver.services.recorder_service import RecorderService  # noqa: E402

WEB_DIR = Path(__file__).resolve().parent / 'manual_web'
APP_VERSION = '0_1_4'



def _mjpeg_generator(camera_service: CameraService):
    seq = 0
    while True:
        frame, seq = camera_service.wait_for_jpeg(seq, timeout=1.0)
        if frame is None:
            time.sleep(0.05)
            continue
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n'
            b'Cache-Control: no-store, no-cache, must-revalidate, max-age=0\r\n'
            b'Pragma: no-cache\r\n\r\n' + frame + b'\r\n'
        )


def _deep_merge(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in (incoming or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


class ManualControlContext:
    def __init__(self) -> None:
        self.config_store = ConfigStore(PISERVER_RUNTIME_PATH)
        self.manual_config = load_manual_control_config()
        initial_runtime = self.config_store.load()

        self.camera_service = CameraService()
        camera_cfg = initial_runtime.get('camera') if isinstance(initial_runtime, dict) else None
        if isinstance(camera_cfg, dict):
            self.camera_service.apply_settings(camera_cfg, restart=False)
        self.camera_service.start()

        self.motor_service = MotorService()
        model_root = PISERVER_ROOT / 'models'
        record_root = DATA_DIR / 'manual_records'
        self.model_service = ModelService(model_root)
        self.recorder_service = RecorderService(record_root)
        self.algorithms = build_registry()
        self.control_service = ControlService(
            camera_service=self.camera_service,
            motor_service=self.motor_service,
            model_service=self.model_service,
            recorder_service=self.recorder_service,
            algorithms=self.algorithms,
            config_store=self.config_store,
            loop_hz=20,
        )
        self.control_service.start()
        self.control_service.select_algorithm('manual')
        self.control_service.set_runtime_parameters(current_page='manual')

        default_speed = float(self.manual_config.get('ui', {}).get('manual_speed', 0.55))
        self.control_service.set_runtime_parameters(max_throttle=default_speed)
        self.camera_service.set_preview_enabled(bool(self.manual_config.get('ui', {}).get('show_camera', True)))

    def close(self) -> None:
        try:
            self.control_service.stop()
        except Exception:
            pass
        try:
            self.camera_service.stop()
        except Exception:
            pass
        try:
            self.motor_service.close()
        except Exception:
            pass

    def get_manual_config(self) -> dict[str, Any]:
        return load_manual_control_config()

    def save_manual_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        merged = _deep_merge(self.get_manual_config(), updates or {})
        saved = save_manual_control_config(merged)
        self.manual_config = saved
        manual_speed = float(saved.get('ui', {}).get('manual_speed', 0.55))
        self.control_service.set_runtime_parameters(max_throttle=manual_speed)
        self.camera_service.set_preview_enabled(bool(saved.get('ui', {}).get('show_camera', True)))
        return saved

    def status_payload(self) -> dict[str, Any]:
        payload = self.control_service.snapshot()
        payload['manual_config'] = self.get_manual_config()
        payload['recorder_sessions'] = self.recorder_service.list_sessions()
        payload['runtime_config_path'] = str(PISERVER_RUNTIME_PATH)
        payload['competition_mode'] = True
        payload['motor_config'] = self.motor_service.get_config()
        payload['camera_config'] = self.camera_service.get_config()
        return payload



def create_manual_control_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(WEB_DIR / 'templates'),
        static_folder=str(WEB_DIR / 'static'),
    )

    ctx = ManualControlContext()
    app.config['manual_ctx'] = ctx

    @app.route('/')
    def index():
        return render_template('index.html', app_version=APP_VERSION)

    @app.route('/video_feed')
    def video_feed():
        response = Response(
            _mjpeg_generator(ctx.camera_service),
            mimetype='multipart/x-mixed-replace; boundary=frame',
        )
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.route('/api/camera/frame.jpg')
    def api_camera_frame():
        frame = ctx.camera_service.get_jpeg_frame()
        if frame is None:
            frame, _ = ctx.camera_service.wait_for_jpeg(0, timeout=0.35)
        if frame is None:
            return ('', 204)
        response = Response(frame, mimetype='image/jpeg')
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.route('/api/status')
    def api_status():
        return jsonify(ctx.status_payload())

    @app.route('/api/control', methods=['POST'])
    def api_control():
        data = request.get_json(silent=True) or {}
        ok_controls, msg_controls = ctx.control_service.set_manual_controls(
            steering=data.get('steering'),
            throttle=data.get('throttle'),
        )
        ok_runtime, msg_runtime = ctx.control_service.set_runtime_parameters(
            max_throttle=data.get('max_throttle'),
            steer_mix=data.get('steer_mix'),
            current_page='manual',
        )
        ok_algo, msg_algo = ctx.control_service.select_algorithm('manual')
        if not (ok_controls and ok_runtime and ok_algo):
            message = msg_controls if not ok_controls else msg_runtime if not ok_runtime else msg_algo
            return jsonify({'ok': False, 'message': message, 'state': ctx.status_payload()}), 400
        return jsonify({'ok': True, 'state': ctx.status_payload()})

    @app.route('/api/record/toggle', methods=['POST'])
    def api_record_toggle():
        ok, recording, message = ctx.control_service.toggle_recording()
        code = 200 if ok else 423
        return jsonify({'ok': ok, 'recording': recording, 'message': message, 'state': ctx.status_payload()}), code

    @app.route('/api/system/estop', methods=['POST'])
    def api_estop():
        data = request.get_json(silent=True) or {}
        enabled = bool(data.get('enabled', True))
        ctx.control_service.set_safety_stop(enabled)
        if enabled:
            ctx.motor_service.stop()
        return jsonify({'ok': True, 'state': ctx.status_payload()})

    @app.route('/api/manual/config', methods=['GET'])
    def api_manual_config_get():
        return jsonify({'ok': True, 'config': ctx.get_manual_config()})

    @app.route('/api/manual/config', methods=['POST'])
    def api_manual_config_save():
        data = request.get_json(silent=True) or {}
        try:
            saved = ctx.save_manual_config(data)
        except Exception as exc:
            return jsonify({'ok': False, 'message': f'Failed to save manual control config: {exc}'}), 400
        return jsonify({'ok': True, 'config': saved, 'state': ctx.status_payload(), 'message': 'Manual control settings saved.'})

    @app.route('/api/config/save', methods=['POST'])
    def api_config_save():
        config = ctx.control_service.save_runtime_config()
        return jsonify({'ok': True, 'config': config, 'message': 'PiServer runtime config saved.', 'state': ctx.status_payload()})

    @app.route('/api/config/reload', methods=['POST'])
    def api_config_reload():
        config = ctx.control_service.reload_runtime_config()
        ctx.control_service.select_algorithm('manual')
        ctx.control_service.set_runtime_parameters(current_page='manual')
        manual_speed = float(ctx.get_manual_config().get('ui', {}).get('manual_speed', 0.55))
        ctx.control_service.set_runtime_parameters(max_throttle=manual_speed)
        return jsonify({'ok': True, 'config': config, 'message': 'PiServer runtime config reloaded.', 'state': ctx.status_payload()})

    @app.route('/api/camera/preview_state', methods=['POST'])
    def api_camera_preview_state():
        data = request.get_json(silent=True) or {}
        enabled = bool(data.get('enabled', True))
        ctx.camera_service.set_preview_enabled(enabled)
        return jsonify({'ok': True, 'enabled': enabled, 'config': ctx.camera_service.get_config(), 'state': ctx.status_payload()})

    @app.route('/api/camera/config')
    def api_camera_config():
        return jsonify({'ok': True, 'config': ctx.camera_service.get_config()})

    @app.route('/api/motor/config')
    def api_motor_config():
        return jsonify({'ok': True, 'config': ctx.motor_service.get_config()})

    @atexit.register
    def _cleanup() -> None:
        ctx.close()

    return app
