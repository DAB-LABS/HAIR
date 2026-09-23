"""Thinning: removing states a device does not have (thinning-plan.md).

A person tells HAIR which states their unit really has, and HAIR removes
the rest. It is the per-cell delete HAIR already has
(``DeviceManager.async_delete_cell``) at the scale of an axis, a mode or
a whole extras lattice, done in one write, with a record.

THIS MODULE IS THE ARITHMETIC, and nothing else. It takes the current
matrix and the WHOLE desired shape (never a diff: the card holds the
whole shape, and a diff invites the two to disagree), refuses anything
it cannot honour, and returns the new matrix plus the record. It does
no I/O, touches no device and writes no wig; the websocket door
(``ws_device_matrix_thin``) resolves, writes and writes through. Kept
apart so the refusals and the counts can be driven directly, exactly
the way the door will drive them.

What it will never do, by construction:

- Add anything. Every kept value must be one the mode carries now, and
  an axis the mode lacks cannot be given one.
- Touch ``off``. It is how the wig turns the unit off, so the shape has
  no way to say it, and a payload that tries is refused by name.
- Move the matrix's frame. ``off``, ``unit``, ``precision``, the bounds
  and the three vocabulary lists come across unchanged, so a thinned
  matrix is the old one with cells missing and nothing else different.
- Carry a Pronto into the record. The undo is the original wig, which
  the write-through never deletes.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any

from .wig_format import ClimateCell, ClimateExtra, ClimateMatrix, cell_key

#: Where the record lives: ``ClimateMatrix.extra``, so it rides the
#: matrix file and the exported wig by the unknown-keys contract with
#: no format change (plan section 4). A list, newest last.
THINNING_KEY = "hair_thinning"

#: A thinning is ``accepted`` in the repair tiers' vocabulary
#: (tangles.TIER_ACCEPTED): a human said yes, and no transmission is
#: claimed. Spelled here as the same literal rather than imported, so
#: this module stays free of the tangles import graph; the test pins
#: that the two agree.
TIER_ACCEPTED = "accepted"

#: The one refusal that is not about a malformed shape: the shape was
#: fine and asked for nothing. Decided AFTER building the new matrix,
#: by diffing it against the current one, never from the payload's
#: spelling (plan section 2, added 2026-09-21).
NOTHING_TO_REMOVE = "nothing to remove"

#: The three axes a mode can carry, in the payload's spelling, with the
#: cell attribute each one reads.
_AXES = (("fans", "fan"), ("swings", "swing"), ("temps", "temp"))

#: Keys that would address ``off``. Refused wherever they appear.
_OFF_KEYS = ("off", "keep_off")

_TEMP_TOLERANCE = 1e-6


class ThinRefused(ValueError):
    """The shape cannot be honoured. The message names what and where,
    and the door sends it as ``invalid_format`` verbatim."""


@dataclass
class ThinOutcome:
    """What a thin produces: the new matrix and what it removed."""

    matrix: ClimateMatrix
    #: The record entry, before the door adds ``portholes_removed``.
    record: dict[str, Any]
    #: Every removed cell, per lattice: ``(axis, key) -> [cell, ...]``,
    #: with ``(None, None)`` for the main lattice. The door matches
    #: portholes against these; nothing else reads them.
    removed: dict[tuple[str | None, str | None], list[ClimateCell]] = field(
        default_factory=dict
    )


def _where(axis: str | None, key: str | None, mode: str | None = None) -> str:
    """A human name for a place in the shape, for refusal messages."""
    place = "the main lattice" if key is None else f"lattice {axis}:{key}"
    return place if mode is None else f"mode {mode!r} in {place}"


def _ordered(declared: list[str], observed: list[str]) -> list[str]:
    """Declared order first, observed strays after (matrix_summary's rule)."""
    out = [v for v in declared if v in observed]
    out += [v for v in observed if v not in out]
    return out


def _mode_axes(
    matrix: ClimateMatrix, cells: list[ClimateCell], mode: str
) -> dict[str, list[Any]]:
    """What one mode carries now, per axis. An EMPTY list means the mode
    has no such axis at all, which the payload must spell as null."""
    fans: list[str] = []
    swings: list[str] = []
    temps: list[float] = []
    for cell in cells:
        if cell.mode != mode:
            continue
        if cell.fan is not None and cell.fan not in fans:
            fans.append(cell.fan)
        if cell.swing is not None and cell.swing not in swings:
            swings.append(cell.swing)
        if cell.temp is not None and not any(
            abs(float(cell.temp) - t) < _TEMP_TOLERANCE for t in temps
        ):
            temps.append(float(cell.temp))
    return {
        "fans": _ordered(matrix.fan_modes, fans),
        "swings": _ordered(matrix.swing_modes, swings),
        "temps": sorted(temps),
    }


def _modes_of(cells: list[ClimateCell]) -> list[str]:
    out: list[str] = []
    for cell in cells:
        if cell.mode not in out:
            out.append(cell.mode)
    return out


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _refuse_off(raw: dict[str, Any], place: str) -> None:
    for key in _OFF_KEYS:
        if key in raw:
            raise ThinRefused(
                f"off cannot be removed or addressed ({key!r} in {place}); "
                "it is how the wig turns the unit off"
            )


def _kept_values(
    raw: dict[str, Any],
    carried: dict[str, list[Any]],
    place: str,
) -> dict[str, list[Any] | None]:
    """Validate one mode entry's three axes against what it carries.

    Returns the kept values per axis, in the mode's own order, or None
    for an axis the mode does not have."""
    kept: dict[str, list[Any] | None] = {}
    for axis, _attr in _AXES:
        if axis not in raw:
            raise ThinRefused(f"{place}: {axis!r} is required (a list, or null)")
        value = raw[axis]
        have = carried[axis]
        if value is None:
            if have:
                raise ThinRefused(
                    f"{place}: {axis} given as null, but the mode carries it"
                )
            kept[axis] = None
            continue
        if not isinstance(value, list):
            raise ThinRefused(f"{place}: {axis} must be a list or null")
        if not have:
            raise ThinRefused(
                f"{place}: {axis} given as a list, but the mode has no "
                f"{axis[:-1]} axis; thinning never adds an axis"
            )
        if not value:
            raise ThinRefused(
                f"{place}: {axis} is empty; keep at least one value, or "
                "leave the mode out to remove it"
            )
        if axis == "temps":
            out: list[float] = []
            for item in value:
                if not _is_number(item):
                    raise ThinRefused(
                        f"{place}: temps must be numbers, got {item!r}"
                    )
                match = next(
                    (t for t in have if abs(t - float(item)) < _TEMP_TOLERANCE),
                    None,
                )
                if match is None:
                    raise ThinRefused(
                        f"{place}: temp {item!r} is not a value the mode carries"
                    )
                if match not in out:
                    out.append(match)
            kept[axis] = sorted(out)
        else:
            for item in value:
                if not isinstance(item, str) or item not in have:
                    raise ThinRefused(
                        f"{place}: {axis[:-1]} {item!r} is not a value the "
                        "mode carries"
                    )
            kept[axis] = [v for v in have if v in value]
    return kept


def _cell_survives(cell: ClimateCell, kept: dict[str, list[Any] | None]) -> bool:
    """Does this cell stay under the mode's kept values?

    A cell with NO value on an axis the mode otherwise carries (a mixed
    branch: most cells carry a temperature, one does not) is not
    addressable by that axis, so that axis's filter passes it. Thinning
    removes what a person pointed at, never a cell they had no way to
    point at.
    """
    for axis, attr in _AXES:
        values = kept[axis]
        own = getattr(cell, attr)
        if values is None or own is None:
            continue
        if attr == "temp":
            if not any(abs(float(own) - t) < _TEMP_TOLERANCE for t in values):
                return False
        elif own not in values:
            return False
    return True


def _thin_lattice(
    matrix: ClimateMatrix,
    cells: list[ClimateCell],
    axis: str | None,
    key: str | None,
    raw_modes: Any,
) -> tuple[list[ClimateCell], list[dict], list[dict], list[ClimateCell]]:
    """One lattice: (kept cells, modes_removed, narrowed, removed cells)."""
    place = _where(axis, key)
    if not isinstance(raw_modes, list):
        raise ThinRefused(f"{place}: modes must be a list")
    if not raw_modes:
        if key is None:
            raise ThinRefused(
                "the main lattice has no modes; a matrix keeps at least one"
            )
        raise ThinRefused(
            f"{place} has no modes; leave the lattice out to remove it"
        )
    present = _modes_of(cells)
    wanted: dict[str, dict[str, list[Any] | None]] = {}
    for raw in raw_modes:
        if not isinstance(raw, dict):
            raise ThinRefused(f"{place}: every mode entry must be an object")
        mode = raw.get("mode")
        if not isinstance(mode, str) or not mode:
            raise ThinRefused(f"{place}: every mode entry needs a mode")
        where = _where(axis, key, mode)
        _refuse_off(raw, where)
        stray = sorted(set(raw) - {"mode", "fans", "swings", "temps"})
        if stray:
            raise ThinRefused(f"{where}: unknown field {stray[0]!r}")
        if mode not in present:
            raise ThinRefused(f"{where}: no such mode")
        if mode in wanted:
            raise ThinRefused(f"{where}: given twice")
        wanted[mode] = _kept_values(raw, _mode_axes(matrix, cells, mode), where)

    kept_cells: list[ClimateCell] = []
    removed: list[ClimateCell] = []
    for cell in cells:
        rule = wanted.get(cell.mode)
        if rule is not None and _cell_survives(cell, rule):
            kept_cells.append(cell)
        else:
            removed.append(cell)

    modes_removed: list[dict] = []
    narrowed: list[dict] = []
    for mode in present:
        before = sum(1 for c in cells if c.mode == mode)
        if mode not in wanted:
            modes_removed.append({
                "axis": axis, "key": key, "mode": mode, "cells": before,
            })
            continue
        after = sum(1 for c in kept_cells if c.mode == mode)
        if after < before:
            rule = wanted[mode]
            narrowed.append({
                "axis": axis, "key": key, "mode": mode,
                "fans": rule["fans"], "swings": rule["swings"],
                "temps": [_json_temp(t) for t in rule["temps"]]
                if rule["temps"] is not None else None,
                # REMOVED here, as in the other two lists, so the three
                # add up to ``removed_cells``. The kept values say what
                # survived; this says what it cost.
                "cells": before - after,
            })
    return kept_cells, modes_removed, narrowed, removed


def _json_temp(value: float) -> int | float:
    return int(value) if float(value).is_integer() else float(value)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def thin_matrix(
    matrix: ClimateMatrix,
    lattices: Any,
    keep_on: bool,
    *,
    now: str | None = None,
) -> ThinOutcome:
    """Build the thinned matrix and its record, or raise ``ThinRefused``.

    ``lattices`` is the payload's list verbatim. A lattice absent from it
    is removed; a mode absent from its lattice is removed; a kept mode
    keeps exactly the cells whose values survive on every axis. The
    main lattice must be present with at least one mode.
    """
    if not isinstance(lattices, list):
        raise ThinRefused("lattices must be a list")

    extras_by_id = {(e.axis, e.key): e for e in (matrix.extras or [])}
    given: dict[tuple[str | None, str | None], Any] = {}
    for raw in lattices:
        if not isinstance(raw, dict):
            raise ThinRefused("every lattice entry must be an object")
        axis, key = raw.get("axis"), raw.get("key")
        if (axis is None) != (key is None):
            raise ThinRefused(
                "a lattice names both axis and key, or neither for the "
                f"main lattice (got axis={axis!r}, key={key!r})"
            )
        if axis is not None and not (
            isinstance(axis, str) and isinstance(key, str)
        ):
            raise ThinRefused("a lattice's axis and key must be strings")
        place = _where(axis, key)
        _refuse_off(raw, place)
        stray = sorted(set(raw) - {"axis", "key", "modes"})
        if stray:
            raise ThinRefused(f"{place}: unknown field {stray[0]!r}")
        if axis is not None and (axis, key) not in extras_by_id:
            raise ThinRefused(f"{place}: no such lattice on this matrix")
        if (axis, key) in given:
            raise ThinRefused(f"{place}: given twice")
        given[(axis, key)] = raw.get("modes")

    if (None, None) not in given:
        raise ThinRefused("the main lattice is missing; it cannot be removed")

    removed: dict[tuple[str | None, str | None], list[ClimateCell]] = {}
    modes_removed: list[dict] = []
    narrowed: list[dict] = []

    main_cells, m_removed, m_narrowed, m_gone = _thin_lattice(
        matrix, matrix.cells, None, None, given[(None, None)],
    )
    modes_removed += m_removed
    narrowed += m_narrowed
    if m_gone:
        removed[(None, None)] = m_gone

    new_extras: list[ClimateExtra] = []
    lattices_removed: list[dict] = []
    for extra in matrix.extras or []:
        ident = (extra.axis, extra.key)
        if ident not in given:
            lattices_removed.append({
                "axis": extra.axis, "key": extra.key,
                "cells": len(extra.cells),
            })
            if extra.cells:
                removed[ident] = list(extra.cells)
            continue
        kept, e_removed, e_narrowed, e_gone = _thin_lattice(
            matrix, extra.cells, extra.axis, extra.key, given[ident],
        )
        modes_removed += e_removed
        narrowed += e_narrowed
        if e_gone:
            removed[ident] = e_gone
        new_extras.append(ClimateExtra(axis=extra.axis, key=extra.key,
                                       cells=kept))

    on_removed = matrix.on is not None and not keep_on
    removed_cells = sum(len(cells) for cells in removed.values())
    if removed_cells == 0 and not on_removed:
        raise ThinRefused(NOTHING_TO_REMOVE)

    kept_cells = len(main_cells) + sum(len(e.cells) for e in new_extras)
    record: dict[str, Any] = {
        "at": now or _now(),
        "tier": TIER_ACCEPTED,
        "removed_cells": removed_cells,
        "kept_cells": kept_cells,
        # The plan's record has no field for the separate On code, and
        # dropping it is a removal like any other, so it is said here
        # rather than left for a reader to infer from the matrix.
        "on_removed": on_removed,
        "lattices_removed": lattices_removed,
        "modes_removed": modes_removed,
        "narrowed": narrowed,
    }
    history = list((matrix.extra or {}).get(THINNING_KEY) or [])
    history.append(record)
    thinned = replace(
        matrix,
        # The frame is copied, never edited: same off, unit, precision,
        # bounds and vocabulary lists (plan section 3, step 2).
        modes=list(matrix.modes),
        fan_modes=list(matrix.fan_modes),
        swing_modes=list(matrix.swing_modes),
        on=None if on_removed else matrix.on,
        cells=main_cells,
        extras=new_extras,
        extra={**(matrix.extra or {}), THINNING_KEY: history},
    )
    return ThinOutcome(matrix=thinned, record=record, removed=removed)


def porthole_addresses(
    matrix_cell: dict[str, Any],
    removed: dict[tuple[str | None, str | None], list[ClimateCell]],
) -> ClimateCell | None:
    """The removed cell a porthole's ``matrix_cell`` addresses, or None.

    Matched by coordinates within the porthole's own lattice, the way
    ``_porthole_cell`` identifies one and never by the row's name. A
    porthole carries no lattice today (the comb only walks the main
    one), so one without the pair is the main lattice's; one that ever
    grows the pair is matched in that lattice and nowhere else.
    """
    axis = matrix_cell.get("axis")
    key = matrix_cell.get("lattice")
    ident = (axis, key) if axis is not None and key is not None else (None, None)
    for cell in removed.get(ident, ()):
        if cell.mode != matrix_cell.get("mode"):
            continue
        if (cell.fan or None) != (matrix_cell.get("fan") or None):
            continue
        if (cell.swing or None) != (matrix_cell.get("swing") or None):
            continue
        a, b = cell.temp, matrix_cell.get("temp")
        if a is None or b is None:
            if a is None and b is None:
                return cell
            continue
        if abs(float(a) - float(b)) < _TEMP_TOLERANCE:
            return cell
    return None


def porthole_record(
    command_id: str, matrix_cell: dict[str, Any], cell: ClimateCell
) -> dict[str, Any]:
    """One ``portholes_removed`` entry: which row, which cell, no bytes."""
    axis = matrix_cell.get("axis")
    key = matrix_cell.get("lattice")
    if axis is None or key is None:
        axis = key = None
    return {
        "command_id": command_id,
        "axis": axis,
        "key": key,
        "cell_key": cell_key(cell),
    }
