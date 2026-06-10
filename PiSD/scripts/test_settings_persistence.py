#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import HTTPError
# PiSD_0_4_1 cleanup: URLError was imported by an earlier network-check draft but is not referenced.
# from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pisd.core.errors import PiSDErrorCodes
from pisd.core.settings_manager import SettingsManager


def line(ok: bool, code: str, label: str, message: str) -> bool:
    print(f"{'OK' if ok else 'FAIL'}   {code}   {label} - {message}")
    return ok


def http_json(method: str, url: str, body: dict | None = None) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body).encode('utf-8')
    req = urlrequest.Request(url, data=data, method=method, headers={'Content-Type': 'application/json'})
    try:
        with urlrequest.urlopen(req, timeout=5) as res:
            return res.status, json.loads(res.read().decode('utf-8'))
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode('utf-8'))
        except Exception:
            payload = {'ok': False, 'code': 'PISD-API-002', 'message': str(exc)}
        return exc.code, payload


def static_checks() -> bool:
    required = [
        ROOT / 'pisd/core/settings_manager.py',
        ROOT / 'pisd/web/templates/settings_tab.html',
        ROOT / 'pisd/web/static/js/settings_tab.js',
        ROOT / 'pisd/web/static/js/panel_presentation_global.js',
        ROOT / 'pisd/web/templates/manual_drive.html',
        ROOT / 'pisd/web/static/js/manual_drive.js',
    ]
    ok = True
    for path in required:
        ok &= line(path.exists(), PiSDErrorCodes.OK if path.exists() else PiSDErrorCodes.TEST_SETTINGS_PERSISTENCE_FAILED, f'static.exists.{path.name}', str(path.relative_to(ROOT)))
    html = (ROOT / 'pisd/web/templates/manual_drive.html').read_text(encoding='utf-8')
    js = (ROOT / 'pisd/web/static/js/manual_drive.js').read_text(encoding='utf-8')
    ok &= line('mdrvDragPad' in html and 'mdrvDragKnob' in html, PiSDErrorCodes.OK if 'mdrvDragPad' in html else PiSDErrorCodes.TEST_MANUAL_DRIVE_CONTRACT_FAILED, 'manual_drive.drag_pad_markup', 'drag pad markup present')
    ok &= line('/api/settings' in js and 'pointerdown' in js and 'pointermove' in js and 'pisd.manualDrive.v1' not in js, PiSDErrorCodes.OK if ('/api/settings' in js and 'pisd.manualDrive.v1' not in js) else PiSDErrorCodes.TEST_MANUAL_DRIVE_CONTRACT_FAILED, 'manual_drive.global_settings_only', 'manual drive reads/saves through the global settings API without legacy per-page speed storage')
    reduced_overlay_html = all(token in html for token in ('mdrvOverlayTurnRateVisualScale', 'mdrvOverlayLengthScale', 'mdrvOverlayPathWidth', 'mdrvOverlayBaseY', 'mdrvOverlayHorizonY', 'mdrvOverlayPerspectiveScale', 'mdrvOverlayOpacity', 'Overlay calibration — 7 controls', 'Shape', 'Camera alignment', 'Visibility')) and all(legacy not in html for legacy in ('mdrvOverlayCurveScale', 'mdrvOverlaySampleCount', 'mdrvOverlayWheelbase', 'mdrvOverlayMaxSteerRad', 'mdrvOverlayCurveResponse', 'mdrvOverlayCurvatureScale', 'mdrvOverlayCurvatureLimit', 'mdrvOverlayEntryBlendStart', 'mdrvOverlayRoadHalfWidth', 'mdrvOverlayCameraOffset', 'mdrvOverlayNearClip', 'mdrvOverlayPerspectiveDepth', 'mdrvOverlayTurnCompression', 'mdrvOverlayTurnWidthTaper'))
    ok &= line(reduced_overlay_html and 'persistOverlaySettingsSoon' in js and 'normaliseOverlaySettings' in js and 'finiteOverlayValue' in js and 'OVERLAY_CONTROL_LIMITS' not in js, PiSDErrorCodes.OK if reduced_overlay_html else PiSDErrorCodes.TEST_SETTINGS_PERSISTENCE_FAILED, 'manual_drive.overlay_settings', 'overlay calibration settings are reduced to seven uncapped visual controls and persisted')
    stjs = (ROOT / 'pisd/web/static/js/settings_tab.js').read_text(encoding='utf-8')
    ok &= line('/api/settings/apply' in stjs and 'panel_presentation' in stjs and 'storeLocal(settings); if' not in stjs, PiSDErrorCodes.OK if ('/api/settings/apply' in stjs and 'storeLocal(settings); if' not in stjs) else PiSDErrorCodes.TEST_SETTINGS_PERSISTENCE_FAILED, 'settings_tab.backend_apply', 'settings tab saves and applies backend settings without writing unsaved form edits as global cache')
    settings_html = (ROOT / 'pisd/web/templates/settings_tab.html').read_text(encoding='utf-8')
    ok &= line('name="steering_mode"' in settings_html and 'turn_rate' in settings_html and 'arcade_mix' in settings_html, PiSDErrorCodes.OK if 'name="steering_mode"' in settings_html else PiSDErrorCodes.TEST_SETTINGS_PERSISTENCE_FAILED, 'settings_tab.steering_mode', 'motor steering mode setting is exposed')
    ok &= line('turn_gain' not in settings_html and 'turn_curve' not in settings_html and 'min_inside_speed' in settings_html, PiSDErrorCodes.OK if ('turn_gain' not in settings_html and 'turn_curve' not in settings_html) else PiSDErrorCodes.TEST_SETTINGS_PERSISTENCE_FAILED, 'settings_tab.turn_rate_tuning', 'linear turn-rate motor settings are exposed without removed turn_gain/turn_curve')
    ok &= line('name="start_deadzone"' not in settings_html and 'name="start_kick_seconds"' not in settings_html and 'start_deadzone' not in stjs and 'start_kick_seconds' not in stjs, PiSDErrorCodes.OK if ('name="start_deadzone"' not in settings_html and 'start_deadzone' not in stjs) else PiSDErrorCodes.TEST_SETTINGS_PERSISTENCE_FAILED, 'settings_tab.no_start_deadzone', 'motor start dead-zone/kick tuning is removed from the settings UI')
    ok &= line('steer_strength' not in html and 'Steer strength' not in html and "$('mdrvSteer')" not in js and 'mdrvSteerOut' not in js, PiSDErrorCodes.OK if ('steer_strength' not in html and 'Steer strength' not in html and "$('mdrvSteer')" not in js and 'mdrvSteerOut' not in js) else PiSDErrorCodes.TEST_MANUAL_DRIVE_CONTRACT_FAILED, 'manual_drive.no_steer_strength', 'Manual Drive no longer scales steering X with a steer-strength slider')
    ok &= line('name="steer_strength"' not in settings_html and 'Steer strength' not in settings_html, PiSDErrorCodes.OK if ('name="steer_strength"' not in settings_html and 'Steer strength' not in settings_html) else PiSDErrorCodes.TEST_SETTINGS_PERSISTENCE_FAILED, 'settings_tab.no_steer_strength', 'Settings page no longer exposes steer_strength')
    ok &= line('value="0.80"' in html and 'value="0.80"' in settings_html, PiSDErrorCodes.OK if ('value="0.80"' in html and 'value="0.80"' in settings_html) else PiSDErrorCodes.TEST_SETTINGS_PERSISTENCE_FAILED, 'settings.global_manual_speed_default', 'global Manual speed default is 0.80 in Manual Drive and Settings UI')
    ok &= line('Camera capture FPS' in settings_html and 'name="live_preview_fps"' in settings_html and 'stAIForm' in settings_html and 'AI prediction FPS' in settings_html and 'ai_mode' in stjs and 'live_preview_fps' in stjs, PiSDErrorCodes.OK if ('Camera capture FPS' in settings_html and 'live_preview_fps' in stjs) else PiSDErrorCodes.TEST_SETTINGS_PERSISTENCE_FAILED, 'settings.three_rate_global_fps', 'Settings page exposes global camera capture FPS, live preview FPS, and AI prediction FPS without page-only duplicate keys')
    return ok


