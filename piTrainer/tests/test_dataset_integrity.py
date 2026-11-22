"""Regression tests for source-safe training splits and non-overwriting preprocess saves."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from piTrainer.app_state import TrainConfig
from piTrainer.services.preprocess import preprocess_service
from piTrainer.services.train.split_service import split_dataframe, split_by_rows, split_by_sequential_rows, split_by_session


class SourceSafeSplitTests(unittest.TestCase):
    @staticmethod
    def sample():
        rows = []
        for number in range(1, 9):
            session = 'session_a' if number <= 4 else 'session_b'
            source = f'frame_{number:06d}'
            for variant in ('original', 'horizontal_flip', 'color_mild_1'):
                rows.append({
                    'session': session,
                    'frame_id': source if variant == 'original' else f's_{source}_{variant}',
                    'source_frame_id': source,
                    'abs_image': f'/photos/{source}.jpg',
                    'synthetic_variant': variant,
                    'steering': 0.25 if variant != 'horizontal_flip' else -0.25,
                    'throttle': 0.4,
                })
        return pd.DataFrame(rows)

    def assert_disjoint_sources(self, train, validation):
        train_keys = set(zip(train['session'], train['source_frame_id']))
        val_keys = set(zip(validation['session'], validation['source_frame_id']))
        self.assertFalse(train_keys & val_keys)
        self.assertFalse(set(train['abs_image']) & set(validation['abs_image']))
        self.assertGreater(len(train), 0)
        self.assertGreater(len(validation), 0)

    def test_random_split_groups_all_synthetic_variants(self):
        df = self.sample()
        config = TrainConfig(split_mode='Random rows', val_ratio=0.25, seed=42)
        train, val = split_dataframe(df, config)
        self.assertEqual(len(train) + len(val), len(df))
        self.assert_disjoint_sources(train, val)
        again_train, again_val = split_dataframe(df, config)
        self.assertEqual(train.to_dict('records'), again_train.to_dict('records'))
        self.assertEqual(val.to_dict('records'), again_val.to_dict('records'))

    def test_sequential_split_keeps_synthetic_frames_with_original(self):
        original = self.sample()
        # Real preprocessing appends synthetic rows after original rows.
        df = pd.concat([original[original.synthetic_variant == variant]
                        for variant in ('original', 'horizontal_flip', 'color_mild_1')], ignore_index=True)
        train, val = split_by_sequential_rows(df, .25)
        self.assert_disjoint_sources(train, val)
        self.assertEqual(len(train) + len(val), len(df))

    def test_duplicate_image_paths_group_even_if_frame_ids_disagree(self):
        df = self.sample()
        df.loc[1, 'source_frame_id'] = 'different_source_id'
        train, val = split_by_rows(df, .25, 7)
        self.assertFalse(set(train.abs_image) & set(val.abs_image))
        self.assertEqual(len(train) + len(val), len(df))

    def test_session_split_groups_shared_images_across_sessions(self):
        df = self.sample()
        df.loc[df.session == 'session_b', 'abs_image'] = '/photos/shared.jpg'
        df.loc[df.session == 'session_a', 'abs_image'] = '/photos/shared.jpg'
        train, val = split_by_session(df, .25, 42)
        self.assertEqual(len(train), len(df))
        self.assertTrue(val.empty)  # One connected source family cannot be split safely.

    def test_real_preprocess_augmentation_remains_source_disjoint(self):
        originals = self.sample().loc[lambda df: df.synthetic_variant == 'original'].copy()
        augmented, summary = preprocess_service._build_augmented_dataset(
            originals, {'mirror_enabled': True, 'color_variants': 1}
        )
        self.assertEqual(summary['mirror_rows_added'], len(originals))
        self.assertEqual(len(augmented), len(originals) * 3)
        train, val = split_by_rows(augmented, .25, 41)
        self.assert_disjoint_sources(train, val)

    def test_session_split_keeps_distinct_sessions_separated(self):
        train, val = split_by_session(self.sample(), .25, 42)
        self.assertFalse(set(train.session) & set(val.session))
        self.assertEqual(len(train) + len(val), len(self.sample()))

    def test_source_frame_id_groups_when_variant_image_paths_differ(self):
        df = self.sample()
        df.loc[df.synthetic_variant != 'original', 'abs_image'] += '_variant'
        train, val = split_by_rows(df, .25, 42)
        self.assert_disjoint_sources(train, val)

    def test_single_source_avoids_fake_validation(self):
        df = self.sample().iloc[:3]
        train, val = split_by_rows(df, .2, 42)
        self.assertEqual(len(train), 3)
        self.assertTrue(val.empty)

    def test_legacy_missing_source_metadata_still_splits(self):
        df = pd.DataFrame({'session': ['a'] * 8, 'abs_image': [f'/photos/{i}.jpg' for i in range(8)]})
        train, val = split_by_rows(df, .25, 42)
        self.assertEqual(len(train), 6)
        self.assertEqual(len(val), 2)


class SaveDatasetTests(unittest.TestCase):
    def test_same_second_saves_never_overwrite_prior_records(self):
        with tempfile.TemporaryDirectory() as workspace:
            df_a = pd.DataFrame([{'abs_image': 'first.jpg', 'steering': 0.1, 'throttle': 0.2}])
            df_b = pd.DataFrame([{'abs_image': 'second.jpg', 'steering': 0.9, 'throttle': 0.8}])
            with patch.object(preprocess_service, 'datetime') as clock:
                clock.now.return_value.strftime.return_value = '20261122_153300'
                first = preprocess_service.save_preprocessed_dataset(df_a, {'name': 'first'}, Path(workspace))
                second = preprocess_service.save_preprocessed_dataset(df_b, {'name': 'second'}, Path(workspace))
            self.assertNotEqual(first, second)
            self.assertEqual(first.name, 'preprocessed_20261122_153300')
            self.assertEqual(second.name, 'preprocessed_20261122_153300_02')
            self.assertEqual(pd.read_csv(first / 'preprocessed_records.csv').loc[0, 'steering'], .1)
            self.assertEqual(pd.read_csv(second / 'preprocessed_records.csv').loc[0, 'steering'], .9)
            self.assertEqual(json.loads((first / 'preprocess_recipe.json').read_text())['name'], 'first')
            self.assertEqual(json.loads((second / 'preprocess_recipe.json').read_text())['name'], 'second')
            self.assertEqual(len((first / 'preprocessed_records.jsonl').read_text().splitlines()), 1)


if __name__ == '__main__':
    unittest.main()
