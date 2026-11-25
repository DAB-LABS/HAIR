"""The "can't read" line under the Sniffer's pills.

When a radio receiver's window closes having heard a code HAIR couldn't
read, and nothing was filed, a muted line shows under the pills:

- one per receiver, its name first;
- from the radio subscription's item for a software window, from the
  capture row for a capture device;
- gone while that receiver's window is open again, or once dismissed for
  that window (a later window with its own count shows again);
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
import { unreadLines } from "./rule.js";

const rm4 = { receiver_entity_id: "rm4", name: "RM4 Pro", medium: "rf", software_window: false,
    unread_radio: 2, unread_window_opened_at: "T1" };
const cc = { receiver_entity_id: "cc", name: "CC1101", medium: "rf", software_window: true,
    unread_radio: 0 };
const ir = { receiver_entity_id: "ir", name: "IR", medium: "ir", software_window: false,
    unread_radio: 3, unread_window_opened_at: "T1" };
const quiet = { receiver_entity_id: "q", name: "Quiet", medium: "rf", software_window: false };
const items = { cc: { receiver_entity_id: "cc", unread_radio: 1, unread_window_opened_at: "T2" } };
const closed = () => false;
const keys = (lines) => lines.map((l) => l.key);
console.log(JSON.stringify({
    shown: unreadLines([rm4, cc, ir, quiet], items, closed, new Set()),
    open: keys(unreadLines([rm4, cc], items, (r) => r.receiver_entity_id === "rm4", new Set())),
    dismissed: keys(unreadLines([rm4, cc], items, closed, new Set(["rm4@T1"]))),
    nextWindow: keys(unreadLines([{ ...rm4, unread_window_opened_at: "T3" }], {}, closed,
                                 new Set(["rm4@T1"]))),
}));
"""


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("unreadline")
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
            {"receiver": "rm4", "name": "RM4 Pro", "key": "rm4@T1"},
            # A software window's count comes from its subscription item.
            {"receiver": "cc", "name": "CC1101", "key": "cc@T2"},
        ]

    def test_not_while_that_window_is_open(self, run):
        assert run["open"] == ["cc@T2"]

    def test_dismissed_for_that_window_only(self, run):
        assert run["dismissed"] == ["cc@T2"]
        assert run["nextWindow"] == ["rm4@T3"]


class TestTheLine:
    def test_it_renders_under_the_pills_muted(self):
        row = _read("ir-listen-row.ts")
        assert '<div class="unread" title=${t("listen.unread_radio_hint")}>' in row
        assert '${t("listen.unread_radio")}' in row
        assert "this._dismissed = new Set([...this._dismissed, line.key])" in row
        assert ".unread {" in row and "color: var(--secondary-text-color);" in row

    def test_a_phone_gets_the_hint_as_a_second_line(self):
        row = _read("ir-listen-row.ts")
        assert "@media (hover: none), (max-width: 600px) {" in row

    def test_the_fields(self):
        types = _read("types.ts")
        # The server's fields, on the capture row and the radio item.
        assert types.count("unread_radio: number;") == 2
        assert types.count("unread_window_opened_at: string | null;") == 2


class TestTheStrings:
    @pytest.mark.parametrize("path", sorted(LOCALES.glob("*.json")), ids=lambda p: p.stem)
    def test_every_language(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in ("listen.unread_radio", "listen.unread_radio_hint"):
            assert data.get(key), (path.name, key)
            assert "\u2014" not in data[key], (path.name, key)

    def test_the_english_as_approved(self):
        en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        assert en["listen.unread_radio"] == (
            "Heard a radio code HAIR can't read yet. It may change on every press."
        )
        assert en["listen.unread_radio_hint"] == (
            "Some remotes send a new code on every press. HAIR can't read all of those yet."
        )
