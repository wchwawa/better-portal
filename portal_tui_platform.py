"""Small native-host differences for the shared terminal wizard."""
import ctypes
from dataclasses import dataclass
import ipaddress


# Keep the existing Mac copy; Windows uses the corresponding localized PC copy.
WINDOWS_COPY = {
    '  /  Mac + PS5 + Portal': '  /  PC + PS5 + Portal',
    'Mac awake': 'PC awake',
    'Mac LAN interface': 'PC LAN adapter',
    'Restoring the direct path; please keep this Mac awake.':
        'Restoring the direct path; please keep this PC awake.',
    'Keep this Mac awake until the result appears.': 'Keep this PC awake until the result appears.',
    'D: recovery details    Q / Esc: quit (keep Mac awake)':
        'D: recovery details    Q / Esc: quit (keep PC awake)',
    'Keep this Mac awake for automatic recovery. Reconnect Portal if needed. Press D for recovery details. Start another attempt only after recovery.':
        'Keep this PC awake for automatic recovery. Reconnect Portal if needed. Press D for recovery details. Start another attempt only after recovery.',
}


@dataclass(frozen=True)
class Adapter:
    id: str
    label: str


def windows_adapters():
    """List local adapters only; do not scan or change network settings."""
    from scapy.all import conf
    choices = []
    for adapter in conf.ifaces.values():
        try:
            address = ipaddress.IPv4Address(adapter.ip)
            if address.is_loopback or address.is_unspecified or not adapter.mac:
                continue
            if not adapter.is_valid():
                continue
        except (AttributeError, ValueError):
            continue
        label = f'{adapter.name} ({address})'
        choices.append(Adapter(adapter.network_name, label))
    return sorted(choices, key=lambda item: (item.label.casefold(), item.id))


def windows_admin():
    return bool(ctypes.windll.shell32.IsUserAnAdmin())


def windows_adapter_for_peers(values, adapters):
    """Suggest only a shared direct route; never probe devices or change routes."""
    if not adapters:
        return None
    from scapy.all import conf
    from scapy.interfaces import resolve_iface
    try:
        peers = [str(ipaddress.IPv4Address(values[key].strip()))
                 for key in ('ps5_ip', 'portal_ip')]
        if peers[0] == peers[1]:
            return None
        conf.route.resync()
        choices = set()
        for peer in peers:
            iface, source, gateway = conf.route.route(peer)
            if gateway != '0.0.0.0' or source in (*peers, '0.0.0.0'):
                return None
            choices.add(resolve_iface(iface).network_name)
        if len(choices) == 1:
            choice = choices.pop()
            if choice in {adapter.id for adapter in adapters}:
                return choice
    except (OSError, ValueError, KeyError, AttributeError):
        pass
    return None


def recovery_command(state, windows=False, *, python=None, script=None):
    if windows:
        # This is displayed for pasting into PowerShell, not passed to CreateProcess.
        # Single quotes keep $, &, backticks and spaces literal in folder names.
        arguments = [r'.venv\Scripts\python.exe', 'portal_windows.py', '--restore', str(state)]
        return '& ' + ' '.join("'" + value.replace("'", "''") + "'" for value in arguments)
    import shlex
    return shlex.join(['sudo', str(python or '.venv/bin/python'),
                       str(script or 'portal_capture.py'), '--restore', str(state)])
