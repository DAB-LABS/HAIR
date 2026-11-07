"""irdb CSV files in the Closet (GH #235).

An irdb CSV names a protocol and its D, S and F; HAIR builds the code
from its own classes. The fixtures in fixtures/adapters/irdb_*.csv are
written by hand in irdb's shape, with values chosen for the tests.

WHAT ANCHORS EACH PROTOCOL. A build that is decoded with the same
assumptions it was built with proves only that the code agrees with
itself. So each row of the table is checked against the field layout
the protocol's published definition (IRP notation) states, written out
here independently of the builder: NEC's address is D then S, a Sony20
address is D then S after five bits, a Kaseikyo frame's data bytes are
the bytes the protocol lists. The decode must give those values back.

PER LEG. NEC is decoded by the optional library only, so on the leg
without it an NEC-family build decodes as nothing; the build and the
code are the same on both legs, and the bypass flag records whether
HAIR can rebuild the code from its decode.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from custom_components.hair import irdb_csv
from custom_components.hair.const import DOMAIN
from custom_components.hair.ir_command import raw_to_pronto
from custom_components.hair.irdb_csv import IRDB_PROTOCOLS, IrdbError
from custom_components.hair.protocol_decode import try_decode_identity
from custom_components.hair.websocket_api import ws_wigs_upload
from custom_components.hair.wig_adapters import (
    _carrier_for,
    _int_or_none,
    _triple_reproduces,
    convert,
    sniff,
)

FIXTURES = Path(__file__).parent / "fixtures" / "adapters"
_HAS_LIBRARY = importlib.util.find_spec("infrared_protocols") is not None
LEG = "lib" if _HAS_LIBRARY else "nolib"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _kaseikyo(data: list[int]) -> int:
    """The KASEIKYO48 decode's command: the four data bytes, first first."""
    return int.from_bytes(bytes(data), "big")


def _nec(d: int, s: int, f: int) -> tuple:
    return ("NEC", d | (s << 8), f, None)


# --- the table ---------------------------------------------------------------
#
# name -> (D, S, F, carrier Hz, {leg: identity}, {leg: bypass}).
# An identity is (protocol, address, command, extras), written from the
# protocol's definition; None means the leg decodes nothing.

_P_D, _P_S, _P_F = 128, 0, 61
_K_D, _K_S, _K_F = 4, 1, 123
_K_CHECK = ((_K_D << 4) ^ _K_S ^ (_K_F << 4) ^ ((_K_F >> 4) & 0xFF)) & 0xFF

