from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
