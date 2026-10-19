"""Capture devices: receivers that hear only while a capture window is open.

``receiver_window.py`` knows no integration by name. A receiver is a
capture device because its state carries a boolean ``capturing``, and
for no other reason. These tests run against fake receivers in both
shapes BroadSniff has shipped:

- 0.1.0: ``capturing`` and ``window_ends_at`` only. Its one IR switch on
  the device is suggested; an RF-capable model has two switches, so
  nothing is suggested and the user chooses.
- 0.2.0: also declares ``capture_switch`` and ``capture_mode``.

Entity IDs are deliberately odd (a user rename), because HAIR must work
from the registry and the receiver's own attributes, never from names.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair import receiver_window as rw
from custom_components.hair.const import DOMAIN
from custom_components.hair.receiver_window import (
    ARM_FAILED_CODE,
    CaptureDeviceError,
    CaptureReceiverStore,
    ReceiverArmError,
    capture_receivers,
    resolve,
)

# The living-room Broadlink, renamed by the user.
RX = "infrared.wohnzimmer_empfaenger"
RX_ENTRY = "reg-0001"
DEVICE = "dev-living"
IR_SWITCH = "switch.the_listen_thing"
RF_SWITCH = "switch.living_rf"

# A second Broadlink, an RM mini without RF.
OFFICE_RX = "infrared.office_rm_mini_ir_receiver"
OFFICE_ENTRY = "reg-0002"
OFFICE_DEVICE = "dev-office"
OFFICE_SWITCH = "switch.office_rm_mini_ir_capture"

# An always-listening ESPHome receiver, with a switch on its device.
ATHOM_RX = "infrared.athom_rx"
ATHOM_ENTRY = "reg-0003"
ATHOM_DEVICE = "dev-athom"
ATHOM_SWITCH = "switch.athom_status_led"

HELPER = "input_boolean.learn_mode"
ELSEWHERE = "switch.garage_door"

PRONTO = "0000 006D 0002 0000 0020 0040 0020 0040"


def _entry(entity_id, entry_id, device_id, *, disabled_by=None, name=None):
    return SimpleNamespace(
        id=entry_id, entity_id=entity_id, device_id=device_id,
        disabled_by=disabled_by, name=name, original_name=None,
    )


class _Registry:
    """The entity registry: looks up by entity id or by entry id, as HA's does."""

    def __init__(self, entries):
        self.entries = list(entries)

    def async_get(self, key):
        for entry in self.entries:
            if key in (entry.entity_id, entry.id):
                return entry
        return None

    def rename(self, old, new):
        entry = self.async_get(old)
        entry.entity_id = new

    def remove(self, entity_id):
        self.entries = [e for e in self.entries if e.entity_id != entity_id]


def _entries(*, rf=True):
    entries = [
        _entry(RX, RX_ENTRY, DEVICE),
        _entry(IR_SWITCH, "reg-0011", DEVICE),
        _entry(OFFICE_RX, OFFICE_ENTRY, OFFICE_DEVICE),
        _entry(OFFICE_SWITCH, "reg-0021", OFFICE_DEVICE),
        _entry(ATHOM_RX, ATHOM_ENTRY, ATHOM_DEVICE),
        _entry(ATHOM_SWITCH, "reg-0031", ATHOM_DEVICE),
        _entry(ELSEWHERE, "reg-0041", "dev-garage"),
        _entry(HELPER, "reg-0051", None),
        _entry("light.living_led", "reg-0012", DEVICE),
    ]
    if rf:
        entries.append(_entry(RF_SWITCH, "reg-0013", DEVICE))
    return entries


@contextlib.contextmanager
def _registry(registry):
    def for_device(reg, device_id, **_kw):
        return [e for e in reg.entries if e.device_id == device_id]

    devices = {
        DEVICE: SimpleNamespace(name="Living Room RM4", name_by_user=None),
        OFFICE_DEVICE: SimpleNamespace(name="RM mini", name_by_user="Office RM mini"),
        ATHOM_DEVICE: SimpleNamespace(name="Athom IR Proxy", name_by_user=None),
    }
    device_registry = SimpleNamespace(async_get=devices.get)
    with (
        patch.object(rw.er, "async_get", return_value=registry),
        patch.object(rw.er, "async_entries_for_device", side_effect=for_device),
        patch.object(rw.dr, "async_get", return_value=device_registry),
    ):
        yield registry


class _MemStore:
    """``homeassistant.helpers.storage.Store``, in memory."""

    loaded: ClassVar[dict | None] = None
    saved: ClassVar[list] = []

    def __init__(self, _hass, _version, _key):
        pass

    async def async_load(self):
        return _MemStore.loaded

    def async_delay_save(self, func, _delay):
        _MemStore.saved.append(func())


@pytest.fixture(autouse=True)
def _fresh():
    rw._refusals_logged.clear()
    _MemStore.loaded = None
    _MemStore.saved = []
    with patch.object(rw, "Store", _MemStore):
        yield


def _state(state="on", **attributes):
    return SimpleNamespace(state=state, attributes=dict(attributes))


def v010(capturing=False):
    """BroadSniff 0.1.0's receiver: ``capturing`` and the deadline only."""
    return _state(capturing=capturing, window_ends_at=None)


def v020(capturing=False, mode="sliding", switch=IR_SWITCH):
    """BroadSniff 0.2.0's receiver: it also names its switch and its mode."""
    return _state(
        capturing=capturing, window_ends_at=None,
        capture_switch=switch, capture_mode=mode,
    )


