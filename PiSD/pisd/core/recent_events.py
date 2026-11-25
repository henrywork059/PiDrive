"""Bounded local operator history. Never retain request body, URL or raw errors."""
from collections import deque
from datetime import datetime, timezone
from threading import Lock

ROUTES = {
    'api_camera_start': 'Camera start',
    'api_camera_stop': 'Camera stop',
    'api_camera_apply': 'Camera settings Apply',
    'api_motor_apply': 'Motor settings Apply',
    'api_settings_save': 'Settings Save',
    'api_settings_apply': 'Settings Apply',
    'api_settings_reset': 'Settings Reset',
    'api_recording_start': 'Recording start',
    'api_recording_stop': 'Recording stop',
    'api_recording_capture': 'Snapshot capture',
    'api_recording_delete': 'Recording deletion',
    'api_ai_upload_model': 'Model upload',
    'api_ai_load_model': 'Model load',
    'api_ai_delete_model': 'Model deletion',
    'api_ai_start': 'AI start',
    'api_ai_stop': 'AI stop',
    'api_control_stop': 'Motor STOP requested',
    'api_safety_rearm': 'Safety rearm requested',
}

class RecentEvents:
    capacity = 128

    def __init__(self):
        self._items = deque(maxlen=self.capacity)
        self._lock = Lock()

    def observe(self, endpoint, status, payload=None):
        if endpoint not in ROUTES:
            return
        failed = status >= 400 or (isinstance(payload, dict) and payload.get('ok') is False)
        outcome = 'failed' if failed else 'acknowledged' if isinstance(payload, dict) and payload.get('ok') is True else 'response observed'
        item = {'timestamp_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'title': ROUTES[endpoint], 'outcome': outcome}
        with self._lock:
            self._items.append(item)

    def snapshot(self):
        with self._lock:
            return [dict(item) for item in list(self._items)[-80:]]
