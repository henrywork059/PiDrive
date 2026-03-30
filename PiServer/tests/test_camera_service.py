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

    def test_apply_settings_accepts_awb_alias_for_web_compatibility(self):
        svc = CameraService()
        svc.auto_white_balance = True
        ok, _message, config = svc.apply_settings({"awb": False}, restart=False)
        self.assertTrue(ok)
        self.assertFalse(svc.auto_white_balance)
        self.assertFalse(config["auto_white_balance"])
        self.assertFalse(config["awb"])

    def test_apply_settings_accepts_manual_colour_gain_aliases(self):
        svc = CameraService()
        ok, _message, config = svc.apply_settings({"colour_gain_red": 0.72, "blue_gain": 1.18}, restart=False)
        self.assertTrue(ok)
        self.assertAlmostEqual(svc.color_gain_red, 0.72)
        self.assertAlmostEqual(svc.color_gain_blue, 1.18)
        self.assertAlmostEqual(config["color_gain_red"], 0.72)
        self.assertAlmostEqual(config["color_gain_blue"], 1.18)

    def test_set_picamera_controls_sends_manual_colour_gains_when_awb_disabled(self):
        svc = CameraService()
        fake_picam = mock.Mock()
        svc._picam2 = fake_picam
        svc.auto_white_balance = False
        svc.color_gain_red = 0.68
        svc.color_gain_blue = 1.24
        svc._set_picamera_controls_locked()
        controls = fake_picam.set_controls.call_args.args[0]
        self.assertEqual(controls["AwbEnable"], False)
        self.assertEqual(controls["ColourGains"], (0.68, 1.24))

    def test_set_picamera_controls_omits_manual_colour_gains_when_awb_enabled(self):
        svc = CameraService()
        fake_picam = mock.Mock()
        svc._picam2 = fake_picam
        svc.auto_white_balance = True
        svc._set_picamera_controls_locked()
        controls = fake_picam.set_controls.call_args.args[0]
        self.assertEqual(controls["AwbEnable"], True)
        self.assertNotIn("ColourGains", controls)

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

    def test_capture_snapshot_frame_refreshes_live_picamera_frame_instead_of_reusing_stale_cache(self):
        svc = CameraService()
        svc._picam2 = object()
        stale = DummyFrame("first")
        svc._raw_frame = stale
        svc._raw_frame_time = 123.0
        fresh = DummyFrame("second")
        with mock.patch.object(svc, "_capture_picamera_request", return_value=(fresh, None, True, "")) as patched:
            frame = svc.capture_snapshot_frame(retries=0, delay_s=0.0, copy=True)
        self.assertIsNotNone(frame)
        self.assertEqual(frame.token, "second")
        self.assertIs(svc._raw_frame, fresh)
        patched.assert_called_once_with(True, False)

    def test_capture_snapshot_frame_uses_fresh_raw_cache_when_direct_capture_is_unavailable(self):
        svc = CameraService()
        fresh = DummyFrame("cached")
        svc._raw_frame = fresh
        svc._raw_frame_time = 10.0
        with mock.patch.object(svc, "_capture_picamera_request") as patched, \
             mock.patch("piserver.services.camera_service.time.time", return_value=10.2):
            frame = svc.capture_snapshot_frame(retries=0, delay_s=0.0, copy=True, max_cache_age_s=0.5)
        self.assertIsNotNone(frame)
        self.assertEqual(frame.token, "cached")
        patched.assert_not_called()

    def test_capture_snapshot_frame_does_not_use_stale_raw_cache_without_new_live_capture(self):
        svc = CameraService()
        stale = DummyFrame("old")
        svc._raw_frame = stale
        svc._raw_frame_time = 10.0
        with mock.patch.object(svc, "_capture_picamera_request") as patched, \
             mock.patch("piserver.services.camera_service.time.time", return_value=11.0):
            frame = svc.capture_snapshot_frame(retries=0, delay_s=0.0, copy=True, max_cache_age_s=0.5)
        self.assertIsNone(frame)
        patched.assert_not_called()


if __name__ == "__main__":
    unittest.main()
