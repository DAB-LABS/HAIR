"""Tests for the HAIR data models."""
from __future__ import annotations

import pytest

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
    UnknownSignal,
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


def test_command_send_count_round_trip():
    cmd = IRCommand(name="Power", send_count=3)
    assert IRCommand.from_dict(cmd.to_dict()).send_count == 3
    # Default and legacy records (no key) fall back to 1.
    assert IRCommand(name="X").send_count == 1
    assert IRCommand.from_dict({"name": "X"}).send_count == 1


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


def test_device_power_sensor_round_trip():
    device = IRDevice(
        name="AC",
        device_type=DeviceType.AC,
        power_sensor_entity_id="sensor.ac_plug_power",
        power_off_below_w=5.0,
        power_on_above_w=10.0,
    )
    restored = IRDevice.from_dict(device.to_dict())
    assert restored.power_sensor_entity_id == "sensor.ac_plug_power"
    assert restored.power_off_below_w == 5.0
    assert restored.power_on_above_w == 10.0


def test_device_power_sensor_absent_defaults_none(mock_device: IRDevice):
    # mock_device never sets the power fields, from_dict on a legacy
    # (pre-power-sensor) record must not error and must resolve to
    # "no power monitoring configured".
    restored = IRDevice.from_dict(mock_device.to_dict())
    assert restored.power_sensor_entity_id is None
    assert restored.power_off_below_w is None
    assert restored.power_on_above_w is None


def test_device_climate_sensors_round_trip():
    device = IRDevice(
        name="AC",
        device_type=DeviceType.AC,
        temperature_sensor_entity_id="sensor.living_room_temp",
        humidity_sensor_entity_id="sensor.living_room_humidity",
    )
    restored = IRDevice.from_dict(device.to_dict())
    assert restored.temperature_sensor_entity_id == "sensor.living_room_temp"
    assert restored.humidity_sensor_entity_id == "sensor.living_room_humidity"


def test_device_climate_sensors_absent_defaults_none(mock_device: IRDevice):
    # Same legacy-record tolerance as the power sensor above -- a
    # record from before this field existed must not error and must
    # resolve to "no room sensor configured".
    restored = IRDevice.from_dict(mock_device.to_dict())
    assert restored.temperature_sensor_entity_id is None
    assert restored.humidity_sensor_entity_id is None


def test_device_climate_sensors_independent(mock_device: IRDevice):
    # Unlike the power trio, temperature and humidity are not a
    # coupled group -- setting one leaves the other at its default.
    device = IRDevice(
        name="AC",
        device_type=DeviceType.AC,
        temperature_sensor_entity_id="sensor.living_room_temp",
    )
    restored = IRDevice.from_dict(device.to_dict())
    assert restored.temperature_sensor_entity_id == "sensor.living_room_temp"
    assert restored.humidity_sensor_entity_id is None


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


def test_device_clone_preserves_non_id_fields(mock_device: IRDevice):
    clone = mock_device.clone("Test TV (Copy)")
    assert clone.name == "Test TV (Copy)"
    assert clone.device_type == mock_device.device_type
    assert clone.manufacturer == mock_device.manufacturer
    assert clone.model == mock_device.model
    assert clone.emitter_entity_ids == mock_device.emitter_entity_ids
    assert clone.power_sensor_entity_id == mock_device.power_sensor_entity_id
    assert clone.power_off_below_w == mock_device.power_off_below_w
    assert clone.power_on_above_w == mock_device.power_on_above_w
    assert (
        clone.temperature_sensor_entity_id
        == mock_device.temperature_sensor_entity_id
    )
    assert (
        clone.humidity_sensor_entity_id == mock_device.humidity_sensor_entity_id
    )
    assert clone.capture_device_id == mock_device.capture_device_id
    assert clone.capture_provider_type == mock_device.capture_provider_type
    assert clone.database_id == mock_device.database_id
    assert len(clone.commands) == len(mock_device.commands)
    assert clone.entity_config.platform == mock_device.entity_config.platform
    assert (
        clone.entity_config.command_mapping
        == mock_device.entity_config.command_mapping
    )


def test_device_clone_generates_fresh_ids(mock_device: IRDevice):
    clone = mock_device.clone("Test TV (Copy)")
    assert clone.id != mock_device.id
    for src_cmd, clone_cmd in zip(
        mock_device.commands, clone.commands, strict=True
    ):
        assert clone_cmd.id != src_cmd.id
        # Same content though.
        assert clone_cmd.name == src_cmd.name
        assert clone_cmd.category == src_cmd.category
        assert clone_cmd.protocol == src_cmd.protocol
        assert clone_cmd.code == src_cmd.code


