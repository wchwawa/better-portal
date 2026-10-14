# Investigating stutter at a higher bitrate

The bitrate result confirms a setup request. It does not measure smooth playback.
If camera movement stutters at 100 Mbps while a stationary view looks normal,
compare fresh sessions at **65 → 100 → 65 Mbps** in the same game scene and at the
same Portal location. Wait for the result screen before each comparison. Keep the
game's graphics mode and Portal quality settings the same.

For each session, spend 30 seconds stationary and 30 seconds rotating the camera
at a consistent speed. Record whether the picture pauses, whether sound also
breaks up, and whether the TV picture stutters too. After a successful setup,
quitting the wizard normally does not end the boosted session; repeat the camera
movement with the wizard closed. Each new Portal connection needs a new setup.

If both 65 Mbps sessions are smooth and 100 Mbps stutters, use 65 Mbps for now.
That comparison implicates the higher setting on this setup, but does not by
itself distinguish Wi-Fi transport, encoding or Portal decoding/frame pacing.
Motion also makes an existing frame-pacing problem easier to notice; a stationary
picture alone cannot establish that frames are arriving on time.

## What the diagnostics retain

`CONNECTIONQUALITY` messages previously saved only `target_bitrate_raw`. They now
also retain optional `loss_raw`, `rtt_raw`, `upstream_bitrate_raw` and
`upstream_loss_raw`. The field mapping follows
[Chiaki-ng's protocol definition](https://github.com/streetpea/chiaki-ng/blob/c8bea2642d0e95402f373af55584a3b98cd89417/lib/protobuf/takion.proto#L285).
Missing or invalid optional fields are omitted, not recorded as zero. Structural
protobuf errors retain the existing rejection behavior.

These are console-reported raw values. This implementation does not establish
the loss counter's interval or the RTT unit. Do not add loss samples together,
derive packet-loss percentages from undocumented fields, or treat them as
independent end-to-end measurements. Fields 7 and 8 are intentionally not assigned
meanings by this diagnostic. Target confirmation remains a separate result and
does not imply zero loss.

For an older report, the local `egress-private.pcap` may still contain these
fields. From a checkout with the Python dependencies installed, run:

```sh
python tools/analyze_stream_quality.py /path/to/experiment-folder
```

Pass several experiment folders to compare them. This reads existing files only;
it does not require sudo, send packets, change settings or modify captures. The
JSON output excludes device addresses, capture payloads and original file paths.
If the capture is missing, an older report's absent loss field remains unknown.
An unreadable capture is explicitly reported rather than interpreted as zero loss.
The output lists sample counts from each source and flags a capture with fewer
quality samples than the report. The capture need not cover every reported sample.
Reports that already contain loss telemetry remain the primary source; a shorter
capture cannot replace their recorded loss with an apparent zero.

## Evidence from the initial investigation

An existing 100 Mbps setup capture contained these consecutive quality reports:

| Sample | Reported target (Mbps) | Raw loss field |
| --- | ---: | ---: |
| 1 | 97.087 | 0 |
| 2 | 87.241 | 40 |
| 3 | 87.266 | 0 |

Three earlier 65 Mbps setup captures each had three reports at 63.106 Mbps with
raw loss zero. They were different sessions, not controlled recordings of the
same moving scene. The 100 Mbps target decrease coincided with a nonzero loss
report. This is useful evidence of a setup-quality problem, not proof of the
cause of later motion stutter.

The capture covers the temporary Mac relay and restoration window. That relay
can itself affect transport timing. The witness captures control packets only;
it is not a video throughput or frame-rate recording. The production relay
closes its sockets before displaying the result. Its reported Mbps counters do
not measure gameplay after the direct path is restored, and successful local
repair sends do not verify the devices' ARP caches.

To investigate sustained post-setup stutter, use the controlled scene comparison
above and, where available, router/AP measurements of the Portal connection.
Ordinary Mac Wi-Fi captures may not see traffic between PS5 and Portal after
restoration. Packet silence at the Mac cannot establish a healthy stream or no
loss. Keeping the temporary relay active changes the tested network path and is
not an equivalent measurement of direct playback.

For a network comparison, Sony recommends PS5 on Ethernet and Portal on 5 GHz
Wi-Fi in its [Portal network guide](https://www.playstation.com/en-ca/support/hardware/playstation-remote-play-on-psportal/#network).
Change one variable per comparison; an internet speed test does not establish
the quality of the local PS5-to-Portal path.
