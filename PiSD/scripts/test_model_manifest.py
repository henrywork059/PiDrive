import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pisd.core.model_manifest import make_manifest, write_manifest, inspect_manifest, manifest_path, validate_manifest

class ModelManifestTests(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory(); self.addCleanup(self.dir.cleanup)
        self.model=Path(self.dir.name)/'demo.tflite';self.model.write_bytes(b'TFL3\x00test-model')

    def make(self,kind='steering_control'):
        return make_manifest(self.model,model_kind=kind,width=160,height=120,
                             class_names=['car'] if kind=='yolo_detection' else [], training_seed=42)

    def test_legacy_accepted_with_warning(self):
        result,warning=inspect_manifest(self.model,expected_kind='steering_control');self.assertIsNone(result);self.assertIn('Legacy',warning)

    def test_steering_roundtrip(self):
        meta=self.make();write_manifest(self.model,meta)
        item,warning=inspect_manifest(self.model,expected_kind='steering_control',input_size=(160,120))
        self.assertEqual(item,meta);self.assertIn('verified',warning)

    def test_yolo_rejected_in_steering_runtime(self):
        write_manifest(self.model,self.make('yolo_detection'))
        with self.assertRaisesRegex(ValueError,'Wrong model family'):
            inspect_manifest(self.model,expected_kind='steering_control')

    def test_steering_rejected_in_detector(self):
        write_manifest(self.model,self.make())
        with self.assertRaisesRegex(ValueError,'Wrong model family'):
            inspect_manifest(self.model,expected_kind='yolo_detection')

    def test_checksum_mismatch(self):
        write_manifest(self.model,self.make());self.model.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'checksum'):
            inspect_manifest(self.model,expected_kind='steering_control')

    def test_wrong_geometry(self):
        write_manifest(self.model,self.make())
        with self.assertRaisesRegex(ValueError,'geometry'):
            inspect_manifest(self.model,expected_kind='steering_control',input_size=(320,320))

    def test_invalid_color_and_output(self):
        meta=self.make();meta['input']['color_order']='BGR'
        with self.assertRaisesRegex(ValueError,'color'):
            validate_manifest(meta)
        meta=self.make();meta['output']['interpretation']='yolo_boxes'
        with self.assertRaisesRegex(ValueError,'Output'):
            validate_manifest(meta)

    def test_manifest_write_failure_leaves_existing(self):
        write_manifest(self.model,self.make());before=manifest_path(self.model).read_bytes()
        with patch('pisd.core.model_manifest.os.replace',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):write_manifest(self.model,self.make())
        self.assertEqual(manifest_path(self.model).read_bytes(),before)
        self.assertFalse(list(Path(self.dir.name).glob('*.tmp')))

    def test_invalid_json_rejected(self):
        manifest_path(self.model).write_text('{broken')
        with self.assertRaisesRegex(ValueError,'unreadable'):
            inspect_manifest(self.model)

    def test_manifest_size_bounded(self):
        manifest_path(self.model).write_bytes(b'x' * (128 * 1024 + 1))
        with self.assertRaisesRegex(ValueError,'too large'):
            inspect_manifest(self.model)

if __name__=='__main__': unittest.main()
