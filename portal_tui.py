#!/usr/bin/env python3
"""Guided macOS launcher. Demo mode never changes configuration or networking."""
import argparse
import ipaddress
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from portal_tui_text import LANGUAGE_NAMES, LANGUAGES, cell_width, clip_cells, pad_cells, translate, wrap_cells

ROOT = Path(__file__).resolve().parent
CONNECT_SECONDS = 120
CONFIRM_SECONDS = 15
PROFILES = ('65', '100', '200')
LANGUAGE_COLUMNS = 3


def default_interface():
    try:
        route = subprocess.check_output(
            ['/sbin/route', '-n', 'get', 'default'], text=True,
            stderr=subprocess.DEVNULL, timeout=2)
        match = re.search(r'interface:\s+(en[0-9]+)\b', route)
        if match:
            return match[1]
    except (OSError, subprocess.SubprocessError):
        pass
    return ''


def load_config(path):
    """Pre-fill real enrollment, but leave documentation placeholders blank."""
    try:
        saved = json.loads(path.read_text())
        if not isinstance(saved, dict):
            return {}
    except (OSError, ValueError):
        return {}
    values = {'interface': str(saved.get('interface', ''))}
    for key in ('ps5_ip', 'portal_ip'):
        value = str(saved.get(key, ''))
        try:
            address = ipaddress.IPv4Address(value)
            if address in ipaddress.IPv4Network('192.0.2.0/24'):
                value = ''
        except ValueError:
            value = ''
        values[key] = value
    return values


def validate_form(values):
    config = {key: values[key].strip()
              for key in ('interface', 'ps5_ip', 'portal_ip')}
    for key, label in (('ps5_ip', 'PS5'), ('portal_ip', 'Portal')):
        try:
            address = ipaddress.IPv4Address(config[key])
        except ValueError:
            raise ValueError(f'Enter a valid {label} IPv4 address, such as 192.168.1.20') from None
        if (address.is_multicast or address.is_loopback or address.is_unspecified
                or address.is_reserved or int(address) == 0xffffffff):
            raise ValueError(f'Use the {label} IPv4 address shown by your router')
    if config['ps5_ip'] == config['portal_ip']:
        raise ValueError('PS5 and Portal must have different IPv4 addresses')
    if not re.fullmatch(r'en[0-9]+', config['interface']):
        raise ValueError('Select a Mac LAN interface such as en0 or en4')
    return config


