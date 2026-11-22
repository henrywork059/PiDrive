"""Regression tests for session-safe YOLO train/val split and annotation QA."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import yaml

from custom_trainer.services.dataset_service import prepare_dataset_yaml
from custom_trainer.services.yolo_io import validate_yolo_label_file, read_yolo_label_file


class DatasetIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)

    def image(self, session: str, stem: str, payload: bytes, label: str | None = '0 0.50 0.50 0.20 0.20\n'):
        folder = self.root / session
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f'{stem}.jpg'
        path.write_bytes(payload)
        if label is not None:
            labels = folder / 'labels'
            labels.mkdir(exist_ok=True)
            (labels / f'{stem}.txt').write_text(label, encoding='utf-8')
        return path

    def prepare(self):
        yaml_path, created, summary = prepare_dataset_yaml(self.root / 'dataset.yaml', ['car', 'pedestrian'])
        spec = yaml.safe_load(yaml_path.read_text(encoding='utf-8'))
        def listing(name):
            content = (summary.cache_root / f'{name}.txt').read_text(encoding='utf-8')
            return [Path(line) for line in content.splitlines() if line]
        return summary, listing('train'), listing('val'), spec

    def test_session_groups_not_split_across_train_and_validation(self):
        for session, number in [('first', 5), ('second', 3), ('third', 2)]:
            for i in range(number):
                self.image(session, f'{i:03d}', f'{session}/{i}'.encode())
        summary, train, val, spec = self.prepare()
        self.assertEqual(len(train) + len(val), 10)
        self.assertEqual(len(train), summary.train_images)
        self.assertEqual(len(val), summary.val_images)
        self.assertTrue(summary.has_validation_holdout)
        self.assertFalse(set(train) & set(val))
        def names(paths):
            return {p.relative_to(summary.cache_root / 'images').parts[0] for p in paths}
        self.assertFalse(names(train) & names(val))
        self.assertEqual(spec['nc'], 2)
        self.assertEqual(spec['names'], ['car', 'pedestrian'])
        self.assertEqual(len(summary.session_quality), 3)
        self.assertEqual(summary.total_instances, 10)

    def test_identical_frames_in_different_sessions_cannot_leak(self):
        self.image('a', 'one', b'shared-image')
        self.image('b', 'one', b'shared-image')
        self.image('c', 'one', b'completely-different')
        summary, train, val, _ = self.prepare()
        self.assertTrue(summary.has_validation_holdout)
        self.assertEqual(summary.duplicate_images, 1)
        self.assertEqual(len(train) + len(val), 3)
        hashes = lambda paths: {hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        self.assertFalse(hashes(train) & hashes(val))
        a_and_b = [p for p in train + val if p.parts[-2] in {'a', 'b'}]
        self.assertEqual(len(a_and_b), 2)
        self.assertTrue(all(p in train for p in a_and_b) or all(p in val for p in a_and_b))

    def test_one_image_has_no_fake_holdout(self):
        self.image('single', 'one', b'one')
        summary, train, val, spec = self.prepare()
        self.assertEqual((summary.train_images, summary.val_images), (1, 0))
        self.assertFalse(summary.has_validation_holdout)
        self.assertEqual(len(train), 1)
        self.assertEqual(val, [])
        self.assertIn('No independent validation holdout', summary.warnings[0])
        self.assertEqual(spec['val'], 'val.txt')

    def test_one_session_many_images_still_has_no_independent_holdout(self):
        for i in range(15):
            self.image('single', str(i), f'image-{i}'.encode())
        summary, train, val, _ = self.prepare()
        self.assertEqual(len(train), 15)
        self.assertEqual(len(val), 0)
        self.assertFalse(summary.has_validation_holdout)

    def test_all_duplicate_sessions_have_no_holdout(self):
        for session in ('a', 'b', 'c'):
            self.image(session, 'one', b'same')
        summary, train, val, _ = self.prepare()
        self.assertEqual((len(train), len(val)), (3, 0))
        self.assertEqual(summary.duplicate_images, 2)
        self.assertFalse(summary.has_validation_holdout)

    def test_split_is_repeatable(self):
        for session in ('one', 'two', 'three', 'four'):
            for i in range(3):
                self.image(session, f'{i}', f'{session}{i}'.encode())
        first, train_a, val_a, _ = self.prepare()
        second, train_b, val_b, _ = self.prepare()
        self.assertEqual([p.as_posix() for p in train_a], [p.as_posix() for p in train_b])
        self.assertEqual([p.as_posix() for p in val_a], [p.as_posix() for p in val_b])
        self.assertEqual(first.total_instances, second.total_instances)

    def test_bad_yolo_boxes_are_reported_without_silent_clamping(self):
        path = self.root / 'labels.txt'
        path.write_text('\n'.join([
            '# comment',
            '0 0.5 0.5 0.2 0.2',
            '1 0.5 0.5 0.4 0.4',
            '3 0.5 0.5 0.2 0.2',  # out-of-range class
            '0.5 0.5 0.5 0.2 0.2',  # fractional class id
            '-1 0.5 0.5 0.2 0.2',
            '0 nan 0.5 0.2 0.2',
            '0 inf 0.5 0.2 0.2',
            '0 -0.2 0.5 0.2 0.2',
            '0 0.05 0.5 0.2 0.2',  # box crosses image edge
            '0 0.5 0.5 0 0.2',
            '0 0.5 0.5 -0.1 0.2',
            '0 0.5 0.5 0.2 1.2',
            '0 0.5 0.5',
            '0 nope 0.5 0.2 0.2',
        ])+'\n',encoding='utf-8')
        boxes, issues = validate_yolo_label_file(path, 2)
        self.assertEqual(len(boxes), 2)
        self.assertEqual(len(issues), 12)
        self.assertTrue(all(issue.line >= 1 for issue in issues))
        reasons = ' '.join(issue.reason for issue in issues)
        for expected in ('class ID', 'NaN or infinity', 'beyond image boundaries', 'width/height', 'expected 5'):
            self.assertIn(expected, reasons)
        self.assertEqual(len(read_yolo_label_file(path)), 12)  # legacy UI reader remains unchanged

    def test_invalid_geometry_only_removed_from_derived_cache(self):
        invalid = '0 0.50 0.50 0.20 0.20\n1 0.05 0.50 0.20 0.20\n1 nan 0.1 0.2 0.2\n'
        img = self.image('one', 'img', b'a', label=invalid)
        self.image('two', 'img', b'b')
        summary, _, _, _ = self.prepare()
        self.assertEqual(summary.invalid_label_files, 1)
        self.assertEqual(summary.invalid_annotations, 2)
        self.assertEqual(summary.total_instances, 2)
        self.assertTrue(any('line 2:' in x for x in summary.annotation_issues))
        self.assertTrue(any('line 3:' in x for x in summary.annotation_issues))
        self.assertEqual((img.parent/'labels'/'img.txt').read_text(encoding='utf-8'),invalid)
        cache_txt = summary.cache_root / 'labels' / 'one' / 'img.txt'
        self.assertEqual(len(cache_txt.read_text(encoding='utf-8').splitlines()), 1)
        self.assertIn('invalid_boxes=2', summary.describe())

    def test_missing_and_invalid_annotations_counted_distinctly(self):
        self.image('a', 'empty', b'a', label=None)
        self.image('a', 'invalid', b'b', label='1 0.1 0.1 0.8 0.8\n')
        self.image('b', 'good', b'c')
        summary, _, _, _ = self.prepare()
        self.assertEqual(summary.empty_or_missing_labels, 1)
        self.assertEqual(summary.invalid_label_files, 1)
        self.assertEqual(summary.invalid_annotations, 1)
        self.assertEqual(summary.total_instances, 1)
        self.assertTrue(any('invalid_files=1' in x for x in summary.session_quality))

    def test_class_ids_follow_active_class_name_count(self):
        self.image('a','one',b'a',label='1 0.5 0.5 0.2 0.2\n')
        self.image('b','two',b'b',label='0 0.5 0.5 0.2 0.2\n')
        summary, _, _, spec = self.prepare()
        self.assertEqual(spec['names'], ['car','pedestrian'])
        self.assertEqual(summary.total_instances,2)
        self.assertEqual(summary.invalid_annotations,0)

    def test_valid_border_touching_box_remains_valid(self):
        p=self.root/'labels.txt'
        p.write_text('0 0.25 0.25 0.5 0.5\n')
        boxes,issues=validate_yolo_label_file(p,2)
        self.assertEqual(len(boxes),1)
        self.assertEqual(issues,[])


if __name__ == '__main__':
    unittest.main()