class _Hass:
    """States, switch services that open and close the receiver's window,
    HA's state tracker, timers that fire on request, and real tasks."""

    def __init__(self, states=None, *, opens=None, fail_on=()):
        self.data: dict = {}
        self._states = {
            IR_SWITCH: _state("off"),
            RF_SWITCH: _state("off"),
            OFFICE_SWITCH: _state("off"),
            ATHOM_SWITCH: _state("off"),
            HELPER: _state("off"),
            ATHOM_RX: _state("on"),
        }
        self._states.update(states or {})
        self.states = SimpleNamespace(get=self._states.get)
        # Which receiver's window each switch opens, as the integration
        # behind it would.
        self.opens = opens if opens is not None else {
            IR_SWITCH: RX, HELPER: RX, OFFICE_SWITCH: OFFICE_RX,
        }
        self.calls: list[tuple[str, str, str]] = []
        self._fail_on = set(fail_on)
        self.listeners: dict[str, list] = {}
        self.timers: list = []

        async def async_call(domain, service, data, blocking=False):
            entity_id = data["entity_id"]
            self.calls.append((domain, service, entity_id))
            if len(self.calls) in self._fail_on:
                raise RuntimeError("device did not answer")
            on = service == "turn_on"
            self._states[entity_id] = _state("on" if on else "off")
            receiver = self.opens.get(entity_id)
            if receiver is not None:
                self.set_capturing(receiver, on)

        self.services = SimpleNamespace(async_call=async_call)
        self.bus = SimpleNamespace(async_fire=MagicMock())

        def call_later(_delay, callback):
            timer = SimpleNamespace(callback=callback, cancelled=False)
            timer.cancel = lambda: setattr(timer, "cancelled", True)
            self.timers.append(timer)
            return timer

        self.loop = SimpleNamespace(call_later=call_later)

    def async_create_task(self, coro):
        return asyncio.get_running_loop().create_task(coro)

    async def async_add_executor_job(self, func, *args):
        return func(*args)

    def set(self, entity_id, state):
        self._states[entity_id] = state

    def drop(self, entity_id):
        self._states.pop(entity_id, None)

    def set_capturing(self, receiver, on):
        """The receiver's window opening or closing, and HA saying so."""
        old = self._states.get(receiver)
        if old is None:
            return
        new = _state(old.state, **{**old.attributes, "capturing": on})
        self._states[receiver] = new
        event = SimpleNamespace(data={"old_state": old, "new_state": new})
        for action in list(self.listeners.get(receiver, [])):
            action(event)

    def fire_timeout(self):
        live = [t for t in self.timers if not t.cancelled]
        assert live, "no timer armed"
        live[-1].callback()


@contextlib.contextmanager
def _infrared(hass, receivers=(RX, OFFICE_RX, ATHOM_RX)):
    """The infrared platform's receiver list, and HA's state tracker."""

    def track(_hass, entity_ids, action):
        for entity_id in entity_ids:
            hass.listeners.setdefault(entity_id, []).append(action)

        def unsub():
            for entity_id in entity_ids:
                hass.listeners[entity_id].remove(action)

        return unsub

    infrared = MagicMock()
    infrared.async_get_receivers = lambda _hass: list(receivers)
    with (
        patch.dict("sys.modules", {"homeassistant.components.infrared": infrared}),
        patch("homeassistant.helpers.event.async_track_state_change_event", track),
    ):
        yield


async def _loaded_store(hass, records=None):
    _MemStore.loaded = {"receivers": records} if records is not None else None
    store = CaptureReceiverStore(hass)
    await store.async_load()
    hass.data.setdefault(DOMAIN, {})["entry-1"] = {"capture_receivers": store}
    return store


async def _settle():
    for _ in range(10):
        await asyncio.sleep(0)


@pytest.fixture
def clock():
    """``receiver_window``'s monotonic clock, moved by hand."""
    now = SimpleNamespace(t=1000.0)
    with patch.object(rw, "monotonic", lambda: now.t):
        yield now


# ---------------------------------------------------------------------------
# What makes a capture device
# ---------------------------------------------------------------------------


