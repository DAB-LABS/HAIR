"""Climate matrix helpers: the dimension checklist and cell resolution.

Cold Cuts (v0.8.8). Two consumers share this module:

- The fitting flow derives the DIMENSION CHECK here: a deterministic
  checklist standing in for the full lattice (owner rulings 2026-07-28,
  mockup CC1). Nobody fits 2,689 cells; everybody can fit every mode,
  every fan speed, every swing position, both ends of the temperature
  range, and off/on -- 12 to 20 sends regardless of matrix size. The
  derivation is a pure function of the climate block (file order plus
  sorted temps, no randomness), so every install of the same file
  produces the identical list and fittings accumulate in one ledger.

- The climate entity resolves target states to cells here: nearest-temp
  snap inside the chosen branch, first-of-branch fallbacks for a fan or
  swing the file does not carry, and honest None when a mode subtree
  simply has no such state (matrices are SPARSE -- census found 158
  explicit nulls; absent combinations never became cells at import).

Vocabulary is verbatim throughout (addendum section 3): mode / fan /
swing strings are lookup keys AND entity attributes, so nothing here
case-normalizes or unifies spellings. The one mapping that exists is
MODE_ALIAS, which translates a file's mode key to the HA HVAC mode
vocabulary without touching the stored cell.
"""
from __future__ import annotations

from dataclasses import dataclass

from .wig_format import ClimateCell, ClimateMatrix, _temp_str, cell_key

# File-mode -> HA HVACMode value. Direct names map to themselves; the
# two aliases are corpus fact (census: "fan" in 24 files, "cold" in 1).
# Anything else was skipped with a receipt at import, so a parsed
# matrix should only carry mappable modes -- but consumers still treat
# an unmappable mode defensively (skip, never raise).
MODE_ALIAS: dict[str, str] = {
    "cool": "cool",
    "heat": "heat",
    "dry": "dry",
    "fan_only": "fan_only",
    "heat_cool": "heat_cool",
    "auto": "auto",
    "fan": "fan_only",
    "cold": "cool",
}


def ha_mode_for(mode: str) -> str | None:
    """The HA HVAC mode string for a file mode key, or None."""
    return MODE_ALIAS.get(mode)


# Power-code display labels. Title case where cells stay verbatim
# because the power keys are OURS (file-level "off"/"on", not user
# vocabulary), so they may carry the one capitalization in the system.
_STATE_DISPLAY = {"off": "Off", "on": "On"}


def state_display_name(kind: str) -> str:
    """The human label for a power code: "off" -> "Off", "on" -> "On"."""
    return _STATE_DISPLAY.get(kind, kind)


def cell_display_name(cell: ClimateCell) -> str:
    """THE human name of a cell, on every user surface.

    Owner-ruled grammar (2026-07-29, mockup CC4): spaced slashes, mode
    bare first, fan and swing labeled, temperature a bare number last:
    "cool / fan: auto / 22". The labels are load-bearing, not
    decoration: "auto" is a legal value in the mode, fan, AND swing
    vocabularies of real corpus files, so an unlabeled
    "auto / auto / auto" cannot be read back into coordinates. Values
    ride verbatim (never case-normalized, addendum section 3);
    dimensions the cell does not carry are omitted, so a depth-1 cell
    reads "dry / fan: auto" and a bare-mode cell is just its mode.
    The compact ``cell_key`` ("cool/auto/23") stays the fittings
    ledger key and must never appear on a human surface.
    """
    parts = [cell.mode]
    if cell.fan is not None:
        parts.append(f"fan: {cell.fan}")
    if cell.swing is not None:
        parts.append(f"swing: {cell.swing}")
    if cell.temp is not None:
        parts.append(_temp_str(cell.temp))
    return " / ".join(parts)


def exact_cell(
    matrix: ClimateMatrix,
    mode: str,
    fan: str | None = None,
    swing: str | None = None,
    temp: float | None = None,
) -> ClimateCell | None:
    """The cell at EXACTLY these coordinates, or None.

    No snapping and no first-of-branch fallbacks, unlike
    ``resolve_cell``: the cell browser and save-state-as-command send
    coordinates read off the matrix itself (Cold Cuts second half,
    2026-07-29), so a miss means a stale or hand-rolled caller and the
    honest answer is "no such state", never a nearby one.
    """
    temp = float(temp) if temp is not None else None
    for cell in matrix.cells:
        if (
            cell.mode == mode
            and cell.fan == fan
            and cell.swing == swing
            and cell.temp == temp
        ):
            return cell
    return None


