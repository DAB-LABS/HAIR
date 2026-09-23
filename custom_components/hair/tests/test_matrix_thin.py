"""Thinning: removing states a device does not have (thinning-plan.md).

Two halves, the way the code is split:

- The arithmetic (``matrix_thin.thin_matrix``), driven directly: which
  cells go, which stay, what the frame keeps, every refusal by name,
  and the record.
- The door (``ws_device_matrix_thin``), driven through a real adopt
  and a real closet: the one write, the signal every live copy of the
  lattice needs, portholes going with their cells, and the repairs'
  own write-through minting beside the original and superseding only
  its own files.

THE CORPUS PIN is Marcos's Komeco from WigShop PR #19. The repo's
Komeco fixture IS his before file (same bytes, md5 25a72159...), and
his after file sits under ``fixtures/thinning``. The thin that takes
one to the other is the one the plan names: heat_cool to 25, dry to 25
with swings off and horizontal. 1,156 cells to 834.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair import matrix_thin
from custom_components.hair.const import DOMAIN, CommandSource
from custom_components.hair.matrix_store import (
    SIGNAL_MATRIX_CHANGED,
    load_matrix,
    matrix_path,
    write_matrix,
)
from custom_components.hair.matrix_thin import (
    NOTHING_TO_REMOVE,
    THINNING_KEY,
    ThinRefused,
    thin_matrix,
)
from custom_components.hair.models import IRCommand
from custom_components.hair.tangles import (
    REPAIR_SUCCESSOR,
    TIER_ACCEPTED,
    WROTE_NOT_ADOPTED,
)
from custom_components.hair.tests.test_extras_fitting import fork
from custom_components.hair.websocket_api import (
    ws_device_matrix_thin,
    ws_wig_make_device,
)
from custom_components.hair.wig_climate import (
    dimension_checklist,
    matrix_summary,
)
from custom_components.hair.wig_fitting import claims_ledger
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateMatrix,
    Wig,
    cell_key,
    cells_content_hash,
    lattice_cell_key,
    normalized_pronto,
    parse_wig,
    serialize_wig,
)
from custom_components.hair.wig_store import ensure_wigs_dir, wigs_dir

FIXTURES = Path(__file__).parent / "fixtures"
KOMECO = (FIXTURES / "wigs"
          / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")
KOMECO_AFTER = FIXTURES / "thinning" / "komeco-pr19-after-834.wig.json"
SOURCE = "komeco.wig.json"

FANS = ["auto", "low", "medium", "high"]
SWINGS = ["off", "vertical", "horizontal", "both"]
TEMPS = list(range(16, 33))


def _komeco() -> Wig:
    parsed = parse_wig(KOMECO.read_text(encoding="utf-8"))
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


def _full(mode: str, fans=FANS, swings=SWINGS, temps=TEMPS) -> dict:
    return {"mode": mode, "fans": list(fans), "swings": list(swings),
            "temps": list(temps)}


def _main(*modes: dict) -> dict:
    return {"axis": None, "key": None, "modes": list(modes)}


def _komeco_shape(**over: dict) -> list[dict]:
    """The Komeco's whole shape as it stands, with ``over`` replacing
    (or, given None, dropping) one mode entry by name."""
    base = {
        "cool": _full("cool"),
        "heat": _full("heat"),
        "dry": _full("dry", fans=["low"]),
        "fan_only": _full("fan_only"),
        "heat_cool": _full("heat_cool"),
    }
    for mode, entry in over.items():
        if entry is None:
            base.pop(mode)
        else:
            base[mode] = entry
    return [_main(*base.values())]


#: THE PR #19 THIN, exactly as the plan states it.
PR19 = _komeco_shape(
    heat_cool=_full("heat_cool", temps=[25]),
    dry=_full("dry", fans=["low"], swings=["off", "horizontal"], temps=[25]),
)


def _p(n: int) -> str:
    """A distinct valid Pronto per ``n``."""
    pairs = ["0156 00AB"] + [
        "0015 0040" if (n >> bit) & 1 else "0015 0015" for bit in range(16)
    ] + ["0015 0400"]
    return f"0000 006D {len(pairs):04X} 0000 " + " ".join(pairs)


def _depths() -> ClimateMatrix:
    """Three depths in one matrix: ``cool`` carries fan, swing and
    temperature; ``fan_only`` carries fan and swing and no temperature;
    ``auto`` is a single code with no axis at all."""
    n = [0]

    def code() -> str:
        n[0] += 1
        return _p(n[0])

    cells = [
        ClimateCell(mode="cool", fan=f, swing=s, temp=float(t), pronto=code())
        for f in ("auto", "high") for s in ("off", "on") for t in (20, 21, 22)
    ]
    cells += [
        ClimateCell(mode="fan_only", fan=f, swing=s, pronto=code())
        for f in ("auto", "high") for s in ("off", "on")
    ]
    cells.append(ClimateCell(mode="auto", pronto=code()))
    return ClimateMatrix(
        min_temp=16.0, max_temp=30.0, off=_p(9000), on=_p(9001),
        cells=cells, modes=["cool", "fan_only", "auto"],
        fan_modes=["auto", "high"], swing_modes=["off", "on"],
    )


def _depth_shape(**over) -> list[dict]:
    base = {
        "cool": {"mode": "cool", "fans": ["auto", "high"],
                 "swings": ["off", "on"], "temps": [20, 21, 22]},
        "fan_only": {"mode": "fan_only", "fans": ["auto", "high"],
                     "swings": ["off", "on"], "temps": None},
        "auto": {"mode": "auto", "fans": None, "swings": None, "temps": None},
    }
    for mode, entry in over.items():
        if entry is None:
            base.pop(mode)
        else:
            base[mode] = entry
    return [_main(*base.values())]


def _refused(matrix, lattices, keep_on=True) -> str:
    with pytest.raises(ThinRefused) as err:
        thin_matrix(matrix, lattices, keep_on)
    return str(err.value)


def _pairs(cells) -> set[tuple[str, str]]:
    return {(cell_key(c), normalized_pronto(c.pronto)) for c in cells}


# ---------------------------------------------------------------------------
# The arithmetic on a /3 matrix
# ---------------------------------------------------------------------------


class TestTheArithmetic:
    def test_narrowing_one_axis_removes_exactly_those_cells(self):
        matrix = _komeco().climate
        before = list(matrix.cells)
        out = thin_matrix(
            matrix, _komeco_shape(heat_cool=_full("heat_cool", temps=[25])),
            True,
        )
        gone = [c for c in before if c not in out.matrix.cells]
        assert len(gone) == 256
        assert all(c.mode == "heat_cool" and c.temp != 25 for c in gone)
        # Every other cell survives, same object, same bytes, same order.
        assert out.matrix.cells == [c for c in before if c not in gone]

    def test_removing_a_mode_removes_all_its_cells(self):
        matrix = _komeco().climate
        out = thin_matrix(matrix, _komeco_shape(dry=None), True)
        assert len(out.matrix.cells) == 1156 - 68
        assert not any(c.mode == "dry" for c in out.matrix.cells)
        assert out.record["modes_removed"] == [
            {"axis": None, "key": None, "mode": "dry", "cells": 68},
        ]

    def test_the_frame_is_unchanged(self):
        matrix = _komeco().climate
        out = thin_matrix(matrix, PR19, True).matrix
        assert out.modes == matrix.modes
        assert out.fan_modes == matrix.fan_modes
        assert out.swing_modes == matrix.swing_modes
        assert out.off == matrix.off
        assert out.on == matrix.on
        assert out.unit == matrix.unit
        assert out.precision == matrix.precision
        assert (out.min_temp, out.max_temp) == (
            matrix.min_temp, matrix.max_temp)

    def test_cells_hash_moves_and_the_source_is_untouched(self):
        matrix = _komeco().climate
        before_hash = cells_content_hash(matrix)
        out = thin_matrix(matrix, PR19, True).matrix
        assert cells_content_hash(out) != before_hash
        assert cells_content_hash(matrix) == before_hash
        assert len(matrix.cells) == 1156
        assert THINNING_KEY not in matrix.extra

    def test_dropping_on_alone_is_a_thin(self):
        matrix = _depths()
        out = thin_matrix(matrix, _depth_shape(), keep_on=False)
        assert out.matrix.on is None
        assert out.matrix.off == matrix.off
        assert out.record["on_removed"] is True
        assert out.record["removed_cells"] == 0


class TestTheCorpusPin:
    """Marcos's shape, WigShop PR #19: 1,156 cells to 834."""

    def test_1156_to_834(self):
        matrix = _komeco().climate
        assert len(matrix.cells) == 1156
        out = thin_matrix(matrix, PR19, True)
        assert len(out.matrix.cells) == 834
        assert out.record["removed_cells"] == 322
        assert out.record["kept_cells"] == 834
        per_mode = {}
        for cell in out.matrix.cells:
            per_mode[cell.mode] = per_mode.get(cell.mode, 0) + 1
        assert per_mode == {
            "cool": 272, "heat": 272, "fan_only": 272,
            "heat_cool": 16, "dry": 2,
        }

    def test_the_thinned_matrix_is_the_after_files_cell_set(self):
        """Every coordinate of the after file, and its bytes.

        FOUR CELLS DIFFER IN BYTES, and not because of the thin: the
        after file's ``heat_cool/medium/*/25`` codes are not the before
        file's. PR #19 repaired those four in the same change, and a
        thin never changes a byte, so the thin of the before file
        carries the before file's codes there. The four are named here
        rather than hidden behind a looser assertion; every other one
        of the 834 matches exactly.
        """
        after = parse_wig(KOMECO_AFTER.read_text(encoding="utf-8")).wig
        assert after is not None
        out = thin_matrix(_komeco().climate, PR19, True).matrix
        assert {cell_key(c) for c in out.cells} == {
            cell_key(c) for c in after.climate.cells
        }
        mine, theirs = _pairs(out.cells), _pairs(after.climate.cells)
        repaired = {k for k, _p in mine - theirs}
        assert repaired == {
            "heat_cool/medium/off/25", "heat_cool/medium/vertical/25",
            "heat_cool/medium/horizontal/25", "heat_cool/medium/both/25",
        }
        assert {k for k, _p in theirs - mine} == repaired
        assert len(mine & theirs) == 830
        # The frame matches the after file too.
        assert out.off == after.climate.off
        assert out.modes == after.climate.modes
        assert out.fan_modes == after.climate.fan_modes
        assert out.swing_modes == after.climate.swing_modes