class TestWhatMakesACaptureDevice:

    @pytest.mark.asyncio
    async def test_capturing_is_the_only_test(self):
        """A switch on an always-listening receiver's device changes nothing."""
        hass = _Hass()
        store = await _loaded_store(hass)
        with _registry(_Registry(_entries())), _infrared(hass):
            assert resolve(hass, ATHOM_RX, store) is None
            assert capture_receivers(hass, store) == []

    @pytest.mark.asyncio
    async def test_a_capturing_that_is_not_a_boolean_does_not_count(self):
        hass = _Hass({RX: _state(capturing="yes")})
        store = await _loaded_store(hass)
        with _registry(_Registry(_entries())):
            assert resolve(hass, RX, store) is None

    @pytest.mark.asyncio
    async def test_broadsniff_010_its_one_switch_is_suggested(self):
        hass = _Hass({OFFICE_RX: v010()})
        store = await _loaded_store(hass)
        with _registry(_Registry(_entries())):
            found = resolve(hass, OFFICE_RX, store)
        assert found.switch == OFFICE_SWITCH
        assert found.source == rw.SOURCE_DEVICE

    @pytest.mark.asyncio
    async def test_broadsniff_010_with_rf_has_two_switches_so_no_suggestion(self):
        hass = _Hass({RX: v010()})
        store = await _loaded_store(hass)
        with _registry(_Registry(_entries(rf=True))), _infrared(hass):
            found = resolve(hass, RX, store)
            rows = capture_receivers(hass, store)
        assert found.switch is None and found.source is None
        assert found.switches == (RF_SWITCH, IR_SWITCH)  # sorted by entity id
        living = next(r for r in rows if r["receiver_entity_id"] == RX)
        assert living["switch_entity_id"] is None
        assert [s["entity_id"] for s in living["device_switches"]] == [
            RF_SWITCH, IR_SWITCH,
        ]

    @pytest.mark.asyncio
    async def test_broadsniff_020_declares_its_switch(self):
        """Declared beats the device's switches, even when there are two."""
        hass = _Hass({RX: v020()})
        store = await _loaded_store(hass)
        with _registry(_Registry(_entries(rf=True))):
            found = resolve(hass, RX, store)
        assert found.switch == IR_SWITCH
        assert found.source == rw.SOURCE_DECLARED

    @pytest.mark.asyncio
    async def test_a_declaration_beats_a_stored_choice_which_is_kept(self):
        """Owner ruling 2026-10-20: a declared switch is final. The RF
        switch chosen for the IR receiver before 0.2.0 is not used, and
        stays in the store."""
        hass = _Hass({RX: v020()})
        store = await _loaded_store(hass, {RX_ENTRY: {"capture": True, "switch": RF_SWITCH}})
        with _registry(_Registry(_entries())):
            found = resolve(hass, RX, store)
        assert (found.switch, found.source) == (IR_SWITCH, rw.SOURCE_DECLARED)
        assert store.choice(RX_ENTRY) == RF_SWITCH

    @pytest.mark.asyncio
    async def test_the_choice_applies_again_once_the_declaration_is_gone(self):
        hass = _Hass({RX: v020()})
        store = await _loaded_store(hass, {RX_ENTRY: {"capture": True, "switch": RF_SWITCH}})
        with _registry(_Registry(_entries())):
            assert resolve(hass, RX, store).source == rw.SOURCE_DECLARED
            hass.set(RX, v010())  # the integration stops declaring
            found = resolve(hass, RX, store)
        assert (found.switch, found.source) == (RF_SWITCH, rw.SOURCE_USER)

    @pytest.mark.asyncio
    async def test_the_order_is_declared_then_user_then_device(self):
        registry = _Registry(_entries(rf=False))
        hass = _Hass({RX: v010()})
        store = await _loaded_store(hass)
        with _registry(registry):
            assert resolve(hass, RX, store).source == rw.SOURCE_DEVICE
            store.set_choice(RX_ENTRY, HELPER)
            assert (resolve(hass, RX, store).switch, resolve(hass, RX, store).source) == (
                HELPER, rw.SOURCE_USER,
            )
            hass.set(RX, v020(switch=IR_SWITCH))
            found = resolve(hass, RX, store)
        assert (found.switch, found.source) == (IR_SWITCH, rw.SOURCE_DECLARED)

    @pytest.mark.asyncio
    async def test_a_disabled_switch_is_not_counted(self):
        entries = _entries(rf=True)
        next(e for e in entries if e.entity_id == RF_SWITCH).disabled_by = "user"
        hass = _Hass({RX: v010()})
        store = await _loaded_store(hass)
        with _registry(_Registry(entries)):
            found = resolve(hass, RX, store)
        assert (found.switch, found.source) == (IR_SWITCH, rw.SOURCE_DEVICE)


# ---------------------------------------------------------------------------
# The safety rule
# ---------------------------------------------------------------------------


class TestTheSafetyRule:

    @pytest.mark.asyncio
    async def test_a_declared_switch_on_another_device_is_ignored(self, caplog):
        hass = _Hass({OFFICE_RX: v020(switch=ELSEWHERE)})
        store = await _loaded_store(hass)
        with _registry(_Registry(_entries())), caplog.at_level(
            logging.DEBUG, logger=rw.__name__
        ):
            first = resolve(hass, OFFICE_RX, store)
            second = resolve(hass, OFFICE_RX, store)
        # Falls through to the device's own one switch, never the garage.
        assert first.switch == second.switch == OFFICE_SWITCH
        assert first.source == rw.SOURCE_DEVICE
        refusals = [r for r in caplog.records if ELSEWHERE in r.getMessage()]
        assert len(refusals) == 1, "logged once, not on every read"
        assert refusals[0].levelno == logging.DEBUG

    @pytest.mark.asyncio
    async def test_a_declaration_that_fails_the_rule_lets_the_choice_apply(self):
        """A refused declaration counts as none: the user's choice wins,
        and the door takes a new one (the card's menu comes back)."""
        hass = _Hass({OFFICE_RX: v020(switch=ELSEWHERE)})
        store = await _loaded_store(hass, {OFFICE_ENTRY: {"capture": True, "switch": HELPER}})
        with _registry(_Registry(_entries())):
            found = resolve(hass, OFFICE_RX, store)
            assert (found.switch, found.source) == (HELPER, rw.SOURCE_USER)
            rw.set_choice(hass, OFFICE_RX, OFFICE_SWITCH)
            found = resolve(hass, OFFICE_RX, store)
        assert (found.switch, found.source) == (OFFICE_SWITCH, rw.SOURCE_USER)

    @pytest.mark.asyncio
    async def test_a_declared_entity_that_is_not_a_switch_is_ignored(self):
        hass = _Hass({RX: v020(switch="light.living_led")})  # on the same device
        store = await _loaded_store(hass)
        with _registry(_Registry(_entries(rf=True))):
            found = resolve(hass, RX, store)
        assert found.switch is None

    @pytest.mark.asyncio
    async def test_a_declared_input_boolean_is_ignored(self):
        """Only a hand-made choice may be an input_boolean."""
        hass = _Hass({RX: v020(switch=HELPER)})
        store = await _loaded_store(hass)
        with _registry(_Registry(_entries(rf=True))):
            assert resolve(hass, RX, store).switch is None

    @pytest.mark.asyncio
    async def test_a_choice_may_be_an_input_boolean_from_anywhere(self):
        hass = _Hass({RX: v010()})
        await _loaded_store(hass)
        with _registry(_Registry(_entries())):
            rw.set_choice(hass, RX, HELPER)
            assert resolve(hass, RX).switch == HELPER

    @pytest.mark.asyncio
    async def test_a_choice_must_be_a_switch_or_an_input_boolean(self):
        hass = _Hass({RX: v010()})
        await _loaded_store(hass)
        with _registry(_Registry(_entries())), pytest.raises(CaptureDeviceError) as err:
            rw.set_choice(hass, RX, "light.living_led")
        assert err.value.code == "invalid_capture_switch"

    @pytest.mark.asyncio
    async def test_no_choice_is_kept_for_a_receiver_that_is_not_a_capture_device(self):
        hass = _Hass()
        await _loaded_store(hass)
        with _registry(_Registry(_entries())), pytest.raises(CaptureDeviceError) as err:
            rw.set_choice(hass, ATHOM_RX, ATHOM_SWITCH)
        assert err.value.code == rw.NOT_CAPTURE_DEVICE_CODE

    def test_the_contract_and_the_module_say_the_declaration_is_final(self):
        """Owner ruling 2026-10-20, in the published contract and the module."""
        doc = (Path(rw.__file__).parents[2] / "docs" / "windowed-receivers.md").read_text()
        section = doc.split("## Which entity HAIR toggles", 1)[1].split("\n## ", 1)[0]
        first, second = "1. **Your declaration**", "2. **The user's choice.**"
        assert section.index(first) < section.index(second)
        assert "It cannot be overridden" in section
        assert "does not guess between" in section
        module = rw.__doc__ or ""
        assert module.index("1. ``declared``") < module.index("2. ``user``")
        assert "It is final" in module

    def test_every_door_takes_a_receiver_never_a_switch(self):
        source = (Path(rw.__file__).parent / "websocket_api.py").read_text()
        for door in ("receivers/listen", "receivers/capture_switch"):
            block = source.split(f'f"{{WS_PREFIX}}/{door}"', 1)[1].split("})", 1)[0]
            assert 'vol.Required("receiver_entity_id")' in block
        listen = source.split('f"{WS_PREFIX}/receivers/listen"', 1)[1].split("})", 1)[0]
        assert '"entity_id"' not in listen.replace("receiver_entity_id", "")


