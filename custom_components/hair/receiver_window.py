"""Capture devices: infrared receivers that listen only while a window is open.

Some receivers hear codes only while a capture window is open: a
Broadlink through BroadSniff, a learn-mode hub. HAIR opens and closes
that window for the user, from the Sniffer's Listen row, the Devices
card and the code editor's Listen. This module is everything HAIR knows
about such receivers, and it knows no integration by name: a receiver
says it is a capture device through its own state attributes, and any
integration can say so. The published contract is
``docs/windowed-receivers.md``; the attribute names are chosen to map
onto a capture feature on HA core's infrared receiver if core adopts
one, and the contract will follow core if it does.

THE CONTRACT, read from the receiver entity's attributes:

- ``capturing`` (bool, required): the window is open now. Its presence
  is what makes the receiver a capture device. Nothing else does; in
  particular a switch on the receiver's device does not.
- ``capture_switch`` (entity ID, recommended): what HAIR toggles to open
  and close the window.
- ``window_ends_at`` (ISO 8601, optional): when the open window closes,
  for the panel's draining fill.
- ``capture_mode`` (optional, ``single`` | ``sliding`` | ``multiple``):
  only ``single`` changes HAIR's behaviour: the window is the whole
  listen, so HAIR does not re-open it.

UNAVAILABLE RECEIVERS. HA writes no extra attributes while an entity is
unavailable, so a missing ``capturing`` then means nothing. HAIR
remembers which receivers have been capture devices, keyed by registry
entry id, and keeps treating a remembered one as a capture device while
it is unavailable (its chip disabled). Only an available receiver
without ``capturing`` is an ordinary, always-listening receiver, and
that also clears the memory.

WHICH ENTITY OPENS THE WINDOW, in this order (owner ruling, 2026-10-20):

1. ``declared``: the receiver's ``capture_switch``, when it passes the
   safety rule. It is final: the card's switch menu offers it alone,
   and the door that stores a choice refuses the receiver. It is
   remembered while the receiver is unavailable (the store, below). A Broadlink RM4 Pro
   has an IR and an RF capture switch, and the RF one opens a window IR
   presses never reach, so the integration's word is not overridden.
2. ``user``: the entity the user chose on the receiver's card, stored
   by the receiver's registry entry id, so a rename keeps it. A choice
   stored before the receiver declared is kept, unused, and applies
   again if the declaration goes away or fails the safety rule.
3. ``device``: the receiver's device has exactly one enabled ``switch``.
4. none: the card waits for a choice.

THE SAFETY RULE. HAIR toggles only a ``switch`` on the receiver's own
HA device, or an entity the user chose by hand, which must be a
``switch`` or an ``input_boolean``. A declared ``capture_switch`` naming
anything else is ignored, and logged once at debug; the receiver is then
treated as declaring nothing, so a choice applies and the card's menu
comes back. Every door takes a receiver, never an entity to toggle.
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
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

ATTR_CAPTURING = "capturing"
ATTR_CAPTURE_SWITCH = "capture_switch"
ATTR_WINDOW_ENDS_AT = "window_ends_at"
ATTR_CAPTURE_MODE = "capture_mode"

MODE_SINGLE = "single"

SOURCE_USER = "user"
SOURCE_DECLARED = "declared"
SOURCE_DEVICE = "device"

# Domains HAIR will toggle: a declaration or a suggestion must be a
# switch on the receiver's own device; a hand-made choice may also be
# an input_boolean, wherever it lives, because the user picked it.
DECLARED_DOMAINS = frozenset({"switch"})
CHOSEN_DOMAINS = frozenset({"switch", "input_boolean"})

# Error codes the doors send, so the panel can say them in the user's
# language.
ARM_FAILED_CODE = "receiver_arm_failed"
NOT_CAPTURE_DEVICE_CODE = "not_capture_device"
NO_CAPTURE_SWITCH_CODE = "no_capture_switch"
RECEIVER_UNAVAILABLE_CODE = "receiver_unavailable"
CAPTURE_SWITCH_DECLARED_CODE = "capture_switch_declared"

# A window that closes again within this long of HAIR opening it is a
# receiver that is not really listening. Re-opening it would be a tight
# loop, so the listen ends instead.
REARM_MIN_INTERVAL_S = 0.5

STORAGE_KEY = "hair_capture_receivers"
STORAGE_VERSION = 1

_UNAVAILABLE = "unavailable"


class ReceiverArmError(Exception):
    """A capture device could not open its window."""

    code = ARM_FAILED_CODE

    def __init__(self, name: str) -> None:
        super().__init__(f"{name} could not start listening")
        self.name = name


class CaptureDeviceError(ValueError):
    """A door was asked to act on something it cannot act on."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# What a receiver says about itself