class TestDepth:
    def test_a_mode_with_no_temperature_thins_on_fan_and_swing(self):
        matrix = _depths()
        out = thin_matrix(matrix, _depth_shape(fan_only={
            "mode": "fan_only", "fans": ["high"], "swings": ["on"],
            "temps": None,
        }), True)
        kept = [c for c in out.matrix.cells if c.mode == "fan_only"]
        assert [(c.fan, c.swing) for c in kept] == [("high", "on")]

    def test_a_temperature_on_a_mode_without_one_is_refused(self):
        why = _refused(_depths(), _depth_shape(fan_only={
            "mode": "fan_only", "fans": ["high"], "swings": ["on"],
            "temps": [22],
        }))
        assert "temps given as a list" in why
        assert "never adds an axis" in why

    def test_a_single_code_mode_can_be_removed_and_nothing_else(self):
        matrix = _depths()
        out = thin_matrix(matrix, _depth_shape(auto=None), True)
        assert len(out.matrix.cells) == len(matrix.cells) - 1
        assert not any(c.mode == "auto" for c in out.matrix.cells)
        why = _refused(matrix, _depth_shape(auto={
            "mode": "auto", "fans": ["auto"], "swings": None, "temps": None,
        }))
        assert "fans given as a list" in why

    def test_one_surviving_temperature_is_still_an_axis(self):
        """Ruling 1: keep 25. The cells keep ``temp: 25``."""
        out = thin_matrix(_komeco().climate, PR19, True).matrix
        heat_cool = [c for c in out.cells if c.mode == "heat_cool"]
        assert {c.temp for c in heat_cool} == {25.0}


