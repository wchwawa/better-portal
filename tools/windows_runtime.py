"""Small, read-only checks for the Windows first-launch setup."""
import argparse
import importlib
from importlib import metadata
from pathlib import Path
import re
import sys
import sysconfig


def check_python():
    if (sys.platform != 'win32' or not (3, 10) <= sys.version_info[:2] < (3, 15)
            or sysconfig.get_platform() != 'win-amd64'):
        raise RuntimeError('Python 3.10-3.14 for x64 Windows is required.')


def check_dependencies(requirements):
    for line in Path(requirements).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        entry = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)(?:; sys_platform == 'win32')?", line)
        if not entry:
            raise RuntimeError('Unsupported dependency entry: ' + line)
        if metadata.version(entry[1]) != entry[2]:
            raise RuntimeError('Dependency needs updating: ' + entry[1])
    # A matching package record alone does not establish that its native module loads.
    importlib.import_module('curses')
    importlib.import_module('scapy.all')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('check', choices=('python', 'dependencies', 'npcap'))
    parser.add_argument('--requirements', type=Path, default=Path(__file__).resolve().parents[1] / 'requirements.txt')
    args = parser.parse_args()
    try:
        check_python()
        if args.check == 'python':
            print(sys.executable)
        elif args.check == 'dependencies':
            check_dependencies(args.requirements)
            print('DEPENDENCIES_READY')
        else:
            if not importlib.import_module('scapy.all').conf.use_npcap:
                raise RuntimeError('Npcap is not available.')
            print('NPCAP_READY')
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
