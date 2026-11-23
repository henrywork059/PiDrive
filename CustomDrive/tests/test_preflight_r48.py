"""R48 CustomDrive general GUI + Mission1 read-only preflight tests.

Only imports a pure formatter; no Flask app, GPIO, camera, arm or detector.
"""
from __future__ import annotations

import ast
import copy
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from custom_drive.preflight import build_gui_preflight, build_mission1_preflight, disk_check

BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE / "custom_drive" / "preflight.py"
GUI_APP = BASE / "custom_drive" / "gui_control_app.py"
MISSION_APP = BASE / "custom_drive" / "mission1_session_app.py"


class ReadOnlyCustomDrivePreflightR48(unittest.TestCase):
    def setUp(self):
        self.camera = {"backend": "picamera2", "preview_enabled": True}
        self.motor = {"gpio_available": True, "left_max_speed": 0.6}
        self.arm = {"enabled": True, "available": True, "simulated": False}
        self.ai = {"backend": "tflite", "ready": True, "active_model": "none"}
        self.safety = {"latched": False}
        self.usage = types.SimpleNamespace(total=20 * 1024**3, free=12 * 1024**3)

    def gui(self):
        with patch("custom_drive.preflight.shutil.disk_usage", return_value=self.usage):
            return build_gui_preflight(camera=self.camera, motor=self.motor,
                                       ai=self.ai, arm=self.arm,
                                       safety=self.safety, project_root=BASE)

    def mission(self, *, camera=None, selected=True, loaded=False, running=False):
        with patch("custom_drive.preflight.shutil.disk_usage", return_value=self.usage):
            return build_mission1_preflight(camera=camera, motor=self.motor,
                                            model_selected=selected, model_loaded=loaded,
                                            arm=self.arm, safety=self.safety,
                                            mission_running=running, project_root=BASE)

    @staticmethod
    def rows(result):
        return {row["key"]: row for row in result["checks"]}

    def test_both_apps_have_seven_read_only_checks(self):
        for result in (self.gui(), self.mission()):
            self.assertTrue(result["read_only"])
            self.assertEqual(len(result["checks"]), 7)
            self.assertEqual(set(self.rows(result)),
                             {"mode", "camera", "model", "motor", "arm", "disk", "network"})

    def test_gui_reports_real_gpio_adapter_but_no_output_test(self):
        result = self.gui()
        self.assertEqual(result["mode"], "hardware-adapter")
        self.assertIn("not tested", self.rows(result)["motor"]["detail"])

    def test_gui_no_gpio_explicitly_simulated(self):
        self.motor["gpio_available"] = False
        result = self.gui()
        self.assertEqual(result["mode"], "simulation")
        self.assertEqual(self.rows(result)["motor"]["state"], "simulation")

    def test_gui_color_detection_does_not_require_tflite_model(self):
        self.ai.update(backend="color", ready=False)
        row = self.rows(self.gui())["model"]
        self.assertEqual(row["state"], "ready")
        self.assertIn("not required", row["detail"])

    def test_missing_gui_tflite_marks_model_attention(self):
        self.ai.update(backend="tflite", ready=False)
        self.assertEqual(self.rows(self.gui())["model"]["state"], "attention")

    def test_arm_disabled_is_identified_with_action(self):
        self.arm.update(enabled=False, available=False)
        row = self.rows(self.gui())["arm"]
        self.assertEqual(row["state"], "attention")
        self.assertIn("Enable", row["next_step"])

    def test_simulated_arm_is_never_mislabeled_as_real(self):
        self.arm["simulated"] = True
        row = self.rows(self.gui())["arm"]
        self.assertEqual(row["state"], "simulation")
        self.assertIn("Simulated", row["detail"])

    def test_mission_deferred_camera_is_expected_and_does_not_start(self):
        row = self.rows(self.mission(camera=None))["camera"]
        self.assertEqual(row["state"], "attention")
        self.assertIn("expected", row["detail"])
        self.assertIn("configured stage", row["next_step"])

    def test_mission_selected_model_is_not_falsely_loaded(self):
        row = self.rows(self.mission(selected=True, loaded=False))["model"]
        self.assertEqual(row["state"], "attention")
        self.assertIn("not loaded", row["detail"])

    def test_mission_no_model_explains_detection_unavailable(self):
        row = self.rows(self.mission(selected=False, loaded=False))["model"]
        self.assertIn("unavailable", row["detail"])
        self.assertIn("Upload", row["next_step"])

    def test_mission_live_model_reports_ready_without_inference_run(self):
        row = self.rows(self.mission(selected=True, loaded=True))["model"]
        self.assertEqual(row["state"], "ready")
        self.assertIn("not tested", row["detail"])

    def test_safety_latch_never_cleared(self):
        self.safety["latched"] = True
        for data in (self.gui(), self.mission()):
            self.assertEqual(self.rows(data)["motor"]["state"], "attention")
        self.assertTrue(self.safety["latched"])

    def test_unreadable_disk_does_not_echo_sensitive_path(self):
        with patch("custom_drive.preflight.shutil.disk_usage",
                   side_effect=OSError("failed /home/pi/.config/secret")):
            row = disk_check(BASE)
        self.assertEqual(row["state"], "unknown")
        self.assertNotIn("/home/pi", str(row))

    def test_snapshots_are_immutable_after_observation(self):
        original = copy.deepcopy((self.camera, self.motor, self.ai, self.arm, self.safety))
        self.gui()
        self.mission()
        self.assertEqual(original, (self.camera, self.motor, self.ai, self.arm, self.safety))

    def test_network_reports_only_this_http_connection(self):
        self.assertIn("no internet", self.rows(self.gui())["network"]["detail"].lower())
        self.assertIn("no internet", self.rows(self.mission())["network"]["detail"].lower())

    def test_formatter_source_contains_no_motor_camera_arm_or_setting_writes(self):
        code = SOURCE.read_text(encoding="utf-8")
        ast.parse(code, filename=str(SOURCE))
        for forbidden in ("motor_service.update(", "motor_service.stop(", "arm_service.load_role(",
                          "camera_service.start(", "model_service.load(", ".save_config(",
                          ".mkdir(", "socket.", "subprocess.", ".write_text("):
            self.assertNotIn(forbidden, code)

    def test_two_get_routes_never_instantiate_hardware(self):
        for path, route_marker in (
            (GUI_APP, "@app.get('/api/preflight')"),
            (MISSION_APP, "@app.get('/api/preflight')"),
        ):
            with self.subTest(app=str(path.name)):
                code = path.read_text(encoding="utf-8")
                ast.parse(code, filename=str(path))
                route = code.split(route_marker, 1)[1].split("    @app.route", 1)[0]
                self.assertIn("get_config()", route)
                self.assertIn("safety_status()", route)
                self.assertNotIn("MotorService(", route)
                self.assertNotIn("start_session(", route)
                self.assertNotIn("camera_service.start(", route)


if __name__ == "__main__":
    unittest.main()
