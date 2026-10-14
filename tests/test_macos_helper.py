"""Authorization-boundary tests with private pipes and synthetic relay I/O."""
import contextlib
import io
import json
import os
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import portal_macos_client as client
import portal_macos_runtime as runtime
import portal_active_probe as probe
import portal_tui as tui
import test_tui as relay_tests


class FakeBridge:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []
        self.closed = False

    def exchange(self, request):
        self.requests.append(request)
        value = next(self.responses)
        if isinstance(value, BaseException):
            raise value
        return value

    def close(self):
        self.closed = True


class ClientTests(unittest.TestCase):
    def run_client(self, responses, progress=lambda event: True):
        self.bridge = FakeBridge(responses)
        with tempfile.TemporaryDirectory() as directory, patch.object(client.time, 'sleep'):
            root = Path(directory)
            report = client.run_session('65', {'interface': 'en0', 'ps5_ip': '192.168.1.20',
                                              'portal_ip': '192.168.1.30'}, progress,
                                        report_root=root, bridge_factory=lambda: self.bridge)
            if report.get('directory'):
                self.assertEqual(json.loads((Path(report['directory']) / 'report.json').read_text()), report)
            return report

    def test_normal_flow_preserves_events_and_saves_report_as_current_user(self):
        events = []
        report = self.run_client([{}, {'started': True},
                                 {'events': [{'type': 'ready', 'seconds': 120}]},
                                 {'report': {'completed': True, 'restoration_errors': [],
                                             'watchdog_state': '/root/secret'}}],
                                lambda event: events.append(event) or True)
        self.assertTrue(report['completed'])
        self.assertTrue(report['managed_helper'])
        self.assertIsNone(report['watchdog_state'])
        self.assertIn({'type': 'ready', 'seconds': 120}, events)
        self.assertTrue(self.bridge.closed)
        self.assertEqual(set(self.bridge.requests[1]), {'op', 'config', 'profile'})

    def test_missing_revoked_or_busy_helper_does_not_submit_start(self):
        for response in (OSError('not installed'), RuntimeError('permission revoked'),
                         {'busy': True}, {'recovery_pending': True}, {'removing': True}):
            with self.subTest(response=response), self.assertRaises(client.HelperUnavailable):
                self.run_client([response])
            self.assertEqual(self.bridge.requests, [{'op': 'status'}])
            self.assertTrue(self.bridge.closed)

    def test_cancel_waits_for_result_and_close_does_not_skip_recovery(self):
        report = self.run_client([{}, {'started': True},
                                 {'events': [{'type': 'ready', 'seconds': 120}]},
                                 {'report': {'completed': False, 'run_error': 'Cancelled by user',
                                             'restoration_errors': []}}],
                                lambda event: event['type'] != 'ready')
        self.assertEqual(self.bridge.requests[-1], {'op': 'cancel'})
        self.assertEqual(tui.summarize(report).title, 'Attempt stopped')
        self.assertTrue(self.bridge.closed)

    def test_unknown_start_outcome_or_disconnection_never_claims_recovery(self):
        for responses in ([{}, RuntimeError('lost start reply')],
                          [{}, {'started': True}, RuntimeError('daemon stopped')]):
            report = self.run_client(responses)
            self.assertEqual(tui.summarize(report).kind, 'error')
            self.assertNotIn('preflight_failed', report)
            self.assertTrue(self.bridge.closed)

    def test_keyboard_interrupt_during_poll_requests_cancellation(self):
        report = self.run_client([{}, {'started': True}, KeyboardInterrupt(),
                                 {'report': {'completed': False, 'restoration_errors': [],
                                             'run_error': 'Cancelled by user'}}])
        self.assertEqual(self.bridge.requests[-1], {'op': 'cancel'})
        self.assertFalse(report['completed'])

    def test_rejected_before_start_creates_no_bridge(self):
        factory = MagicMock(side_effect=AssertionError('No bridge should be created'))
        result = client.run_session('65', {}, lambda _: False, bridge_factory=factory)
        self.assertEqual(result['run_error'], 'Cancelled by user')
        factory.assert_not_called()

    def test_privileged_report_paths_are_never_exported(self):
        report = runtime.public_report({'watchdog_state': '/secret', 'directory': '/private',
                                        'counts': {'forwarded_in': 5}})
        self.assertIsNone(report['directory'])
        self.assertIsNone(report['watchdog_state'])
        self.assertEqual(report['counts']['forwarded_in'], 5)

    @unittest.skipIf(os.name == 'nt', 'POSIX storage checks')
    def test_preplanted_directory_symlink_and_user_owned_storage_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'target'
            target.mkdir(mode=0o700)
            link = root / 'link'
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(RuntimeError):
                runtime.private_directory(link)
            if os.geteuid() != 0:
                with self.assertRaises(RuntimeError):
                    runtime.private_directory(target)
            with self.assertRaises(ValueError):
                runtime.recovery_path(root / 'state.json')


