#!/usr/bin/env python3
"""Verify a development bundle without sudo, registration, or live networking."""
import json
import os
from pathlib import Path
import plistlib
import subprocess
import fcntl
import pty
import select
import shutil
import struct
import tempfile
import termios
import time

STAGE = Path(__file__).resolve().parents[1] / 'build/installer-root'
BASE = STAGE / 'Library/Application Support/Better Portal'
APP = BASE / 'Better Portal.app'
PROTECTED = BASE / 'Private'
LAUNCHER = STAGE / 'Applications/Better Portal.app'
runtime = APP / 'Contents/Resources/PortalRuntime/PortalRuntime'
subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(APP)], check=True)
subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(LAUNCHER)], check=True)
subprocess.run(['/usr/bin/codesign', '--verify', '--strict',
                str(PROTECTED / 'PortalRuntime/PortalRuntime')], check=True)
assert PROTECTED.stat().st_mode & 0o077 == 0
assert BASE.stat().st_mode & 0o022 == 0
assert not (LAUNCHER / 'Contents/Library/LaunchDaemons').exists()
assert (PROTECTED / 'PortalRuntime/PortalRuntime').read_bytes() == runtime.read_bytes()
with tempfile.TemporaryDirectory(prefix='better-portal-tamper-') as temporary:
    tampered = Path(temporary) / 'PortalRuntime'
    shutil.copy2(PROTECTED / 'PortalRuntime/PortalRuntime', tampered)
    with tampered.open('r+b') as stream:
        stream.seek(4096)
        original = stream.read(1)
        assert original
        stream.seek(4096)
        stream.write(bytes([original[0] ^ 1]))
    result = subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(tampered)],
                            capture_output=True)
    assert result.returncode != 0, 'Modified root worker passed code-signature verification'
info = plistlib.loads((APP / 'Contents/Info.plist').read_bytes())
assert info['CFBundleIdentifier'] == 'com.wchwawa.betterportal'
job = plistlib.loads((APP / 'Contents/Library/LaunchDaemons/com.wchwawa.betterportal.helper.plist').read_bytes())
assert job['BundleProgram'] == 'Contents/MacOS/PortalHelper'
assert job['AbandonProcessGroup'] is True
assert set(job['MachServices']) == {'com.wchwawa.betterportal.helper'}
for language in ('zh-CN', 'ja', 'ko', 'es', 'fr'):
    catalog = json.loads((APP / f'Contents/Resources/locales/{language}.json').read_text())
    assert catalog['Enable connection helper']
assert os.access(APP / 'Contents/Resources/Start.command', os.X_OK)
result = subprocess.run([str(runtime), '--help'], capture_output=True, text=True, check=True)
assert 'worker' in result.stdout and 'tui' in result.stdout
subprocess.run([str(runtime), 'self-test'], check=True)
result = subprocess.run([str(runtime), 'worker', '--caller-uid', '501'], capture_output=True, text=True)
assert result.returncode != 0 and 'installed macOS connection helper' in result.stderr
result = subprocess.run([str(APP / 'Contents/MacOS/PortalBridge')], input='', capture_output=True, text=True)
assert result.returncode != 0
assert 'signed' in result.stdout or 'normal Mac user' in result.stdout

# Draw the actual frozen curses UI in a private terminal, then leave the demo.
# The --demo path neither saves settings nor submits a helper session.
master, slave = pty.openpty()
fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 100, 0, 0))
process = subprocess.Popen([str(runtime), 'tui', '--demo', '--no-animations'],
                           stdin=slave, stdout=slave, stderr=slave,
                           env=dict(os.environ, TERM='xterm-256color'))
os.close(slave)
screen = bytearray()
try:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if select.select([master], [], [], .1)[0]:
            screen.extend(os.read(master, 65536))
        if b'guided setup' in screen.lower():
            break
    assert b'guided setup' in screen.lower(), screen.decode(errors='replace')
    os.write(master, b'q')
    deadline = time.monotonic() + 10
    while process.poll() is None and time.monotonic() < deadline:
        if select.select([master], [], [], .1)[0]:
            try:
                screen.extend(os.read(master, 65536))
            except OSError:
                break  # macOS reports EIO when the slave terminal closes.
    assert process.wait(timeout=2) == 0, screen.decode(errors='replace')
finally:
    if process.poll() is None:
        process.kill()
        process.wait(timeout=5)
    os.close(master)
print('Development bundle verified: signatures, tamper rejection, job, resources, frozen imports, real TUI, privileged-operation rejection')
