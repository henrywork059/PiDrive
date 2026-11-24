from __future__ import annotations

import unittest
from unittest.mock import patch

from piserver.services.control_service import ControlService


class DummyStateful:
    pass


class DummyCamera:
    def __init__(self):
        self.backend = "dummy"
        self.width = 320
        self.height = 240
        self.camera_format = "BGR888"
        self.preview_live = True
        self.last_error = ""
        self.processing_enabled_calls = []
        self.apply_settings_calls = []

    def get_fps(self):
        return 0.0

    def get_raw_frame_age(self):
        # No raw frame has been captured by this hardware-free camera.
        return None

    def set_processing_enabled(self, enabled):
        self.processing_enabled_calls.append(bool(enabled))

    def get_latest_frame(self, copy=True):
        return None

    def get_config(self):
        return {}

    def apply_settings(self, settings, restart=True):
        self.apply_settings_calls.append((dict(settings), bool(restart)))
        return True, "ok", {}


class DummyMotor:
    def __init__(self, fail=False):
        self.fail = fail
        self.stop_calls = 0
        self.update_calls = []
        self.cfg = {
            "left_direction": 1,
            "right_direction": 1,
            "left_max_speed": 1.0,
            "right_max_speed": 1.0,
            "left_bias": 0.0,
            "right_bias": 0.0,
        }

    def update(self, steering, throttle, steer_mix):
        self.update_calls.append((steering, throttle, steer_mix))
        if self.fail:
            raise RuntimeError("motor boom")
        return throttle - steer_mix * steering, throttle + steer_mix * steering

    def stop(self):
        self.stop_calls += 1

    def get_config(self):
        return dict(self.cfg)

    def apply_settings(self, cfg):
        self.cfg.update(cfg or {})
        return self.get_config()


class DummyModel:
    def get_active_name(self):
        return "none"


class DummyRecorder:
    def __init__(self):
        self.recording = False
        self.recorded = []

    def toggle(self):
        self.recording = not self.recording

    def maybe_record(self, frame, snapshot):
        self.recorded.append((frame, snapshot))


class DummyConfig:
    def __init__(self, data=None):
        self.data = data or {}

    def load(self):
        return dict(self.data)

    def save(self, data):
        self.data = dict(data)


class ManualAlgo:
    name = "manual"
    label = "Manual"

    def compute(self, state, camera_service, model_service):
        return state.manual_steering, state.manual_throttle


class BoomAlgo:
    name = "boom"
    label = "Boom"

    def compute(self, state, camera_service, model_service):
        raise RuntimeError("algo boom")


