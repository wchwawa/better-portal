"""Observe a user-owned PS5/Portal pair without redirecting its traffic.

This diagnostic records evidence and manual phase labels, not a connection
verdict. It never sends wake, pairing, registration or Remote Play requests.
"""
import argparse
import collections
import datetime
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import select
import signal
import socket
import subprocess
import sys
import threading
import time


SEARCH = b'SRCH * HTTP/1.1\ndevice-discovery-protocol-version:00030010\n'
PHASES = {'1': 'connected', '2': 'disconnected', '3': 'reconnected'}


def parse_discovery(data):
    lines = data.decode('utf-8', errors='replace').splitlines()
    if not lines or not re.fullmatch(r'HTTP/1\.1 \d{3}(?: .*)?', lines[0]):
        return None
    fields = {}
    for line in lines[1:]:
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        if key.lower() in ('host-id', 'host-name'):
            value = 'sha256:' + hashlib.sha256(value.encode()).hexdigest()[:16]
        fields[key.lower()] = value.strip()
    return {'status': lines[0], 'fields': fields}


def packet_summary(line, config):
    """Only store header metadata. No stream payload or unrelated addresses."""
    if 'ARP,' in line:
        return {'kind': 'arp', 'request': 'Request ' in line, 'reply': 'Reply ' in line}
    match = re.search(r'\bIP (\d+\.\d+\.\d+\.\d+)(?:\.(\d+))? > '
                      r'(\d+\.\d+\.\d+\.\d+)(?:\.(\d+))?: (.*)', line)
    if not match:
        return None
    source, source_port, destination, destination_port, detail = match.groups()
    roles = {config['ps5_ip']: 'ps5', config['portal_ip']: 'portal'}
    if source not in roles and destination not in roles:
        return None
    source_port, destination_port = int(source_port or 0), int(destination_port or 0)
    peer = {source, destination} == set(roles)
    protocol = 'udp' if detail.startswith('UDP,') else 'tcp' if 'Flags [' in detail else 'other'
    flags = re.search(r'Flags \[([^]]*)\]', detail)
    return {'kind': 'ip', 'source': roles.get(source, 'other'),
            'destination': roles.get(destination, 'other'), 'protocol': protocol,
            'source_port': source_port, 'destination_port': destination_port,
            'tcp_flags': flags[1] if flags else None, 'peer': peer,
            'peer_udp_9296': peer and protocol == 'udp' and 9296 in (source_port, destination_port)}


class Recorder:
    def __init__(self, stream):
        self.stream = stream
        self.lock = threading.Lock()
        self.phase = 'unlabeled'
        self.started = time.monotonic()
        self.counts = collections.Counter()

    def record(self, event_type, **values):
        with self.lock:
            event = {'time': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     'elapsed': round(time.monotonic() - self.started, 3),
                     'phase': self.phase, 'event': event_type, **values}
            self.stream.write(json.dumps(event, ensure_ascii=False) + '\n')
            self.stream.flush()
            if event_type == 'packet':
                self.counts['packets'] += 1
                self.counts['peer_packets'] += int(values.get('peer', False))
                self.counts['peer_udp_9296'] += int(values.get('peer_udp_9296', False))

    def mark(self, phase):
        with self.lock:
            self.phase = phase
        self.record('manual_label', label=phase)


def discovery_loop(config, recorder, stop):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(1)
        while not stop.is_set():
            try:
                sock.sendto(SEARCH, (config['ps5_ip'], 9302))
                data, address = sock.recvfrom(4096)
                response = parse_discovery(data)
                if address == (config['ps5_ip'], 9302) and response:
                    recorder.record('discovery', **response)
                else:
                    recorder.record('discovery_unrecognized')
            except TimeoutError:
                recorder.record('discovery_timeout')
            except OSError as exc:
                recorder.record('discovery_error', error=str(exc))
            stop.wait(2)


