"""N18: a trigger's receivers hear its own medium.

The owner's "Doorbell" trigger on VM998 was stored with the Athom's
infrared receiver while the doorbell arrives on the Athom's radio
receiver, so it never fired. The trigger create and update doors refuse
a receiver of the other medium (``receiver_wrong_medium``), and the
receivers door lists every radio receiver HAIR hears, always-on ones
included, so a radio trigger's picker has the right one to offer.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.const import DOMAIN, MEDIUM_IR, MEDIUM_RF
from custom_components.hair.models import IRTrigger
from custom_components.hair.storage import HAIRStore
from custom_components.hair.websocket_api import (
    RECEIVER_WRONG_MEDIUM,
    ws_create_trigger,
    ws_get_receivers,
    ws_update_trigger,
)

IR_RX = "infrared.athom_rx"
RF_RX = "radio_frequency.office_athom_ir_rf_433mhz_rf_receiver"
RADIO = {"protocol": "RF_RAW", "signal_fingerprint": "rf:doorbell"}
INFRARED = {"protocol": "NEC", "signal_fingerprint": "NEC:0x04:0x08"}


def _store(fake_hass) -> HAIRStore:
    store = HAIRStore(fake_hass)
    store._loaded = True
    store.async_save = AsyncMock()
    fake_hass.data[DOMAIN] = {
        "e1": {
            "store": store,
            "device_manager": MagicMock(),
            "config_entry": SimpleNamespace(entry_id="e1"),
        }
    }
    return store


async def _create(fake_hass, kind, receivers):
    conn = MagicMock()
    with patch("custom_components.hair.event.sync_trigger_entities"), patch(
        "custom_components.hair.event.sync_remote_entities"
    ), patch("custom_components.hair.pin_bindings.rederive_all_pinned"):
        await ws_create_trigger(fake_hass, conn, {
            "id": 1, "type": "hair/trigger/create", "name": "Doorbell",
            "min_hits": 1, "receiver_entity_ids": receivers, **kind,
        })
    return conn


def _error_code(conn) -> str | None:
    if not conn.send_error.called:
        return None
    return conn.send_error.call_args.args[1]


@pytest.mark.asyncio
class TestTheCreateDoor:
    async def test_a_radio_trigger_on_an_infrared_receiver_is_refused(self, fake_hass):
        store = _store(fake_hass)
        conn = await _create(fake_hass, RADIO, [IR_RX])
        assert _error_code(conn) == RECEIVER_WRONG_MEDIUM
        assert IR_RX in conn.send_error.call_args.args[2]
        assert store.get_all_triggers() == []
        store.async_save.assert_not_called()

    async def test_an_infrared_trigger_on_a_radio_receiver_is_refused(self, fake_hass):
        store = _store(fake_hass)
        conn = await _create(fake_hass, INFRARED, [IR_RX, RF_RX])
        assert _error_code(conn) == RECEIVER_WRONG_MEDIUM
        assert RF_RX in conn.send_error.call_args.args[2]
        assert IR_RX not in conn.send_error.call_args.args[2]
        assert store.get_all_triggers() == []

    @pytest.mark.parametrize(
        ("kind", "receivers", "medium"),
        [
            (RADIO, [RF_RX], MEDIUM_RF),
            (RADIO, [], MEDIUM_RF),
            (INFRARED, [IR_RX], MEDIUM_IR),
            (INFRARED, [], MEDIUM_IR),
            # A receiver whose domain names no medium is left alone.
            (RADIO, ["sensor.legacy_rx"], MEDIUM_RF),
        ],
    )
    async def test_its_own_medium_or_any_receiver_is_kept(
        self, fake_hass, kind, receivers, medium
    ):
        store = _store(fake_hass)
        conn = await _create(fake_hass, kind, receivers)
        assert _error_code(conn) is None
        [trigger] = store.get_all_triggers()
        assert trigger.medium == medium
        assert trigger.receiver_entity_ids == receivers


def _stored(store, protocol, receivers) -> IRTrigger:
    trigger = IRTrigger(
        name="Doorbell", signal_fingerprint="fp", protocol=protocol,
        receiver_entity_ids=list(receivers),
    )
    store.add_trigger(trigger)
    return trigger


async def _update(fake_hass, trigger_id, **fields):
    conn = MagicMock()
    with patch("custom_components.hair.event.sync_trigger_entities"), patch(
        "custom_components.hair.event.sync_remote_entities"
    ):
        await ws_update_trigger(fake_hass, conn, {
            "id": 2, "type": "hair/trigger/update", "trigger_id": trigger_id, **fields,
        })
    return conn


@pytest.mark.asyncio
class TestTheUpdateDoor:
    async def test_a_wrong_medium_receiver_is_refused_and_nothing_changes(self, fake_hass):
        store = _store(fake_hass)
        trigger = _stored(store, "RF_RAW", [])
        conn = await _update(
            fake_hass, trigger.id, name="Front door", min_hits=3,
            receiver_entity_ids=[IR_RX],
        )
        assert _error_code(conn) == RECEIVER_WRONG_MEDIUM
        assert trigger.name == "Doorbell"
        assert trigger.min_hits == 1
        assert trigger.receiver_entity_ids == []
        store.async_save.assert_not_called()

    async def test_the_owners_doorbell_is_repaired_by_saving_its_own_receiver(self, fake_hass):
        # Stored as on VM998: a radio trigger scoped to the infrared side.
        store = _store(fake_hass)
        trigger = _stored(store, "RF_RAW", [IR_RX])
        conn = await _update(fake_hass, trigger.id, receiver_entity_ids=[RF_RX])
        assert _error_code(conn) is None
        assert trigger.receiver_entity_ids == [RF_RX]

    async def test_saving_any_receiver_repairs_it_too(self, fake_hass):
        store = _store(fake_hass)
        trigger = _stored(store, "RF_RAW", [IR_RX])
        conn = await _update(fake_hass, trigger.id, receiver_entity_ids=[])
        assert _error_code(conn) is None
        assert trigger.receiver_entity_ids == []

    async def test_an_update_without_receivers_leaves_a_stored_scope_alone(self, fake_hass):
        # The doors refuse what they are sent; a stored scope is changed
        # only when the dialog saves one (owner, 2026-11-09).
        store = _store(fake_hass)
        trigger = _stored(store, "RF_RAW", [IR_RX])
        conn = await _update(fake_hass, trigger.id, name="Front door")
        assert _error_code(conn) is None
        assert trigger.name == "Front door"
        assert trigger.receiver_entity_ids == [IR_RX]

    async def test_an_infrared_trigger_refuses_a_radio_receiver(self, fake_hass):
        store = _store(fake_hass)
        trigger = _stored(store, "NEC", [IR_RX])
        conn = await _update(fake_hass, trigger.id, receiver_entity_ids=[RF_RX])
        assert _error_code(conn) == RECEIVER_WRONG_MEDIUM
        assert trigger.receiver_entity_ids == [IR_RX]


def _rf_state(entity_id, capturing):
    attrs = {"friendly_name": entity_id}
    if capturing is not None:
        attrs["capturing"] = capturing
    return SimpleNamespace(entity_id=entity_id, attributes=attrs, state="idle")


@pytest.mark.asyncio
async def test_the_receivers_door_lists_always_on_radio_receivers(fake_hass):
    capture = "radio_frequency.rm4_pro_rf_receiver"
    states = {RF_RX: _rf_state(RF_RX, None), capture: _rf_state(capture, False)}
    fake_hass.states.get = MagicMock(side_effect=states.get)
    conn = MagicMock()
    with patch(
        "homeassistant.components.infrared.async_get_receivers",
        return_value=[], create=True,
    ), patch(
        "custom_components.hair.rf_receive.rf_receiver_ids",
        return_value=sorted(states),
    ), patch(
        "custom_components.hair.websocket_api.er.async_get",
        return_value=MagicMock(async_get=MagicMock(return_value=None)),
    ):
        await ws_get_receivers(fake_hass, conn, {"id": 3, "type": "hair/receivers"})
    [result] = conn.send_result.call_args.args[1:]
    assert result == [
        {"entity_id": RF_RX, "name": RF_RX, "medium": "rf"},
        {"entity_id": capture, "name": capture, "medium": "rf"},
    ]
