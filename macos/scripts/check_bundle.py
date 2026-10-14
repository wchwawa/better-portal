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
import struct
import termios
import time

APP = Path(__file__).resolve().parents[1] / 'build/installer-root/Better Portal.app'
runtime = APP / 'Contents/Resources/PortalRuntime/PortalRuntime'
subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(APP)], check=True)
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
        if b'better portal' in screen.lower():
            break
    assert b'better portal' in screen.lower(), screen.decode(errors='replace')
    os.write(master, b'\x1b')
    assert process.wait(timeout=5) == 0, screen.decode(errors='replace')
finally:
    if process.poll() is None:
        process.kill()
        process.wait(timeout=5)
    os.close(master)
print('Development bundle verified: signatures, job, resources, frozen imports, real TUI, privileged-operation rejection')
