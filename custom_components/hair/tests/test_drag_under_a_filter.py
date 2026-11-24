"""Cards drag while a filter is on.

The rule, HAIR's own since the Sniffer's store learned it for hidden and
low-hit remotes (``signal_store.reorder_devices``): the cards that are
showing move among the slots they hold, and a card a filter hides keeps
its slot. It now applies everywhere a filter used to switch drag off:

- the Sniffer, under its IR glyph, its RF glyph and the hidden eye;
- the Devices tab's Devices grid and Remotes grid, under their IR and RF
  glyphs.

The panel works the whole order out (``reorder-slots.ts``) and sends it,
hidden cards in their slots. So the Devices and Remotes doors keep
refusing anything but exactly the current set, and the Sniffer's door,
which already takes the list the Sniffer holds, gets the same answer it
would have worked out itself.

Clipper and Plucker have no filter. Every grid keeps its handle: the
Sniffer, Clipper and Plucker drag by the glyph or grip only.

The rules run under node with the repo's TypeScript (skipped without the
toolchain); the stores and the source pins run everywhere.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from custom_components.hair.models import IRDevice, TriggerRemote
from custom_components.hair.signal_store import SignalStore
from custom_components.hair.storage import HAIRStore
from custom_components.hair.tests.test_signal_store import (
    _make_hass,
    _ordered_device,
)
from custom_components.hair.tests.test_storage import _FakeStore

COMPONENT = Path(__file__).parent.parent
FRONTEND = COMPONENT / "frontend"
SRC = FRONTEND / "src"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None

# The whole order is A..F. Under the filter B and E are hidden; the
# drag moves F (the last card showing) to the top of what shows.
ORDER = ["A", "B", "C", "D", "E", "F"]
HIDDEN = {"B", "E"}
DRAG_SHOWN = ["F", "A", "C", "D"]
EXPECTED = ["F", "B", "A", "C", "E", "D"]

DRIVER = r"""
import { movedWithin, reorderInSlots } from "./reorder-slots.js";
import { mediaShows } from "./media-filter.js";
import { snifferShows } from "./sniffer-filter.js";

const id = (x) => x.id;
const ids = (xs) => (xs ? xs.map(id) : null);
const make = (spec) => spec.map(([id, extra]) => ({ id, ...extra }));

// The rule itself.
const plain = make([["A"], ["B"], ["C"]]);
const rule = {
    no_filter: ids(reorderInSlots(plain, [plain[2], plain[0], plain[1]], id)),
    hidden_keep_slots: ids(reorderInSlots(
        make(["A", "B", "C", "D", "E", "F"].map((k) => [k])),
        make(["F", "A", "C", "D"].map((k) => [k])),
        id,
    )),
    duplicate: ids(reorderInSlots(plain, [plain[0], plain[0]], id)),
    unknown: ids(reorderInSlots(plain, [{ id: "Z" }], id)),
    nothing_shown: ids(reorderInSlots(plain, [], id)),
};
const moves = {
    up: movedWithin(["a", "b", "c"], 2, 0),
    down: movedWithin(["a", "b", "c"], 0, 2),
    same: movedWithin(["a", "b", "c"], 1, 1),
    none: movedWithin(["a", "b", "c"], undefined, 1),
    out_of_range: movedWithin(["a", "b", "c"], 3, 0),
};

