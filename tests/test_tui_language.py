"""Offline language selection, persistence, and CJK terminal layout checks."""
import json
import os
import stat
import string
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import portal_tui as tui
from portal_tui_text import ZH_CN, cell_width, clip_cells, pad_cells, translate, wrap_cells


class LanguageTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        root_patch = patch.object(tui, 'ROOT', self.root)
        route_patch = patch.object(tui, 'default_interface', return_value='en0')
        root_patch.start()
        route_patch.start()
        self.addCleanup(root_patch.stop)
        self.addCleanup(route_patch.stop)
        self.preferences = self.root / 'tui-settings.json'
        self.curses = SimpleNamespace(
            A_BOLD=1, A_DIM=2, A_REVERSE=4, error=RuntimeError,
            has_colors=lambda: False, curs_set=lambda _: None,
            KEY_UP=259, KEY_DOWN=258, KEY_LEFT=260, KEY_RIGHT=261,
            KEY_BTAB=353, KEY_ENTER=343, KEY_BACKSPACE=263, KEY_DC=330,
            KEY_HOME=262, KEY_END=360,
        )

    def wizard(self, *, demo=False, keys=()):
        screen = MagicMock()
        screen.getmaxyx.return_value = (24, 72)
        screen.getch.side_effect = keys
        return tui.Wizard(screen, self.curses, demo=demo)

    def save(self, value):
        self.preferences.write_text(json.dumps(value), encoding='utf-8')

    def test_first_choice_is_saved_before_device_setup_and_remembered_next_run(self):
        wizard = self.wizard(keys=[self.curses.KEY_DOWN, 13])
        wizard.prepare = MagicMock(return_value=False)
        self.assertEqual(wizard.run(), 0)
        self.assertEqual(wizard.language, 'zh-CN')
        self.assertEqual(tui.load_preferences(self.preferences), {'language': 'zh-CN'})
        self.assertFalse((self.root / 'config.json').exists())
        if os.name != 'nt':
            self.assertEqual(stat.S_IMODE(self.preferences.stat().st_mode), 0o600)
        returning = self.wizard()
        returning.choose_language = MagicMock(side_effect=AssertionError('Must remember language'))
        returning.prepare = MagicMock(return_value=False)
        self.assertEqual(returning.run(), 0)
        self.assertEqual(returning.language, 'zh-CN')

    def test_language_save_preserves_existing_profile_and_other_preferences(self):
        self.save({'profile': '100', 'future_setting': True})
        wizard = self.wizard(keys=[self.curses.KEY_RIGHT, 13])
        self.assertTrue(wizard.choose_language())
        self.assertEqual(wizard.profile, '100')
        self.assertEqual(tui.load_preferences(self.preferences),
                         {'language': 'zh-CN', 'profile': '100', 'future_setting': True})

    def test_form_save_preserves_language_and_config_schema(self):
        self.save({'language': 'zh-CN', 'profile': '65', 'future_setting': True})
        wizard = self.wizard(keys=[13] * 5)
        wizard.values = ['192.168.1.20', '192.168.1.30', 'en0']
        wizard.profile = '100'
        config = wizard.configure()
        self.assertEqual(set(config), {'interface', 'ps5_ip', 'portal_ip'})
        self.assertEqual(tui.load_preferences(self.preferences),
                         {'language': 'zh-CN', 'profile': '100', 'future_setting': True})

    def test_legacy_invalid_and_malformed_preferences_offer_language_selection(self):
        for raw in ('not JSON', '[]', 'null', '{"profile":"100"}',
                    '{"language":"unknown"}', '{"language":[],"profile":{}}'):
            with self.subTest(raw=raw):
                self.preferences.write_text(raw, encoding='utf-8')
                wizard = self.wizard()
                self.assertIsNone(wizard.language)
                self.assertEqual(wizard.profile, '100' if '100' in raw else '65')

    def test_cancel_first_choice_exits_without_writing_or_starting_setup(self):
        wizard = self.wizard(keys=[27])
        wizard.prepare = MagicMock(side_effect=AssertionError('Setup must not start'))
        self.assertEqual(wizard.run(), 0)
        self.assertFalse(self.preferences.exists())

    def test_prepare_language_shortcut_changes_saved_language_and_returns_to_prepare(self):
        self.save({'language': 'zh-CN', 'profile': '100'})
        wizard = self.wizard(keys=[ord('l'), self.curses.KEY_LEFT, 13, 27])
        self.assertFalse(wizard.prepare())
        self.assertEqual(wizard.language, 'en')
        self.assertEqual(tui.load_preferences(self.preferences), {'language': 'en', 'profile': '100'})

    def test_cancel_language_change_keeps_previous_choice(self):
        self.save({'language': 'en'})
        wizard = self.wizard(keys=[self.curses.KEY_DOWN, 27])
        self.assertFalse(wizard.choose_language())
        self.assertEqual(wizard.language, 'en')
        self.assertEqual(tui.load_preferences(self.preferences), {'language': 'en'})

    def test_failed_save_keeps_old_language_and_allows_cancel(self):
        self.save({'language': 'en', 'profile': '100'})
        wizard = self.wizard(keys=[self.curses.KEY_DOWN, 13, 27])
        with patch.object(Path, 'replace', side_effect=OSError('synthetic write failure')):
            self.assertFalse(wizard.choose_language())
        self.assertEqual(wizard.language, 'en')
        self.assertEqual(tui.load_preferences(self.preferences), {'language': 'en', 'profile': '100'})
        self.assertTrue(any('Cannot save' in call.args[2] for call in wizard.screen.addstr.call_args_list))
        self.assertEqual(list(self.root.iterdir()), [self.preferences])

    def test_demo_language_and_profile_changes_never_write_files(self):
        self.save({'language': 'en', 'profile': '100'})
        before = self.preferences.read_bytes()
        wizard = self.wizard(demo=True, keys=[self.curses.KEY_DOWN, 13] + [13] * 5)
        with patch.object(tui, 'save_private_json', side_effect=AssertionError('Demo must not write')):
            self.assertTrue(wizard.choose_language())
            wizard.profile = '65'
            self.assertIsNotNone(wizard.configure())
        self.assertEqual(wizard.language, 'zh-CN')
        self.assertEqual(self.preferences.read_bytes(), before)
        self.assertFalse((self.root / 'config.json').exists())

    def test_small_terminal_cannot_confirm_a_hidden_language_choice(self):
        wizard = self.wizard(keys=[13, 27])
        wizard.screen.getmaxyx.return_value = (18, 60)
        self.assertFalse(wizard.choose_language())
        self.assertFalse(self.preferences.exists())

    def test_chinese_inline_and_rainbow_use_display_cells(self):
        self.save({'language': 'zh-CN'})
        wizard = self.wizard()
        wizard.screen.addstr.reset_mock()
        wizard.inline(1, 4, ('Wait for ', 0), ('CONNECT NOW', 1), (' before connecting Portal.', 0))
        calls = wizard.screen.addstr.call_args_list
        self.assertEqual([call.args[1] for call in calls], [4, 9, 17])
        wizard.screen.addstr.reset_mock()
        wizard.rainbow(16, 9, '65 推荐')
        self.assertEqual([call.args[1] for call in wizard.screen.addstr.call_args_list], [9, 10, 11, 12, 14])

    def test_settings_apply_and_save_language_without_confirming_or_leaving_the_panel(self):
        self.save({'language': 'en', 'profile': '100'})
        wizard = self.wizard()
        self.assertTrue(wizard.settings_key(ord('S')))
        self.assertTrue(wizard.settings_key(self.curses.KEY_RIGHT))
        self.assertTrue(wizard.settings_open)
        self.assertEqual(wizard.language, 'zh-CN')
        self.assertEqual(tui.load_preferences(self.preferences), {'language': 'zh-CN', 'profile': '100'})
        wizard.refresh()
        self.assertTrue(any(call.args[2] == '设置' for call in wizard.screen.addstr.call_args_list))
        wizard.settings_key(27)
        self.assertFalse(wizard.settings_open)
        self.assertEqual(self.wizard().language, 'zh-CN', 'Esc closes settings without undoing saved changes')

    def test_settings_preserve_unsaved_form_values_profile_and_input_position(self):
        self.save({'language': 'en', 'profile': '65'})
        wizard = self.wizard(keys=[ord('s'), self.curses.KEY_RIGHT, 13, 27])
        values = ['192.168.1.', '192.168.1.30', 'en4']
        wizard.values = values.copy()
        wizard.profile = '100'
        self.assertIsNone(wizard.configure())
        self.assertEqual(wizard.values, values)
        self.assertEqual((wizard.focus, wizard.cursor, wizard.selected), (0, len(values[0]), True))
        self.assertEqual(wizard.profile, '100')
        self.assertFalse((self.root / 'config.json').exists())
        self.assertEqual(tui.load_preferences(self.preferences), {'language': 'zh-CN', 'profile': '65'})

    def test_live_settings_keep_processing_events_and_do_not_reset_the_countdown(self):
        self.save({'language': 'en'})
        wizard = self.wizard(keys=[ord('s'), self.curses.KEY_RIGHT, -1, 27])
        with patch.object(wizard, 'choose_language', side_effect=AssertionError('No blocking picker in a relay')):
            self.assertTrue(wizard.progress({'type': 'ready', 'seconds': 120}))
            started = wizard.phase_started
            self.assertTrue(wizard.progress({'type': 'tick', 'phase': 'waiting', 'seconds': 119}))
            self.assertEqual(wizard.language, 'zh-CN')
            self.assertTrue(wizard.settings_open)
            self.assertTrue(wizard.progress({'type': 'tick', 'phase': 'waiting', 'seconds': 118}))
            self.assertEqual(wizard.event['seconds'], 118)
            self.assertEqual(wizard.phase_started, started)
            self.assertTrue(wizard.progress({'type': 'modified'}))
        self.assertFalse(wizard.settings_open)
        self.assertEqual(wizard.event['phase'], 'confirming')
        self.assertEqual(wizard.event['seconds'], tui.CONFIRM_SECONDS)
        self.assertEqual(wizard.screen.getch.call_count, 4, 'Each event must read at most one key')

    def test_live_cancel_keys_still_cancel_with_settings_open(self):
        for key in (ord('q'), ord('Q'), 3):
            with self.subTest(key=key):
                wizard = self.wizard(demo=True, keys=[ord('s'), key])
                self.assertTrue(wizard.progress({'type': 'ready', 'seconds': 120}))
                self.assertFalse(wizard.progress({'type': 'tick', 'phase': 'waiting', 'seconds': 119}))
                self.assertFalse(wizard.settings_open)

    def test_recovery_dismisses_settings_without_consuming_recovery_keys(self):
        for phase in ('restoring', 'stopping'):
            with self.subTest(phase=phase):
                wizard = self.wizard(demo=True, keys=[ord('s')])
                wizard.progress({'type': 'ready', 'seconds': 120})
                self.assertTrue(wizard.progress({'type': phase}))
                self.assertFalse(wizard.settings_open)
                self.assertEqual(wizard.screen.getch.call_count, 1)

    def test_result_and_details_support_settings_without_retrying_the_attempt(self):
        self.save({'language': 'en'})
        wizard = self.wizard(keys=[ord('s'), self.curses.KEY_RIGHT, 13, ord('d'),
                                   ord('S'), self.curses.KEY_LEFT, 27, 27, ord('q')])
        self.assertFalse(wizard.result({'completed': True, 'unique_mutated_sequences': 0}))
        self.assertFalse(wizard.settings_open)
        self.assertEqual(wizard.language, 'en')
        self.assertEqual(tui.load_preferences(self.preferences), {'language': 'en'})

    def test_failed_settings_save_preserves_language_and_can_be_retried(self):
        self.save({'language': 'en', 'profile': '100'})
        wizard = self.wizard()
        wizard.settings_key(ord('s'))
        with patch.object(Path, 'replace', side_effect=OSError('synthetic write failure')):
            wizard.settings_key(self.curses.KEY_RIGHT)
        self.assertEqual(wizard.language, 'en')
        self.assertIn('synthetic write failure', wizard.settings_error)
        self.assertEqual(tui.load_preferences(self.preferences), {'language': 'en', 'profile': '100'})
        wizard.refresh()
        self.assertTrue(any('Language unchanged' in call.args[2] for call in wizard.screen.addstr.call_args_list))
        wizard.settings_key(self.curses.KEY_RIGHT)
        self.assertEqual(wizard.language, 'zh-CN')
        self.assertEqual(wizard.settings_error, '')
        self.assertEqual(list(self.root.iterdir()), [self.preferences])

    def test_settings_preview_is_readonly_and_hidden_settings_cannot_change_language(self):
        self.save({'language': 'en'})
        before = self.preferences.read_bytes()
        wizard = self.wizard(demo=True)
        with patch.object(tui, 'save_private_json', side_effect=AssertionError('Demo must not write')):
            wizard.settings_key(ord('s'))
            wizard.settings_key(self.curses.KEY_RIGHT)
            self.assertEqual(wizard.language, 'zh-CN')
            wizard.screen.getmaxyx.return_value = (18, 50)
            wizard.settings_key(self.curses.KEY_LEFT)
            self.assertEqual(wizard.language, 'zh-CN')
            wizard.small_terminal(live=True)
            self.assertFalse(wizard.settings_open)
            wizard.settings_key(ord('s'))
            self.assertFalse(wizard.settings_open)
        self.assertEqual(self.preferences.read_bytes(), before)


