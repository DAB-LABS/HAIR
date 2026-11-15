"""Coming back to the Devices tab reloads the Remotes as well as the
devices (owner, 2026-11-14, on VM999).

A Remote made with Make a Remote from the Sniffer, the Clipper, the
Plucker or the Closet fires ``remote-created`` inside that tab, and the
panel only listens for it on the Devices tab's list. Every way back to
the Devices tab goes through ``_switchTab``, so that is where both lists
reload. Pinned in the source, the house style for panel wiring.
"""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).parent.parent / "frontend" / "src"


def _panel() -> str:
    return (SRC / "ha-panel-ir-devices.ts").read_text(encoding="utf-8")


def _switch_tab() -> str:
    src = _panel()
    start = src.index("    private _switchTab(tab: PanelTab): void {")
    end = re.search(r"\n    [^\s}]", src[start + 10:])
    return src[start : start + 10 + end.start()] if end else src[start:]


def test_the_devices_tab_reloads_both_lists():
    body = " ".join(_switch_tab().split())
    assert (
        'if (tab === "devices") { '
    ) in body
    devices = body.index("void this._refreshDevices();")
    remotes = body.index("void this._refreshTriggerRemotes();")
    assert devices < remotes


def test_every_way_back_goes_through_switch_tab():
    src = _panel()
    # Only _switchTab assigns the active tab, so its reload covers
    # navigate-device from every other tab and the tab bar alike.
    assert len(re.findall(r"this\._activeTab = ", src)) == 1
    nav = src.split("private _onNavigateDevice", 1)[1].split("\n    }", 1)[0]
    assert 'this._switchTab("devices");' in nav
