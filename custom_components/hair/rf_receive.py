"""Hearing through Home Assistant's radio frequency receivers.

Home Assistant 2026.11 gives the ``radio_frequency`` platform receivers
shaped like the infrared ones: a ``RadioFrequencyReceiverEntity`` per
receiver, ``async_subscribe_receiver`` to hear it, and a received signal
carrying signed microsecond timings, a frequency (or None) and a
modulation. This module finds those receivers, decides which HAIR
listens to, keeps the subscriptions alive across reloads and renames,
and hands each capture to the signal monitor.

WHICH RECEIVERS HAIR LISTENS TO. A receiver whose state carries
``capturing`` is a capture device (``docs/windowed-receivers.md``): it
hears only inside a window the user opened, so it cannot flood the
catalog, and HAIR subscribes to it as soon as it appears. A receiver
without ``capturing`` listens all the time. Radio receivers of that kind
report several thousand noise captures an hour, so HAIR lists one and
subscribes to it only once the user opts it in (``rf_window.py``), and
then mints new rows from it only while its software Listen window is
open. The infrared GH #72 filter is not consulted here; it stays on the
infrared inventory.

EVERY CALL IS GUARDED. The ``radio_frequency`` component loads only when
some integration forwards a platform to it, and every core helper raises
``component_not_loaded`` otherwise. HAIR loads on cores without the
platform at all (the floor is 2026.6; the platform arrived in 2026.11),
so nothing here imports it at module level.

THE FREQUENCY OF A CODE, in order: the received signal's own
``frequency`` (``signal``); else the receiver's ``frequency_hz``
attribute while its ``capture_phase`` reads ``listening``, the carrier
the open window listens on (``window``); else the receiver's declared
range when it is one fixed value (``receiver``); else none, and the row's
band reads unknown.
"""
from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_added_domain,
    async_track_state_change_event,
    async_track_state_removed_domain,
)

from .const import (
    RF_FREQUENCY_SOURCE_RECEIVER,
    RF_FREQUENCY_SOURCE_SIGNAL,
    RF_FREQUENCY_SOURCE_WINDOW,
)
from .receiver_window import (
    ATTR_CAPTURE_PHASE,
    ATTR_FREQUENCY_HZ,
    PHASE_LISTENING,
    says_capture,
)

_LOGGER = logging.getLogger(__name__)

RF_DOMAIN = "radio_frequency"
RECEIVER_DEVICE_CLASS = "receiver"


def rf_component(hass: HomeAssistant) -> Any | None:
    """The ``radio_frequency`` entity component, or None when not loaded."""
    try:
        from homeassistant.components.radio_frequency.const import (  # type: ignore[import-not-found]
            DATA_COMPONENT,
        )
    except ImportError:
        return None
    return hass.data.get(DATA_COMPONENT)


def is_rf_receiver_state(state: Any) -> bool:
    """Whether a state is a radio frequency receiver's."""
    return (
        state is not None
        and state.entity_id.startswith(f"{RF_DOMAIN}.")
        and state.attributes.get("device_class") == RECEIVER_DEVICE_CLASS
    )


def rf_receiver_ids(hass: HomeAssistant) -> list[str]:
    """Every radio frequency receiver in the state machine, sorted."""
    async_all = getattr(hass.states, "async_all", None)
    if async_all is None:
        return []
    return sorted(
        state.entity_id
        for state in async_all(RF_DOMAIN)
        if is_rf_receiver_state(state)
    )


def supported_ranges(hass: HomeAssistant, entity_id: str) -> list[tuple[int, int]] | None:
    """A receiver's declared ``(min_hz, max_hz)`` ranges, or None if unknown.

    Ranges are not state attributes; they live on the entity object, read
    the way core's own websocket command reads them.
    """
    component = rf_component(hass)
    if component is None:
        return None
    try:
        entity = component.get_entity(entity_id)
        if entity is None:
            return None
        return [
            (int(low), int(high)) for low, high in entity.supported_frequency_ranges
        ]
    except Exception:
        _LOGGER.debug("Could not read the ranges of %s", entity_id, exc_info=True)
        return None


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def fixed_frequency(ranges: list[tuple[int, int]] | None) -> int | None:
    """The one carrier a receiver is fixed to, or None.

    One range with ``min == max != 0``. A ``(0, 0)`` range means the
    receiver declares no frequency, never a fixed 0 Hz.
    """
    if not ranges or len(ranges) != 1:
        return None
    low, high = ranges[0]
    return low if low == high and low else None


def frequency_of(
    hass: HomeAssistant, entity_id: str, signal: Any
) -> tuple[int | None, str | None]:
    """The carrier of a code heard on a receiver, and where it came from."""
    frequency = getattr(signal, "frequency", None)
    if _positive_int(frequency):
        return frequency, RF_FREQUENCY_SOURCE_SIGNAL
    state = hass.states.get(entity_id)
    if state is not None and state.attributes.get(ATTR_CAPTURE_PHASE) == PHASE_LISTENING:
        window = state.attributes.get(ATTR_FREQUENCY_HZ)
        if _positive_int(window):
            return window, RF_FREQUENCY_SOURCE_WINDOW
    fixed = fixed_frequency(supported_ranges(hass, entity_id))
    if fixed is not None:
        return fixed, RF_FREQUENCY_SOURCE_RECEIVER
    return None, None


def listens_to(state: Any) -> bool:
    """Whether HAIR subscribes to this receiver: a capture device, available."""
    return (
        is_rf_receiver_state(state)
        and state.state != STATE_UNAVAILABLE
        and says_capture(state)
    )


