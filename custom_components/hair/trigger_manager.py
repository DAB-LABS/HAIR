"""Trigger manager for HAIR.

Tracks per-trigger hit counts and fires HA event entities when the
configured ``min_hits`` threshold is reached within the reset window.

v0.5.7 (location-aware triggers): each capture is threaded with the
receiver that observed it. Triggers gain an optional receiver scope
(``matches_receiver``); the fire payload carries the receiver entity plus
its resolved area. A single physical press captured by several receivers
within ``MULTI_RECEIVER_DEDUP_WINDOW_S`` counts once per (trigger,
fingerprint) so multi-receiver setups do not double-count toward
``min_hits`` or double-fire.
"""
from __future__ import annotations

import contextlib
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)

from .const import (
    EVENT_TRIGGER_FIRED,
    MULTI_RECEIVER_DEDUP_WINDOW_S,
    TRIGGER_HIT_RESET_WINDOW_S,
)
from .models import IRTrigger
from .storage import HAIRStore

_LOGGER = logging.getLogger(__name__)


@dataclass
class _RecentObservation:
    """Observations of a fingerprint within the dedup window, per receiver.

    Best-effort tracking used only for the informational log line when a
    scoped trigger fires while other receivers also observed the press.
    """

    first_receiver: str | None = None
    observed_at: float = 0.0
    other_observers: list[str] = field(default_factory=list)


class _HitState:
    """Per-trigger hit accumulator.

    The reset window is anchored at the FIRST press of the chain
    (v0.6.6, owner bench ruling): all min_hits presses must land within
    ``TRIGGER_HIT_RESET_WINDOW_S`` of the first one, which is what the
    trigger dialog's "within 5s" copy always promised. Before v0.6.6
    the window slid on every press, so a chain of slow presses with
    sub-5s gaps could accumulate to the threshold across an arbitrary
    total span (two presses, a long thoughtful pause, two more = fire).
    A press that arrives after the window closes starts a fresh chain
    and counts as its first hit.
    """

    __slots__ = ("count", "first_hit")

    def __init__(self) -> None:
        self.count: int = 0
        self.first_hit: float = 0.0

    def increment(self, now: float) -> int:
        """Increment hit count, resetting if the window has elapsed."""
        if now - self.first_hit > TRIGGER_HIT_RESET_WINDOW_S:
            self.count = 0
        if self.count == 0:
            self.first_hit = now
        self.count += 1
        return self.count

    def reset(self) -> None:
        self.count = 0
        self.first_hit = 0.0


