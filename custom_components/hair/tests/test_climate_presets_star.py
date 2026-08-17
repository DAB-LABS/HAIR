"""Climate presets: the star (climate-presets-star.md).

The contracts under test:

- ``EntityConfig.starred`` is its own field, not a ``command_mapping``
  key, and it round-trips, defaults empty, and rides a device clone.
- The manager's ``async_set_starred`` is idempotent in both
  directions, stores the command's own spelling, and persists through
  ``async_update_device`` so the entity re-reads.
- Renaming a starred command renames the preset; deleting one prunes
  the star.
- The climate entity advertises ``PRESET_MODE`` only when something is
  starred, offers the starred names in the device's COMMAND order (the
  stored list is click order), sends the starred command through the
  ordinary device send path, and clears ``preset_mode`` on every other
  setter so the attribute never lies.
- On a matrix device a starred STATE row also moves the ``matrix_cell``
  readout, because a STATE row's name IS its cell's display name.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.climate import ClimateEntityFeature, HVACMode

from custom_components.hair.climate import HAIRClimateEntity
from custom_components.hair.const import DOMAIN, CommandSource, DeviceType
from custom_components.hair.device_manager import DeviceManager
from custom_components.hair.entity_factory import EntityFactory
from custom_components.hair.models import EntityConfig, IRCommand, IRDevice
from custom_components.hair.storage import HAIRStore
from custom_components.hair.websocket_api import ws_device_star
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix

# Entity tests never validate or transmit codes, so readable tags beat
# real Pronto hex for pinning which command went out.
P_OFF = "P-OFF"
P_ON = "P-ON"
STATE_ROW = "cool / fan: auto / 22"


class _FakeStore:
    def __init__(self, *args, **kwargs):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


@pytest.fixture
def manager(fake_hass):
    with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
        store = HAIRStore(fake_hass)
        store._loaded = True
        factory = EntityFactory(fake_hass)
        with patch(
            "custom_components.hair.device_manager.dr.async_get",
            return_value=MagicMock(
                async_get_or_create=MagicMock(
                    return_value=MagicMock(id="ha-dev-1")
                ),
                async_get_device=MagicMock(return_value=None),
                async_remove_device=MagicMock(),
            ),
        ):
            yield DeviceManager(fake_hass, store, factory, "entry-1")


def _flat_commands() -> list[IRCommand]:
    return [
        IRCommand(id="c-cool", name="Cool", protocol="PRONTO", code="P-C"),
        IRCommand(id="c-sleep", name="Sleep", protocol="PRONTO", code="P-S"),
        IRCommand(id="c-quiet", name="Quiet", protocol="PRONTO", code="P-Q"),
    ]


def _flat_device(starred: list[str] | None = None) -> IRDevice:
    return IRDevice(
        id="dev-flat",
        name="Bedroom AC",
        device_type=DeviceType.AC,
        emitter_entity_ids=["infrared.e"],
        commands=_flat_commands(),
        entity_config=EntityConfig(
            platform="climate",
            command_mapping={"mode_cool": "Cool"},
            starred=list(starred or []),
        ),
    )


def _flat_entity(starred: list[str] | None = None):
    """A preset-mode (flat) entity with the manager mocked.

    No ``async_added_to_hass``: a flat device has no matrix to load and
    nothing here depends on restore.
    """
    mgr = MagicMock()
    mgr.async_send_command = AsyncMock()
    entity = HAIRClimateEntity(_flat_device(starred), mgr)
    entity.async_write_ha_state = MagicMock()
    entity.hass = MagicMock()
    return entity, mgr


def _matrix() -> ClimateMatrix:
    return ClimateMatrix(
        min_temp=16.0,
        max_temp=30.0,
        precision=1.0,
        modes=["cool"],
        fan_modes=["auto"],
        swing_modes=[],
        off=P_OFF,
        on=P_ON,
        cells=[
            ClimateCell(mode="cool", fan="auto", temp=22.0, pronto="P-C-A-22"),
        ],
    )


async def _matrix_entity(starred: list[str] | None = None):
    """A matrix-mode entity carrying one saved STATE row."""
    device = IRDevice(
        id="dev-matrix",
        name="Living Room AC",
        device_type=DeviceType.AC,
        emitter_entity_ids=["infrared.e"],
        climate_matrix=True,
        commands=[
            IRCommand(
                id="c-state",
                name=STATE_ROW,
                source=CommandSource.MATRIX,
                protocol="PRONTO",
                code="P-C-A-22",
            ),
        ],
        entity_config=EntityConfig(
            platform="climate", starred=list(starred or [])
        ),
    )
    mgr = MagicMock()
    mgr.async_send_command = AsyncMock()
    mgr.async_send_matrix_cell = AsyncMock()
    mgr.async_get_matrix = AsyncMock(return_value=_matrix())
    entity = HAIRClimateEntity(device, mgr)
    entity.async_write_ha_state = MagicMock()
    entity.hass = MagicMock()
    await entity.async_added_to_hass()
    return entity, mgr


class TestModel:
    def test_defaults_empty(self):
        assert EntityConfig().starred == []

    def test_round_trip(self):
        config = EntityConfig(platform="climate", starred=["Sleep", "Quiet"])
        assert config.to_dict()["starred"] == ["Sleep", "Quiet"]
        assert EntityConfig.from_dict(config.to_dict()).starred == [
            "Sleep",
            "Quiet",
        ]

    def test_absent_reads_as_empty(self):
        """Stores written before this field parse as unstarred, not as
        a crash and not as None."""
        assert EntityConfig.from_dict({"platform": "climate"}).starred == []

    def test_starred_is_not_a_mapping_key(self):
        """The whole storage decision in one assertion: a command can be
        mapped AND starred at the same time, which a command_mapping key
        could never be (ws_update_mapping clears every key pointing at
        the command before setting a new one)."""
        device = _flat_device(starred=["Cool"])
        assert device.entity_config.command_mapping["mode_cool"] == "Cool"
        assert device.entity_config.starred == ["Cool"]

    def test_clone_copies_stars(self):
        clone = _flat_device(starred=["Sleep"]).clone("Bedroom AC copy")
        assert clone.entity_config.starred == ["Sleep"]
        # A copy, not the same list object.
        clone.entity_config.starred.append("Quiet")
        assert _flat_device(starred=["Sleep"]).entity_config.starred == [
            "Sleep"
        ]

    def test_rides_device_to_dict(self):
        """_device_full serializes entity_config wholesale, so the star
        reaches the frontend without a payload change of its own."""
        device = _flat_device(starred=["Sleep"])
        assert device.to_dict()["entity_config"]["starred"] == ["Sleep"]


class TestManagerSetStarred:
    @pytest.mark.asyncio
    async def test_star_then_unstar(self, manager):
        device = _flat_device()
        manager._store.add_device(device)
        assert await manager.async_set_starred(device.id, "Sleep", True) == [
            "Sleep"
        ]
        assert device.entity_config.starred == ["Sleep"]
        assert await manager.async_set_starred(device.id, "Sleep", False) == []
        assert device.entity_config.starred == []

    @pytest.mark.asyncio
    async def test_star_is_idempotent_and_keeps_click_order(self, manager):
        device = _flat_device()
        manager._store.add_device(device)
        await manager.async_set_starred(device.id, "Sleep", True)
        await manager.async_set_starred(device.id, "Cool", True)
        # Re-starring an already-starred command must not move it to
        # the end of the click order.
        assert await manager.async_set_starred(device.id, "Sleep", True) == [
            "Sleep",
            "Cool",
        ]

    @pytest.mark.asyncio
    async def test_unstar_is_idempotent(self, manager):
        device = _flat_device()
        manager._store.add_device(device)
        assert await manager.async_set_starred(device.id, "Sleep", False) == []

    @pytest.mark.asyncio
    async def test_stores_the_commands_own_spelling(self, manager):
        device = _flat_device()
        manager._store.add_device(device)
        assert await manager.async_set_starred(device.id, "sLeEp", True) == [
            "Sleep"
        ]

    @pytest.mark.asyncio
    async def test_unknown_device_or_command_returns_none(self, manager):
        device = _flat_device()
        manager._store.add_device(device)
        assert await manager.async_set_starred("nope", "Sleep", True) is None
        assert (
            await manager.async_set_starred(device.id, "Nope", True) is None
        )

    @pytest.mark.asyncio
    async def test_persists_through_update_device(self, manager):
        """Not a bare save: the entity update_device hooks have to fire
        or the more-info dialog keeps the previous preset set until a
        restart."""
        device = _flat_device()
        manager._store.add_device(device)
        with patch.object(
            manager, "async_update_device", AsyncMock(return_value=device)
        ) as update:
            await manager.async_set_starred(device.id, "Sleep", True)
        update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_write_when_already_in_state(self, manager):
        device = _flat_device(starred=["Sleep"])
        manager._store.add_device(device)
        with patch.object(
            manager, "async_update_device", AsyncMock(return_value=device)
        ) as update:
            await manager.async_set_starred(device.id, "Sleep", True)
        update.assert_not_awaited()


class TestCascadeAndPrune:
    @pytest.mark.asyncio
    async def test_rename_cascades_to_the_star(self, manager):
        device = _flat_device(starred=["Sleep"])
        manager._store.add_device(device)
        result = await manager.async_update_command(
            device.id, "c-sleep", name="Night"
        )
        assert result["success"] is True
        assert device.entity_config.starred == ["Night"]

    @pytest.mark.asyncio
    async def test_rename_leaves_other_stars_alone(self, manager):
        device = _flat_device(starred=["Sleep", "Quiet"])
        manager._store.add_device(device)
        await manager.async_update_command(device.id, "c-sleep", name="Night")
        assert device.entity_config.starred == ["Night", "Quiet"]

    @pytest.mark.asyncio
    async def test_delete_prunes_the_star(self, manager):
        device = _flat_device(starred=["Sleep", "Quiet"])
        manager._store.add_device(device)
        assert await manager.async_remove_command(device.id, "c-sleep") is True
        assert device.entity_config.starred == ["Quiet"]

    @pytest.mark.asyncio
    async def test_delete_leaves_unstarred_rows_alone(self, manager):
        device = _flat_device(starred=["Quiet"])
        manager._store.add_device(device)
        await manager.async_remove_command(device.id, "c-sleep")
        assert device.entity_config.starred == ["Quiet"]


class TestEntityFeatureAndModes:
    def test_no_stars_no_feature(self):
        entity, _ = _flat_entity()
        assert not (int(entity.supported_features)
                    & ClimateEntityFeature.PRESET_MODE)
        assert entity.preset_modes is None

    def test_star_lights_the_feature(self):
        entity, _ = _flat_entity(["Sleep"])
        assert (int(entity.supported_features)
                & ClimateEntityFeature.PRESET_MODE)

    @pytest.mark.asyncio
    async def test_feature_on_matrix_devices_too(self):
        entity, _ = await _matrix_entity([STATE_ROW])
        assert (int(entity.supported_features)
                & ClimateEntityFeature.PRESET_MODE)
        assert entity.preset_modes == [STATE_ROW]

    def test_preset_modes_follow_command_order_not_click_order(self):
        """Stored click order is Quiet then Cool; the device's command
        list is Cool, Sleep, Quiet, and that is what the picker shows."""
        entity, _ = _flat_entity(["Quiet", "Cool"])
        assert entity.preset_modes == ["Cool", "Quiet"]

    def test_preset_modes_drop_names_with_no_command(self):
        entity, _ = _flat_entity(["Sleep", "Ghost"])
        assert entity.preset_modes == ["Sleep"]

    def test_only_ghost_names_read_as_no_presets(self):
        entity, _ = _flat_entity(["Ghost"])
        assert entity.preset_modes is None
        assert not (int(entity.supported_features)
                    & ClimateEntityFeature.PRESET_MODE)

    def test_preset_mode_is_none_before_any_selection(self):
        entity, _ = _flat_entity(["Sleep"])
        assert entity.preset_mode is None


class TestSetPresetMode:
    @pytest.mark.asyncio
    async def test_flat_send_and_attribute(self):
        entity, mgr = _flat_entity(["Sleep"])
        await entity.async_set_preset_mode("Sleep")
        # The ordinary device send path -- the same call the row's TEST
        # button makes, which is what stamps the Mirror row via
        # record_send. A bespoke send here would go unlogged.
        mgr.async_send_command.assert_awaited_once_with("dev-flat", "c-sleep")
        assert entity.preset_mode == "Sleep"

    @pytest.mark.asyncio
    async def test_preset_always_sends_even_while_off(self):
        """Unlike the matrix dial setters, which store and wait: picking
        a preset is an explicit go-there (plan 3.3)."""
        entity, mgr = _flat_entity(["Sleep"])
        assert entity.hvac_mode == HVACMode.OFF
        await entity.async_set_preset_mode("Sleep")
        mgr.async_send_command.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unstarred_command_sends_nothing(self):
        entity, mgr = _flat_entity(["Sleep"])
        await entity.async_set_preset_mode("Quiet")
        mgr.async_send_command.assert_not_awaited()
        assert entity.preset_mode is None

    @pytest.mark.asyncio
    async def test_unknown_name_sends_nothing(self):
        entity, mgr = _flat_entity(["Sleep"])
        await entity.async_set_preset_mode("Ghost")
        mgr.async_send_command.assert_not_awaited()
        assert entity.preset_mode is None

    @pytest.mark.asyncio
    async def test_matrix_state_row_moves_the_cell_readout(self):
        entity, mgr = await _matrix_entity([STATE_ROW])
        await entity.async_set_preset_mode(STATE_ROW)
        mgr.async_send_command.assert_awaited_once_with(
            "dev-matrix", "c-state"
        )
        assert entity.preset_mode == STATE_ROW
        assert entity.extra_state_attributes["matrix_cell"] == STATE_ROW

    @pytest.mark.asyncio
    async def test_preset_does_not_move_the_dial(self):
        """No parsing of the display grammar back into mode/fan/temp:
        the dial stays where it was."""
        entity, _ = await _matrix_entity([STATE_ROW])
        entity._target_temperature = 26.0
        entity._fan_mode = "auto"
        await entity.async_set_preset_mode(STATE_ROW)
        assert entity.target_temperature == 26.0
        assert entity.fan_mode == "auto"


class TestPresetModeClears:
    @pytest.mark.asyncio
    async def test_set_hvac_mode_clears(self):
        entity, _ = _flat_entity(["Sleep"])
        await entity.async_set_preset_mode("Sleep")
        await entity.async_set_hvac_mode(HVACMode.COOL)
        assert entity.preset_mode is None

    @pytest.mark.asyncio
    async def test_set_temperature_clears(self):
        entity, _ = _flat_entity(["Sleep"])
        entity._device.entity_config.temperature_presets = [22]
        await entity.async_set_preset_mode("Sleep")
        await entity.async_set_temperature(temperature=22)
        assert entity.preset_mode is None

    @pytest.mark.asyncio
    async def test_set_temperature_without_a_target_does_not_clear(self):
        """The no-op early return is not a state change."""
        entity, _ = _flat_entity(["Sleep"])
        await entity.async_set_preset_mode("Sleep")
        await entity.async_set_temperature()
        assert entity.preset_mode == "Sleep"

    @pytest.mark.asyncio
    async def test_set_fan_mode_clears(self):
        entity, _ = _flat_entity(["Sleep"])
        await entity.async_set_preset_mode("Sleep")
        await entity.async_set_fan_mode("low")
        assert entity.preset_mode is None

    @pytest.mark.asyncio
    async def test_set_swing_mode_clears_on_matrix(self):
        entity, _ = await _matrix_entity([STATE_ROW])
        await entity.async_set_preset_mode(STATE_ROW)
        await entity.async_set_swing_mode("swing")
        assert entity.preset_mode is None

    @pytest.mark.asyncio
    async def test_turn_on_clears(self):
        entity, _ = _flat_entity(["Sleep"])
        await entity.async_set_preset_mode("Sleep")
        await entity.async_turn_on()
        assert entity.preset_mode is None

    @pytest.mark.asyncio
    async def test_turn_off_clears(self):
        entity, _ = _flat_entity(["Sleep"])
        await entity.async_set_preset_mode("Sleep")
        await entity.async_turn_off()
        assert entity.preset_mode is None

    @pytest.mark.asyncio
    async def test_matrix_hvac_mode_clears(self):
        entity, _ = await _matrix_entity([STATE_ROW])
        await entity.async_set_preset_mode(STATE_ROW)
        await entity.async_set_hvac_mode(HVACMode.COOL)
        assert entity.preset_mode is None


class TestWebsocket:
    @staticmethod
    def _conn():
        conn = MagicMock()
        conn.send_result = MagicMock()
        conn.send_error = MagicMock()
        return conn

    @staticmethod
    def _msg(**over):
        msg = {
            "id": 1,
            "type": "hair/device/star",
            "device_id": "dev-flat",
            "command_name": "Sleep",
            "starred": True,
        }
        msg.update(over)
        return msg

    @pytest.mark.asyncio
    async def test_returns_the_updated_list(self, fake_hass):
        manager = MagicMock()
        manager.async_set_starred = AsyncMock(return_value=["Sleep"])
        fake_hass.data[DOMAIN] = {
            "entry-1": {"device_manager": manager},
        }
        conn = self._conn()
        await ws_device_star(fake_hass, conn, self._msg())
        manager.async_set_starred.assert_awaited_once_with(
            "dev-flat", "Sleep", True
        )
        conn.send_result.assert_called_once_with(1, {"starred": ["Sleep"]})

    @pytest.mark.asyncio
    async def test_unstar_passes_the_flag_through(self, fake_hass):
        manager = MagicMock()
        manager.async_set_starred = AsyncMock(return_value=[])
        fake_hass.data[DOMAIN] = {"entry-1": {"device_manager": manager}}
        conn = self._conn()
        await ws_device_star(fake_hass, conn, self._msg(starred=False))
        manager.async_set_starred.assert_awaited_once_with(
            "dev-flat", "Sleep", False
        )
        conn.send_result.assert_called_once_with(1, {"starred": []})

    @pytest.mark.asyncio
    async def test_unknown_target_errors(self, fake_hass):
        manager = MagicMock()
        manager.async_set_starred = AsyncMock(return_value=None)
        fake_hass.data[DOMAIN] = {"entry-1": {"device_manager": manager}}
        conn = self._conn()
        await ws_device_star(fake_hass, conn, self._msg(command_name="Ghost"))
        conn.send_result.assert_not_called()
        assert conn.send_error.call_args[0][1] == "not_found"

    @pytest.mark.asyncio
    async def test_not_configured_errors(self, fake_hass):
        conn = self._conn()
        await ws_device_star(fake_hass, conn, self._msg())
        conn.send_result.assert_not_called()
        assert conn.send_error.call_args[0][1] == "not_configured"
