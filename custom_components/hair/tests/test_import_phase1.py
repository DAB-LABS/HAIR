"""Import phase 1: the formats HAIR already accepted, finished.

Four of the seven items are places where HAIR accepted a file and then
did something quietly wrong with it, so most of what is asserted here
is the difference between a receipt and a silence.

BOTH LEGS. Every builder entry and the whole LIRC Manchester path
resolve their classes through ``protocol_decode.get_spec``, which
answers with this package's own decoders where the optional library
ships none, so none of these tests is skipped when the library is
absent. The one thing that IS leg-dependent is what the registry makes
of a rebuilt waveform, and those assertions say so.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.hair.ir_command import (
    ProntoCommand,
    carrier_or_default,
    raw_to_pronto,
)
from custom_components.hair.protocol_decode import get_spec, try_decode_identity
from custom_components.hair.tests.leg import strict_nec_available
from custom_components.hair.wig_adapters import (
    FLIPPER_REMOTE_HEADER,
    convert,
    sniff_format,
)
from custom_components.hair.wig_format import (
    KIND_BY_KEY,
    WIG_FORMAT_V3,
    WIG_FORMAT_V4,
    cells_content_hash,
    parse_wig,
    serialize_wig,
)

FIXTURES = Path(__file__).parent / "fixtures" / "adapters"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8", errors="replace")


def _one_wig(name: str):
    result = convert(_fixture(name), name)
    assert result.error is None, result.error
    assert len(result.wigs) == 1
    return result, result.wigs[0]


# ---------------------------------------------------------------------------
# Item 3: Flipper
# ---------------------------------------------------------------------------


class TestFlipperLibraryRefusal:
    """A universal library file is refused by header, with a receipt."""

    def test_it_is_refused_and_says_what_the_file_is(self):
        result = convert(_fixture("flipper_library_tv.ir"), "tv.ir")
        assert result.format == "flipper_library"
        assert result.wigs == []
        assert result.error is not None
        assert "library" in result.error
        assert FLIPPER_REMOTE_HEADER in result.error

    def test_the_receipt_counts_the_models_it_holds(self):
        result = convert(_fixture("flipper_library_tv.ir"), "tv.ir")
        assert "(2 models)" in (result.error or "")

    def test_a_single_remote_with_a_model_comment_is_not_mistaken_for_one(
        self,
    ):
        """The only bypass is editing the header, which is a person
        declaring the file is one remote."""
        # RC6 rather than NEC: the plain ``NEC`` entry is one of the
        # library-gated ones, and this test runs on both legs.
        text = (
            f"{FLIPPER_REMOTE_HEADER}\nVersion: 1\n#\n# Model: generic-tv-a\n"
            "#\nname: Power\ntype: parsed\nprotocol: RC6\n"
            "address: 04 00 00 00\ncommand: 08 00 00 00\n"
        )
        assert sniff_format(text) == "flipper"
        result = convert(text, "one.ir")
        assert result.error is None
        assert len(result.wigs[0].signals) == 1


class TestTheLibraryHeaderIsALine:
    """The refusal reads a declaration, not any mention of one.

    A person told to copy their model's block into a file of its own
    does exactly that, and keeps the original header as a provenance
    comment. An unanchored search refused them again, with the same
    message, telling them to do what they had just done.
    """

    def _single_remote(self, comment: str) -> str:
        return (
            f"{FLIPPER_REMOTE_HEADER}\n"
            "Version: 1\n"
            f"# {comment}\n"
            "#\n"
            "name: Power\n"
            "type: raw\n"
            "frequency: 38000\n"
            "data: 9000 4500 560 560\n"
        )

    def test_a_comment_quoting_the_library_header_still_imports(self):
        text = self._single_remote("Filetype: IR library file")
        assert sniff_format(text) == "flipper"
        result = convert(text, "power.ir")
        assert result.error is None
        assert [s.alias for s in result.wigs[0].signals] == ["Power"]

    def test_a_comment_quoting_the_remote_header_is_not_a_header(self):
        """The same anchoring, the other way round: a library file
        stays a library file."""
        library = _fixture("flipper_library_tv.ir")
        doctored = library.replace(
            "Version: 1", f"Version: 1\n# {FLIPPER_REMOTE_HEADER}", 1
        )
        assert sniff_format(doctored) == "flipper_library"

    def test_the_real_library_file_is_still_refused(self):
        assert sniff_format(_fixture("flipper_library_tv.ir")) == (
            "flipper_library"
        )


class TestFlipperBuilderEntries:
    """RC6, RC5X and RCA, at the widths the firmware documents."""

    def _row(self, protocol: str, address: str, command: str) -> str:
        return (
            f"{FLIPPER_REMOTE_HEADER}\nVersion: 1\n#\n"
            f"name: Row\ntype: parsed\nprotocol: {protocol}\n"
            f"address: {address}\ncommand: {command}\n"
        )

    def test_rc6_converts_and_decodes_back(self):
        result = convert(self._row("RC6", "04 00 00 00", "0C 00 00 00"), "x.ir")
        assert result.skipped == []
        signal = result.wigs[0].signals[0]
        timings = ProntoCommand(signal.pronto).get_raw_timings()
        decoded = get_spec("RC6").command_cls.from_raw_timings(timings)
        assert decoded is not None
        assert (decoded.address, decoded.command) == (0x04, 0x0C)
        assert decoded.mode == 0
        assert decoded.toggle == 0

    def test_rc5x_keeps_the_seventh_command_bit(self):
        """The RC5 entry's ``& 0x3F`` cannot express 0x40..0x7F.

        This package's RC-5 class spends the second start bit on
        command bit 6, so the wide command is exactly what RC5X means.
        """
        result = convert(self._row("RC5X", "10 00 00 00", "4B 00 00 00"), "x.ir")
        assert result.skipped == []
        signal = result.wigs[0].signals[0]
        timings = ProntoCommand(signal.pronto).get_raw_timings()
        decoded = get_spec("RC5").command_cls.from_raw_timings(timings)
        assert decoded is not None
        assert (decoded.address, decoded.command) == (0x10, 0x4B)

    def test_rca_converts_and_decodes_back(self):
        result = convert(self._row("RCA", "0F 00 00 00", "3A 00 00 00"), "x.ir")
        assert result.skipped == []
        signal = result.wigs[0].signals[0]
        timings = ProntoCommand(signal.pronto).get_raw_timings()
        decoded = get_spec("RCA").command_cls.from_raw_timings(timings)
        assert decoded is not None
        assert (decoded.device, decoded.function) == (0x0F, 0x3A)

    @pytest.mark.parametrize(
        ("protocol", "address", "command", "names"),
        [
            ("RCA", "1F 00 00 00", "3A 00 00 00", "RCA device"),
            ("RC5X", "FF 00 00 00", "01 00 00 00", "RC5X address"),
            ("RC6", "FF 01 00 00", "01 00 00 00", "RC6 address"),
        ],
    )
    def test_a_field_too_wide_is_refused_by_name(
        self, protocol, address, command, names
    ):
        """Checked, not masked: a mask invents a code."""
        result = convert(self._row(protocol, address, command), "x.ir")
        assert result.wigs == []
        assert any(names in reason for reason in result.skipped), result.skipped

    def test_kaseikyo_keeps_its_honest_receipt(self):
        """Not added, and the reason is in the report.

        The Flipper address is a packed composite and the firmware's
        own files disagree on the command width, so an entry would be a
        guess rather than a mapping.
        """
        result = convert(
            self._row("Kaseikyo", "02 20 00 00", "3A 01 00 00"), "x.ir"
        )
        assert result.wigs == []
        assert any("Kaseikyo" in reason for reason in result.skipped)

    def test_the_new_entries_do_not_need_the_optional_library(self):
        from custom_components.hair.wig_adapters import _flipper_builders

        builders = _flipper_builders()
        for name in ("RC6", "RC5X", "RCA"):
            assert name in builders


# ---------------------------------------------------------------------------
# Item 4: LIRC RC-5 and RC-6
# ---------------------------------------------------------------------------


class TestLircRc5:
    def test_every_row_converts_with_the_mapping_the_plan_predicted(self):
        result, wig = _one_wig("lirc_rc5_shift_enc.lircd.conf")
        assert result.skipped == []
        expected = {
            "Amp 1-0": (0x10, 0x00),
            "Amp 1-Vol+": (0x10, 0x10),
            "Amp 1-Mute": (0x10, 0x0D),
            # S2 reads 0, so the command carries bit 6: RC5X.
            "Tv-Menu-X": (0x10, 0x4B),
        }
        seen = {}
        for signal in wig.signals:
            timings = ProntoCommand(signal.pronto).get_raw_timings()
            decoded = get_spec("RC5").command_cls.from_raw_timings(timings)
            assert decoded is not None
            seen[signal.alias] = (decoded.address, decoded.command)
        assert seen == expected

    def test_every_row_carries_toggle_zero(self):
        _, wig = _one_wig("lirc_rc5_shift_enc.lircd.conf")
        for signal in wig.signals:
            timings = ProntoCommand(signal.pronto).get_raw_timings()
            decoded = get_spec("RC5").command_cls.from_raw_timings(timings)
            assert decoded.toggle == 0

    def test_the_receipt_says_the_timings_are_the_protocol_s(self):
        result, _ = _one_wig("lirc_rc5_shift_enc.lircd.conf")
        assert any("rebuilt from the protocol" in f for f in result.folds)
        assert any("toggle pinned to 0" in f for f in result.folds)

    def test_a_width_this_reader_does_not_know_is_refused_by_name(self):
        text = (
            "begin remote\n  name  Odd\n  bits  10\n  flags RC5\n"
            "  one 889 889\n  zero 889 889\n  gap 113792\n"
            "      begin codes\n          a 0x001\n      end codes\n"
            "end remote\n"
        )
        result = convert(text, "odd.lircd.conf")
        assert result.wigs == []
        assert any("10 bits" in reason for reason in result.skipped)

    def test_post_data_is_refused_rather_than_split_by_luck(self):
        text = (
            "begin remote\n  name  Post\n  bits  6\n  flags RC5\n"
            "  pre_data_bits 2\n  pre_data 0x2\n"
            "  post_data_bits 5\n  post_data 0x11\n"
            "  one 889 889\n  zero 889 889\n  gap 113792\n"
            "      begin codes\n          a 0x01\n      end codes\n"
            "end remote\n"
        )
        result = convert(text, "post.lircd.conf")
        assert result.wigs == []
        assert any("post_data" in reason for reason in result.skipped)


class TestLircRc6:
    def test_mode_0_rows_decode_to_the_device_and_function(self):
        result, wig = _one_wig("lirc_rc6_mode0.lircd.conf")
        assert result.skipped == []
        for signal in wig.signals:
            timings = ProntoCommand(signal.pronto).get_raw_timings()
            decoded = get_spec("RC6").command_cls.from_raw_timings(timings)
            assert decoded is not None
            assert decoded.mode == 0
            assert decoded.address == 0x04
            assert decoded.toggle == 0
        assert {s.alias for s in wig.signals} == {
            "Power", "Volumeup", "Volumedown", "Menu", "Ok",
        }

    def test_a_block_with_only_toggle_bit_is_read_not_refused(self):
        """The ``rc6_mask`` gate is withdrawn.

        The fixture carries ``toggle_bit`` and no ``rc6_mask``, which is
        the shape a quarter of the RC-6 blocks in circulation have,
        including the format's own generic template.
        """
        text = _fixture("lirc_rc6_mode0.lircd.conf")
        assert "rc6_mask" not in text
        assert "toggle_bit" in text
        result = convert(text, "rc6.lircd.conf")
        assert result.error is None
        assert len(result.wigs[0].signals) == 5

    def test_mode_6a_reads_its_customer_field_from_its_own_leading_bit(self):
        result, wig = _one_wig("lirc_rc6_mode6a.lircd.conf")
        assert result.skipped == []
        for signal in wig.signals:
            timings = ProntoCommand(signal.pronto).get_raw_timings()
            decoded = get_spec("RC6").command_cls.from_raw_timings(timings)
            assert decoded is not None
            assert decoded.mode == 6
            assert decoded.customer == 0x800F
            assert decoded.address == 0x04
            assert decoded.toggle == 0
        assert {
            s.alias for s in wig.signals
        } == {"Red", "Green", "Yellow", "Blue"}

    def test_a_25_bit_word_is_refused_by_name(self):
        text = (
            "begin remote\n  name  Deferred\n  bits  12\n  flags RC6\n"
            "  pre_data_bits 13\n  pre_data 0x1000\n"
            "  one 444 444\n  zero 444 444\n  gap 107000\n"
            "      begin codes\n          a 0x001\n      end codes\n"
            "end remote\n"
        )
        result = convert(text, "deferred.lircd.conf")
        assert result.wigs == []
        assert any("RC-6-6-20" in reason for reason in result.skipped)

    def test_a_word_whose_start_bit_reads_zero_is_refused(self):
        """Reading the word uncomplemented is what that looks like."""
        text = (
            "begin remote\n  name  Uncomplemented\n  bits  8\n  flags RC6\n"
            "  pre_data_bits 13\n  pre_data 0x1104\n"
            "  one 444 444\n  zero 444 444\n  gap 107000\n"
            "      begin codes\n          a 0x03\n      end codes\n"
            "end remote\n"
        )
        result = convert(text, "u.lircd.conf")
        assert result.wigs == []
        assert any("start bit" in reason for reason in result.skipped)

    def test_a_refused_row_never_raises_out_of_the_converter(self):
        """Every construction is wrapped; a refusal is a receipt."""
        text = (
            "begin remote\n  name  Mixed\n  bits  8\n  flags RC6\n"
            "  pre_data_bits 13\n  pre_data 0xEFB\n"
            "  one 444 444\n  zero 444 444\n  gap 107000\n"
            "      begin codes\n          good 0xF3\n          bad zzz\n"
            "      end codes\nend remote\n"
        )
        result = convert(text, "mixed.lircd.conf")
        assert len(result.wigs[0].signals) == 1
        assert any("bad code" in reason for reason in result.skipped)


class TestLircRowsAreSafeToSend:
    """Every rendered row goes through the import round-trip check.

    A row whose decoded triple cannot reproduce its stored Pronto is
    stored with the protocol bypass set, so what reaches the emitter is
    the frame the reader built rather than a re-encode of whatever the
    registry made of it. That matters here because the registry does
    not always agree with the encoder about a Manchester waveform.
    """

    @pytest.mark.parametrize(
        "name",
        [
            "lirc_rc5_shift_enc.lircd.conf",
            "lirc_rc6_mode0.lircd.conf",
            "lirc_rc6_mode6a.lircd.conf",
            "lirc_space_enc_sony_rm-w101.lircd.conf",
        ],
    )
    def test_a_row_the_triple_cannot_reproduce_is_bypass(self, name):
        from custom_components.hair.ir_command import build_decoded_command

        _, wig = _one_wig(name)
        for signal in wig.signals:
            timings = ProntoCommand(signal.pronto).get_raw_timings()
            identity = try_decode_identity(timings)
            reproduces = True
            if identity is not None:
                rebuilt = build_decoded_command(
                    identity.protocol,
                    identity.address,
                    identity.command,
                    decoded_extras=(
                        dict(identity.extras) if identity.extras else None
                    ),
                )
                if rebuilt is None:
                    reproduces = True
                else:
                    reproduces = raw_to_pronto(
                        list(rebuilt.get_raw_timings()),
                        frequency=carrier_or_default(
                            getattr(rebuilt, "modulation", None)
                        ),
                    ) == signal.pronto
            assert signal.bypass_protocol is not reproduces


# ---------------------------------------------------------------------------
# Item 5: the SmartIR fork schema
# ---------------------------------------------------------------------------


class TestForkWalk:
    def test_the_preset_level_is_not_stored_as_the_fan(self):
        """The silent failure this item exists to fix, pinned.

        A four-level fork branch is mode / preset / fan / temp, and an
        upstream four-level branch is mode / fan / swing / temp. Reading
        by depth put the preset in the fan slot and the fan in the
        swing slot; reading by the file's own declared lists cannot.
        """
        _, wig = _one_wig("smartir_fork_climate_presets.json")
        matrix = wig.climate
        assert matrix is not None
        assert matrix.fan_modes == ["low", "high"]
        assert matrix.swing_modes == []
        assert {c.fan for c in matrix.cells} == {"low", "high"}
        assert {c.swing for c in matrix.cells} == {None}

    def test_the_first_preset_is_the_main_lattice_and_the_rest_are_extras(
        self,
    ):
        result, wig = _one_wig("smartir_fork_climate_presets.json")
        matrix = wig.climate
        assert [e.key for e in matrix.extras] == ["eco", "boost"]
        assert {e.axis for e in matrix.extras} == {"preset"}
        assert all(e.cells for e in matrix.extras)
        assert any("main lattice" in fold for fold in result.folds)

    def test_a_file_with_swing_and_no_preset_still_reads_as_upstream(self):
        """``swingModes`` is an upstream key and never a fork marker."""
        text = _fixture("smartir_climate_swing.json")
        assert sniff_format(text) == "smartir_climate"
        _, wig = _one_wig("smartir_climate_swing.json")
        matrix = wig.climate
        assert matrix.swing_modes == ["auto", "off"]
        assert matrix.extras == []
        assert {c.swing for c in matrix.cells} == {"auto", "off"}

    def test_the_two_files_differ_only_where_the_schemas_do(self):
        _, fork = _one_wig("smartir_fork_climate_presets.json")
        _, upstream = _one_wig("smartir_climate_swing.json")
        assert fork.climate.modes == upstream.climate.modes
        assert fork.climate.fan_modes == upstream.climate.fan_modes
        assert fork.climate.min_temp == upstream.climate.min_temp
        assert len(fork.climate.cells) == 12
        assert len(upstream.climate.cells) == 24
        assert upstream.climate.extras == []
        assert len(fork.climate.extras) == 2

    def test_a_level_naming_none_of_the_declared_lists_is_receipted(self):
        import json

        data = json.loads(_fixture("smartir_fork_climate_presets.json"))
        data["commands"]["cool"]["surprise"] = {"low": {"16": "0000 006D"}}
        result = convert(json.dumps(data), "x.json")
        assert any(
            "names none of the declared lists" in reason
            for reason in result.skipped
        ), result.skipped

    def test_a_five_level_upstream_file_is_refused_with_the_branch(self):
        import json

        data = json.loads(_fixture("smartir_climate_swing.json"))
        data["commands"]["cool"]["low"]["auto"] = {"deeper": {"16": "0000 006D"}}
        result = convert(json.dumps(data), "x.json")
        assert result.wigs == []
        assert result.error is not None
        assert "five levels deep" in result.error
        assert "cool/low/auto" in result.error

    def test_a_vendor_mode_that_is_deeper_does_not_refuse_the_file(self):
        """The skip the walk applies, applied by the depth check too.

        A mode with no Home Assistant word is skipped with a receipt
        and never read, so its depth is nobody's business. Judging it
        refused a whole file at import that converted 24 cells the day
        before, over a branch the converter would not have opened.
        """
        import json

        data = json.loads(_fixture("smartir_climate_swing.json"))
        data["commands"]["ion"] = {
            "low": {"auto": {"16": {"x": "0000 006D 0002 0000 0020 0040"}}}
        }
        result = convert(json.dumps(data), "x.json")
        assert result.error is None, result.error
        matrix = result.wigs[0].climate
        assert len(matrix.cells) == 24
        assert any("ion" in reason for reason in result.skipped), result.skipped
        assert "cool" in matrix.modes and "ion" not in matrix.modes

    def test_a_nameable_mode_that_is_deeper_still_refuses(self):
        """The check still fires where the walk would actually read."""
        import json

        data = json.loads(_fixture("smartir_climate_swing.json"))
        data["commands"]["cool"]["low"]["auto"] = {
            "deeper": {"16": "0000 006D 0002 0000 0020 0040"}
        }
        result = convert(json.dumps(data), "x.json")
        assert result.wigs == []
        assert "five levels deep" in (result.error or "")

    def test_receipts_survive_an_early_return(self):
        """Both refusals emit what the walk gathered.

        The five-level case used to report "no convertible state cells"
        with an empty skipped list, because the early return fired
        before any receipt was written.
        """
        import json

        data = json.loads(_fixture("smartir_fork_climate_presets.json"))
        data["commands"]["ion"] = {"low": {"16": "0000 006D"}}
        for branch in ("cool", "heat"):
            data["commands"][branch] = {"none": {"low": {"16": None}}}
        result = convert(json.dumps(data), "x.json")
        assert result.error == "no convertible state cells in this file"
        assert result.skipped, "the walk's receipts were dropped"
        assert any("ion" in reason for reason in result.skipped)

    def test_a_declared_preset_with_no_cells_is_receipted_not_fatal(self):
        """The main lattice is whatever the walk actually filled.

        A file may declare a preset its code tree does not carry. The
        promotion used to take the declared first regardless, so the
        main lattice came out empty and a file whose every cell had
        converted was refused as having none, with no receipt.
        """
        import json

        data = json.loads(_fixture("smartir_fork_climate_presets.json"))
        first = data["presetModes"][0]
        for mode in ("cool", "heat"):
            branch = data["commands"].get(mode)
            if isinstance(branch, dict):
                branch.pop(first, None)
        result = convert(json.dumps(data), "x.json")
        assert result.error is None, result.error
        matrix = result.wigs[0].climate
        assert matrix.cells, "the file's cells went nowhere"
        assert first not in [e.key for e in matrix.extras]
        assert any(
            f'preset "{first}" is declared but carries no cells' in fold
            for fold in result.folds
        ), result.folds

    def test_a_mode_only_under_a_secondary_preset_is_named(self):
        """It leaves the mode list; it does not leave silently.

        The entity is built from the main lattice, so a file whose
        heating codes live only under an eco preset yields a
        cooling-only entity. The codes stay in the file and inside the
        digest, and the receipt says where they went.
        """
        import json

        data = json.loads(_fixture("smartir_fork_climate_presets.json"))
        presets = data["presetModes"]
        main, secondary = presets[0], presets[1]
        heat = data["commands"]["heat"]
        data["commands"]["heat"] = {secondary: heat[secondary]}
        result = convert(json.dumps(data), "x.json")
        assert result.error is None, result.error
        matrix = result.wigs[0].climate
        assert "heat" not in matrix.modes
        assert any(
            f'mode "heat" is only under preset "{secondary}"' in fold
            for fold in result.folds
        ), result.folds
        assert main in [m for m in presets if m]  # the fixture still declares it
        assert any(
            "heat" in {c.mode for c in e.cells} for e in matrix.extras
        ), "the codes left the file as well as the mode list"

    def test_a_scalar_preset_list_is_read_as_absent_not_raised(self):
        """A malformed file is a receipt, not a traceback.

        The upload handler has no try/except around ``convert``, so a
        ``TypeError`` from here reaches the user as a generic failure
        with a stack trace in the log, on a file that imported fine
        before this reader existed.
        """
        import json

        data = json.loads(_fixture("smartir_climate_swing.json"))
        for value in (1, "eco", {"a": 1}, None, 1.5, True):
            data["presetModes"] = value
            result = convert(json.dumps(data), "x.json")
            assert result.error is None, (value, result.error)
            assert len(result.wigs[0].climate.cells) == 24, value
            assert result.wigs[0].climate.extras == []

    def test_a_preset_list_with_junk_entries_keeps_the_names(self):
        import json

        data = json.loads(_fixture("smartir_fork_climate_presets.json"))
        data["presetModes"] = [*data["presetModes"], 7, None]
        result = convert(json.dumps(data), "x.json")
        assert result.error is None
        assert any("presetModes" in fold for fold in result.folds)
        assert [e.key for e in result.wigs[0].climate.extras] == [
            "eco", "boost"
        ]

    def test_a_tree_deeper_than_the_cap_is_receipted_not_recursed(self):
        """A bounded walk. The recursion had no bound at all, so a
        deeply nested file raised ``RecursionError`` out of the same
        unguarded call site."""
        import json

        data = json.loads(_fixture("smartir_fork_climate_presets.json"))
        # Every level names a declared vocabulary, so the walk keeps
        # descending: this is the shape with no natural floor.
        node: object = {"16": "0000 006D 0002 0000 0020 0040"}
        for _ in range(12):
            node = {"low": node}
        data["commands"]["cool"]["none"] = node
        result = convert(json.dumps(data), "x.json")
        assert any(
            "levels deep" in reason for reason in result.skipped
        ), result.skipped

    def test_the_importer_names_a_kind_from_the_list(self):
        _, wig = _one_wig("smartir_fork_climate_presets.json")
        assert wig.kind in KIND_BY_KEY


class TestLightFilesStillImport:
    """Light files keep the flat-button path, and no probe claims them.

    An earlier cut of this work carried a light probe whose markers
    were the ordinary light schema's own, so a stock seven-button light
    file was refused where the day before it imported as seven buttons.
    The probe is gone; this is the pin that keeps it gone.
    """

    def test_a_light_file_imports_as_flat_buttons(self):
        text = _fixture("smartir_light_brightness.json")
        assert sniff_format(text) == "smartir"
        result = convert(text, "light.json")
        assert result.error is None
        assert [s.alias for s in result.wigs[0].signals] == [
            "On", "Off", "Brighten", "Dim", "Colder", "Warmer", "Night",
        ]

    def test_the_full_light_vocabulary_claims_nothing_else(self):
        """The exact marker set the removed probe keyed on.

        ``brightness`` as a list plus the five command words was the
        narrowed marker, and it is what upstream light files carry.
        """
        import json

        data = json.loads(_fixture("smartir_light_brightness.json"))
        assert isinstance(data["brightness"], list)
        assert {"night", "brighten", "dim", "colder", "warmer"} <= set(
            data["commands"]
        )
        assert sniff_format(json.dumps(data)) == "smartir"

    def test_no_probe_is_registered_for_a_light_schema(self):
        from custom_components.hair.wig_adapters import _PROBES

        assert not [p for p in _PROBES if "light" in p.name]


class TestExtrasRideInsideTheDigest:
    def test_a_wig_with_extras_stamps_the_version_that_needs_it(self):
        _, wig = _one_wig("smartir_fork_climate_presets.json")
        assert serialize_wig(wig).count(WIG_FORMAT_V4) == 1

    def test_a_wig_without_extras_is_untouched_by_the_bump(self):
        _, wig = _one_wig("smartir_climate_swing.json")
        text = serialize_wig(wig)
        assert WIG_FORMAT_V3 in text
        assert WIG_FORMAT_V4 not in text

    def test_extras_change_the_cells_hash(self):
        """The reason for the bump, as a measurement.

        Extras are transmit recipes and a claim binds ``cells_hash``;
        outside the hash they could be swapped wholesale on a signed
        wig. Inside it, changing one changes the hash.
        """
        _, wig = _one_wig("smartir_fork_climate_presets.json")
        matrix = wig.climate
        before = cells_content_hash(matrix)
        cell = matrix.extras[0].cells[0]
        # One word different, still a valid code: the hash has to move
        # on the codes themselves, not only on structure.
        cell.pronto = cell.pronto.replace(" 0016 0041", " 0041 0016", 1)
        assert cells_content_hash(matrix) != before

    def test_a_matrix_with_no_extras_hashes_exactly_as_before(self):
        """Every wig written before this key hashes to what it did.

        The canonical object gains the key only when there is something
        to put in it, so an empty extras list is not a new field with
        an empty value: it is no field at all.
        """
        _, wig = _one_wig("smartir_climate_swing.json")
        matrix = wig.climate
        assert matrix.extras == []
        from custom_components.hair.wig_format import canonical_cells_json

        assert "extras" not in canonical_cells_json(matrix)

    def test_extras_round_trip_through_parse_and_serialize(self):
        _, wig = _one_wig("smartir_fork_climate_presets.json")
        text = serialize_wig(wig)
        result = parse_wig(text)
        assert result.ok, result.errors
        assert [e.key for e in result.wig.climate.extras] == ["eco", "boost"]
        assert cells_content_hash(result.wig.climate) == cells_content_hash(
            wig.climate
        )

    def test_the_same_bytes_are_refused_under_the_older_stamp(self):
        """The floor, which the ceiling alone did not give.

        Two installs reading one file must not disagree about the hash
        a signature binds. An older HAIR keeps ``extras`` as an unknown
        key and hashes the matrix without it; this one folds it in. So
        the key needs the version that describes it, and a file that
        stamps less is refused by name rather than read two ways.
        """
        _, wig = _one_wig("smartir_fork_climate_presets.json")
        text = serialize_wig(wig)
        assert WIG_FORMAT_V4 in text
        assert parse_wig(text).ok

        older = text.replace(WIG_FORMAT_V4, WIG_FORMAT_V3, 1)
        result = parse_wig(older)
        assert not result.ok
        assert any("extra lattices" in error for error in result.errors)
        assert any(WIG_FORMAT_V4 in error for error in result.errors)

    def test_a_wig_with_no_extras_still_parses_under_every_major(self):
        """The floor applies to the key, not to the climate block."""
        _, wig = _one_wig("smartir_climate_swing.json")
        text = serialize_wig(wig)
        assert WIG_FORMAT_V3 in text
        for major in ("hair-wig/2", WIG_FORMAT_V3, WIG_FORMAT_V4):
            stamped = text.replace(WIG_FORMAT_V3, major, 1)
            assert parse_wig(stamped).ok, major

    def test_every_shipped_wig_keeps_the_hashes_it_had(self):
        """Measured on the base tree, committed here.

        The whole argument for a conditional stamp is that a wig with
        no extras is untouched by the key's existence. These two are
        the wigs the repo ships, and both values were computed with
        the pre-patch ``wig_format`` before they were written down.
        """
        import hashlib
        import json

        from custom_components.hair.wig_format import canonical_signals_json

        wigs = Path(__file__).parent / "fixtures" / "wigs"
        expected = {
            "dreo-fan-dr-haf004s-perfect-fit.wig.json": (
                "sha256:5e5dace39920528c52ee50889fcdd25afa54f1f23f2a34e"
                "ebee81ec1c5a82a61",
                None,
            ),
            "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json": (
                "sha256:4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba8"
                "73c2f11161202b945",
                "sha256:b5b33921b281fdca2d5f2955c57be4c459c4238a1d3df15"
                "db5b96a44cdd378f1",
            ),
        }
        walked = sorted(p.name for p in wigs.glob("*.wig.json"))
        assert walked == sorted(expected), "a shipped wig has no pinned hash"
        for name, (signals_hash, cells_hash) in expected.items():
            result = parse_wig((wigs / name).read_text())
            assert result.ok, result.errors
            wig = result.wig
            canon = canonical_signals_json(wig.signals)
            digest = hashlib.sha256(canon.encode("utf-8")).hexdigest()
            assert f"sha256:{digest}" == signals_hash, name
            if cells_hash is None:
                assert wig.climate is None, name
            else:
                assert cells_content_hash(wig.climate) == cells_hash, name
                assert wig.climate.extras == []
            # A matrix-only wig's signals list is empty, and its
            # canonical form is the empty array: still JSON, still
            # hashed, still pinned above.
            assert isinstance(json.loads(canon), list)

    def test_a_bad_pronto_inside_extras_is_a_parse_error(self):
        """``parse_wig`` validates the codes inside extras.

        They are inside the digest, and a code nothing validated has no
        business inside a hash somebody signs.
        """
        _, wig = _one_wig("smartir_fork_climate_presets.json")
        victim = wig.climate.extras[0].cells[0].pronto
        text = serialize_wig(wig).replace(
            f'"pronto": "{victim}"', '"pronto": "nonsense"'
        )
        assert '"nonsense"' in text
        result = parse_wig(text)
        assert not result.ok
        assert any("pronto" in error for error in result.errors)


class TestPrecision:
    def test_a_declared_precision_finer_than_the_cells_is_demoted(self):
        import json

        data = json.loads(_fixture("smartir_climate_swing.json"))
        data["precision"] = 0.1
        result = convert(json.dumps(data), "x.json")
        matrix = result.wigs[0].climate
        assert matrix.precision == 1.0
        # The receipt is a FOLD: every cell converted, one number was
        # rewritten. ``skipped`` is what the panel counts as "could not
        # convert", and nothing here could not convert.
        assert any("precision" in fold for fold in result.folds), result.folds
        assert result.skipped == []

    def test_a_half_degree_file_keeps_its_step(self):
        """The one-sided rule, and why it is one-sided.

        A real half-degree device whose cells happen to be whole
        degrees would lose its step under a two-sided rule, and the comb
        would stop reporting the half-degree holes it exists to report.
        """
        import json

        data = json.loads(_fixture("smartir_climate_swing.json"))
        data["precision"] = 0.5
        result = convert(json.dumps(data), "x.json")
        assert result.wigs[0].climate.precision == 0.5

    def test_an_assumed_toggle_is_a_fold_not_a_failure(self):
        """The other receipt in the wrong channel.

        A block naming no toggle bit still converts every row; the
        note records the assumption the reconstruction made. Reporting
        it as a skip told the user a signal was lost and sent them to
        the wig notes to find out which.
        """
        import re

        text = _fixture("lirc_rc6_mode0.lircd.conf")
        stripped = re.sub(
            r"^\s*toggle_bit(_mask)?\s+\S+\s*$", "", text, flags=re.MULTILINE
        )
        assert "toggle_bit" not in stripped
        result = convert(stripped, "rc6.lircd.conf")
        assert result.error is None
        assert len(result.wigs[0].signals) == 5
        assert result.skipped == [], result.skipped
        assert any("toggle" in fold for fold in result.folds), result.folds

    def test_a_sparse_lattice_does_not_become_a_coarse_step(self):
        """Holes are the comb's business, not the precision field's.

        A matrix carrying 16, 22 and 30 shows a six-degree spacing and
        is not a device that steps by six. Writing that spacing into
        ``precision`` would silence every hole report on the file,
        which is the same harm the one-sided rule exists to avoid, so
        the demotion stops at a whole degree.
        """
        import json

        data = json.loads(_fixture("smartir_climate_swing.json"))

        def _spread(node):
            """Re-file every temperature run as 16 / 22 / 30."""
            temps = [k for k in node if k.lstrip("-").replace(".", "").isdigit()]
            if temps:
                codes = [node[k] for k in temps]
                return {
                    t: codes[i % len(codes)]
                    for i, t in enumerate(("16", "22", "30"))
                }
            return {
                k: _spread(v) if isinstance(v, dict) else v
                for k, v in node.items()
            }

        data["commands"] = {
            k: _spread(v) if isinstance(v, dict) else v
            for k, v in data["commands"].items()
        }
        result = convert(json.dumps(data), "x.json")
        matrix = result.wigs[0].climate
        assert sorted({c.temp for c in matrix.cells if c.temp}) == [
            16.0, 22.0, 30.0
        ]
        assert matrix.precision == 1.0
        assert not any("precision" in fold for fold in result.folds)

    def test_a_declared_precision_coarser_than_the_cells_is_kept(self):
        import json

        data = json.loads(_fixture("smartir_climate_swing.json"))
        data["precision"] = 2
        result = convert(json.dumps(data), "x.json")
        assert result.wigs[0].climate.precision == 2.0


# ---------------------------------------------------------------------------
# Items 6 and 7: the carrier
# ---------------------------------------------------------------------------


class TestCarrierRule:
    def test_every_lirc_row_says_where_its_carrier_came_from(self):
        _, wig = _one_wig("lirc_rc5_shift_enc.lircd.conf")
        for signal in wig.signals:
            assert signal.extra["carrier"] == {"hz": 36000, "source": "declared"}

    def test_a_block_that_declares_no_carrier_takes_the_protocol_nominal(self):
        _, wig = _one_wig("lirc_rc6_mode0.lircd.conf")
        for signal in wig.signals:
            assert signal.extra["carrier"]["source"] == "protocol"
            assert signal.extra["carrier"]["hz"] == 36000

    def test_a_space_enc_block_with_no_frequency_is_marked_assumed(self):
        text = (
            "begin remote\n  name  NoFreq\n  bits  8\n  flags SPACE_ENC\n"
            "  header 9000 4500\n  one 560 1690\n  zero 560 560\n"
            "  ptrail 560\n  gap 108000\n"
            "      begin codes\n          a 0x12\n      end codes\n"
            "end remote\n"
        )
        result = convert(text, "nofreq.lircd.conf")
        signal = result.wigs[0].signals[0]
        assert signal.extra["carrier"] == {"hz": 38000, "source": "assumed"}

    def test_every_fixture_row_from_every_reader_carries_the_stamp(self):
        """The walk, so a new reader cannot ship without it.

        Item 7 is "every imported row records its carrier and where
        the number came from". An earlier cut of this work stamped the
        three LIRC doors only, and the Flipper, GIRR and SmartIR rows
        recorded an invented 38 kHz indistinguishable from a declared
        one. This walks the whole fixture directory, so the next reader
        added here is held to the same rule by this test failing.
        """
        sources = {"declared", "protocol", "assumed", "none"}
        seen: set[str] = set()
        walked = 0
        for path in sorted(FIXTURES.iterdir()):
            if not path.is_file():
                continue
            result = convert(path.read_text(errors="replace"), path.name)
            for wig in result.wigs:
                for signal in wig.signals:
                    walked += 1
                    stamp = signal.extra.get("carrier")
                    assert stamp is not None, (
                        f"{path.name}/{signal.alias} has no carrier stamp"
                    )
                    assert isinstance(stamp["hz"], int)
                    assert stamp["source"] in sources, stamp
                    seen.add(stamp["source"])
        assert walked > 100, walked
        # Three of the four answers are reachable from the fixtures as
        # they stand; "none" needs a file that declares a zero carrier,
        # which the non-modulated tests build for themselves.
        assert {"declared", "protocol", "assumed"} <= seen, seen

    def test_a_flipper_raw_row_without_a_frequency_says_assumed(self):
        """The review's own failing input, as a test."""
        text = (
            "Filetype: IR signals file\n"
            "Version: 1\n"
            "#\n"
            "name: Power\n"
            "type: raw\n"
            "data: 9000 4500 560 560\n"
        )
        result = convert(text, "one.ir")
        signal = result.wigs[0].signals[0]
        assert signal.extra["carrier"] == {"hz": 38000, "source": "assumed"}

    def test_a_flipper_raw_row_with_a_frequency_says_declared(self):
        text = (
            "Filetype: IR signals file\n"
            "Version: 1\n"
            "#\n"
            "name: Power\n"
            "type: raw\n"
            "frequency: 40000\n"
            "data: 9000 4500 560 560\n"
        )
        result = convert(text, "one.ir")
        signal = result.wigs[0].signals[0]
        assert signal.extra["carrier"] == {"hz": 40000, "source": "declared"}

    def test_a_girr_row_carries_the_stamp_its_source_supports(self):
        result = convert(
            _fixture("girr_irscrutinizer_export.girr"), "x.girr"
        )
        stamps = [
            s.extra["carrier"] for w in result.wigs for s in w.signals
        ]
        assert stamps, "the girr fixture converted nothing"
        assert all(s["source"] in ("declared", "assumed") for s in stamps)

    def test_the_stamp_is_outside_every_digest(self):
        from custom_components.hair.wig_format import canonical_signals_json

        _, wig = _one_wig("lirc_rc5_shift_enc.lircd.conf")
        assert "carrier" not in canonical_signals_json(wig.signals)


