#!/usr/bin/env python3
"""Experimental automatic Portal-to-PS5 relay. Video stays on the direct path."""
import argparse
import collections
import datetime
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import time
from scapy.all import ARP, Ether
import portal_active_probe as probe
import portal_auto_platform as net

ROOT = Path(__file__).resolve().parent
PROFILES = {'65': bytes.fromhex('04'), '100': bytes.fromhex('03501b0005'), '200': bytes.fromhex('00501b0005')}
LOG = logging.getLogger('portal-auto')
HEARTBEAT_TIMEOUT = 30  # Allows a bounded Windows forwarding-state query.


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def atomic_json(path, value):
    temp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    temp.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def config(path):
    c = json.loads(path.read_text(encoding='utf-8-sig'))
    if set(c) != {'network', 'profile', 'ps5_mac', 'portal_mac'} or c['profile'] not in PROFILES:
        raise ValueError('Invalid enrollment/profile. Run configure.')
    net.win.validate_config(c['network'])
    for k in ('ps5_mac', 'portal_mac'):
        c[k] = net.win.normal_mac(c[k])
    if c['ps5_mac'] == c['portal_mac']:
        raise ValueError('Peer MAC addresses must differ')
    return c


def fingerprint(c):
    digest = hashlib.sha256(json.dumps(c, sort_keys=True).encode())
    for name in ('portal_auto.py', 'portal_auto_platform.py', 'portal_active_probe.py', 'portal_windows_network.py', 'protocol.py'):
        digest.update((ROOT / name).read_bytes())
    return digest.hexdigest()


def baseline_valid(c, runtime):
    try:
        receipt = json.loads((runtime / 'auto-baseline.json').read_text())
        return receipt['fingerprint'] == fingerprint(c) and receipt['forwarded_out'] > 0 and receipt['restored'] is True
    except (OSError, ValueError, KeyError, TypeError):
        return False


def portal_arp(state, repair=False):
    return Ether(src=state['own_mac'], dst=state['portal_mac']) / ARP(
        op=2, psrc=state['config']['ps5_ip'], pdst=state['config']['portal_ip'],
        hwsrc=state['ps5_mac'] if repair else state['own_mac'], hwdst=state['portal_mac'])


def outbound(frame, state, active=True):
    if len(frame) < 34 or frame[6:12] != bytes.fromhex(state['portal_mac'].replace(':', '')):
        return None
    result = probe.transform(frame, state, active)
    return result if result and result[2] == 'out' else None


def restore_peer(state):
    sock = None
    try:
        net.configure(state['config'])
        sock = net.open_socket()
        for _ in range(5):
            net.send(sock, portal_arp(state, True))
            time.sleep(.1)
        return []
    except Exception as exc:
        return [str(exc)]
    finally:
        if sock is not None:
            sock.close()


def pipe_reader(pipe, messages, ready_line=False):
    try:
        if ready_line:
            messages.put(pipe.readline().strip())
        else:
            while pipe.read(1):
                messages.put(True)
            messages.put(False)
    except OSError:
        messages.put(False)


def guardian(runtime, parent):
    state = json.loads((runtime / 'restore-state.json').read_text())
    lock = net.Lock(runtime, existing=True)
    owner = net.Parent(parent)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal.SIG_IGN)
    messages = queue.Queue()
    threading.Thread(target=pipe_reader, args=(sys.stdin.buffer, messages), daemon=True).start()
    # Verify the recovery adapter can be opened before allowing any redirection.
    net.configure(state['config'])
    test_socket = net.open_socket()
    test_socket.close()
    print('GUARD_READY', flush=True)
    reason = 'relay_closed'
    try:
        while True:
            try:
                if not messages.get(timeout=HEARTBEAT_TIMEOUT):
                    break
            except queue.Empty:
                reason = 'heartbeat_timeout'
                owner.stop()
                break
        errors = restore_peer(state)
        atomic_json(runtime / 'recovery.json', {'time': utc(), 'parent': parent, 'reason': reason, 'errors': errors})
        if not errors:
            (runtime / 'recovery-required').unlink(missing_ok=True)
        lock.close(parent, repaired=not errors)
        return 1 if errors else 0
    finally:
        owner.close()


def health_worker(results):
    try:
        net.health()
        results.put(None)
    except Exception as exc:
        results.put(str(exc))


