from __future__ import annotations

import atexit
import time
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

from .arm_service import ArmService
from .manual_control_config import load_manual_control_config, save_manual_control_config
from .object_detection_service import ObjectDetectionService
from .project_paths import CUSTOMDRIVE_ROOT, DATA_DIR, PISERVER_ROOT, PISERVER_RUNTIME_PATH, ensure_piserver_import_paths

ensure_piserver_import_paths()

from piserver.algorithms import build_registry  # noqa: E402
from piserver.core.config_store import ConfigStore  # noqa: E402
from piserver.services.camera_service import CameraService  # noqa: E402
from piserver.services.control_service import ControlService  # noqa: E402
from piserver.services.model_service import ModelService  # noqa: E402
from piserver.services.motor_service import MotorService  # noqa: E402
from piserver.services.recorder_service import RecorderService  # noqa: E402

WEB_DIR = Path(__file__).resolve().parent / 'gui_web'
APP_VERSION = '0_2_10'
OD_MODEL_ROOT = CUSTOMDRIVE_ROOT / 'models' / 'object_detection'


def _mjpeg_generator(camera_service: CameraService, detector_service: ObjectDetectionService):
    seq = 0
    while True:
        jpeg_frame, seq = camera_service.wait_for_jpeg(seq, timeout=1.0)
        if jpeg_frame is None:
            time.sleep(0.05)
            continue
        out_jpeg = jpeg_frame
        if detector_service.get_status().get('ready') and detector_service.get_status().get('overlay_enabled'):
            live_frame = camera_service.get_latest_frame(copy=True)
            if live_frame is not None:
                annotated, _ = detector_service.annotate_frame_jpeg(live_frame)
                if annotated is not None:
                    out_jpeg = annotated
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n'
            b'Cache-Control: no-store, no-cache, must-revalidate, max-age=0\r\n'
            b'Pragma: no-cache\r\n\r\n' + out_jpeg + b'\r\n'
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
        self.object_detection_service = ObjectDetectionService(OD_MODEL_ROOT, self.manual_config.get('ai', {}))
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
        self.object_detection_service.apply_runtime_config(self.manual_config.get('ai', {}))
        active_model = self.object_detection_service.get_active_model_name()
        if active_model != 'none' and (OD_MODEL_ROOT / active_model).exists():
            self.object_detection_service.deploy_model(active_model)

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
        payload['ai_status'] = self.object_detection_service.get_status()
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
        'object_detection': ctx.object_detection_service,
    }

    @app.route('/')
    def index():
        return render_template('index.html', app_version=APP_VERSION)

    @app.route('/video_feed')
    def video_feed():
        response = Response(
            _mjpeg_generator(ctx.camera_service, ctx.object_detection_service),
            mimetype='multipart/x-mixed-replace; boundary=frame',
        )
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.route('/api/camera/frame.jpg')
    def api_camera_frame():
        jpeg_frame = ctx.camera_service.get_jpeg_frame()
        if jpeg_frame is None:
            jpeg_frame, _ = ctx.camera_service.wait_for_jpeg(0, timeout=0.35)
        if jpeg_frame is None:
            return ('', 204)
        out_frame = jpeg_frame
        if ctx.object_detection_service.get_status().get('ready') and ctx.object_detection_service.get_status().get('overlay_enabled'):
            live_frame = ctx.camera_service.get_latest_frame(copy=True)
            if live_frame is not None:
                annotated, _ = ctx.object_detection_service.annotate_frame_jpeg(live_frame)
                if annotated is not None:
                    out_frame = annotated
        response = Response(out_frame, mimetype='image/jpeg')
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

    @app.route('/api/ai/status')
    def api_ai_status():
        return jsonify({'ok': True, 'ai_status': ctx.object_detection_service.get_status()})

    @app.route('/api/ai/models')
    def api_ai_models():
        return jsonify({'ok': True, 'models': ctx.object_detection_service.list_models(), 'ai_status': ctx.object_detection_service.get_status()})

    @app.route('/api/ai/upload', methods=['POST'])
    def api_ai_upload():
        files = request.files.getlist('files')
        ok, saved, message = ctx.object_detection_service.save_uploaded_files(files)
        code = 200 if ok else 400
        return jsonify({'ok': ok, 'saved': saved, 'message': message, 'models': ctx.object_detection_service.list_models(), 'ai_status': ctx.object_detection_service.get_status()}), code

    @app.route('/api/ai/delete', methods=['POST'])
    def api_ai_delete():
        data = request.get_json(silent=True) or {}
        model_name = str(data.get('model', '') or '').strip()
        ok, message = ctx.object_detection_service.delete_model_bundle(model_name)
        if ok:
            ctx.save_manual_config({'ai': {'deployed_model': ctx.object_detection_service.get_active_model_name()}})
        code = 200 if ok else 400
        return jsonify({'ok': ok, 'message': message, 'models': ctx.object_detection_service.list_models(), 'ai_status': ctx.object_detection_service.get_status(), 'state': ctx.status_payload()}), code

    @app.route('/api/ai/deploy', methods=['POST'])
    def api_ai_deploy():
        data = request.get_json(silent=True) or {}
        model_name = str(data.get('model', '') or '').strip()
        overrides = {
            'confidence_threshold': data.get('confidence_threshold', 0.25),
            'iou_threshold': data.get('iou_threshold', 0.45),
            'overlay_enabled': data.get('overlay_enabled', True),
            'max_overlay_fps': data.get('max_overlay_fps', 6.0),
        }
        ok, message = ctx.object_detection_service.deploy_model(model_name, overrides)
        if ok:
            ctx.save_manual_config({'ai': {
                'deployed_model': ctx.object_detection_service.get_active_model_name(),
                'confidence_threshold': overrides['confidence_threshold'],
                'iou_threshold': overrides['iou_threshold'],
                'overlay_enabled': overrides['overlay_enabled'],
                'max_overlay_fps': overrides['max_overlay_fps'],
            }})
        code = 200 if ok else 400
        return jsonify({'ok': ok, 'message': message, 'ai_status': ctx.object_detection_service.get_status(), 'state': ctx.status_payload()}), code

    @app.route('/api/ai/config', methods=['POST'])
    def api_ai_config():
        data = request.get_json(silent=True) or {}
        ai_updates = {
            'overlay_enabled': bool(data.get('overlay_enabled', True)),
            'confidence_threshold': float(data.get('confidence_threshold', 0.25)),
            'iou_threshold': float(data.get('iou_threshold', 0.45)),
            'max_overlay_fps': float(data.get('max_overlay_fps', 6.0)),
            'deployed_model': str(data.get('deployed_model', ctx.object_detection_service.get_active_model_name()) or 'none'),
        }
        saved = ctx.save_manual_config({'ai': ai_updates})
        return jsonify({'ok': True, 'message': 'AI settings saved.', 'config': saved.get('ai', {}), 'ai_status': ctx.object_detection_service.get_status(), 'state': ctx.status_payload()})

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
