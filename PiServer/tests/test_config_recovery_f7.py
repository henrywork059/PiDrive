"""Test actual config endpoints with hardware-free fixtures."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_control_service import DummyCamera, DummyMotor, DummyModel, DummyRecorder, ManualAlgo
from piserver.core.config_store import ConfigStore
from piserver.services.control_service import ControlService


class ConfigRecoveryApiTests(unittest.TestCase):
    def test_corrupt_reload_keeps_runtime_and_stop_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.json"
            store = ConfigStore(path)
            store.save({"max_throttle": 0.32})
            camera, motor, model, recorder = DummyCamera(), DummyMotor(), DummyModel(), DummyRecorder()
            camera.start = camera.stop = lambda: None
            motor.close = lambda: None
            with (
                patch.dict("os.environ", {"PISERVER_ACCESS_TOKEN": ""}),
                patch("piserver.app.CameraService", return_value=camera),
                patch("piserver.app.MotorService", return_value=motor),
                patch("piserver.app.ModelService", return_value=model),
                patch("piserver.app.RecorderService", return_value=recorder),
                patch("piserver.app.ConfigStore", return_value=store),
                patch("piserver.app.build_registry", return_value={"manual": ManualAlgo()}),
                patch.object(ControlService, "start", lambda self: None),
            ):
                from piserver.app import create_app
                app = create_app()
            with app.test_client() as client:
                raw = b'{"camera":'
                path.write_bytes(raw)
                reply = client.post("/api/config/reload")
                self.assertEqual(reply.status_code, 409)
                self.assertTrue(reply.json["config_recovery"]["load_failed"])
                status = client.get("/api/status").json
                self.assertAlmostEqual(status["max_throttle"], 0.32)
                self.assertTrue(status["config_recovery"]["warning"])
                self.assertEqual(path.read_bytes(), raw)
                self.assertEqual(client.post("/api/system/estop", json={}).status_code, 200)
                with patch("piserver.core.config_recovery.os.replace", side_effect=OSError("disk failure")):
                    self.assertEqual(client.post("/api/config/save").status_code, 500)
                self.assertEqual(path.read_bytes(), raw)
                self.assertEqual(client.post("/api/config/save").status_code, 200)
                self.assertEqual((path.parent / store.recovery_status()["backup"]).read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
