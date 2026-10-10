"""The real-air harness: every field pack pressed through the air model.

Every cell of every field pack is pressed through
``test_read_bytes_identity._air``, salted per code, on both
transmitters, whole and cut where the FILE code closes a frame at its
map's ``timing.gap_min`` (a receiver whose idle lies between the code's
longest in-frame space and its frame gap). Each press is counted three
ways, kept apart:

- ``read``, every map: unglitched whole presses ``read_code`` reads as
  the pack's family. This is the window figure, the one a map-window
  patch moves.
- ``key``, the families on ``identity.READ_BYTES_VERIFIED`` only:
  unglitched presses whose read key is the cell's own file key, whole,
  and split (any piece forms it).
- ``heard_wrong``, every map: presses or pieces the pack's own cell
  index hears as a cell that is neither the pressed cell nor a member
  of its merged group.

Beside them: ``wrong_key`` (presses or pieces whose read key names a
state they are not: a key other than the cell's own that a cell outside
the pressed cell's group holds, or that any cell of another pack holds;
or the cell's own key held by another pack outside the designed shared
settings frame), which is 0 on every map and must stay 0;
``wrong_state`` (presses or pieces that read as the family with field
values other than the file's); and ``glitched`` (the model's glitched
presses, and how many of them were still heard as their own cell or
formed their own key).

THE CLOSING SPACE. A receiver closes every capture with its own idle
time, whatever gap the code had. The model's presses and pieces keep the
file code's own closing (its trailing word, or the gap a piece was cut
at), so every press and piece is also counted re-closed at each idle in
``CLOSINGS``: ``closed_read`` (whole unglitched presses ``read_code``
reads), ``closed_key`` (listed families, the ``key`` figure again) and
``closed_heard_wrong``. This re-closes each variant; it does not model a
receiver's own split or join (a 10 ms receiver also cuts DAIKIN216 at
its 29.7 ms gap, which the pieces already cover; an 80 ms receiver joins
every two-frame press, which ``RECEIVER_BUFFER`` counts). The
dimension exists because a 10 ms closing space under DAIKIN216's 11 ms
``gap_min`` once kept every lone Daikin settings frame from keying on
the air while the model, closing at the file's own gap, saw nothing
(fake-remote air bench, 2026-10-05).

THE MODEL IS DETERMINISTIC. ``_air`` seeds a string, and the salt is a
sha256 of the normalized code, never ``hash()``, so every figure is an
exact count, the same on every run, every ``PYTHONHASHSEED``, both
Python legs and without the protocol library. Figures are asserted with
``==``: a floor asserted with ``>=`` would let a widened window raise the
count and a later narrowing drop it back, with nothing failing, and any
tolerance hides a one-tick change.

WHAT THE MODEL CANNOT SEE. A boundary moved inside the model's slack
changes no figure. For MITSUBISHI144's ``unit.minimum`` the binding
floor is the real air-path captures, not the model: real blaster marks
come within 13 us of it, the model's closest within 39 us, and the
four blaster rows that do not read are refused there. Those rows are
pinned exactly below.

The index's own-cell rate is printed (``test_the_table``), not
asserted: it moves with the protocol library, which closes the
normalized tier to a press it decodes.
"""
from __future__ import annotations

import collections
import dataclasses
import datetime
import functools
import gzip
import hashlib
import json
import types

import pytest

from custom_components.hair import field_readers as fr
from custom_components.hair import identity as idm
from custom_components.hair.event_parser import EventParser
from custom_components.hair.matrix_listener import _coords, build_cell_index
from custom_components.hair.signal_monitor import normalize
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix, cell_key

from .conftest import real_air_missing
from .merged_group_shapes import FIXTURES, PACKS, map_split, press_identity
from .test_cell_index_shared_keys import _pack_matrix
from .test_daikin152_traits import CAPTURE as DAIKIN152_CAPTURE
from .test_identity_round import _flipper_presses
from .test_matrix_listener import _air_captures, _air_code, _air_matrix, _heard
from .test_read_bytes_identity import _air

pytestmark = pytest.mark.real_air

#: The presses of the model, per transmitter. ESPHome 0, 3, 4 and 19
#: cover marks 0.83 and 0.95 and spaces 1.00 and 1.12; Broadlink 0, 2,
#: 3 and 7 cover all three mark factors, and 3 and 7 are the model's
#: two glitched presses. The set is part of the model: changing it
#: moves ``MODEL_DIGEST`` as well as the figures.
PRESSES = {"esphome": (0, 3, 4, 19), "broadlink": (0, 2, 3, 7)}

#: The receiver idles every press and piece is also closed at, in
#: microseconds: ESPHome's default ``idle`` (10 ms, the stock Athom
#: package) and the value the ESPHome configs ship since #196 (80 ms).
#: Part of the model: changing it moves ``MODEL_DIGEST``.
CLOSINGS = (10_000, 80_000)

#: sha256 over ``_press`` for the first cell of every pack at every
#: chosen press, each also re-closed at every idle in ``CLOSINGS``. A
#: change to ``_air``, the salt, the press set or the closing fails here
#: as a model change, never as fifteen map changes.
MODEL_DIGEST = (
    "3432b2d499b58f91e6f0af90f3622388"
    "73902c5ddceaa359dcb933e8873dddd5"
)

REMEASURE_MAP = (
    "the map changed: re-measure, since a window patch moves this line "
    "and resets this family's comb attestations"
)
REMEASURE_PACK = (
    "the pack changed: re-measure, and check that the lattice is the one "
    "you meant to measure"
)


# ---------------------------------------------------------------------------
# The model
# ---------------------------------------------------------------------------


def _norm(pronto: str) -> str:
    return " ".join(pronto.split()).upper()


def _salt(pronto: str) -> str:
    return hashlib.sha256(_norm(pronto).encode()).hexdigest()[:16]


def _press(pronto: str, press: int, transmitter: str) -> tuple[str, bool]:
    """One press of ``pronto`` off the air, seeded per code."""
    return _air(pronto, press, transmitter, salt=_salt(pronto))


def _closed(pronto: str, idle_us: int) -> str:
    """``pronto`` with its closing space set to a receiver's idle: what a
    receiver with that ``idle`` hands over for the same burst."""
    words = pronto.split()
    tick = int(words[1], 16) * fr._PRONTO_TICK_US
    words[-1] = f"{round(idle_us / tick):04X}"
    return " ".join(words)


def _words(pronto: str) -> list[int]:
    return [int(w, 16) for w in pronto.split()]


