"""One frequency control on every radio receiver's pill.

The server describes each receiver once (``hair/rf/receiver_tuning``,
its ``form``) and the pill draws from that alone:

- select: the receiver's own presets in order, "Sweep" among them, and
  "Other..." only when its number feeds an option;
- number: the common bands, greyed outside its limits or declared ranges
  but still a pick, then "Other...";
- both: the presets, then "Other...";
- fixed: its one frequency, no menu, a hover line;
- none: "auto", or where its open window locked, no menu, a hover line;
- "band unknown" for a receiver HAIR can set that gives nothing; right
  after a pick the box shows the picked value, even while the server's
  ``trusted`` is false for stamping.

A pick sends a frequency, or a preset by name (the only way to a sweep).
The rows are read again when what they were built from changes in Home
Assistant, one read at a time. The rules run under node (skipped without the toolchain); the
source pins run everywhere.
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
LOCALES = SRC / "locales"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None

DRIVER = r"""
import { tuneLabel, stillTitle, outsideLimits, tuneMenu, tuneNote, rangesText } from "./rule.js";
import { tuningWatch } from "./watch.js";

const base = { ranges: [], accepts: [], presets: [], select: null, number: null, trusted: true,
    windowed: false, listening: false };
const hz = (v, source) => ({ kind: "hz", hz: v, source });
const rows = {
    select: { ...base, receiver_entity_id: "rm4", form: "select", windowed: true,
        ranges: [[305000000, 335000000], [433420000, 438000000]], select: "select.f",
        accepts: [[305000000, 335000000], [433420000, 438000000]],
        presets: [
            { option: "mhz_433_92", hz: 433920000, current: true },
            { option: "mhz_315", hz: 315000000, current: false },
            { option: "sweep", hz: null, current: false },
        ], now: hz(433920000, "select") },
    selectWithNumber: { ...base, receiver_entity_id: "rm4b", form: "both", select: "select.f",
        number: { entity_id: "number.c", min_hz: null, max_hz: null, step_hz: null,
                  source: "declared" },
        presets: [
            { option: "mhz_433_92", hz: 433920000, current: false },
            { option: "custom", hz: 390000000, current: true, number: true },
        ], now: hz(390000000, "select") },
    number: { ...base, receiver_entity_id: "cc", form: "number",
        number: { entity_id: "number.l", min_hz: 300000000, max_hz: 400000000, step_hz: 1000,
                  source: "found" },
        // No declared ranges: the server's accepts is the number's limits.
        accepts: [[300000000, 400000000]], now: hz(345000000, "number") },
    fixed: { ...base, receiver_entity_id: "athom", form: "fixed",
        ranges: [[433920000, 433920000]], now: hz(433920000, "fixed") },
    none: { ...base, receiver_entity_id: "rx", form: "none", now: { kind: "none", hz: null,
        source: null } },
    noneLocked: { ...base, receiver_entity_id: "rx2", form: "none", windowed: true,
        listening: true, now: hz(315000000, "receiver") },
    sweeping: { ...base, receiver_entity_id: "rm4s", form: "select", listening: true,
        presets: [{ option: "sweep", hz: null, current: true }],
        now: { kind: "sweep", hz: null, source: "receiver" } },
    unknown: { ...base, receiver_entity_id: "cc2", form: "number",
        number: { entity_id: "number.x", min_hz: null, max_hz: null, step_hz: null,
                  source: "found" },
        now: { kind: "unknown", hz: null, source: null } },
    // The answer to a pick of 315: confirmed, the number already 315,
    // and trusted false for the two seconds after HAIR set it.
    justPicked: { ...base, receiver_entity_id: "cc3", form: "number", trusted: false,
        number: { entity_id: "number.y", min_hz: 300000000, max_hz: 928000000,
                  step_hz: 1000, source: "found" },
        now: hz(315000000, "number") },
};
const menu = (r) => {
    const m = tuneMenu(r);
    return m && { other: m.other,
                  rows: m.rows.map((x) => [x.label, x.hz, x.option, x.current, x.dim]),
                  blocked: m.rows.filter((x) => x.blocked).map((x) => [x.hz, x.title]) };
};
console.log(JSON.stringify({
    label: Object.fromEntries(Object.entries(rows).map(([k, r]) => [k, tuneLabel(r, null)])),
    pending: [tuneLabel(rows.number, { hz: 315000000 }),
              tuneLabel(rows.select, { option: "sweep" }),
              tuneLabel(rows.select, { option: "mhz_315" })],
    still: Object.fromEntries(Object.entries(rows).map(([k, r]) => [k, stillTitle(r)])),
    menu: Object.fromEntries(["select", "selectWithNumber", "number", "fixed", "none"].map(
        (k) => [k, menu(rows[k])])),
    outside: [outsideLimits(rows.number, 433920000), outsideLimits(rows.number, 315000000),
              outsideLimits(rows.select, 390000000), outsideLimits(rows.select, 315000000),
              outsideLimits(rows.none, 1), outsideLimits(null, 1)],
    note: [tuneNote({ hz: 390000000, accepts: rows.select.accepts }, null),
           tuneNote(null, { result: "confirmed", current_mhz: 433.0 }),
           tuneNote(null, { result: "did_not_change", current_mhz: 433.92 }),
           tuneNote(null, { result: "cannot_tune", current_mhz: null }),
           tuneNote(null, { result: "not_accepted", current_mhz: null, hz: 390000000,
                            accepts: [[300000000, 928000000]] })],
    ranges: [rangesText(rows.select.accepts, "and", "en"),
             rangesText(rows.select.accepts, "or", "en"),
             rangesText([[300000000, 928000000]], "and", "en"),
             rangesText([[300000000, 348000000], [387000000, 464000000], [779000000, 928000000]],
                        "and", "en"),
             rangesText(rows.select.accepts, "and", "de"),
             rangesText([], "and", "en")],
    watch: (() => {
        const s = { "select.f": { state: "mhz_433_92" },
                    rm4: { state: "2020-01-01T00:00:00", attributes: { capturing: false } } };
        const a = tuningWatch(s, [rows.select]);
        const later = { state: "2020-01-01T00:00:05", attributes: { capturing: false } };
        const heard = tuningWatch({ ...s, rm4: later }, [rows.select]);
        const picked = tuningWatch({ ...s, "select.f": { state: "mhz_315" } }, [rows.select]);
        const opened = tuningWatch({ ...s, rm4: { state: "x", attributes: { capturing: true,
                                   capture_phase: "listening", frequency_hz: 315000000 } } },
                                   [rows.select]);
        return [a === heard, a === picked, a === opened];
    })(),
}));
"""


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _compile(out: Path, name: str, src: str, start: str, head: str) -> None:
    rules = src[src.index(start):src.index("@customElement(")]
    (out / f"{name}.ts").write_text(head + rules, encoding="utf-8")


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("onecontrol")
    t_fn = (
        "function t(key: string, subs?: Record<string, string>): string {\n"
        "  return subs ? key + JSON.stringify(subs) : key;\n}\n"
    )
    _compile(out, "control", _read("rf-frequency-control.ts"),
             "/** The bands the Other field offers",
             'import { hzToMhz, mhzToHz, presetOf } from "./rf-code.js";\n')
    _compile(out, "rule", _read("ir-listen-tune.ts"), "/** What the box reads.",
             'import { hzToMhz } from "./rf-code.js";\n'
             'import { listBands, outsideRange, type ListRow } from "./control.js";\n'
             "type ReceiverTuning = any; type ReceiverTuneResult = any; type TunePick = any;\n"
             + t_fn)
    _compile(out, "watch", _read("ir-listen-row.ts"),
             "/** What the radio receivers' rows depend on", "type ReceiverTuning = any;\n")
    shutil.copy(SRC / "rf-code.ts", out / "rf-code.ts")
    subprocess.run(
        [
            str(TSC), *(str(out / f) for f in ("rule.ts", "control.ts", "watch.ts", "rf-code.ts")),
            "--module", "esnext", "--target", "es2022", "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "driver.mjs").write_text(DRIVER, encoding="utf-8")
    result = subprocess.run(["node", str(out / "driver.mjs")], check=True,
                            capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


MHZ = 'rfedit.mhz{{"mhz":"{}"}}'


class TestWhatThePillReads:
    def test_each_form(self, run):
        assert run["label"] == {
            "select": "433.92",
            "selectWithNumber": "390",
            "number": "345",
            "fixed": "433.92",
            "none": "listen.tune_auto",
            "noneLocked": "315",
            "sweeping": "listen.sweep",
            "unknown": "listen.band_unknown",
            "justPicked": "315",
        }

    def test_a_pick_shows_the_picked_value_not_band_unknown(self, run):
        # The bench case: confirmed, trusted false, the pill must not
        # snap back to "band unknown".
        assert run["label"]["justPicked"] == "315"

    def test_a_pick_on_its_way(self, run):
        assert run["pending"] == [
            'listen.tune_setting{"mhz":"315"}',
            'listen.tune_setting{"mhz":"listen.sweep"}',
            'listen.tune_setting{"mhz":"315"}',
        ]

    def test_only_fixed_and_none_have_a_hover_line_and_no_menu(self, run):
        still = {k: v for k, v in run["still"].items() if v is not None}
        assert still == {
            "fixed": "listen.tune_fixed_title",
            "none": "listen.tune_auto_title",
            "noneLocked": "listen.tune_auto_title",
        }
        assert run["menu"]["fixed"] is None and run["menu"]["none"] is None


class TestTheMenu:
    def test_a_select_shows_only_its_presets(self, run):
        menu = run["menu"]["select"]
        assert menu == {"other": False, "rows": [
            [MHZ.format("433.92"), 433920000, "mhz_433_92", True, False],
            [MHZ.format("315"), 315000000, "mhz_315", False, False],
            ["listen.sweep", None, "sweep", False, False],
        ], "blocked": []}

    def test_the_numbers_option_is_other_not_a_band(self, run):
        menu = run["menu"]["selectWithNumber"]
        assert menu["other"] is True
        assert [r[2] for r in menu["rows"]] == ["mhz_433_92"]

    def test_a_band_it_does_not_accept_cannot_be_picked(self, run):
        blocked = run["menu"]["number"]["blocked"]
        assert [b[0] for b in blocked] == [418000000, 433420000, 433920000, 868350000, 915000000]
        assert blocked[0][1] == 'listen.tune_band_refused{"mhz":"418"}'
        # A select's presets are the device's own: never blocked.
        assert run["menu"]["select"]["blocked"] == []
        assert run["menu"]["selectWithNumber"]["blocked"] == []

    def test_a_number_gets_the_common_bands_greyed_outside(self, run):
        menu = run["menu"]["number"]
        assert menu["other"] is True
        by_hz = {r[1]: r for r in menu["rows"]}
        # The current odd value takes its place, marked.
        assert by_hz[345000000][3] is True
        # Inside what it accepts (300 to 400 here): not greyed; above it:
        # greyed, and blocked (above).
        assert by_hz[315000000][4] is False and by_hz[390000000][4] is False
        assert by_hz[433920000][4] is True and by_hz[915000000][4] is True
        assert all(r[2] is None for r in menu["rows"])

    def test_outside_is_what_the_server_says_it_accepts(self, run):
        assert run["outside"] == [True, False, True, False, False, False]


class TestTheLines:
    def test_the_note_after_a_pick(self, run):
        refused, confirmed, unchanged, cannot, door = run["note"]
        r = 'listen.tune_range{{"low":"{}","high":"{}"}}'.format
        assert refused == {"key": "listen.tune_refused", "params": {
            "mhz": "390", "ranges": f"{r('305', '335')} and {r('433.42', '438')}"}}
        assert confirmed is None
        assert unchanged == {"key": "listen.tune_did_not_change", "params": {"mhz": "433.92"}}
        assert cannot == {"key": "listen.tune_cannot"}
        # The door refused what got through: the same line, from its answer.
        assert door == {"key": "listen.tune_refused", "params": {
            "mhz": "390", "ranges": r("300", "928")}}

    def test_the_ranges_as_words(self, run):
        r = 'listen.tune_range{{"low":"{}","high":"{}"}}'.format
        two_and, two_or, one, three, german, none = run["ranges"]
        assert two_and == f"{r('305', '335')} and {r('433.42', '438')}"
        assert two_or == f"{r('305', '335')} or {r('433.42', '438')}"
        assert one == r("300", "928")
        assert three == f"{r('300', '348')}, {r('387', '464')}, and {r('779', '928')}"
        assert german == f"{r('305', '335')} und {r('433.42', '438')}"
        assert none == ""


class TestReadAgain:
    def test_what_starts_a_read(self, run):
        heard, picked, opened = run["watch"]
        # A code heard moves the receiver's state, not its tuning.
        assert heard is True
        # The select changed in Home Assistant, or a window opened.
        assert picked is False and opened is False

    def test_one_read_at_a_time_and_no_timer(self):
        row = _read("ir-listen-row.ts")
        assert "if (changed.has(\"hass\")) this._rereadOnChange();" in row
        assert "if (this._tuningReading) {\n            this._tuningAgain = true;" in row
        assert "setTimeout" not in row
        assert "this._tuningSeen = tuningWatch(this.hass?.states, receivers);" in row


class TestWiring:
    def test_every_radio_pill_gets_the_one_control(self):
        chip = _read("ir-listen-chip.ts")
        assert 'const freqs = row.medium === "rf" ? [] : frequencyChoices(row);' in chip
        block = chip.split("// Where a radio receiver listens", 1)[1]
        block = block.split("const lengths = lengthChoices(", 1)[0]
        assert 'if (row.medium === "rf" && this.tuning) {' in block
        assert "?inactive=${!active}" in block

    def test_the_list_takes_the_rows(self):
        tune = _read("ir-listen-tune.ts")
        assert ".rows=${menu.rows}" in tune and ".other=${menu.other}" in tune
        assert "@frequency-pick=" in tune
        control = _read("rf-frequency-control.ts")
        assert (
            'this._fire("frequency-pick", row.option !== null ? { option: row.option } : '
            '{ hz: row.hz });'
        ) in control

    def test_a_pick_sends_a_frequency_or_a_preset(self):
        api = _read("api.ts")
        assert '...("hz" in pick ? { frequency_hz: pick.hz } : { option: pick.option }),' in api
        tune = _read("ir-listen-tune.ts")
        assert "result = await this.api.receiverTune(this.receiverEntityId, pick);" in tune


class TestTheStrings:
    KEYS = ("listen.tune_auto", "listen.tune_auto_title", "listen.tune_fixed_title",
            "listen.sweep", "listen.tune_other")

    @pytest.mark.parametrize("path", sorted(LOCALES.glob("*.json")), ids=lambda p: p.stem)
    def test_every_language(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in self.KEYS:
            assert data.get(key), (path.name, key)
            assert "\u2014" not in data[key], (path.name, key)

    def test_the_english(self):
        en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        assert en["listen.tune_auto"] == "auto"
        # True whether or not the receiver sweeps inside its window.
        assert en["listen.tune_auto_title"] == "HAIR can't set where this receiver listens."
        assert en["listen.tune_fixed_title"] == "This receiver only listens here."
