"""Extras lattices on the fitting checklist (extras-fitting-plan.md).

A hair-wig/4 matrix can carry extras lattices (``climate.extras``):
whole lattices the main one has no axis for, a preset's worth of cells
at the same coordinates as the main lattice but with different codes.
They sit inside ``cells_hash``, so a Perfect Fit that never sampled
them vouched for bytes nobody pressed. This file pins the fix:

- The three real fork shapes, as fixtures, with their checklist
  lengths PINNED, so a sampler change that quietly doubles the work
  fails here (plan 8).
- Every extras row names its lattice; main rows and power rows never
  do.
- THE DEDUP TRAP (plan 3a): the sampler's ``seen`` set is shared
  across lattices, and with an unqualified key the main rows eat the
  extras rows at the same coordinates. The test runs that failure and
  says so.
- Completeness, exclusions and ghost filtering grow with the
  checklist, as plan 4 claims -- each consumer checked, not assumed.
- Every existing matrix fixture: identical checklist, digests and
  completeness (plan 5, 9).
- The dialog's TEST, driven end to end: the plan row, through the
  frontend's own send helper and wire, to the real door. The extras
  code sent differs from the main code at the same coordinates.

The fork shapes are transcribed from the three real SmartIR files the
plan cites (which branches exist, per lattice); the codes are
generated. Distinct valid Prontos, one per cell, so every shared
coordinate carries a different code, exactly as it does in the real
files and exactly what makes the dedup trap bite.
"""
from __future__ import annotations

import glob
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair import wig_climate
from custom_components.hair.const import DOMAIN, DeviceType
from custom_components.hair.models import IRDevice
from custom_components.hair.wig_climate import (
    SECTION_START,
    SECTION_WRAP,
    dimension_checklist,
    dimension_checklist_digests,
)
from custom_components.hair.wig_fitting import bundle_is_complete
from custom_components.hair.wig_format import (
    VERDICT_NOT_ON_DEVICE,
    VERDICT_WONT_WORK,
    VERDICT_WORKED,
    ClaimsBundle,
    ClimateCell,
    ClimateExtra,
    ClimateMatrix,
    RowClaim,
    Wig,
    WigSignal,
    cell_key,
    lattice_cell_key,
    parse_wig,
    row_digest,
)
from custom_components.hair.wig_save import (
    Attestation,
    _allowed_claim_digests,
    build_save_plan,
    drop_ghost_claims,
    reject_flat_exclusions,
)

TESTS = Path(__file__).parent
FIXTURES = TESTS / "fixtures"
FRONTEND = TESTS.parent / "frontend"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"


# ---------------------------------------------------------------------------
# Fixtures: the three real fork shapes
# ---------------------------------------------------------------------------


def _pronto(n: int) -> str:
    """A distinct, VALID Pronto for every ``n`` below 65536: a leader,
    sixteen data bits spelling ``n``, a trailer. Valid matters: the row
    digest hashes the validator's normalized form, and distinct matters
    because the dedup trap only bites when shared coordinates carry
    different codes."""
    pairs = ["0156 00AB"] + [
        "0015 0040" if (n >> bit) & 1 else "0015 0015" for bit in range(16)
    ] + ["0015 0400"]
    return f"0000 006D {len(pairs):04X} 0000 " + " ".join(pairs)


_F1266 = ["auto", "low", "medium_low", "medium", "medium_high", "high"]
_F3102 = ["auto", "quiet", "low", "medium", "high", "turbo"]

