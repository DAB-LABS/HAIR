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
from typing import ClassVar

import pytest

FRONTEND = Path(__file__).parent.parent / "frontend"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"
SRC = FRONTEND / "src"

DRIVER = """
import { latticeFields, latticeView } from "./matrix-lattice.js";

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
    fields: {
        both: latticeFields({ axis: "preset", lattice: "eco" }),
        neither_null: latticeFields({ axis: null, lattice: null }),
        neither_absent: latticeFields({}),
        axis_only: latticeFields({ axis: "preset", lattice: null }),
        lattice_only: latticeFields({ lattice: "eco" }),
        no_ref: latticeFields(null),
        undefined_ref: latticeFields(undefined),
        // A card pick carries more than the pair; the helper takes
        // only what it names.
        from_pick: latticeFields({
            power: null, mode: "cool", fan: "auto", swing: null,
            temp: 22, name: "(eco) cool / fan: auto / 22",
            axis: "preset", lattice: "eco",
        }),
    },
}));
"""


# THE WIRE, driven. ``api.ts`` is compiled and its real HairApi run
# against a connection that records what it is handed, so these tests
# see the exact message each method puts on the websocket -- the thing
# the round-1 hole got wrong, and the thing a source pin can only
# approximate.
WIRE_DRIVER = """
import { HairApi } from "./api.js";

async function wire(call) {
    const sent = [];
    const hass = { connection: { sendMessagePromise: (m) => {
        sent.push(m);
        return Promise.resolve({});
    } } };
    await call(new HairApi(hass));
    return sent[0];
}

const COORDS = { mode: "cool", fan: "auto", swing: null, temp: 22 };
const MAIN = { ...COORDS, axis: null, lattice: null };
const ECO = { ...COORDS, axis: "preset", lattice: "eco" };
const HALF = { ...COORDS, axis: "preset", lattice: null };

console.log(JSON.stringify({
    send_main: await wire((a) => a.matrixSend("dev-1", MAIN)),
    send_bare: await wire((a) => a.matrixSend("dev-1", COORDS)),
    send_eco: await wire((a) => a.matrixSend("dev-1", ECO)),
    send_half: await wire((a) => a.matrixSend("dev-1", HALF)),
    send_power: await wire((a) => a.matrixSend("dev-1", { power: "off" })),
    command_main: await wire((a) => a.matrixCommand("dev-1", MAIN)),
    command_eco: await wire((a) => a.matrixCommand("dev-1", ECO)),
    command_half: await wire((a) => a.matrixCommand("dev-1", HALF)),
    cell_main: await wire((a) => a.remoteMatrixCell(
        "r-1", { ...MAIN, power: null })),
    cell_eco: await wire((a) => a.remoteMatrixCell(
        "r-1", { ...ECO, power: null })),
    cell_half: await wire((a) => a.remoteMatrixCell(
        "r-1", { ...HALF, power: null })),
    cell_power_eco: await wire((a) => a.remoteMatrixCell(
        "r-1", { power: "off", axis: "preset", lattice: "eco" })),
}));
"""


def _toolchain() -> None:
    if not TSC.exists() or shutil.which("node") is None:
        pytest.skip("frontend toolchain not installed (node_modules / node)")


