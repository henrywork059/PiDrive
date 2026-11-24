"""Test-only adapters to the actual PiSD AI correction and limiter methods.

No alternative safety calculations, model loads, camera start or motor objects.
"""
from __future__ import annotations

import atexit
import tempfile
from contextlib import contextmanager
from unittest.mock import patch

from pisd.services.ai_drive_service import AIDriveService


@contextmanager
def _service(settings):
    with tempfile.TemporaryDirectory() as root:
        service = AIDriveService(root, settings)
        try:
            yield service
        finally:
            atexit.unregister(service.close)
            service.close()


def correction_case(model_steering, model_throttle, manual_steering,
                    manual_throttle, *, gain_percent, age_s=0.1,
                    enabled=True):
    settings = {"manual_correction_enabled": enabled,
                "manual_mix_percent": gain_percent,
                "manual_correction_timeout_s": 0.75}
    with _service(settings) as service:
        with patch("pisd.services.ai_drive_service.time.monotonic", return_value=10.0):
            service.set_manual_correction(manual_steering, manual_throttle, source="validation")
        with patch("pisd.services.ai_drive_service.time.monotonic", return_value=10.0 + age_s):
            return service._mix_manual_correction(model_steering, model_throttle)


def safety_case(steering, throttle, settings, previous):
    with _service(settings) as service:
        # Seed the previous output to characterize production smoothing.
        with service._lock:
            service._last_safe = dict(previous)
        return service.apply_safety(steering, throttle)
