"""Windows/Npcap adapter for a single explicitly configured local device pair."""
import ctypes
import ipaddress
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from scapy.all import ARP, Ether, conf, srp
from scapy.data import MTU
from scapy.interfaces import resolve_iface
from portal_recovery import restore_peer_mappings

ROOT = Path(__file__).resolve().parent
PS5 = '192.0.2.10'
PORTAL = '192.0.2.20'
IFACE = None
MUTEX_NAME = 'Global\\PS5PortalBitrateLabPreview'


def require_windows():
    if sys.platform != 'win32':
        raise RuntimeError('Run this launcher on native Windows 10/11, not WSL.')
    if not ctypes.windll.shell32.IsUserAnAdmin():
        raise RuntimeError('Open Windows Terminal as administrator, then retry.')
    conf.use_pcap = True
    if not conf.use_npcap:
        raise RuntimeError('Npcap is required. Install it from https://npcap.com/#download and restart this terminal.')


def validate_config(c):
    if set(c) != {'interface', 'ps5_ip', 'portal_ip'} or not isinstance(c['interface'], str) or not c['interface'].strip():
        raise ValueError('Config requires interface, ps5_ip and portal_ip.')
    try:
        ipaddress.ip_address(c['interface'].strip())
    except ValueError:
        pass
    else:
        raise ValueError('The LAN interface is an adapter name/ID, not the PC IP address. Run Configure and select your adapter.')
    ips = [ipaddress.IPv4Address(c[k]) for k in ('ps5_ip', 'portal_ip')]
    if ips[0] == ips[1] or any(x.is_multicast or x.is_loopback or x.is_unspecified or x.is_reserved for x in ips):
        raise ValueError('Use two distinct unicast device IPv4 addresses.')
    return c


def configure(c=None):
    global IFACE, PS5, PORTAL
    c = validate_config(c if c is not None else json.loads((ROOT / 'config.windows.json').read_text(encoding='utf-8-sig')))
    IFACE = resolve_iface(c['interface'])
    PS5, PORTAL = c['ps5_ip'], c['portal_ip']
    return c


def normal_mac(value):
    if not re.fullmatch(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}', value or ''):
        raise ValueError('Invalid Ethernet MAC address.')
    if int(value[:2], 16) & 1 or value == '00:00:00:00:00:00':
        raise ValueError('Expected unicast Ethernet MAC address.')
    return value.lower()


def forwarding_disabled(index):
    # Query only: do not disable sharing, firewalls, routing or registry settings.
    script = ("$ErrorActionPreference='Stop'; Get-NetIPInterface -AddressFamily IPv4 "
              f"-InterfaceIndex {int(index)} | Select-Object InterfaceIndex,Forwarding | ConvertTo-Json -Compress")
    try:
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
                                capture_output=True, text=True, check=True, timeout=15)
    except subprocess.CalledProcessError as exc:
        reason = (exc.stderr or exc.stdout or f'Exit status {exc.returncode}').strip()
        raise RuntimeError('Windows could not check adapter forwarding. ' + reason) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Windows adapter forwarding check timed out. Retry the setup check.') from exc
    except OSError as exc:
        raise RuntimeError('Windows could not start its adapter check: ' + str(exc)) from exc
    try:
        data = json.loads(result.stdout.lstrip('\ufeff'))
    except (ValueError, AttributeError) as exc:
        raise RuntimeError('Windows returned an unreadable adapter forwarding status. No network changes made.') from exc
    rows = data if isinstance(data, list) else [data]
    if not rows or any(not isinstance(x, dict) or x.get('InterfaceIndex') != int(index)
                       or x.get('Forwarding') not in (0, 'Disabled') for x in rows):
        raise RuntimeError('Selected adapter has forwarding enabled or unknown state. No changes made.')


def peer_mac(ip):
    answers, _ = srp(Ether(src=IFACE.mac, dst='ff:ff:ff:ff:ff:ff') / ARP(pdst=ip),
                     iface=IFACE, timeout=2, retry=1, verbose=False)
    found = {normal_mac(r[ARP].hwsrc) for _, r in answers
             if ARP in r and r[ARP].op == 2 and r[ARP].psrc == ip}
    if len(found) != 1:
        raise RuntimeError(f'{ip}: could not resolve exactly one peer. Check IP, Wi-Fi isolation and power.')
    return found.pop()


def preflight(c):
    conf.route.resync()
    for ip in (PS5, PORTAL):
        iface, source, gateway = conf.route.route(ip)
        routed = resolve_iface(iface)
        device = 'PS5' if ip == PS5 else 'Portal'
        if routed.network_name != IFACE.network_name:
            raise RuntimeError(f'{device} uses {routed.name}. Select that connection under PC LAN adapter, then retry.')
        if gateway != '0.0.0.0':
            raise RuntimeError(f'{device} is not on the selected local network. Check its IPv4 address and VPN/guest Wi-Fi routes.')
        if source in (PS5, PORTAL, '0.0.0.0'):
            raise RuntimeError('Peer IP matches this computer, or no local address exists.')
    forwarding_disabled(IFACE.index)
    state = {'config': dict(c, interface=IFACE.network_name), 'own_mac': normal_mac(IFACE.mac),
             'ps5_mac': peer_mac(PS5), 'portal_mac': peer_mac(PORTAL)}
    if len({state[k] for k in ('own_mac', 'ps5_mac', 'portal_mac')}) != 3:
        raise RuntimeError('Expected three distinct devices; refusing proxy ARP/gateway mappings.')
    return state


