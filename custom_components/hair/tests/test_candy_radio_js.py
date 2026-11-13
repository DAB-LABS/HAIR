"""Radio in the Candy Drawer, the panel's half, actually executed.

``candy-text.ts`` lays out a radio block (a voted press, a lone frame, a
single static capture, a radio send), puts the verdict words in every
received block's header, and decides what the seven chips show and what
Copy all hands over. This transpiles it with the repo's own TypeScript
and runs it under node. Schema: docs/internal/IR-RF/rf-2026-11-11-candy-schema.md.

The ``.sub`` lines in a block come from the radio editor's own writer,
and are checked here against the server's pinned twin
(``rf_paste.to_sub``), so a block copied from the drawer pastes into the
Clipper as the same code.

Node-driven tests are skipped without the frontend toolchain; the
source and locale pins run everywhere.
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
LOCALES = SRC / "locales"

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None

TS = 1793473471.218  # 2026-10-31 19:04:31.218 UTC

FRAME = [456, -1368, 1368, -456, 456, -1368, 456, -12900]
PRESS = {
    "ts": TS, "dir": "rx", "entity_id": "radio_frequency.athom_rx",
    "name": "Athom IR-RF 433MHz RF Receiver", "medium": "rf",
    "verdict": "known", "known_from": "device", "known_name": "Bench Plug / On",
    "stage": "press", "protocol": None, "address": None, "command": None,
    "fingerprint": "rf:sl:abcd", "covers": None, "carrier_hz": None, "pronto": None,
    "ditto": None, "echo": None, "echo_of": None, "echo_via": None,
    "frequency_hz": 433_920_000, "frequency_source": "receiver", "modulation": "OOK",
    "short_mark_us": 456, "gap_us": 12_900, "gap_source": "measured",
    "frames": 8, "votes": 6, "frame_hash": "afe42b2c99", "body_edges": 48,
    "frame": FRAME, "raw": [456, -1368, 1368, -456],
}

DRIVER = r"""
import {
    formatBlock, knownWords, kindOf, isVisible, copyText, parseChips,
    serializeChips, addStatic, staticLine, isStaticSummary, DEFAULT_CANDY_FILTER,
} from "./candy-text.js";
import { toSub } from "./rf-code.js";

const press = __PRESS__;
const ir = {
    ts: press.ts, dir: "rx", entity_id: "infrared.living_ir", name: "Living room IR",
    protocol: "NEC", address: "0x0004", command: "0x08", fingerprint: "NEC:0x0004:0x08",
    covers: true, carrier_hz: 38000, frames: 3, pronto: "0000 006D", raw: [8990, -4480],
    ditto: false, echo: null, echo_of: null, echo_via: null,
    medium: "ir", verdict: "known", known_from: "device", known_name: "TV / Power", stage: null,
};
const frame = { ...press, stage: "frame", frames: 1, votes: null, gap_us: null,
                gap_source: "assumed", verdict: "unknown", known_from: null, known_name: null };