@unittest.skipIf(os.name == 'nt', 'macOS source launcher checks')
class SourceLauncherTests(unittest.TestCase):
    def test_direct_probe_rejects_root_python_before_network_access(self):
        with patch.object(probe.sys, 'platform', 'darwin'), \
             patch.object(probe.network, 'configure') as configure:
            with self.assertRaisesRegex(RuntimeError, 'installed connection helper'):
                probe.run(True)
            configure.assert_not_called()
            with patch.object(probe.sys, 'argv', ['portal_active_probe.py']), \
                 contextlib.redirect_stderr(io.StringIO()) as stderr, \
                 self.assertRaises(SystemExit) as stopped:
                probe.main()
            self.assertEqual(stopped.exception.code, 2)
            self.assertIn('do not run this script with sudo', stderr.getvalue())
            configure.assert_not_called()

    def test_direct_mac_launch_uses_helper_and_rejects_sudo(self):
        with tempfile.TemporaryDirectory() as directory:
            user_data = Path(directory) / 'user data'
            with patch.object(tui, 'ROOT', Path(directory)), \
                 patch.object(tui.sys, 'platform', 'darwin'), \
                 patch.object(tui.sys, 'argv', ['portal_tui.py']), \
                 patch.object(tui.sys.stdin, 'isatty', return_value=True), \
                 patch.object(tui.sys.stdout, 'isatty', return_value=True), \
                 patch('portal_macos_client.user_directory', return_value=user_data), \
                 patch('curses.wrapper', side_effect=lambda draw: draw(MagicMock())), \
                 patch.object(tui, 'Wizard') as wizard:
                wizard.return_value.run.return_value = 0
                with patch.object(tui.os, 'geteuid', return_value=501):
                    self.assertEqual(tui.main(), 0)
                self.assertTrue(wizard.call_args.kwargs['helper'])
                self.assertEqual(wizard.call_args.kwargs['data_dir'], user_data)
                self.assertTrue(user_data.is_dir())
                wizard.reset_mock()
                with patch.object(tui.os, 'geteuid', return_value=0), \
                     contextlib.redirect_stderr(io.StringIO()) as stderr, \
                     self.assertRaises(SystemExit) as stopped:
                    tui.main()
                self.assertEqual(stopped.exception.code, 2)
                self.assertIn('normal Mac user', stderr.getvalue())
                wizard.assert_not_called()