# ---------------------------------------------------------------------------


def says_capture(state: Any) -> bool:
    """Whether a receiver's state declares it a capture device."""
    if state is None:
        return False
    return isinstance(state.attributes.get(ATTR_CAPTURING), bool)


def is_available(state: Any) -> bool:
    """Whether HA currently has the receiver loaded and reporting."""
    return state is not None and state.state != _UNAVAILABLE


def is_capturing(state: Any) -> bool:
    """Whether the receiver's window is open now."""
    return state is not None and state.attributes.get(ATTR_CAPTURING) is True


def capture_mode(state: Any) -> str | None:
    if state is None:
        return None
    mode = state.attributes.get(ATTR_CAPTURE_MODE)
    return mode if isinstance(mode, str) else None


def _domain(entity_id: str) -> str:
    return entity_id.split(".", 1)[0]


# ---------------------------------------------------------------------------
# The store: remembered capture devices and hand-made choices
# ---------------------------------------------------------------------------


class CaptureReceiverStore:
    """What HAIR remembers per receiver, keyed by registry entry id.

    ``{entry_id: {"capture": bool, "switch": entity_id | None}}``, plus
    ``"declared": entity_id`` while the receiver declares a valid
    ``capture_switch`` (owner, 2026-10-20). The registry entry id, not the
    entity id, because users rename entities and a rename must keep both
    the memory and the choice.

    The declared switch is remembered because HA writes no extra
    attributes while an entity is unavailable: without it, a declaring
    receiver that goes offline would lose its declaration and offer its
    other switches (an RM4 Pro's RF capture) until it came back. It is
    written only from an available receiver, and cleared when an
    available receiver stops declaring or declares something the safety
    rule refuses.

    A record is dropped on load only when its registry entry no longer
    exists. Never from state or availability: HAIR can load before the
    receiver's integration does, and a state-based check would wipe the
    user's choice on every restart.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._records: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        raw = await self._store.async_load() or {}
        records = raw.get("receivers") if isinstance(raw, dict) else None
        if not isinstance(records, dict):
            records = {}
        registry = er.async_get(self._hass)
        kept: dict[str, dict[str, Any]] = {}
        for entry_id, record in records.items():
            if not isinstance(record, dict):
                continue
            if registry.async_get(entry_id) is None:
                continue  # the receiver itself is gone from the registry
            switch = record.get("switch")
            kept[entry_id] = {
                "capture": bool(record.get("capture")),
                "switch": switch if isinstance(switch, str) and switch else None,
            }
            declared = record.get("declared")
            if isinstance(declared, str) and declared:
                kept[entry_id]["declared"] = declared
        self._records = kept
        if len(kept) != len(records):
            self._schedule_save()

    def _schedule_save(self) -> None:
        self._store.async_delay_save(lambda: {"receivers": self._records}, 1.0)

    def entry_ids(self) -> list[str]:
        """Every receiver HAIR keeps a record for."""
        return list(self._records)

    def remembered(self, entry_id: str | None) -> bool:
        return bool(entry_id and self._records.get(entry_id, {}).get("capture"))

    def choice(self, entry_id: str | None) -> str | None:
        if not entry_id:
            return None
        return self._records.get(entry_id, {}).get("switch")

    def declared(self, entry_id: str | None) -> str | None:
        """The valid capture_switch the receiver last declared while available."""
        if not entry_id:
            return None
        return self._records.get(entry_id, {}).get("declared")

    def note_declared(self, entry_id: str | None, declared: str | None) -> None:
        """Record an available capture device's valid declaration, or its absence."""
        record = self._records.get(entry_id) if entry_id else None
        if record is None or record.get("declared") == declared:
            return
        if declared:
            record["declared"] = declared
        else:
            record.pop("declared", None)
        self._schedule_save()

    def note_capture(self, entry_id: str | None, capture: bool) -> None:
        """Record what an available receiver just said about itself."""
        if not entry_id:
            return
        record = self._records.get(entry_id)
        if record is None:
            if not capture:
                return
            self._records[entry_id] = {"capture": True, "switch": None}
            self._schedule_save()
        elif record["capture"] != capture:
            record["capture"] = capture
            self._schedule_save()

    def set_choice(self, entry_id: str, entity_id: str) -> None:
        record = self._records.setdefault(entry_id, {"capture": True, "switch": None})
        record["capture"] = True
        record["switch"] = entity_id
        self._schedule_save()


