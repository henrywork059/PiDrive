"""R48 PiSD passive preflight unit tests, without camera/GPIO/Flask initialization."""
from __future__ import annotations

import ast
import copy
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from pisd.core.preflight import build_preflight, disk_check

BASE = Path(__file__).resolve().parents[1]
PREFLIGHT = BASE / "pisd" / "core" / "preflight.py"
APP = BASE / "pisd" / "app.py"


class ReadOnlyPiSDPreflightR48(unittest.TestCase):
    def setUp(self):
        self.camera = {"backend": "picamera2", "hardware_enabled": True, "running": True}
        self.motor = {"hardware_requested": True, "hardware_enabled": True, "adapter": "rpigpio"}
        self.ai = {"model_loaded": True, "model_ready": True,
                   "runtime_support": {"tflite": True}}
        self.safety = {"latched": False}

    def build(self, *, hardware=True, **overrides):
        args = {
            "hardware_requested": hardware, "camera": self.camera,
            "motor": self.motor, "ai": self.ai, "safety": self.safety,
            "project_root": BASE,
        }
        args.update(overrides)
        usage = types.SimpleNamespace(total=20 * 1024**3, free=12 * 1024**3)
        with patch("pisd.core.preflight.shutil.disk_usage", return_value=usage):
            return build_preflight(**args)

    def rows(self, data):
        return {c["key"]: c for c in data["checks"]}

    def test_six_passive_checks_and_versioned_fields(self):
        data = self.build()
        self.assertTrue(data["read_only"])
        self.assertEqual(data["component"], "PiSD")
        self.assertEqual(set(self.rows(data)), {"mode", "camera", "model", "motor", "disk", "network"})

    def test_hardware_requested_does_not_mean_backend_is_real(self):
        self.motor["hardware_enabled"] = False
        data = self.build()
        self.assertEqual(self.rows(data)["mode"]["state"], "simulation")
        self.assertEqual(self.rows(data)["motor"]["state"], "attention")

    def test_simulation_requested_is_explicit_even_if_camera_mock_runs(self):
        self.camera.update(backend="simulation", hardware_enabled=False)
        self.motor["hardware_enabled"] = False
        data = self.build(hardware=False)
        self.assertEqual(data["mode"], "simulation-requested")
        self.assertEqual(self.rows(data)["camera"]["state"], "simulation")

    def test_unstarted_camera_does_not_trigger_camera_start(self):
        self.camera.update(running=False, backend="not_started")
        row = self.rows(self.build())["camera"]
        self.assertEqual(row["state"], "attention")
        self.assertIn("Start live", row["next_step"])

    def test_no_model_loaded_has_an_actionable_reason(self):
        self.ai["model_loaded"] = False
        data = self.build()
        row = self.rows(data)["model"]
        self.assertEqual(row["state"], "attention")
        self.assertIn("Upload", row["next_step"])

    def test_missing_tflite_runtime_identifies_installation_without_importing_it(self):
        self.ai.update(model_loaded=False, model_ready=False, runtime_support={"tflite": False})
        row = self.rows(self.build())["model"]
        self.assertIn("runtime missing", row["detail"].lower())
        self.assertIn("tflite-runtime", row["next_step"])

    def test_camera_fault_latch_preserved(self):
        self.safety["latched"] = True
        row = self.rows(self.build())["motor"]
        self.assertEqual(row["state"], "attention")
        self.assertTrue(self.safety["latched"])

    def test_disk_low_capacity_warns_and_path_failure_is_redacted(self):
        with patch("pisd.core.preflight.shutil.disk_usage",
                   return_value=types.SimpleNamespace(total=20 * 1024**3, free=250 * 1024**2)):
            self.assertEqual(disk_check(BASE)["state"], "attention")
        with patch("pisd.core.preflight.shutil.disk_usage", side_effect=OSError("secret /root/private")):
            row = disk_check(BASE)
        self.assertEqual(row["state"], "unknown")
        self.assertNotIn("/root/private", str(row))

    def test_preflight_does_not_mutate_or_save_any_snapshot(self):
        previous = copy.deepcopy((self.camera, self.motor, self.ai, self.safety))
        self.build()
        self.assertEqual(previous, (self.camera, self.motor, self.ai, self.safety))

    def test_network_is_http_reachability_not_internet_probe(self):
        row = self.rows(self.build())["network"]
        self.assertIn("HTTP", row["detail"])
        self.assertIn("not tested", row["detail"])

    def test_source_does_not_issue_model_load_motor_or_camera_commands(self):
        text = PREFLIGHT.read_text(encoding="utf-8")
        ast.parse(text, filename=str(PREFLIGHT))
        for banned in ("camera_service.start(", "motor_service.update(", "motor_service.stop(",
                       "load_model(", ".mkdir(", "socket.", "urllib.", "subprocess.", "settings_manager.save("):
            self.assertNotIn(banned, text)

    def test_read_only_get_route_reuses_loaded_services(self):
        text = APP.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(APP))
        route_node = next(node for node in ast.walk(tree)
                          if isinstance(node, ast.FunctionDef) and node.name == "api_preflight")
        self.assertTrue(any(isinstance(d, ast.Call)
                            and isinstance(d.func, ast.Attribute)
                            and d.func.attr == "get"
                            and any(isinstance(a, ast.Constant) and a.value == "/api/preflight"
                                    for a in d.args)
                            for d in route_node.decorator_list))
        route = ast.unparse(route_node)
        for required in ("camera_service.status()", "motor_service.status()",
                         "ai_drive_service.status()", "ai_drive_service.safety_status()"):
            self.assertIn(required, route)
        # Check actual calls, not explanatory comments containing forbidden names.
        allowed = {"jsonify", "build_preflight", "bool", "status", "safety_status"}
        for node in ast.walk(route_node):
            if isinstance(node, ast.Call):
                called = node.func.id if isinstance(node.func, ast.Name) else (
                    node.func.attr if isinstance(node.func, ast.Attribute) else "")
                if node in route_node.decorator_list:
                    continue
                self.assertIn(called, allowed, f"Unexpected preflight call: {ast.unparse(node)}")


if __name__ == "__main__":
    unittest.main()
