"""Hardware-free provisioning credential and web mutation security tests."""
from __future__ import annotations

import http.client
import json
import os
import tempfile
import threading
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock
import time
from unittest.mock import patch
from urllib.parse import urlencode

from pibooter.app import PiBooterController, PiBooterServer
from pibooter.config import ConfigStore, DEFAULT_CONFIG
from pibooter.network import NetworkManagerBackend
from pibooter.provisioning_security import (
    PUBLISHED_HOTSPOT_PASSWORD, authorized_setup_client, hotspot_password_safe,
    request_token_matches, trusted_post_origin,
)


class CredentialTests(unittest.TestCase):
    def test_new_config_generates_unique_secret_and_reloads_without_rotation(self):
        with tempfile.TemporaryDirectory() as temp:
            one = ConfigStore(Path(temp) / 'first.json')
            two = ConfigStore(Path(temp) / 'second.json')
            a, b = one.data['network']['hotspot_password'], two.data['network']['hotspot_password']
            self.assertTrue(hotspot_password_safe(a))
            self.assertTrue(hotspot_password_safe(b))
            self.assertGreaterEqual(len(a), 32)
            self.assertNotEqual(a, b)
            self.assertEqual(ConfigStore(one.path).data['network']['hotspot_password'], a)
            self.assertFalse(one.provision_hotspot_password())
            self.assertEqual(one.data['network']['hotspot_password'], a)
            if os.name == 'posix':
                self.assertEqual(one.path.stat().st_mode & 0o777, 0o600)

    def test_published_default_is_not_silently_rotated_on_normal_load(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'settings.json'
            raw = {'network': {'hotspot_password': PUBLISHED_HOTSPOT_PASSWORD}, 'extra': {'keep': True}}
            path.write_text(json.dumps(raw))
            config = ConfigStore(path)
            self.assertEqual(config.data['network']['hotspot_password'], PUBLISHED_HOTSPOT_PASSWORD)
            self.assertFalse(hotspot_password_safe(config.data['network']['hotspot_password']))
            self.assertEqual(config.data['extra'], {'keep': True})
            self.assertTrue(config.provision_hotspot_password())
            new = config.data['network']['hotspot_password']
            self.assertTrue(hotspot_password_safe(new))
            self.assertEqual(ConfigStore(path).data['extra'], {'keep': True})
            self.assertFalse(config.provision_hotspot_password())
            self.assertEqual(config.data['network']['hotspot_password'], new)
            self.assertTrue(config.provision_hotspot_password(rotate=True))
            self.assertNotEqual(config.data['network']['hotspot_password'], new)

    def test_custom_password_and_invalid_config_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'settings.json'
            path.write_text(json.dumps({'network': {'hotspot_password': 'my-private-key-01234567'}}))
            store = ConfigStore(path)
            before = path.read_bytes()
            self.assertFalse(store.provision_hotspot_password())
            self.assertEqual(path.read_bytes(), before)
            path.write_bytes(b'not a valid JSON config')
            corrupted = ConfigStore(path)
            with self.assertRaises(RuntimeError):
                corrupted.provision_hotspot_password()
            self.assertEqual(path.read_bytes(), b'not a valid JSON config')
            self.assertIsNotNone(corrupted.recovery_backup)


    def test_preexisting_published_password_hotspot_is_stopped(self):
        controller = PiBooterController.__new__(PiBooterController)
        controller.config = deepcopy(DEFAULT_CONFIG)
        controller.hotspot_ssid = 'PiBooter-legacy'
        controller.network = Mock()
        controller.network.get_runtime_snapshot.return_value = {
            'phase': 'hotspot', 'wifi': {'hotspot_active': True},
            'nmcli_available': False, 'ip_addresses': {}, 'devices': [],
            'message': 'old hotspot is on',
        }
        controller.network.get_known_wifi_connections.return_value = []
        controller.get_scan_results = lambda **kwargs: []
        controller.state = Mock()
        controller.state.snapshot.return_value = {}
        controller.status_store = Mock()
        controller.status_store.snapshot.return_value = {}
        controller._shutdown_requested = threading.Event()
        controller._session_active = False
        controller._session_source = ''
        controller._session_started_at = 0.0
        controller._started_at = time.time()
        controller._unsafe_hotspot_warning_logged = False
        result = controller.refresh_state(ensure_hotspot=True)
        controller.network.stop_hotspot.assert_called_once()
        self.assertEqual(controller.state.update.call_args.kwargs['phase'], 'error')
        self.assertIn('password', controller.state.update.call_args.kwargs['message'])
        self.assertNotIn('password', controller.state.update.call_args.kwargs['hotspot'])
        controller.network.start_hotspot.assert_not_called()

    def test_short_password_remains_invalid_not_predictably_padded(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'settings.json'
            path.write_text(json.dumps({'network': {'hotspot_password': 'bad'}}))
            store = ConfigStore(path)
            self.assertEqual(store.data['network']['hotspot_password'], 'bad')
            self.assertFalse(hotspot_password_safe('bad'))
            backend = NetworkManagerBackend(store.data)
            with patch.object(backend, 'run') as runner:
                result = backend.start_hotspot('PiBooter-unsafe', 'bad')
            self.assertFalse(result.ok)
            runner.assert_not_called()

    def test_known_password_never_reaches_nmcli(self):
        backend = NetworkManagerBackend(deepcopy(DEFAULT_CONFIG))
        with patch.object(backend, 'run') as runner:
            result = backend.start_hotspot('PiBooter-demo', PUBLISHED_HOTSPOT_PASSWORD)
        self.assertFalse(result.ok)
        self.assertIn('publicly known', result.stderr)
        runner.assert_not_called()


class SecurityPolicyTests(unittest.TestCase):
    def test_client_must_be_in_hotspot_network_or_loopback(self):
        hotspot = '192.168.4.1/24'
        for peer in ('192.168.4.2', '192.168.4.250', '127.0.0.1', '::1'):
            self.assertTrue(authorized_setup_client(peer, hotspot), peer)
        for peer in ('192.168.4.1', '192.168.5.2', '192.168.68.5', '0.0.0.0', 'not-IP', '::ffff:192.168.4.2'):
            self.assertFalse(authorized_setup_client(peer, hotspot), peer)
        self.assertFalse(authorized_setup_client('192.168.4.3', 'invalid-cidr'))

    def test_csrf_token_and_origin_checks(self):
        expected = 'secure-random-token-' + 'x'*20
        self.assertTrue(request_token_matches(expected, expected))
        for attempt in ('', 'wrong', expected+'x', 'x'*500):
            self.assertFalse(request_token_matches(attempt, expected))
        self.assertTrue(trusted_post_origin('http://192.168.4.1', '192.168.4.1'))
        self.assertTrue(trusted_post_origin(None, '192.168.4.1'))
        self.assertFalse(trusted_post_origin('http://evil.example', '192.168.4.1'))
        self.assertFalse(trusted_post_origin('http://192.168.4.1.evil.example', '192.168.4.1'))
        self.assertFalse(trusted_post_origin('https://192.168.4.1', '192.168.4.1'))
        self.assertFalse(trusted_post_origin('http://[broken', '192.168.4.1'))


class FakeState:
    def snapshot(self):
        return {'scan_results': [{'ssid': 'sample', 'security': 'WPA2'}]}


class FakeController:
    def __init__(self):
        self.config = {
            'network': {'hotspot_ip': '192.168.4.1/24'},
            'ui': {'title': 'PiBooter Test', 'subtitle': 'Test UI', 'status_refresh_s': 0},
            'server': {'startup_wait_s': 5},
        }
        self.csrf_token = 'secure-random-token-' + 'y'*20
        self.hotspot_ssid = 'PiBooter-unit'
        self.hostname = 'pi-test'
        self.state = FakeState()
        self.calls: list[tuple] = []

    def refresh_state(self, *, ensure_hotspot=False):
        return {
            'phase': 'hotspot', 'message': 'Ready', 'primary_ip': '192.168.4.1',
            'active_connection': 'PiBooter-unit', 'session_active': True,
            'startup_remaining_s': 0, 'known_connections': [{'name': 'saved-wifi', 'autoconnect': 'yes'}],
            'scan_results': [], 'network': {'wifi': {'interface': 'wlan0'}, 'devices': [], 'nmcli_available': False},
            'hotspot': {'ssid': 'PiBooter-unit', 'password': 'must-not-leak', 'url': 'http://192.168.4.1/'},
            'last_status': {}, 'hotspot_clients': [], 'logs': [],
        }

    def note_http_activity(self, path, client_ip):
        self.calls.append(('activity', path, client_ip))

    def start_connection_attempt(self, ssid, password, hidden):
        self.calls.append(('connect', ssid, password, hidden))

    def forget_connection(self, name):
        self.calls.append(('forget', name))
        return True, 'ok'

    def rescan(self):
        self.calls.append(('rescan',))

    def set_shutdown_callback(self, callback):
        pass

    def close(self):
        pass


class HttpMutationTests(unittest.TestCase):
    def setUp(self):
        self.controller = FakeController()
        self.server = PiBooterServer(('127.0.0.1', 0), self.controller)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def send(self, method, path, data=None, *, origin=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=4)
        headers = dict(headers or {})
        if data is not None:
            headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')
            data = urlencode(data).encode('utf-8') if isinstance(data, dict) else data
        if origin is not None:
            headers['Origin'] = origin
        connection.request(method, path, body=data, headers=headers)
        response = connection.getresponse()
        body = response.read()
        result = response.status, body, dict(response.getheaders())
        connection.close()
        return result

    def test_html_has_tokens_on_all_forms_no_password_leak(self):
        code, html, headers = self.send('GET', '/')
        self.assertEqual(code, 200)
        self.assertIn(self.controller.csrf_token.encode(), html)
        self.assertEqual(html.count(b'name="csrf_token"') + html.count(b"name='csrf_token'"), 3)
        self.assertNotIn(b'must-not-leak', html)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(headers['X-Frame-Options'], 'DENY')
        code, json_body, _ = self.send('GET', '/api/status')
        self.assertEqual(code, 200)
        self.assertNotIn(b'must-not-leak', json_body)

    def test_scanned_ssid_cannot_inject_markup_or_script(self):
        from pibooter.app import RequestHandler
        malicious = '\" onmouseover=\"alert(1)'
        markup = RequestHandler.render_scan_results([{'ssid': malicious, 'signal': 40, 'security': 'WPA2', 'channel': '1'}])
        self.assertIn('&quot;', markup)
        self.assertNotIn('onclick=\"fillSsid(\"', markup)
        self.assertNotIn('onmouseover=\"alert', markup)

    def test_no_get_side_effects_on_network_listing(self):
        code, body, _ = self.send('GET','/api/networks')
        self.assertEqual(code, 200)
        self.assertIn(b'sample', body)
        self.assertFalse(any(c[0]=='rescan' for c in self.controller.calls))

    def test_wifi_change_rejects_missing_csrf_and_cross_origin(self):
        base={'ssid':'home','password':'ssid-private'}
        code, _, _ = self.send('POST','/connect',base)
        self.assertEqual(code,403)
        code, _, _ = self.send('POST','/connect',{**base,'csrf_token':'bad'})
        self.assertEqual(code,403)
        code, _, _ = self.send('POST','/connect',{**base,'csrf_token':self.controller.csrf_token},origin='http://other.example')
        self.assertEqual(code,403)
        self.assertFalse(any(c[0]=='connect' for c in self.controller.calls))

    def test_valid_forms_can_connect_forget_and_rescan(self):
        token=self.controller.csrf_token
        code, _, _ = self.send('POST','/connect',{'ssid':'home','password':'private','csrf_token':token})
        self.assertEqual(code,302)
        self.assertIn(('connect','home','private',False),self.controller.calls)
        code, _, _ = self.send('POST','/forget',{'name':'saved-wifi','csrf_token':token})
        self.assertEqual(code,302)
        self.assertIn(('forget','saved-wifi'),self.controller.calls)
        code, _, _ = self.send('POST','/rescan',{'csrf_token':token})
        self.assertEqual(code,302)
        self.assertIn(('rescan',),self.controller.calls)

    def test_bounded_body_and_errors_are_safe(self):
        code, _, _=self.send('POST','/connect',b'large'*2200,headers={'Content-Type':'application/x-www-form-urlencoded'})
        self.assertEqual(code,413)
        code, _, _=self.send('POST','/connect',b'plain',headers={'Content-Type':'text/plain'})
        self.assertEqual(code,400)
        code, _, _=self.send('POST','/connect',b'{broken',headers={'Content-Type':'application/json'})
        self.assertEqual(code,400)
        self.assertFalse(any(c[0]=='connect' for c in self.controller.calls))


if __name__=='__main__':
    unittest.main()