def save_private_json(path, value):
    """Replace atomically and leave sudo-created settings owned by the caller."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent,
                                         prefix='.' + path.name + '-', delete=False) as stream:
            temporary = Path(stream.name)
            os.chmod(temporary, 0o600)
            json.dump(value, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        if os.name == 'posix' and os.geteuid() == 0 and 'SUDO_UID' in os.environ:
            os.chown(temporary, int(os.environ['SUDO_UID']), int(os.environ['SUDO_GID']))
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_preferences(path):
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


@dataclass
class Result:
    kind: str
    title: str
    message: str
    advice: str
    target: float | None = None


def summarize(report):
    if report.get('restoration_errors'):
        return Result('error', 'Network recovery needs attention',
                      'The direct path could not be fully restored.',
                      'Keep this Mac awake for automatic recovery. Reconnect Portal if needed. '
                      'Press D for recovery details. Start another attempt only after recovery.')
    if not report.get('completed'):
        message = report.get('run_error') or 'The attempt was stopped.'
        title = 'Attempt stopped' if message == 'Cancelled by user' else 'Could not finish'
        return Result('warning', title, message,
                      ('No network mappings were changed. Keep both devices awake on the same LAN. '
                       'Check the addresses and LAN adapter, then try again.'
                       if report.get('preflight_failed') else
                       'Network restoration completed. You can try again or quit.'))
    if not report.get('unique_mutated_sequences'):
        forwarded = sum(report.get('counts', {}).get(key, 0)
                        for key in ('forwarded_in', 'forwarded_out'))
        title = 'No compatible startup captured' if forwarded else 'No new connection detected'
        return Result('warning', title, 'The connection request was not modified.',
                      'Disconnect Portal from PS5. Try again, wait for CONNECT NOW, '
                      'then start a fresh Portal connection before the countdown ends.')
    targets = [event.get('target_bitrate_raw') for event in report.get('ps5_messages', [])
               if event.get('type') == 'CONNECTIONQUALITY']
    target = next((value / 1e6 for value in reversed(targets)
                   if isinstance(value, (int, float))), None)
    witness = report.get('egress_witness') or {}
    if report.get('high_target_confirmed') and witness.get('all_expected_observed'):
        return Result('success', 'Bitrate target confirmed',
                      'PS5 reported the higher target. Playback has not been verified.',
                      'Check picture, sound and controls on Portal. If blank, reconnect normally. '
                      'Run the wizard again for each new connection.', target)
    if report.get('high_target_confirmed'):
        return Result('warning', 'Target reported; verification incomplete',
                      'PS5 reported the higher target, but local packet verification was incomplete.',
                      'Direct-path restoration completed. Check the report before retrying.', target)
    return Result('warning', 'Higher target not confirmed',
                  'A startup request was modified, but three high target reports were not observed.',
                  'Direct-path restoration completed. Reconnect normally, or retry with 65 Mbps.', target)


class Wizard:
    """Single-threaded curses UI; the relay callback keeps the countdown live."""
    MIN_ROWS = 24
    MIN_COLS = 72

    def __init__(self, screen, curses, demo=False, animations=True, helper=False):
        self.screen, self.curses, self.demo = screen, curses, demo
        self.animations = animations
        self.helper = helper
        data_root = ROOT
        if helper:
            from portal_macos_client import user_directory
            data_root = user_directory()
            if not demo:
                data_root.mkdir(parents=True, mode=0o700, exist_ok=True)
        self.config_path = data_root / 'config.json'
        self.preferences_path = data_root / 'tui-settings.json'
        saved = load_config(self.config_path)
        self.values = [saved.get('ps5_ip', ''), saved.get('portal_ip', ''),
                       saved.get('interface') or default_interface()]
        if demo:
            self.values = ['192.168.1.20', '192.168.1.30', 'en0']
        preferences = load_preferences(self.preferences_path)
        profile = preferences.get('profile', '65')
        self.profile = profile if profile in PROFILES else '65'
        language = preferences.get('language')
        self.language = language if language in LANGUAGES else None
        self.settings_open = False
        self.settings_error = ''
        self.focus = 0
        self.cursor = 0
        self.selected = True
        self.error = ''
        self.event = {'phase': 'checking', 'seconds': CONNECT_SECONDS}
        self.phase_started = time.monotonic()
        self.report = None
        self.notice = ''
        self.colors = {}
        self.rainbow_colors = []
        self.cursor_mode = None
        self.screen.keypad(True)
        self.screen.timeout(100)
        if curses.has_colors():
            curses.start_color()
            try:
                curses.use_default_colors()
                background = -1
            except curses.error:
                background = curses.COLOR_BLACK
            for number, (name, color) in enumerate(
                    [('accent', curses.COLOR_CYAN), ('success', curses.COLOR_GREEN),
                     ('warning', curses.COLOR_YELLOW), ('error', curses.COLOR_RED),
                     ('blue', curses.COLOR_BLUE), ('magenta', curses.COLOR_MAGENTA)], 1):
                curses.init_pair(number, color, background)
                self.colors[name] = curses.color_pair(number)
            # Bright steps around the 256-color cube keep the sweep readable.
            palette = (203, 209, 215, 221, 227, 191, 155, 119,
                       83, 84, 85, 86, 87, 81, 75, 69,
                       63, 99, 135, 171, 207, 206, 205, 204)
            if curses.COLORS >= 256 and curses.COLOR_PAIRS > len(self.colors) + len(palette):
                for number, color in enumerate(palette, len(self.colors) + 1):
                    curses.init_pair(number, color, background)
                    self.rainbow_colors.append(curses.color_pair(number) | curses.A_BOLD)
        if not self.rainbow_colors:
            self.rainbow_colors = [self.emphasis(name) for name in
                                   ('error', 'warning', 'success', 'accent', 'blue', 'magenta')]
        self.hide_cursor()

    def t(self, text, **values):
        return translate(text, self.language, **values)

    def save_preferences(self, **changes):
        if not self.demo:
            preferences = load_preferences(self.preferences_path)
            preferences.update(changes)
            save_private_json(self.preferences_path, preferences)

    def choose_language(self):
        """Ask before setup; an existing selection can be changed from Prepare."""
        selected = LANGUAGES.index(self.language) if self.language in LANGUAGES else 0
        error = ''
        while True:
            self.screen.erase()
            self.hide_cursor()
            rows, columns = self.screen.getmaxyx()
            full_size = rows >= self.MIN_ROWS and columns >= self.MIN_COLS
            if full_size:
                language = LANGUAGES[selected]

                def put(row, text, style=0):
                    self.put(row, 4, text, style, language=language)

                put(1, 'BETTER PORTAL', self.emphasis())
                put(2, 'Language', self.curses.A_DIM)
                put(5, '-' * min(82, columns - 8), self.curses.A_DIM)
                put(7, 'Choose your language', self.curses.A_BOLD)
                for index, name in enumerate(LANGUAGE_NAMES.values()):
                    style = self.emphasis() | self.curses.A_REVERSE if selected == index else 0
                    put(9 + index, f' {">" if selected == index else " "} [{"x" if selected == index else " "}] {name} ', style)
                if error:
                    message = translate('Could not save settings: {error}', language, error=error)
                    for row, line in enumerate(wrap_cells(message, columns - 8)[:2], 16):
                        put(row, line, self.colors.get('error', 0))
                else:
                    put(16, 'DEMO: language is not saved.' if self.demo else
                        'Remembered for next time.', self.curses.A_DIM)
                put(rows - 5, ' ' + translate('Continue ->', language) + ' ',
                    self.emphasis() | self.curses.A_REVERSE)
                put(rows - 3, '-' * min(82, columns - 8), self.curses.A_DIM)
                put(rows - 2, '↑/↓: select    Enter: confirm    Esc: back', self.curses.A_DIM)
                self.screen.refresh()
            else:
                self.small_terminal()
            key = self.screen.getch()
            if key in (27, ord('q'), ord('Q')):
                return False
            if not full_size:
                continue
            if key in (self.curses.KEY_DOWN, self.curses.KEY_RIGHT, 9, 32):
                selected = (selected + 1) % len(LANGUAGES)
            elif key in (self.curses.KEY_UP, self.curses.KEY_LEFT, self.curses.KEY_BTAB):
                selected = (selected - 1) % len(LANGUAGES)
            elif key in (10, 13, self.curses.KEY_ENTER):
                language = LANGUAGES[selected]
                try:
                    self.save_preferences(language=language)
                except OSError as exc:
                    error = str(exc)
                    continue
                self.language = language
                return True

    def settings_key(self, key, *, live=False):
        """Handle one key without nesting a loop inside the relay callback."""
        rows, columns = self.screen.getmaxyx()
        full_size = rows >= self.MIN_ROWS and columns >= self.MIN_COLS
        if key in (ord('s'), ord('S')):
            if self.settings_open or full_size:
                self.settings_open = not self.settings_open
                self.settings_error = ''
            return True
        if not self.settings_open:
            return False
        if key in (27, 10, 13, self.curses.KEY_ENTER):
            self.settings_open = False
        elif live and key in (3, ord('q'), ord('Q')):
            self.settings_open = False
            return False
        elif full_size and key in (self.curses.KEY_LEFT, self.curses.KEY_RIGHT,
                                   self.curses.KEY_UP, self.curses.KEY_DOWN,
                                   self.curses.KEY_BTAB, 9, 32):
            current = LANGUAGES.index(self.language) if self.language in LANGUAGES else 0
            direction = {self.curses.KEY_LEFT: -1, self.curses.KEY_BTAB: -1,
                         self.curses.KEY_UP: -LANGUAGE_COLUMNS,
                         self.curses.KEY_DOWN: LANGUAGE_COLUMNS}.get(key, 1)
            language = LANGUAGES[(current + direction) % len(LANGUAGES)]
            try:
                self.save_preferences(language=language)
            except OSError as exc:
                self.settings_error = str(exc)
            else:
                self.language = language
                self.settings_error = ''
        return True

    def refresh(self, *, live=False):
        """Paint settings over the current page while preserving its state."""
        rows, columns = self.screen.getmaxyx()
        if self.settings_open and rows >= self.MIN_ROWS and columns >= self.MIN_COLS:
            self.hide_cursor()
            width = min(64, columns - 8)
            left = (columns - width) // 2
            for row in range(9, 17):
                line = '+' + '-' * (width - 2) + '+' if row in (9, 16) else '|' + ' ' * (width - 2) + '|'
                self.put(row, left, line, self.colors.get('accent', 0))
            self.inline(10, left + 3, ('Settings', self.emphasis()),
                        (' / ', self.curses.A_DIM), ('Language', self.curses.A_BOLD))
            cell = (width - 6) // LANGUAGE_COLUMNS
            for index, (language, name) in enumerate(LANGUAGE_NAMES.items()):
                selected = self.language == language
                label = f' [{"x" if selected else " "}] {name} '
                style = self.emphasis() | self.curses.A_REVERSE if selected else 0
                row = 12 + index // LANGUAGE_COLUMNS
                column = left + 3 + (index % LANGUAGE_COLUMNS) * cell
                self.put(row, column, label, style)
            if self.settings_error:
                message = self.t('Could not save settings: {error}', error=self.settings_error)
                self.put(14, left + 3, clip_cells(message, width - 6), self.colors.get('error', 0))
                self.put(15, left + 3, 'Language unchanged. Try again.', self.curses.A_DIM)
            else:
                self.put(15, left + 3, 'Applies immediately; saved for next time.' if not self.demo
                         else 'Applies immediately. Demo changes are not saved.', self.curses.A_DIM)
            footer = ('←/→: language  Esc/S: back  Q/Ctrl+C: stop' if live else
                      '←/→: language    Enter / Esc / S: back')
            self.put(rows - 2, 4, ' ' * (columns - 5))
            self.put(rows - 2, 4, footer, self.curses.A_DIM)
        self.screen.refresh()

    def hide_cursor(self):
        self.set_cursor(0)

    def set_cursor(self, mode):
        if self.cursor_mode == mode:
            return
        try:
            self.curses.curs_set(mode)
            self.cursor_mode = mode
        except self.curses.error:
            pass

    def put(self, row, column, text, style=0, *, language=None):
        """Translate source copy and clip it by terminal cells, never by bytes."""
        rows, columns = self.screen.getmaxyx()
        if row < 0 or column < 0 or row >= rows or column >= columns - 1:
            return
        try:
            text = translate(str(text), self.language if language is None else language)
            self.screen.addstr(row, column, clip_cells(text, columns - column - 1), style)
        except self.curses.error:
            pass

    def paragraph(self, row, text, style=0, column=4, max_rows=None):
        width = min(86, self.screen.getmaxyx()[1] - 4) - column
        lines = wrap_cells(self.t(text), width=max(10, width))
        if max_rows is not None and len(lines) > max_rows:
            lines = lines[:max_rows]
            lines[-1] = clip_cells(lines[-1], max(0, width - 3)).rstrip() + '...'
        for line in lines:
            self.put(row, column, line, style)
            row += 1
        return row

    def emphasis(self, color='accent'):
        return self.colors.get(color, 0) | self.curses.A_BOLD

    def inline(self, row, column, *spans):
        for text, style in spans:
            text = self.t(text)
            self.put(row, column, text, style)
            column += cell_width(text)

    def rainbow(self, row, column, text):
        """Let color flow through stationary text on the existing redraw clock."""
        count = len(self.rainbow_colors)
        phase = int(time.monotonic() * count / 4) if self.animations else 0
        for index, character in enumerate(text):
            color = (index * count // len(text) - phase) % count
            self.put(row, column, character, self.rainbow_colors[color])
            column += cell_width(character)

    def transition_line(self, row, color, elapsed, direction='forward'):
        """One brief sweep marks a state change; the new state is readable at once."""
        width = min(82, self.screen.getmaxyx()[1] - 8)
        fraction = min(1, max(0, elapsed) / .7) if self.animations else 1
        self.put(row, 4, '-' * width, self.curses.A_DIM)
        if direction == 'inward':
            length = max(1, round(width / 2 * fraction))
            self.put(row, 4, '-' * length, color)
            self.put(row, 4 + width - length, '-' * length, color)
        elif direction == 'outward':
            length = max(1, round(width * fraction))
            self.put(row, 4 + (width - length) // 2, '-' * length, color)
        else:
            self.put(row, 4, '-' * max(1, round(width * fraction)), color)

    def badge(self, row, label, title, color):
        self.inline(row, 4, (f' {self.t(label)} ', self.emphasis(color) | self.curses.A_REVERSE),
                    ('  ' + self.t(title), self.emphasis(color)))

    def frame(self, step, footer):
        self.screen.erase()
        if step != 1:
            self.hide_cursor()
        rows, columns = self.screen.getmaxyx()
        self.put(1, 4, 'PS5 PORTAL', self.colors.get('accent', 0) | self.curses.A_BOLD)
        if step != 2 or self.event.get('phase') not in ('restoring', 'stopping'):
            hint = self.t('S Settings')
            self.put(1, min(86, columns - 4) - cell_width(hint), hint, self.curses.A_DIM)
        self.put(2, 4, self.t('High Bitrate  /  Guided setup') +
                 (self.t('  /  DEMO: no network changes') if self.demo else ''),
                 self.curses.A_DIM)
        column = 4
        for index, label in enumerate(('1 Prepare', '2 Devices', '3 Connect', '4 Result')):
            label = self.t(label)
            style = self.curses.A_BOLD | self.colors.get('accent', 0) if index == step else self.curses.A_DIM
            self.put(4, column, label, style)
            column += cell_width(label) + 5
        self.put(5, 4, '-' * min(82, columns - 8), self.curses.A_DIM)
        self.put(rows - 3, 4, '-' * min(82, columns - 8), self.curses.A_DIM)
        self.put(rows - 2, 4, footer, self.curses.A_DIM)
        return rows >= self.MIN_ROWS and columns >= self.MIN_COLS

    def small_terminal(self, live=False):
        self.settings_open = False
        self.screen.erase()
        self.hide_cursor()
        self.put(1, 1, 'Please enlarge this terminal to at least 72 x 24.')
        if live:
            stage_label = {'checking': 'CHECK', 'preparing': 'WAIT', 'waiting': 'CONNECT',
                           'confirming': 'VERIFY', 'restoring': 'RESTORE', 'stopping': 'STOPPING'}
            self.put(3, 1, self.t('{phase}: {seconds}s remaining',
                     phase=self.t(stage_label.get(self.event.get('phase'), 'CHECK')),
                     seconds=self.event.get('seconds', 0)))
            self.put(5, 1, 'Q or Esc stops safely and restores the network.')
        else:
            self.put(3, 1, 'Esc exits. Setup resumes when the window is larger.')
        self.screen.refresh()

    def button(self, row, text, active=True):
        style = self.curses.A_BOLD | self.colors.get('accent', 0)
        if active:
            style |= self.curses.A_REVERSE
        self.put(row, 4, '  ' + self.t(text) + '  ', style)

    def prepare(self):
        highlight = self.emphasis('warning')
        while True:
            if self.frame(0, 'Enter: continue    Esc: quit'):
                self.put(7, 4, 'Before you begin', self.curses.A_BOLD)
                self.inline(9, 4, ('1. ', self.curses.A_DIM),
                            ('SAME NETWORK', highlight),
                            ('  /  Mac + PS5 + Portal', 0))
                self.put(10, 7, 'Use the main LAN; avoid guest Wi-Fi and VPN routes.', self.curses.A_DIM)
                self.inline(12, 4, ('2. ', self.curses.A_DIM),
                            ('DISCONNECT PORTAL', highlight),
                            ('  /  keep ', 0), ('PS5 powered on', highlight))
                self.inline(13, 7, ('On Portal: ', self.curses.A_DIM),
                            ('Quick Menu -> Disconnect', highlight))
                self.inline(15, 4, ('Keep this ', 0), ('Mac awake', highlight),
                            (' until restoration finishes.', 0))
                self.inline(17, 4, ('Wait for ', 0), ('CONNECT NOW', highlight),
                            (' before connecting Portal.', 0))
                self.button(self.screen.getmaxyx()[0] - 5, 'I have checked these steps  ->')
                self.refresh()
            else:
                self.small_terminal()
            key = self.screen.getch()
            if self.settings_key(key):
                continue
            if key in (27, ord('q'), ord('Q')):
                return False
            if key in (ord('l'), ord('L')):
                self.choose_language()
            if key in (10, 13, self.curses.KEY_ENTER) and self.screen.getmaxyx()[0] >= self.MIN_ROWS and self.screen.getmaxyx()[1] >= self.MIN_COLS:
                return True

    def form_values(self):
        return dict(zip(('ps5_ip', 'portal_ip', 'interface'), self.values))

    def change_focus(self, direction):
        self.focus = (self.focus + direction) % 5
        self.selected = True
        self.cursor = len(self.values[self.focus]) if self.focus < 3 else 0

    def draw_form(self):
        if not self.frame(1, 'Tab: next field    Enter: next / start    Esc: back'):
            self.small_terminal()
            return False
        self.put(7, 4, 'Your devices', self.curses.A_BOLD)
        self.put(8, 4, 'Edit the fields below, then choose your bitrate.', self.curses.A_DIM)
        for index, label in enumerate(('PS5 IPv4 address', 'Portal IPv4 address', 'Mac LAN interface')):
            row = 10 + index * 2
            focused = self.focus == index
            self.put(row, 2, '>' if focused else ' ', self.emphasis())
            self.put(row, 4, label, self.curses.A_BOLD if focused else 0)
            style = self.emphasis()
            if focused:
                style |= self.curses.A_REVERSE
            value = self.values[index] or self.t('Enter interface' if index == 2 else 'Enter IPv4 address')
            self.put(row, 27, '[ ' + pad_cells(value, 24) + ' ]', style)
            if focused:
                self.put(row, 57, 'type here', self.emphasis())
        self.put(16, 2, '>' if self.focus == 3 else ' ', self.emphasis())
        self.put(15, 4, 'Bitrate (Mbps)', self.curses.A_BOLD if self.focus == 3 else 0)
        column = 4
        for profile in PROFILES:
            label = f' [{"x" if profile == self.profile else " "}] {profile} '
            if profile == '65':
                label += self.t('recommended') + ' '
            style = self.emphasis() if profile == self.profile else 0
            if profile == self.profile and self.focus == 3 and profile != '65':
                style |= self.curses.A_REVERSE
            self.put(16, column, label, style)
            if profile == '65':
                self.rainbow(16, column + 5, '65 ' + self.t('recommended'))
                if self.profile == '65' and self.focus == 3:
                    self.put(16, column + 1, '[x]', self.emphasis() | self.curses.A_REVERSE)
            column += cell_width(label) + 1
        self.put(16, column, 'use arrow to choose',
                 self.emphasis() if self.focus == 3 else self.curses.A_DIM)
        if self.error:
            self.paragraph(18, self.error, self.colors.get('error', 0), max_rows=2)
        elif self.focus < 2:
            self.put(18, 4, 'Type to replace; arrows to edit. Find IPs in your router list.', self.curses.A_DIM)
        elif self.focus == 2:
            self.put(18, 4, 'Use the adapter on the PS5 / Portal LAN. Wi-Fi is often en0.', self.curses.A_DIM)
        else:
            self.put(18, 4, {'65': '65 Mbps is recommended for your first attempt.',
                             '100': 'Try 100 Mbps after a stable 65 Mbps session.',
                             '200': '200 Mbps is experimental and may increase stutter.'}[self.profile],
                     self.colors.get('warning', 0) if self.profile == '200' else self.curses.A_DIM)
        self.button(self.screen.getmaxyx()[0] - 4, 'Save and prepare connection  ->', self.focus == 4)
        if self.focus < 3:
            try:
                self.set_cursor(1)
                self.screen.move(10 + self.focus * 2, 29 + min(self.cursor, 23))
            except self.curses.error:
                pass
        else:
            self.hide_cursor()
        self.refresh()
        return True

    def configure(self):
        self.error = ''
        self.focus = 0
        self.selected = True
        self.cursor = len(self.values[self.focus]) if self.focus < 3 else 0
        while True:
            full_size = self.draw_form()
            key = self.screen.getch()
            if self.settings_key(key):
                continue
            if key == 27:
                return None
            if not full_size:
                continue
            if key in (9, self.curses.KEY_DOWN):
                self.change_focus(1)
            elif key in (self.curses.KEY_BTAB, self.curses.KEY_UP):
                self.change_focus(-1)
            elif key in (10, 13, self.curses.KEY_ENTER):
                if self.focus != 4:
                    self.change_focus(1)
                    continue
                try:
                    config = validate_form(self.form_values())
                    if not self.demo:
                        save_private_json(self.config_path, config)
                        self.save_preferences(profile=self.profile)
                    self.values = [config['ps5_ip'], config['portal_ip'], config['interface']]
                    return config
                except ValueError as exc:
                    self.error = str(exc)
                    self.focus = 1 if 'Portal' in self.error else (0 if 'PS5' in self.error else 2)
                    self.cursor = len(self.values[self.focus])
                    self.selected = True
                except OSError as exc:
                    self.error = self.t('Could not save settings: {error}', error=str(exc))
            elif self.focus == 3 and key in (self.curses.KEY_LEFT, self.curses.KEY_RIGHT, 32):
                direction = -1 if key == self.curses.KEY_LEFT else 1
                self.profile = PROFILES[(PROFILES.index(self.profile) + direction) % len(PROFILES)]
            elif self.focus < 3:
                value = self.values[self.focus]
                if key in (self.curses.KEY_BACKSPACE, 127, 8):
                    if self.selected:
                        value, self.cursor = '', 0
                    elif self.cursor:
                        value = value[:self.cursor - 1] + value[self.cursor:]
                        self.cursor -= 1
                elif key == self.curses.KEY_DC:
                    value = '' if self.selected else value[:self.cursor] + value[self.cursor + 1:]
                elif key in (self.curses.KEY_HOME, 1):
                    self.cursor = 0
                elif key in (self.curses.KEY_END, 5):
                    self.cursor = len(value)
                elif key == self.curses.KEY_LEFT:
                    self.cursor = max(0, self.cursor - 1)
                elif key == self.curses.KEY_RIGHT:
                    self.cursor = min(len(value), self.cursor + 1)
                elif 32 <= key <= 126:
                    if self.selected:
                        value, self.cursor = '', 0
                    if len(value) < 24:
                        value = value[:self.cursor] + chr(key) + value[self.cursor:]
                        self.cursor += 1
                else:
                    continue
                self.selected = False
                self.values[self.focus] = value
                self.error = ''

    def connection_stage(self):
        """Describe the latest relay evidence; elapsed time cannot establish a link."""
        phase = self.event.get('phase', 'checking')
        if phase != 'confirming':
            return phase
        if not self.event.get('accepted'):
            return 'connecting'
        if not self.event.get('streaming'):
            return 'accepted'
        return 'confirmed' if self.event.get('samples', 0) >= 3 else 'verifying'

    def draw_devices(self, row, label, color, *, highlighted=False, marker='*'):
        """Share the same device silhouettes between progress and results."""
        portal = (
            '    .-------------.    ',
            ' .--|             |--. ',
            '| + |             | o |',
            "| o '-------------' + |",
            ' \\___/           \\___/ ',
        )
        ps5 = (
            '   /|  |\\',
            '  / |  | \\',
            ' |  |  |  |',
            ' |  |  :  |',
            ' |__|__|__|',
        )
        left = 4
        width = min(82, self.screen.getmaxyx()[1] - 8)
        right = left + width - max(map(len, ps5))
        outline = self.colors.get(color, 0) if highlighted else self.curses.A_DIM
        for index, line in enumerate(portal):
            self.put(row + index, left, line, outline)
        for index, line in enumerate(ps5):
            self.put(row + index, right, line, outline)
        self.put(row + 2, left + 5, pad_cells(self.t(label), 13, center=True), self.emphasis(color))
        self.put(row + 2, right + 6, marker, self.emphasis(color))
        self.put(row + 5, left + 7, 'PS PORTAL', self.curses.A_BOLD)
        self.put(row + 5, right + 4, 'PS5', self.curses.A_BOLD)

        start = left + max(map(len, portal)) + 2
        length = right - start - 2
        return start, length

    def connection_art(self, row, stage, elapsed):
        """Keep the devices still while the link reflects the observed state."""
        color, label = {
            'checking': ('warning', 'CHECK'),
            'preparing': ('warning', 'WAIT'),
            'waiting': ('accent', 'CONNECT'),
            'connecting': ('warning', 'LINKING'),
            'accepted': ('accent', 'LINKED'),
            'verifying': ('accent', 'VERIFY'),
            'confirmed': ('success', 'OK'),
            'restoring': ('warning', 'RESTORE'),
            'stopping': ('warning', 'RESTORE'),
        }[stage]
        linked = stage in ('accepted', 'verifying', 'confirmed')
        start, length = self.draw_devices(
            row, label, color, highlighted=linked,
            marker='?' if stage == 'checking' else '*')
        if linked:
            line = '=' if stage == 'confirmed' else '-'
            self.put(row + 2, start, '<' + line * (length - 2) + '>',
                     self.colors.get(color, 0))
            if self.animations:
                offset = 1 + (length - 4 - int(elapsed * 8) % (length - 3))
                self.put(row + 2, start + offset, '<<', self.emphasis(color))
        else:
            self.put(row + 2, start, ('- ' * length)[:length], self.curses.A_DIM)
            if stage == 'connecting':
                offset = int(elapsed * 8) % (length - 1) if self.animations else length // 2
                self.put(row + 2, start + offset, '>>', self.emphasis(color))
            else:
                if stage == 'waiting':
                    marker = '.' * (1 + int(elapsed * 2) % 3) if self.animations else '...'
                else:
                    spinner = '|/-\\'[int(elapsed * 6) % 4] if self.animations else '*'
                    marker = '[' + spinner + ']'
                self.put(row + 2, start + (length - 5) // 2, marker.center(5),
                         self.emphasis(color))

    def result_art(self, row, summary):
        """Show the completed attempt, without suggesting ongoing monitoring."""
        label, marker = {
            'success': ('CONFIRMED', '[OK]'),
            'warning': ('CHECK', '[?]'),
            'error': ('RECOVER', '[!]'),
        }[summary.kind]
        if summary.title == 'Attempt stopped':
            label, marker = 'STOPPED', '[X]'
        start, length = self.draw_devices(
            row, label, summary.kind, highlighted=summary.kind != 'warning',
            marker='*' if summary.kind == 'success' else marker[1])
        if summary.kind == 'success':
            line = '<' + '=' * (length - 2) + '>'
        else:
            line = ('- ' * length)[:length]
        self.put(row + 2, start, line, self.colors.get(summary.kind, 0))
        self.put(row + 2, start + (length - len(marker) - 2) // 2,
                 ' ' + marker + ' ', self.emphasis(summary.kind))

    def draw_progress(self):
        phase = self.event.get('phase', 'checking')
        stage = self.connection_stage()
        elapsed = max(0, time.monotonic() - self.phase_started)
        footer = 'Restoring the direct path; please keep this Mac awake.' if phase in ('restoring', 'stopping') else 'Q / Esc / Ctrl+C: stop and restore the network'
        if not self.frame(2, footer):
            self.small_terminal(live=True)
            return
        label, title, message, color = {
            'checking': ('WAIT', 'Keep Portal disconnected', 'Checking devices...', 'warning'),
            'preparing': ('WAIT', 'Keep Portal disconnected', 'Preparing the connection path...', 'warning'),
            'waiting': ('READY', 'CONNECT NOW: Portal -> PS5', 'Waiting for Portal to connect...', 'success'),
            'connecting': ('LINKING', 'Connection request received', 'Waiting for PS5 to accept the connection...', 'warning'),
            'accepted': ('LINKED', 'PS5 accepted the connection', 'Waiting for stream information...', 'accent'),
            'verifying': ('VERIFY', 'Checking the higher target', 'Verifying the higher bitrate...', 'accent'),
            'confirmed': ('CONFIRMED', 'Higher target reported', 'PS5 confirmed the higher target.', 'success'),
            'restoring': ('RESTORING', 'Finishing this attempt', 'Restoring the direct connection...', 'warning'),
            'stopping': ('STOPPING', 'Restoring your network', 'Restoring the direct connection...', 'warning'),
        }[stage]
        self.badge(7, label, title, color)
        self.transition_line(8, self.emphasis(color), elapsed,
                             'outward' if phase == 'waiting' else 'forward')
        self.put(9, 4, message)
        self.connection_art(10, stage, elapsed)
        if phase == 'waiting':
            remaining = max(0, min(CONNECT_SECONDS, self.event.get('seconds', 0)))
            color = 'warning' if remaining <= 20 else 'success'
            self.inline(17, 4, (f'{remaining // 60:02d}:{remaining % 60:02d}', self.emphasis(color)),
                        (self.t('  /  {seconds}s left to connect', seconds=remaining), self.curses.A_BOLD))
            width = min(48, self.screen.getmaxyx()[1] - 12)
            filled = round(width * remaining / CONNECT_SECONDS)
            self.put(18, 4, '[' + '#' * filled + '.' * (width - filled) + ']',
                     self.colors.get(color, 0))
            self.put(19, 4, 'On Portal, select your PS5 to start Remote Play.', self.curses.A_DIM)
        elif phase in ('checking', 'preparing'):
            self.put(17, 4, 'No action needed yet.', self.curses.A_BOLD)
            self.put(18, 4, self.t('When READY appears, you get {seconds} seconds to connect.',
                                 seconds=CONNECT_SECONDS),
                     self.curses.A_DIM)
        elif phase == 'confirming':
            guidance = (self.t('Finishing this attempt...') if stage == 'confirmed' else
                        self.t('Up to {seconds}s left to confirm.',
                               seconds=self.event.get('seconds', CONFIRM_SECONDS)))
            self.inline(17, 4, ('Keep Portal connected.  ', self.curses.A_BOLD),
                        (guidance, self.curses.A_DIM))
            column = 4
            for done, text in (
                    (self.event.get('modified', 0) > 0, self.t('Request')),
                    (self.event.get('accepted', False), self.t('PS5 accepted')),
                    (self.event.get('samples', 0) >= 3,
                     self.t('Target {samples}/3', samples=min(self.event.get('samples', 0), 3)))):
                text = ('[x] ' if done else '[ ] ') + text + '   '
                self.put(18, column, text,
                         self.colors.get('success', 0) if done else self.curses.A_DIM)
                column += cell_width(text)
        else:
            self.put(17, 4, 'Keep this Mac awake until the result appears.', self.curses.A_BOLD)
        target = self.event.get('target_bitrate')
        if isinstance(target, (int, float)):
            self.put(19, 4, self.t('PS5-reported target: {target:.3f} Mbps', target=target / 1e6),
                     self.curses.A_BOLD)
        if self.notice:
            self.put(19, 4, ' ' * min(82, self.screen.getmaxyx()[1] - 8))
            self.paragraph(19, self.notice, self.colors.get('warning', 0), max_rows=2)
        self.refresh(live=True)

    def progress(self, event):
        kind = event['type']
        previous_phase = self.event.get('phase')
        self.event.update({key: value for key, value in event.items() if key != 'type'})
        if kind in ('checking', 'preparing', 'restoring', 'stopping'):
            self.event['phase'] = kind
            if kind in ('restoring', 'stopping'):
                self.settings_open = False
        elif kind == 'ready':
            self.event['phase'] = 'waiting'
        elif kind == 'modified':
            self.event.update(phase='confirming', modified=1, seconds=CONFIRM_SECONDS,
                              accepted=False, streaming=False, samples=0, target_bitrate=None)
            self.notice = ''
        elif kind == 'reconnect':
            self.notice = 'Existing stream detected. Disconnect Portal, then reconnect now.'
        if self.event.get('phase') != previous_phase:
            self.phase_started = time.monotonic()
        self.draw_progress()
        if self.event.get('phase') in ('restoring', 'stopping'):
            return True
        key = self.screen.getch()
        if self.settings_key(key, live=True):
            return True
        return key not in (27, 3, ord('q'), ord('Q'))

    def simulate(self):
        """Exercise the actual screens without sudo, packet capture, or file writes."""
        target = {'65': 63_106_000, '100': 97_087_000, '200': 194_174_000}[self.profile]
        if not self.progress({'type': 'checking'}):
            return self.cancelled_demo()
        start = time.monotonic()
        while time.monotonic() - start < .8:
            if not self.progress({'type': 'tick', 'phase': 'checking'}):
                return self.cancelled_demo()
            time.sleep(.1)
        if not self.progress({'type': 'preparing', 'seconds': 5}):
            return self.cancelled_demo()
        start = time.monotonic()
        while time.monotonic() - start < 1:
            if not self.progress({'type': 'tick', 'phase': 'preparing', 'seconds': 1}):
                return self.cancelled_demo()
            time.sleep(.1)
        if not self.progress({'type': 'ready', 'seconds': CONNECT_SECONDS}):
            return self.cancelled_demo()
        start = time.monotonic()
        while time.monotonic() - start < 3:
            if not self.progress({'type': 'tick', 'phase': 'waiting',
                                  'seconds': CONNECT_SECONDS - int(time.monotonic() - start)}):
                return self.cancelled_demo()
            time.sleep(.1)
        if not self.progress({'type': 'modified'}):
            return self.cancelled_demo()
        start = time.monotonic()
        while time.monotonic() - start < .8:
            if not self.progress({'type': 'tick', 'phase': 'confirming'}):
                return self.cancelled_demo()
            time.sleep(.1)
        if not self.progress({'type': 'observed', 'accepted': True}):
            return self.cancelled_demo()
        time.sleep(.4)
        for samples in range(1, 4):
            if not self.progress({'type': 'tick', 'phase': 'confirming',
                                  'seconds': CONFIRM_SECONDS - samples,
                                  'modified': 1, 'accepted': True, 'streaming': True,
                                  'samples': samples, 'target_bitrate': target}):
                return self.cancelled_demo()
            time.sleep(.4)
        self.progress({'type': 'restoring'})
        time.sleep(.3)
        return {'completed': True, 'restoration_errors': [], 'unique_mutated_sequences': 1,
                'high_target_confirmed': True, 'egress_witness': {'all_expected_observed': True},
                'ps5_messages': [{'type': 'CONNECTIONQUALITY', 'target_bitrate_raw': target}]}

    def cancelled_demo(self):
        self.progress({'type': 'restoring'})
        return {'completed': False, 'run_error': 'Cancelled by user', 'restoration_errors': []}

    def connect(self, config):
        self.event = {'phase': 'checking', 'seconds': CONNECT_SECONDS}
        self.phase_started = time.monotonic()
        self.notice = ''
        self.screen.nodelay(True)
        self.curses.flushinp()
        probe = None
        started = False
        try:
            if self.demo:
                return self.simulate()
            if self.helper:
                from portal_macos_client import run_session, HelperUnavailable
                try:
                    return run_session(self.profile, config, self.progress)
                except HelperUnavailable as exc:
                    return {'completed': False, 'run_error': str(exc), 'restoration_errors': [],
                            'preflight_failed': True}
            import portal_active_probe as probe
            probe.set_profile(self.profile)
            started = True
            return probe.run(True, finish_on_high_target=True, connect_timeout=CONNECT_SECONDS,
                             confirmation_timeout=CONFIRM_SECONDS, progress=self.progress, config=config)
        except KeyboardInterrupt:
            return {'completed': False, 'run_error': 'Cancelled by user', 'restoration_errors': []}
        except Exception as exc:
            if not started or (probe is not None and isinstance(exc, probe.PreflightError)):
                return {'completed': False, 'run_error': str(exc), 'restoration_errors': [],
                        'preflight_failed': True}
            return {'completed': False, 'run_error': str(exc),
                    'restoration_errors': ['Unexpected failure; recovery could not be confirmed: ' + str(exc)]}
        finally:
            self.screen.timeout(100)
            self.curses.flushinp()

    def details(self, report):
        while True:
            if self.frame(3, 'Enter / Esc: back to result'):
                self.put(7, 4, 'Local session details', self.curses.A_BOLD)
                row = 9
                if report.get('directory'):
                    row = self.paragraph(row, self.t('Report: {path}',
                                         path=str(Path(report['directory']) / 'report.json'))) + 1
                if report.get('restoration_errors'):
                    row = self.paragraph(row, self.t('Recovery errors: {errors}',
                                         errors='; '.join(report['restoration_errors'])),
                                         self.colors.get('error', 0)) + 1
                    deadline = report.get('watchdog_seconds')
                    row = self.paragraph(row, self.t('Automatic recovery deadline: {seconds}s after watchdog start.',
                                                    seconds=deadline)
                                         if deadline else 'The independent recovery process has its own deadline.') + 1
                    state = report.get('watchdog_state')
                    if report.get('managed_helper'):
                        self.paragraph(row, 'Open Better Portal to check the connection helper. Keep this Mac awake for recovery.')
                    elif state:
                        self.paragraph(row, self.t('Manual recovery from this project folder: {command}',
                                       command='sudo .venv/bin/python portal_capture.py --restore ' + state))
                elif report.get('directory'):
                    self.paragraph(row, 'The report and captures stay local. Share only a redacted summary.')
                else:
                    self.paragraph(row, 'Demo sessions do not write reports or change networking.' if self.demo
                                   else 'The attempt stopped before a report was created.')
                self.refresh()
            else:
                self.small_terminal()
            key = self.screen.getch()
            if self.settings_key(key):
                continue
            if key in (10, 13, 27, self.curses.KEY_ENTER):
                return

    def draw_result(self, summary, elapsed):
        if not self.frame(3, 'Enter / R: try again    D: details    Q / Esc: quit' if summary.kind != 'error'
                          else 'D: recovery details    Q / Esc: quit (keep Mac awake)'):
            self.small_terminal()
            return
        label = {'success': 'OK', 'warning': '!', 'error': '! RECOVERY'}[summary.kind]
        if summary.title == 'Attempt stopped':
            label = 'STOPPED'
        self.badge(7, label, summary.title, summary.kind)
        self.transition_line(8, self.emphasis(summary.kind), elapsed,
                             'forward' if summary.kind == 'success' else 'inward')
        self.result_art(9, summary)
        row = 15
        if summary.target is not None:
            self.inline(row, 4, (f'{summary.target:.3f} Mbps', self.curses.A_BOLD),
                        (' / PS5 target, not measured throughput.', self.curses.A_DIM))
            row += 1
        row = self.paragraph(row, summary.message, self.curses.A_DIM, max_rows=2)
        self.paragraph(row, summary.advice, max_rows=self.screen.getmaxyx()[0] - 4 - row)
        self.button(self.screen.getmaxyx()[0] - 4,
                    'Try another session  ->' if summary.kind != 'error' else 'Quit and allow recovery')
        self.refresh()

    def result(self, report):
        self.settings_open = False
        summary = summarize(report)
        started = time.monotonic()
        while True:
            self.draw_result(summary, time.monotonic() - started)
            key = self.screen.getch()
            if self.settings_key(key):
                continue
            if key in (27, ord('q'), ord('Q')):
                return False
            if key in (ord('d'), ord('D')):
                self.details(report)
            elif key in (10, 13, self.curses.KEY_ENTER, ord('r'), ord('R')):
                return summary.kind != 'error'

    def run(self):
        if self.language is None and not self.choose_language():
            return 0
        while self.prepare():
            config = self.configure()
            if config is None:
                continue
            self.report = self.connect(config)
            if not self.result(self.report):
                return 2 if self.report.get('restoration_errors') else 0
        return 0


def main():
    def t(text, **values):
        preferences = ROOT / 'tui-settings.json'
        if '--helper' in sys.argv:
            from portal_macos_client import user_directory
            preferences = user_directory() / 'tui-settings.json'
        language = load_preferences(preferences).get('language')
        return translate(text, language, **values)

    parser = argparse.ArgumentParser(description=t(__doc__))
    parser.add_argument('--demo', action='store_true',
                        help=t('Preview the wizard with simulated events; no sudo or network changes'))
    parser.add_argument('--no-animations', action='store_true',
                        help=t('Keep state labels and highlights, without motion'))
    parser.add_argument('--helper', action='store_true',
                        help=t('Use the installed macOS connection helper without sudo'))
    args = parser.parse_args()
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.exit(2, t('Open this wizard in an interactive Terminal window.') + '\n')
    if not args.demo:
        if sys.platform != 'darwin':
            parser.exit(2, t('This guided launcher currently supports macOS.') + '\n')
        if args.helper and os.geteuid() == 0:
            parser.exit(2, t('Open Better Portal as your normal Mac user.') + '\n')
        if not args.helper and (os.geteuid() != 0 or 'SUDO_UID' not in os.environ):
            parser.exit(2, t('Double-click Start.command, or run: sudo .venv/bin/python portal_tui.py') + '\n')
    try:
        import curses
    except ImportError:
        parser.exit(2, t('This Python installation needs the standard curses module.') + '\n')
    try:
        return curses.wrapper(lambda screen: Wizard(screen, curses, demo=args.demo,
                                                     animations=not args.no_animations,
                                                     helper=args.helper).run())
    except KeyboardInterrupt:
        print(t('Demo closed.' if args.demo else 'Wizard closed.'))
        return 1
    except curses.error as exc:
        print(t('Terminal setup failed: {error}. Try the macOS Terminal app.', error=str(exc)), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