TABLE: dict[str, tuple] = {
    "NEC": (4, -1, 16, 38000,
            {"lib": _nec(4, 251, 16), "nolib": None},
            {"lib": False, "nolib": False}),
    "NEC1": (4, -1, 17, 38000,
             {"lib": _nec(4, 251, 17), "nolib": None},
             {"lib": False, "nolib": False}),
    "NEC2": (4, -1, 8, 38000,
             {"lib": _nec(4, 251, 8), "nolib": None},
             {"lib": False, "nolib": False}),
    # NEC1-f16's fourth byte defaults to ~F, which an irdb row cannot
    # change, so its frame is NEC1's.
    "NEC1-f16": (4, -1, 9, 38000,
                 {"lib": _nec(4, 251, 9), "nolib": None},
                 {"lib": False, "nolib": False}),
    # NECx: D then S as one 16-bit address. The decode writes D,D as D.
    "NECx1": (7, 8, 2, 38000,
              {leg: ("SAMSUNG32", 7 | (8 << 8), 2, None) for leg in ("lib", "nolib")},
              {"lib": False, "nolib": False}),
    "NECx2": (7, 7, 3, 38000,
              {leg: ("SAMSUNG32", 7, 3, None) for leg in ("lib", "nolib")},
              {"lib": False, "nolib": False}),
    # F 64..127 is RC5X; 70 checks the seventh bit.
    "RC5": (5, -1, 70, 36000,
            {leg: ("RC5", 5, 70, {"toggle": 0}) for leg in ("lib", "nolib")},
            {"lib": False, "nolib": False}),
    "Sony12": (1, -1, 21, 40000,
               {leg: ("SONY12", 1, 21, None) for leg in ("lib", "nolib")},
               {"lib": False, "nolib": False}),
    "Sony15": (26, -1, 46, 40000,
               {leg: ("SONY15", 26, 46, None) for leg in ("lib", "nolib")},
               {"lib": False, "nolib": False}),
    # F:7, D:5, S:8 -- the address is D then S after five bits.
    "Sony20": (26, 73, 55, 40000,
               {leg: ("SONY20", 26 | (73 << 5), 55, None) for leg in ("lib", "nolib")},
               {"lib": False, "nolib": False}),
    "RC6": (4, -1, 12, 36000,
            {leg: ("RC6", 4, 12, {"mode": 0, "toggle": 0}) for leg in ("lib", "nolib")},
            {"lib": False, "nolib": False}),
    # RC6 mode 6 with OEM1 128 and S as OEM2.
    "MCE": (4, 15, 12, 36000,
            {leg: ("RC6", 4, 12, {"mode": 6, "toggle": 0, "customer": (128 << 8) | 15})
             for leg in ("lib", "nolib")},
            {"lib": False, "nolib": False}),
    # Vendor 2, 32 (0x2002); data D, S, F, D^S^F; the protocol's 37 kHz.
    "Panasonic": (_P_D, _P_S, _P_F, 37000,
                  {leg: ("KASEIKYO48", 0x2002,
                         _kaseikyo([_P_D, _P_S, _P_F, _P_D ^ _P_S ^ _P_F]), None)
                   for leg in ("lib", "nolib")},
                  {"lib": True, "nolib": True}),
    # Vendor 84, 50 (0x3254); 0:4 D:4 S:4 F:12 and the check byte.
    "Denon-K": (_K_D, _K_S, _K_F, 37000,
                {leg: ("KASEIKYO48", 0x3254,
                       _kaseikyo([_K_D << 4, _K_S | ((_K_F & 0xF) << 4),
                                  _K_F >> 4, _K_CHECK]), None)
                 for leg in ("lib", "nolib")},
                {"lib": True, "nolib": True}),
    # The NEC2 frame at 40 kHz. The library reads it as NEC, so the
    # bypass keeps the 40 kHz code as built rather than a 38 kHz rebuild.
    "Pioneer": (165, -1, 28, 40000,
                {"lib": _nec(165, 90, 28), "nolib": None},
                {"lib": True, "nolib": False}),
    "RCA": (15, -1, 84, 58000,
            {leg: ("RCA", 15, 84, None) for leg in ("lib", "nolib")},
            {"lib": True, "nolib": True}),
    "Sharp": (1, -1, 22, 38000,
              {leg: ("SHARP", 1, 22, {"extension": 1}) for leg in ("lib", "nolib")},
              {"lib": False, "nolib": False}),
    "Denon": (2, -1, 22, 38000,
              {leg: ("SHARP", 2, 22, None) for leg in ("lib", "nolib")},
              {"lib": False, "nolib": False}),
    # D:8 S:5 as the 13-bit address, then F, each with its complement.
    "Aiwa": (110, 3, 10, 38000,
             {leg: ("NEC42", 110 | (3 << 8), 10, None) for leg in ("lib", "nolib")},
             {"lib": False, "nolib": False}),
    # D:8 F:8, no subdevice, 38 kHz.
    "JVC": (67, -1, 3, 38000,
            {leg: ("JVC", 67, 3, None) for leg in ("lib", "nolib")},
            {"lib": False, "nolib": False}),
    # Encode only (encoders/mitsubishi.py): nothing decodes it, so it is
    # stored as built. The frame itself is checked in test_irdb_encoders.
    "Mitsubishi": (71, -1, 23, 32600,
                   {"lib": None, "nolib": None},
                   {"lib": False, "nolib": False}),
    # Encode only (encoders/recs80.py), toggle 0.
    "RECS80": (5, -1, 38, 38000,
               {"lib": None, "nolib": None},
               {"lib": False, "nolib": False}),
    # Encode only (encoders/gi_cable.py).
    "G.I.Cable": (0, -1, 29, 38700,
                  {"lib": None, "nolib": None},
                  {"lib": False, "nolib": False}),
}

