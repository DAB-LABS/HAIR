"""Transmit gate: serialize sends across emitters, one gate per medium.

IR is a shared medium. When HAIR broadcasts one command through two
emitters, or the user tests a signal out of several blasters at once,
the transmissions overlap in the air and any receiver that hears both
captures a superimposed hybrid: a perfectly valid pulse train that
decodes as nothing, fails the echo claim, and falls into the Sniffer
as a junk row (owner bench, 2026-07-18).

The gate is a single process-wide choke point wrapped around every
HAIR-originated send. Consecutive sends on the SAME emitter pass
straight through -- the device queues its own back-to-back bursts and
SEND_REPEAT_GAP already paces whole-frame repeats. When the emitter
CHANGES, the gate holds off until the previous send has stopped
occupying the air.

The ack does NOT mean the air is clear. A service call returns when
the blaster accepted the bytes, not when it finished radiating them,
and a bundled burst can go on transmitting for over a second after its
own call returned (send spacing, GH #151). So the hold is
max(EMITTER_STAGGER_GAP_S, the previous send's PLANNED air time),
measured from that send's ack: the constant covers an ordinary frame,
the planned figure covers a burst, and callers that pass no air time
get exactly today's behaviour.

The hold is slept OUTSIDE the lock, because holding the lock through a
second of quiet would block a same-emitter send that has nothing to
wait for. It is re-checked inside only when another sender keyed up
during the wait, which is the one case where the hold just slept was
measured against a stamp that no longer exists.

Because the gate holds one asyncio.Lock across the actual send call,
concurrent callers (the four tabs fire one test call per emitter via
Promise.allSettled) serialize here without any websocket or frontend
contract change.
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from .const import EMITTER_STAGGER_GAP_S


class _Medium:
    """One medium's gate: its lock and the last send's stamps.

    Infrared and radio do not share the air, so a radio send never waits
    on an infrared burst elsewhere (and the reverse); within a medium the
    rule above applies unchanged.
    """

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.last_emitter: str | None = None
        self.last_ack: float = 0.0
        # Planned air time of the last send, in seconds. Zero for every
        # caller that does not know (which is every caller on the old
        # path), and the hold then falls back to EMITTER_STAGGER_GAP_S.
        self.last_air: float = 0.0
        # Bumped on every stamp. The hold is computed outside the lock,
        # so this is how a waiter tells "nothing moved while I waited"
        # (my hold is still good) from "somebody else keyed up".
        self.ack_seq: int = 0

    def hold_for(self, emitter_id: str) -> float:
        """Seconds still owed before ``emitter_id`` may key up, or 0."""
        if self.last_emitter is None or self.last_emitter == emitter_id:
            return 0.0
        quiet = max(EMITTER_STAGGER_GAP_S, self.last_air)
        return max(0.0, quiet - (time.monotonic() - self.last_ack))


_media: dict[str, _Medium] = {}


def _gate(medium: str) -> _Medium:
    gate = _media.get(medium)
    if gate is None:
        gate = _media[medium] = _Medium()
    return gate


async def gated_send(
    hass: Any,
    emitter_id: str,
    ir_cmd: Any,
    sender: Callable[[Any, str, Any], Awaitable[None]],
    air_s: float = 0.0,
    medium: str = "ir",
) -> None:
    """Send ``ir_cmd`` via ``sender``, staggering emitter changes.

    ``sender`` is the medium's ``async_send_command`` (passed in so its
    lazy runtime import stays at the call site, matching the existing
    send paths).

    ``air_s`` is how long THIS call will keep the air busy once the
    service returns. A bundled burst radiates for far longer than its
    own ack, so the next emitter has to wait on the air rather than on
    the ack (send spacing, GH #151). Zero, the default, gives exactly
    today's EMITTER_STAGGER_GAP_S behaviour.

    ``medium`` picks the gate: ``"ir"`` (the default, every infrared
    caller) or ``"rf"``.
    """
    gate = _gate(medium)
    # Wait outside the lock: a hold that can now run to a second and a
    # half must not block a same-emitter send that owes nothing.
    seen = gate.ack_seq
    wait = gate.hold_for(emitter_id)
    if wait > 0:
        await asyncio.sleep(wait)
    async with gate.lock:
        # Re-check under the lock, but only when somebody else keyed up
        # while this call was waiting. Nothing moved means the hold just
        # slept is still the right one, and sleeping it again would
        # double every stagger on the quiet path.
        if gate.ack_seq != seen:
            wait = gate.hold_for(emitter_id)
            if wait > 0:
                await asyncio.sleep(wait)
        try:
            await sender(hass, emitter_id, ir_cmd)
        finally:
            # Stamp even on failure: the blaster may have partially
            # transmitted before erroring, so the quiet gap still applies.
            gate.last_emitter = emitter_id
            gate.last_ack = time.monotonic()
            gate.last_air = max(0.0, float(air_s or 0.0))
            gate.ack_seq += 1


def reset_for_test() -> None:
    """Reset module state between tests."""
    _media.clear()
