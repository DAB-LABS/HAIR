"""The State Matrix card draws its temperature tiles by the chips' rule.

GH #116: in Send mode the Mode / Fan / Swing chips are drawn selected
from the first render, but the temperature tile waited for a click
(it gated on ``_browsed``), so a card came up with its temperature
looking unpicked while Send sent it. The tiles now read ``_fills``,
the one rule the chips use: selected at once in Send mode, only after
a real click in Hear mode. Read as text, the house tactic for the
card, which imports ``lit`` and cannot run on its own under node.
"""
from __future__ import annotations

import re
from pathlib import Path

CARD = (
    Path(__file__).parent.parent / "frontend" / "src" / "ir-matrix-card.ts"
)


def _render_grid() -> str:
    text = CARD.read_text(encoding="utf-8")
    start = text.index("private _renderGrid(")
    end = text.index("\n    private ", start + 1)
    return text[start:end]


def test_the_temperature_tiles_read_the_chips_rule():
    grid = _render_grid()
    # Both tile paths: the bare tile of a branch with no temperatures,
    # and the tile per temperature.
    assert "const isSel = this._selPower === null && this._fills;" in grid
    assert re.search(
        r"this\._selPower === null &&\s+this\._fills &&\s+pos === this\._selTemp",
        grid,
    )
    assert not re.search(r"this\._browsed &&\s+pos === this\._selTemp", grid)
    assert "this._selPower === null && this._browsed" not in grid


def test_the_rule_is_send_now_and_hear_after_a_click():
    text = CARD.read_text(encoding="utf-8")
    assert re.search(
        r'private get _fills\(\): boolean \{\s+return this\.mode !== "hear" \|\| this\._browsed;',
        text,
    )
