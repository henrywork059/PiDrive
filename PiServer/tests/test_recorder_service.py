from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from piserver.services.recorder_service import RecorderService


class RecorderServiceTests(unittest.TestCase):
    def test_list_sessions_and_zip_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "records"
            svc = RecorderService(root)
            session = root / "20260321-120000"
            images = session / "images"
            images.mkdir(parents=True, exist_ok=True)
            (session / "records.jsonl").write_text(json.dumps({"frame_id": "a"}) + "\n", encoding="utf-8")
            (images / "frame1.jpg").write_bytes(b"jpg1")
            (images / "frame2.jpg").write_bytes(b"jpg2")
            (root / "snapshots").mkdir(parents=True, exist_ok=True)

            sessions = svc.list_sessions()
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0]["name"], "20260321-120000")
            self.assertEqual(sessions[0]["image_count"], 2)

            buf = io.BytesIO()
            ok, payload = svc.write_session_zip("20260321-120000", buf)
            self.assertTrue(ok)
            self.assertEqual(payload, "20260321-120000")
            buf.seek(0)
            with zipfile.ZipFile(buf, "r") as zf:
                names = set(zf.namelist())
            self.assertIn("20260321-120000/records.jsonl", names)
            self.assertIn("20260321-120000/images/frame1.jpg", names)
            self.assertIn("20260321-120000/images/frame2.jpg", names)


if __name__ == "__main__":
    unittest.main()
