"""Every Remote reports its last press (heard state round 1, GH #172).

One ``event`` entity per named Remote, "Last pressed", whose event
types are the Remote's buttons. The contracts under test:

- it fires once per confirmed trigger fire, from the same TriggerManager
  callback as the per-trigger entities, with the button's type and data;
  an echo never reaches a trigger, so it never fires on one;
- the event type is the button's name as written, " (2)" for a second
  button of one name (by creation order, so a reorder never reshuffles
  it), "Button" for a blank name;
- HA refuses an event whose type is not listed yet, so a button pressed
  right after it is created or renamed syncs its Remote's types first;
- lifecycle: created with a Remote (create, Make a Remote, Duplicate),
  empty Remotes included; follows a Remote rename and every button add,
  rename, reorder and delete; removed with its Remote, registry row
  included; the drawer gets none;
- the per-trigger event entities are unchanged.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.entity_factory import (
    classify_unique_id,
    remote_last_pressed_unique_id,
    trigger_unique_id,
)
from custom_components.hair.event import (
    BLANK_BUTTON,
    EVENT_TYPE,
    HAIRRemoteLastPressedEntity,
    HAIRTriggerEventEntity,
    async_setup_entry,
    remote_event_types,
    sync_remote_entities,
)
from custom_components.hair.models import IRCommand, IRDevice, IRTrigger, TriggerRemote
from custom_components.hair.storage import HAIRStore

from .test_device_sent import _FakeStore
from .test_orphan_entities import FakeRegistry, _registry_patch

ENTRY_ID = "entry-1"


class _Bench:
    """A real store and the real event platform, with HA's entity
    plumbing reduced to a recorder."""

    def __init__(self, fake_hass):
        self.hass = fake_hass
        with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
            self.store = HAIRStore(fake_hass)
        self.store._loaded = True
        self.store.async_save = AsyncMock()
        self.trigger_manager = MagicMock()
        self.added: list = []
        self.removed: list = []
        self.registry = FakeRegistry()
        fake_hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())
        fake_hass.data[DOMAIN] = {ENTRY_ID: {
            "store": self.store,
            "trigger_manager": self.trigger_manager,
            "device_manager": MagicMock(),
            "config_entry": SimpleNamespace(entry_id=ENTRY_ID),
        }}

    @property
    def data(self) -> dict:
        return self.hass.data[DOMAIN][ENTRY_ID]

    def _add_entities(self, entities):
        for entity in entities:
            entity.hass = self.hass
            entity.entity_id = f"event.{entity._attr_unique_id}"
            entity.async_write_ha_state = MagicMock()
            entity.async_remove = AsyncMock(
                side_effect=lambda e=entity: self.removed.append(e)
            )
            if isinstance(entity, HAIRRemoteLastPressedEntity):
                self.registry.rows[f"event.{entity.remote_id}_last_pressed"] = (
                    SimpleNamespace(
                        entity_id=f"event.{entity.remote_id}_last_pressed",
                        domain="event", platform=DOMAIN,
                        unique_id=entity._attr_unique_id,
                        config_entry_id=ENTRY_ID,
                    )
                )
            else:
                self.registry.rows[f"event.trigger_{entity.trigger.id}"] = (
                    SimpleNamespace(
                        entity_id=f"event.trigger_{entity.trigger.id}",
                        domain="event", platform=DOMAIN,
                        unique_id=entity._attr_unique_id,
                        config_entry_id=ENTRY_ID,
                    )
                )
        self.added.extend(entities)

    async def setup(self):
        with _registry_patch(self.registry):
            await async_setup_entry(
                self.hass, SimpleNamespace(entry_id=ENTRY_ID), self._add_entities
            )
        self.fire_cb = self.trigger_manager.register_entity_callback.call_args[0][0]
        return self

    def remote_entities(self) -> dict[str, HAIRRemoteLastPressedEntity]:
        return self.data["_remote_last_pressed_entities"]

    def entity(self, remote_id) -> HAIRRemoteLastPressedEntity:
        return self.remote_entities()[remote_id]

    def fire(self, trigger_id, **extra):
        with _registry_patch(self.registry):
            self.fire_cb(trigger_id, {"trigger_id": trigger_id, "hit_count": 1, **extra})

    def sync(self, removed=None):
        with _registry_patch(self.registry):
            sync_remote_entities(self.hass, ENTRY_ID, removed_remote_id=removed)


def _trigger(tid, name, remote_id="rem1", created="2026-10-20T00:00:00", order=None):
    return IRTrigger(
        id=tid, name=name, trigger_remote_id=remote_id,
        signal_fingerprint=f"fp-{tid}", created_at=created, order=order,
    )


def _store_with(bench, remotes=(), triggers=()):
    for remote in remotes:
        bench.store.add_trigger_remote(remote)
    for trigger in triggers:
        bench.store.add_trigger(trigger)


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------


def test_event_types_are_the_names_as_written(fake_hass):
    bench = _Bench(fake_hass)
    _store_with(bench, [TriggerRemote(id="rem1", name="Office TV")], [
        _trigger("t1", "  Power  ", order=0),
        _trigger("t2", "Volume +", order=1),
        _trigger("t3", "音量", order=2),
        _trigger("t4", "", order=3),
    ])
    assert list(remote_event_types(bench.store, "rem1").values()) == [
        "Power", "Volume +", "音量", BLANK_BUTTON,
    ]


def test_a_shared_name_gets_a_suffix_by_creation_order_not_button_order(fake_hass):
    bench = _Bench(fake_hass)
    _store_with(bench, [TriggerRemote(id="rem1", name="Office TV")], [
        _trigger("t1", "Power", created="2026-10-20T00:00:02", order=0),
        _trigger("t2", "Power", created="2026-10-20T00:00:01", order=1),
        _trigger("t3", "Power", created="2026-10-20T00:00:03", order=2),
    ])
    types = remote_event_types(bench.store, "rem1")
    assert types == {"t1": "Power (2)", "t2": "Power", "t3": "Power (3)"}
    bench.store.reorder_triggers(["t3", "t1", "t2"])
    assert remote_event_types(bench.store, "rem1") == {
        "t3": "Power (3)", "t1": "Power (2)", "t2": "Power",
    }


def test_a_newer_literal_name_takes_the_next_free_and_moves_no_older_type(fake_hass):
    """Owner ruling 2026-10-21: types are claimed in creation order, so
    adding a button never changes an existing button's type."""
    bench = _Bench(fake_hass)
    _store_with(bench, [TriggerRemote(id="rem1", name="Office TV")], [
        _trigger("t1", "Power", created="2026-10-20T00:00:01"),
        _trigger("t2", "Power", created="2026-10-20T00:00:02"),
    ])
    before = remote_event_types(bench.store, "rem1")
    assert before == {"t1": "Power", "t2": "Power (2)"}

    bench.store.add_trigger(
        _trigger("t3", "Power (2)", created="2026-10-20T00:00:03")
    )
    after = remote_event_types(bench.store, "rem1")
    assert {k: after[k] for k in before} == before
    assert after["t3"] == "Power (2) (2)"
    assert len(set(after.values())) == 3


