"""The Plucker's ghosts, actually executed (1.4.1).

``buildGhosts`` decides everything the Plucker tab offers beyond what
is already plucked: which ghosts exist, which are disabled and why, and
their order (stores by source, then the tweezer
ghosts, then the disabled ones). ``idsToTop`` decides where a new
remote lands. Both are pure, so this transpiles ``pluck-ghosts.ts`` with
the repo's own TypeScript and runs them under node, as
``test_pluck_helpers_js.py`` does for the empty-tab helpers.

SKIPPED when the frontend toolchain is not installed, for the same
reason as that file: CI runs pytest without node_modules.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

FRONTEND = Path(__file__).parent.parent / "frontend"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"

pytestmark = pytest.mark.skipif(
    not TSC.exists() or shutil.which("node") is None,
    reason="frontend toolchain not installed (node_modules / node)",
)

DRIVER = r"""
import { buildGhosts, idsToTop, landingSentence, tweezerRemoteName } from "./pluck-ghosts.js";

const sub = (subdevice, over) => ({
    subdevice,
    label: `Living room: ${subdevice}`,
    codes: 3, ir_codes: 3, rf_codes: 0,
    pluckable: true, reason: null, device_id: null,
    ...over,
});
const store = (over) => ({
    store_id: "broadlink_remote_aa_codes",
    integration: "broadlink",
    friendly_name: "Living room",
    subdevices: 0, codes: 0, ir_codes: 0, rf_codes: 0,
    error: null,
    remotes: [],
    ...over,
});
const tuyaStore = (over) => store({
    store_id: "tuya_local_remote_bb",
    integration: "tuya_local",
    friendly_name: "Office hub",
    ...over,
});
const oirb = (over) => store({
    store_id: "openirblaster_cc",
    integration: "openirblaster",
    friendly_name: "Hallway",
    ...over,
});
const vendor = {
    integration: "tuya_local",
    name: "Tuya Local",
    appliance_label: "Appliance (the name you used at learn time)",
    appliance_help: "Find this in your Tuya Smart app.",
    blasters: [
        { entity_id: "remote.office_hub", name: "Office hub" },
        { entity_id: "remote.den_hub", name: "Den hub" },
    ],
};
const src = (integration, name, mechanisms) =>
    ({ integration, name, mechanisms, loaded: true, ready: {} });
const sources = [
    src("broadlink", "Broadlink", ["storage"]),
    src("tuya_local", "Tuya Local", ["replay", "storage"]),
    src("openirblaster", "OpenIRBlaster", ["storage"]),
];
const brief = (g) => [g.kind, g.name, g.reason ?? null];

const out = {};

out.mixed = buildGhosts(
    [
        // Server order puts Tuya first here on purpose: the panel sorts.
        tuyaStore({ remotes: [sub("heater", { label: "Office hub: heater" })] }),
        oirb({ remotes: [sub("OpenIRBlaster", { label: "Hallway" })] }),
        store({
            remotes: [
                sub("tv", { device_id: "dev1" }),
                sub("soundbar"),
                sub("garage", { pluckable: false, reason: "radio_only" }),
                sub("old", { pluckable: false, reason: "empty", codes: 0 }),
                sub("projector"),
            ],
        }),
        store({
            store_id: "broadlink_remote_dd_codes",
            friendly_name: "Bedroom",
            error: "bad json",
            remotes: [],
        }),
        tuyaStore({ store_id: "tuya_local_remote_ee", friendly_name: "Garage hub", remotes: [] }),
    ],
    [vendor],
    sources,
).map(brief);

out.full = buildGhosts([store({ remotes: [sub("soundbar")] })], [vendor], sources);

out.deleted = buildGhosts(
    [store({ remotes: [sub("tv", { device_id: null })] })], [], sources,
).map(brief);

const old = (store_id, friendly_name, codes) => ({
    store_id, integration: "broadlink", friendly_name,
    subdevices: codes ? 2 : 0, codes, ir_codes: codes, rf_codes: 0, error: null,
});
out.legacy = buildGhosts(
    [
        old("s1", "Old server", 7),
        old("s2", "Old empty", 0),
    ],
    [], sources,
).map((g) => [g.kind, g.name, g.subdevice ?? null, g.codes ?? null, g.reason ?? null]);

out.nameless_source = buildGhosts(
    [store({ integration: "zigbee_ir", remotes: [sub("x")] })], [], [],
).map((g) => g.source);

out.top = [
    idsToTop(["a", "b", "c"], ["c"]),
    idsToTop(["a", "b", "c"], ["d"]),
    idsToTop(["a", "b"], ["b", "b", "a"]),
    idsToTop(["a", "b"], []),
];

out.names = [
    tweezerRemoteName("Office hub", " aircon "),
    tweezerRemoteName("Office hub", "  "),
];

const t = (key, subs) => {
    let s = key;
    for (const [k, v] of Object.entries(subs ?? {})) s += `|${k}=${v}`;
    return s;
};
const tp = (key, n) => `${key}#${n}`;
const imp = (over) => ({
    remotes: 1, signals: 4, washed: 0, kept_raw: 0, toggle_pairs: 0,
    rf_receipted: 0, no_timings: 0, already_present: 0, ...over,
});
out.landing = [
    landingSentence(imp({ washed: 2, rf_receipted: 1 }), t, tp),
    landingSentence(imp({ already_present: 4 }), t, tp),
];

