from __future__ import annotations

import unittest
from importlib.util import find_spec
from unittest.mock import patch

from test_control_service import DummyCamera, DummyMotor, DummyModel, DummyRecorder, DummyConfig, ManualAlgo
from piserver.services.control_service import ControlService


@unittest.skipUnless(find_spec("flask") is not None, "Flask is required for API integration tests")
class ControlApiTests(unittest.TestCase):
    def test_api_validates_before_mutation_and_rejects_nonfinite(self):
        camera, motor, model, recorder, config = DummyCamera(), DummyMotor(), DummyModel(), DummyRecorder(), DummyConfig()
        camera.start = lambda: None
        camera.stop = lambda: None
        motor.close = lambda: None
        import piserver.app
        with (
            patch("piserver.app.CameraService", return_value=camera),
            patch("piserver.app.MotorService", return_value=motor),
            patch("piserver.app.ModelService", return_value=model),
            patch("piserver.app.RecorderService", return_value=recorder),
            patch("piserver.app.ConfigStore", return_value=config),
            patch("piserver.app.build_registry", return_value={"manual": ManualAlgo()}),
            patch.object(ControlService, "start", lambda self: None),
        ):
            from piserver.app import create_app
            app = create_app()
        with app.test_client() as client:
            reply = client.post("/api/control", json={"steering": 0.4, "throttle": 0.2, "algorithm": "unknown"})
            self.assertEqual(reply.status_code, 400)
            self.assertEqual(reply.json["state"]["manual_steering"], 0.0)
            self.assertEqual(reply.json["state"]["manual_throttle"], 0.0)

            reply = client.post("/api/control", json={"steering": 0.3, "throttle": 0.5})
            self.assertEqual(reply.status_code, 200)
            self.assertAlmostEqual(reply.json["manual_throttle"], 0.5)

            reply = client.post("/api/control", json={"steering": 0.8, "throttle": "NaN"})
            self.assertEqual(reply.status_code, 400)
            self.assertTrue(reply.json["state"]["safety_stop"])
            self.assertEqual(reply.json["state"]["manual_throttle"], 0.0)
            self.assertGreaterEqual(motor.stop_calls, 1)

            reply = client.post("/api/control", json=[{"throttle": 1}])
            self.assertEqual(reply.status_code, 400)


if __name__ == "__main__":
    unittest.main()
