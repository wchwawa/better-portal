#!/usr/bin/env python3
"""Build a protected, self-contained macOS app and optional signed installer.

No service is installed or registered by this script. --development builds are
only for compilation/demo testing and cannot enable the privileged helper.
"""
import argparse
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
MAC = ROOT / 'macos'
APP_ID = 'com.wchwawa.betterportal'


def run(*args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--development', action='store_true')
    parser.add_argument('--identity', help='Developer ID Application signing identity')
    parser.add_argument('--installer-identity', help='Developer ID Installer signing identity')
    parser.add_argument('--notary-profile', help='Existing notarytool Keychain profile name')
    parser.add_argument('--version', default='0.1.0')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('Build on macOS')
    if args.development and any((args.identity, args.installer_identity, args.notary_profile)):
        parser.error('Development builds cannot use release signing options')
    if not args.development and not (args.identity and args.installer_identity):
        parser.error('Release builds require both Developer ID identities')
    if not args.version or any(c not in '0123456789.' for c in args.version):
        parser.error('Use a numeric dotted version')
    identity = args.identity or '-'
    build = MAC / 'build'
    dist = MAC / 'dist'
    stage = build / 'installer-root'
    app = stage / 'Better Portal.app'
    # Remove only generated staging, never a user's installed app.
    if stage.exists():
        shutil.rmtree(stage)
    dist.mkdir(parents=True, exist_ok=True)
    contents = app / 'Contents'
    executables = contents / 'MacOS'
    resources = contents / 'Resources'
    daemons = contents / 'Library/LaunchDaemons'
    for directory in (executables, resources, daemons):
        directory.mkdir(parents=True, exist_ok=True)
    run('swift', 'build', '--package-path', MAC, '-c', 'release')
    binary_dir = Path(subprocess.check_output(
        ['swift', 'build', '--package-path', str(MAC), '-c', 'release', '--show-bin-path'], text=True).strip())
    for name in ('BetterPortal', 'PortalHelper', 'PortalBridge'):
        shutil.copy2(binary_dir / name, executables / name)
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir',
               '--name', 'PortalRuntime', '--distpath', str(build / 'frozen'),
               '--workpath', str(build / 'pyinstaller'), '--specpath', str(build),
               '--paths', str(ROOT), '--add-data', f'{ROOT / "locales"}:locales',
               '--hidden-import', 'portal_tui', '--hidden-import', 'portal_macos_client',
               '--hidden-import', 'portal_active_probe', '--hidden-import', 'portal_capture',
               '--hidden-import', 'curses', '--hidden-import', 'scapy.layers.inet',
               '--hidden-import', 'scapy.layers.l2']
    if args.identity:
        command += ['--codesign-identity', args.identity]
    run(*command, ROOT / 'portal_macos_runtime.py', cwd=ROOT)
    shutil.copytree(build / 'frozen/PortalRuntime', resources / 'PortalRuntime', symlinks=True)
    shutil.copytree(ROOT / 'locales', resources / 'locales')
    shutil.copy2(MAC / 'Resources/Start.command', resources / 'Start.command')
    (resources / 'Start.command').chmod(0o755)
    shutil.copy2(MAC / f'Resources/{APP_ID}.helper.plist', daemons)
    shutil.copy2(ROOT / 'LICENSE', resources / 'LICENSE')
    with (contents / 'Info.plist').open('wb') as stream:
        plistlib.dump({
            'CFBundleIdentifier': APP_ID, 'CFBundleName': 'Better Portal',
            'CFBundleDisplayName': 'Better Portal', 'CFBundleExecutable': 'BetterPortal',
            'CFBundlePackageType': 'APPL', 'CFBundleShortVersionString': args.version,
            'CFBundleVersion': args.version, 'LSMinimumSystemVersion': '13.0',
            'NSHighResolutionCapable': True,
        }, stream)
    # The package installs every payload as root:wheel. No group/world writes.
    for path in stage.rglob('*'):
        if not path.is_symlink():
            path.chmod(path.stat().st_mode & ~0o022)
    flags = ['--force', '--sign', identity]
    if not args.development:
        flags += ['--options', 'runtime', '--timestamp']
    for name, identifier in (('PortalHelper', APP_ID + '.helper'),
                             ('PortalBridge', APP_ID + '.bridge'),
                             ('BetterPortal', APP_ID)):
        run('/usr/bin/codesign', *flags, '--identifier', identifier, executables / name)
    run('/usr/bin/codesign', *flags, '--identifier', APP_ID + '.runtime',
        resources / 'PortalRuntime/PortalRuntime')
    # Dependencies were signed by PyInstaller; sign the outer bundle last.
    run('/usr/bin/codesign', *flags, app)
    run('/usr/bin/codesign', '--verify', '--deep', '--strict', '--verbose=2', app)
    if args.development:
        print(f'Development app: {app}\nHelper registration is deliberately unavailable without an Apple signature.')
        return 0
    package = dist / f'Better-Portal-{args.version}-{os.uname().machine}.pkg'
    scripts = build / 'installer-scripts'
    scripts.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MAC / 'Resources/preinstall', scripts / 'preinstall')
    (scripts / 'preinstall').chmod(0o755)
    run('/usr/bin/pkgbuild', '--root', stage, '--identifier', APP_ID + '.installer',
        '--version', args.version, '--install-location', '/Applications',
        '--ownership', 'recommended', '--scripts', scripts,
        '--sign', args.installer_identity, package)
    if args.notary_profile:
        run('xcrun', 'notarytool', 'submit', package, '--keychain-profile', args.notary_profile, '--wait')
        run('xcrun', 'stapler', 'staple', package)
        run('/usr/sbin/spctl', '--assess', '--type', 'install', '--verbose=2', package)
    print(f'Installer: {package}')
    if not args.notary_profile:
        print('Not notarized yet. Submit and staple this package before public distribution.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
