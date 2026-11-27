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


if __name__ == "__main__":
    unittest.main(verbosity=2)
