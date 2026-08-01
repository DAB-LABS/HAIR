"""Cold Cuts (v0.8.8): SmartIR climate import, checklist, resolution.

The census-pinned contracts (docs/internal/research on the owner's
side, restated in wig_adapters and wig_climate):

- Walk order is mode -> fan -> swing -> temp, detected per BRANCH.
- Vocabulary is verbatim: no humanizing, no case-normalizing on cells.
- Depth-0 extras become flat signals riding alongside the matrix.
- Unmappable-mode subtrees skip with a receipt; null cells count as
  absent states; "$"-prefixed keys are filtered at every level.
- The dimension checklist is a pure function of the climate block.
- v1 signal wigs keep their hash byte-for-byte (fittings unbroken).
"""
from __future__ import annotations

import base64
import json

from custom_components.hair.wig_adapters import convert, sniff_format
from custom_components.hair.wig_climate import (
    SECTION_FAN,
    SECTION_MODES,
    SECTION_SWING,
    SECTION_TEMP,
    SECTION_WRAP,
    cell_display_name,
    dimension_checklist,
    display_temp_str,
    exact_cell,
    matrix_summary,
    resolve_cell,
    state_display_name,
    unit_letter,
)
from custom_components.hair.wig_format import (
    ClimateCell,
    Wig,
    WigSignal,
    canonical_cells_json,
    cells_content_hash,
    parse_wig,
    serialize_wig,
    signals_content_hash,
    wig_content_hash,
)

PRONTO = "0000 006D 0002 0000 0020 0040 0020 0040"


def _b64(seed: int = 0x12) -> str:
    """A minimal valid Broadlink packet, varied by seed."""
    payload = bytes([seed, 0x24, 0x12, 0x12, 0x12, 0x24, 0x12, 0x12,
                     0x12, 0x24])
    packet = bytes([0x26, 0x00, len(payload), 0x00]) + payload
    return base64.b64encode(packet).decode()


def _smartir_file() -> str:
    """A trimmed corpus-shaped file: mixed depth, swing, extras, warts."""
    return json.dumps({
        "manufacturer": "Fixture",
        "supportedModels": ["FX-100"],
        "supportedController": "Broadlink",
        "commandsEncoding": "Base64",
        "minTemperature": 16.0,
        "maxTemperature": 30,
        "precision": 1,
        "operationModes": ["cool", "dry", "heat", "ion"],
        "fanModes": ["auto", "low", "high"],
        "swingModes": ["swing"],
        "commands": {
            "off": _b64(0x30),
            "on": _b64(0x31),
            "$comment": "filtered at every level",
            "cool": {
                "auto": {"16": _b64(0x40), "22": _b64(0x41),
                         "30": _b64(0x42)},
                "low": {"22": _b64(0x43), "23": None},
                "high": {"swing": {"22": _b64(0x44)}},
                "$comment": "also filtered",
            },
            "dry": {"auto": _b64(0x50), "low": _b64(0x51)},
            "heat": {"auto": {"22": _b64(0x60)}},
            "ion": {"auto": {"22": _b64(0x70)}},
            "on_once": _b64(0x71),
        },
    })


class TestAdapter:
    def test_sniffs_as_climate(self):
        assert sniff_format(_smartir_file()) == "smartir_climate"

    def test_walk_order_and_per_branch_depth(self):
        """cool/high sits behind a swing layer while cool/auto goes
        straight to temps; dry has no temperature at all. All in ONE
        file, all in one mode for the swing case (per-branch rule)."""
        result = convert(_smartir_file())
        assert result.error is None
        wig = result.wigs[0]
        m = wig.climate
        assert m is not None
        keyed = {(c.mode, c.fan, c.swing, c.temp) for c in m.cells}
        assert ("cool", "auto", None, 22.0) in keyed
        assert ("cool", "high", "swing", 22.0) in keyed
        assert ("dry", "auto", None, None) in keyed
        assert ("heat", "auto", None, 22.0) in keyed

    def test_vocab_verbatim_and_bounds(self):
        wig = convert(_smartir_file()).wigs[0]
        m = wig.climate
        assert m.modes == ["cool", "dry", "heat"]
        assert m.fan_modes == ["auto", "low", "high"]
        assert m.swing_modes == ["swing"]
        assert m.min_temp == 16.0 and m.max_temp == 30.0
        assert m.precision == 1.0
        assert m.on is not None
        assert wig.kind == "ac"

    def test_depth0_extra_becomes_flat_signal(self):
        wig = convert(_smartir_file()).wigs[0]
        assert [s.alias for s in wig.signals] == ["On Once"]

    def test_unmappable_subtree_and_null_cell_receipts(self):
        result = convert(_smartir_file())
        assert any('"ion"' in s for s in result.skipped)
        assert any("absent states" in s for s in result.skipped)
        # ion's lattice must NOT be in the matrix.
        assert all(c.mode != "ion" for c in result.wigs[0].climate.cells)

    def test_xiaomi_raw_refused(self):
        data = json.loads(_smartir_file())
        data["supportedController"] = "Xiaomi"
        data["commandsEncoding"] = "Raw"
        result = convert(json.dumps(data))
        assert result.error is not None and "Xiaomi" in result.error

    def test_esphome_raw_converts(self):
        data = json.loads(_smartir_file())
        data["supportedController"] = "ESPHome"
        data["commandsEncoding"] = "Raw"
        raw = "9000, -4500, 560, -560, 560, -1690"
        data["commands"] = {"off": raw, "cool": {"auto": {"22": raw}}}
        result = convert(json.dumps(data))
        assert result.error is None
        assert len(result.wigs[0].climate.cells) == 1

    def test_roundtrips_through_wig_format(self):
        wig = convert(_smartir_file()).wigs[0]
        text = serialize_wig(wig)
        # Both kinds stamp /3 from the recipe break on: removing
        # send_count from the cell canonical rolled matrix hashes too, so
        # a matrix wig has to refuse on an old install exactly as a flat
        # one does.
        assert '"format": "hair-wig/3"' in text
        parsed = parse_wig(text)
        assert parsed.ok, parsed.errors
        assert cells_content_hash(parsed.wig.climate) == \
            cells_content_hash(wig.climate)


