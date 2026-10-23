"""The Logitech Harmony reader (import phase 2).

The fixtures under fixtures/adapters/harmony_* cover each shape the
reader takes or refuses: a device file with its commands, a code set, a
code set keyed by its hash, a device file that names its code set by
path, one that names it by hash, and a file holding several code sets.
Their codes are NEC frames from HAIR's own encoder, so every test knows
the bytes that must reach the wire.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.hair.tests.wire_bits import first_frame_bytes
from custom_components.hair.wig_adapters import (
    _HARMONY_KIND,
    convert,
    sniff,
)
from custom_components.hair.wig_format import (
    KIND_BY_KEY,
    parse_wig,
    serialize_wig,
)

FIXTURES = Path(__file__).parent / "fixtures" / "adapters"

DEVICE = "harmony_device_with_commands_fixture_audio_fa-2100.json"
CODESET = "harmony_codeset_7f3a09c2d4e5b6a1.json"
KEYED = "harmony_codeset_keyed_by_hash.json"
POINTER = "harmony_device_pointing_to_codeset_file.json"
NAMED = "harmony_device_naming_codeset_hash.json"
SEVERAL = "harmony_several_codesets.json"

#: alias -> NEC command byte, as the generator wrote them (address 0x10).
EXPECTED = {
    "Bass Down": 0x09, "Bass Up": 0x08, "Input Hdmi 1": 0x07,
    "Input Optical": 0x06, "Mute": 0x05, "Power Toggle": 0x02,
    "Volume Down": 0x04, "Volume Up": 0x03,
}

RECEIPTS = [
    "Play: keycode damaged in the source file, no code to send",
    "Radio: not infrared (radio, ATI 21 Bit)",
    "Sleep: not infrared (USB HID, HID 16 Bit)",
]


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _convert(name: str):
    return convert(_read(name), name)


class TestSniff:
    @pytest.mark.parametrize("name", [
        DEVICE, CODESET, KEYED, SEVERAL, NAMED, POINTER,
        "harmony_codeset_network_only.json",
    ])
    def test_every_shape_is_harmony(self, name):
        assert sniff(_read(name), name).format == "harmony"

    def test_smartir_is_not_harmony(self):
        # SmartIR's commands is an object; a list of keycode objects is
        # the Harmony marker.
        text = _read("smartir_media_player_1000.json")
        assert sniff(text).format == "smartir"

    def test_a_list_without_keycodes_is_not_harmony(self):
        assert sniff('{"commands": [{"name": "x", "code": "1"}]}').format \
            is None


class TestDeviceWithCommands:
    def test_the_infrared_rows_land_and_the_rest_are_receipted(self):
        result = _convert(DEVICE)
        assert result.error is None
        assert [w.name for w in result.wigs] == ["Fixture Audio FA-2100"]
        wig = result.wigs[0]
        assert sorted(s.alias for s in wig.signals) == sorted(EXPECTED)
        assert sorted(result.skipped) == RECEIPTS
        assert result.folds == []

    def test_device_fields(self):
        wig = _convert(DEVICE).wigs[0]
        assert wig.brand == "Fixture Audio"
        assert wig.model == "FA-2100"
        assert wig.kind == "amplifier"  # deviceType 19
        assert wig.origin == "converted:harmony"
        assert wig.notes == (
            "Imported from a Logitech Harmony device file. Power: toggle."
        )

    def test_the_codes_are_the_files_codes_on_the_wire(self):
        wig = _convert(DEVICE).wigs[0]
        for signal in wig.signals:
            command = EXPECTED[signal.alias]
            assert first_frame_bytes(signal.pronto) == [
                0x10, 0xEF, command, command ^ 0xFF,
            ], signal.alias

    def test_pronto_is_kept_verbatim(self):
        raw = json.loads(_read(DEVICE))
        by_name = {c["name"]: c.get("pronto") for c in raw["commands"]}
        wig = _convert(DEVICE).wigs[0]
        for signal in wig.signals:
            source = by_name[signal.alias.replace(" ", "")]
            assert signal.pronto == source

    def test_send_count_is_one_although_every_keycode_says_three(self):
        """MUTATION CHECK. The keycode's ``:3`` is a press hint, not a
        waveform repeat; a reader that took it would triple every send."""
        raw = json.loads(_read(DEVICE))
        assert all(c["keycode"].endswith(":3") for c in raw["commands"])
        wig = _convert(DEVICE).wigs[0]
        assert {s.send_count for s in wig.signals} == {1}

    def test_carrier_is_declared(self):
        wig = _convert(DEVICE).wigs[0]
        assert {s.extra["carrier"]["source"] for s in wig.signals} == {
            "declared"
        }

    def test_round_trips_through_the_wig_format(self):
        wig = _convert(DEVICE).wigs[0]
        again = parse_wig(serialize_wig(wig))
        assert again.ok, again.errors
        assert again.wig.kind == "amplifier"

    def test_a_device_with_no_commands_is_refused(self):
        raw = json.loads(_read(DEVICE))
        raw["commands"] = []
        result = convert(json.dumps(raw), DEVICE)
        assert not result.wigs
        assert "no infrared commands" in result.error


class TestCodeSets:
    def test_code_set(self):
        result = _convert(CODESET)
        wig = result.wigs[0]
        assert wig.name == "Harmony code set 7f3a09c2d4e5b6a1"
        assert wig.brand is None and wig.model is None and wig.kind is None
        assert "no brand or model" in wig.notes
        assert sorted(result.skipped) == RECEIPTS

    def test_a_code_set_keyed_by_its_hash_is_the_same_code_set(self):
        plain = {s.alias: s.pronto for s in _convert(CODESET).wigs[0].signals}
        result = _convert(KEYED)
        keyed = {s.alias: s.pronto for s in result.wigs[0].signals}
        assert keyed == plain
        assert sorted(result.skipped) == RECEIPTS

    def test_device_file_and_code_set_carry_the_same_codes(self):
        plain = {s.alias: s.pronto for s in _convert(CODESET).wigs[0].signals}
        device = {s.alias: s.pronto for s in _convert(DEVICE).wigs[0].signals}
        assert device == plain

    def test_a_network_only_code_set_is_refused_with_its_reasons(self):
        result = _convert("harmony_codeset_network_only.json")
        assert not result.wigs
        assert "no infrared commands" in result.error
        assert "not infrared (network, Fixture IP)" in result.error
        assert len(result.skipped) == 3


class TestRefusals:
    def test_a_device_file_without_its_codes_says_what_to_drop(self):
        result = _convert(POINTER)
        assert not result.wigs
        assert result.error == (
            "this Harmony file lists the device but not its codes. Drop the "
            "device file that includes its commands, or its code set."
        )

    def test_a_device_file_with_no_code_set_at_all(self):
        raw = json.loads(_read(POINTER))
        raw["codeset"] = None
        result = convert(json.dumps(raw), "x.json")
        assert result.error == (
            "this Harmony file lists the device but has no codes for it, so "
            "there is nothing to import."
        )

    def test_a_device_entry_names_its_code_set(self):
        result = _convert(NAMED)
        assert not result.wigs
        assert result.error == (
            "this Harmony file describes the device but not its codes. Drop "
            "its code set (7f3a09c2d4e5b6a1) instead."
        )

    def test_several_code_sets_are_refused_with_a_count(self):
        result = _convert(SEVERAL)
        assert not result.wigs
        assert "holds 3 Harmony code sets" in result.error
        assert "save the one you want" in result.error

    def test_an_unreadable_pronto_is_receipted(self):
        raw = json.loads(_read(CODESET))
        raw["commands"][0]["pronto"] = "0000 zzzz"
        result = convert(json.dumps(raw), CODESET)
        assert any("unreadable Pronto" in s for s in result.skipped)
        assert result.wigs


class TestKindTable:
    def test_every_mapped_kind_is_on_the_list(self):
        assert set(_HARMONY_KIND.values()) <= set(KIND_BY_KEY)

    def test_the_kinds_harmony_shares_with_hair(self):
        assert _HARMONY_KIND[13] == "monitor"
        assert _HARMONY_KIND[19] == "amplifier"
        assert _HARMONY_KIND[21] == "minisystem"
        assert _HARMONY_KIND[30] == "avswitch"
        assert _HARMONY_KIND[3] == "player"

    def test_climate_and_radio_stay_blank(self):
        assert 45 not in _HARMONY_KIND
        assert 36 not in _HARMONY_KIND


def test_nothing_from_the_file_is_stored_as_an_identifier():
    """The file's catalogue id helps recognise its shape; it is not
    stored."""
    raw = json.loads(_read(DEVICE))
    assert "globalDeviceId" in raw
    wig = _convert(DEVICE).wigs[0]
    assert wig.identifiers is None
    assert "990001" not in serialize_wig(wig)
