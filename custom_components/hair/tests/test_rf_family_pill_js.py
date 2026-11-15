"""A radio family in the protocol pill (decoder round 2, owner rulings of
2026-11-14 19:06 PT on the family pill mock).

1. Fit A: the pill reads "PT2262/1527" for "PT2262 or EV1527"; every
   other shown label fits as sent.
2. Read-only, and the tooltip is the label and the fields only.
3. The radio code editor gets the infrared editor's pill row.
4. A radio row with no family gets no pill, and "RF_RAW" never shows.
5. The Clipper's radio rows get the pill too.

The label rules run under node with the repo's TypeScript (skipped
without the toolchain); the source pins run everywhere.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

COMPONENT = Path(__file__).parent.parent
FRONTEND = COMPONENT / "frontend"
SRC = FRONTEND / "src"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None


def _f(name: str, value: str) -> dict:
    return {"name": name, "value": value}


# Every label a shown family can give, as rf_family.py sends it
# (shaq-2026-11-15-answers-gertrude-pills.md, answer 3).
SHOWN = {
    "ev1527": {
        "label": "EV1527", "family": "ev1527", "certainty": "decoded", "unit_us": 400,
        "fields": [_f("address", "950E4"), _f("data", "9")], "aliases": [],
    },
    "pt2262_ev1527": {
        "label": "PT2262 or EV1527", "family": "pt2262_ev1527", "certainty": "ambiguous",
        "unit_us": 350,
        "fields": [_f("tri-state", "0F10FF001001"), _f("code", "1C50C3")],
        "aliases": ["SC2262", "HS1527"],
    },
    "ht12e": {
        "label": "HT12E", "family": "ht12e", "certainty": "decoded", "unit_us": 330,
        "fields": [_f("address", "10110010"), _f("data", "0110"), _f("code", "B26")],
        "aliases": [],
    },
    "ht12e_ambiguous": {
        # As the server sends it: a hidden family (CAME) also fits, so the
        # shape's shared fields, not HT12E's split (ruling 2026-11-15).
        "label": "HT12E", "family": "ht12e", "certainty": "ambiguous", "unit_us": 320,
        "fields": [_f("bits", "101100100110"), _f("code", "B26")],
        "aliases": [],
    },
    "ht6p20": {
        "label": "HT6P20", "family": "ht6p20", "certainty": "decoded", "unit_us": 450,
        "fields": [_f("code", "A1B2C3")], "aliases": [],
    },
    "keeloq": {
        "label": "KeeLoq", "family": "keeloq", "certainty": "decoded", "unit_us": 400,
        "fields": [_f("serial", "1A2B3C4"), _f("buttons", "S0+S2"), _f("low battery", "no")],
        "aliases": ["HCS200", "HCS300", "HCS301"],
    },
}
UNSEEN = {
    "label": "FOO1 or BAR22", "family": "foo1_bar22", "certainty": "ambiguous",
    "fields": [_f("code", "AB")],
}

DRIVER = r"""
import {
    FAMILY_SHORT, familyEditorText, familyFieldsText, familyShort, familyTitle,
} from "./rf-family-label.js";

