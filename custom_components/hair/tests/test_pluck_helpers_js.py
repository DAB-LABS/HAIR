"""The two pluck helpers, actually executed.

Everything else guarding this branch's frontend reads the TypeScript as
text, which is the house tactic and is enough for "is the gate gone".
It is not enough for the two pure functions the whole design leans on:
``anyPluckReadyNow`` decides whether a dialog offers Plucker at all, and
``pluckEmptyBlocks`` decides what an empty tab says -- including which
of up to four keys each source resolves to, which is the part a grep
cannot check at all. Only running them confirms what they answer.

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
import { anyPluckReadyNow, pluckEmptyBlocks } from "./api.js";

// Stands in for localize.ts's t(): same contract, including the
// fall-through-to-the-key behaviour the helper relies on to stay
// silent about a source it has no wording for.
const TABLE = {
    "pluck.empty.not_installed": "GENERIC NOT INSTALLED",
    "pluck.empty.source.broadlink": "BROADLINK TAB",
    "pluck.empty.source.broadlink_dialog": "BROADLINK DIALOG",
    "pluck.empty.source.tuya_local": "TUYA LOADED",
    "pluck.empty.source.tuya_local.not_installed": "TUYA NOT INSTALLED",
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
const stranger = (over) => source({
    integration: "zigbee_ir",
    name: "Zigbee IR",
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

    tab_loaded: pluckEmptyBlocks([source({ loaded: true })], t, "tab"),
    dialog_loaded: pluckEmptyBlocks([source({ loaded: true })], t, "dialog"),
    tab_loaded_tuya: pluckEmptyBlocks([tuya({ loaded: true })], t, "tab"),
    dialog_loaded_tuya: pluckEmptyBlocks([tuya({ loaded: true })], t, "dialog"),
    tuya_not_installed: pluckEmptyBlocks([tuya()], t, "tab"),
    broadlink_not_installed: pluckEmptyBlocks([source()], t, "tab"),
    stranger_not_installed: pluckEmptyBlocks([stranger()], t, "tab"),
    stranger_loaded: pluckEmptyBlocks([stranger({ loaded: true })], t, "tab"),
    ready_says_nothing: pluckEmptyBlocks(
        [source({ loaded: true, ready: { storage: true } })], t, "tab"),
    partly_ready_says_nothing: pluckEmptyBlocks(
        [tuya({ loaded: true, ready: { replay: true, storage: false } })],
        t, "tab"),
    order: pluckEmptyBlocks(
        [source({ loaded: true }), tuya({ loaded: true })], t, "tab"),
    nullish: pluckEmptyBlocks(null, t, "tab"),
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


class TestPluckEmptyBlocks:
    """What the empty card says, per source, in order.

    Each block is a name and a body: the name renders as a small label
    above, from the payload, so the body is a clean sentence with no
    brand prefix in any language.
    """

    def test_a_loaded_source_gets_its_own_body(self, helpers):
        assert helpers["tab_loaded"] == [
            {"integration": "broadlink", "name": "Broadlink",
             "body": "BROADLINK TAB"},
        ]

    def test_the_dialog_variant_wins_in_the_dialog(self, helpers):
        """Round two gave Broadlink a dialog wording ("this blaster"),
        which only makes sense where a blaster is being added."""
        assert helpers["dialog_loaded"][0]["body"] == "BROADLINK DIALOG"

    def test_a_source_with_no_dialog_variant_falls_back(self, helpers):
        """Tuya Local has one line for both places. The dialog asks for
        a variant, does not find one, and uses the neutral line rather
        than going silent."""
        assert helpers["tab_loaded_tuya"][0]["body"] == "TUYA LOADED"
        assert helpers["dialog_loaded_tuya"][0]["body"] == "TUYA LOADED"

    def test_a_per_source_not_installed_line_wins(self, helpers):
        assert helpers["tuya_not_installed"][0]["body"] == "TUYA NOT INSTALLED"

    def test_the_generic_line_covers_a_source_without_one(self, helpers):
        """Broadlink has no not-installed line of its own, so it gets
        the fallback -- which is exactly what the fallback is for."""
        assert helpers["broadlink_not_installed"][0]["body"] == (
            "GENERIC NOT INSTALLED"
        )

    def test_the_name_always_comes_from_the_payload(self, helpers):
        """Never from the string. This is what lets the bodies drop
        their brand prefixes without losing the name."""
        for key in ("tab_loaded", "tuya_not_installed",
                    "broadlink_not_installed"):
            block = helpers[key][0]
            assert block["name"] and block["name"] not in block["body"]

    def test_a_stranger_still_gets_the_generic_line(self, helpers):
        """A provider nobody wrote copy for is still worth offering."""
        assert helpers["stranger_not_installed"][0]["body"] == (
            "GENERIC NOT INSTALLED"
        )

    def test_a_loaded_stranger_says_nothing(self, helpers):
        """There is no honest generic sentence for "installed, and
        nothing to pluck": what would make something appear differs per
        integration, which is why these keys are per-source. Silence
        beats printing pluck.empty.source.zigbee_ir at somebody."""
        assert helpers["stranger_loaded"] == []

    def test_a_ready_source_says_nothing(self, helpers):
        assert helpers["ready_says_nothing"] == []

    def test_ready_anywhere_is_enough_to_stay_silent(self, helpers):
        assert helpers["partly_ready_says_nothing"] == []

    def test_one_block_per_source_in_the_order_given(self, helpers):
        assert [b["name"] for b in helpers["order"]] == [
            "Broadlink", "Tuya Local",
        ]

    def test_no_sources_is_no_blocks_not_a_crash(self, helpers):
        assert helpers["nullish"] == []
