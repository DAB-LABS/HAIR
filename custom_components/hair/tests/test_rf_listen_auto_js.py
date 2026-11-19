"""A radio receiver HAIR can't tune gets no list of bands.

- One with a single fixed frequency (an Athom) shows that frequency.
- A receiver that declares nothing (no tuning number and no single
  declared frequency) shows "auto", or while its window is open and the
  receiver says where it locked, that frequency.
- Neither opens a menu or has a caret; each has a line on hover.
- "band unknown" stays for a tunable receiver whose number gives nothing.

The rules run under node (skipped without the toolchain); the source
pins run everywhere.
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
import { tuneKind, tuneLabel, stillTitle } from "./rule.js";

const cc1101 = { receiver_entity_id: "c", tunable: true, number_entity: "n", available: true,
    current_mhz: 433.92, min_mhz: 300, max_mhz: 928, declared: [], fixed: false };
const lost = { ...cc1101, available: false, current_mhz: null };
const athom = { receiver_entity_id: "a", tunable: false, number_entity: null, available: true,
    current_mhz: 433.92, min_mhz: null, max_mhz: null, declared: [[433920000, 433920000]],
    fixed: true };
const nothing = { receiver_entity_id: "b", tunable: false, number_entity: null, available: false,
    current_mhz: null, min_mhz: null, max_mhz: null, declared: [], fixed: false };
console.log(JSON.stringify({
    kind: [cc1101, lost, athom, nothing, null].map(tuneKind),
    label: [
        tuneLabel(cc1101, null), tuneLabel(lost, null), tuneLabel(athom, null),
        tuneLabel(nothing, null), tuneLabel(nothing, null, 315000000),
        tuneLabel(athom, null, 315000000), tuneLabel(cc1101, null, 315000000),
    ],
    still: [cc1101, lost, athom, nothing].map(stillTitle),
}));
"""


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("listenauto")
    src = _read("ir-listen-tune.ts")
    rules = src[src.index("/** Which of the three"):src.index("@customElement(")]
    head = (
        'import { hzToMhz } from "./rf-code.js";\n'
        "type ReceiverTuning = any; type ReceiverTuneResult = any;\n"
        "function t(key: string, subs?: Record<string, string>): string {\n"
        "  return subs ? key + JSON.stringify(subs) : key;\n}\n"
    )
    (out / "rule.ts").write_text(head + rules, encoding="utf-8")
    shutil.copy(SRC / "rf-code.ts", out / "rf-code.ts")
    subprocess.run(
        [
            str(TSC), str(out / "rule.ts"), str(out / "rf-code.ts"),
            "--module", "esnext", "--target", "es2022", "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "driver.mjs").write_text(DRIVER, encoding="utf-8")
    result = subprocess.run(["node", str(out / "driver.mjs")], check=True,
                            capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


class TestTheThreeKinds:
    def test_which_is_which(self, run):
        assert run["kind"] == ["tunable", "tunable", "fixed", "auto", "tunable"]

    def test_what_each_reads(self, run):
        assert run["label"] == [
            "433.92",
            "listen.band_unknown",
            "433.92",
            "listen.tune_auto",
            "315",
            # A window's frequency is read only for a receiver that finds
            # its own; a fixed or tunable one shows what it holds.
            "433.92",
            "433.92",
        ]

    def test_only_the_untunable_have_a_hover_line(self, run):
        assert run["still"] == [
            None, None, "listen.tune_fixed_title", "listen.tune_auto_title",
        ]


class TestNothingToPick:
    def _tune(self) -> str:
        return _read("ir-listen-tune.ts")

    def test_a_plain_value_and_no_menu(self):
        tune = self._tune()
        body = tune.split("if (still !== null) {", 1)[1].split("\n        }\n", 1)[0]
        assert '<span class="box still" title=${still}' in body
        assert "<button" not in body and "caret" not in body and "_open" not in body

    def test_it_comes_before_the_menu(self):
        tune = self._tune()
        assert tune.index("if (still !== null) {") < tune.index('aria-haspopup=${this.inactive')

    def test_the_pill_hands_over_the_locked_frequency(self):
        chip = _read("ir-listen-chip.ts")
        assert '.windowHz=${live.phase === "listening" ? live.frequencyHz : null}' in chip


class TestTheStrings:
    KEYS = ("listen.tune_auto", "listen.tune_auto_title", "listen.tune_fixed_title")

    @pytest.mark.parametrize("path", sorted(LOCALES.glob("*.json")), ids=lambda p: p.stem)
    def test_every_language(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in self.KEYS:
            assert data.get(key), (path.name, key)
            assert "—" not in data[key], (path.name, key)

    def test_the_english(self):
        en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        assert en["listen.tune_auto"] == "auto"
        # True whether or not the receiver sweeps inside its window.
        assert en["listen.tune_auto_title"] == "HAIR can't set where this receiver listens."
        assert en["listen.tune_fixed_title"] == "This receiver only listens here."
