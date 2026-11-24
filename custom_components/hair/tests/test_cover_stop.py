"""A screen's Stop, Up and Down land on the cover's own actions (GH #313).

The shared auto-map table gives a name one key for every type, so a
screen's "Stop" was ``stop`` (the media player's), which the cover does
not read: the cover offered no Stop. On a screen the key is translated
after the lookup: Stop to ``stop_cover``, Up to ``open_cover`` and Down
to ``close_cover`` (the shade convention), with every locale's synonym
and the Screen template's own "Stop". French "Arrêt", Off in the shared
table, is Stop on a screen. Every other type is unchanged.

Setup heals what the old rule stored: a Screen Device's ``stop`` key
becomes ``stop_cover``, or is dropped when ``stop_cover`` is already
mapped; a typed screen Remote, which lost its Stop button outright, gets
``stop_cover`` from a button whose name maps there.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import custom_components.hair as hair_init
from custom_components.hair.command_templates import (
    ACTION_OPTIONS,
    COMMAND_TEMPLATES,
)
from custom_components.hair.const import DeviceType
from custom_components.hair.cover import HAIRCoverEntity
from custom_components.hair.device_manager import (
    AUTO_MAP_RULES,
    DeviceManager,
    auto_map_feature,
    heal_screen_stop,
)
from custom_components.hair.models import (
    EntityConfig,
    IRCommand,
    IRDevice,
    IRTrigger,
    TriggerRemote,
)
from custom_components.hair.remote_state import FILL_NAMES, plan_fill
from custom_components.hair.storage import HAIRStore
from custom_components.hair.tests.test_storage import _FakeStore
from custom_components.hair.vocabulary import localized_auto_map

SCREEN = DeviceType.SCREEN


def _screen(*names: str) -> IRDevice:
    device = IRDevice(name="Awning", device_type=SCREEN)
    manager = DeviceManager.__new__(DeviceManager)
    for name in names:
        command = IRCommand(name=name)
        device.add_command(command)
        manager._auto_map_command(device, command)
    return device


def _synonyms(key: str) -> list[str]:
    names = {n for n, k in AUTO_MAP_RULES.items() if k == key}
    names |= {n for n, k in localized_auto_map(AUTO_MAP_RULES).items() if k == key}
    return sorted(names)


# ---------------------------------------------------------------------------
# The mapping
# ---------------------------------------------------------------------------


class TestTheMapping:
    def test_stop_up_and_down_on_a_screen(self):
        assert auto_map_feature("Stop", SCREEN) == "stop_cover"
        assert auto_map_feature("Up", SCREEN) == "open_cover"
        assert auto_map_feature("Down", SCREEN) == "close_cover"
        assert auto_map_feature("Open", SCREEN) == "open_cover"
        assert auto_map_feature("Close", SCREEN) == "close_cover"

    @pytest.mark.parametrize(
        ("key", "cover_key"),
        [
            ("stop", "stop_cover"),
            ("navigate_up", "open_cover"),
            ("navigate_down", "close_cover"),
        ],
    )
    def test_every_locales_synonym_follows(self, key, cover_key):
        names = _synonyms(key)
        assert len(names) > 5, names
        for name in names:
            assert auto_map_feature(name, SCREEN) == cover_key, name
            assert auto_map_feature(name.upper(), SCREEN) == cover_key, name

    @pytest.mark.parametrize("name", ["Arrêt", "ARRÊT", "arret", " Arrêt "])
    def test_arret_is_stop_on_a_screen_only(self, name):
        assert auto_map_feature(name, SCREEN) == "stop_cover"
        if name.strip().casefold() == "arrêt":
            assert auto_map_feature(name.strip(), DeviceType.MEDIA_PLAYER) == "turn_off"

    @pytest.mark.parametrize(
        "device_type",
        [t for t in DeviceType if t != SCREEN] + [None],
    )
    def test_every_other_type_is_unchanged(self, device_type):
        assert auto_map_feature("Stop", device_type) == "stop"
        assert auto_map_feature("Up", device_type) == "navigate_up"
        assert auto_map_feature("Down", device_type) == "navigate_down"

    def test_the_screen_templates_all_map_to_what_a_screen_offers(self):
        offered = {key for key, _ in ACTION_OPTIONS[SCREEN]}
        for template in COMMAND_TEMPLATES[SCREEN]:
            assert auto_map_feature(template.name, SCREEN) in offered, template.name

    def test_an_unknown_name_still_maps_nothing(self):
        assert auto_map_feature("My", SCREEN) is None
        assert auto_map_feature("Halt", SCREEN) is None

    def test_a_device_captured_from_the_template_gets_stop(self):
        device = _screen("Open", "Close", "Stop")
        assert device.entity_config.command_mapping == {
            "open_cover": "Open", "close_cover": "Close", "stop_cover": "Stop",
        }


# ---------------------------------------------------------------------------
# The cover entity
# ---------------------------------------------------------------------------


class TestTheCover:
    @pytest.mark.asyncio
    async def test_the_cover_offers_and_sends_stop(self):
        device = _screen("Up", "Down", "Stop")
        sent = AsyncMock()
        manager = MagicMock()
        manager.async_send_command = sent
        entity = HAIRCoverEntity(device, manager)
        entity.hass = MagicMock()
        entity.async_write_ha_state = MagicMock()
        # OPEN 1 + CLOSE 2 + STOP 8: what the reporter asked for.
        assert int(entity.supported_features) == 11
        await entity.async_stop_cover()
        assert sent.await_args[0][:2] == (device.id, device.get_command_by_name("Stop").id)
        await entity.async_open_cover()
        assert sent.await_args[0][:2] == (device.id, device.get_command_by_name("Up").id)


# ---------------------------------------------------------------------------
# A typed screen Remote's fill
# ---------------------------------------------------------------------------


async def _store(fake_hass) -> HAIRStore:
    store = HAIRStore(fake_hass)
    await store.async_load()
    return store


def _buttons(store, remote, *names):
    triggers = []
    for name in names:
        trigger = IRTrigger(name=name, trigger_remote_id=remote.id)
        store.add_trigger(trigger)
        triggers.append(trigger)
    return triggers


class TestARemotesFill:
    @pytest.mark.asyncio
    async def test_a_screen_remote_maps_its_stop_by_name(self, fake_hass):
        with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
            store = await _store(fake_hass)
            remote = TriggerRemote(name="Awning handset")
            store.add_trigger_remote(remote)
            up, stop, down = _buttons(store, remote, "Up", "Stop", "Down")
            plan = plan_fill(store, remote, SCREEN)
            assert plan.source == FILL_NAMES
            assert plan.mapping == {
                "open_cover": up.id, "stop_cover": stop.id, "close_cover": down.id,
            }


# ---------------------------------------------------------------------------
# The heal at setup
# ---------------------------------------------------------------------------


def _old_screen(**mapping) -> IRDevice:
    device = IRDevice(
        name="Awning", device_type=SCREEN,
        entity_config=EntityConfig(command_mapping=dict(mapping)),
    )
    for name in set(mapping.values()):
        device.add_command(IRCommand(name=name))
    return device


class TestTheHeal:
    @pytest.mark.asyncio
    async def test_a_screens_stop_key_becomes_the_covers(self, fake_hass):
        with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
            store = await _store(fake_hass)
            device = _old_screen(open_cover="Open", close_cover="Close", stop="Stop")
            store.add_device(device)
            assert heal_screen_stop(store) is True
            assert device.entity_config.command_mapping == {
                "open_cover": "Open", "close_cover": "Close", "stop_cover": "Stop",
            }
            assert heal_screen_stop(store) is False

    @pytest.mark.asyncio
    async def test_a_stop_cover_set_by_hand_wins(self, fake_hass):
        with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
            store = await _store(fake_hass)
            device = _old_screen(stop_cover="Halt", stop="Stop")
            store.add_device(device)
            assert heal_screen_stop(store) is True
            assert device.entity_config.command_mapping == {"stop_cover": "Halt"}

    @pytest.mark.asyncio
    async def test_other_types_keep_their_stop(self, fake_hass):
        with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
            store = await _store(fake_hass)
            tv = IRDevice(
                name="TV", device_type=DeviceType.MEDIA_PLAYER,
                entity_config=EntityConfig(command_mapping={"stop": "Stop"}),
            )
            store.add_device(tv)
            assert heal_screen_stop(store) is False
            assert tv.entity_config.command_mapping == {"stop": "Stop"}

    @pytest.mark.asyncio
    async def test_a_screen_remote_gets_its_lost_stop(self, fake_hass):
        with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
            store = await _store(fake_hass)
            remote = TriggerRemote(name="Awning handset", device_type=SCREEN)
            store.add_trigger_remote(remote)
            up, stop, down = _buttons(store, remote, "Up", "Stopp", "Down")
            remote.entity_config.command_mapping = {
                "open_cover": up.id, "close_cover": down.id,
            }
            assert heal_screen_stop(store) is True
            assert remote.entity_config.command_mapping["stop_cover"] == stop.id
            assert heal_screen_stop(store) is False

    @pytest.mark.asyncio
    async def test_a_remote_button_holding_another_key_is_left(self, fake_hass):
        with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
            store = await _store(fake_hass)
            remote = TriggerRemote(name="Handset", device_type=SCREEN)
            store.add_trigger_remote(remote)
            (stop,) = _buttons(store, remote, "Stop")
            remote.entity_config.command_mapping = {"close_cover": stop.id}
            assert heal_screen_stop(store) is False
            assert remote.entity_config.command_mapping == {"close_cover": stop.id}

    @pytest.mark.asyncio
    async def test_other_remotes_are_left(self, fake_hass):
        with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
            store = await _store(fake_hass)
            untyped = TriggerRemote(name="Untyped")
            player = TriggerRemote(name="TV", device_type=DeviceType.MEDIA_PLAYER)
            for remote in (untyped, player):
                store.add_trigger_remote(remote)
                _buttons(store, remote, "Stop")
            assert heal_screen_stop(store) is False
            assert untyped.entity_config.command_mapping == {}
            assert player.entity_config.command_mapping == {}

    def test_setup_runs_it_after_the_table_and_saves_once(self):
        import inspect

        source = inspect.getsource(hair_init.async_setup_entry)
        prime = source.index("await hass.async_add_executor_job(prime_localized_auto_map)")
        heal = source.index("healed = heal_screen_stop(store)")
        assert prime < heal
        block = source[heal: heal + 300]
        assert "if healed:\n        await store.async_save()" in block
        guard = source[prime:heal]
        assert "try:" in guard