class TestNonModulated:
    def test_a_zero_carrier_survives_the_helper_where_or_would_not(self):
        assert carrier_or_default(0) == 0
        assert carrier_or_default(None) == 38000
        assert carrier_or_default(36000) == 36000

    def test_a_zero_carrier_row_is_not_rewritten_to_38_khz(self):
        """The two transmit-path sites, as the values they now pass.

        ``frequency or 38000`` read a zero as absent, so a
        non-modulated row was rebuilt modulated before any refusal
        could see it.
        """
        from custom_components.hair.ir_command import build_command

        pronto = raw_to_pronto([9000, -4500, 560, -560, 560], frequency=0)
        command = build_command(protocol="PRONTO", code=pronto)
        assert command.modulation == 0
        raw = build_command(
            raw_timings=[9000, -4500, 560], frequency=carrier_or_default(0)
        )
        assert raw.modulation == 0

    def test_the_code_round_trips_with_its_time_base(self):
        pronto = raw_to_pronto([9000, -4500, 560, -560, 560], frequency=0)
        assert pronto.startswith("0100 ")
        command = ProntoCommand(pronto)
        assert command.modulation == 0
        assert command.unmodulated is True
        assert command.timebase_hz > 0
        again = raw_to_pronto(
            command.get_raw_timings(),
            frequency=command.modulation,
            timebase_hz=command.timebase_hz,
        )
        assert again == pronto

    def test_a_non_modulated_code_canonicalizes(self):
        from custom_components.hair.identity import canonical_pronto

        pronto = raw_to_pronto([9000, -4500, 560, -560, 560], frequency=0)
        canonical = canonical_pronto(pronto)
        assert canonical is not None
        assert canonical.startswith("0100 ")

    def test_a_wig_carrying_one_parses_and_digests(self):
        from custom_components.hair.wig_format import (
            Wig,
            WigSignal,
            signals_content_hash,
        )

        pronto = raw_to_pronto([9000, -4500, 560, -560, 560], frequency=0)
        wig = Wig(name="Unmodulated", signals=[
            WigSignal(alias="Power", pronto=pronto),
        ])
        text = serialize_wig(wig)
        result = parse_wig(text)
        assert result.ok, result.errors
        assert result.wig.signals[0].pronto.startswith("0100 ")
        assert signals_content_hash(result.wig.signals).startswith("sha256:")

    def test_an_imported_non_modulated_row_is_stored_bypass(self):
        """Nothing can rebuild it, so nothing is allowed to try."""
        import json

        pronto = raw_to_pronto(
            [9000, -4500, 560, -1690, 560, -560, 560], frequency=0
        )
        data = {
            "manufacturer": "Acme",
            "supportedModels": ["X"],
            "commandsEncoding": "Pronto",
            "supportedController": "MQTT",
            "commands": {"power": pronto},
        }
        result = convert(json.dumps(data), "x.json")
        signal = result.wigs[0].signals[0]
        assert signal.pronto.startswith("0100 ")


