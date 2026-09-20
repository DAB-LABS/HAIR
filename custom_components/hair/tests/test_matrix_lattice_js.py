"""The card's lattice chooser: the decision it rests on, executed.

The house tactic guards frontend structure by reading the TypeScript
as text, and that is enough for "is the chooser conditional". It is
not enough for the one thing this change actually turns on: WHICH
vocabulary the dimension browser reads once a lattice is picked. An
extra is usually narrower than the main lattice -- one real file's
``eco`` carries fan ``auto`` alone across four modes -- so a browser
reading its axes off the matrix offers values that lattice does not
have, and every one of them resolves to ``not_found`` at the door.
A grep cannot tell those two readings apart. Running the function can.

So the rule lives in ``matrix-lattice.ts``, which imports nothing but
types, and this transpiles it with the repo's own TypeScript and runs
it under node, the same way the pluck helpers and the landing notice
are run. The card itself imports ``lit`` and its siblings, so its
emitted module cannot stand alone; that is why the rule is beside it
rather than inside it, exactly as ``notice-state.ts`` sits beside the
panel.

SKIPPED when the frontend toolchain is not installed, for the reason
the sibling modules give: CI runs pytest without node_modules, and a
test that fails for want of a toolchain it never asked for is noise.
The source assertions at the foot of this file run everywhere.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

FRONTEND = Path(__file__).parent.parent / "frontend"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"
SRC = FRONTEND / "src"

DRIVER = """
import { latticeView } from "./matrix-lattice.js";

// The main lattice is WIDE: two fans, a swing. The eco lattice is
// NARROW: fan auto only, no swing. That is the real corpus shape and
// the whole reason the browser cannot read its axes off the matrix.
const PAYLOAD = {
    min_temp: 16, max_temp: 30, precision: 1, unit: "C",
    modes: ["cool", "dry"],
    fan_modes: ["auto", "quiet"],
    swing_modes: ["swing"],
    has_on: false,
    cells: [
        { m: "cool", f: "auto", t: 22 },
        { m: "cool", f: "quiet", s: "swing", t: 25 },
        { m: "dry", f: "auto" },
    ],
    lattices: [{
        axis: "preset",
        key: "eco",
        modes: ["cool", "dry"],
        fan_modes: ["auto"],
        swing_modes: [],
        cells: [
            { m: "cool", f: "auto", t: 22 },
            { m: "dry", f: "auto" },
        ],
    }],
};

const NO_EXTRAS = { ...PAYLOAD };
delete NO_EXTRAS.lattices;

console.log(JSON.stringify({
    main: latticeView(PAYLOAD, null),
    eco: latticeView(PAYLOAD, "eco"),
    stale: latticeView(PAYLOAD, "turbo"),
    no_extras_main: latticeView(NO_EXTRAS, null),
    no_extras_named: latticeView(NO_EXTRAS, "eco"),
}));
"""


@pytest.fixture(scope="module")
def views(tmp_path_factory):
    if not TSC.exists() or shutil.which("node") is None:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("latticejs")
    subprocess.run(
        [
            str(TSC), "src/matrix-lattice.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "driver.mjs").write_text(DRIVER, encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "driver.mjs")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


class TestTheBrowserReadsTheSelectedLattice:
    def test_no_selection_is_the_matrix_itself(self, views):
        main = views["main"]
        assert main["modes"] == ["cool", "dry"]
        assert main["fan_modes"] == ["auto", "quiet"]
        assert main["swing_modes"] == ["swing"]
        assert len(main["cells"]) == 3

    def test_an_extra_narrows_every_axis_to_its_own(self, views):
        """The failure this prevents: offering ``quiet`` and a swing
        on a lattice that has neither."""
        eco = views["eco"]
        assert eco["fan_modes"] == ["auto"]
        assert eco["swing_modes"] == []
        assert len(eco["cells"]) == 2
        assert views["main"]["fan_modes"] != eco["fan_modes"]

    def test_the_cells_come_from_the_selected_lattice(self, views):
        """Same coordinates in both, so only the cell COUNT and the
        source can tell them apart here; the codes differ at the door,
        which the backend suite pins."""
        assert len(views["eco"]["cells"]) < len(views["main"]["cells"])
        assert {"m": "cool", "f": "quiet", "s": "swing", "t": 25} in (
            views["main"]["cells"]
        )
        assert {"m": "cool", "f": "quiet", "s": "swing", "t": 25} not in (
            views["eco"]["cells"]
        )

    def test_a_payload_with_no_extras_is_the_matrix_either_way(self, views):
        """A card that never sees a lattices key behaves as it always
        did, including if a stale selection somehow survives a
        reload."""
        assert views["no_extras_main"]["fan_modes"] == ["auto", "quiet"]
        assert views["no_extras_named"]["fan_modes"] == ["auto", "quiet"]

    def test_a_stale_key_falls_back_to_the_main_lattice(self, views):
        """Client-side only, and deliberately unlike the backend: the
        card must have a branch to draw. The DOOR never falls back."""
        assert views["stale"]["fan_modes"] == ["auto", "quiet"]


class TestTheCardSource:
    """The structural claims, which need no toolchain."""

    def _card(self) -> str:
        return (SRC / "ir-matrix-card.ts").read_text(encoding="utf-8")

    def test_the_chooser_is_absent_not_empty_with_no_extras(self):
        card = self._card()
        body = card[card.index("private _renderLatticeRow()"):]
        body = body[: body.index("\n    /**")]
        assert "if (lattices.length === 0) return nothing;" in body

    def test_the_power_row_is_hidden_while_an_extra_is_selected(self):
        card = self._card()
        assert (
            "${this._selLattice === null\n"
            "                              ? this._renderPowerRow(mc)\n"
            "                              : nothing}"
        ) in card

    def test_the_chooser_sits_above_the_dimension_browser(self):
        card = self._card()
        chooser = card.index("${this._renderLatticeRow()}")
        first_dim = card.index("t(\"devices.matrix_dim_mode\")")
        assert chooser < first_dim

    def test_the_preview_name_carries_the_parentheses(self):
        card = self._card()
        body = card[card.index("private _cellName("):]
        body = body[: body.index("\n    /**")]
        assert "`(${this._selLattice}) ${name}`" in body

    def test_every_locale_carries_the_two_chooser_keys(self):
        locales = sorted((SRC / "locales").glob("*.json"))
        assert len(locales) == 10
        for path in locales:
            data = json.loads(path.read_text(encoding="utf-8"))
            for key in (
                "devices.matrix_dim_lattice",
                "devices.matrix_lattice_main",
            ):
                assert key in data, f"{path.name} is missing {key}"
                assert data[key].strip(), f"{path.name}:{key} is empty"
