## Credits

The original bitrate approach comes from **[@atameric](https://github.com/atameric)** and [ps5-portal-high-bitrate](https://github.com/atameric/ps5-portal-high-bitrate). You can [support the original creator](https://buymeacoffee.com/atameric).

Licensed under [MIT](LICENSE). Independent community software; not affiliated with Sony or PlayStation.

# Better Portal

**English** · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md) · [Türkçe](README.tr.md)

Choose a higher picture-quality target when playing your PS5 through PlayStation Portal. Better Portal guides you through the setup on **macOS or Windows**, one screen at a time.

[macOS quick start](#macos-quick-start) · [Windows quick start](#windows-quick-start) · [First session](#your-first-session) · [Find device addresses](#find-device-addresses) · [Get unstuck](#questions-and-fixes)

## Before you start

Have these ready:

- A **Mac or Windows 10/11 PC**, a **PS5** and a **PlayStation Portal**. Portal should already be able to play games from your own PS5 using Remote Play.
- All three connected to your **usual home router**. Your computer and Portal can use home Wi-Fi; PS5 can use Wi-Fi or a network cable to that router. Avoid the guest network, and disconnect a VPN on the computer if you use one.
- Internet access for installation, and permission to authorize Better Portal on your computer.

This is an experimental community tool. Start with **65 Mbps**. Bitrate describes how much picture data can be sent each second; a higher setting can help detail, but can also cause stuttering on a less stable connection.

<a id="get-started"></a>

## Quick start

You only need to install once. Keep the downloaded folder: it contains the file you will open each time you play.

Choose the instructions for **your computer**. Setup installs the dependencies once; Start opens the wizard each time you need a new Portal connection.

| Your computer | First-time setup | Start a session |
| --- | --- | --- |
| **macOS** | Double-click **Setup.command** | Double-click **Start.command** |
| **Windows 10 / 11** | Double-click **Setup-Windows.cmd** | Double-click **Start-Windows.cmd** |

### macOS quick start

<a id="a-install-python"></a>

1. **Install Python:** open [Python's Mac download page](https://www.python.org/downloads/macos/), choose a **Python 3.14 macOS installer**, and open the downloaded `.pkg`. Follow **Continue → Install**. If you already use Python 3.10 or newer, you can keep it.
2. **Finish Python setup:** in Finder, open **Applications → Python 3.14** and double-click **Install Certificates.command**. Wait for `update complete`, then close the window. For another Python version, use its matching Applications folder. See the [official installation instructions](https://docs.python.org/3.14/using/mac.html).
3. **Download Better Portal:** [download the ZIP](https://github.com/wchwawa/better-portal/archive/refs/heads/main.zip), open **Finder → Downloads**, and double-click the ZIP to expand it. Open the **better-portal-main** folder.
4. **Set up once:** double-click **Setup.command**. A Terminal window opens. Wait for **`Setup complete.`**, press **Return**, and close the window.
5. **Start a session:** double-click **Start.command** in the same folder. If **`Password:`** appears, enter your **Mac login password** and press **Return**. **No letters or dots appear while you type**; this is normal. Continue with [Your first session](#your-first-session).

If macOS blocks a launcher, see [“macOS won't open the file”](#macos-blocked). If setup fails, see [Questions and fixes](#questions-and-fixes) before starting a session.

### Windows quick start

1. **Install Python:** open [Python's Windows download page](https://www.python.org/downloads/windows/) and install **64-bit Python 3.14 (x86-64)** with the **`py` launcher**. An existing compatible x86-64 Python 3.10–3.14 installation also works.
2. **Install Npcap:** download it from [npcap.com](https://npcap.com/#download). Leave **WinPcap compatibility mode unchecked**; Wi-Fi monitor mode / raw 802.11 support is not needed. These options follow [Scapy's Windows instructions](https://scapy.readthedocs.io/en/stable/installation.html#windows).
3. **Download Better Portal:** [download the ZIP](https://github.com/wchwawa/better-portal/archive/refs/heads/main.zip). In **File Explorer → Downloads**, right-click the ZIP → **Extract All**, then open the extracted **better-portal-main** folder.
4. **Set up once:** double-click **Setup-Windows.cmd**. Wait for **`Setup complete`**, then press a key to close the window. If the offline checks fail, fix the error before starting a session.
5. **Start a session:** double-click **Start-Windows.cmd** in the same folder and accept the **Windows permission prompt**. Continue with [Your first session](#your-first-session).

Windows uses the same wizard, languages, settings and 120-second connection countdown. Its Devices screen has a **PC LAN adapter** selector. Real-device testing on Windows is still in progress; see the [Windows guide](WINDOWS.md) for detailed requirements and troubleshooting.

**For both platforms:** keep the entire extracted folder, and open its Start file for each new session. Addresses, language and bitrate are saved. You can install and launch by double-clicking these files; you do not need to edit code.

## Your first session

**Use your computer's keyboard in the wizard.** Click inside its terminal window once to focus it. The colored buttons are selected with keys, not mouse clicks. **Return** on a Mac is the **Enter** key mentioned on screen.

| Key | What it does |
| --- | --- |
| **Return / Enter** | Confirm a choice, move to the next field, or activate the highlighted button. |
| **Tab** or **↑ / ↓** | Move between device fields. The `>` marks the current row. |
| **← / →** | Change the bitrate when its row is selected. `[x]` marks the chosen option. |
| **S** | Open Settings to change language. Press the letter once; no Return needed. |

The pictures below show the **actual app in demo mode on Mac**. Windows follows the same steps and uses a PC adapter selector instead of the Mac interface field. The `DEMO` label and example addresses are for the illustrations. **Use your own device addresses and follow the timer in your app.** Click a picture to enlarge it.

### Choose your language

Use **↑ / ↓** to choose **English**, **简体中文**, **日本語**, **한국어**, **Español** or **Français**, then press **Return**. Your choice is remembered. If you go straight to Prepare, you already have a saved choice; **S** lets you change it.

![First-launch language list; the highlighted row is confirmed with Return](docs/images/language.png)

### 1. Prepare your devices

On **Portal**, swipe left from the upper-right corner to open the quick menu, then choose **Disconnect**. Leave **Put the Connected PS5 in Rest Mode** off so PS5 stays on. See [Sony's Remote Play guide](https://www.playstation.com/en-nz/support/hardware/playstation-remote-play-on-psportal/) if you need help finding the menu.

**Keep Portal switched on and connected to Wi-Fi.** You are only ending its current play session. Keep your computer awake; leave a laptop's lid open.

On your **computer**, read the yellow reminders, then press **Enter / Return** to open Devices.

![Prepare screen: same home network, Portal disconnected from PS5, and Mac awake](docs/images/prepare.png)

### 2. Enter two addresses and keep 65 Mbps

<a id="find-device-addresses"></a>
**First, find your PS5 and Portal addresses.** An IPv4 address is a device's number on your home network: four groups of numbers separated by dots. The two devices have different numbers.

1. Open the app or management page you normally use for your **home router or Wi-Fi**. Its name depends on your router or internet provider.
2. Look for **Devices**, **Connected devices** or **Clients**. Open the entry for **PS5** and write down its **IP address / IPv4 address**. Do the same for **PlayStation Portal**.
3. Keep both numbers beside you. Use the device addresses, not the router's own address, a MAC address or an internet speed-test result. **Do not copy `192.168.1.20` and `192.168.1.30` from this guide.**

For an illustrated example, [TP-Link Tether uses Local Device → Clients → the device](https://www.tp-link.com/us/support/faq/2611/). [ASUS has its own device-list guide](https://www.asus.com/us/support/faq/1005513/). If you do not know how to open your router's app or identify the devices, ask the person who set up your Wi-Fi or your internet provider for those two local addresses before continuing.

**Now fill in the Devices screen, from top to bottom:**

| Row | What to do, then press Return |
| --- | --- |
| **PS5 IPv4 address** | Type the PS5 address you found. |
| **Portal IPv4 address** | Type the Portal address you found. |
| **Mac LAN interface** — macOS only | Usually leave the suggested value, such as `en0`. If blank or using another adapter, [check it here](#mac-adapter). |
| **PC LAN adapter** — Windows only | Use **← / →** to select the Wi-Fi or Ethernet adapter connected to your home router. |
| **Bitrate (Mbps)** | Leave **65 recommended** selected for your first try. |
| **Save and prepare connection** | Press Return to begin. Keep Portal disconnected for now. |

When you move into a field, typing replaces its previous value. Use **↑** to go back if you make a mistake. Addresses and bitrate are saved for the next run.

![Devices screen at first use: the PS5 input is highlighted, with type here beside it](docs/images/devices-input.png)

<details>
<summary>Watch the keyboard steps and the moving 65 Mbps recommendation</summary>

This example enters sample addresses, leaves the suggested adapter, keeps 65 Mbps and moves to the start button. It loops; your inputs will stay on screen.

![Keyboard progression through both addresses, the Mac adapter, the animated 65 Mbps choice and the start button](docs/images/devices.gif)

</details>

<details>
<summary>What about 100 or 200 Mbps?</summary>

On the bitrate row, use **← / →** or **Space** to choose. Try **100 Mbps** after a stable 65 Mbps session. **200 Mbps** is experimental and may increase stuttering. Compare the same game scene; more is not always better.

</details>

### 3. Wait on your computer, then connect on Portal

**First: WAIT means wait.** Leave Portal disconnected while your computer checks the devices and prepares the connection.

![WAIT screen: keep Portal disconnected while the app checks the devices](docs/images/connect-wait.png)

**Next: READY / CONNECT NOW means pick up Portal.** On Portal's Remote Play home screen, select your PS5 and connect as you normally would. You have **120 seconds**, starting at **02:00** in the wizard. The app is waiting for **you to make this connection on Portal**.

![READY screen: connect Portal to PS5 now, while the two-minute countdown runs](docs/images/connect-ready.png)

When Portal connects, leave it connected. Wait for the **Result** screen on your computer before closing anything. If the timer runs out, follow the retry instructions in the result.

To stop early, press **Q** on your computer and wait for the result. Keep the computer awake while it restores the connection.

<details>
<summary>Watch a shortened connection example</summary>

This repeating demo moves from WAIT to READY, connection checks and success. It uses simulated events and a shortened wait. **Your app's countdown is the one to follow.**

![One simulated successful attempt from device checks through READY to the result](docs/images/connect.gif)

</details>

### 4. Check the bitrate target, then check Portal

A green **Bitrate target confirmed** with **`[OK]`** means PS5 reported the higher target. **Check picture, sound and controls on Portal before playing.** The tool cannot verify playback or the devices' address mappings. If the screen stays black, disconnect and reconnect normally without Better Portal, then report the problem. Keep the computer awake until restoration finishes. Press **Q** to quit; when the launcher says `Press Enter to close`, press Enter / Return and close its window.

The screenshots and animations show an earlier version, which called this result **Ready to play**. That message also confirmed the target only.

![Successful result: Ready to play and a green OK link between Portal and PS5](docs/images/result-success.png)

A number such as **63.106 Mbps** is the target PS5 reported, **not a measurement of actual video throughput**. Your computer no longer needs to relay this session.

**Next time you disconnect or turn off Portal:** open **Start.command** on Mac or **Start-Windows.cmd** on Windows and repeat the four steps. Saved addresses will be filled in; check them if your network has changed.

## If your result is different

These are **alternative outcomes**, not stages you should wait through after success.

| Message in the wizard | Your next action |
| --- | --- |
| **No new connection detected** / **No compatible startup captured** | Disconnect Portal from PS5. Press **Return** to retry. Connect on Portal only after the next READY prompt. |
| **Higher target not confirmed** / **Target reported; verification incomplete** | Press **D** for details. After network restoration, reconnect normally or retry with 65 Mbps. |
| **Attempt stopped** | Read the restoration status. If restored, retry with Return or quit with Q. |
| **Network recovery needs attention** | Keep the computer awake. Press **D** for recovery details and wait for recovery before another attempt. |

<details>
<summary>See separate retry and recovery examples</summary>

**No new connection:** start another attempt and make a fresh Portal connection after READY.

![Example of a finished attempt with no new Portal connection detected](docs/images/result-timeout.png)

**Recovery needs attention:** keep the computer awake and follow D: details.

![Example of an incomplete network restoration, with recovery instructions](docs/images/result-recovery.png)

The [result animation](docs/images/result-terminal-art.gif) shows separate simulated outcomes for comparison; one successful session does not pass through all of them.

</details>

## Language settings

Press **S**, use the **arrow keys** to choose a language, then **Enter**, **Esc** or **S** to return. Changes apply immediately and are saved; Esc closes the panel without undoing the change. Your inputs and current step stay in place.

During connection, the countdown continues while Settings is open. **Q** still stops the attempt. The panel closes when network restoration starts.

<details>
<summary>See live language switching and the four additional translations</summary>

![Settings switching instantly through six languages, then returning to the same form](docs/images/settings.gif)

![The same device screen in Japanese, Korean, Spanish and French](docs/images/languages.gif)

</details>

<a id="troubleshooting-and-recovery"></a>

## Questions and fixes

**Windows setup, permissions, Npcap or adapter selection?**

Use the [Windows troubleshooting guide](WINDOWS.md#questions-and-fixes). The `.command` files and Mac interface instructions below are for macOS.

<a id="macos-blocked"></a>
**macOS won't open the file: “developer cannot be verified” or “Apple cannot check…”**

After trying to open the file downloaded from this repository, go to **Apple menu → System Settings → Privacy & Security**. Find its blocked-file notice, choose **Open Anyway**, then confirm **Open** if you trust this download. [Apple's illustrated instructions](https://support.apple.com/en-us/102445) explain the prompts. A “will damage your computer” alert is a different case; stop and follow Apple's guidance for that alert.

**Setup shows a Python or certificate error instead of “Setup complete”.**

Complete the [macOS Python steps](#macos-quick-start), including **Install Certificates.command**. Close the failed setup window, then reopen **Setup.command**. If it still fails, copy the error text when asking for help.

**The password doesn't work, or says the account cannot use sudo.**

Use your Mac login password. If your Mac account is not an administrator, ask the person who manages the Mac to help authorize the launch.

**The text is cut off or the app asks for a larger window.**

Drag a corner of the Terminal window to enlarge it. The app needs at least 72 columns and 24 rows of text. It resumes when there is enough space.

**A device did not respond, or the picture stutters.**

Keep PS5 and Portal awake. Recheck both current addresses and the home Wi-Fi connection. For stuttering, try 65 Mbps or disconnect Portal and reconnect normally without Better Portal.

**Will it save my administrator password?**

No. macOS or Windows controls authorization. Retrying inside the same open wizard does not ask again.

**How do I get help?**

[Open an issue](https://github.com/wchwawa/better-portal/issues) with the step and message shown, your computer's operating system and Portal versions, and selected bitrate. Remove device addresses from screenshots before sharing. Raw reports and packet captures can contain private network information; keep them local.

<a id="terminal-help"></a>

<details>
<summary>macOS Terminal help: opening the folder, preview mode and a missing Python file</summary>

To open Terminal manually, press **Command (⌘) + Space**, type **Terminal**, then press Return.

1. Type `cd` followed by **one space**.
2. Drag the **better-portal-main folder** from Finder into the Terminal window, then press Return. This tells Terminal which folder to use.
3. Copy **one command at a time** from below, paste it into Terminal and press Return. Copy only the command text.

If Start cannot find `.venv/bin/python`, run setup from this folder first:

```sh
./Setup.command
```

Then launch a real session:

```sh
./Start.command
```

To **preview only**, after setup:

```sh
.venv/bin/python portal_tui.py --demo
```

To **preview without animation**:

```sh
.venv/bin/python portal_tui.py --demo --no-animations
```

Both preview commands simulate a connection without your devices. They need no administrator password, change no networking and save no settings. Quit the preview before opening Start.command for a real session.

</details>

<a id="mac-adapter"></a>

<details>
<summary>The Mac LAN interface is blank, or I use a USB / Ethernet adapter</summary>

The interface is a name such as `en0`, not your Wi-Fi name or an IP address. To check it, open Terminal using the instructions above and run:

```sh
networksetup -listallhardwareports
```

For Wi-Fi, find the **Hardware Port: Wi-Fi** section and use the name beside **Device:**. For a cable connection, use the section for the connected Ethernet adapter. Enter that Device name in Better Portal. If you cannot tell which adapter is in use, include this question when asking for help.

</details>

<details>
<summary>Already use Git and Terminal on Mac?</summary>

```sh
git clone https://github.com/wchwawa/better-portal.git
cd better-portal
./Setup.command
./Start.command
```

</details>

**Linux?** See the upstream [Linux / automatic setup guide](https://github.com/atameric/ps5-portal-high-bitrate/blob/main/AUTOMATION.md).
