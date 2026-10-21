"""Npcap ABI faults and packet buffers, below the production Windows adapter."""
from collections import deque
from contextlib import ExitStack
import ctypes
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scapy.all import Ether, IP, UDP, Raw
import scapy.libs
import portal_auto_platform as auto
import portal_windows as win
import portal_windows_network as net


class Timeval(ctypes.Structure):
    _fields_ = [('tv_sec', ctypes.c_long), ('tv_usec', ctypes.c_long)]


class PacketHeader(ctypes.Structure):
    _fields_ = [('ts', Timeval), ('caplen', ctypes.c_uint32),
               ('len', ctypes.c_uint32)]


class CaptureAPI:
    """Only the native boundary is simulated; packet buffers use real pointers."""
    PCAP_ERRBUF_SIZE = 256
    PCAP_ERROR = -1
    PCAP_ERROR_BREAK = -2
    PCAP_ERROR_NOT_ACTIVATED = -3
    pcap_pkthdr = PacketHeader

    def __init__(self):
        self.reads = deque()
        self.buffers = []
        self.sent = []
        self.error = b'adapter disconnected'
        self.nonblock_result = self.send_result = self.mintocopy_result = 0
        self.nonblock_calls = []

    def pcap_setmintocopy(self, handle, minimum):
        return self.mintocopy_result

    def pcap_setnonblock(self, handle, enabled, errbuf):
        self.nonblock_calls.append(enabled)
        if self.nonblock_result == self.PCAP_ERROR:
            errbuf.value = b'nonblocking capture unavailable'
        return self.nonblock_result

    def pcap_geterr(self, handle):
        return self.error

    def packet(self, data, wire_length=None):
        header = PacketHeader(Timeval(123, 250000), len(data),
                              len(data) if wire_length is None else wire_length)
        buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
        self.buffers.append((header, buffer))
        self.reads.append((header, buffer))

    def pcap_next_ex(self, handle, header_out, packet_out):
        item = self.reads.popleft() if self.reads else 0
        if isinstance(item, int):
            return item
        header, buffer = item
        ctypes.cast(header_out, ctypes.POINTER(ctypes.POINTER(PacketHeader)))[0] = ctypes.pointer(header)
        ctypes.cast(packet_out, ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)))[0] = buffer
        return 1

    def pcap_sendpacket(self, handle, data, size):
        if self.send_result == 0:
            self.sent.append(bytes(data[:size]))
        return self.send_result


class ScapyCapture:
    """The pinned Scapy wrapper discards these native receive/setup errors."""
    def __init__(self, api):
        self.api = api
        self.pcap_fd = self
        self.pcap = object()
        self.closed = False
        self.header = ctypes.POINTER(PacketHeader)()
        self.data = ctypes.POINTER(ctypes.c_ubyte)()

    def datalink(self):
        return 1

    def setnonblock(self, enabled):
        self.api.pcap_setnonblock(self.pcap, enabled, ctypes.create_string_buffer(256))

    def recv_raw(self):
        result = self.api.pcap_next_ex(self.pcap, ctypes.byref(self.header), ctypes.byref(self.data))
        if result <= 0:
            return None, None, None
        # Use caplen in the test double so a failing test cannot overread memory.
        return Ether, ctypes.string_at(self.data, self.header.contents.caplen), 123.25

    def send(self, data):
        status = self.api.pcap_sendpacket(self.pcap, data, len(data))
        return len(data) if status == 0 else status

    def close(self):
        self.closed = True