def _store(hass: HomeAssistant) -> CaptureReceiverStore | None:
    from .const import DOMAIN

    for value in hass.data.get(DOMAIN, {}).values():
        if isinstance(value, dict) and isinstance(
            value.get("capture_receivers"), CaptureReceiverStore
        ):
            return value["capture_receivers"]
    return None


# ---------------------------------------------------------------------------
# Which entity opens the window
# ---------------------------------------------------------------------------

_refusals_logged: set[tuple[str, str]] = set()


def device_switches(registry: Any, device_id: str | None) -> list[str]:
    """The enabled ``switch`` entities on a device, sorted."""
    if not device_id:
        return []
    return sorted(
        entry.entity_id
        for entry in er.async_entries_for_device(registry, device_id)
        if _domain(entry.entity_id) == "switch"
        and getattr(entry, "disabled_by", None) is None
    )


def _on_receivers_device(registry: Any, entity_id: str, device_id: str | None) -> bool:
    if not device_id or _domain(entity_id) not in DECLARED_DOMAINS:
        return False
    entry = registry.async_get(entity_id)
    return entry is not None and entry.device_id == device_id


@dataclass(frozen=True)
class CaptureDevice:
    """One capture device, resolved."""

    receiver: str
    entry_id: str | None
    device_id: str | None
    available: bool
    switch: str | None
    source: str | None
    switches: tuple[str, ...]


def resolve(
    hass: HomeAssistant, receiver: str, store: CaptureReceiverStore | None = None
) -> CaptureDevice | None:
    """The capture device behind a receiver entity, or None.

    None for a receiver that is not a capture device: an available one
    without ``capturing``, or an unavailable one HAIR has never seen
    declare itself.
    """
    store = store if store is not None else _store(hass)
    registry = er.async_get(hass)
    entry = registry.async_get(receiver)
    entry_id = entry.id if entry is not None else None
    device_id = entry.device_id if entry is not None else None
    state = hass.states.get(receiver)
    available = is_available(state)
    declares = says_capture(state)
    if available and store is not None:
        store.note_capture(entry_id, declares)
    if not declares and not (
        not available and store is not None and store.remembered(entry_id)
    ):
        return None

    switches = tuple(device_switches(registry, device_id))
    switch: str | None = None
    source: str | None = None
    chosen = store.choice(entry_id) if store is not None else None
    declared = state.attributes.get(ATTR_CAPTURE_SWITCH) if state is not None else None
    if not isinstance(declared, str) or not declared:
        declared = None
    if declared is None and not available and store is not None:
        # HA drops the attribute while the receiver is unavailable; the
        # declaration it last made while available still holds.
        declared = store.declared(entry_id)
    if declared is not None:
        if _on_receivers_device(registry, declared, device_id):
            switch, source = declared, SOURCE_DECLARED
        elif (receiver, declared) not in _refusals_logged:
            _refusals_logged.add((receiver, declared))
            _LOGGER.debug(
                "Ignoring capture_switch %s on %s: HAIR only toggles a "
                "switch on the receiver's own device",
                declared, receiver,
            )
    if available and store is not None:
        store.note_declared(entry_id, switch if source == SOURCE_DECLARED else None)
    if switch is None and chosen and _domain(chosen) in CHOSEN_DOMAINS:
        switch, source = chosen, SOURCE_USER
    if switch is None and len(switches) == 1:
        switch, source = switches[0], SOURCE_DEVICE
    return CaptureDevice(
        receiver=receiver,
        entry_id=entry_id,
        device_id=device_id,
        available=available,
        switch=switch,
        source=source,
        switches=switches,
    )


def _name(hass: HomeAssistant, device_id: str | None, entity_id: str) -> str:
    if device_id:
        device = dr.async_get(hass).async_get(device_id)
        if device is not None and (device.name_by_user or device.name):
            return str(device.name_by_user or device.name)
    state = hass.states.get(entity_id)
    if state is not None:
        return str(state.attributes.get("friendly_name") or entity_id)
    return entity_id


