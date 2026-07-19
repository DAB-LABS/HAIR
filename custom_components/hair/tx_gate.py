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
CHANGES, the gate inserts EMITTER_STAGGER_GAP_S of quiet, measured
from the previous send's service ack, so the first blaster finishes
speaking before the next one starts.

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


async def gated_send(
    hass: Any,
    emitter_id: str,
    ir_cmd: Any,
    sender: Callable[[Any, str, Any], Awaitable[None]],
) -> None:
    """Send ``ir_cmd`` via ``sender``, staggering emitter changes.

    ``sender`` is the infrared component's ``async_send_command`` (passed
    in so its lazy runtime import stays at the call site, matching the
    existing send paths).
    """
    global _last_emitter, _last_ack
    async with _lock:
        if _last_emitter is not None and _last_emitter != emitter_id:
            wait = EMITTER_STAGGER_GAP_S - (time.monotonic() - _last_ack)
            if wait > 0:
                await asyncio.sleep(wait)
        try:
            await sender(hass, emitter_id, ir_cmd)
        finally:
            # Stamp even on failure: the blaster may have partially
            # transmitted before erroring, so the quiet gap still applies.
            _last_emitter = emitter_id
            _last_ack = time.monotonic()


def reset_for_test() -> None:
    """Reset module state between tests."""
    global _last_emitter, _last_ack
    _last_emitter = None
    _last_ack = 0.0