class TestChecklist:
    def _matrix(self):
        return convert(_smartir_file()).wigs[0].climate

    def test_shape_and_order(self):
        rows = dimension_checklist(self._matrix())
        keys = [r.key for r in rows]
        assert keys[0] == "on"
        assert keys[-1] == "off"
        sections = [r.section for r in rows]
        # Sections appear in walk order.
        order = [SECTION_MODES, SECTION_FAN, SECTION_SWING, SECTION_TEMP]
        positions = [sections.index(s) for s in order if s in sections]
        assert positions == sorted(positions)
        assert sections[-1] == SECTION_WRAP

    def test_covers_every_dimension(self):
        rows = dimension_checklist(self._matrix())
        modes = {r.mode for r in rows if r.section == SECTION_MODES}
        assert modes == {"cool", "dry", "heat"}
        # Every fan of the richest mode (cool) is covered somewhere --
        # cool/auto's cell dedups into the MODES pass, by design.
        fans = {
            r.fan for r in rows
            if r.mode == "cool"
            and r.section in (SECTION_MODES, SECTION_FAN)
        }
        assert fans == {"auto", "low", "high"}
        temp_rows = [r for r in rows if r.section == SECTION_TEMP]
        assert {r.temp_role for r in temp_rows} == {"min", "max"}
        assert {r.temp for r in temp_rows} == {16.0, 30.0}

    def test_depth1_row_flagged_temp_less(self):
        rows = dimension_checklist(self._matrix())
        dry = next(r for r in rows if r.mode == "dry")
        assert dry.temp_less is True and dry.temp is None

    def test_deterministic(self):
        a = [r.key for r in dimension_checklist(self._matrix())]
        b = [r.key for r in dimension_checklist(self._matrix())]
        c = [r.key for r in dimension_checklist(
            convert(_smartir_file()).wigs[0].climate
        )]
        assert a == b == c

    def test_no_duplicate_keys(self):
        keys = [r.key for r in dimension_checklist(self._matrix())]
        assert len(keys) == len(set(keys))


class TestMatrixSummary:
    """The closet/device summary block (owner ruling 2026-07-28)."""

    def _matrix(self):
        return convert(_smartir_file()).wigs[0].climate

    def test_shape_and_counts(self):
        summary = matrix_summary(self._matrix())
        matrix = self._matrix()
        assert summary["cells"] == len(matrix.cells)
        # Bounds native, unit riding along (unit ruling 2026-07-29):
        # the frontend converts per render, the payload never does.
        assert summary["min_temp"] == 16.0
        assert summary["max_temp"] == 30.0
        assert summary["unit"] == "C"
        # The fixture declares an "on" code; the frontend bounds the
        # clip-confirm count with this flag (bench bug 2026-07-29).
        assert summary["has_on"] is True

    def test_has_on_false_without_on_code(self):
        matrix = self._matrix()
        matrix.on = None
        assert matrix_summary(matrix)["has_on"] is False

    def test_describes_observed_not_declared(self):
        # "ion" is declared but its subtree skipped at import
        # (unmappable mode); the summary must not advertise it.
        summary = matrix_summary(self._matrix())
        assert summary["modes"] == ["cool", "dry", "heat"]
        assert summary["fan_modes"] == ["auto", "low", "high"]
        assert summary["swing_modes"] == ["swing"]


