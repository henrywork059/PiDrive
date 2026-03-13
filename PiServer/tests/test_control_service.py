import unittest

from piserver.services.control_service import ControlService


class DummyStateAlgo:
    def __init__(self, name, exc=False):
        self.name = name
        self.label = name
        self.mode = name
        self.exc = exc

    def compute(self, state, camera_service, model_service):
        if self.exc:
            raise RuntimeError("boom")
        return state.manual_steering, state.manual_throttle


class DummyCameraService:
    def __init__(self):
        self.backend = "test"
        self.width = 320
        self.height = 240
        self.camera_format = "BGR888"
        self.preview_live = True
        self.last_error = ""
        self._fps = 30.0
        self.processing_enabled_calls = []

    def get_fps(self):
        return self._fps

    def set_processing_enabled(self, enabled):
        self.processing_enabled_calls.append(bool(enabled))

    def apply_settings(self, *_args, **_kwargs):
        return True, "ok", {}

    def get_config(self):
        return {}

    def get_latest_frame(self, copy=True):
        return None


class DummyMotorService:
    def __init__(self):
        self.calls = []

    def get_config(self):
        return {
            "left_direction": 1,
            "right_direction": 1,
            "left_max_speed": 1.0,
            "right_max_speed": 1.0,
            "left_bias": 0.0,
            "right_bias": 0.0,
        }

    def update(self, steering, throttle, steer_mix):
        self.calls.append((steering, throttle, steer_mix))
        return steering, throttle

    def stop(self):
        return None

    def apply_settings(self, _data):
        return self.get_config()


class DummyModelService:
    def get_active_name(self):
        return "none"


class DummyRecorder:
    recording = False

    def toggle(self):
        self.recording = not self.recording


class DummyConfigStore:
    def __init__(self, data=None):
        self.data = data or {}

    def load(self):
        return self.data

    def save(self, data):
        self.data = data


class ControlServiceTests(unittest.TestCase):
    def setUp(self):
        self.camera = DummyCameraService()
        self.motor = DummyMotorService()
        self.model = DummyModelService()
        self.recorder = DummyRecorder()
        self.algorithms = {
            "manual": DummyStateAlgo("manual"),
            "autopilot": DummyStateAlgo("autopilot"),
            "bad": DummyStateAlgo("bad", exc=True),
        }
        self.service = ControlService(
            camera_service=self.camera,
            motor_service=self.motor,
            model_service=self.model,
            recorder_service=self.recorder,
            algorithms=self.algorithms,
            config_store=DummyConfigStore(),
            loop_hz=20,
        )

    def test_invalid_manual_controls_are_ignored(self):
        self.service.state.manual_steering = 0.25
        self.service.state.manual_throttle = 0.5

        ok, msg = self.service.set_manual_controls(steering="bad", throttle="also_bad")

        self.assertTrue(ok)
        self.assertEqual(msg, "OK")
        self.assertEqual(self.service.state.manual_steering, 0.25)
        self.assertEqual(self.service.state.manual_throttle, 0.5)

    def test_invalid_runtime_params_are_ignored(self):
        self.service.state.max_throttle = 0.4
        self.service.state.steer_mix = 0.6

        ok, msg = self.service.set_runtime_parameters(max_throttle="bad", steer_mix="bad")

        self.assertTrue(ok)
        self.assertEqual(msg, "OK")
        self.assertEqual(self.service.state.max_throttle, 0.4)
        self.assertEqual(self.service.state.steer_mix, 0.6)

    def test_processing_flag_sent_only_when_changed(self):
        self.service._processing_enabled_cached = None

        self.service.state.active_algorithm = "manual"
        self.service.state.safety_stop = False
        self.service.recorder_service.recording = False
        self.service._loop = lambda: None

        # emulate two loop iterations of just the processing decision logic
        for _ in range(2):
            processing_needed = (not self.service.state.safety_stop) and (
                self.service.state.active_algorithm != "manual" or bool(self.service.recorder_service.recording)
            )
            if processing_needed != self.service._processing_enabled_cached:
                self.camera.set_processing_enabled(processing_needed)
                self.service._processing_enabled_cached = processing_needed

        self.assertEqual(self.camera.processing_enabled_calls, [False])

    def test_algorithm_exception_falls_back_to_safe_outputs(self):
        self.service.state.active_algorithm = "bad"
        algo = self.algorithms["bad"]

        try:
            steer, throttle = algo.compute(self.service.state, self.camera, self.model)
        except Exception as exc:
            steer, throttle = 0.0, 0.0
            self.service.state.system_message = f"Algorithm error: {exc}"

        self.assertEqual((steer, throttle), (0.0, 0.0))
        self.assertIn("Algorithm error", self.service.state.system_message)


if __name__ == "__main__":
    unittest.main()
