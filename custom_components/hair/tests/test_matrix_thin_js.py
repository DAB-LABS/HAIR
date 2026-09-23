"""The thinning editor's rules, executed; and listening-mode marking.

The card imports ``lit`` and cannot load under node, so the rules it
renders from live in ``matrix-thin.ts`` (the draft) and
``matrix-lattice.ts`` (whether a heard state belongs to the lattice on
screen), both type-only, both transpiled with the repo's own TypeScript
and RUN here, the way the lattice chooser and the pluck helpers are.

What is driven, per plan section 9's frontend line: the default open
state; that a chip toggles without opening anything; the constraints
(one mode survives in the main lattice, one value on any axis kept,
off has no toggle at all); that the counts and the button's number
track the draft; that cancel discards; and the payload the door gets.
The structural claims (pencil absent in hear mode, the card wired to
these helpers, the chip classes' order) are source pins at the foot,
which run with no toolchain.

SKIPPED when the frontend toolchain is not installed, for the reason
the sibling modules give.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

FRONTEND = Path(__file__).parent.parent / "frontend"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"
SRC = FRONTEND / "src"

DRIVER = r"""
import { readFileSync } from "node:fs";
import {
    defaultOpen, depthOf, latticeKept, modeKept, removesAnything,
    startDraft, thinPayload, thinReceipt, toggleLattice, toggleMode,
    toggleOn, toggleValue, totals,
} from "./matrix-thin.js";
import { heardInLattice } from "./matrix-lattice.js";

// The Komeco's shape in miniature, sparse like the real thing: dry
// carries fan low only, fan_only has no temperature, auto is a single
// code. Plus an extras lattice, as the card payload spells it.
const cells = [];
for (const f of ["auto", "low", "high"]) {
    for (const s of ["off", "both"]) {
        for (const t of [20, 21, 22]) {
            cells.push({ m: "cool", f, s, t });
            cells.push({ m: "heat_cool", f, s, t });
        }
        cells.push({ m: "fan_only", f, s });
    }
}
for (const s of ["off", "both"]) {
    for (const t of [20, 21, 22]) cells.push({ m: "dry", f: "low", s, t });
}
cells.push({ m: "auto" });
const MC = {
    min_temp: 16, max_temp: 30, precision: 1, unit: "C",
    modes: ["cool", "dry", "fan_only", "auto", "heat_cool"],
    fan_modes: ["auto", "low", "high"],
    swing_modes: ["off", "both"],
    has_on: true,
    cells,
    lattices: [{
        axis: "preset", key: "boost",
        modes: ["cool"], fan_modes: ["high"], swing_modes: [],
        cells: [20, 21, 22].map((t) => ({ m: "cool", f: "high", t })),
    }],
};

const out = {};
const d = startDraft(MC);
out.fresh = {
    lattices: d.lattices.map((l) => ({
        axis: l.axis, key: l.key,
        modes: l.modes.map((m) => ({
            mode: m.mode, depth: depthOf(m), total: m.cells.length,
            carried: m.carried,
        })),
    })),
    totals: totals(d),
    removes: removesAnything(d),
    open: defaultOpen(d),
    hasOn: d.hasOn, keepOn: d.keepOn,
};

// A chip on a CLOSED line: dry is closed by default. Toggling it must
// not touch the open state -- the card keeps the two apart.
const open = defaultOpen(d);
const openBefore = JSON.stringify(open);
out.dryOff = toggleMode(d, 0, "dry");
out.openAfterChip = JSON.stringify(open) === openBefore;
out.afterDry = totals(d);

// Narrow heat_cool to one temperature: 16 clicks' worth, here two.
toggleValue(d, 0, "heat_cool", "temps", 20);
toggleValue(d, 0, "heat_cool", "temps", 21);
out.afterNarrow = totals(d);
out.heatCoolKept = modeKept(d.lattices[0],
    d.lattices[0].modes.find((m) => m.mode === "heat_cool"));