def manager_checks() -> bool:
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'runtime_settings.json'
        mgr = SettingsManager(path, {'camera': {'width': 426, 'auto_white_balance': False, 'awb_settle_seconds': 1.0}, 'motor': {'steer_mix': 1.0}})
        ok &= line(mgr.get()['camera']['width'] == 426, PiSDErrorCodes.OK, 'settings.manager.defaults', 'defaults loaded')
        ok &= line(mgr.get()['camera']['auto_white_balance'] is False and mgr.get()['camera']['awb_settle_seconds'] == 1.0, PiSDErrorCodes.OK, 'settings.manager.camera_default_profile', '0.5.6 camera default profile loaded')
        ok &= line(abs(float(mgr.get()['manual_drive']['speed']) - 0.80) < 1e-9, PiSDErrorCodes.OK, 'settings.manager.manual_speed_default', 'new Manual speed default is 0.80 from the global settings manager')
        fps_saved, fps_settings, fps_report = mgr.save({'camera': {'fps': 500, 'live_preview_fps': 0}, 'ai_mode': {'update_hz': 500}})
        ok &= line(fps_saved and fps_settings['camera']['fps'] == 120 and fps_settings['camera']['live_preview_fps'] == 1 and fps_settings['ai_mode']['update_hz'] == 60.0, PiSDErrorCodes.OK if fps_saved else fps_report.code, 'settings.manager.three_rate_clamp', 'global FPS settings are saved once and clamped through the backend settings manager')
        saved, settings, report = mgr.save({'manual_drive': {'speed': 0.22, 'overlay': {'path_length_scale': 9, 'curve_strength': 0.1, 'opacity': 'bad', 'path_width_scale': 1.4, 'sample_count': 128, 'perspective_scale': 105, 'turn_rate_visual_scale': 3.1}}, 'panel_presentation': {'theme': 'light'}})
        ok &= line(saved and settings['manual_drive']['speed'] == 0.22, PiSDErrorCodes.OK if saved else report.code, 'settings.manager.save', 'settings saved')
        overlay = settings['manual_drive']['overlay']
        ok &= line(
            set(overlay.keys()) == {'enabled', 'turn_rate_visual_scale', 'path_length_scale', 'path_width_scale', 'base_y', 'horizon_y', 'perspective_scale', 'opacity'}
            and overlay['path_length_scale'] == 9
            and overlay['opacity'] == 0.94
            and overlay['path_width_scale'] == 1.4
            and overlay['perspective_scale'] == 105
            and overlay['turn_rate_visual_scale'] == 3.1
            and 'curve_strength' not in overlay
            and 'sample_count' not in overlay,
            PiSDErrorCodes.OK,
            'settings.manager.overlay_reduced_keys',
            'overlay calibration persists only the seven user-facing visual controls without earlier min/max caps and prunes legacy advanced keys',
        )
        motor_saved, motor_settings, motor_report = mgr.save({'motor': {'steering_mode': 'turn_rate', 'turn_gain': 1.25, 'turn_curve': 1.8, 'min_inside_speed': 0.2, 'allow_pivot_turn': True, 'start_deadzone': 0.24, 'start_kick_seconds': 0.11}})
        motor = motor_settings['motor']
        ok &= line(
            motor_saved
            and motor['steering_mode'] == 'turn_rate'
            and 'turn_gain' not in motor
            and 'turn_curve' not in motor
            and motor['min_inside_speed'] == 0.2
            and motor['allow_pivot_turn'] is True
            and 'start_deadzone' not in motor
            and 'start_kick_seconds' not in motor,
            PiSDErrorCodes.OK if motor_saved else motor_report.code,
            'settings.manager.turn_rate_motor_settings',
            'linear turn-rate motor settings are saved while legacy turn_gain/turn_curve and removed start-dead-zone keys are ignored',
        )
        legacy_saved, legacy_settings, legacy_report = mgr.save({'manual_drive': {'steer_strength': 0.25, 'speed': 0.19}})
        ok &= line(legacy_saved and 'steer_strength' not in legacy_settings['manual_drive'] and legacy_settings['manual_drive']['speed'] == 0.19, PiSDErrorCodes.OK if legacy_saved else legacy_report.code, 'settings.manager.legacy_steer_strength_ignored', 'legacy manual steer_strength is ignored and removed')
        ai_saved, ai_settings, ai_report = mgr.save({'ai_mode': {'motor_output_enabled': True, 'fixed_throttle': 0.44}})
        ok &= line(ai_saved and ai_settings['ai_mode']['motor_output_enabled'] is False and ai_settings['ai_mode']['fixed_throttle'] == 0.44, PiSDErrorCodes.OK if ai_saved else ai_report.code, 'settings.manager.ai_motor_enable_session_only', 'AI motor output enable is not persisted')
        mgr2 = SettingsManager(path, {'camera': {'width': 426}, 'motor': {'steer_mix': 1.0}})
        ok &= line(mgr2.get()['panel_presentation']['theme'] == 'light', PiSDErrorCodes.OK, 'settings.manager.reload', 'settings reloaded')
        ok &= line(mgr2.get()['ai_mode']['motor_output_enabled'] is False, PiSDErrorCodes.OK, 'settings.manager.ai_motor_enable_reload_false', 'AI motor output enable remains false after reload')
        bad, _settings, report = mgr2.save({'unknown_group': {}})
        ok &= line((not bad) and report and report.code == PiSDErrorCodes.SETTINGS_INVALID_PAYLOAD, report.code if report else PiSDErrorCodes.TEST_SETTINGS_PERSISTENCE_FAILED, 'settings.manager.reject_bad', 'bad payload rejected with code')

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'runtime_settings.json'
        path.write_text(json.dumps({'camera': {
            'capture_source': 'request',
            'array_color_order': 'rgb',
            'format': 'BGR888',
            'auto_white_balance': True,
            'awb_mode': 'auto',
            'colour_gains_red': 0.0,
            'colour_gains_blue': 0.0,
            'awb_settle_seconds': 0.5,
            'brightness': 0.0,
            'contrast': 1.0,
            'saturation': 1.0,
        }}, indent=2), encoding='utf-8')
        mgr3 = SettingsManager(path, {'camera': {'auto_white_balance': False, 'awb_settle_seconds': 1.0}, 'motor': {}})
        cam = mgr3.get()['camera']
        ok &= line(cam['auto_white_balance'] is False and cam['awb_settle_seconds'] == 1.0, PiSDErrorCodes.OK, 'settings.manager.camera_migration', 'old AWB-auto camera default migrates to locked-AWB profile')

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'runtime_settings.json'
        path.write_text(json.dumps({'camera': {'auto_white_balance': True, 'awb_mode': 'daylight'}}, indent=2), encoding='utf-8')
        mgr4 = SettingsManager(path, {'camera': {'auto_white_balance': False, 'awb_settle_seconds': 1.0}, 'motor': {}})
        cam = mgr4.get()['camera']
        ok &= line(cam['auto_white_balance'] is True and cam['awb_mode'] == 'daylight', PiSDErrorCodes.OK, 'settings.manager.camera_custom_preserved', 'custom camera AWB mode is preserved')
    return ok


