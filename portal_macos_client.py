"""Unprivileged TUI client for the signed macOS bridge; no sudo or passwords."""
import datetime
import json
import os
from pathlib import Path
import select
import subprocess
import time

BRIDGE = Path('/Applications/Better Portal.app/Contents/MacOS/PortalBridge')
MAX_REPLY = 1_048_576


class HelperUnavailable(RuntimeError):
    """No session was submitted; the app's authorization panel can resolve this."""


def user_directory():
    return Path.home() / 'Library/Application Support/Better Portal'


class Bridge:
    def __init__(self):
        self.process = subprocess.Popen([str(BRIDGE)], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        bufsize=0, cwd='/', env={
                                            'PATH': '/usr/bin:/bin:/usr/sbin:/sbin',
                                            'LANG': 'en_US.UTF-8'})
        self.buffer = bytearray()

    def exchange(self, message):
        encoded = json.dumps(message).encode() + b'\n'
        if len(encoded) > 4096:
            raise ValueError('Helper request too large')
        self.process.stdin.write(encoded)
        deadline = time.monotonic() + 35
        while b'\n' not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([self.process.stdout], [], [], remaining)[0]:
                raise RuntimeError('Helper did not respond. Open Better Portal to check its authorization.')
            data = os.read(self.process.stdout.fileno(), 65536)
            if not data:
                raise RuntimeError('Connection helper disconnected. Keep this Mac awake for recovery.')
            self.buffer.extend(data)
            if len(self.buffer) > MAX_REPLY:
                raise RuntimeError('Helper response too large')
        line, _, self.buffer = self.buffer.partition(b'\n')
        reply = json.loads(line)
        if not isinstance(reply, dict):
            raise RuntimeError('Invalid helper response')
        if reply.get('error'):
            raise RuntimeError(str(reply['error']))
        return reply

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        self.process.stdout.close()


def run_session(profile, config, progress, *, report_root=None, bridge_factory=Bridge):
    bridge = None
    submitted = False
    cancel = False
    last_event = {'type': 'checking'}
    try:
        if progress(last_event) is False:
            return {'completed': False, 'run_error': 'Cancelled by user',
                    'restoration_errors': [], 'preflight_failed': True}
        try:
            bridge = bridge_factory()
            status = bridge.exchange({'op': 'status'})
            if status.get('busy') or status.get('recovery_pending') or status.get('removing'):
                raise HelperUnavailable('Another attempt or recovery is active. Wait for it to finish.')
        except (RuntimeError, OSError) as exc:
            raise HelperUnavailable(str(exc)) from exc
        # After sending start, a lost reply is ambiguous. Never label it as a
        # preflight failure or offer an immediate retry with unknown recovery.
        submitted = True
        response = bridge.exchange({'op': 'start', 'profile': profile, 'config': config})
        if response.get('started') is not True:
            raise RuntimeError('Helper did not confirm session start')
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            try:
                reply = bridge.exchange({'op': 'cancel' if cancel else 'poll'})
                for event in reply.get('events', []):
                    last_event = event
                    if progress(event) is False:
                        cancel = True
                if 'report' in reply:
                    report = reply['report']
                    break
                # Preflight may take a few seconds; keep cancellation responsive
                # without advancing phases or fabricating countdown values.
                if progress(last_event) is False:
                    cancel = True
                time.sleep(.1)
            except KeyboardInterrupt:
                cancel = True
        else:
            raise RuntimeError('Helper recovery has not finished. Keep this Mac awake.')
    except HelperUnavailable:
        raise
    except (Exception, KeyboardInterrupt) as exc:
        if not submitted:
            raise HelperUnavailable(str(exc)) from exc
        report = {'completed': False, 'run_error': str(exc) or 'Cancelled by user',
                  'restoration_errors': ['Connection to helper lost; recovery could not be confirmed.'],
                  'watchdog_seconds': 155, 'managed_helper': True}
    finally:
        if bridge is not None:
            try:
                bridge.close()
            except (OSError, subprocess.SubprocessError) as exc:
                if not submitted:
                    raise HelperUnavailable(str(exc)) from exc
                report = {'completed': False, 'run_error': str(exc), 'managed_helper': True,
                          'restoration_errors': ['Helper connection cleanup could not be confirmed.']}
    # Only this unprivileged client chooses and writes a user report path.
    from portal_tui import save_private_json
    root = report_root if report_root is not None else user_directory() / 'reports'
    folder = root / datetime.datetime.now().strftime('session-%Y%m%d-%H%M%S-%f')
    try:
        folder.mkdir(parents=True, mode=0o700)
        report = dict(report, directory=str(folder), watchdog_state=None, managed_helper=True)
        save_private_json(folder / 'report.json', report)
    except OSError as exc:
        report = dict(report, report_write_error=str(exc), directory=None)
    return report
