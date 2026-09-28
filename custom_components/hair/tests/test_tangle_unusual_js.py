"""The Unusual card's panel rules, executed and pinned (GH #177).

Two halves, in the house style. The bucketing and the keep rule are
pure functions in ``ir-tangle-buckets.ts``, so they are transpiled with
the repo's own TypeScript and run under node: which card a row lands
on, and when "It Works, Keep It" opens, are exactly what a grep cannot
see. The wiring around them (the keep door, the Fix popup, the tooltip,
the section's send record, the save dialog's count, the locale keys) is
checked as source text, which runs everywhere, CI included.

The node-driven tests SKIP when the frontend toolchain is not
installed, as the other ``*_js`` modules do.
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
LOCALES = SRC / "locales"

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None

DRIVER = """
import {
    bucketDecide,
    bucketFixRows,
    bucketListenRows,
    bucketUnusualRows,
    blockingCount,
    keepEnabled,
    sentKey,
} from "./ir-tangle-buckets.js";

function row(id, extra = {}) {
    return {
        id, target: { kind: "command", key: id, command_id: id },
        classes: ["frame-shape"], findings: [], pronto: "0000", digest: "d-" + id,
        has_donor: false, donor: null, donor_abstain: null, verdict: null,
        ...extra,
    };
}

const rows = [
    row("odd", { unusual: true }),
    row("malformed", { classes: ["frame-shape", "malformed"], unusual: false }),
    row("donor", { classes: ["stray-burst"], has_donor: true, unusual: false }),
    row("pairA", { classes: ["duplicate-labels"], unusual: false }),
    row("pairB", { classes: ["duplicate-labels"], unusual: true }),
    row("planned", { classes: ["field-mismatch"], unusual: false }),
    row("older", { classes: ["frame-shape"] }),
];
const listing = {
    rows,
    clusters: [
        { id: "c1", rule: "identical-bytes", cause: "", mechanic: "recapture",
          members: ["pairA", "pairB"] },
    ],
    advisories: [], attested: [], matrix: false, coverage: {},
    protocol: null, field_tier: "no-lattice", candidate_sources: [],
    unusual_classes: ["frame-shape", "stray-burst", "bypass-with-dittos", "ramp-dittos"],
};
const ids = (list) => list.map((r) => r.id);

const odd = rows[0];
const sent = new Set();
const before = keepEnabled(odd, sent);
sent.add(sentKey(odd));
const after = keepEnabled(odd, sent);
const moved = { ...odd, digest: "d-new" };
const afterBytesMoved = keepEnabled(moved, sent);
const otherRow = keepEnabled(rows[1], sent);

