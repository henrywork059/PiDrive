"""Opt-in native lores preview, safe fallback, request ownership and bounded-slot diagnostics."""
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
from piserver.services import camera_service as cam


class Request:
    def __init__(self, size, fail=False):
        self.size, self.fail, self.releases = size, fail, 0
        self.lores_calls, self.main_calls = 0, 0

    def make_array(self, name):
        self.lores_calls += 1
        if self.fail:
            raise ValueError("lores unavailable")
        w, h = self.size
        return np.full((h * 3 // 2, w), 128, dtype=np.uint8)

    def make_image(self, name):
        self.main_calls += 1
        return Image.new('RGB', (426, 240), (20, 80, 140))

    def release(self):
        self.releases += 1


class Camera:
    instances = []
    reject = False
    def __init__(self):
        self.__class__.instances.append(self)
        self.cfg, self.closed, self.requests = {}, False, []

    def create_video_configuration(self, **kw):
        if self.__class__.reject and 'lores' in kw:
            raise ValueError("unsupported")
        self.cfg = kw
        return kw

    def configure(self, cfg):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def close(self):
        self.closed = True

    def set_controls(self, controls):
        pass

    def capture_request(self):
        req = Request(self.cfg.get('lores', {'size': (320, 180)})['size'])
        self.requests.append(req)
        return req


class PreviewResourceTests(unittest.TestCase):
    def setUp(self):
        Camera.instances = []
        Camera.reject = False
        self.service = cam.CameraService()

    def tearDown(self):
        self.service._release_backends_locked()

    def test_default_and_opt_in_request_ownership(self):
        with patch.object(cam, 'Picamera2', Camera):
            self.assertTrue(self.service._open_picamera2_locked()[0])
            self.assertNotIn('lores', Camera.instances[-1].cfg)
            self.service._release_backends_locked()
            self.service.apply_settings({'preview_source': 'lores', 'preview_stream_width': 320}, restart=False)
            self.assertTrue(self.service._open_picamera2_locked()[0])
        obj = Camera.instances[-1]
        self.assertEqual(obj.cfg['lores'], {'format': 'YUV420', 'size': (320, 180)})
        frame, data, live, error = self.service._capture_picamera_request(True, True)
        self.assertTrue(live)
        self.assertEqual(frame.shape, (240, 426, 3))
        self.assertTrue(frame.flags.writeable)
        self.assertTrue(data.startswith(b'\xff\xd8'))
        self.assertEqual((obj.requests[0].lores_calls, obj.requests[0].main_calls, obj.requests[0].releases), (1, 1, 1))

    def test_configuration_rejection_does_not_leave_open_request(self):
        self.service.apply_settings({'preview_source': 'lores'}, restart=False)
        Camera.reject = True
        with patch.object(cam, 'Picamera2', Camera):
            self.assertTrue(self.service._open_picamera2_locked()[0])
        self.assertTrue(Camera.instances[0].closed)
        self.assertEqual(self.service.get_config()['preview_stream_active'], 'main')
        self.assertTrue(self.service.get_config()['preview_stream_fallback_reason'])

    def test_failed_capture_circuit_breaks_and_falls_back(self):
        self.service.apply_settings({'preview_source': 'lores'}, restart=False)
        with patch.object(cam, 'Picamera2', Camera):
            self.assertTrue(self.service._open_picamera2_locked()[0])
        obj = Camera.instances[-1]
        native = obj.capture_request
        def bad_capture():
            req = native()
            req.fail = True
            return req
        obj.capture_request = bad_capture
        self.assertTrue(self.service._capture_picamera_request(False, True)[1].startswith(b'\xff\xd8'))
        self.assertTrue(self.service._capture_picamera_request(False, True)[1].startswith(b'\xff\xd8'))
        self.assertEqual([req.lores_calls for req in obj.requests], [1, 0])
        self.assertTrue(all(req.releases == 1 for req in obj.requests))
        self.assertEqual(self.service.get_config()['preview_stream_active'], 'main')

    def test_latest_frame_single_slot_and_skips(self):
        for value in [b'a', b'b', b'c', b'd']:
            self.service._publish_jpeg(value)
        self.assertEqual(self.service.wait_for_jpeg(last_seq=1, timeout=0), (b'd', 4))
        stats = self.service.get_preview_delivery_stats()
        self.assertEqual((stats['max_pending_frames'],stats['subscriber_skipped_frames'],
                          stats['latest_jpeg_bytes']), (1,2,1))
        self.assertIsNotNone(stats['latest_age_s'])


if __name__ == '__main__':
    unittest.main()
