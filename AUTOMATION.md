# Automatic relay preview: Windows, Linux and macOS

The owner confirmed an always-on Mac mini prototype with a real PS5/Portal. This release ports that one-way design to a common engine. **Windows automation still awaits physical validation. A community tester has now reported Linux/Pi installation, reboot and reconnect success; crash recovery and broader compatibility remain unverified.** The common engine's macOS service packaging is not included; the existing macOS manual launcher remains available. This is a community testing prerelease, not guaranteed support.

## What changes

Leave one computer powered on, awake and connected to the same directly connected IPv4 LAN as your PS5 and Portal. Ethernet is recommended for the relay host. Enroll exactly those two devices and reserve their IP addresses in your router. No USB connection is used.

The service continuously redirects only Portal-to-PS5 control/outbound traffic through that computer. It applies the selected 65/100/200 Mbps request patch to each matching new session startup. PS5-to-Portal video takes the direct path. This differs from the manual launcher, which leaves the path after a bounded experiment. There is still an extra hop on the control path; latency is unmeasured. No 4K, upscaling or guaranteed 200 Mbps throughput is added.

The packet-layout gate and inferred offsets have the same firmware limitations as the original launcher. A `unique_modified_startups` count proves only a locally sent mutation. The Portal display and a playable session must confirm the result. Auto mode does not intercept the console's bitrate response and cannot report PS5 acceptance.

## Windows 10/11 preview

