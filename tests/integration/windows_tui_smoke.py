"""Run the real Windows curses UI in a private console, with simulated networking.

The parent stays attached to CI logs. Only the child allocates a new console.
No UAC, driver, host network change, or real device is involved.
"""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def console():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel.GetStdHandle.restype = wintypes.HANDLE
    kernel.FreeConsole()
    if not kernel.AllocConsole():
        raise ctypes.WinError(ctypes.get_last_error())
    sys.stdin = open('CONIN$', 'r', encoding='utf-8')
    sys.stdout = open('CONOUT$', 'w', encoding='utf-8')
    sys.stderr = open('CONOUT$', 'w', encoding='utf-8')
    handle = kernel.GetStdHandle(-11)

    class Coord(ctypes.Structure):
        _fields_ = [('x', ctypes.c_short), ('y', ctypes.c_short)]

    class Rect(ctypes.Structure):
        _fields_ = [('left', ctypes.c_short), ('top', ctypes.c_short),
                    ('right', ctypes.c_short), ('bottom', ctypes.c_short)]

    kernel.SetConsoleWindowInfo.argtypes = [wintypes.HANDLE, wintypes.BOOL, ctypes.POINTER(Rect)]
    kernel.SetConsoleScreenBufferSize.argtypes = [wintypes.HANDLE, Coord]
    rect = Rect(0, 0, 71, 23)
    if not kernel.SetConsoleWindowInfo(handle, True, ctypes.byref(rect)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel.SetConsoleScreenBufferSize(handle, Coord(72, 24)):
        raise ctypes.WinError(ctypes.get_last_error())


def exercise(screen):
    import curses
    import portal_tui as tui
    from portal_tui_text import LANGUAGES

    class StrictScreen:
        """Use native drawing/input; fail instead of hiding a curses draw error."""
        def __init__(self):
            self.keys = []
            self.writes = 0
            self.text = []

        def __getattr__(self, key):
            return getattr(screen, key)

        def getch(self):
            if self.keys:
                curses.ungetch(self.keys.pop(0))
            return screen.getch()

        def addstr(self, *args):
            try:
                screen.addstr(*args)
            except curses.error as exc:
                raise AssertionError(f'Native drawing failed at {args!r}') from exc
            self.writes += 1
            self.text.append(args[2])

    strict = StrictScreen()
    results = []
    with tempfile.TemporaryDirectory() as directory:
        previous_root = tui.ROOT
        tui.ROOT = Path(directory)
        try:
            for index, language in enumerate(LANGUAGES):
                wizard = tui.Wizard(strict, curses, demo=True)
                assert wizard.windows
                strict.keys = [curses.KEY_DOWN] * index + [13]
                assert wizard.choose_language() and wizard.language == language
                strict.keys = [13]
                assert wizard.prepare()
                strict.keys = [13, 13, curses.KEY_RIGHT, 13, curses.KEY_RIGHT, curses.KEY_LEFT, 13, 13]
                config = wizard.configure()
                assert config['interface'] == 'demo-wifi'
                assert wizard.profile == '65'
                report = wizard.connect(config)
                assert tui.summarize(report).kind == 'success'
                strict.keys = [ord('q')]
                assert not wizard.result(report)
                for failed in ({'completed': True, 'unique_mutated_sequences': 0},
                               {'restoration_errors': ['simulated recovery failure']}):
                    wizard.draw_result(tui.summarize(failed), 1)
                failed = {'completed': False, 'preflight_failed': True,
                          'run_error': ('Diagnostic context ' * 100) + 'CIM_ACCESS_DENIED',
                          'restoration_errors': []}
                assert tui.summarize(failed).title == 'Setup check failed'
                wizard.draw_result(tui.summarize(failed), 1)
                strict.text.clear()
                strict.keys = [curses.KEY_DOWN] * 40 + [13]
                wizard.details(failed)
                assert 'CIM_ACCESS_DENIED' in '\n'.join(strict.text), 'Error details must be readable by scrolling'
                wizard.settings_key(ord('s'))
                wizard.settings_key(curses.KEY_RIGHT)
                wizard.refresh()
                assert wizard.language == LANGUAGES[(index + 1) % len(LANGUAGES)]
                wizard.settings_key(27)
                results.append({'language': language, 'flow': 'prepare/devices/connect/result/error-details/settings'})
            assert not list(Path(directory).iterdir()), 'Demo must not write configuration or reports'
        finally:
            tui.ROOT = previous_root
    return {'ok': True, 'console_size': screen.getmaxyx(), 'native_draw_calls': strict.writes,
            'languages': results, 'network': 'simulated; no Npcap or devices'}


def child(path):
    result = {}
    try:
        console()
        import curses
        result = curses.wrapper(exercise)
    except BaseException:
        result = {'ok': False, 'error': traceback.format_exc()}
    finally:
        path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return 0 if result.get('ok') else 1


def main():
    if sys.platform != 'win32':
        raise SystemExit('This check requires native Windows.')
    if len(sys.argv) == 3 and sys.argv[1] == '--child':
        return child(Path(sys.argv[2]))
    with tempfile.TemporaryDirectory() as directory:
        result = Path(directory) / 'result.json'
        process = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--child', str(result)],
                                 creationflags=subprocess.CREATE_NEW_CONSOLE, timeout=120)
        if not result.exists():
            raise RuntimeError(f'Console child exited {process.returncode} without a report')
        report = json.loads(result.read_text(encoding='utf-8'))
        print(json.dumps(report, indent=2))
        return 0 if process.returncode == 0 and report.get('ok') else 1


if __name__ == '__main__':
    raise SystemExit(main())
