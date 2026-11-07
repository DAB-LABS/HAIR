"""The Dyson rolling counter: one per device, three values (GH #33).

A Dyson frame ends in a two-bit rolling counter, and the fan ignores a
frame whose counter equals the last one it accepted, whatever the
button. channafam's AM07 captures settle how the handset drives it:

- THE COUNTER BELONGS TO THE REMOTE, not to a button. It keeps advancing
  across Power, Speed +, Speed - and Swing.
- THREE VALUES, NEVER FOUR. The last two wire bits go 00, 01, 10 and
  round again, which in HAIR's numbering (F bits 6-7, see
  ``decoders/dyson.py``) is 0, 2, 1, 0. The wire pair 11 never appears.
- Each press is sent as two identical frames.

Until 1.1.1 HAIR kept a counter in each command row and advanced it
``+1 & 0x3``, so Power then Speed + could both go out with the same
counter and the second was dropped, and the counter eventually sent 3.

HERE IS WHERE IT LIVES NOW. ``IRDevice.press_counters`` maps
``"DYSON:<address>"`` to the LAST counter the fan is known to have
accepted from that address: the last one HAIR sent there, or the last
one a receiver heard from the handset. A send uses the next value in the
handset's order and records it once at least one emitter took the frame
(the GH #65 rule). The command rows' own ``counter`` extras are no
longer read while the device has an entry; they are kept in step with
each press so a row read without this module still starts from a
sensible value. The counter has never been part of the fingerprint, so
no identity moves.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from typing import Any

_LOGGER = logging.getLogger(__name__)

DYSON = "DYSON"

#: The handset's order in HAIR's numbering (wire 00 -> 01 -> 10 -> 00).
#: 3 (wire 11) is never sent; if one is ever heard or stored, the next
#: send starts the cycle again at 0.
_NEXT = {0: 2, 2: 1, 1: 0, 3: 0}


def next_counter(last: int) -> int:
    """The value the handset sends after ``last``."""
    return _NEXT[int(last) & 0x3]


def counter_key(address: int) -> str:
    """The ``press_counters`` key for a Dyson address."""
    return f"{DYSON}:{int(address) & 0x7F}"


def is_dyson(protocol: str | None) -> bool:
    return (protocol or "").upper() == DYSON


def counter_for_send(device: Any, address: int, row_extras: Any) -> int:
    """The counter the next Dyson press to ``address`` on ``device`` uses.

    The next value after the device's last known one. A device with no
    entry yet (every device before 1.1.1, until its first press) starts
    from the row's own stored counter, which is what it would have sent
    before this change, unless that is 3, which is never sent.
    """
    counters = getattr(device, "press_counters", None) or {}
    last = counters.get(counter_key(address))
    if last is not None:
        return next_counter(last)
    stored = int((row_extras or {}).get("counter", 0)) & 0x3
    return 0 if stored == 3 else stored


def record_sent(device: Any, address: int, value: int, row_extras: Any) -> None:
    """Record a landed press: the fan has now accepted ``value``.

    The row's own counter is set to the value after it, the meaning that
    field had before this change, so a row read without the device
    counter still starts where the remote would.
    """
    device.press_counters[counter_key(address)] = int(value) & 0x3
    if isinstance(row_extras, dict) and "counter" in row_extras:
        row_extras["counter"] = next_counter(value)


def last_frame_counter(timings: Sequence[int] | None) -> int | None:
    """The counter of the last Dyson frame in a capture, or None.

    A held button advances the counter every second frame, and what the
    fan last accepted is the last frame, not the majority the identity
    decode votes on.
    """
    if not timings:
        return None
    from .decoders import split_frames
    from .decoders.dyson import _FRAME_GAP_US, DysonCommand

    last = None
    for frame in split_frames(list(timings), _FRAME_GAP_US):
        decoded = DysonCommand._decode_frame(frame)
        if decoded is not None:
            last = decoded[2]
    return last


def devices_sending_to(devices: Iterable[Any], address: int) -> list[Any]:
    """The devices holding a Dyson command for ``address``."""
    found = []
    for device in devices:
        for command in getattr(device, "commands", ()):
            if (
                is_dyson(command.decoded_protocol)
                and command.decoded_address is not None
                and int(command.decoded_address) == int(address)
            ):
                found.append(device)
                break
    return found


def observe_heard_press(
    devices: Iterable[Any], address: int, counter: int
) -> Any | None:
    """A receiver heard the handset: set the device's counter to it.

    Only when exactly one device sends to that address. With two, HAIR
    cannot tell which fan the handset was pointed at, and setting both
    could make the next send to the other fan repeat the counter it last
    accepted, so neither moves. Returns the device that moved, if any.
    HAIR's own transmissions never get here: the echo claim takes them
    before any consumer sees the capture.
    """
    targets = devices_sending_to(devices, address)
    if len(targets) != 1:
        if targets:
            _LOGGER.debug(
                "Heard Dyson address %d, but %d devices send to it; "
                "leaving their counters alone", address, len(targets),
            )
        return None
    (device,) = targets
    key = counter_key(address)
    value = int(counter) & 0x3
    if device.press_counters.get(key) == value:
        return None
    device.press_counters[key] = value
    return device
