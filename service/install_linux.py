"""Install a root-owned systemd preview only after a local baseline."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import portal_auto as auto


def main():
    if sys.platform != 'linux' or os.geteuid() != 0:
        raise SystemExit('Native Linux and sudo required')
    c = auto.config(ROOT / 'auto-config.json')
    if not auto.baseline_valid(c, ROOT / 'auto-runtime'):
        raise SystemExit('Run configure and baseline successfully first')
    if input('Was the baseline picture and control response usable? Type YES: ') != 'YES':
        raise SystemExit('Installation cancelled')
    target = Path('/opt/portal-bitrate-auto')
    runtime = Path('/var/lib/portal-bitrate-auto')
    # Refuse replacement: stop/uninstall and review retained files before upgrading.
    if target.exists() or runtime.exists():
        raise SystemExit('Existing installation found. Stop/uninstall and back up/remove old installation directories first.')
    os.umask(0o077)
    target.mkdir(mode=0o700)
    runtime.mkdir(mode=0o700)
    names = ['portal_auto.py', 'portal_auto_platform.py', 'portal_active_probe.py', 'portal_capture.py',
             'portal_egress_witness.py', 'portal_windows_network.py', 'portal_recovery.py',
             'protocol.py', 'requirements.txt', 'auto-config.json']
    for name in names:
        shutil.copyfile(ROOT / name, target / name)
        (target / name).chmod(0o600)
    shutil.copyfile(ROOT / 'auto-runtime/auto-baseline.json', runtime / 'auto-baseline.json')
    subprocess.run([sys.executable, '-m', 'venv', str(target / '.venv')], check=True)
    subprocess.run([str(target / '.venv/bin/python'), '-m', 'pip', 'install', '-r', str(target / 'requirements.txt')], check=True)
    unit = Path('/etc/systemd/system/portal-bitrate-auto.service')
    shutil.copyfile(ROOT / 'service/portal-bitrate-auto.service', unit)
    unit.chmod(0o644)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'enable', '--now', 'portal-bitrate-auto'], check=True)
    subprocess.run(['systemctl', 'status', '--no-pager', 'portal-bitrate-auto'], check=True)


if __name__ == '__main__':
    main()
