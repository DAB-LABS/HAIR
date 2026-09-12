"""Transmit gate: serialize IR sends across emitters.

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

_lock = asyncio.Lock()
_last_emitter: str | None = None
_last_ack: float = 0.0
# Planned air time of the last send, in seconds. Zero for every caller
# that does not know (which is every caller on the old path), and the
# hold then falls back to EMITTER_STAGGER_GAP_S alone.
_last_air: float = 0.0
# Bumped on every stamp. The hold is computed outside the lock, so this
# is how a waiter tells "nothing moved while I waited" (my hold is still
# good) from "somebody else keyed up" (recompute before sending).
_ack_seq: int = 0


def _hold_for(emitter_id: str) -> float:
    """Seconds still owed before ``emitter_id`` may key up, or 0."""
    if _last_emitter is None or _last_emitter == emitter_id:
        return 0.0
    quiet = max(EMITTER_STAGGER_GAP_S, _last_air)
    return max(0.0, quiet - (time.monotonic() - _last_ack))


async def gated_send(
    hass: Any,
    emitter_id: str,
    ir_cmd: Any,
    sender: Callable[[Any, str, Any], Awaitable[None]],
    air_s: float = 0.0,
) -> None:
    """Send ``ir_cmd`` via ``sender``, staggering emitter changes.

    ``sender`` is the infrared component's ``async_send_command`` (passed
    in so its lazy runtime import stays at the call site, matching the
    existing send paths).

    ``air_s`` is how long THIS call will keep the air busy once the
    service returns. A bundled burst radiates for far longer than its
    own ack, so the next emitter has to wait on the air rather than on
    the ack (send spacing, GH #151). Zero, the default, gives exactly
    today's EMITTER_STAGGER_GAP_S behaviour.
    """
    global _last_emitter, _last_ack, _last_air, _ack_seq
    # Wait outside the lock: a hold that can now run to a second and a
    # half must not block a same-emitter send that owes nothing.
    seen = _ack_seq
    wait = _hold_for(emitter_id)
    if wait > 0:
        await asyncio.sleep(wait)
    async with _lock:
        # Re-check under the lock, but only when somebody else keyed up
        # while this call was waiting. Nothing moved means the hold just
        # slept is still the right one, and sleeping it again would
        # double every stagger on the quiet path.
        if _ack_seq != seen:
            wait = _hold_for(emitter_id)
            if wait > 0:
                await asyncio.sleep(wait)
        try:
            await sender(hass, emitter_id, ir_cmd)
        finally:
            # Stamp even on failure: the blaster may have partially
            # transmitted before erroring, so the quiet gap still applies.
            _last_emitter = emitter_id
            _last_ack = time.monotonic()
            _last_air = max(0.0, float(air_s or 0.0))
            _ack_seq += 1


def reset_for_test() -> None:
    """Reset module state between tests."""
    global _last_emitter, _last_ack, _last_air, _ack_seq
    _last_emitter = None
    _last_ack = 0.0
    _last_air = 0.0
    _ack_seq = 0