#: Which branches each lattice carries, per real file: mode -> fans.
#: Every branch spans the file's whole temperature range and, where
#: the file has swings, every declared swing.
SHAPES: dict[str, dict] = {
    # 1266: six modes, six fans, no swing, no discrete on. ``eco`` is
    # fan auto alone across four modes -- the narrow extra the plan's
    # vocabulary ruling is about. ``boost`` is wide but not full.
    "1266": {
        "modes": ["auto", "heat_cool", "cool", "dry", "heat", "fan_only"],
        "fans": _F1266, "swings": [], "on": False, "temps": (17, 30),
        "main": {
            "auto": ["auto"], "heat_cool": _F1266, "cool": _F1266,
            "dry": ["auto"], "heat": _F1266, "fan_only": _F1266,
        },
        "extras": [
            ("eco", {
                "auto": ["auto"], "heat_cool": ["auto"],
                "cool": ["auto"], "heat": ["auto"],
            }),
            ("boost", {
                "auto": ["auto"], "heat_cool": _F1266[:5],
                "cool": _F1266, "heat": _F1266,
            }),
        ],
    },
    # 1706: swings on every branch, a sparse main lattice, a tiny
    # ``sleep``.
    "1706": {
        "modes": ["auto", "cool", "dry", "fan_only"],
        "fans": ["auto", "low", "medium", "high"],
        "swings": ["on", "off"], "on": False, "temps": (16, 32),
        "main": {
            "auto": ["auto"], "cool": ["auto", "low", "medium", "high"],
            "dry": ["low"], "fan_only": ["low", "medium", "high"],
        },
        "extras": [("sleep", {"auto": ["auto"], "cool": ["auto"]})],
    },
    # 3102: ``sleep`` is the identical shape to the main lattice, so
    # EVERY one of its sampled coordinates is shared -- the dedup trap
    # at its starkest: unqualified, all ten sleep rows vanish.
    "3102": {
        "modes": ["cool", "heat"], "fans": _F3102,
        "swings": ["fixed", "swing"], "on": True, "temps": (16, 30),
        "main": {"cool": _F3102, "heat": _F3102},
        "extras": [("sleep", {"cool": _F3102, "heat": _F3102})],
    },
}

#: THE PINNED NUMBERS (plan 8). Checklist length without and with the
#: extras, and each extra's own share. A sampler change that moves any
#: of these moves the work a fitter is asked to do, and must be a
#: decision, not an accident.
TOTALS = {"1266": (14, 31), "1706": (11, 16), "3102": (12, 22)}
PER_EXTRA = {
    "1266": {"eco": 6, "boost": 11},
    "1706": {"sleep": 5},
    "3102": {"sleep": 10},
}
#: What the checklist collapses to with an UNQUALIFIED key.
TRAPPED = {"1266": 23, "1706": 14, "3102": 12}


def _cells(shape: dict, branches: dict, counter: list[int]) -> list[ClimateCell]:
    lo, hi = shape["temps"]
    cells = []
    for mode, fans in branches.items():
        for fan in fans:
            for swing in shape["swings"] or [None]:
                for temp in range(lo, hi + 1):
                    counter[0] += 1
                    cells.append(ClimateCell(
                        mode=mode, fan=fan, swing=swing, temp=float(temp),
                        pronto=_pronto(counter[0]),
                    ))
    return cells


def fork(name: str, extras: bool = True) -> ClimateMatrix:
    """One real fork's shape as a ClimateMatrix. ``extras=False`` is the
    same file with its extras stripped: identical main lattice, down to
    every code."""
    shape = SHAPES[name]
    counter = [0]
    main = _cells(shape, shape["main"], counter)
    extra_list = [
        ClimateExtra(axis="preset", key=key, cells=_cells(shape, b, counter))
        for key, b in shape["extras"]
    ]
    counter[0] += 1
    off = _pronto(counter[0])
    counter[0] += 1
    on = _pronto(counter[0]) if shape["on"] else None
    lo, hi = shape["temps"]
    return ClimateMatrix(
        min_temp=float(lo), max_temp=float(hi), off=off, on=on,
        cells=main, modes=list(shape["modes"]),
        fan_modes=list(shape["fans"]), swing_modes=list(shape["swings"]),
        extras=extra_list if extras else [],
    )


def _wig(matrix: ClimateMatrix, signals: list[WigSignal] | None = None) -> Wig:
    return Wig(name="Fork AC", signals=signals or [], climate=matrix,
               wig_id="00000000-0000-4000-8000-000000000001")


def _bundle(digests, verdict: str = VERDICT_WORKED) -> ClaimsBundle:
    return ClaimsBundle(wig_id="x", rows=[
        RowClaim(alias_at_claim="r", digest=d, verdict=verdict)
        for d in sorted(digests)
    ])