# ---------------------------------------------------------------------------
# Every refusal in plan section 2, by name
# ---------------------------------------------------------------------------


class TestRefusals:
    def test_main_lattice_missing(self):
        why = _refused(fork("1266"), [
            {"axis": "preset", "key": "eco", "modes": []},
        ])
        assert "main lattice is missing" in why

    def test_main_lattice_with_no_modes(self):
        why = _refused(_komeco().climate, [_main()])
        assert "main lattice has no modes" in why

    def test_an_axis_as_a_list_where_the_mode_has_none(self):
        why = _refused(_depths(), _depth_shape(auto={
            "mode": "auto", "fans": None, "swings": ["off"], "temps": None,
        }))
        assert "mode 'auto'" in why
        assert "swings given as a list" in why

    def test_an_axis_as_null_where_the_mode_has_one(self):
        why = _refused(_komeco().climate, _komeco_shape(
            cool={**_full("cool"), "fans": None}))
        assert "mode 'cool'" in why
        assert "fans given as null" in why

    @pytest.mark.parametrize("axis,value,word", [
        ("fans", "turbo", "fan 'turbo'"),
        ("swings", "spin", "swing 'spin'"),
        ("temps", 33, "temp 33"),
    ])
    def test_a_value_the_mode_does_not_carry(self, axis, value, word):
        why = _refused(_komeco().climate, _komeco_shape(
            cool={**_full("cool"), axis: [value]}))
        assert word in why
        assert "is not a value the mode carries" in why

    def test_a_fan_the_matrix_has_but_this_mode_does_not(self):
        """dry carries fan low only, though the matrix declares four."""
        why = _refused(_komeco().climate, _komeco_shape(
            dry=_full("dry", fans=["low", "high"])))
        assert "mode 'dry'" in why
        assert "fan 'high'" in why

    def test_an_empty_value_list_on_an_axis_that_exists(self):
        why = _refused(_komeco().climate, _komeco_shape(
            cool={**_full("cool"), "temps": []}))
        assert "temps is empty" in why

    @pytest.mark.parametrize("where", ["lattice", "mode"])
    @pytest.mark.parametrize("word", ["off", "keep_off"])
    def test_off_addressed_in_any_way(self, where, word):
        shape = _komeco_shape()
        if where == "lattice":
            shape[0][word] = False
        else:
            shape[0]["modes"][0][word] = False
        why = _refused(_komeco().climate, shape)
        assert "off cannot be removed" in why
        assert repr(word) in why

    def test_a_shape_that_removes_nothing(self):
        why = _refused(_komeco().climate, _komeco_shape())
        assert why == NOTHING_TO_REMOVE

    def test_nothing_is_decided_from_the_new_matrix_not_the_spelling(self):
        """A shape spelled differently (values reordered, duplicated,
        the temperature as 25.0) that keeps every cell is still nothing."""
        shape = _komeco_shape(cool={
            "mode": "cool", "fans": [*reversed(FANS), "auto"],
            "swings": SWINGS, "temps": [float(t) for t in TEMPS],
        })
        assert _refused(_komeco().climate, shape) == NOTHING_TO_REMOVE

    def test_keep_on_false_with_no_on_code_removes_nothing(self):
        assert _refused(
            _komeco().climate, _komeco_shape(), keep_on=False,
        ) == NOTHING_TO_REMOVE

    # The shape's own hygiene, beyond the plan's list.

    def test_half_a_lattice_pair(self):
        why = _refused(fork("1266"), [{"axis": "preset", "key": None,
                                       "modes": []}])
        assert "both axis and key, or neither" in why

    def test_an_unknown_lattice(self):
        why = _refused(_komeco().climate, [
            *_komeco_shape(),
            {"axis": "preset", "key": "turbo", "modes": []},
        ])
        assert "lattice preset:turbo" in why
        assert "no such lattice" in why

    def test_an_unknown_mode(self):
        why = _refused(_komeco().climate, _komeco_shape(auto=_full("auto")))
        assert "mode 'auto'" in why
        assert "no such mode" in why

    def test_a_mode_given_twice(self):
        shape = _komeco_shape()
        shape[0]["modes"].append(_full("cool"))
        assert "given twice" in _refused(_komeco().climate, shape)

    def test_an_extra_with_no_modes(self):
        matrix = fork("1266")
        shape = _all_of(matrix)
        shape[1]["modes"] = []
        why = _refused(matrix, shape)
        assert "lattice preset:eco" in why
        assert "leave the lattice out to remove it" in why

    def test_an_unknown_field(self):
        shape = _komeco_shape()
        shape[0]["modes"][0]["speed"] = ["fast"]
        assert "unknown field 'speed'" in _refused(_komeco().climate, shape)