// The last value on an axis cannot go.
out.lastTemp = toggleValue(d, 0, "heat_cool", "temps", 22);
// A value the mode does not carry cannot be added.
out.strayFan = toggleValue(d, 0, "dry", "fans", "high");
// The whole boost lattice, in one click on its closed header.
out.boostOff = toggleLattice(d, 1);
out.mainOff = toggleLattice(d, 0);
out.afterBoost = totals(d);
out.boostKept = latticeKept(d.lattices[1]);
// On has a keep toggle.
out.onOff = toggleOn(d);
out.afterOn = totals(d);
out.payload = thinPayload(d);

// The last mode in the main lattice cannot go.
const lone = startDraft({ ...MC, lattices: undefined, has_on: false });
for (const m of ["cool", "dry", "fan_only", "auto"]) toggleMode(lone, 0, m);
out.lastMode = toggleMode(lone, 0, "heat_cool");
out.loneModes = lone.lattices[0].modes.filter((m) => m.on).map((m) => m.mode);
out.noOnToggle = toggleOn(lone);
out.lonePayloadKeepOn = thinPayload(lone).keep_on;

// Cancel discards: a fresh draft after a cancel is the file again.
const again = startDraft(MC);
out.afterCancel = { totals: totals(again), removes: removesAnything(again) };

// A draft with only On removed still removes something.
const onlyOn = startDraft(MC);
toggleOn(onlyOn);
out.onlyOn = { totals: totals(onlyOn), removes: removesAnything(onlyOn) };

// THE RECEIPT, composed against the shipped strings (owner bench
// 2026-09-22, item 2). The locale dir arrives as argv[2], so what is
// asserted below is what a person reads, not a key name.
const LOCALES = process.argv[2];
const dict = (lang) => JSON.parse(
    readFileSync(`${LOCALES}/${lang}.json`, "utf-8"));
const translator = (lang) => {
    const d = dict(lang);
    return (key, subs) => {
        let text = d[key] ?? key;
        for (const [k, v] of Object.entries(subs ?? {})) {
            text = text.split(`{${k}}`).join(String(v));
        }
        return text;
    };
};
const en = translator("en");
out.receipt = {
    written: thinReceipt({ from: 143, to: 77 }, { written: true }, en),
    not_adopted: thinReceipt({ from: 143, to: 77 },
        { written: false, reason: "not-adopted" }, en),
    source_missing: thinReceipt({ from: 143, to: 77 },
        { written: false, reason: "source_missing" }, en),
    unknown_reason: thinReceipt({ from: 143, to: 77 },
        { written: false, reason: "write_failed" }, en),
    no_counts: thinReceipt(null, { written: true }, en),
    no_wig: thinReceipt({ from: 143, to: 77 }, undefined, en),
    de: thinReceipt({ from: 143, to: 77 }, { written: true },
        translator("de")),
    ja: thinReceipt({ from: 143, to: 77 }, { written: true },
        translator("ja")),
};
out.summaryClause = {
    en: en("devices.matrix_trimmed", { from: "143", to: "77" }),
    de: translator("de")("devices.matrix_trimmed",
        { from: "143", to: "77" }),
};

