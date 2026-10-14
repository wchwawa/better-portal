# macOS black-screen investigation

The reported symptom is a confirmed 65 Mbps profile (PS5 target: 58.374 Mbps),
followed by a black screen, no audio, and a later disconnect. The reporter's raw
diagnostics and firmware version were not available for this investigation.

## What the tests establish

The original macOS cleanup sends three corrective ARP replies per peer, at about
0, 0.1 and 0.2 seconds, then closes the relay. It checks local sends and system
settings, not the peers' address mappings. A peer can therefore keep sending
traffic to the Mac after the relay has stopped, with `restoration_errors: []`.

This is reproducible against a real Linux ARP cache. Linux can temporarily reject
a changed mapping during its [ARP locktime](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/arp.c).
The repository's Linux deployment helper already waits and repairs again in this
situation; the macOS cleanup did not.

The isolated test calls the production macOS `restore()` and `frames()` functions
and sends real Ethernet frames through a veth pair. Only macOS configuration and
sysctl access are replaced. The container has no external network, no host
network access, and only NET_ADMIN/NET_RAW capabilities. Its Linux interface acts
as each peer in turn; it is not a real PS5 or Portal.

Observed with Docker Desktop kernel `6.12.76-linuxkit`, default locktime 100
USER_HZ units (one second), before the fix at `35b6523` and after the fix:

| Peer model | Time from redirection to repair | Before: peer mapping / next UDP destination restored | After |
| --- | --- | --- | --- |
| Portal | 0.05 s | No / No, despite no restoration error | Yes / Yes |
| PS5 | 0.05 s | No / No, despite no restoration error | Yes / Yes |
| Portal | 1.2 s | Yes / Yes | Yes / Yes |
| PS5 | 1.2 s | Yes / Yes | Yes / Yes |

The UDP payload is only 25 bytes. High stream bandwidth is not required to
reproduce this failure mode. A later repair with exactly the same ARP frame
contents succeeds, providing a positive control for the timing problem.

Separate offline tests feed actual Ethernet and protocol bytes into the main
relay loop, including an accepted startup and three 58.374 Mbps target reports.
Before the fix, a packet, a startup retransmission, or a DISCONNECT arriving
during restoration is not processed. The disconnect case still produces the
successful result. The new tests reproduce both gaps before the fix and pass
after it.

## The fix and its limits

- Send another corrective ARP burst after 1.5 seconds, with the last reply at
  1.7 seconds. The standalone watchdog uses the same bounded schedule.
- Keep forwarding during those waits, without sending further redirecting ARP.
  Startup retransmissions retain the same mutation. A received DISCONNECT
  invalidates target confirmation.
- Preserve independent recovery if forwarding or repair reports a failure.
  Check short Ethernet writes as well as exceptions.
- Label success as target confirmation. Reports explicitly say playback and
  peer ARP state were not verified, and include traffic forwarded during repair.

This fixes demonstrated defects, not a confirmed diagnosis of this reporter's
network. It does not test Portal decoding, the actual Wi-Fi path, macOS packet
injection under load, all firmware layouts, or devices that reject every repair
packet. A successful repair send is still not proof that the peer received it.
The repair interval fits within the existing 15-second recovery budget.

## Run the checks

Offline tests need no elevated permissions or network changes:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

The real-kernel check requires Docker. It creates temporary interfaces only in
its isolated container; do not run the Python script directly on a host:

```sh
docker build -f tests/integration/Dockerfile.restore -t portal-restore-test tests/integration
docker run --rm --network none --cap-drop ALL --cap-add NET_ADMIN --cap-add NET_RAW \
  --mount "type=bind,src=$PWD,dst=/src,readonly" \
  portal-restore-test python tests/integration/restore_kernel_check.py --expect-fixed
```

To reproduce the old failure, use the test-only commit `089ce9a` and omit
`--expect-fixed`. The check prints each peer mapping and the destination of the
next real UDP packet; it asserts that the late positive-control repair works.

## What remains to verify on the reporter's devices

First confirm that ordinary Remote Play still works after disconnecting and
reconnecting without the tool. Then test this repair once with the same 65 Mbps
profile and game scene. Keep the Mac awake through restoration and check picture,
sound and controls on Portal after the result appears.

If it still fails, collect the exact software/firmware versions and a redacted
summary of `counts`, `ps5_messages`, `udp_9296_mbps_by_second`,
`restoration_forwarded_packets`, `restoration_errors` and `egress_witness`.
Do not publish raw captures, device addresses or local recovery-state files.
Normal Remote Play succeeding does not isolate the cause: it changes both the
bitrate request and the temporary relay path. A real-device comparison is still
needed to distinguish recovery, relay performance and firmware compatibility.
