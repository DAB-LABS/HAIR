"""The hear side of a climate matrix (signpost 4, Track M).

A Remote minted from a matrix wig (or through either mirror door)
carries a COPY of the lattice, keyed by its own id in the same
``hair/matrices/`` folder the device side uses. The device's matrix is
the one it SENDS from; the remote's is the one it HEARS on. This module
owns the remote side of that file: reading it, holding it, matching
captured frames against its cells, and recording what was heard.

WHY THIS IS NOT A TRIGGER LOOKUP. A lattice is thousands of states, and
the lattice never auto-mints rows (the matrix rule) -- so cells cannot
live in ``IRTrigger`` or in ``get_triggers_for_signal`` without turning
a linear scan over a handful of triggers into a scan over thousands of
cells on every capture. Instead each matrix remote gets its own reverse
index, built once from its file and consulted right after the trigger
match, under the same not-echo gate. A cell that a user deliberately
promotes to a trigger is a plain trigger from that moment and matches
through the ordinary path; this listener stays the always-on reading of
the whole lattice.

IDENTITY TIERS, the one that is deliberately missing, and the one added
last. Cells are indexed by decoded fingerprint, by ``(S/L fingerprint,
byte_hash)``, and by ``byte_hash`` alone -- the order
``HAIRStore.match_command`` and ``pin_bindings`` already use. The
bare-fingerprint tier is NOT built here at all. AC frames are long state
blobs whose S/L patterns are near neighbours across a whole branch, so a
fingerprint-only match would report the wrong cell -- and reporting the
wrong state is worse than reporting none, because a wrong state is a
plausible lie the card would show with full confidence.

Beneath those sits the receiver-tolerant tier (2026-08-18), because the
byte hash does not survive a real air path for a lattice code: twenty
presses of one Mitsubishi cell through a microsecond-accurate
transmitter gave twenty byte hashes, none of them the file's. A cell is
always file-sourced, so every cell is indexed there; the gates are that
the CAPTURE must have decoded as nothing, and that a normalized value
two genuinely different cells claim is dropped rather than answered.
identity.py's normalized-fingerprint block carries the measurement.

THE INDEX BUILDS IN THE BACKGROUND, ONCE. Deriving identity per cell
runs the same decode the Sniffer runs: measured on the bench,
3.7 ms/cell on a Mitsubishi lattice and 0.8 ms/cell on a Gree one (the
cost tracks frame length, not cell count), so the census worst case of
2,689 cells is seconds of work. The build is dispatched as a task and
the frames that arrive meanwhile simply do not match (logged once per
remote); awaiting it on the capture path would delay a capture by
seconds to save one press.

That cost is paid ONCE, not once per boot: the built index is written
beside the matrix file as ``<id>.index.json`` and reloaded on the next
start, so restarts are instant. The stored index names the matrix it
came from by content hash and records the display unit its names were
built in, so a rewritten lattice or a flipped unit system rebuilds
instead of being believed. Every door that writes, copies or deletes a
matrix drops the index too.

AND IT IS PAID AT SETUP, NOT ON THE FIRST FRAME (0.10.1 item 3). The
lazy path above still exists, but nothing should ever need it at boot:
``async_warm_indexes`` runs once during setup, strictly before any
receiver is subscribed, so the first press after a restart matches.
Reading a stored index is 6 to 12 ms, which sounds like a race nobody
loses -- but a single-frame file-sourced code pressed in the first
moments after boot fell inside it, and a two-frame press only matched
because its SECOND frame arrived after the read. The lazy path stays as
the fallback for a remote minted at runtime, and the mint doors warm
their new lattice themselves so even that one rarely runs.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from .const import EVENT_STATE_HEARD, MATRIX_STATE_DEDUP_WINDOW_S
from .identity import (
    TIER_BYTE_HASH,
    TIER_DECODED,
    TIER_NORM_FP,
    NormFpIndex,
    tier_name,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .models import TriggerRemote
    from .storage import HAIRStore
    from .trigger_manager import TriggerManager
    from .wig_format import ClimateMatrix

_LOGGER = logging.getLogger(__name__)

# One capture's identity, in ``CellIndex.match`` order: decoded
# fingerprint, S/L fingerprint, byte hash, normalized fingerprint, and
# the decode's coverage. Carried past the hearing so a pinned Device
# can be asked "which of YOUR cells is this frame?" when its lattice
# spells the same state with different words -- and so it can be asked
# with the same tolerance, and the same scepticism, the hearing had.
#: One capture's identity as ``CellIndex.match`` takes it: the four
#: tier values, then whether the decode explained the whole capture.
#: The last field joined the tuple on 2026-09-25; a decode that covers
#: only part of a capture is not that capture's identity.
_Identity = tuple[
    str | None, str | None, str | None, str | None, bool | None
]

#: "No cell has claimed this key yet", distinct from a cell that
#: claimed it with a discriminator of None.
_UNCLAIMED = object()


class _StateOrCode:
    """The refusal discriminator for a READ-BYTES cell.

    Two claimants of one key are the same thing when they are the same
    STATE -- two copies that differ only in a clock or timer byte (owner
    ruling 2026-09-30) -- or when they carry the same CODE: a file that
    stores one code under several labels, as dry and fan_only do when
    the unit ignores temperature (owner ruling 2026-09-30, measured on
    the #183 wig: 1,344 of 2,016 cells in 64 such groups). Either one
    merges; only a pair that differs in both is refused. Deliberately
    not an equivalence relation, so it is never hashed.
    """

    __slots__ = ("code", "state")
    __hash__ = None  # type: ignore[assignment]

    def __init__(self, state: tuple, code: object) -> None:
        self.state = state
        self.code = code

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _StateOrCode):
            return NotImplemented
        return self.state == other.state or self.code == other.code

    def __ne__(self, other: object) -> bool:
        equal = self.__eq__(other)
        return equal if equal is NotImplemented else not equal


@dataclass(frozen=True)
class CellHit:
    """One heard state, resolved to the lattice.

    Carries both the key (the fittings-ledger form, "cool/auto/23") and
    the display name, plus the coordinates themselves: the card rings
    the heard branch dimension by dimension, so it needs the parts, not
    only the string. ``power`` is set for the matrix's own off/on codes
    and None for every climate cell -- the two are mutually exclusive
    by construction, which is what makes the card's rest rings
    mutually exclusive without a rule of their own.
    """

    cell_key: str
    cell_name: str
    power: str | None = None
    mode: str | None = None
    fan: str | None = None
    swing: str | None = None
    temp: float | None = None
    sl_pattern: str | None = None
    # Which lattice this state belongs to, None for the main one
    # (extras-in-the-matrix-card.md item 5c). The coordinates alone
    # cannot say: every coordinate the lattices share carries a
    # different code, which is exactly why matching by identity finds
    # the right one and why the answer has to travel with the hit.
    axis: str | None = None
    lattice: str | None = None
    # WHAT THE PRESS DOES NOT PIN DOWN. Empty for a code the file
    # stores once. For a code it stores under several settings (every
    # temperature of dry, when the unit ignores temperature there), the
    # dimensions those cells disagree on, each with its sorted values:
    # ``(("temp", (18.0, ..., 30.0)),)``. The coordinates above stay the
    # representative's, the cell the index met last, because triggers,
    # the dedup window and the "+ Trigger" door all key on them; this is
    # what stops the hearing surfaces passing the representative's
    # temperature off as the one pressed.
    spanned: tuple[tuple[str, tuple], ...] = ()
    # The coordinates of every cell in that group, one tuple shared by
    # every hit of the group. On the hit because nothing else on it
    # names its group once the index has come back off disk, and the
    # card needs them to ring only the tiles that really are this code.
    members: tuple[tuple, ...] = ()


#: The four dimensions of a cell, in the order coordinates are written.
_DIMS = ("mode", "fan", "swing", "temp")


def _coords(cell: Any) -> tuple:
    """A cell's coordinates as a group records them: temperature as a
    float, so a coordinate read back from JSON compares equal."""
    temp = cell.temp
    return (cell.mode, cell.fan, cell.swing,
            None if temp is None else float(temp))


def _sorted_values(values: Any) -> tuple:
    """A dimension's values in one fixed order, None last.

    The order has to be the same in memory and after a round trip
    through the stored index, and a None can sit beside strings or
    numbers when one member lacks the dimension, which a bare sort
    would refuse to compare.
    """
    return tuple(sorted(
        set(values), key=lambda v: (v is None, "" if v is None else v),
    ))


def spanned_of(members: Any) -> tuple[tuple[str, tuple], ...]:
    """The dimensions a set of member coordinates disagrees on, with
    each dimension's values."""
    rows = list(members)
    out = []
    for position, dim in enumerate(_DIMS):
        values = _sorted_values(row[position] for row in rows)
        if len(values) > 1:
            out.append((dim, values))
    return tuple(out)


def spanned_dict(spanned: Any) -> dict[str, list]:
    """``spanned`` as every surface outside the hit renders it:
    ``{"temp": [18.0, ..., 30.0]}``. JSON-native, so it can sit in a
    stored index, an event, ``last_heard`` and a send's cell dict."""
    return {dim: list(values) for dim, values in spanned}


def _spanned_from_dict(rendered: Any) -> tuple[tuple[str, tuple], ...]:
    """The tuple form back from the dict rendering (a stored row)."""
    if not rendered:
        return ()
    return tuple(
        (dim, tuple(
            float(v) if dim == "temp" and v is not None else v
            for v in rendered[dim]
        ))
        for dim in _DIMS
        if dim in rendered
    )


@dataclass(frozen=True)
class CellGroup:
    """The cells of one lattice that carry one code.

    What a file does when the unit ignores a setting: dry stored once
    per temperature with the same code each time. Built with the index
    and looked up from any member cell's TEXT, by
    ``CellIndex.groups[(lattice, digest)]``; see ``build_cell_index``.

    ``lattice`` is None for the main lattice and ``(axis, key)`` for an
    extra. ``members`` is every member's coordinates, in lattice order.
    ``digests`` is every member's text digest, which can be several:
    the group is HAIR's quantized idea of one code, so a lattice built
    from captures holds one code as several texts. ``full_branches`` is
    every ``(mode, fan, swing)`` branch all of whose cells are members,
    which is where the unit demonstrably ignores temperature.
    """

    lattice: tuple[str, str] | None
    members: tuple[tuple, ...]
    digests: frozenset[str]
    full_branches: frozenset[tuple]


@dataclass
class CellIndex:
    """Reverse index over one lattice's cells, by identity tier.

    The lattice twin of ``pin_bindings.DeviceCommandIndex``. No
    ``fp_legacy`` map exists here on purpose -- see the module
    docstring.
    """

    decoded: dict[str, CellHit] = field(default_factory=dict)
    fp_bytehash: dict[tuple[str, str | None], CellHit] = field(
        default_factory=dict
    )
    bytehash: dict[str, CellHit] = field(default_factory=dict)
    # The receiver-tolerant tier (2026-08-18). A lattice cell is always
    # file-sourced, so every cell earns it; the gate that matters is on
    # the capture side, in match().
    norm_fp: NormFpIndex = field(default_factory=NormFpIndex)
    # Every merged group, reachable from any member cell by
    # ``(lattice, digest of its normalized Pronto)``: None for the main
    # lattice and ``(axis, key)`` for an extra, since an extra can hold
    # a main cell's exact text. One shared ``CellGroup`` per group. The
    # send side reads this on the DEVICE's own index, never the
    # remote's: what was sent is the device's fact.
    groups: dict[tuple, CellGroup] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return bool(
            self.decoded or self.fp_bytehash or self.bytehash or self.norm_fp
        )

    def match(
        self,
        decoded_fingerprint: str | None,
        signal_fingerprint: str | None,
        byte_hash: str | None,
        norm_fp: str | None = None,
        decode_covers: bool | None = None,
    ) -> tuple[CellHit, int] | None:
        """The cell this capture is and the tier that said so, or None.

        Same tier order as every other matcher in HAIR, minus the bare
        fingerprint: an AC blob's S/L pattern is a near neighbour of its
        whole branch, so a fingerprint-only match would report the wrong
        cell, and a wrong state is a plausible lie the card would show
        with full confidence.

        The normalized fingerprint is last, and only for a capture
        NOTHING could decode. A frame that decoded has already been
        answered by tier 1 -- if its decoded identity is not in this
        lattice, the honest answer is that this lattice does not hold
        it, not that something of a similar shape does.

        A NON-COVERING DECODE IS NOT AN IDENTITY (owner bench
        2026-09-25). ``decode_covers is False`` means the decoder
        explained a fraction of the capture and nothing about the rest:
        every DAIKIN216 code reads as the same
        ``KASEIKYO64:0xda11:0x20f000000002`` because the decoder only
        ever reads the constant frame 0. Tier 1 is skipped for such a
        capture, and -- because the decode told us nothing -- the
        normalized tier is allowed to answer, which the old "only if
        nothing decoded" wording would have blocked.
        """
        skipped_decode = decode_covers is False
        if (
            decoded_fingerprint
            and not skipped_decode
            and decoded_fingerprint in self.decoded
        ):
            return (self.decoded[decoded_fingerprint], TIER_DECODED)
        if signal_fingerprint or byte_hash:
            hit = self.fp_bytehash.get((signal_fingerprint, byte_hash))
            if hit is not None:
                return (hit, TIER_BYTE_HASH)
        if byte_hash is not None:
            hit = self.bytehash.get(byte_hash)
            if hit is not None:
                return (hit, TIER_BYTE_HASH)
        if norm_fp and (not decoded_fingerprint or skipped_decode):
            hit = self.norm_fp.get(norm_fp)
            if hit is not None:
                return (hit, TIER_NORM_FP)
        return None


def build_cell_index(
    matrix: ClimateMatrix, display_unit: str | None = None
) -> CellIndex:
    """Index every cell (and both power codes) by identity.

    Pure and blocking: callers run it in the executor. A cell whose
    Pronto does not validate is skipped -- it could never be heard
    anyway.

    NO TIER ANSWERS FOR TWO DIFFERENT CODES (owner bench 2026-09-25).
    Last write used to win on every tier, on the reasoning that two
    cells sharing a waveform ARE the same press and the file's later
    row is the one a send would use. The first half of that is still
    true and still honoured. The second half assumed a shared key meant
    a shared waveform, and on a Daikin lattice it does not: identity
    below is computed from frame 0 alone, so all 520 states of an
    FTXS50KVM share one decoded fingerprint, one S/L fingerprint and
    one byte hash, and "the file's later row" was the Off code, added
    after the cells. Every press of that handset reported Off, and a
    remote pinned to a Daikin device sent Off for every button.

    So every tier now applies the rule ``NormFpIndex`` already applied
    to its own: a key claimed by two cells whose WHOLE codes differ is
    poisoned and answers nothing, while a key two cells claim with the
    SAME code still resolves. ``whole_code_discriminator`` is what
    "same code" means here, and it is quantized, so a capture-built
    lattice holding one waveform twice still counts it once.

    The result for a Daikin is that nothing matches at all, which is
    the honest answer until payload-frame identity lands: better to
    hear nothing than to name a state nobody pressed.

    ONE IDENTITY FORM, and it is not the file's. ``wig_signal_identity``
    hashes the canonical (wire) Pronto -- see identity.py's
    canonical-form block for why a lattice code's trailing gap word does
    not survive the capture path, and what it cost before 2026-08-17.
    Do not add a second form here: if a cell ever fails to match a real
    frame, the answer is in that helper, not in another dict key.

    The normalized fingerprint is built from the cell's TIMINGS rather
    than its code text, and a value two genuinely different cells claim
    is dropped rather than won by whichever came last (identity.py's
    NormFpIndex). On the bench closet that costs a handful of lattices a
    handful of cells, and it is the price of never naming the wrong
    state.

    A KEY THAT MERGES A GROUP NAMES THE GROUP. A key several cells
    claim with the same code keeps the last of them, which is the right
    code and the wrong setting: a file stores dry once per temperature
    with one code when the unit ignores temperature there, so a dry
    press was heard as "dry / fan: auto / 30", whatever the handset
    showed, and a pinned unit's card moved to 30. Ten of the fifteen
    field packs do this somewhere. So after the cells are added, the
    cells of each lattice are grouped by the code they claimed under,
    and every stored hit of a group of two or more learns what the
    group spans and is named for it ("dry / fan: auto / 18-30"). Its
    coordinates and ``cell_key`` stay the representative's, so every
    key resolves exactly as it did and a trigger minted on the old name
    still fires. ``_attach_groups`` has the rules.
    """
    from .event_parser import EventParser
    from .identity import (
        canonical_pronto,
        norm_fingerprint,
        whole_code_discriminator,
    )
    from .wig_climate import (
        cell_display_name,
        spanned_display_name,
        state_display_name,
    )
    from .wig_format import cell_key
    from .wig_identity import wig_signal_identity

    index = CellIndex()
    # Which code claimed each tier key, and the keys two different codes
    # claimed. ``NormFpIndex`` keeps its own pair of these internally;
    # these are the same bookkeeping for the three plain dicts.
    claims: dict[str, dict[Any, Any]] = {
        "decoded": {}, "fp_bytehash": {}, "bytehash": {},
    }
    poisoned: dict[str, set] = {
        "decoded": set(), "fp_bytehash": set(), "bytehash": set(),
    }

    def _claim(
        tier: str, store: dict, key: Any, code: Any, hit: CellHit
    ) -> None:
        """Put ``hit`` under ``key``, unless two codes want that key."""
        if key in poisoned[tier]:
            return
        claimed = claims[tier].get(key, _UNCLAIMED)
        if claimed is not _UNCLAIMED and claimed != code:
            poisoned[tier].add(key)
            claims[tier].pop(key, None)
            store.pop(key, None)
            return
        claims[tier][key] = code
        store[key] = hit

    def _add(pronto: str | None, hit_factory: Any) -> tuple[CellHit, Any] | None:
        """Index one code; its hit and claim discriminator, or None."""
        if not pronto:
            return None
        identity = wig_signal_identity(pronto)
        if identity is None:
            return None
        # The diamonds show what was HEARD, so the pattern comes off
        # the canonical form too.
        hit = hit_factory(
            EventParser._pronto_sl_pattern(
                canonical_pronto(identity.pronto) or identity.pronto
            )
        )
        code: Any = whole_code_discriminator(
            identity.raw_timings,
            identity.byte_hash or identity.fingerprint,
        )
        # A READ-BYTES family names its state by what the map reads, so
        # the refusal asks "same state, or same code?" rather than "same
        # code?" alone: see ``_StateOrCode``. Asked of the whole code
        # only, two copies of one state that differ in a clock byte would
        # refuse each other and neither would ever be heard.
        read_key = EventParser.pronto_read_key(
            canonical_pronto(identity.pronto) or identity.pronto
        )
        if read_key is not None and read_key == identity.byte_hash:
            code = _StateOrCode(
                ("state", hit.lattice, hit.cell_key, hit.power), code,
            )
        # A DECODE THAT EXPLAINS PART OF THE CAPTURE IS NOT AN IDENTITY.
        # Indexing it would claim this cell IS that fingerprint, and on
        # a Daikin every cell would claim the same one.
        if identity.decoded_fingerprint and identity.decode_covers is not False:
            _claim(
                "decoded", index.decoded,
                identity.decoded_fingerprint, code, hit,
            )
        if identity.fingerprint:
            _claim(
                "fp_bytehash", index.fp_bytehash,
                (identity.fingerprint, identity.byte_hash), code, hit,
            )
        if identity.byte_hash is not None:
            _claim("bytehash", index.bytehash, identity.byte_hash, code, hit)
        index.norm_fp.add(
            norm_fingerprint(identity.raw_timings), code, hit,
        )
        return hit, code

    # What the merged groups are built from: every indexed cell by the
    # lattice it belongs to and the code it claimed under, and for each
    # hit the group it would belong to. The group is found from the hit
    # by that record, never by its coordinates: a lattice may hold two
    # cells at one coordinate with different codes, and a coordinate
    # lookup would hand one of them the other's group.
    claimed: dict[tuple, list[tuple[Any, CellHit]]] = {}
    hit_group: dict[int, tuple] = {}
    power_codes: set = set()

    def _member(lattice: tuple | None, cell: Any, added: Any) -> None:
        if added is None:
            return
        hit, code = added
        inner = _inner_code(code)
        if inner is None:
            return
        key = (lattice, inner)
        claimed.setdefault(key, []).append((cell, hit))
        hit_group[id(hit)] = key

    for cell in matrix.cells:
        added = _add(
            cell.pronto,
            lambda sl, cell=cell: CellHit(
                cell_key=cell_key(cell),
                cell_name=cell_display_name(
                    cell,
                    unit=matrix.unit,
                    display_unit=display_unit,
                    precision=matrix.precision,
                ),
                mode=cell.mode,
                fan=cell.fan,
                swing=cell.swing,
                temp=cell.temp,
                sl_pattern=sl,
            ),
        )
        _member(None, cell, added)
    # EXTRAS ARE HEARD TOO (item 5c). The index is built from
    # matrix.cells alone before this, so a handset sending an Eco state
    # raised no state_heard and drew no LAST HEARD row, while the card
    # could browse that state and mint a trigger on it -- a trigger
    # that would then never fire. Matching is by identity, and an
    # extras code never collides with a main-lattice one, so these rows
    # add reach without taking any away.
    #
    # ``cell_key`` stays the bare coordinate form here, unqualified:
    # it is the fittings-ledger key and it changes in the fitting plan,
    # not in this one. The lattice travels on its own two fields.
    for extra in getattr(matrix, "extras", None) or ():
        for cell in extra.cells:
            added = _add(
                cell.pronto,
                lambda sl, cell=cell, extra=extra: CellHit(
                    cell_key=cell_key(cell),
                    cell_name=cell_display_name(
                        cell,
                        unit=matrix.unit,
                        display_unit=display_unit,
                        precision=matrix.precision,
                        lattice=extra.key,
                    ),
                    mode=cell.mode,
                    fan=cell.fan,
                    swing=cell.swing,
                    temp=cell.temp,
                    axis=extra.axis,
                    lattice=extra.key,
                    sl_pattern=sl,
                ),
            )
            _member((extra.axis, extra.key), cell, added)
    for power, pronto in (("off", matrix.off), ("on", matrix.on)):
        added = _add(
            pronto,
            lambda sl, power=power: CellHit(
                cell_key=power,
                cell_name=state_display_name(power),
                power=power,
                sl_pattern=sl,
            ),
        )
        if added is not None:
            power_codes.add(_inner_code(added[1]))
    _attach_groups(
        index, matrix, claimed, hit_group, power_codes,
        lambda cell, spanned, lattice: spanned_display_name(
            cell,
            spanned,
            unit=matrix.unit,
            display_unit=display_unit,
            precision=matrix.precision,
            lattice=lattice,
        ),
    )
    return index


def _inner_code(code: Any) -> Any:
    """The whole-code discriminator itself, out of a read-bytes wrapper.

    ``_StateOrCode`` is deliberately unhashable, because "same state OR
    same code" is not an equivalence; the code inside it is a plain
    string, and same-code is the relation a merged group is made of.
    """
    return code.code if isinstance(code, _StateOrCode) else code


def _attach_groups(
    index: CellIndex,
    matrix: Any,
    claimed: dict[tuple, list[tuple[Any, CellHit]]],
    hit_group: dict[int, tuple],
    power_codes: set,
    name: Any,
) -> None:
    """Record every merged group, and tell each stored hit its own.

    A group is the cells of ONE lattice that claimed under one code, so
    an extra holding a main cell's code never joins a main group: the
    two lattices are different codes at every shared coordinate by
    construction, and a coincidence between them is not a setting the
    unit ignores. A code the matrix also uses as Off or On is not a
    group either; a cell spelled with the Off bytes is malformed, and
    its stored hit is Off's, as it was.

    Each stored hit of a group is replaced once, memoized by the object
    it replaces, so a key that stores a different representative than
    another key of the same group (a capture-built lattice, whose S/L
    fingerprints differ from capture to capture) keeps its own. Every
    replacement shares the group's one members tuple. Coordinates,
    ``cell_key`` and ``sl_pattern`` are the representative's and are
    not touched, so every key answers the same cell it did and the
    stored row count does not move.
    """
    from .wig_climate import pronto_digest

    lattice_cells: dict[tuple | None, list] = {None: list(matrix.cells)}
    for extra in getattr(matrix, "extras", None) or ():
        lattice_cells.setdefault((extra.axis, extra.key), []).extend(
            extra.cells
        )
    groups: dict[tuple, CellGroup] = {}
    cell_of_hit: dict[int, Any] = {}
    for key, entries in claimed.items():
        lattice, inner = key
        if len(entries) < 2 or inner in power_codes:
            continue
        members = tuple(dict.fromkeys(_coords(cell) for cell, _hit in entries))
        if len(members) < 2:
            # Two copies of one code at one coordinate: nothing spans.
            continue
        member_cells = {id(cell) for cell, _hit in entries}
        covered: dict[tuple, bool] = {}
        for cell in lattice_cells.get(lattice, ()):
            branch = (cell.mode, cell.fan, cell.swing)
            covered[branch] = (
                covered.get(branch, True) and id(cell) in member_cells
            )
        digests = frozenset(
            digest for digest in (
                pronto_digest(cell.pronto) for cell, _hit in entries
            ) if digest is not None
        )
        group = CellGroup(
            lattice=lattice,
            members=members,
            digests=digests,
            full_branches=frozenset(
                branch for branch, full in covered.items() if full
            ),
        )
        groups[key] = group
        for digest in digests:
            index.groups[(lattice, digest)] = group
        for cell, hit in entries:
            cell_of_hit[id(hit)] = cell
    if not groups:
        return

    replaced: dict[int, CellHit] = {}

    def _named(hit: CellHit) -> CellHit:
        group = groups.get(hit_group.get(id(hit)))  # type: ignore[arg-type]
        if group is None:
            return hit
        new = replaced.get(id(hit))
        if new is None:
            spanned = spanned_of(group.members)
            new = replaced[id(hit)] = replace(
                hit,
                spanned=spanned,
                members=group.members,
                cell_name=name(
                    cell_of_hit[id(hit)], dict(spanned), hit.lattice,
                ),
            )
        return new

    for store in (
        index.decoded, index.fp_bytehash, index.bytehash, index.norm_fp.refs,
    ):
        for key, hit in list(store.items()):
            store[key] = _named(hit)


class MatrixListener:
    """Per-remote climate matrices: load, cache, and hear."""

    def __init__(
        self,
        hass: HomeAssistant,
        store: HAIRStore,
        trigger_manager: TriggerManager | None = None,
        device_manager: Any | None = None,
    ) -> None:
        self._hass = hass
        self._store = store
        # Used for three things it already owns: resolving a receiver
        # to an HA area (the v0.5.7 location trio), fanning a push out
        # to the panel's existing subscription, and -- Track 4 -- the
        # one retransmit dispatcher, so a heard state and a fired
        # trigger share a coalescer and a loop breaker. A state heard
        # is not a trigger fire and never becomes one; these are shared
        # pipes, not shared behavior.
        self._trigger_manager = trigger_manager
        # The send side of a pinned matrix Device (Track 4). Optional
        # for the same reason the trigger manager's is: without it a
        # matrix remote still hears, it just drives nothing.
        self._device_manager = device_manager
        # Parsed matrices by REMOTE id. Loaded on first ask and held
        # for the install's lifetime; misses are deliberately NOT
        # cached, so a file that appears later (a restored backup, or
        # a mint racing a list call) is picked up on the next ask
        # rather than being remembered as absent.
        self._matrix_cache: dict[str, ClimateMatrix] = {}
        self._index_cache: dict[str, CellIndex] = {}
        # Ids whose index is being built right now, so a burst of
        # frames dispatches one build rather than one per frame.
        self._building: set[str] = set()
        # How many times each id has been invalidated. A build started
        # under one count and finishing under another was built from a
        # file that has since changed, so it neither caches nor writes,
        # and builds again: a second change landing mid-build used to be
        # swallowed by ``_building`` and leave the first change's index
        # in place for the rest of the run.
        self._generation: dict[str, int] = {}
        # Last heard time per (remote, cell), for the one-press-one-event
        # rule. Keyed on the cell as well as the remote so a deliberate
        # change of state inside the window is still two events; see
        # MATRIX_STATE_DEDUP_WINDOW_S.
        self._recent_hits: dict[tuple[str, str], float] = {}
        # --- Track 4: driving pinned matrix Devices -------------------
        # The heard frame behind each dispatched cell target, by cell
        # key. The dispatcher's target is three strings, so the send
        # side reads the coordinates back from here rather than trying
        # to parse them out of a display key. Bounded by the number of
        # distinct states this install has ever heard.
        self._heard_frames: dict[str, tuple[CellHit, _Identity]] = {}
        # (remote_id, device_id) pairs already reported as unmappable,
        # so a handset held on a state the device does not have logs
        # once instead of once per press. Cleared for a pair the moment
        # it does map, so a pairing that breaks later says so again.
        self._unmapped: set[tuple[str, str]] = set()

    # --- Access -------------------------------------------------------

    async def async_get_matrix(self, remote_id: str) -> ClimateMatrix | None:
        """The remote's climate matrix, cache-first.

        None = no file or an unreadable one; ``matrix_store`` has
        already logged the reason. Callers treat None as "this remote
        has no readable lattice" and render the flat shape rather than
        guessing, exactly as the climate entity does on the device
        side.
        """
        cached = self._matrix_cache.get(remote_id)
        if cached is not None:
            return cached
        from .matrix_store import load_matrix

        matrix = await self._hass.async_add_executor_job(
            load_matrix, self._hass.config.config_dir, remote_id
        )
        if matrix is not None:
            self._matrix_cache[remote_id] = matrix
        return matrix

    def invalidate(self, remote_id: str) -> None:
        """Drop one remote's cached matrix and index, in memory and on disk.

        Called by every door that writes, copies or deletes a matrix
        file. The caches are held for the install's lifetime on the
        argument that nothing changes a matrix behind our back, so
        every door that DOES change one has to say so here. The stored
        index would also fail its own content-hash check, but deleting
        it keeps the folder honest rather than leaving a file that
        describes a lattice nobody has any more.
        """
        self._matrix_cache.pop(remote_id, None)
        self._index_cache.pop(remote_id, None)
        self._generation[remote_id] = self._generation.get(remote_id, 0) + 1
        for key in [k for k in self._recent_hits if k[0] == remote_id]:
            self._recent_hits.pop(key, None)
        from .matrix_store import delete_cell_index

        try:
            delete_cell_index(self._hass.config.config_dir, remote_id)
        except Exception:  # never let hygiene break a mint
            _LOGGER.debug(
                "Could not drop the stored cell index for %s",
                remote_id, exc_info=True,
            )

    def forget_matrix(self, matrix_id: str) -> None:
        """Drop everything held for a matrix that no longer exists.

        ``invalidate`` is for a lattice that CHANGED; this is for one
        that is GONE (0.10.1 item 8). On top of the caches invalidate
        clears, it drops the already-reported unmapped pairings that
        name this id, so a later id can never inherit a suppression it
        did not earn.
        """
        self.invalidate(matrix_id)
        for pair in [
            p for p in self._unmapped if matrix_id in p
        ]:
            self._unmapped.discard(pair)

    # --- Warming ------------------------------------------------------

    def _matrix_ids_to_warm(self) -> list[str]:
        """Every lattice this install can be asked about at boot.

        Both sides of the pairing, because both index through this one
        cache: a matrix Remote hears on its lattice, and a matrix Device
        that a Remote is pinned to is asked "which of YOUR cells is this
        frame?" through ``_cell_by_identity``. Warming only the remotes
        would leave the Track 4 fallback cold and lose the first press
        that needs it, which is the same defect one layer down.
        """
        ids: list[str] = []
        seen: set[str] = set()

        def _want(matrix_id: str) -> None:
            if matrix_id in seen or matrix_id in self._index_cache:
                return
            seen.add(matrix_id)
            ids.append(matrix_id)

        for remote in self._store.get_all_trigger_remotes():
            if not remote.climate_matrix:
                continue
            _want(remote.id)
            for device_id in remote.pinned_device_ids:
                device = self._store.get_device(device_id)
                if device is not None and device.climate_matrix:
                    _want(device_id)
        return ids

    async def async_warm_indexes(self) -> None:
        """Read or build every cell index before the first frame arrives.

        Called once at setup, before receivers are subscribed. Each
        build already runs its disk read and its per-cell decode in the
        executor, so the per-lattice work overlaps; a failure warms one
        lattice less rather than failing setup, since the lazy path is
        still there to try again on the first frame.
        """
        ids = self._matrix_ids_to_warm()
        if not ids:
            return
        results = await asyncio.gather(
            *(self._async_warm_one(matrix_id) for matrix_id in ids),
            return_exceptions=True,
        )
        read = sum(1 for r in results if r == "read")
        built = sum(1 for r in results if r == "built")
        for matrix_id, result in zip(ids, results, strict=True):
            if isinstance(result, BaseException):
                _LOGGER.debug(
                    "Could not warm the cell index for matrix %s at setup; "
                    "it will be built on the first frame instead",
                    matrix_id, exc_info=result,
                )
        _LOGGER.info(
            "Warmed %d cell indexes at setup (%d read from disk, %d built)",
            read + built, read, built,
        )

    async def _async_warm_one(self, matrix_id: str) -> str | None:
        """One warm, holding the same in-flight guard the lazy path sets."""
        if matrix_id in self._building:
            return None
        self._building.add(matrix_id)
        return await self._async_build_index(matrix_id)

    def warm_index(self, matrix_id: str) -> None:
        """Build one lattice's index now, off the caller's path.

        The mint doors call this the moment a matrix file lands, so a
        remote created at runtime is ready for its first press the same
        way a remote that existed at boot is. Safe to call twice: an
        in-flight build is not started again.

        A WARM INDEX IS LEFT ALONE. The pin door and the matrix-changed
        signal warm a device's lattice too, and a warm that rebuilt an
        index already in hand would only be rebuilding the copy this
        listener has, which a porthole edit can leave behind the file.
        Every door that CHANGES a lattice invalidates it first, so it
        arrives here cold and is built from disk.
        """
        if matrix_id in self._index_cache:
            return
        self._schedule_index_build(matrix_id)

    # --- Hearing ------------------------------------------------------

    async def on_signal_captured(
        self,
        signal_fingerprint: str | None,
        byte_hash: str | None,
        decoded_fingerprint: str | None,
        receiver_entity_id: str | None = None,
        norm_fp: str | None = None,
        decode_covers: bool | None = None,
    ) -> list[str]:
        """Match one capture against every matrix remote's lattice.

        Runs on the capture path, right after the trigger match and
        under the same not-echo gate, so HAIR never hears its own
        transmissions as handset presses. Returns the ids of the
        remotes that heard something (for caller awareness and tests).

        ``norm_fp`` is the capture's receiver-tolerant fingerprint,
        computed once per capture beside the byte hash and passed down
        the same way. Absent (the default) simply means the lowest tier
        is not consulted.

        ``decode_covers`` is that capture's decode coverage, threaded
        for the same reason: False means the decoded fingerprint
        explains only part of what was heard, so it is not this
        capture's identity and the decoded tier is skipped. None is
        trusted, matching ``protocol_decode``'s own rule that an
        unverifiable census is unknown rather than false.
        """
        heard: list[str] = []
        for remote in self._store.get_all_trigger_remotes():
            if not remote.climate_matrix:
                continue
            # Remote-level receiver scope (the 2026-08-10 ruling): a
            # named remote's rows never carry their own, so the
            # remote's own list is the whole rule here.
            if not remote.matches_receiver(receiver_entity_id):
                continue
            index = self._index_cache.get(remote.id)
            if index is None:
                self._schedule_index_build(remote.id)
                continue
            matched = index.match(
                decoded_fingerprint, signal_fingerprint, byte_hash, norm_fp,
                decode_covers,
            )
            if matched is None:
                continue
            hit, tier = matched
            # ONE PRESS IS ONE EVENT. Two receivers observing the same
            # frame arrive here twice, and so do the two frames a single
            # press of an AC state code is made of (103 to 148 ms apart
            # on the bench). The window slides for the same reason the
            # trigger dedup's does, so a held button collapses too, and
            # it is keyed on the CELL as well as the remote: hearing a
            # different state inside the window is a different press.
            now = time.monotonic()
            key = (remote.id, hit.cell_key)
            if (
                now - self._recent_hits.get(key, 0.0)
                < MATRIX_STATE_DEDUP_WINDOW_S
            ):
                self._recent_hits[key] = now
                continue
            self._recent_hits[key] = now
            # WHICH TIER ANSWERED. The dress rehearsal had to rebuild
            # the index outside HAIR to learn this; now the log says.
            _LOGGER.debug(
                "Remote '%s' heard %s on the %s tier (receiver %s)",
                remote.name, hit.cell_key, tier_name(tier),
                receiver_entity_id or "unknown",
            )
            self._record(
                remote,
                hit,
                receiver_entity_id,
                (decoded_fingerprint, signal_fingerprint, byte_hash,
                 norm_fp, decode_covers),
            )
            heard.append(remote.id)
        return heard

    def _schedule_index_build(self, remote_id: str) -> None:
        """Build one lattice's cell index off the capture path.

        Takes a matrix id, not specifically a remote's: a pinned matrix
        Device's lattice is indexed through here too (Track 4), and
        ``matrix_store`` keys both from one flat namespace.
        """
        if remote_id in self._building:
            return
        self._building.add(remote_id)
        _LOGGER.debug(
            "Building the cell index for matrix %s; frames heard before "
            "it is ready do not match", remote_id,
        )
        self._hass.async_create_task(self._async_build_index(remote_id))

    async def _async_build_index(self, remote_id: str) -> str | None:
        """Populate one lattice's index; "read", "built" or None.

        The return value exists for the setup warm's one INFO line. The
        lazy path drops it, as a task's result always is.

        BUILT FROM THE FILE, STAMPED WITH THE FILE IT WAS BUILT FROM.
        The matrix is read from disk here, not from this listener's
        cached parse, and the file is hashed BEFORE it is read. A porthole
        edit writes the file under a parse this listener may still hold,
        and an index built from that parse and stamped with the new
        file's hash would be believed by every boot after it. Hashed
        first, a file that changes mid-build leaves an index stamped
        with the older hash, which the next read refuses.

        And a build that an ``invalidate`` overtook is thrown away and
        started again rather than cached, for the reason given where the
        generation count is kept.
        """
        generation = self._generation.get(remote_id, 0)
        cached = False
        try:
            from .matrix_store import load_matrix, matrix_content_hash
            from .wig_climate import unit_letter

            config_dir = self._hass.config.config_dir
            display_unit = unit_letter(
                self._hass.config.units.temperature_unit
            )
            index = await self._hass.async_add_executor_job(
                _load_stored_index, config_dir, remote_id, display_unit,
            )
            if self._generation.get(remote_id, 0) != generation:
                return None
            if index is not None:
                self._index_cache[remote_id] = index
                cached = True
                _LOGGER.debug(
                    "Cell index for remote %s read from disk", remote_id
                )
                return "read"
            content_hash = await self._hass.async_add_executor_job(
                matrix_content_hash, config_dir, remote_id,
            )
            matrix = await self._hass.async_add_executor_job(
                load_matrix, config_dir, remote_id,
            )
            if matrix is None:
                return None
            index = await self._hass.async_add_executor_job(
                build_cell_index, matrix, display_unit,
            )
            if self._generation.get(remote_id, 0) != generation:
                return None
            await self._hass.async_add_executor_job(
                _store_index,
                config_dir, remote_id, index, content_hash, display_unit,
            )
            if self._generation.get(remote_id, 0) != generation:
                # The file on disk is stamped with the hash of what it
                # was built from, so the next read refuses it if that
                # is stale; only the in-memory copy has to be withheld.
                return None
            self._index_cache[remote_id] = index
            cached = True
            _LOGGER.debug(
                "Cell index built for matrix %s: %d decoded, %d hashed",
                remote_id, len(index.decoded), len(index.bytehash),
            )
            return "built"
        finally:
            self._building.discard(remote_id)
            # Decided from the count, not from which line returned: a read
            # of a file caught mid-write returns None, an exception
            # returns nothing at all, and either can land after the
            # writer's own signal, whose warm ``_building`` swallowed.
            if (
                not cached
                and self._generation.get(remote_id, 0) != generation
            ):
                _LOGGER.debug(
                    "Matrix %s changed while its cell index was being "
                    "built; building it again", remote_id,
                )
                self._schedule_index_build(remote_id)

    def _record(
        self,
        remote: TriggerRemote,
        hit: CellHit,
        receiver_entity_id: str | None,
        identity: _Identity = (None, None, None, None, None),
    ) -> None:
        """Stamp the heard state, fire the event, push, and dispatch.

        Synchronous for the same reason ``_fire_trigger`` is: this runs
        from the capture path, so the save is dispatched as a task
        rather than awaited. A heard state is human-press-paced, so a
        save per hearing is proportionate -- the same call the trigger
        fire path makes for ``fire_count``.
        """
        now_iso = datetime.now(UTC).isoformat()
        area_id: str | None = None
        area_name: str | None = None
        if self._trigger_manager is not None:
            area_id, area_name = self._trigger_manager.resolve_receiver_area(
                receiver_entity_id
            )

        spanned = dict(hit.spanned)
        remote.last_heard = {
            "cell_key": hit.cell_key,
            "cell_name": hit.cell_name,
            "power": hit.power,
            # The representative's coordinates even on a press whose
            # code the file stores under several settings: the
            # "+ Trigger" door forwards these to a door that resolves
            # coordinates, and the card seeds its branch from them.
            # ``spanned`` says which of them the press did not pin down.
            "mode": hit.mode,
            "fan": hit.fan,
            "swing": hit.swing,
            "temp": hit.temp,
            # Which lattice was heard (item 5c). Null on a main-lattice
            # state and on a power code, which is every row written
            # before this, so an old row reads exactly as it did.
            "axis": hit.axis,
            "lattice": hit.lattice,
            "spanned": spanned_dict(hit.spanned),
            "sl_pattern": hit.sl_pattern,
            "at": now_iso,
            "receiver_entity_id": receiver_entity_id,
            "receiver_area_name": area_name,
        }
        members = [list(member) for member in hit.members]
        if members:
            # For the card's tile ring, which has to test a WHOLE
            # coordinate: a group need not be every combination of its
            # values, so "fan is one of them and swing is one of them"
            # can ring a tile that is another code.
            remote.last_heard["members"] = members
        remote.updated_at = now_iso
        self._store.update_trigger_remote(remote)
        self._hass.async_create_task(self._store.async_save())

        # THE EVENT SAYS ONLY WHAT THE PRESS PINS DOWN (owner ruling
        # 2026-10-01: honesty over compatibility). A setting the code
        # does not decide is null here, with ``spanned`` listing what it
        # could be: the representative's value is just the last cell
        # the file happened to list, and an automation handed it would
        # act on a number nobody chose. Only the event, never the hit
        # or ``last_heard``, which the doors above still need whole.
        event_data = {
            "remote_id": remote.id,
            "remote_name": remote.name,
            "cell_key": hit.cell_key,
            "cell_name": hit.cell_name,
            "power": hit.power,
            "mode": None if "mode" in spanned else hit.mode,
            "fan": None if "fan" in spanned else hit.fan,
            "swing": None if "swing" in spanned else hit.swing,
            "temp": None if "temp" in spanned else hit.temp,
            "axis": hit.axis,
            "lattice": hit.lattice,
            "spanned": spanned_dict(hit.spanned),
            "timestamp": now_iso,
            # The v0.5.7 location trio, resolved the same way and at
            # the same moment a trigger fire resolves it.
            "receiver_entity_id": receiver_entity_id,
            "receiver_area_id": area_id,
            "receiver_area_name": area_name,
        }
        self._hass.bus.async_fire(EVENT_STATE_HEARD, event_data)

        # The panel's bloom rides the existing trigger subscription
        # with a discriminator rather than a second subscribe command:
        # one channel, two kinds of news. The members ride here and
        # not on the event, which the recorder keeps: a few kilobytes
        # on every stored event would be paid for by nobody who reads
        # them.
        if self._trigger_manager is not None:
            push = {"kind": "state_heard", **event_data}
            if members:
                push["members"] = [list(member) for member in hit.members]
            self._trigger_manager.notify_subscribers(push)

        self._dispatch_pinned_cell(remote, hit, identity)

    # --- Driving pinned matrix Devices (Track 4) ------------------------
    #
    # THE INTERSECTION. Pinning maps a Remote's BUTTONS to a Device's
    # COMMANDS (pin_bindings). A matrix pair has neither: the remote
    # hears a state, and the device holds a lattice. So the map here is
    # made of coordinates, not rows -- what was heard as "cool, fan
    # auto, 23" is looked up as "cool, fan auto, 23" on the device.
    #
    # Two lattices minted from the SAME wig agree on those coordinates
    # exactly, which is the case this was built for. Two different wigs
    # for the same unit need not: one file may write the fan speed as
    # "auto" and the other as "Auto". The fallback is the frame itself
    # -- if the device's lattice contains a cell that transmits the
    # very bytes just heard, that cell IS the heard state whatever its
    # file calls it. When neither the words nor the bytes match, this
    # sends nothing. A near-miss cell would be a plausible lie sent at
    # a real air conditioner, which is worse than silence.

    def _dispatch_pinned_cell(
        self, remote: TriggerRemote, hit: CellHit, identity: _Identity
    ) -> None:
        """Drive the same state on every pinned matrix Device.

        Synchronous like the rest of ``_record``, so the resolution
        (which reads lattices, possibly off disk) runs as a task. A
        remote with no pins pays one attribute check, the common case.
        """
        if self._trigger_manager is None or not remote.pinned_device_ids:
            return
        self._heard_frames[hit.cell_key] = (hit, identity)
        self._hass.async_create_task(
            self._async_dispatch_pinned_cell(remote, hit, identity)
        )

    async def _async_dispatch_pinned_cell(
        self, remote: TriggerRemote, hit: CellHit, identity: _Identity
    ) -> None:
        for device_id in remote.pinned_device_ids:
            device = self._store.get_device(device_id)
            # A pinned FLAT device is out of scope (Track 4.2): a state
            # has no command row to land on, and pin_bindings already
            # yields nothing for a matrix remote's buttons.
            if device is None or not device.climate_matrix:
                continue
            pair = (remote.id, device_id)
            # Only "is there such a state?" is asked here; the send
            # resolves again, so the group pass, which is the costly part
            # on a large group, runs once per press rather than twice.
            resolved = await self._async_resolve_device_cell(
                device_id, hit, identity, with_group=False,
            )
            if resolved is None:
                if pair not in self._unmapped:
                    self._unmapped.add(pair)
                    _LOGGER.debug(
                        "Remote '%s' heard %s, but device '%s' has no such "
                        "state and no cell carrying that code; nothing sent "
                        "for this pairing until one of them changes",
                        remote.name, hit.cell_key, device.name,
                    )
                continue
            self._unmapped.discard(pair)
            # The target's third element is the HEARD key, so a handset
            # held on one state coalesces into one pending send per
            # device exactly as a held button does per command.
            self._trigger_manager.dispatch_cell_retransmit(
                remote.id,
                device_id,
                hit.cell_key,
                (remote.name, device.name, hit.cell_name),
            )

    async def async_send_pinned_cell(
        self, device_id: str, cell_key: str
    ) -> None:
        """Send the heard state on one pinned device (the dispatcher's send).

        Called from ``TriggerManager._send_bound_command`` when a target
        carries the cell prefix, so a cell retransmit and a command
        retransmit leave through the same door. Resolves again rather
        than carrying a Pronto through the queue: a coalesced target can
        be sent a moment after it was dispatched, and the lattice on
        disk is the only thing entitled to say what bytes a state is.
        """
        frame = self._heard_frames.get(cell_key)
        if frame is None or self._device_manager is None:
            return
        hit, identity = frame
        resolved = await self._async_resolve_device_cell(
            device_id, hit, identity
        )
        if resolved is None:
            return
        name, pronto, send_count, state = resolved
        # pinned=True is what mints the echo ticket and labels the
        # Mirror row, exactly as it does for a command retransmit.
        #
        # The coordinates ride along (0.10.1 item 7): a pinned
        # retransmit is a SEND, so the pinned Device's climate card
        # follows it. This is the one door by which a heard state
        # reaches a card, and it reaches it as the send it caused, not
        # as the hearing -- an unpinned Remote hearing the same handset
        # moves nothing.
        power = state.get("power")
        await self._device_manager.async_send_matrix_cell(
            device_id, name, pronto, send_count, pinned=True,
            cell=None if power else dict(state),
            power=power,
        )

    async def _async_resolve_device_cell(
        self,
        device_id: str,
        hit: CellHit,
        identity: _Identity,
        *,
        with_group: bool = True,
    ) -> tuple[str, str, int, dict[str, Any]] | None:
        """The heard state on that device: (name, Pronto, count, state).

        ``with_group=False`` resolves base alone, named as itself: for a
        caller that only needs to know whether the device has the state.

        Coordinates first, the frame's own identity second, nothing
        third. The bytes always come from the device's CURRENT lattice
        (the device manager's cache, which its writers invalidate), so
        even a stale index can only ever mis-map -- it cannot make this
        transmit a code the file no longer holds.
        """
        if self._device_manager is None:
            return None
        matrix = await self._device_manager.async_get_matrix(device_id)
        if matrix is None:
            return None
        from .wig_climate import (
            cell_display_name,
            spanned_display_name,
            state_display_name,
            unit_letter,
        )

        # Power is a pseudo-cell on both sides: the matrix's own off/on
        # codes, which every lattice has (on is optional) whatever its
        # climate vocabulary looks like.
        if hit.power is not None:
            pronto = matrix.off if hit.power == "off" else matrix.on
            if not pronto:
                return None
            return (
                state_display_name(hit.power), pronto, 1,
                {"power": hit.power},
            )

        cell = extra = None
        if hit.mode is not None:
            cell, extra = _cell_in_hit_lattice(matrix, hit)
        if cell is None:
            cell, extra = self._cell_by_identity(device_id, matrix, identity)
        if cell is None:
            return None
        base = cell
        display_unit = unit_letter(self._hass.config.units.temperature_unit)
        lattice_key = None if extra is None else extra.key
        # BASE'S BYTES, ALWAYS. Everything below may change what the send
        # is CALLED and which coordinates the card is told; nothing below
        # may change what goes to the air. The Pronto and the count
        # returned are base's own on every path, so a merged group can
        # only ever relabel a send, never redirect it.
        grouped = None
        if with_group:
            try:
                grouped = self._merged_group_send(
                    device_id, base,
                    matrix.cells if extra is None else extra.cells,
                    None if extra is None else (extra.axis, extra.key),
                )
            except Exception:
                # A fault in the group pass may cost the send its name,
                # never the send: base goes out as it always did.
                _LOGGER.debug(
                    "Merged-group pass failed for device %s; sending %s "
                    "under its own name", device_id, base.mode,
                    exc_info=True,
                )
                grouped = None
        named = base if grouped is None else grouped["chosen"]
        # The DEVICE's own coordinates, not the remote's: two wigs for
        # one unit may spell a dimension differently, and the card
        # belongs to the device.
        state: dict[str, Any] = {
            "mode": named.mode, "fan": named.fan,
            "swing": named.swing, "temp": named.temp,
        }
        if extra is not None:
            # Which lattice, as matrix-send carries it: the same
            # coordinates name a different code in the main lattice, so
            # the card must not follow this send to the main tile.
            state["axis"] = extra.axis
            state["lattice"] = extra.key
        if grouped is None or grouped["concrete"]:
            name = cell_display_name(
                named,
                unit=matrix.unit,
                display_unit=display_unit,
                precision=matrix.precision,
                lattice=lattice_key,
            )
        else:
            # A MISS IS NAMED AS ONE. The device card rings as "current"
            # the tile whose name this is, so naming the representative
            # here would ring 30 while the dial says 24.
            name = spanned_display_name(
                named,
                grouped["spanned"],
                unit=matrix.unit,
                display_unit=display_unit,
                precision=matrix.precision,
                lattice=lattice_key,
            )
        if grouped is not None:
            state["spanned"] = {
                dim: list(values) for dim, values in grouped["spanned"].items()
            }
            state["members"] = [list(member) for member in grouped["members"]]
            state["temp_free"] = grouped["temp_free"]
        return (name, base.pronto, base.send_count, state)

    def _merged_group_send(
        self,
        device_id: str,
        base: Any,
        cells: list,
        lattice: tuple[str, str] | None,
    ) -> dict[str, Any] | None:
        """What a send of ``base`` may say about the group it is in.

        None when there is no group to speak of: the device's index is
        not built yet, or base's code is the only cell that carries it.
        The send then goes out named as base, exactly as it always did.

        THE DEVICE'S GROUP, NEVER THE REMOTE'S. The hit carries the
        remote's ``spanned``, which says what the remote's file stores;
        what the card follows is what was sent to the device, out of
        the device's file, and the two files need not agree. So the
        group is looked up on the device's own index, by base's lattice
        and the digest of base's text.

        CHECKED AGAINST THE LIVE LATTICE. The index can be behind the
        file: a porthole edit rewrites a cell in place, a delete or a
        thinning removes cells. So base's list is walked once, comparing
        coordinates only, and a member coordinate is kept only when at
        least one cell is found at it and every cell found there still
        carries one of the group's texts. Only the cells found at member
        coordinates have their text normalized, which bounds the work
        by the group rather than by the lattice: this runs on the event
        loop, twice per press per pinned device.

        THE NAME AND THE CARD MAY FOLLOW THE DEVICE'S CURRENT STATE,
        through a sibling: a kept cell with base's exact text and send
        count, which therefore transmits exactly what base does. On
        each spanned dimension the wanted value is the device's current
        one when the group holds it, base's otherwise, and the wanted
        cell is looked up among the siblings only, never in the lattice
        by coordinates: a lattice may hold another code at the same
        coordinate.
        """
        from .wig_climate import pronto_digest

        index = self._index_cache.get(device_id)
        if index is None:
            # The press goes out as it always did, and the next one has
            # its group. Nothing else builds a device's index after a
            # runtime pin or a matrix change when its words and the
            # remote's agree, so without this the dial rule would stay
            # off until a restart.
            self._schedule_index_build(device_id)
            return None
        base_digest = pronto_digest(base.pronto)
        group = index.groups.get((lattice, base_digest))
        if group is None:
            return None
        wanted_coords = set(group.members)
        found: dict[tuple, list] = {}
        for cell in cells:
            coords = _coords(cell)
            if coords in wanted_coords:
                found.setdefault(coords, []).append(cell)
        digests: dict[int, str | None] = {}
        kept: list[tuple] = []
        for member in group.members:
            at = found.get(member)
            if not at:
                continue
            for cell in at:
                digests[id(cell)] = pronto_digest(cell.pronto)
            if all(digests[id(cell)] in group.digests for cell in at):
                kept.append(member)
        spanned = dict(spanned_of(kept))
        if not spanned:
            return None
        dropped = wanted_coords.difference(kept)
        siblings = [
            cell
            for member in kept
            for cell in found[member]
            if digests[id(cell)] == base_digest
            and cell.send_count == base.send_count
        ]
        if not any(cell is base for cell in siblings):
            siblings.append(base)

        provider = getattr(self._device_manager, "climate_state", None)
        current = provider(device_id) if provider is not None else None
        if not isinstance(current, dict):
            current = None
        wanted = list(_coords(base))
        found_all = current is not None
        for position, dim in enumerate(_DIMS):
            if dim not in spanned:
                continue
            value = None if current is None else current.get(dim)
            if value is not None and value in spanned[dim]:
                wanted[position] = (
                    float(value) if dim == "temp" else value
                )
            else:
                found_all = False
        chosen = next(
            (cell for cell in siblings if _coords(cell) == tuple(wanted)),
            base,
        )
        branch = (chosen.mode, chosen.fan, chosen.swing)
        return {
            "chosen": chosen,
            "concrete": found_all and _coords(chosen) == tuple(wanted),
            "spanned": spanned,
            "members": kept,
            # The unit ignores temperature on this branch only when the
            # file stores every cell of it as this one code, and none of
            # those cells has since changed under the index.
            "temp_free": branch in group.full_branches
            and not any(member[:3] == branch for member in dropped),
        }

    def _cell_by_identity(
        self, device_id: str, matrix: ClimateMatrix, identity: _Identity
    ) -> tuple[Any | None, Any | None]:
        """The device cell whose code IS this frame, and its lattice.

        ``(cell, extra)`` as ``_cell_in_hit_lattice`` returns it, and
        ``(None, None)`` when nothing matches.

        Uses the device's own ``CellIndex``, built and stored exactly
        like a remote's -- ``matrix_store`` is id-agnostic, so a device
        lattice indexes and persists through the same helpers. The
        build runs in the background for the same reason it does on the
        hear side, so the first press that needs this fallback resolves
        nothing and the next one does.
        """
        index = self._index_cache.get(device_id)
        if index is None:
            self._schedule_index_build(device_id)
            return None, None
        matched = index.match(*identity)
        if matched is None:
            return None, None
        hit, _tier = matched
        if hit.power is not None or hit.mode is None:
            return None, None
        return _cell_in_hit_lattice(matrix, hit)


def _cell_in_hit_lattice(
    matrix: ClimateMatrix, hit: CellHit
) -> tuple[Any | None, Any | None]:
    """The cell at a hit's coordinates, in the lattice the hit names.

    ``(cell, extra)``, with ``extra`` None for the main lattice, or
    ``(None, None)``. A hit naming an extras lattice this matrix does
    not carry is a miss and NEVER the main lattice: every coordinate the
    two share carries a different code, so a fallback would transmit
    the wrong frame. The same rule the card's doors keep
    (``websocket_api._lattice_for_request``), and the same
    ``exact_cell(cells=...)`` search they use.
    """
    from .wig_climate import exact_cell

    extra = None
    if hit.axis is not None or hit.lattice is not None:
        extra = next(
            (
                candidate
                for candidate in getattr(matrix, "extras", None) or ()
                if candidate.axis == hit.axis and candidate.key == hit.lattice
            ),
            None,
        )
        if extra is None:
            return None, None
    cell = exact_cell(
        matrix, hit.mode, hit.fan, hit.swing, hit.temp,
        cells=None if extra is None else extra.cells,
    )
    if cell is None:
        return None, None
    return cell, extra


# ---------------------------------------------------------------------------
# The index on disk (signpost 4, Track M)
# ---------------------------------------------------------------------------
#
# Blocking helpers: the listener runs both through the executor. Kept at
# module level, beside the builder they wrap, so the on-disk shape and
# the in-memory one cannot drift apart in a refactor.

# Bumped to /2 for the receiver-tolerant tier (2026-08-18), to /3 for
# the unified strip (GH #125), to /4 for the shared-key refusal and the
# coverage gate (owner bench 2026-09-25) -- a /3 index was built by
# rules that let one Daikin key answer for 520 states -- and to /5 for
# setting-frame identity (2026-09-29), which moves WHERE an allowlisted
# family's identity is computed from, to /6 for read-bytes identity
# (GH #183, 2026-09-30), which moves WHAT a listed family's byte hash is
# computed from, and to /7 when DAIKIN152 joined and the Daikin settings
# frame both families share took one key of its own (and the refusal
# learned to merge a code a file stores under several labels), and to
# /8 when a hit row gained its axis and lattice: a /7 row has no room
# for them, so every extras hit it holds would read back as a
# main-lattice state, and to /9 when a hit learned the merged group it
# answers for and the index gained the groups themselves: a /8 index
# names a dry press by its last cell and gives the send side no group
# to read. A stored index of an older format is
# simply not read, so every lattice rebuilds once and gains the new map;
# the rebuild is the same seconds-of-work the first build was.
#
# WHY THE VERSION IS THE ONLY LEVER HERE. ``_load_stored_index`` checks
# three things: this string, the matrix file's content hash, and the
# display unit. A change to the identity ALGORITHM moves none of them --
# the migration never touches the matrix file, so its content hash is
# unchanged -- and the stored index would go on answering with
# pre-migration hashes while captures arrived carrying post-migration
# ones. Every climate lattice would silently stop recognizing its own
# cells, with nothing in any log to say so.
INDEX_FORMAT = "hair-cell-index/9"


def _hit_to_row(hit: CellHit, group: int | None = None) -> list:
    """One stored hit. Element 10 is ``spanned`` in its dict rendering
    and element 11 the ordinal of the hit's group in the payload's
    ``groups`` list, so the members are stored once per group rather
    than once per row."""
    return [
        hit.cell_key, hit.cell_name, hit.power, hit.mode, hit.fan,
        hit.swing, hit.temp, hit.sl_pattern, hit.axis, hit.lattice,
        spanned_dict(hit.spanned), group,
    ]


def _row_to_hit(row: list, groups: list[CellGroup] | None = None) -> CellHit:
    ordinal = row[11] if len(row) > 11 else None
    return CellHit(
        cell_key=row[0], cell_name=row[1], power=row[2], mode=row[3],
        fan=row[4], swing=row[5], temp=row[6], sl_pattern=row[7],
        axis=row[8], lattice=row[9],
        spanned=_spanned_from_dict(row[10] if len(row) > 10 else None),
        members=(
            () if ordinal is None or groups is None
            else groups[ordinal].members
        ),
    )


def _branch_order(branch: tuple) -> tuple:
    return tuple((v is None, "" if v is None else v) for v in branch)


def _group_to_row(group: CellGroup) -> dict:
    """One group, JSON-native only.

    ``write_cell_index`` swallows a ``TypeError``, so a set or a tuple
    key in here would not fail loudly: the index would simply never be
    written, and every boot would pay the build again.
    """
    return {
        "lattice": None if group.lattice is None else list(group.lattice),
        "members": [list(member) for member in group.members],
        "digests": sorted(group.digests),
        "full": [
            list(branch)
            for branch in sorted(group.full_branches, key=_branch_order)
        ],
    }


def _row_to_group(row: dict) -> CellGroup:
    """One group back from JSON, in exactly the shapes the build makes.

    JSON has no tuples and no sets. A member read back as a list is
    never ``in`` a tuple of tuples, and a branch read back as a list is
    never in a set of tuples, so without the rebuild below the dial
    rule would quietly stop applying from the second boot on.
    """
    lattice = row["lattice"]
    if lattice is not None:
        axis, key = lattice
        lattice = (axis, key)
    members = tuple(
        (mode, fan, swing, None if temp is None else float(temp))
        for mode, fan, swing, temp in row["members"]
    )
    return CellGroup(
        lattice=lattice,
        members=members,
        digests=frozenset(row["digests"]),
        full_branches=frozenset(
            (mode, fan, swing) for mode, fan, swing in row["full"]
        ),
    )


def _index_to_payload(
    index: CellIndex, content_hash: str | None, display_unit: str | None
) -> dict:
    """Serialize an index: one hit table, three maps of indices into it.

    A lattice's cells are heavily shared across tiers (the same hit is
    reachable by decoded fingerprint, by composite key and by hash), so
    storing the hits once and pointing at them keeps the file at roughly
    the size of the coordinates rather than three copies of them. The
    merged groups are stored once each, and a hit points at its own.
    """
    groups: list[dict] = []
    ordinal: dict[int, int] = {}
    for group in index.groups.values():
        if id(group.members) not in ordinal:
            ordinal[id(group.members)] = len(groups)
            groups.append(_group_to_row(group))

    hits: list[list] = []
    seen: dict[int, int] = {}

    def _ref(hit: CellHit) -> int:
        key = id(hit)
        if key not in seen:
            seen[key] = len(hits)
            hits.append(_hit_to_row(
                hit, ordinal.get(id(hit.members)) if hit.members else None,
            ))
        return seen[key]

    from .identity import field_map_digest

    return {
        "format": INDEX_FORMAT,
        # The field maps and the allowlist decide which frames an
        # allowlisted family's identity is sliced from, so a change to
        # either makes this index answer with boundaries the current
        # library would not choose. Nothing else in the freshness check
        # moves when a map is edited (review finding 2).
        "maps": field_map_digest(),
        # What this index was built FROM. A rewritten matrix gets a new
        # hash and this file is ignored (and normally already deleted).
        "matrix": content_hash,
        # Cell NAMES are display strings, so they freeze the unit they
        # were built in; flipping the install's unit rebuilds.
        "unit": display_unit,
        "groups": groups,
        "hits": hits,
        "decoded": {k: _ref(v) for k, v in index.decoded.items()},
        "fp_bytehash": [
            [fp, bh, _ref(hit)]
            for (fp, bh), hit in index.fp_bytehash.items()
        ],
        "bytehash": {k: _ref(v) for k, v in index.bytehash.items()},
        # Only the unambiguous entries: a value two different cells
        # claimed was already dropped at build time and must not come
        # back through the file.
        "norm_fp": {k: _ref(v) for k, v in index.norm_fp.refs.items()},
    }


def _payload_to_index(payload: dict) -> CellIndex | None:
    try:
        if payload.get("format") != INDEX_FORMAT:
            return None
        groups = [_row_to_group(row) for row in payload["groups"]]
        hits = [_row_to_hit(row, groups) for row in payload["hits"]]
        index = CellIndex()
        for group in groups:
            for digest in group.digests:
                index.groups[(group.lattice, digest)] = group
        for key, ref in payload["decoded"].items():
            index.decoded[key] = hits[ref]
        for fp, bh, ref in payload["fp_bytehash"]:
            index.fp_bytehash[(fp, bh)] = hits[ref]
        for key, ref in payload["bytehash"].items():
            index.bytehash[key] = hits[ref]
        for key, ref in payload["norm_fp"].items():
            # Already resolved when it was written; re-claiming through
            # add() would need the discriminators, which the file has no
            # reason to carry.
            index.norm_fp.refs[key] = hits[ref]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    return index or None


def _load_stored_index(
    config_dir: str, remote_id: str, display_unit: str | None
) -> CellIndex | None:
    """The index from disk, or None when absent, stale or unreadable.

    Four freshness keys now: the format string, the matrix content
    hash, the display unit, and the field-map digest.
    """
    from .matrix_store import load_cell_index, matrix_content_hash

    payload = load_cell_index(config_dir, remote_id)
    if payload is None:
        return None
    if payload.get("unit") != display_unit:
        return None
    if payload.get("matrix") != matrix_content_hash(config_dir, remote_id):
        return None
    from .identity import field_map_digest

    if payload.get("maps") != field_map_digest():
        return None
    return _payload_to_index(payload)


def _store_index(
    config_dir: str,
    remote_id: str,
    index: CellIndex,
    content_hash: str | None,
    display_unit: str | None,
) -> bool:
    """Leave a built index on disk for the next boot."""
    from .matrix_store import write_cell_index

    return write_cell_index(
        config_dir, remote_id,
        _index_to_payload(index, content_hash, display_unit),
    )


def _build_and_store_index(
    config_dir: str,
    remote_id: str,
    matrix: Any,
    display_unit: str | None,
    content_hash: str | None = None,
) -> CellIndex:
    """Build the index and leave a copy on disk for the next boot.

    ``content_hash`` is the hash of the file ``matrix`` was read FROM,
    taken before it was read. Hashing the file after the build stamps
    an index built from an older parse with the newer file's hash, and
    every later boot then believes it. Omitted, the file is hashed now,
    which is right only for a caller that has just read it.
    """
    from .matrix_store import matrix_content_hash

    if content_hash is None:
        content_hash = matrix_content_hash(config_dir, remote_id)
    index = build_cell_index(matrix, display_unit)
    _store_index(config_dir, remote_id, index, content_hash, display_unit)
    return index
