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

### Npcap capture and injection regressions

The pinned Scapy 2.6.1 wrapper discards the return value of `pcap_setnonblock`
and maps negative `pcap_next_ex` results to an empty queue. Injecting a native
read error through that wrapper reproduced a Windows baseline that waited for
its entire 120-second connection window and reported `completed: true`,
`run_error: null`, and empty packet counts. The session had no working capture;
`completed` meant the loop ended, not that baseline playback succeeded.

The Windows adapter now checks the native setup and read results, preserves the
driver's error text, and copies only complete captured frames. Injection uses
`pcap_sendpacket` with its documented zero-on-success contract. Capture errors
stop the relay and enter its existing restoration path; failed restoration
retains the independent watchdog. A normally empty capture queue is still valid.
End-of-capture and inactive-handle results use their own messages instead of
repeating stale error text from an earlier operation.

`tests/test_windows_io.py` exercises the production adapter with real ctypes
packet-buffer pointers and controlled native API results. It replays both
directions through the baseline and active session loops, checks unchanged
baseline content and patched startup retransmissions, and covers capture loss,
truncated buffers, setup failures, injection failures, the egress witness, and
the Windows automatic relay. The native API is simulated: these tests establish
error handling and packet integrity, not Windows driver/device compatibility or
the root cause of a particular community report.

The focused suite is reproducible with:

```sh
python -m unittest discover -s tests -p test_windows_io.py -v
```

Local acceptance on macOS/Python 3.12 passed all 16 new I/O cases, the full
201-test suite (one Windows kernel-lock test skipped), and four tooling tests.
An additional offline smoke check used the system libpcap through the real
Scapy ctypes bindings: it copied a synthetic Ethernet frame exactly, preserved
the native savefile injection refusal, and detected EOF without repeating that
earlier send error. It did not access a network interface or Windows/Npcap.

API contracts: [capture results](https://npcap.com/guide/wpcap/pcap_next_ex.html),
[nonblocking setup](https://npcap.com/guide/wpcap/pcap_setnonblock.html), and
[packet injection](https://npcap.com/guide/wpcap/pcap_inject.html).

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

## Quick-start installation checks

The quick-start workflow also runs the shipped CMD and Windows PowerShell 5.1
entry points in a new extracted-folder model. Its path contains spaces, an
apostrophe, an ampersand, and a non-ASCII character. Checks cover a first package
download failure and retry, a healthy repeat without a package index, changed
requirements that cannot be installed, repair of a deleted native curses module,
and preservation of saved language, bitrate, and device addresses.

The freshly prepared interpreter runs the native six-language TUI smoke test.
A separate console probe follows the CMD → PowerShell → Python launch chain and
checks interactive standard handles, arguments, working directory, and exit
codes. The final Python target is replaced only in that temporary console probe;
the TUI smoke test uses the production wizard. Driver installation is simulated
to check that missing Npcap blocks completion and that setup rechecks it after
the user returns from the official download page. Concurrent setup is rejected.

CI supplies a supported Python interpreter. Downloading/installing Python with
WinGet, the fallback browser instructions, the actual Npcap installer, and human
UAC consent still need a physical Windows check. No driver, real PS5, or Portal
is involved in these automated quick-start checks.

## Physical Windows 11 acceptance

Use the [Windows guide](../WINDOWS.md) or [Chinese guide](../WINDOWS.zh-CN.md).
Record the exact commit, Windows build, Python/Npcap version, adapter and Portal
firmware. Check the following with your own devices:

- On a PC without Python/Npcap, extract the ZIP and double-click Start. Check the
  WinGet installation or official Python fallback, complete the official Npcap
  installer, and confirm the wizard opens after its UAC prompt.
- Open Start again with the Internet unavailable. Healthy dependencies are reused;
  saved settings remain. UAC appears once per wizard launch.
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
