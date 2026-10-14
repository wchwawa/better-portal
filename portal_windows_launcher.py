"""Open the shared wizard with a native UAC prompt; never handle passwords."""
import argparse
import ctypes
from ctypes import wintypes
from pathlib import Path
import subprocess
import sys

from portal_tui_platform import windows_admin

ROOT = Path(__file__).resolve().parent


def elevate(arguments):
    """Launch Python directly, so paths never pass through cmd/PowerShell code."""
    execute = ctypes.windll.shell32.ShellExecuteW
    execute.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR,
                        wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_int]
    execute.restype = ctypes.c_void_p
    parameters = subprocess.list2cmdline([
        str(ROOT / 'portal_windows_launcher.py'), '--elevated', *arguments])
    result = execute(None, 'runas', sys.executable, parameters, str(ROOT), 1)
    if not result or result <= 32:
        raise RuntimeError('Windows permission was not granted. Reopen Start-Windows.cmd to try again.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--no-animations', action='store_true')
    parser.add_argument('--elevated', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if sys.platform != 'win32':
            raise RuntimeError('Use Start.command on macOS; this launcher is for native Windows.')
        forwarded = (['--demo'] if args.demo else []) + (['--no-animations'] if args.no_animations else [])
        if not args.demo and not windows_admin():
            if args.elevated:
                raise RuntimeError('Administrator access was not granted. Reopen Start-Windows.cmd.')
            elevate(forwarded)
            return 0
        import portal_tui
        previous = sys.argv
        try:
            sys.argv = ['portal_tui.py', *forwarded]
            result = portal_tui.main()
        except SystemExit as exc:
            result = exc.code or 0
        finally:
            sys.argv = previous
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        result = 2
    if sys.stdin.isatty():
        try:
            input('\nPress Enter to close. ')
        except (EOFError, KeyboardInterrupt):
            pass
    return result


if __name__ == '__main__':
    raise SystemExit(main())
