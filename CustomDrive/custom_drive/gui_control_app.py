from __future__ import annotations

import atexit
import time
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

from .project_paths import CUSTOMDRIVE_ROOT, PISERVER_ROOT, PISERVER_RUNTIME_PATH, ensure_piserver_import_paths

APP_VERSION = '0_1_14'
WEB_DIR = Path(__file__).resolve().parent / 'gui_web'


def mjpeg_generator(camera_service):
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


def create_app() -> Flask:
    ensure_piserver_import_paths()
    from piserver.algorithms import build_registry  # noqa: WPS433,E402
    from piserver.core.config_store import ConfigStore  # noqa: WPS433,E402
    from piserver.services.camera_service import CameraService  # noqa: WPS433,E402
    from piserver.services.control_service import ControlService  # noqa: WPS433,E402
    from piserver.services.model_service import ModelService  # noqa: WPS433,E402
    from piserver.services.motor_service import MotorService  # noqa: WPS433,E402
    from piserver.services.recorder_service import RecorderService  # noqa: WPS433,E402

    app = Flask(
        __name__,
        template_folder=str(WEB_DIR / 'templates'),
        static_folder=str(WEB_DIR / 'static'),
    )

    config_store = ConfigStore(PISERVER_RUNTIME_PATH)
    initial_runtime = config_store.load()
    if not isinstance(initial_runtime, dict):
        initial_runtime = {}

    camera_service = CameraService()
    camera_cfg = initial_runtime.get('camera')
    if isinstance(camera_cfg, dict):
        camera_service.apply_settings(camera_cfg, restart=False)
    camera_service.start()

    motor_service = MotorService()
    motor_cfg = initial_runtime.get('motor')
    if isinstance(motor_cfg, dict):
        motor_service.apply_settings(motor_cfg)

    model_service = ModelService(PISERVER_ROOT / 'models')
    recorder_service = RecorderService(CUSTOMDRIVE_ROOT / 'data' / 'records')
    algorithms = build_registry()
    control_service = ControlService(
        camera_service=camera_service,
        motor_service=motor_service,
        model_service=model_service,
        recorder_service=recorder_service,
        algorithms=algorithms,
        config_store=config_store,
        loop_hz=20,
    )
    control_service.select_algorithm('manual')
    control_service.set_runtime_parameters(current_page='manual')
    control_service.start()

    app.config['services'] = {
        'camera': camera_service,
        'motor': motor_service,
        'model': model_service,
        'recorder': recorder_service,
        'control': control_service,
        'algorithms': algorithms,
        'config_store': config_store,
    }

    def cleanup_services() -> None:
        try:
            control_service.stop()
        except Exception:
            pass
        try:
            camera_service.stop()
        except Exception:
            pass
        try:
            motor_service.close()
        except Exception:
            pass

    atexit.register(cleanup_services)

    def status_payload() -> dict[str, Any]:
        state = control_service.snapshot()
        camera_config = camera_service.get_config()
        return {
            'ok': True,
            'app_version': APP_VERSION,
            'title': 'CustomDrive GUI Control',
            'message': str(state.get('system_message', 'Ready') or 'Ready'),
            'state': state,
            'camera': {
                'preview_enabled': bool(camera_config.get('preview_enabled', True)),
                'preview_live': bool(camera_config.get('preview_live', state.get('camera_preview_live', False))),
                'backend': str(state.get('camera_backend', camera_config.get('backend', 'unknown')) or 'unknown'),
                'width': int(state.get('camera_width', camera_config.get('width', 0)) or 0),
                'height': int(state.get('camera_height', camera_config.get('height', 0)) or 0),
                'fps': float(state.get('fps', 0.0) or 0.0),
                'last_error': str(state.get('camera_error', camera_config.get('last_error', '')) or ''),
            },
            'motor': motor_service.get_config(),
            'timestamp': time.time(),
        }

    @app.route('/')
    def index():
        return render_template('index.html', app_version=APP_VERSION)

    @app.route('/video_feed')
    def video_feed():
        response = Response(
            mjpeg_generator(camera_service),
            mimetype='multipart/x-mixed-replace; boundary=frame',
        )
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.route('/api/status')
    def api_status():
        return jsonify(status_payload())

    @app.route('/api/camera/preview_state', methods=['POST'])
    def api_camera_preview_state():
        data = request.get_json(silent=True) or {}
        enabled = bool(data.get('enabled', True))
        camera_service.set_preview_enabled(enabled)
        return jsonify({'ok': True, 'enabled': enabled, 'status': status_payload()})

    @app.route('/api/control', methods=['POST'])
    def api_control():
        data = request.get_json(silent=True) or {}
        control_service.select_algorithm('manual')
        if 'safety_stop' in data:
            control_service.set_safety_stop(bool(data.get('safety_stop')))
        ok_controls, msg_controls = control_service.set_manual_controls(
            steering=data.get('steering'),
            throttle=data.get('throttle'),
        )
        ok_runtime, msg_runtime = control_service.set_runtime_parameters(
            max_throttle=data.get('max_throttle'),
            steer_mix=data.get('steer_mix'),
            steer_bias=data.get('steer_bias'),
            current_page='manual',
        )
        if not ok_controls:
            return jsonify({'ok': False, 'message': msg_controls, 'status': status_payload()}), 400
        if not ok_runtime:
            return jsonify({'ok': False, 'message': msg_runtime, 'status': status_payload()}), 400
        return jsonify(status_payload())

    @app.route('/api/safety_stop', methods=['POST'])
    def api_safety_stop():
        data = request.get_json(silent=True) or {}
        enabled = bool(data.get('enabled', True))
        control_service.set_safety_stop(enabled)
        return jsonify({'ok': True, 'enabled': enabled, 'status': status_payload()})

    @app.route('/api/runtime/save', methods=['POST'])
    def api_runtime_save():
        control_service.save_runtime_config()
        return jsonify({'ok': True, 'status': status_payload()})

    return app
