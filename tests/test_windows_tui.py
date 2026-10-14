"""Windows enrollment, launch, and shared UI state contracts; no live networking."""
import ctypes
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import portal_active_probe as core
import portal_tui as tui
import portal_windows as win
import portal_windows_launcher as launcher
from portal_tui_platform import Adapter, WINDOWS_COPY, recovery_command
from portal_tui_text import LANGUAGES, CATALOGS, cell_width


class WindowsWizardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.adapters = [Adapter(r'\Device\NPF_{12345678-1234-1234-1234-123456789012}',
                                 'Wi-Fi 家庭 (192.168.1.10)'),
                         Adapter(r'\Device\NPF_{87654321-1234-1234-1234-123456789012}',
                                 'Ethernet (192.168.1.11)')]
        for override in (patch.object(tui, 'ROOT', self.root),
                         patch.object(tui, 'windows_adapters', return_value=self.adapters)):
            override.start()
            self.addCleanup(override.stop)
        self.curses = SimpleNamespace(
            A_BOLD=1, A_DIM=2, A_REVERSE=4, error=RuntimeError,
            has_colors=lambda: False, curs_set=lambda _: None, flushinp=lambda: None,
            KEY_UP=259, KEY_DOWN=258, KEY_LEFT=260, KEY_RIGHT=261,
            KEY_BTAB=353, KEY_ENTER=343, KEY_BACKSPACE=263, KEY_DC=330,
            KEY_HOME=262, KEY_END=360,
        )

    def wizard(self, platform='win32', demo=False, keys=()):
        screen = MagicMock()
        screen.getmaxyx.return_value = (24, 72)
        screen.getch.side_effect = keys
        return tui.Wizard(screen, self.curses, demo=demo, platform=platform)

    def test_arrow_selection_saves_full_adapter_id_without_touching_mac_config(self):
        mac = self.root / 'config.json'
        mac.write_text('existing Mac configuration')
        tui.save_private_json(self.root / 'tui-settings.json', {'language': 'zh-CN', 'profile': '100'})
        wizard = self.wizard(keys=[13, 13, self.curses.KEY_RIGHT, ord('a'), 13, 13, 13])
        wizard.values[:2] = ['192.168.1.20', '192.168.1.30']
        config = wizard.configure()
        self.assertEqual(config['interface'], self.adapters[1].id)
        self.assertGreater(len(config['interface']), 24)
        saved = tui.load_config(self.root / 'config.windows.json')
        self.assertEqual(saved, config)
        self.assertEqual(mac.read_text(), 'existing Mac configuration')
        again = self.wizard()
        self.assertEqual(again.values, wizard.values)
        self.assertEqual((again.language, again.profile), ('zh-CN', '100'))

    def test_missing_or_stale_adapter_cannot_be_saved(self):
        values = {'interface': 'missing adapter', 'ps5_ip': '192.168.1.20', 'portal_ip': '192.168.1.30'}
        with self.assertRaisesRegex(ValueError, 'available LAN adapter'):
            tui.validate_form(values, adapters=self.adapters)
        with self.assertRaises(ValueError):
            tui.validate_form(dict(values, interface=self.adapters[0].id), adapters=[])
        with self.assertRaisesRegex(ValueError, 'Mac LAN'):
            tui.validate_form(dict(values, interface=self.adapters[0].id))
        with patch.object(tui, 'windows_adapters', return_value=[]):
            wizard = self.wizard(keys=[13, 13, 13, 13, 13, 27])
        wizard.values[:2] = [values['ps5_ip'], values['portal_ip']]
        self.assertIsNone(wizard.configure())
        self.assertFalse((self.root / 'config.windows.json').exists())

    def test_guided_backends_receive_identical_timing_config_and_progress(self):
        config = {'interface': self.adapters[0].id, 'ps5_ip': '192.168.1.20', 'portal_ip': '192.168.1.30'}
        report = {'completed': True, 'restoration_errors': []}
        wizard = self.wizard()
        with patch.object(win, 'run_session', return_value=report) as run, \
                patch.object(core, 'run', side_effect=AssertionError('Windows cannot use Mac networking')):
            self.assertIs(wizard.connect(config), report)
        self.assertEqual(run.call_args.args, ('65',))
        self.assertEqual(run.call_args.kwargs,
                         {'connect_timeout': 120, 'confirmation_timeout': 15,
                          'progress': wizard.progress, 'config': config})

    def test_preflight_and_unexpected_failures_have_distinct_recovery_states(self):
        wizard = self.wizard()
        with patch.object(win, 'run_session', side_effect=core.PreflightError('Npcap missing')):
            report = wizard.connect({})
            self.assertTrue(report['preflight_failed'])
            self.assertEqual(report['restoration_errors'], [])
        with patch.object(win, 'run_session', side_effect=OSError('unhandled I/O')):
            self.assertEqual(tui.summarize(wizard.connect({})).kind, 'error')

    def test_same_evidence_drives_same_states_on_both_platforms(self):
        events = [{'type': 'checking'}, {'type': 'preparing'}, {'type': 'ready', 'seconds': 120},
                  {'type': 'tick', 'phase': 'waiting', 'seconds': 100}, {'type': 'modified'},
                  {'type': 'observed', 'accepted': True},
                  {'type': 'observed', 'accepted': True, 'streaming': True, 'samples': 1},
                  {'type': 'observed', 'accepted': True, 'streaming': True, 'samples': 3},
                  {'type': 'restoring'}]
        snapshots = []
        for platform in ('darwin', 'win32'):
            wizard = self.wizard(platform, demo=True, keys=[-1] * len(events))
            stages = []
            for event in events:
                self.assertTrue(wizard.progress(event))
                stages.append((wizard.connection_stage(), dict(wizard.event)))
            snapshots.append(stages)
        self.assertEqual(*snapshots)

    def test_windows_copy_and_labels_fit_in_every_language(self):
        for language in LANGUAGES:
            wizard = self.wizard()
            wizard.language = language
            wizard.draw_form()
            draws = wizard.screen.addstr.call_args_list
            label = next(call.args for call in draws if call.args[2] == wizard.t('Mac LAN interface'))
            self.assertLess(label[1] + cell_width(label[2]), 27)
            for call in draws:
                self.assertNotIn('en0', call.args[2])
                self.assertNotIn('Mac', call.args[2])
                self.assertLessEqual(call.args[1] + cell_width(call.args[2]), 71)
            for mac, pc in WINDOWS_COPY.items():
                self.assertNotIn('Mac', wizard.t(mac))
                if language != 'en':
                    self.assertIn(pc, CATALOGS[language])

    def test_windows_demo_needs_no_adapters_and_writes_nothing(self):
        with patch.object(tui, 'windows_adapters', side_effect=AssertionError('Demo cannot discover adapters')):
            wizard = self.wizard(demo=True, keys=[13, 13, 13, 13, 13])
        self.assertIsNotNone(wizard.configure())
        wizard.save_preferences(language='fr')
        self.assertEqual(list(self.root.iterdir()), [])

    def test_windows_recovery_command_quotes_powershell_metacharacters(self):
        state = "C:\\Users\\Test's PC\\Portal&$(literal)`\\recovery-state.json"
        command = recovery_command(state, windows=True)
        self.assertEqual(command,
                         "& '.venv\\Scripts\\python.exe' 'portal_windows.py' '--restore' "
                         "'C:\\Users\\Test''s PC\\Portal&$(literal)`\\recovery-state.json'")
        self.assertNotIn('sudo', command)
        self.assertNotIn('portal_capture.py', command)


