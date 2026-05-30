"""Tests for the HAIR data models."""
from __future__ import annotations

from custom_components.hair.const import (
    CaptureProviderType,
    CommandCategory,
    CommandSource,
    DeviceType,
)
from custom_components.hair.models import (
    CaptureResult,
    EntityConfig,
    IRCommand,
    IRDevice,
)


def test_command_round_trip():
    cmd = IRCommand(
        name="Power",
        category=CommandCategory.POWER,
        source=CommandSource.CAPTURED,
        protocol="NEC",
        code="0xABCD",
        raw_timings=[9000, -4500, 560],
        frequency=38000,
        repeat_count=2,
    )
    restored = IRCommand.from_dict(cmd.to_dict())
    assert restored.name == cmd.name
    assert restored.protocol == cmd.protocol
    assert restored.code == cmd.code
    assert restored.raw_timings == cmd.raw_timings
    assert restored.frequency == cmd.frequency
    assert restored.repeat_count == cmd.repeat_count
    assert restored.category == CommandCategory.POWER


def test_device_round_trip(mock_device: IRDevice):
    restored = IRDevice.from_dict(mock_device.to_dict())
    assert restored.id == mock_device.id
    assert restored.name == mock_device.name
    assert restored.device_type == mock_device.device_type
    assert restored.manufacturer == mock_device.manufacturer
    assert len(restored.commands) == len(mock_device.commands)
    assert restored.commands[0].name == mock_device.commands[0].name
    assert restored.entity_config.command_mapping == (
        mock_device.entity_config.command_mapping
    )


def test_device_command_helpers(mock_device: IRDevice):
    assert mock_device.get_command("cmd-1") is not None
    assert mock_device.get_command("missing") is None
    assert mock_device.get_command_by_name("power").name == "Power"
    assert mock_device.get_command_by_name("POWER").name == "Power"
    assert mock_device.get_command_by_name("missing") is None


def test_device_add_replace_remove():
    device = IRDevice(name="x", device_type=DeviceType.MEDIA_PLAYER)
    cmd1 = IRCommand(name="Power", protocol="NEC", code="0x1")
    device.add_command(cmd1)
    assert len(device.commands) == 1

    # Adding a command with the same name replaces.
    cmd2 = IRCommand(name="power", protocol="NEC", code="0x2")
    device.add_command(cmd2)
    assert len(device.commands) == 1
    assert device.commands[0].code == "0x2"

    # ID is preserved across replace.
    cmd3 = IRCommand(name="Power", protocol="NEC", code="0x3")
    device.replace_command(device.commands[0].id, cmd3)
    assert device.commands[0].code == "0x3"
    assert device.commands[0].id == cmd2.id

    # Remove by id.
    assert device.remove_command(device.commands[0].id) is True
    assert len(device.commands) == 0
    assert device.remove_command("missing") is False


def test_reorder_commands_happy_path():
    device = IRDevice(name="x", device_type=DeviceType.MEDIA_PLAYER)
    cmd_a = IRCommand(name="A", protocol="NEC", code="0x1")
    cmd_b = IRCommand(name="B", protocol="NEC", code="0x2")
    cmd_c = IRCommand(name="C", protocol="NEC", code="0x3")
    device.add_command(cmd_a)
    device.add_command(cmd_b)
    device.add_command(cmd_c)
    original_updated_at = device.updated_at

    device.reorder_commands([cmd_c.id, cmd_a.id, cmd_b.id])

    assert [c.id for c in device.commands] == [cmd_c.id, cmd_a.id, cmd_b.id]
    assert device.updated_at != original_updated_at


def test_reorder_commands_empty_device_with_empty_list():
    device = IRDevice(name="x", device_type=DeviceType.MEDIA_PLAYER)
    # No-op on a device with no commands.
    device.reorder_commands([])
    assert device.commands == []


def test_reorder_commands_duplicate_id_raises():
    device = IRDevice(name="x", device_type=DeviceType.MEDIA_PLAYER)
    cmd = IRCommand(name="A", protocol="NEC", code="0x1")
    device.add_command(cmd)
    original_order = list(device.commands)

    import pytest

    with pytest.raises(ValueError, match="Duplicate"):
        device.reorder_commands([cmd.id, cmd.id])

    # Validation failure must not mutate state.
    assert device.commands == original_order


