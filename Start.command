#!/bin/zsh
set -eu
cd -- "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  printf 'Run Setup.command first, then reopen this launcher.\n'
  read 'reply?Press Enter to close. '
  exit 1
fi
printf 'Opening the guided Portal setup through the installed macOS connection helper.\n'
set +e
.venv/bin/python portal_tui.py --helper
result=$?
printf '\nWizard closed (status %s).\n' "$result"
read 'reply?Press Enter to close. '
exit "$result"