class TriggerManager:
    """Manages trigger matching, hit counting, and event firing.

    Call ``on_signal_captured()`` from the signal monitor for every parsed
    IR reception. The manager checks all enabled triggers, applies receiver
    scope, tracks hits (deduplicated across receivers of the same press),
    and fires the corresponding event entity when thresholds are met.
    """

    def __init__(self, hass: HomeAssistant, store: HAIRStore) -> None:
        self._hass = hass
        self._store = store
        self._hit_states: dict[str, _HitState] = {}
        self._subscribers: list[Callable[[dict[str, Any]], None]] = []

        # Multi-receiver dedup (v0.5.7). A single physical press captured by
        # several receivers within MULTI_RECEIVER_DEDUP_WINDOW_S counts once
        # per (trigger_id, fingerprint): the second and later observations are
        # gated out before the hit increment, so min_hits still counts distinct
        # presses and a matching trigger fires at most once per press.
        # Keyed on trigger id alone (unified identity): see the dedup
        # comment in on_signal_captured.
        self._recent_fires: dict[str, float] = {}
        # Best-effort per-fingerprint observation tracking for the diagnostic
        # log line only.
        self._pending_obs: dict[str, _RecentObservation] = {}
        # Prune counter: _maybe_prune_recent_fires runs every 100 calls.
        self._call_counter: int = 0

        # Callback for event entity platform to register its trigger handler.
        self._entity_fire_callback: Callable[[str, dict[str, Any]], None] | None = None

    def register_entity_callback(
        self, callback: Callable[[str, dict[str, Any]], None]
    ) -> None:
        """Register the event entity platform's fire callback.

        Args:
            callback: Called with (trigger_id, event_data) when a trigger fires.
        """
        self._entity_fire_callback = callback

    def on_signal_captured(
        self,
        fingerprint: str,
        protocol: str | None,
        code: str | None,
        source_device_fp: str | None = None,
        receiver_entity_id: str | None = None,
        byte_hash: str | None = None,
        decoded_fingerprint: str | None = None,
    ) -> list[str]:
        """Process an incoming signal against all enabled triggers.

        Threads the capturing ``receiver_entity_id`` (or ``None`` for legacy
        ESPHome-bridge captures) plus the signal's ``byte_hash`` and
        ``decoded_fingerprint``; matching is the tiered identity rule
        (v0.5.8 unified identity, decoded > byte_hash > S/L fingerprint),
        so a boundary protocol's fingerprint flip no longer disconnects a
        trigger from its button. Applies each trigger's receiver scope,
        then the existing ``min_hits`` accumulation, with a sliding
        per-trigger dedup so one physical press counts once even for
        protocols that transmit several full frames per press (Sony sends
        4-5 at ~45ms spacing; each skipped frame refreshes the window).

        Returns the list of trigger IDs that fired (for caller awareness).
        """
        now = time.monotonic()

        self._call_counter += 1
        if self._call_counter % 100 == 0:
            self._maybe_prune_recent_fires()

        # Track observations of this fingerprint for the diagnostic log line.
        obs = self._pending_obs.get(fingerprint)
        if obs is None or (now - obs.observed_at) > MULTI_RECEIVER_DEDUP_WINDOW_S:
            obs = _RecentObservation(
                first_receiver=receiver_entity_id, observed_at=now
            )
            self._pending_obs[fingerprint] = obs
        elif (
            receiver_entity_id
            and receiver_entity_id != obs.first_receiver
            and receiver_entity_id not in obs.other_observers
        ):
            obs.other_observers.append(receiver_entity_id)

        triggers = self._store.get_triggers_for_signal(
            protocol, code, fingerprint, byte_hash, decoded_fingerprint
        )
        if not triggers:
            return []

        fired_ids: list[str] = []
        # Resolve the receiver's area lazily -- only if a trigger actually
        # fires -- so the registry chain isn't walked on every capture.
        area_resolved = False
        area_id: str | None = None
        area_name: str | None = None

        for trigger in triggers:
            if not trigger.matches_receiver(receiver_entity_id):
                continue

            # Cross-receiver dedup: within the window, a repeat capture of
            # the same press for this trigger is skipped entirely -- no hit
            # increment, no fire -- so min_hits counts distinct presses.
            # The window SLIDES (v0.5.8): a skipped capture refreshes the
            # timestamp, so protocols that transmit several full frames per
            # press (Sony: 4-5 frames ~45ms apart, longer than the window
            # end to end) collapse into one hit instead of re-firing on
            # frame 3 and frame 5. Two intentional presses are never this
            # close together; NEC dittos are filtered before this point.
            #
            # Keyed on the trigger id ALONE (unified identity): under
            # tiered matching two receivers can compute DIFFERENT
            # fingerprints for one physical press (the Sony boundary flip)
            # and both reach this point via byte_hash, so a
            # fingerprint-qualified key would double-fire. This aligns the
            # dedup key with ``_hit_states``, which was already
            # trigger-global, and closes the dual-path capture hole
            # (native PRONTO fp vs legacy protocol:code fp) for free. One
            # trigger cannot legitimately match two different buttons
            # inside the window: same-fingerprint siblings shared a key
            # already, and the RC-6 bin-share corner is a case where
            # collapsing is the correct outcome.
            key = trigger.id
            if now - self._recent_fires.get(key, 0.0) < MULTI_RECEIVER_DEDUP_WINDOW_S:
                self._recent_fires[key] = now
                continue
            self._recent_fires[key] = now

            state = self._hit_states.get(trigger.id)
            if state is None:
                state = _HitState()
                self._hit_states[trigger.id] = state

            count = state.increment(now)

            if count >= trigger.min_hits:
                if not area_resolved:
                    area_id, area_name = self._resolve_receiver_area(
                        receiver_entity_id
                    )
                    area_resolved = True
                self._fire_trigger(
                    trigger,
                    count,
                    source_device_fp,
                    receiver_entity_id,
                    area_id,
                    area_name,
                )
                state.reset()
                fired_ids.append(trigger.id)

                # Diagnostic: a scoped trigger fired while other receivers also
                # observed the same press within the dedup window.
                if trigger.receiver_entity_ids and obs.other_observers:
                    _LOGGER.info(
                        "Trigger '%s' fired from %s; signal also observed by %s",
                        trigger.name,
                        receiver_entity_id or "<unknown>",
                        ", ".join(obs.other_observers),
                    )

        return fired_ids

    def _maybe_prune_recent_fires(self) -> None:
        """Evict stale ``_recent_fires`` entries (older than 5x the window).

        Called every 100 captures from ``on_signal_captured``. Bounded and
        cheap; keeps the dedup map from growing with the number of distinct
        triggers seen over the process lifetime.
        """
        now = time.monotonic()
        cutoff = 5 * MULTI_RECEIVER_DEDUP_WINDOW_S
        self._recent_fires = {
            k: v for k, v in self._recent_fires.items() if now - v < cutoff
        }

    def _resolve_receiver_area(
        self, receiver_entity_id: str | None
    ) -> tuple[str | None, str | None]:
        """Resolve a receiver entity to its ``(area_id, area_name)``.

        Walks the entity -> device -> area registry chain at fire time (not
        persisted on the trigger) so area renames and device moves are
        reflected without any migration. Returns ``(None, None)`` when the
        receiver is unknown, deviceless, or unassigned to an area. Registry
        accessors are synchronous.
        """
        if not receiver_entity_id:
            return None, None
        ent_reg = er.async_get(self._hass)
        dev_reg = dr.async_get(self._hass)
        area_reg = ar.async_get(self._hass)

        entity_entry = ent_reg.async_get(receiver_entity_id)
        if entity_entry is None or entity_entry.device_id is None:
            return None, None
        device_entry = dev_reg.async_get(entity_entry.device_id)
        if device_entry is None or device_entry.area_id is None:
            return None, None
        area_id = device_entry.area_id
        area = area_reg.async_get_area(area_id)
        return area_id, (area.name if area else None)

    def _fire_trigger(
        self,
        trigger: IRTrigger,
        hit_count: int,
        source_device_fp: str | None,
        receiver_entity_id: str | None = None,
        receiver_area_id: str | None = None,
        receiver_area_name: str | None = None,
    ) -> None:
        """Fire the HA event and notify subscribers."""
        now_iso = datetime.now(UTC).isoformat()
        event_data = {
            "trigger_id": trigger.id,
            "trigger_name": trigger.name,
            "hit_count": hit_count,
            "protocol": trigger.protocol,
            "code": trigger.code,
            "source_remote": source_device_fp,
            "timestamp": now_iso,
            # Location-aware fields (v0.5.7). None for legacy captures or a
            # receiver whose device has no HA area assignment.
            "receiver_entity_id": receiver_entity_id,
            "receiver_area_id": receiver_area_id,
            "receiver_area_name": receiver_area_name,
        }

        # Fire the event entity.
        if self._entity_fire_callback is not None:
            self._entity_fire_callback(trigger.id, event_data)

        # Fire a general HA bus event (for automations listening directly).
        self._hass.bus.async_fire(EVENT_TRIGGER_FIRED, event_data)

        _LOGGER.debug(
            "Trigger %s (%s) fired with %d hits",
            trigger.name,
            trigger.id,
            hit_count,
        )

        # Notify WebSocket subscribers (for frontend card glow).
        for cb in self._subscribers:
            try:
                cb(event_data)
            except Exception:
                _LOGGER.exception("Error notifying trigger subscriber")

    # -----------------------------------------------------------------
    # Rewire (edit/snap of a bound signal or command)
    # -----------------------------------------------------------------

    async def rewire(
        self,
        old_fingerprint: str,
        new_fingerprint: str,
        new_protocol: str | None,
        new_code: str | None,
        old_byte_hash: str | None = None,
        new_byte_hash: str | None = None,
        old_decoded_fingerprint: str | None = None,
        new_decoded_fingerprint: str | None = None,
    ) -> dict[str, list[str]]:
        """Repoint triggers from an old signal identity to a new one.

        Used when an edit changes a signal/command's identity. Identity is
        the (S/L fingerprint, byte_hash, decoded_fingerprint) triple
        (v0.5.8): a sub-threshold edit (Sony code A to Sony code B) changes
        ONLY the byte_hash, so this must run on ANY component changing, not
        just the fingerprint. Callers capture ``old_byte_hash`` and
        ``old_decoded_fingerprint`` BEFORE mutating the signal/command.

        Repoint rule: a trigger on the old fingerprint is rewired when its
        byte-level and decoded identities are each either unknown on one
        side or equal -- precise for scoped triggers, broad for legacy
        ones; a trigger scoped to a DIFFERENT sibling identity is left
        alone. Every rewired trigger is stamped with the full new identity
        (``new_byte_hash``, ``new_decoded_fingerprint``), which promotes
        legacy triggers to precise identity; the edit gives us certain
        knowledge of the new identity, so this is a strict improvement.
        (Note the tiered matcher itself would keep an unstamped trigger
        firing across a fingerprint-only change via byte_hash, but stamping
        keeps stored identity honest rather than relying on the rescue.)

        v0.5.7: multiple triggers per fingerprint are legal (they may carry
        different receiver scopes), so there is no collision rejection -- all
        matching triggers are rewired, then a single ``async_save`` persists.

        Returns ``{"rewired": [names], "skipped": []}``; ``skipped`` is kept in
        the shape for callers but is always empty now that collisions are legal.
        """
        rewired: list[str] = []
        skipped: list[str] = []
        if not new_fingerprint:
            return {"rewired": rewired, "skipped": skipped}
        if (
            old_fingerprint == new_fingerprint
            and old_byte_hash == new_byte_hash
            and old_decoded_fingerprint == new_decoded_fingerprint
        ):
            return {"rewired": rewired, "skipped": skipped}

        changed = False
        for trigger in self._store.get_all_triggers():
            if trigger.signal_fingerprint != old_fingerprint:
                continue
            if (
                trigger.byte_hash is not None
                and old_byte_hash is not None
                and trigger.byte_hash != old_byte_hash
            ):
                # Scoped to a DIFFERENT button on the same fingerprint
                # (sub-threshold sibling); this edit is not its signal.
                continue
            if (
                trigger.decoded_fingerprint is not None
                and old_decoded_fingerprint is not None
                and trigger.decoded_fingerprint != old_decoded_fingerprint
            ):
                # Same guard, decoded tier: bound to a different decoded
                # identity that merely shares the S/L fingerprint.
                continue
            trigger.signal_fingerprint = new_fingerprint
            trigger.protocol = new_protocol
            trigger.code = new_code
            trigger.byte_hash = new_byte_hash
            trigger.decoded_fingerprint = new_decoded_fingerprint
            self._store.update_trigger(trigger)
            rewired.append(trigger.name)
            changed = True

        if changed:
            await self._store.async_save()
        return {"rewired": rewired, "skipped": skipped}

    # -----------------------------------------------------------------
    # Subscriber management (WebSocket push for card glow)
    # -----------------------------------------------------------------

    def subscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register a callback for real-time trigger fire notifications."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Remove a previously registered callback."""
        with contextlib.suppress(ValueError):
            self._subscribers.remove(callback)