def test_reorder_commands_unknown_id_raises():
    device = IRDevice(name="x", device_type=DeviceType.MEDIA_PLAYER)
    cmd = IRCommand(name="A", protocol="NEC", code="0x1")
    device.add_command(cmd)
    original_order = list(device.commands)

    import pytest

    with pytest.raises(ValueError, match="unknown"):
        device.reorder_commands([cmd.id, "ghost"])

    assert device.commands == original_order


def test_reorder_commands_missing_id_raises():
    device = IRDevice(name="x", device_type=DeviceType.MEDIA_PLAYER)
    cmd_a = IRCommand(name="A", protocol="NEC", code="0x1")
    cmd_b = IRCommand(name="B", protocol="NEC", code="0x2")
    device.add_command(cmd_a)
    device.add_command(cmd_b)
    original_order = list(device.commands)

    import pytest

    with pytest.raises(ValueError, match="missing"):
        device.reorder_commands([cmd_a.id])  # cmd_b is missing

    assert device.commands == original_order


def test_capture_result_matches_by_protocol_code():
    a = CaptureResult(protocol="NEC", code="0xABCD", raw_timings=[1])
    b = CaptureResult(protocol="NEC", code="0xABCD", raw_timings=[2])
    c = CaptureResult(protocol="NEC", code="0xDEAD", raw_timings=[1])
    assert a.matches(b)
    assert not a.matches(c)


def test_capture_result_matches_by_raw_timings():
    a = CaptureResult(raw_timings=[9000, -4500, 560, -560, 560])
    b = CaptureResult(raw_timings=[9000, -4500, 560, -560, 560])
    c = CaptureResult(raw_timings=[9000, -4500, 1700, -1700, 560])
    assert a.matches(b)
    assert not a.matches(c)


def test_capture_result_to_command():
    result = CaptureResult(
        protocol="NEC",
        code="0xABCD",
        raw_timings=[1, 2, 3],
        frequency=38000,
    )
    command = result.to_command("Power", CommandCategory.POWER)
    assert command.name == "Power"
    assert command.category == CommandCategory.POWER
    assert command.protocol == "NEC"
    assert command.code == "0xABCD"
    assert command.source == CommandSource.CAPTURED


def test_entity_config_round_trip():
    config = EntityConfig(
        platform="climate",
        command_mapping={"turn_on": "Power On"},
        temperature_presets=[68, 70, 72],
        hvac_modes=["cool", "heat"],
        fan_modes=["low", "high"],
    )
    restored = EntityConfig.from_dict(config.to_dict())
    assert restored.platform == config.platform
    assert restored.command_mapping == config.command_mapping
    assert restored.temperature_presets == config.temperature_presets
    assert restored.hvac_modes == config.hvac_modes
    assert restored.fan_modes == config.fan_modes


def test_provider_enum_round_trip():
    assert CaptureProviderType("esphome") == CaptureProviderType.ESPHOME
    assert str(CaptureProviderType.BROADLINK) == "broadlink"


# ---------------------------------------------------------------------------
# UnknownSignal sl_pattern
# ---------------------------------------------------------------------------

def test_unknown_signal_to_dict_includes_sl_pattern_for_pronto():
    from custom_components.hair.models import UnknownSignal

    sig = UnknownSignal(
        fingerprint="abc123",
        protocol="PRONTO",
        code="0000 006D 0003 0000 0020 0040 0020",
        hit_count=5,
    )
    d = sig.to_dict()
    assert d["sl_pattern"] == "SLS"


def test_unknown_signal_to_dict_no_sl_pattern_for_nec():
    from custom_components.hair.models import UnknownSignal

    sig = UnknownSignal(
        fingerprint="abc123",
        protocol="NEC",
        code="0x1234",
        hit_count=3,
    )
    d = sig.to_dict()
    assert "sl_pattern" not in d


def test_unknown_signal_to_dict_no_sl_pattern_for_raw():
    from custom_components.hair.models import UnknownSignal

    sig = UnknownSignal(
        fingerprint="abc123",
        raw_timings=[9000, -4500, 560, -560],
        hit_count=1,
    )
    d = sig.to_dict()
    assert "sl_pattern" not in d


# ---------------------------------------------------------------------------
# Legacy device type migration
# ---------------------------------------------------------------------------

def test_legacy_device_type_migration():
    """Loading 'tv', 'soundbar', 'projector' from dict produces MEDIA_PLAYER."""
    for legacy_type in ("tv", "soundbar", "projector"):
        data = {"name": "Test", "device_type": legacy_type}
        device = IRDevice.from_dict(data)
        assert device.device_type == DeviceType.MEDIA_PLAYER