# ---------------------------------------------------------------------------
# Unavailable receivers, and the store
# ---------------------------------------------------------------------------


class TestUnavailableReceivers:

    @pytest.mark.asyncio
    async def test_a_remembered_capture_device_stays_one_while_unavailable(self):
        """HA writes no attributes while unavailable, so ``capturing`` is
        missing then. The card stays RX-CAPTURE, its chip disabled."""
        hass = _Hass({OFFICE_RX: v010()})
        store = await _loaded_store(hass)
        with _registry(_Registry(_entries())), _infrared(hass):
            assert resolve(hass, OFFICE_RX, store) is not None  # seen once
            hass.set(OFFICE_RX, _state("unavailable"))
            found = resolve(hass, OFFICE_RX, store)
            rows = capture_receivers(hass, store)
            with pytest.raises(CaptureDeviceError) as err:
                rw.require(hass, OFFICE_RX)
        assert found is not None and found.available is False
        assert found.switch == OFFICE_SWITCH
        office = next(r for r in rows if r["receiver_entity_id"] == OFFICE_RX)
        assert office["available"] is False
        assert err.value.code == rw.RECEIVER_UNAVAILABLE_CODE

    @pytest.mark.asyncio
    async def test_an_available_receiver_without_capturing_is_rx_native(self):
        """And that clears the memory, so a later outage does not bring it back."""
        hass = _Hass({OFFICE_RX: v010()})
        store = await _loaded_store(hass)
        with _registry(_Registry(_entries())):
            resolve(hass, OFFICE_RX, store)
            hass.set(OFFICE_RX, _state("on"))  # its integration stopped declaring
            assert resolve(hass, OFFICE_RX, store) is None
            hass.set(OFFICE_RX, _state("unavailable"))
            assert resolve(hass, OFFICE_RX, store) is None
        assert store.remembered(OFFICE_ENTRY) is False

    @pytest.mark.asyncio
    async def test_a_declared_switch_holds_while_the_receiver_is_unavailable(self):
        """Owner, 2026-10-20: an RM4 Pro that goes offline must not offer
        its RF switch. The declaration is remembered and the door still
        refuses."""
        from custom_components.hair.websocket_api import ws_set_capture_switch

        hass = _Hass({RX: v020()})
        store = await _loaded_store(hass)
        conn = _conn()
        with _registry(_Registry(_entries(rf=True))), _infrared(hass):
            assert resolve(hass, RX, store).source == rw.SOURCE_DECLARED
            hass.set(RX, _state("unavailable"))
            found = resolve(hass, RX, store)
            rows = capture_receivers(hass, store)
            ws_set_capture_switch(hass, conn, {
                "id": 1, "receiver_entity_id": RX, "entity_id": RF_SWITCH,
            })
        assert (found.available, found.switch, found.source) == (
            False, IR_SWITCH, rw.SOURCE_DECLARED,
        )
        living = next(r for r in rows if r["receiver_entity_id"] == RX)
        assert (living["switch_entity_id"], living["source"]) == (IR_SWITCH, "declared")
        assert conn.send_error.call_args.args[1] == rw.CAPTURE_SWITCH_DECLARED_CODE
        assert store.choice(RX_ENTRY) is None

    @pytest.mark.asyncio
    async def test_the_remembered_declaration_clears_when_it_stops(self):
        hass = _Hass({RX: v020()})
        store = await _loaded_store(hass)
        with _registry(_Registry(_entries(rf=True))):
            resolve(hass, RX, store)
            assert store.declared(RX_ENTRY) == IR_SWITCH
            hass.set(RX, v010())  # available, and no longer declaring
            assert resolve(hass, RX, store).source is None
            hass.set(RX, _state("unavailable"))
            found = resolve(hass, RX, store)
        assert store.declared(RX_ENTRY) is None
        assert (found.switch, found.source) == (None, None)

    @pytest.mark.asyncio
    async def test_a_refused_declaration_is_not_remembered(self):
        hass = _Hass({OFFICE_RX: v020(switch=ELSEWHERE)})
        store = await _loaded_store(hass)
        with _registry(_Registry(_entries())):
            resolve(hass, OFFICE_RX, store)
            hass.set(OFFICE_RX, _state("unavailable"))
            found = resolve(hass, OFFICE_RX, store)
        assert store.declared(OFFICE_ENTRY) is None
        assert found.source == rw.SOURCE_DEVICE

    @pytest.mark.asyncio
    async def test_the_remembered_declaration_survives_a_restart(self):
        hass = _Hass({RX: _state("unavailable")})
        store = await _loaded_store(hass, {
            RX_ENTRY: {"capture": True, "switch": RF_SWITCH, "declared": IR_SWITCH},
        })
        with _registry(_Registry(_entries(rf=True))):
            found = resolve(hass, RX, store)
        assert (found.switch, found.source) == (IR_SWITCH, rw.SOURCE_DECLARED)
        assert store.choice(RX_ENTRY) == RF_SWITCH

    @pytest.mark.asyncio
    async def test_an_unavailable_receiver_never_seen_declaring_is_not_one(self):
        hass = _Hass({OFFICE_RX: _state("unavailable")})
        store = await _loaded_store(hass)
        with _registry(_Registry(_entries())):
            assert resolve(hass, OFFICE_RX, store) is None

    @pytest.mark.asyncio
    async def test_a_remembered_receiver_whose_integration_has_not_loaded_keeps_its_card(self):
        """No state at all and not on the infrared platform yet: the row
        still comes from the store, by registry entry."""
        hass = _Hass()
        store = await _loaded_store(hass, {OFFICE_ENTRY: {"capture": True, "switch": None}})
        with _registry(_Registry(_entries())), _infrared(hass, receivers=(ATHOM_RX,)):
            rows = capture_receivers(hass, store)
        assert [r["receiver_entity_id"] for r in rows] == [OFFICE_RX]
        assert rows[0]["available"] is False
        assert rows[0]["name"] == "Office RM mini"


