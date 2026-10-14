"""Small native-host differences for the shared terminal wizard."""
import ctypes
from dataclasses import dataclass
import ipaddress
import subprocess


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


def recovery_command(state, windows=False):
    if windows:
        return subprocess.list2cmdline([
            r'.venv\Scripts\python.exe', 'portal_windows.py', '--restore', str(state)])
    import shlex
    return 'sudo .venv/bin/python portal_capture.py --restore ' + shlex.quote(str(state))
