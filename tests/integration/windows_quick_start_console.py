"""Verify the real CMD/PowerShell launch chain preserves native console handles.

Only the copied launcher's final Python target is a probe. The shared curses UI
is exercised separately in the same freshly prepared environment.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback

from windows_tui_smoke import console


def child(root, result):
    launcher = root / 'portal_windows_launcher.py'
    original = launcher.read_bytes()
    try:
        console()
        for expected in (0, 7):
            launcher.write_text(
                'import json, os, sys\nfrom pathlib import Path\n'
                "Path('console-probe.json').write_text(json.dumps({"
                "'tty': [sys.stdin.isatty(), sys.stdout.isatty(), sys.stderr.isatty()], "
                "'args': sys.argv[1:], 'cwd': os.getcwd()}), encoding='utf-8')\n"
                f'raise SystemExit({expected})\n', encoding='utf-8')
            entry = root / 'Start-Windows.cmd'
            command = f'"{os.environ["COMSPEC"]}" /d /s /c ""{entry}" -Demo -NoPause"'
            process = subprocess.run(command, cwd=root, timeout=90)
            probe = json.loads((root / 'console-probe.json').read_text(encoding='utf-8'))
            if process.returncode != expected or probe['tty'] != [True, True, True]:
                raise AssertionError((process.returncode, expected, probe))
            if probe['args'] != ['--demo'] or Path(probe['cwd']) != root:
                raise AssertionError(probe)
        report = {'ok': True, 'console_handles': 'interactive', 'exit_codes': [0, 7]}
    except BaseException:
        report = {'ok': False, 'error': traceback.format_exc()}
    finally:
        launcher.write_bytes(original)
    result.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return 0 if report['ok'] else 1


def main():
    if len(sys.argv) == 4 and sys.argv[1] == '--child':
        return child(Path(sys.argv[2]), Path(sys.argv[3]))
    root = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory() as directory:
        result = Path(directory) / 'console-result.json'
        process = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--child', str(root), str(result)],
                                 creationflags=subprocess.CREATE_NEW_CONSOLE, timeout=210)
        if not result.exists():
            raise RuntimeError('Native launch test did not produce a report')
        report = json.loads(result.read_text(encoding='utf-8'))
        print(json.dumps(report, indent=2))
        return 0 if process.returncode == 0 and report.get('ok') else 1


if __name__ == '__main__':
    raise SystemExit(main())
