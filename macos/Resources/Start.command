#!/bin/zsh
set -eu
cd /
exec "${0:A:h}/PortalRuntime/PortalRuntime" tui
