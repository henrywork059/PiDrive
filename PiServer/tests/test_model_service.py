from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from piserver.services.model_service import ModelService


class DummyUpload:
    def __init__(self, filename: str, payload: bytes):
        self.filename = filename
        self.payload = payload

    def save(self, target):
        Path(target).write_bytes(self.payload)


class ModelServiceTests(unittest.TestCase):
    def test_save_uploaded_model_uses_basename_and_rejects_bad_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            svc = ModelService(tmp)
            ok, msg = svc.save_uploaded_model(DummyUpload("../nested/test_model.tflite", b"123"))
            self.assertTrue(ok)
            self.assertEqual(msg, "test_model.tflite")
            self.assertTrue((Path(tmp) / "test_model.tflite").exists())

            ok, msg = svc.save_uploaded_model(DummyUpload("not_model.txt", b"123"))
            self.assertFalse(ok)
            self.assertIn("Only .tflite", msg)


if __name__ == "__main__":
    unittest.main()
