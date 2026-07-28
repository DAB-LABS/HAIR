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
    dimension_checklist,
    matrix_summary,
    resolve_cell,
)
from custom_components.hair.wig_format import (
    Wig,
    WigSignal,
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
        assert '"format": "hair-wig/2"' in text
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
        assert summary["min_temp"] == 16.0
        assert summary["max_temp"] == 30.0

    def test_describes_observed_not_declared(self):
        # "ion" is declared but its subtree skipped at import
        # (unmappable mode); the summary must not advertise it.
        summary = matrix_summary(self._matrix())
        assert summary["modes"] == ["cool", "dry", "heat"]
        assert summary["fan_modes"] == ["auto", "low", "high"]
        assert summary["swing_modes"] == ["swing"]


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
    def test_v1_hash_unchanged_by_cold_cuts(self):
        """Existing fittings bind to signals_content_hash; the value
        for a signal wig must be identical before and after this
        release. Pinned against a literal digest."""
        sig = WigSignal(alias="Power", pronto=PRONTO)
        w = Wig(name="TV", signals=[sig])
        assert wig_content_hash(w) == signals_content_hash([sig])
        assert signals_content_hash([sig]) == (
            "sha256:"
            "d4196489f8e398a7396cf46d1188ce595fea3ad6263e34d2fc8f"
            "b37c6d8d0351"
        )

    def test_matrix_wig_binds_to_cells(self):
        wig = convert(_smartir_file()).wigs[0]
        assert wig_content_hash(wig) == cells_content_hash(wig.climate)
        # ...and is unaffected by the flat extras riding along.
        wig.signals = []
        assert wig_content_hash(wig) == cells_content_hash(wig.climate)
