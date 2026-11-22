"""PiSD storage faults stop recording, not driving; no hardware required."""
from __future__ import annotations
import errno
import json
import tempfile
import time
import unittest
from pathlib import Path
from collections import namedtuple
from unittest.mock import patch
from pisd.services.recording_service import RecordingService

class Camera:
    def __init__(self): self.n=0
    def start(self): return None
    def wait_for_jpeg_frame(self, last_seq=None, timeout=1.0):
        self.n+=1
        return b'fakejpeg',self.n,str(self.n),8
    def get_config(self): return {'width':2,'height':2,'fps':12}

class Motor:
    def __init__(self): self.moves=[]
    def status(self):
        return {'last_command':{'steering':0.17,'throttle':0.3,'steer_mix':.8}, 'last_left':.2,'last_right':.3}
    def update(self,*args,**kwargs): self.moves.append((args,kwargs))
    def stop(self): self.moves.append(('stopped',{}))

class RecordingStorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.svc=RecordingService(self.root)
        self.cam=Camera();self.motor=Motor()
        self.usage=namedtuple('usage','total used free')
    def low_disk(self, m=8):
        return patch('pisd.core.recording_storage.shutil.disk_usage',return_value=self.usage(1024**3,1024**3-m*1024**2,m*1024**2))

    def test_critical_space_refuses_session_with_no_folder_or_motor_change(self):
        with self.low_disk():
            result=self.svc.start(self.cam,self.motor)
            self.assertFalse(result['ok'])
            self.assertEqual(self.svc.status()['storage']['state'],'critical')
        self.assertFalse((self.root/'recordings').exists())
        self.assertEqual(self.motor.moves,[])
        self.assertEqual(len(self.svc.status()['storage']['recent_write_errors']),1)

    def test_critical_space_rejects_single_capture_before_writing(self):
        with self.low_disk():
            result=self.svc.capture_once(self.cam,self.motor)
        self.assertFalse(result['ok'])
        self.assertEqual(self.cam.n,0)
        self.assertFalse((self.root/'recordings').exists())
        self.assertEqual(self.motor.moves,[])

    def test_worker_write_error_stops_and_preserves_historical_data(self):
        folder=self.root/'recordings'/'historical';folder.mkdir(parents=True)
        preserved=folder/'records.jsonl';preserved.write_text('keep-original\n')
        with patch.object(self.svc,'_save_frame_record_locked',side_effect=OSError(errno.ENOSPC,'SD card full')):
            result=self.svc.start(self.cam,self.motor,fps=30)
            self.assertTrue(result['ok'])
            limit=time.monotonic()+3
            while time.monotonic()<limit and self.svc.status()['running']:
                time.sleep(.025)
            # Even when failure happens on the first thread iteration, it must
            # leave the camera/motor adapter untouched and stop new writes.
            self.assertFalse(self.svc.status()['running'])
        self.assertEqual(preserved.read_text(),'keep-original\n')
        self.assertFalse(self.svc._active_session)
        self.assertEqual(self.motor.moves,[])
        state=self.svc.status()
        self.assertEqual(state['last_error_code'],'PISD-REC-002')
        self.assertTrue(state['storage']['recent_write_errors'])

    def test_successful_capture_reports_size_and_preserves_labels(self):
        result=self.svc.capture_once(self.cam,self.motor,label='safe')
        self.assertTrue(result['ok'])
        record=result['record']
        labels=Path(record['file']).parent.parent/'labels.jsonl'
        self.assertTrue(labels.exists())
        self.assertEqual(json.loads(labels.read_text().splitlines()[0])['steering'],0.17)
        state=self.svc.status()['storage']
        self.assertGreater(state['session_size_bytes'],0)
        self.assertEqual(self.motor.moves,[])

if __name__=='__main__':unittest.main()