def test_an_older_literal_name_keeps_it_and_the_newer_duplicate_moves_on(fake_hass):
    bench = _Bench(fake_hass)
    _store_with(bench, [TriggerRemote(id="rem1", name="Office TV")], [
        _trigger("t1", "Power (2)", created="2026-10-20T00:00:01"),
        _trigger("t2", "Power", created="2026-10-20T00:00:02"),
    ])
    before = remote_event_types(bench.store, "rem1")
    bench.store.add_trigger(_trigger("t3", "Power", created="2026-10-20T00:00:03"))
    after = remote_event_types(bench.store, "rem1")
    assert {k: after[k] for k in before} == before
    assert after == {"t1": "Power (2)", "t2": "Power", "t3": "Power (3)"}


def test_only_this_remotes_buttons(fake_hass):
    bench = _Bench(fake_hass)
    _store_with(bench, [
        TriggerRemote(id="rem1", name="Office TV"),
        TriggerRemote(id="rem2", name="Fan"),
    ], [
        _trigger("t1", "Power"), _trigger("t2", "Speed", remote_id="rem2"),
        _trigger("t3", "Doorbell", remote_id=None),
    ])
    assert list(remote_event_types(bench.store, "rem1").values()) == ["Power"]


# ---------------------------------------------------------------------------
# Firing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_fire_reports_the_button_once_with_its_data(fake_hass):
    bench = _Bench(fake_hass)
    _store_with(bench, [TriggerRemote(id="rem1", name="Office TV")], [
        _trigger("t1", "Power", order=0), _trigger("t2", "Mute", order=1),
    ])
    await bench.setup()
    entity = bench.entity("rem1")
    assert entity._attr_event_types == ["Power", "Mute"]
    entity.async_write_ha_state.reset_mock()

    bench.fire("t2", receiver_entity_id="infrared.lr")

    assert entity._last_event_type == "Mute"
    data = entity._last_event_attributes
    assert data["button"] == "Mute"
    assert data["trigger_id"] == "t2"
    assert data["entity_id"] == "event.trigger_t2"
    assert data["remote_id"] == "rem1"
    assert data["remote_name"] == "Office TV"
    assert data["receiver_entity_id"] == "infrared.lr"
    assert entity.async_write_ha_state.call_count == 1
    # The per-trigger entity still fires, unchanged.
    per_trigger = bench.data["_trigger_entities"]["t2"]
    assert per_trigger._last_event_type == EVENT_TYPE