1. Download and extract the new prerelease ZIP to a trusted local folder. Do not mix files from older releases.
2. Install **64-bit Python 3.10+ from [python.org](https://www.python.org/downloads/windows/)**. For the startup task, use the full installer, select installation for all users under `C:\Program Files`, and install the Python launcher. A Microsoft Store or per-user Python installation is not suitable for the SYSTEM task.
3. Install [Npcap](https://npcap.com/#download), with WinPcap API-compatible mode. Normal Ethernet framing is required; do not enable Wi-Fi monitor mode. This project does not bundle Npcap. Reboot if its installer requests it.
4. Run `Setup-Windows.cmd`. It creates `.venv`, installs the pinned Scapy dependency and runs offline tests. If `py -3` chooses a per-user Python, recreate `.venv` using your all-users Python's full path before proceeding.
5. Keep Portal on and connected to Wi-Fi. Right-click `Auto-Windows.cmd`, choose **Run as administrator**, enter `Configure`, then profile `65` for the first test. Select the **menu number** of the Ethernet/Wi-Fi adapter connected to your PS5/Portal LAN, then enter both device IPv4 addresses. The PC IP printed beside the adapter is information only. Older preview.1 asks for an interface name/GUID: use the adapter name or full Npcap device ID, never the PC IP. Their MAC addresses are enrolled locally. Use no VPN, guest network or client isolation.
6. Disconnect Portal's play session. Run the same menu as administrator, choose `Baseline`. After **BASELINE READY**, connect Portal and check picture and controls for 60 seconds. This forwards without changing the bitrate. A receipt is saved only if outbound traffic was forwarded and recovery completed. It does not automatically verify video or responsiveness.
7. If baseline is usable, choose `Run` for a foreground active trial. After **AUTO READY**, disconnect/reconnect Portal. Check the Portal's network display and play a moving scene. Stop with Ctrl+C and allow restoration. If this fails, do not install the task.
8. Choose `Install` only after those tests. Confirm your baseline observation. The installer copies an allowlist of files into an Administrators/SYSTEM-only folder under `C:\ProgramData\PortalBitrateAuto`, creates its own virtual environment and registers `PortalBitrateAutoPreview` in Task Scheduler as SYSTEM at startup. It starts the task now. No account password/token is saved.
9. Use `Status` to check both Task Scheduler and timestamped relay reports. Disconnect/reconnect Portal again, then reboot the PC and repeat to validate unattended startup. Keep the PC awake while playing.

`Start`, `Stop`, `Status`, `Uninstall` are in the same administrator menu. `Stop` writes a persistent disable marker and waits for graceful recovery. A disabled task stays disabled across reboot until `Start`. `Uninstall` unregisters the task but retains private files for diagnosis. Do not force-end a running guardian or remove files before restoration.

If installation rejects the Python path, reinstall Python for all users and recreate the source `.venv`. If the guardian cannot escape a Windows job or open Npcap under SYSTEM, startup fails before redirecting traffic. Report that failure; do not remove the check. A task registered successfully does not prove a working relay.

## Native Linux preview

Initial target: Debian/Ubuntu-style native Linux with Ethernet, Python 3.10+, iproute2, libpcap and systemd. Other distributions require equivalent packages. A Raspberry Pi 3B running Raspberry Pi OS has a community success report below; its OS architecture/version was not supplied, so ARM64 compatibility is not established. WSL, NAT-based Docker/VM networking, Android and router firmware are not supported deployment targets. The separate experimental Proxmox LXC / Linux Docker macvlan path is described below.

```sh
sudo apt update
sudo apt install python3 python3-venv python3-pip iproute2 libpcap0.8
# In the extracted release folder:
sh Auto-Linux.sh setup
sh Auto-Linux.sh configure 65
```

The configure step asks for the physical LAN interface (for example `eth0` or `enp3s0`) and both IPv4 addresses. Find yours with `ip -br link` and `ip -br addr`. Both devices must be reachable on the LAN during enrollment.

1. Disconnect Portal's play session. Run `sh Auto-Linux.sh baseline` and connect after **BASELINE READY**. Check picture and controls during the 60-second unchanged relay trial.
2. If usable, run `sh Auto-Linux.sh run`. Connect after **AUTO READY**, check the Portal display and play. Ctrl+C stops and repairs its ARP entry.
3. Only after a successful foreground trial, run `sh Auto-Linux.sh install`. This asks you to confirm the baseline observation. It installs root-owned code/venv under `/opt/portal-bitrate-auto`, private runtime files under `/var/lib/portal-bitrate-auto`, and a systemd service named `portal-bitrate-auto`.
4. Check `sh Auto-Linux.sh status`. Reconnect Portal and then reboot Linux to validate automatic startup on your hardware.

```sh
sh Auto-Linux.sh stop
sh Auto-Linux.sh start
sh Auto-Linux.sh status
sh Auto-Linux.sh uninstall
# Logs, for local inspection only:
sudo journalctl -u portal-bitrate-auto -n 50 --no-pager
```

Stop persists across reboot until Start. Uninstall disables/removes the unit, retaining private code/config/logs for your review. Upgrades intentionally refuse to overwrite an installation: stop/uninstall, back up private data, remove the old installation directories and repeat setup/baseline with the new release.

## Community Linux report (2026-09-30)

[Tester tissee reports](https://www.reddit.com/r/PlaystationPortal/comments/1wtyglf/comment/pd2k5ls/) successful use on an EndeavourOS notebook and on a Raspberry Pi 3B running Raspberry Pi OS over Ethernet. On the Pi, the tester confirmed systemd startup after reboot, a fresh Portal reconnect and the 100 Mbps profile working when PS5 wakes from rest mode. Exact distro releases, OS architecture, sustained video throughput and input latency were not supplied. This is a community report, not a maintainer-run benchmark or a universal compatibility guarantee. Crash recovery and long-duration stability still need validation.

The tester had to resolve IPv4 forwarding being enabled/reapplied by Docker. Our relay refuses to start with forwarding enabled and does not change that setting. [Docker documents](https://docs.docker.com/engine/network/packet-filtering-firewalls/#docker-on-a-router) that its usual iptables backend can enable forwarding at startup; Docker bridge networking requires forwarding. Disabling it on a shared Docker host can disrupt container networking. Use a dedicated relay host when those requirements conflict; do not blindly disable forwarding or remove the relay check. This report covers native Linux, not running this relay inside Docker.

## Proxmox LXC and Docker (community)

[deploy/](deploy/README.md) runs this same relay in an unprivileged Alpine LXC bridged on Proxmox VE, or in a Linux Docker container on a `macvlan` network. Both give the relay its own MAC and network namespace on the PS5/Portal LAN. Forwarding is turned off only inside the documented container. Proxmox has a contributor report with a real PS5 and Portal; Docker has synthetic tests from the contributor's fork, with no real-device validation. These are optional experimental deployments. The same baseline, foreground trial and reboot checks apply. **The Proxmox creator disables filtering on the new relay CT's NIC (`firewall=0`), not the host-wide firewall; read the firewall scope and test limits in the deployment guide first.** Contribution: [SDNick484, PR #1](https://github.com/atameric/ps5-portal-high-bitrate/pull/1).

## Recovery and limitations

A separate guardian watches the relay's pipe/heartbeat. On normal stop or process failure it sends corrective ARP replies; on a stalled relay it terminates the exact parent before repair. A recovery marker blocks restart after unconfirmed repair. On Linux the service gives the guardian a grace period before group termination. Windows uses a separate process group outside the task job, if the OS allows it.

Power loss, cable removal, host sleep, capture-driver failure or terminating both processes can prevent repair. Reconnect Portal to refresh its network state, and check host logs. This is why a real crash/reboot test is still needed on each platform. If a stale recovery marker remains, first stop the task/service and verify no relay or guardian remains, then use `portal_auto.py repair` with the installed Python and the installed `--runtime` directory. It asks for `STOPPED` before sending repair frames. Do not delete a live lock to start a second relay.

The native Windows/systemd service does not enable IP forwarding, edit a firewall, open a remote control port or change firmware. Existing forwarding causes a refusal. The optional container deployment has its own forwarding and NIC-filtering setup described above. Keep DHCP reservations stable. Changed MAC enrollment is rejected when a conflicting live ARP response is observed at startup. This is not a defense against a hostile LAN.

To change profile or device addresses, stop/uninstall the service, configure again, repeat baseline and reinstall as described above. Start with 65; 100/200 are more demanding targets and may add stutter or latency without visible benefit.

## Share test results safely

Use [TESTING.md](TESTING.md). Share OS/version, adapter type, Npcap version on Windows, profile, whether baseline/foreground/startup/reconnect worked, display range and stutter. Remove personal information from errors before posting. **Do not upload `auto-config.json`, `config*.json` containing real enrollment, `auto-runtime`, ProgramData/var-lib runtime directories, packet captures, environment files, tokens or keys.** No raw captures or session payloads are retained by auto mode; logs/status still contain local operational information.
