"""The radio code editor says when a pasted code is a rolling code.

- ``hair/rf/validate`` returns ``rf_rolling`` ("keeloq", "somfy_rts" or
  null); the editor's strip shows one line under the pill when it is set,
  before Save, and nothing when it is null or the paste is refused.
- The line is a notice, in the strip's warning style, in every language.

Source pins and locale checks; the server's key is pinned in
test_rf_rolling_guard.py and the paste tests.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

COMPONENT = Path(__file__).parent.parent
SRC = COMPONENT / "frontend" / "src"
LOCALES = SRC / "locales"
KEY = "rfedit.rolling_code"


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _feedback() -> str:
    editor = _read("ir-rf-editor.ts")
    body = editor.split("private _renderFeedback() {", 1)[1]
    return body.split("\n    }\n", 1)[0]


class TestTheValidateAnswer:
    def test_the_type_carries_the_key(self):
        types = _read("types.ts")
        block = types.split("export interface RfValidation {", 1)[1].split("\n}\n", 1)[0]
        assert 'rf_rolling?: "keeloq" | "somfy_rts" | null;' in block

    def test_the_server_returns_it_from_validate(self):
        source = (COMPONENT / "rf_paste.py").read_text(encoding="utf-8")
        assert '"rf_rolling": rolling_family(frame),' in source


class TestTheLine:
    def test_it_shows_only_when_the_code_is_rolling(self):
        body = _feedback()
        assert "${v.rf_rolling\n" in body
        assert '<div class="msg warn rolling">${t("rfedit.rolling_code")}</div>' in body

    def test_it_sits_under_the_pill_before_the_frames_warning(self):
        body = _feedback()
        pill = body.index("this._renderRecognized(family)")
        line = body.index('t("rfedit.rolling_code")')
        frames = body.index('t("rfedit.frames_agree"')
        assert pill < line < frames

    def test_a_refusal_never_reaches_it(self):
        body = _feedback()
        assert body.index("if (!v.ok) {") < body.index("v.rf_rolling")


class TestTheStrings:
    @pytest.mark.parametrize("path", sorted(LOCALES.glob("*.json")), ids=lambda p: p.stem)
    def test_every_language(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get(KEY), path.name
        assert "HAIR" in data[KEY], path.name
        assert "—" not in data[KEY], path.name

    def test_the_english(self):
        en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        assert en[KEY] == "Rolling code: HAIR keeps it but never sends it."