class TestTheStore:

    @pytest.mark.asyncio
    async def test_a_choice_survives_a_receiver_with_no_state_at_load(self):
        """HAIR can load before the receiver's integration does. The
        choice must survive that, because gone means gone from the
        registry, never missing from the state machine."""
        hass = _Hass()  # no state for RX at all
        store = await _loaded_store(hass, {RX_ENTRY: {"capture": True, "switch": RF_SWITCH}})
        assert store.choice(RX_ENTRY) == RF_SWITCH
        assert _MemStore.saved == [], "nothing dropped, nothing rewritten"

    @pytest.mark.asyncio
    async def test_a_record_is_dropped_only_when_its_registry_entry_is_gone(self):
        registry = _Registry(_entries())
        registry.remove(OFFICE_RX)
        hass = _Hass()
        with _registry(registry):
            store = await _loaded_store(hass, {
                RX_ENTRY: {"capture": True, "switch": RF_SWITCH},
                OFFICE_ENTRY: {"capture": True, "switch": OFFICE_SWITCH},
                "garbage": "not a record",
            })
        assert store.entry_ids() == [RX_ENTRY]
        assert _MemStore.saved[-1] == {
            "receivers": {RX_ENTRY: {"capture": True, "switch": RF_SWITCH}},
        }

    @pytest.mark.asyncio
    async def test_a_stored_choice_survives_a_receiver_rename(self):
        registry = _Registry(_entries())
        hass = _Hass({RX: v010()})
        await _loaded_store(hass)
        with _registry(registry):
            rw.set_choice(hass, RX, RF_SWITCH)
            renamed = "infrared.salon_receiver"
            registry.rename(RX, renamed)
            hass.set(renamed, v010())
            hass.drop(RX)
            found = resolve(hass, renamed)
        assert (found.switch, found.source) == (RF_SWITCH, rw.SOURCE_USER)

    @pytest.mark.asyncio
    async def test_a_choice_is_saved(self):
        hass = _Hass({RX: v010()})
        await _loaded_store(hass)
        with _registry(_Registry(_entries())):
            rw.set_choice(hass, RX, IR_SWITCH)
        assert _MemStore.saved[-1]["receivers"][RX_ENTRY] == {
            "capture": True, "switch": IR_SWITCH,
        }

    @pytest.mark.asyncio
    async def test_a_receiver_with_no_registry_entry_keeps_no_choice(self):
        hass = _Hass({"infrared.yaml_rx": v010()})
        await _loaded_store(hass)
        with _registry(_Registry(_entries())), pytest.raises(CaptureDeviceError) as err:
            rw.set_choice(hass, "infrared.yaml_rx", IR_SWITCH)
        assert err.value.code == "not_registered"


# ---------------------------------------------------------------------------
# The receivers doors
# ---------------------------------------------------------------------------


def _conn():
    conn = MagicMock()
    conn.subscriptions = {}
    return conn


