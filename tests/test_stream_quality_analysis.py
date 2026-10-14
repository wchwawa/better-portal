"""Offline diagnostics must not confuse missing setup evidence with healthy playback."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scapy.all import Ether, IP, UDP, Raw, wrpcap

from portal_quality import analyze, main
from test_probe import field


class QualityAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.report = self.root / 'report.json'
        self.report.write_text(json.dumps({
            'profile': '100mbps_experimental', 'high_target_confirmed': True,
            'directory': '/private/device-data', 'ps5_ip': '192.0.2.10',
            'restoration_errors': [],
            'ps5_messages': [{'type': 'CONNECTIONQUALITY', 'target_bitrate_raw': 97_087_000}],
        }))

    def packet(self, target, loss, *, sport=9296, stamp=1):
        header = bytearray(26)
        header[14] = 1
        payload = bytes(header) + field(1, 16) + field(17, field(1, target) + field(6, loss))
        packet = (Ether(src='02:00:00:00:00:01', dst='02:00:00:00:00:02') /
                  IP(src='192.0.2.10', dst='192.0.2.20') /
                  UDP(sport=sport, dport=50000) / Raw(payload))
        packet.time = stamp
        return packet

    def test_existing_capture_recovers_loss_omitted_by_older_report(self):
        wrpcap(str(self.root / 'egress-private.pcap'), [
            self.packet(97_087_000, 0, stamp=10),
            self.packet(87_241_000, 40, stamp=11),
            self.packet(87_266_000, 0, stamp=12),
            self.packet(1, 999, sport=50000, stamp=13),
        ])
        result = analyze(self.root)
        self.assertEqual(result['source'], 'existing_control_capture')
        self.assertEqual(result['samples_with_nonzero_loss'], 1)
        self.assertEqual(result['max_reported_loss_raw'], 40)
        self.assertTrue(result['target_decreased'])
        self.assertTrue(result['high_target_confirmed'])
        self.assertEqual(result['quality_samples'][-1]['seconds_from_first_sample'], 2)
        self.assertEqual(result['observation_scope'], 'setup_and_restoration_only')
        self.assertNotIn('192.0.2', json.dumps(result))
        self.assertNotIn('/private/device-data', json.dumps(result))
        self.assertIn('temporary relay', ' '.join(result['limits']))

    def test_missing_loss_is_unknown_not_zero(self):
        result = analyze(self.report)
        self.assertEqual(result['source'], 'report')
        self.assertEqual(result['samples_with_loss_field'], 0)
        self.assertIsNone(result['samples_with_nonzero_loss'])
        self.assertIsNone(result['max_reported_loss_raw'])
        self.assertIsNone(result['target_decreased'])

    def test_explicit_zero_loss_is_retained_without_playback_claim(self):
        report = json.loads(self.report.read_text())
        report['ps5_messages'][0]['loss_raw'] = 0
        self.report.write_text(json.dumps(report))
        result = analyze(self.report)
        self.assertEqual(result['max_reported_loss_raw'], 0)
        self.assertEqual(result['samples_with_nonzero_loss'], 0)
        self.assertNotIn('playback_verified', result)

    def test_partial_capture_does_not_hide_its_shorter_observation(self):
        report = json.loads(self.report.read_text())
        report['ps5_messages'] *= 3
        self.report.write_text(json.dumps(report))
        wrpcap(str(self.root / 'egress-private.pcap'), [self.packet(97_087_000, 0)])
        result = analyze(self.report)
        self.assertEqual(result['report_quality_sample_count'], 3)
        self.assertEqual(result['capture_quality_sample_count'], 1)
        self.assertTrue(result['capture_has_fewer_samples_than_report'])

    def test_unreadable_capture_is_explicit_and_does_not_erase_report(self):
        (self.root / 'egress-private.pcap').write_bytes(b'not a pcap')
        result = analyze(self.report)
        self.assertIsNotNone(result['capture_read_error'])
        self.assertEqual(result['source'], 'report')
        self.assertEqual(result['quality_samples'][0]['target_bitrate_raw'], 97_087_000)
        self.assertIsNone(result['max_reported_loss_raw'])

    def test_truncated_capture_cannot_erase_reported_loss(self):
        report = json.loads(self.report.read_text())
        report['ps5_messages'] = [
            {'type': 'CONNECTIONQUALITY', 'target_bitrate_raw': 97_087_000, 'loss_raw': 0},
            {'type': 'CONNECTIONQUALITY', 'target_bitrate_raw': 87_241_000, 'loss_raw': 40},
        ]
        self.report.write_text(json.dumps(report))
        capture = self.root / 'egress-private.pcap'
        first = self.packet(97_087_000, 0)
        wrpcap(str(capture), [first, self.packet(87_241_000, 40)])
        original = capture.read_bytes()
        for end in (len(original) - 1, 24 + 16 + len(bytes(first)) + 7):
            with self.subTest(end=end):
                capture.write_bytes(original[:end])
                result = analyze(self.report)
                self.assertIsNotNone(result['capture_read_error'])
                self.assertEqual(result['source'], 'report')
                self.assertEqual(result['max_reported_loss_raw'], 40)

    def test_shorter_valid_capture_cannot_erase_reported_loss(self):
        report = json.loads(self.report.read_text())
        report['ps5_messages'][0]['loss_raw'] = 40
        report['ps5_messages'] *= 3
        self.report.write_text(json.dumps(report))
        wrpcap(str(self.root / 'egress-private.pcap'), [self.packet(97_087_000, 0)])
        result = analyze(self.report)
        self.assertTrue(result['capture_has_fewer_samples_than_report'])
        self.assertEqual(result['source'], 'report')
        self.assertEqual(result['max_reported_loss_raw'], 40)

    def test_cli_is_read_only_and_does_not_export_identifiers(self):
        before = self.report.read_bytes()
        output = io.StringIO()
        with patch('scapy.all.conf.L2socket', side_effect=AssertionError('Network access')), contextlib.redirect_stdout(output):
            self.assertEqual(main([str(self.root)]), 0)
        self.assertEqual(self.report.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['report.json'])
        data = json.loads(output.getvalue())
        self.assertEqual(len(data), 1)
        self.assertNotIn('192.0.2', output.getvalue())


if __name__ == '__main__':
    unittest.main()