class TestDisplayName:
    """The owner-ruled display grammar (2026-07-29, mockup CC4).

    Spaced slashes, mode bare first, fan and swing labeled, temp a
    bare number last. The labels are load-bearing: "auto" is a legal
    value in all three vocabularies (real corpus files declare fan
    "auto", swing "auto", and mode "auto"), so an unlabeled join could
    not be read back into coordinates. This grammar is THE name on
    every human surface; the compact cell_key stays fittings-only.
    """

    def test_full_cell(self):
        cell = ClimateCell(mode="cool", fan="auto", temp=22.0, pronto="P")
        assert cell_display_name(cell) == "cool / fan: auto / 22"

    def test_swing_cell(self):
        cell = ClimateCell(
            mode="cool", fan="quiet", swing="swing", temp=25.0, pronto="P"
        )
        assert cell_display_name(cell) == (
            "cool / fan: quiet / swing: swing / 25"
        )

    def test_triple_auto_stays_readable(self):
        """The case that forced the labels: every coordinate "auto"."""
        cell = ClimateCell(
            mode="auto", fan="auto", swing="auto", temp=24.0, pronto="P"
        )
        assert cell_display_name(cell) == (
            "auto / fan: auto / swing: auto / 24"
        )

    def test_depth1_cell(self):
        cell = ClimateCell(mode="dry", fan="auto", pronto="P")
        assert cell_display_name(cell) == "dry / fan: auto"

    def test_bare_mode_cell(self):
        assert cell_display_name(
            ClimateCell(mode="cool", pronto="P")
        ) == "cool"

    def test_values_verbatim_never_case_normalized(self):
        """Vocabulary rides exactly as the file spells it (addendum
        section 3): the strings double as lookup keys."""
        cell = ClimateCell(
            mode="COOL", fan="Turbo MAX", swing="Wide  Swing",
            temp=22.5, pronto="P",
        )
        assert cell_display_name(cell) == (
            "COOL / fan: Turbo MAX / swing: Wide  Swing / 22.5"
        )

    def test_whole_temps_drop_the_point(self):
        cell = ClimateCell(mode="cool", fan="auto", temp=22.0, pronto="P")
        assert cell_display_name(cell).endswith("/ 22")

    def test_power_labels(self):
        assert state_display_name("off") == "Off"
        assert state_display_name("on") == "On"
        # Defensive passthrough for anything else.
        assert state_display_name("weird") == "weird"


class TestUnitConversion:
    """Display conversion of matrix temperatures (unit ruling
    2026-07-29): machine keys stay file-native forever, displays and
    minted names convert to the viewer's unit, non-temp parts never
    change. displayTemp in temperature.ts mirrors display_temp_str
    byte-for-byte; any behavior change here must land there too.
    """

    def test_c_to_f_nearest_int_is_non_uniform(self):
        """16C and 17C are 1.8F apart, so their nearest whole degrees
        are 61 and 63 -- the gap is honest, not a bug."""
        assert display_temp_str(16.0, "C", "F") == "61"
        assert display_temp_str(17.0, "C", "F") == "63"
        assert display_temp_str(22.0, "C", "F") == "72"

    def test_half_degree_matrices_render_one_decimal(self):
        """0.5C steps are 0.9F apart: int rounding would collide
        distinct cells (22.5C and 23C both round to 73F), so a
        sub-degree matrix keeps one decimal in the foreign unit."""
        converted = {
            display_temp_str(t, "C", "F", precision=0.5)
            for t in (22.0, 22.5, 23.0)
        }
        assert converted == {"71.6", "72.5", "73.4"}

    def test_f_to_c_mirrors_both_rules(self):
        assert display_temp_str(72.0, "F", "C") == "22"
        assert display_temp_str(61.0, "F", "C") == "16"
        assert display_temp_str(72.0, "F", "C", precision=0.5) == "22.2"

    def test_same_or_absent_display_unit_stays_native(self):
        assert display_temp_str(22.5, "C", "C", precision=0.5) == "22.5"
        assert display_temp_str(22.0, "C") == "22"
        assert display_temp_str(22.0, "F", None) == "22"

    def test_cell_name_converts_only_the_temperature(self):
        cell = ClimateCell(
            mode="cool", fan="auto", swing="swing", temp=22.0, pronto="P"
        )
        assert cell_display_name(cell, unit="C", display_unit="F") == (
            "cool / fan: auto / swing: swing / 72"
        )
        # Zero-arg form: unchanged, native.
        assert cell_display_name(cell) == (
            "cool / fan: auto / swing: swing / 22"
        )

    def test_unit_letter_reads_ha_units_defensively(self):
        from homeassistant.const import UnitOfTemperature

        assert unit_letter(UnitOfTemperature.FAHRENHEIT) == "F"
        assert unit_letter(UnitOfTemperature.CELSIUS) == "C"
        # A mocked or missing config can never flip a name.
        assert unit_letter(object()) == "C"
        assert unit_letter(None) == "C"