console.log(JSON.stringify({
    unusual: ids(bucketUnusualRows(listing)),
    fix: ids(bucketFixRows(listing)),
    listen: ids(bucketListenRows(listing)),
    listenPlanned: ids(bucketListenRows(listing, new Set(["planned"]))),
    decide: bucketDecide(listing).pairs.map((p) => ids(p.rows)),
    blocking: blockingCount(listing),
    keep: { before, after, afterBytesMoved, otherRow },
}));
"""


@pytest.fixture(scope="module")
def ran(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("unusualjs")
    subprocess.run(
        [
            str(TSC), "src/ir-tangle-buckets.ts",
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


class TestTheBucketsRun:
    def test_an_unusual_row_lands_on_unusual_and_nowhere_else(self, ran):
        assert ran["unusual"] == ["odd"]
        assert "odd" not in ran["listen"]
        assert "odd" not in ran["fix"]

    def test_the_stricter_bucket_keeps_its_row(self, ran):
        """frame-shape plus malformed stays in LISTEN, as today."""
        assert "malformed" in ran["listen"]

    def test_a_row_with_a_candidate_stays_in_fix(self, ran):
        assert ran["fix"] == ["donor"]

    def test_decide_wins_over_unusual(self, ran):
        """A pair member is DECIDE's, whatever else is said about it, so
        Keep Both keeps working on the pair it always did."""
        assert ran["decide"] == [["pairA", "pairB"]]
        assert "pairB" not in ran["unusual"]

    def test_an_older_backend_changes_nothing(self, ran):
        """No `unusual` flag at all reads as not unusual: the row keeps
        the LISTEN bucket it had before this card existed."""
        assert "older" in ran["listen"]

    def test_planned_rows_still_leave_listen(self, ran):
        assert "planned" in ran["listen"]
        assert "planned" not in ran["listenPlanned"]

    def test_only_rows_outside_unusual_block_a_fit(self, ran):
        assert ran["blocking"] == 5


class TestTheKeepRule:
    def test_disabled_before_a_send(self, ran):
        assert ran["keep"]["before"] is False

    def test_enabled_after_a_send(self, ran):
        assert ran["keep"]["after"] is True

    def test_new_bytes_need_a_new_send(self, ran):
        assert ran["keep"]["afterBytesMoved"] is False

    def test_a_send_counts_for_its_own_row_only(self, ran):
        assert ran["keep"]["otherRow"] is False


# --- source-level pins (run everywhere) ------------------------------------


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


class TestTheWiring:
    def test_the_class_list_is_not_copied_into_the_panel(self):
        """One list, on the server. The files that decide the Unusual
        bucket read the row's flag and never name a class.
        (ir-tangle-reason.ts names every check for its reason keys,
        which is a different list with a different job.)"""
        for name in ("ir-tangle-buckets.ts", "ir-tangle-unusual.ts",
                     "ir-tangle-section.ts", "ir-save-perfect-dialog.ts"):
            text = _read(name)
            for check in ("frame-shape", "stray-burst",
                          "bypass-with-dittos", "ramp-dittos"):
                assert f'"{check}"' not in text, (name, check)

    def test_keep_calls_the_existing_door_with_tested_true(self):
        body = _read("ir-tangle-unusual.ts")
        assert "this.api.tangleKeep(this.deviceId, row.id, true)" in body

    def test_keep_is_gated_on_the_send_record(self):
        body = _read("ir-tangle-unusual.ts")
        assert "keepEnabled(row, this.sent)" in body
        assert "?disabled=${!canKeep || busy}" in body
        assert 't("tangles.unusual_keep_hint")' in body

    def test_send_sends_the_rows_own_bytes(self):
        body = _read("ir-tangle-unusual.ts")
        assert "tangleTestSend(this.deviceId, row.pronto)" in body
        assert "if (result.sent)" in body

    def test_fix_opens_the_same_popup_listen_opens(self):
        """Same editor, same tangle bindings, attribute for attribute."""
        def bindings(name: str) -> list[str]:
            text = _read(name)
            block = text[text.index("<ir-signal-editor"):
                         text.index("></ir-signal-editor>")]
            return sorted(re.findall(r"\.(\w+)=\$\{", block))

        assert bindings("ir-tangle-unusual.ts") == bindings(
            "ir-tangle-listen.ts")

    def test_the_section_holds_the_send_record(self):
        body = _read("ir-tangle-section.ts")
        assert "@tangle-unusual-sent=${this._handleUnusualSent}" in body
        assert ".sent=${this._sent}" in body
        # Cleared with everything else that belongs to a device.
        forget = body[body.index("private _forget()"):]
        forget = forget[:forget.index("\n    }\n")]
        assert "this._sent = new Set();" in forget

    def test_the_save_dialog_counts_only_blocking_rows(self):
        body = _read("ir-save-perfect-dialog.ts")
        assert "this._openTangles = blockingCount(listing);" in body
        assert "this._openTangles = listing.rows.length;" not in body

    def test_the_superseded_ruling_is_recorded_as_superseded(self):
        section = _read("ir-tangle-section.ts")
        assert "omit it entirely" not in section
        assert "SUPERSEDED (owner ruled 2026-09-27, GH Discussion #177)" in (
            section)
        buckets = _read("ir-tangle-buckets.ts")
        decide_doc = buckets[:buckets.index("export function bucketDecide")]
        assert "superseded" in decide_doc


class TestTheCopy:
    KEYS = (
        "tangles.card_unusual.one",
        "tangles.card_unusual.other",
        "tangles.unusual_keep",
        "tangles.unusual_keep_hint",
    )

    def test_the_owner_s_sentence_verbatim(self):
        en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        assert en["tangles.card_unusual.other"] == (
            "Unusual: {count} codes are shaped differently from the rest "
            "of this remote. If they work on your device, keep them.")
        assert en["tangles.unusual_keep"] == "It Works, Keep It"

    def test_every_locale_carries_every_key(self):
        for path in sorted(LOCALES.glob("*.json")):
            strings = json.loads(path.read_text(encoding="utf-8"))
            for key in self.KEYS:
                assert strings.get(key), f"{path.name}: {key}"
            assert "{count}" in strings["tangles.card_unusual.other"]

    def test_polish_and_russian_carry_their_plural_forms(self):
        for lang in ("pl", "ru"):
            strings = json.loads(
                (LOCALES / f"{lang}.json").read_text(encoding="utf-8"))
            for form in ("few", "many"):
                assert strings.get(f"tangles.card_unusual.{form}"), lang
