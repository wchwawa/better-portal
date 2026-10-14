"""Homebrew launch, migration and update tests; no privilege or network changes."""
from contextlib import contextmanager, redirect_stdout
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import portal_cli as cli
import portal_tui as tui
from portal_tui_platform import recovery_command
import test_tui as relay_tests


class HomebrewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='better portal ')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / 'old checkout'
        self.destination = self.root / 'user data'
        self.source.mkdir()
        self.destination.mkdir()
        self.config = {'interface': 'en0', 'ps5_ip': '192.168.1.20', 'portal_ip': '192.168.1.30'}
        self.settings = {'language': 'zh-CN', 'profile': '65'}

    def write_source(self):
        for name, value in [('config.json', self.config), ('tui-settings.json', self.settings)]:
            (self.source / name).write_text(json.dumps(value), encoding='utf-8')

    def test_import_is_repeatable_preserves_existing_values_and_ignores_other_files(self):
        self.write_source()
        (self.source / 'unrelated.key').write_text('private fixture')
        self.assertEqual(cli.import_settings(self.source, self.destination), 2)
        saved = {path.name: path.read_bytes() for path in self.destination.iterdir()}
        self.settings['profile'] = '200'
        self.write_source()
        self.assertEqual(cli.import_settings(self.source, self.destination), 0)
        self.assertEqual(saved, {path.name: path.read_bytes() for path in self.destination.iterdir()})
        self.assertEqual(set(saved), {'config.json', 'tui-settings.json'})
        if os.name != 'nt':
            self.assertEqual((self.destination / 'config.json').stat().st_mode & 0o777, 0o600)
        self.assertTrue((self.source / 'config.json').exists())

    def test_invalid_second_file_cannot_partially_import_first_file(self):
        self.write_source()
        (self.source / 'tui-settings.json').write_text('{"profile": "999"}')
        with self.assertRaises(ValueError):
            cli.import_settings(self.source, self.destination)
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_failed_write_removes_incomplete_file_and_retry_can_import(self):
        self.write_source()
        with patch.object(cli.json, 'dump', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                cli.import_settings(self.source, self.destination)
        self.assertEqual(list(self.destination.iterdir()), [])
        self.assertEqual(cli.import_settings(self.source, self.destination), 2)

    @unittest.skipIf(os.name == 'nt', 'macOS launcher uses a POSIX lock')
    def test_second_launch_or_update_is_blocked_until_the_wizard_exits(self):
        script = ('import portal_cli as c; from pathlib import Path; '
                  'lock=c.session_lock(Path(__import__("sys").argv[1])); lock.__enter__()')
        with cli.session_lock(self.destination):
            result = subprocess.run([sys.executable, '-c', script, str(self.destination)],
                                    cwd=cli.ROOT, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Close the other Better Portal', result.stderr)
        with cli.session_lock(self.destination):
            pass

    def test_update_uses_brew_only_and_stops_if_refresh_fails(self):
        brew = self.root / 'brew'
        brew.touch()
        run = MagicMock(return_value=MagicMock(returncode=7))
        with patch.object(cli, 'NETWORK_LOCK', self.root / 'inactive'):
            self.assertEqual(cli.update({'brew': str(brew)}, run), 7)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], [str(brew), 'update'])
        self.assertEqual(run.call_args.kwargs['env']['HOMEBREW_NO_INSTALL_CLEANUP'], '1')
        run.reset_mock()
        run.side_effect = [MagicMock(returncode=0), MagicMock(returncode=9)]
        with patch.object(cli, 'NETWORK_LOCK', self.root / 'inactive'):
            self.assertEqual(cli.update({'brew': str(brew)}, run), 9)
        self.assertEqual(run.call_args.args[0], [str(brew), 'upgrade', '--fetch-HEAD', cli.FORMULA])

    def installed_update(self, *, current='b' * 40, prefix_result=0, missing=False):
        brew = self.root / 'brew'
        brew.touch()
        prefix = self.root / 'new keg'
        app = prefix / 'libexec' / 'app'
        app.mkdir(parents=True)
        if not missing:
            (app / 'installation.json').write_text(json.dumps({
                'version': 'HEAD-' + current[:12], 'revision': current,
                'changes_scope': 'update', 'previous_version': 'HEAD-' + 'a' * 12,
                'changes': ['Keep saved settings when upgrading'],
            }))
        run = MagicMock(side_effect=[MagicMock(returncode=0), MagicMock(returncode=0),
                                    MagicMock(returncode=prefix_result, stdout=str(prefix) + '\n')])
        info = {'version': 'HEAD-' + 'a' * 12, 'brew': str(brew),
                'formula': 'test/tap/better-portal', 'changes': ['Stale old notes']}
        return info, run

    def test_update_displays_new_installed_notes_and_uses_the_installed_tap(self):
        info, run = self.installed_update()
        output = io.StringIO()
        with patch.object(cli, 'NETWORK_LOCK', self.root / 'inactive'), redirect_stdout(output):
            self.assertEqual(cli.update(info, run), 0)
        self.assertIn('Updated: HEAD-aaaaaaaaaaaa -> HEAD-bbbbbbbbbbbb.', output.getvalue())
        self.assertIn('Keep saved settings when upgrading', output.getvalue())
        self.assertNotIn('Stale old notes', output.getvalue())
        self.assertEqual(run.call_args_list[1].args[0][-1], 'test/tap/better-portal')
        self.assertEqual(run.call_args.args[0], [info['brew'], '--prefix', 'test/tap/better-portal'])

    def test_no_op_update_still_displays_current_notes_without_claiming_a_new_version(self):
        info, run = self.installed_update(current='a' * 40)
        output = io.StringIO()
        with patch.object(cli, 'NETWORK_LOCK', self.root / 'inactive'), redirect_stdout(output):
            self.assertEqual(cli.update(info, run), 0)
        self.assertIn('Already up to date: HEAD-aaaaaaaaaaaa.', output.getvalue())
        self.assertIn('Keep saved settings when upgrading', output.getvalue())
        self.assertNotIn('Updated:', output.getvalue())

    def test_cannot_claim_success_when_brew_prefix_lookup_fails(self):
        info, run = self.installed_update(prefix_result=1)
        output = io.StringIO()
        with patch.object(cli, 'NETWORK_LOCK', self.root / 'inactive'), redirect_stdout(output):
            with self.assertRaisesRegex(RuntimeError, 'could not be verified'):
                cli.update(info, run)
        self.assertEqual(output.getvalue(), '')

    def test_cannot_claim_success_when_new_installation_metadata_is_missing(self):
        info, run = self.installed_update(missing=True)
        output = io.StringIO()
        with patch.object(cli, 'NETWORK_LOCK', self.root / 'inactive'), redirect_stdout(output):
            with self.assertRaisesRegex(RuntimeError, 'could not be verified'):
                cli.update(info, run)
        self.assertEqual(output.getvalue(), '')

    def test_changes_can_be_read_offline_without_a_session_lock(self):
        output = io.StringIO()
        with patch.object(cli.sys, 'platform', 'darwin'), \
                patch.object(cli.os, 'geteuid', return_value=501, create=True), \
                patch.object(cli, 'installation', return_value={'version': 'HEAD-example', 'changes': ['Saved notes']}), \
                patch.object(cli, 'data_directory', return_value=self.destination), \
                patch.object(cli, 'session_lock') as lock, \
                patch.object(cli.subprocess, 'run') as run, redirect_stdout(output):
            self.assertEqual(cli.main(['changes']), 0)
        self.assertIn('Saved notes', output.getvalue())
        lock.assert_not_called()
        run.assert_not_called()

    def test_change_notes_use_the_saved_language(self):
        (self.destination / 'tui-settings.json').write_text('{"language": "zh-CN"}')
        text = cli.changes_text({'version': 'HEAD-example', 'changes': ['Original English subject']},
                                cli.translator(self.destination))
        self.assertIn('更新内容', text)
        self.assertIn('Original English subject', text)

    def test_invalid_metadata_is_treated_as_missing(self):
        for content in ('[]', 'null', '{'):
            (self.destination / 'installation.json').write_text(content)
            self.assertEqual(cli.installation(self.destination), {})

    def test_notes_are_bound_to_the_built_revision_and_previous_install(self):
        (self.source / 'installation.json').write_text(json.dumps({'version': 'HEAD-' + 'a' * 12}))
        run = MagicMock(side_effect=[MagicMock(stdout='b' * 40 + '\n'), MagicMock(returncode=0),
                                    MagicMock(stdout='A new feature\nFix a connection error\n')])
        with patch.object(cli.subprocess, 'run', run):
            cli.write_installation(self.root, self.destination, self.source, '/brew', cli.FORMULA)
        info = cli.installation(self.destination)
        self.assertEqual(info['revision'], 'b' * 40)
        self.assertEqual(info['changes_scope'], 'update')
        self.assertEqual(info['changes'], ['A new feature', 'Fix a connection error'])
        self.assertEqual(run.call_args.args[0][-1], 'a' * 12 + '..' + 'b' * 40)
        self.assertIn('Since HEAD-aaaaaaaaaaaa:', (self.destination / 'changes.txt').read_text())

    def test_rewritten_history_is_explicitly_labeled_as_recent_changes(self):
        (self.source / 'installation.json').write_text(json.dumps({'version': 'HEAD-' + 'a' * 12}))
        run = MagicMock(side_effect=[MagicMock(stdout='b' * 40), MagicMock(returncode=1),
                                    MagicMock(stdout='\n'.join('Change ' + str(i) for i in range(11)))])
        with patch.object(cli.subprocess, 'run', run):
            cli.write_installation(self.root, self.destination, self.source, '/brew', cli.FORMULA)
        info = cli.installation(self.destination)
        self.assertEqual(info['changes_scope'], 'recent')
        self.assertTrue(info['changes_truncated'])
        self.assertEqual(len(info['changes']), 10)
        self.assertNotIn('Since ', cli.changes_text(info))
        self.assertEqual(run.call_args.args[0][-1], 'b' * 40)

    def test_active_recovery_prevents_brew_from_running(self):
        brew = self.root / 'brew'
        brew.touch()
        run = MagicMock()
        with patch.object(cli, 'NETWORK_LOCK', brew):
            with self.assertRaisesRegex(RuntimeError, 'recovery'):
                cli.update({'brew': str(brew)}, run)
        run.assert_not_called()

    def test_ctrl_c_keeps_waiting_for_the_wizards_restoration(self):
        child = MagicMock()
        child.__enter__.return_value = child
        child.wait.side_effect = [KeyboardInterrupt, 2]
        with patch.object(cli.subprocess, 'Popen', return_value=child):
            self.assertEqual(cli.run_wizard(['python', 'wizard']), 2)
        self.assertEqual(child.wait.call_count, 2)
        child.kill.assert_not_called()

    def test_launch_paths_are_explicit_and_demo_never_requests_sudo(self):
        @contextmanager
        def lock(_):
            yield
        with patch.object(cli, 'data_directory', return_value=self.destination), \
                patch.object(cli, 'session_lock', lock), \
                patch.object(cli.sys, 'platform', 'darwin'), \
                patch.object(cli.os, 'geteuid', return_value=501, create=True), \
                patch.object(cli, 'run_wizard', return_value=0) as run:
            self.assertEqual(cli.main(['--demo']), 0)
            arguments = run.call_args.args[0]
            self.assertNotIn('/usr/bin/sudo', arguments)
            self.assertIn('--demo', arguments)
            self.assertEqual(arguments[arguments.index('--data-dir') + 1], str(self.destination))
            self.assertEqual(cli.main([]), 0)
            self.assertEqual(run.call_args.args[0][0], sys.executable)
            self.assertEqual(run.call_args.args[0][1], str(cli.ROOT / 'portal_tui.py'))
            self.assertIn('--helper', run.call_args.args[0])
            self.assertNotIn('/usr/bin/sudo', run.call_args.args[0])

    def test_root_launch_never_runs_brew_or_creates_a_root_profile(self):
        with patch.object(cli.sys, 'platform', 'darwin'), \
                patch.object(cli.os, 'geteuid', return_value=0, create=True), \
                patch.object(cli, 'session_lock') as lock:
            self.assertEqual(cli.main(['update']), 2)
            lock.assert_not_called()

    def test_user_settings_are_independent_of_the_installation_directory(self):
        self.write_source()
        cli.import_settings(self.source, self.destination)
        # A second Homebrew keg can use the same user directory without moving it.
        screen, curses = MagicMock(), MagicMock()
        curses.has_colors.return_value = False
        with patch.object(tui, 'ROOT', self.source), patch.object(tui, 'default_interface', return_value='en0'):
            first = tui.Wizard(screen, curses, data_dir=self.destination, platform='darwin')
        with patch.object(tui, 'ROOT', self.root / 'new keg'), patch.object(tui, 'default_interface', return_value='en0'):
            second = tui.Wizard(screen, curses, data_dir=self.destination, platform='darwin')
        self.assertEqual(first.values, second.values)
        self.assertEqual((second.language, second.profile), ('zh-CN', '65'))
        self.assertEqual(second.config_path, self.destination / 'config.json')

    def test_absolute_recovery_command_works_from_any_folder(self):
        interpreter = self.root / 'Cellar/Better Portal/bin/python'
        script = self.root / 'Cellar/Better Portal/app/portal_capture.py'
        state = self.root / "state's folder/state.json"
        self.assertEqual(shlex.split(recovery_command(state, python=interpreter, script=script)),
                         ['sudo', str(interpreter), str(script), '--restore', str(state)])


@unittest.skipIf(os.name == 'nt', 'Mocked POSIX relay lifecycle')
class HomebrewRelayTests(relay_tests.RelayLifecycleTests):
    """Exercise the existing relay fault suite with reports outside the package."""
    def run_relay(self, callback=None):
        import portal_active_probe as probe
        return probe.run(True, finish_on_high_target=True, connect_timeout=tui.CONNECT_SECONDS,
                         confirmation_timeout=tui.CONFIRM_SECONDS, progress=callback or self.progress,
                         output_root=self.root / 'user data')

    def test_report_moves_to_user_data_but_watchdog_uses_installed_code(self):
        report = self.run_relay()
        self.assertEqual(Path(report['directory']).parent, self.root / 'user data' / 'experiments')
        self.assertEqual(self.spawn.call_args.args[0][1], str(self.root / 'portal_capture.py'))


if __name__ == '__main__':
    unittest.main()
