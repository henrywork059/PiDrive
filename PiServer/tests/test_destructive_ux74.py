import unittest
from unittest.mock import patch
from test_control_service import DummyCamera, DummyMotor, DummyModel, DummyRecorder, DummyConfig, ManualAlgo
from piserver.services.control_service import ControlService

class DestructiveTests(unittest.TestCase):
    def test_exact_model_confirmation_and_stop(self):
        camera, motor, model, recorder, config = DummyCamera(), DummyMotor(), DummyModel(), DummyRecorder(), DummyConfig()
        camera.start = camera.stop = motor.close = lambda: None
        with (
            patch.dict("os.environ", {"PISERVER_ACCESS_TOKEN": ""}),
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
        with app.test_client() as client, patch.object(model, "delete_model", create=True, return_value=(True, "Deleted target")) as delete, patch.object(model, "list_models", create=True, return_value=[]):
            for payload in ({}, {"confirm":"true"}, {"confirm":1}, {"filename":"../target.tflite","confirm":True}):
                self.assertEqual(client.post("/api/model/delete", json=payload).status_code, 400)
            delete.assert_not_called()
            self.assertEqual(client.post("/api/model/delete", json={"filename":"target.tflite","confirm":True}).status_code, 200)
            delete.assert_called_once_with("target.tflite")
            self.assertEqual(client.post("/api/system/estop", json={}).status_code, 200)
if __name__ == "__main__":
    unittest.main()
