# macOS authorization: approve setup, then use normally

**Status: implemented as a packaged-app preview; signed installation and physical-device acceptance are still pending.** Source and Homebrew launchers, including a direct `portal_tui.py` launch, require the signed helper for live sessions; they never launch Python with sudo. The old direct `portal_active_probe.py` macOS live command is disabled. An ad hoc development build cannot enable the privileged helper. There is no released signed installer to download yet, so these launchers currently support demo mode only.

## Using the packaged app

This flow requires macOS 13 or later and a signed Better Portal installer for your Mac's architecture. The installer includes Python and the existing six-language TUI.

1. Open the Better Portal `.pkg` installer and follow the macOS installation prompts. It installs **Better Portal** in **Applications**.
2. Open **Applications → Better Portal**. Choose **Enable connection helper**.
3. Approve Better Portal in the macOS permission flow. If the app says approval is needed, choose **System Settings**, allow Better Portal's background helper, then return to the app. Cancelling approval leaves the helper disabled.
4. Choose **Open wizard**. The existing language choice, settings, device setup, 120-second countdown and result screens open in Terminal. The wizard runs as your normal user; session starts do not invoke sudo.
5. For each new Portal connection, open Better Portal and choose **Open wizard** again. Authorization is reused while macOS continues to approve the helper.

The system may ask for administrator authorization during installation and helper approval. Better Portal never reads or saves that password. Revocation, reinstalling, a signing change or managed-device policy may require approval again. This is not a promise of a single lifetime password prompt.

### Settings, reports and recovery

The packaged app stores your addresses, language and profile in `~/Library/Application Support/Better Portal/`. Session summaries are in its `reports` folder. Your source checkout's settings are unchanged; enter the device addresses once in the packaged wizard.

Reports are written by the normal user. Raw captures and recovery state stay in the helper's private, root-owned `/Library/Application Support/Better Portal/Private/sessions/` directory. They are not exported by the IPC interface. Removing the helper retains these diagnostics and your settings.

If the terminal closes, the bridge disconnects or the helper exits, the running session stops and attempts restoration. The independent watchdog remains available if the relay fails. Keep the Mac awake until recovery finishes. An unresolved recovery blocks another attempt and helper removal. The helper never accepts a client-provided recovery file or a command to run.

If permissions are revoked, the app shows **Helper disabled**. Open **System Settings** to review approval. A lost helper connection during a session produces a recovery warning, not a success result. Bitrate confirmation still does not prove actual picture, sound, input latency or throughput.

### Remove or update

Choose **Remove connection helper** in Better Portal. It stops your active attempt, waits for recovery and prevents another attempt from starting while unregistering. It refuses to interrupt another Mac user's session. To remove the app afterward, move both the launcher in Applications and `/Library/Application Support/Better Portal/Better Portal.app` to the Trash; Finder may require administrator approval for the protected copy. Keep `Private` until all recovery and any desired diagnostics are finished.

Before installing an update, remove the helper this way. The installer refuses to overwrite a loaded helper or an outstanding recovery. Install the new package and enable the helper again. Existing user settings remain available. Do not delete a recovery lock to force an update or removal.

