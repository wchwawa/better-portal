---
name: Windows preview test result
about: Report a Windows guided session, preflight or legacy baseline experiment
title: 'Windows preview test: '
---

<!-- Do not upload config, recovery state, raw captures, passwords or session identifiers. Redact private data in errors. -->

## Environment
- Preview version:
- Windows version/build and CPU architecture:
- Python version (`py -3 --version`):
- Npcap version:
- Network adapter model and Wi-Fi/Ethernet:
- PS5 wired or wireless:
- Portal firmware:

## Steps reached
- [ ] Setup offline tests passed
- [ ] Start-Windows.cmd opened the guided TUI after the Windows permission prompt
- [ ] Language, addresses, adapter and bitrate saved correctly
- [ ] CONNECT NOW started a 120-second countdown
- [ ] Picture, sound and controls worked after the result
- [ ] Cancellation restored normal play; a second attempt worked
- [ ] Optional legacy CHECK / Baseline passed
- [ ] 65 tested
- [ ] 100 tested (only after 65)
- [ ] 200 tested (only after 100)

## Observations
- Profile:
- Portal displayed resolution/bitrate (not just console target):
- Image quality and stutter/input response:
- Normal connection still works after test:

## Redacted diagnostic fields
Paste `counts`, `unique_mutated_sequences`, `ps5_messages`, `egress_witness`, `restoration_errors` and a redacted error message. Target bitrate is not actual video throughput. Never attach the entire experiment folder.
