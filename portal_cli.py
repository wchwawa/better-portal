"""Homebrew entry point: launch the wizard, keep user data, and delegate updates."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys

from portal_tui_text import LANGUAGES, translate

ROOT = Path(__file__).resolve().parent
FORMULA = 'wchwawa/better-portal/better-portal'
NETWORK_LOCK = Path('/var/run/portal-lab-capture.lock')


def data_directory():
    return Path.home() / 'Library' / 'Application Support' / 'Better Portal'


def installation():
    try:
        return json.loads((ROOT / 'installation.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def translator(directory):
    try:
        language = json.loads((directory / 'tui-settings.json').read_text(encoding='utf-8')).get('language')
    except (OSError, ValueError, AttributeError):
        language = None
    return lambda text, **values: translate(text, language, **values)


@contextmanager
def session_lock(directory):
    """Keep this launcher's update and play commands from overlapping."""
    import fcntl
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(directory / '.brew-session.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Close the other Better Portal window before continuing.') from None
        yield
    finally:
        os.close(descriptor)


def import_settings(source, destination):
    """Copy only missing settings; never replace the source or saved user data."""
    from portal_tui import load_config, validate_form
    if not source.is_dir():
        raise ValueError('The old Better Portal folder could not be found.')
    pending = {}
    for name in ('config.json', 'tui-settings.json'):
        target = destination / name
        path = source / name
        if target.exists() or target.is_symlink() or not path.is_file():
            continue
        if path.stat().st_size > 65536:
            raise ValueError('Settings file is too large: ' + name)
        value = json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(value, dict):
            raise ValueError('Invalid settings file: ' + name)
        if name == 'config.json':
            value = validate_form(load_config(path))
        else:
            if value.get('language') not in (*LANGUAGES, None):
                raise ValueError('Invalid saved language')
            if value.get('profile', '65') not in ('65', '100', '200'):
                raise ValueError('Invalid saved bitrate')
        pending[name] = value
    # Validate both inputs before writing either; exclusive creation preserves any
    # file created since the initial check. A retry imports only missing files.
    for name, value in pending.items():
        descriptor = os.open(destination / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                json.dump(value, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
        except BaseException:
            (destination / name).unlink(missing_ok=True)
            raise
    return len(pending)


def update(info, run=subprocess.run):
    brew = info.get('brew')
    if not isinstance(brew, str) or not Path(brew).is_absolute() or not Path(brew).is_file():
        raise RuntimeError('Install Better Portal with Homebrew before using this command.')
    if NETWORK_LOCK.exists():
        raise RuntimeError('A Portal connection or recovery is active. Wait until it finishes.')
    # Homebrew owns downloads, dependency upgrades and installation. Retain old
    # kegs for manual recovery; never call sudo or alter the user's source tree.
    environment = dict(os.environ, HOMEBREW_NO_INSTALL_CLEANUP='1')
    for arguments in ([brew, 'update'], [brew, 'upgrade', '--fetch-HEAD', FORMULA]):
        result = run(arguments, env=environment, check=False)
        if result.returncode:
            return result.returncode
    return 0


def run_wizard(arguments):
    # Ctrl+C reaches the whole terminal foreground group. Keep our lock until
    # the wizard has finished its own cancellation and network restoration.
    with subprocess.Popen(arguments) as child:
        while True:
            try:
                return child.wait()
            except KeyboardInterrupt:
                continue


def main(argv=None):
    directory = data_directory()
    t = translator(directory)
    parser = argparse.ArgumentParser(description=t('Open Better Portal or update its Homebrew installation.'))
    parser.add_argument('--version', action='version',
                        version='Better Portal ' + installation().get('version', 'source'))
    parser.add_argument('--demo', action='store_true', help=t('Preview the wizard without network changes.'))
    parser.add_argument('--no-animations', action='store_true')
    parser.add_argument('command', nargs='?', choices=('update', 'import-settings'),
                        help=t('Update with Homebrew, or import settings from an old folder.'))
    parser.add_argument('folder', nargs='?', type=Path)
    args = parser.parse_args(argv)
    if (args.command == 'import-settings') != (args.folder is not None):
        parser.error('Use: better-portal import-settings /path/to/old/better-portal')
    if args.command and (args.demo or args.no_animations):
        parser.error('Preview options apply only when opening the wizard.')
    try:
        if sys.platform != 'darwin':
            raise RuntimeError('The Homebrew launcher supports macOS.')
        if os.geteuid() == 0:
            raise RuntimeError('Run better-portal without sudo. It requests permission when needed.')
        with session_lock(directory):
            if args.command == 'update':
                print(t('Updating Better Portal with Homebrew. Your settings stay in place.'), flush=True)
                result = update(installation())
                if result == 0:
                    print(t('Update complete. Run better-portal to open the wizard.'))
                else:
                    print(t('Homebrew could not finish. Read the error above, then retry better-portal update.'),
                          file=sys.stderr)
                return result
            if args.command == 'import-settings':
                count = import_settings(args.folder.expanduser().resolve(), directory)
                print(t('Imported {count} settings files. Existing settings were kept.', count=count))
                return 0
            arguments = [sys.executable, str(ROOT / 'portal_tui.py'), '--data-dir', str(directory)]
            if args.demo:
                arguments.append('--demo')
            else:
                print(t('Opening Better Portal. Enter your Mac login password if requested.'), flush=True)
                arguments.insert(0, '/usr/bin/sudo')
            if args.no_animations:
                arguments.append('--no-animations')
            # The parent keeps the update lock while sudo and the wizard run.
            return run_wizard(arguments)
    except (OSError, ValueError, RuntimeError) as exc:
        print(t(str(exc)), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
