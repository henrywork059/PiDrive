#!/usr/bin/env python3
"""Hardware-free checks for PiSD's AI camera freshness safety gate."""

from __future__ import annotations

import tempfile
import time
import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pisd.services.ai_drive_service import AIDriveService


class StaticCamera:
    def __init__(self):
        self.frame_seq = 7

    def start(self):
        return True, "ready"

    def get_jpeg_frame_info(self):
        return b"fake-jpeg", self.frame_seq, "", 9


class CapturingMotor:
    hardware_enabled = False

    def __init__(self):
        self.commands = []
        self.stop_count = 0

    def update(self, *, steering, throttle, control_source="other"):
        self.commands.append((steering, throttle))
        return throttle - steering, throttle + steering

    def status(self):
        return {"last_intended_left": 0.2, "last_intended_right": 0.4}

    def stop(self):
        self.stop_count += 1


class AICameraFreshnessTests(unittest.TestCase):
    def make_service(self, **settings):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        service = AIDriveService(
            Path(workspace.name),
            {"command_timeout_s": 0.75, "steering_smoothing": 0.0,
             "throttle_smoothing": 0.0, **settings},
        )
        self.addCleanup(service.close)
        return service

    def test_same_frame_expires_and_new_sequence_renews(self):
        service = self.make_service()
        service._assert_fresh_frame_seq(9, now_monotonic=10.0)
        service._assert_fresh_frame_seq(9, now_monotonic=10.7)
        with self.assertRaisesRegex(RuntimeError, "stale"):
            service._assert_fresh_frame_seq(9, now_monotonic=10.76)
        with self.assertRaisesRegex(RuntimeError, "safety latch"):
            service._assert_fresh_frame_seq(10, now_monotonic=10.77)

    def test_unknown_sequence_is_not_permanently_trusted(self):
        service = self.make_service()
        service._assert_fresh_frame_seq(0, now_monotonic=20.0)
        service._assert_fresh_frame_seq(0, now_monotonic=20.5)
        with self.assertRaisesRegex(RuntimeError, "stale"):
            service._assert_fresh_frame_seq(0, now_monotonic=20.8)

    def test_stale_prediction_stops_motor_and_clears_command(self):
        service = self.make_service()
        camera = StaticCamera()
        motor = CapturingMotor()
        service._ensure_model_ready_for_run = lambda: None
        service._predict_from_jpeg = lambda _: (0.4, 0.3)
        service._running = True
        service._mode = "drive"
        service._drive_output_enabled = True

        first = service.predict_once(camera, motor, drive=True)
        self.assertTrue(first.get("ok"), first)
        self.assertEqual(len(motor.commands), 1)
        with service._lock:
            service._last_fresh_frame_monotonic = time.monotonic() - 1.0

        stale = service.predict_once(camera, motor, drive=True)
        self.assertFalse(stale.get("ok"), stale)
        self.assertEqual(len(motor.commands), 1)
        self.assertGreaterEqual(motor.stop_count, 1)
        status = service.status()
        self.assertTrue(status["camera_frame_stale"])
        self.assertEqual(status["last_safe_command"]["throttle"], 0.0)
        self.assertEqual(status["last_raw_prediction"]["steering"], 0.0)
        self.assertTrue(status["camera_frame_fault_latched"])
        camera.frame_seq = 8
        still_stopped = service.predict_once(camera, motor, drive=True)
        self.assertFalse(still_stopped.get("ok"))
        self.assertEqual(len(motor.commands), 1)

    def test_explicit_restart_state_reset_allows_new_grace_window(self):
        service = self.make_service()
        service._assert_fresh_frame_seq(3, now_monotonic=10.0)
        with service._lock:
            service._last_fresh_frame_seq = 0
            service._last_fresh_frame_monotonic = None
        service._camera_frame_fault_latched = False
        service._assert_fresh_frame_seq(3, now_monotonic=time.monotonic())
        self.assertFalse(service.status()["camera_frame_stale"])


if __name__ == "__main__":
    unittest.main()