def _entity_name(hass: HomeAssistant, entity_id: str) -> str:
    state = hass.states.get(entity_id)
    if state is not None and state.attributes.get("friendly_name"):
        return str(state.attributes["friendly_name"])
    entry = er.async_get(hass).async_get(entity_id)
    if entry is not None and (entry.name or entry.original_name):
        return str(entry.name or entry.original_name)
    return entity_id


def capture_receivers(
    hass: HomeAssistant, store: CaptureReceiverStore | None = None
) -> list[dict[str, Any]]:
    """One row per capture device, for the panel.

    The receivers HA has loaded, plus any remembered capture device
    whose integration has not loaded, so its card stays RX-CAPTURE.
    Empty when no receiver is a capture device.
    """
    store = store if store is not None else _store(hass)
    candidates: list[str] = []
    try:
        from homeassistant.components.infrared import (  # type: ignore[attr-defined]
            async_get_receivers,
        )

        candidates.extend(async_get_receivers(hass))
    except (ImportError, AttributeError):
        pass
    if store is not None:
        registry = er.async_get(hass)
        for entry_id in store.entry_ids():
            entry = registry.async_get(entry_id)
            if entry is not None and entry.entity_id not in candidates:
                candidates.append(entry.entity_id)

    rows: list[dict[str, Any]] = []
    for receiver in candidates:
        found = resolve(hass, receiver, store)
        if found is None:
            continue
        rows.append({
            "receiver_entity_id": receiver,
            "name": _name(hass, found.device_id, receiver),
            "ha_device_id": found.device_id,
            "available": found.available,
            "switch_entity_id": found.switch,
            "source": found.source,
            "device_switches": [
                {"entity_id": s, "name": _entity_name(hass, s)} for s in found.switches
            ],
        })
    rows.sort(key=lambda row: row["name"].casefold())
    return rows


# ---------------------------------------------------------------------------
# Acting on a capture device
# ---------------------------------------------------------------------------


def require(hass: HomeAssistant, receiver: str) -> CaptureDevice:
    """The capture device, ready to toggle, or a CaptureDeviceError."""
    found = resolve(hass, receiver)
    if found is None:
        raise CaptureDeviceError(
            NOT_CAPTURE_DEVICE_CODE, f"{receiver} is not a capture device"
        )
    if not found.available:
        raise CaptureDeviceError(
            RECEIVER_UNAVAILABLE_CODE, f"{receiver} is unavailable"
        )
    if found.switch is None:
        raise CaptureDeviceError(
            NO_CAPTURE_SWITCH_CODE,
            f"No switch is chosen to open {receiver}'s capture window",
        )
    return found


async def _async_toggle(hass: HomeAssistant, entity_id: str, on: bool) -> None:
    await hass.services.async_call(
        _domain(entity_id),
        "turn_on" if on else "turn_off",
        {"entity_id": entity_id},
        blocking=True,
    )


async def async_set_listening(hass: HomeAssistant, receiver: str, on: bool) -> None:
    """Open or close a capture device's window, through its resolved entity.

    Raises CaptureDeviceError for a receiver HAIR cannot act on, and
    ReceiverArmError when the window will not open.
    """
    found = require(hass, receiver)
    try:
        await _async_toggle(hass, found.switch or "", on)
    except Exception as err:
        if not on:
            raise
        raise ReceiverArmError(_name(hass, found.device_id, receiver)) from err


def set_choice(hass: HomeAssistant, receiver: str, entity_id: str) -> None:
    """Store the user's choice of what opens a capture device's window.

    Refused for a receiver that declares a valid ``capture_switch``:
    that switch is final.
    """
    if _domain(entity_id) not in CHOSEN_DOMAINS:
        raise CaptureDeviceError(
            "invalid_capture_switch",
            "Only a switch or an input_boolean can open a capture window",
        )
    store = _store(hass)
    found = resolve(hass, receiver, store)
    if found is None:
        raise CaptureDeviceError(
            NOT_CAPTURE_DEVICE_CODE, f"{receiver} is not a capture device"
        )
    if found.source == SOURCE_DECLARED:
        raise CaptureDeviceError(
            CAPTURE_SWITCH_DECLARED_CODE,
            f"{receiver} names its own capture switch, which cannot be changed",
        )
    if store is None or found.entry_id is None:
        raise CaptureDeviceError(
            "not_registered", f"{receiver} has no registry entry to keep a choice on"
        )
    store.set_choice(found.entry_id, entity_id)