const tx = {
    ts: press.ts, dir: "tx", seq: 9, label: "Bench Plug / On", sends: 6, origin: "manager",
    device: "Bench Plug", command_name: "On", medium: "rf", verdict: "known",
    known_from: null, known_name: null, stage: null,
    emitters: [{ entity_id: "radio_frequency.athom_tx", name: "Athom TX" }],
    skipped: [{ entity_id: "radio_frequency.rm4_tx", name: "RM4 TX", reason: "unavailable" }],
    frequency_hz: 433_920_000, on_air_hz: 433_920_000, substituted: false,
    fingerprint: "rf:sl:abcd", frame_hash: "afe42b2c99", gap_us: 12_900, frame: press.frame,
    raw: [456, -1368], protocol: null, address: null, command: null, covers: null,
    carrier_hz: null, frames: 1, pronto: null,
};
const filter = (over) => ({ ...DEFAULT_CANDY_FILTER, ...over });
const kinds = {
    irKnown: { dir: "rx", medium: "ir", verdict: "known" },
    irNew: { dir: "rx", medium: "ir", verdict: "unknown" },
    rfKnown: { dir: "rx", medium: "rf", verdict: "known" },
    rfNew: { dir: "rx", medium: "rf", verdict: "unknown" },
    rfStatic: { dir: "rx", medium: "rf", verdict: "static" },
    rfTx: { dir: "tx", medium: "rf", verdict: "known" },
    irTx: { dir: "tx", medium: "ir", verdict: "known" },
};
const matrix = {};
const sets = {
    all: filter({}),
    irOnly: filter({ rf: false }),
    rfOnly: filter({ ir: false }),
    knownOnly: filter({ unknown: false }),
    unknownOnly: filter({ known: false }),
    staticOn: filter({ static: true }),
    staticButRfOff: filter({ static: true, rf: false }),
    txOnly: filter({ rx: false }),
};
for (const [name, f] of Object.entries(sets)) {
    matrix[name] = Object.fromEntries(Object.entries(kinds).map(([k, v]) => [k, isVisible(v, f)]));
}
const blocks = Object.entries(kinds).map(([k, v]) => ({ kind: v, text: k }));
const totals = new Map();
const summary = (entity_id, name, count) =>
    ({ ts: 1, dir: "rx", entity_id, name, count, stage: "static", verdict: "static" });
addStatic(totals, summary("radio_frequency.athom_rx", "Athom", 5));
addStatic(totals, summary("radio_frequency.athom_rx", "Athom", 12));
addStatic(totals, summary("radio_frequency.rm4_rx", "RM4", 1));