class ControlServiceTests(unittest.TestCase):
    def build_service(self, *, algorithms=None, motor=None, config=None):
        camera = DummyCamera()
        motor = motor or DummyMotor()
        model = DummyModel()
        recorder = DummyRecorder()
        algorithms = algorithms or {"manual": ManualAlgo()}
        config = config or DummyConfig()
        svc = ControlService(
            camera_service=camera,
            motor_service=motor,
            model_service=model,
            recorder_service=recorder,
            algorithms=algorithms,
            config_store=config,
            loop_hz=20,
        )
        return svc, camera, motor, recorder, config

    def test_invalid_manual_inputs_fail_safe_without_partial_mutation(self):
        for bad in ("bad", object(), "NaN", float("nan"), "Infinity", "-Infinity", True):
            with self.subTest(value=str(bad)):
                svc, _, motor, _, _ = self.build_service()
                svc.set_manual_controls(steering=0.25, throttle=-0.5)
                ok, _ = svc.set_manual_controls(steering=0.7, throttle=bad)
                self.assertFalse(ok)
                self.assertTrue(svc.state.safety_stop)
                self.assertEqual(svc.state.manual_steering, 0.0)
                self.assertEqual(svc.state.manual_throttle, 0.0)
                self.assertIsNone(svc._manual_command_at)
                self.assertGreaterEqual(motor.stop_calls, 1)

    def test_invalid_runtime_inputs_keep_previous_config_and_engage_stop(self):
        svc, _, motor, _, _ = self.build_service()
        svc.state.max_throttle = 0.6
        svc.state.steer_mix = 0.3
        ok, _ = svc.set_runtime_parameters(max_throttle="nope", steer_mix=0.9)
        self.assertFalse(ok)
        self.assertEqual(svc.state.max_throttle, 0.6)
        self.assertEqual(svc.state.steer_mix, 0.3)
        self.assertTrue(svc.state.safety_stop)
        self.assertGreaterEqual(motor.stop_calls, 1)

    def test_processing_toggle_only_updates_on_change(self):
        svc, camera, motor, recorder, _ = self.build_service()
        svc.running = True
        recorder.recording = False
        camera.processing_enabled_calls.clear()

        original_sleep = __import__("time").sleep
        import time as _time
        calls = {"n": 0}

        def fake_sleep(_):
            calls["n"] += 1
            if calls["n"] >= 2:
                svc.running = False

        _time.sleep = fake_sleep
        try:
            svc._loop()
        finally:
            _time.sleep = original_sleep
        self.assertEqual(camera.processing_enabled_calls, [False])
        self.assertGreaterEqual(len(motor.update_calls), 1)

    def test_algorithm_exception_falls_back_to_zero_outputs(self):
        svc, camera, motor, recorder, _ = self.build_service(
            algorithms={"manual": ManualAlgo(), "boom": BoomAlgo()}
        )
        svc.state.active_algorithm = "boom"
        svc.running = True

        original_sleep = __import__("time").sleep
        import time as _time

        def fake_sleep(_):
            svc.running = False

        _time.sleep = fake_sleep
        try:
            svc._loop()
        finally:
            _time.sleep = original_sleep

        self.assertEqual(svc.state.applied_steering, 0.0)
        self.assertEqual(svc.state.applied_throttle, 0.0)
        self.assertEqual(svc.state.motor_left, 0.0)
        self.assertEqual(svc.state.motor_right, 0.0)
        self.assertIn("Algorithm error", svc.state.system_message)

    def test_motor_exception_hard_stops_and_zeros_applied_output(self):
        svc, *_ = self.build_service(motor=DummyMotor(fail=True))
        svc.state.manual_throttle = 0.4
        svc.running = True

        original_sleep = __import__("time").sleep
        import time as _time

        def fake_sleep(_):
            svc.running = False

        _time.sleep = fake_sleep
        try:
            svc._loop()
        finally:
            _time.sleep = original_sleep

        self.assertEqual(svc.state.applied_steering, 0.0)
        self.assertEqual(svc.state.applied_throttle, 0.0)
        self.assertEqual(svc.state.motor_left, 0.0)
        self.assertEqual(svc.state.motor_right, 0.0)
        self.assertIn("Motor update failed", svc.state.system_message)

    def test_camera_apply_invalidates_processing_cache(self):
        svc, camera, *_ = self.build_service(config=DummyConfig({"camera": {"width": 320}}))
        svc._processing_enabled_cached = True
        svc.apply_runtime_config({"camera": {"width": 640}}, initial=False)
        self.assertEqual(camera.apply_settings_calls[-1], ({"width": 640}, True))
        self.assertIsNone(svc._processing_enabled_cached)

    def test_runtime_steer_bias_is_applied_and_persisted(self):
        svc, _, motor, _, config = self.build_service(config=DummyConfig({"steer_bias": 0.15}))
        self.assertAlmostEqual(svc.state.steer_bias, 0.15)
        ok, _ = svc.set_runtime_parameters(steer_bias=0.2)
        self.assertTrue(ok)
        self.assertAlmostEqual(svc.state.steer_bias, 0.2)
        svc.set_manual_controls(steering=0.1, throttle=0.0)
        svc.running = True

        original_sleep = __import__("time").sleep
        import time as _time

        def fake_sleep(_):
            svc.running = False

        _time.sleep = fake_sleep
        try:
            svc._loop()
        finally:
            _time.sleep = original_sleep

        self.assertGreaterEqual(len(motor.update_calls), 1)
        steer, throttle, _ = motor.update_calls[-1]
        self.assertAlmostEqual(steer, 0.3, places=6)
        saved = svc.get_runtime_config()
        self.assertAlmostEqual(saved["steer_bias"], 0.2)


    def run_one_tick(self, svc):
        svc.running = True
        with patch("piserver.services.control_service.time.sleep", side_effect=lambda _: setattr(svc, "running", False)):
            svc._loop()


    def test_zero_manual_command_never_uses_bias_to_spin_motors(self):
        svc, _, motor, _, _ = self.build_service(config=DummyConfig({"steer_bias": 0.25}))
        svc.set_manual_controls(steering=0, throttle=0.5)
        self.run_one_tick(svc)
        self.assertNotEqual(motor.update_calls[-1][0], 0.0)
        svc.set_manual_controls(steering=0, throttle=0)
        self.run_one_tick(svc)
        self.assertEqual(motor.update_calls[-1][:2], (0.0, 0.0))

    def test_finite_controls_still_clamp_and_reverse_works(self):
        svc, _, motor, _, _ = self.build_service()
        ok, _ = svc.set_manual_controls(steering=7, throttle=-9)
        self.assertTrue(ok)
        self.assertEqual(svc.state.manual_steering, 1.0)
        self.assertEqual(svc.state.manual_throttle, -1.0)
        self.run_one_tick(svc)
        self.assertEqual(motor.update_calls[-1][1], -0.55)

    def test_algorithm_validation_is_atomic(self):
        svc, *_ = self.build_service()
        svc.set_manual_controls(steering=0.1, throttle=0.2)
        ok, msg = svc.apply_control_update({
            "algorithm": "does-not-exist", "steering": -0.9, "throttle": -1,
            "max_throttle": 1, "current_page": "auto"
        })
        self.assertFalse(ok)
        self.assertIn("Unknown algorithm", msg)
        self.assertEqual(svc.state.manual_steering, 0.1)
        self.assertEqual(svc.state.manual_throttle, 0.2)
        self.assertEqual(svc.state.max_throttle, 0.55)
        self.assertEqual(svc.state.current_page, "manual")

    def test_invalid_numeric_runtime_update_is_atomic(self):
        svc, *_ = self.build_service()
        ok, _ = svc.apply_control_update({
            "steering": 0.3, "throttle": 0.4, "max_throttle": "NaN", "steer_bias": 0.4
        })
        self.assertFalse(ok)
        self.assertEqual(svc.state.max_throttle, 0.55)
        self.assertEqual(svc.state.steer_bias, 0.0)
        self.assertEqual(svc.state.manual_throttle, 0.0)
        self.assertTrue(svc.state.safety_stop)

    def test_manual_command_expires_without_new_packet(self):
        svc, _, motor, _, _ = self.build_service()
        with patch("piserver.services.control_service.time.monotonic", return_value=10.0):
            svc.set_manual_controls(steering=0.2, throttle=0.6)
        with patch("piserver.services.control_service.time.monotonic", return_value=10.2):
            self.run_one_tick(svc)
            status = svc.snapshot()
        self.assertAlmostEqual(motor.update_calls[-1][1], 0.55)
        self.assertAlmostEqual(status["manual_command_age_s"], 0.2)
        self.assertFalse(status["manual_command_timed_out"])
        with patch("piserver.services.control_service.time.monotonic", return_value=10.9):
            self.run_one_tick(svc)
            status = svc.snapshot()
        self.assertEqual(motor.update_calls[-1][:2], (0.0, 0.0))
        self.assertEqual(svc.state.manual_throttle, 0.0)
        self.assertTrue(status["manual_command_timed_out"])
        self.assertIsNone(status["manual_command_age_s"])
        with patch("piserver.services.control_service.time.monotonic", return_value=11.0):
            self.run_one_tick(svc)
        self.assertEqual(motor.update_calls[-1][:2], (0.0, 0.0))

    def test_heartbeat_renews_lease_without_latching_stale_commands(self):
        svc, _, motor, _, _ = self.build_service()
        with patch("piserver.services.control_service.time.monotonic", return_value=10.0):
            svc.set_manual_controls(steering=0, throttle=0.4)
        with patch("piserver.services.control_service.time.monotonic", return_value=10.65):
            svc.set_manual_controls(steering=0, throttle=0.4)
        with patch("piserver.services.control_service.time.monotonic", return_value=11.0):
            self.run_one_tick(svc)
        self.assertAlmostEqual(motor.update_calls[-1][1], 0.4)

    def test_estop_with_steer_bias_is_zero_and_requires_new_control(self):
        svc, _, motor, _, _ = self.build_service(config=DummyConfig({"steer_bias": 0.2}))
        svc.set_manual_controls(steering=0.3, throttle=0.5)
        svc.set_safety_stop(True)
        self.run_one_tick(svc)
        self.assertEqual(motor.update_calls[-1][:2], (0.0, 0.0))
        self.assertFalse(svc.set_safety_stop(False))
        self.assertTrue(svc.state.safety_stop)
        self.run_one_tick(svc)
        self.assertEqual(motor.update_calls[-1][:2], (0.0, 0.0))
        # run_one_tick simulates loop shutdown; explicit rearm requires running.
        svc.running = True
        ok, _ = svc.rearm_safety(confirm=True)
        self.assertTrue(ok)
        self.assertFalse(svc.state.safety_stop)
        self.run_one_tick(svc)
        self.assertEqual(motor.update_calls[-1][:2], (0.0, 0.0))
        svc.set_manual_controls(steering=0.1, throttle=0.5)
        self.run_one_tick(svc)
        self.assertGreater(motor.update_calls[-1][1], 0)

    def test_algorithm_exception_with_steer_bias_stays_zero(self):
        svc, _, motor, _, _ = self.build_service(
            algorithms={"manual": ManualAlgo(), "boom": BoomAlgo()},
            config=DummyConfig({"steer_bias": 0.3})
        )
        svc.select_algorithm("boom")
        self.run_one_tick(svc)
        self.assertEqual(motor.update_calls[-1][:2], (0.0, 0.0))



if __name__ == "__main__":
    unittest.main()
