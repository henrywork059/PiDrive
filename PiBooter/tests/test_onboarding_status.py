"""R34: deterministic, hardware-free PiBooter onboarding state and UI tests."""
from __future__ import annotations

import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from pibooter.onboarding_status import project_onboarding
from pibooter.app import HTML_SHELL, PiBooterController, RequestHandler
from pibooter.network import CommandResult


def status(**updates):
    baseline = {
        'phase': 'hotspot',
        'hotspot': {'active': True, 'ssid': 'PiBooter-test', 'url': 'http://192.168.4.1/'},
        'connection_attempt': None,
        'session_active': True,
        'startup_remaining_s': 0,
        'scan_in_progress': False,
        'last_status': {},
        'network': {'nmcli_available': True, 'wifi': {'interface': 'wlan0'}, 'devices': []},
        'known_connections': [],
        'scan_results': [],
        'hotspot_clients': [],
        'logs': [],
        'message': 'Hotspot active',
    }
    baseline.update(updates)
    return baseline


class OnboardingProjectionTests(unittest.TestCase):
    def test_ready_hotspot(self):
        result = project_onboarding(status())
        self.assertEqual(result['state'], 'ready')
        self.assertFalse(result['retry_available'])

    def test_scanning_is_explicit(self):
        result = project_onboarding(status(scan_in_progress=True))
        self.assertEqual(result['state'], 'scanning')
        self.assertIn('SSID', result['next_action'])

    def test_running_wifi_attempt_overrides_hotspot(self):
        result = project_onboarding(status(connection_attempt={'status': 'running', 'ssid': 'home'}))
        self.assertEqual(result['state'], 'connecting')
        self.assertIn('disconnect', result['next_action'])

    def test_success_overrides_hotspot(self):
        result = project_onboarding(status(connection_attempt={'status': 'success', 'ssid': 'home'}))
        self.assertEqual(result['state'], 'connected')

    def test_non_hotspot_connected(self):
        self.assertEqual(project_onboarding(status(phase='connected'))['state'], 'connected')

    def test_failure_not_hidden_by_restored_hotspot(self):
        result = project_onboarding(status(
            connection_attempt={'status': 'error', 'ssid': 'home', 'message': 'bad password'}))
        self.assertEqual(result['state'], 'failed')
        self.assertTrue(result['retry_available'])
        self.assertIn('submit again', result['next_action'])

    def test_failed_connection_without_hotspot_offers_restart(self):
        result = project_onboarding(status(
            hotspot={'active': False}, connection_attempt={'status':'error'}))
        self.assertEqual(result['state'], 'failed')
        self.assertFalse(result['retry_available'])
        self.assertIn('restart PiBooter', result['next_action'])

    def test_failure_never_echoes_ssid_or_password(self):
        private = 'super-secret-wifi-key'
        result = project_onboarding(status(
            connection_attempt={'status':'error', 'ssid':'private-network', 'message':private},
            last_error=private))
        self.assertNotIn(private, str(result))
        self.assertNotIn('private-network', str(result))

    def test_invalid_legacy_hotspot_credential_guidance(self):
        result = project_onboarding(status(
            phase='error', message='setup hotspot password invalid'))
        self.assertEqual(result['state'], 'failed')
        self.assertIn('Provision a private hotspot password', result['next_action'])

    def test_network_manager_missing_shows_safe_guidance(self):
        result = project_onboarding(status(phase='error', message='nmcli missing'))
        self.assertIn('NetworkManager', result['next_action'])

    def test_short_window_closing_uses_existing_countdown(self):
        result = project_onboarding(status(session_active=False,startup_remaining_s=2))
        self.assertEqual(result['state'], 'window_closing')
        self.assertEqual(result['startup_remaining_s'], 2)

    def test_active_setup_session_does_not_show_closing(self):
        self.assertEqual(project_onboarding(status(session_active=True,startup_remaining_s=0))['state'],'ready')

    def test_shutdown_requested_without_client_is_closing(self):
        result = project_onboarding(status(
            phase='hotspot',session_active=False,should_exit=True,startup_remaining_s=0))
        self.assertEqual(result['state'], 'window_closing')
        self.assertIn('reboot', result['next_action'])

    def test_starting_status_is_not_falsely_scanning(self):
        self.assertEqual(project_onboarding(status(phase='starting',hotspot={'active':False}))['state'],'starting')

    def test_invalid_remaining_does_not_crash(self):
        self.assertEqual(project_onboarding(status(
            phase='starting',hotspot={},session_active=False,startup_remaining_s='no'))['startup_remaining_s'],None)

    def test_connected_ip_guidance_is_honest(self):
        result = project_onboarding(status(phase='connected',
            last_status={'last_known_ip':'192.168.1.25'}))
        self.assertIn('last known Pi IP', result['next_action'])

    def test_no_backend_status_still_safe(self):
        self.assertEqual(project_onboarding(None)['state'], 'starting')


