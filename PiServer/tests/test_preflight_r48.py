"""R48 read-only PiServer preflight contract; no Flask, motor or camera instantiated."""
from __future__ import annotations

import ast
import copy
import shutil
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from piserver.core.preflight import build_preflight, disk_check

BASE = Path(__file__).resolve().parents[1]
PREFLIGHT = BASE / "piserver" / "core" / "preflight.py"
APP = BASE / "piserver" / "app.py"


class ReadOnlyPreflightR48(unittest.TestCase):
    def setUp(self):
        self.camera = {"backend": "picamera2", "preview_enabled": False}
        self.motor = {"gpio_available": True, "left_max_speed": 1.0}
        self.safety = {"latched": False}
        self.usage = types.SimpleNamespace(total=20 * 1024**3, free=12 * 1024**3)

    def summary(self, **overrides):
        kwargs = {
            "camera": self.camera, "motor": self.motor,
            "model_active": True, "safety": self.safety, "disk_root": BASE,
        }
        kwargs.update(overrides)
        with patch("piserver.core.preflight.shutil.disk_usage", return_value=self.usage):
            return build_preflight(**kwargs)

    @staticmethod
    def checks(result):
        return {entry["key"]: entry for entry in result["checks"]}

    def test_six_bounded_named_checks(self):
        data = self.summary()
        self.assertEqual(set(self.checks(data)), {"mode", "camera", "model", "motor", "disk", "network"})
        self.assertTrue(data["read_only"])
        self.assertTrue(data["ok"])

    def test_gpio_adapter_is_not_a_motor_motion_test(self):
        data = self.summary()
        self.assertEqual(data["mode"], "hardware-adapter")
        self.assertIn("not tested", self.checks(data)["motor"]["detail"].lower())

    def test_simulated_adapter_is_explicit(self):
        self.motor["gpio_available"] = False
        data = self.summary()
        self.assertEqual(data["mode"], "simulation")
        self.assertEqual(self.checks(data)["motor"]["state"], "simulation")

    def test_placeholder_camera_is_not_reported_as_hardware(self):
        self.camera["backend"] = "placeholder"
        data = self.summary()
        self.assertEqual(self.checks(data)["camera"]["state"], "attention")

    def test_no_active_model_explains_ai_unavailability(self):
        data = self.summary(model_active=False)
        row = self.checks(data)["model"]
        self.assertEqual(row["state"], "attention")
        self.assertIn("Upload", row["next_step"])

    def test_safety_latch_is_not_cleared_by_preflight(self):
        self.safety["latched"] = True
        data = self.summary()
        self.assertEqual(self.checks(data)["motor"]["state"], "attention")
        self.assertTrue(self.safety["latched"])

    def test_disk_low_and_unknown_have_safe_recovery(self):
        with patch("piserver.core.preflight.shutil.disk_usage", return_value=types.SimpleNamespace(total=10 * 1024**3, free=1 * 1024**3 - 1)):
            self.assertEqual(disk_check(BASE)["state"], "attention")
        with patch("piserver.core.preflight.shutil.disk_usage", side_effect=OSError("/home/pi/secret")):
            result = disk_check(BASE)
        self.assertEqual(result["state"], "unknown")
        self.assertNotIn("/home", str(result))

    def test_input_snapshots_are_not_modified(self):
        old = copy.deepcopy((self.camera, self.motor, self.safety))
        self.summary()
        self.assertEqual(old, (self.camera, self.motor, self.safety))

    def test_network_check_only_confirms_this_http_request(self):
        row = self.checks(self.summary())["network"]
        self.assertIn("Internet", row["detail"])
        self.assertIn("not tested", row["detail"])

    def test_source_contains_no_actuator_or_disk_write_calls(self):
        source = PREFLIGHT.read_text(encoding="utf-8")
        ast.parse(source, filename=str(PREFLIGHT))
        for forbidden in ("motor_service.stop(", "motor_service.update(", "camera_service.start(",
                          "model_service.load(", "subprocess.", "socket.", ".write_text(", ".mkdir("):
            self.assertNotIn(forbidden, source)

    def test_route_is_get_only_and_uses_existing_snapshot_services(self):
        source = APP.read_text(encoding="utf-8")
        ast.parse(source, filename=str(APP))
        route = source.split('@app.get("/api/preflight")', 1)[1].split("    @app.route", 1)[0]
        for required in ("get_config()", "get_active_name()", "safety_status()", "disk_root=BASE_DIR"):
            self.assertIn(required, route)
        self.assertNotIn("MotorService(", route)
        self.assertNotIn("camera_service.start(", route)


if __name__ == "__main__":
    unittest.main()
