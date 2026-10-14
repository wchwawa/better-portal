"""Fixed entry points for the signed, installed macOS runtime.

The helper invokes worker with an authenticated UID and sends only validated
session input over a private pipe. No user-supplied executable or output path is
accepted. Source checkouts keep using the existing sudo launcher.
"""
import argparse
import json
import os
from pathlib import Path
import select
import signal
import stat
import sys
import time
import uuid

STORAGE = Path('/Library/Application Support/Better Portal/Private')
RUNTIME = STORAGE / 'PortalRuntime/PortalRuntime'
LOCK = Path('/var/run/portal-lab-capture.lock')


def private_directory(path):
    """Create a fixed helper-owned directory or reject a pre-planted entry."""
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
        raise RuntimeError('Helper storage is not a private root-owned directory')
    return path


def recovery_path(path):
    value = Path(path)
    if (not value.is_absolute() or value.resolve() != value
            or not value.is_relative_to(STORAGE / 'sessions') or value.name != 'state.json'):
        raise ValueError('Recovery must use a helper-owned state file')
    current = value
    while current != STORAGE.parent:
        info = current.lstat()
        if info.st_uid != 0 or info.st_mode & 0o077 or stat.S_ISLNK(info.st_mode):
            raise ValueError('Recovery state is not protected')
        current = current.parent
    return value


def emit(value):
    try:
        print(json.dumps(value, separators=(',', ':')), flush=True)
        return True
    except (BrokenPipeError, OSError):
        return False


def public_report(report):
    # Raw capture and recovery paths never cross the privilege boundary.
    return dict(report, directory=None, watchdog_state=None, managed_helper=True)


def worker(caller_uid):
    import portal_active_probe as probe
    import portal_capture as network
    raw = sys.stdin.buffer.readline(4097)
    if len(raw) > 4096 or not raw.endswith(b'\n'):
        raise ValueError('Invalid session request')
    request = json.loads(raw)
    if not isinstance(request, dict) or set(request) != {'config', 'profile'}:
        raise ValueError('Invalid session request')
    network.validate_config(request['config'])
    if request['profile'] not in probe.PROFILES or caller_uid < 501:
        raise ValueError('Invalid session request')
    private_directory(STORAGE)
    sessions = private_directory(STORAGE / 'sessions')
    probe.set_profile(request['profile'])
    context = probe.HelperContext(caller_uid, sessions, (str(RUNTIME), 'watchdog'), uuid.uuid4().hex)

    def progress(event):
        connected = emit({'event': event})
        if event['type'] in ('restoring', 'stopping'):
            return True
        # EOF means the helper disappeared. Unknown pipe input also cancels;
        # nothing sent after enrollment is interpreted as code or configuration.
        return connected and not select.select([sys.stdin], [], [], 0)[0]

    try:
        report = probe.run(True, finish_on_high_target=True, connect_timeout=120,
                           confirmation_timeout=15, progress=progress,
                           config=request['config'], helper_context=context)
    except (probe.PreflightError, KeyboardInterrupt) as exc:
        report = {'completed': False, 'preflight_failed': True, 'restoration_errors': [],
                  'run_error': 'Cancelled by user' if isinstance(exc, KeyboardInterrupt) else str(exc)}
    emit({'report': public_report(report)})


def watchdog(path, seconds):
    import portal_capture as network
    if not 16 <= seconds <= 170:
        raise ValueError('Invalid recovery deadline')
    parent_pid = os.getppid()
    saved = recovery_path(path)
    state = json.loads(saved.read_text())
    token = state.get('helper_lock_token')
    if not isinstance(token, str) or len(token) != 32 or not all(c in '0123456789abcdef' for c in token):
        raise ValueError('Invalid recovery ownership')
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    os.umask(0o077)
    saved.with_suffix('.ready').write_text('ready\n')
    time.sleep(seconds)
    stop_parent(parent_pid)
    errors = network.restore(state)
    saved.with_suffix('.result.json').write_text(json.dumps({'restoration_errors': errors}))
    if not errors and LOCK.exists() and LOCK.read_text() == token:
        LOCK.unlink()
    return 1 if errors else 0


def stop_parent(parent_pid):
    """Stop our own relay before repair; never signal a reused numeric PID.

    getppid() ties the identity to the kernel's parent-child relationship. Once
    orphaned, a watchdog must not signal the old PID, which may have been reused.
    """
    if parent_pid <= 1 or os.getppid() != parent_pid:
        return
    try:
        os.kill(parent_pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + 3
    while os.getppid() == parent_pid and time.monotonic() < deadline:
        time.sleep(.05)
    if os.getppid() == parent_pid:
        try:
            os.kill(parent_pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + 3
        while os.getppid() == parent_pid and time.monotonic() < deadline:
            time.sleep(.05)
        if os.getppid() == parent_pid:
            raise RuntimeError('Relay has not stopped; retaining the recovery lock')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='mode', required=True)
    commands.add_parser('self-test', help='Check bundled imports without changing networking')
    ui = commands.add_parser('tui')
    ui.add_argument('--demo', action='store_true')
    ui.add_argument('--no-animations', action='store_true')
    task = commands.add_parser('worker')
    task.add_argument('--caller-uid', type=int, required=True)
    recovery = commands.add_parser('watchdog')
    recovery.add_argument('--watchdog', required=True)
    recovery.add_argument('--watchdog-seconds', type=int, required=True)
    args = parser.parse_args()
    if args.mode == 'self-test':
        import portal_active_probe as probe
        from scapy.all import Ether, ARP
        from portal_tui_text import LANGUAGES, CATALOGS
        assert probe.RelayWindow(0, 120, 15).watchdog_seconds == 155
        assert len(bytes(Ether() / ARP())) == 42
        assert len(LANGUAGES) == 6 and len(CATALOGS) == 5
        print('Bundled relay, packet encoding and six language catalogs loaded.')
        return 0
    if args.mode == 'tui':
        if os.geteuid() == 0:
            parser.error('Open Better Portal as your normal Mac user')
        import portal_tui
        sys.argv = [sys.argv[0], '--helper']
        if args.demo:
            sys.argv.append('--demo')
        if args.no_animations:
            sys.argv.append('--no-animations')
        return portal_tui.main()
    if not getattr(sys, 'frozen', False) or Path(sys.executable) != RUNTIME or os.geteuid() != 0:
        parser.error('Privileged operations require the installed macOS connection helper')
    if args.mode == 'worker':
        worker(args.caller_uid)
        return 0
    return watchdog(args.watchdog, args.watchdog_seconds)


if __name__ == '__main__':
    raise SystemExit(main())
