from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pibooter.config import ConfigStore, DEFAULT_CONFIG


class ConfigRecoveryTests(unittest.TestCase):
    def test_invalid_json_is_preserved_and_backed_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'settings.json'
            raw = b'{invalid json (do not erase me)'
            target.write_bytes(raw)
            store = ConfigStore(target)
            self.assertEqual(target.read_bytes(), raw)
            self.assertIn('could not be loaded', store.load_error)
            self.assertIsNotNone(store.recovery_backup)
            self.assertEqual(store.recovery_backup.read_bytes(), raw)
            self.assertEqual(store.data['server']['port'], DEFAULT_CONFIG['server']['port'])
            with self.assertRaises(RuntimeError):
                store.save()
            self.assertEqual(target.read_bytes(), raw)
            store.save(replace_invalid=True)
            self.assertEqual(json.loads(target.read_text())['server']['port'], DEFAULT_CONFIG['server']['port'])
            self.assertEqual(store.recovery_backup.read_bytes(), raw)

    def test_wrong_schema_does_not_destroy_original(self):
        for raw in ('[]', '{"network": 7}', '{"server": "not an object"}'):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / 'settings.json'
                target.write_text(raw)
                store = ConfigStore(target)
                self.assertTrue(store.load_error)
                self.assertEqual(target.read_text(), raw)
                self.assertTrue(store.recovery_backup.exists())

    def test_valid_saved_unknown_keys_and_password_survive_normalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'settings.json'
            target.write_text(json.dumps({'network': {'hotspot_password': 'custom-secret-1234'}, 'future_key': {'v': 1}}))
            store = ConfigStore(target)
            self.assertEqual(store.data['network']['hotspot_password'], 'custom-secret-1234')
            self.assertEqual(store.data['future_key'], {'v': 1})
            self.assertEqual(json.loads(target.read_text())['future_key'], {'v': 1})
            self.assertFalse(store.load_error)
            self.assertIsNone(store.recovery_backup)
            before=target.read_bytes()
            store.reload()
            self.assertEqual(target.read_bytes(), before)

    def test_new_config_created_without_dangling_temporary_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'settings.json'
            store = ConfigStore(target)
            self.assertTrue(target.exists())
            self.assertFalse(store.load_error)
            self.assertEqual(list(Path(tmp).glob('*.tmp')), [])


if __name__ == '__main__':
    unittest.main()
