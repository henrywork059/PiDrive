import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pisd.app import create_app

class DestructiveTests(unittest.TestCase):
    def test_explicit_confirmation_required_and_stop_unaffected(self):
        with tempfile.TemporaryDirectory() as tmp, patch("pisd.app.RUNTIME_SETTINGS_PATH", Path(tmp)/"runtime.json"), patch.dict("os.environ", {"PISD_ACCESS_TOKEN": ""}):
            app = create_app(hardware_enabled=False)
            services = app.config["pisd_services"]
            try:
                client = app.test_client()
                for payload in ({}, {"confirm": False}, {"confirm": "true"}, {"confirm": 1}):
                    with patch.object(services["ai_drive"], "delete_model") as delete, patch.object(services["settings"], "reset") as reset:
                        self.assertEqual(client.post("/api/ai/delete-model", json={**payload, "model_id":"target.tflite"}).status_code, 400)
                        self.assertEqual(client.post("/api/settings/reset", json=payload).status_code, 400)
                        delete.assert_not_called()
                        reset.assert_not_called()
                with patch.object(services["ai_drive"], "delete_model", return_value={"ok": True}) as delete:
                    self.assertEqual(client.post("/api/ai/delete-model", json={"model_id":"target.tflite","confirm":True}).status_code, 200)
                    delete.assert_called_once_with("target.tflite")
                self.assertEqual(client.post("/api/control/stop").status_code, 200)
            finally:
                services["ai_drive"].close()
                services["motor"].close()
                services["camera"].stop()

if __name__ == "__main__":
    unittest.main()