def ping_loop(device, ip, recorder, stop):
    while not stop.is_set():
        try:
            result = subprocess.run(['/sbin/ping', '-n', '-c', '1', '-W', '1000', ip],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
            recorder.record('ping', device=device, replied=result.returncode == 0)
        except subprocess.TimeoutExpired:
            recorder.record('ping', device=device, replied=False)
        stop.wait(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=600)
    args = parser.parse_args()
    if sys.platform != 'darwin' or os.geteuid() != 0 or 'SUDO_UID' not in os.environ:
        parser.error('Run this diagnostic using sudo in your local Mac Terminal.')
    if not sys.stdin.isatty():
        parser.error('An interactive Terminal is needed for manual phase labels.')
    if not 30 <= args.seconds <= 1800:
        parser.error('--seconds must be between 30 and 1800')
    config = json.loads(args.config.read_text())
    if not re.fullmatch(r'en\d+', config['interface']):
        parser.error('Expected a Mac LAN interface such as en0.')
    addresses = [ipaddress.IPv4Address(config[key]) for key in ('ps5_ip', 'portal_ip')]
    if addresses[0] == addresses[1] or any(not ip.is_private or ip.is_multicast or ip.is_loopback for ip in addresses):
        parser.error('Use two distinct private LAN IPv4 addresses.')
    os.umask(0o077)
    args.output.mkdir(parents=True, exist_ok=False)
    uid, gid = int(os.environ['SUDO_UID']), int(os.environ['SUDO_GID'])
    os.chown(args.output, uid, gid)
    events = (args.output / 'events.jsonl').open('x', encoding='utf-8')
    errors = (args.output / 'capture.log').open('x', encoding='utf-8')
    for path in (args.output / 'events.jsonl', args.output / 'capture.log'):
        os.chown(path, uid, gid)
    recorder = Recorder(events)
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda *_: stop.set())
    packet_filter = f'(arp or ip) and (host {addresses[0]} or host {addresses[1]})'
    capture = subprocess.Popen(['/usr/sbin/tcpdump', '-n', '-tt', '-l', '-p', '-s', '96',
                                '-i', config['interface'], packet_filter],
                               stdout=subprocess.PIPE, stderr=errors, text=True)
    threads = []

    def packets():
        for line in capture.stdout:
            packet = packet_summary(line, config)
            if packet:
                recorder.record('packet', **packet)

    def worker(target, arguments):
        try:
            target(*arguments)
        except Exception as exc:
            recorder.record('observer_error', worker=target.__name__, error=str(exc))
            stop.set()

    try:
        # Do not tell the operator to disconnect until tcpdump has opened BPF.
        deadline = time.monotonic() + 5
        while 'listening on' not in (args.output / 'capture.log').read_text():
            if capture.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('Capture did not start. See capture.log.')
            time.sleep(.05)
        for target, arguments in ((packets, ()), (discovery_loop, (config, recorder, stop)),
                                  (ping_loop, ('ps5', config['ps5_ip'], recorder, stop)),
                                  (ping_loop, ('portal', config['portal_ip'], recorder, stop))):
            thread = threading.Thread(target=worker, args=(target, arguments), daemon=True)
            thread.start()
            threads.append(thread)
        recorder.record('ready', interface=config['interface'], probes='DDP search and ICMP only')
        print('READY. Packet observation started; traffic is still direct.', flush=True)
        print('Keep PS5 awake and Portal on Wi-Fi throughout the test.', flush=True)
        print('When playing: 1 + Return. After disconnecting Remote Play: 2 + Return.', flush=True)
        print('After reconnecting and seeing the game: 3 + Return. Stay in each state for 20 seconds.', flush=True)
        print('Repeat 2 and 3 once more if convenient. Q + Return finishes. Limit: 10 minutes.', flush=True)
        print('Live evidence: ' + str(args.output / 'events.jsonl'), flush=True)
        deadline = time.monotonic() + args.seconds
        next_status = 0
        while not stop.is_set() and time.monotonic() < deadline:
            if capture.poll() is not None:
                raise RuntimeError('Packet capture stopped unexpectedly. See capture.log.')
            if select.select([sys.stdin], [], [], .2)[0]:
                command = sys.stdin.readline().strip().lower()
                if command == 'q':
                    break
                if command in PHASES:
                    recorder.mark(PHASES[command])
                    print('Marked: ' + PHASES[command], flush=True)
            if time.monotonic() >= next_status:
                with recorder.lock:
                    counts = dict(recorder.counts)
                    phase = recorder.phase
                print(f'[{phase}] visible pair packets={counts.get("peer_packets", 0)}, '
                      f'pair UDP/9296={counts.get("peer_udp_9296", 0)} (totals)', flush=True)
                next_status = time.monotonic() + 10
    finally:
        stop.set()
        capture.terminate()
        try:
            capture.wait(timeout=3)
        except subprocess.TimeoutExpired:
            capture.kill()
            capture.wait()
        for thread in threads:
            thread.join(timeout=3)
        recorder.record('stopped')
        capture.stdout.close()
        events.close()
        errors.close()
        print('Stopped. Local evidence: ' + str(args.output), flush=True)


if __name__ == '__main__':
    main()