class ReceiverWindowArm:
    """Keeps one capture device listening for the length of one listen.

    Start opens the window unless it is already open. While the listen
    runs, a window that closes is opened again, except in ``single``
    mode, where the window is the whole listen and ``on_window_closed``
    ends it. ``reopen_after_code`` relaxes that for a listen that
    takes several presses (the Fix window's miss ladder, owner ruling
    2026-10-19): a single-mode window that closes after a code arrived
    opens again, and one that closes empty still ends the listen.

    Stop closes the window only if HAIR opened the one that is open; a
    window the user opened is left alone. A window that closes within
    ``REARM_MIN_INTERVAL_S`` of HAIR opening it is a receiver that is
    not really listening: the listen ends with ``on_failure`` instead
    of looping, and nothing is ever retried.

    The window's state is read from the receiver's own ``capturing``,
    the contract, never from the entity that opens it.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        device: CaptureDevice,
        name: str,
        *,
        on_failure: Callable[[ReceiverArmError], None],
        on_window_closed: Callable[[], None],
        reopen_after_code: bool = False,
    ) -> None:
        self._hass = hass
        self._device = device
        self._name = name
        self._on_failure = on_failure
        self._on_window_closed = on_window_closed
        self._reopen_after_code = reopen_after_code
        self._owned = False
        self._stopped = False
        self._armed_at: float | None = None
        self._heard_since_open = False
        self._unsubscribe: Callable[[], None] | None = None

    @property
    def owns_window(self) -> bool:
        return self._owned

    def _open_now(self) -> bool:
        return is_capturing(self._hass.states.get(self._device.receiver))

    async def _async_open(self) -> None:
        try:
            await _async_toggle(self._hass, self._device.switch or "", True)
        except Exception as err:
            raise ReceiverArmError(self._name) from err
        self._owned = True
        self._armed_at = monotonic()
        self._heard_since_open = False

    async def async_start(self) -> None:
        """Open a window for the listen; raises ReceiverArmError."""
        from homeassistant.helpers.event import async_track_state_change_event

        if not self._open_now():
            await self._async_open()
        self._unsubscribe = async_track_state_change_event(
            self._hass, [self._device.receiver], self._on_receiver_event
        )

    def note_code(self) -> None:
        """A code from this receiver reached the listen."""
        self._heard_since_open = True

    @callback
    def _on_receiver_event(self, event: Any) -> None:
        if self._stopped:
            return
        old = event.data.get("old_state")
        new = event.data.get("new_state")
        if not is_capturing(old) or is_capturing(new):
            return  # only an open window closing matters
        self._owned = False
        if capture_mode(new) == MODE_SINGLE and not (
            self._reopen_after_code and self._heard_since_open
        ):
            self._on_window_closed()
            return
        if (
            self._armed_at is not None
            and monotonic() - self._armed_at < REARM_MIN_INTERVAL_S
        ):
            self._fail(ReceiverArmError(self._name))
            return
        self._hass.async_create_task(self._async_rearm())

    async def _async_rearm(self) -> None:
        if self._stopped:
            return
        try:
            await self._async_open()
        except ReceiverArmError as err:
            self._fail(err)

    def _fail(self, err: ReceiverArmError) -> None:
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
        """End the listen: stop re-opening, close HAIR's own window."""
        self._detach()
        if self._owned and self._open_now():
            self._owned = False
            try:
                await _async_toggle(self._hass, self._device.switch or "", False)
            except Exception:  # a close that fails leaves the device's own timer
                _LOGGER.warning(
                    "Could not close the capture window on %s", self._device.receiver
                )


def arm_for(
    hass: HomeAssistant,
    receiver: str,
    *,
    on_failure: Callable[[ReceiverArmError], None],
    on_window_closed: Callable[[], None],
    reopen_after_code: bool = False,
) -> ReceiverWindowArm | None:
    """A window arm for a capture device, or None for any other receiver.

    Raises CaptureDeviceError for a capture device HAIR cannot open
    (unavailable, or no entity chosen to open it).
    """
    found = resolve(hass, receiver)
    if found is None:
        return None
    require(hass, receiver)
    return ReceiverWindowArm(
        hass,
        found,
        _name(hass, found.device_id, receiver),
        on_failure=on_failure,
        on_window_closed=on_window_closed,
        reopen_after_code=reopen_after_code,
    )