FORKS = sorted(SHAPES)


# ---------------------------------------------------------------------------
# The fixtures are what they claim to be
# ---------------------------------------------------------------------------


class TestTheFixtures:
    @pytest.mark.parametrize("name", FORKS)
    def test_every_shared_coordinate_carries_a_different_code(self, name):
        """The corpus fact the dedup trap rests on, true of the
        fixtures too, or the trap test below would prove nothing."""
        matrix = fork(name)
        main = {cell_key(c): c.pronto for c in matrix.cells}
        shared = 0
        for extra in matrix.extras:
            for cell in extra.cells:
                if cell_key(cell) in main:
                    shared += 1
                    assert cell.pronto != main[cell_key(cell)]
        assert shared == sum(len(e.cells) for e in matrix.extras)

    @pytest.mark.parametrize("name", FORKS)
    def test_every_code_is_distinct_after_normalization(self, name):
        matrix = fork(name)
        codes = [c.pronto for c in matrix.cells] + [
            c.pronto for e in matrix.extras for c in e.cells
        ]
        assert len({row_digest(p) for p in codes}) == len(codes)


# ---------------------------------------------------------------------------
# The checklist
# ---------------------------------------------------------------------------


class TestTheChecklistLength:
    @pytest.mark.parametrize("name", FORKS)
    def test_the_pinned_totals(self, name):
        before, after = TOTALS[name]
        assert len(dimension_checklist(fork(name, extras=False))) == before
        assert len(dimension_checklist(fork(name))) == after

    @pytest.mark.parametrize("name", FORKS)
    def test_each_extra_contributes_its_pinned_share(self, name):
        rows = dimension_checklist(fork(name))
        share: dict[str, int] = {}
        for row in rows:
            if row.lattice is not None:
                share[row.lattice] = share.get(row.lattice, 0) + 1
        assert share == PER_EXTRA[name]

    def test_a_narrow_extra_is_sampled_against_its_own_cells(self):
        """1266's ``eco`` is fan auto alone. Sampled against the
        matrix's six declared fans it would invent five rows; it gets
        none, and no row names a fan the lattice lacks."""
        rows = [r for r in dimension_checklist(fork("1266"))
                if r.lattice == "eco"]
        assert {r.fan for r in rows} == {"auto"}
        assert [r.mode for r in rows if r.section == "modes"] == [
            "auto", "heat_cool", "cool", "heat",
        ]


class TestRowsCarryTheirLattice:
    @pytest.mark.parametrize("name", FORKS)
    def test_extras_rows_name_their_lattice(self, name):
        matrix = fork(name)
        keys = {e.key for e in matrix.extras}
        extras = [r for r in dimension_checklist(matrix) if r.lattice]
        assert extras
        for row in extras:
            assert row.axis == "preset"
            assert row.lattice in keys
            assert row.key.startswith(f"preset:{row.lattice}/")

    @pytest.mark.parametrize("name", FORKS)
    def test_main_and_power_rows_name_nothing(self, name):
        rows = dimension_checklist(fork(name))
        n_main = TOTALS[name][0]
        for row in rows[:n_main - 1] + rows[-1:]:
            assert row.axis is None
            assert row.lattice is None
        power = [r for r in rows if r.section in (SECTION_START, SECTION_WRAP)]
        assert [r.key for r in power] == (
            ["on", "off"] if SHAPES[name]["on"] else ["off"]
        )
        assert all(r.axis is None and r.lattice is None for r in power)

    @pytest.mark.parametrize("name", FORKS)
    def test_the_main_rows_keep_their_exact_place(self, name):
        """Everything before the first extras row, plus ``off``, is the
        no-extras checklist, field for field."""
        without = dimension_checklist(fork(name, extras=False))
        with_extras = dimension_checklist(fork(name))
        head = len(without) - 1
        assert with_extras[:head] == without[:head]
        assert with_extras[-1] == without[-1]
        assert with_extras[-1].key == "off"

    def test_extras_follow_in_wig_order(self):
        order = [r.lattice for r in dimension_checklist(fork("1266"))]
        first_boost = order.index("boost")
        assert "eco" in order[:first_boost]
        assert "eco" not in order[first_boost:]

    @pytest.mark.parametrize("name", FORKS)
    def test_every_extras_row_is_that_lattices_code(self, name):
        matrix = fork(name)
        by_lattice = {
            e.key: {cell_key(c): c.pronto for c in e.cells}
            for e in matrix.extras
        }
        for row in dimension_checklist(matrix):
            if row.lattice is None:
                continue
            coords = row.key.split("/", 1)[1]
            assert row.pronto == by_lattice[row.lattice][coords]