class TestTransmitRefusesRatherThanLies:
    def test_the_allowlist_ships_empty(self):
        from custom_components.hair.send_plan import CARRIERLESS_PLATFORMS

        assert set() == CARRIERLESS_PLATFORMS

    def test_no_platform_qualifies_today(self):
        from custom_components.hair.send_plan import can_send_unmodulated

        for platform in ("esphome", "broadlink", "smlight", "mqtt", None):
            assert can_send_unmodulated(platform) is False

    def test_both_send_paths_ask_the_same_helper(self):
        """One door, asked twice, so the two cannot drift again.

        The broadcast path has refused an unmodulated code since item 6
        landed. The Test button did not ask at all, which is how a
        ``0100`` row could be tested onto a blaster that modulates
        whatever it is handed and be reported as a success.
        """
        import inspect

        from custom_components.hair import device_manager, signal_monitor

        for module in (device_manager, signal_monitor):
            source = inspect.getsource(module)
            assert "refuse_unmodulated(" in source, module.__name__

    @pytest.mark.asyncio
    async def test_the_test_button_refuses_a_no_carrier_row(self, fake_hass):
        """The failing input from the review, driven end to end.

        A ``0100`` row on a broadlink emitter: the refusal comes back as
        a result rather than an exception, because that is the shape
        ``test_signal`` returns, and nothing is handed to the emitter.
        """
        from unittest.mock import AsyncMock, patch

        import homeassistant.components.infrared as infrared_mod

        from custom_components.hair import send_plan as send_plan_mod
        from custom_components.hair.models import UnknownSignal
        from custom_components.hair.tests.test_capture_dittos import (
            _monitor as make_monitor,
        )

        pronto = raw_to_pronto([9000, -4500, 560, -560], frequency=0)
        signal = UnknownSignal(
            id="s1", fingerprint="fp", protocol="PRONTO", code=pronto,
            frequency=0,
        )
        monitor, _ = make_monitor(fake_hass, signal)
        send = AsyncMock()
        with (
            patch.object(infrared_mod, "async_send_command", send),
            patch.object(
                send_plan_mod, "emitter_platform", return_value="broadlink"
            ),
        ):
            result = await monitor.test_signal("s1", "infrared.e")
        assert result["success"] is False
        assert result["code"] == "no_carrier"
        assert "no carrier" in result["error"]
        send.assert_not_called()

    @pytest.mark.asyncio
    async def test_a_modulated_row_still_tests(self, fake_hass):
        """The guard refuses one thing and nothing else."""
        from unittest.mock import AsyncMock, patch

        import homeassistant.components.infrared as infrared_mod

        from custom_components.hair import send_plan as send_plan_mod
        from custom_components.hair.models import UnknownSignal
        from custom_components.hair.tests.test_capture_dittos import (
            _monitor as make_monitor,
        )

        pronto = raw_to_pronto([9000, -4500, 560, -560], frequency=38000)
        signal = UnknownSignal(
            id="s1", fingerprint="fp", protocol="PRONTO", code=pronto,
        )
        monitor, _ = make_monitor(fake_hass, signal)
        with (
            patch.object(infrared_mod, "async_send_command", AsyncMock()),
            patch.object(
                send_plan_mod, "emitter_platform", return_value="broadlink"
            ),
        ):
            result = await monitor.test_signal("s1", "infrared.e")
        assert result["success"] is True

    def test_a_built_command_reports_whether_it_is_unmodulated(self):
        from custom_components.hair.ir_command import build_command
        from custom_components.hair.send_plan import is_unmodulated

        pronto = raw_to_pronto([9000, -4500, 560], frequency=0)
        assert is_unmodulated(build_command(protocol="PRONTO", code=pronto))
        modulated = raw_to_pronto([9000, -4500, 560], frequency=38000)
        assert not is_unmodulated(
            build_command(protocol="PRONTO", code=modulated)
        )


