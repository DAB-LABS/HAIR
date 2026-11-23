"""The panel side of a typed Remote's state source.

- One Power section for every settings dialog: the Device's fields
  moved into ir-power-source-section.ts, and both dialogs use it.
- The Remote's settings get the Power card only for a typed Remote whose
  type has power, and Save only with it.
- The Remote's words say "press" where the Device's say "send".
- Nothing copies a power source between a Device and its Remote.

Source pins; the dialogs are Lit elements with no node driver.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.hair.remote_state import REMOTE_SETTINGS_COPIED

COMPONENT = Path(__file__).parent.parent
SRC = COMPONENT / "frontend" / "src"
LOCALES = SRC / "locales"


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _method(text: str, name: str) -> str:
    body = text[text.index(name):]
    return body[: body.index("\n    }\n")]


REMOTE = "ir-trigger-remote-settings-dialog.ts"
DEVICE = "ir-device-settings-dialog.ts"
POWER = "ir-power-source-section.ts"


class TestOnePowerSection:
    @pytest.mark.parametrize("name", [DEVICE, REMOTE])
    def test_both_dialogs_use_the_shared_section(self, name):
        text = _read(name)
        assert "<ir-power-source-section" in text
        assert ".source=" in text
        assert "@power-source-change=${() => this.requestUpdate()}" in text
        # No second copy of the picker.
        for private in ("_renderSourceField", "_pickerEvent", "stateSourceCandidates"):
            assert private not in text, private

    def test_the_section_owns_the_picker_and_the_rules(self):
        text = _read(POWER)
        for method in (
            "private _renderSourceField",
            "private _renderSourcePanel",
            "private _pickerEvent",
            "get validationError()",
            "patch(): PowerSource",
            "get summary(): string",
        ):
            assert method in text, method
        assert '@customElement("ir-power-source-section")' in text

    def test_the_dialogs_save_through_it(self):
        device = _method(_read(DEVICE), "private async _save")
        assert "Object.assign(patch, this._power.patch());" in device
        remote = _method(_read(REMOTE), "private async _save")
        assert "this.api.setTriggerRemotePower(this.remote.id, power.patch())" in remote

    def test_the_section_inherits_the_accent(self):
        """The element takes the card rules but not the :host accent, so
        the dialog's light or dark value reaches it."""
        text = _read(POWER)
        assert "settingsSectionStyles," in text
        assert "sectionAccentHost" not in text
        for name in (DEVICE, REMOTE):
            assert "sectionAccentHost," in _read(name), name


class TestTheRemotesDialog:
    def test_the_power_card_shows_for_a_remote_that_can_use_it(self):
        text = _read(REMOTE)
        assert "return this.remote.power_eligible === true;" in _method(
            text, "private get _hasPower()"
        )
        assert 'class="card card-power ${this._powerOpen ? "open" : ""}"' in text
        assert "?hidden=${!this._hasPower}" in text

    def test_save_comes_with_the_power_card_only(self):
        text = _read(REMOTE)
        footer = text[text.index('<div class="dialog-actions">'):]
        footer = footer[: footer.index("</ha-dialog>")]
        assert footer.index("${this._hasPower") < footer.index('class="action-btn save-btn"')
        assert "?disabled=${this._busy || !!problem}" in footer

    def test_its_words_are_the_remotes(self):
        assert "                                  forRemote\n" in _read(REMOTE)
        text = _read(POWER)
        for key in (
            "devsettings.power_intro_remote",
            "devsettings.settle_help_remote",
            "devsettings.sum_power_none_remote",
        ):
            assert f'"{key}"' in text, key

    def test_a_save_refreshes_the_remotes(self):
        assert 'new CustomEvent("remote-power-changed", {' in _read(REMOTE)
        assert "@remote-power-changed=${this._onRemoteChanged}" in _read(
            "ha-panel-ir-devices.ts"
        )
        listing = _read("ir-device-list.ts")
        block = listing[listing.index("<ir-trigger-remote-settings-dialog"):]
        block = block[: block.index(".remote=")]
        assert ".api=${this.api}" in block and ".hass=${this.hass}" in block

    def test_the_door_and_the_types(self):
        api = _read("api.ts")
        call = api[api.index("setTriggerRemotePower("):]
        call = call[: call.index("\n    }\n")]
        assert '"hair/trigger-remote/set-power"' in call
        types = _read("types.ts")
        info = types[types.index("export interface TriggerRemoteInfo"):]
        info = info[: info.index("\n}\n")]
        for field in (
            "power_eligible: boolean;",
            "power_sensor_entity_id: string | null;",
            "power_settle_s: number | null;",
        ):
            assert field in info, field


class TestNoCopy:
    def test_make_a_device_copies_no_source(self):
        assert not [name for name in REMOTE_SETTINGS_COPIED if name.startswith("power_")]

    def test_make_a_remote_copies_no_source(self):
        source = (COMPONENT / "remote_state.py").read_text(encoding="utf-8")
        seed = source[source.index("def seed_from_device("):]
        seed = seed[: seed.index("\ndef ")]
        take = source[source.index("def _take_device_config("):]
        take = take[: take.index("\ndef ")]
        assert "power_" not in seed + take


NEW_KEYS = (
    "devsettings.power_intro_remote",
    "devsettings.settle_help_remote",
    "devsettings.sum_power_none_remote",
)


class TestTheWords:
    def test_english(self):
        en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        assert en["devsettings.power_intro_remote"] == (
            "A sensor tells HAIR the unit's real power state and overrides "
            "what it assumed from the last press it heard."
        )
        assert en["devsettings.settle_help_remote"] == (
            "How long after HAIR hears a Power press before the sensor can "
            "overrule it. At least the sensor's reporting interval. 0 turns it off."
        )
        assert en["devsettings.sum_power_none_remote"] == (
            "No source · state from the presses HAIR hears"
        )

    @pytest.mark.parametrize("path", sorted(LOCALES.glob("*.json")), ids=lambda p: p.stem)
    def test_every_locale(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in NEW_KEYS:
            assert data.get(key), key
            assert "—" not in data[key], key
            assert "{" not in data[key], key