class TestTheReceiversDoors:

    @pytest.mark.asyncio
    async def test_the_capture_door_lists_each_capture_device(self):
        from custom_components.hair.websocket_api import ws_capture_receivers

        hass = _Hass({RX: v020(), OFFICE_RX: v010()})
        await _loaded_store(hass)
        conn = _conn()
        with _registry(_Registry(_entries())), _infrared(hass):
            ws_capture_receivers(hass, conn, {"id": 1})
        rows = conn.send_result.call_args.args[1]
        assert [(r["name"], r["switch_entity_id"], r["source"]) for r in rows] == [
            ("Living Room RM4", IR_SWITCH, "declared"),
            ("Office RM mini", OFFICE_SWITCH, "device"),
        ]
        assert set(rows[0]) == {
            "receiver_entity_id", "name", "ha_device_id", "available",
            "switch_entity_id", "source", "device_switches",
        }

    @pytest.mark.asyncio
    async def test_listen_toggles_the_resolved_switch(self):
        from custom_components.hair.websocket_api import ws_receiver_listen

        hass = _Hass({OFFICE_RX: v010()})
        await _loaded_store(hass)
        conn = _conn()
        with _registry(_Registry(_entries())):
            await ws_receiver_listen(hass, conn, {
                "id": 2, "receiver_entity_id": OFFICE_RX, "on": True,
            })
            await ws_receiver_listen(hass, conn, {
                "id": 3, "receiver_entity_id": OFFICE_RX, "on": False,
            })
        assert hass.calls == [
            ("switch", "turn_on", OFFICE_SWITCH),
            ("switch", "turn_off", OFFICE_SWITCH),
        ]
        conn.send_error.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("receiver", "state", "code"), [
        (ATHOM_RX, _state("on"), rw.NOT_CAPTURE_DEVICE_CODE),
        (RX, v010(), rw.NO_CAPTURE_SWITCH_CODE),  # two switches, none chosen
    ])
    async def test_listen_refuses_what_it_cannot_open(self, receiver, state, code):
        from custom_components.hair.websocket_api import ws_receiver_listen

        hass = _Hass({receiver: state})
        await _loaded_store(hass)
        conn = _conn()
        with _registry(_Registry(_entries(rf=True))):
            await ws_receiver_listen(hass, conn, {
                "id": 4, "receiver_entity_id": receiver, "on": True,
            })
        assert conn.send_error.call_args.args[1] == code
        assert hass.calls == []

    @pytest.mark.asyncio
    async def test_a_window_that_will_not_open_names_the_device(self):
        from custom_components.hair.websocket_api import ws_receiver_listen

        hass = _Hass({OFFICE_RX: v010()}, fail_on={1})
        await _loaded_store(hass)
        conn = _conn()
        with _registry(_Registry(_entries())):
            await ws_receiver_listen(hass, conn, {
                "id": 5, "receiver_entity_id": OFFICE_RX, "on": True,
            })
        _id, code, message = conn.send_error.call_args.args
        assert code == ARM_FAILED_CODE == "receiver_arm_failed"
        assert message == "Office RM mini could not start listening"

    @pytest.mark.asyncio
    async def test_the_switch_door_keeps_a_choice(self):
        from custom_components.hair.websocket_api import (
            ws_capture_receivers,
            ws_set_capture_switch,
        )

        hass = _Hass({RX: v010()})
        await _loaded_store(hass)
        conn = _conn()
        with _registry(_Registry(_entries())), _infrared(hass):
            ws_set_capture_switch(hass, conn, {
                "id": 6, "receiver_entity_id": RX, "entity_id": RF_SWITCH,
            })
            ws_capture_receivers(hass, conn, {"id": 7})
        living = conn.send_result.call_args.args[1][0]
        assert (living["switch_entity_id"], living["source"]) == (RF_SWITCH, "user")

    @pytest.mark.asyncio
    async def test_the_switch_door_refuses_a_receiver_that_declares_its_switch(self):
        from custom_components.hair.websocket_api import ws_set_capture_switch

        hass = _Hass({RX: v020()})
        store = await _loaded_store(hass)
        conn = _conn()
        with _registry(_Registry(_entries())):
            ws_set_capture_switch(hass, conn, {
                "id": 9, "receiver_entity_id": RX, "entity_id": RF_SWITCH,
            })
            found = resolve(hass, RX, store)
        _id, code, _message = conn.send_error.call_args.args
        assert code == rw.CAPTURE_SWITCH_DECLARED_CODE == "capture_switch_declared"
        conn.send_result.assert_not_called()
        assert store.choice(RX_ENTRY) is None
        assert (found.switch, found.source) == (IR_SWITCH, rw.SOURCE_DECLARED)

    @pytest.mark.asyncio
    async def test_the_switch_door_refuses_anything_but_a_switch_or_helper(self):
        from custom_components.hair.websocket_api import ws_set_capture_switch

        hass = _Hass({RX: v010()})
        await _loaded_store(hass)
        conn = _conn()
        with _registry(_Registry(_entries())):
            ws_set_capture_switch(hass, conn, {
                "id": 8, "receiver_entity_id": RX, "entity_id": "lock.front_door",
            })
        assert conn.send_error.call_args.args[1] == "invalid_capture_switch"


# ---------------------------------------------------------------------------
# The listen doors, aimed at one receiver
# ---------------------------------------------------------------------------


class _Monitor:
    def __init__(self):
        self.subscribers: list = []

    def subscribe(self, cb):
        self.subscribers.append(cb)

    def unsubscribe(self, cb):
        if cb in self.subscribers:
            self.subscribers.remove(cb)

    def press(self, receiver):
        for cb in list(self.subscribers):
            cb({
                "device_id": "u1", "device_fingerprint": "fp-1",
                "signal_id": "s1", "protocol": "PRONTO", "code": PRONTO,
                "receiver_entity_id": receiver,
            })


def _signal_store():
    signal = MagicMock()
    signal.code = PRONTO
    signal.protocol = "PRONTO"
    signal.decoded_fingerprint = None
    signal.decoded_protocol = None
    signal.heard_by = [RX]
    device = MagicMock()
    device.get_signal_by_id = MagicMock(return_value=signal)
    store = MagicMock()
    store.get_device = MagicMock(return_value=device)
    return store


async def _wired(states, **kw):
    hass = _Hass(states, **kw)
    store = await _loaded_store(hass)
    monitor = _Monitor()
    hass.data[DOMAIN]["entry-1"].update({
        "device_manager": MagicMock(),
        "signal_monitor": monitor,
        "signal_store": _signal_store(),
    })
    return hass, store, monitor


def _events(conn):
    return [c.args[1]["type"] for c in conn.send_event.call_args_list]


async def _command_listen(hass, conn, receiver=None, msg_id=9):
    from custom_components.hair.websocket_api import ws_command_listen

    msg = {"id": msg_id, "type": "hair/command/listen"}
    if receiver is not None:
        msg["receiver_entity_id"] = receiver
    await ws_command_listen(hass, conn, msg)
    await _settle()


