"""Exercise Windows session decisions with actual protocol bytes, without a LAN."""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from scapy.all import Ether, IP, UDP, Raw
import portal_active_probe as core
import portal_tui as tui
import portal_windows as win
import portal_windows_network as net
from test_probe import fixture, field


class WindowsSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.clock = 0
        self.events, self.sent, self.packets = [], [], []
        self.state = {'config': {'interface': r'\Device\NPF_{test}',
                                'ps5_ip': '192.0.2.10', 'portal_ip': '192.0.2.20'},
                      'own_mac': '02:00:00:00:00:01', 'ps5_mac': '02:00:00:00:00:02',
                      'portal_mac': '02:00:00:00:00:03'}
        self.rx, self.child, self.witness = MagicMock(), MagicMock(), MagicMock()
        self.rx.recv_raw.side_effect = self.receive
        self.child.poll.return_value = None
        self.witness.expected = set()
        self.witness.report.return_value = {'all_expected_observed': True}
        for override in (
            patch.object(net, 'ROOT', self.root), patch.object(net, 'require_windows'),
            patch.object(net, 'configure', return_value=self.state['config']),
            patch.object(net, 'PS5', self.state['config']['ps5_ip']),
            patch.object(net, 'PORTAL', self.state['config']['portal_ip']),
            patch.object(net, 'preflight', return_value=self.state),
            patch.object(net, 'open_socket', return_value=self.rx),
            patch.object(win, 'Witness', return_value=self.witness),
            patch.object(win.time, 'monotonic', side_effect=lambda: self.clock),
            patch.object(win.time, 'sleep', side_effect=self.sleep),
            patch.object(win.subprocess, 'CREATE_NEW_PROCESS_GROUP', 512, create=True),
            patch.object(win.subprocess, 'DETACHED_PROCESS', 8, create=True),
        ):
            self.stack.enter_context(override)
        self.lock = self.stack.enter_context(patch.object(net, 'MachineLock'))
        self.spawn = self.stack.enter_context(patch.object(win.subprocess, 'Popen', side_effect=self.watchdog))
        self.send = self.stack.enter_context(patch.object(net, 'send_raw', side_effect=self.send_packet))

    def sleep(self, seconds):
        self.clock = round(self.clock + seconds, 6)

    def receive(self):
        self.sleep(.05)
        if self.packets and self.packets[0][0] <= self.clock:
            _, packet = self.packets.pop(0)
            return None, packet, self.clock
        return None, None, None

    def send_packet(self, sock, packet):
        self.sent.append((self.clock, bytes(packet)))

    def watchdog(self, args, **kwargs):
        Path(args[-1]).with_suffix('.ready').write_text('ready')
        return self.child

    def progress(self, event):
        self.events.append((self.clock, event))
        return True

    def run_session(self, callback=None, **kwargs):
        return win.run_session('65', progress=callback or self.progress,
                               config=self.state['config'], **kwargs)

    def frame(self, payload, direction):
        a, b = self.state['config']['portal_ip'], self.state['config']['ps5_ip']
        src, dst = (a, b) if direction == 'out' else (b, a)
        source_mac = self.state['portal_mac' if direction == 'out' else 'ps5_mac']
        sport, dport = (50000, 9296) if direction == 'out' else (9296, 50000)
        return bytes(Ether(src=source_mac, dst=self.state['own_mac']) /
                     IP(src=src, dst=dst) / UDP(sport=sport, dport=dport) / Raw(payload))

    def session_packets(self, start=6, *, disconnect=False):
        def control(kind, body=b''):
            header = bytearray(26)
            header[14] = 1
            return bytes(header) + field(1, kind) + body
        startup = fixture()[0]
        quality = control(16, field(17, field(1, 58_374_000)))
        session = [(startup, 'out'),
                   (control(1, field(3, field(1, 20) + field(3, 1) + field(4, 1))), 'in'),
                   (control(13), 'in')] + [(quality, 'in')] * 3
        # These arrive after three target samples, during the recovery handoff.
        session += ([(control(8), 'in')] if disconnect else
                    [(b'pending-media-packet', 'in'), (startup, 'out')])
        self.packets = [(start + index * .1, self.frame(payload, direction))
                        for index, (payload, direction) in enumerate(session)]

    def test_ready_starts_full_countdown_and_watchdog_outlasts_confirmation(self):
        report = self.run_session()
        ready = next((stamp, e) for stamp, e in self.events if e['type'] == 'ready')
        self.assertGreaterEqual(ready[0], 5)
        self.assertEqual(ready[1]['seconds'], 120)
        restoring = next(stamp for stamp, e in self.events if e['type'] == 'restoring')
        self.assertGreaterEqual(restoring - ready[0], 119.9)
        self.assertEqual(report['watchdog_seconds'], 155)
        self.assertIn('155', self.spawn.call_args.args[0])
        self.assertEqual(tui.summarize(report).title, 'No new connection detected')
        self.assertEqual(report['restoration_errors'], [])

    def test_late_startup_still_confirms_and_emits_shared_states(self):
        self.session_packets(124.5)
        report = self.run_session()
        self.assertTrue(report['high_target_confirmed'])
        self.assertEqual(tui.summarize(report).kind, 'success')
        kinds = [event['type'] for _, event in self.events]
        for kind in ('checking', 'preparing', 'ready', 'modified', 'observed', 'confirmed', 'restoring'):
            self.assertIn(kind, kinds)
        self.assertGreater(self.clock, 125)
        self.assertLess(self.clock, 141)

    def test_restore_forwards_media_and_identical_retransmission_before_close(self):
        self.session_packets()
        report = self.run_session()
        payloads = [bytes(Ether(raw)[UDP].payload) for _, raw in self.sent if UDP in Ether(raw)]
        startup = payloads[0]
        self.assertEqual(payloads.count(startup), 2)
        self.assertIn(b'pending-media-packet', payloads)
        self.assertEqual(report['unique_mutated_sequences'], 1)
        self.assertEqual(report['restoration_forwarded_packets'], {'in': 1, 'out': 1})
        self.assertFalse(report['playback_verified'])
        self.assertFalse(report['restoration_peer_state_verified'])
        self.assertEqual(report['restoration_errors'], [])
        self.child.terminate.assert_called_once()
        self.lock.return_value.close.assert_called_once()
        repair = [stamp for stamp, raw in self.sent if net.ARP in Ether(raw)
                  and Ether(raw)[net.ARP].hwsrc != self.state['own_mac']]
        self.assertGreaterEqual(max(repair) - min(repair), 1.7)

    def test_disconnect_during_restore_invalidates_success(self):
        self.session_packets(disconnect=True)
        report = self.run_session()
        self.assertFalse(report['high_target_confirmed'])
        self.assertNotEqual(tui.summarize(report).kind, 'success')

    def test_cancellation_and_retry_leave_no_session_or_profile_state(self):
        original = core.network, core.PATCH_DELTA, core.CONFIRM_TARGET
        def cancel(event):
            self.progress(event)
            return event['type'] != 'ready'
        stopped = self.run_session(cancel)
        self.assertEqual(tui.summarize(stopped).title, 'Attempt stopped')
        self.assertEqual(stopped['restoration_errors'], [])
        self.assertEqual((core.network, core.PATCH_DELTA, core.CONFIRM_TARGET), original)
        self.events.clear()
        self.session_packets(self.clock + 6)
        report = self.run_session()
        self.assertEqual(tui.summarize(report).kind, 'success')
        self.assertEqual(report['unique_mutated_sequences'], 1)
        self.assertEqual(self.lock.return_value.close.call_count, 2)
        self.assertEqual((core.network, core.PATCH_DELTA, core.CONFIRM_TARGET), original)
        self.assertEqual(len(list(self.root.glob('experiments/*/report.json'))), 2)

    def test_cancel_before_preparation_never_sends_redirects(self):
        for phase in ('checking', 'preparing'):
            self.sent.clear()
            callback = lambda event: event['type'] != phase
            if phase == 'checking':
                with self.assertRaises(KeyboardInterrupt):
                    self.run_session(callback)
            else:
                report = self.run_session(callback)
                self.assertEqual(report['run_error'], 'Cancelled by user')
            self.assertEqual(self.sent, [])

    def test_failed_repair_continues_other_attempts_and_keeps_watchdog(self):
        self.session_packets()
        def send(sock, frame):
            packet = Ether(bytes(frame))
            if net.ARP in packet and packet[net.ARP].hwsrc != self.state['own_mac']:
                raise OSError('injection failed')
            self.send_packet(sock, frame)
        self.send.side_effect = send
        report = self.run_session()
        self.assertEqual(tui.summarize(report).kind, 'error')
        self.assertEqual(len(report['restoration_errors']), 12)
        self.child.terminate.assert_not_called()

    def test_preflight_or_busy_machine_never_opens_capture(self):
        self.lock.side_effect = RuntimeError('Another Portal experiment or recovery watchdog is running.')
        with self.assertRaises(core.PreflightError):
            self.run_session()
        net.open_socket.assert_not_called()
        self.assertFalse((self.root / 'experiments').exists())

    def test_watchdog_failure_before_ready_never_changes_arp(self):
        def spawn(args, **kwargs):
            return self.child
        self.spawn.side_effect = spawn
        self.child.poll.return_value = 2
        report = self.run_session()
        self.assertIn('did not become ready', report['run_error'])
        self.assertFalse(self.sent)
        self.assertNotEqual(tui.summarize(report).kind, 'success')

    def test_target_without_egress_is_incomplete(self):
        self.session_packets()
        self.witness.report.return_value = {'all_expected_observed': False}
        report = self.run_session()
        self.assertTrue(report['high_target_confirmed'])
        self.assertEqual(tui.summarize(report).title, 'Target reported; verification incomplete')

    def test_cli_still_requires_baseline_but_guided_path_does_not(self):
        with self.assertRaisesRegex(core.PreflightError, 'Baseline-Windows'):
            self.run_session(require_baseline=True)
        self.assertEqual(self.sent, [])
        report = self.run_session()
        self.assertTrue(report['completed'])


@unittest.skipUnless(os.name == 'nt', 'Native Windows kernel mutex')
class NativeLockTests(unittest.TestCase):
    def test_watchdog_handle_blocks_retry_until_recovery_finishes(self):
        with patch.object(net, 'MUTEX_NAME', 'Local\\BetterPortalTest-' + str(os.getpid())):
            first = net.MachineLock()
            self.addCleanup(first.close)
            guard = net.MachineLock(existing=True)
            self.addCleanup(guard.close)
            with self.assertRaisesRegex(RuntimeError, 'Another Portal'):
                net.MachineLock()
            first.close()
            with self.assertRaisesRegex(RuntimeError, 'Another Portal'):
                net.MachineLock()
            guard.close()
            retry = net.MachineLock()
            retry.close()
            retry.close()


if __name__ == '__main__':
    unittest.main()