def test_device_clone_preserves_power_sensor():
    device = IRDevice(
        name="AC",
        device_type=DeviceType.AC,
        power_sensor_entity_id="sensor.ac_plug_power",
        power_off_below_w=5.0,
        power_on_above_w=10.0,
    )
    clone = device.clone("AC Clone")
    assert clone.power_sensor_entity_id == "sensor.ac_plug_power"
    assert clone.power_off_below_w == 5.0
    assert clone.power_on_above_w == 10.0


def test_device_clone_preserves_climate_sensors():
    device = IRDevice(
        name="AC",
        device_type=DeviceType.AC,
        temperature_sensor_entity_id="sensor.living_room_temp",
        humidity_sensor_entity_id="sensor.living_room_humidity",
    )
    clone = device.clone("AC Clone")
    assert clone.temperature_sensor_entity_id == "sensor.living_room_temp"
    assert clone.humidity_sensor_entity_id == "sensor.living_room_humidity"


def test_device_clone_with_empty_commands():
    device = IRDevice(
        name="Bare device",
        device_type=DeviceType.LIGHT,
        emitter_entity_ids=["infrared.foo"],
    )
    clone = device.clone("Bare device (Copy)")
    assert clone.name == "Bare device (Copy)"
    assert clone.commands == []
    assert clone.emitter_entity_ids == ["infrared.foo"]


def test_device_clone_deep_copies_mutable_fields(mock_device: IRDevice):
    clone = mock_device.clone("Test TV (Copy)")
    # Mutating the clone's lists/dicts must not bleed back into the source.
    clone.emitter_entity_ids.append("infrared.bogus")
    clone.commands.clear()
    clone.entity_config.command_mapping["mode"] = "Bogus"
    assert "infrared.bogus" not in mock_device.emitter_entity_ids
    assert len(mock_device.commands) > 0
    assert "mode" not in mock_device.entity_config.command_mapping


def test_device_clone_round_trips_through_dict(mock_device: IRDevice):
    clone = mock_device.clone("Test TV (Copy)")
    restored = IRDevice.from_dict(clone.to_dict())
    assert restored.name == clone.name
    assert restored.id == clone.id
    assert len(restored.commands) == len(clone.commands)


def test_device_clone_carries_signal_identity_fields():
    """B14: clone preserves byte_hash and the v0.4.0 decoded fields on
    every command, so a clone matches and transmits like its source."""
    src = IRDevice(
        name="Source",
        device_type=DeviceType.MEDIA_PLAYER,
        commands=[
            IRCommand(
                name="Power",
                byte_hash="abc123",
                decoded_protocol="NEC",
                decoded_address=0xFB04,
                decoded_command=0x08,
                decoded_fingerprint="NEC:0xfb04:0x08",
                tx_force_raw=True,
            )
        ],
    )
    clone = src.clone("Copy")
    c = clone.commands[0]
    assert c.id != src.commands[0].id
    assert c.byte_hash == "abc123"
    assert c.decoded_protocol == "NEC"
    assert c.decoded_address == 0xFB04
    assert c.decoded_command == 0x08
    assert c.decoded_fingerprint == "NEC:0xfb04:0x08"
    assert c.tx_force_raw is True


def test_ircommand_decoded_fields_round_trip():
    cmd = IRCommand(
        name="X",
        byte_hash="bh",
        decoded_protocol="NEC",
        decoded_address=0x1234,
        decoded_command=0x56,
        decoded_fingerprint="NEC:0x1234:0x56",
        tx_force_raw=True,
    )
    restored = IRCommand.from_dict(cmd.to_dict())
    assert restored.byte_hash == "bh"
    assert restored.decoded_protocol == "NEC"
    assert restored.decoded_address == 0x1234
    assert restored.decoded_command == 0x56
    assert restored.decoded_fingerprint == "NEC:0x1234:0x56"
    assert restored.tx_force_raw is True


def test_ircommand_decoded_fields_default_none_and_false():
    cmd = IRCommand(name="X")
    assert cmd.decoded_protocol is None
    assert cmd.decoded_address is None
    assert cmd.decoded_command is None
    assert cmd.decoded_fingerprint is None
    assert cmd.tx_force_raw is False
    restored = IRCommand.from_dict({"name": "X"})
    assert restored.decoded_fingerprint is None
    assert restored.tx_force_raw is False