class TestTheCommandEditorsListen:

    @pytest.mark.asyncio
    async def test_it_opens_the_window_before_answering_and_closes_it_on_a_code(self):
        hass, _store, monitor = await _wired({OFFICE_RX: v010()})
        conn = _conn()
        opened_before_answer = []
        conn.send_result.side_effect = lambda *_a: opened_before_answer.append(
            list(hass.calls)
        )
        with _registry(_Registry(_entries())), _infrared(hass):
            await _command_listen(hass, conn, OFFICE_RX)
            assert opened_before_answer == [[("switch", "turn_on", OFFICE_SWITCH)]]
            monitor.press(OFFICE_RX)
            await _settle()
        assert _events(conn) == ["command_capture"]
        assert hass.calls[-1] == ("switch", "turn_off", OFFICE_SWITCH)
        assert hass.listeners[OFFICE_RX] == []

    @pytest.mark.asyncio
    async def test_it_forwards_only_its_own_receivers_presses(self):
        hass, _store, monitor = await _wired({OFFICE_RX: v010()})
        conn = _conn()
        with _registry(_Registry(_entries())), _infrared(hass):
            await _command_listen(hass, conn, OFFICE_RX)
            monitor.press(ATHOM_RX)
            monitor.press(None)  # the legacy ESPHome bridge
            await _settle()
            assert _events(conn) == []
            monitor.press(OFFICE_RX)
            await _settle()
        assert _events(conn) == ["command_capture"]

    @pytest.mark.asyncio
    async def test_a_timeout_closes_the_window(self):
        hass, _store, _monitor = await _wired({OFFICE_RX: v010()})
        conn = _conn()
        with _registry(_Registry(_entries())), _infrared(hass):
            await _command_listen(hass, conn, OFFICE_RX)
            hass.fire_timeout()
            await _settle()
        assert _events(conn) == ["command_listen_timeout"]
        assert hass.calls[-1] == ("switch", "turn_off", OFFICE_SWITCH)

    @pytest.mark.asyncio
    async def test_closing_the_tab_closes_the_window(self):
        """The panel's unsubscribe and a dropped connection both run the
        subscription's teardown."""
        hass, _store, monitor = await _wired({OFFICE_RX: v010()})
        conn = _conn()
        with _registry(_Registry(_entries())), _infrared(hass):
            await _command_listen(hass, conn, OFFICE_RX)
            conn.subscriptions[9]()
            await _settle()
        assert hass.calls == [
            ("switch", "turn_on", OFFICE_SWITCH),
            ("switch", "turn_off", OFFICE_SWITCH),
        ]
        assert monitor.subscribers == []

    @pytest.mark.asyncio
    async def test_a_window_the_user_opened_is_left_open(self):
        hass, _store, monitor = await _wired({OFFICE_RX: v010(capturing=True)})
        conn = _conn()
        with _registry(_Registry(_entries())), _infrared(hass):
            await _command_listen(hass, conn, OFFICE_RX)
            monitor.press(OFFICE_RX)
            await _settle()
        assert _events(conn) == ["command_capture"]
        assert hass.calls == []

    @pytest.mark.asyncio
    async def test_a_window_closing_on_its_own_timer_is_reopened(self, clock):
        hass, _store, _monitor = await _wired({OFFICE_RX: v010()})
        conn = _conn()
        with _registry(_Registry(_entries())), _infrared(hass):
            await _command_listen(hass, conn, OFFICE_RX)
            clock.t += 30
            hass.set_capturing(OFFICE_RX, False)
            await _settle()
        assert hass.calls == [("switch", "turn_on", OFFICE_SWITCH)] * 2
        assert _events(conn) == []

    @pytest.mark.asyncio
    async def test_in_single_mode_the_window_is_the_whole_listen(self, clock):
        hass, _store, _monitor = await _wired({RX: v020(mode="single")})
        conn = _conn()
        with _registry(_Registry(_entries())), _infrared(hass):
            await _command_listen(hass, conn, RX)
            clock.t += 30
            hass.set_capturing(RX, False)
            await _settle()
        assert _events(conn) == ["command_listen_timeout"]
        assert hass.calls == [("switch", "turn_on", IR_SWITCH)]

    @pytest.mark.asyncio
    async def test_a_window_that_snaps_shut_ends_the_listen(self, clock):
        """Not a tight loop: once, and the listen says the device failed."""
        hass, _store, _monitor = await _wired({OFFICE_RX: v010()})
        conn = _conn()
        with _registry(_Registry(_entries())), _infrared(hass):
            await _command_listen(hass, conn, OFFICE_RX)
            clock.t += 0.1
            hass.set_capturing(OFFICE_RX, False)
            await _settle()
        payload = conn.send_event.call_args.args[1]
        assert payload["type"] == "receiver_arm_failed"
        assert payload["name"] == "Office RM mini"
        assert hass.calls == [("switch", "turn_on", OFFICE_SWITCH)]

    @pytest.mark.asyncio
    async def test_a_window_that_will_not_open_refuses_the_listen(self):
        hass, _store, monitor = await _wired({OFFICE_RX: v010()}, fail_on={1})
        conn = _conn()
        with _registry(_Registry(_entries())), _infrared(hass):
            await _command_listen(hass, conn, OFFICE_RX)
        assert conn.send_error.call_args.args[1] == "receiver_arm_failed"
        conn.send_result.assert_not_called()
        assert monitor.subscribers == [] and conn.subscriptions == {}

    @pytest.mark.asyncio
    async def test_a_capture_device_it_cannot_open_refuses_the_listen(self):
        hass, _store, monitor = await _wired({RX: v010()})  # two switches
        conn = _conn()
        with _registry(_Registry(_entries(rf=True))), _infrared(hass):
            await _command_listen(hass, conn, RX)
        assert conn.send_error.call_args.args[1] == "no_capture_switch"
        assert monitor.subscribers == []

    @pytest.mark.asyncio
    async def test_an_always_listening_receiver_is_only_filtered(self):
        hass, _store, monitor = await _wired({})
        conn = _conn()
        with _registry(_Registry(_entries())), _infrared(hass):
            await _command_listen(hass, conn, ATHOM_RX)
            monitor.press(OFFICE_RX)
            monitor.press(ATHOM_RX)
            await _settle()
        assert _events(conn) == ["command_capture"]
        assert hass.calls == []

    @pytest.mark.asyncio
    async def test_without_a_receiver_nothing_changes(self):
        hass, _store, monitor = await _wired({OFFICE_RX: v010()})
        conn = _conn()
        with _registry(_Registry(_entries())), _infrared(hass):
            await _command_listen(hass, conn)
            monitor.press(None)
            await _settle()
        assert conn.send_result.call_args.args[1] == {"listening": True}
        assert _events(conn) == ["command_capture"]
        assert hass.calls == []