process.stdout.write(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    out = tmp_path_factory.mktemp("ghostsjs")
    subprocess.run(
        [
            str(TSC), "src/pluck-ghosts.ts",
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


class TestBuildGhosts:
    def test_the_ruled_order(self, run):
        """Store ghosts by source (Broadlink, Tuya Local, OpenIRBlaster),
        file order inside a store, then one tweezer per replay blaster,
        then everything disabled, in the same source order."""
        assert run["mixed"] == [
            ["store", "Living room: soundbar", None],
            ["store", "Living room: projector", None],
            ["store", "Office hub: heater", None],
            ["store", "Hallway", None],
            ["tweezer", "Office hub", None],
            ["tweezer", "Den hub", None],
            ["disabled", "Living room: garage", "radio_only"],
            ["disabled", "Living room: old", "empty"],
            ["disabled", "Bedroom", "unreadable"],
            ["disabled", "Garage hub", "empty"],
        ]

    def test_a_plucked_sub_device_has_no_ghost(self, run):
        names = [row[1] for row in run["mixed"]]
        assert "Living room: tv" not in names

    def test_a_deleted_remote_brings_its_ghost_back(self, run):
        assert run["deleted"] == [["store", "Living room: tv", None]]

    def test_a_store_ghost_carries_what_the_click_needs(self, run):
        soundbar = run["full"][0]
        assert soundbar["kind"] == "store"
        assert soundbar["storeId"] == "broadlink_remote_aa_codes"
        assert soundbar["subdevice"] == "soundbar"
        assert soundbar["codes"] == 3
        assert soundbar["source"] == "Broadlink"

    def test_a_tweezer_ghost_carries_the_blaster(self, run):
        office = run["full"][1]
        assert office["kind"] == "tweezer"
        assert office["entityId"] == "remote.office_hub"
        assert office["integration"] == "tuya_local"
        assert office["blasterName"] == "Office hub"
        assert office["source"] == "Tuya Local"
        assert office["applianceHelp"] == "Find this in your Tuya Smart app."
        assert office["applianceLabel"].startswith("Appliance")

    def test_keys_are_unique(self, run):
        keys = [g["key"] for g in run["full"]]
        assert len(keys) == len(set(keys))

    def test_an_older_server_plucks_the_whole_store(self, run):
        """No sub-device list: one ghost per store, no sub-device, so a
        click imports the whole store as the old dialog did."""
        assert run["legacy"] == [
            ["store", "Old server", None, 7, None],
            ["disabled", "Old empty", None, None, "empty"],
        ]

    def test_an_unknown_source_shows_its_domain(self, run):
        assert run["nameless_source"] == ["zigbee_ir"]


class TestIdsToTop:
    def test_new_remotes_land_at_the_top(self, run):
        assert run["top"] == [
            ["c", "a", "b"],
            ["d", "a", "b", "c"],
            ["b", "a"],
            ["a", "b"],
        ]


class TestNames:
    def test_blaster_colon_appliance(self, run):
        assert run["names"] == ["Office hub: aircon", "Office hub"]


class TestLanding:
    def test_zero_clauses_are_left_out(self, run):
        line = run["landing"][0]
        assert "pluckstore.landing.washed#2" in line
        assert "pluckstore.landing.rf#1" in line
        assert "kept_raw" not in line
        assert "no_timings" not in line

    def test_all_already_present_says_only_that(self, run):
        line = run["landing"][1]
        assert line.endswith("pluckstore.landing.already#4")
        assert "washed" not in line


class TestThePanel:
    """The tab, read as text (the house tactic for render code)."""

    SRC = FRONTEND / "src"

    def _pluck(self) -> str:
        return (self.SRC / "ir-pluck.ts").read_text(encoding="utf-8")

    def test_the_ghosts_wear_the_add_tiles_own_sheet(self):
        body = self._pluck()
        assert "ghostTileStyles" in body
        tile = (self.SRC / "ir-ghost-tile.ts").read_text(encoding="utf-8")
        assert "ghostTileStyles" in tile
        sheet = (self.SRC / "ghost-tile-styles.ts").read_text(encoding="utf-8")
        assert ".gt-tile {" in sheet
        css_body = sheet.split("export const ghostTileStyles = css`", 1)[1]
        assert ":host" not in css_body

    def test_dimmer_at_rest_than_the_devices_tile(self):
        body = self._pluck()
        block = body.split(".gt-tile.pk {", 1)[1].split("}", 1)[0]
        assert "opacity: 0.3;" in block

    def test_ghosts_sit_outside_the_sortable_list(self):
        """Sortable maps drag indices onto _devices; a ghost inside
        .device-list would shift them."""
        body = self._pluck()
        ghosts = body.split("private _renderGhosts(", 1)[1]
        ghosts = ghosts.split("private _renderGhost(", 1)[0]
        assert 'class="ghost-list"' in ghosts
        assert "device-list" not in ghosts

    def test_the_tweezer_runs_before_it_creates(self):
        """A failed first command must leave no empty remote behind."""
        body = self._pluck()
        run = body.split("private async _runTweezer(", 1)[1].split("private _onTweezerKey(", 1)[0]
        assert run.index("this.api.runPluck(") < run.index("this.api.createPluckedBlaster(")

    def test_new_remotes_go_through_the_reorder_door(self):
        body = self._pluck()
        land = body.split("private async _landAtTop(", 1)[1]
        land = land.split("private async _pluckGhost(", 1)[0]
        assert 'this.api.reorderUnknownDevices("plucked", order)' in land

    def test_the_toolbar_count_is_translated(self):
        body = self._pluck()
        assert 'tp("pluckstore.n_remotes", count)' in body
        assert '"blasters"' not in body