@pytest.mark.asyncio
async def test_the_drawer_has_no_last_pressed_and_its_fires_reach_none(fake_hass):
    bench = _Bench(fake_hass)
    _store_with(bench, [TriggerRemote(id="rem1", name="Office TV")], [
        _trigger("t1", "Doorbell", remote_id=None),
    ])
    await bench.setup()
    assert set(bench.remote_entities()) == {"rem1"}
    bench.fire("t1")
    assert getattr(bench.entity("rem1"), "_last_event_type", None) is None


@pytest.mark.asyncio
async def test_an_echo_never_fires_it(fake_hass):
    """Echoes are claimed in the signal monitor, before any trigger is
    matched, so neither entity hears one. Driven through a real
    TriggerManager: an echo claim means on_signal_captured is never
    called, and a real capture is."""
    from custom_components.hair.trigger_manager import TriggerManager

    bench = _Bench(fake_hass)
    _store_with(bench, [TriggerRemote(id="rem1", name="Office TV")], [
        _trigger("t1", "Power"),
    ])
    tm = TriggerManager(fake_hass, bench.store, MagicMock())
    bench.data["trigger_manager"] = tm
    with _registry_patch(bench.registry):
        await async_setup_entry(
            fake_hass, SimpleNamespace(entry_id=ENTRY_ID), bench._add_entities
        )
    entity = bench.entity("rem1")
    entity.async_write_ha_state.reset_mock()

    with _registry_patch(bench.registry):
        tm.on_signal_captured("fp-t1", None, None)
    assert entity._last_event_type == "Power"
    assert entity.async_write_ha_state.call_count == 1


@pytest.mark.asyncio
async def test_a_button_pressed_right_after_it_is_created_fires(fake_hass):
    """No sync ran between the store change and the press: the fire
    resolves its own type first, as HA would refuse an unlisted one."""
    bench = _Bench(fake_hass)
    _store_with(bench, [TriggerRemote(id="rem1", name="Office TV")])
    await bench.setup()
    entity = bench.entity("rem1")
    assert entity._attr_event_types == []

    bench.store.add_trigger(_trigger("t1", "Power"))
    bench.fire("t1")

    assert entity._attr_event_types == ["Power"]
    assert entity._last_event_type == "Power"


@pytest.mark.asyncio
async def test_a_button_pressed_right_after_a_rename_fires_under_its_new_name(fake_hass):
    bench = _Bench(fake_hass)
    _store_with(bench, [TriggerRemote(id="rem1", name="Office TV")], [
        _trigger("t1", "Pwr"),
    ])
    await bench.setup()
    entity = bench.entity("rem1")

    trigger = bench.store.get_trigger("t1")
    trigger.name = "Power"
    bench.store.update_trigger(trigger)
    bench.fire("t1")

    assert entity._attr_event_types == ["Power"]
    assert entity._last_event_type == "Power"
    assert entity._last_event_attributes["button"] == "Power"


def test_the_stub_refuses_an_unlisted_type_as_ha_does():
    """The guard above is only tested if an unlisted type would raise."""
    entity = HAIRRemoteLastPressedEntity(TriggerRemote(id="rem1", name="X"), {})
    with pytest.raises(ValueError):
        entity._trigger_event("Power", {})


# ---------------------------------------------------------------------------
# The entity itself
# ---------------------------------------------------------------------------


def test_the_unique_id_and_device_and_name():
    remote = TriggerRemote(id="rem1", name="Office TV")
    entity = HAIRRemoteLastPressedEntity(remote, {"t1": "Power"})
    assert entity._attr_unique_id == "hair_remote_rem1_last_pressed"
    assert entity._attr_unique_id == remote_last_pressed_unique_id("rem1")
    assert entity._attr_translation_key == "last_pressed"
    assert entity.device_info == {
        "identifiers": {(DOMAIN, "rem1")},
        "name": "Office TV",
        "manufacturer": "HAIR",
        "model": "IR Triggers",
    }
    trigger_entity = HAIRTriggerEventEntity(_trigger("t1", "Power"), "rem1", "Office TV")
    assert entity.device_info == trigger_entity.device_info


