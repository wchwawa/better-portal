"""Bounded peer repair shared by the macOS and Windows manual relays."""
import time


def restore_peer_mappings(send, packets, *, service=None):
    """Retry past short ARP cache locks while the live relay drains traffic."""
    errors = []
    start = time.monotonic()
    for offset in (0, .1, .2, 1.5, 1.6, 1.7):
        remaining = max(0, start + offset - time.monotonic())
        if remaining and service is not None:
            try:
                service(remaining)
            except Exception as exc:
                errors.append('Relay during restore: ' + str(exc))
                service = None
        remaining = max(0, start + offset - time.monotonic())
        if remaining:
            time.sleep(remaining)
        for packet in packets:
            try:
                send(packet)
            except Exception as exc:
                errors.append('ARP restore: ' + str(exc))
    return errors
