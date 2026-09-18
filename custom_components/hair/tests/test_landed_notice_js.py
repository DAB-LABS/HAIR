"""The multi-wig landing receipt, actually executed.

``_landedFromDrop`` used to return without a word when a drop filed
anything other than exactly one wig: four remotes went into the closet
and the panel said nothing at all. Item 1 splits that three ways, and
the part a person actually reads is one pure function.

The rest of the change is checked as source text, which is the house
tactic and is enough for "is the gate gone". The sentence is not: which
key it resolves to and what it does when the list is long are exactly
what a grep cannot see. So this transpiles ``api.ts`` with the repo's
own TypeScript and runs the helper under node, the way
``test_pluck_helpers_js.py`` already does for the two pluck helpers.

The node-driven tests are SKIPPED when the frontend toolchain is not
installed, for the same reason that module's are: CI runs pytest
without node_modules. The skip lives on the ``notices`` fixture, not
on the module, so the source-level tests below (the wiring in
``_refreshDevices``, the gate, the locale keys) run everywhere,
including CI.
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

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None

DRIVER = """
import { landedManyNotice } from "./api.js";
import { nextNotice } from "./notice-state.js";

// THE SEQUENCE A DROP ACTUALLY PRODUCES, run rather than described.
// The panel dispatches the notice and a device-changed together; the
// refetch that device-changed triggers resolves a round trip later and
// used to clear the notice on its way past. Each step below is one of
// the panel's own four call sites, in the order they fire.
async function dropSequence() {
    let notice = null;
    notice = nextNotice(notice, { kind: "landed", text: "4 wigs landed" });
    const afterLanding = notice;
    await new Promise((resolve) => setTimeout(resolve, 0));  // the round trip
    notice = nextNotice(notice, { kind: "refreshed" });
    const afterRefresh = notice;
    notice = nextNotice(notice, { kind: "dismissed" });
    const afterDismiss = notice;

    let second = nextNotice(null, { kind: "landed", text: "2 wigs landed" });
    second = nextNotice(second, { kind: "drop-failed" });
    return { afterLanding, afterRefresh, afterDismiss, afterNextDrop: second };
}

const sequence = await dropSequence();

console.log(JSON.stringify({
    sequence,
    two: landedManyNotice(["amp.wig.json", "tv.wig.json"], 2),
    four: landedManyNotice(
        ["a.wig.json", "b.wig.json", "c.wig.json", "d.wig.json"], 4),
    many: landedManyNotice(
        ["a.wig.json", "b.wig.json", "c.wig.json", "d.wig.json",
         "e.wig.json", "f.wig.json"], 6),
    no_names: landedManyNotice([], 3),
}));
"""


@pytest.fixture(scope="module")
def notices(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("landedjs")
    subprocess.run(
        [
            str(TSC), "src/api.ts", "src/notice-state.ts",
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


class TestLandedManyNotice:
    def test_it_names_every_wig_when_the_list_is_short(self, notices):
        assert notices["two"]["key"] == "wigs.upload_landed_many"
        assert notices["two"]["params"]["count"] == 2
        assert notices["two"]["params"]["names"] == "amp.wig.json, tv.wig.json"

    def test_four_names_still_fit(self, notices):
        assert notices["four"]["key"] == "wigs.upload_landed_many"
        assert notices["four"]["params"]["names"].count(",") == 3

    def test_a_long_list_is_capped_and_the_count_stays_exact(self, notices):
        many = notices["many"]
        assert many["key"] == "wigs.upload_landed_many_capped"
        assert many["params"]["count"] == 6
        assert many["params"]["rest"] == 2
        assert many["params"]["names"].count(",") == 3

    def test_a_count_with_no_names_still_says_how_many(self, notices):
        assert notices["no_names"]["params"]["count"] == 3
        assert notices["no_names"]["params"]["rest"] == 3


class TestTheNoticeOutlivesItsOwnRefetch:
    """The ordering, driven. The three source greps this replaces could
    not see it: they asserted the events are dispatched and the banner
    exists, and both were true while the banner lived for one round
    trip."""

    def test_the_notice_survives_the_refetch_the_drop_triggered(
        self, notices
    ):
        sequence = notices["sequence"]
        assert sequence["afterLanding"] == "4 wigs landed"
        assert sequence["afterRefresh"] == "4 wigs landed"

    def test_a_dismiss_ends_it(self, notices):
        assert notices["sequence"]["afterDismiss"] is None

    def test_the_next_drop_ends_it(self, notices):
        assert notices["sequence"]["afterNextDrop"] is None

    def test_the_panel_asks_the_rule_rather_than_assigning_null(self):
        """The wiring, which a run cannot see from outside the panel."""
        text = (SRC / "ha-panel-ir-devices.ts").read_text(encoding="utf-8")
        body = text[text.index("private async _refreshDevices"):]
        body = body[: body.index("\n    /**")]
        code = "\n".join(
            line for line in body.splitlines()
            if not line.strip().startswith("//")
        )
        assert "this._notice = null" not in code
        assert 'nextNotice(this._notice, { kind: "refreshed" })' in code
        assert text.count("nextNotice(") == 4  # landed, failed, dismissed, refreshed

    def test_the_banner_can_be_dismissed(self):
        text = (SRC / "ha-panel-ir-devices.ts").read_text(encoding="utf-8")
        assert "dismissable" in text
        assert "@alert-dismissed-clicked=" in text


class TestTheGateIsGone:
    """The source assertions, the house tactic."""

    def test_the_one_file_gate_is_gone(self):
        text = (SRC / "ir-device-list.ts").read_text(encoding="utf-8")
        assert "landed.length !== 1" not in text
        assert "landed.length === 1" in text
        assert "landed.length === 0" in text

    def test_every_locale_carries_the_three_keys(self):
        locales = sorted((SRC / "locales").glob("*.json"))
        assert len(locales) == 10
        for path in locales:
            data = json.loads(path.read_text(encoding="utf-8"))
            for key in (
                "wigs.upload_landed_many",
                "wigs.upload_landed_many_capped",
                "wigs.upload_landed_none",
            ):
                assert key in data, f"{path.name} is missing {key}"
            assert "{count}" in data["wigs.upload_landed_many"]
            assert "{names}" in data["wigs.upload_landed_many"]
            assert "{rest}" in data["wigs.upload_landed_many_capped"]
