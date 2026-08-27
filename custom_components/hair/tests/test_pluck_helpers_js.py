"""The two pluck helpers, actually executed.

Everything else guarding this branch's frontend reads the TypeScript as
text, which is the house tactic and is enough for "is the gate gone".
It is not enough for the two pure functions the whole design leans on:
``anyPluckReadyNow`` decides whether a dialog offers Plucker at all, and
``pluckEmptyLines`` decides what an empty tab says. A grep can confirm
they are called; only running them confirms what they answer.

So this transpiles ``api.ts`` with the repo's own TypeScript and runs
the result under node. Both helpers are pure and import nothing but
types, which erase, so the emitted module stands alone.

SKIPPED when the frontend toolchain is not installed -- CI runs pytest
without node_modules (builds happen on the portal), and a test that
fails for want of a toolchain it never asked for is noise. It runs
wherever a build could run, which is where a frontend change is
actually being made.
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

DRIVER = """
import { anyPluckReadyNow, pluckEmptyLines } from "./api.js";

// Stands in for localize.ts's t(): same contract, including the
// fall-through-to-the-key behaviour the helper relies on to stay
// silent about a source it has no wording for.
const TABLE = {
    "pluck.empty.not_installed": "{vendor} is not set up here",
    "pluck.empty.source.broadlink": "BROADLINK LINE",
    "pluck.empty.source.tuya_local": "TUYA LINE",
};
const t = (key, subs) => {
    let s = TABLE[key] ?? key;
    for (const [k, v] of Object.entries(subs ?? {})) {
        s = s.split(`{${k}}`).join(String(v));
    }
    return s;
};

const source = (over) => ({
    integration: "broadlink",
    name: "Broadlink",
    mechanisms: ["storage"],
    loaded: false,
    ready: { storage: false },
    ...over,
});
const tuya = (over) => source({
    integration: "tuya_local",
    name: "Tuya Local",
    mechanisms: ["replay", "storage"],
    ready: { replay: false, storage: false },
    ...over,
});

console.log(JSON.stringify({
    ready_empty: anyPluckReadyNow([]),
    ready_nullish: anyPluckReadyNow(null),
    ready_nothing: anyPluckReadyNow([source({ loaded: true }), tuya({ loaded: true })]),
    ready_one_mechanism: anyPluckReadyNow([
        source({ loaded: true }),
        tuya({ loaded: true, ready: { replay: true, storage: false } }),
    ]),
    ready_not_installed_but_flagged: anyPluckReadyNow([
        source({ ready: { storage: true } }),
    ]),
    lines_not_installed: pluckEmptyLines([source()], t),
    lines_loaded_nothing_ready: pluckEmptyLines([source({ loaded: true })], t),
    lines_ready: pluckEmptyLines(
        [source({ loaded: true, ready: { storage: true } })], t),
    lines_partly_ready: pluckEmptyLines(
        [tuya({ loaded: true, ready: { replay: true, storage: false } })], t),
    lines_unknown_provider: pluckEmptyLines(
        [source({ integration: "zigbee_ir", name: "Zigbee IR", loaded: true })], t),
    lines_order: pluckEmptyLines(
        [source({ loaded: true }), tuya({ loaded: true })], t),
    lines_nullish: pluckEmptyLines(null, t),
}));
"""


@pytest.fixture(scope="module")
def helpers(tmp_path_factory):
    out = tmp_path_factory.mktemp("pluckjs")
    subprocess.run(
        [
            str(TSC), "src/api.ts",
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


class TestAnyPluckReadyNow:
    """The ACTION PICKER rule. A dialog offering a source for a new
    device must not offer a route with nothing behind it."""

    def test_nothing_at_all(self, helpers):
        assert helpers["ready_empty"] is False
        assert helpers["ready_nullish"] is False

    def test_installed_but_nothing_ready(self, helpers):
        """The reported bug, at the picker: the integrations are right
        there and there is still nothing to pluck."""
        assert helpers["ready_nothing"] is False

    def test_one_mechanism_on_one_source_is_enough(self, helpers):
        assert helpers["ready_one_mechanism"] is True

    def test_it_reads_ready_not_loaded(self, helpers):
        """Ready is the question. A source flagged ready while not
        loaded is a contradiction the backend will not produce, and
        this helper still answers on ready alone rather than
        second-guessing it."""
        assert helpers["ready_not_installed_but_flagged"] is True


class TestPluckEmptyLines:
    """What the empty card says, per source, in order."""

    def test_not_installed_gets_the_generic_line_with_its_name(self, helpers):
        assert helpers["lines_not_installed"] == ["Broadlink is not set up here"]

    def test_loaded_with_nothing_ready_gets_its_own_line(self, helpers):
        assert helpers["lines_loaded_nothing_ready"] == ["BROADLINK LINE"]

    def test_a_ready_source_says_nothing(self, helpers):
        """There is something to pluck from it, so the empty card is
        not the place to talk about it."""
        assert helpers["lines_ready"] == []

    def test_ready_anywhere_is_enough_to_stay_silent(self, helpers):
        """Tuya Local with replay live and storage empty is not a
        source anybody needs advice about."""
        assert helpers["lines_partly_ready"] == []

    def test_a_provider_with_no_wording_says_nothing(self, helpers):
        """Rather than printing pluck.empty.source.zigbee_ir at a
        user. A provider added later needs its key added with it."""
        assert helpers["lines_unknown_provider"] == []

    def test_one_line_per_source_in_the_order_given(self, helpers):
        assert helpers["lines_order"] == ["BROADLINK LINE", "TUYA LINE"]

    def test_no_sources_is_no_lines_not_a_crash(self, helpers):
        assert helpers["lines_nullish"] == []