def run(c, runtime, active=True, seconds=None):
    if (runtime / 'recovery-required').exists():
        raise RuntimeError('Previous relay recovery is unconfirmed. Run repair before restarting.')
    if active and not baseline_valid(c, runtime):
        raise RuntimeError('Run a successful baseline with this config/version first.')
    state = net.state_for(c)
    probe.network = net
    probe.PATCH_DELTA = PROFILES[c['profile']]
    probe.OFFSET = 334
    lock = net.Lock(runtime)
    guard = rx = tx = None
    counts = collections.Counter()
    running = True
    errors = []
    seen = collections.OrderedDict()
    started = time.monotonic()
    last_mutation = None
    def stop(_sig, _frame):
        nonlocal running
        running = False
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, stop)
    try:
        atomic_json(runtime / 'restore-state.json', state)
        (runtime / 'recovery-required').write_text(str(os.getpid()))
        filt = f'ether dst {state["own_mac"]} and ether src {state["portal_mac"]} and ip and src host {net.PORTAL} and dst host {net.PS5}'
        rx, tx = net.open_socket(filt), net.open_socket()
        guard = subprocess.Popen([sys.executable, '-u', str(ROOT / 'portal_auto.py'), 'guardian',
                                  '--runtime', str(runtime), '--parent', str(os.getpid())],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, **net.spawn_options())
        ready = queue.Queue()
        threading.Thread(target=pipe_reader, args=(guard.stdout, ready, True), daemon=True).start()
        if ready.get(timeout=10) != b'GUARD_READY':
            raise RuntimeError('Recovery guardian failed before redirection')
        print('AUTO READY' if active else 'BASELINE READY: connect Portal now and check picture/controls.', flush=True)
        next_arp = next_beat = next_status = 0
        next_health = time.monotonic() + 30
        health_results = queue.Queue()
        health_pending = False
        while running and (seconds is None or time.monotonic() - started < seconds):
            now = time.monotonic()
            if (runtime / 'disabled').exists():
                break
            if guard.poll() is not None:
                raise RuntimeError('Recovery guardian exited')
            if now >= next_beat:
                guard.stdin.write(b'.'); guard.stdin.flush()
                next_beat = now + 1
            if health_pending:
                try:
                    health_error = health_results.get_nowait()
                    health_pending = False
                    next_health = now + 30
                    if health_error:
                        raise RuntimeError(health_error)
                except queue.Empty:
                    pass
            if now >= next_health and not health_pending:
                # PowerShell may take seconds. Keep relaying while its bounded
                # read-only health query runs, then stop on any reported error.
                threading.Thread(target=health_worker, args=(health_results,), daemon=True).start()
                health_pending = True
            if now >= next_arp:
                net.send(tx, portal_arp(state))
                next_arp = now + 1
            if now >= next_status:
                atomic_json(runtime / 'status.json', {'time': utc(), 'state': 'running', 'pid': os.getpid(),
                    'guardian_pid': guard.pid, 'mode': 'active' if active else 'baseline', 'profile': c['profile'],
                    'counts': dict(counts), 'last_mutation': last_mutation,
                    'limit': 'Local packet mutation is not PS5 acceptance or measured bitrate. Video bypasses this host.'})
                next_status = now + 2
            frame = net.receive(rx)
            if not frame:
                continue
            result = outbound(frame, state, active)
            if not result:
                continue
            forwarded, payload, _, changed = result
            net.send(tx, forwarded)
            counts['forwarded_out'] += 1
            counts['forwarded_bytes'] += len(forwarded)
            if changed:
                counts['modified_packets_including_retransmits'] += 1
                ident = (payload[1:5], payload[17:21])
                if ident not in seen:
                    seen[ident] = now
                    if len(seen) > 256:
                        seen.popitem(last=False)
                    counts['unique_modified_startups'] += 1
                    last_mutation = utc()
                    LOG.info('Startup modified, profile=%s; device validation still required', c['profile'])
    finally:
        if guard is not None:
            try:
                guard.stdin.close()
            except OSError:
                pass
            try:
                rc = guard.wait(timeout=HEARTBEAT_TIMEOUT + 5)
                if rc:
                    errors = restore_peer(state)
                    if not errors:
                        (runtime / 'recovery-required').unlink(missing_ok=True)
            except subprocess.TimeoutExpired:
                errors = ['Guardian still running; recovery lock retained']
        else:
            # No guardian means no ARP redirection has been sent.
            (runtime / 'recovery-required').unlink(missing_ok=True)
        for sock in (rx, tx):
            if sock is not None:
                sock.close()
        lock.close(os.getpid(), repaired=not errors)
        atomic_json(runtime / 'status.json', {'time': utc(), 'state': 'stopped' if not errors else 'recovery_failed',
                   'counts': dict(counts), 'last_mutation': last_mutation, 'errors': errors})
        if errors:
            raise RuntimeError('; '.join(errors))
    if not active and counts['forwarded_out']:
        atomic_json(runtime / 'auto-baseline.json', {'time': utc(), 'fingerprint': fingerprint(c),
                    'forwarded_out': counts['forwarded_out'], 'restored': True,
                    'limit': 'Transport observed, not proof of picture quality or input responsiveness.'})
    return dict(counts)