const SHOWN = __SHOWN__;
const UNSEEN = __UNSEEN__;
const out = { shown: {}, none: {} };
for (const [key, fam] of Object.entries(SHOWN)) {
    out.shown[key] = {
        short: familyShort(fam),
        title: familyTitle(fam),
        fields: familyFieldsText(fam),
        editor: familyEditorText(fam),
    };
}
out.unseen = { short: familyShort(UNSEEN), title: familyTitle(UNSEEN) };
out.none = {
    short: [familyShort(null), familyShort(undefined)],
    title: familyTitle(null),
    editor: familyEditorText(null),
    fields: familyFieldsText(undefined),
};
out.table = FAMILY_SHORT;
console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("rffamilypill")
    subprocess.run(
        [
            str(TSC), "src/rf-family-label.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler", "--skipLibCheck",
            "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    driver = DRIVER.replace("__SHOWN__", json.dumps(SHOWN)).replace(
        "__UNSEEN__", json.dumps(UNSEEN)
    )
    (out / "driver.mjs").write_text(driver, encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "driver.mjs")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


class TestPillText:
    def test_fit_a_for_the_ambiguous_pair(self, run):
        assert run["shown"]["pt2262_ev1527"]["short"] == "PT2262/1527"

    @pytest.mark.parametrize(
        ("key", "text"),
        [
            ("ev1527", "EV1527"),
            ("ht12e", "HT12E"),
            ("ht12e_ambiguous", "HT12E"),
            ("ht6p20", "HT6P20"),
            ("keeloq", "KeeLoq"),
        ],
    )
    def test_every_other_shown_label_as_sent(self, run, key, text):
        assert run["shown"][key]["short"] == text

    def test_every_shown_label_fits_the_column(self, run):
        # SAMSUNG32, the widest infrared label in the 88px column, is
        # nine characters; "PT2262/1527" measured as wide (fit A).
        for key, view in run["shown"].items():
            assert len(view["short"]) <= len("PT2262/1527"), key

    def test_the_table_holds_only_what_needs_shortening(self, run):
        assert run["table"] == {"pt2262_ev1527": "PT2262/1527"}

    def test_an_unseen_label_is_shortened_by_the_same_rule(self, run):
        assert run["unseen"]["short"] == "FOO1/BAR22"
        assert run["unseen"]["title"] == "FOO1 or BAR22 · code AB"

    def test_no_family_no_pill(self, run):
        assert run["none"]["short"] == [None, None]
        assert run["none"]["title"] == ""
        assert run["none"]["editor"] == ""
        assert run["none"]["fields"] == ""


class TestTooltip:
    def test_label_and_fields_only(self, run):
        assert run["shown"]["ev1527"]["title"] == "EV1527 · address 950E4 · data 9"
        assert run["shown"]["pt2262_ev1527"]["title"] == (
            "PT2262 or EV1527 · tri-state 0F10FF001001 · code 1C50C3"
        )
        assert run["shown"]["keeloq"]["title"] == (
            "KeeLoq · serial 1A2B3C4 · buttons S0+S2 · low battery no"
        )

    def test_the_clone_names_stay_out(self, run):
        for key in ("pt2262_ev1527", "keeloq"):
            view = run["shown"][key]
            for alias in SHOWN[key]["aliases"]:
                assert alias not in view["title"]
                assert alias not in view["editor"]

    def test_certainty_is_not_spelled_out(self, run):
        # An ambiguous HT12E has the same label as a decoded one: the
        # label never names a hidden family, and no word is added to
        # translate. Only its fields differ (the shared bits and code).
        assert run["shown"]["ht12e_ambiguous"]["short"] == run["shown"]["ht12e"]["short"]
        assert run["shown"]["ht12e_ambiguous"]["title"] == (
            "HT12E · bits 101100100110 · code B26"
        )


class TestEditorLine:
    def test_the_fields_after_the_pill(self, run):
        assert run["shown"]["ev1527"]["editor"] == "address 950E4 data 9"
        assert run["shown"]["ht6p20"]["editor"] == "code A1B2C3"

    def test_a_shortened_pill_gets_the_full_label_first(self, run):
        assert run["shown"]["pt2262_ev1527"]["editor"] == (
            "PT2262 or EV1527 · tri-state 0F10FF001001 code 1C50C3"
        )

    def test_the_fields_match_the_drawers_line(self, run):
        assert run["shown"]["keeloq"]["fields"] == "serial 1A2B3C4 buttons S0+S2 low battery no"


# --- Source pins: where the pill goes ------------------------------------


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


class TestThePill:
    def test_the_radio_pill_is_the_protocol_pill(self):
        chip = _read("ir-protocol-chip.ts")
        assert "public family: RfFamily | null | undefined = undefined" in chip
        assert "if (this.family !== undefined) return this._renderFamily();" in chip

    def test_read_only_with_the_tooltip_on_a_span(self):
        chip = _read("ir-protocol-chip.ts")
        body = chip[chip.index("private _renderFamily()"):chip.index("static styles")]
        assert "<span" in body and "<button" not in body
        assert "toggle-bypass" not in body
        assert "title=${title}" in body
        # Text, not an image: no role that makes a reader say "image".
        assert 'role="img"' not in body

    def test_never_wider_than_the_column(self):
        chip = _read("ir-protocol-chip.ts")
        rule = chip[chip.index(".chip.family {"):]
        rule = rule[: rule.index("}")]
        assert "max-width: 88px" in rule and "text-overflow: ellipsis" in rule


RADIO_PLACES = [
    # (file, the radio test, what the pill reads)
    ("ir-signal-monitor.ts", 'sig.medium === "rf"', ".family=${sig.rf_family ?? null}"),
    ("ir-clips.ts", 'sig.medium === "rf"', ".family=${sig.rf_family ?? null}"),
    (
        "ir-command-row.ts",
        'this.command?.medium === "rf"',
        ".family=${this.command.rf_family ?? null}",
    ),
    (
        "ir-trigger-row.ts",
        'trig.medium === "rf" || trig.protocol === RF_TRIGGER_PROTOCOL',
        ".family=${trig.rf_family ?? null}",
    ),
    ("ir-save-perfect-dialog.ts", "${row.rf_family", ".family=${row.rf_family}"),
]


class TestPlaces:
    @pytest.mark.parametrize(("name", "test", "family"), RADIO_PLACES)
    def test_each_row_passes_its_family(self, name, test, family):
        src = _read(name)
        assert test in src
        assert family in src

    def test_the_trigger_row_never_passes_rf_raw_to_the_pill(self):
        row = _read("ir-trigger-row.ts")
        branch = row[row.index("trig.medium === \"rf\" || trig.protocol === RF_TRIGGER_PROTOCOL"):]
        branch = branch[: branch.index("</div>")]
        radio, infrared = branch.split(": html`<ir-protocol-chip", 1)
        assert ".protocol=" not in radio
        assert ".protocol=${trig.protocol}" in infrared

    def test_the_clipper_no_longer_drops_its_radio_pill(self):
        clips = _read("ir-clips.ts")
        assert "the Clipper carries none (round 1 ruling)" not in clips

    def test_the_mirror_names_the_family_never_rf_raw(self):
        mirror = _read("ir-mirror.ts")
        assert (
            "const pill = radio ? familyShort(sig.rf_family) : "
            "(sig.decoded_protocol ?? sig.protocol);"
        ) in mirror
        assert "const pillRaw = !radio && !sig.decoded_protocol;" in mirror
        assert "title=${r.pillTitle || nothing}" in mirror

    def test_pluck_stays_infrared_only(self):
        assert ".family=" not in _read("ir-pluck.ts")


class TestEditor:
    def test_the_pill_row_reads_the_saved_family(self):
        editor = _read("ir-rf-editor.ts")
        assert "public initialFamily: RfFamily | null = null;" in editor
        body = editor[editor.index("private _renderFamily()"):editor.index("render() {")]
        assert "this._creating || this._codeChanged || !this.initialFamily" in body
        assert "<ir-protocol-chip .family=${this.initialFamily}>" in body
        assert "familyEditorText(this.initialFamily)" in body

    def test_the_pill_row_sits_above_the_code(self):
        editor = _read("ir-rf-editor.ts")
        render = editor[editor.index("    render() {"):]
        assert render.index("this._renderFamily()") < render.index('id="rf-code"')

    @pytest.mark.parametrize(
        ("name", "row"),
        [
            ("ir-clips.ts", "this._editSignal.signal"),
            ("ir-device-detail.ts", "this._editCommand"),
            ("ir-mirror.ts", "this._editSignal"),
            ("ir-signal-monitor.ts", "this._editSignal.signal"),
        ],
    )
    def test_every_caller_passes_the_family(self, name, row):
        assert f".initialFamily=${{{row}.rf_family ?? null}}" in _read(name)


class TestTypes:
    def test_rows_that_carry_it(self):
        types = _read("types.ts")
        for iface in (
            "IRCommand", "SavePlanRow", "UnknownSignal", "UnknownSignalEvent", "IRTrigger",
        ):
            start = types.index(f"export interface {iface} {{")
            body = types[start: types.index("\n}\n", start)]
            assert re.search(r"rf_family\?: RfFamily \| null;", body), iface
