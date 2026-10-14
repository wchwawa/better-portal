"""Offline checks for the direct-path feasibility experiment."""
import io
import json
import unittest

from tools.observe_portal_session import Recorder, packet_summary, parse_discovery


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.config = {'interface': 'en0', 'ps5_ip': '192.168.1.10', 'portal_ip': '192.168.1.20'}

    def test_discovery_keeps_status_and_unknown_fields_without_exposing_host_identity(self):
        reply = parse_discovery(b'HTTP/1.1 200 Ok\r\nhost-id:private-id\r\nhost-name:private-name\r\nnew-field:value\r\n')
        self.assertEqual(reply['status'], 'HTTP/1.1 200 Ok')
        self.assertEqual(reply['fields']['new-field'], 'value')
        self.assertNotIn('private', json.dumps(reply))
        self.assertNotIn('connected', reply)
        self.assertIsNone(parse_discovery(b'not a discovery reply'))

    def test_peer_stream_packets_are_separated_from_discovery_and_ping(self):
        peer = packet_summary('123 IP 192.168.1.10.9296 > 192.168.1.20.52000: UDP, length 1234', self.config)
        discovery = packet_summary('124 IP 192.168.1.10.9302 > 192.168.1.30.50000: UDP, length 200', self.config)
        ping = packet_summary('125 IP 192.168.1.20 > 192.168.1.30: ICMP echo reply, id 1, seq 0, length 64', self.config)
        self.assertTrue(peer['peer_udp_9296'])
        self.assertFalse(discovery['peer'])
        self.assertFalse(ping['peer'])
        self.assertEqual(ping['source_port'], 0)
        stream = io.StringIO()
        recorder = Recorder(stream)
        recorder.record('packet', **peer)
        recorder.record('packet', **discovery)
        self.assertEqual(recorder.counts['peer_udp_9296'], 1)
        self.assertEqual(recorder.counts['packets'], 2)
        self.assertEqual(json.loads(stream.getvalue().splitlines()[0])['event'], 'packet')

    def test_connection_closure_is_metadata_not_an_inferred_result(self):
        packet = packet_summary('123 IP 192.168.1.20.52000 > 192.168.1.10.9295: Flags [F.], seq 1, ack 2', self.config)
        self.assertEqual(packet['tcp_flags'], 'F.')
        self.assertTrue(packet['peer'])
        self.assertNotIn('connected', packet)
        self.assertIsNone(packet_summary('123 IP 10.0.0.1.123 > 10.0.0.2.123: UDP, length 12', self.config))

    def test_manual_labels_and_zero_packet_observations_do_not_claim_disconnection(self):
        stream = io.StringIO()
        recorder = Recorder(stream)
        recorder.mark('connected')
        recorder.record('ping', device='portal', replied=True)
        events = [json.loads(line) for line in stream.getvalue().splitlines()]
        self.assertEqual(events[0]['event'], 'manual_label')
        self.assertEqual(events[1]['phase'], 'connected')
        self.assertEqual(recorder.counts['peer_packets'], 0)


if __name__ == '__main__':
    unittest.main()
