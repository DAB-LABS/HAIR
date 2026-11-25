"""The "press it again" line under the Sniffer's pills.

When a radio receiver's window closes having heard a code HAIR could
read but couldn't tell what kind of remote sent it (two family shapes
fit, ``rf_family.fits_two_shapes``), with no clean code after it, a
muted line asks for the button again:

- one per receiver, its name first, from the same places as the
  "can't read" line;
- gone while that receiver's window is open, or once dismissed for that
  window, and never mixed up with a "can't read" line's dismissal;
- never for an infrared receiver.

The rules run under node (skipped without the toolchain); the source pins
run everywhere.
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
import { ambiguousLines, unreadLines } from "./rule.js";

const rm4 = { receiver_entity_id: "rm4", name: "RM4 Pro", medium: "rf", software_window: false,
    ambiguous_radio: 1, ambiguous_window_opened_at: "T1", unread_radio: 0 };
const cc = { receiver_entity_id: "cc", name: "CC1101", medium: "rf", software_window: true,
    ambiguous_radio: 0 };
const ir = { receiver_entity_id: "ir", name: "IR", medium: "ir", software_window: false,
    ambiguous_radio: 3, ambiguous_window_opened_at: "T1" };
const quiet = { receiver_entity_id: "q", name: "Quiet", medium: "rf", software_window: false };
const items = {
    cc: { receiver_entity_id: "cc", ambiguous_radio: 2, ambiguous_window_opened_at: "T2" },
};
const closed = () => false;
const keys = (lines) => lines.map((l) => l.key);
console.log(JSON.stringify({
    shown: ambiguousLines([rm4, cc, ir, quiet], items, closed, new Set()),
    open: keys(ambiguousLines([rm4, cc], items, (r) => r.receiver_entity_id === "rm4", new Set())),
    dismissed: keys(ambiguousLines([rm4, cc], items, closed, new Set(["again:rm4@T1"]))),
    unreadDismissal: keys(ambiguousLines([rm4], {}, closed, new Set(["rm4@T1"]))),
    unreadOnly: keys(unreadLines([rm4], {}, closed, new Set())),
}));
"""


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("againline")
    src = _read("ir-listen-row.ts")
    start = src.index('/** The "can\'t read" lines')
    rules = src[start:src.index("/** What the radio receivers'")]
    head = "type CaptureReceiverRow = any; type RfReceiverItem = any;\n"
    (out / "rule.ts").write_text(head + rules, encoding="utf-8")
    subprocess.run(
        [
            str(TSC), str(out / "rule.ts"),
            "--module", "esnext", "--target", "es2022", "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    (out / "driver.mjs").write_text(DRIVER, encoding="utf-8")
    result = subprocess.run(["node", str(out / "driver.mjs")], check=True,
                            capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


class TestWhenItShows:
    def test_radio_receivers_with_a_count_only(self, run):
        assert run["shown"] == [
            {"receiver": "rm4", "name": "RM4 Pro", "key": "again:rm4@T1"},
            {"receiver": "cc", "name": "CC1101", "key": "again:cc@T2"},
        ]

    def test_not_while_that_window_is_open(self, run):
        assert run["open"] == ["again:cc@T2"]

    def test_dismissed_on_its_own(self, run):
        assert run["dismissed"] == ["again:cc@T2"]
        # Dismissing a "can't read" line for the window doesn't hide it.
        assert run["unreadDismissal"] == ["again:rm4@T1"]

    def test_it_is_not_a_cant_read_line(self, run):
        assert run["unreadOnly"] == []


class TestTheLine:
    def test_it_renders_with_the_cant_read_lines_style(self):
        row = _read("ir-listen-row.ts")
        assert '<div class="unread again">' in row
        assert '${t("listen.ambiguous_radio")}' in row
        assert "const again = ambiguousLines(rows, this._items, isOpen, this._dismissed);" in row

    def test_the_fields(self):
        types = _read("types.ts")
        assert types.count("ambiguous_radio: number;") == 2
        assert types.count("ambiguous_window_opened_at: string | null;") == 2


class TestTheStrings:
    @pytest.mark.parametrize("path", sorted(LOCALES.glob("*.json")), ids=lambda p: p.stem)
    def test_every_language(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("listen.ambiguous_radio"), path.name
        assert "\u2014" not in data["listen.ambiguous_radio"], path.name

    def test_the_english_as_approved(self):
        en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        assert en["listen.ambiguous_radio"] == (
            "HAIR heard that but couldn't tell what kind of remote it is. "
            "Press the button again."
        )