class TestTheDedupTrap:
    """Plan 3a. The sampler's ``seen`` set is SHARED across the main
    lattice and every extra, so the key a row enters it under must name
    its lattice. This runs the checklist with the qualifier removed."""

    @staticmethod
    def _unqualified(monkeypatch):
        monkeypatch.setattr(
            wig_climate, "lattice_cell_key",
            lambda cell, axis=None, lattice=None: cell_key(cell),
        )

    @pytest.mark.parametrize("name", FORKS)
    def test_an_unqualified_key_eats_the_extras_rows(self, name, monkeypatch):
        full = len(dimension_checklist(fork(name)))
        self._unqualified(monkeypatch)
        trapped = dimension_checklist(fork(name))
        assert len(trapped) == TRAPPED[name] < full, (
            "with an unqualified key the main lattice's rows swallow the "
            "extras rows at the same coordinates, and the checklist looks "
            "complete while never sampling those codes"
        )

    def test_the_starkest_case_loses_every_extras_row(self, monkeypatch):
        """3102's ``sleep`` is the main lattice's exact shape: all ten
        of its rows share coordinates with a main row, and all ten
        vanish. A Perfect Fit on that checklist would vouch for ten
        codes nobody pressed."""
        self._unqualified(monkeypatch)
        rows = dimension_checklist(fork("3102"))
        assert [r for r in rows if r.lattice == "sleep"] == [], (
            "the extras rows vanished, as they must without the qualifier"
        )
        assert len(rows) == TOTALS["3102"][0]

    def test_the_qualified_key_keeps_them(self):
        rows = dimension_checklist(fork("3102"))
        assert len([r for r in rows if r.lattice == "sleep"]) == 10


class TestLatticeCellKey:
    CELL = ClimateCell(mode="cool", fan="auto", temp=22.0, pronto="x")

    def test_the_qualified_shape(self):
        assert lattice_cell_key(self.CELL, "preset", "eco") == (
            "preset:eco/cool/auto/22"
        )

    def test_the_main_lattice_key_does_not_move(self):
        assert lattice_cell_key(self.CELL) == cell_key(self.CELL)
        assert lattice_cell_key(self.CELL) == "cool/auto/22"

    def test_both_or_neither(self):
        assert lattice_cell_key(self.CELL, "preset", None) == "cool/auto/22"
        assert lattice_cell_key(self.CELL, None, "eco") == "cool/auto/22"


# ---------------------------------------------------------------------------
# Plan 4: the consumers, each checked
# ---------------------------------------------------------------------------


class TestCompleteness:
    @pytest.mark.parametrize("name", FORKS)
    def test_a_main_only_bundle_is_not_complete_with_extras(self, name):
        stripped = fork(name, extras=False)
        main_only = _bundle(dimension_checklist_digests(stripped))
        assert bundle_is_complete(main_only, _wig(stripped)) is True
        assert bundle_is_complete(main_only, _wig(fork(name))) is False

    @pytest.mark.parametrize("name", FORKS)
    def test_the_whole_checklist_is_complete(self, name):
        matrix = fork(name)
        full = _bundle(dimension_checklist_digests(matrix))
        assert bundle_is_complete(full, _wig(matrix)) is True

    @pytest.mark.parametrize("name", FORKS)
    def test_the_digests_grow_by_the_extras_rows_and_nothing_else(self, name):
        before = dimension_checklist_digests(fork(name, extras=False))
        after = dimension_checklist_digests(fork(name))
        assert before < after
        assert len(after) == TOTALS[name][1]


