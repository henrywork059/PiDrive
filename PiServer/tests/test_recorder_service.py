from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from piserver.services import recorder_service as recorder_module
from piserver.services.recorder_service import RecorderService


class _FakeCv2:
    @staticmethod
    def imwrite(path: str, _frame) -> bool:
        Path(path).write_bytes(b"fake-jpg")
        return True


class RecorderServiceTests(unittest.TestCase):
    def test_list_sessions_zip_and_delete_folder(self):
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
            (root / "snapshots" / "shot1.jpg").write_bytes(b"snap")

            sessions = svc.list_sessions()
            self.assertEqual(len(sessions), 2)
            self.assertEqual(sessions[0]["name"], "snapshots")
            self.assertEqual(sessions[0]["kind"], "snapshots")
            self.assertEqual(sessions[1]["name"], "20260321-120000")
            self.assertEqual(sessions[1]["image_count"], 2)

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

            shot_buf = io.BytesIO()
            ok, payload = svc.write_session_zip("snapshots", shot_buf)
            self.assertTrue(ok)
            self.assertEqual(payload, "snapshots")
            shot_buf.seek(0)
            with zipfile.ZipFile(shot_buf, "r") as zf:
                snapshot_names = set(zf.namelist())
            self.assertIn("snapshots/shot1.jpg", snapshot_names)

            ok, message = svc.delete_folder("20260321-120000")
            self.assertTrue(ok)
            self.assertIn("Deleted 20260321-120000", message)
            self.assertFalse(session.exists())

    def test_capture_once_reuses_single_shared_snapshot_folder_across_service_restarts(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(recorder_module, "cv2", _FakeCv2()):
            root = Path(tmp) / "data" / "records"

            first = RecorderService(root)
            ok, message = first.capture_once(frame_bgr=object(), snapshot={"active_algorithm": "manual"})
            self.assertTrue(ok)
            self.assertIn("Snapshot saved:", message)

            second = RecorderService(root)
            ok, message = second.capture_once(frame_bgr=object(), snapshot={"active_algorithm": "manual"})
            self.assertTrue(ok)
            self.assertIn("Snapshot saved:", message)

            snapshot_dir = root / "snapshots"
            self.assertTrue(snapshot_dir.is_dir())
            self.assertEqual(sorted(path.name for path in root.iterdir() if path.is_dir()), ["snapshots"])
            self.assertEqual(len(list(snapshot_dir.glob("*.jpg"))), 2)

            metadata_path = snapshot_dir / "snapshots.jsonl"
            lines = [line for line in metadata_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(lines), 2)

            buf = io.BytesIO()
            ok, payload = second.write_session_zip("snapshots", buf)
            self.assertTrue(ok)
            self.assertEqual(payload, "snapshots")
            buf.seek(0)
            with zipfile.ZipFile(buf, "r") as zf:
                names = sorted(zf.namelist())
            self.assertIn("snapshots/snapshots.jsonl", names)
            jpg_names = [name for name in names if name.startswith("snapshots/") and name.endswith(".jpg")]
            self.assertEqual(len(jpg_names), 2)
            self.assertFalse(any(name.count("/") > 1 for name in jpg_names))

    def test_nested_snapshot_folders_are_flattened_back_into_shared_snapshots_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data" / "records"
            nested = root / "snapshots" / "20260321-120000"
            nested.mkdir(parents=True, exist_ok=True)
            (nested / "shot1.jpg").write_bytes(b"old-snap")
            (nested / "snapshots.jsonl").write_text(
                json.dumps({"image": "snapshots/shot1.jpg", "mode": "manual"}) + "\n",
                encoding="utf-8",
            )

            svc = RecorderService(root)

            self.assertFalse(nested.exists())
            self.assertTrue((root / "snapshots" / "shot1.jpg").exists())
            merged_meta = (root / "snapshots" / "snapshots.jsonl").read_text(encoding="utf-8")
            self.assertIn('"image": "snapshots/shot1.jpg"', merged_meta)

            buf = io.BytesIO()
            ok, payload = svc.write_session_zip("snapshots", buf)
            self.assertTrue(ok)
            self.assertEqual(payload, "snapshots")
            buf.seek(0)
            with zipfile.ZipFile(buf, "r") as zf:
                names = sorted(zf.namelist())
            self.assertIn("snapshots/shot1.jpg", names)
            self.assertFalse(any(name.startswith("snapshots/20260321-120000/") for name in names))


if __name__ == "__main__":
    unittest.main()