#: Protocols whose S defaults to 255-D when the row gives -1.
S_DEFAULTS = {"NEC", "NEC1", "NEC2", "NEC1-f16", "NECx1", "NECx2", "Pioneer"}
#: Protocols with no S at all: the row must give -1.
NO_S = {"RC5", "Sony12", "Sony15", "RC6", "RCA", "Sharp", "Denon", "JVC",
        "Mitsubishi", "RECS80", "G.I.Cable"}
#: Protocols whose S has no default: -1 is refused.
S_REQUIRED = {"Sony20", "MCE", "Panasonic", "Denon-K", "Aiwa"}


def _built(name: str, d: int, s: int, f: int):
    command = irdb_csv.build(name, d, s, f)
    timings = list(command.get_raw_timings())
    hz, _ = _carrier_for(None, _int_or_none(getattr(command, "modulation", None)))
    return command, timings, hz


def _identity(timings):
    found = try_decode_identity(timings)
    if found is None:
        return None
    return (found.protocol, found.address, found.command, found.extras or None)


class TestTheTable:
    def test_the_table_is_exactly_the_verified_set(self):
        assert {spelled for spelled, _ in IRDB_PROTOCOLS.values()} == set(TABLE)

    def test_nokia32_is_not_in_the_table(self):
        """Its X field is never 0 in practice and an irdb row cannot
        carry it, so it waits for phase 2."""
        assert "nokia32" not in IRDB_PROTOCOLS

    def test_every_table_name_is_one_irdb_uses(self):
        assert all(irdb_csv.known_name(name) for name in TABLE)

    def test_the_default_groups_cover_the_table_once(self):
        groups = (S_DEFAULTS, NO_S, S_REQUIRED)
        assert set().union(*groups) == set(TABLE)
        assert sum(len(g) for g in groups) == len(TABLE)

    @pytest.mark.parametrize("name", sorted(TABLE))
    def test_builds_and_decodes_to_the_published_fields(self, name):
        d, s, f, _, identity, _ = TABLE[name]
        _, timings, _ = _built(name, d, s, f)
        assert _identity(timings) == identity[LEG]

    @pytest.mark.parametrize("name", sorted(TABLE))
    def test_carrier_is_the_protocols_own(self, name):
        d, s, f, hz, _, _ = TABLE[name]
        _, _, built_hz = _built(name, d, s, f)
        assert built_hz == hz

    @pytest.mark.parametrize("name", sorted(TABLE))
    def test_bypass_is_pinned_per_leg(self, name):
        d, s, f, hz, _, bypass = TABLE[name]
        _, timings, _ = _built(name, d, s, f)
        pronto = raw_to_pronto(timings, frequency=hz)
        assert (not _triple_reproduces(pronto, timings)) is bypass[LEG]

    @pytest.mark.parametrize("name", sorted(TABLE))
    def test_any_letter_case_names_the_same_protocol(self, name):
        d, s, f, *_ = TABLE[name]
        _, upper, _ = _built(name.upper(), d, s, f)
        _, lower, _ = _built(name.lower(), d, s, f)
        assert upper == lower


class TestMinusOne:
    @pytest.mark.parametrize("name", sorted(S_DEFAULTS))
    def test_s_minus_one_is_255_minus_d(self, name):
        d, _, f, *_ = TABLE[name]
        _, defaulted, _ = _built(name, d, -1, f)
        _, explicit, _ = _built(name, d, 255 - d, f)
        assert defaulted == explicit

    @pytest.mark.parametrize("name", sorted(NO_S))
    def test_a_protocol_with_no_s_refuses_one(self, name):
        d, s, f, *_ = TABLE[name]
        assert s == -1
        with pytest.raises(IrdbError, match="has no subdevice"):
            irdb_csv.build(name, d, 0, f)

    @pytest.mark.parametrize("name", sorted(S_REQUIRED))
    def test_a_required_s_has_no_default(self, name):
        d, _, f, *_ = TABLE[name]
        with pytest.raises(IrdbError, match="needs a subdevice"):
            irdb_csv.build(name, d, -1, f)

    @pytest.mark.parametrize("name", sorted(TABLE))
    def test_d_and_f_have_no_default(self, name):
        d, s, f, *_ = TABLE[name]
        with pytest.raises(IrdbError, match="needs a device"):
            irdb_csv.build(name, -1, s, f)
        with pytest.raises(IrdbError, match="needs a function"):
            irdb_csv.build(name, d, s, -1)


