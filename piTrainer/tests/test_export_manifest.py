import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from piTrainer.app_state import TrainConfig, ExportConfig
from piTrainer.services.export import export_service as m
from piTrainer.utils.model_manifest import inspect_manifest, manifest_path

class ExportManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        self.train=TrainConfig(img_w=160,img_h=120,seed=27)
        self.config=ExportConfig(out_dir=str(self.folder),base_name='robot',export_keras=True,export_tflite=True,quantize_int8=False)

    @staticmethod
    def fake_keras(model,path,notes=()):
        path.write_bytes(b'keras-checksum-contents')
        return m.ExportArtifact(str(path),'.keras',path.stat().st_size)

    @staticmethod
    def fake_tflite(model,path,quantize,representative_ds,notes=()):
        path.write_bytes(b'TFL3-data')
        return m.ExportArtifact(str(path),'.tflite',path.stat().st_size)

    def test_each_artifact_has_typed_sidecar(self):
        with patch.object(m,'save_keras_model',side_effect=self.fake_keras),patch.object(m,'export_tflite_model',side_effect=self.fake_tflite):
            artifacts=m.export_model_artifacts(None,self.config,None,self.train)
        self.assertEqual(len(artifacts),2)
        for artifact in artifacts:
            model_path=Path(artifact.path)
            self.assertTrue(manifest_path(model_path).is_file())
            md,status=inspect_manifest(model_path,expected_kind='steering_control',input_size=(160,120))
            self.assertEqual(md['training_seed'],27)
            self.assertEqual(md['output']['interpretation'],'steering_throttle')

    def test_int8_export_records_dynamic_io_optimization(self):
        self.config.export_keras=False;self.config.quantize_int8=True
        with patch.object(m,'build_representative_dataset',return_value=None),patch.object(m,'export_tflite_model',side_effect=self.fake_tflite):
            artifacts=m.export_model_artifacts(None,self.config,None,self.train)
        md,_=inspect_manifest(Path(artifacts[0].path))
        self.assertEqual(md['quantization']['mode'],'dynamic')

    def test_sidecar_failure_is_reported_not_success(self):
        self.config.export_keras=False
        with patch.object(m,'export_tflite_model',side_effect=self.fake_tflite),patch.object(m,'write_manifest',side_effect=OSError('full drive')):
            with self.assertRaisesRegex(RuntimeError,'manifest'):
                m.export_model_artifacts(None,self.config,None,self.train)

if __name__=='__main__':unittest.main()
