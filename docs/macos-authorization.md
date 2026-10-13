# macOS authorization: approve setup, then use normally

**Status: researched proposal, not implemented.** The current terminal launcher still uses sudo. This document describes the recommended next step for Better Portal; it is not an installation script or a claim that passwordless startup already works.

## Recommended approach

Package Better Portal as a signed macOS app with a narrowly scoped privileged helper managed by **SMAppService**. The user approves the helper through macOS during initial setup. The TUI then runs as the user and asks the helper to perform an allowed Portal session.

Apple recommends SMAppService for bundled helpers on macOS 13 and later. A LaunchDaemon requires administrator approval; once approved, it can be bootstrapped on subsequent boots. The app must check the service's authorization state and guide the user to System Settings when approval is needed. [SMAppService](https://developer.apple.com/documentation/servicemanagement/smappservice), [register()](https://developer.apple.com/documentation/servicemanagement/smappservice/register%28%29), [helper approval](https://developer.apple.com/documentation/servicemanagement/updating-helper-executables-from-earlier-versions-of-macos).

This supports **initial setup approval followed by normal launches without another sudo prompt**. It does not promise that macOS will never request approval again: revocation, reinstalling, signing changes or managed-device policy can change authorization.

## Intended user experience

1. Open Better Portal and choose **Enable connection helper**.
2. Complete the macOS approval flow. Better Portal never reads or stores the administrator password.
3. Use the existing four-step TUI. Each new Portal connection still needs another session, but normal session starts no longer invoke sudo.
4. Show a clear **Helper disabled** action if permission is revoked, with a link to the relevant System Settings page.
5. Offer **Remove connection helper**, finishing any active recovery before unregistering it.

The existing source launcher remains the fallback while this packaged flow is developed. Attempts retried inside the same currently running wizard already share its initial sudo authorization.

## Integration boundaries for this codebase

These are proposed project requirements, not behavior supplied automatically by SMAppService:

- Keep the TUI unprivileged. A signed client bridge communicates with the helper over authenticated XPC. The helper checks the caller's code identity and user identity before allowing operations.
- Expose only session start, progress, cancellation and result retrieval. Validate the interface, distinct local IPv4 addresses and the allowed 65/100/200 profiles in the helper. Accept no shell command, executable path, import path or arbitrary restoration file from the client.
- Execute only an installed, protected and code-validated worker and its dependencies. Do not run Python from a user's writable checkout or virtual environment through a permanent privileged service.
- Derive the requesting user from the authenticated connection. Replace the current reliance on sudo-provided identity with an explicit trusted caller context; do not trust a client-supplied UID or forged SUDO_UID.
- Preserve the existing single-session lock, 120-second connection window, confirmation window and independent recovery. Losing the UI connection must trigger bounded cleanup rather than leaving the network redirected.
- Keep helper-owned recovery state protected. Deliver user-owned settings and reports through a controlled interface without allowing arbitrary root file writes.

Apple's authorization model separates restricted operations into a helper and lets the system handle authentication. The XPC boundary still needs its own authorization design. [Using Authorization](https://developer.apple.com/library/archive/documentation/Security/Conceptual/AuthenticationAndAuthorizationGuide/Authorization/Authorization.html).

## Packaging and validation before release

Build an app bundle and helper with stable identifiers and the same Apple-issued signing identity. Apple DTS specifically warns that ad hoc signatures can cause helper authorization problems across restarts. Follow the native daemon setup first, then add IPC. [Getting Started with SMAppService](https://developer.apple.com/forums/thread/802443), [Apple DTS on signing and persistence](https://developer.apple.com/forums/thread/799910).

For public distribution, supply a Developer ID-signed, hardened and notarized build. Signing credentials stay outside the repository and must be configured by the maintainer. [Apple distribution guidance](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).

Before calling this ready, verify initial approval, denial, cancellation, reboot, upgrade, revocation and uninstall on a Mac. Exercise an actual Portal session and recovery after UI/helper failure. Reject unauthorized clients, modified payloads, malformed requests, concurrent starts and attempts to execute arbitrary commands or overwrite files.

## Password handling decision

Do not store the Mac login password in settings or Keychain for replay into sudo. Do not grant blanket NOPASSWD access to Python, make a launcher setuid, or extend the system-wide sudo timeout. A saved password or a broad executable exemption gives a much wider capability than a validated Portal-session request.

The deliverable needed next is the signed app/helper integration and its lifecycle tests. This research commit changes no launch behavior and installs no background service.
