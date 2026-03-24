from __future__ import annotations

import atexit
import time
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

from .project_paths import CUSTOMDRIVE_ROOT, PISERVER_RUNTIME_PATH, ensure_piserver_import_paths

APP_VERSION = '0_1_12'
WEB_DIR = Path(__file__).resolve().parent / 'gui_web'


def create_app() -> Flask:
    ensure_piserver_import_paths()
    from piserver.core.config_store import ConfigStore  # noqa: WPS433,E402
    from piserver.services.camera_service import CameraService  # noqa: WPS433,E402

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

    app.config['services'] = {
        'camera': camera_service,
        'config_store': config_store,
    }

    def snapshot() -> dict[str, Any]:
        camera_config = camera_service.get_config()
        frame = camera_service.get_latest_frame(copy=False)
        frame_live = bool(frame is not None)
        backend = str(camera_config.get('backend', 'unknown') or 'unknown')
        last_error = str(camera_config.get('last_error', '') or '')
        return {
            'ok': True,
            'app_version': APP_VERSION,
            'gui': {
                'page': 'control',
                'title': 'CustomDrive GUI Control',
                'mode_selection_enabled': False,
            },
            'camera': {
                'live': frame_live,
                'backend': backend,
                'backend_format': str(camera_config.get('backend_format', 'unknown') or 'unknown'),
                'width': int(camera_config.get('width', 0) or 0),
                'height': int(camera_config.get('height', 0) or 0),
                'fps': int(camera_config.get('fps', 0) or 0),
                'preview_enabled': bool(camera_config.get('preview_enabled', True)),
                'preview_live': bool(camera_config.get('preview_live', frame_live)),
                'stream_quality': str(camera_config.get('stream_quality', 'balanced') or 'balanced'),
                'last_error': last_error,
            },
            'panels': {
                'viewer': 'live',
                'drive': 'empty',
                'system': 'empty',
            },
            'message': 'CustomDrive GUI shell ready.' if not last_error else last_error,
            'timestamp': time.time(),
        }

    @app.route('/')
    def index():
        return render_template('index.html', app_version=APP_VERSION)

    @app.route('/settings')
    def settings():
        return render_template('settings.html', app_version=APP_VERSION)

    @app.route('/api/status')
    def api_status():
        return jsonify(snapshot())

    @app.route('/api/camera/frame.jpg')
    def api_camera_frame():
        frame = camera_service.get_jpeg_frame()
        if frame is None:
            frame, _ = camera_service.wait_for_jpeg(0, timeout=0.35)
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
        camera_service.set_preview_enabled(enabled)
        return jsonify({'ok': True, 'enabled': enabled, 'status': snapshot()})

    @atexit.register
    def _cleanup() -> None:
        try:
            camera_service.stop()
        except Exception:
            pass

    return app