class TestRefusals:
    def test_a_protocol_outside_the_table_is_named(self):
        with pytest.raises(IrdbError, match=r"^Velleman cannot be built yet$"):
            irdb_csv.build("Velleman", 0, -1, 10)

    def test_jvc_refuses_a_subdevice_and_a_wide_device(self):
        with pytest.raises(IrdbError, match="JVC has no subdevice, but the row gives 1"):
            irdb_csv.build("JVC", 67, 1, 3)
        with pytest.raises(IrdbError, match="JVC device 256 is outside 0 to 255"):
            irdb_csv.build("JVC", 256, -1, 3)
        with pytest.raises(IrdbError, match="JVC function 256 is outside 0 to 255"):
            irdb_csv.build("JVC", 67, -1, 256)

    def test_jvc_decodes_to_its_own_fingerprint(self):
        _, timings, _ = _built("JVC", 67, -1, 3)
        assert try_decode_identity(timings).fingerprint == "JVC:0x0043:0x03"

    def test_out_of_range_is_refused_not_masked(self):
        with pytest.raises(IrdbError, match="outside 0 to 31"):
            irdb_csv.build("RC5", 40, -1, 12)
        with pytest.raises(IrdbError, match="outside 0 to 255"):
            irdb_csv.build("NEC1", 4, -1, 256)

    def test_necx_s_zero_with_a_device_cannot_be_sent(self):
        with pytest.raises(IrdbError, match="cannot be sent yet"):
            irdb_csv.build("NECx1", 7, 0, 2)

    def test_panasonic_device_low_bits_cannot_be_sent(self):
        with pytest.raises(IrdbError, match="low four bits"):
            irdb_csv.build("Panasonic", 1, 0, 3)


# --- the probe ----------------------------------------------------------------


class TestProbe:
    def test_an_irdb_file_is_irdb(self):
        assert sniff(_read("irdb_necx1.csv")).format == "irdb"
        assert sniff(_read("irdb_necx1.csv"), "45,45.csv").format == "irdb"

    def test_content_wins_over_the_name(self):
        assert sniff(_read("irdb_necx1.csv"), "codes.txt").format == "irdb"

    def test_a_control_tower_csv_is_still_global_cache(self):
        text = _read("globalcache_codeset.csv")
        assert sniff(text).format == "globalcache"
        assert sniff(text, "globalcache_codeset.csv").format == "globalcache"

    def test_a_csv_with_another_header_is_neither(self):
        result = sniff(_read("csv_other_header.csv"), "csv_other_header.csv")
        assert result.format is None
        assert result.candidates == ()

    @pytest.mark.parametrize("header", [
        "functionname,protocol,device,subdevice,function",
        "FunctionName,Protocol,Device,Subdevice,Function",
        "\ufefffunctionname,protocol,device,subdevice,function",
        "functionname\tprotocol,device,subdevice,function",
        "functionname, protocol, device, subdevice, function",
        "function,protocol,device,subdevice,function",
    ])
    def test_each_header_spelling(self, header):
        assert irdb_csv.is_irdb(header + "\nPOWER,NEC1,4,-1,8\n")

    def test_headerless_needs_every_line_to_fit(self):
        good = "POWER,NEC1,4,-1,8\nMUTE,nec1,4,-1,9\n"
        assert irdb_csv.is_irdb(good)
        assert not irdb_csv.is_irdb(good + "NOTE,NEC1,4,-1,eight\n")
        assert not irdb_csv.is_irdb(good + "SIX,NEC1,4,-1,8,1\n")
        assert not irdb_csv.is_irdb(good + "ODD,Whatever,4,-1,8\n")

    def test_a_json_file_is_never_irdb(self):
        assert sniff('{"functionname": "protocol"}').format is None

    def test_an_empty_file_is_not_irdb(self):
        assert not irdb_csv.is_irdb("")
        assert not irdb_csv.is_irdb("\n\n")


# --- the reader ---------------------------------------------------------------


