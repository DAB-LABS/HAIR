"""The Power card's wake tick and its two groups (GH #323), pinned in the
source, so it runs without the frontend toolchain.

The tick shows only for a matrix whose file has an "on" code, and not
while "This device has one Power button" is ticked. The card is two
groups, "How the unit turns on" and "Power state", for a matrix device;
any other device shows the source alone, as before.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

SRC = Path(__file__).parent.parent / "frontend" / "src"
DIALOG = SRC / "ir-device-settings-dialog.ts"
LOCALES = sorted((SRC / "locales").glob("*.json"))
KEYS = (
    "devsettings.power_group_turns_on",
    "devsettings.power_group_state",
    "devsettings.wake_with_on_label",
    "devsettings.wake_with_on_help",
)


def _flat(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def _method(text: str, name: str) -> str:
    start = text.index(name)
    end = text.index("\n    }\n", start)
    return " ".join(text[start:end].split())


def test_the_tick_shows_only_with_an_on_code_and_no_power_button():
    shows = _method(DIALOG.read_text(encoding="utf-8"), "private _showsWakeWithOn()")
    assert "this.device.matrix?.has_on === true && !this._powerToggles" in shows


def test_absent_reads_as_ticked_and_it_saves_only_with_an_on_code():
    flat = _flat(DIALOG)
    assert "this._wakeWithOn = this.device.entity_config?.wake_with_on !== false;" in flat
    assert (
        "if (this.device.matrix?.has_on) { patch.wake_with_on = this._wakeWithOn; }"
        in flat
    )


def test_the_card_is_two_groups_in_order():
    card = _method(DIALOG.read_text(encoding="utf-8"), "private _renderPowerCard()")
    order = [
        't("devsettings.power_group_turns_on")',
        't("devsettings.power_toggles_label")',
        't("devsettings.wake_with_on_label")',
        't("devsettings.wake_with_on_help")',
        't("devsettings.power_group_state")',
        "<ir-power-source-section",
    ]
    positions = [card.index(piece) for piece in order]
    assert positions == sorted(positions)
    # The first group, and both headings, only for a matrix device.
    assert "const turnsOn = Boolean(this.device.matrix);" in card
    assert "<h3" not in card


def test_no_new_colour_values():
    flat = _flat(DIALOG)
    start = flat.index(".power-group-head {")
    block = flat[start:flat.index(".save-btn {", start)]
    assert "#" not in block and "rgb" not in block


@pytest.mark.parametrize("path", LOCALES, ids=lambda p: p.stem)
def test_every_locale_has_the_strings(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in KEYS:
        assert data[key].strip(), key


def test_the_english_label_is_the_owners_words_with_its_quotes():
    data = json.loads((SRC / "locales" / "en.json").read_text(encoding="utf-8"))
    assert data["devsettings.wake_with_on_label"] == (
        'Unit requires "power on" to wake from "off" state'
    )
    assert data["devsettings.wake_with_on_help"] == (
        "HAIR sends On first, then your mode or temperature."
    )