# ---------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------


class TestTheRecord:
    def test_the_fields_as_specified(self):
        out = thin_matrix(_komeco().climate, PR19, True, now="2026-09-21T12:00:00+00:00")
        assert out.record == {
            "at": "2026-09-21T12:00:00+00:00",
            "tier": "accepted",
            "removed_cells": 322,
            "kept_cells": 834,
            "on_removed": False,
            "lattices_removed": [],
            "modes_removed": [],
            "narrowed": [
                {"axis": None, "key": None, "mode": "dry",
                 "fans": ["low"], "swings": ["off", "horizontal"],
                 "temps": [25], "cells": 66},
                {"axis": None, "key": None, "mode": "heat_cool",
                 "fans": FANS, "swings": SWINGS, "temps": [25],
                 "cells": 256},
            ],
        }

    def test_the_tier_is_the_repairs_accepted(self):
        assert matrix_thin.TIER_ACCEPTED == TIER_ACCEPTED

    def test_the_removed_counts_add_up(self):
        matrix = fork("1266")
        shape = _all_of(matrix)
        shape = [shape[0], shape[1]]  # boost removed whole
        shape[0]["modes"] = [m for m in shape[0]["modes"]
                             if m["mode"] != "dry"]
        shape[1]["modes"][0]["temps"] = [22]
        out = thin_matrix(matrix, shape, True)
        rec = out.record
        total = sum(e["cells"] for e in (
            rec["lattices_removed"] + rec["modes_removed"] + rec["narrowed"]))
        assert total == rec["removed_cells"]
        assert rec["removed_cells"] + rec["kept_cells"] == (
            len(matrix.cells) + sum(len(e.cells) for e in matrix.extras))

    def test_no_pronto_in_it(self):
        matrix = _komeco().climate
        out = thin_matrix(matrix, PR19, True)
        text = json.dumps(out.record).lower()
        assert "0000 006d" not in text
        assert normalized_pronto(matrix.off) not in text
        for cell in matrix.cells[:50]:
            assert normalized_pronto(cell.pronto) not in text

    def test_one_entry_per_save_newest_last(self):
        first = thin_matrix(_komeco().climate, _komeco_shape(dry=None),
                            True, now="2026-09-21T10:00:00+00:00").matrix
        second = thin_matrix(first, [_main(
            _full("cool"), _full("heat"), _full("fan_only"),
            _full("heat_cool", temps=[25]),
        )], True, now="2026-09-21T11:00:00+00:00").matrix
        history = second.extra[THINNING_KEY]
        assert [e["at"] for e in history] == [
            "2026-09-21T10:00:00+00:00", "2026-09-21T11:00:00+00:00",
        ]
        assert history[0]["modes_removed"][0]["mode"] == "dry"
        assert history[1]["narrowed"][0]["mode"] == "heat_cool"

    def test_it_survives_export_and_reimport(self):
        wig = _komeco()
        wig.climate = thin_matrix(wig.climate, PR19, True).matrix
        again = parse_wig(serialize_wig(wig))
        assert again.wig is not None, again.errors
        assert again.wig.climate.extra[THINNING_KEY] == (
            wig.climate.extra[THINNING_KEY])
        # Outside the digest: the record never moves cells_hash.
        assert cells_content_hash(again.wig.climate) == cells_content_hash(
            wig.climate)


# ---------------------------------------------------------------------------
# The summary line's last clause (owner ruling 2026-09-22)
# ---------------------------------------------------------------------------


class TestTheTrimmedSummary:
    """The Thinned badge is gone; what a trim cost rides the summary
    line instead, and the numbers come from here."""

    def test_an_untrimmed_matrix_says_nothing(self):
        summary = matrix_summary(_komeco().climate)
        assert "trimmed" not in summary
        assert "thinned" not in summary

    def test_after_one_trim(self):
        matrix = thin_matrix(_komeco().climate, PR19, True).matrix
        summary = matrix_summary(matrix)
        assert summary["cells"] == 834
        assert summary["trimmed"] == {"from": 1156, "to": 834}

    def test_a_second_trim_still_reads_from_the_original_size(self):
        once = thin_matrix(_komeco().climate, PR19, True).matrix
        twice = thin_matrix(once, [_main(
            _full("cool"), _full("heat"),
            _full("heat_cool", temps=[25]),
            _full("dry", fans=["low"], swings=["off", "horizontal"],
                  temps=[25]),
        )], True).matrix
        assert len(twice.extra[THINNING_KEY]) == 2
        assert matrix_summary(twice)["trimmed"] == {"from": 1156, "to": 562}

    def test_to_counts_every_lattice(self):
        """The record counts across every lattice, so this does too. A
        matrix with extras therefore reads a "to" larger than the
        summary's own main-lattice states count, which is what the
        states count has always been."""
        matrix = fork("1266")
        whole = len(matrix.cells) + sum(len(e.cells) for e in matrix.extras)
        shape = _all_of(matrix)
        shape[0]["modes"] = [
            m for m in shape[0]["modes"] if m["mode"] != "dry"
        ]
        thinned = thin_matrix(matrix, shape, True).matrix
        summary = matrix_summary(thinned)
        assert summary["trimmed"]["from"] == whole
        assert summary["trimmed"]["to"] == (
            len(thinned.cells)
            + sum(len(e.cells) for e in thinned.extras)
        )
        assert summary["cells"] == len(thinned.cells)

    @pytest.mark.parametrize("record", [
        "nonsense", [], [[]], [{}],
        [{"kept_cells": 10}], [{"kept_cells": "10", "removed_cells": 1}],
        [{"kept_cells": True, "removed_cells": False}],
        [{"kept_cells": 0, "removed_cells": 0}],
    ])
    def test_a_record_it_cannot_read_is_ignored(self, record):
        """It rides the file as an unknown key, so a hand-edited or
        foreign one must not put a broken clause on the card."""
        matrix = _komeco().climate
        matrix.extra[THINNING_KEY] = record
        assert "trimmed" not in matrix_summary(matrix)


