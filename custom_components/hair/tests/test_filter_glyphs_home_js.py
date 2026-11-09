"""Items 14 and 15 (owner, 2026-11-07): the filter glyphs beyond the
Sniffer's remote list.

Item 14: the homepage's Devices and Remotes headers each carry an IR
and an RF glyph, each an independent toggle over the cards below that
header, both on by default, remembered in this browser per section and
separate from the Sniffer's.
A card that uses both media shows while either is lit; a card with no
medium shows while either is lit. The glyphs are the Sniffer's own
look (``filter-glyph-styles.ts``).

Item 15: the Sniffer's IR and RF glyphs filter the receiver pills too,
except that a pill with its window open always shows.

The Sniffer's IR and RF glyphs are remembered in this browser too
(owner, 2026-11-08), under their own key; its hidden eye is not.

The rules run under node with the repo's TypeScript (skipped without
the toolchain); the source pins below run everywhere.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

COMPONENT = Path(__file__).parent.parent
FRONTEND = COMPONENT / "frontend"
SRC = FRONTEND / "src"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None

DRIVER = r"""
import {
    MEDIA_SHOW_DEFAULT, mediaShowKey, loadMediaShow, mediaShows,
    mediaShowsEverything, parseMediaShow, saveMediaShow,
} from "./media-filter.js";
import { pillShown } from "./ir-listen-state.js";

const both = { ir: true, rf: true };
const irOnly = { ir: true, rf: false };
const rfOnly = { ir: false, rf: true };
const none = { ir: false, rf: false };
const shows = (show) => ({
    ir: mediaShows(show, ["ir"]),
    rf: mediaShows(show, ["rf"]),
    mixed: mediaShows(show, ["ir", "rf"]),
    empty: mediaShows(show, []),
    missing: mediaShows(show, undefined),
});

class MemoryStorage {
    constructor() { this.data = new Map(); }
    getItem(k) { return this.data.has(k) ? this.data.get(k) : null; }
    setItem(k, v) { this.data.set(k, String(v)); }
}
const refusing = {
    getItem() { throw new Error("blocked"); },
    setItem() { throw new Error("blocked"); },
};
const mem = new MemoryStorage();
saveMediaShow(mem, "devices", { ir: false, rf: true });
const sniff = new MemoryStorage();
saveMediaShow(sniff, "sniffer", { ir: true, rf: false, hidden: true });

const row = (medium) => ({ medium, receiver_entity_id: "x" });
const pair = (show, on) => [
    pillShown(show, row("ir"), { on }),
    pillShown(show, row("rf"), { on }),
];