def _signals(result):
    assert len(result.wigs) == 1, result.error
    return result.wigs[0].signals


class TestReader:
    def test_one_file_one_wig(self):
        result = convert(_read("irdb_necx1.csv"), "LG/Blu-Ray/45,45.csv")
        assert result.format == "irdb"
        assert result.error is None
        assert result.skipped == []
        wig = result.wigs[0]
        assert wig.name == "LG Blu-Ray 45,45"
        assert (wig.brand, wig.kind, wig.model) == ("LG", None, None)
        assert wig.origin == "converted:irdb"
        assert wig.notes == "Imported from an irdb CSV."
        assert [s.alias for s in wig.signals] == [
            "POWER", "POWER ON", "VOLUME UP", "VOLUME DOWN", "MUTE", "PLAY",
            "TR PLAY",
        ]

    def test_a_bare_file_name_is_the_wig_name(self):
        result = convert(_read("irdb_necx1.csv"), "45,45.csv")
        assert result.wigs[0].name == "45,45"

    def test_a_name_with_no_folders_has_no_brand_or_kind(self):
        wig = convert(_read("irdb_necx1.csv"), "45,45.csv").wigs[0]
        assert (wig.brand, wig.kind) == (None, None)

    @pytest.mark.parametrize(("hint", "brand", "kind"), [
        ("Samsung/TV/7,7.csv", "Samsung", "tv"),
        ("Denon/Receiver/4,1.csv", "Denon", "receiver"),
        ("LG/Blu-Ray/45,45.csv", "LG", None),
    ])
    def test_brand_and_kind_come_from_the_folders(self, hint, brand, kind):
        wig = convert(_read("irdb_necx1.csv"), hint).wigs[0]
        assert (wig.brand, wig.kind) == (brand, kind)

    def test_no_name_at_all(self):
        assert convert(_read("irdb_necx1.csv")).wigs[0].name == "irdb Import"

    def test_names_that_repeat_a_function_are_kept(self):
        signals = _signals(convert(_read("irdb_necx1.csv"), "x.csv"))
        by_alias = {s.alias: s.pronto for s in signals}
        assert by_alias["PLAY"] == by_alias["TR PLAY"]

    def test_each_signal_is_the_built_code(self):
        signals = _signals(convert(_read("irdb_necx1.csv"), "x.csv"))
        _, timings, hz = _built("NECx1", 7, 7, 2)
        assert signals[0].pronto == raw_to_pronto(timings, frequency=hz)
        assert signals[0].extra == {"carrier": {"hz": 38000, "source": "protocol"}}
        assert signals[0].bypass_protocol is False

    @pytest.mark.parametrize("name", sorted(TABLE))
    def test_the_stored_signal_carries_the_tables_bypass_and_carrier(self, name):
        d, s, f, hz, _, bypass = TABLE[name]
        text = (
            "functionname,protocol,device,subdevice,function\n"
            f"KEY,{name},{d},{s},{f}\n"
        )
        (signal,) = _signals(convert(text, "x.csv"))
        assert signal.bypass_protocol is bypass[LEG]
        assert signal.extra == {"carrier": {"hz": hz, "source": "protocol"}}

    def test_mixed_protocols_and_the_grouped_receipt(self):
        result = convert(_read("irdb_mixed_protocols.csv"), "x.csv")
        signals = _signals(result)
        assert [s.alias for s in signals] == [
            "POWER", "INPUT", "OK", "SLEEP", "TUNER", "CD", "AUX",
        ]
        assert [s.extra["carrier"]["hz"] for s in signals] == [
            38000, 38000, 36000, 40000, 38000, 38000, 38000,
        ]
        assert result.skipped == [
            "1 row not read: Nokia32, which HAIR cannot build yet",
        ]

    def test_a_jvc_file_now_imports(self):
        result = convert(_read("irdb_jvc_dvhs.csv"), "JVC/D-VHS/67,-1.csv")
        assert result.error is None
        assert result.skipped == []
        wig = result.wigs[0]
        assert (wig.name, wig.brand, wig.kind) == ("JVC D-VHS 67,-1", "JVC", None)
        assert [s.alias for s in wig.signals] == [
            "POWER", "PLAY", "PAUSE", "REW <<", "FF >>", "REC",
        ]
        for signal, function in zip(wig.signals, (0, 12, 13, 14, 15, 28), strict=True):
            _, timings, hz = _built("JVC", 67, -1, function)
            assert signal.pronto == raw_to_pronto(timings, frequency=hz)
            assert signal.bypass_protocol is False
            assert signal.extra == {"carrier": {"hz": 38000, "source": "protocol"}}

    def test_an_unknown_protocol_name_is_worded_apart(self):
        text = "functionname,protocol,device,subdevice,function\n" \
               "A,NEC1,4,-1,8\nB,Zorro,1,1,1\n"
        result = convert(text, "x.csv")
        assert result.skipped == [
            "1 row not read: Zorro is not a protocol name irdb uses",
        ]

    def test_headerless(self):
        signals = _signals(convert(_read("irdb_headerless.csv"), "x.csv"))
        assert [s.alias for s in signals] == ["POWER", "VOL+", "VOL-"]

    def test_tab_header_bom_and_letter_case(self):
        result = convert(_read("irdb_tab_header.csv"), "x.csv")
        assert [s.alias for s in _signals(result)] == ["POWER", "MUTE", "INFO"]
        assert result.skipped == []

    def test_function_as_the_first_header_word(self):
        signals = _signals(convert(_read("irdb_function_header.csv"), "x.csv"))
        assert [s.alias for s in signals] == ["POWER", "MUTE"]

    def test_quoted_names(self):
        signals = _signals(convert(_read("irdb_quoted_names.csv"), "x.csv"))
        assert [s.alias for s in signals] == [
            "INPUT, NEXT", 'SURROUND "ON"', "PLAIN",
        ]

    def test_empty_names_are_function_n(self):
        signals = _signals(convert(_read("irdb_empty_names.csv"), "x.csv"))
        assert [s.alias for s in signals] == ["Function 22", "Function 23", "STOP"]

    def test_merged_device_read_when_the_file_name_agrees(self):
        result = convert(_read("irdb_merged_device.csv"), "Denon/Receiver/4,1.csv")
        signals = _signals(result)
        assert result.skipped == []
        assert result.wigs[0].name == "Denon Receiver 4,1"
        assert [s.alias for s in signals] == ["PHONO", "TUNER", "POWER"]
        _, timings, hz = _built("Denon-K", 4, 1, 40)
        assert signals[0].pronto == raw_to_pronto(timings, frequency=hz)

    @pytest.mark.parametrize("hint", ["4,2.csv", "1,4.csv", "receiver.csv", ""])
    def test_merged_device_skipped_when_the_file_name_does_not_say(self, hint):
        result = convert(_read("irdb_merged_device.csv"), hint)
        assert [s.alias for s in _signals(result)] == ["POWER"]
        assert result.skipped == [
            f"line {n}: device and subdevice are written together as 4.1, "
            "and the file name does not say which is which"
            for n in (2, 3)
        ]

    def test_malformed_rows_are_named_in_file_order(self):
        result = convert(_read("irdb_malformed_rows.csv"), "x.csv")
        assert [s.alias for s in _signals(result)] == ["GOOD"]
        assert result.skipped == [
            "line 3: 3 fields, not 5",
            "line 4: no protocol",
            "line 5: device, subdevice and function must be whole numbers",
            "DEFAULTED was not read: RC5 needs a device, and -1 has no default here",
            "WIDE was not read: RC5 device 40 is outside 0 to 31",
            "EXTRA S was not read: Sharp has no subdevice, but the row gives 7",
        ]

    def test_a_button_named_twice_is_told_apart_by_its_line(self):
        text = (
            "functionname,protocol,device,subdevice,function\n"
            "POWER,NEC1,4,-1,8\n"
            "MUTE,RC5,40,-1,13\n"
            "POWER,RC5,40,-1,12\n"
        )
        result = convert(text, "x.csv")
        assert result.skipped == [
            "MUTE was not read: RC5 device 40 is outside 0 to 31",
            "POWER (line 4) was not read: RC5 device 40 is outside 0 to 31",
        ]

    def test_nothing_supported_is_an_error(self):
        result = convert(_read("irdb_all_unsupported.csv"), "x.csv")
        assert result.wigs == []
        assert result.error == (
            "nothing in this irdb file can be built "
            "(3 rows not read: Velleman, which HAIR cannot build yet)"
        )