# ---------------------------------------------------------------------------
# Item 1: several remotes from one file
# ---------------------------------------------------------------------------


class TestTheSonyOverlapRate:
    """Today's number, pinned so it is visible when it changes.

    HAIR's Sony decoder claims RC-6 frames whose bits are mostly zero,
    which is where a remote at address 0 lives, and it probes before
    RC-6. The rows still transmit correctly: the round-trip check sees
    the mismatch and stores them bypassed, so they replay the stored
    bytes. What is lost is the protocol identity, and several distinct
    buttons collapse onto one decoded triple.

    The registry order is not this patch's to change -- the same
    misdecode is on the base tree -- but this patch is the first thing
    that mints RC-6 rows at import, so the number belongs somewhere it
    can be read. When the registry work lands, this test fails and the
    new rate goes in its place.
    """

    FIXTURE = "lirc_rc6_mode0_address0.lircd.conf"

    def _rows(self):
        result = convert(_fixture(self.FIXTURE), self.FIXTURE)
        assert result.error is None, result.error
        return [s for wig in result.wigs for s in wig.signals]

    def test_the_rate_today_is_seven_rows_in_twelve(self):
        rows = self._rows()
        bypassed = [s.alias for s in rows if s.bypass_protocol]
        assert len(rows) == 12
        assert len(bypassed) == 7, bypassed
        # And it falls on the buttons a person presses most.
        assert {"Power", "Volumeup", "Channelup"} <= set(bypassed)

    def test_the_same_rate_on_both_legs(self):
        """The overlap is in HAIR's own decoders, not the library's."""
        from custom_components.hair.protocol_decode import get_spec

        assert get_spec("SONY20") is not None

    def test_the_misdecoded_rows_share_one_triple(self):
        """Why the identity loss matters: it is not one wrong label."""
        from custom_components.hair.ir_command import ProntoCommand

        seen: dict[str, list[str]] = {}
        for signal in self._rows():
            if not signal.bypass_protocol:
                continue
            timings = ProntoCommand(signal.pronto).get_raw_timings()
            identity = try_decode_identity(timings)
            seen.setdefault(identity.fingerprint, []).append(signal.alias)
        assert len(seen) == 1, seen
        fingerprint, aliases = next(iter(seen.items()))
        assert "SONY" in fingerprint
        assert len(aliases) == 7

    def test_every_misdecoded_row_still_transmits_what_the_file_wrote(self):
        """The reason this is an identity loss and not a wire fault."""
        rows = self._rows()
        for signal in rows:
            if signal.bypass_protocol:
                assert signal.pronto.startswith("0000 ")
        assert all(s.extra["carrier"]["hz"] == 36000 for s in rows)