console.log(JSON.stringify({
    default: MEDIA_SHOW_DEFAULT,
    keys: [mediaShowKey("devices"), mediaShowKey("remotes")],
    snifferKey: mediaShowKey("sniffer"),
    snifferStored: sniff.getItem(mediaShowKey("sniffer")),
    snifferLoaded: loadMediaShow(sniff, "sniffer"),
    snifferLeavesHome: loadMediaShow(sniff, "devices"),
    homeLeavesSniffer: loadMediaShow(mem, "sniffer"),
    both: shows(both), irOnly: shows(irOnly), rfOnly: shows(rfOnly), none: shows(none),
    everything: [mediaShowsEverything(both), mediaShowsEverything(irOnly)],
    stored: mem.getItem(mediaShowKey("devices")),
    loaded: loadMediaShow(mem, "devices"),
    otherSection: loadMediaShow(mem, "remotes"),
    fresh: loadMediaShow(new MemoryStorage(), "devices"),
    refused: loadMediaShow(refusing, "devices"),
    noStorage: loadMediaShow(undefined, "remotes"),
    saveRefused: (() => { saveMediaShow(refusing, "remotes", both); return "no throw"; })(),
    garbage: [
        parseMediaShow("{"), parseMediaShow("[]"),
        parseMediaShow('{"ir":"yes","rf":false}'),
    ],
    pills: {
        irOffClosed: pair(rfOnly, false),
        rfOffClosed: pair(irOnly, false),
        bothOn: pair(both, false),
        offButOpen: pair(none, true),
        noMediumIsInfrared: [pillShown(rfOnly, row(undefined), { on: false })],
    },
}));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("filterglyphsjs")
    subprocess.run(
        [
            str(TSC),
            "src/media-filter.ts", "src/ir-listen-state.ts",
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


class TestTheHomepageRule:
    def test_both_on_by_default(self, run):
        assert run["default"] == {"ir": True, "rf": True}

    def test_each_glyph_filters_its_own_medium(self, run):
        assert run["both"] == dict.fromkeys(("ir", "rf", "mixed", "empty", "missing"), True)
        rest = {"mixed": True, "empty": True, "missing": True}
        assert run["irOnly"] == {"ir": True, "rf": False, **rest}
        assert run["rfOnly"] == {"ir": False, "rf": True, **rest}

    def test_a_card_with_no_medium_hides_only_when_both_are_off(self, run):
        assert run["none"] == dict.fromkeys(("ir", "rf", "mixed", "empty", "missing"), False)

    def test_reordering_needs_every_card(self, run):
        assert run["everything"] == [True, False]


class TestRememberedInThisBrowser:
    def test_a_choice_round_trips_per_section(self, run):
        assert run["keys"] == [
            "hair.homepage.media_show.devices",
            "hair.homepage.media_show.remotes",
        ]
        assert json.loads(run["stored"]) == {"ir": False, "rf": True}
        assert run["loaded"] == {"ir": False, "rf": True}
        assert run["otherSection"] == {"ir": True, "rf": True}

    def test_no_or_refusing_storage_is_the_default(self, run):
        for k in ("fresh", "refused", "noStorage"):
            assert run[k] == {"ir": True, "rf": True}, k
        assert run["saveRefused"] == "no throw"

    def test_unreadable_values_fall_back_per_key(self, run):
        assert run["garbage"] == [
            {"ir": True, "rf": True},
            {"ir": True, "rf": True},
            {"ir": True, "rf": False},
        ]


class TestTheSnifferRemembers:
    def test_its_own_key_and_only_ir_and_rf(self, run):
        assert run["snifferKey"] == "hair.sniffer.media_show"
        assert json.loads(run["snifferStored"]) == {"ir": True, "rf": False}
        assert run["snifferLoaded"] == {"ir": True, "rf": False}

    def test_separate_from_the_homepage(self, run):
        assert run["snifferLeavesHome"] == {"ir": True, "rf": True}
        assert run["homeLeavesSniffer"] == {"ir": True, "rf": True}

    def test_the_panel_loads_and_saves_it_and_the_eye_starts_off(self):
        flat = _flat("ir-signal-monitor.ts")
        start = flat.split("@state() private _show: SnifferShow = {", 1)[1].split("};", 1)[0]
        assert '...loadMediaShow(browserStorage(), "sniffer"),' in start
        assert start.strip().endswith("hidden: false,")
        toggle = flat.split("private _toggleShow(kind: keyof SnifferShow): void {", 1)[1]
        toggle = toggle.split('if (this._show.hidden) {', 1)[0]
        save = 'saveMediaShow(browserStorage(), "sniffer", this._show);'
        assert f'if (kind !== "hidden") {{ {save} return; }}' in toggle
        assert flat.count("saveMediaShow(") == 1


class TestTheReceiverPills:
    def test_a_medium_off_takes_its_pills_off(self, run):
        assert run["pills"]["irOffClosed"] == [False, True]
        assert run["pills"]["rfOffClosed"] == [True, False]
        assert run["pills"]["bothOn"] == [True, True]

    def test_an_open_window_always_shows(self, run):
        assert run["pills"]["offButOpen"] == [True, True]

    def test_a_pill_with_no_medium_is_infrared(self, run):
        assert run["pills"]["noMediumIsInfrared"] == [False]


def _flat(name: str) -> str:
    return " ".join((SRC / name).read_text(encoding="utf-8").split())


class TestTheWiring:
    def test_both_headers_carry_the_glyphs_and_both_grids_filter(self):
        flat = _flat("ir-device-list.ts")
        assert '${this._renderMediaGlyphs("devices")}' in flat
        assert '${this._renderMediaGlyphs("remotes")}' in flat
        assert "devices.filter((d) => mediaShows(this._mediaShow.devices, d.media))" in flat
        remotes = "this.triggerRemotes.filter((r) => mediaShows(this._mediaShow.remotes, r.media))"
        assert remotes in flat
        assert "disabled: !mediaShowsEverything(this._mediaShow.devices)," in flat
        assert "saveMediaShow(" in flat and "loadMediaShow(" in flat

    def test_no_hidden_glyph_on_the_homepage(self):
        head = "private _renderMediaGlyphs(section: HomeSection) {"
        body = _flat("ir-device-list.ts").split(head, 1)[1]
        body = body.split("private _renderProtoGlyphs(", 1)[0]
        assert "hidden" not in body

    def test_one_look_everywhere(self):
        for name in ("ir-device-list.ts", "ir-signal-monitor.ts"):
            assert 'import { filterGlyphStyles } from "./filter-glyph-styles.js";' in _flat(name)
            assert "filterGlyphStyles," in _flat(name)
        assert ".show-glyph.on {" not in _flat("ir-signal-monitor.ts")
        styles = _flat("filter-glyph-styles.ts")
        lit = styles.split(".show-glyph.on {", 1)[1].split("}", 1)[0]
        assert "color-mix(in srgb, var(--primary-color) 30%, transparent)" in lit

    def test_the_sniffer_hands_its_glyphs_to_the_pills(self):
        assert ".rows=${this._listenRows} .show=${this._show}" in _flat("ir-signal-monitor.ts")
        row = _flat("ir-listen-row.ts")
        live = "pillLive(states, row, this._items[row.receiver_entity_id] ?? null)"
        assert f"pillShown(this.show, row, {live})" in row
        assert "${rows.map(" in row
