"""Trigger manager for HAIR.

Tracks per-trigger hit counts and fires HA event entities when the
configured ``min_hits`` threshold is reached within the reset window.
"""
from __future__ import annotations

import contextlib
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    EVENT_TRIGGER_FIRED,
    TRIGGER_HIT_RESET_WINDOW_S,
)
from .models import IRTrigger
from .storage import HAIRStore

_LOGGER = logging.getLogger(__name__)


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

    Call ``on_signal()`` from the signal monitor for every parsed IR
    reception. The manager checks all enabled triggers, tracks hits,
    and fires the corresponding event entity when thresholds are met.
    """

    def __init__(self, hass: HomeAssistant, store: HAIRStore) -> None:
        self._hass = hass
        self._store = store
        self._hit_states: dict[str, _HitState] = {}
        self._subscribers: list[Callable[[dict[str, Any]], None]] = []

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

    def on_signal(
        self,
        fingerprint: str,
        protocol: str | None,
        code: str | None,
        source_device_fp: str | None = None,
    ) -> list[str]:
        """Process an incoming signal against all enabled triggers.

        Returns list of trigger IDs that fired (for caller awareness).
        """
        triggers = self._store.get_triggers_for_signal(
            protocol, code, fingerprint
        )
        if not triggers:
            return []

        now = time.monotonic()
        fired_ids: list[str] = []

        for trigger in triggers:
            state = self._hit_states.get(trigger.id)
            if state is None:
                state = _HitState()
                self._hit_states[trigger.id] = state

            count = state.increment(now)

            if count >= trigger.min_hits:
                self._fire_trigger(trigger, count, source_device_fp)
                state.reset()
                fired_ids.append(trigger.id)

        return fired_ids

    def _fire_trigger(
        self,
        trigger: IRTrigger,
        hit_count: int,
        source_device_fp: str | None,
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