def test_unknown_signal_decoded_fields_round_trip():
    sig = UnknownSignal(
        fingerprint="fp",
        byte_hash="bh",
        decoded_protocol="NEC",
        decoded_address=0x1234,
        decoded_command=0x56,
        decoded_fingerprint="NEC:0x1234:0x56",
    )
    restored = UnknownSignal.from_dict(sig.to_dict())
    assert restored.decoded_protocol == "NEC"
    assert restored.decoded_address == 0x1234
    assert restored.decoded_command == 0x56
    assert restored.decoded_fingerprint == "NEC:0x1234:0x56"


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


# ---------------------------------------------------------------------------
# source field (sniffed / manual) on unknown records
# ---------------------------------------------------------------------------

def test_unknown_signal_source_defaults_to_sniffed():
    from custom_components.hair.models import UnknownSignal

    assert UnknownSignal().source == "sniffed"


def test_unknown_device_source_defaults_to_sniffed():
    from custom_components.hair.models import UnknownDevice

    assert UnknownDevice().source == "sniffed"


def test_unknown_signal_source_round_trip():
    from custom_components.hair.models import UnknownSignal

    sig = UnknownSignal(fingerprint="abc123", source="manual")
    d = sig.to_dict()
    assert d["source"] == "manual"
    assert UnknownSignal.from_dict(d).source == "manual"


def test_unknown_device_source_round_trip():
    from custom_components.hair.models import UnknownDevice

    dev = UnknownDevice(label="Living Room TV", source="manual")
    d = dev.to_dict()
    assert d["source"] == "manual"
    assert UnknownDevice.from_dict(d).source == "manual"


def test_unknown_signal_legacy_load_defaults_to_sniffed():
    """Old .storage records lack a source field and must default to sniffed."""
    from custom_components.hair.models import UnknownSignal

    legacy = {"fingerprint": "abc123", "protocol": "PRONTO", "code": "0000 006D"}
    assert UnknownSignal.from_dict(legacy).source == "sniffed"


def test_unknown_device_legacy_load_defaults_to_sniffed():
    """Old .storage records lack a source field and must default to sniffed."""
    from custom_components.hair.models import UnknownDevice

    legacy = {"id": "dev1", "label": "Old Remote", "signals": []}
    assert UnknownDevice.from_dict(legacy).source == "sniffed"


def test_unknown_device_source_wig_round_trip():
    """The matrix-clip provenance stamp (Cold Cuts second half, owner
    ruling CC5) persists through the catalog store's to/from_dict."""
    from custom_components.hair.models import UnknownDevice

    stamp = {"filename": "cold-ac.wig.json", "cells_hash": "sha256:ab"}
    dev = UnknownDevice(label="Cold AC", source="manual", source_wig=stamp)
    d = dev.to_dict()
    assert d["source_wig"] == stamp
    loaded = UnknownDevice.from_dict(d)
    assert loaded.source_wig == stamp
    # Pre-Cold-Cuts records lack the field entirely: default None.
    legacy = {"id": "dev1", "label": "Old Remote", "signals": []}
    assert UnknownDevice.from_dict(legacy).source_wig is None
    assert UnknownDevice().to_dict()["source_wig"] is None


# ---------------------------------------------------------------------------
# alias field (Clips signal nickname) on UnknownSignal
# ---------------------------------------------------------------------------

def test_unknown_signal_alias_defaults_to_empty():
    from custom_components.hair.models import UnknownSignal

    assert UnknownSignal().alias == ""


def test_unknown_signal_alias_round_trip():
    from custom_components.hair.models import UnknownSignal

    sig = UnknownSignal(fingerprint="abc123", alias="Power")
    d = sig.to_dict()
    assert d["alias"] == "Power"
    assert UnknownSignal.from_dict(d).alias == "Power"


def test_unknown_signal_legacy_load_defaults_alias_to_empty():
    """Old .storage records lack an alias field and must default to empty."""
    from custom_components.hair.models import UnknownSignal

    legacy = {"fingerprint": "abc123", "protocol": "PRONTO", "code": "0000 006D"}
    assert UnknownSignal.from_dict(legacy).alias == ""


# ---------------------------------------------------------------------------
# order field + reorder_signals (drag-to-reorder, v0.3.2)
# ---------------------------------------------------------------------------

def test_unknown_device_order_defaults_to_zero():
    from custom_components.hair.models import UnknownDevice

    assert UnknownDevice().order == 0


def test_unknown_device_order_round_trip():
    from custom_components.hair.models import UnknownDevice

    dev = UnknownDevice(label="Remote", order=5)
    d = dev.to_dict()
    assert d["order"] == 5
    assert UnknownDevice.from_dict(d).order == 5


