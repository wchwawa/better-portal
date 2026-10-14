# Observing a session after setup

The current result screen describes a completed bitrate setup attempt. It does
not observe whether Portal is still playing. A manual trial on 14 October 2026
found no reliable session-state signal in the ordinary Mac interface capture,
ICMP replies, or PS5 discovery replies after the direct connection was restored.

This is a limitation of the tested observation methods and network, not proof
that every possible monitoring method is impossible.

## Real-device trial

The instructions asked the operator to start from a working Portal session after
using Better Portal, keep PS5 awake and Portal on Wi-Fi, and reconnect from Portal
without running the boost again. The operator manually labelled connected,
disconnected, reconnected, disconnected, and reconnected. These labels are user
observations, not states detected by the diagnostic. The diagnostic did not
independently verify playback or the initial bitrate.

The Mac captured on its ordinary `en0` interface, without redirecting traffic or
enabling wireless monitor mode. It also sent ordinary ICMP echo requests to both
devices and discovery SEARCH requests to the PS5 on UDP 9302. It sent no wake,
pairing, registration, or Remote Play commands. Only packet header metadata and
discovery replies were recorded; host names and identifiers were hashed.

The completed capture lasted 163.425 seconds, including an initial unlabelled
interval. Each row below is a separate interval; repeated labels were not merged.

| Manual state | Seconds until next label or stop | PS5 ping replies / attempts | Portal ping replies / attempts | PS5 discovery replies | Visible PS5–Portal packets |
| --- | ---: | ---: | ---: | ---: | ---: |
| Connected | 15.125 | 8 / 8 | 8 / 8 | 7 | 0 |
| Disconnected, first round | 32.403 | 16 / 16 | 15 / 15 | 16 | 0 |
| Reconnected, first round | 44.252 | 22 / 22 | 22 / 22 | 21 | 0 |
| Disconnected, second round | 53.759 | 26 / 26 | 26 / 26 | 25 | 0 |
| Reconnected, second round | 5.844 | 3 / 3 | 3 / 3 | 3 | 0 |

All 78 discovery replies across the full capture had the same status and header
values: `HTTP/1.1 200 Ok`, host identity, host type, request port, discovery
protocol version, and system version. No changing session field was observed.
All 81 PS5 pings and 80 Portal pings received replies.

`tcpdump` captured 511 packets with zero kernel drops; the diagnostic recorded
all 511 as packet events. They consisted of 322 other IP packets (consistent with
the ping requests and replies), 156 PS5 discovery packets to/from the observer's
UDP port, 32 ARP packets, and one Portal-originated packet to UDP 9302.
That last packet appeared during the second disconnected interval. It did not
repeat across both reconnect cycles, did not establish a peer stream, and cannot
serve as a confirmed connected/disconnected signal. No peer TCP close or peer
UDP 9296 packet was observed, including during labelled playback.

Ignoring the first three seconds after each label gives the same result. This
reduces ambiguity from requests started before a label, but does not remove the
delay between an action on Portal and the operator entering its label. The final
reconnected interval is only 5.844 seconds and is not a full-duration repeat.
The earlier reconnected interval lasted over 44 seconds. No observer errors or
discovery timeouts occurred. An earlier 12.659-second capture had no labels and
was excluded from the state comparison.

## What this means for the result screen

After setup, the production relay restores the direct path and closes its
capture sockets. The result loop redraws the saved attempt report. Neither
device reachability nor an unchanged discovery reply establishes an active
Remote Play session. Packet silence also cannot establish disconnection when
the same observer sees no peer packets during known playback.

This agrees with the documented limitations of [ordinary WLAN captures](https://wiki.wireshark.org/CaptureSetup/WLAN):
traffic between other devices is generally not supplied to the capturing host.
Special monitor modes depend on hardware and drivers and may disconnect the Mac
from Wi-Fi. A switched wired network has [similar visibility limits](https://wiki.wireshark.org/CaptureSetup/Ethernet).

Keep the result labelled as the outcome of the last setup attempt. Do not turn
ping replies into a live green connection indicator, or a capture timeout into a
disconnected indicator. A new connection also needs a new bitrate confirmation;
the prior report does not prove that the boost survived a reconnect.

A live connection indicator would need another validated source, such as
router/access-point telemetry or mirrored traffic that actually includes the
peer session. Keeping the Mac in the forwarding path is another research option,
but would change recovery, latency, and Mac sleep/exit requirements. None of these
alternatives was tested in this trial. They should be evaluated separately before
connecting an observer to the production result screen.

## Repeat the observation

On a Mac with the Homebrew installation and saved device settings, open
`Observe-Session.command` from a checkout of this branch. Enter the administrator
password in the local Terminal prompt. The diagnostic uses the Homebrew Python
runtime and does not modify the installed application.

1. Start from working playback after a successful setup attempt. Keep the result
   screen open and launch the observer in a separate Terminal.
2. Wait for `READY`. Enter `1` and Return while picture, sound, and controls work.
   Stay in that state for at least 20 seconds.
3. Disconnect Remote Play on Portal while keeping PS5 awake and Portal on Wi-Fi.
   Enter `2` and Return, then wait at least 20 seconds.
4. Reconnect from Portal without boosting again. Once playback works, enter `3`
   and Return, then wait at least 20 seconds.
5. Repeat steps 3 and 4 if convenient. Enter `q` and Return to finish.

Evidence is saved under the checkout's ignored `research/session-*` directory.
Keep the original evidence local. Share redacted summaries rather than raw
device identifiers or network recordings. The observer does not decide whether
a session is connected. Its offline checks can run without administrator access:

```sh
python3 -m unittest discover -s tools/tests -v
```
