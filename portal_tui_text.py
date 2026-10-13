"""Wizard translations and terminal-cell layout, without runtime dependencies."""
import json
import re
import textwrap
import unicodedata
from pathlib import Path

LANGUAGE_NAMES = {
    'en': 'English',
    'zh-CN': '简体中文',
    'ja': '日本語',
    'ko': '한국어',
    'es': 'Español',
    'fr': 'Français',
}
LANGUAGES = tuple(LANGUAGE_NAMES)

# English is the source language. Diagnostic text from the relay stays verbatim.
LOCALES = Path(__file__).resolve().parent / 'locales'
CATALOGS = {language: json.loads((LOCALES / f'{language}.json').read_text(encoding='utf-8'))
            for language in LANGUAGES if language != 'en'}


def translate(text, language, **values):
    catalog = CATALOGS.get(language, {}) if isinstance(language, str) else {}
    translated = catalog.get(text, text)
    return translated.format(**values) if values else translated


def cell_width(text):
    """CJK characters occupy two cells; combining marks share the prior cell."""
    return sum(0 if unicodedata.combining(char) else
               2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1
               for char in text)


def clip_cells(text, width):
    used = 0
    for index, char in enumerate(text):
        used += cell_width(char)
        if used > width:
            return text[:index]
    return text


def pad_cells(text, width, *, center=False):
    text = clip_cells(text, width)
    remaining = width - cell_width(text)
    left = remaining // 2 if center else 0
    return ' ' * left + text + ' ' * (remaining - left)


def wrap_cells(text, width):
    if width < 2:
        raise ValueError('Text width must be at least two terminal cells')
    if cell_width(text) == len(text):
        return textwrap.wrap(text, width=width)
    # Keep Latin words intact when possible, but allow breaks between CJK glyphs.
    tokens = re.findall(r'[\w./:=+-]+|\s+|.', text, flags=re.ASCII)
    lines, line = [], ''
    for token in tokens:
        if token.isspace():
            if line and not line.endswith(' '):
                line += ' '
            continue
        if line and cell_width(line + token) > width:
            lines.append(line.rstrip())
            line = ''
        while cell_width(token) > width:
            head = clip_cells(token, width)
            lines.append(head)
            token = token[len(head):]
        line += token
    if line:
        lines.append(line.rstrip())
    return lines