def test_unknown_device_legacy_load_defaults_order_to_zero():
    """Old .storage records lack an order field and must default to 0."""
    from custom_components.hair.models import UnknownDevice

    legacy = {"id": "dev1", "label": "Old Remote", "signals": []}
    assert UnknownDevice.from_dict(legacy).order == 0


def _sig(signal_id: str, fingerprint: str | None = None):
    from custom_components.hair.models import UnknownSignal

    return UnknownSignal(id=signal_id, fingerprint=fingerprint or signal_id)


# ---------------------------------------------------------------------------
# id + byte_hash + composite matching (pronto-bytes tiebreaker, v0.3.4)
# ---------------------------------------------------------------------------

def test_unknown_signal_id_and_byte_hash_round_trip():
    from custom_components.hair.models import UnknownSignal

    sig = UnknownSignal(id="sig1", fingerprint="fp1", byte_hash="bh1")
    d = sig.to_dict()
    assert d["id"] == "sig1"
    assert d["byte_hash"] == "bh1"
    loaded = UnknownSignal.from_dict(d)
    assert loaded.id == "sig1"
    assert loaded.byte_hash == "bh1"


def test_unknown_signal_legacy_load_generates_id_and_null_byte_hash():
    """Pre-0.3.4 records lack id and byte_hash; id is generated, hash is None."""
    from custom_components.hair.models import UnknownSignal

    legacy = {"fingerprint": "fp1", "code": "0000 006D"}
    loaded = UnknownSignal.from_dict(legacy)
    assert loaded.id  # a fresh uuid was generated
    assert loaded.byte_hash is None


def test_get_signal_matches_fingerprint_then_byte_hash():
    from custom_components.hair.models import UnknownDevice

    dev = UnknownDevice(label="R")
    a = _sig("a", fingerprint="fp")
    a.byte_hash = "h1"
    b = _sig("b", fingerprint="fp")
    b.byte_hash = "h2"
    dev.signals = [a, b]
    # Fingerprint-only matches the first signal with that fingerprint.
    assert dev.get_signal("fp") is a
    # The composite key distinguishes two same-fingerprint signals.
    assert dev.get_signal("fp", "h2") is b
    assert dev.get_signal("fp", "nope") is None


def test_get_signal_by_id_and_remove_by_id():
    from custom_components.hair.models import UnknownDevice

    dev = UnknownDevice(label="R")
    a = _sig("a", fingerprint="fp")
    b = _sig("b", fingerprint="fp")  # same fingerprint, distinct id
    dev.signals = [a, b]
    assert dev.get_signal_by_id("b") is b
    assert dev.remove_signal_by_id("a") is True
    assert [s.id for s in dev.signals] == ["b"]
    assert dev.remove_signal_by_id("missing") is False


def test_reorder_signals_happy_path():
    from custom_components.hair.models import UnknownDevice

    dev = UnknownDevice(label="Remote")
    dev.signals = [_sig("a"), _sig("b"), _sig("c")]
    dev.reorder_signals(["c", "a", "b"])
    assert [s.id for s in dev.signals] == ["c", "a", "b"]


def test_reorder_signals_by_id_with_shared_fingerprint():
    """Two signals can share a fingerprint (byte-hash tiebreaker); reorder
    keys on id, not fingerprint."""
    from custom_components.hair.models import UnknownDevice

    dev = UnknownDevice(label="Remote")
    dev.signals = [_sig("a", "fp"), _sig("b", "fp")]
    dev.reorder_signals(["b", "a"])
    assert [s.id for s in dev.signals] == ["b", "a"]


def test_reorder_signals_empty_with_empty_list():
    from custom_components.hair.models import UnknownDevice

    dev = UnknownDevice(label="Remote")
    dev.reorder_signals([])
    assert dev.signals == []


def test_reorder_signals_duplicate_raises():
    from custom_components.hair.models import UnknownDevice

    dev = UnknownDevice(label="Remote")
    dev.signals = [_sig("a")]
    original = list(dev.signals)
    with pytest.raises(ValueError, match="Duplicate"):
        dev.reorder_signals(["a", "a"])
    assert dev.signals == original


def test_reorder_signals_unknown_raises():
    from custom_components.hair.models import UnknownDevice

    dev = UnknownDevice(label="Remote")
    dev.signals = [_sig("a")]
    original = list(dev.signals)
    with pytest.raises(ValueError, match="unknown"):
        dev.reorder_signals(["a", "ghost"])
    assert dev.signals == original


def test_reorder_signals_missing_raises():
    from custom_components.hair.models import UnknownDevice

    dev = UnknownDevice(label="Remote")
    dev.signals = [_sig("a"), _sig("b")]
    original = list(dev.signals)
    with pytest.raises(ValueError, match="missing"):
        dev.reorder_signals(["a"])
    assert dev.signals == original


