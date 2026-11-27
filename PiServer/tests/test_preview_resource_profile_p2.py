from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
from piserver.services.camera_service import CameraService
from piserver.core.config_store import ConfigStore


class PreviewProfileTests(unittest.TestCase):
    def test_profile_restores_baseline_without_restart_or_capture_change(self):
        cam = CameraService()
        cam.apply_settings({'stream_quality':'manual','preview_fps':15,'preview_quality':80}, restart=False)
        cam._running = True
        frame = np.random.default_rng(17).integers(0,256,(240,426,3),dtype=np.uint8)
        baseline = cam._encode_preview_jpeg_cv(frame)
        baseline_pil = cam._jpeg_from_pil(Image.fromarray(frame))
        for processing in (False, True):
            cam.set_processing_enabled(processing)
            capture_fps = cam._desired_capture_fps_locked()
            with patch.object(cam, 'restart', side_effect=AssertionError('profile must not restart')):
                ok, _, active = cam.apply_settings({'preview_resource_profile':'economy'})
                self.assertTrue(ok)
                self.assertEqual((active['effective_preview_fps'],active['effective_preview_quality']), (6,40))
                self.assertEqual((active['preview_fps'],active['preview_quality']), (15,80))
                self.assertEqual(cam._desired_capture_fps_locked(),capture_fps)
                self.assertLess(len(cam._encode_preview_jpeg_cv(frame)),len(baseline))
                self.assertLess(len(cam._jpeg_from_pil(Image.fromarray(frame))),len(baseline_pil))
                self.assertFalse(cam.apply_settings({'preview_resource_profile':'invalid'})[0])
                self.assertEqual(cam.get_config()['preview_resource_profile'],'economy')
                ok, _, restored = cam.apply_settings({'preview_resource_profile':'standard'})
                self.assertTrue(ok)
                self.assertEqual((restored['effective_preview_fps'],restored['effective_preview_quality']),(15,80))
                self.assertEqual(cam._encode_preview_jpeg_cv(frame),baseline)
                self.assertEqual(cam._jpeg_from_pil(Image.fromarray(frame)),baseline_pil)
                self.assertEqual(cam._desired_capture_fps_locked(),capture_fps)
        cam._running=False

    def test_saved_profile_and_legacy_config_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            store=ConfigStore(Path(d)/'runtime.json')
            store.save({'camera':{'stream_quality':'manual','preview_fps':4,'preview_quality':30,'custom_key':7}})
            cam=CameraService()
            cam.apply_settings(store.load()['camera'],restart=False)
            self.assertEqual(cam.preview_resource_profile,'standard')
            cam.apply_settings({'preview_resource_profile':'economy'})
            store.save({'camera':cam.get_config()})
            fresh=CameraService()
            fresh.apply_settings(ConfigStore(store.path).load()['camera'],restart=False)
            self.assertEqual(fresh.preview_resource_profile,'economy')
            self.assertEqual((fresh._effective_preview_fps(),fresh._effective_preview_quality()),(4,30))
            self.assertEqual(store.load()['camera']['custom_key'],7)
            fresh.apply_settings({'preview_resource_profile':'standard'})
            self.assertEqual((fresh._effective_preview_fps(),fresh._effective_preview_quality()),(4,30))