def api_checks(base_url: str) -> bool:
    ok = True
    status, payload = http_json('GET', f'{base_url}/api/settings')
    ok &= line(status == 200 and payload.get('code') == PiSDErrorCodes.OK, payload.get('code', 'PISD-API-002'), 'api.settings.get', 'settings endpoint loaded')
    test_payload = {'manual_drive': {'speed': 0.21, 'steer_strength': 0.33, 'overlay': {'enabled': True, 'opacity': 0.75}}, 'panel_presentation': {'theme': 'dark', 'density': 'compact'}}
    status, payload = http_json('POST', f'{base_url}/api/settings/apply', test_payload)
    ok &= line(status == 200 and payload.get('code') == PiSDErrorCodes.OK and 'steer_strength' not in payload.get('settings', {}).get('manual_drive', {}), payload.get('code', 'PISD-API-002'), 'api.settings.apply', 'settings saved and legacy steer_strength ignored')
    status, payload = http_json('POST', f'{base_url}/api/settings', {'bad_group': {}})
    ok &= line(status >= 400 and payload.get('code') == PiSDErrorCodes.SETTINGS_INVALID_PAYLOAD, payload.get('code', 'PISD-API-002'), 'api.settings.bad_payload', 'bad settings rejected')
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description='Check PiSD persistent settings and manual-drive UI contracts.')
    parser.add_argument('--base-url', default='', help='Optional running PiSD server base URL for live settings API checks.')
    args = parser.parse_args()
    ok = static_checks() & manager_checks()
    if args.base_url:
        ok &= api_checks(args.base_url.rstrip('/'))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