class TestExactCell:
    """The no-snap lookup behind matrix-send and save-state (Cold
    Cuts second half): real coordinates hit, anything else is None."""

    def _matrix(self):
        return convert(_smartir_file()).wigs[0].climate

    def test_exact_hit(self):
        cell = exact_cell(self._matrix(), "cool", "auto", None, 22)
        assert cell is not None and cell.temp == 22.0

    def test_int_temp_matches_float_cell(self):
        # WS payloads carry 22, cells store 22.0; same coordinate.
        m = self._matrix()
        assert exact_cell(m, "cool", "auto", None, 22) \
            is exact_cell(m, "cool", "auto", None, 22.0)

    def test_never_snaps(self):
        # 24 sits between real temps 22 and 30: resolve_cell would
        # snap, exact_cell must refuse.
        assert exact_cell(self._matrix(), "cool", "auto", None, 24) is None

    def test_no_dimension_fallbacks(self):
        m = self._matrix()
        assert exact_cell(m, "cool", "nonsense", None, 22) is None
        # cool/high exists only behind swing; without it, no cell.
        assert exact_cell(m, "cool", "high", None, 22) is None
        assert exact_cell(m, "cool", "high", "swing", 22) is not None

    def test_depth1_exact(self):
        cell = exact_cell(self._matrix(), "dry", "auto")
        assert cell is not None and cell.temp is None

    def test_missing_mode(self):
        assert exact_cell(self._matrix(), "ion", "auto", None, 22) is None


class TestResolveCell:
    def _matrix(self):
        return convert(_smartir_file()).wigs[0].climate

    def test_exact_and_snap(self):
        m = self._matrix()
        exact = resolve_cell(m, "cool", "auto", None, 22)
        assert exact.temp == 22.0
        snapped = resolve_cell(m, "cool", "auto", None, 24)
        assert snapped.temp == 22.0  # nearest of 16/22/30
        assert resolve_cell(m, "cool", "auto", None, 27).temp == 30.0

    def test_fan_fallback_and_depth1(self):
        m = self._matrix()
        # "high" in cool exists only behind swing; requesting an
        # unknown fan falls back to the branch's first fan.
        assert resolve_cell(m, "cool", "nonsense", None, 22) is not None
        dry = resolve_cell(m, "dry", "auto")
        assert dry is not None and dry.temp is None

    def test_missing_mode_is_none(self):
        assert resolve_cell(self._matrix(), "ion") is None


class TestHashRegression:
    def test_signal_wig_hash_pinned_after_the_recipe_break(self):
        """A signal wig still binds to signals_content_hash, and the
        value is pinned against a literal.

        The digest CHANGED at the recipe break, deliberately and once:
        send_count left the canonical form and both hashed recipe fields
        became explicit. Cold Cuts left it alone; the recipe release
        rolled it. Re-pinned here so a future accidental change to the
        canonical form still fails loudly.
        """
        sig = WigSignal(alias="Power", pronto=PRONTO)
        w = Wig(name="TV", signals=[sig])
        assert wig_content_hash(w) == signals_content_hash([sig])
        assert signals_content_hash([sig]) == (
            "sha256:"
            "fa4a98d52f6a9fea79720a56be38b95d2eed99ed3db5a22b2a4d"
            "d9b1665cb238"
        )

    def test_matrix_wig_binds_to_cells(self):
        wig = convert(_smartir_file()).wigs[0]
        assert wig_content_hash(wig) == cells_content_hash(wig.climate)
        # ...and is unaffected by the flat extras riding along.
        wig.signals = []
        assert wig_content_hash(wig) == cells_content_hash(wig.climate)


class TestRecipeBreakOnCells:
    """send_count left the cell canonical for the same reason it left
    the signal canonical: the dimension checklist never transmitted it.

    Cells carry no ditto field at all. Dittos are an NEC-family frame
    construct and an AC state blob is one long frame, so there is
    nothing for the concept to mean here (owner ruling).
    """

    def _matrix(self):
        return convert(_smartir_file()).wigs[0].climate

    def test_send_count_is_gone_from_the_cell_object(self):
        canon = canonical_cells_json(self._matrix())
        assert '"send_count"' not in canon
        assert "ditto_count" not in canon

    def test_unit_off_and_on_still_participate(self):
        """Everything else about the cell canonical is untouched: the
        break removed one key and changed nothing else."""
        matrix = self._matrix()
        base = cells_content_hash(matrix)

        matrix.unit = "F" if matrix.unit == "C" else "C"
        assert cells_content_hash(matrix) != base
