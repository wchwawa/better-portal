# Community test report

## macOS and Windows guided terminal wizard

Offline tests cover enrollment validation and atomic saving, elapsed-time connection/confirmation deadlines, watchdog timing, cancellation and repeated attempts, relay failures, recovery failures and honest result classification. `portal_tui.py --demo` exercises the screens without network or configuration changes. These checks do not replace a real-device test of the wizard.

The [black-screen investigation](docs/macos-restoration-tests.md) includes an isolated real-kernel ARP recovery test, its before/after results, and the remaining real-device checks. New offline cases cover packets, patched retransmissions and disconnect notices arriving during restoration.

The [Windows validation guide](docs/windows-tui-validation.md) adds native terminal, UAC-launch, adapter, session-parity and kernel-lock checks. Run `python tests/integration/windows_tui_smoke.py` on native Windows to exercise the real console in all six languages with simulated networking. Physical Windows 11 playback and UAC consent still require the device checklist.

- macOS / Python / Portal firmware versions:
- Start.command opened the wizard; terminal dimensions:
- On Windows: Setup-Windows.cmd completed; Start-Windows.cmd opened the same wizard after one UAC prompt; PC LAN adapter selected correctly:
- Saved enrollment was pre-filled correctly; new enrollment saved and reloaded:
- Prerequisite keywords, editable fields and bitrate selection were clear:
- WAIT changed visibly to READY; CONNECT NOW showed a full 120-second countdown:
- Success and incomplete attempts had distinct labels and brief effects:
- Motion-free mode, monochrome terminals and 72x24 layout remained usable:
- Fresh connection: modified request, acceptance, three high target reports and local egress verified:
- Picture and controls remained usable after direct-path restoration:
- Connecting near the end of the countdown left time for confirmation:
- No-connection timeout and Q/Esc/Ctrl-C cancellation restored the direct path:
- A second guided attempt worked after cancellation or success:
- Profile, PS5-reported target, actual Portal observations and restoration errors:

Keep real configuration, reports, recovery state and captures private. Do not call a reported target a measured sustained video bitrate.


## v0.3.0 automation / Linux preview

- OS version and architecture:
- Deployment (native / Proxmox LXC / Docker macvlan) and host:
- Ethernet/Wi-Fi adapter (and Npcap version on Windows):
- Profile (65/100/200):
- Baseline picture/control usable, recovery complete:
- Foreground active trial and Portal display range:
- Windows SYSTEM task / Linux systemd / container OpenRC or Docker startup result:
- Fresh Portal disconnect/reconnect result:
- Host reboot result:
- Graceful stop recovery result:
- Crash recovery result (only if intentionally tested):
- Stutter, input-response observations (not a benchmark):
- Sanitized error message:

Do not attach real enrollment/config files, raw captures, runtime folders, credentials or private addresses. A modified startup counter is not confirmation of PS5 acceptance. Failed or untested steps should be reported as such.
