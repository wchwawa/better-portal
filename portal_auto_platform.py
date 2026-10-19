"""Native LAN I/O for the experimental one-way automatic relay."""
import ctypes
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from scapy.all import ARP, Ether, conf, get_if_hwaddr, srp
import portal_windows_network as win

PS5 = '192.0.2.10'
PORTAL = '192.0.2.20'
IFACE = None


def require_admin():
    if sys.platform == 'win32':
        win.require_windows()
    elif sys.platform in ('linux', 'darwin'):
        if os.geteuid() != 0:
            raise RuntimeError('Run with sudo.')
        if sys.platform == 'linux' and 'microsoft' in Path('/proc/sys/kernel/osrelease').read_text().lower():
            raise RuntimeError('Native Linux is required; WSL is not supported.')
    else:
        raise RuntimeError('Supported hosts: native Windows, Linux and macOS.')


def configure(c):
    global PS5, PORTAL, IFACE
    win.validate_config(c)
    PS5, PORTAL = c['ps5_ip'], c['portal_ip']
    if sys.platform == 'win32':
        win.configure(c)
        IFACE = win.IFACE
    else:
        if not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,32}', c['interface']):
            raise ValueError('Invalid interface name')
        IFACE = c['interface']


def health():
    """Read only: never change routing, forwarding or firewall settings."""
    if sys.platform == 'win32':
        conf.route.resync()
        for ip in (PS5, PORTAL):
            iface, source, gateway = conf.route.route(ip)
            if win.resolve_iface(iface).network_name != IFACE.network_name or gateway != '0.0.0.0' or source in (PS5, PORTAL, '0.0.0.0'):
                raise RuntimeError('Both devices must be directly connected through this adapter.')
        win.forwarding_disabled(IFACE.index)
    elif sys.platform == 'linux':
        for path in ('/proc/sys/net/ipv4/ip_forward', f'/proc/sys/net/ipv4/conf/{IFACE}/forwarding'):
            if Path(path).read_text().strip() != '0':
                raise RuntimeError('IPv4 forwarding is enabled. No changes made.')
        for ip in (PS5, PORTAL):
            rows = json.loads(subprocess.check_output(['ip', '-j', '-4', 'route', 'get', ip], text=True, timeout=2))
            if len(rows) != 1 or rows[0].get('dev') != IFACE or rows[0].get('gateway') or rows[0].get('type', 'unicast') != 'unicast' or rows[0].get('prefsrc') in (PS5, PORTAL):
                raise RuntimeError('Both devices must route directly through the selected interface.')
    else:
        if subprocess.check_output(['/usr/sbin/sysctl', '-n', 'net.inet.ip.forwarding'], text=True, timeout=2).strip() != '0':
            raise RuntimeError('IPv4 forwarding is enabled. No changes made.')
        for ip in (PS5, PORTAL):
            route = subprocess.check_output(['/sbin/route', '-n', 'get', ip], text=True, timeout=2)
            if re.search(r'flags:.*GATEWAY', route) or not re.search(rf'interface:\s+{re.escape(IFACE)}\b', route):
                raise RuntimeError('Both devices must route directly through the selected interface.')


def state_for(c, enroll=False):
    configure(c['network'])
    health()
    own = win.normal_mac(IFACE.mac if sys.platform == 'win32' else get_if_hwaddr(IFACE))
    state = {'config': dict(c['network']), 'own_mac': own}
    if sys.platform == 'win32':
        state['config']['interface'] = IFACE.network_name
    for key, ip in (('ps5_mac', PS5), ('portal_mac', PORTAL)):
        ans, _ = srp(Ether(src=own, dst='ff:ff:ff:ff:ff:ff') / ARP(hwsrc=own, pdst=ip), iface=IFACE, timeout=1, verbose=False)
        found = {win.normal_mac(r[ARP].hwsrc) for _, r in ans if ARP in r and r[ARP].op == 2 and r[ARP].psrc == ip}
        if enroll:
            if len(found) != 1:
                raise RuntimeError(f'{ip}: verify the device IP and LAN connection, then enroll again.')
            state[key] = found.pop()
        else:
            state[key] = win.normal_mac(c[key])
            if found - {state[key]}:
                raise RuntimeError('Enrolled IP now belongs to a different MAC. Reconfigure.')
    if len({state[k] for k in ('own_mac', 'ps5_mac', 'portal_mac')}) != 3:
        raise RuntimeError('Expected three distinct devices.')
    return state


def open_socket(filter=None):
    if sys.platform == 'win32':
        return win.open_socket(filter)
    # Explicit Ethernet framing; no Wi-Fi monitor mode.
    return conf.L2socket(iface=IFACE, filter=filter)


def receive(sock):
    if sys.platform == 'win32':
        _, frame, _ = sock.recv_raw()
        if not frame:
            time.sleep(.002)
        return frame
    if not sock.select([sock], remain=.02):
        return None
    _, frame, _ = sock.recv_raw()
    return frame


def send(sock, frame):
    if sys.platform == 'win32':
        win.send_raw(sock, frame)
    else:
        n = sock.send(frame)
        if n != len(bytes(frame)):
            raise RuntimeError('Incomplete Ethernet transmission')


def spawn_options():
    if sys.platform == 'win32':
        # Refuse to run if the enclosing job disallows an independent guardian.
        return {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS | subprocess.CREATE_BREAKAWAY_FROM_JOB}
    return {'start_new_session': True}


class Parent:
    """Pin the exact parent process on Windows; never kill a recycled PID."""
    def __init__(self, pid):
        self.pid = pid
        self.handle = None
        if sys.platform == 'win32':
            from ctypes import wintypes
            self.k = ctypes.WinDLL('kernel32', use_last_error=True)
            self.k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            self.k.OpenProcess.restype = wintypes.HANDLE
            self.k.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
            self.k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            self.k.CloseHandle.argtypes = [wintypes.HANDLE]
            self.handle = self.k.OpenProcess(0x00100001, False, pid)
            if not self.handle:
                raise ctypes.WinError(ctypes.get_last_error())

    def stop(self):
        if self.handle:
            if self.k.WaitForSingleObject(self.handle, 0) == 0x102:
                if not self.k.TerminateProcess(self.handle, 1):
                    raise RuntimeError('Could not stop stalled relay; recovery lock retained')
                if self.k.WaitForSingleObject(self.handle, 3000) != 0:
                    raise RuntimeError('Stalled relay has not exited')
        elif os.getppid() == self.pid:
            os.kill(self.pid, signal.SIGKILL)

    def close(self):
        if self.handle:
            self.k.CloseHandle(self.handle)


class Lock:
    def __init__(self, runtime, existing=False):
        self.handle = None
        self.path = Path('/var/run/portal-lab-capture.lock')
        if sys.platform == 'win32':
            self.handle = win.MachineLock(existing=existing)
        elif not existing:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, 'w') as f:
                f.write(str(os.getpid()))

    def close(self, parent, repaired=True):
        if self.handle:
            self.handle.close()
        elif repaired:
            try:
                if self.path.read_text().strip() == str(parent):
                    self.path.unlink()
            except FileNotFoundError:
                pass