// Listening-mode marking.
out.heard = {
    main_on_main: heardInLattice(
        { mode: "cool", axis: null, lattice: null }, {}),
    eco_on_main: heardInLattice(
        { mode: "cool", axis: "preset", lattice: "eco" }, {}),
    eco_on_eco: heardInLattice(
        { mode: "cool", axis: "preset", lattice: "eco" },
        { axis: "preset", lattice: "eco" }),
    main_on_eco: heardInLattice(
        { mode: "cool", axis: null, lattice: null },
        { axis: "preset", lattice: "eco" }),
    eco_on_boost: heardInLattice(
        { mode: "cool", axis: "preset", lattice: "eco" },
        { axis: "preset", lattice: "boost" }),
    legacy_on_main: heardInLattice({ mode: "cool" }, {}),
    legacy_on_eco: heardInLattice(
        { mode: "cool" }, { axis: "preset", lattice: "eco" }),
    power_on_main: heardInLattice(
        { power: "off", axis: null, lattice: null }, {}),
    nothing: heardInLattice(null, {}),
};
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if not TSC.exists() or shutil.which("node") is None:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("thinjs")
    subprocess.run(
        [
            str(TSC), "src/matrix-thin.ts", "src/matrix-lattice.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "driver.mjs").write_text(DRIVER, encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "driver.mjs"), str(SRC / "locales")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


class TestTheFreshDraft:
    def test_everything_is_kept(self, run):
        assert run["fresh"]["totals"]["removed"] == 0
        assert run["fresh"]["totals"]["kept"] == run["fresh"]["totals"]["total"]
        assert run["fresh"]["removes"] is False
        assert run["fresh"]["keepOn"] is True

    def test_counts_are_cells_not_products(self, run):
        """dry carries fan low only: 6 cells, not 3 fans x 2 x 3."""
        main = run["fresh"]["lattices"][0]
        by = {m["mode"]: m for m in main["modes"]}
        assert by["dry"]["total"] == 6
        assert by["dry"]["carried"]["fans"] == ["low"]
        assert run["fresh"]["totals"]["total"] == 18 * 2 + 6 + 6 + 1 + 3

    def test_depth_tags(self, run):
        main = run["fresh"]["lattices"][0]
        depth = {m["mode"]: m["depth"] for m in main["modes"]}
        assert depth == {"cool": 3, "dry": 3, "fan_only": 2, "auto": 0,
                         "heat_cool": 3}
        boost = run["fresh"]["lattices"][1]
        assert boost["modes"][0]["depth"] == 2  # fan and temp, no swing

    def test_main_first_then_extras_in_wig_order(self, run):
        keys = [(g["axis"], g["key"]) for g in run["fresh"]["lattices"]]
        assert keys == [(None, None), ("preset", "boost")]

    def test_mode_order_follows_the_declared_vocabulary(self, run):
        main = run["fresh"]["lattices"][0]
        assert [m["mode"] for m in main["modes"]] == [
            "cool", "dry", "fan_only", "auto", "heat_cool",
        ]


class TestTheDefaultOpenState:
    def test_main_open_every_mode_closed_extras_closed(self, run):
        """RULED: Main controls open, every mode inside it collapsed,
        presets closed."""
        open_ = run["fresh"]["open"]
        assert open_["g:0"] is True
        assert open_["g:1"] is False
        modes = {k: v for k, v in open_.items() if k.startswith("m:")}
        assert modes and not any(modes.values())


class TestChipsAndConstraints:
    def test_a_chip_on_a_closed_line_toggles_without_opening(self, run):
        assert run["dryOff"] is True
        assert run["openAfterChip"] is True
        assert run["afterDry"]["removed"] == 6
        assert run["afterDry"]["modes"] == ["dry"]

    def test_narrowing_counts_cells(self, run):
        assert run["heatCoolKept"] == 6  # 3 fans x 2 swings x one temp
        assert run["afterNarrow"]["removed"] == 6 + 12
        assert run["afterNarrow"]["modes"] == ["dry", "heat_cool"]

    def test_the_last_value_on_an_axis_cannot_go(self, run):
        assert run["lastTemp"] is False

    def test_a_value_the_mode_does_not_carry_cannot_be_added(self, run):
        assert run["strayFan"] is False

    def test_a_whole_lattice_in_one_click_and_main_has_none(self, run):
        assert run["boostOff"] is True
        assert run["mainOff"] is False
        assert run["boostKept"] == 0
        assert run["afterBoost"]["lattices"] == ["(boost)"]
        assert run["afterBoost"]["removed"] == 6 + 12 + 3

    def test_the_last_mode_in_the_main_lattice_cannot_go(self, run):
        assert run["lastMode"] is False
        assert run["loneModes"] == ["heat_cool"]

    def test_on_has_a_keep_toggle_and_off_has_none(self, run):
        assert run["onOff"] is True
        assert run["afterOn"]["onRemoved"] is True
        assert run["noOnToggle"] is False  # a matrix with no On code
        assert run["lonePayloadKeepOn"] is True


class TestTheCountsTrackTheDraft:
    def test_kept_plus_removed_is_the_whole(self, run):
        t = run["afterOn"]
        assert t["kept"] + t["removed"] == t["total"]

    def test_only_on_removed_still_removes_something(self, run):
        assert run["onlyOn"]["removes"] is True
        assert run["onlyOn"]["totals"]["removed"] == 0

    def test_cancel_discards(self, run):
        assert run["afterCancel"]["removes"] is False
        assert run["afterCancel"]["totals"]["removed"] == 0


class TestThePayload:
    def test_the_whole_shape_with_removed_things_absent(self, run):
        payload = run["payload"]
        assert payload["keep_on"] is False
        assert [(g["axis"], g["key"]) for g in payload["lattices"]] == [
            (None, None),
        ]
        modes = {m["mode"]: m for m in payload["lattices"][0]["modes"]}
        assert "dry" not in modes
        assert modes["heat_cool"] == {
            "mode": "heat_cool", "fans": ["auto", "low", "high"],
            "swings": ["off", "both"], "temps": [22],
        }
        assert modes["fan_only"]["temps"] is None
        assert modes["auto"] == {"mode": "auto", "fans": None,
                                 "swings": None, "temps": None}


class TestListeningModeMarking:
    """Folded-in item 1: a tile is marked only when the heard state's
    pair matches the selected lattice, both null for the main one."""

    def test_the_main_lattice_marks_a_main_press(self, run):
        assert run["heard"]["main_on_main"] is True

    def test_an_eco_press_does_not_light_a_main_tile(self, run):
        assert run["heard"]["eco_on_main"] is False

    def test_an_eco_press_marks_the_eco_lattice(self, run):
        assert run["heard"]["eco_on_eco"] is True

    def test_a_main_press_does_not_light_an_eco_tile(self, run):
        assert run["heard"]["main_on_eco"] is False
        assert run["heard"]["eco_on_boost"] is False

    def test_a_row_heard_before_extras_existed_is_the_main_lattices(self, run):
        assert run["heard"]["legacy_on_main"] is True
        assert run["heard"]["legacy_on_eco"] is False

    def test_power_and_nothing(self, run):
        assert run["heard"]["power_on_main"] is True
        assert run["heard"]["nothing"] is False


# ---------------------------------------------------------------------------
# Source pins: no toolchain needed
# ---------------------------------------------------------------------------


def _card() -> str:
    return (SRC / "ir-matrix-card.ts").read_text(encoding="utf-8")


def _method(text: str, start: str) -> str:
    body = text[text.index(start):]
    return body[: body.index("\n    }\n") + 6]


class TestTheCardSource:
    def test_the_pencil_is_send_mode_only_and_needs_a_saver(self):
        card = _card()
        assert "const canThin = !hear && !!mc && this.thinSaver !== null;" in card
        assert "${canThin" in card

    def test_the_pencil_is_the_house_edit_button(self):
        card = _card()
        assert "renderEditBtn(" in card
        assert "editButtonStyles" in card
        # Nothing new drawn: no inline pencil path in the card.
        assert "m537.43" not in card

    def test_the_remote_page_passes_no_saver(self):
        remote = (SRC / "ir-device-list.ts").read_text(encoding="utf-8")
        block = remote[remote.index('mode="hear"') - 400:]
        block = block[: block.index("</ir-matrix-card>")]
        assert "thinSaver" not in block
        device = (SRC / "ir-device-detail.ts").read_text(encoding="utf-8")
        assert ".thinSaver=${this._matrixThin}" in device

    def test_the_chevron_is_the_house_one_on_the_right(self):
        card = _card()
        css = card[card.index("static styles"):]
        rule = css[css.index("            .expand-btn {"):]
        rule = rule[: rule.index("}")]
        for prop in ("--hair-chevron-size: 32px",
                     "--hair-chevron-glyph: 22px",
                     "--hair-chevron-weight: 2.5",
                     "margin-left: auto"):
            assert prop in rule
        assert '<path d="M6 9l6 6 6-6"></path>' in card

    def test_keep_and_drop_are_declared_after_chip_and_tile(self):
        """T3 shipped the grid cell's own background beating .keep."""
        css = _card()[_card().index("static styles"):]
        keep = css.index(".mx-chip.keep,")
        drop = css.index(".mx-chip.drop,")
        for base in (".mx-chip {", ".mx-chip.on {", ".mx-tile {",
                     ".mx-tile.sel {"):
            assert css.index(base) < keep, base
            assert css.index(base) < drop, base
        assert ".mx-tile.keep" in css[keep:keep + 40]
        assert ".mx-tile.drop" in css[drop:drop + 40]

    def test_off_is_locked_with_a_tooltip_and_no_toggle(self):
        editor = _method(_card(), "private _renderEditor(")
        off = editor[editor.index('class="mx-chip keep locked"'):]
        off = off[: off.index("</button>")]
        assert 't("devices.thin_off_tip")' in off
        assert "this._offClicked()" in off
        assert "toggle" not in off

    def test_no_bulk_shortcuts(self):
        card = _card().lower()
        for word in ("keep all", "keep_all", "keepall", "only("):
            assert word not in card

    def test_cancel_and_the_pencil_both_discard_the_draft(self):
        card = _card()
        cancel = _method(card, "private _cancelEdit(")
        assert "this._draft = null;" in cancel
        pencil = _method(card, "private _togglePencil(")
        assert "this._cancelEdit();" in pencil
        assert "defaultOpen(this._draft)" in pencil

    def test_the_count_line_is_empty_and_the_button_off_until_a_change(self):
        editor = _method(_card(), "private _renderEditor(")
        assert "const nothingYet = !removesAnything(d);" in editor
        assert "${nothingYet ? nothing : this._countLine(sums)}" in editor
        assert "?disabled=${nothingYet || this._thinBusy || this.busy}" in editor
        assert 'tp("devices.thin_remove_btn", sums.removed)' in editor

    def test_a_chip_click_never_opens_a_line(self):
        """Opening is the chevron's job alone: no chip handler touches
        ``_open``."""
        card = _card()
        for start in ("private _renderGroup(", "private _renderModeLine("):
            body = _method(card, start)
            for handler in re.findall(r"@click=\$\{\(\) =>\s*this\._change\([^`]*?\)\}",
                                      body, flags=re.S):
                assert "_flip" not in handler and "_open" not in handler

    def test_edit_mode_swaps_the_browse_rows_and_the_actions(self):
        card = _card()
        render = card[card.index("    render() {"):]
        render = render[: render.index("    private _renderBrowse(")]
        assert "${editing\n                    ? this._renderEditor(mc!)" in render
        assert 'class="matrix-card ${editing ? "editing" : ""}"' in render

    def test_the_heard_state_rings_only_its_own_lattice(self):
        card = _card()
        assert "heardHere ? h!.mode : null" in card
        assert "heardHere ? h!.fan : null" in card
        assert "heardHere ? h!.swing : null" in card
        branch = _method(card, "private _onHeardBranch(")
        assert "if (!this._heardHere()) return false;" in branch
        seed = _method(card, "private _seedBranch(")
        assert "this._heardHere()" in seed

    def test_the_card_keeps_no_receipt_of_its_own(self):
        """Owner bench 2026-09-22, item 2: round one held the line in
        this element's state and it never reached the bench. The page
        says what happened now."""
        card = _card()
        assert "_thinNotice" not in card
        assert "thin-notice" not in card
        assert "thin-marker" not in card
        assert "thin_marker" not in card
        save = _method(card, "private async _saveThin(")
        assert "thinSaver(thinPayload(draft))" in save
        assert "tangles.updated" not in save

    def test_the_page_flashes_the_receipt(self):
        detail = (SRC / "ir-device-detail.ts").read_text(encoding="utf-8")
        body = _method(detail, "private _matrixThin = async (")
        assert (
            "this._flash(\n            thinReceipt(result.device?.matrix"
            "?.trimmed, result.wig, t),\n        );"
        ) in body
        assert 't("devices.thin_failed")' in body
        # A refusal and a lost answer must not read alike: the bench run
        # wrote the wig and never answered, so the second case points at
        # a reload instead of claiming nothing was saved.
        assert "failed?.code" in body
        assert 't("devices.thin_no_answer")' in body
        assert "throw err;" in body

    def test_the_summary_line_carries_the_trim(self):
        card = _card()
        assert "${summaryText}${trimmedText}" in card
        assert 't("devices.matrix_trimmed"' in card

    def test_every_control_is_inert_while_a_save_is_in_flight(self):
        """Item 3: the draft cannot change under a write already on its
        way, and the button says what it is doing."""
        card = _card()
        editor = _method(card, "private _renderEditor(")
        assert 't("common.saving")' in editor
        assert editor.count("?disabled=${this._thinBusy}") >= 2
        for start in ("private _renderGroup(", "private _renderModeLine(",
                      "private _renderAxis(", "private _renderTemps(",
                      "private _chevron("):
            body = _method(card, start)
            assert "this._thinBusy" in body, start
        save = _method(card, "private async _saveThin(")
        assert "if (this._thinBusy) return;" in save


class TestTheSaveDialogPointer:
    def test_the_exclusion_picker_points_at_thinning(self):
        dialog = (SRC / "ir-save-perfect-dialog.ts").read_text(encoding="utf-8")
        body = _method(dialog, "private _renderReasons(")
        assert 't("wigs.save.reason_thin")' in body

    def test_every_locale_carries_the_pointer_and_the_editor_keys(self):
        locales = sorted((SRC / "locales").glob("*.json"))
        assert len(locales) == 10
        for path in locales:
            data = json.loads(path.read_text(encoding="utf-8"))
            for key in ("wigs.save.reason_thin", "devices.matrix_trimmed",
                        "devices.thin_receipt", "devices.thin_main",
                        "devices.thin_banner_title", "devices.thin_cost_3",
                        "devices.thin_no_answer",
                        "devices.thin_remove_btn.other"):
                assert data.get(key, "").strip(), f"{path.name}:{key}"
            assert "devices.thin_marker" not in data, path.name

    def test_nothing_a_person_reads_says_thinned(self):
        """Owner ruling 2026-09-22: the word is "trimmed". The internal
        names (hair_thinning, matrix-thin, the door) are untouched."""
        en = json.loads(
            (SRC / "locales" / "en.json").read_text(encoding="utf-8"))
        offenders = [
            key for key, value in en.items()
            if isinstance(value, str) and "thinn" in value.lower()
        ]
        assert offenders == []


class TestTheReceipt:
    """Item 2's line, composed against the shipped strings."""

    def test_a_written_wig(self, run):
        assert run["receipt"]["written"] == (
            "Trimmed from 143 to 77. Your wig has been updated."
        )

    def test_the_write_through_reasons(self, run):
        receipt = run["receipt"]
        assert receipt["not_adopted"].startswith("Trimmed from 143 to 77. ")
        assert "no wig to update" in receipt["not_adopted"]
        assert "no longer in the closet" in receipt["source_missing"]
        assert "could not be updated" in receipt["unknown_reason"]

    def test_a_payload_with_no_counts_says_only_what_it_knows(self, run):
        assert run["receipt"]["no_counts"] == "Your wig has been updated."

    def test_no_write_through_answer_is_not_a_success(self, run):
        assert "could not be updated" in run["receipt"]["no_wig"]

    def test_it_is_the_locales_own_words(self, run):
        assert run["receipt"]["de"] == (
            "Von 143 auf 77 gekürzt. Ihre Perücke wurde aktualisiert."
        )
        assert run["receipt"]["ja"].startswith("143件から77件に削減しました。")

    def test_the_summary_clause_carries_the_house_separator(self, run):
        clause = run["summaryClause"]
        assert clause["en"] == " · trimmed from 143 to 77"
        assert clause["de"].startswith(" · ")
        assert "143" in clause["de"] and "77" in clause["de"]
