"""Tests for the device manager."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import homeassistant.components.infrared as _infrared_mod
import pytest

from custom_components.hair.const import (
    SEND_REPEAT_GAP,
    CommandCategory,
    DeviceType,
)
from custom_components.hair.device_manager import (
    DeviceManager,
    category_for_command_name,
)
from custom_components.hair.entity_factory import EntityFactory
from custom_components.hair.event_parser import EventParser
from custom_components.hair.models import IRCommand, IRDevice, IRTrigger
from custom_components.hair.pronto_validator import validate_pronto
from custom_components.hair.storage import HAIRStore
from custom_components.hair.trigger_manager import TriggerManager


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
        # Don't await async_load; the fake returns None synchronously for tests.
        store._loaded = True
        factory = EntityFactory(fake_hass)
        # Stub registry interactions used during create.
        with patch(
            "custom_components.hair.device_manager.dr.async_get",
            return_value=MagicMock(
                async_get_or_create=MagicMock(return_value=MagicMock(id="ha-dev-1")),
                async_get_device=MagicMock(return_value=None),
                async_remove_device=MagicMock(),
            ),
        ):
            yield DeviceManager(fake_hass, store, factory, "entry-1")


@pytest.mark.asyncio
async def test_send_command_uses_decoded_when_present(manager):
    """TX prefers encode-from-decoded when the command carries decoded
    fields and is not pinned to captured timings."""
    cmd = IRCommand(
        id="c1",
        name="Power",
        protocol="PRONTO",
        code="0000 006D 0002 0000 0020 0040 0020 0040",
        decoded_protocol="NEC",
        decoded_address=0xFB04,
        decoded_command=0x08,
        decoded_fingerprint="NEC:0xfb04:0x08",
    )
    dev = IRDevice(name="TV", emitter_entity_ids=["infrared.e"], commands=[cmd])
    manager._store.add_device(dev)
    sentinel = object()
    with patch.object(
        _infrared_mod, "async_send_command", AsyncMock()
    ) as ir_send, patch(
        "custom_components.hair.ir_command.build_decoded_command",
        return_value=sentinel,
    ) as bdc, patch(
        "custom_components.hair.ir_command.build_command"
    ) as bc:
        await manager.async_send_command(dev.id, "c1")
    bdc.assert_called_once()
    bc.assert_not_called()
    ir_send.assert_awaited_once()
    assert ir_send.call_args[0][2] is sentinel


@pytest.mark.asyncio
async def test_send_command_falls_back_when_tx_force_raw(manager):
    cmd = IRCommand(
        id="c1",
        name="Power",
        protocol="PRONTO",
        code="0000 006D 0002 0000 0020 0040 0020 0040",
        decoded_fingerprint="NEC:0xfb04:0x08",
        decoded_protocol="NEC",
        decoded_address=0xFB04,
        decoded_command=0x08,
        tx_force_raw=True,
    )
    dev = IRDevice(name="TV", emitter_entity_ids=["infrared.e"], commands=[cmd])
    manager._store.add_device(dev)
    fallback = object()
    with patch.object(
        _infrared_mod, "async_send_command", AsyncMock()
    ) as ir_send, patch(
        "custom_components.hair.ir_command.build_decoded_command"
    ) as bdc, patch(
        "custom_components.hair.ir_command.build_command", return_value=fallback
    ):
        await manager.async_send_command(dev.id, "c1")
    bdc.assert_not_called()
    assert ir_send.call_args[0][2] is fallback


@pytest.mark.asyncio
async def test_send_command_repeats_whole_frame(manager):
    """send_count loops the whole built frame across every emitter."""
    cmd = IRCommand(
        id="c1", name="Power", protocol="PRONTO",
        code="0000 006D 0002 0000 0020 0040 0020 0040",
        send_count=3,
    )
    dev = IRDevice(
        name="TV",
        emitter_entity_ids=["infrared.a", "infrared.b"],
        commands=[cmd],
    )
    manager._store.add_device(dev)
    with patch.object(
        _infrared_mod, "async_send_command", AsyncMock()
    ) as ir_send, patch(
        "custom_components.hair.device_manager.asyncio.sleep", AsyncMock()
    ) as sleep:
        await manager.async_send_command(dev.id, "c1")
    # 3 repeats x 2 emitters; a gap between each repeat (not after the last).
    assert ir_send.await_count == 6
    # Sleeps: 2 inter-frame SEND_REPEAT_GAP pauses, plus 5 transmit-gate
    # staggers -- the send order alternates a,b | a,b | a,b, so every one
    # of the 5 emitter CHANGES inserts a quiet gap (see tx_gate). The
    # patch on device_manager.asyncio.sleep is the shared asyncio module,
    # so the gate's sleeps land in the same mock.
    gaps = [c.args[0] for c in sleep.await_args_list]
    assert gaps.count(SEND_REPEAT_GAP) == 2
    assert len(gaps) == 7


@pytest.mark.asyncio
async def test_send_command_default_sends_once(manager):
    """Default send_count=1 sends once per emitter, with no inter-frame gap."""
    cmd = IRCommand(
        id="c1", name="Power", protocol="PRONTO",
        code="0000 006D 0002 0000 0020 0040 0020 0040",
    )
    dev = IRDevice(name="TV", emitter_entity_ids=["infrared.a"], commands=[cmd])
    manager._store.add_device(dev)
    with patch.object(
        _infrared_mod, "async_send_command", AsyncMock()
    ) as ir_send, patch(
        "custom_components.hair.device_manager.asyncio.sleep", AsyncMock()
    ) as sleep:
        await manager.async_send_command(dev.id, "c1")
    assert ir_send.await_count == 1
    assert sleep.await_count == 0


@pytest.mark.asyncio
async def test_set_command_tx_force_raw(manager):
    dev = IRDevice(name="TV", commands=[IRCommand(id="c1", name="Power")])
    manager._store.add_device(dev)
    assert await manager.async_set_command_tx_force_raw(dev.id, "c1", True) is True
    assert manager._store.get_device(dev.id).commands[0].tx_force_raw is True
    assert (
        await manager.async_set_command_tx_force_raw(dev.id, "missing", True)
        is False
    )
    assert (
        await manager.async_set_command_tx_force_raw("nope", "c1", True) is False
    )


@pytest.mark.asyncio
async def test_create_and_remove_device(manager, mock_device: IRDevice):
    with patch(
        "custom_components.hair.device_manager.dr.async_get",
        return_value=MagicMock(
            async_get_or_create=MagicMock(return_value=MagicMock(id="ha-dev-1")),
            async_get_device=MagicMock(return_value=MagicMock(id="ha-dev-1")),
            async_remove_device=MagicMock(),
        ),
    ):
        await manager.async_create_device(mock_device)
        assert manager.get_device(mock_device.id) is not None

        removed = await manager.async_remove_device(mock_device.id)
        assert removed is True
        assert manager.get_device(mock_device.id) is None


@pytest.mark.asyncio
async def test_add_command_auto_maps_for_tv(manager):
    device = IRDevice(
        name="TV", device_type=DeviceType.MEDIA_PLAYER, emitter_entity_ids=["infrared.a"]
    )
    with patch(
        "custom_components.hair.device_manager.dr.async_get",
        return_value=MagicMock(
            async_get_or_create=MagicMock(return_value=MagicMock(id="x")),
            async_get_device=MagicMock(return_value=None),
        ),
    ):
        await manager.async_create_device(device)
    await manager.async_add_command(
        device.id,
        IRCommand(name="Volume Up", protocol="NEC", code="0x1"),
    )
    refreshed = manager.get_device(device.id)
    assert "volume_up" in refreshed.entity_config.command_mapping
    assert refreshed.entity_config.command_mapping["volume_up"] == "Volume Up"


@pytest.mark.asyncio
async def test_add_command_populates_ac_modes(manager):
    device = IRDevice(
        name="AC", device_type=DeviceType.AC, emitter_entity_ids=["infrared.a"]
    )
    with patch(
        "custom_components.hair.device_manager.dr.async_get",
        return_value=MagicMock(
            async_get_or_create=MagicMock(return_value=MagicMock(id="x")),
            async_get_device=MagicMock(return_value=None),
        ),
    ):
        await manager.async_create_device(device)
    await manager.async_add_command(
        device.id, IRCommand(name="Mode: Cool", protocol="NEC", code="0x1")
    )
    await manager.async_add_command(
        device.id, IRCommand(name="Fan: High", protocol="NEC", code="0x2")
    )
    refreshed = manager.get_device(device.id)
    assert "cool" in (refreshed.entity_config.hvac_modes or [])
    assert "high" in (refreshed.entity_config.fan_modes or [])


@pytest.mark.asyncio
async def test_remove_command_clears_mapping(manager):
    device = IRDevice(
        name="TV", device_type=DeviceType.MEDIA_PLAYER, emitter_entity_ids=["infrared.a"]
    )
    with patch(
        "custom_components.hair.device_manager.dr.async_get",
        return_value=MagicMock(
            async_get_or_create=MagicMock(return_value=MagicMock(id="x")),
            async_get_device=MagicMock(return_value=None),
        ),
    ):
        await manager.async_create_device(device)
    cmd = IRCommand(name="Volume Up", protocol="NEC", code="0x1")
    await manager.async_add_command(device.id, cmd)

    refreshed = manager.get_device(device.id)
    cmd_id = refreshed.commands[0].id

    await manager.async_remove_command(device.id, cmd_id)
    refreshed = manager.get_device(device.id)
    assert "volume_up" not in refreshed.entity_config.command_mapping


@pytest.mark.asyncio
async def test_send_command_calls_infrared_helper(manager, mock_device: IRDevice):
    """Verify async_send_command() calls infrared.async_send_command with a built Command."""
    mock_ir_send = AsyncMock()
    with (
        patch(
            "custom_components.hair.device_manager.dr.async_get",
            return_value=MagicMock(
                async_get_or_create=MagicMock(return_value=MagicMock(id="x")),
                async_get_device=MagicMock(return_value=None),
            ),
        ),
    ):
        await manager.async_create_device(mock_device)

    import sys
    ir_mod = sys.modules["homeassistant.components.infrared"]
    orig = ir_mod.async_send_command
    ir_mod.async_send_command = mock_ir_send
    try:
        await manager.async_send_command(mock_device.id, "cmd-1")
    finally:
        ir_mod.async_send_command = orig

    mock_ir_send.assert_awaited_once()
    call_args = mock_ir_send.call_args
    assert call_args[0][0] is manager._hass  # hass
    assert call_args[0][1] == "infrared.test_emitter"  # entity_id
    ir_cmd = call_args[0][2]  # the Command object
    assert hasattr(ir_cmd, "get_raw_timings")


def test_category_for_command_name():
    assert category_for_command_name("Power") == CommandCategory.POWER
    assert category_for_command_name("Volume Up") == CommandCategory.VOLUME
    assert category_for_command_name("Mute") == CommandCategory.VOLUME
    assert category_for_command_name("Channel Up") == CommandCategory.CHANNEL
    assert category_for_command_name("Mode: Cool") == CommandCategory.MODE
    assert category_for_command_name("Fan: High") == CommandCategory.FAN_SPEED
    assert category_for_command_name("Random") == CommandCategory.CUSTOM


# ---------------------------------------------------------------------------
# async_update_command -- device-command editor + rename (F5/F6)
# ---------------------------------------------------------------------------

# Two structurally valid Prontos with distinct S/L fingerprints (all-short
# vs all-long bursts), so an edit between them moves the matcher key.
_CODE_SHORT = "0000 006D 0002 0000 0010 0010 0010 0010"
_CODE_LONG = "0000 006D 0002 0000 0040 0040 0040 0040"


def _fp(code: str, raw=None) -> str:
    return EventParser.signal_fingerprint("PRONTO", code, raw)


class TestUpdateCommand:
    """device_manager.async_update_command edits a command in place."""

    @pytest.mark.asyncio
    async def test_code_edit_recomputes_identity_and_index(self, manager):
        manager._entity_factory.async_update_entities = AsyncMock()
        cmd = IRCommand(id="c1", name="Power", protocol="PRONTO", code=_CODE_SHORT)
        dev = IRDevice(name="TV", commands=[cmd])
        manager._store.add_device(dev)
        old_fp = _fp(_CODE_SHORT)
        assert manager._store.match_command(None, old_fp, None) == (dev.id, "c1")

        with patch(
            "custom_components.hair.protocol_decode.try_decode_identity",
            return_value=None,
        ):
            result = await manager.async_update_command(
                dev.id, "c1", pronto=_CODE_LONG
            )

        assert result["success"] is True
        updated = manager._store.get_device(dev.id).get_command("c1")
        assert updated.code == validate_pronto(_CODE_LONG).normalized
        # The new code is now the known command...
        new_fp = _fp(updated.code, updated.raw_timings)
        assert manager._store.match_command(
            None, new_fp, updated.byte_hash
        ) == (dev.id, "c1")
        # ...and the old code no longer resolves to anything.
        assert manager._store.match_command(None, old_fp, None) is None

    @pytest.mark.asyncio
    async def test_rename_cascades_mappings_two_features(self, manager):
        manager._entity_factory.async_update_entities = AsyncMock()
        cmd = IRCommand(id="c1", name="Power", protocol="PRONTO", code=_CODE_SHORT)
        dev = IRDevice(name="TV", commands=[cmd])
        # Two features mapped to the one command -- both must cascade.
        dev.entity_config.command_mapping = {
            "power_toggle": "Power",
            "turn_on": "Power",
        }
        manager._store.add_device(dev)

        result = await manager.async_update_command(
            dev.id, "c1", name="Power Button"
        )
        assert result["success"] is True
        assert result["mappings_updated"] == 2
        refreshed = manager._store.get_device(dev.id)
        assert refreshed.get_command("c1").name == "Power Button"
        assert refreshed.entity_config.command_mapping == {
            "power_toggle": "Power Button",
            "turn_on": "Power Button",
        }

    @pytest.mark.asyncio
    async def test_rename_rejects_duplicate_name(self, manager):
        manager._entity_factory.async_update_entities = AsyncMock()
        dev = IRDevice(
            name="TV",
            commands=[
                IRCommand(id="c1", name="Power", protocol="PRONTO",
                          code=_CODE_SHORT),
                IRCommand(id="c2", name="Mute", protocol="PRONTO",
                          code=_CODE_LONG),
            ],
        )
        manager._store.add_device(dev)

        result = await manager.async_update_command(dev.id, "c1", name="Mute")
        assert result["success"] is False
        assert result["code"] == "duplicate_name"
        assert manager._store.get_device(dev.id).get_command("c1").name == "Power"

    @pytest.mark.asyncio
    async def test_rename_leaves_triggers_untouched(self, manager):
        manager._entity_factory.async_update_entities = AsyncMock()
        cmd = IRCommand(id="c1", name="Power", protocol="PRONTO", code=_CODE_SHORT)
        dev = IRDevice(name="TV", commands=[cmd])
        manager._store.add_device(dev)
        trig = IRTrigger(
            name="TV Power",
            signal_fingerprint=_fp(_CODE_SHORT),
            protocol="PRONTO",
            code=_CODE_SHORT,
        )
        manager._store.add_trigger(trig)
        tm = TriggerManager(manager._hass, manager._store)

        result = await manager.async_update_command(
            dev.id, "c1", name="Power Button", trigger_manager=tm
        )
        assert result["success"] is True
        assert result["triggers"] == {"rewired": [], "skipped": []}
        assert trig.signal_fingerprint == _fp(_CODE_SHORT)
        assert trig.code == _CODE_SHORT

    @pytest.mark.asyncio
    async def test_code_edit_names_rewired_trigger(self, manager):
        manager._entity_factory.async_update_entities = AsyncMock()
        cmd = IRCommand(id="c1", name="Power", protocol="PRONTO", code=_CODE_SHORT)
        dev = IRDevice(name="TV", commands=[cmd])
        manager._store.add_device(dev)
        trig = IRTrigger(
            name="TV Power",
            signal_fingerprint=_fp(_CODE_SHORT),
            protocol="PRONTO",
            code=_CODE_SHORT,
        )
        manager._store.add_trigger(trig)
        tm = TriggerManager(manager._hass, manager._store)

        with patch(
            "custom_components.hair.protocol_decode.try_decode_identity",
            return_value=None,
        ):
            result = await manager.async_update_command(
                dev.id, "c1", pronto=_CODE_LONG, trigger_manager=tm
            )

        assert result["success"] is True
        assert result["triggers"]["rewired"] == ["TV Power"]
        updated = manager._store.get_device(dev.id).get_command("c1")
        assert trig.signal_fingerprint == _fp(updated.code, updated.raw_timings)

    @pytest.mark.asyncio
    async def test_not_found_errors(self, manager):
        manager._entity_factory.async_update_entities = AsyncMock()
        missing_device = await manager.async_update_command("nope", "c1", name="X")
        assert missing_device["code"] == "device_not_found"

        dev = IRDevice(name="TV", commands=[IRCommand(id="c1", name="Power")])
        manager._store.add_device(dev)
        missing_cmd = await manager.async_update_command(
            dev.id, "missing", name="X"
        )
        assert missing_cmd["code"] == "command_not_found"

    @pytest.mark.asyncio
    async def test_sets_send_count(self, manager):
        manager._entity_factory.async_update_entities = AsyncMock()
        cmd = IRCommand(id="c1", name="Power", protocol="PRONTO",
                        code=_CODE_SHORT)
        dev = IRDevice(name="TV", commands=[cmd])
        manager._store.add_device(dev)
        result = await manager.async_update_command(dev.id, "c1", send_count=4)
        assert result["success"] is True
        assert manager._store.get_device(dev.id).get_command("c1").send_count == 4

    @pytest.mark.asyncio
    async def test_clamps_send_count(self, manager):
        manager._entity_factory.async_update_entities = AsyncMock()
        cmd = IRCommand(id="c1", name="Power", protocol="PRONTO",
                        code=_CODE_SHORT)
        dev = IRDevice(name="TV", commands=[cmd])
        manager._store.add_device(dev)
        await manager.async_update_command(dev.id, "c1", send_count=99)
        assert manager._store.get_device(dev.id).get_command("c1").send_count == 10
        await manager.async_update_command(dev.id, "c1", send_count=0)
        assert manager._store.get_device(dev.id).get_command("c1").send_count == 1


class TestApplyAutoMap:
    """async_apply_auto_map: the action mapping the assign path skips."""

    @pytest.mark.asyncio
    async def test_maps_standard_command(self, manager):
        manager._entity_factory.async_update_entities = AsyncMock()
        # Mimic an assign: model add_command, with no auto-map applied.
        dev = IRDevice(name="TV", device_type=DeviceType.MEDIA_PLAYER)
        dev.add_command(IRCommand(id="c1", name="Volume Up"))
        manager._store.add_device(dev)
        assert dev.entity_config.command_mapping == {}

        await manager.async_apply_auto_map(dev.id, "c1")
        mapping = manager._store.get_device(dev.id).entity_config.command_mapping
        assert mapping.get("volume_up") == "Volume Up"

    @pytest.mark.asyncio
    async def test_registers_ac_fan_mode(self, manager):
        manager._entity_factory.async_update_entities = AsyncMock()
        dev = IRDevice(name="AC", device_type=DeviceType.AC)
        dev.add_command(IRCommand(id="c1", name="Fan: Auto"))
        manager._store.add_device(dev)

        await manager.async_apply_auto_map(dev.id, "c1")
        refreshed = manager._store.get_device(dev.id)
        assert refreshed.entity_config.command_mapping.get("fan_auto") == "Fan: Auto"
        assert "auto" in (refreshed.entity_config.fan_modes or [])

    @pytest.mark.asyncio
    async def test_maps_speed_level(self, manager):
        manager._entity_factory.async_update_entities = AsyncMock()
        dev = IRDevice(name="Fan", device_type=DeviceType.FAN)
        dev.add_command(IRCommand(id="c1", name="Speed 3"))
        manager._store.add_device(dev)

        await manager.async_apply_auto_map(dev.id, "c1")
        mapping = manager._store.get_device(dev.id).entity_config.command_mapping
        assert mapping.get("speed_3") == "Speed 3"

    @pytest.mark.asyncio
    async def test_noop_for_custom_name(self, manager):
        manager._entity_factory.async_update_entities = AsyncMock()
        dev = IRDevice(name="TV", device_type=DeviceType.MEDIA_PLAYER)
        dev.add_command(IRCommand(id="c1", name="My Macro"))
        manager._store.add_device(dev)

        await manager.async_apply_auto_map(dev.id, "c1")
        assert (
            manager._store.get_device(dev.id).entity_config.command_mapping == {}
        )


# --- Temp N auto-map (v0.6.1, GH #45) ---------------------------------------


def _mock_device_registry():
    return patch(
        "custom_components.hair.device_manager.dr.async_get",
        return_value=MagicMock(
            async_get_or_create=MagicMock(return_value=MagicMock(id="x")),
            async_get_device=MagicMock(return_value=None),
        ),
    )


@pytest.mark.asyncio
async def test_temp_commands_auto_map_and_derive_presets(manager):
    """"Temp 24" maps to temp_24 and registers the preset, sorted."""
    device = IRDevice(
        name="AC", device_type=DeviceType.AC, emitter_entity_ids=["infrared.a"]
    )
    with _mock_device_registry():
        await manager.async_create_device(device)
    for name in ("Temp 24", "Temp: 22", "temperature 26"):
        await manager.async_add_command(
            device.id, IRCommand(name=name, protocol="NEC", code="0x1")
        )
    refreshed = manager.get_device(device.id)
    mapping = refreshed.entity_config.command_mapping
    assert mapping["temp_24"] == "Temp 24"
    assert mapping["temp_22"] == "Temp: 22"
    assert mapping["temp_26"] == "temperature 26"
    # Presets deduped and sorted; these drive the thermostat min/max,
    # so a metric user's 16..30 set behaves as Celsius end to end.
    assert refreshed.entity_config.temperature_presets == [22, 24, 26]


@pytest.mark.asyncio
async def test_temp_pattern_ignores_non_ac_devices(manager):
    device = IRDevice(
        name="TV",
        device_type=DeviceType.MEDIA_PLAYER,
        emitter_entity_ids=["infrared.a"],
    )
    with _mock_device_registry():
        await manager.async_create_device(device)
    await manager.async_add_command(
        device.id, IRCommand(name="Temp 24", protocol="NEC", code="0x1")
    )
    refreshed = manager.get_device(device.id)
    assert "temp_24" not in refreshed.entity_config.command_mapping
    assert refreshed.entity_config.temperature_presets is None


@pytest.mark.asyncio
async def test_temp_preset_deduplicates(manager):
    device = IRDevice(
        name="AC", device_type=DeviceType.AC, emitter_entity_ids=["infrared.a"]
    )
    with _mock_device_registry():
        await manager.async_create_device(device)
    await manager.async_add_command(
        device.id, IRCommand(name="Temp 24", protocol="NEC", code="0x1")
    )
    await manager.async_add_command(
        device.id, IRCommand(name="TEMP 24", protocol="NEC", code="0x2")
    )
    refreshed = manager.get_device(device.id)
    assert refreshed.entity_config.temperature_presets == [24]


@pytest.mark.asyncio
async def test_removing_temp_command_retires_preset(manager):
    device = IRDevice(
        name="AC", device_type=DeviceType.AC, emitter_entity_ids=["infrared.a"]
    )
    with _mock_device_registry():
        await manager.async_create_device(device)
    await manager.async_add_command(
        device.id, IRCommand(name="Temp 24", protocol="NEC", code="0x1")
    )
    await manager.async_add_command(
        device.id, IRCommand(name="Temp 26", protocol="NEC", code="0x2")
    )
    refreshed = manager.get_device(device.id)
    target = next(
        c for c in refreshed.commands if c.name == "Temp 24"
    )
    await manager.async_remove_command(device.id, target.id)
    refreshed = manager.get_device(device.id)
    assert "temp_24" not in refreshed.entity_config.command_mapping
    assert refreshed.entity_config.temperature_presets == [26]
    # Removing the last one clears the feature entirely (None, not []).
    target = next(c for c in refreshed.commands if c.name == "Temp 26")
    await manager.async_remove_command(device.id, target.id)
    refreshed = manager.get_device(device.id)
    assert refreshed.entity_config.temperature_presets is None
