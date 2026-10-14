#!/usr/bin/env python3
"""Read setup reports and existing captures without opening a network socket."""
import argparse
import json
import struct
import sys
from pathlib import Path

from scapy.all import PcapReader, UDP

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from portal_active_probe import observe


def validate_capture(source):
    """Scapy tolerates short records; a diagnostic must not silently lose evidence."""
    size = source.seek(0, 2)
    source.seek(0)
    header = source.read(24)
    endians = {b'\xd4\xc3\xb2\xa1': '<', b'\xa1\xb2\xc3\xd4': '>',
               b'\x4d\x3c\xb2\xa1': '<', b'\xa1\xb2\x3c\x4d': '>'}
    if len(header) != 24 or header[:4] not in endians:
        raise ValueError('Expected a complete classic pcap header')
    endian = endians[header[:4]]
    snaplen = struct.unpack(endian + 'I', header[16:20])[0]
    while source.tell() < size:
        record = source.read(16)
        if len(record) != 16:
            raise ValueError('Truncated pcap record header')
        _, _, captured, original = struct.unpack(endian + 'IIII', record)
        if captured > snaplen or captured > original or captured > size - source.tell():
            raise ValueError('Incomplete or invalid pcap record')
        source.seek(captured, 1)
    source.seek(0)


def capture_samples(path):
    """Only inspect PS5 control replies on the recorded service port."""
    with Path(path).open('rb') as source:
        validate_capture(source)
        return read_samples(source)


def read_samples(source):
    samples = []
    first = None
    with PcapReader(source) as packets:
        for packet in packets:
            if UDP not in packet or packet[UDP].sport != 9296:
                continue
            events = []
            observe(bytes(packet[UDP].payload), events)
            for event in events:
                if event['type'] != 'CONNECTIONQUALITY':
                    continue
                stamp = float(packet.time)
                if first is None:
                    first = stamp
                samples.append(dict(event, seconds_from_first_sample=round(stamp - first, 6)))
    return samples


def analyze(path):
    path = Path(path)
    if path.is_dir():
        path = path / 'report.json'
    report = json.loads(path.read_text(encoding='utf-8'))
    samples = [event for event in report.get('ps5_messages', [])
               if event.get('type') == 'CONNECTIONQUALITY']
    report_sample_count = len(samples)
    capture_sample_count = None
    source = 'report'
    capture = path.with_name('egress-private.pcap')
    capture_error = None
    if capture.is_file():
        try:
            recorded = capture_samples(capture)
            capture_sample_count = len(recorded)
            if recorded and not any('loss_raw' in event for event in samples):
                samples, source = recorded, 'existing_control_capture'
        except Exception as exc:
            # Do not present an unreadable capture as evidence of zero loss.
            capture_error = type(exc).__name__
    # Whitelist fields: never export peer addresses, raw payloads or report paths.
    allowed = ('target_bitrate_raw', 'loss_raw', 'rtt_raw', 'upstream_bitrate_raw',
               'upstream_loss_raw', 'seconds_from_first_sample')
    samples = [{key: event[key] for key in allowed if key in event} for event in samples]
    loss = [event['loss_raw'] for event in samples
            if isinstance(event.get('loss_raw'), int) and event['loss_raw'] >= 0]
    targets = [event['target_bitrate_raw'] for event in samples
               if isinstance(event.get('target_bitrate_raw'), int)]
    return {
        'profile': report.get('profile'),
        'source': source,
        'capture_read_error': capture_error,
        'report_quality_sample_count': report_sample_count,
        'capture_quality_sample_count': capture_sample_count,
        'capture_has_fewer_samples_than_report': (capture_sample_count < report_sample_count
                                                 if capture_sample_count is not None else None),
        'observation_scope': 'setup_and_restoration_only',
        'high_target_confirmed': report.get('high_target_confirmed'),
        'restoration_error_count': len(report.get('restoration_errors', [])),
        'quality_samples': samples,
        'samples_with_loss_field': len(loss),
        'samples_with_nonzero_loss': sum(value > 0 for value in loss) if loss else None,
        'max_reported_loss_raw': max(loss) if loss else None,
        'target_decreased': (any(b < a for a, b in zip(targets, targets[1:]))
                             if len(targets) > 1 else None),
        'limits': [
            'A confirmed target does not verify video playback.',
            'Loss and RTT are protocol-reported raw values, not independent measurements.',
            'The loss counting interval and RTT unit are not established here.',
            'Missing loss telemetry is unknown, not zero loss.',
            'These records do not cover gameplay after direct-path restoration.',
            'The temporary relay can affect the setup measurements.',
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reports', type=Path, nargs='+', help='Report files or experiment folders')
    args = parser.parse_args(argv)
    results = []
    for path in args.reports:
        try:
            results.append(analyze(path))
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            parser.exit(1, f'Could not analyze a report: {type(exc).__name__}\n')
    print(json.dumps(results, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