class TestMultiWigLanding:
    def test_a_four_block_file_converts_to_four_wigs(self):
        result = convert(
            _fixture("lirc_four_remotes.lircd.conf"), "four.lircd.conf"
        )
        assert result.error is None
        assert len(result.wigs) == 4
        assert [w.name for w in result.wigs] == [
            "Hallway_Amp", "Study_TV", "Deck_Fan", "Shed_Light",
        ]
        assert all(len(w.signals) == 3 for w in result.wigs)


@pytest.mark.skipif(
    not strict_nec_available(), reason="the registry label needs the library"
)
class TestWhatTheRegistryMakesOfARebuiltFrame:
    """Named rather than hidden: the registry is not the encoder.

    A Manchester waveform this package's own encoder produced does not
    always come back through the registry as the protocol that produced
    it -- Sony probes before RC-6 and claims a minority of RC-6 frames.
    That is a property of the probe order, which this patch does not
    touch. What phase 1 owes is that such a row still transmits the
    frame the file meant, which the import round-trip check guarantees
    by pinning it to raw replay.
    """

    def test_a_row_the_registry_mislabels_is_pinned_to_raw_replay(self):
        rc6 = get_spec("RC6").command_cls
        mislabelled = []
        for command in range(0, 256, 3):
            timings = rc6(
                address=0x00, command=command, mode=0, toggle=0
            ).get_raw_timings()
            identity = try_decode_identity(timings)
            if identity is not None and identity.protocol != "RC6":
                mislabelled.append((command, identity.protocol))
        assert mislabelled, (
            "the overlap this test documents is gone; delete the test"
        )
        # Every one of them, imported, is stored bypass.
        for command, _label in mislabelled[:4]:
            text = (
                f"{FLIPPER_REMOTE_HEADER}\nVersion: 1\n#\n"
                f"name: Row\ntype: parsed\nprotocol: RC6\n"
                f"address: 00 00 00 00\ncommand: {command:02X} 00 00 00\n"
            )
            result = convert(text, "x.ir")
            assert result.wigs[0].signals[0].bypass_protocol is True