class TestExclusions:
    FLAT = WigSignal(alias="Beep", pronto=_pronto(60000))

    def _extras_digest(self, matrix):
        row = next(r for r in dimension_checklist(matrix) if r.lattice)
        return row_digest(row.pronto)

    @pytest.mark.parametrize("verdict", [VERDICT_NOT_ON_DEVICE, VERDICT_WONT_WORK])
    def test_an_extras_exclusion_is_accepted(self, verdict):
        matrix = fork("1706")
        wig = _wig(matrix, [self.FLAT])
        att = Attestation(claims={self._extras_digest(matrix): verdict})
        assert reject_flat_exclusions(att, wig) is False

    def test_an_extras_exclusion_costs_completeness(self):
        matrix = fork("1706")
        wig = _wig(matrix)
        digests = dimension_checklist_digests(matrix)
        excluded = self._extras_digest(matrix)
        bundle = ClaimsBundle(wig_id="x", rows=[
            RowClaim(
                alias_at_claim="r", digest=d,
                verdict=VERDICT_NOT_ON_DEVICE if d == excluded else VERDICT_WORKED,
            )
            for d in sorted(digests)
        ])
        assert bundle_is_complete(bundle, wig) is False

    def test_a_flat_row_exclusion_is_still_refused(self):
        wig = _wig(fork("1706"), [self.FLAT])
        att = Attestation(claims={
            row_digest(self.FLAT.pronto): VERDICT_NOT_ON_DEVICE,
        })
        assert reject_flat_exclusions(att, wig) is True


class TestGhostClaims:
    """A consumer plan 4 does not list: ``_allowed_claim_digests``
    feeds ``drop_ghost_claims``, which strips any claim whose digest the
    wig does not carry BEFORE the bundle is built. It reads
    ``_checklist_rows`` too, so it grows with the checklist; if it did
    not, every extras claim would be dropped as a ghost and the signed
    bundle would never be complete."""

    @pytest.mark.parametrize("name", FORKS)
    def test_extras_claims_are_not_ghosts(self, name):
        matrix = fork(name)
        wig = _wig(matrix)
        digests = dimension_checklist_digests(matrix)
        assert digests <= _allowed_claim_digests(wig)
        att = Attestation(claims={d: VERDICT_WORKED for d in digests})
        assert drop_ghost_claims(att, wig) is att

    def test_a_real_ghost_is_still_dropped(self):
        matrix = fork("1706")
        att = Attestation(claims={
            row_digest(_pronto(61000)): VERDICT_WORKED,
            row_digest(matrix.off): VERDICT_WORKED,
        })
        kept = drop_ghost_claims(att, _wig(matrix))
        assert list(kept.claims) == [row_digest(matrix.off)]


# ---------------------------------------------------------------------------
# The save plan
# ---------------------------------------------------------------------------


def _device() -> IRDevice:
    device = IRDevice(id="dev-1", name="Fork AC", device_type=DeviceType.AC,
                      emitter_entity_ids=["infrared.e"])
    device.climate_matrix = True
    return device


class TestPlanRows:
    def test_plan_rows_carry_the_pair(self):
        plan = build_save_plan(_device(), matrix=fork("1706"))
        extras = [r for r in plan.rows if r.lattice]
        assert len(extras) == PER_EXTRA["1706"]["sleep"]
        assert all(r.axis == "preset" and r.lattice == "sleep" for r in extras)
        assert all(r.command_id == "" for r in extras)

    def test_serialized_only_on_extras_rows(self):
        rows = build_save_plan(_device(), matrix=fork("1706")).as_dict()["rows"]
        for row in rows:
            if "lattice" in row:
                assert row["axis"] == "preset" and row["lattice"] == "sleep"
            else:
                assert "axis" not in row
        assert sum("lattice" in r for r in rows) == 5

    @pytest.mark.parametrize("name", FORKS)
    def test_a_plan_without_extras_is_byte_identical(self, name):
        """No key added to any row of a wig without extras: the stripped
        fork's plan serializes with neither field anywhere."""
        rows = build_save_plan(
            _device(), matrix=fork(name, extras=False),
        ).as_dict()["rows"]
        assert rows
        assert not any("axis" in r or "lattice" in r for r in rows)


