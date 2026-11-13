"""Where the Candy Drawer opens, actually executed.

``candy-surface.ts`` holds the pure half of the pop-out: whether the drawer
opens in a window of its own or as a dialog in the panel, the window's
features, and the dialog's box inside the panel's area. This transpiles it
and runs it under node, like ``test_candy_text_js.py``.

The node-driven tests are SKIPPED when the frontend toolchain is not
installed (CI runs pytest without node_modules). The source-level tests
at the bottom run everywhere.
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
import {
    chooseSurface, popupFeatures, overlayBox, dialogSize,
    CANDY_POPUP_NAME, CANDY_NARROW_PX,
} from "./candy-surface.js";

const vp = { width: 1400, height: 900 };
console.log(JSON.stringify({
    name: CANDY_POPUP_NAME,
    narrow: CANDY_NARROW_PX,
    choose: {
        desktop: chooseSurface({ external: false, viewportWidth: 1400 }),
        app: chooseSurface({ external: true, viewportWidth: 1400 }),
        phone: chooseSurface({ external: false, viewportWidth: 390 }),
        edge: chooseSurface({ external: false, viewportWidth: 768 }),
        justWider: chooseSurface({ external: false, viewportWidth: 769 }),
    },
    features: popupFeatures(1920, 1080),
    smallScreen: popupFeatures(1280, 700),
    noScreen: popupFeatures(),
    overlay: {
        open: overlayBox({ left: 256, top: 0, width: 1144, height: 2000 }, vp),
        narrow: overlayBox({ left: 56, top: 0, width: 1344, height: 900 }, vp),
        hidden: overlayBox({ left: 0, top: 0, width: 1400, height: 900 }, vp),
        scrolled: overlayBox({ left: 256, top: -400, width: 1144, height: 2000 }, vp),
        missing: overlayBox(null, vp),
        empty: overlayBox({ left: 0, top: 0, width: 0, height: 0 }, vp),
    },
    size: {
        wide: dialogSize({ left: 256, top: 0, width: 1144, height: 900 }),
        roomy: dialogSize({ left: 0, top: 0, width: 2000, height: 1400 }),
        phone: dialogSize({ left: 0, top: 0, width: 390, height: 780 }),
    },
}));
"""


@pytest.fixture(scope="module")
def surface(tmp_path_factory):
    if TOOLCHAIN_MISSING:
        pytest.skip("frontend toolchain not installed (node_modules / node)")
    out = tmp_path_factory.mktemp("candysurfacejs")
    subprocess.run(
        [
            str(TSC), "src/candy-surface.ts",
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


class TestChoice:
    def test_a_window_of_its_own_on_a_desktop(self, surface):
        assert surface["choose"]["desktop"] == "popout"
        assert surface["choose"]["justWider"] == "popout"

    def test_the_dialog_in_the_companion_app_and_on_a_phone(self, surface):
        assert surface["choose"]["app"] == "dialog"
        assert surface["choose"]["phone"] == "dialog"
        assert surface["choose"]["edge"] == "dialog"
        assert surface["narrow"] == 768

    def test_one_window_by_name(self, surface):
        assert surface["name"] == "hair-candy"


class TestWindowFeatures:
    def test_about_720_by_900_and_resizable(self, surface):
        assert surface["features"] == (
            "popup=yes,width=720,height=900,resizable=yes,scrollbars=yes"
        )
        assert surface["noScreen"] == surface["features"]

    def test_kept_inside_a_small_screen(self, surface):
        assert "height=700" in surface["smallScreen"]
        assert "width=720" in surface["smallScreen"]


class TestDialogBox:
    def test_the_overlay_is_the_panel_area_not_the_viewport(self, surface):
        overlay = surface["overlay"]
        assert overlay["open"] == {"left": 256, "top": 0, "width": 1144, "height": 900}
        assert overlay["narrow"] == {"left": 56, "top": 0, "width": 1344, "height": 900}
        assert overlay["hidden"] == {"left": 0, "top": 0, "width": 1400, "height": 900}

    def test_a_scrolled_panel_still_covers_the_screen_below_its_top(self, surface):
        assert surface["overlay"]["scrolled"] == {
            "left": 256, "top": 0, "width": 1144, "height": 900,
        }

    def test_no_panel_means_the_viewport(self, surface):
        whole = {"left": 0, "top": 0, "width": 1400, "height": 900}
        assert surface["overlay"]["missing"] == whole
        assert surface["overlay"]["empty"] == whole

    def test_the_window_inside_it(self, surface):
        assert surface["size"]["wide"] == {"width": 1096, "height": 820}
        assert surface["size"]["roomy"] == {"width": 1100, "height": 820}
        assert surface["size"]["phone"] == {"width": 390, "height": 780}


# --- source level, runs everywhere ------------------------------------------


class TestSource:
    def test_the_window_opens_from_the_click_before_any_await(self):
        mirror = (SRC / "ir-mirror.ts").read_text(encoding="utf-8")
        handler = mirror[mirror.index("private _openCandy = "):]
        handler = handler[: handler.index("};")]
        assert "await" not in handler
        assert "openCandyPopout(" in handler
        assert "this._candyOpen = true" in handler

    def test_the_pop_out_carries_no_token_and_no_new_door(self):
        controller = (SRC / "candy-controller.ts").read_text(encoding="utf-8")
        console = (SRC / "candy-console.ts").read_text(encoding="utf-8")
        feed = (SRC / "candy-feed.ts").read_text(encoding="utf-8")
        for source in (controller, console, feed):
            assert "access_token" not in source
            assert "localStorage" not in source and "sessionStorage" not in source
            assert "postMessage" not in source
        # The pop-out is a blank window rendered from the panel's code,
        # and its events come over the panel's own connection.
        assert 'window.open(\n        "",' in controller
        assert "new CandyFeed(opts.api," in controller
        assert "this.api\n            .subscribeCandy(" in feed

    def test_the_console_is_not_a_custom_element(self):
        console = (SRC / "candy-console.ts").read_text(encoding="utf-8")
        assert "customElement" not in console
        assert "LitElement" not in console
        assert "adoptedStyleSheets" not in console
