"""Hardware-free, on-disk current PiSD/PiServer/legacy recording contract."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from piTrainer.app_state import TrainConfig, ExportConfig
from piTrainer.services.data.session_service import list_sessions
from piTrainer.services.data.record_loader_service import load_records_dataframe, build_filtered_dataframe
from piTrainer.services.data.edit_service import update_frame_controls
from piTrainer.services.data.visibility_service import mark_record_hidden
from piTrainer.services.preprocess.preprocess_service import apply_preprocessing_recipe
from piTrainer.services.train.split_service import split_dataframe
from piTrainer.services.train.experiment_service import create_run_snapshot, finish_run, attach_model_artifact
from piTrainer.services.export import export_service
from piTrainer.services.validation.validation_provenance import file_context, stable_file_context, in_memory_context
from piTrainer.utils.model_manifest import inspect_manifest


def jsonl(path, rows):
    path.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')


class RecordingContractTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.current = self.root / 'recordings' / '2026-11-24' / 'pisd_manual'
        self.server = self.root / 'server_manual'
        self.legacy = self.root / 'legacy_manual'
        for folder, images in ((self.current, 'frames'), (self.server, 'images'), (self.legacy, 'images')):
            (folder / images).mkdir(parents=True)
            for i in range(3):
                Image.new('RGB', (16, 12), (i * 25, 100, 200)).save(folder / images / f'{i}.jpg')
        labels = [{'frame_id': f'f{i}', 'frame': f'frames/{i}.jpg',
                   'timestamp_utc': f'2026-11-24T00:00:0{i}Z',
                   'steering': .25, 'throttle': .5, 'mode': 'manual'} for i in range(3)]
        labels[-1] = mark_record_hidden(labels[-1])
        jsonl(self.current / 'labels.jsonl', labels)
        jsonl(self.current / 'records.jsonl', [
            {'frame_id': row['frame_id'], 'training_label': dict(row)} for row in labels])
        (self.current / 'manifest.json').write_text(json.dumps({'label':'manual_drive'}), encoding='utf-8')
        jsonl(self.server / 'records.jsonl', [{'frame_id':f'f{i}', 'ts':i, 'image':f'images/{i}.jpg',
            'steering':-.25, 'throttle':.5, 'mode':'manual'} for i in range(3)])
        jsonl(self.legacy / 'records.jsonl', [{'id':f'f{i}', 'image':f'images/{i}.jpg',
            'user/angle':.1, 'user/throttle':.5, 'mode':'manual'} for i in range(3)])
        self.names = list_sessions(self.root)

    def test_record_edit_hide_flip_split_export_and_provenance(self):
        self.assertEqual(set(self.names), {'2026-11-24/pisd_manual','server_manual','legacy_manual'})
        original = build_filtered_dataframe(load_records_dataframe(self.root,self.names), False)
        self.assertEqual(len(original),8)
        self.assertEqual(len(original[original.session=='2026-11-24/pisd_manual']),2)
        row = original[(original.session=='2026-11-24/pisd_manual') & (original.frame_id=='f0')].iloc[0]
        ok, _ = update_frame_controls(self.root, row.session, row.frame_id, row.abs_image, row.ts, .75, .5)
        self.assertTrue(ok)
        active = build_filtered_dataframe(load_records_dataframe(self.root,self.names),False)
        changed = active[(active.session==row.session)&(active.frame_id=='f0')].iloc[0]
        self.assertAlmostEqual(changed.steering,.75)
        self.assertAlmostEqual(active[(active.session=='server_manual')&(active.frame_id=='f0')].iloc[0].steering,-.25)
        recipe={'mirror_enabled':True,'require_images':True}
        expanded, summary = apply_preprocessing_recipe(active,recipe)
        self.assertEqual(len(expanded),16)
        self.assertEqual(summary['mirror_rows_added'],8)
        flipped = expanded[(expanded.session==row.session)&(expanded.source_frame_id=='f0')&expanded.aug_flip_lr]
        self.assertEqual(len(flipped),1)
        self.assertTrue(str(flipped.iloc[0].frame_id).startswith('s_'))
        self.assertAlmostEqual(flipped.iloc[0].steering,-.75)
        self.assertAlmostEqual(flipped.iloc[0].throttle,.5)
        config = TrainConfig(seed=27)
        train, val = split_dataframe(expanded,config)
        self.assertTrue(len(train) and len(val))
        self.assertFalse(set(train.abs_image)&set(val.abs_image))
        record = finish_run(create_run_snapshot(train,val,config,recipe,self.names),'succeeded',{'loss':[.5]})
        self.assertEqual(record['train_rows']+record['validation_rows'],16)
        self.assertIsNone(record['preprocessed_dataset_path'])
        self.assertTrue(record['preprocessing_sha256'])
        self.assertEqual(in_memory_context(record)['run_id'],record['run_id'])

        output = self.root / 'out'
        config_export = ExportConfig(out_dir=str(output),base_name='fixture',export_keras=False,export_tflite=True)
        def fake_export(model,path,quantize,representative_ds,notes=()):
            path.write_bytes(b'dummy-not-a-real-interpreter')
            return export_service.ExportArtifact(str(path),'.tflite',path.stat().st_size)
        with patch.object(export_service,'export_tflite_model',side_effect=fake_export):
            first = export_service.export_model_artifacts(None,config_export,train,config)[0]
            second = export_service.export_model_artifacts(None,config_export,train,config)[0]
        self.assertNotEqual(first.path,second.path)
        self.assertEqual(Path(first.path).read_bytes(),b'dummy-not-a-real-interpreter')
        manifest,_=inspect_manifest(Path(first.path),expected_kind='steering_control',input_size=(160,120))
        self.assertEqual(manifest['training_seed'],27)
        linked,_=attach_model_artifact(self.root,record,first.path)
        context=file_context(first.path)
        self.assertEqual(context['run_id'],linked['run_id'])
        self.assertEqual(context['model_sha256'],manifest['model_sha256'])
        self.assertIsNone(file_context(second.path)['run_id'])
        Path(first.path).write_bytes(b'tampered')
        self.assertIsNone(file_context(first.path)['run_id'])
        self.assertIsNone(stable_file_context(context,file_context(first.path))['run_id'])

    def test_missing_and_unsuccessful_memory_run_are_unknown(self):
        self.assertIsNone(in_memory_context(None)['run_id'])
        self.assertIsNone(in_memory_context({'run_id':'fake','status':'cancelled'})['run_id'])


if __name__ == '__main__':
    unittest.main()