# ---------------------------------------------------------------------------
# Extras lattices
# ---------------------------------------------------------------------------


def _all_of(matrix: ClimateMatrix) -> list[dict]:
    """The matrix's whole current shape, every lattice, every mode."""
    def lattice(axis, key, cells):
        modes = []
        for mode in dict.fromkeys(c.mode for c in cells):
            carried = matrix_thin._mode_axes(matrix, cells, mode)
            modes.append({
                "mode": mode,
                **{a: (list(v) if v else None) for a, v in carried.items()},
            })
        return {"axis": axis, "key": key, "modes": modes}

    return [lattice(None, None, matrix.cells)] + [
        lattice(e.axis, e.key, e.cells) for e in matrix.extras
    ]


class TestExtras:
    def test_a_lattice_removed_whole(self):
        matrix = fork("1266")
        shape = [s for s in _all_of(matrix) if s["key"] != "boost"]
        out = thin_matrix(matrix, shape, True)
        assert [e.key for e in out.matrix.extras] == ["eco"]
        boost = next(e for e in matrix.extras if e.key == "boost")
        assert out.record["lattices_removed"] == [
            {"axis": "preset", "key": "boost", "cells": len(boost.cells)},
        ]
        assert out.matrix.cells == matrix.cells

    def test_a_mode_narrowed_inside_a_lattice(self):
        matrix = fork("1266")
        shape = _all_of(matrix)
        eco = shape[1]
        cool = next(m for m in eco["modes"] if m["mode"] == "cool")
        cool["temps"] = [22, 23]
        out = thin_matrix(matrix, shape, True)
        eco_after = next(e for e in out.matrix.extras if e.key == "eco")
        cool_cells = [c for c in eco_after.cells if c.mode == "cool"]
        assert sorted(c.temp for c in cool_cells) == [22.0, 23.0]
        assert out.record["narrowed"] == [{
            "axis": "preset", "key": "eco", "mode": "cool",
            "fans": ["auto"], "swings": None, "temps": [22, 23],
            "cells": 12,
        }]
        # The main lattice's cool, same coordinates, is untouched.
        assert out.matrix.cells == matrix.cells

    def test_the_wig_drops_to_3_when_its_last_extra_goes(self):
        matrix = fork("1266")
        wig = Wig(name="Fork AC", signals=[], climate=matrix)
        assert json.loads(serialize_wig(wig))["format"] == "hair-wig/4"
        wig.climate = thin_matrix(matrix, _all_of(matrix)[:1], True).matrix
        assert wig.climate.extras == []
        assert json.loads(serialize_wig(wig))["format"] == "hair-wig/3"


class TestTheChecklistIsBuiltFromTheThinnedMatrix:
    """Folded-in item 3. Thinning happens to the MATRIX, before any
    checklist exists, so the dedup trap cannot reopen: the sampler
    never sees a removed cell, and the extras rows that remain keep
    their lattice-qualified keys."""

    def test_removed_cells_are_absent_from_every_lattice(self):
        matrix = fork("1266")
        shape = _all_of(matrix)
        shape = [shape[0], shape[1]]  # boost goes whole
        for entry in shape:
            for mode in entry["modes"]:
                if mode["temps"]:
                    mode["temps"] = [22, 23]
        out = thin_matrix(matrix, shape, True)
        removed = {
            normalized_pronto(c.pronto)
            for cells in out.removed.values() for c in cells
        }
        assert removed
        rows = dimension_checklist(out.matrix)
        assert not any(normalized_pronto(r.pronto) in removed for r in rows)
        assert not any(r.lattice == "boost" for r in rows)
        assert {r.temp for r in rows if r.temp is not None} <= {22.0, 23.0}

    def test_the_remaining_extras_rows_keep_their_qualified_keys(self):
        matrix = fork("1266")
        shape = _all_of(matrix)
        eco = shape[1]
        for mode in eco["modes"]:
            mode["temps"] = [22, 23]
        out = thin_matrix(matrix, shape, True)
        rows = dimension_checklist(out.matrix)
        eco_rows = [r for r in rows if r.lattice == "eco"]
        assert eco_rows
        eco_cells = next(e for e in out.matrix.extras if e.key == "eco").cells
        for row in eco_rows:
            assert row.key.startswith("preset:eco/")
            cell = next(c for c in eco_cells if normalized_pronto(c.pronto)
                        == normalized_pronto(row.pronto))
            assert row.key == lattice_cell_key(cell, "preset", "eco")
        # And the main lattice's rows at the same coordinates are still
        # there beside them: nothing ate anything.
        main_keys = {r.key for r in rows if r.lattice is None}
        for row in eco_rows:
            bare = row.key.split("/", 1)[1]
            if bare in {cell_key(c) for c in out.matrix.cells}:
                assert row.key not in main_keys