Until a signed installer is available, the [source](../README.md#get-started) and Homebrew launchers can preview the wizard but cannot make a live connection through the helper. Do not run checkout or Homebrew Python as root to bypass that boundary.

## How the privilege boundary works

| Component | Runs as | Allowed work |
| --- | --- | --- |
| Better Portal app | Current user | Register/check/remove the bundled SMAppService daemon; open settings and Terminal |
| TUI and signed native bridge | Current user | Configure the existing wizard; submit one session; poll, cancel and retrieve its result |
| Connection helper | root | Authenticate the XPC peer, validate session input, serialize attempts and launch the protected worker |
| Protected worker and detached watchdog | root | Run the existing bounded relay and recovery, using private helper-owned files |

The daemon requires an Apple-signed client with the same Team ID and the exact app or bridge identifier. The bridge verifies the helper's identity too. The caller UID comes from `NSXPCConnection.effectiveUserIdentifier` and must match the active macOS console user. Switching accounts cancels an active session. A supplied UID, `SUDO_UID`, executable, import path, shell command or output path is rejected. A process already running as that same user can launch the signed bridge, so this boundary limits *what* the helper can do rather than proving which user-level program requested it.

The helper accepts only a Mac `enN` interface, distinct unicast IPv4 addresses and profiles **65 / 100 / 200**. The worker checks that both peers are directly reachable through that interface before changing mappings. It preserves the existing 120-second connection window, 15-second confirmation allowance, target validation, media forwarding during repair and machine-wide attempt lock.

The installer places a small unprivileged launcher in `/Applications` and the service app beneath root-owned `/Library/Application Support/Better Portal`. Its `Private` subdirectory is mode 0700 and holds a separate worker copy. `/Applications` can be writable by local administrators, so the daemon never launches from there. It checks every parent of the service app and worker paths for symlinks or non-root writes, then checks payload ownership, internal links and code signatures. The frozen worker never imports code from a user's checkout or virtual environment. Its environment and working directory are fixed.

The session channel has bounded messages and progress history. A disconnected client or a ten-second missed heartbeat requests cancellation. A stuck worker is terminated after the cleanup allowance, while its independent watchdog and recovery lock remain. Removal uses a drain state: no new session can start between recovery completion and unregistration.

No Mac password storage, Keychain password replay, sudoers exemption, setuid launcher or system-wide sudo timeout change is involved.

## Build and verify

Use a Mac with current Xcode or Swift Command Line Tools and Python 3.12+. Build each architecture on a matching Mac. The runtime's own minimum OS requirements also apply; test the oldest macOS version you plan to distribute to.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r macos/requirements-build.txt
sh macos/scripts/test-native.sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python macos/scripts/build.py --development
.venv/bin/python macos/scripts/check_bundle.py
```

The bundle check also builds an unsigned test package and inspects its BOM: the protected service and worker must install as root-owned, non-writable files, with the private directory at mode 0700. It does not install the package.

The development service app appears under `macos/build/installer-root/Library/Application Support/Better Portal/Better Portal.app`, with the unprivileged launcher at `macos/build/installer-root/Applications/Better Portal.app`. Both are ad hoc signed for local UI/build tests; registration is deliberately rejected. Preview the packaged wizard without authorization or network changes:

```sh
'macos/build/installer-root/Library/Application Support/Better Portal/Better Portal.app/Contents/Resources/PortalRuntime/PortalRuntime' tui --demo
```

For release, configure your **Developer ID Application** and **Developer ID Installer** identities in the local signing Keychain. Keep certificates, private keys and notary credentials outside the repository. The build script uses the supplied identities and an existing `notarytool` Keychain profile; it does not collect credentials.

```sh
.venv/bin/python macos/scripts/build.py \
  --identity 'Developer ID Application: YOUR NAME (TEAMID)' \
  --installer-identity 'Developer ID Installer: YOUR NAME (TEAMID)' \
  --notary-profile 'better-portal-notary' \
  --version 0.1.0
```

This builds and checks the app, signs the installer, submits it for notarization and staples the result. Omitting `--notary-profile` creates a signed but unnotarized package; do not publish it as a completed release. No build or test command installs a daemon or changes host networking.

## Acceptance before release

Automated tests cover request rejection, authenticated caller ownership, concurrent starts, cancellation, heartbeat loss, cleanup deadlines, pending-recovery retry blocking, removal draining, protected payloads, native XPC acceptance/rejection, packaged imports and the existing relay fault cases. CI builds an ad hoc app and exercises these without administrator authorization or a live Portal session.

The following require a **signed installation and a real Mac** and must be recorded before release:

- Fresh install → approve → quit → reopen → run without sudo; also deny and cancel approval.
- Restart the Mac and verify helper approval persists and the TUI still runs as the logged-in user.
- Establish actual PS5/Portal playback; check picture, sound and controls after restoration.
- Close or kill the TUI, bridge, worker and helper separately during preparation, waiting and confirmation; verify device recovery and retry.
- Revoke approval while idle and active; verify the disabled state and bounded cleanup.
- Attempt replacement or modified app and protected worker payloads, an unrelated signed client, malformed requests and another user's access; reject them before privileged work.
- Remove while idle and active; install an update after removal; verify no stale service, overlapping attempt or lost user settings.

A passing loopback test is not proof of SMAppService approval, persistence across reboot, notarization or real playback. No signed lifecycle or playback result is claimed until that checklist is completed.

## Apple references

The implementation uses [SMAppService](https://developer.apple.com/documentation/servicemanagement/smappservice) and its [registration lifecycle](https://developer.apple.com/forums/thread/802443). Apple recommends consistent Apple-issued signing identities for [helper authorization across restarts](https://developer.apple.com/forums/thread/799910). XPC peer checks use [connection code-signing requirements](https://developer.apple.com/documentation/foundation/nsxpcconnection/setcodesigningrequirement(_:)) and [listener requirements](https://developer.apple.com/documentation/foundation/nsxpclistener/setconnectioncodesigningrequirement(_:)). Public packages follow Apple's [notarization guidance](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).