# Checklist sections, in walk order (mockup CC1). OFF is last so the
# session leaves the unit off.
SECTION_START = "start"
SECTION_MODES = "modes"
SECTION_FAN = "fan"
SECTION_SWING = "swing"
SECTION_TEMP = "temp"
SECTION_WRAP = "wrap"


@dataclass
class ChecklistRow:
    """One dimension-check row: a sendable state plus display facts.

    ``key`` is the fitting record key (``cell_key`` for matrix cells,
    literal "on" / "off" for the power codes). ``context`` carries the
    section's held-constant coordinates for the frontend's "in Cool
    23, fan auto" label; row-specific coordinates live in mode / fan /
    swing / temp.
    """

    key: str
    section: str
    pronto: str
    send_count: int = 1
    mode: str | None = None
    fan: str | None = None
    swing: str | None = None
    temp: float | None = None
    # True when this row's mode subtree has no temperature dimension
    # (depth-1 branches; the dialog says so inline).
    temp_less: bool = False
    # "min" / "max" on the temperature-range rows.
    temp_role: str | None = None


class _Branches:
    """Cells indexed mode -> fan -> swing -> sorted temps."""

    def __init__(self, matrix: ClimateMatrix) -> None:
        self.matrix = matrix
        self.by_mode: dict[str, list[ClimateCell]] = {}
        self.index: dict[
            tuple[str, str | None, str | None], dict[float | None, ClimateCell]
        ] = {}
        for cell in matrix.cells:
            self.by_mode.setdefault(cell.mode, []).append(cell)
            self.index.setdefault(
                (cell.mode, cell.fan, cell.swing), {}
            )[cell.temp] = cell

    def modes(self) -> list[str]:
        """Declared order first (advisory), then undeclared observed."""
        ordered = [m for m in self.matrix.modes if m in self.by_mode]
        ordered += [m for m in self.by_mode if m not in ordered]
        return ordered

    def fans(self, mode: str) -> list[str]:
        observed: list[str] = []
        for cell in self.by_mode.get(mode, []):
            if cell.fan is not None and cell.fan not in observed:
                observed.append(cell.fan)
        ordered = [f for f in self.matrix.fan_modes if f in observed]
        ordered += [f for f in observed if f not in ordered]
        return ordered

    def swings(self, mode: str, fan: str | None) -> list[str]:
        observed: list[str] = []
        for cell in self.by_mode.get(mode, []):
            if cell.fan == fan and cell.swing is not None \
                    and cell.swing not in observed:
                observed.append(cell.swing)
        ordered = [s for s in self.matrix.swing_modes if s in observed]
        ordered += [s for s in observed if s not in ordered]
        return ordered

    def temps(
        self, mode: str, fan: str | None, swing: str | None
    ) -> list[float]:
        branch = self.index.get((mode, fan, swing), {})
        return sorted(t for t in branch if t is not None)

    def cell(
        self, mode: str, fan: str | None, swing: str | None,
        temp: float | None,
    ) -> ClimateCell | None:
        return self.index.get((mode, fan, swing), {}).get(temp)

    def richest_mode(self) -> str | None:
        modes = self.modes()
        if not modes:
            return None
        return max(modes, key=lambda m: (len(self.by_mode[m]),
                                         -modes.index(m)))

    def representative(self, mode: str) -> ClimateCell | None:
        """The mode's one checklist cell: first fan, first swing, median
        temp -- or the branch's bare cell when a dimension is absent."""
        fans = self.fans(mode)
        fan = fans[0] if fans else None
        swings = self.swings(mode, fan)
        swing = swings[0] if swings else None
        temps = self.temps(mode, fan, swing)
        if temps:
            return self.cell(mode, fan, swing, temps[len(temps) // 2])
        return self.cell(mode, fan, swing, None)


def dimension_checklist(matrix: ClimateMatrix) -> list[ChecklistRow]:
    """The dimension check: deterministic, dedup'd, off last."""
    branches = _Branches(matrix)
    rows: list[ChecklistRow] = []
    seen: set[str] = set()

    def _add(section: str, cell: ClimateCell | None, **extra) -> None:
        if cell is None:
            return
        key = cell_key(cell)
        if key in seen:
            return
        seen.add(key)
        temps_here = branches.temps(cell.mode, cell.fan, cell.swing)
        rows.append(ChecklistRow(
            key=key, section=section, pronto=cell.pronto,
            send_count=cell.send_count, mode=cell.mode, fan=cell.fan,
            swing=cell.swing, temp=cell.temp,
            temp_less=not temps_here, **extra,
        ))

    if matrix.on is not None:
        rows.append(ChecklistRow(
            key="on", section=SECTION_START, pronto=matrix.on,
        ))
        seen.add("on")

    for mode in branches.modes():
        _add(SECTION_MODES, branches.representative(mode))

    rich = branches.richest_mode()
    if rich is not None:
        rich_fans = branches.fans(rich)
        for fan in rich_fans:
            swings = branches.swings(rich, fan)
            swing = swings[0] if swings else None
            temps = branches.temps(rich, fan, swing)
            cell = (
                branches.cell(rich, fan, swing, temps[len(temps) // 2])
                if temps else branches.cell(rich, fan, swing, None)
            )
            _add(SECTION_FAN, cell)

        primary_fan = rich_fans[0] if rich_fans else None
        for swing in branches.swings(rich, primary_fan):
            temps = branches.temps(rich, primary_fan, swing)
            cell = (
                branches.cell(
                    rich, primary_fan, swing, temps[len(temps) // 2]
                )
                if temps else branches.cell(rich, primary_fan, swing, None)
            )
            _add(SECTION_SWING, cell)

        prim_swings = branches.swings(rich, primary_fan)
        primary_swing = prim_swings[0] if prim_swings else None
        temps = branches.temps(rich, primary_fan, primary_swing)
        if temps:
            _add(
                SECTION_TEMP,
                branches.cell(rich, primary_fan, primary_swing, temps[0]),
                temp_role="min",
            )
            _add(
                SECTION_TEMP,
                branches.cell(rich, primary_fan, primary_swing, temps[-1]),
                temp_role="max",
            )

    rows.append(ChecklistRow(
        key="off", section=SECTION_WRAP, pronto=matrix.off,
    ))
    return rows


def matrix_summary(matrix: ClimateMatrix) -> dict:
    """The one-line matrix summary the closet and device page render.

    Owner ruling 2026-07-28: wigs/list and the full device payload both
    carry this block so the frontend can say "300 states, 5 modes,
    16-30" without ever loading cells. Declared vocabulary order leads
    (it is advisory display order, same rule as _Branches), observed
    values the file forgot to declare follow, and values declared but
    never observed are dropped -- the summary describes what the
    matrix can actually do, not what its header claims.
    """
    modes_seen: list[str] = []
    fans_seen: list[str] = []
    swings_seen: list[str] = []
    for cell in matrix.cells:
        if cell.mode not in modes_seen:
            modes_seen.append(cell.mode)
        if cell.fan is not None and cell.fan not in fans_seen:
            fans_seen.append(cell.fan)
        if cell.swing is not None and cell.swing not in swings_seen:
            swings_seen.append(cell.swing)

    def _ordered(declared: list[str], observed: list[str]) -> list[str]:
        out = [v for v in declared if v in observed]
        out += [v for v in observed if v not in out]
        return out

    return {
        "cells": len(matrix.cells),
        "modes": _ordered(matrix.modes, modes_seen),
        "fan_modes": _ordered(matrix.fan_modes, fans_seen),
        "swing_modes": _ordered(matrix.swing_modes, swings_seen),
        "min_temp": matrix.min_temp,
        "max_temp": matrix.max_temp,
    }


def resolve_cell(
    matrix: ClimateMatrix,
    mode: str,
    fan: str | None = None,
    swing: str | None = None,
    temp: float | None = None,
) -> ClimateCell | None:
    """The entity's lookup: the cell nearest the requested state.

    Mode must match a real subtree (the caller already alias-mapped
    from HVACMode back to the file's verbatim key). Fan and swing fall
    back to the branch's first value when the requested one does not
    exist there; temp snaps to the nearest available in the final
    branch. Returns None only when the mode subtree has no cells at
    all -- callers log and refuse, never KeyError (sparse matrices are
    corpus fact).
    """
    branches = _Branches(matrix)
    if mode not in branches.by_mode:
        return None
    fans = branches.fans(mode)
    use_fan = fan if fan in fans else (fans[0] if fans else None)
    swings = branches.swings(mode, use_fan)
    use_swing = swing if swing in swings else (swings[0] if swings else None)
    temps = branches.temps(mode, use_fan, use_swing)
    if not temps:
        return branches.cell(mode, use_fan, use_swing, None)
    target = (
        temps[len(temps) // 2] if temp is None
        else min(temps, key=lambda t: abs(t - temp))
    )
    return branches.cell(mode, use_fan, use_swing, target)
