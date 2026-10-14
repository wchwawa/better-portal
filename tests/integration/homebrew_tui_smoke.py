"""Open the installed Homebrew wizard in a private PTY; never run a live session."""
import errno
import fcntl
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import time


def main():
    binary = str(Path(sys.argv[1]).resolve())
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 100, 0, 0))
    child = subprocess.Popen([binary, '--demo', '--no-animations'],
                             stdin=slave, stdout=slave, stderr=slave,
                             env=dict(os.environ, TERM='xterm-256color'), start_new_session=True)
    os.close(slave)
    output = bytearray()
    quit_sent = False
    deadline = time.monotonic() + 20
    try:
        while time.monotonic() < deadline:
            if select.select([master], [], [], .1)[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError as exc:
                    if exc.errno != errno.EIO:
                        raise
                    chunk = b''
                output.extend(chunk)
            if not quit_sent and b'Better Portal' in output:
                os.write(master, b'q')
                quit_sent = True
            if child.poll() is not None:
                break
        assert quit_sent, 'Installed wizard never drew its initial screen: ' + repr(output[-3000:])
        assert child.poll() == 0, 'Installed wizard did not exit cleanly: ' + repr(output[-3000:])
        print('Installed Homebrew wizard opened and exited without sudo or network changes.')
    finally:
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
        os.close(master)


if __name__ == '__main__':
    main()
