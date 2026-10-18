"""BroadSniff: HAIR opens and closes a Broadlink's capture window.

BroadSniff (``DAB-LABS/broadsniff``, domain ``broadsniff``) gives a
Broadlink RM remote an IR receiver on Home Assistant's infrared
platform, and HAIR hears it through the native receiver path like any
other receiver. The catch is that the remote only hears codes while
BroadSniff has a capture window open, and BroadSniff closes that window
on its own (after its window length, restarted by each code in its
``sliding`` mode, or after the first code in ``single``).

This module is the whole of what HAIR knows about BroadSniff. It talks
to it only through the entity registry and Home Assistant services:
nothing here imports BroadSniff, and when BroadSniff is not installed
every lookup answers "not a BroadSniff receiver", so HAIR behaves
exactly as before.

The contract, from BroadSniff 0.1.0. Every entity on a BroadSniff
remote has platform ``broadsniff``, sits on that remote's device, and
has a unique ID of ``<prefix>-<suffix>``, with one prefix for all of a
remote's entities (the remote's MAC in practice). Entity IDs and names
are never matched: users rename them, and an entity ID gains an area
prefix depending on when its device got an area.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)

PLATFORM = "broadsniff"

SUFFIX_RECEIVER = "receiver"
SUFFIX_SWITCH = "ir_capture"
SUFFIX_MODE = "capture_mode"
SUFFIX_WINDOW = "capture_window"
SUFFIX_CODES = "codes_captured"

# BroadSniff's capture modes, as its select reports them.
MODE_SINGLE = "single"

ATTR_WINDOW_ENDS_AT = "window_ends_at"

# The error a capture session ends with when the remote will not open a
# window. The code lets the panel show its own translated wording.
ARM_FAILED_CODE = "broadsniff_arm_failed"
ARM_FAILED_MESSAGE = "The Broadlink could not start listening"

# A window that closes again within this long of HAIR opening it is a
# remote that is not really listening. Re-arming it would be a tight
# loop, so the session ends instead (brief item 5: no tight re-arm).
REARM_MIN_INTERVAL_S = 0.5


class BroadSniffArmError(Exception):
    """A BroadSniff remote could not open a capture window."""

    code = ARM_FAILED_CODE

    def __init__(self, message: str = ARM_FAILED_MESSAGE) -> None:
        super().__init__(message)


@dataclass(frozen=True)
class BroadSniffRemote:
    """One BroadSniff remote, as entity IDs resolved from the registry."""

    receiver: str
    switch: str
    device_id: str
    mode: str | None = None
    window: str | None = None
    codes: str | None = None


def broadsniff_remote(
    hass: HomeAssistant, receiver_entity_id: str
) -> BroadSniffRemote | None:
    """The BroadSniff remote behind a receiver entity, or None.

    None for anything that is not a BroadSniff IR receiver with an IR
    capture switch beside it, and for any registry trouble: a lookup
    must never turn into a failure somewhere else in HAIR.
    """
    try:
        registry = er.async_get(hass)
        entry = registry.async_get(receiver_entity_id)
        if (
            entry is None
            or getattr(entry, "platform", None) != PLATFORM
            or not getattr(entry, "device_id", None)
        ):
            return None
        unique_id = str(getattr(entry, "unique_id", "") or "")
        tail = f"-{SUFFIX_RECEIVER}"
        if not unique_id.endswith(tail):
            return None
        # The prefix keeps its trailing "-", so a sibling is exactly
        # prefix + suffix and never another remote's entity.
        prefix = unique_id[: -len(SUFFIX_RECEIVER)]
        by_suffix: dict[str, str] = {}
        for sibling in er.async_entries_for_device(registry, entry.device_id):
            if getattr(sibling, "platform", None) != PLATFORM:
                continue
            sibling_uid = str(getattr(sibling, "unique_id", "") or "")
            if sibling_uid.startswith(prefix):
                by_suffix[sibling_uid[len(prefix):]] = sibling.entity_id
    except Exception:  # registry trouble is "not BroadSniff", never a crash
        _LOGGER.debug("BroadSniff lookup failed for %s", receiver_entity_id)
        return None
    switch = by_suffix.get(SUFFIX_SWITCH)
    if switch is None:
        return None
    return BroadSniffRemote(
        receiver=receiver_entity_id,
        switch=switch,
        device_id=entry.device_id,
        mode=by_suffix.get(SUFFIX_MODE),
        window=by_suffix.get(SUFFIX_WINDOW),
        codes=by_suffix.get(SUFFIX_CODES),
    )


def ir_capture_switch(hass: HomeAssistant, receiver_entity_id: str) -> str | None:
    """The IR capture switch paired with a receiver, or None.

    The one helper every BroadSniff path in HAIR goes through.
    """
    remote = broadsniff_remote(hass, receiver_entity_id)
    return remote.switch if remote is not None else None


def list_broadsniff_receivers(hass: HomeAssistant) -> list[dict[str, Any]]:
    """One row per BroadSniff receiver, for the Sniffer's Listen row.

    Empty when BroadSniff is not installed, or on a Home Assistant too
    old to have receivers at all. The panel reads each entity's live
    state from its own copy of the state machine; this only says which
    entities belong together and what the remote is called.
    """
    try:
        from homeassistant.components.infrared import (  # type: ignore[attr-defined]
            async_get_receivers,
        )
    except (ImportError, AttributeError):
        return []
    rows: list[dict[str, Any]] = []
    device_registry = dr.async_get(hass)
    for receiver in async_get_receivers(hass):
        remote = broadsniff_remote(hass, receiver)
        if remote is None:
            continue
        name = receiver
        device = device_registry.async_get(remote.device_id)
        if device is not None:
            name = device.name_by_user or device.name or name
        rows.append({
            "receiver_entity_id": remote.receiver,
            "switch_entity_id": remote.switch,
            "mode_entity_id": remote.mode,
            "window_entity_id": remote.window,
            "codes_entity_id": remote.codes,
            "ha_device_id": remote.device_id,
            "name": str(name),
        })
    rows.sort(key=lambda row: row["name"].casefold())
    return rows


async def _async_switch(hass: HomeAssistant, switch: str, on: bool) -> None:
    await hass.services.async_call(
        "switch",
        "turn_on" if on else "turn_off",
        {"entity_id": switch},
        blocking=True,
    )


async def async_set_listening(
    hass: HomeAssistant, receiver_entity_id: str, on: bool
) -> None:
    """Open or close a BroadSniff remote's capture window.

    Raises ValueError for a receiver that is not BroadSniff's, so HAIR
    can never toggle an entity that is not a BroadSniff capture switch,
    and BroadSniffArmError when the remote will not open a window.
    """
    switch = ir_capture_switch(hass, receiver_entity_id)
    if switch is None:
        raise ValueError(f"{receiver_entity_id} is not a BroadSniff receiver")
    try:
        await _async_switch(hass, switch, on)
    except Exception as err:
        if not on:
            raise
        raise BroadSniffArmError() from err


class BroadSniffSessionArm:
    """Keeps one remote listening for the length of one capture session.

    Start opens a window unless one is already open. While the session
    runs, a window that closes is opened again, except in ``single``
    mode, where the window IS the session: its first code is the
    capture, and a window that closes empty ends the session (owner
    ruling 2026-10-17). Stop closes the window only if HAIR opened the
    one that is open; a window the user opened is left alone, and so is
    a window that is not open any more.

    A remote that will not open a window ends the session with
    ``on_failure`` and is never retried. A window that closes again
    straight after HAIR opened it counts as the same failure, so a
    remote that is not really listening cannot be re-armed in a loop.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        remote: BroadSniffRemote,
        *,
        on_failure: Callable[[BroadSniffArmError], None],
        on_window_closed: Callable[[], None],
    ) -> None:
        self._hass = hass
        self._remote = remote
        self._on_failure = on_failure
        self._on_window_closed = on_window_closed
        self._owned = False
        self._stopped = False
        self._armed_at: float | None = None
        self._unsubscribe: Callable[[], None] | None = None

    @property
    def owns_window(self) -> bool:
        """Whether the open window, if any, is one HAIR opened."""
        return self._owned

    def _switch_on(self) -> bool:
        state = self._hass.states.get(self._remote.switch)
        return state is not None and state.state == "on"

    def _mode(self) -> str | None:
        if self._remote.mode is None:
            return None
        state = self._hass.states.get(self._remote.mode)
        return state.state if state is not None else None

    async def _async_open(self) -> None:
        try:
            await _async_switch(self._hass, self._remote.switch, True)
        except Exception as err:
            raise BroadSniffArmError() from err
        self._owned = True
        self._armed_at = monotonic()

    async def async_start(self) -> None:
        """Open a window for the session; raises BroadSniffArmError."""
        from homeassistant.helpers.event import async_track_state_change_event

        if not self._switch_on():
            await self._async_open()
        self._unsubscribe = async_track_state_change_event(
            self._hass, [self._remote.switch], self._on_switch_event
        )

    @callback
    def _on_switch_event(self, event: Any) -> None:
        if self._stopped:
            return
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state != "off":
            return
        # The window that just closed is no longer anyone's to close.
        self._owned = False
        if self._mode() == MODE_SINGLE:
            self._on_window_closed()
            return
        if (
            self._armed_at is not None
            and monotonic() - self._armed_at < REARM_MIN_INTERVAL_S
        ):
            self._fail(BroadSniffArmError())
            return
        self._hass.async_create_task(self._async_rearm())

    async def _async_rearm(self) -> None:
        if self._stopped:
            return
        try:
            await self._async_open()
        except BroadSniffArmError as err:
            self._fail(err)

    def _fail(self, err: BroadSniffArmError) -> None:
        if self._stopped:
            return
        self._detach()
        self._on_failure(err)

    def _detach(self) -> None:
        self._stopped = True
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None

    async def async_stop(self) -> None:
        """End the session: stop re-arming, close HAIR's own window."""
        self._detach()
        if self._owned and self._switch_on():
            self._owned = False
            try:
                await _async_switch(self._hass, self._remote.switch, False)
            except Exception:  # a close that fails leaves BroadSniff's own timer
                _LOGGER.warning(
                    "Could not close the capture window on %s",
                    self._remote.switch,
                )