def _read_train(pronto: str) -> list[int]:
    """The train ``read_code`` walks: trailing Pronto zeros removed and
    nothing else. Not ``identity._stripped``, which also drops the
    closing space (identity's rule, not the reader's)."""
    train = fr.pronto_microseconds(pronto)
    while train and train[-1] == 0:
        train.pop()
    return train


def _cut_points(pronto: str, gap_us: float) -> frozenset[int]:
    """Pair indices at which the FILE code closes a frame at the gap."""
    words = _words(pronto)
    tick = words[1] * fr._PRONTO_TICK_US
    body = words[4:]
    return frozenset(
        i // 2 for i in range(0, len(body) - 1, 2)
        if body[i + 1] * tick >= gap_us
    )


def _cut(pronto: str, points: frozenset[int]) -> list[str]:
    """``pronto`` cut after each pair index in ``points``, each piece
    keeping the space that closed it."""
    words = _words(pronto)
    head, body = words[:4], words[4:]
    pieces: list[list[int]] = []
    current: list[int] = []
    for i in range(0, len(body) - 1, 2):
        current += [body[i], body[i + 1]]
        if i // 2 in points:
            pieces.append(current)
            current = []
    if current:
        pieces.append(current)
    return [
        " ".join(f"{w:04X}" for w in [head[0], head[1], len(p) // 2, 0, *p])
        for p in pieces
    ]


def _variants(cell_pronto: str, heard: str, gap_us: float) -> list[tuple[str, str]]:
    """``[("whole", press), ("piece", piece), ...]``: the press, then its
    pieces when the file code splits."""
    points = _cut_points(cell_pronto, gap_us)
    if not points:
        return [("whole", heard)]
    assert len(_words(heard)) == len(_words(cell_pronto)), "the model moved a pair"
    pieces = _cut(heard, points)
    if len(pieces) < 2:
        return [("whole", heard)]
    return [("whole", heard), *(("piece", p) for p in pieces)]


# ---------------------------------------------------------------------------
# Packs, maps, indexes
# ---------------------------------------------------------------------------


def _packs() -> list[str]:
    return sorted(
        p.stem for p in PACKS.glob("*.json") if ".defects" not in p.name
    )


def _maps() -> dict[str, fr.FieldMap]:
    return {m.protocol_id: m for m in fr.library()}


@functools.cache
def _matrix(pid: str) -> ClimateMatrix:
    return _pack_matrix(f"{pid}.json")


@functools.cache
def _index(pid: str):
    return build_cell_index(_matrix(pid))


def _fields(field_map: fr.FieldMap, frames) -> tuple:
    reading = fr.Reading(field_map.protocol_id, tuple(map(tuple, frames)))
    return tuple(fr.read_field(reading, spec) for spec in field_map.fields)


@functools.cache
def _global_keys() -> dict[str, frozenset[tuple[str, str]]]:
    """Every pack cell's read key: ``{key: {(pack, cell key)}}``."""
    out: dict[str, set] = collections.defaultdict(set)
    for pid in _packs():
        for cell in _matrix(pid).cells:
            key = EventParser.pronto_read_key(cell.pronto)
            if key is not None:
                out[key].add((pid, cell_key(cell)))
    return {k: frozenset(v) for k, v in out.items()}


def _sharing(pid: str) -> frozenset[str]:
    """The families that share a settings frame with ``pid``, itself
    included: a key one of them holds is not a wrong key for it."""
    out = {pid}
    for members in idm.shared_settings_frames().values():
        families = {family for family, _ in members}
        if pid in families:
            out |= families
    return frozenset(out)


def _hit_coords(hit) -> tuple:
    return (hit.mode, hit.fan, hit.swing,
            None if hit.temp is None else float(hit.temp))


# ---------------------------------------------------------------------------
# Where a press stops: inside the walk, or after it
# ---------------------------------------------------------------------------
#
# The walk's own reason comes from ``field_readers.walk_refusal``. What
# happens after the walk (the layout, the identity bytes, the half-press
# licence, integrity; for the key, ``read_bytes_hash``'s three answers)
# is re-derived here from the reader's and identity's own helpers, and
# checked on EVERY press against ``read_code`` and ``read_bytes_hash``,
# so the re-derivation cannot drift from what it describes.


def _walk_reason(timing: fr.FrameTiming, why: fr.WalkRefusal) -> str:
    """A refusal inside the walk, named for the report. Naming only: the
    walk has no header rule, so a header outside its windows refuses as
    the first bit of its frame."""
    where = f"f{why.frame}"
    if why.bit == 0 and timing.header_mark.holds(why.mark_us) \
            and not timing.header_space.holds(why.space_us):
        return f"header space {where}"
    if why.bit == 0 and not timing.header_mark.holds(why.mark_us) \
            and why.mark_us > 2 * timing.unit.nominal:
        return f"header mark {where}"
    if why.window == "unit":
        half = "mark" if timing.classify == "space" else "space"
        return f"unit ({half}) {where}"
    carrier = why.space_us if timing.classify == "space" else why.mark_us
    if carrier > timing.one.nominal:
        side = "above one"
    elif carrier < timing.zero.nominal:
        side = "below zero"
    else:
        side = "between zero and one"
    return f"carrier {side} {where}"


def _read_stage(field_map: fr.FieldMap, train: list[int],
                why: fr.WalkRefusal | None) -> tuple[str, str]:
    """``(where, reason)`` for the pack's own map: ``("reads", ...)``,
    ``("walk", ...)`` or ``("after", ...)``, the way ``read_code`` goes
    for this map."""
    if why is not None:
        return "walk", _walk_reason(field_map.timing, why)
    frames, failed = fr.read_frames(field_map.timing, train)
    assert not failed
    laid = fr.aligned_frames(field_map, frames)
    if laid is not None:
        decoded = [fr.bits_to_bytes(f, field_map.bit_order) for f in laid]
        if not fr._matches_identity(field_map, decoded):
            return "after", "identity bytes"
        return "reads", "whole layout"
    if fr._matches_repeat(field_map, frames):
        decoded = [fr.bits_to_bytes(f, field_map.bit_order) for f in frames]
        if not fr._matches_identity(field_map, decoded):
            return "after", "identity bytes (half press)"
        if not fr._payload_holds(field_map, decoded):
            return "after", "integrity (half press)"
        return "reads", "half press"
    declared = len(field_map.frame_layout)
    if len(frames) < declared:
        return "after", "layout: fewer frames"
    if len(frames) > declared:
        return "after", "layout: more frames"
    return "after", "layout: frame width"


def _key_stage(timings: list[int]) -> tuple[str, str | None]:
    """``(stage, key)``: ``read_bytes_hash`` re-derived, with the stage
    that answered or ended it."""
    train = idm._stripped(timings)
    if not train:
        return "no train", None
    walked: dict[str, tuple] = {}
    for field_map in fr.library():
        if field_map.protocol_id not in idm.READ_BYTES_VERIFIED:
            continue
        if fr.walk_refusal(field_map.timing, train) is not None:
            continue
        frames, places, _failed = fr.read_frames_positioned(
            field_map.timing, train
        )
        walked[field_map.protocol_id] = (field_map, frames)
        laid = fr.aligned_positioned(field_map, frames, places)
        if laid is None:
            continue
        decoded = [fr.bits_to_bytes(f, field_map.bit_order) for f in laid[0]]
        if not fr._matches_identity(field_map, decoded):
            continue
        if not idm._setting_rules_hold(field_map, decoded):
            return "after: integrity", None
        shared = idm._shared_group_of(field_map.protocol_id)
        if shared is not None:
            signature, members = shared
            key = idm.shared_frame_key(
                signature, members, decoded[field_map.setting_frames[0]]
            )
        else:
            key = idm.read_bytes_key(field_map, decoded)
        if key is None:
            return "after: a field unreadable", None
        return "answer 1: whole press", key
    groups = idm.shared_settings_frames()
    key = idm._lone_shared_frame_key(train, timings, groups)
    if key is not None:
        return "answer 2: shared frame", key
    got = idm._lone_family_frame_key(timings, walked, groups)
    if got is not None:
        return "answer 3: lone frame", got[0]
    if not walked:
        return "walk: every listed timing refused", None
    if any(len(frames) == 1 for _map, frames in walked.values()):
        return "after: lone frame, no state", None
    return "after: layout", None


def _key_timings(pronto: str) -> list[int]:
    """The timings ``EventParser.pronto_read_key`` hands the identity."""
    words = EventParser._parse_pronto_words(pronto)
    return [] if words is None else EventParser._pronto_us(words)


# ---------------------------------------------------------------------------
# The measurement
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class Figures:
    """One map's line. Every figure is an exact count."""

    version: str
    pack: str
    # (accurate reads, accurate presses, blaster reads, blaster presses)
    read: tuple[int, int, int, int] = (0, 0, 0, 0)
    # listed only: (accurate whole, accurate split, blaster whole, split)
    key: tuple[int, int, int, int] | None = None
    # (glitched presses, of them heard as their own cell or keyed)
    glitched: tuple[int, int] = (0, 0)
    wrong_key: int = 0
    wrong_state: int = 0
    heard_wrong: int = 0
    # ``read`` again, every press re-closed at each idle in ``CLOSINGS``
    # in turn: (accurate, blaster) per idle, in ``CLOSINGS`` order
    closed_read: tuple[int, ...] = (0, 0, 0, 0)
    # listed only: ``key`` again, re-closed, its four counts per idle
    closed_key: tuple[int, ...] | None = None
    # ``heard_wrong`` over every re-closed press and piece, every idle
    closed_heard_wrong: int = 0

    def line(self, pid: str) -> str:
        """The literal to paste into ``FIGURES``, dated today."""
        (version, pack, read, key, glitched, wrong_key, wrong_state,
         heard_wrong, closed_read, closed_key,
         closed_heard_wrong) = dataclasses.astuple(self)
        return (
            f'    "{pid}": (  # measured {datetime.date.today().isoformat()}\n'
            f'        "{version}", "{pack}",\n'
            f"        {read}, {key}, {glitched}, {wrong_key}, {wrong_state}, "
            f"{heard_wrong},\n"
            f"        {closed_read}, {closed_key}, {closed_heard_wrong},\n"
            f"    ),"
        )


@dataclasses.dataclass
class Audit:
    """What the harness reports but does not pin, and its self-checks."""

    # (accurate heard as own, accurate presses, blaster ..., ...),
    # unglitched whole presses through the pack's own index
    own_heard: tuple[int, int, int, int] = (0, 0, 0, 0)
    # {(shape, clean or glitched, where, reason): count}, own map
    stages: collections.Counter = dataclasses.field(
        default_factory=collections.Counter
    )
    # {(shape, clean or glitched, stage): count}, the read-key path
    key_stages: collections.Counter = dataclasses.field(
        default_factory=collections.Counter
    )
    walks: int = 0
    walks_refused: int = 0
    walk_disagreements: list = dataclasses.field(default_factory=list)
    stage_disagreements: list = dataclasses.field(default_factory=list)
    variants: int = 0


def _walk_agrees(field_map: fr.FieldMap, train: list[int], own: bool,
                 audit: Audit) -> fr.WalkRefusal | None:
    """``walk_refusal`` against ``read_frames_positioned`` on one train,
    recording any disagreement. Returns the refusal."""
    timing = field_map.timing
    why = fr.walk_refusal(timing, train)
    frames, places, failed = fr.read_frames_positioned(timing, train)
    audit.walks += 1
    audit.walks_refused += failed
    if (why is not None) != failed:
        audit.walk_disagreements.append((field_map.protocol_id, "verdict"))
        return why
    if why is not None:
        mark, space = abs(train[2 * why.pair]), abs(train[2 * why.pair + 1])
        carrier = space if timing.classify == "space" else mark
        other = mark if timing.classify == "space" else space
        consistent = (
            (why.mark_us, why.space_us) == (mark, space)
            and space < timing.gap_min
            and (why.window == "unit") == (not timing.unit.holds(other))
            and (why.window == "unit" or not (
                timing.zero.holds(carrier) or timing.one.holds(carrier)))
            and fr.walk_refusal(timing, train[:2 * why.pair]) is None
        )
        if not consistent:
            audit.walk_disagreements.append((field_map.protocol_id, "reason"))
    elif own:
        # The frames read are the frames the pairs carry: every bit sits
        # on the pair it names, in the window of its value.
        for frame, where in zip(frames, places, strict=True):
            for bit, pair in zip(frame, where, strict=True):
                mark, space = abs(train[2 * pair]), abs(train[2 * pair + 1])
                carrier = space if timing.classify == "space" else mark
                window = timing.one if bit else timing.zero
                if not window.holds(carrier) or (
                        bit and timing.zero.holds(carrier)):
                    audit.walk_disagreements.append(
                        (field_map.protocol_id, "frames"))
                    return why
    return why


@functools.cache
def measure(pid: str) -> tuple[Figures, Audit]:
    """Press every cell of ``pid``'s pack and count."""
    maps = _maps()
    field_map = maps[pid]
    path = PACKS / f"{pid}.json"
    matrix = _matrix(pid)
    index = _index(pid)
    listed = pid in idm.READ_BYTES_VERIFIED
    sharing = _sharing(pid)
    every_key = _global_keys()
    gap = field_map.timing.gap_min
    keys = {cell_key(c): EventParser.pronto_read_key(c.pronto) for c in matrix.cells}
    holders: dict[str, set] = collections.defaultdict(set)
    for cell in matrix.cells:
        if keys[cell_key(cell)] is not None:
            holders[keys[cell_key(cell)]].add(_coords(cell))
    group_of: dict[tuple, frozenset] = {}
    for group in index.groups.values():
        for member in group.members:
            group_of[member] = frozenset(group.members)

    fig = Figures(
        version=field_map.version,
        pack=hashlib.sha256(path.read_bytes()).hexdigest()[:12],
    )
    audit = Audit()
    read = collections.Counter()
    keyed = collections.Counter()
    heard_own = collections.Counter()
    closed_read = collections.Counter()
    closed_keyed = collections.Counter()
    glitched = glitched_found = 0
    for cell in matrix.cells:
        coords = _coords(cell)
        group = group_of.get(coords, frozenset({coords}))
        own_key = keys[cell_key(cell)]
        file_read = fr.read_code(cell.pronto)
        file_fields = (
            _fields(field_map, file_read.frames)
            if file_read.protocol_id == pid else None
        )
        for tx, presses in PRESSES.items():
            for press in presses:
                heard, is_glitched = _press(cell.pronto, press, tx)
                purity = "glitched" if is_glitched else "clean"
                found = whole_key = split_key = False
                for shape, variant in _variants(cell.pronto, heard, gap):
                    audit.variants += 1
                    whole = shape == "whole"
                    train = _read_train(variant)
                    own_why = None
                    for other in maps.values():
                        why = _walk_agrees(other, train, other is field_map, audit)
                        if other is field_map:
                            own_why = why

                    # The read: the window figure, and the state it reads.
                    reading = fr.read_code(variant)
                    reads = reading.protocol_id == pid
                    where, reason = _read_stage(field_map, train, own_why)
                    audit.stages[(shape, purity, where, reason)] += 1
                    if (where == "reads") != reads:
                        audit.stage_disagreements.append(
                            ("read", cell_key(cell), tx, press, shape, reason,
                             reading.protocol_id))
                    if whole and not is_glitched:
                        read[(tx, "n")] += 1
                        read[(tx, "read")] += reads
                    if reads and file_fields is not None:
                        values = _fields(field_map, reading.frames)
                        if any(v is not None and v != f
                               for v, f in zip(values, file_fields, strict=True)):
                            fig.wrong_state += 1

                    # The key, and whether anything else holds it.
                    key = EventParser.pronto_read_key(variant)
                    stage, derived = _key_stage(_key_timings(variant))
                    audit.key_stages[(shape, purity, stage)] += 1
                    if derived != key:
                        audit.stage_disagreements.append(
                            ("key", cell_key(cell), tx, press, shape, stage))
                    if key is not None:
                        packs = {p for p, _ in every_key.get(key, ())}
                        if key == own_key:
                            whole_key |= whole
                            split_key |= not whole
                            # The cell's own key: another pack may hold it
                            # only through the designed shared frame.
                            wrong = bool(packs - sharing)
                        else:
                            # Any other key names another state: held
                            # outside the cell's group, or by another pack,
                            # shared frame or not, it is wrong.
                            wrong = bool(holders.get(key, set()) - group
                                         or packs - {pid})
                        fig.wrong_key += wrong

                    # What the pack's own index hears.
                    identity = press_identity(variant)
                    hit = None if identity is None else index.match(*identity)
                    if hit is not None:
                        cell_hit = hit[0]
                        mine = cell_hit.power is None and (
                            _hit_coords(cell_hit) == coords
                            or coords in cell_hit.members
                        )
                        found |= mine
                        fig.heard_wrong += not mine
                        if whole and not is_glitched:
                            heard_own[tx] += mine
                if is_glitched:
                    glitched += 1
                    glitched_found += found or whole_key or split_key
                elif listed:
                    keyed[(tx, "whole")] += whole_key
                    keyed[(tx, "split")] += split_key
                # The same press and pieces, each re-closed at a
                # receiver's idle: read, key and hearing only. The walk
                # audit above runs on the file's own closing; these
                # trains differ from it only in their last space.
                for idle in CLOSINGS:
                    whole_key = split_key = False
                    for shape, variant in _variants(cell.pronto, heard, gap):
                        whole = shape == "whole"
                        variant = _closed(variant, idle)
                        if whole and not is_glitched:
                            closed_read[(idle, tx)] += (
                                fr.read_code(variant).protocol_id == pid)
                        key = EventParser.pronto_read_key(variant)
                        if listed and key is not None and key == own_key:
                            whole_key |= whole
                            split_key |= not whole
                        identity = press_identity(variant)
                        hit = None if identity is None else index.match(*identity)
                        if hit is not None:
                            cell_hit = hit[0]
                            fig.closed_heard_wrong += not (
                                cell_hit.power is None and (
                                    _hit_coords(cell_hit) == coords
                                    or coords in cell_hit.members))
                    if listed and not is_glitched:
                        closed_keyed[(idle, tx, "whole")] += whole_key
                        closed_keyed[(idle, tx, "split")] += split_key

    fig.read = (read[("esphome", "read")], read[("esphome", "n")],
                read[("broadlink", "read")], read[("broadlink", "n")])
    if listed:
        fig.key = (keyed[("esphome", "whole")], keyed[("esphome", "split")],
                   keyed[("broadlink", "whole")], keyed[("broadlink", "split")])
    fig.closed_read = tuple(
        closed_read[(idle, tx)] for idle in CLOSINGS for tx in PRESSES)
    if listed:
        fig.closed_key = tuple(
            closed_keyed[(idle, tx, shape)] for idle in CLOSINGS
            for tx in PRESSES for shape in ("whole", "split"))
    fig.glitched = (glitched, glitched_found)
    audit.own_heard = (heard_own["esphome"], read[("esphome", "n")],
                       heard_own["broadlink"], read[("broadlink", "n")])
    return fig, audit


#: One line per map, each dated the day it was measured:
#: (map version, pack sha256[:12], read, key, glitched, wrong_key,
#: wrong_state, heard_wrong, closed_read, closed_key,
#: closed_heard_wrong). See ``Figures`` for each figure.
FIGURES: dict[str, tuple] = {
    "AUX104": (  # measured 2026-10-06
        "d0935d54602a24a9", "b167a767d155",
        (480, 480, 240, 240), None, (240, 13), 0, 0, 0,
        (480, 240, 480, 240), None, 0,
    ),
    "CHIGO96B": (  # measured 2026-10-06
        "6430185d13ab50a0", "ea9789e58b54",
        (240, 240, 111, 120), None, (120, 0), 0, 0, 0,
        (240, 111, 240, 111), None, 0,
    ),
    "DAIKIN152": (  # measured 2026-10-06
        "ceb4988ec73d2731", "0a6885d0ca72",
        (240, 240, 115, 120), (240, 240, 115, 120), (120, 86), 0, 0, 0,
        (240, 115, 240, 115), (240, 240, 115, 120, 240, 240, 115, 120), 0,
    ),
    # closed_read at 10 ms is (0, 0): read_code walks the closing space
    # (the option A follow-up, left as is by ruling). No receiver hands
    # over this train: a 10 ms idle splits the press at its 29.7 ms gap,
    # and the pieces' keys are the closed_key figures.
    "DAIKIN216": (  # measured 2026-10-06
        "5d703155104b885f", "98b4048ab976",
        (800, 800, 396, 400), (800, 800, 396, 400), (400, 254), 0, 0, 0,
        (0, 0, 800, 396), (800, 800, 396, 400, 800, 800, 396, 400), 0,
    ),
    "FUJITSU128": (  # measured 2026-10-06
        "3170604d23b900ed", "ac0419b43ebb",
        (372, 480, 156, 240), None, (240, 108), 0, 0, 0,
        (372, 156, 372, 156), None, 0,
    ),
    "GREE": (  # measured 2026-10-06
        "780b814d907167e3", "01d505d7b5e2",
        (320, 320, 160, 160), None, (160, 44), 0, 1, 3,
        (320, 160, 320, 160), None, 6,
    ),
    "MHI152": (  # measured 2026-10-06
        "fabd77ead6afc643", "0459b8c87dfd",
        (320, 320, 159, 160), None, (160, 76), 0, 0, 0,
        (320, 159, 320, 159), None, 0,
    ),
    "MHI160": (  # measured 2026-10-06
        "bba131b4bff3d00e", "8f5fe6835017",
        (192, 192, 47, 96), None, (96, 9), 0, 0, 0,
        (192, 47, 192, 47), None, 0,
    ),
    "MHI48": (  # measured 2026-10-06
        "2337b9c498fee532", "fad45f1c35d0",
        (192, 192, 77, 96), None, (96, 18), 0, 0, 0,
        (192, 77, 192, 77), None, 0,
    ),
    "MIDEA_COOLIX": (  # measured 2026-10-06
        "d50eee7049af3556", "49009f52efca",
        (240, 240, 120, 120), None, (120, 33), 0, 0, 0,
        (240, 120, 240, 120), None, 0,
    ),
    "MITSUBISHI144": (  # measured 2026-10-06
        "89dde7274a96b5b4", "c89d24ffa929",
        (960, 960, 470, 480), (960, 960, 470, 480), (480, 480), 0, 0, 0,
        (960, 470, 960, 470), (960, 960, 470, 480, 960, 960, 470, 480), 0,
    ),
    "OEM112": (  # measured 2026-10-06
        "337f06d3bbbc3305", "ec42e36360eb",
        (960, 960, 478, 480), None, (480, 225), 0, 0, 0,
        (960, 478, 960, 478), None, 0,
    ),
    "PANASONIC216": (  # measured 2026-10-06
        "d2deab1e897d3667", "72d6013f1f7d",
        (155, 640, 96, 320), None, (320, 208), 0, 0, 0,
        (155, 96, 155, 96), None, 0,
    ),
    "TCL112": (  # measured 2026-10-06
        "d892bc53b040164d", "e760706aba0e",
        (800, 800, 395, 400), None, (400, 1), 0, 1, 0,
        (800, 395, 800, 395), None, 0,
    ),
    "ZHLT01": (  # measured 2026-10-06
        "6480fb092e637235", "06277c4470a8",
        (480, 480, 240, 240), None, (240, 0), 0, 0, 0,
        (480, 240, 480, 240), None, 0,
    ),
}


def check(pid: str, measured: Figures, literal: tuple) -> None:
    """The one comparison. The map version and the pack come first: a
    line measured on another map or another lattice says nothing."""
    version, pack = literal[:2]
    why = "; ".join(
        text for moved, text in (
            (measured.version != version, REMEASURE_MAP),
            (measured.pack != pack, REMEASURE_PACK),
        ) if moved
    )
    assert not why, (
        f"{pid}: map version {measured.version}, pack {measured.pack}; "
        f"{why}. Measured:\n{measured.line(pid)}"
    )
    assert dataclasses.astuple(measured) == tuple(literal), (
        f"{pid} moved with its map and pack unchanged: the reader, the "
        "identity (READ_BYTES_VERIFIED included), the cell index or the air "
        "model moved these counts. If test_the_model_is_the_model also "
        "fails, the model moved; otherwise this is a reading change and a "
        "regression unless the PR means it. Paste only with the cause "
        f"named:\n{measured.line(pid)}"
    )


# ---------------------------------------------------------------------------
# The floors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("pid", _packs())
def test_the_figures_hold(pid):
    check(pid, measure(pid)[0], FIGURES[pid])


def test_every_map_has_a_pack_and_a_line():
    maps, packs, lines = set(_maps()), set(_packs()), set(FIGURES)
    assert maps == packs == lines, (
        f"maps without a pack: {sorted(maps - packs)}; maps without a "
        f"line: {sorted(maps - lines)}; packs or lines without a map: "
        f"{sorted((packs | lines) - maps)}. A new map needs its field pack "
        "in fixtures/field-packs and a measured line in FIGURES (run "
        "test_the_table with -rP and paste its line); a pack or line whose "
        "map has gone goes with it"
    )


def test_every_listed_family_has_key_figures():
    listed = {pid for pid, line in FIGURES.items() if line[3] is not None}
    closed = {pid for pid, line in FIGURES.items() if line[9] is not None}
    assert closed == listed, (
        "key and closed_key go together: a listed family has both, any "
        f"other family neither (key: {sorted(listed)}, closed_key: "
        f"{sorted(closed)})"
    )
    verified = set(idm.READ_BYTES_VERIFIED)
    assert listed == verified, (
        f"on READ_BYTES_VERIFIED without key figures: "
        f"{sorted(verified - listed)}; with key figures but off the list: "
        f"{sorted(listed - verified)}. Joining or leaving the list moves "
        "the family's key figures: re-measure its line (test_the_table "
        "with -rP) and paste it"
    )


def test_a_raised_or_lowered_literal_fails():
    """Every count in a line, one up and one down, fails the same
    ``check`` the floor test runs. No re-measure: ``measure`` is cached."""
    pid = "PANASONIC216"
    measured = measure(pid)[0]
    line = dataclasses.astuple(measured)
    check(pid, measured, line)
    tried = 0
    for slot, value in enumerate(line):
        if isinstance(value, str) or value is None:
            continue
        counts = [value] if isinstance(value, int) else list(value)
        for at in range(len(counts)):
            for step in (1, -1):
                moved = list(counts)
                moved[at] += step
                literal = list(line)
                literal[slot] = moved[0] if isinstance(value, int) else tuple(moved)
                with pytest.raises(AssertionError):
                    check(pid, measured, tuple(literal))
                tried += 1
    assert tried == 2 * (4 + 2 + 3 + 2 * len(CLOSINGS) + 1)
    with pytest.raises(AssertionError, match="the map changed: re-measure"):
        check(pid, measured, ("another version", *line[1:]))
    with pytest.raises(AssertionError, match="the pack changed: re-measure"):
        check(pid, measured, (line[0], "another pack", *line[2:]))


def test_no_read_key_is_wrong():
    """On every map, glitched presses included: no press or piece forms
    a key that names another state, in its own pack or in any other. The
    designed shared settings frame lets another pack hold only the
    cell's own key."""
    assert {pid: measure(pid)[0].wrong_key for pid in _packs()} == dict.fromkeys(
        _packs(), 0)


def test_a_receivers_closing_space_keys_as_the_files_gap_does():
    """A capture's last space is its terminator, not data. Every listed
    family forms its key re-closed at each receiver idle in ``CLOSINGS``
    exactly as often as at the file code's own gap, whole and split.
    Before the closing-space round DAIKIN216 formed no key at 10 ms and
    DAIKIN152's pieces none either, while the fake-remote air bench's
    receiver (ESPHome's default idle) hands every capture over at 10 ms."""
    for pid in sorted(idm.READ_BYTES_VERIFIED):
        fig = measure(pid)[0]
        per_idle = {
            idle: fig.closed_key[4 * i:4 * i + 4]
            for i, idle in enumerate(CLOSINGS)
        }
        assert per_idle == dict.fromkeys(CLOSINGS, fig.key), (
            f"{pid}: key at the file's own gap {fig.key}, re-closed "
            f"{per_idle}. A receiver's idle changed what the read key "
            "sees: identity's train (identity._stripped) has to drop the "
            "capture's closing space before any map walks it"
        )


def _capture_path_identity(pronto: str) -> tuple:
    """A press as the box computes it: the receiver's timings, closing
    space included, through the native receiver path
    (``EventParser.parse_received_signal``) and ``normalize``. Not
    through ``ProntoCommand``, whose constructor drops the closing space
    the way every stored identity does."""
    timings = fr.pronto_microseconds(pronto)
    while timings and timings[-1] == 0:
        timings.pop()  # a receiver reports no zero-length space
    signal = types.SimpleNamespace(timings=timings, modulation=38000)
    n = normalize(EventParser.parse_received_signal(signal))
    return (n.decoded_fingerprint, n.sig_fp, n.byte_hash, n.norm_fp,
            n.decode_covers, n.raw_timings)


def test_the_harness_hears_as_the_capture_path_does():
    """``press_identity`` reaches identity through the stored (canonical)
    path; the box reaches it from the received Pronto, closing space and
    all. The two once disagreed on exactly the closing-space class, so
    every hearing figure here was blind to it. Over every press, piece
    and closing of the first four cells of every pack they must agree,
    or the harness measures a different road from the box's.

    The capture each hands ``CellIndex.match`` differs in form, the
    harness's Pronto against the box's received train, so for it the
    two must read as the same settings."""
    checked = 0
    for pid in _packs():
        gap = _maps()[pid].timing.gap_min
        for cell in _matrix(pid).cells[:4]:
            for tx, presses in PRESSES.items():
                for press in presses:
                    heard, _glitched = _press(cell.pronto, press, tx)
                    for _shape, variant in _variants(cell.pronto, heard, gap):
                        for pronto in (variant, *(_closed(variant, idle)
                                                  for idle in CLOSINGS)):
                            box = _capture_path_identity(pronto)
                            harness = press_identity(pronto)
                            where = (pid, cell_key(cell), tx, press)
                            assert box[:5] == harness[:5], where
                            assert fr.read_settings(box[5]) == (
                                fr.read_settings(harness[5])), where
                            checked += 1
    assert checked > 4000


#: Per map: how many of the pack's whole file codes run past 192 pulse
#: pairs, and how many of the longest captures a receiver with each
#: idle in ``CLOSINGS`` hands over do (a receiver splits a code at any
#: space at least its idle long). A classic ESP32 receiving with
#: ESPHome's default ``rmt_symbols: 192`` cuts every capture there: the
#: fake-remote air bench's Athom delivered 193 pairs of every longer
#: code. Measurement for the receiver docs, not an engine figure.
RECEIVER_BUFFER: dict[str, tuple[int, int, int]] = {
    "AUX104": (0, 0, 0),
    "CHIGO96B": (0, 0, 0),
    "DAIKIN152": (60, 60, 60),
    "DAIKIN216": (200, 0, 200),
    "FUJITSU128": (0, 0, 0),
    "GREE": (0, 0, 0),
    "MHI152": (0, 0, 0),
    "MHI160": (0, 0, 0),
    "MHI48": (0, 0, 0),
    "MIDEA_COOLIX": (0, 0, 0),
    "MITSUBISHI144": (240, 240, 240),
    "OEM112": (0, 0, 0),
    "PANASONIC216": (160, 160, 160),
    "TCL112": (200, 200, 200),
    "ZHLT01": (0, 0, 0),
}


def _receiver_buffer(pid: str) -> tuple[int, int, int]:
    cells = _matrix(pid).cells
    pairs = [sum(_words(c.pronto)[2:4]) for c in cells]
    return (
        sum(n > 192 for n in pairs),
        *(sum(max(int(p.split()[2], 16) for p in map_split(c.pronto, idle))
              > 192 for c in cells) for idle in CLOSINGS),
    )


def test_the_receiver_buffer_counts():
    assert {pid: _receiver_buffer(pid) for pid in _packs()} == RECEIVER_BUFFER


def test_the_wrong_hearings_and_states_are_the_known_ones():
    """Not an invariant: the base's measured defects, pinned so they can
    only move on purpose. GREE's three are glitched blaster presses the
    normalized tier hears as the neighbouring fan speed; GREE's and
    TCL112's one wrong state each is a frame shifted by a dropped first
    bit that still fits its layout."""
    heard = {pid: measure(pid)[0].heard_wrong for pid in _packs()}
    state = {pid: measure(pid)[0].wrong_state for pid in _packs()}
    closed = {pid: measure(pid)[0].closed_heard_wrong for pid in _packs()}
    assert {pid: n for pid, n in heard.items() if n} == {"GREE": 3}
    assert {pid: n for pid, n in state.items() if n} == {"GREE": 1, "TCL112": 1}
    # The same three GREE presses, once at each receiver idle: a closing
    # space neither causes a wrong hearing nor hides one.
    assert {pid: n for pid, n in closed.items() if n} == {
        "GREE": 3 * len(CLOSINGS)}


# ---------------------------------------------------------------------------
# The model stays the model
# ---------------------------------------------------------------------------


def _model_digest() -> str:
    digest = hashlib.sha256()
    for pid in _packs():
        first = _matrix(pid).cells[0].pronto
        for tx, presses in PRESSES.items():
            for press in presses:
                heard, glitched = _press(first, press, tx)
                digest.update(f"{pid}|{tx}|{press}|{glitched}|{heard}\n".encode())
                for idle in CLOSINGS:
                    digest.update(f"{idle}|{_closed(heard, idle)}\n".encode())
    return digest.hexdigest()


def test_the_model_is_the_model():
    assert _model_digest() == MODEL_DIGEST, (
        "the air model moved (_air, the salt, PRESSES or CLOSINGS): every "
        "line moves with it; re-measure them all and MODEL_DIGEST together, "
        "and say in the PR why the model changed"
    )


def _ratios(pronto: str, press: int, transmitter: str) -> list[float]:
    """The perturbation itself: heard over file, edge by edge, to one
    decimal. The trailing zero word (the Pronto terminator) is left out."""
    heard = _words(_press(pronto, press, transmitter)[0])[4:]
    return [round(h / f, 1)
            for h, f in zip(heard, _words(pronto)[4:], strict=True) if f]


def _glitch_at(pronto: str, press: int) -> list[int]:
    """The Broadlink edges the model glitched: no clean ratio leaves 0.47
    to 1.40, a glitch lands near 0.24 (a mark) or 7.8 (a space)."""
    return [i for i, r in enumerate(_ratios(pronto, press, "broadlink"))
            if r < 0.4 or r > 5]


def test_the_salt_takes_effect():
    """Two codes of one length take different air. The ratio of heard to
    file at each edge is the perturbation, whatever the edge's length:
    per-press seeding, salted with a constant or not at all, gives both
    codes the same ratios and the glitch at the same edge."""
    cells = _matrix("DAIKIN216").cells
    a, b = cells[0].pronto, cells[1].pronto
    assert len(a.split()) == len(b.split())
    for tx in PRESSES:
        ra, rb = _ratios(a, 0, tx), _ratios(b, 0, tx)
        same = sum(x == y for x, y in zip(ra, rb, strict=True))
        assert same < 0.9 * len(ra), (
            f"{tx}: {same} of {len(ra)} edge ratios coincide between two "
            "codes: the presses are not seeded per code")
    for press in (3, 7):
        assert _glitch_at(a, press), press
        assert _glitch_at(a, press) != _glitch_at(b, press), (
            f"broadlink press {press}: both codes glitch at the same edge")
    assert _press(a, 3, "broadlink") != _air(a, 3, "broadlink")


def test_glitch_cover_is_there():
    assert {3, 7} <= set(PRESSES["broadlink"])
    for pid in _packs():
        assert measure(pid)[0].glitched[0] > 0, pid


# ---------------------------------------------------------------------------
# The refusal reasons
# ---------------------------------------------------------------------------


def test_walk_refusal_agrees_with_the_walk():
    """Every map's walk over every press and piece of the harness: the
    same verdict as ``read_frames_positioned``, a reason that names the
    pair the walk stopped at, and on the pack's own map, frames whose
    every bit sits on the pair it names. Most walks are refused, so the
    agreement is not vacuous."""
    walks = refused = 0
    for pid in _packs():
        audit = measure(pid)[1]
        assert audit.walk_disagreements == [], pid
        walks += audit.walks
        refused += audit.walks_refused
    assert walks > 0
    assert refused > walks // 4


def test_the_refusal_stages_agree_with_the_reader():
    """The re-derived stage says "reads" exactly when ``read_code`` reads
    the family, and forms exactly the key ``read_bytes_hash`` forms, on
    every press and piece of every pack."""
    for pid in _packs():
        assert measure(pid)[1].stage_disagreements == [], pid


# ---------------------------------------------------------------------------
# The real captures
# ---------------------------------------------------------------------------
#
# The air-path rows are lone MITSUBISHI144 frames a real receiver cut at
# the real gap (tests/fixtures/air-path). The four blaster C2 rows that
# do not read are refused in the walk at pair 139, a mark under
# ``unit.minimum``: the model never produces a mark that short.

#: first_seen of the four blaster C2 rows that read as nothing, and the
#: (cell, tier) each is heard as on (the two-cell lattice, the 64-cell
#: bench lattice). None: heard as nothing.
UNREAD_ROWS: dict[str, tuple] = {
    "2026-08-17T22:02:24.937414+00:00": (("heat/low/20", 4), ("heat/auto/20", 4)),
    "2026-08-17T22:02:26.913326+00:00": (("heat/low/20", 4), ("heat/auto/20", 4)),
    "2026-08-17T22:02:39.161820+00:00": (None, None),
    "2026-08-17T22:02:41.143672+00:00": (("heat/low/20", 4), ("heat/auto/20", 4)),
}

#: The cell each file code is heard as: (two-cell lattice, 64-cell).
FILE_CELLS = {"C1": ("cool/auto/23", "cool/auto/23"),
              "C2": ("heat/low/20", "heat/auto/20")}


def _sg15h_matrix() -> ClimateMatrix:
    """The 64-cell bench lattice the air-path codes come from."""
    raw = json.loads(gzip.decompress(
        (FIXTURES / "air-path" / "sg15h-matrix.json.gz").read_bytes()
    ))
    cells = []
    for entry in raw["codes"]:
        for key in entry["keys"]:
            mode, fan, temp = key.split("/")
            cells.append(ClimateCell(mode=mode, fan=fan, swing=None,
                                     temp=float(temp), pronto=entry["pronto"]))
    return ClimateMatrix(
        min_temp=16.0, max_temp=31.0, precision=1.0,
        modes=sorted({c.mode for c in cells}),
        fan_modes=sorted({c.fan for c in cells}),
        swing_modes=[], off=raw["off"], cells=cells,
    )


def _heard_as(index, pronto: str) -> tuple | None:
    identity = press_identity(pronto)
    hit = None if identity is None else index.match(*identity)
    return None if hit is None else (hit[0].cell_key, hit[1])


@pytest.mark.parametrize("lattice", ["two-cell", "64-cell"])
def test_the_air_path_rows(lattice):
    column = 0 if lattice == "two-cell" else 1
    index = build_cell_index(
        _air_matrix() if lattice == "two-cell" else _sg15h_matrix()
    )
    timing = _maps()["MITSUBISHI144"].timing
    tally = collections.Counter()
    for code in ("C1", "C2"):
        file_key = EventParser.pronto_read_key(_air_code(code))
        assert file_key is not None
        assert _heard_as(index, _air_code(code)) == (
            FILE_CELLS[code][column], idm.TIER_BYTE_HASH)
        for row in _air_captures(code):
            pronto = _heard(row).code
            key = EventParser.pronto_read_key(pronto)
            heard = _heard_as(index, pronto)
            if row["first_seen"] in UNREAD_ROWS:
                assert (code, row["transmitter"]) == ("C2", "broadlink")
                assert fr.read_code(pronto).protocol_id is None
                assert key is None, row["first_seen"]
                why = fr.walk_refusal(
                    timing, _read_train(pronto))
                assert (why.pair, why.window) == (139, "unit")
                assert why.mark_us < timing.unit.minimum
                assert heard == UNREAD_ROWS[row["first_seen"]][column]
                tally["unread"] += 1
            else:
                assert key == file_key, row["first_seen"]
                assert heard == (FILE_CELLS[code][column], idm.TIER_BYTE_HASH)
                tally[row["transmitter"]] += 1
    assert tally == {"esphome": 28, "broadlink": 12, "inject": 2, "unread": 4}


def _real_presses() -> dict[str, list[str]]:
    """The handset presses and the DAIKIN152 capture, each with the
    pieces a receiver cutting at its family's gap hands over."""
    maps = _maps()
    out = {}
    presses = {f"flipper {name}": p for name, p in _flipper_presses().items()}
    presses["orthobot DAIKIN152"] = DAIKIN152_CAPTURE
    for name, pronto in presses.items():
        family = fr.read_code(pronto).protocol_id
        assert family is not None, name
        out[name] = [pronto, *map_split(pronto, maps[family].timing.gap_min)]
    return out


def test_the_handset_presses_and_the_daikin152_capture_are_heard_as_no_other_cell():
    """No lattice in the repo holds these states, so all they can show
    is that nothing else is heard: every press and piece is heard as
    nothing by every pack's index, and no pack cell holds their keys."""
    presses = _real_presses()
    assert {name: len(v) for name, v in presses.items()} == {
        "flipper POWER": 3, "flipper Off": 3, "orthobot DAIKIN152": 5}
    whole = {name: EventParser.pronto_read_key(v[0]) for name, v in presses.items()}
    assert whole == {
        "flipper POWER": "6a518f17015ba625",
        "flipper Off": "cacce556e03b69d2",
        "orthobot DAIKIN152": "48f8ed8f36faeadc",
    }
    every_key = _global_keys()
    identities = [
        press_identity(p) for variants in presses.values() for p in variants
    ]
    for variants in presses.values():
        for pronto in variants:
            key = EventParser.pronto_read_key(pronto)
            assert key is None or key not in every_key
    for pid in _packs():
        index = _index(pid)
        for identity in identities:
            assert identity is None or index.match(*identity) is None, pid


# ---------------------------------------------------------------------------
# The guard and the table
# ---------------------------------------------------------------------------


def test_a_ci_run_without_the_harness_fails():
    class Item:
        def __init__(self, marked, nodeid=""):
            self.marked = marked
            self.nodeid = nodeid

        def get_closest_marker(self, name):
            return object() if self.marked and name == "real_air" else None

    ci = {"GITHUB_ACTIONS": "true"}
    assert real_air_missing([Item(False)], ci) is not None
    assert real_air_missing([], ci) is not None
    assert real_air_missing([Item(False), Item(True)], ci) is None
    assert real_air_missing([Item(False)], {}) is None
    # Some of the harness deselected (a -k, -m or --deselect that keeps
    # one of its tests) fails as well; all of it selected passes.
    both = [Item(True, "floor[A]"), Item(True, "floor[B]")]
    collected = ["floor[A]", "floor[B]"]
    assert real_air_missing(both, ci, collected) is None
    assert "floor[B]" in real_air_missing(both[:1], ci, collected)
    assert real_air_missing(both[:1], {}, collected) is None


def table() -> str:
    """The per-map table: the pinned figures, and beside them the index's
    own-cell rate and where refusals happen, unpinned."""
    rows = [
        "| map | read acc | read bl | key | glitched (found) | wrong key "
        "| wrong state | heard wrong | heard own acc | heard own bl "
        "| clean whole refused: walk / after | closed read | closed key "
        "| closed heard wrong | over 192 pairs: whole / at each idle |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for pid in _packs():
        fig, audit = measure(pid)
        walk = sum(n for (s, p, w, _r), n in audit.stages.items()
                   if (s, p, w) == ("whole", "clean", "walk"))
        after = sum(n for (s, p, w, _r), n in audit.stages.items()
                    if (s, p, w) == ("whole", "clean", "after"))
        a, n, b, m = fig.read
        ha, _, hb, _ = audit.own_heard
        rows.append(
            f"| {pid} | {a}/{n} | {b}/{m} | {fig.key or '-'} | "
            f"{fig.glitched[0]} ({fig.glitched[1]}) | {fig.wrong_key} | "
            f"{fig.wrong_state} | {fig.heard_wrong} | {ha}/{n} | {hb}/{m} | "
            f"{walk} / {after} | {fig.closed_read} | {fig.closed_key or '-'} | "
            f"{fig.closed_heard_wrong} | "
            f"{' / '.join(map(str, _receiver_buffer(pid)))} |"
        )
    return "\n".join(rows)


def test_the_table():
    """Printed (``-rP``), never asserted: the table, and every line as
    measured on this run, so three runs or two legs compare as text."""
    print()
    print(table())
    print(f"MODEL_DIGEST {_model_digest()}")
    for pid in _packs():
        print(measure(pid)[0].line(pid))