@unittest.skipIf(os.name == 'nt', 'POSIX relay fixture')
class HelperRelayTests(relay_tests.RelayLifecycleTests):
    """Run the existing timing/cancel/retransmit/failure tests through helper mode."""
    def setUp(self):
        super().setUp()
        self.helper_storage = self.root / 'helper'
        self.helper_storage.mkdir()
        self.context = probe.HelperContext(501, self.helper_storage,
                                           ('/protected/PortalRuntime', 'watchdog'), 'a' * 32)
        self.stack.enter_context(patch.dict(os.environ, {'SUDO_UID': '99999', 'SUDO_GID': '99999'}))
        self.original_spawn = self.spawn.side_effect

        def spawn(*args, **kwargs):
            command = args[0]
            saved = Path(command[command.index('--watchdog') + 1])
            saved.with_suffix('.ready').write_text('ready')
            return self.watcher
        self.spawn.side_effect = spawn

    def run_relay(self, callback=None):
        return probe.run(True, finish_on_high_target=True, connect_timeout=120,
                         confirmation_timeout=15, config=self.state['config'],
                         progress=callback or self.progress, helper_context=self.context)

    def test_helper_uses_fixed_worker_context_and_never_chowns_to_sudo_uid(self):
        report = self.run_relay()
        self.assertTrue(Path(report['directory']).is_relative_to(self.helper_storage))
        self.assertTrue(Path(report['watchdog_state']).is_relative_to(self.helper_storage))
        probe.os.chown.assert_not_called()
        self.assertEqual(self.spawn.call_args.args[0][:2], ['/protected/PortalRuntime', 'watchdog'])
        self.assertNotIn('SUDO_UID', self.spawn.call_args.kwargs['env'])
        self.assertEqual(self.spawn.call_args.kwargs['env']['PYINSTALLER_RESET_ENVIRONMENT'], '1')
        state = json.loads(Path(report['watchdog_state']).read_text())
        self.assertEqual(state['helper_lock_token'], 'a' * 32)

    def test_helper_needs_no_sudo_environment(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(self.run_relay()['completed'])

    def test_no_network_changes_without_watchdog_readiness(self):
        self.spawn.side_effect = None
        self.watcher.poll.return_value = 1
        report = self.run_relay()
        probe.network.syswrite.assert_not_called()
        self.restore.assert_not_called()
        self.assertFalse(report['completed'])
        self.assertIn('Independent recovery', report['run_error'])


@unittest.skipIf(os.name == 'nt', 'macOS/POSIX watchdog signals')
class WatchdogTests(unittest.TestCase):
    def test_recovery_releases_only_its_own_lock_after_success(self):
        import portal_capture as network
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); saved = root / 'state.json'; lock = root / 'lock'
            token = 'a' * 32
            saved.write_text(json.dumps({'helper_lock_token': token}))
            for lock_token, errors, remains in ((token, [], False), ('b' * 32, [], True),
                                                (token, ['repair failed'], True)):
                lock.write_text(lock_token)
                with patch.object(runtime, 'recovery_path', return_value=saved), \
                        patch.object(runtime, 'LOCK', lock), \
                        patch.object(runtime.time, 'sleep') as sleep, \
                        patch.object(runtime, 'stop_parent') as stop, \
                        patch.object(runtime.signal, 'signal'), patch.object(runtime.os, 'umask'), \
                        patch.object(network, 'restore', return_value=errors):
                    self.assertEqual(runtime.watchdog(str(saved), 155), 1 if errors else 0)
                    sleep.assert_called_once_with(155)
                    stop.assert_called_once()
                self.assertEqual(lock.exists(), remains)
                self.assertTrue(saved.with_suffix('.ready').exists())

    def test_watchdog_never_signals_an_orphaned_or_reused_parent(self):
        with patch.object(runtime.os, 'getppid', return_value=1), patch.object(runtime.os, 'kill') as kill:
            runtime.stop_parent(12345)
            runtime.stop_parent(1)
            kill.assert_not_called()

    def test_watchdog_waits_for_parent_exit_before_repair(self):
        with patch.object(runtime.os, 'getppid', side_effect=[12345, 12345, 1, 1]), \
                patch.object(runtime.os, 'kill') as kill, patch.object(runtime.time, 'sleep'):
            runtime.stop_parent(12345)
            kill.assert_called_once_with(12345, signal.SIGTERM)


if __name__ == '__main__':
    unittest.main()