class TestFileName:
    @pytest.mark.parametrize(("hint", "pair"), [
        ("45,45.csv", (45, 45)),
        ("LG/Blu-Ray/45,45.csv", (45, 45)),
        ("C:\\irdb\\Denon\\Receiver\\4,-1.CSV", (4, -1)),
        ("remote.csv", None),
        ("", None),
    ])
    def test_file_pair(self, hint, pair):
        assert irdb_csv.file_pair(hint) == pair

    @pytest.mark.parametrize(("hint", "name"), [
        ("LG/Blu-Ray/45,45.csv", "LG Blu-Ray 45,45"),
        ("Blu-Ray/45,45.csv", "45,45"),
        ("my remote.csv", "my remote"),
        ("", ""),
    ])
    def test_wig_name(self, hint, name):
        assert irdb_csv.wig_name(hint) == name

    @pytest.mark.parametrize(("hint", "brand"), [
        ("LG/Blu-Ray/45,45.csv", "LG"),
        ("irdb/codes/LG/Blu-Ray/45,45.csv", "LG"),
        ("C:\\irdb\\Denon\\Receiver\\4,1.csv", "Denon"),
        ("Blu-Ray/45,45.csv", None),
        ("45,45.csv", None),
        ("", None),
    ])
    def test_brand(self, hint, brand):
        assert irdb_csv.brand(hint) == brand

    @pytest.mark.parametrize(("hint", "kind"), [
        ("Samsung/TV/7,7.csv", "tv"),
        ("Sony/Receiver/1,-1.csv", "receiver"),
        ("Epson/Projector/1,1.csv", "projector"),
        ("Daikin/Air Conditioner/1,1.csv", "ac"),
        ("Bose/Mini System/1,1.csv", "minisystem"),
        # Folders that name no kind of HAIR's stay unset, never Other.
        ("LG/Blu-Ray/45,45.csv", None),
        ("Pioneer/DVD Player/175,-1.csv", None),
        ("Sharp/Unknown_TV/1,-1.csv", None),
        ("TV/7,7.csv", None),
        ("7,7.csv", None),
    ])
    def test_kind_only_when_the_folder_names_one_of_hairs(self, hint, kind):
        assert irdb_csv.kind(hint) == kind