def test_the_orphan_sweep_never_touches_its_row():
    assert classify_unique_id(remote_last_pressed_unique_id("abc123")) is None


def test_every_translation_names_it():
    import json
    from pathlib import Path

    folder = Path(__file__).parent.parent / "translations"
    files = sorted(folder.glob("*.json"))
    assert len(files) == 12
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        name = data["entity"]["event"]["last_pressed"]["name"]
        assert name.strip(), path.name
    english = json.loads((folder / "en.json").read_text(encoding="utf-8"))
    assert english["entity"]["event"]["last_pressed"]["name"] == "Last pressed"


# ---------------------------------------------------------------------------
# Lifecycle, through the real WebSocket handlers
# ---------------------------------------------------------------------------


def _conn():
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    return conn


def _dr():
    registry = MagicMock()
    registry.async_get_or_create = MagicMock(return_value=MagicMock(id="ha-dev"))
    registry.async_get_device = MagicMock(return_value=None)
    return patch(
        "custom_components.hair.websocket_api.dr.async_get", return_value=registry,
    )


@pytest.mark.asyncio
async def test_an_empty_remote_gets_its_entity_at_creation(fake_hass):
    from custom_components.hair.websocket_api import ws_create_trigger_remote

    bench = await _Bench(fake_hass).setup()
    conn = _conn()
    with _dr(), _registry_patch(bench.registry):
        await ws_create_trigger_remote(fake_hass, conn, {
            "id": 1, "type": "hair/trigger-remote/create", "name": "Bedroom Fan",
        })
    remote_id = conn.send_result.call_args[0][1]["id"]
    entity = bench.entity(remote_id)
    assert entity in bench.added
    assert entity._attr_event_types == []
    assert entity.device_info["name"] == "Bedroom Fan"


@pytest.mark.asyncio
async def test_buttons_added_renamed_reordered_and_deleted_follow(fake_hass):
    from custom_components.hair.websocket_api import (
        ws_create_trigger,
        ws_delete_trigger,
        ws_reorder_triggers,
        ws_update_trigger,
    )

    bench = _Bench(fake_hass)
    _store_with(bench, [TriggerRemote(id="rem1", name="Office TV")])
    await bench.setup()
    entity = bench.entity("rem1")

    with _registry_patch(bench.registry):
        for name in ("Power", "Mute"):
            conn = _conn()
            await ws_create_trigger(fake_hass, conn, {
                "id": 1, "type": "hair/trigger/create", "name": name,
                "signal_fingerprint": f"fp-{name}", "protocol": None,
                "code": None, "min_hits": 1, "trigger_remote_id": "rem1",
            })
            conn.send_error.assert_not_called()
    assert entity._attr_event_types == ["Power", "Mute"]
    ids = [t.id for t in bench.store.get_triggers_for_remote("rem1")]

    with _registry_patch(bench.registry):
        await ws_update_trigger(fake_hass, _conn(), {
            "id": 2, "type": "hair/trigger/update", "trigger_id": ids[1],
            "name": "Silence",
        })
    assert entity._attr_event_types == ["Power", "Silence"]

    conn = _conn()
    with _registry_patch(bench.registry):
        await ws_reorder_triggers(fake_hass, conn, {
            "id": 3, "type": "hair/triggers/reorder",
            "trigger_ids": list(reversed(
                [t.id for t in bench.store.get_all_triggers_ordered()]
            )),
        })
    conn.send_error.assert_not_called()
    assert entity._attr_event_types == ["Silence", "Power"]

    with _registry_patch(bench.registry):
        await ws_delete_trigger(fake_hass, _conn(), {
            "id": 4, "type": "hair/trigger/delete", "trigger_id": ids[0],
        })
    assert entity._attr_event_types == ["Silence"]