# ---------------------------------------------------------------------------
# Plan 5 and 9: every existing matrix fixture, unchanged
# ---------------------------------------------------------------------------


#: CAPTURED FROM THE BASE TREE (fbc2650) by running this same summary
#: there, before any change, then written down. The shape hash covers
#: each row's key, section, temp role and temp-less flag, in order.
BASELINE = {
    "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json": (
        14, "a6aba5bfc35cc1af", "7657c780b2b63b81"),
    "adapters/smartir_climate_swing.json": (
        8, "39403728db787e1e", "97301adf0ade7edd"),
    "field-packs/DAIKIN216.defects.json": (
        12, "341bae183c55be4c", "f17bd8b8f98f4cae"),
    "field-packs/DAIKIN216.json": (
        12, "341bae183c55be4c", "4981da44f346b424"),
    "gh108/cecotec-forceclima-12650.json": (
        5, "d4e5e6b3602dc310", "9d79caa938641142"),
}


def _existing_matrices():
    from custom_components.hair import wig_adapters as wa

    for path in sorted(glob.glob(str(FIXTURES / "wigs" / "*.wig.json"))):
        result = parse_wig(Path(path).read_text(encoding="utf-8"))
        if result.ok and result.wig.climate is not None:
            yield Path(path).name, result.wig
    for path in sorted(glob.glob(str(FIXTURES / "**" / "*.json"), recursive=True)):
        try:
            text = Path(path).read_text(encoding="utf-8")
            if wa.sniff_format(text) != "smartir_climate":
                continue
            converted = wa.convert(text, path)
        except Exception:  # not every fixture is a source
            continue
        for wig in converted.wigs:
            if wig.climate is not None and not wig.climate.extras:
                yield path.split("fixtures/", 1)[1], wig


class TestExistingFixturesUnchanged:
    def test_every_matrix_fixture_matches_the_base_tree(self):
        seen = {}
        for name, wig in _existing_matrices():
            matrix = wig.climate
            rows = dimension_checklist(matrix)
            shape = [(r.key, r.section, r.temp_role, r.temp_less) for r in rows]
            digests = sorted(dimension_checklist_digests(matrix))
            seen[name] = (
                len(rows),
                hashlib.sha256(json.dumps(shape).encode()).hexdigest()[:16],
                hashlib.sha256(json.dumps(digests).encode()).hexdigest()[:16],
            )
            full = _bundle(digests)
            partial = _bundle(digests[:-1])
            assert bundle_is_complete(full, wig) is True, name
            assert bundle_is_complete(partial, wig) is False, name
            assert all(r.axis is None and r.lattice is None for r in rows)
        assert seen == BASELINE


# ---------------------------------------------------------------------------
# The dialog's TEST, end to end (plan 6, 8)
# ---------------------------------------------------------------------------