# --- the upload door ------------------------------------------------------------


def _conn():
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    conn.user.name = "dab"
    return conn


class TestWebsocket:
    @pytest.mark.asyncio
    async def test_a_dropped_file_files_one_wig_with_its_receipt(
        self, fake_hass, tmp_path
    ):
        (tmp_path / "hair" / "wigs").mkdir(parents=True)
        fake_hass.config.config_dir = str(tmp_path)
        fake_hass.data[DOMAIN] = {"entry-1": {
            "device_manager": MagicMock(), "fitting_manager": None, "store": None,
        }}
        conn = _conn()
        await ws_wigs_upload(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/upload",
            "text": _read("irdb_mixed_protocols.csv"),
            "filename": "irdb_mixed_protocols.csv",
        })
        payload = conn.send_result.call_args.args[1]
        assert payload["success"], payload
        assert payload["format"] == "irdb"
        assert len(payload["filenames"]) == 1
        assert payload["skipped"][0] == (
            "1 row not read: Nokia32, which HAIR cannot build yet"
        )

    @pytest.mark.asyncio
    async def test_a_file_with_nothing_buildable_is_refused(
        self, fake_hass, tmp_path
    ):
        (tmp_path / "hair" / "wigs").mkdir(parents=True)
        fake_hass.config.config_dir = str(tmp_path)
        fake_hass.data[DOMAIN] = {"entry-1": {
            "device_manager": MagicMock(), "fitting_manager": None, "store": None,
        }}
        conn = _conn()
        await ws_wigs_upload(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/upload",
            "text": _read("irdb_all_unsupported.csv"),
            "filename": "irdb_all_unsupported.csv",
        })
        payload = conn.send_result.call_args.args[1]
        assert payload["success"] is False
        assert "nothing in this irdb file can be built" in payload["errors"][0]
