from __future__ import annotations

import unittest
from unittest import mock

from piserver.services.camera_service import CameraService


class DummyFrame:
    def __init__(self, token: str):
        self.token = token

    def copy(self):
        return DummyFrame(self.token)


class CameraServiceTests(unittest.TestCase):
    def test_capture_snapshot_frame_uses_direct_picamera_capture_when_raw_cache_missing(self):
        svc = CameraService()
        svc._picam2 = object()
        direct = DummyFrame("live")
        with mock.patch.object(svc, "_capture_picamera_request", return_value=(direct, None, True, "")) as patched:
            frame = svc.capture_snapshot_frame(retries=0, delay_s=0.0, copy=True)
        self.assertIsNotNone(frame)
        self.assertIsInstance(frame, DummyFrame)
        self.assertEqual(frame.token, "live")
        self.assertIsNot(frame, direct)
        self.assertIs(svc._raw_frame, direct)
        patched.assert_called_once_with(True, False)

    def test_capture_snapshot_frame_prefers_existing_raw_frame(self):
        svc = CameraService()
        raw = DummyFrame("cached")
        svc._raw_frame = raw
        with mock.patch.object(svc, "_capture_picamera_request") as patched:
            frame = svc.capture_snapshot_frame(retries=0, delay_s=0.0, copy=True)
        self.assertIsNotNone(frame)
        self.assertIsInstance(frame, DummyFrame)
        self.assertEqual(frame.token, "cached")
        self.assertIsNot(frame, raw)
        patched.assert_not_called()


if __name__ == "__main__":
    unittest.main()
