# Windows TUI validation

The Windows wizard uses `portal_tui.py`, its six translation catalogs, terminal art,
settings panel and result classifier. Native I/O stays in the Windows/Npcap adapter.
Both manual relays share the packet transform, target confirmation, connection
deadline calculation and corrective ARP retry schedule.

## Checks

Run from the project directory after installing requirements:

```sh
python -m unittest discover -s tests -v
```

The Windows session tests exercise real synthetic Ethernet/protocol bytes through
the production relay loop. The OS adapter and monotonic clock are controlled;
there is no LAN access. They check a full 120-second connection window, a late
startup, cancellation before/after preparation, repeated sessions without old
confirmation state, missing egress evidence, watchdog readiness, overlapping
attempt rejection, and repair errors. Media and startup retransmissions arriving
during handoff must still be forwarded; a disconnect must invalidate confirmation.

The Windows UI tests check long adapter IDs, arrow selection, separate Windows
configuration, saved language/profile, shared state transitions, six-language
layout, demo isolation, native recovery commands and UAC launch argument handling.
The real Windows mutex test checks that an independent recovery handle continues
to block a new attempt after the original session releases its handle.

Setup-failure regressions cover route-based adapter suggestions with multiple
adapters, saved/manual choices, stale adapter IDs, complete scrollable errors on
both hosts, and preservation of PowerShell failure reasons. The production Windows
preflight path is exercised with controlled OS responses for permission, Npcap,
route, forwarding and address-discovery failures. Each must stop before opening a
relay socket or changing network mappings. These cases reproduce failure paths;
they do not identify the cause of a user report without its full error text.

On native Windows, also run:

```bat
python tests\integration\windows_tui_smoke.py
```

This opens a private native console, runs real windows-curses drawing and keyboard
input through Prepare, Devices, simulated Connect, Result, scrollable error details and Settings in all six
languages, and fails on any drawing error. No administrator access, Npcap, PS5 or
Portal is involved. GitHub Actions runs this on Windows for Python 3.10, 3.12 and
3.14, alongside the existing macOS/Linux checks. A hosted Windows runner is not a
Windows 11 physical-device test.

The existing isolated Linux-kernel recovery test and deployment checks also remain
required because recovery code and installation file lists are shared.

## Physical Windows 11 acceptance

Use the [Windows guide](../WINDOWS.md) or [Chinese guide](../WINDOWS.zh-CN.md).
Record the exact commit, Windows build, Python/Npcap version, adapter and Portal
firmware. Check the following with your own devices:

- Double-click Setup, then Start; UAC appears once per wizard launch.
- First-launch language, live S switching, saved addresses/profile and adapter.
- Full countdown after CONNECT NOW, including connecting near its end.
- Actual picture, sound and controls after a confirmed target and restoration.
- Timeout; Q/Esc/Ctrl+C cancellation; a second attempt after either outcome.
- A second launch cannot overlap the current attempt or recovery watchdog.
- Normal Remote Play still works after stopping the tool.

Do not claim that target confirmation proves playable audio/video, actual video
throughput, lower latency or every Wi-Fi adapter's injection behavior. Recovery
reports verify local sends, not peer ARP caches. Automated tests cannot establish
those hardware outcomes, and UAC consent is still a human interaction.

## Compatibility choices

- The guided Windows flow performs preflight and watchdog readiness itself. The
  old CLI baseline requirement remains on `portal_windows.py --profile`; it is
  not an additional step in the shared wizard.
- Demo mode never needs Npcap, administrator permission or network access.
- `config.windows.json` stays compatible with the older Windows tools. Mac
  `config.json` is not overwritten. Settings writes use atomic replacement.
- No Windows firewall, registry, IP-forwarding or persistent credential changes.
- Native ARM64 Python is outside this preview's pinned Windows curses wheels;
  the user guide specifies x86-64 Python.

Dependencies and API references: [windows-curses](https://github.com/zephyrproject-rtos/windows-curses),
[Scapy/Npcap setup](https://scapy.readthedocs.io/en/stable/installation.html#windows),
[Windows UAC launch](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shellexecutew).
