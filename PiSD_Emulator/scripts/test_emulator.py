#!/usr/bin/env python3
"""Unit and PiSD-service adapter checks for the PiSD Emulator milestone."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

COMPONENT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = COMPONENT_ROOT.parent
PISD_ROOT = REPOSITORY_ROOT / "PiSD"
for import_path in (str(PISD_ROOT), str(COMPONENT_ROOT)):
    if import_path not in sys.path:
        sys.path.insert(0, import_path)

from pisd.services.camera_service import CameraService
from pisd.services.motor_service import MotorService
from pisd.services.recording_service import RecordingService
from pisd_emulator.engine import TrackPath, VehicleEngine
from pisd_emulator.renderer import RoadRenderer
from pisd_emulator.runtime import PiSDRuntime
from pisd_emulator.control_app import create_control_app


class EmulatorEngineTests(unittest.TestCase):
    def test_forward_outputs_move_vehicle_along_track(self) -> None:
        engine = VehicleEngine()
        engine.set_motor_outputs({"left_intended": 0.5, "right_intended": 0.5, "left_hardware": 0.5, "right_hardware": 0.5})
        engine.step(120)
        state = engine.snapshot()
        self.assertGreater(state["vehicle"]["y_m"], 0.5)
        self.assertGreater(state["vehicle"]["speed_mps"], 0.3)

    def test_differential_outputs_turn_vehicle_right(self) -> None:
        engine = VehicleEngine()
        engine.set_motor_outputs({"left_intended": 0.45, "right_intended": 0.12, "left_hardware": 0.45, "right_hardware": 0.12})
        engine.step(120)
        state = engine.snapshot()["vehicle"]
        self.assertGreater(state["heading_rad"], 0.0)
        self.assertGreater(state["x_m"], 0.0)

    def test_zero_motor_output_brakes_to_stop(self) -> None:
        engine = VehicleEngine()
        engine.set_motor_outputs({"left_intended": 0.5, "right_intended": 0.5})
        engine.step(120)
        engine.set_motor_outputs({"left_intended": 0.0, "right_intended": 0.0})
        engine.step(120)
        self.assertLess(abs(engine.snapshot()["vehicle"]["speed_mps"]), 0.01)

    def test_paused_timestep_can_be_advanced_manually(self) -> None:
        engine = VehicleEngine()
        engine.set_motor_outputs({"left_intended": 0.4, "right_intended": 0.4})
        engine.set_paused(True)
        engine.step(60)
        self.assertGreater(engine.snapshot()["vehicle"]["y_m"], 0.1)

    def test_motor_response_delay_uses_simulation_time(self) -> None:
        engine = VehicleEngine({"response_delay_s": 0.1})
        engine.set_motor_outputs({"left_intended": 0.5, "right_intended": 0.5})
        engine.step(5)
        self.assertAlmostEqual(engine.snapshot()["vehicle"]["speed_mps"], 0.0)
        engine.step(20)
        self.assertGreater(engine.snapshot()["vehicle"]["speed_mps"], 0.1)

    def test_track_path_is_repeatable_for_same_track(self) -> None:
        first = TrackPath("s_curve")
        second = TrackPath("s_curve")
        self.assertTrue((first.points == second.points).all())
        self.assertEqual(first.headings.tolist(), second.headings.tolist())

    def test_rendered_camera_frame_has_scene_and_changes_with_pose(self) -> None:
        engine = VehicleEngine()
        renderer = RoadRenderer()
        camera = SimpleNamespace(width=160, height=120, brightness=0.0, contrast=1.0, saturation=1.0, hflip=False, vflip=False)
        initial = renderer.render(engine, camera)
        engine.set_motor_outputs({"left_intended": 0.4, "right_intended": 0.4})
        engine.step(100)
        moved = renderer.render(engine, camera)
        self.assertEqual(initial.shape, (120, 160, 3))
        self.assertEqual(initial.dtype.name, "uint8")
        self.assertGreater(int(initial.std()), 15)
        self.assertFalse((initial == moved).all())

    def test_obstacle_layout_is_seeded(self) -> None:
        first = VehicleEngine({"seed": 123})
        second = VehicleEngine({"seed": 123})
        self.assertEqual(first.snapshot()["obstacles"], second.snapshot()["obstacles"])


class PiSDAdapterTests(unittest.TestCase):
    def test_motor_service_publishes_processed_outputs_without_gpio(self) -> None:
        engine = VehicleEngine()
        config = json.loads((PISD_ROOT / "config" / "defaults.json").read_text(encoding="utf-8"))["motor"]
        motor = MotorService(config, hardware_enabled=False, output_sink=engine.set_motor_outputs)
        try:
            motor.update(steering=0.5, throttle=0.4)
            state = engine.snapshot()
            self.assertFalse(motor.hardware_enabled)
            self.assertEqual(motor.status()["adapter"], "emulator")
            self.assertGreater(state["motor"]["left_intended"], state["motor"]["right_intended"])
            self.assertTrue(all(pin["state"] in {"LOW", "PWM"} for pin in state["motor"]["virtual_gpio"]))
        finally:
            motor.close()

    def test_camera_service_uses_rendered_frames_as_its_backend(self) -> None:
        engine = VehicleEngine()
        renderer = RoadRenderer()
        camera_defaults = json.loads((PISD_ROOT / "config" / "defaults.json").read_text(encoding="utf-8"))["camera"]
        camera = CameraService(camera_defaults, hardware_enabled=False, frame_provider=lambda settings: renderer.render(engine, settings))
        try:
            ok, _ = camera.start()
            self.assertTrue(ok)
            jpeg, sequence, _, _ = camera.wait_for_jpeg_frame(timeout=3.0)
            self.assertTrue(jpeg and jpeg.startswith(b"\xff\xd8"))
            self.assertGreater(sequence, 0)
            self.assertEqual(camera.status()["backend"], "emulator")
            self.assertEqual(camera.status()["last_capture_source"], "emulator")
        finally:
            camera.stop()

    def test_recording_manifest_marks_emulator_data_as_synthetic(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            service = RecordingService(
                temp,
                source_metadata={"kind": "synthetic_simulation", "generated_by": "PiSD_Emulator", "physical_camera": False},
            )
            try:
                session, _ = service._single_capture_session("unit")
                self.assertEqual(session["data_source"]["kind"], "synthetic_simulation")
                self.assertFalse(session["data_source"]["physical_camera"])
            finally:
                service.close()

    def test_emulator_app_rejects_hardware_mode_before_startup(self) -> None:
        from pisd.app import create_app

        with self.assertRaisesRegex(ValueError, "cannot be started with hardware enabled"):
            create_app(hardware_enabled=True, emulator=VehicleEngine())

    def test_emulator_runtime_defaults_to_local_hardware_disabled_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime = PiSDRuntime(REPOSITORY_ROOT, workspace=temp)
            status = runtime.status()
            self.assertEqual(status["host"], "127.0.0.1")
            self.assertFalse(status["hardware_enabled"])
            self.assertFalse(status["gpio_access"])
            self.assertEqual(status["version"], runtime.pisd_version)
            self.assertTrue(status["version"])
            runtime.close()


    def test_emulator_settings_roundtrip_and_unknown_key_preservation(self) -> None:
        # Independent temporary workspace; never touch a user's configuration.
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "saved"
            config = workspace / "config" / "emulator_settings.json"
            config.parent.mkdir(parents=True)
            original = {"max_speed_mps": 0.72, "future_setting": {"keep": True}}
            config.write_text(json.dumps(original), encoding="utf-8")
            runtime = PiSDRuntime(REPOSITORY_ROOT, workspace=workspace)
            other = PiSDRuntime(REPOSITORY_ROOT, workspace=Path(temp) / "other")
            try:
                client = create_control_app(runtime).test_client()
                origin = f"http://127.0.0.1:{runtime.control_port}"
                response = client.post("/api/simulation/settings", base_url=origin,
                                       json={"max_speed_mps": 0.8, "hardware_enabled": True})
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertFalse(data["hardware_enabled"])
                self.assertFalse(data["gpio_access"])
                self.assertFalse(data["running"])
                self.assertEqual(data["generation"], 0)
                self.assertAlmostEqual(data["engine"]["physics"]["config"]["max_speed_mps"], 0.8)
                saved = json.loads(config.read_text(encoding="utf-8"))
                self.assertEqual(saved, {"max_speed_mps": 0.8, "future_setting": {"keep": True}})
                self.assertFalse(config.with_suffix(".tmp").exists())
                self.assertAlmostEqual(other.status()["engine"]["physics"]["config"]["max_speed_mps"], 0.72)
                self.assertFalse((other.workspace / "config" / "emulator_settings.json").exists())
                # A foreign origin must not modify the already persisted value.
                before = config.read_bytes()
                denied = client.post("/api/simulation/settings", base_url=origin,
                                     headers={"Origin": "http://127.0.0.1:9999"},
                                     json={"max_speed_mps": 0.9})
                self.assertEqual(denied.status_code, 403)
                self.assertEqual(config.read_bytes(), before)
            finally:
                runtime.close()
                other.close()
            recreated = PiSDRuntime(REPOSITORY_ROOT, workspace=workspace)
            try:
                self.assertAlmostEqual(recreated.status()["engine"]["physics"]["config"]["max_speed_mps"], 0.8)
                self.assertFalse(recreated.status()["hardware_enabled"])
                self.assertFalse(recreated.status()["running"])
                self.assertEqual(json.loads(config.read_text(encoding="utf-8")), saved)
            finally:
                recreated.close()

    def test_bundled_workspace_assets_are_served_without_hardware(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            runtime = PiSDRuntime(REPOSITORY_ROOT, workspace=temp)
            try:
                origin = f"http://127.0.0.1:{runtime.control_port}"
                client = create_control_app(runtime).test_client()
                index = client.get("/", base_url=origin)
                self.assertEqual(index.status_code, 200)
                self.assertIn(b"id=\"emulatorTheme\"", index.data)
                index.close()
                for name in ("app.css", "app.js", "fonts/InterVariable.woff2",
                             "fonts/IBMPlexMono-Regular.woff2", "fonts/Inter-LICENSE.txt",
                             "fonts/IBMPlexMono-LICENSE.txt"):
                    source = COMPONENT_ROOT / "web" / "assets" / name
                    response = client.get("/assets/" + name, base_url=origin)
                    try:
                        self.assertEqual(response.status_code, 200, name)
                        self.assertEqual(response.data, source.read_bytes(), name)
                        if name.startswith("fonts/"):
                            original = PISD_ROOT / "pisd" / "web" / "static" / name
                            self.assertEqual(response.data, original.read_bytes(), name)
                    finally:
                        response.close()
                self.assertFalse(runtime.status()["hardware_enabled"])
                self.assertFalse(runtime.status()["running"])
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