@pytest.mark.asyncio
async def test_a_remote_rename_reaches_its_device_name(fake_hass):
    from custom_components.hair.websocket_api import ws_rename_trigger_remote

    bench = _Bench(fake_hass)
    _store_with(bench, [TriggerRemote(id="rem1", name="Office TV")])
    await bench.setup()
    with _dr(), _registry_patch(bench.registry):
        await ws_rename_trigger_remote(fake_hass, _conn(), {
            "id": 1, "type": "hair/trigger-remote/rename",
            "remote_id": "rem1", "name": "Den TV",
        })
    assert bench.entity("rem1").device_info["name"] == "Den TV"
    bench.entity("rem1").async_write_ha_state.assert_called()


@pytest.mark.asyncio
async def test_deleting_a_remote_removes_its_entity_and_registry_row(fake_hass):
    from custom_components.hair.websocket_api import ws_delete_trigger_remote

    bench = _Bench(fake_hass)
    _store_with(bench, [
        TriggerRemote(id="rem1", name="Office TV"),
        TriggerRemote(id="rem2", name="Fan"),
    ], [_trigger("t1", "Power")])
    await bench.setup()
    doomed = bench.entity("rem1")
    with _dr(), _registry_patch(bench.registry):
        await ws_delete_trigger_remote(fake_hass, _conn(), {
            "id": 1, "type": "hair/trigger-remote/delete", "remote_id": "rem1",
        })
    assert set(bench.remote_entities()) == {"rem2"}
    doomed.async_remove.assert_called_once()
    assert "event.rem1_last_pressed" in bench.registry.removed
    assert "event.rem2_last_pressed" in bench.registry.rows


def test_a_removed_remotes_row_goes_even_without_the_entity_object(fake_hass):
    """After a restart the dict is rebuilt from the store, so a deleted
    Remote's object may never have existed in this run."""
    bench = _Bench(fake_hass)
    bench.registry.rows["event.gone_last_pressed"] = SimpleNamespace(
        entity_id="event.gone_last_pressed", domain="event", platform=DOMAIN,
        unique_id=remote_last_pressed_unique_id("gone"), config_entry_id=ENTRY_ID,
    )
    bench.data["_remote_last_pressed_entities"] = {}
    bench.data["_trigger_add_entities"] = bench._add_entities
    bench.sync(removed="gone")
    assert bench.registry.removed == ["event.gone_last_pressed"]


@pytest.mark.asyncio
async def test_duplicate_and_make_a_remote_create_it(fake_hass):
    from custom_components.hair.websocket_api import (
        ws_device_make_remote,
        ws_duplicate_trigger_remote,
    )

    bench = _Bench(fake_hass)
    _store_with(bench, [TriggerRemote(id="rem1", name="Office TV")], [
        _trigger("t1", "Power"),
    ])
    bench.store.add_device(IRDevice(
        id="dev1", name="Office TV",
        commands=[IRCommand(id="c1", name="Power", protocol="PRONTO",
                            code="0000 006D 0002 0000 0020 0020 0040 0040")],
    ))
    await bench.setup()
    bench.data["device_manager"] = MagicMock(get_device=bench.store.get_device)

    conn = _conn()
    with _dr(), _registry_patch(bench.registry):
        await ws_duplicate_trigger_remote(fake_hass, conn, {
            "id": 1, "type": "hair/trigger-remote/duplicate",
            "remote_id": "rem1", "new_name": "Office TV 2",
        })
    conn.send_error.assert_not_called()
    clone_id = conn.send_result.call_args[0][1]["id"]
    assert bench.entity(clone_id)._attr_event_types == ["Power"]

    conn = _conn()
    with _dr(), _registry_patch(bench.registry):
        await ws_device_make_remote(fake_hass, conn, {
            "id": 2, "type": "hair/device/make-remote",
            "device_id": "dev1", "name": "Office TV Triggers",
        })
    conn.send_error.assert_not_called()
    made_id = conn.send_result.call_args[0][1]["id"]
    assert bench.entity(made_id)._attr_event_types == ["Power"]


@pytest.mark.asyncio
async def test_a_sync_with_nothing_changed_writes_nothing(fake_hass):
    bench = _Bench(fake_hass)
    _store_with(bench, [TriggerRemote(id="rem1", name="Office TV")], [
        _trigger("t1", "Power"),
    ])
    await bench.setup()
    entity = bench.entity("rem1")
    entity.async_write_ha_state.reset_mock()
    bench.sync()
    entity.async_write_ha_state.assert_not_called()