# ---------------------------------------------------------------------------
# Fittings
# ---------------------------------------------------------------------------


class TestFittings:
    def test_a_bundle_on_the_source_is_not_current_on_the_thinned_lattice(self):
        wig = _komeco()
        ledger = claims_ledger(wig, None)
        assert ledger["entries"]
        assert all(e["lattice_current"] is True for e in ledger["entries"])
        thinned = Wig(name=wig.name, signals=[], climate=thin_matrix(
            wig.climate, PR19, True).matrix, extra=dict(wig.extra),
            wig_id=wig.wig_id)
        after = claims_ledger(thinned, None)
        assert after["entries"]
        assert all(e["lattice_current"] is False for e in after["entries"])


# ---------------------------------------------------------------------------
# The door, through a real adopt and a real closet
# ---------------------------------------------------------------------------


def _conn():
    connection = MagicMock()
    connection.send_result = MagicMock()
    connection.send_error = MagicMock()
    return connection


async def _call(handler, hass, payload, *, expect_error=None):
    connection = _conn()
    await handler(hass, connection, payload)
    if expect_error is None:
        connection.send_error.assert_not_called()
        return connection.send_result.call_args.args[1]
    connection.send_result.assert_not_called()
    assert connection.send_error.call_args.args[1] == expect_error
    return connection.send_error.call_args.args[2]


@pytest.fixture
def _no_signing(monkeypatch):
    monkeypatch.setattr(
        "custom_components.hair.fitting_signing.async_get_private_key",
        AsyncMock(return_value=None),
    )


@pytest.fixture
def signals(monkeypatch):
    sent: list = []
    monkeypatch.setattr(
        "custom_components.hair.websocket_api.async_dispatcher_send",
        lambda _hass, signal, *args: sent.append((signal, *args)),
    )
    return sent


def _wire(fake_hass, tmp_path):
    """A manager whose matrix calls reach the real matrix store."""
    devices: list = []
    cache: dict = {}

    async def _get_matrix(did):
        if did not in cache:
            cache[did] = load_matrix(str(tmp_path), did)
        return cache[did]

    async def _write_matrix(did, matrix):
        write_matrix(str(tmp_path), did, matrix)
        cache[did] = matrix

    async def _remove_command(did, command_id):
        device = next(d for d in devices if d.id == did)
        return device.remove_command(command_id)

    async def _delete_cell(did, coords):
        # The manager's own rule, so the porthole delete behaves here
        # exactly as it does in the field.
        from custom_components.hair.device_manager import DeviceManager

        matrix = await _get_matrix(did)
        keep = [
            c for c in matrix.cells
            if not DeviceManager._cell_matches(c, coords)
        ]
        if len(keep) == len(matrix.cells):
            return False
        matrix.cells = keep
        await _write_matrix(did, matrix)
        return True

    manager = MagicMock()
    manager.async_create_device = AsyncMock(
        side_effect=lambda d: devices.append(d))
    manager.async_update_device = AsyncMock()
    manager._auto_map_command = MagicMock()
    manager.get_device = MagicMock(
        side_effect=lambda did: next(
            (d for d in devices if d.id == did), None))
    manager.async_get_matrix = AsyncMock(side_effect=_get_matrix)
    manager.async_write_matrix = AsyncMock(side_effect=_write_matrix)
    manager.async_remove_command = AsyncMock(side_effect=_remove_command)
    manager.async_delete_cell = AsyncMock(side_effect=_delete_cell)
    store = MagicMock()
    store.get_device = manager.get_device
    store.get_all_devices = MagicMock(side_effect=lambda: list(devices))
    listener = MagicMock()
    fake_hass.config.config_dir = str(tmp_path)
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager, "store": store,
        "matrix_listener": listener, "fitting_manager": None,
    }}
    return devices, manager, listener


async def _adopt(fake_hass, tmp_path, wig: Wig, filename: str = SOURCE):
    ensure_wigs_dir(tmp_path)
    (wigs_dir(tmp_path) / filename).write_text(
        serialize_wig(wig), encoding="utf-8")
    devices, manager, listener = _wire(fake_hass, tmp_path)
    await _call(ws_wig_make_device, fake_hass, {
        "id": 1, "type": "hair/wigs/make-device", "filename": filename,
        "name": "Komeco", "device_type": "ac",
        "emitter_entity_ids": ["infrared.blaster"],
    })
    return devices[0], manager, listener


@pytest.fixture
async def adopted(fake_hass, tmp_path):
    device, manager, listener = await _adopt(fake_hass, tmp_path, _komeco())
    return fake_hass, device, tmp_path, manager, listener


def _thin(device, lattices, keep_on=True, **extra):
    return {"id": 9, "type": "hair/devices/matrix-thin",
            "device_id": device.id, "keep_on": keep_on,
            "lattices": lattices, **extra}


def _closet(tmp_path):
    return sorted(p.name for p in wigs_dir(tmp_path).glob("*.wig.json"))


def _load(tmp_path, filename) -> Wig:
    parsed = parse_wig((wigs_dir(tmp_path) / filename).read_text())
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


