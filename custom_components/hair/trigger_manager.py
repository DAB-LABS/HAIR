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
    """Per-trigger hit accumulator."""

    __slots__ = ("count", "last_hit")

    def __init__(self) -> None:
        self.count: int = 0
        self.last_hit: float = 0.0

    def increment(self, now: float) -> int:
        """Increment hit count, resetting if the window has elapsed."""
        if now - self.last_hit > TRIGGER_HIT_RESET_WINDOW_S:
            self.count = 0
        self.count += 1
        self.last_hit = now
        return self.count

    def reset(self) -> None:
        self.count = 0
        self.last_hit = 0.0


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
        self._recent_fires: dict[tuple[str, str], float] = {}
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
    ) -> list[str]:
        """Process an incoming signal against all enabled triggers.

        Threads the capturing ``receiver_entity_id`` (or ``None`` for legacy
        ESPHome-bridge captures). Applies each trigger's receiver scope, then
        the existing ``min_hits`` accumulation, with a 60ms cross-receiver
        dedup so one physical press counts once per (trigger, fingerprint).

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

        triggers = self._store.get_triggers_for_signal(protocol, code, fingerprint)
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

            # Cross-receiver dedup: within the window, a repeat capture of the
            # same press for this (trigger, fingerprint) is skipped entirely --
            # no hit increment, no fire -- so min_hits counts distinct presses.
            key = (trigger.id, fingerprint)
            if now - self._recent_fires.get(key, 0.0) < MULTI_RECEIVER_DEDUP_WINDOW_S:
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
        (trigger, fingerprint) pairs seen over the process lifetime.
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
    ) -> dict[str, list[str]]:
        """Repoint triggers from an old signal fingerprint to a new one.

        Used when an edit changes a signal/command's S/L fingerprint: every
        trigger bound to the old fingerprint is updated to the new
        ``(signal_fingerprint, protocol, code)`` together so it keeps firing
        on the edited signal. A no-op when the fingerprint is unchanged (snap
        and byte-only edits preserve the S/L fingerprint).

        v0.5.7: multiple triggers per fingerprint are legal (they may carry
        different receiver scopes), so there is no collision rejection -- all
        matching triggers are rewired. All matching triggers are mutated in
        memory, then a single ``async_save`` persists.

        Returns ``{"rewired": [names], "skipped": []}``; ``skipped`` is kept in
        the shape for callers but is always empty now that collisions are legal.
        """
        rewired: list[str] = []
        skipped: list[str] = []
        if not new_fingerprint or old_fingerprint == new_fingerprint:
            return {"rewired": rewired, "skipped": skipped}

        changed = False
        for trigger in self._store.get_all_triggers():
            if trigger.signal_fingerprint != old_fingerprint:
                continue
            trigger.signal_fingerprint = new_fingerprint
            trigger.protocol = new_protocol
            trigger.code = new_code
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