def frames(state, restore=False):
    a, b, own = state['ps5_mac'], state['portal_mac'], state['own_mac']
    return [Ether(src=own, dst=a)/ARP(op=2, psrc=PORTAL, pdst=PS5, hwsrc=b if restore else own, hwdst=a),
            Ether(src=own, dst=b)/ARP(op=2, psrc=PS5, pdst=PORTAL, hwsrc=a if restore else own, hwdst=b)]


def _pcap_error(api, handle, status):
    # Only PCAP_ERROR promises fresh handle error text; other statuses can
    # otherwise repeat an unrelated error from an earlier operation.
    if status == api.PCAP_ERROR:
        return (api.pcap_geterr(handle) or b'No driver error provided.').decode(errors='replace')
    if status == api.PCAP_ERROR_BREAK:
        return 'Capture ended unexpectedly.'
    if status == api.PCAP_ERROR_NOT_ACTIVATED:
        return 'Capture handle is not activated.'
    return f'Unexpected Npcap status {status}.'


class _NpcapSocket:
    """Preserve native Npcap errors and copy only the captured packet bytes.

    Scapy 2.6.1 treats pcap_next_ex errors as an empty queue and discards the
    pcap_setnonblock result. The relay needs both failures to stop and recover.
    Scapy still owns adapter selection, capture setup, filters and handle cleanup.
    """
    def __init__(self, capture, api):
        self._capture = capture
        self._api = api
        self._handle = capture.pcap_fd.pcap
        self._header = ctypes.POINTER(api.pcap_pkthdr)()
        self._data = ctypes.POINTER(ctypes.c_ubyte)()

    def recv_raw(self):
        result = self._api.pcap_next_ex(
            self._handle, ctypes.byref(self._header), ctypes.byref(self._data))
        if result == 0:
            return None, None, None
        if result != 1:
            raise RuntimeError('Npcap packet capture failed: ' + _pcap_error(self._api, self._handle, result))
        if not self._header or not self._data:
            raise RuntimeError('Npcap returned an empty packet buffer.')
        header = self._header.contents
        if header.caplen < header.len:
            raise RuntimeError(f'Npcap truncated an Ethernet frame ({header.caplen}/{header.len} bytes).')
        if not 0 < header.caplen <= MTU or header.caplen != header.len:
            raise RuntimeError('Npcap returned an invalid packet length.')
        # Npcap owns the buffer and can overwrite it on the next receive call.
        frame = ctypes.string_at(self._data, header.caplen)
        timestamp = header.ts.tv_sec + header.ts.tv_usec / 1e6
        return Ether, frame, timestamp

    def send(self, frame):
        data = bytes(frame)
        # This API returns zero on success; unlike pcap_inject it has no byte count.
        result = self._api.pcap_sendpacket(self._handle, data, len(data))
        if result != 0:
            raise RuntimeError('Npcap packet injection failed: ' + _pcap_error(self._api, self._handle, result))
        return len(data)

    def close(self):
        self._capture.close()


def open_socket(filter=None):
    from scapy.libs import winpcapy as api
    sock = conf.L2socket(iface=IFACE, filter=filter, promisc=True)
    try:
        if sock.pcap_fd.datalink() != 1:
            raise RuntimeError('Adapter must expose Ethernet frames. Do not use Wi-Fi monitor mode.')
        handle = sock.pcap_fd.pcap
        result = api.pcap_setmintocopy(handle, 0)
        if result != 0:
            raise RuntimeError('Npcap low-latency capture setup failed: ' + _pcap_error(api, handle, result))
        error = ctypes.create_string_buffer(api.PCAP_ERRBUF_SIZE)
        result = api.pcap_setnonblock(handle, True, error)
        if result != 0:
            reason = error.value.decode(errors='replace') or _pcap_error(api, handle, result)
            raise RuntimeError('Npcap nonblocking capture setup failed: ' + reason)
        return _NpcapSocket(sock, api)
    except BaseException:
        sock.close()
        raise


def send_raw(sock, frame):
    data = bytes(frame)
    if sock.send(data) != len(data):
        raise RuntimeError('Incomplete Npcap packet injection.')


def restore(state, *, service=None):
    sock = None
    errors = []
    try:
        configure(state['config'])
        sock = open_socket()
        errors.extend(restore_peer_mappings(
            lambda frame: send_raw(sock, frame), frames(state, True), service=service))
    except Exception as exc:
        errors.append(f'{type(exc).__name__}: {exc}')
    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception as exc:
                errors.append('Adapter close: ' + type(exc).__name__)
    return errors


class MachineLock:
    """A named kernel object held by parent and watchdog until restoration ends."""
    def __init__(self, existing=False):
        from ctypes import wintypes
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        k.CreateMutexW.restype = wintypes.HANDLE
        k.OpenMutexW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        k.OpenMutexW.restype = wintypes.HANDLE
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.CloseHandle.restype = wintypes.BOOL
        self.k = k
        ctypes.set_last_error(0)
        self.handle = k.OpenMutexW(0x00100000, False, MUTEX_NAME) if existing else k.CreateMutexW(None, False, MUTEX_NAME)
        error = ctypes.get_last_error()
        if not self.handle:
            raise ctypes.WinError(error)
        if not existing and error == 183:
            self.close()
            raise RuntimeError('Another Portal experiment or recovery watchdog is running.')

    def close(self):
        if self.handle:
            self.k.CloseHandle(self.handle)
            self.handle = None
