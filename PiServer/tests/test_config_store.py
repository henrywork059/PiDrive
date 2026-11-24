from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from piserver.core.config_store import ConfigStore


class ConfigStoreTests(unittest.TestCase):
    def test_load_merges_defaults_and_preserves_unknown_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.json"
            path.write_text(json.dumps({"motor": {"left_direction": -1}, "extra": {"a": 1}}), encoding="utf-8")
            store = ConfigStore(path)
            data = store.load()
            self.assertEqual(data["motor"]["left_direction"], -1)
            self.assertIn("right_direction", data["motor"])
            self.assertEqual(data["extra"], {"a": 1})
            self.assertIn("camera", data)

    def test_merge_save_is_atomic_style_and_preserves_existing_unknown_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.json"
            path.write_text(json.dumps({"extra": {"keep": True}, "motor": {"left_direction": 1}}), encoding="utf-8")
            store = ConfigStore(path)
            saved = store.merge_save({"motor": {"left_direction": -1}})
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["motor"]["left_direction"], -1)
            self.assertEqual(raw["extra"], {"keep": True})
            self.assertFalse(path.with_suffix(".json.tmp").exists())


    def test_default_camera_awb_is_now_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.json"
            store = ConfigStore(path)
            data = store.load()
            self.assertFalse(data["camera"]["auto_white_balance"])

    def test_explicit_camera_awb_true_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.json"
            path.write_text(json.dumps({"camera": {"auto_white_balance": True}}), encoding="utf-8")
            store = ConfigStore(path)
            data = store.load()
            self.assertTrue(data["camera"]["auto_white_balance"])

    def test_invalid_bytes_preserved_before_replacement_and_restart(self):
        for raw in (b'{"motor":', b'[]', b'{"camera":null}', b'\xff'):
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "runtime.json"
                path.write_bytes(raw)
                store = ConfigStore(path)
                self.assertEqual(store.load()["active_algorithm"], "manual")
                recovery = store.recovery_status()
                backup = path.parent / recovery["backup"]
                self.assertTrue(recovery["load_failed"])
                self.assertEqual(path.read_bytes(), raw)
                self.assertEqual(backup.read_bytes(), raw)
                store.save({"max_throttle": 0.3})
                self.assertEqual(backup.read_bytes(), raw)
                self.assertEqual(ConfigStore(path).load()["max_throttle"], 0.3)

    def test_external_damage_and_backup_failure_leave_file_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.json"
            store = ConfigStore(path)
            store.save({"max_throttle": 0.31, "extra": {"keep": True}})
            raw = b'{"motor":'
            path.write_bytes(raw)
            with patch("piserver.core.config_recovery.os.open", side_effect=PermissionError("denied")):
                with self.assertRaises(OSError):
                    store.save({"max_throttle": 0.9})
            self.assertEqual(path.read_bytes(), raw)
            self.assertTrue(store.recovery_status()["write_blocked"])
            self.assertEqual(store.load()["max_throttle"], 0.31)
            self.assertEqual(store.save({"max_throttle": 0.42})["extra"], {"keep": True})
            self.assertEqual((path.parent / store.recovery_status()["backup"]).read_bytes(), raw)

    def test_failed_replacement_preserves_valid_bytes_and_previous_raw(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.json"
            store = ConfigStore(path)
            store.save({"max_throttle": 0.31, "extra": {"keep": True}})
            raw = path.read_bytes()
            with patch("piserver.core.config_recovery.os.replace", side_effect=OSError("disk failure")):
                with self.assertRaises(OSError):
                    store.save({"max_throttle": 0.9})
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(store.load()["max_throttle"], 0.31)
            self.assertEqual(store.save({"max_throttle": 0.42})["extra"], {"keep": True})


if __name__ == "__main__":
    unittest.main()
