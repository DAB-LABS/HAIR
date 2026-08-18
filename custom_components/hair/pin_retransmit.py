"""Retransmit dispatch for pinned Remotes (signpost 4, Tracks 2 and 3a).

A confirmed trigger fire on a pinned Remote retransmits the mapped
command out each pinned Device's own emitters. This module owns the
dispatch POLICY only; the send itself is the device's ordinary send
path, so send_count, the transmit gate's per-emitter stagger, the
emitter loop, assumed state and the Mirror's echo expectation all
apply unchanged -- the device's command, sent the device's way.

Why a policy is needed at all. ``_fire_trigger`` is a synchronous
callback on the capture path, so a retransmit cannot be awaited there
and has to dispatch as a task. Every HAIR send then funnels through
``tx_gate.gated_send``, a single process-wide lock that inserts
``EMITTER_STAGGER_GAP_S`` of quiet whenever the emitter changes, so a
held button generates presses faster than the gate can drain them.

COALESCING (owner-ruled 2026-08-18): one pending retransmit per
binding target -- remote x device x command. While a send for that
target is in flight, a new confirmed fire marks the target PENDING
instead of enqueuing behind it, and pending is a slot, not a queue: a
hundred presses arriving during one in-flight send collapse into a
single follow-up. What lands is the latest press. Under fan-out load
fewer steps land than presses were made, which is the honest trade; in
exchange the backlog is never more than one press deep, so a ramp
stops climbing when the finger lifts.

THE LOOP BREAKER (Track 3a, non-optional, owner-ruled 2026-08-18
after a bench runaway). Pinning is a feedback-loop generator by
construction: the emitter transmits the very code a receiver just
heard. The echo defense in ``signal_monitor`` is the real protection
and it is supposed to make loops impossible. This is the floor under
it, for when it is wrong.

It exists because it has already been needed. A single-use echo ticket
that armed too early let a handset's own repeat frames spend it, so
the true echo fell through as a genuine press, retransmitted, echoed,
and bred: 77 fires and a retransmit every ~0.63 s for over 40 seconds,
stopped only by a human unpinning the devices. Manual unpin worked as
a brake, and it must never be the only one in a user's house.

The rule is deliberately blunt: more than ``PINNED_LOOP_MAX_SENDS``
sends for one target inside ``PINNED_LOOP_WINDOW_S`` cuts that
binding's retransmit for ``PINNED_LOOP_COOLDOWN_S`` and logs at
WARNING naming remote, device and trigger. It does not try to prove
the chain was echo-driven -- a runaway and a very long button hold
look alike from here, and the honest trade is that an implausibly long
hold gets cut short and recovers by itself, while a genuine loop stops
in seconds instead of running until someone notices. The thresholds
live in ``const.py`` precisely so the bench can move them.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any

from .const import (
    PINNED_LOOP_COOLDOWN_S,
    PINNED_LOOP_MAX_SENDS,
    PINNED_LOOP_WINDOW_S,
)

_LOGGER = logging.getLogger(__name__)

# (remote_id, device_id, command_id)
#
# The third element is a command id, EXCEPT for a matrix Remote driving
# a matrix Device (signpost 4, Track 4), where it is this prefix plus
# the heard cell's key -- "cell:cool/auto/23". A lattice cell has no
# command row to point at, and keying the coalescer and the loop
# breaker on the cell means a held handset collapses per state exactly
# as a held button collapses per command.
CELL_TARGET_PREFIX = "cell:"
Target = tuple[str, str, str]
# (remote_name, device_name, trigger_name), for the WARNING only.
Label = tuple[str, str, str]


class RetransmitDispatcher:
    """Coalescing dispatcher with a loop breaker.

    Deliberately does not hold the task objects ``async_create_task``
    returns. All bookkeeping happens inside the coroutine's own
    ``finally``, which keeps the dispatcher correct whether the caller
    hands back a real Task or something else.
    """

    def __init__(
        self,
        hass: Any,
        sender: Callable[[str, str], Awaitable[None]],
    ) -> None:
        self._hass = hass
        self._sender = sender
        self._inflight: set[Target] = set()
        self._pending: set[Target] = set()
        # Send start times per target, pruned to PINNED_LOOP_WINDOW_S.
        self._history: dict[Target, list[float]] = {}
        # Targets currently cut by the breaker, and when they recover.
        self._cooldown: dict[Target, float] = {}
        self._stopped = False

    def dispatch(self, target: Target, label: Label | None = None) -> bool:
        """Send now, mark pending, or refuse.

        Returns True when a send was started, False when the fire was
        coalesced into an in-flight send, refused by the loop breaker,
        or the dispatcher is stopped.
        """
        if self._stopped:
            return False
        now = monotonic()

        recovers_at = self._cooldown.get(target)
        if recovers_at is not None:
            if now < recovers_at:
                return False
            # Cooldown served: forget the chain that tripped it, so the
            # target starts clean rather than re-tripping on one send.
            del self._cooldown[target]
            self._history.pop(target, None)

        if target in self._inflight:
            self._pending.add(target)
            return False

        if self._trips_breaker(target, now, label):
            return False

        self._inflight.add(target)
        self._hass.async_create_task(self._run(target, label))
        return True

    def _trips_breaker(
        self, target: Target, now: float, label: Label | None
    ) -> bool:
        """Record this send and cut the binding if the rate is a loop."""
        cutoff = now - PINNED_LOOP_WINDOW_S
        history = [t for t in self._history.get(target, []) if t >= cutoff]
        history.append(now)
        self._history[target] = history
        if len(history) <= PINNED_LOOP_MAX_SENDS:
            return False

        self._cooldown[target] = now + PINNED_LOOP_COOLDOWN_S
        self._pending.discard(target)
        self._history.pop(target, None)
        remote_name, device_name, trigger_name = label or target
        _LOGGER.warning(
            "Pinned retransmit loop detected: trigger '%s' on remote '%s' "
            "fired %d times in under %.0f seconds driving device '%s'. "
            "Retransmit for this pairing is paused for %.0f seconds. The "
            "remote is most likely hearing that device's own emitter -- "
            "move the receiver out of the emitter's line of sight, narrow "
            "the remote's receiver scope, or unpin the pair.",
            trigger_name,
            remote_name,
            len(history),
            PINNED_LOOP_WINDOW_S,
            device_name,
            PINNED_LOOP_COOLDOWN_S,
        )
        return True

    async def _run(self, target: Target, label: Label | None = None) -> None:
        _, device_id, command_id = target
        try:
            await self._sender(device_id, command_id)
        except Exception:
            # Never propagate: this runs detached from the capture
            # path, and one misconfigured device (no emitters, all
            # emitters unavailable) must not stop the remote's other
            # pinned devices from being driven.
            _LOGGER.exception(
                "Pinned retransmit failed for device %s command %s",
                device_id,
                command_id,
            )
        finally:
            self._inflight.discard(target)
            if target in self._pending:
                self._pending.discard(target)
                self.dispatch(target, label)

    @property
    def busy(self) -> bool:
        """True while any target is in flight or waiting. Tests only."""
        return bool(self._inflight or self._pending)

    def is_cooling_down(self, target: Target) -> bool:
        """True while the breaker has this target cut. Tests only."""
        recovers_at = self._cooldown.get(target)
        return recovers_at is not None and monotonic() < recovers_at

    def shutdown(self) -> None:
        """Stop dispatching (config entry unload).

        Drops anything pending and refuses new work. Sends already in
        flight are left to finish -- IR that has reached the blaster
        cannot be recalled.
        """
        self._stopped = True
        self._pending.clear()