@pytest.fixture(scope="module")
def wire(tmp_path_factory):
    """Every message the three forwarding methods put on the wire."""
    _toolchain()
    out = tmp_path_factory.mktemp("wirejs")
    subprocess.run(
        [
            str(TSC), "src/api.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "wire.mjs").write_text(WIRE_DRIVER, encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "wire.mjs")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


# THE HEARD RINGS, run. A plain press rings as it always has; a press
# whose code the file stores under several settings rings no chip on a
# dimension it does not pin down, and a tile only where the whole
# coordinate is one of the cells carrying that code.
RINGS_DRIVER = """
import { heardRings } from "./matrix-lattice.js";

const plain = {
    cell_key: "cool/auto/22", cell_name: "cool / fan: auto / 22",
    power: null, mode: "cool", fan: "auto", swing: null, temp: 22,
    at: "t", sl_pattern: null, receiver_entity_id: null,
    receiver_area_name: null,
};
const bare = { ...plain, mode: "dry", temp: null, cell_key: "dry/auto" };
const dryTemps = [18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30];
const dry = {
    ...plain, mode: "dry", fan: "auto", swing: "off", temp: 30,
    cell_key: "dry/auto/off/30",
    cell_name: "dry / fan: auto / swing: off / 18-30",
    spanned: { temp: dryTemps },
    members: dryTemps.map((t) => ["dry", "auto", "off", t]),
};
// The 1294 shape: not every combination of its values.
const shape1294 = {
    ...plain, mode: "cool", fan: "quiet", swing: "off", temp: 18,
    spanned: { fan: ["low", "quiet"], swing: ["off", "vertical"] },
    members: [["cool", "low", "vertical", 18], ["cool", "quiet", "off", 18]],
};
const bareGroup = {
    ...plain, mode: "fan_only", fan: "high", swing: null, temp: null,
    spanned: { fan: ["auto", "high"] },
    members: [["fan_only", "auto", null, null], ["fan_only", "high", null, null]],
};
const MAIN = {};
const branch = (mode, fan, swing) => ({ mode, fan, swing });

console.log(JSON.stringify({
    plain_fresh: heardRings(plain, MAIN, branch("cool", "auto", null), false),
    plain_on_branch: heardRings(plain, MAIN, branch("cool", "auto", null), true),
    plain_off_branch: heardRings(plain, MAIN, branch("cool", "quiet", null), true),
    plain_bare: heardRings(bare, MAIN, branch("dry", "auto", null), false),
    plain_old_row: heardRings(
        { ...plain, spanned: undefined, members: undefined },
        MAIN, branch("cool", "auto", null), false),
    plain_empty_spanned: heardRings(
        { ...plain, spanned: {} }, MAIN, branch("cool", "auto", null), false),
    dry_fresh: heardRings(dry, MAIN, branch("dry", "auto", "off"), false),
    dry_other_fan: heardRings(dry, MAIN, branch("dry", "high", "off"), true),
    g1294_low_off: heardRings(shape1294, MAIN, branch("cool", "low", "off"), true),
    g1294_low_vertical: heardRings(
        shape1294, MAIN, branch("cool", "low", "vertical"), true),
    g1294_quiet_off_fresh: heardRings(
        shape1294, MAIN, branch("cool", "quiet", "off"), false),
    bare_group: heardRings(bareGroup, MAIN, branch("fan_only", "high", null), true),
    // A drawn branch whose swing is undefined, as a cell omits it.
    undefined_swing: heardRings(
        bareGroup, MAIN, { mode: "fan_only", fan: "auto" }, true),
    power: heardRings({ ...plain, power: "off", mode: null },
        MAIN, branch("cool", "auto", null), false),
    other_lattice: heardRings({ ...dry, axis: "preset", lattice: "eco" },
        MAIN, branch("dry", "auto", "off"), false),
    nothing: heardRings(null, MAIN, branch("cool", "auto", null), false),
}));
"""


@pytest.fixture(scope="module")
def rings(tmp_path_factory):
    """``heardRings`` run on the shapes above."""
    _toolchain()
    out = tmp_path_factory.mktemp("ringsjs")
    subprocess.run(
        [
            str(TSC), "src/matrix-lattice.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "rings.mjs").write_text(RINGS_DRIVER, encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "rings.mjs")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


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


class TestLatticeFields:
    """The helper every forwarder goes through: both, or nothing."""

    def test_both_present_gives_both(self, views):
        assert views["fields"]["both"] == {
            "axis": "preset", "lattice": "eco",
        }

    def test_both_absent_gives_nothing_at_all(self, views):
        """An EMPTY object, not ``{axis: null}``: spread into a message
        it must add no key, so a main-lattice message is byte for byte
        what it was before lattices existed."""
        fields = views["fields"]
        assert fields["neither_null"] == {}
        assert fields["neither_absent"] == {}
        assert fields["no_ref"] == {}
        assert fields["undefined_ref"] == {}

    def test_one_without_the_other_gives_nothing(self, views):
        """Never a half pair. The doors refuse one field without the
        other as a client bug, so the helper does not emit one."""
        assert views["fields"]["axis_only"] == {}
        assert views["fields"]["lattice_only"] == {}

    def test_it_takes_a_whole_card_pick(self, views):
        """Written against the ref shape, not the pick, so the fitting
        round's dialog can hand it whatever row it has."""
        assert views["fields"]["from_pick"] == {
            "axis": "preset", "lattice": "eco",
        }


# Today's messages, CAPTURED FROM THE BASE TREE (ce66d65) by driving its
# own api.ts the same way, then written down here. A main-lattice pick
# must still produce exactly these.
TODAY_SEND = {
    "type": "hair/devices/matrix-send", "device_id": "dev-1",
    "mode": "cool", "fan": "auto", "swing": None, "temp": 22,
}
TODAY_COMMAND = {
    "type": "hair/devices/matrix-command", "device_id": "dev-1",
    "mode": "cool", "fan": "auto", "swing": None, "temp": 22,
}
TODAY_CELL = {
    "type": "hair/trigger-remote/matrix-cell", "remote_id": "r-1",
    "mode": "cool", "fan": "auto", "temp": 22,
}


class TestTheLatticeReachesTheWire:
    """The hole itself, closed, observed on the websocket.

    Round 1 put the pair on every pick and taught every door, but the
    code in between rebuilt each message from the coordinates alone, so
    an extras cell reached the door as the MAIN lattice's cell and the
    main code went out reporting success.
    """

    def test_a_main_pick_sends_exactly_todays_message(self, wire):
        """The call sites now pass ``axis: null, lattice: null`` on
        every main pick; not one extra key reaches the wire, and the
        key ORDER is today's too."""
        assert wire["send_main"] == TODAY_SEND
        assert list(wire["send_main"]) == list(TODAY_SEND)
        assert wire["command_main"] == TODAY_COMMAND
        assert list(wire["command_main"]) == list(TODAY_COMMAND)
        assert wire["cell_main"] == TODAY_CELL
        assert list(wire["cell_main"]) == list(TODAY_CELL)

    def test_a_caller_that_never_heard_of_lattices_is_unchanged(self, wire):
        assert wire["send_bare"] == TODAY_SEND

    def test_an_extras_pick_carries_its_lattice_on_every_method(self, wire):
        pair = {"axis": "preset", "lattice": "eco"}
        assert wire["send_eco"] == {**TODAY_SEND, **pair}
        assert wire["command_eco"] == {**TODAY_COMMAND, **pair}
        assert wire["cell_eco"] == {**TODAY_CELL, **pair}

    def test_a_half_pair_never_reaches_a_door(self, wire):
        """It would be refused there as a client bug; it is dropped
        here instead, and the message is the main one."""
        assert wire["send_half"] == TODAY_SEND
        assert wire["command_half"] == TODAY_COMMAND
        assert wire["cell_half"] == TODAY_CELL

    def test_a_power_press_is_untouched(self, wire):
        assert wire["send_power"] == {
            "type": "hair/devices/matrix-send", "device_id": "dev-1",
            "power": "off",
        }

    def test_the_transport_makes_no_power_policy(self, wire):
        """A power request carrying a lattice is forwarded, not
        stripped, so the door answers it by its own documented rule
        (the trigger door reports it as a client bug, 4a)."""
        assert wire["cell_power_eco"] == {
            "type": "hair/trigger-remote/matrix-cell", "remote_id": "r-1",
            "power": "off", "axis": "preset", "lattice": "eco",
        }


class TestEveryForwarderCarriesThePair:
    """Source pins, one per forwarder, which run with no toolchain.

    The wire tests above prove the api layer; these guard the four call
    sites that feed it, so a future rewrite of any one message cannot
    drop the pair quietly the way round 1 did.
    """

    def _body(self, filename: str, start: str) -> str:
        text = (SRC / filename).read_text(encoding="utf-8")
        body = text[text.index(start):]
        end = body.find("\n    private ", 1)
        return body if end == -1 else body[:end]

    def _assert_forwards(self, body: str, source: str) -> None:
        assert f"axis: {source}.axis" in body, body[:200]
        assert f"lattice: {source}.lattice" in body, body[:200]

    def test_device_detail_matrix_send(self):
        self._assert_forwards(
            self._body("ir-device-detail.ts", "private async _matrixSend("),
            "pick",
        )

    def test_device_detail_matrix_save_command(self):
        self._assert_forwards(
            self._body(
                "ir-device-detail.ts", "private async _matrixSaveCommand("
            ),
            "pick",
        )

    def test_device_list_last_heard_trigger(self):
        """Door 1. Not in the review's inventory, and the same hole:
        the heard state's lattice, which the backend already sends."""
        self._assert_forwards(
            self._body("ir-device-list.ts", "private _onLastHeardTrigger("),
            "heard",
        )

    def test_device_list_matrix_save_trigger(self):
        """Doors 2 and 3, the card's action bar."""
        self._assert_forwards(
            self._body("ir-device-list.ts", "private _onMatrixSaveTrigger("),
            "p",
        )

    def _api_method(self, name: str) -> str:
        text = (SRC / "api.ts").read_text(encoding="utf-8")
        body = text[text.index(f"    {name}(\n"):]
        return body[: body.index("\n    }\n") + 6]

    def test_api_matrix_send(self):
        body = self._api_method("matrixSend")
        assert "axis?: string | null;" in body
        assert "...latticeFields({ axis, lattice })" in body
        # Stripped off the raw spread, which is what keeps a main pick
        # from putting two null keys on the wire.
        assert "const { axis, lattice, ...coords } = state;" in body

    def test_api_matrix_command(self):
        body = self._api_method("matrixCommand")
        assert "axis?: string | null;" in body
        assert "...latticeFields({ axis, lattice })" in body
        assert "const { axis, lattice, ...coords } = state;" in body

    def test_api_remote_matrix_cell(self):
        body = self._api_method("remoteMatrixCell")
        assert "axis?: string | null;" in body
        assert "Object.assign(msg, latticeFields(pick));" in body

    def test_last_heard_declares_the_pair(self):
        """What lets door 1 forward it at all: the type now says what
        the backend has sent since the listener learned extras."""
        text = (SRC / "types.ts").read_text(encoding="utf-8")
        body = text[text.index("export interface LastHeard {"):]
        body = body[: body.index("\n}\n")]
        assert "axis?: string | null;" in body
        assert "lattice?: string | null;" in body


class TestTheHeardRings:
    """``heardRings``: which chips and tiles a heard state rings."""

    NONE: ClassVar[dict] = {
        "mode": None, "fan": None, "swing": None, "tiles": [],
    }

    def test_a_plain_press_rings_as_it_always_did(self, rings):
        assert rings["plain_fresh"] == {
            "mode": "cool", "fan": "auto", "swing": None, "tiles": [22],
        }
        assert rings["plain_on_branch"]["tiles"] == [22]
        # Browsed off the heard branch: the chips stay, the tile does
        # not, because the same position there is another command.
        assert rings["plain_off_branch"] == {
            "mode": "cool", "fan": "auto", "swing": None, "tiles": [],
        }
        assert rings["plain_bare"]["tiles"] == [None]

    def test_a_row_from_before_reads_as_a_plain_press(self, rings):
        assert rings["plain_old_row"] == rings["plain_fresh"]
        assert rings["plain_empty_spanned"] == rings["plain_fresh"]

    def test_a_spanned_dimension_rings_no_chip(self, rings):
        assert rings["dry_fresh"]["mode"] == "dry"
        assert rings["dry_fresh"]["fan"] == "auto"
        assert rings["g1294_low_off"]["fan"] is None
        assert rings["g1294_low_off"]["swing"] is None
        assert rings["g1294_low_off"]["mode"] == "cool"

    def test_every_member_tile_rings_and_nothing_else(self, rings):
        """A fresh press, before any click: the drawn branch is the
        representative's, and every temperature the code is stored at
        rings there. Another fan's branch is another code."""
        assert rings["dry_fresh"]["tiles"] == list(range(18, 31))
        assert rings["dry_other_fan"]["tiles"] == []

    def test_a_tile_rings_only_on_a_whole_member_coordinate(self, rings):
        """The 1294 shape. cool / low / off is in the fans and in the
        swings, and cool / low / off / 18 is another code, so browsing
        it rings no tile; the two real members each ring 18."""
        assert rings["g1294_low_off"]["tiles"] == []
        assert rings["g1294_low_vertical"]["tiles"] == [18]
        assert rings["g1294_quiet_off_fresh"]["tiles"] == [18]

    def test_a_bare_branch_and_an_absent_dimension(self, rings):
        assert rings["bare_group"]["tiles"] == [None]
        assert rings["undefined_swing"]["tiles"] == [None]

    def test_power_another_lattice_and_nothing_ring_nothing(self, rings):
        assert rings["power"] == self.NONE
        assert rings["other_lattice"] == self.NONE
        assert rings["nothing"] == self.NONE


class TestTheMergedGroupPlumbing:
    """Source pins, for the parts that run only inside lit."""

    def test_last_heard_declares_spanned_and_members(self):
        text = (SRC / "types.ts").read_text(encoding="utf-8")
        body = text[text.index("export interface LastHeard {"):]
        body = body[: body.index("\n}\n")]
        assert "spanned?: Record<string, (string | number | null)[]>;" in body
        assert "members?: (string | number | null)[][];" in body

    def test_the_card_rings_through_the_helper(self):
        text = (SRC / "ir-matrix-card.ts").read_text(encoding="utf-8")
        assert "heardRings(" in text
        assert "_onHeardBranch" not in text
        assert "rings.tiles.includes(pos)" in text

    def test_door_one_offers_the_rows_name_on_a_spanned_press(self):
        text = (SRC / "ir-device-list.ts").read_text(encoding="utf-8")
        body = text[text.index("private _onLastHeardTrigger("):]
        body = body[: body.find("\n    private ", 1)]
        assert "heard.cell_name" in body
        assert "heard.spanned" in body
        assert ".presetName=${this._mintTrigger.name ??" in text