class TerminalTextTests(unittest.TestCase):
    def test_clip_and_padding_never_split_a_wide_character(self):
        self.assertEqual(cell_width('65 推荐'), 7)
        self.assertEqual(cell_width('e\u0301'), 1)
        self.assertEqual(clip_cells('PS5 连接', 7), 'PS5 连')
        self.assertEqual(clip_cells('e\u0301中文', 2), 'e\u0301')
        self.assertEqual(pad_cells('检查', 13, center=True), '    检查     ')
        self.assertEqual(cell_width(pad_cells('输入 IPv4 地址', 24)), 24)

    def test_mixed_paragraphs_fit_without_losing_text_or_breaking_short_latin_words(self):
        text = 'PS5 已确认更高的目标码率，直接连接已恢复。保持 Portal 连接。'
        lines = wrap_cells(text, 20)
        self.assertTrue(all(cell_width(line) <= 20 for line in lines))
        self.assertEqual(''.join(lines).replace(' ', ''), text.replace(' ', ''))
        self.assertTrue(any('Portal' in line for line in lines))
        path = '报告：/a-very-long-example-folder/' * 4
        self.assertEqual(''.join(wrap_cells(path, 20)), path)
        with self.assertRaises(ValueError):
            wrap_cells('中文', 1)

    def test_localized_templates_keep_the_same_format_fields_and_raw_diagnostics(self):
        def fields(text):
            return {field for _, field, _, _ in string.Formatter().parse(text) if field is not None}
        for source, localized in ZH_CN.items():
            with self.subTest(source=source):
                self.assertEqual(fields(source), fields(localized))
        self.assertEqual(translate('PS5-reported target: {target:.3f} Mbps', 'zh-CN', target=63.106),
                         'PS5 报告的目标码率：63.106 Mbps')
        diagnostic = 'Unknown driver failure: interface en4'
        self.assertEqual(translate(diagnostic, 'zh-CN'), diagnostic)
        self.assertEqual(translate('Ready to play', 'en'), 'Ready to play')


if __name__ == '__main__':
    unittest.main()
