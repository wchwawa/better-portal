"""Exercise macOS repair frames against a real Linux ARP cache, in Docker only.

Run with --network none and NET_ADMIN/NET_RAW; the two temporary veth interfaces
stay inside the container. This tests peer ARP behavior, not Portal firmware or
macOS Wi-Fi. Only platform setup/sysctl calls are substituted; restore(), frames()
and Scapy Ethernet transmission are the production implementations.
"""
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scapy.all import ARP, Ether, conf
import portal_capture as network


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def run_case(peer, wait_before_repair):
    state = {
        'config': {'interface': 'relay0', 'ps5_ip': '192.0.2.10',
                   'portal_ip': '192.0.2.20'},
        'own_mac': '02:00:00:00:00:01', 'ps5_mac': '02:00:00:00:00:02',
        'portal_mac': '02:00:00:00:00:03',
        'sysctl': dict(zip(network.KEYS, ['0', '1'])),
    }
    other = 'portal' if peer == 'ps5' else 'ps5'
    local_ip, remote_ip = (state['config'][key + '_ip'] for key in (peer, other))
    local_mac, remote_mac = (state[key + '_mac'] for key in (peer, other))
    command('ip', 'link', 'add', 'relay0', 'type', 'veth', 'peer', 'name', 'peer0')
    try:
        for iface, address in (('relay0', state['own_mac']), ('peer0', local_mac)):
            command('ip', 'link', 'set', iface, 'address', address, 'up')
        command('ip', 'addr', 'add', local_ip + '/24', 'dev', 'peer0')
        command('ip', 'neigh', 'replace', remote_ip, 'lladdr', remote_mac,
                'nud', 'reachable', 'dev', 'peer0')
        locktime = Path('/proc/sys/net/ipv4/neigh/peer0/locktime').read_text().strip()
        # Let the initial legitimate entry become replaceable at the default locktime.
        time.sleep(1.2)
        conf.ifaces.reload()

        def neighbor():
            entries = json.loads(command('ip', '-j', 'neigh', 'show', remote_ip,
                                         'dev', 'peer0'))
            return entries[0]['lladdr']

        with patch.object(network, 'IFACE', 'relay0'), \
                patch.object(network, 'PS5', state['config']['ps5_ip']), \
                patch.object(network, 'PORTAL', state['config']['portal_ip']), \
                patch.object(network, 'configure'), patch.object(network, 'syswrite'):
            sender = conf.L2socket(iface='relay0')
            try:
                redirect = next(packet for packet in network.frames(state)
                                if packet[ARP].pdst == local_ip)
                started = time.monotonic()
                sender.send(redirect)
                time.sleep(wait_before_repair)
                assert neighbor() == state['own_mac'], 'Redirection was not applied'
                errors = network.restore(state)
                after = neighbor()

                # Observe where a real kernel sends the next very small UDP packet.
                with socket.socket(socket.AF_PACKET, socket.SOCK_RAW,
                                   socket.htons(0x0800)) as capture:
                    capture.bind(('relay0', 0))
                    capture.settimeout(2)
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
                        udp.bind((local_ip, 0))
                        udp.sendto(b'low-rate-continuity-check', (remote_ip, 9296))
                    emitted = Ether(capture.recv(2048)).dst

                result = {'peer': peer, 'delay_before_restore_seconds': wait_before_repair,
                          'locktime_user_hz': locktime, 'restoration_errors': errors,
                          'elapsed_seconds': round(time.monotonic() - started, 3),
                          'peer_mapping_restored': after == remote_mac,
                          'next_udp_uses_direct_mac': emitted == remote_mac}
                # Positive control: the same repair frames work outside the lock window.
                time.sleep(1.2)
                network.restore(state)
                result['late_repair_restores_mapping'] = neighbor() == remote_mac
                assert result['late_repair_restores_mapping'], result
                return result
            finally:
                sender.close()
    finally:
        command('ip', 'link', 'del', 'relay0')


if __name__ == '__main__':
    if not Path('/.dockerenv').exists() or sys.platform != 'linux':
        raise SystemExit('Run this check only in its isolated Docker container.')
    results = [run_case(peer, delay) for peer in ('portal', 'ps5')
               for delay in (0.05, 1.2)]
    print(json.dumps({'kernel': command('uname', '-r'), 'cases': results}, indent=2))
    if '--expect-fixed' in sys.argv:
        assert all(item['peer_mapping_restored'] and item['next_udp_uses_direct_mac']
                   and not item['restoration_errors'] for item in results), results
