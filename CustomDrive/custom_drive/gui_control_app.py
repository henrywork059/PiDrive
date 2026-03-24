from __future__ import annotations

import atexit
import time
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

from .arm_service import ArmService
from .manual_control_config import load_manual_control_config, save_manual_control_config
from .project_paths import DATA_DIR, PISERVER_ROOT, PISERVER_RUNTIME_PATH, ensure_piserver_import_paths

ensure_piserver_import_paths()

from piserver.algorithms import build_registry  # noqa: E402
from piserver.core.config_store import ConfigStore  # noqa: E402
from piserver.services.camera_service import CameraService  # noqa: E402
from piserver.services.control_service import ControlService  # noqa: E402
from piserver.services.model_service import ModelService  # noqa: E402
from piserver.services.motor_service import MotorService  # noqa: E402
from piserver.services.recorder_service import RecorderService  # noqa: E402

WEB_DIR = Path(__file__).resolve().parent / 'gui_web'
APP_VERSION = '0_1_16'


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


class GuiControlContext:
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
        self.model_service = ModelService(PISERVER_ROOT / 'models')
        self.recorder_service = RecorderService(DATA_DIR / 'manual_records')
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
        self.arm_service = ArmService(self.manual_config.get('arm', {}))
        self.control_service.start()
        self._apply_defaults()

    def _apply_defaults(self) -> None:
        self.manual_config = load_manual_control_config()
        ui_cfg = self.manual_config.get('ui', {}) if isinstance(self.manual_config, dict) else {}
        default_speed = float(ui_cfg.get('manual_speed', 0.55))
        self.control_service.select_algorithm('manual')
        self.control_service.set_runtime_parameters(current_page='manual', max_throttle=default_speed)
        self.camera_service.set_preview_enabled(bool(ui_cfg.get('show_camera', True)))
        self.arm_service.reload(self.manual_config.get('arm', {}))

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
        try:
            self.arm_service.shutdown()
        except Exception:
            pass

    def get_manual_config(self) -> dict[str, Any]:
        return load_manual_control_config()

    def save_manual_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        current = self.get_manual_config()
        merged = current
        for key, value in (updates or {}).items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = {**merged.get(key, {}), **value}
            else:
                merged[key] = value
        saved = save_manual_control_config(merged)
        self.manual_config = saved
        self._apply_defaults()
        return saved

    def status_payload(self) -> dict[str, Any]:
        payload = self.control_service.snapshot()
        payload['manual_config'] = self.get_manual_config()
        payload['runtime_config_path'] = str(PISERVER_RUNTIME_PATH)
        payload['motor_config'] = self.motor_service.get_config()
        payload['camera_config'] = self.camera_service.get_config()
        payload['arm_status'] = self.arm_service.status()
        payload['app'] = 'gui_control'
        return payload



def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(WEB_DIR / 'templates'),
        static_folder=str(WEB_DIR / 'static'),
    )

    ctx = GuiControlContext()
    app.config['gui_ctx'] = ctx
    app.config['services'] = {
        'camera': ctx.camera_service,
        'motor': ctx.motor_service,
        'model': ctx.model_service,
        'recorder': ctx.recorder_service,
        'control': ctx.control_service,
        'algorithms': ctx.algorithms,
        'arm': ctx.arm_service,
    }

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

    @app.route('/api/camera/preview_state', methods=['POST'])
    def api_camera_preview_state():
        data = request.get_json(silent=True) or {}
        enabled = bool(data.get('enabled', True))
        ctx.camera_service.set_preview_enabled(enabled)
        return jsonify({'ok': True, 'enabled': enabled, 'config': ctx.camera_service.get_config(), 'state': ctx.status_payload()})

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
            steer_bias=data.get('steer_bias'),
            current_page='manual',
        )
        ctx.control_service.select_algorithm('manual')
        if not ok_controls:
            return jsonify({'ok': False, 'message': msg_controls, 'state': ctx.status_payload()}), 400
        if not ok_runtime:
            return jsonify({'ok': False, 'message': msg_runtime, 'state': ctx.status_payload()}), 400
        return jsonify({'ok': True, 'state': ctx.status_payload()})

    @app.route('/api/system/estop', methods=['POST'])
    def api_estop():
        data = request.get_json(silent=True) or {}
        enabled = bool(data.get('enabled', True))
        ctx.control_service.set_safety_stop(enabled)
        if enabled:
            ctx.motor_service.stop()
        return jsonify({'ok': True, 'state': ctx.status_payload()})

    @app.route('/api/motor/config')
    def api_motor_config():
        return jsonify({'ok': True, 'config': ctx.motor_service.get_config()})

    @app.route('/api/motor/apply', methods=['POST'])
    def api_motor_apply():
        data = request.get_json(silent=True) or {}
        try:
            config = ctx.motor_service.apply_settings(data)
            ctx.control_service.invalidate_processing_state_cache()
        except Exception as exc:
            return jsonify({'ok': False, 'message': f'Motor settings failed: {exc}'}), 400
        saved = False
        save_error = ''
        try:
            ctx.config_store.save(ctx.control_service.get_runtime_config())
            saved = True
        except Exception as exc:
            save_error = str(exc)
        message = 'Drive settings applied. Motors stopped for safety.'
        if saved:
            message += ' Settings saved.'
        elif save_error:
            message += f' Settings were not saved: {save_error}'
        return jsonify({'ok': True, 'saved': saved, 'message': message, 'config': config, 'state': ctx.status_payload()})

    @app.route('/api/arm/action', methods=['POST'])
    def api_arm_action():
        data = request.get_json(silent=True) or {}
        action = str(data.get('action', '') or '').strip().lower()
        if not action:
            return jsonify({'ok': False, 'message': 'No arm action provided.', 'arm_status': ctx.arm_service.status()}), 400
        ok, message = ctx.arm_service.perform_action(action)
        code = 200 if ok else 400
        return jsonify({'ok': ok, 'message': message, 'arm_status': ctx.arm_service.status(), 'state': ctx.status_payload()}), code

    @app.route('/api/manual-config', methods=['GET'])
    def api_manual_config_get():
        return jsonify({'ok': True, 'config': ctx.get_manual_config()})

    @app.route('/api/manual-config', methods=['POST'])
    def api_manual_config_save():
        data = request.get_json(silent=True) or {}
        try:
            saved = ctx.save_manual_config(data)
        except Exception as exc:
            return jsonify({'ok': False, 'message': f'Failed to save CustomDrive GUI config: {exc}'}), 400
        return jsonify({'ok': True, 'message': 'CustomDrive GUI config saved.', 'config': saved, 'state': ctx.status_payload()})

    @atexit.register
    def _cleanup() -> None:
        ctx.close()

    return app
