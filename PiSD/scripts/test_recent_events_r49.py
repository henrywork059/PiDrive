import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pisd.core.recent_events import RecentEvents
from pisd.app import create_app

class RecentEventTests(unittest.TestCase):
    def test_bounded_allowlisted_events(self):
        ring=RecentEvents()
        ring.observe('raw-secret',200,{'ok':True})
        self.assertEqual(ring.snapshot(),[])
        for i in range(150):
            ring.observe('api_recording_start',409,{'ok':False,'message':'secret'})
        items=ring.snapshot()
        self.assertEqual(len(items),80)
        self.assertEqual(ring.capacity,128)
        self.assertEqual(items[-1]['outcome'],'failed')
        self.assertEqual(set(items[-1]),{'timestamp_utc','title','outcome'})
        self.assertNotIn('secret',str(items))
    def test_api_records_acknowledgement_without_payload(self):
        with tempfile.TemporaryDirectory() as tmp, patch('pisd.app.PROJECT_ROOT',Path(tmp)), patch('pisd.app.RUNTIME_SETTINGS_PATH',Path(tmp)/'runtime.json'), patch.dict('os.environ',{'PISD_ACCESS_TOKEN':''}):
            app=create_app(hardware_enabled=False)
            services=app.config['pisd_services']
            try:
                client=app.test_client()
                self.assertEqual(client.get('/api/recent-events').get_json()['events'],[])
                with patch.object(services['ai_drive'],'delete_model',return_value={'ok':True,'message':'secret-model-name'}):
                    self.assertEqual(client.post('/api/ai/delete-model',json={'model_id':'secret-model-name','confirm':True}).status_code,200)
                result=client.get('/api/recent-events').get_json()
                self.assertEqual(result['events'][-1]['title'],'Model deletion')
                self.assertEqual(result['events'][-1]['outcome'],'acknowledged')
                self.assertNotIn('secret',str(result))
                self.assertEqual(client.get('/api/recent-events').get_json(),result)
            finally:
                services['ai_drive'].close()
                services['motor'].close()
                services['camera'].stop()