def is_always_on(state: Any) -> bool:
    """An available radio receiver that listens all the time (no ``capturing``)."""
    return (
        is_rf_receiver_state(state)
        and state.state != STATE_UNAVAILABLE
        and not says_capture(state)
    )


class RfReceiverTracker:
    """Keeps HAIR subscribed to every radio capture device, and to every
    always-on radio receiver the user opted in.

    Mirrors the infrared path in ``signal_monitor``: the domain
    add/remove trackers catch receivers appearing, a state watcher over
    every radio receiver catches one becoming available or becoming a
    capture device, and a receiver going unavailable releases its
    subscription, because across a reload its entity object is replaced
    and a handle on the old one would hear nothing. Coming back,
    reconcile subscribes the current object.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        on_signal: Callable[[Any, str], None],
        *,
        opted_in: Callable[[str], bool] | None = None,
        on_attach: Callable[[str], None] | None = None,
        on_detach: Callable[[str], None] | None = None,
    ) -> None:
        self._hass = hass
        self._on_signal = on_signal
        # Always-on receivers: whether the user opted one in (by entity
        # id), and who to tell when HAIR starts or stops hearing one.
        self._opted_in = opted_in or (lambda _entity_id: False)
        self._on_attach = on_attach
        self._on_detach = on_detach
        self._always_on: set[str] = set()
        self._subs: dict[str, CALLBACK_TYPE] = {}
        self._unsubs: list[CALLBACK_TYPE] = []
        self._watch_unsub: CALLBACK_TYPE | None = None
        self._watched: tuple[str, ...] = ()

    @property
    def subscribed(self) -> list[str]:
        """The receivers HAIR is listening to now."""
        return sorted(self._subs)

    @callback
    def async_start(self) -> None:
        """Track the radio domain and subscribe to what is there."""
        self._unsubs.append(
            async_track_state_added_domain(self._hass, RF_DOMAIN, self._on_added)
        )
        self._unsubs.append(
            async_track_state_removed_domain(self._hass, RF_DOMAIN, self._on_removed)
        )
        self.reconcile()

    @callback
    def async_stop(self) -> None:
        """Release every subscription and tracker."""
        for unsub in self._unsubs:
            with contextlib.suppress(Exception):
                unsub()
        self._unsubs.clear()
        if self._watch_unsub is not None:
            with contextlib.suppress(Exception):
                self._watch_unsub()
            self._watch_unsub = None
        for entity_id in list(self._subs):
            self._release(entity_id)

    @callback
    def _on_added(self, event: Event) -> None:
        entity_id = (event.data or {}).get("entity_id")
        if entity_id in self._subs:
            self._release(entity_id)
        self.reconcile()

    @callback
    def _on_removed(self, event: Event) -> None:
        entity_id = (event.data or {}).get("entity_id")
        if entity_id in self._subs:
            self._release(entity_id)
        self.reconcile()

    @callback
    def _on_state(self, event: Event) -> None:
        """A radio receiver's state changed: subscribe or release as needed.

        Every heard code bumps the receiver's state, so the common case
        (already subscribed, still a capture device) returns at once.
        """
        data = event.data or {}
        entity_id = data.get("entity_id")
        new_state = data.get("new_state")
        wanted = self._wanted(entity_id, new_state)
        if not wanted and entity_id in self._subs:
            self._release(entity_id)
        elif wanted and entity_id not in self._subs:
            self._subscribe(entity_id)

    @callback
    def reconcile(self) -> None:
        """Bring subscriptions in line with the receivers present now.

        Idempotent; one bad receiver never stops the loop.
        """
        receivers = rf_receiver_ids(self._hass)
        states = self._hass.states
        for entity_id in [e for e in self._subs if e not in receivers]:
            self._release(entity_id)
        for entity_id in receivers:
            wanted = self._wanted(entity_id, states.get(entity_id))
            if wanted and entity_id not in self._subs:
                self._subscribe(entity_id)
            elif not wanted and entity_id in self._subs:
                self._release(entity_id)
        watched = tuple(receivers)
        if watched != self._watched:
            if self._watch_unsub is not None:
                self._watch_unsub()
                self._watch_unsub = None
            if watched:
                self._watch_unsub = async_track_state_change_event(
                    self._hass, list(watched), self._on_state
                )
            self._watched = watched

    def _wanted(self, entity_id: str | None, state: Any) -> bool:
        """A capture device, or an always-on receiver the user opted in."""
        if entity_id is None:
            return False
        return listens_to(state) or (is_always_on(state) and self._opted_in(entity_id))

    @callback
    def _subscribe(self, entity_id: str) -> None:
        try:
            from homeassistant.components.radio_frequency import (  # type: ignore[attr-defined]
                async_subscribe_receiver,
            )
        except ImportError:
            return
        try:
            unsub = async_subscribe_receiver(
                self._hass,
                entity_id,
                lambda signal, rid=entity_id: self._on_signal(signal, rid),
            )
        except Exception:
            _LOGGER.debug(
                "Could not subscribe to radio receiver %s yet", entity_id,
                exc_info=True,
            )
            return
        self._subs[entity_id] = unsub
        if is_always_on(self._hass.states.get(entity_id)):
            self._always_on.add(entity_id)
            if self._on_attach is not None:
                self._on_attach(entity_id)
        _LOGGER.debug("Subscribed to radio receiver %s", entity_id)

    @callback
    def _release(self, entity_id: str) -> None:
        unsub = self._subs.pop(entity_id, None)
        if unsub is not None:
            with contextlib.suppress(Exception):
                unsub()
        if entity_id in self._always_on:
            self._always_on.discard(entity_id)
            if self._on_detach is not None:
                self._on_detach(entity_id)
        _LOGGER.debug("Released radio receiver %s", entity_id)
