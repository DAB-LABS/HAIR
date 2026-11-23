"""A matrix wig can be picked in Add Device's Closet tab.

The wig picker used to refuse every matrix row, a rule from before a
matrix wig could be adopted from a dialog. Add Device now opens it with
``allowMatrix``: the pick locks the Type to AC and creates through
``wigMakeDevice()``, the call ADOPT DEVICE on the Closet card makes.
Add Trigger Remote leaves it off, since a matrix has no single signal a
trigger can point at. A matrix row's count shows its states, as the
Closet does, and other rows say signals, not states.

Pinned in the source, so it runs without the frontend toolchain.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

SRC = Path(__file__).parent.parent / "frontend" / "src"
LOCALES = sorted((SRC / "locales").glob("*.json"))


def _flat(name: str) -> str:
    return " ".join((SRC / name).read_text(encoding="utf-8").split())


def _picker_tag(name: str) -> str:
    flat = _flat(name)
    start = flat.index("<ir-wig-picker")
    return flat[start:flat.index("></ir-wig-picker>", start)]


class TestPicker:
    def test_allow_matrix_is_off_by_default(self):
        flat = _flat("ir-wig-picker.ts")
        assert "@property({ type: Boolean }) public allowMatrix = false;" in flat

    def test_pick_refuses_a_matrix_row_only_when_not_allowed(self):
        flat = _flat("ir-wig-picker.ts")
        assert "if (this.disabled || this._blocked(row)) return;" in flat
        assert "return !!row.wig?.matrix && !this.allowMatrix;" in flat
        # The old blanket refusal is gone.
        assert "if (this.disabled || row.wig?.matrix) return;" not in flat

    def test_only_a_blocked_row_looks_unclickable(self):
        flat = _flat("ir-wig-picker.ts")
        assert 'this._blocked(row) ? "blocked" : ""' in flat
        assert ".row.blocked { cursor: default; }" in flat
        assert ".row.matrix {" not in flat

    def test_a_matrix_row_counts_its_states(self):
        flat = _flat("ir-wig-picker.ts")
        assert (
            "return row.wig?.matrix ? row.wig.matrix.cells : row.signalCount;"
            in flat
        )
        assert '<div class="row-count">${this._shownCount(row)}</div>' in flat

    def test_other_rows_say_signals(self):
        flat = _flat("ir-wig-picker.ts")
        assert ': tp("wigs.signals", row.signalCount)}' in flat
        assert "wigs.states" not in flat


class TestCallers:
    def test_add_device_allows_matrix(self):
        tag = _picker_tag("ir-add-controlled-device-dialog.ts")
        assert " allowMatrix " in f"{tag} "

    def test_add_trigger_remote_does_not(self):
        tag = _picker_tag("ir-add-trigger-remote-dialog.ts")
        assert "allowMatrix" not in tag

    def test_a_matrix_pick_locks_the_type_and_adopts(self):
        flat = _flat("ir-add-controlled-device-dialog.ts")
        assert (
            'if (e.detail.row.wig?.matrix) { this._deviceType = "ac"; }' in flat
        )
        assert "created = await this.api.wigMakeDevice(" in flat
        assert "? { filename: wig.wig!.filename }" in flat

    def test_a_matrix_pick_previews_its_states(self):
        flat = _flat("ir-add-controlled-device-dialog.ts")
        assert 't("adddc.preview_creates_matrix", {' in flat
        assert 'states: tp("wigs.states", wig.wig?.matrix?.cells ?? 0),' in flat
        # Both doors: the Closet tab's preview line and drop mode's.
        assert flat.count("this._matrixPreview(") == 2


@pytest.mark.parametrize("path", LOCALES, ids=lambda p: p.stem)
def test_every_locale_has_the_matrix_preview(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    value = data["adddc.preview_creates_matrix"]
    assert "{name}" in value
    assert "{states}" in value