class OnboardingHtmlTests(unittest.TestCase):
    def setUp(self):
        self.handler = RequestHandler.__new__(RequestHandler)
        self.handler.controller = SimpleNamespace(
            csrf_token='safe-token',hostname='raspberrypi',
            config={'server':{'startup_wait_s':5},
                    'network':{'hotspot_url':'http://192.168.4.1/'}})

    def test_failed_markup_has_explicit_next_step_not_private_error(self):
        data=status(connection_attempt={'status':'error','message':'password-here'},
                    known_connections=[{'name':'saved-home','autoconnect':'yes'}])
        page=self.handler.render_index_body(data)
        self.assertIn('Wi-Fi setup failed',page)
        self.assertIn('Check the Wi-Fi name and password',page)
        self.assertNotIn('password-here',page)
        self.assertEqual(page.count('name="csrf_token"')+page.count("name='csrf_token'"),3)

    def test_closing_markup_still_mentions_five_second_policy(self):
        page=self.handler.render_index_body(status(session_active=False,startup_remaining_s=1))
        self.assertIn('Setup window closing',page)
        self.assertIn('5 seconds',page)
        self.assertIn('1s before automatic exit',page)

    def test_html_shell_still_formats_with_embedded_client_script(self):
        page=HTML_SHELL.format(title='PiBooter Test',subtitle='Setup',notice='',body='<main>Safe</main>',
                               status_timer='setInterval(refreshStatus, 3000);')
        self.assertIn('showSubmittedState',page)
        self.assertIn("fetch('/api/status')",page)
        self.assertIn('PiBooter Test',page)


class OnboardingRuntimeTests(unittest.TestCase):
    def test_rescan_resets_scan_status_after_success(self):
        controller=PiBooterController.__new__(PiBooterController)
        controller._scan_in_progress=False
        states=[]
        controller.get_scan_results=lambda force_rescan: states.append(controller._scan_in_progress)
        controller.refresh_state=lambda ensure_hotspot: states.append(controller._scan_in_progress)
        controller.rescan()
        self.assertEqual(states,[True,True])
        self.assertFalse(controller._scan_in_progress)

    def test_rescan_resets_status_when_scan_fails(self):
        controller=PiBooterController.__new__(PiBooterController)
        controller._scan_in_progress=False
        def fail(force_rescan):
            self.assertTrue(controller._scan_in_progress)
            raise OSError('Scan failed')
        controller.get_scan_results=fail
        controller.refresh_state=Mock()
        with self.assertRaises(OSError):
            controller.rescan()
        self.assertFalse(controller._scan_in_progress)

    def test_failed_network_command_redacts_wifi_and_hotspot_secret(self):
        controller=PiBooterController.__new__(PiBooterController)
        controller._connection_lock=threading.Lock()
        secret='really-private-password'
        hotspot='another-private-hotspot-key'
        controller.network=Mock()
        controller.network.connect_to_wifi.return_value=CommandResult(
            ok=False,stderr='Error ' + secret + ' ' + hotspot)
        controller.network.start_hotspot.return_value=CommandResult(ok=True)
        controller.state=Mock()
        controller.get_scan_results=Mock(return_value=[])
        controller.refresh_state=Mock()
        controller.config={'network':{'hotspot_autostart_when_unconfigured':True,
                                       'hotspot_password':hotspot}}
        controller.hotspot_ssid='PiBooter-test'
        controller._run_connection_attempt('home',secret,False)
        calls=str(controller.state.log.call_args_list)+str(controller.state.update.call_args_list)
        self.assertNotIn(secret,calls)
        self.assertNotIn(hotspot,calls)
        self.assertIn('Wi-Fi authentication failed',calls)
        self.assertNotIn('Error ' + secret,calls)

    def test_unexpected_network_exception_becomes_failed_state(self):
        controller=PiBooterController.__new__(PiBooterController)
        controller._connection_lock=threading.Lock()
        controller.network=Mock()
        controller.network.connect_to_wifi.side_effect=RuntimeError('network unavailable')
        controller.state=Mock()
        controller.config={'network':{'hotspot_autostart_when_unconfigured':False,
                                       'hotspot_password':'private-hotspot'}}
        controller.get_scan_results=Mock(return_value=[])
        controller.refresh_state=Mock()
        controller._run_connection_attempt('home','private-wifi',False)
        latest=controller.state.update.call_args.kwargs
        self.assertEqual(latest['connection_attempt']['status'],'error')
        self.assertIn('NetworkManager could not connect',latest['last_error'])


if __name__ == '__main__':
    unittest.main()
