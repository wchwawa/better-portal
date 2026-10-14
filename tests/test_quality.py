"""Synthetic wire messages for connection-quality diagnostics, not playback tests."""
import json
import math
import struct
import unittest
from unittest.mock import patch

import portal_active_probe as probe
from portal_tui import summarize
from protocol import fields


def varint(value):
    encoded = bytearray()
    while value > 127:
        encoded.append((value & 127) | 128)
        value >>= 7
    return bytes(encoded) + bytes([value])


def field(number, value, wire=0):
    prefix = varint((number << 3) | wire)
    if wire == 0:
        return prefix + varint(value)
    if wire == 2:
        return prefix + varint(len(value)) + value
    return prefix + value


def control(kind, body=b''):
    header = bytearray(26)
    header[14] = 1
    return bytes(header) + field(1, kind) + body


def quality(payload):
    events = []
    probe.observe(control(16, field(17, payload, 2)), events)
    return events


class QualityTests(unittest.TestCase):
    def test_typed_wire_reader_keeps_default_output_compatible(self):
        payload = (field(1, 7) + field(2, b'12345678', 1)
                   + field(3, b'12345678', 2) + field(4, b'1234', 5))
        self.assertEqual(fields(payload), {1: 7, 2: b'12345678',
                                           3: b'12345678', 4: b'1234'})
        self.assertEqual(fields(payload, with_wire=True), {
            1: (0, 7), 2: (1, b'12345678'), 3: (2, b'12345678'), 4: (5, b'1234')})

    def test_sparse_target_preserves_existing_event(self):
        self.assertEqual(quality(field(1, 97_000_000)), [
            {'type': 'CONNECTIONQUALITY', 'target_bitrate_raw': 97_000_000}])

    def test_complete_telemetry_preserves_raw_values(self):
        payload = (field(1, 87_000_000) + field(2, 32_000)
                   + field(3, struct.pack('<f', .125), 5)
                   + field(5, struct.pack('<d', 2.5), 1) + field(6, 40)
                   + field(7, 900) + field(8, b'unknown', 2))
        self.assertEqual(quality(payload), [{
            'type': 'CONNECTIONQUALITY', 'target_bitrate_raw': 87_000_000,
            'upstream_bitrate_raw': 32_000, 'upstream_loss_raw': .125,
            'rtt_raw': 2.5, 'loss_raw': 40}])

    def test_invalid_optional_values_do_not_discard_valid_target(self):
        invalid = [
            field(2, 1 << 32), field(2, b'1234', 5),
            field(3, 5), field(3, struct.pack('<f', .5), 2),
            field(3, struct.pack('<d', .5), 1),
            field(5, 5), field(5, struct.pack('<d', .5), 2),
            field(5, struct.pack('<f', .5), 5),
            field(6, 1 << 64), field(6, b'12345678', 1),
        ]
        for value in (-1.0, math.nan, math.inf, -math.inf):
            invalid.extend((field(3, struct.pack('<f', value), 5),
                            field(5, struct.pack('<d', value), 1)))
        for optional in invalid:
            for payload in (field(1, 65_000_000) + optional,
                            optional + field(1, 65_000_000)):
                with self.subTest(optional=optional, payload=payload):
                    events = quality(payload)
                    self.assertEqual(events, [{'type': 'CONNECTIONQUALITY',
                                               'target_bitrate_raw': 65_000_000}])
                    json.dumps(events, allow_nan=False)

    def test_zero_and_unsigned_boundaries_are_retained(self):
        self.assertEqual(quality(field(1, 65_000_000) + field(2, (1 << 32) - 1)
                                 + field(3, struct.pack('<f', 0), 5)
                                 + field(5, struct.pack('<d', 0), 1)
                                 + field(6, (1 << 64) - 1)), [{
            'type': 'CONNECTIONQUALITY', 'target_bitrate_raw': 65_000_000,
            'upstream_bitrate_raw': (1 << 32) - 1, 'upstream_loss_raw': 0.0,
            'rtt_raw': 0.0, 'loss_raw': (1 << 64) - 1}])

    def test_structurally_invalid_messages_keep_existing_rejection(self):
        for invalid in (field(1, 65_000_000) + b'\x29\0',
                        field(1, 65_000_000) + field(6, 0) + field(6, 4)):
            with self.subTest(invalid=invalid):
                self.assertEqual(quality(invalid), [])

    def test_invalid_target_cannot_crash_confirmation(self):
        for invalid in (b'', field(1, 1 << 32), field(1, b'65000', 2)):
            with self.subTest(invalid=invalid):
                self.assertEqual(quality(invalid + field(6, 40)), [])

    def test_high_targets_with_loss_confirm_only_the_target(self):
        events = []
        acceptance = field(3, field(1, 20) + field(3, 1) + field(4, 1), 2)
        probe.observe(control(1, acceptance), events)
        probe.observe(control(13), events)
        for target, loss in ((97_000_000, 0), (87_000_000, 40), (87_100_000, 0)):
            events.extend(quality(field(1, target) + field(6, loss)))
        with patch.object(probe, 'CONFIRM_TARGET', 80_000_000):
            confirmation = probe.TargetConfirmation()
            confirmation.modified()
            for event in events:
                confirmation.observe(event)
            self.assertTrue(confirmation.ready)
        report = {'completed': True, 'restoration_errors': [],
                  'unique_mutated_sequences': 1, 'high_target_confirmed': True,
                  'playback_verified': False, 'ps5_messages': events,
                  'egress_witness': {'all_expected_observed': True}}
        self.assertEqual([event['loss_raw'] for event in events
                          if event['type'] == 'CONNECTIONQUALITY'], [0, 40, 0])
        self.assertIn('Playback has not been verified.', summarize(report).message)
        json.dumps(report, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