class LauncherTests(unittest.TestCase):
    def test_uac_runs_python_directly_and_preserves_paths_and_options(self):
        shell = MagicMock()
        shell.ShellExecuteW.return_value = 42
        root = Path('/folder with spaces & punctuation')
        with patch.object(ctypes, 'windll', SimpleNamespace(shell32=shell), create=True), \
                patch.object(launcher, 'ROOT', root):
            launcher.elevate(['--no-animations'])
        args = shell.ShellExecuteW.call_args.args
        self.assertEqual(args[1], 'runas')
        self.assertEqual(args[2], launcher.sys.executable)
        self.assertEqual(args[3], subprocess.list2cmdline([
            str(root / 'portal_windows_launcher.py'), '--elevated', '--no-animations']))
        self.assertEqual(args[4], str(root))

    def test_uac_denial_is_visible_and_never_launches_the_wizard(self):
        shell = MagicMock()
        for code in (0, 5, 32):
            shell.ShellExecuteW.return_value = code
            with patch.object(ctypes, 'windll', SimpleNamespace(shell32=shell), create=True):
                with self.assertRaisesRegex(RuntimeError, 'not granted'):
                    launcher.elevate([])

    def test_demo_does_not_elevate_or_require_npcap(self):
        with patch.object(launcher.sys, 'platform', 'win32'), \
                patch.object(launcher.sys, 'argv', ['launcher', '--demo', '--no-animations']), \
                patch.object(launcher.sys.stdin, 'isatty', return_value=False), \
                patch.object(launcher, 'windows_admin', side_effect=AssertionError('No UAC in demo')), \
                patch.object(tui, 'main', return_value=0) as main:
            self.assertEqual(launcher.main(), 0)
            main.assert_called_once()


if __name__ == '__main__':
    unittest.main()
