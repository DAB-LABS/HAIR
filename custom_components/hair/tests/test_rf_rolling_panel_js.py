"""The rolling-code guard's panel half: HAIR never sends a rolling code.

- The server's refusal code has a sentence, in every language.
- The Assign dialog says a rolling row can't be a command before the
  press, from the row's ``rf_rolling``, and keeps Assign off.
- The wording promises nothing about triggers, matching the server's own
  message.

Source pins and locale checks; the server half is test_rf_rolling_guard.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

COMPONENT = Path(__file__).parent.parent
SRC = COMPONENT / "frontend" / "src"
LOCALES = SRC / "locales"
KEYS = ("errors.rf_rolling_code", "assign.rolling_code")


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _locale(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TestTheRefusal:
    def test_the_code_has_a_sentence(self):
        errors = _read("rf-errors.ts")
        assert 'export const RF_ROLLING_CODE = "rf_rolling_code";' in errors
        assert '[RF_ROLLING_CODE]: "errors.rf_rolling_code",' in errors

    def test_the_server_uses_the_same_code(self):
        from custom_components.hair.const import RF_ROLLING_CODE

        assert f'"{RF_ROLLING_CODE}"' in _read("rf-errors.ts")

    def test_the_english_matches_the_servers_meaning(self):
        from custom_components.hair.const import RF_ROLLING_CODE_MESSAGE

        en = _locale(LOCALES / "en.json")
        assert en["errors.rf_rolling_code"] == RF_ROLLING_CODE_MESSAGE
        assert en["assign.rolling_code"] == (
            "Rolling code: HAIR never sends it, so it can't be a device command."
        )


class TestTheAssignDialog:
    def _dialog(self) -> str:
        return _read("ir-assign-signal-dialog.ts")

    def test_it_reads_the_rows_rolling_family(self):
        text = self._dialog()
        assert "return !!this.signal?.rf_rolling;" in text
        assert 'rf_rolling?: "keeloq" | "somfy_rts" | null;' in _read("types.ts")

    def test_the_line_shows_before_the_tabs(self):
        text = self._dialog()
        render = text[text.index("<ha-dialog"):]
        assert render.index('t("assign.rolling_code")') < render.index('<div class="mode-tabs">')
        assert "${this._rolling" in render

    def test_assign_stays_off(self):
        text = self._dialog()
        button = text.split('class="action-btn wide assign-btn"', 1)[1].split(">", 1)[0]
        assert "?disabled=${this._busy || this._rolling}" in button

    def test_a_refusal_reads_in_the_persons_language(self):
        text = self._dialog()
        assert 'import { sendRefusal } from "./rf-errors.js";' in text
        assert "this._error = sendRefusal(err) ?? (err as Error).message;" in text


class TestTheStrings:
    @pytest.mark.parametrize("path", sorted(LOCALES.glob("*.json")), ids=lambda p: p.stem)
    def test_every_language_has_both(self, path):
        data = _locale(path)
        for key in KEYS:
            assert data.get(key), (path.name, key)
            assert "—" not in data[key], (path.name, key)

    def test_no_trigger_promise_yet(self):
        # Option C: a trigger on a rolling code won't fire again until
        # rolling-code triggers ship, so no language says it can be one.
        en = _locale(LOCALES / "en.json")
        for key in KEYS:
            assert "trigger" not in en[key].lower(), key
