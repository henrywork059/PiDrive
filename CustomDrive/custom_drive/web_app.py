from __future__ import annotations

import atexit
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

from .debug_tools import clamp_float, clamp_int
from .run_settings import load_run_settings, save_run_settings
from .runtime_factory import create_runtime

WEB_DIR = Path(__file__).resolve().parent / 'web'


def create_app(mode: str | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(WEB_DIR / 'templates'),
        static_folder=str(WEB_DIR / 'static'),
    )

    state: dict[str, Any] = {
        'run_settings': load_run_settings(),
        'runtime': None,
        'safety_fault_latched': False,
        'safety_fault_reason': '',
    }
    if mode is not None:
        state['run_settings']['runtime_mode'] = str(mode).strip().lower()

    def current_runtime():
        return state['runtime']

    def current_run_settings() -> dict[str, Any]:
        return dict(state['run_settings'])

    def build_runtime(autostart: bool | None = None) -> None:
        previous = state.get('runtime')
        was_running = False
        if previous is not None:
            try:
                status = previous.status()
                was_running = bool(status.get('running'))
            except Exception:
                was_running = False
            try:
                previous.close()
            except Exception:
                pass

        run_cfg = current_run_settings()
        runtime = create_runtime(
            mode=run_cfg.get('runtime_mode', 'sim'),
            max_cycles=int(run_cfg.get('max_cycles', 2)),
        )
        state['runtime'] = runtime

        should_start = bool(run_cfg.get('auto_start_gui', False) if autostart is None else autostart)
        if not should_start and was_running:
            should_start = True
        if state['safety_fault_latched']:
            should_start = False
        if should_start:
            tick_s = clamp_float(run_cfg.get('gui_tick_s', 0.2), 0.2, 0.02, 10.0)
            runtime.start_background(tick_s=tick_s)

    def safe_status_payload() -> dict[str, Any]:
        runtime = current_runtime()
        try:
            payload = runtime.status()
        except Exception as exc:
            payload = {
                'mode': 'unknown',
                'state': 'failed',
                'detail': f'Failed to read runtime status: {exc}',
                'retries': 0,
                'completed_cycles': 0,
                'active_route_leg': None,
                'last_command': {'steering': 0.0, 'throttle': 0.0, 'note': 'status unavailable'},
                'frame': {'width': 640, 'height': 360},
                'detections': [],
                'logs': [],
                'debug_events': [],
                'running': False,
                'max_cycles': current_run_settings().get('max_cycles', 2),
                'last_error': str(exc),
            }
        if str(payload.get('state', '')).lower() == 'failed':
            state['safety_fault_latched'] = True
            state['safety_fault_reason'] = str(payload.get('last_error') or payload.get('detail') or 'Mission failed')
        latched = bool(state['safety_fault_latched'])
        running = bool(payload.get('running'))
        payload['safety'] = {
            'schema_version': 1,
            'component': 'CustomDrive',
            'state': 'latched' if latched else ('running' if running else 'ready'),
            'latched': latched,
            'motion_allowed': not latched,
            'rearm_required': latched,
            'rearm_available': bool(latched and not running),
            'reason': str(state['safety_fault_reason']) if latched else '',
        }
        payload['mode_requested'] = getattr(runtime, 'mode_requested', payload.get('mode', 'sim'))
        payload['fallback_reason'] = getattr(runtime, 'fallback_reason', '')
        payload['run_settings'] = current_run_settings()
        return payload

    build_runtime()

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/api/status')
    def api_status():
        return jsonify(safe_status_payload())

    @app.route('/api/safety/status')
    def api_safety_status():
        return jsonify({'ok': True, 'safety': safe_status_payload()['safety']})

    @app.route('/api/safety/rearm', methods=['POST'])
    def api_safety_rearm():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({'ok': False, 'message': 'Expected a JSON object.'}), 400
        status = safe_status_payload()
        if data.get('confirm') is not True:
            return jsonify({'ok': False, 'message': 'Explicit confirm=true is required.',
                            'safety': status['safety']}), 409
        if not state['safety_fault_latched']:
            return jsonify({'ok': True, 'message': 'No active mission fault.', 'safety': status['safety']})
        runtime = current_runtime()
        try:
            runtime.stop_background(join=True)
            if runtime.status().get('running'):
                raise RuntimeError('Mission worker is still running.')
            motor = getattr(runtime, 'motor_service', None)
            if motor is not None:
                motor.stop()
            runtime.reset()
            if runtime.status().get('state') == 'failed' or runtime.status().get('running'):
                raise RuntimeError('Mission reset did not reach a stopped, safe state.')
        except Exception as exc:
            return jsonify({'ok': False, 'message': f'Rearm refused: {exc}',
                            'safety': safe_status_payload()['safety']}), 409
        state['safety_fault_latched'] = False
        state['safety_fault_reason'] = ''
        return jsonify({'ok': True, 'message': 'Mission rearmed at zero; send a new Start command.',
                        'safety': safe_status_payload()['safety']})

    @app.route('/api/frame.jpg')
    def api_frame_jpg():
        runtime = current_runtime()
        get_jpeg = getattr(runtime, 'get_jpeg_frame', None)
        if not callable(get_jpeg):
            return ('', 204)
        frame = get_jpeg()
        if frame is None:
            return ('', 204)
        response = Response(frame, mimetype='image/jpeg')
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.route('/api/settings')
    def api_settings():
        runtime = current_runtime()
        getter = getattr(runtime, 'get_settings', None)
        if not callable(getter):
            return jsonify({'ok': False, 'message': 'Runtime settings are unavailable.'}), 404
        return jsonify({'ok': True, 'settings': getter()})

    @app.route('/api/settings', methods=['POST'])
    def api_settings_save():
        runtime = current_runtime()
        saver = getattr(runtime, 'save_settings', None)
        if not callable(saver):
            return jsonify({'ok': False, 'message': 'Runtime settings are unavailable.'}), 404
        data = request.get_json(silent=True) or {}
        try:
            saved = saver(data)
        except Exception as exc:
            return jsonify({'ok': False, 'message': f'Failed to save runtime settings: {exc}'}), 400
        return jsonify({'ok': True, 'settings': saved, 'status': safe_status_payload()})

    @app.route('/api/run-settings')
    def api_run_settings():
        return jsonify({'ok': True, 'run_settings': current_run_settings()})

    @app.route('/api/run-settings', methods=['POST'])
    def api_run_settings_save():
        safe_status_payload()
        data = request.get_json(silent=True) or {}
        merged = dict(current_run_settings())
        for key, value in data.items():
            merged[key] = value
        try:
            saved = save_run_settings(merged)
        except Exception as exc:
            return jsonify({'ok': False, 'message': f'Failed to save run settings: {exc}'}), 400
        state['run_settings'] = saved
        build_runtime()
        return jsonify(
            {
                'ok': True,
                'message': 'Run settings saved. GUI and headless launchers now use the same file.',
                'run_settings': current_run_settings(),
                'status': safe_status_payload(),
            }
        )

    @app.route('/api/runtime/rebuild', methods=['POST'])
    def api_runtime_rebuild():
        safe_status_payload()
        runtime = current_runtime()
        data = request.get_json(silent=True) or {}
        autostart = data.get('autostart')
        if runtime is not None:
            try:
                runtime.stop_background(join=True)
            except Exception:
                pass
        build_runtime(autostart=bool(autostart) if autostart is not None else False)
        return jsonify({'ok': True, 'message': 'Runtime rebuilt using the current saved run settings.', 'status': safe_status_payload()})

    @app.route('/api/start', methods=['POST'])
    def api_start():
        if safe_status_payload()['safety']['latched']:
            return jsonify({'ok': False, 'message': 'Mission fault latched; explicitly rearm before starting.',
                            'status': safe_status_payload()}), 423
        runtime = current_runtime()
        run_cfg = current_run_settings()
        data = request.get_json(silent=True) or {}
        tick_s = clamp_float(data.get('tick_s', run_cfg.get('gui_tick_s', 0.2)), 0.2, 0.02, 10.0)
        runtime.start_background(tick_s=tick_s)
        return jsonify({'ok': True, 'status': safe_status_payload(), 'run_settings': run_cfg})

    @app.route('/api/stop', methods=['POST'])
    def api_stop():
        runtime = current_runtime()
        runtime.stop_background(join=True)
        return jsonify({'ok': True, 'status': safe_status_payload(), 'run_settings': current_run_settings()})

    @app.route('/api/step', methods=['POST'])
    def api_step():
        if safe_status_payload()['safety']['latched']:
            return jsonify({'ok': False, 'message': 'Mission fault latched; explicitly rearm before stepping.',
                            'status': safe_status_payload()}), 423
        runtime = current_runtime()
        runtime.step()
        return jsonify({'ok': True, 'status': safe_status_payload(), 'run_settings': current_run_settings()})

    @app.route('/api/reset', methods=['POST'])
    def api_reset():
        safe_status_payload()
        runtime = current_runtime()
        run_cfg = current_run_settings()
        data = request.get_json(silent=True) or {}
        max_cycles = clamp_int(data.get('max_cycles', run_cfg.get('max_cycles', 2)), 2, 1, 999)
        runtime.stop_background(join=True)
        runtime.reset(max_cycles=max_cycles)
        return jsonify({'ok': True, 'status': safe_status_payload(), 'run_settings': run_cfg})

    @atexit.register
    def _shutdown_runtime() -> None:
        runtime = state.get('runtime')
        closer = getattr(runtime, 'close', None)
        if callable(closer):
            closer()
        elif runtime is not None:
            runtime.stop_background(join=True)

    return app