class TestTheDoor:
    @pytest.mark.asyncio
    async def test_it_thins_writes_and_answers(
            self, adopted, _no_signing, signals):
        hass, device, tmp_path, manager, _l = adopted
        result = await _call(ws_device_matrix_thin, hass, _thin(device, PR19))
        assert result["thinned"]["removed_cells"] == 322
        assert result["thinned"]["portholes_removed"] == []
        assert result["wig"]["written"] is True
        assert result["device"]["matrix"]["cells"] == 834
        # What the summary line's last clause reads from (owner ruling
        # 2026-09-22): the size before the first trim, and now.
        assert result["device"]["matrix"]["trimmed"] == {
            "from": 1156, "to": 834,
        }
        manager.async_write_matrix.assert_awaited_once()

        on_disk = load_matrix(str(tmp_path), device.id)
        assert len(on_disk.cells) == 834
        assert on_disk.extra[THINNING_KEY] == [result["thinned"]]

    @pytest.mark.asyncio
    async def test_the_record_rides_the_real_matrix_file(
            self, adopted, _no_signing, signals):
        hass, device, tmp_path, _m, _l = adopted
        await _call(ws_device_matrix_thin, hass, _thin(device, PR19))
        raw = json.loads(matrix_path(str(tmp_path), device.id).read_text())
        assert raw["format"] == "hair-matrix/1"
        record = raw["climate"][THINNING_KEY]
        assert len(record) == 1
        assert record[0]["tier"] == "accepted"
        assert record[0]["removed_cells"] == 322

    @pytest.mark.asyncio
    async def test_every_live_copy_is_told(
            self, adopted, _no_signing, signals):
        """The climate entity loaded its matrix once; without the signal
        it would go on offering the removed states."""
        hass, device, _tmp, _m, listener = adopted
        await _call(ws_device_matrix_thin, hass, _thin(device, PR19))
        assert (SIGNAL_MATRIX_CHANGED, device.id) in signals
        listener.invalidate.assert_called_with(device.id)

    @pytest.mark.asyncio
    async def test_off_as_a_top_level_key_is_refused_by_name(
            self, adopted, _no_signing, signals):
        hass, device, _tmp, manager, _l = adopted
        for word in ("off", "keep_off"):
            why = await _call(
                ws_device_matrix_thin, hass,
                _thin(device, PR19, **{word: False}),
                expect_error="invalid_format",
            )
            assert "off cannot be removed" in why
        manager.async_write_matrix.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_a_refusal_writes_nothing(
            self, adopted, _no_signing, signals):
        hass, device, tmp_path, manager, _l = adopted
        before = matrix_path(str(tmp_path), device.id).read_bytes()
        closet = _closet(tmp_path)
        why = await _call(
            ws_device_matrix_thin, hass, _thin(device, _komeco_shape()),
            expect_error="invalid_format",
        )
        assert why == NOTHING_TO_REMOVE
        assert matrix_path(str(tmp_path), device.id).read_bytes() == before
        assert _closet(tmp_path) == closet
        assert signals == []
        manager.async_write_matrix.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_a_device_with_no_matrix_is_not_found(
            self, adopted, _no_signing):
        hass, device, _tmp, _m, _l = adopted
        device.climate_matrix = False
        await _call(ws_device_matrix_thin, hass, _thin(device, PR19),
                    expect_error="not_found")


class TestTheWriteThrough:
    @pytest.mark.asyncio
    async def test_the_first_thin_mints_beside_the_original(
            self, adopted, _no_signing, signals):
        hass, device, tmp_path, _m, _l = adopted
        before = (wigs_dir(tmp_path) / SOURCE).read_text()
        result = await _call(ws_device_matrix_thin, hass, _thin(device, PR19))
        closet = _closet(tmp_path)
        assert len(closet) == 2
        assert SOURCE in closet
        assert (wigs_dir(tmp_path) / SOURCE).read_text() == before
        successor = _load(tmp_path, result["wig"]["filename"])
        assert successor.extra.get(REPAIR_SUCCESSOR) is True
        assert len(successor.climate.cells) == 834

    @pytest.mark.asyncio
    async def test_the_exporter_carries_the_record(
            self, adopted, _no_signing, signals):
        """Plan section 4: verified, not assumed. The record rides
        ``matrix.extra`` through build_wig_from_device and the writer's
        unknown-keys pass, into the closet file, and back out."""
        hass, device, tmp_path, _m, _l = adopted
        result = await _call(ws_device_matrix_thin, hass, _thin(device, PR19))
        successor = _load(tmp_path, result["wig"]["filename"])
        assert successor.climate.extra[THINNING_KEY] == [result["thinned"]]
        raw = json.loads(
            (wigs_dir(tmp_path) / result["wig"]["filename"]).read_text())
        assert raw["climate"][THINNING_KEY] == [result["thinned"]]

    @pytest.mark.asyncio
    async def test_a_second_thin_supersedes_the_first_mint_only(
            self, adopted, _no_signing, signals):
        hass, device, tmp_path, _m, _l = adopted
        original = (wigs_dir(tmp_path) / SOURCE).read_text()
        first = await _call(ws_device_matrix_thin, hass, _thin(device, PR19))
        second_shape = [_main(
            _full("cool"), _full("heat"),
            _full("heat_cool", temps=[25]),
            _full("dry", fans=["low"], swings=["off", "horizontal"],
                  temps=[25]),
        )]
        second = await _call(ws_device_matrix_thin, hass,
                             _thin(device, second_shape))
        assert second["wig"]["written"] is True
        assert second["wig"]["replaced"] == first["wig"]["filename"]
        closet = _closet(tmp_path)
        assert closet == sorted([SOURCE, second["wig"]["filename"]])
        assert (wigs_dir(tmp_path) / SOURCE).read_text() == original
        successor = _load(tmp_path, second["wig"]["filename"])
        history = successor.climate.extra[THINNING_KEY]
        assert len(history) == 2
        assert history[-1]["modes_removed"] == [
            {"axis": None, "key": None, "mode": "fan_only", "cells": 272},
        ]

    @pytest.mark.asyncio
    async def test_the_successor_carries_no_fittings(
            self, adopted, _no_signing, signals):
        hass, device, tmp_path, _m, _l = adopted
        assert claims_ledger(_load(tmp_path, SOURCE), None)["entries"]
        result = await _call(ws_device_matrix_thin, hass, _thin(device, PR19))
        successor = _load(tmp_path, result["wig"]["filename"])
        assert claims_ledger(successor, None)["entries"] == []

    @pytest.mark.asyncio
    async def test_a_source_that_left_the_closet_says_so(
            self, adopted, _no_signing, signals):
        hass, device, tmp_path, _m, _l = adopted
        (wigs_dir(tmp_path) / SOURCE).unlink()
        result = await _call(ws_device_matrix_thin, hass, _thin(device, PR19))
        assert result["wig"] == {"written": False, "reason": "source_missing"}
        assert len(load_matrix(str(tmp_path), device.id).cells) == 834

    @pytest.mark.asyncio
    async def test_a_device_never_adopted_says_so(
            self, adopted, _no_signing, signals):
        hass, device, _tmp, _m, _l = adopted
        device.source_wig_id = None
        result = await _call(ws_device_matrix_thin, hass, _thin(device, PR19))
        assert result["wig"] == {"written": False, "reason": WROTE_NOT_ADOPTED}


