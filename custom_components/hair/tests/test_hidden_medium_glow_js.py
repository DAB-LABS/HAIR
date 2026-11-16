"""A switched-off medium's glyph rings and keeps a dot when a signal of
that medium arrives, exactly as the Sniffer's eye does for a hidden
remote (owner, 2026-11-16 13:08 and 13:11 PT; ruled at 13:40 PT: the
Sniffer and the Remotes header, not the Devices header; a hidden remote
of a hidden medium rings the eye only).

One behaviour, in hidden-activity.ts, held by the eye, the Sniffer's IR
and RF glyphs and the Remotes header's IR and RF glyphs. The rules run
under node (skipped without the toolchain); the source pins run
everywhere.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

COMPONENT = Path(__file__).parent.parent
FRONTEND = COMPONENT / "frontend"
SRC = FRONTEND / "src"
TSC = FRONTEND / "node_modules" / ".bin" / "tsc"

TOOLCHAIN_MISSING = not TSC.exists() or shutil.which("node") is None

DRIVER = r"""
import { hiddenMedium } from "./media-filter.js";
import { afterPing, afterLook } from "./rule.js";

const both = { ir: true, rf: true };
const irOff = { ir: false, rf: true };
const rfOff = { ir: true, rf: false };
const none = { ir: false, rf: false };
const sniffer = { ir: false, rf: true, hidden: false };
console.log(JSON.stringify({
    shown: [hiddenMedium(both, "ir"), hiddenMedium(both, "rf")],
    irOff: [hiddenMedium(irOff, "ir"), hiddenMedium(irOff, "rf")],
    rfOff: [hiddenMedium(rfOff, "ir"), hiddenMedium(rfOff, "rf")],
    none: [hiddenMedium(none, "ir"), hiddenMedium(none, "rf")],
    noMediumIsInfrared: [hiddenMedium(irOff, undefined), hiddenMedium(irOff, null)],
    sniffer: hiddenMedium(sniffer, "ir"),
    ping: afterPing({ glow: false, dot: false }),
    look: afterLook({ glow: true, dot: true }),
    lookQuiet: afterLook({ glow: false, dot: false }),
}));
"""


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("hiddenglow")
    # hidden-activity.ts imports lit for its styles; compile only the
    # pure rules.
    src = _read("hidden-activity.ts")
    start = src.index("export interface HiddenActivityState")
    end = src.index("export class HiddenActivity")
    (out / "rule.ts").write_text(src[start:end], encoding="utf-8")
    subprocess.run(
        [
            str(TSC), "src/media-filter.ts", str(out / "rule.ts"),
            "--module", "esnext", "--target", "es2022", "--moduleResolution", "bundler",
            "--skipLibCheck", "--outDir", str(out),
        ],
        cwd=FRONTEND, check=True, capture_output=True, timeout=180,
    )
    if not (out / "rule.js").exists():
        # tsc keeps the common root: the two inputs land in subfolders.
        for found in out.rglob("*.js"):
            found.replace(out / found.name)
    (out / "driver.mjs").write_text(DRIVER, encoding="utf-8")
    result = subprocess.run(["node", str(out / "driver.mjs")], check=True,
                            capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


class TestTheRule:
    def test_a_shown_medium_never_rings(self, run):
        assert run["shown"] == [None, None]

    def test_only_the_switched_off_medium_rings(self, run):
        assert run["irOff"] == ["ir", None]
        assert run["rfOff"] == [None, "rf"]
        assert run["none"] == ["ir", "rf"]

    def test_no_medium_is_infrared(self, run):
        assert run["noMediumIsInfrared"] == ["ir", "ir"]

    def test_the_sniffers_show_works_too(self, run):
        assert run["sniffer"] == "ir"

    def test_an_arrival_rings_and_sets_the_dot_a_look_clears_the_dot(self, run):
        assert run["ping"] == {"glow": True, "dot": True}
        assert run["look"] == {"glow": True, "dot": False}
        assert run["lookQuiet"] == {"glow": False, "dot": False}


class TestOneBehaviour:
    def test_the_eye_and_both_glyphs_hold_the_shared_piece(self):
        monitor = _read("ir-signal-monitor.ts")
        assert "private readonly _hiddenRemotes = new HiddenActivity(this);" in monitor
        assert "ir: new HiddenActivity(this)," in monitor
        assert "rf: new HiddenActivity(this)," in monitor
        assert "hiddenActivityStyles, css`" in monitor
        # No copy of the ring left in the Sniffer.
        assert "@keyframes hidden-pulse" not in monitor
        assert ".hidden-dot {" not in monitor
        assert "_hiddenGlowTimer" not in monitor

    def test_every_press_rings_again(self):
        src = " ".join(_read("hidden-activity.ts").split())
        body = src.split("ping(): void {", 1)[1].split("clearDot(): void {", 1)[0]
        assert body.index("this.glow = false;") < body.index("requestAnimationFrame(")
        assert body.count("requestAnimationFrame(") == 2
        assert "HIDDEN_GLOW_HOLD_MS);" in body
        assert "export const HIDDEN_GLOW_HOLD_MS = 3800;" in src

    def test_the_colour_is_the_themes_and_no_fixed_one(self):
        styles = _read("hidden-activity.ts").split("export const hiddenActivityStyles", 1)[1]
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", styles)
        assert "rgba(" not in styles
        assert "var(--primary-color)" in styles

    def test_reduced_motion_is_kept(self):
        styles = _read("hidden-activity.ts")
        assert "@media (prefers-reduced-motion: reduce)" in styles
        assert ".show-glyph.hidden-glow .hair-proto" in styles


class TestTheSniffer:
    def _live(self) -> str:
        text = _read("ir-signal-monitor.ts")
        return text.split("private _onLiveSignal(ev: UnknownSignalEvent): void {", 1)[1].split(
            "const now = new Date().toISOString();", 1
        )[0]

    def test_a_signal_of_a_switched_off_medium_rings_its_glyph(self):
        live = self._live()
        assert "const hidden = hiddenMedium(this._show, ev.medium);" in live
        assert "if (hidden) this._hiddenMedia[hidden].ping();" in live

    def test_a_mirror_push_never_rings(self):
        live = self._live()
        assert live.index("if (ev.device_fingerprint === MIRROR_DEVICE_FP) return;") < live.index(
            "hiddenMedium("
        )

    def test_a_hidden_remote_rings_the_eye_only(self):
        text = _read("ir-signal-monitor.ts")
        handler = text.split("private _onHiddenActivity(): void {", 1)[1].split("}", 1)[0]
        assert handler.strip() == "this._hiddenRemotes.ping();"

    def test_showing_a_medium_again_clears_its_dot(self):
        text = _read("ir-signal-monitor.ts")
        toggle = text.split("private _toggleShow(kind: keyof SnifferShow): void {", 1)[1]
        toggle = toggle.split("\n    }\n", 1)[0]
        assert "if (this._show[kind]) this._hiddenMedia[kind].clearDot();" in toggle
        assert "this._hiddenRemotes.clearDot();" in toggle

    def test_each_glyph_wears_its_own_ring_and_dot(self):
        text = _read("ir-signal-monitor.ts")
        glyphs = text.split("private _renderShowGlyphs() {", 1)[1].split("    render() {", 1)[0]
        holder = 'g.kind === "hidden" ? this._hiddenRemotes : this._hiddenMedia[g.kind];'
        assert f"const activity = {holder}" in glyphs
        assert '${activity.glow ? "hidden-glow" : ""}' in glyphs
        dot = '<span class="hidden-dot" aria-hidden="true"></span>'
        assert f"${{activity.dot ? html`{dot}` : nothing}}" in glyphs


class TestTheRemotesHeader:
    def _list(self) -> str:
        return _read("ir-device-list.ts")

    def test_a_fire_on_a_hidden_medium_remote_rings_its_glyph(self):
        text = self._list()
        ring = text.split("private _ringHiddenRemoteMedium(triggerId: string): void {", 1)[1]
        ring = ring.split("\n    }\n", 1)[0]
        assert "if (!trigger?.trigger_remote_id) return;" in ring
        assert "hiddenMedium(this._mediaShow.remotes, trigger.medium)" in ring
        assert "this._hiddenRemoteMedia[hidden].ping();" in ring

    def test_only_a_real_fire_rings(self):
        # A matrix Remote's heard state and any other kind return first.
        text = self._list()
        handler = text.split("(ev: TriggerFiredEvent) => {", 1)[1]
        assert handler.index("if (ev.kind) return;") < handler.index(
            "this._ringHiddenRemoteMedium(ev.trigger_id);"
        )

    def test_the_devices_header_does_not_ring(self):
        text = self._list()
        glyphs = text.split("private _renderMediaGlyphs(section: HomeSection) {", 1)[1]
        glyphs = glyphs.split("\n    }\n", 1)[0]
        holder = 'section === "remotes" ? this._hiddenRemoteMedia[g.kind] : null;'
        assert f"const activity = {holder}" in glyphs

    def test_showing_a_medium_again_clears_its_dot(self):
        text = self._list()
        head = "private _toggleMedia(section: HomeSection, kind: keyof MediaShow): void {"
        toggle = text.split(head, 1)[1].split("\n    }\n", 1)[0]
        clear = 'if (section === "remotes" && show[kind]) '
        assert clear + "this._hiddenRemoteMedia[kind].clearDot();" in toggle

    def test_the_header_loads_the_shared_look(self):
        assert "        hiddenActivityStyles,\n" in self._list()
