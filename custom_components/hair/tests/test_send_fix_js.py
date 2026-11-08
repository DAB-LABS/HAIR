"""Send review fix round, frontend: N14.

N14: a Sniffer or Clipper Test refused for its frequency names the
transmitter the user picked and the band, in the bottom toast, and the
row keeps its Test button.

The rules run under node with the repo's TypeScript (skipped without the
toolchain), with ``localize.js`` replaced by a stand-in that echoes the
key and its values; the source pins run everywhere.
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

LOCALIZE_STUB = """
export function t(key, params) {
    return JSON.stringify(params ? [key, params] : [key]);
}
"""

DRIVER = r"""
import { testRefusal, testRefusalKey } from "./rf-errors.js";

const err = (code) => ({ code });
console.log(JSON.stringify({
    keys: [
        testRefusalKey(err("rf_frequency_unsupported"), "Athom RF", "315"),
        testRefusalKey(err("rf_frequency_unsupported"), "Athom RF", null),
        testRefusalKey(err("rf_no_frequency"), "Athom RF", "315"),
        testRefusalKey(err("wrong_medium_code"), "Athom RF", null),
        testRefusalKey(new Error("boom"), "Athom RF", "315"),
        testRefusalKey(null, "Athom RF", "315"),
    ],
    sentence: testRefusal(err("rf_frequency_unsupported"), "Athom RF", "433.92"),
}));
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("sendfixjs")
    subprocess.run(
        [
            str(TSC), "src/rf-errors.ts",
            "--module", "esnext", "--target", "es2022",
            "--moduleResolution", "bundler", "--resolveJsonModule",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "localize.js").write_text(LOCALIZE_STUB, encoding="utf-8")
    (out / "driver.mjs").write_text(DRIVER, encoding="utf-8")
    result = subprocess.run(
        ["node", str(out / "driver.mjs")],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


def _flat(name: str) -> str:
    return " ".join((SRC / name).read_text(encoding="utf-8").split())


class TestTheTestRefusal:
    def test_a_frequency_refusal_names_the_transmitter_and_the_band(self, run):
        assert run["keys"][0] == {
            "key": "errors.test_rf_frequency_unsupported",
            "params": {"name": "Athom RF", "band": "315"},
        }
        assert json.loads(run["sentence"]) == [
            "errors.test_rf_frequency_unsupported", {"name": "Athom RF", "band": "433.92"},
        ]

    def test_other_refusals_keep_their_own_sentence(self, run):
        assert run["keys"][1] == {"key": "errors.rf_frequency_unsupported"}
        assert run["keys"][2] == {"key": "errors.rf_no_frequency"}
        assert run["keys"][3] == {"key": "errors.wrong_medium_code"}

    def test_an_error_that_is_not_a_refusal_is_none(self, run):
        assert run["keys"][4:] == [None, None]

    def test_every_language_says_it_with_both_values(self):
        for path in (SRC / "locales").glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            for key in ("errors.test_rf_frequency_unsupported", "errors.wrong_medium_code"):
                assert data.get(key), (path.name, key)
            text = data["errors.test_rf_frequency_unsupported"]
            assert "{name}" in text and "{band}" in text, path.name
            assert "—" not in text, path.name
        en = json.loads((SRC / "locales" / "en.json").read_text(encoding="utf-8"))
        assert en["errors.test_rf_frequency_unsupported"] == (
            "{name} can't send {band} MHz; choose another transmitter."
        )

    @pytest.mark.parametrize("name", ["ir-signal-monitor.ts", "ir-clips.ts"])
    def test_the_sniffer_and_the_clipper_say_it_at_the_bottom(self, name):
        flat = _flat(name)
        assert "testRefusal(r.reason, this._emitterName(emitters[i]), band)" in flat
        # The refusal goes to the toast and the row keeps its Test button.
        refused = flat.split("if (refused) {", 1)[1].split("}", 1)[0]
        assert "this._showRefusal(refused);" in refused
        assert "this._testingSignalId = null;" in refused
        assert "return;" in refused
        assert "this._testResult = refused" not in flat
        assert '<div class="bottom-toast" role="status">${this._refusalToast}</div>' in flat
        assert "bottomToastStyles," in flat

