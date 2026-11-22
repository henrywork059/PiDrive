"""No real GPIO or camera: recording storage failure cannot affect drive state."""
from __future__ import annotations
import errno
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from collections import namedtuple
from piserver.services import recorder_service as recorder_mod
from piserver.services.recorder_service import RecorderService
from piserver.core.recording_storage import RecordingStorageError

class FakeCv2:
    fail = False
    def imwrite(self, filename, frame):
        if self.fail: return False
        Path(filename).write_bytes(b'jpg')
        return True

class RecorderStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.svc=RecorderService(Path(self.tmp.name)/'records')
        self.fake=FakeCv2(); self.fake.fail=False
        self.cv=patch.object(recorder_mod,'cv2',self.fake)
        self.cv.start(); self.addCleanup(self.cv.stop)
        self.usage=namedtuple('usage','total used free')

    def pressure(self,free_mib):
        return patch('piserver.core.recording_storage.shutil.disk_usage',return_value=self.usage(2**30,2**30-free_mib*2**20,free_mib*2**20))

    def test_low_disk_rejects_start_without_touching_existing_sessions(self):
        historical=self.svc.root/'old';historical.mkdir();(historical/'important.txt').write_text('retain')
        with self.pressure(16):
            with self.assertRaises(RecordingStorageError): self.svc.start()
            state=self.svc.get_status()['recording_storage']
        self.assertFalse(self.svc.recording)
        self.assertEqual((historical/'important.txt').read_text(),'retain')
        self.assertEqual(state['state'],'critical')
        self.assertEqual(len(state['recent_write_errors']),1)

    def test_failed_frame_write_stops_recording_and_keeps_index_intact(self):
        self.svc.start(); self.svc.min_interval=0
        filename=self.svc.session_path/'records.jsonl'
        self.svc.maybe_record(object(),{'applied_steering':.1,'applied_throttle':.5})
        before=filename.read_bytes()
        self.fake.fail=True
        self.svc.maybe_record(object(),{'applied_steering':.2})
        self.assertFalse(self.svc.recording)
        self.assertEqual(filename.read_bytes(),before)
        self.assertIn('record',self.svc.get_status()['recording_storage']['recent_write_errors'][-1]['operation'])

    def test_low_space_while_recording_stops_only_recording(self):
        self.svc.start(); self.svc.min_interval=0
        with self.pressure(32):
            self.svc.maybe_record(object(),{'applied_steering':.2})
        self.assertFalse(self.svc.recording)
        self.assertEqual(self.svc.get_status()['recording_storage']['state'],'ok')
        self.assertTrue(self.svc.get_status()['recording_storage']['recent_write_errors'])

    def test_snapshot_failure_returns_error_without_metadata(self):
        self.fake.fail=True
        ok, message=self.svc.capture_once(object())
        self.assertFalse(ok)
        self.assertIn('not saved',message)
        self.assertFalse((self.svc.snapshot_dir/'snapshots.jsonl').exists())

    def test_recording_start_failure_does_not_change_motor_state(self):
        import threading
        from types import SimpleNamespace
        from piserver.services.control_service import ControlService
        controller = ControlService.__new__(ControlService)
        controller.lock = threading.RLock()
        controller.recorder_service = self.svc
        controller.state = SimpleNamespace(recording=False, system_message='', safety_stop=False)
        with self.pressure(15):
            ok, recording, message = controller.toggle_recording()
        self.assertFalse(ok)
        self.assertFalse(recording)
        self.assertIn('Recording unavailable', message)
        self.assertFalse(controller.state.safety_stop)

    def test_metadata_write_error_stops_safely(self):
        self.svc.start(); self.svc.min_interval = 0
        original = self.svc.index_file
        class FailedIndex:
            def tell(self): return 0
            def write(self, _text): raise OSError(errno.ENOSPC, 'simulated full disk')
            def seek(self, *_args): return 0
            def truncate(self, *_args): return 0
            def flush(self): return None
            def close(self): return None
        self.svc.index_file = FailedIndex()
        before = (self.svc.session_path / 'records.jsonl').read_bytes()
        self.svc.maybe_record(object(), {'applied_throttle': .4})
        self.assertFalse(self.svc.recording)
        self.assertEqual((self.svc.last_session_path / 'records.jsonl').read_bytes(), before)
        original.close()

    def test_storage_status_reports_size_and_successful_snapshot(self):
        ok,_=self.svc.capture_once(object());self.assertTrue(ok)
        state=self.svc.get_status()['recording_storage']
        self.assertGreater(state['session_size_bytes'],0) if self.svc.session_path else self.assertEqual(state['state'],'ok')
        self.assertEqual(self.svc.list_sessions()[0]['kind'],'snapshots')
        self.assertGreater(self.svc.list_sessions()[0]['size_bytes'],0)

if __name__=='__main__':unittest.main()
