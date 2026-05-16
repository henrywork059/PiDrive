#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

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
    ok &= line('/api/settings' in js and 'pointerdown' in js and 'pointermove' in js, PiSDErrorCodes.OK if '/api/settings' in js else PiSDErrorCodes.TEST_MANUAL_DRIVE_CONTRACT_FAILED, 'manual_drive.drag_pad_logic', 'drag pad and settings logic present')
    stjs = (ROOT / 'pisd/web/static/js/settings_tab.js').read_text(encoding='utf-8')
    ok &= line('/api/settings/apply' in stjs and 'panel_presentation' in stjs, PiSDErrorCodes.OK if '/api/settings/apply' in stjs else PiSDErrorCodes.TEST_SETTINGS_PERSISTENCE_FAILED, 'settings_tab.backend_apply', 'settings tab saves and applies backend settings')
    return ok


def manager_checks() -> bool:
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'runtime_settings.json'
        mgr = SettingsManager(path, {'camera': {'width': 426}, 'motor': {'steer_mix': 1.0}})
        ok &= line(mgr.get()['camera']['width'] == 426, PiSDErrorCodes.OK, 'settings.manager.defaults', 'defaults loaded')
        saved, settings, report = mgr.save({'manual_drive': {'speed': 0.22}, 'panel_presentation': {'theme': 'light'}})
        ok &= line(saved and settings['manual_drive']['speed'] == 0.22, PiSDErrorCodes.OK if saved else report.code, 'settings.manager.save', 'settings saved')
        mgr2 = SettingsManager(path, {'camera': {'width': 426}, 'motor': {'steer_mix': 1.0}})
        ok &= line(mgr2.get()['panel_presentation']['theme'] == 'light', PiSDErrorCodes.OK, 'settings.manager.reload', 'settings reloaded')
        bad, _settings, report = mgr2.save({'unknown_group': {}})
        ok &= line((not bad) and report and report.code == PiSDErrorCodes.SETTINGS_INVALID_PAYLOAD, report.code if report else PiSDErrorCodes.TEST_SETTINGS_PERSISTENCE_FAILED, 'settings.manager.reject_bad', 'bad payload rejected with code')
    return ok


def api_checks(base_url: str) -> bool:
    ok = True
    status, payload = http_json('GET', f'{base_url}/api/settings')
    ok &= line(status == 200 and payload.get('code') == PiSDErrorCodes.OK, payload.get('code', 'PISD-API-002'), 'api.settings.get', 'settings endpoint loaded')
    test_payload = {'manual_drive': {'speed': 0.21, 'steer_strength': 0.33}, 'panel_presentation': {'theme': 'dark', 'density': 'compact'}}
    status, payload = http_json('POST', f'{base_url}/api/settings/apply', test_payload)
    ok &= line(status == 200 and payload.get('code') == PiSDErrorCodes.OK, payload.get('code', 'PISD-API-002'), 'api.settings.apply', 'settings saved and applied')
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