class TestPortholes:
    """Plan section 3, step 3: a porthole is a view of a cell, and when
    the cell goes the view goes, in the same save."""

    def _porthole(self, coords: dict, name: str) -> IRCommand:
        return IRCommand(
            name=name, protocol="PRONTO", code=_p(4242),
            source=CommandSource.MATRIX, repeat_count=0,
            matrix_cell=dict(coords), comb_suspect=True,
        )

    @pytest.mark.asyncio
    async def test_a_porthole_on_a_removed_cell_goes_and_others_stay(
            self, adopted, _no_signing, signals):
        hass, device, tmp_path, _m, _l = adopted
        doomed = self._porthole(
            {"mode": "heat_cool", "fan": "auto", "swing": "off",
             "temp": 16.0}, "cool lookalike name")
        kept = self._porthole(
            {"mode": "heat_cool", "fan": "auto", "swing": "off",
             "temp": 25}, "heat_cool 16")
        flat = IRCommand(name="heat_cool auto off 16", protocol="PRONTO",
                         code=_p(4343), repeat_count=0)
        device.commands.extend([doomed, kept, flat])

        result = await _call(ws_device_matrix_thin, hass, _thin(device, PR19))
        ids = {c.id for c in device.commands}
        assert doomed.id not in ids
        assert kept.id in ids
        assert flat.id in ids
        assert result["thinned"]["portholes_removed"] == [{
            "command_id": doomed.id, "axis": None, "key": None,
            "cell_key": "heat_cool/auto/off/16",
        }]
        on_disk = load_matrix(str(tmp_path), device.id)
        assert on_disk.extra[THINNING_KEY][0]["portholes_removed"] == (
            result["thinned"]["portholes_removed"])
        successor = _load(tmp_path, result["wig"]["filename"])
        aliases = {s.alias for s in successor.signals}
        # NEITHER porthole is a signal in the successor (owner bench
        # 2026-09-22): the removed one is gone from the device, and the
        # surviving one is a view of a cell the lattice already carries.
        # The ordinary command beside them is exported as it always was.
        assert aliases == {"heat_cool auto off 16"}
        assert kept.id in {c.id for c in device.commands}

    @pytest.mark.asyncio
    async def test_a_porthole_is_matched_by_coordinates_never_by_name(
            self, adopted, _no_signing, signals):
        """The flat command above is NAMED like a removed cell and
        survives; the porthole named like a kept one goes. Covered in
        the test above; this one pins the name-only case on its own."""
        hass, device, _tmp, _m, _l = adopted
        named = IRCommand(name="heat_cool / fan: auto / swing: off / 16",
                          protocol="PRONTO", code=_p(4444), repeat_count=0)
        device.commands.append(named)
        await _call(ws_device_matrix_thin, hass, _thin(device, PR19))
        assert named.id in {c.id for c in device.commands}


class TestAWig4Device:
    @pytest.mark.asyncio
    async def test_removing_the_last_extra_mints_a_3_successor(
            self, fake_hass, tmp_path, _no_signing, signals):
        matrix = fork("1266")
        wig = Wig(name="Fork AC", signals=[], climate=matrix,
                  wig_id="00000000-0000-4000-8000-00000000f0a1")
        device, _m, _l = await _adopt(fake_hass, tmp_path, wig,
                                      "fork.wig.json")
        assert json.loads((wigs_dir(tmp_path) / "fork.wig.json").read_text())[
            "format"] == "hair-wig/4"
        shape = _all_of(load_matrix(str(tmp_path), device.id))[:1]
        result = await _call(ws_device_matrix_thin, fake_hass,
                             _thin(device, shape))
        raw = json.loads(
            (wigs_dir(tmp_path) / result["wig"]["filename"]).read_text())
        assert raw["format"] == "hair-wig/3"
        assert "extras" not in raw["climate"]
        assert [e["key"] for e in result["thinned"]["lattices_removed"]] == [
            "eco", "boost",
        ]
