# Windows guided setup

[简体中文](WINDOWS.zh-CN.md) · [Back to Better Portal](README.md)

Better Portal uses the **same terminal wizard on Windows and Mac**: choose a language, check the prerequisites, enter your device addresses, choose a bitrate, wait for **CONNECT NOW**, and check the result. Windows uses Npcap for the network connection and the normal Windows permission prompt for administrator access.

This is a **Windows preview**. Automated checks cover the native Windows terminal and session logic; real PS5/Portal playback on Windows still needs device testing. A confirmed target is not proof of working picture, sound, lower latency or sustained video bitrate.

## Install once

You need an x64 Windows 11 or Windows 10 PC, a PS5 and a PlayStation Portal. Ordinary Remote Play must already work. Connect all three to the same home router; PS5 can use Ethernet. Keep Portal on Wi-Fi but disconnected from its PS5 session, and keep the PC awake. Native ARM64 PCs are not supported by this quick start yet.

1. Download the [Better Portal ZIP](https://github.com/wchwawa/better-portal/archive/refs/heads/main.zip). In File Explorer, right-click it → **Extract All**. Open the extracted folder. Keep all its files together; do not run files inside the ZIP or copy a Mac `.venv` folder.
2. Double-click **Start-Windows.cmd**. It reuses a supported x64 Python 3.10–3.14 installation, or installs Python 3.14 with Windows Package Manager. If the package manager is unavailable, it opens [Python's official page](https://www.python.org/downloads/windows/): install Python 3.14 using **Windows installer (64-bit)**, then return to the setup window and press Enter. Application dependencies are installed automatically.
3. If Npcap is missing, its [official download page](https://npcap.com/#download) opens. Download and run the installer, accepting the Windows permission prompt. Leave **WinPcap compatibility mode unchecked**. Wi-Fi monitor mode / raw 802.11 support is not needed. Administrator-only access is fine. These options follow [Scapy's Windows instructions](https://scapy.readthedocs.io/en/stable/installation.html#windows). Finish the installer, return to the setup window, then press **Enter**. If it requests a restart, restart and open Start-Windows.cmd again.
4. Once dependencies are ready, the wizard opens automatically. Accept its Windows permission prompt and follow the steps below. There is no separate Setup step to remember.

You do not need Git or Wireshark. Installation downloads Scapy and [windows-curses](https://github.com/zephyrproject-rtos/windows-curses). Npcap is installed from its own website and is not bundled; its free installer requires [interactive installation](https://npcap.com/guide/npcap-users-guide.html). Already installed dependencies are reused. **Setup-Windows.cmd** remains available if you want to prepare dependencies without opening the wizard.

## Every time you play

**Double-click Start-Windows.cmd.** Accept the Windows **User Account Control** prompt. If your account needs an administrator’s credentials, Windows asks for them. Better Portal does not collect or save passwords. Repeated attempts in the same open wizard reuse that authorization. The launcher uses Windows’ [standard `runas` operation](https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shellexecutew).

On first launch, choose **English, 简体中文, 日本語, 한국어, Español or Français**. Your choice is saved. Press **S** later to change language without restarting.

1. **Prepare:** keep Portal disconnected from PS5, keep PS5 on, and check that PC, PS5 and Portal use the same home network.
2. **Devices:** enter the PS5 and Portal **IPv4 addresses** from your router’s device list. On first use, **PC LAN adapter** suggests the connection Windows uses to reach both devices directly. Check it, or use **← / →** to choose your Wi-Fi or Ethernet connection. Saved and manual choices are kept. If no connection can be suggested, choose it yourself and check both addresses. Choose **65 Mbps** for your first attempt, then **Save and prepare connection**. Use Tab or ↑ / ↓ to move between rows and Enter to continue.
3. **Connect:** keep Portal disconnected during **WAIT**. When **CONNECT NOW** appears, connect Portal to PS5 normally. The **120-second countdown** starts at that prompt. A request near the end still gets its own confirmation window. Follow the terminal art as the request, PS5 acceptance and target reports arrive.
4. **Result:** **Bitrate target confirmed** means the software observed the higher target, checked local packet egress and completed its restoration steps. **Check picture, sound and controls on Portal.** If the screen is black, disconnect and reconnect normally without Better Portal. Press **D** for local report/recovery details, **Enter** to retry when allowed, or **Q** to quit.

The [illustrated README](README.md#your-first-session) shows the shared wizard. Those images were recorded on Mac in demo mode; Windows uses the PC adapter selector and Windows launchers described here.

Addresses are saved in `config.windows.json`; language and bitrate in `tui-settings.json`. The Mac’s `config.json` is separate. Disconnecting or turning off Portal ends the session: run **Start-Windows.cmd** again for the next connection.

To make a desktop shortcut, right-click **Start-Windows.cmd** → **Show more options** → **Send to → Desktop (create shortcut)**. Keep the original project folder in place.

## Questions and fixes

**Do I need my PlayStation account credentials?**

No. Better Portal does not ask for your PSN username or password. Enter the two local device addresses and choose your PC’s network adapter.

**Python installation failed.**

Read the error in the setup window, check your Internet connection, and reopen **Start-Windows.cmd** to retry. You can also install x64 Python 3.14 from the official page above. The launcher looks for the installed interpreter directly; you do not need to edit PATH or run `py` yourself.

**The wizard cannot import curses, or closes during startup.**

Reopen **Start-Windows.cmd**. It checks package versions and imports, and retries preparation when a dependency is missing or broken. The setup error stays visible until you press Enter. Keep the extracted folder writable and close any other setup window. Do not run the live wizard through WSL or a notebook.

**No LAN adapter is available, or the check reports Npcap missing.**

Install Npcap, close the wizard and reopen **Start-Windows.cmd**. Keep the intended Wi-Fi or Ethernet adapter connected. Choose that adapter instead of a VPN or loopback interface. If Windows permission was cancelled, reopen the launcher and accept the prompt.

**It goes straight from Devices to “Setup check failed” or “Could not finish”.**

Read the error below the title. Press **D**, then **↑ / ↓**, to read the full error; press Enter or Esc to return. “Setup check failed” means a check stopped the attempt before network mappings changed. If the error names a different connection, retry and select it under **PC LAN adapter**. For other errors, follow the instructions below or share the full error text with private addresses removed. The title alone does not identify the cause.

**A device cannot be reached, or the route/forwarding check fails.**

Keep both devices awake, check their current IPv4 addresses, and select the adapter on the same home LAN. Avoid guest Wi-Fi, client isolation, VPN routes and Internet Connection Sharing on that adapter. The tool checks routing and forwarding; it does not change firewall, registry or forwarding settings. Do not disable the firewall to work around an error.

**There is no new connection, or the countdown expires.**

Disconnect Portal from PS5. Retry in the wizard and reconnect only after the next **CONNECT NOW** prompt. Previously saved settings remain available. Q, Esc or Ctrl+C during the connection attempt stops it and runs restoration before showing the result.

**Network recovery needs attention.**

Keep the PC awake. Press **D** and read the report path and automatic recovery deadline. The independent watchdog retains a machine-wide lock while recovery is pending; another attempt cannot run over it. The wizard also disables retry after a recovery error.

If recovery still fails after the displayed deadline, wait until the attempt/watchdog has stopped. In **PowerShell opened as administrator**, use the exact recovery command shown by **D** with a state file created by this tool. Do not delete locks to force a retry. Reconnecting the devices’ network connections can also refresh their mappings. A powered-off PC cannot run its watchdog.

## Optional diagnostic commands

The guided path does **not** require running separate Check, Configure or Baseline launchers. They remain available for troubleshooting. The legacy command-line bitrate probe still requires a successful baseline receipt for the same configuration.

From the project folder in an administrator terminal:

```bat
.venv\Scripts\python.exe portal_windows.py --check
.venv\Scripts\python.exe portal_windows.py --baseline
.venv\Scripts\python.exe portal_windows.py --profile 65
```

Each baseline or bitrate attempt needs a fresh Portal connection after READY. These legacy commands keep their shorter 35-second connection window. The TUI uses 120 seconds.

Preview the actual UI without administrator permission, Npcap or devices:

```bat
.venv\Scripts\python.exe portal_tui.py --demo
```

Add `--no-animations` for a motion-free preview. Demo mode does not save settings or change networking.

For an always-on service, see [AUTOMATION.md](AUTOMATION.md). Do not run that service and the manual wizard at the same time.

## Report a Windows 11 test

Use the [Windows test issue template](https://github.com/wchwawa/better-portal/issues/new?template=windows-test.md). Include the version, Windows build, Python/Npcap versions, adapter, Portal firmware, last visible stage and whether picture/sound/controls worked after restoration. Report cancellation and a second attempt too.

See [validation details](docs/windows-tui-validation.md) for what automated checks establish. Keep configuration, recovery files and captures private. Share only redacted report fields; a reported target bitrate is not measured throughput.