@pytest.mark.asyncio
async def test_setup_builds_one_per_named_remote(fake_hass):
    bench = _Bench(fake_hass)
    _store_with(bench, [
        TriggerRemote(id="rem1", name="Office TV"),
        TriggerRemote(id="rem2", name="Empty"),
    ], [_trigger("t1", "Power")])
    await bench.setup()
    remotes = [e for e in bench.added if isinstance(e, HAIRRemoteLastPressedEntity)]
    assert sorted(e.remote_id for e in remotes) == ["rem1", "rem2"]
    triggers = [e for e in bench.added if isinstance(e, HAIRTriggerEventEntity)]
    assert [e._attr_unique_id for e in triggers] == [trigger_unique_id("t1")]


def test_every_handler_that_changes_a_remote_or_its_buttons_syncs():
    """Read the source, as the decorator-stack guard in test_websocket_api
    does: a handler that changes a Remote or its buttons and forgets the
    sync leaves "Last pressed" stale until the next fire or restart."""
    import inspect

    from custom_components.hair import websocket_api

    handlers = (
        "ws_create_trigger", "ws_update_trigger", "ws_delete_trigger",
        "ws_reorder_triggers", "ws_create_trigger_remote",
        "ws_rename_trigger_remote", "ws_delete_trigger_remote",
        "ws_duplicate_trigger_remote", "ws_wig_make_remote",
        "ws_device_make_remote",
    )
    for name in handlers:
        source = inspect.getsource(getattr(websocket_api, name))
        assert "sync_remote_entities(" in source, name


def _raising_write(entity):
    """HA's write check: no hass or no entity id raises, as for a
    disabled entity or one whose add is still pending."""
    def _write():
        if entity.hass is None or entity.entity_id is None:
            raise RuntimeError("Attribute hass is None")
    entity.async_write_ha_state = MagicMock(side_effect=_write)


@pytest.mark.parametrize("state", ["disabled", "pending"])
def test_a_disabled_or_pending_entity_stays_silent_and_never_raises(fake_hass, state):
    """A disabled "Last pressed" is never added: HA sets hass back to
    None. A pending one has hass but no entity id yet. Either way a
    press of that Remote must not raise on the capture path."""
    bench = _Bench(fake_hass)
    _store_with(bench, [TriggerRemote(id="rem1", name="Office TV")], [
        _trigger("t1", "Power"),
    ])
    entity = HAIRRemoteLastPressedEntity(
        bench.store.get_trigger_remote("rem1"), {}
    )
    entity.hass = None if state == "disabled" else fake_hass
    entity.entity_id = None
    _raising_write(entity)
    trigger = bench.store.get_trigger("t1")
    assert entity.fire_press(bench.store, trigger, {"trigger_id": "t1"}, None) is False
    entity.async_write_ha_state.assert_not_called()
    assert entity._attr_event_types == ["Power"]


def test_removing_a_disabled_entitys_remote_forgets_its_row_only(fake_hass):
    bench = _Bench(fake_hass)
    entity = HAIRRemoteLastPressedEntity(TriggerRemote(id="gone", name="X"), {})
    entity.hass = None
    entity.async_remove = AsyncMock()
    bench.registry.rows["event.gone_last_pressed"] = SimpleNamespace(
        entity_id="event.gone_last_pressed", domain="event", platform=DOMAIN,
        unique_id=remote_last_pressed_unique_id("gone"), config_entry_id=ENTRY_ID,
    )
    bench.data["_remote_last_pressed_entities"] = {"gone": entity}
    bench.data["_trigger_add_entities"] = bench._add_entities
    bench.sync()
    entity.async_remove.assert_not_called()
    assert bench.registry.removed == ["event.gone_last_pressed"]


def test_a_failing_event_entity_never_costs_the_bus_event_or_the_retransmit(fake_hass):
    """Device triggers listen on the bus event, and pinning rides the
    same fire. Neither may depend on the event entities succeeding."""
    from custom_components.hair.const import EVENT_TRIGGER_FIRED
    from custom_components.hair.trigger_manager import TriggerManager

    bench = _Bench(fake_hass)
    _store_with(bench, [TriggerRemote(id="rem1", name="Office TV")], [
        _trigger("t1", "Power"),
    ])
    tm = TriggerManager(fake_hass, bench.store, MagicMock())
    tm.register_entity_callback(MagicMock(side_effect=RuntimeError("boom")))
    tm._dispatch_retransmits = MagicMock()
    fired = tm.on_signal_captured("fp-t1", None, None)
    assert fired == ["t1"]
    events = [c.args[0] for c in fake_hass.bus.async_fire.call_args_list]
    assert EVENT_TRIGGER_FIRED in events
    tm._dispatch_retransmits.assert_called_once()