# ---------------------------------------------------------------------------
# TriggerRemote, hear-side lattice (signpost 4, Track M)
# ---------------------------------------------------------------------------


def test_trigger_remote_matrix_fields_round_trip():
    """climate_matrix and last_heard survive to_dict/from_dict whole."""
    from custom_components.hair.models import TriggerRemote

    heard = {
        "cell_key": "cool/auto/23",
        "cell_name": "Cool 23 Auto",
        "power": None,
        "at": "2026-08-17T10:00:00+00:00",
        "sl_pattern": "SLLS",
        "receiver_entity_id": "infrared.living_room",
        "receiver_area_name": "Living Room",
    }
    remote = TriggerRemote(
        name="Bedroom AC", climate_matrix=True, last_heard=heard
    )
    restored = TriggerRemote.from_dict(remote.to_dict())
    assert restored.climate_matrix is True
    assert restored.last_heard == heard


def test_trigger_remote_matrix_fields_default_off():
    """A remote written before Track M carries neither key; False and
    None are the truth about it."""
    from custom_components.hair.models import TriggerRemote

    restored = TriggerRemote.from_dict({"id": "r1", "name": "Old Remote"})
    assert restored.climate_matrix is False
    assert restored.last_heard is None


def test_trigger_remote_last_heard_rejects_non_dict():
    """A hand-edited store must not put a string on the render path."""
    from custom_components.hair.models import TriggerRemote

    restored = TriggerRemote.from_dict(
        {"id": "r1", "name": "Odd Remote", "last_heard": "Cool 23"}
    )
    assert restored.last_heard is None


def test_trigger_remote_last_heard_is_copied_not_shared():
    """to_dict hands out a copy, so a serialized payload cannot be
    mutated into the live remote (the pinned_device_ids posture)."""
    from custom_components.hair.models import TriggerRemote

    remote = TriggerRemote(name="AC", last_heard={"cell_key": "cool/auto/23"})
    payload = remote.to_dict()
    payload["last_heard"]["cell_key"] = "heat/auto/30"
    assert remote.last_heard["cell_key"] == "cool/auto/23"


def test_trigger_remote_clone_carries_flag_not_heard_state():
    """The flag is part of what the remote IS; the heard state is not.
    A copy has heard nothing, and the file copy is the caller's job."""
    from custom_components.hair.models import TriggerRemote

    source = TriggerRemote(
        name="Bedroom AC",
        climate_matrix=True,
        last_heard={"cell_key": "cool/auto/23", "cell_name": "Cool 23 Auto"},
    )
    clone = source.clone("Bedroom AC copy")
    assert clone.climate_matrix is True
    assert clone.last_heard is None
    assert clone.id != source.id


class TestSentState:
    """0.10.1 item 7: which state a saved STATE row transmits.

    A separate field from ``matrix_cell`` on purpose. The two carry the
    same four keys and mean opposite things about ownership: a porthole
    IS the lattice cell, a saved STATE row merely transmits its bytes.
    """

    def test_defaults_to_none(self):
        assert IRCommand(name="Power").sent_state is None

    def test_round_trips(self):
        state = {"mode": "cool", "fan": "auto", "swing": None, "temp": 22.0}
        command = IRCommand(name="cool / fan: auto / 22", sent_state=state)
        assert IRCommand.from_dict(command.to_dict()).sent_state == state

    def test_a_power_state_round_trips(self):
        command = IRCommand(name="Off", sent_state={"power": "off"})
        assert IRCommand.from_dict(command.to_dict()).sent_state == {
            "power": "off"
        }

    def test_absent_reads_as_none(self):
        assert IRCommand.from_dict({"name": "Power"}).sent_state is None

    def test_it_is_independent_of_matrix_cell(self):
        command = IRCommand(
            name="cool / fan: auto / 22",
            sent_state={"mode": "cool", "fan": "auto",
                        "swing": None, "temp": 22.0},
        )
        assert command.matrix_cell is None
        restored = IRCommand.from_dict(command.to_dict())
        assert restored.matrix_cell is None
        assert restored.sent_state is not None

    def test_a_clone_carries_it(self):
        """The duplicate gets a byte copy of the lattice, so the
        coordinates are as true on the clone as on the original."""
        state = {"mode": "cool", "fan": "auto", "swing": None, "temp": 22.0}
        device = IRDevice(
            name="AC",
            commands=[IRCommand(name="cool / fan: auto / 22",
                                sent_state=state)],
        )
        assert device.clone("AC copy").commands[0].sent_state == state
