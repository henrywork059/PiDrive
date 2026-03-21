from __future__ import annotations

import unittest

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
            "steering_direction": 1,
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

    def test_invalid_manual_inputs_preserve_existing_values(self):
        svc, *_ = self.build_service()
        svc.state.manual_steering = 0.25
        svc.state.manual_throttle = -0.5
        ok, _ = svc.set_manual_controls("bad", None)
        self.assertTrue(ok)
        self.assertEqual(svc.state.manual_steering, 0.25)
        self.assertEqual(svc.state.manual_throttle, -0.5)
        svc.set_manual_controls(None, object())
        self.assertEqual(svc.state.manual_throttle, -0.5)

    def test_invalid_runtime_inputs_preserve_existing_values(self):
        svc, *_ = self.build_service()
        svc.state.max_throttle = 0.6
        svc.state.steer_mix = 0.3
        ok, _ = svc.set_runtime_parameters(max_throttle="nope", steer_mix=object())
        self.assertTrue(ok)
        self.assertEqual(svc.state.max_throttle, 0.6)
        self.assertEqual(svc.state.steer_mix, 0.3)

    def test_runtime_steer_bias_is_clamped_and_applied(self):
        svc, _, motor, _, _ = self.build_service()
        ok, _ = svc.set_runtime_parameters(steer_bias=1.2)
        self.assertTrue(ok)
        self.assertEqual(svc.state.steer_bias, 0.5)
        svc.state.manual_steering = 0.2
        svc.state.manual_throttle = 0.0
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

        steer, throttle, _ = motor.update_calls[-1]
        self.assertAlmostEqual(steer, 0.7)
        self.assertAlmostEqual(throttle, 0.0)

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


if __name__ == "__main__":
    unittest.main()
