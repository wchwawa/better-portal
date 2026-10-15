"""Setup failures must be actionable before any relay or recovery starts."""
import contextlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import portal_tui as tui
import portal_tui_platform as platform
import portal_windows_network as network


def terminal():
    return SimpleNamespace(A_BOLD=1, A_DIM=2, A_REVERSE=4, error=RuntimeError,
                           has_colors=lambda: False, curs_set=lambda _: None,
                           flushinp=lambda: None, KEY_UP=259, KEY_DOWN=258,
                           KEY_LEFT=260, KEY_RIGHT=261, KEY_ENTER=343,
                           KEY_BTAB=353, KEY_BACKSPACE=263, KEY_DC=330,
                           KEY_HOME=262, KEY_END=360, KEY_NPAGE=338, KEY_PPAGE=339)


class SetupFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.adapters = [platform.Adapter('virtual', 'Ethernet virtual (172.20.0.1)'),
                         platform.Adapter('wifi', 'Wi-Fi (192.168.1.10)')]
        self.screen = MagicMock()
        self.screen.getmaxyx.return_value = (24, 72)
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(tui, 'windows_adapters', return_value=self.adapters))
        self.stack.enter_context(patch.object(tui, 'default_interface', return_value='en0'))

    def wizard(self, host='win32'):
        wizard = tui.Wizard(self.screen, terminal(), platform=host, data_dir=self.root)
        wizard.language = 'en'
        return wizard

    def test_fresh_windows_form_uses_route_to_both_devices_not_alphabetical_adapter(self):
        from scapy.all import conf
        from scapy import interfaces
        wizard = self.wizard()
        wizard.values[:2] = ['192.168.1.20', '192.168.1.30']
        with patch.object(conf.route, 'resync'), \
                patch.object(conf.route, 'route', return_value=('wifi', '192.168.1.10', '0.0.0.0')), \
                patch.object(interfaces, 'resolve_iface', return_value=SimpleNamespace(network_name='wifi')):
            wizard.change_focus(1)
            wizard.change_focus(1)
        self.assertEqual(wizard.values[2], 'wifi')
        self.assertFalse((self.root / 'config.windows.json').exists())

    def test_adapter_suggestion_requires_both_peers_on_one_available_direct_route(self):
        from scapy.all import conf
        from scapy import interfaces
        values = {'ps5_ip': '192.168.1.20', 'portal_ip': '192.168.1.30'}
        direct = ('wifi', '192.168.1.10', '0.0.0.0')
        cases = (
            (direct, ('virtual', '172.20.0.1', '0.0.0.0')),
            (direct, ('wifi', '192.168.1.10', '192.168.1.1')),
            (direct, ('wifi', values['portal_ip'], '0.0.0.0')),
            (direct, ('wifi', '0.0.0.0', '0.0.0.0')),
            (('missing', '192.168.1.10', '0.0.0.0'),) * 2,
        )
        for routes in cases:
            with self.subTest(routes=routes), patch.object(conf.route, 'resync'), \
                    patch.object(conf.route, 'route', side_effect=routes), \
                    patch.object(interfaces, 'resolve_iface',
                                 side_effect=lambda iface: SimpleNamespace(network_name=iface)):
                self.assertIsNone(platform.windows_adapter_for_peers(values, self.adapters))
        with patch.object(conf.route, 'resync', side_effect=OSError('Route unavailable')):
            self.assertIsNone(platform.windows_adapter_for_peers(values, self.adapters))
        with patch.object(conf.route, 'resync') as resync:
            self.assertIsNone(platform.windows_adapter_for_peers(values, []))
            resync.assert_not_called()

    def test_suggested_adapter_never_overrides_an_explicit_choice_or_runs_on_mac(self):
        with patch.object(tui, 'windows_adapter_for_peers', return_value='wifi') as suggest:
            wizard = self.wizard()
            wizard.values[:2] = ['192.168.1.20', '192.168.1.30']
            self.screen.getch.side_effect = [13, 13, 260, 13, 13, 13]
            self.assertEqual(wizard.configure()['interface'], 'virtual')
            wizard.suggest_adapter()
            self.assertEqual(wizard.values[2], 'virtual')
            # A subsequent launch keeps the explicitly selected, saved adapter.
            suggest.reset_mock()
            again = self.wizard()
            again.suggest_adapter()
            self.assertEqual(again.values[2], 'virtual')
            mac = self.wizard('darwin')
            mac.suggest_adapter()
            self.assertEqual(mac.values[2], 'en0')
            suggest.assert_not_called()

    def test_stale_saved_adapter_is_replaced_by_matching_route(self):
        tui.save_private_json(self.root / 'config.windows.json',
                              {'ps5_ip': '192.168.1.20', 'portal_ip': '192.168.1.30',
                               'interface': 'removed-adapter'})
        wizard = self.wizard()
        with patch.object(tui, 'windows_adapter_for_peers', return_value='wifi'):
            wizard.suggest_adapter()
        self.assertEqual(wizard.values[2], 'wifi')

    def test_details_keep_complete_error_readable_on_both_hosts(self):
        message = 'Windows PowerShell failed. ' + ('diagnostic context ' * 100) + 'CIM_ACCESS_DENIED'
        for host in ('win32', 'darwin'):
            with self.subTest(host=host):
                wizard = self.wizard(host)
                self.screen.reset_mock()
                self.screen.getch.side_effect = [258] * 40 + [27]
                wizard.details({'completed': False, 'preflight_failed': True,
                                'run_error': message, 'restoration_errors': []})
                rendered = ' '.join(str(call.args[2]) for call in self.screen.addstr.call_args_list)
                self.assertIn('CIM_ACCESS_DENIED', rendered)

    def test_windows_powershell_failure_keeps_the_actual_reason(self):
        failure = subprocess.CalledProcessError(1, ['powershell.exe', '-Command', 'long command'],
                                               stderr='Get-NetIPInterface: CIM access denied')
        with patch.object(network.subprocess, 'run', side_effect=failure):
            with self.assertRaisesRegex(RuntimeError, 'CIM access denied'):
                network.forwarding_disabled(12)

    def test_forwarding_unknown_or_malformed_state_is_rejected(self):
        for output in ('null', '[]', '{}', 'not JSON',
                       '{"InterfaceIndex":99,"Forwarding":0}',
                       '{"InterfaceIndex":12,"Forwarding":1}',
                       '{"InterfaceIndex":12,"Forwarding":null}'):
            with self.subTest(output=output), \
                    patch.object(network.subprocess, 'run', return_value=SimpleNamespace(stdout=output)):
                with self.assertRaises(RuntimeError):
                    network.forwarding_disabled(12)

    def test_real_windows_preflight_surfaces_failure_without_starting_relay(self):
        from scapy.all import conf
        config = {'interface': 'wifi', 'ps5_ip': '192.168.1.20', 'portal_ip': '192.168.1.30'}
        wifi = SimpleNamespace(network_name='wifi', name='Wi-Fi', index=12,
                               mac='02:00:00:00:00:01')
        virtual = SimpleNamespace(network_name='virtual', name='VPN', index=13)
        cases = (
            ('Npcap is required.', 'native', None),
            ('Open Windows Terminal as administrator', 'native', None),
            ('PS5 uses VPN', 'route', ('virtual', '172.20.0.1', '0.0.0.0')),
            ('not on the selected local network', 'route', ('wifi', '192.168.1.10', '192.168.1.1')),
            ('Peer IP matches this computer', 'route', ('wifi', config['ps5_ip'], '0.0.0.0')),
            ('CIM access denied', 'forwarding', None),
            ('could not resolve exactly one peer', 'arp', None),
        )
        for reason, stage, route in cases:
            with self.subTest(stage=stage, reason=reason), contextlib.ExitStack() as stack:
                for name in ('IFACE', 'PS5', 'PORTAL'):
                    stack.enter_context(patch.object(network, name))
                stack.enter_context(patch.object(network, 'ROOT', self.root))
                stack.enter_context(patch.object(network, 'require_windows',
                                                 side_effect=RuntimeError(reason) if stage == 'native' else None))
                stack.enter_context(patch.object(network, 'resolve_iface',
                                                 side_effect=lambda name: wifi if name == 'wifi' else virtual))
                stack.enter_context(patch.object(conf.route, 'resync'))
                stack.enter_context(patch.object(conf.route, 'route',
                                                 return_value=route or ('wifi', '192.168.1.10', '0.0.0.0')))
                failure = subprocess.CalledProcessError(1, ['powershell.exe'], stderr=reason)
                stack.enter_context(patch.object(network.subprocess, 'run',
                                                 side_effect=failure if stage == 'forwarding' else None,
                                                 return_value=SimpleNamespace(stdout='{"InterfaceIndex":12,"Forwarding":0}')))
                stack.enter_context(patch.object(network, 'peer_mac', side_effect=RuntimeError(reason)))
                opened = stack.enter_context(patch.object(network, 'open_socket'))
                restored = stack.enter_context(patch.object(network, 'restore'))
                locked = stack.enter_context(patch.object(network, 'MachineLock'))
                wizard = self.wizard()
                with patch.object(wizard, 'progress', return_value=True):
                    report = wizard.connect(config)
                self.assertTrue(report['preflight_failed'])
                self.assertIn(reason, report['run_error'])
                self.assertEqual(tui.summarize(report).title, 'Setup check failed')
                self.assertEqual(report['restoration_errors'], [])
                opened.assert_not_called()
                restored.assert_not_called()
                locked.assert_not_called()
                self.assertFalse((self.root / 'experiments').exists())


if __name__ == '__main__':
    unittest.main()
