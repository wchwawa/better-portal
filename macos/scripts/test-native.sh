#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
DEVELOPER=$(xcode-select -p)
FRAMEWORKS="$DEVELOPER/Library/Developer/Frameworks"
if [ -d "$FRAMEWORKS/Testing.framework" ]; then
    # Command Line Tools contain Swift Testing but do not add this path.
    exec swift test --package-path "$ROOT/macos" --disable-xctest \
        -Xswiftc -F -Xswiftc "$FRAMEWORKS" -Xlinker -rpath -Xlinker "$FRAMEWORKS" \
        -Xlinker -rpath -Xlinker "$DEVELOPER/Library/Developer/usr/lib"
fi
exec swift test --package-path "$ROOT/macos" --disable-xctest
