#!/usr/bin/env python3
"""R32 diagnostic-only motor command provenance tests (simulation; GPIO never enabled)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pisd.services.motor_service import MotorService  # noqa: E402


class MotorSourceContractTests(unittest.TestCase):
    def setUp(self):
        self.motor = MotorService(hardware_enabled=False)

    def tearDown(self):
        self.motor.close()

    def test_default_caller_remains_other(self):
        self.motor.update(steering=0.1, throttle=0.2)
        self.assertEqual(self.motor.status()["last_command"]["control_source"], "other")

    def test_manual_caller_is_identified(self):
        self.motor.update(steering=0.0, throttle=0.2, control_source="manual")
        self.assertEqual(self.motor.status()["last_command"]["control_source"], "manual")

    def test_assist_caller_is_distinct(self):
        self.motor.update(steering=0.25, throttle=0.2, control_source="manual_assist")
        self.assertEqual(self.motor.status()["last_command"]["control_source"], "manual_assist")

    def test_ai_caller_is_identified(self):
        self.motor.update(steering=-0.2, throttle=0.1, control_source="ai")
        self.assertEqual(self.motor.status()["last_command"]["control_source"], "ai")

    def test_unrecognized_source_fails_closed_to_other(self):
        self.motor.update(steering=0.0, throttle=0.1, control_source="motor_authorization")
        self.assertEqual(self.motor.status()["last_command"]["control_source"], "other")

    def test_stop_clears_last_command_owner_and_motor_values(self):
        self.motor.update(steering=0.0, throttle=0.3, control_source="manual")
        self.motor.stop()
        status = self.motor.status()
        self.assertEqual(status["last_command"]["control_source"], "stopped")
        self.assertEqual(status["last_intended_left"], 0.0)
        self.assertEqual(status["last_intended_right"], 0.0)
        self.assertEqual(status["last_left"], 0.0)
        self.assertEqual(status["last_right"], 0.0)

    def test_provenance_does_not_alter_motor_mixing(self):
        self.motor.update(steering=0.25, throttle=0.4, control_source="manual")
        first = (self.motor.status()["last_intended_left"],
                 self.motor.status()["last_intended_right"])
        self.motor.update(steering=0.25, throttle=0.4, control_source="ai")
        second = (self.motor.status()["last_intended_left"],
                  self.motor.status()["last_intended_right"])
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