E2E_DRIVER = """
import { readFileSync } from "node:fs";
import { checklistSendState } from "./matrix-lattice.js";
import { HairApi } from "./api.js";

async function wire(state) {
    const sent = [];
    const hass = { connection: { sendMessagePromise: (m) => {
        sent.push(m);
        return Promise.resolve({});
    } } };
    await new HairApi(hass).matrixSend("dev-1", state);
    return sent[0];
}

const rows = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const out = [];
for (const row of rows) {
    // The extras row exactly as the dialog's TEST sends it...
    const extras = await wire(checklistSendState(row));
    // ...and the MAIN lattice's cell at the same coordinates, sent the
    // same way: the same row with its lattice taken off.
    const main = await wire(checklistSendState(
        { ...row, axis: null, lattice: null }));
    out.push({ key: row.alias, extras, main });
}
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def e2e_js(tmp_path_factory):
    if not TSC.exists() or shutil.which("node") is None:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("extrasfit")
    subprocess.run(
        [
            str(TSC), "src/matrix-lattice.ts", "src/api.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "e2e.mjs").write_text(E2E_DRIVER, encoding="utf-8")
    return out


def _run_e2e(out: Path, rows: list[dict]) -> list[dict]:
    data = out / "rows.json"
    data.write_text(json.dumps(rows), encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "e2e.mjs"), str(data)],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


def _wire_door(hass, matrix):
    device = _device()
    manager = MagicMock()
    manager.get_device = MagicMock(return_value=device)
    manager.async_get_matrix = AsyncMock(return_value=matrix)
    # Resolve the heard future at once, as a live receiver would, so
    # the door does not sit out its listen window on every send.
    async def _heard(*_args, heard_future=None, **_kw):
        if heard_future is not None and not heard_future.done():
            heard_future.set_result("infrared.receiver")

    manager.async_send_matrix_cell = AsyncMock(side_effect=_heard)
    hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager,
        "orchestrator": MagicMock(),
        "signal_monitor": MagicMock(),
    }}
    return manager


def _conn():
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    return conn


class TestTheDialogSendsTheExtrasCode:
    """THE FRONTEND TEST THAT MATTERS MOST (plan 6, 8).

    Every extras row of a real plan goes through the dialog's own send
    helper (``checklistSendState``, which carries the pair through
    ``latticeFields``) and the real ``HairApi.matrixSend``, and the
    message that lands on the websocket is handed to the real door.
    Nothing here builds a message by hand. The code the door sends for
    the extras row must be that lattice's code, and must differ from
    the main lattice's code at the same coordinates. Without the pair,
    TEST would send the main code and report success on the wrong
    frame.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("name", FORKS)
    async def test_every_extras_row_sends_its_own_lattices_code(
        self, name, e2e_js, fake_hass
    ):
        from custom_components.hair.websocket_api import ws_device_matrix_send

        matrix = fork(name)
        plan_rows = build_save_plan(_device(), matrix=matrix).as_dict()["rows"]
        extras_rows = [r for r in plan_rows if r.get("lattice")]
        assert len(extras_rows) == sum(PER_EXTRA[name].values())

        wired = _run_e2e(e2e_js, extras_rows)
        manager = _wire_door(fake_hass, matrix)
        main_codes = {cell_key(c): c.pronto for c in matrix.cells}
        extra_codes = {
            e.key: {cell_key(c): c.pronto for c in e.cells}
            for e in matrix.extras
        }

        for item in wired:
            sent = []
            for msg in (item["extras"], item["main"]):
                manager.async_send_matrix_cell.reset_mock()
                conn = _conn()
                await ws_device_matrix_send(fake_hass, conn, {"id": 1, **msg})
                conn.send_error.assert_not_called()
                sent.append(manager.async_send_matrix_cell.await_args.args[2])
            # The row's own key names its lattice: preset:<key>/<coords>.
            qualifier, coords = item["key"].split("/", 1)
            lattice = qualifier.split(":", 1)[1]
            assert sent[0] != sent[1], (
                f"{item['key']}: TEST sent the main lattice's code for an "
                "extras row"
            )
            assert sent[0] == extra_codes[lattice][coords]
            assert sent[1] == main_codes[coords]
            assert item["extras"]["axis"] == "preset"
            assert item["extras"]["lattice"] == lattice
            assert "axis" not in item["main"]
            assert "lattice" not in item["main"]


GROUPS_DRIVER = """
import { readFileSync } from "node:fs";
import { peerGroups } from "./matrix-lattice.js";

const plans = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const out = {};
for (const [name, rows] of Object.entries(plans)) {
    out[name] = peerGroups(rows);
}
console.log(JSON.stringify(out));
"""


def _groups(out: Path, plans: dict[str, list[dict]]) -> dict:
    (out / "groups.mjs").write_text(GROUPS_DRIVER, encoding="utf-8")
    data = out / "plans.json"
    data.write_text(json.dumps(plans), encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "groups.mjs"), str(data)],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


def _flat_device() -> IRDevice:
    """A matrix device with a flat button riding along, so the plan has
    rows after ``off`` as real plans do."""
    from custom_components.hair.models import IRCommand

    device = _device()
    device.commands = [IRCommand(id="c-1", name="Ionizer", protocol="PRONTO",
                                 code=_pronto(62000), repeat_count=0)]
    return device