console.log(JSON.stringify({
    press: formatBlock(press, "UTC"),
    pressSub: toSub(press.frame, press.frequency_hz, press.gap_us),
    frameUnknown: formatBlock(frame, "UTC"),
    frameKnown: formatBlock({ ...frame, verdict: "known", known_from: "sniffer",
                              known_name: "Remote 20 / Button 2 on" }, "UTC"),
    noBand: formatBlock({ ...press, frequency_hz: null, frequency_source: null,
                          frame: null, verdict: "unknown", known_from: null,
                          known_name: null }, "UTC"),
    family: formatBlock({ ...press, protocol: "EV1527" }, "UTC").split("\n")[1],
    echo: formatBlock({ ...press, echo: "send", echo_of: 9, known_from: "echo",
                        known_name: null }, "UTC").split("\n")[0],
    staticCapture: formatBlock({ ts: press.ts, dir: "rx", entity_id: "radio_frequency.athom_rx",
                                 name: "Athom", medium: "rf", stage: "static",
                                 verdict: "static", count: null, raw: [120, -80, 95],
                                 values: 3, frames: 0, reason: "no_body" }, "UTC"),
    reasons: ["lone", "no_body", "short", null, "odd"].map((reason) => knownWords(
        { ts: 1, dir: "rx", medium: "rf", stage: "static", verdict: "static", reason })),
    tx: formatBlock(tx, "UTC"),
    txSubstituted: formatBlock({ ...tx, on_air_hz: 433_920_000, frequency_hz: 433_420_000,
                                 substituted: true, skipped: [] }, "UTC").split("\n")[1],
    words: {
        device: knownWords(ir),
        trigger: knownWords({ ...ir, known_from: "trigger", known_name: "Doorbell" }),
        sniffer: knownWords({ ...ir, known_from: "sniffer", known_name: "Remote 3 / Power" }),
        unknown: knownWords({ ...ir, verdict: "unknown", known_from: null, known_name: null }),
        ditto: knownWords({ ...ir, ditto: true, verdict: "unknown", known_from: null }),
        dittoKnown: knownWords({ ...ir, ditto: true }),
        echo: knownWords({ ...ir, known_from: "echo", known_name: null }),
        old: knownWords({ ...ir, verdict: undefined, known_from: undefined }),
        strange: knownWords({ ...ir, known_from: "telepathy" }),
        tx: knownWords({ ...tx }),
    },
    irBlock: formatBlock(ir, "UTC").split("\n")[0],
    kinds: {
        old: kindOf({ ...ir, medium: undefined, verdict: undefined }),
        tx: kindOf(tx),
        frame: kindOf(frame),
    },
    matrix,
    noVerdict: [
        isVisible(kinds.irKnown, filter({ known: false }), false),
        isVisible(kinds.irKnown, filter({ known: false, unknown: false }), false),
    ],
    copyKnown: copyText("M", null, blocks, filter({ unknown: false }), ["Athom: 17 hidden"]),
    copyRfStatic: copyText("M", null, blocks, filter({ ir: false, static: true })),
    chips: {
        empty: parseChips(null),
        broken: parseChips("{not json"),
        kept: parseChips(serializeChips(filter({ ir: false, known: false, static: true }))),
        staticNeverKept: serializeChips(filter({ static: true })),
        partial: parseChips('{"rx": false, "static": true, "rf": "yes"}'),
    },
    statics: {
        athom: totals.get("radio_frequency.athom_rx"),
        rm4: totals.get("radio_frequency.rm4_rx"),
        line: staticLine("{name}: {count} static captures hidden", "Athom", 17),
        summary: isStaticSummary({ stage: "static", count: 4 }),
        capture: isStaticSummary({ stage: "static", count: null }),
    },
}));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("candyradiojs")
    subprocess.run(
        [
            str(TSC), "src/candy-text.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler", "--resolveJsonModule",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "driver.mjs").write_text(
        DRIVER.replace("__PRESS__", json.dumps(PRESS)), encoding="utf-8"
    )
    result = subprocess.run(
        ["node", str(out / "driver.mjs")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


def _sub(block: str) -> str:
    """The .sub text a block carries, as the editor's copy would hand it."""
    lines = block.split("\n")
    start = lines.index("Sub:") + 1
    end = next(i for i, line in enumerate(lines) if line.startswith("Raw: "))
    return "\n".join(lines[start:end]) + "\n"


class TestARadioPress:
    def test_the_block(self, run):
        lines = run["press"].split("\n")
        assert lines[0] == (
            "19:04:31.218  RX  Athom IR-RF 433MHz RF Receiver (radio_frequency.athom_rx)"
            "   known: Bench Plug / On"
        )
        assert lines[1] == (
            "RF   433.92 MHz (receiver)   short mark 456 us   gap 12.9 ms   "
            "8 frames, 6 agree   fp afe42b2c"
        )
        assert lines[2] == "Sub:"
        assert lines[3] == "Filetype: Flipper SubGhz RAW File"
        assert lines[-1] == "Raw: 456 -1368 1368 -456"

    def test_the_sub_is_the_editors_copy(self, run):
        assert _sub(run["press"]) == run["pressSub"]

    def test_the_sub_is_the_servers_twin_too(self, run):
        from custom_components.hair.rf_paste import to_sub

        assert _sub(run["press"]) == to_sub(FRAME, 433_920_000, 12_900)

    def test_a_family_name_goes_after_rf(self, run):
        assert run["family"].startswith("RF  EV1527   433.92 MHz (receiver)")

    def test_no_band_and_no_frame(self, run):
        lines = run["noBand"].split("\n")
        assert lines[0].endswith("   new")
        assert lines[1].startswith("RF   no band   short mark 456 us")
        assert "Sub:" not in lines

    def test_an_echo_says_its_echo_words_only(self, run):
        assert run["echo"].endswith("   echo of the TX above")
        assert "known:" not in run["echo"]


class TestALoneFrame:
    def test_unknown_is_waiting(self, run):
        lines = run["frameUnknown"].split("\n")
        assert lines[0].endswith("   frame, waiting")
        assert lines[1] == "RF   433.92 MHz (receiver)   short mark 456 us   1 frame   fp afe42b2c"

    def test_known_says_so(self, run):
        assert run["frameKnown"].split("\n")[0].endswith(
            "   known: Remote 20 / Button 2 on, frame"
        )


class TestStatic:
    def test_a_single_capture_is_its_header_and_raw(self, run):
        assert run["staticCapture"].split("\n") == [
            "19:04:31.218  RX  Athom (radio_frequency.athom_rx)   static: hiss",
            "Raw: 120 -80 95",
        ]

    def test_the_header_says_which(self, run):
        # Owner, 2026-11-12: hiss (no code, too short) or a lone frame;
        # a reason this panel does not know is plain static.
        assert run["reasons"] == [
            "static: lone frame", "static: hiss", "static: hiss", "static", "static",
        ]

    def test_static_sits_apart_in_the_chip_row(self):
        console = _flat("candy-console.ts")
        assert (
            'this.chip("unknown", l.unknown, CANDY_GLYPH_UNKNOWN), this.el("span", "sep"), '
            'this.chip("static", l.static, CANDY_GLYPH_STATIC),'
        ) in console

    def test_summaries_add_up_per_receiver(self, run):
        assert run["statics"]["athom"] == {
            "name": "Athom (radio_frequency.athom_rx)", "count": 17,
        }
        assert run["statics"]["rm4"]["count"] == 1
        assert run["statics"]["line"] == "Athom: 17 static captures hidden"
        assert run["statics"]["summary"] is True
        assert run["statics"]["capture"] is False


class TestARadioSend:
    def test_the_block(self, run):
        lines = run["tx"].split("\n")
        assert lines[0] == (
            "19:04:31.218  TX  Athom TX (radio_frequency.athom_tx)   Bench Plug / On   x6 sends"
        )
        assert lines[1] == "RF   433.92 MHz   gap 12.9 ms   fp afe42b2c"
        assert lines[2] == "skipped: RM4 TX (radio_frequency.rm4_tx) (unavailable)"
        assert lines[3] == "Sub:"
        assert _sub(run["tx"]) == run["pressSub"]

    def test_a_fixed_carrier_says_its_own(self, run):
        assert run["txSubstituted"] == (
            "RF   433.42 MHz   on air 433.92 MHz (its own carrier)   gap 12.9 ms   fp afe42b2c"
        )


class TestTheWords:
    def test_each_source(self, run):
        words = run["words"]
        assert words["device"] == "known: TV / Power"
        assert words["trigger"] == "known: trigger Doorbell"
        assert words["sniffer"] == "known: Remote 3 / Power"
        assert words["unknown"] == "new"

    def test_what_says_nothing(self, run):
        words = run["words"]
        # "new" never on a ditto; an echo has its own words; an old
        # event, an unknown source and a send say nothing.
        assert words["ditto"] is None
        assert words["echo"] is None
        assert words["old"] is None
        assert words["strange"] is None
        assert words["tx"] is None
        assert words["dittoKnown"] == "known: TV / Power"

    def test_an_infrared_block_gains_only_the_word(self, run):
        assert run["irBlock"] == (
            "19:04:31.218  RX  Living room IR (infrared.living_ir)   known: TV / Power"
        )


class TestTheChips:
    def test_kinds(self, run):
        assert run["kinds"]["old"] == {"dir": "rx", "medium": "ir", "verdict": "known"}
        assert run["kinds"]["tx"] == {"dir": "tx", "medium": "rf", "verdict": "known"}
        assert run["kinds"]["frame"] == {"dir": "rx", "medium": "rf", "verdict": "unknown"}

    def test_the_matrix(self, run):
        m = run["matrix"]
        assert m["all"] == {
            "irKnown": True, "irNew": True, "rfKnown": True, "rfNew": True,
            "rfStatic": False, "rfTx": True, "irTx": True,
        }
        assert [k for k, v in m["irOnly"].items() if v] == ["irKnown", "irNew", "irTx"]
        assert [k for k, v in m["rfOnly"].items() if v] == ["rfKnown", "rfNew", "rfTx"]
        assert [k for k, v in m["knownOnly"].items() if v] == [
            "irKnown", "rfKnown", "rfTx", "irTx",
        ]
        assert [k for k, v in m["unknownOnly"].items() if v] == ["irNew", "rfNew"]
        assert m["staticOn"]["rfStatic"] is True
        assert m["staticButRfOff"]["rfStatic"] is False
        assert [k for k, v in m["txOnly"].items() if v] == ["rfTx", "irTx"]

    def test_an_event_with_no_verdict_follows_either(self, run):
        assert run["noVerdict"] == [True, False]

    def test_copy_all_follows_the_chips(self, run):
        assert run["copyKnown"] == (
            "M\n\nAthom: 17 hidden\n\nirKnown\n\nrfKnown\n\nrfTx\n\nirTx\n"
        )
        assert run["copyRfStatic"] == "M\n\nrfKnown\n\nrfNew\n\nrfStatic\n\nrfTx\n"

    def test_kept_per_browser_but_static(self, run):
        chips = run["chips"]
        default = {"rx": True, "tx": True, "ir": True, "rf": True,
                   "known": True, "unknown": True, "static": False}
        assert chips["empty"] == default
        assert chips["broken"] == default
        assert chips["kept"] == {**default, "ir": False, "known": False}
        assert "static" not in json.loads(chips["staticNeverKept"])
        assert chips["partial"] == {**default, "rx": False}


FEED_DRIVER = r"""
import { CandyFeed } from "./candy-feed.js";

const log = [];
const pending = [];
const api = {
    subscribeCandy(onEvent, opts) {
        const id = pending.length + 1;
        log.push(`sub${id}:${opts.static ? "static" : "plain"}`);
        let resolve, reject;
        const p = new Promise((res, rej) => { resolve = res; reject = rej; });
        pending.push({ id, onEvent, resolve, reject });
        return p;
    },
};
const unsub = (id) => async () => { log.push(`unsub${id}`); };
const tick = () => new Promise((r) => setTimeout(r, 0));
const seen = [];
const feed = new CandyFeed(api, (e) => seen.push(e.n));

feed.start(false);
pending[0].resolve(unsub(1)); await tick();
pending[0].onEvent({ n: "a" });
feed.start(true);                        // Static on
const orderAtToggle = log.slice();
pending[0].onEvent({ n: "old-in-the-gap" });  // still printing until the new one answers
pending[1].resolve(unsub(2)); await tick();
const afterToggle = log.slice();
pending[0].onEvent({ n: "old-after" });  // closed: dropped
pending[1].onEvent({ n: "b" });
feed.start(false); feed.start(true);     // two quick toggles: sub3, sub4
pending[3].resolve(unsub(4)); await tick();
pending[2].resolve(unsub(3)); await tick();
const afterRace = log.slice();
pending[2].onEvent({ n: "superseded" });
pending[3].onEvent({ n: "c" });
feed.stop();
const afterStop = log.slice();
pending[3].onEvent({ n: "after-stop" });
const late = new CandyFeed(api, () => {});
late.start(false); late.stop();
pending[4].resolve(unsub(5)); await tick();
const refusedSeen = [];
const refused = new CandyFeed(api, (e) => refusedSeen.push(e.n));
refused.start(false); pending[5].resolve(unsub(6)); await tick();
refused.start(true); pending[6].reject(new Error("refused")); await tick();
pending[5].onEvent({ n: "kept" });
console.log(JSON.stringify({ orderAtToggle, afterToggle, afterRace, afterStop,
                             end: log.slice(), seen, refusedSeen }));
"""


@pytest.fixture(scope="module")
def feed(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("candyfeedjs")
    subprocess.run(
        [
            str(TSC), "src/candy-feed.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler", "--resolveJsonModule",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "driver.mjs").write_text(FEED_DRIVER, encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "driver.mjs")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


class TestTheFeed:
    def test_the_new_subscription_opens_before_the_old_closes(self, feed):
        # The server never sees the drawer leave on a Static toggle, so
        # its static counts and ditto memo survive.
        assert feed["orderAtToggle"] == ["sub1:plain", "sub2:static"]
        assert feed["afterToggle"] == ["sub1:plain", "sub2:static", "unsub1"]

    def test_nothing_is_lost_or_printed_twice(self, feed):
        # The old one prints until the new one answers; then only the new.
        assert feed["seen"] == ["a", "old-in-the-gap", "b", "c"]

    def test_quick_toggles_leave_the_last_one_open(self, feed):
        log = feed["afterRace"]
        assert log[3:] == ["sub3:plain", "sub4:static", "unsub2", "unsub3"]

    def test_stop_closes_the_current_one(self, feed):
        assert feed["afterStop"][-1] == "unsub4"

    def test_stop_while_pending_closes_it_when_it_answers(self, feed):
        assert "unsub5" in feed["end"]

    def test_a_refused_resubscribe_keeps_the_old_one_printing(self, feed):
        assert "unsub6" not in feed["end"]
        assert feed["refusedSeen"] == ["kept"]


# --- source level, runs everywhere ------------------------------------------


def _flat(name: str) -> str:
    return " ".join((SRC / name).read_text(encoding="utf-8").split())


class TestTheWiring:
    def test_the_sub_writer_is_the_editors(self):
        text = (SRC / "candy-text.ts").read_text(encoding="utf-8")
        assert 'import { toSub } from "./rf-code.js";' in text
        assert "Filetype" not in text

    def test_static_resubscribes_and_nothing_else_does(self):
        console = _flat("candy-console.ts")
        assert (
            "if (this.filter.static !== staticWas) this.opts.onStaticChange?.(this.filter.static);"
        ) in console
        feed = _flat("candy-feed.ts")
        assert "{ static: withStatic }," in feed
        for host in ("candy-controller.ts", "ir-candy-drawer.ts"):
            flat = _flat(host)
            assert "onStaticChange: (on) =>" in flat, host
            assert ".start(false);" in flat, host
            assert "subscribeCandy(" not in flat, host

    def test_the_api_asks_for_static_only_when_on(self):
        api = _flat("api.ts")
        assert (
            'opts.static ? { type: "hair/candy/subscribe", static: true } '
            ': { type: "hair/candy/subscribe" },'
        ) in api

    def test_static_needs_rf(self):
        console = _flat("candy-console.ts")
        assert 'if (key === "static" && !this.filter.rf) return;' in console
        assert 'if (key === "rf" && !this.filter.rf) this.filter.static = false;' in console
        assert 'if (staticChip && !this.ended) staticChip.disabled = !this.filter.rf;' in console

    def test_the_ir_and_rf_glyphs_are_the_panels(self):
        glyphs = (SRC / "candy-glyphs.ts").read_text(encoding="utf-8")
        proto = (SRC / "ir-proto-glyph.ts").read_text(encoding="utf-8")
        for d in (
            "M9.5 8h8.5M9.5 12h11.5M9.5 16h8.5",
            "M9 9A4.24 4.24 0 0 1 9 15M12 6A8.49 8.49 0 0 1 12 18M15 3A12.73 12.73 0 0 1 15 21",
        ):
            assert d in glyphs and d in proto
        assert 'cx="5" cy="12" r="2.5"' in proto
        assert 'cx: "5", cy: "12", r: "2.5"' in glyphs

    def test_one_constant_per_chip_glyph(self):
        glyphs = (SRC / "candy-glyphs.ts").read_text(encoding="utf-8")
        for name in ("CANDY_GLYPH_KNOWN", "CANDY_GLYPH_UNKNOWN", "CANDY_GLYPH_STATIC"):
            assert glyphs.count(f"export const {name}: CandyGlyph") == 1


KEYS = ("candy.known", "candy.unknown", "candy.static", "candy.static_hidden")


class TestTheLocales:
    def test_english(self):
        en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        assert [en[k] for k in KEYS] == [
            "Known", "Unknown", "Static", "{name}: {count} static captures hidden",
        ]

    @pytest.mark.parametrize("path", sorted(LOCALES.glob("*.json")), ids=lambda p: p.stem)
    def test_every_locale(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in KEYS:
            assert data.get(key), key
            assert "—" not in data[key], key
        assert "{count}" in data["candy.static_hidden"]
        assert "{name}" in data["candy.static_hidden"]
