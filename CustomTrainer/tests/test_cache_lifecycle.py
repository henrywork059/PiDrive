"""U25: immutable cache generations while training/validation read them."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from custom_trainer.services import dataset_service
from custom_trainer.services.cache_lifecycle import (
    MANIFEST, atomic_write_yaml, generation_reader_lease,
    list_cache_generations, prune_cache_generations,
)


class CacheLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name, payload in [('alpha', b'a-first'), ('beta', b'b-second'), ('gamma', b'c-third')]:
            folder = self.root / name
            folder.mkdir()
            (folder / 'frame.jpg').write_bytes(payload)
            labels = folder / 'labels'
            labels.mkdir()
            (labels / 'frame.txt').write_text('0 0.5 0.5 0.2 0.2\n', encoding='utf-8')

    def build(self):
        yaml_path, created, summary = dataset_service.prepare_dataset_yaml(self.root / 'dataset.yaml', ['road'])
        self.assertTrue(yaml_path.is_file())
        self.assertTrue(summary.cache_yaml_path.is_file())
        self.assertEqual(summary.cache_root, summary.cache_yaml_path.parent)
        return yaml_path, summary

    def test_generations_do_not_replace_active_readers(self):
        public, first = self.build()
        old_list = (first.cache_root / 'train.txt').read_text()
        first_yaml = first.cache_yaml_path.read_bytes()
        first_img = next((first.cache_root / 'images').rglob('*.jpg'))
        expected_data = first_img.read_bytes()
        second_public, second = self.build()
        self.assertEqual(public, second_public)
        self.assertNotEqual(first.cache_root, second.cache_root)
        self.assertTrue(first.cache_root.exists())
        self.assertEqual((first.cache_root / 'train.txt').read_text(), old_list)
        self.assertEqual(first.cache_yaml_path.read_bytes(), first_yaml)
        self.assertEqual(first_img.read_bytes(), expected_data)
        self.assertEqual(yaml.safe_load(public.read_text())['path'], second.cache_root.as_posix())
        self.assertEqual(yaml.safe_load(first_yaml)['path'], first.cache_root.as_posix())

    def test_image_bytes_are_copied_not_linked(self):
        _, old = self.build()
        image = old.cache_root / 'images' / 'alpha' / 'frame.jpg'
        original = image.read_bytes()
        src = self.root / 'alpha/frame.jpg'
        src.write_bytes(b'NEW IMAGE BYTES THAT MUST NOT AFFECT SNAPSHOT')
        self.assertEqual(image.read_bytes(), original)
        _, newer = self.build()
        self.assertEqual((newer.cache_root / 'images/alpha/frame.jpg').read_bytes(), src.read_bytes())
        self.assertEqual(image.read_bytes(), original)

    def test_manifest_lists_and_label_counts_match(self):
        _, summary = self.build()
        gen = summary.cache_root
        meta = json.loads((gen / MANIFEST).read_text())
        self.assertEqual(meta['images'], summary.total_images)
        self.assertEqual(meta['train'], summary.train_images)
        self.assertEqual(meta['val'], summary.val_images)
        self.assertEqual(meta['labeled_images'], summary.labeled_images)
        self.assertEqual(meta['labeled_images'], len(list((gen / 'labels').rglob('*.txt'))))
        train = (gen / 'train.txt').read_text().splitlines()
        val = (gen / 'val.txt').read_text().splitlines()
        self.assertEqual(len(set(train + val)), meta['images'])
        for path in train + val:
            self.assertTrue(Path(path).is_file())
            self.assertTrue(Path(path).is_relative_to(gen))

    def test_fault_mid_build_preserves_public_yaml_and_existing_cache(self):
        public, old = self.build()
        original_yaml = public.read_bytes()
        original_img = next((old.cache_root / 'images').rglob('*.jpg')).read_bytes()
        with patch.object(dataset_service, '_link_or_copy_file', side_effect=OSError('simulated disk full')):
            with self.assertRaisesRegex(OSError, 'simulated disk full'):
                self.build()
        self.assertEqual(public.read_bytes(), original_yaml)
        self.assertEqual(next((old.cache_root / 'images').rglob('*.jpg')).read_bytes(), original_img)
        self.assertFalse(list((self.root / '.customtrainer_yolo_cache/.building').iterdir()))

    def test_invalid_manifest_prevents_publish_and_keeps_old_cache(self):
        public, old = self.build()
        previous_yaml = public.read_bytes()
        with patch.object(dataset_service, 'publish_cache_generation', side_effect=ValueError('manifest validation failed')):
            with self.assertRaisesRegex(ValueError, 'manifest validation failed'):
                self.build()
        self.assertEqual(public.read_bytes(), previous_yaml)
        self.assertTrue(old.cache_root.is_dir())
        self.assertEqual(len(list_cache_generations(self.root)), 1)

    def test_failed_root_yaml_replace_preserves_old_pointer_and_existing_data(self):
        public, old = self.build()
        original = public.read_bytes()
        with patch('custom_trainer.services.cache_lifecycle.os.replace', side_effect=OSError('rename failed')):
            with self.assertRaisesRegex(OSError, 'rename failed'):
                self.build()
        self.assertEqual(public.read_bytes(), original)
        self.assertTrue(old.cache_root.is_dir())
        self.assertEqual(list(public.parent.glob('.dataset.yaml.*.tmp')), [])

    def test_reader_can_complete_while_second_generation_is_being_built(self):
        _, first = self.build()
        ready = threading.Event()
        release = threading.Event()
        results = []
        original_copy = dataset_service._link_or_copy_file
        def delayed_copy(src, dst):
            if not ready.is_set():
                ready.set()
                if not release.wait(timeout=3):
                    raise TimeoutError('test preparation blocked')
            original_copy(src, dst)
        def worker():
            try:
                with patch.object(dataset_service, '_link_or_copy_file', side_effect=delayed_copy):
                    _, second = self.build()
                results.append(second.cache_root)
            except BaseException as exc:
                results.append(exc)
        reader_yaml = first.cache_yaml_path.read_bytes()
        t = threading.Thread(target=worker)
        t.start()
        try:
            self.assertTrue(ready.wait(timeout=3))
            self.assertEqual(first.cache_yaml_path.read_bytes(), reader_yaml)
            for image in (first.cache_root / 'images').rglob('*.jpg'):
                self.assertTrue(image.is_file())
            with generation_reader_lease(first.cache_yaml_path):
                self.assertTrue(first.cache_root.exists())
        finally:
            release.set()
            t.join(timeout=5)
        self.assertFalse(t.is_alive())
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], Path, results)
        self.assertNotEqual(results[0], first.cache_root)

    def test_explicit_cleanup_does_not_delete_current_or_unmarked(self):
        generations = [self.build()[1] for _ in range(4)]
        legacy = self.root / '.customtrainer_yolo_cache/legacy-user-data'
        legacy.mkdir()
        (legacy / 'keep.txt').write_text('preserve')
        for item in generations:
            past = time.time()-48*3600
            os.utime(item.cache_root, (past,past))
        with self.assertRaisesRegex(ValueError, 'confirm-idle'):
            prune_cache_generations(self.root)
        removed = prune_cache_generations(self.root, confirm_idle=True)
        self.assertEqual(len(removed), 2)
        self.assertEqual(len(list_cache_generations(self.root)), 2)
        self.assertTrue(generations[-1].cache_root.is_dir())
        self.assertEqual((legacy / 'keep.txt').read_text(), 'preserve')

    @unittest.skipUnless(os.name=='posix', 'POSIX flock subprocess verification')
    def test_busy_external_reader_is_never_pruned(self):
        created = [self.build()[1] for _ in range(4)]
        for item in created:
            past=time.time()-48*3600
            os.utime(item.cache_root,(past,past))
        old = sorted(list_cache_generations(self.root), key=lambda e:e['created_utc'])[0]['path']
        code = '''import sys,time
from custom_trainer.services.cache_lifecycle import generation_reader_lease
with generation_reader_lease(sys.argv[1]):
 print('LEASED',flush=True)
 time.sleep(12)
'''
        env={**os.environ,'PYTHONPATH': str(Path(__file__).resolve().parents[1])}
        child=subprocess.Popen([sys.executable,'-c',code,str(old/'dataset.yaml')],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(),'LEASED')
            pruned=prune_cache_generations(self.root, confirm_idle=True)
            self.assertNotIn(old,pruned)
            self.assertTrue(old.exists())
        finally:
            child.kill()
            child.communicate(timeout=5)
        pruned=prune_cache_generations(self.root, confirm_idle=True)
        self.assertIn(old, pruned)

    def test_corrupt_generated_list_is_rejected_without_publishing(self):
        public, old = self.build()
        original = public.read_bytes()
        from custom_trainer.services.cache_lifecycle import publish_cache_generation, new_cache_generation
        staged, published = new_cache_generation(self.root)
        try:
            (staged / 'train.txt').write_text('/missing/stray.jpg\n')
            (staged / 'val.txt').write_text('')
            with self.assertRaisesRegex(ValueError, 'Generated image missing|outside generation'):
                publish_cache_generation(staged, published, {
                    'path': published.resolve().as_posix(), 'names':['road'], 'nc':1,
                    'train':'train.txt','val':'val.txt',
                }, image_count=1, valid_labels=0)
            self.assertFalse(published.exists())
            self.assertEqual(public.read_bytes(), original)
            self.assertTrue(old.cache_root.is_dir())
        finally:
            import shutil
            shutil.rmtree(staged, ignore_errors=True)

    def test_legacy_cache_directory_is_never_deleted_on_rebuild(self):
        old_dir = self.root / '.customtrainer_yolo_cache/images'
        old_dir.mkdir(parents=True)
        (old_dir / 'legacy-note.txt').write_text('keep')
        self.build()
        self.build()
        self.assertEqual((old_dir / 'legacy-note.txt').read_text(), 'keep')

    def test_cli_keeps_user_yamls_untouched(self):
        manual = self.root / 'manual.yaml'
        manual.write_text('path: /elsewhere\ntrain: custom.txt\n')
        with generation_reader_lease(manual):
            self.assertTrue(manual.exists())
        self.assertEqual(list_cache_generations(self.root),[])


if __name__ == '__main__':
    unittest.main()