// Each grid as the panel runs it: its own filter, then a drag of the
// last card showing to the top.
function dragLastToTop(all, shows) {
    const shown = all.filter(shows);
    const moved = movedWithin(shown, shown.length - 1, 0);
    return moved ? ids(reorderInSlots(all, moved, id)) : null;
}
const media = (m) => ({ media: [m] });
const cards = make([
    ["A", media("ir")], ["B", media("rf")], ["C", media("ir")],
    ["D", media("ir")], ["E", media("rf")], ["F", media("ir")],
]);
const irOnly = { ir: true, rf: false };
const rfOnly = { ir: false, rf: true };
const grids = {
    devices_ir_only: dragLastToTop(cards, (d) => mediaShows(irOnly, d.media)),
    remotes_ir_only: dragLastToTop(cards, (r) => mediaShows(irOnly, r.media)),
    devices_rf_only: dragLastToTop(cards, (d) => mediaShows(rfOnly, d.media)),
};
const sniffed = make([
    ["A", { medium: "ir", dismissed: false }], ["B", { medium: "rf", dismissed: false }],
    ["C", { medium: "ir", dismissed: false }], ["D", { medium: "ir", dismissed: false }],
    ["E", { medium: "rf", dismissed: false }], ["F", { medium: "ir", dismissed: false }],
]);
const sniff = (show) => (d) => snifferShows(show, d);
grids.sniffer_rf_off = dragLastToTop(sniffed, sniff({ ir: true, rf: false, hidden: false }));
// The eye on: the list holds the hidden remotes and shows them, so a
// hidden remote drags too.
const withHidden = make([
    ["A", { medium: "ir", dismissed: false }], ["B", { medium: "ir", dismissed: true }],
    ["C", { medium: "rf", dismissed: false }],
]);
grids.sniffer_eye_on = dragLastToTop(withHidden, sniff({ ir: true, rf: true, hidden: true }));
grids.sniffer_eye_on_ir_off = dragLastToTop(
    withHidden, sniff({ ir: false, rf: true, hidden: true }),
);
console.log(JSON.stringify({ rule, moves, grids }));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("dragfilterjs")
    subprocess.run(
        [
            str(TSC),
            "src/reorder-slots.ts", "src/media-filter.ts", "src/sniffer-filter.ts",
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


# ---------------------------------------------------------------------------
# The rule (node)
# ---------------------------------------------------------------------------


class TestTheRule:
    def test_with_no_filter_it_is_a_plain_reorder(self, run):
        assert run["rule"]["no_filter"] == ["C", "A", "B"]

    def test_hidden_cards_keep_their_slots(self, run):
        assert run["rule"]["hidden_keep_slots"] == EXPECTED

    @pytest.mark.parametrize("case", ["duplicate", "unknown"])
    def test_a_stale_grid_is_ignored(self, run, case):
        assert run["rule"][case] is None

    def test_nothing_shown_changes_nothing(self, run):
        assert run["rule"]["nothing_shown"] == ["A", "B", "C"]

    def test_the_move_among_the_cards_showing(self, run):
        assert run["moves"] == {
            "up": ["c", "a", "b"],
            "down": ["b", "c", "a"],
            "same": None,
            "none": None,
            "out_of_range": None,
        }


class TestEachGrid:
    """A filtered drag keeps the hidden cards in their slots, in each
    grid, with that grid's own filter rule."""

    def test_the_devices_grid_under_ir_only(self, run):
        assert run["grids"]["devices_ir_only"] == EXPECTED

    def test_the_remotes_grid_under_ir_only(self, run):
        assert run["grids"]["remotes_ir_only"] == EXPECTED

    def test_the_devices_grid_under_rf_only(self, run):
        # Radio cards B and E show; E goes to the top of them.
        assert run["grids"]["devices_rf_only"] == ["A", "E", "C", "D", "B", "F"]

    def test_the_sniffer_with_rf_off(self, run):
        assert run["grids"]["sniffer_rf_off"] == EXPECTED

    def test_the_sniffer_with_the_eye_on(self, run):
        assert run["grids"]["sniffer_eye_on"] == ["C", "A", "B"]

    def test_the_sniffer_with_the_eye_on_and_ir_off(self, run):
        # Only C shows: nothing to move, the order stands.
        assert run["grids"]["sniffer_eye_on_ir_off"] is None


# ---------------------------------------------------------------------------
# The doors' stores take what the panel sends
# ---------------------------------------------------------------------------


class TestTheStores:
    def test_the_sniffers_store_agrees_with_the_panel(self):
        """The Sniffer's store, given only the remotes showing, puts them
        where the panel did; given the panel's whole order, the same."""
        for submitted in (DRAG_SHOWN, EXPECTED):
            store = SignalStore(_make_hass())
            devices = [_ordered_device(k) for k in ORDER]
            for device in devices:
                store.add_device(device)
            for index, device in enumerate(devices):
                device.order = index
            store.reorder_devices("sniffed", submitted)
            got = [d.id for d in sorted(devices, key=lambda d: d.order)]
            assert got == EXPECTED, submitted

    @pytest.mark.asyncio
    async def test_the_devices_store_takes_the_whole_order(self, fake_hass):
        with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
            store = HAIRStore(fake_hass)
            await store.async_load()
            for k in ORDER:
                store.add_device(IRDevice(id=k, name=k))
            store.reorder_devices(EXPECTED)
            assert [d.id for d in store.get_all_devices()] == EXPECTED
            # Still exactly the current set: the shown cards alone are
            # refused, so a stale panel is still caught.
            with pytest.raises(ValueError, match="missing"):
                store.reorder_devices(DRAG_SHOWN)

    @pytest.mark.asyncio
    async def test_the_remotes_store_takes_the_whole_order(self, fake_hass):
        with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
            store = HAIRStore(fake_hass)
            await store.async_load()
            for k in ORDER:
                store.add_trigger_remote(TriggerRemote(id=k, name=k))
            store.reorder_trigger_remotes(EXPECTED)
            assert [r.id for r in store.get_all_trigger_remotes()] == EXPECTED
            with pytest.raises(ValueError, match="missing"):
                store.reorder_trigger_remotes(DRAG_SHOWN)


# ---------------------------------------------------------------------------
# The panel (source pins)
# ---------------------------------------------------------------------------


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _method(text: str, name: str) -> str:
    body = text[text.index(name):]
    return body[: body.index("\n    }\n")]


class TestThePanel:
    def test_no_filter_switches_drag_off(self):
        for name in ("ir-device-list.ts", "ir-signal-monitor.ts", "ir-clips.ts", "ir-pluck.ts"):
            text = _read(name)
            assert 'option("disabled"' not in text, name
            assert "ShowsEverything" not in text, name
        for name in ("media-filter.ts", "sniffer-filter.ts"):
            assert "ShowsEverything" not in _read(name), name

    def test_the_devices_grid_reslots(self):
        attach = _method(_read("ir-device-list.ts"), "private _attachDevicesSortable")
        assert "disabled" not in attach
        assert "const reordered = reorderInSlots(base, shown, (d) => d.id);" in attach
        assert "this._scheduleDevicesSave(reordered.map((d) => d.id));" in attach

    def test_the_remotes_grid_reslots(self):
        attach = _method(_read("ir-device-list.ts"), "private _attachRemotesSortable")
        assert "disabled" not in attach
        assert "const reordered = reorderInSlots(base, shown, (r) => r.id);" in attach
        assert "this._scheduleRemotesSave(reordered.map((r) => r.id));" in attach

    def test_the_sniffer_moves_among_the_remotes_showing(self):
        attach = _method(_read("ir-signal-monitor.ts"), "private _attachRemotesSortable")
        assert "disabled" not in attach
        assert (
            "const shown = movedWithin(this._visibleDevices(), e.oldIndex, e.newIndex);"
        ) in attach
        assert "const devices = reorderInSlots(this._devices, shown, (d) => d.id);" in attach
        assert "this._scheduleRemotesSave(devices.map((d) => d.id));" in attach

    def test_the_sniffer_clipper_and_plucker_keep_their_handles(self):
        assert 'handle: ".remote-handle",' in _read("ir-signal-monitor.ts")
        for name in ("ir-clips.ts", "ir-pluck.ts"):
            assert 'handle: ".remote-grip",' in _read(name), name

    def test_the_grids_render_what_shows(self):
        """The drop reads the cards on screen, which are the filtered
        ones, so the shown set is the filter's."""
        sniffer = _read("ir-signal-monitor.ts")
        assert "return this._devices.filter((d) => snifferShows(this._show, d));" in sniffer
        listing = " ".join(_read("ir-device-list.ts").split())
        assert "devices.filter((d) => mediaShows(this._mediaShow.devices, d.media))" in listing
        assert (
            "(this._localRemotes ?? this.triggerRemotes)"
            ".filter((r) => mediaShows(this._mediaShow.remotes, r.media))"
        ) in listing
