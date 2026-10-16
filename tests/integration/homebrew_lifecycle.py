"""Exercise real Brew installs and upgrades in a separate, disposable formula.

The test package uses its own command, data directory and inactive network lock.
It never launches a live connection or changes an existing Better Portal install.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
TAP = 'better-portal-tests/lifecycle'
NAME = 'better-portal-lifecycle-test'
FORMULA = TAP + '/' + NAME


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log-dir', type=Path, required=True)
    args = parser.parse_args()
    args.log_dir.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, HOMEBREW_NO_AUTO_UPDATE='1', HOMEBREW_NO_INSTALL_CLEANUP='1',
                       HOMEBREW_NO_ASK='1')
    brew = shutil.which('brew')
    assert brew and sys.platform == 'darwin', 'Run on a Mac with Homebrew installed.'

    def run(label, command, *, cwd=None, success=True):
        print(label, flush=True)
        result = subprocess.run([str(part) for part in command], cwd=cwd, env=environment,
                                capture_output=True, text=True, timeout=600)
        output = result.stdout + result.stderr
        (args.log_dir / (label + '.log')).write_text(output, encoding='utf-8')
        if success != (result.returncode == 0):
            raise AssertionError(f'{label} exited {result.returncode}:\n{output[-12000:]}')
        return output

    repository = Path(subprocess.check_output([brew, '--repository'], text=True).strip())
    tap = repository / 'Library/Taps/better-portal-tests/homebrew-lifecycle'
    assert not tap.exists(), 'The test tap already exists; leaving it untouched.'
    installed = subprocess.check_output([brew, 'list', '--formula', '--full-name'], text=True).splitlines()
    assert not any(value.split('/')[-1] == NAME for value in installed), 'Test formula already installed.'
    prefix = Path(subprocess.check_output([brew, '--prefix'], text=True).strip())
    command = prefix / 'bin' / NAME
    assert not command.exists(), 'Test command already exists; leaving it untouched.'

    with tempfile.TemporaryDirectory(prefix='better-portal-brew-') as temporary:
        root = Path(temporary)
        source = root / 'source'
        data = root / 'user data'
        old = root / 'old settings'

        def commit(message):
            subprocess.run(['git', 'add', '.'], cwd=source, check=True)
            subprocess.run(['git', '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--signoff',
                            '-m', message], cwd=source, check=True)
            return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()

        def metadata():
            path = prefix / 'opt' / NAME / 'libexec/app/installation.json'
            return json.loads(path.read_text())

        def saved_files():
            return {str(path.relative_to(data)): path.read_bytes() for path in data.rglob('*')
                    if path.is_file() and path.name != '.brew-session.lock'}

        try:
            run('01-clone', ['git', 'clone', '--quiet', '--no-hardlinks', '--single-branch', ROOT, source])
            # Pull-request checkouts can start at a detached merge commit.
            subprocess.run(['git', 'checkout', '--quiet', '-B', 'main'], cwd=source, check=True)
            subprocess.run(['git', 'config', 'user.name', 'Jason'], cwd=source, check=True)
            subprocess.run(['git', 'config', 'user.email', 'wch19961116@gmail.com'], cwd=source, check=True)
            launcher = source / 'portal_cli.py'
            code = launcher.read_text()
            original = "return Path.home() / 'Library' / 'Application Support' / 'Better Portal'"
            assert code.count(original) == 1
            code = code.replace(original, f'return Path({str(data)!r})')
            code = code.replace("NETWORK_LOCK = Path('/var/run/portal-lab-capture.lock')",
                                f'NETWORK_LOCK = Path({str(root / "inactive.lock")!r})')
            launcher.write_text(code)
            first = commit('Package fixture: isolate settings and connection lock')
            (tap / 'Formula').mkdir(parents=True)
            subprocess.run(['git', 'init', '--quiet', str(tap)], check=True)
            formula = (source / 'Formula/better-portal.rb').read_text()
            formula = formula.replace('class BetterPortal <', 'class BetterPortalLifecycleTest <')
            formula = formula.replace('https://github.com/wchwawa/better-portal.git', source.as_uri())
            formula = formula.replace('branch: "main"', 'branch: "main", using: :git')
            formula = formula.replace('bin/"better-portal"', f'bin/"{NAME}"')
            formula = formula.replace('#{bin}/better-portal', '#{bin}/' + NAME)
            (tap / 'Formula' / (NAME + '.rb')).write_text(formula)

            output = run('02-install', [brew, 'install', '--HEAD', FORMULA])
            assert metadata()['revision'] == first
            assert 'Changes in HEAD-' + first[:12] in output, 'Install did not display bundled notes.'
            run('03-dependencies', [brew, 'missing', FORMULA])
            run('04-formula-test', [brew, 'test', FORMULA])
            # Brew deliberately creates application environments without pip.
            # Its managed Python can check that environment without adding pip.
            run('05-pip-check', [prefix / 'opt/python@3.14/bin/python3.14', '-m', 'pip', '--python',
                                 prefix / 'opt' / NAME / 'libexec/bin/python', 'check'])
            run('06-terminal', [sys.executable, ROOT / 'tests/integration/homebrew_tui_smoke.py', command])

            old.mkdir()
            (old / 'config.json').write_text(json.dumps({
                'interface': 'en0', 'ps5_ip': '192.168.1.20', 'portal_ip': '192.168.1.30'}))
            (old / 'tui-settings.json').write_text('{"language": "en", "profile": "100"}')
            run('07-import', [command, 'import-settings', old])
            (data / 'experiments').mkdir()
            (data / 'experiments/saved-report.json').write_text('{"test_fixture": true}')
            saved = saved_files()

            (source / 'package-test.txt').write_text('Second revision\n')
            second_note = 'Package fixture: verify update notes and saved settings'
            second = commit(second_note)
            output = run('08-upgrade', [command, 'update'])
            assert metadata()['revision'] == second
            assert metadata()['changes_scope'] == 'update'
            assert metadata()['changes'] == [second_note], metadata()
            assert f'Updated: HEAD-{first[:12]} -> HEAD-{second[:12]}.' in output
            assert output.count('Changes in HEAD-' + second[:12]) == 1, output
            assert second_note in output
            assert saved_files() == saved

            output = run('09-repeat-update', [command, 'update'])
            assert 'Already up to date: HEAD-' + second[:12] in output
            assert second_note in output
            assert metadata()['revision'] == second and saved_files() == saved

            # A vanished unrelated tap must fail the refresh without a false
            # success message, an upgrade attempt or a change to user data.
            broken_tap = repository / 'Library/Taps/better-portal-tests/homebrew-broken-refresh'
            assert not broken_tap.exists(), 'A broken-refresh test tap already exists.'
            subprocess.run(['git', 'init', '--quiet', str(broken_tap)], check=True)
            try:
                subprocess.run(['git', '-C', str(broken_tap), '-c', 'user.name=Jason',
                                '-c', 'user.email=wch19961116@gmail.com', '-c', 'commit.gpgsign=false',
                                'commit', '--allow-empty', '--quiet', '--signoff',
                                '-m', 'Package fixture: reproduce an unrelated broken tap'], check=True)
                subprocess.run(['git', '-C', str(broken_tap), 'remote', 'add', 'origin',
                                str(root / 'missing-tap')], check=True)
                output = run('10-broken-tap', [command, 'update'], success=False)
                assert 'Homebrew could not finish' in output and 'Update complete.' not in output
                assert metadata()['revision'] == second and saved_files() == saved
            finally:
                subprocess.run([brew, 'untap', '--force', 'better-portal-tests/broken-refresh'],
                               env=environment, check=True)

            # A failed source fetch must preserve the usable previous keg.
            unavailable = root / 'unavailable-source'
            source.rename(unavailable)
            try:
                output = run('11-download-failure', [command, 'update'], success=False)
                assert 'Update complete.' not in output
                assert metadata()['revision'] == second and saved_files() == saved
                run('12-previous-version-works', [command, 'changes'])
            finally:
                unavailable.rename(source)

            (source / 'package-test.txt').write_text('Third revision\n')
            third_note = 'Package fixture: recover after a failed update'
            third = commit(third_note)
            output = run('13-retry', [command, 'update'])
            assert third_note in output and metadata()['revision'] == third
            assert metadata()['changes'] == [third_note] and saved_files() == saved

            (source / 'package-test.txt').write_text('Fourth revision\n')
            fourth_note = 'Package fixture: show notes for a direct Brew upgrade'
            fourth = commit(fourth_note)
            output = run('14-direct-brew-upgrade', [brew, 'upgrade', '--fetch-HEAD', FORMULA])
            assert 'Changes in HEAD-' + fourth[:12] in output and fourth_note in output
            assert metadata()['revision'] == fourth and metadata()['changes'] == [fourth_note]
            assert saved_files() == saved
            run('15-upgraded-formula-test', [brew, 'test', FORMULA])
            run('16-upgraded-terminal', [sys.executable, ROOT / 'tests/integration/homebrew_tui_smoke.py', command])
            run('17-uninstall', [brew, 'uninstall', '--force', FORMULA])
            assert saved_files() == saved, 'Uninstall removed user data.'
            print('PASS: real install, dependencies, upgrade, notes, no-op, failures, retry, direct Brew, TUI and data retention.', flush=True)
        finally:
            subprocess.run([brew, 'uninstall', '--force', FORMULA], env=environment,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if tap.exists():
                subprocess.run([brew, 'untap', '--force', TAP], env=environment, check=True)


if __name__ == '__main__':
    main()
