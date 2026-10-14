#!/bin/zsh
# Read-only connection observation for a local feasibility experiment.
set -eu
BP_SOURCE_DIR="${0:A:h}"
if command -v brew >/dev/null 2>&1; then
  BP_BREW="$(command -v brew)"
elif [[ -x /opt/homebrew/bin/brew ]]; then
  BP_BREW=/opt/homebrew/bin/brew
else
  BP_BREW=/usr/local/bin/brew
fi
BP_PYTHON="$("$BP_BREW" --prefix python@3.14)/bin/python3.14"
umask 077
mkdir -p "$BP_SOURCE_DIR/research"
BP_OUTPUT="$BP_SOURCE_DIR/research/session-$(date +%Y%m%d-%H%M%S)"
exec /usr/bin/sudo "$BP_PYTHON" "$BP_SOURCE_DIR/tools/observe_portal_session.py" \
  --config "$HOME/Library/Application Support/Better Portal/config.json" \
  --output "$BP_OUTPUT"