def choose_windows_interface():
    adapters = [x for x in net.conf.ifaces.values() if x.mac and x.ip and x.ip != '0.0.0.0']
    if not adapters:
        raise RuntimeError('No addressed LAN adapters found. Check Npcap and your LAN connection.')
    print('Select the adapter connected to your PS5/Portal LAN. Use its menu number.')
    for index, adapter in enumerate(adapters, 1):
        print(f'{index}: {adapter.name} ({adapter.description}) - {adapter.ip}')
    try:
        number = int(input('LAN adapter number: ').strip())
    except ValueError:
        raise ValueError('Enter the adapter menu number, not a PC IP address or GUID.') from None
    if not 1 <= number <= len(adapters):
        raise ValueError('Adapter number is outside the displayed list.')
    return adapters[number - 1].network_name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['configure', 'baseline', 'run', 'stop', 'status', 'repair', 'guardian', 'verify-baseline'])
    parser.add_argument('--config', type=Path, default=ROOT / 'auto-config.json')
    parser.add_argument('--runtime', type=Path, default=ROOT / 'auto-runtime')
    parser.add_argument('--profile', choices=PROFILES, default='65')
    parser.add_argument('--seconds', type=int)
    parser.add_argument('--parent', type=int)
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    if args.command == 'status':
        for name in ('status.json', 'recovery.json', 'error.json'):
            path = runtime / name
            if path.exists():
                print(name + ':\n' + path.read_text())
        print('Disabled:', (runtime / 'disabled').exists(), 'Recovery required:', (runtime / 'recovery-required').exists())
        print('Check the OS service/task state too; a timestamped report can be stale after a crash.')
        return 0
    if sys.platform == 'darwin' and args.command in ('configure', 'baseline', 'run', 'verify-baseline'):
        parser.exit(2, 'The experimental automatic relay has no signed macOS helper; new sessions are disabled.\n')
    net.require_admin()
    runtime.mkdir(parents=True, exist_ok=True)
    LOG.setLevel(logging.INFO)
    handler = RotatingFileHandler(runtime / 'events.log', maxBytes=1048576, backupCount=2)
    LOG.addHandler(handler)
    if args.command == 'stop':
        (runtime / 'disabled').touch()
        print('Stop requested. Allow up to 35 seconds for recovery; check status.')
        return 0
    if args.command == 'guardian':
        return guardian(runtime, args.parent)
    if args.command == 'configure':
        if sys.platform == 'win32':
            interface = choose_windows_interface()
        else:
            print('Interfaces:', ', '.join(str(x) for x in net.conf.ifaces.values()))
            interface = input('LAN interface name (for example eth0 or en0, not a PC IP): ').strip()
        c = {'network': {'interface': interface,
                        'ps5_ip': input('PS5 IPv4: ').strip(), 'portal_ip': input('Portal IPv4: ').strip()},
             'profile': args.profile}
        state = net.state_for(c, enroll=True)
        c.update(network=state['config'], ps5_mac=state['ps5_mac'], portal_mac=state['portal_mac'])
        atomic_json(args.config, c)
        print('Enrolled two devices locally. Do not upload auto-config.json.')
        return 0
    if args.command == 'repair':
        # Only after the OS reports the relay stopped. Existing guardians hold locks.
        if input('Confirm relay service and guardian are stopped (type STOPPED): ') != 'STOPPED':
            return 1
        state = json.loads((runtime / 'restore-state.json').read_text())
        errors = restore_peer(state)
        if errors:
            raise RuntimeError('; '.join(errors))
        (runtime / 'recovery-required').unlink(missing_ok=True)
        if sys.platform != 'win32':
            Path('/var/run/portal-lab-capture.lock').unlink(missing_ok=True)
        print('Repair packets sent. Reconnect Portal; verify its connection.')
        return 0
    if args.command == 'verify-baseline':
        if not baseline_valid(config(args.config), runtime):
            raise RuntimeError('Run configure and baseline with this version first')
        print('Baseline receipt matches this configuration and code.')
        return 0
    if (runtime / 'disabled').exists():
        print('Disabled. Use the documented Start command to remove the stop marker.')
        return 0
    c = config(args.config)
    return 0 if run(c, runtime, active=args.command == 'run', seconds=(60 if args.command == 'baseline' else args.seconds)) is not None else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        LOG.exception('Automatic relay failed')
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