@pytest.fixture(scope="module")
def grouped(e2e_js):
    """Every fork's real plan rows, with and without extras, and what
    ``peerGroups`` makes of each."""
    plans = {}
    for name in FORKS:
        plans[name] = build_save_plan(
            _flat_device(), matrix=fork(name)).as_dict()["rows"]
        plans[f"{name}-bare"] = build_save_plan(
            _flat_device(), matrix=fork(name, extras=False),
        ).as_dict()["rows"]
    return plans, _groups(e2e_js, plans)


class TestTheDialogGroupsByLattice:
    """Plan 6, driven: the dialog renders from ``peerGroups``, so what
    it returns on real plan rows is what the fitter sees."""

    @pytest.mark.parametrize("name", FORKS)
    def test_no_headings_without_extras(self, name, grouped):
        """Null, so the dialog draws its flat list exactly as before."""
        _plans, out = grouped
        assert out[f"{name}-bare"] is None

    @pytest.mark.parametrize("name", FORKS)
    def test_main_first_then_each_extra_in_wig_order(self, name, grouped):
        _plans, out = grouped
        keys = [g["key"] for g in out[name]["groups"]]
        assert keys == [None] + [k for k, _ in SHAPES[name]["extras"]]
        for group in out[name]["groups"]:
            assert all(r.get("lattice") == group["key"] for r in group["rows"])
        assert [len(g["rows"]) for g in out[name]["groups"][1:]] == list(
            PER_EXTRA[name].values()
        )

    @pytest.mark.parametrize("name", FORKS)
    def test_nothing_moves(self, name, grouped):
        plans, out = grouped
        got = out[name]
        flat = got["before"] + [
            r for g in got["groups"] for r in g["rows"]
        ] + got["after"]
        assert flat == plans[name]

    @pytest.mark.parametrize("name", FORKS)
    def test_power_stays_outside_every_group(self, name, grouped):
        _plans, out = grouped
        got = out[name]
        assert [r["alias"] for r in got["before"]] == (
            ["on"] if SHAPES[name]["on"] else []
        )
        assert got["after"][0]["alias"] == "off"
        assert got["after"][-1]["alias"] == "Ionizer"
        for group in got["groups"]:
            assert not any(r.get("power") for r in group["rows"])


def _dialog() -> str:
    return (FRONTEND / "src" / "ir-save-perfect-dialog.ts").read_text(
        encoding="utf-8")


def _method(text: str, start: str) -> str:
    body = text[text.index(start):]
    return body[: body.index("\n    }\n") + 6]


class TestTheDialogSource:
    """Structural pins that need no toolchain."""

    def test_test_sends_through_the_shared_helper(self):
        body = _method(_dialog(), "private async _sendRow(")
        assert "checklistSendState(row)" in body
        assert "mode: row.mode" not in body

    def test_the_list_renders_from_peer_groups(self):
        text = _dialog()
        assert "const peers = peerGroups(mainRows);" in text
        assert "this._renderPeerGroups(peers, readOnly)" in text

    def test_an_extras_row_key_differs_from_its_main_twin(self):
        """The frontend twin of the dedup trap: the toggle key must
        carry the pair, appended so main keys do not move."""
        body = _method(_dialog(), "private _rowKey(")
        assert (
            'if (row.lattice != null) parts.push(row.axis ?? "", row.lattice);'
        ) in body

    def test_the_head_shows_the_files_word_verbatim(self):
        text = _dialog()
        css = text[text.index(".peer-head {"):]
        css = css[: css.index("}")]
        assert "text-transform" not in css
        body = _method(text, "private _renderPeerGroups(")
        assert 't("wigs.save.peer_main")' in body
        assert ": g.key}" in body

    def test_the_stem_is_not_lattice(self):
        """``lattice`` already names the whole matrix in this dialog."""
        text = _dialog()
        assert "lattice-group" not in text
        assert "wigs.save.lattice_main" not in text

    def test_every_locale_carries_the_main_heading(self):
        locales = sorted((FRONTEND / "src" / "locales").glob("*.json"))
        assert len(locales) == 10
        for path in locales:
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data.get("wigs.save.peer_main", "").strip(), path.name