class WindowsIOTests(unittest.TestCase):
    def setUp(self):
        self.api = CaptureAPI()
        self.capture = ScapyCapture(self.api)
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict('sys.modules', {'scapy.libs.winpcapy': self.api}))
        self.stack.enter_context(patch.object(scapy.libs, 'winpcapy', self.api, create=True))
        self.stack.enter_context(patch.object(net.conf, 'L2socket', return_value=self.capture))
        self.stack.enter_context(patch.object(net, 'IFACE', SimpleNamespace(name='Ethernet')))

    def open(self):
        sock = net.open_socket('ip')
        self.addCleanup(sock.close)
        return sock

    def test_nonblocking_failure_closes_capture_before_returning(self):
        self.api.nonblock_result = -1
        with self.assertRaisesRegex(RuntimeError, 'nonblocking capture unavailable'):
            self.open()
        self.assertTrue(self.capture.closed)

    def test_low_latency_failure_keeps_driver_error(self):
        self.api.mintocopy_result = -1
        with self.assertRaisesRegex(RuntimeError, 'adapter disconnected'):
            self.open()
        self.assertTrue(self.capture.closed)

    def test_read_error_is_not_an_empty_queue(self):
        sock = self.open()
        self.api.reads.append(-1)
        with self.assertRaisesRegex(RuntimeError, 'adapter disconnected'):
            sock.recv_raw()

    def test_terminal_read_status_does_not_reuse_stale_error_text(self):
        sock = self.open()
        for status, expected in ((-2, 'Capture ended'), (-3, 'not activated'),
                                 (-100, 'Unexpected Npcap status -100')):
            with self.subTest(status=status):
                self.api.reads.append(status)
                with self.assertRaisesRegex(RuntimeError, expected) as caught:
                    sock.recv_raw()
                self.assertNotIn('adapter disconnected', str(caught.exception))

    def test_inactive_capture_setup_does_not_reuse_stale_error_text(self):
        self.api.nonblock_result = -3
        with self.assertRaisesRegex(RuntimeError, 'not activated'):
            self.open()
        self.assertTrue(self.capture.closed)

    def test_empty_queue_remains_nonblocking_even_with_old_error_text(self):
        sock = self.open()
        self.assertEqual(sock.recv_raw(), (None, None, None))
        self.assertEqual(self.api.nonblock_calls, [True])

    def test_frame_bytes_are_copied_before_native_buffer_is_reused(self):
        packet = bytes(Ether(src='02:00:00:00:00:03', dst='02:00:00:00:00:01') /
                       IP(src='192.0.2.20', dst='192.0.2.10') / UDP() / Raw(b'baseline'))
        self.api.packet(packet)
        sock = self.open()
        kind, raw, timestamp = sock.recv_raw()
        self.assertIs(kind, Ether)
        self.assertEqual(raw, packet)
        self.assertEqual(timestamp, 123.25)
        self.api.buffers[0][1][0] ^= 255
        self.assertEqual(raw, packet)

    def test_truncated_frame_is_rejected_before_forwarding(self):
        self.api.packet(b'\x00' * 42, wire_length=1500)
        with self.assertRaisesRegex(RuntimeError, '[Tt]runcated'):
            self.open().recv_raw()
        self.assertEqual(self.api.sent, [])

    def test_invalid_packet_buffers_are_rejected_before_copying(self):
        sock = self.open()
        self.api.reads.append(1)  # Success without setting the output pointers.
        with self.assertRaisesRegex(RuntimeError, 'empty packet buffer'):
            sock.recv_raw()
        for caplen, wirelen in ((0, 0), (61, 60), (net.MTU + 1, net.MTU + 1)):
            with self.subTest(caplen=caplen, wirelen=wirelen):
                self.api.packet(b'\x00' * 60, wire_length=wirelen)
                self.api.buffers[-1][0].caplen = caplen
                with patch.object(net.ctypes, 'string_at') as copy:
                    with self.assertRaisesRegex(RuntimeError, 'invalid packet length'):
                        sock.recv_raw()
                    copy.assert_not_called()

    def test_injection_uses_sendpacket_success_and_preserves_failure_reason(self):
        sock = self.open()
        frame = b'\x00' * 60
        net.send_raw(sock, frame)
        self.assertEqual(self.api.sent, [frame])
        self.api.send_result = -1
        with self.assertRaisesRegex(RuntimeError, 'adapter disconnected'):
            net.send_raw(sock, frame)
        self.assertEqual(self.api.sent, [frame])

    def test_witness_reports_capture_failure_instead_of_missing_egress(self):
        witness = win.Witness({'own_mac': '02:00:00:00:00:01'})
        self.addCleanup(witness.sock.close)
        self.api.reads.append(-1)
        with self.assertRaisesRegex(RuntimeError, 'adapter disconnected'):
            witness.drain()
        self.assertIsNotNone(witness.report()['read_error'])
        self.assertFalse(witness.report()['all_expected_observed'])

    def test_windows_automatic_relay_propagates_the_same_capture_error(self):
        with patch.object(auto.sys, 'platform', 'win32'):
            sock = auto.open_socket('ip')
            self.addCleanup(sock.close)
            self.api.reads.append(-1)
            with self.assertRaisesRegex(RuntimeError, 'adapter disconnected'):
                auto.receive(sock)

    def session(self, *, baseline=False, fail_after=None):
        import test_windows_session as sessions
        open_socket, send_raw = net.open_socket, net.send_raw
        case = sessions.WindowsSessionTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        case.session_packets()
        native_read, native_send = self.api.pcap_next_ex, self.api.pcap_sendpacket

        def read(*args):
            case.sleep(.05)
            if fail_after is not None and case.clock >= fail_after:
                return -1
            if case.packets and case.packets[0][0] <= case.clock:
                _, packet = case.packets.pop(0)
                self.api.packet(packet)
            return native_read(*args)

        def send(handle, data, size):
            result = native_send(handle, data, size)
            if result == 0:
                case.send_packet(None, data)
            return result

        with patch.object(net, 'open_socket', open_socket), \
                patch.object(net, 'send_raw', send_raw), \
                patch.object(net.conf, 'L2socket', side_effect=lambda **kw: ScapyCapture(self.api)), \
                patch.object(self.api, 'pcap_next_ex', side_effect=read), \
                patch.object(self.api, 'pcap_sendpacket', side_effect=send):
            report = case.run_session(baseline=baseline)
        return case, report

    def test_baseline_replays_both_directions_without_changing_content(self):
        from test_probe import fixture
        case, report = self.session(baseline=True)
        self.assertTrue(win.baseline_ok(report))
        self.assertEqual(report['unique_mutated_sequences'], 0)
        payloads = [bytes(Ether(raw)[UDP].payload) for raw in self.api.sent if UDP in Ether(raw)]
        self.assertEqual(payloads.count(fixture()[0]), 2)
        self.assertIn(b'pending-media-packet', payloads)
        self.assertEqual(report['restoration_errors'], [])
        case.child.terminate.assert_called_once()

    def test_active_session_still_mutates_and_recovers_through_native_buffers(self):
        from test_probe import fixture
        case, report = self.session()
        self.assertTrue(report['high_target_confirmed'])
        self.assertEqual(report['unique_mutated_sequences'], 1)
        payloads = [bytes(Ether(raw)[UDP].payload) for raw in self.api.sent if UDP in Ether(raw)]
        self.assertNotIn(fixture()[0], payloads)
        self.assertEqual(payloads.count(payloads[0]), 2)
        self.assertIn(b'pending-media-packet', payloads)
        self.assertEqual(report['restoration_errors'], [])
        case.child.terminate.assert_called_once()

    def test_native_read_failure_stops_baseline_and_attempts_all_repairs(self):
        case, report = self.session(baseline=True, fail_after=6)
        self.assertFalse(report['completed'])
        self.assertIn('Npcap packet capture failed: adapter disconnected', report['run_error'])
        self.assertLess(case.clock, 10)
        repairs = [Ether(raw) for raw in self.api.sent if net.ARP in Ether(raw)
                   and Ether(raw)[net.ARP].hwsrc != case.state['own_mac']]
        self.assertEqual(len(repairs), 12)
        # Failed capture also prevents draining in-flight traffic during repair.
        self.assertTrue(report['restoration_errors'])
        case.child.terminate.assert_not_called()
        self.assertFalse((case.root / 'windows-baseline.json').exists())

    def test_native_setup_failure_stops_before_redirecting_peers(self):
        self.api.nonblock_result = -1
        case, report = self.session(baseline=True)
        self.assertFalse(report['completed'])
        self.assertIn('nonblocking capture unavailable', report['run_error'])
        self.assertEqual(self.api.sent, [])
        case.spawn.assert_not_called()
        self.assertFalse((case.root / 'windows-baseline.json').exists())


if __name__ == '__main__':
    unittest.main()