class TestTheFixWindowsListen:
    """``hair/device/tangle/listen``: several presses on one arm."""

    @pytest.fixture
    def komeco(self):
        from .test_tangle_listen_fixes import KOMECO, parse_wig

        return parse_wig(KOMECO.read_text()).wig

    async def _arm(self, hass, komeco, receiver):
        from custom_components.hair.models import IRDevice
        from custom_components.hair.websocket_api import ws_tangle_listen

        device = IRDevice(name="Komeco", climate_matrix=True,
                          emitter_entity_ids=["infrared.blaster"])
        manager = MagicMock()
        manager.get_device = MagicMock(return_value=device)
        manager.async_get_matrix = AsyncMock(return_value=komeco.climate)
        hass.data[DOMAIN]["entry-1"]["device_manager"] = manager
        conn = _conn()
        await ws_tangle_listen(hass, conn, {
            "id": 11, "device_id": device.id, "receiver_entity_id": receiver,
        })
        await _settle()
        return conn

    @pytest.mark.asyncio
    async def test_it_filters_opens_and_closes_like_the_editor(self, komeco):
        hass, _store, monitor = await _wired({OFFICE_RX: v010()})
        with _registry(_Registry(_entries())), _infrared(hass):
            conn = await self._arm(hass, komeco, OFFICE_RX)
            monitor.press(ATHOM_RX)
            monitor.press(OFFICE_RX)
            monitor.press(OFFICE_RX)
            await _settle()
            assert _events(conn) == ["tangle_capture", "tangle_capture"]
            conn.subscriptions[11]()
            await _settle()
        assert hass.calls == [
            ("switch", "turn_on", OFFICE_SWITCH),
            ("switch", "turn_off", OFFICE_SWITCH),
        ]

    @pytest.mark.asyncio
    async def test_single_mode_reopens_after_a_code(self, komeco, clock):
        """The miss ladder needs a second and third press (owner, 2026-10-19)."""
        hass, _store, monitor = await _wired({RX: v020(mode="single")})
        with _registry(_Registry(_entries())), _infrared(hass):
            conn = await self._arm(hass, komeco, RX)
            monitor.press(RX)
            clock.t += 5
            hass.set_capturing(RX, False)  # the window closes with the code
            await _settle()
        assert hass.calls == [("switch", "turn_on", IR_SWITCH)] * 2
        assert _events(conn) == ["tangle_capture"]
        assert 11 in conn.subscriptions

    @pytest.mark.asyncio
    async def test_single_mode_closing_empty_ends_the_listen(self, komeco, clock):
        hass, _store, monitor = await _wired({RX: v020(mode="single")})
        with _registry(_Registry(_entries())), _infrared(hass):
            conn = await self._arm(hass, komeco, RX)
            monitor.press(RX)
            clock.t += 5
            hass.set_capturing(RX, False)
            await _settle()
            clock.t += 30
            hass.set_capturing(RX, False)  # reopened, then closed with nothing
            await _settle()
        assert _events(conn) == ["tangle_capture", "tangle_listen_timeout"]
        assert conn.subscriptions == {}
        assert monitor.subscribers == []

    @pytest.mark.asyncio
    async def test_without_a_receiver_nothing_changes(self, komeco):
        from custom_components.hair.models import IRDevice
        from custom_components.hair.websocket_api import ws_tangle_listen

        hass, _store, monitor = await _wired({OFFICE_RX: v010()})
        device = IRDevice(name="Komeco", climate_matrix=True,
                          emitter_entity_ids=["infrared.blaster"])
        manager = MagicMock()
        manager.get_device = MagicMock(return_value=device)
        manager.async_get_matrix = AsyncMock(return_value=komeco.climate)
        hass.data[DOMAIN]["entry-1"]["device_manager"] = manager
        conn = _conn()
        with _registry(_Registry(_entries())), _infrared(hass):
            await ws_tangle_listen(hass, conn, {"id": 12, "device_id": device.id})
            monitor.press(OFFICE_RX)
            monitor.press(None)
            await _settle()
        assert _events(conn) == ["tangle_capture", "tangle_capture"]
        assert hass.calls == []


def test_both_listen_doors_take_an_optional_receiver():
    source = (Path(rw.__file__).parent / "websocket_api.py").read_text()
    for door in ("command/listen", "device/tangle/listen"):
        block = source.split(f'f"{{WS_PREFIX}}/{door}"', 1)[1].split("})", 1)[0]
        assert 'vol.Optional("receiver_entity_id"): str' in block, door


def test_the_sniffers_feed_names_the_receiver():
    """The listen filter and the chips' bloom both read it."""
    source = (Path(rw.__file__).parent / "signal_monitor.py").read_text()
    step11 = source.split("# Step 11: Fire HA event.", 1)[1].split("async_fire", 1)[0]
    assert '"receiver_entity_id": receiver_entity_id,' in step11


def test_receiver_arm_error_wording():
    err = ReceiverArmError("Office RM mini")
    assert str(err) == "Office RM mini could not start listening"
    assert err.code == "receiver_arm_failed"
