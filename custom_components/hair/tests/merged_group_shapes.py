"""Fixed lattice constructions for the merged-group pins.

A file that stores one code under several settings answers every press
of that code with whichever of those cells the index met last. The
pins for that live in several modules (the listener, the climate
entity, the stored index, the end to end shapes) and the bytes
invariance golden is generated from the same constructions, so they
live here, once, rather than being rebuilt slightly differently in
each place. A golden generated from one construction and checked
against another would prove nothing.

EVERY CODE HERE IS SYNTHETIC. The DAIKIN152 shapes are built by the
test-side encoder the #183 pins already use (``_stored_state`` over
``_file_form`` over the traits round's ``_settings``), and the
capture-built shape by a small pulse-distance encoder below. The
SmartIR files the shapes are named after are not in this repository;
each shape reproduces only the GROUPING one of them showed (which cells
share a code), never a code from it.

Nothing in this module may change once the golden is committed: the
golden rows are keyed by position in these lattices, and the codes are
what they hash.
"""
from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path

from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateExtra,
    ClimateMatrix,
    parse_wig,
)

from .test_a_leader_is_not_off import _handset, _stored_state
from .test_daikin152_joins import _file_form
from .test_daikin152_traits import _settings

FIXTURES = Path(__file__).parent / "fixtures"
PACKS = FIXTURES / "field-packs"
KOMECO_WIGS = (
    FIXTURES / "wigs" / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json",
    FIXTURES / "thinning" / "komeco-pr19-after-834.wig.json",
)

# ---------------------------------------------------------------------------
# Codes
# ---------------------------------------------------------------------------

_FAN_NIBBLES = (0x3, 0x5, 0x7, 0xA, 0xB)
_SWINGS = ("off", "vertical", "horizontal", "both")


def distinct_code(n: int) -> str:
    """The n-th code of a family of codes that are all different.

    Read-bytes DAIKIN152 states that differ in a byte the map reads, so
    no two of them share an identity on any tier. Cool and heat only:
    dry and fan_only overwrite the temperature byte, which is exactly
    the merge the group codes below are made of.
    """
    temp = 10 + n % 23
    fan = _FAN_NIBBLES[(n // 23) % 5]
    mode = ("cool", "heat")[(n // 115) % 2]
    swing = _SWINGS[(n // 230) % 4]
    flags = (n // 920) % 8
    return _stored_state(_file_form(_settings(
        mode, fan, temp, swing=swing, powerful=bool(flags & 1),
        economy=bool(flags & 2), sleep=bool(flags & 4),
    )))


def group_code(fan: int = 0xA, swing: str = "off") -> str:
    """One shared code: a DAIKIN152 dry state, whose temperature byte
    the encoder fixes, so every temperature spelled with it is one
    code."""
    return _stored_state(_file_form(_settings("dry", fan, 24, swing=swing)))


def _off() -> str:
    return _handset(_settings("cool", 0x7, 24, power=0))


def _matrix(cells: list[ClimateCell], **over) -> ClimateMatrix:
    temps = [c.temp for c in cells if c.temp is not None]
    return ClimateMatrix(
        min_temp=over.pop("min_temp", min(temps)),
        max_temp=over.pop("max_temp", max(temps)),
        precision=1.0,
        modes=over.pop("modes", list(dict.fromkeys(c.mode for c in cells))),
        fan_modes=over.pop(
            "fan_modes",
            list(dict.fromkeys(c.fan for c in cells if c.fan is not None)),
        ),
        swing_modes=over.pop(
            "swing_modes",
            list(dict.fromkeys(c.swing for c in cells if c.swing is not None)),
        ),
        off=over.pop("off", _off()),
        cells=cells,
        **over,
    )


class _Codes:
    """Hands out distinct codes in a fixed order."""

    def __init__(self, start: int = 0) -> None:
        self._next = start

    def __call__(self) -> str:
        code = distinct_code(self._next)
        self._next += 1
        return code


# ---------------------------------------------------------------------------
# The shapes
# ---------------------------------------------------------------------------


def daikin_dry() -> ClimateMatrix:
    """The #183 case: dry stores one code per fan across 18-30.

    Cool is a real code per temperature from 16 to 30, so a dial left
    at 16 in cool is outside the dry group's temperatures, which is the
    case ``temp_free`` exists for. Dry auto and dry high are two groups
    of thirteen text-identical cells.
    """
    codes = _Codes(0)
    cells: list[ClimateCell] = []
    for fan in ("auto", "high"):
        for temp in range(16, 31):
            cells.append(ClimateCell(
                mode="cool", fan=fan, swing="off", temp=float(temp),
                pronto=codes(),
            ))
    for fan, nibble in (("auto", 0xA), ("high", 0x7)):
        shared = group_code(nibble)
        for temp in range(18, 31):
            cells.append(ClimateCell(
                mode="dry", fan=fan, swing="off", temp=float(temp),
                pronto=shared,
            ))
    return _matrix(cells, modes=["cool", "dry"])


def daikin_dry_press(fan: str = "auto") -> str:
    """A handset press of the dry state (any temperature: it is one
    code)."""
    nibble = {"auto": 0xA, "high": 0x7}[fan]
    return _handset(_file_form(_settings("dry", nibble, 24)))


def shape_1294() -> ClimateMatrix:
    """A group that is not a product of its values.

    cool / low / vertical / 18 and cool / quiet / off / 18 are one
    code; cool / low / off / 18 and cool / quiet / vertical / 18 are
    two others. Spanned on fan {low, quiet} and swing {off, vertical},
    and a per-dimension test would call cool / low / off / 18 a member.
    """
    codes = _Codes(100)
    shared = group_code(0x3, "vertical")
    cells: list[ClimateCell] = []
    for fan in ("low", "quiet"):
        for swing in ("off", "vertical"):
            for temp in range(18, 22):
                member = temp == 18 and (fan, swing) in (
                    ("low", "vertical"), ("quiet", "off"),
                )
                cells.append(ClimateCell(
                    mode="cool", fan=fan, swing=swing, temp=float(temp),
                    pronto=shared if member else codes(),
                ))
    return _matrix(cells)


def shape_2740() -> ClimateMatrix:
    """dry / auto / 16 with dry / level1-4 / 16-30, all one code.

    dry / auto / 17-30 are real codes of their own, so dry / auto / 17
    is inside the group's fans and inside its temperatures and is still
    not a member. Cool is a code per cell.
    """
    codes = _Codes(200)
    shared = group_code(0x5)
    fans = ("auto", "level1", "level2", "level3", "level4")
    cells: list[ClimateCell] = []
    for fan in fans:
        for temp in range(16, 31):
            cells.append(ClimateCell(
                mode="cool", fan=fan, temp=float(temp), pronto=codes(),
            ))
    for fan in fans:
        for temp in range(16, 31):
            member = fan != "auto" or temp == 16
            cells.append(ClimateCell(
                mode="dry", fan=fan, temp=float(temp),
                pronto=shared if member else codes(),
            ))
    return _matrix(cells, modes=["cool", "dry"])


def shape_1000() -> ClimateMatrix:
    """A group that covers part of its branch.

    heat / high / 18 and heat / high / 19 are one code while heat /
    high / 16-30 are otherwise all real and distinct, so the unit does
    NOT ignore temperature there and the dial must not stay put.
    """
    codes = _Codes(400)
    shared = group_code(0xB)
    cells: list[ClimateCell] = []
    for mode in ("cool", "heat"):
        for fan in ("low", "high"):
            for temp in range(16, 31):
                member = (mode, fan) == ("heat", "high") and temp in (18, 19)
                cells.append(ClimateCell(
                    mode=mode, fan=fan, temp=float(temp),
                    pronto=shared if member else codes(),
                ))
    return _matrix(cells, modes=["cool", "heat"])


def shape_duplicate_coordinate() -> ClimateMatrix:
    """Two cells at dry / auto / off / 24 with different codes.

    The parser allows it. The other code sits AHEAD of the group's own
    dry / auto / off / 24, so a lookup that searched the lattice by
    coordinates rather than the group's siblings would find it first.
    """
    matrix = daikin_dry()
    at = next(
        i for i, c in enumerate(matrix.cells)
        if (c.mode, c.fan, c.temp) == ("dry", "auto", 24.0)
    )
    matrix.cells.insert(at, ClimateCell(
        mode="dry", fan="auto", swing="off", temp=24.0,
        pronto=distinct_code(600),
    ))
    return matrix


def shape_1100() -> ClimateMatrix:
    """A group spanning fan and temperature that leaves one fan out.

    dry / auto, high, low and mid across 18-30 are one code; dry /
    quiet is a real code per temperature. A device whose current fan is
    quiet is outside the group even though fan is a spanned dimension.
    """
    codes = _Codes(700)
    shared = group_code(0x3)
    cells: list[ClimateCell] = []
    for fan in ("auto", "high", "low", "mid", "quiet"):
        for temp in range(18, 31):
            cells.append(ClimateCell(
                mode="cool", fan=fan, temp=float(temp), pronto=codes(),
            ))
    for fan in ("auto", "high", "low", "mid", "quiet"):
        for temp in range(18, 31):
            cells.append(ClimateCell(
                mode="dry", fan=fan, temp=float(temp),
                pronto=codes() if fan == "quiet" else shared,
            ))
    return _matrix(cells, modes=["cool", "dry"])


# A capture-built lattice. Each cell is its own capture of the code it
# carries, so the members of one group are the same code by HAIR's
# quantized discriminator and different text. Long spaces sit on the
# S/L threshold, so the capture wobble moves some of them across it and
# the S/L fingerprint, hence the composite key, differs from capture to
# capture while the byte hash does not: the shape that makes one group
# store different representatives under different keys.
_UNIT_HEADER = (0x0088, 0x0040)
_MARK = 0x0010
_SPACE_0 = 0x0010
_SPACE_1 = 0x0030
_TRAIL = 0x0400


def _capture_word(value: int, position: int, take: int) -> int:
    """One timing word as capture ``take`` recorded it: a wobble of up
    to two carrier cycles either way, from a fixed pattern, never a
    random one."""
    wobble = ((position * 7 + take * 13) % 5) - 2
    return max(1, value + wobble)


def pulse_code(payload: bytes, take: int | None = None) -> str:
    """A pulse-distance code, optionally as capture ``take`` of it."""
    words = list(_UNIT_HEADER)
    for byte in payload:
        for bit in range(8):
            words += [_MARK, _SPACE_1 if (byte >> bit) & 1 else _SPACE_0]
    words += [_MARK, _TRAIL]
    if take is not None:
        words = [
            _capture_word(w, i, take) if w != _TRAIL else w
            for i, w in enumerate(words)
        ]
    head = [0x0000, 0x006D, len(words) // 2, 0x0000]
    return " ".join(f"{w:04X}" for w in head + words)


def _payload(n: int) -> bytes:
    return bytes([0x23, 0xCB, 0x26, 0x01, n & 0xFF, (n >> 8) & 0xFF,
                  0x5A, (n * 37) & 0xFF])


def shape_1128() -> ClimateMatrix:
    """Capture per cell: dry / level1 / 16-31 is one code in sixteen
    captures, and cool is a code per cell, each its own capture."""
    cells: list[ClimateCell] = []
    take = itertools.count(1)
    for fan_index, fan in enumerate(("level1", "level2")):
        for temp in range(16, 32):
            cells.append(ClimateCell(
                mode="cool", fan=fan, temp=float(temp),
                pronto=pulse_code(
                    _payload(fan_index * 64 + temp), next(take)
                ),
            ))
    shared = _payload(0xDD)
    for temp in range(16, 32):
        cells.append(ClimateCell(
            mode="dry", fan="level1", temp=float(temp),
            pronto=pulse_code(shared, next(take)),
        ))
    return _matrix(
        cells, modes=["cool", "dry"], off=pulse_code(_payload(0xFFF)),
    )


# One state, two waveforms, on a LISTED family. DAIKIN216 built by
# ``test_read_bytes_identity``'s encoder, with one extra (unit, zero)
# pulse pair inserted into some codes: the frame then reads one bit over
# its width, inside the map's ``bits_tolerance``, and ``bits_to_bytes``
# drops the partial byte, so every frame decodes to the same bytes and
# the read key is the same while the whole waveform is not. It is the
# capture-per-cell shape of SmartIR 1128 on a family the index reads.
#
# Where the pair sits decides what else sees it. After frame 0's 64 bits
# (the constant preamble) it is invisible to ``norm_fp`` and to the S/L
# fingerprint, which a ``SETTING_IDENTITY_VERIFIED`` family computes on
# its settings frame alone. After the settings frame's 152 bits both of
# them move, so the two waveforms are two normalized values and two
# composite keys as well.


def extra_pair_code(settings: list[int], where: str) -> str:
    """A DAIKIN216 code of ``settings`` with one extra pulse pair,
    ``where`` "preamble" (after frame 0's last bit) or "settings"
    (after the settings frame's last bit)."""
    from . import test_read_bytes_identity as d216

    timing = d216.D216.timing
    pairs = d216._pairs([d216._FRAME0, settings])
    # header + 64 bits, or everything up to the closing footer pair
    at = 1 + 64 if where == "preamble" else len(pairs) - 1
    pairs.insert(at, (timing.unit.nominal, timing.zero.nominal))
    return d216._pronto(pairs)


def _extra_pair_lattice(where: str) -> ClimateMatrix:
    """cool / low / 18-23, a code each; dry / low / 18-23, one state,
    the even temperatures as the plain code and the odd ones with the
    extra pair."""
    from . import test_read_bytes_identity as d216

    cells: list[ClimateCell] = []
    for temp in range(18, 24):
        cells.append(ClimateCell(
            mode="cool", fan="low", temp=float(temp),
            pronto=d216._code(d216._settings(temp_byte=2 * temp)),
        ))
    dry = d216._settings(mode_power=0x21)
    for temp in range(18, 24):
        cells.append(ClimateCell(
            mode="dry", fan="low", temp=float(temp),
            pronto=(d216._code(dry) if temp % 2 == 0
                    else extra_pair_code(dry, where)),
        ))
    return _matrix(
        cells, modes=["cool", "dry"],
        off=d216._code(d216._settings(mode_power=0x30)),
    )


def shape_extra_pair_settings() -> ClimateMatrix:
    """Shape F1: the extra pair inside the settings frame."""
    return _extra_pair_lattice("settings")


def shape_extra_pair_preamble() -> ClimateMatrix:
    """Shape F0: the extra pair after the constant preamble, where only
    the whole-code discriminator sees it."""
    return _extra_pair_lattice("preamble")


def extra_pair_after(pronto: str, family: str, frame: int) -> str:
    """``pronto`` with one extra (unit, zero) pair after the last bit of
    ``frame``, read with ``family``'s own timing: the same bytes, another
    waveform, for any map the reader can walk."""
    from custom_components.hair.event_parser import EventParser
    from custom_components.hair.field_readers import (
        library,
        read_frames_positioned,
    )

    field_map = next(m for m in library() if m.protocol_id == family)
    words = pronto.split()
    timings = EventParser._pronto_us(EventParser._parse_pronto_words(pronto))
    while timings and timings[-1] == 0:
        timings.pop()
    _frames, places, failed = read_frames_positioned(field_map.timing, timings)
    assert not failed, family
    at = 4 + 2 * (places[frame][-1] + 1)
    tick = int(words[1], 16) * 0.241246
    pair = [
        f"{round(field_map.timing.unit.nominal / tick):04X}",
        f"{round(field_map.timing.zero.nominal / tick):04X}",
    ]
    count = f"{int(words[2], 16) + 1:04X}"
    return " ".join([*words[:2], count, words[3], *words[4:at], *pair,
                     *words[at:]])


def shape_mitsubishi144_capture_per_cell() -> ClimateMatrix:
    """SmartIR 1128's shape on its own family, from the MITSUBISHI144
    pack: cool / auto / auto at the pack's five temperatures, a code
    each, and dry / auto / auto / 16-21 one state, the even temperatures
    as the pack's code and the odd ones with an extra pair after the
    settings frame. Meant for a test that lists the family."""
    pack = pack_matrix("MITSUBISHI144.json")
    cells = [
        ClimateCell(mode=c.mode, fan=c.fan, swing=c.swing, temp=c.temp,
                    pronto=c.pronto)
        for c in pack.cells if (c.mode, c.fan, c.swing) == (
            "cool", "auto", "auto")
    ]
    dry = next(
        c.pronto for c in pack.cells
        if (c.mode, c.fan, c.swing, c.temp) == ("dry", "auto", "auto", 16.0)
    )
    extra = extra_pair_after(dry, "MITSUBISHI144", 0)
    for temp in range(16, 22):
        cells.append(ClimateCell(
            mode="dry", fan="auto", swing="auto", temp=float(temp),
            pronto=dry if temp % 2 == 0 else extra,
        ))
    return _matrix(cells, modes=["cool", "dry"], off=pack.off)


def shape_1128_poisoned() -> ClimateMatrix:
    """``shape_1128`` with every key of its dry captures poisoned.

    Each dry capture gets a heat cell whose code is that capture plus a
    second frame of its own: the first frame is all the composite key,
    the byte hash and the normalized fingerprint of an unlisted family
    see, so those keys are claimed by two different whole codes and
    answer nothing. One more heat cell carries the dry payload played
    slower, which decodes to the dry state's own fingerprint as a
    different code and poisons the decoded key too. The dry captures
    are then joined by nothing but their whole code, which is what a
    merged group was made of before any key could merge one.
    """
    matrix = shape_1128()
    shared = _payload(0xDD)
    dry = [c for c in matrix.cells if c.mode == "dry"]
    heat: list[ClimateCell] = []
    for n, cell in enumerate(dry):
        second = pulse_code(_payload(0x200 + n)).split()[4:]
        first = cell.pronto.split()
        words = first[4:] + second
        heat.append(ClimateCell(
            mode="heat", fan="level1", temp=cell.temp,
            pronto=" ".join(
                [*first[:2], f"{len(words) // 2:04X}", "0000", *words]
            ),
        ))
    slower = pulse_code(shared).split()
    heat.append(ClimateCell(
        mode="heat", fan="level2", temp=16.0,
        pronto=" ".join(slower[:4] + [
            f"{round(int(w, 16) * 1.15):04X}" for w in slower[4:]
        ]),
    ))
    matrix.cells.extend(heat)
    matrix.modes = ["cool", "dry", "heat"]
    return matrix


# ---------------------------------------------------------------------------
# Pairings, for the golden and for the tests that sweep it
# ---------------------------------------------------------------------------

#: How far "a second file" moves every timing word. Small, so a
#: read-bytes family still reads the same bytes; the point is only that
#: the device's text differs from the remote's, so a send out of the
#: wrong file is visible in its hash.
RETIME_OFFSET = 1


def retime(pronto: str | None, offset: int = RETIME_OFFSET) -> str | None:
    """One Pronto with every burst word moved by ``offset`` cycles."""
    if not pronto:
        return pronto
    words = pronto.split()
    head, body = words[:4], words[4:]
    moved = [f"{max(1, int(w, 16) + offset):04X}" for w in body]
    return " ".join(head + moved)


def retimed(matrix: ClimateMatrix) -> ClimateMatrix:
    """The same lattice as a second file with its own text."""
    out = copy.deepcopy(matrix)
    for cell in out.cells:
        cell.pronto = retime(cell.pronto)
    for extra in out.extras or ():
        for cell in extra.cells:
            cell.pronto = retime(cell.pronto)
    out.off = retime(out.off)
    out.on = retime(out.on)
    return out


def sparse(matrix: ClimateMatrix) -> ClimateMatrix:
    """The same lattice with every other temperature removed.

    A press at a removed temperature misses the coordinates, which is
    the door the identity fallback answers.
    """
    out = copy.deepcopy(matrix)
    temps = sorted({c.temp for c in out.cells if c.temp is not None})
    drop = set(temps[1::2])
    out.cells = [c for c in out.cells if c.temp not in drop]
    return out


#: The extras lattice the golden adds to every source: the main cells,
#: every timing word stretched by this factor, under one preset key.
#: A stretched code is a different code by frame identity, so the extra
#: never shares one with the main lattice, while two main cells that
#: shared a code still share one in the extra.
EXTRA_STRETCH = 1.15


def _stretch(pronto: str | None) -> str | None:
    if not pronto:
        return pronto
    words = pronto.split()
    return " ".join(
        words[:4] + [f"{round(int(w, 16) * EXTRA_STRETCH):04X}" for w in words[4:]]
    )


def with_extra(matrix: ClimateMatrix) -> ClimateMatrix:
    """The lattice plus a synthesized ``preset / eco`` extra."""
    out = copy.deepcopy(matrix)
    out.extras = [ClimateExtra(
        axis="preset", key="eco",
        cells=[
            ClimateCell(
                mode=c.mode, fan=c.fan, swing=c.swing, temp=c.temp,
                pronto=_stretch(c.pronto), send_count=c.send_count,
            )
            for c in matrix.cells
        ],
    )]
    return out


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------


def pack_matrix(name: str) -> ClimateMatrix:
    from .test_cell_index_shared_keys import _pack_matrix

    return _pack_matrix(name)


def wig_matrix(path: Path) -> ClimateMatrix:
    return parse_wig(path.read_text(encoding="utf-8")).wig.climate


SYNTHESIZED = {
    "synth-daikin-dry": daikin_dry,
    "synth-1294": shape_1294,
    "synth-2740": shape_2740,
    "synth-1000": shape_1000,
    "synth-1100": shape_1100,
    "synth-1128": shape_1128,
    "synth-duplicate-coordinate": shape_duplicate_coordinate,
    # Appended after the golden was first written (additions only):
    # the golden is keyed by source name, so a new source adds rows and
    # moves none.
    "synth-extra-pair-settings": shape_extra_pair_settings,
}


def golden_sources() -> list[tuple[str, ClimateMatrix]]:
    """Every lattice the bytes golden covers, in a fixed order."""
    out: list[tuple[str, ClimateMatrix]] = []
    for path in sorted(PACKS.glob("*.json")):
        if ".defects" in path.name:
            continue
        out.append((path.name, pack_matrix(path.name)))
    for path in KOMECO_WIGS:
        out.append((path.name, wig_matrix(path)))
    for name, build in SYNTHESIZED.items():
        out.append((name, build()))
    return out


def dump(obj) -> str:
    """The golden's one serialization: sorted keys, one row per line."""
    return json.dumps(obj, sort_keys=True, indent=0) + "\n"


# ---------------------------------------------------------------------------
# What a pinned device sends for a press
# ---------------------------------------------------------------------------

GOLDEN = FIXTURES / "merged-group-golden.json"

#: The four pairings, in the order the golden writes them. ``extras``
#: presses the extra's cells; the other three press the main lattice.
PAIRINGS = ("same", "retimed", "sparse", "extras")


def pairing(matrix: ClimateMatrix, name: str):
    """``(remote lattice, device lattice, the cells pressed)``."""
    if name == "same":
        return matrix, copy.deepcopy(matrix), matrix.cells
    if name == "retimed":
        return matrix, retimed(matrix), matrix.cells
    if name == "sparse":
        return matrix, sparse(matrix), matrix.cells
    if name == "extras":
        both = with_extra(matrix)
        return both, copy.deepcopy(both), both.extras[0].cells
    raise ValueError(name)


def press_identity(pronto: str):
    """A press, as the capture path hands it to ``CellIndex.match``."""
    from custom_components.hair.identity import norm_fingerprint
    from custom_components.hair.wig_identity import wig_signal_identity

    identity = wig_signal_identity(pronto)
    if identity is None:
        return None
    return (
        identity.decoded_fingerprint, identity.fingerprint,
        identity.byte_hash, norm_fingerprint(identity.raw_timings),
        identity.decode_covers,
    )


def sent_row(resolved) -> str | None:
    """One golden row: the sha256 of the normalized Pronto and the send
    count, or None when nothing is sent."""
    import hashlib

    if resolved is None:
        return None
    _name, pronto, send_count, _state = resolved
    text = " ".join(pronto.split()).upper()
    return f"{hashlib.sha256(text.encode()).hexdigest()}:{send_count}"


class PinnedBench:
    """A real ``MatrixListener`` with one remote pinned to one device.

    The device manager is a fake that answers the device's lattice and,
    when given one, a current climate state: the same seam the climate
    entity's provider uses. A fake without ``climate_state`` is what
    every caller before the provider looked like.
    """

    def __init__(self, remote_matrix, device_matrix, remote_index=None,
                 device_index=None):
        from unittest.mock import AsyncMock, MagicMock

        from custom_components.hair.matrix_listener import (
            MatrixListener,
            build_cell_index,
        )

        store = MagicMock()
        store.get_all_trigger_remotes = MagicMock(return_value=[])
        hass = MagicMock()
        hass.config.config_dir = "/nonexistent-config"
        hass.config.units.temperature_unit = "°C"
        hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())
        hass.async_add_executor_job = AsyncMock(
            side_effect=lambda func, *args: func(*args)
        )
        self.state: dict | None = None
        bench = self

        class _Devices:
            async def async_get_matrix(self, device_id):
                return device_matrix

            def climate_state(self, device_id):
                return None if bench.state is None else dict(bench.state)

        self.listener = MatrixListener(hass, store, MagicMock(), _Devices())
        self.remote_index = (
            remote_index if remote_index is not None
            else build_cell_index(remote_matrix)
        )
        self.listener._index_cache["dev-1"] = (
            device_index if device_index is not None
            else build_cell_index(device_matrix)
        )

    def hear(self, pronto: str, identities: dict | None = None):
        """The hit the remote's index answers for a press, and its
        identity, or None when the press is not heard.

        ``identities`` is an optional memo of ``press_identity`` by
        press text, for a caller that hears one press on several
        benches: the identity is a pure function of the text, and
        deriving it is the whole cost of a hearing.
        """
        if identities is None:
            identity = press_identity(pronto)
        else:
            if pronto not in identities:
                identities[pronto] = press_identity(pronto)
            identity = identities[pronto]
        if identity is None:
            return None
        matched = self.remote_index.match(*identity)
        if matched is None:
            return None
        return matched[0], identity

    async def resolve(self, heard, state: dict | None = None):
        """What the device is sent for a heard press."""
        if heard is None:
            return None
        self.state = state
        hit, identity = heard
        return await self.listener._async_resolve_device_cell(
            "dev-1", hit, identity
        )


def golden_benches():
    """Every ``(source, pairing, bench, pressed cells)`` the golden
    covers, building each index once."""
    from custom_components.hair.matrix_listener import build_cell_index

    for source, matrix in golden_sources():
        main_index = build_cell_index(matrix)
        extra_index = None
        for name in PAIRINGS:
            remote, device, pressed = pairing(matrix, name)
            if name == "same":
                bench = PinnedBench(remote, device, main_index, main_index)
            elif name == "extras":
                extra_index = build_cell_index(remote)
                bench = PinnedBench(remote, device, extra_index, extra_index)
            else:
                bench = PinnedBench(remote, device, remote_index=main_index)
            yield source, name, bench, pressed


async def golden_rows() -> dict:
    """The golden's rows: ``{source: {pairing: [row per pressed cell]}}``."""
    rows: dict[str, dict[str, list]] = {}
    for source, name, bench, pressed in golden_benches():
        rows.setdefault(source, {})[name] = [
            sent_row(await bench.resolve(bench.hear(cell.pronto)))
            for cell in pressed
        ]
    return rows


# ---------------------------------------------------------------------------
# The capture column: what a pinned device sends for a press off the air
# ---------------------------------------------------------------------------
#
# The file-code golden presses each cell's own file text, and a file code
# finds its cell through the (fingerprint, byte hash) pair long before
# the read key or the normalized tier is asked. A real press is not file
# text: the air moves every edge and a receiver splits a two-frame press
# at its gap. So this second column presses each cell the way
# ``test_read_bytes_identity._air`` says a receiver hands it over, whole
# and split at the map's own gap, for every source where a read key
# forms. Same benches, same rows.

CAPTURE_GOLDEN = FIXTURES / "merged-group-golden-captures.json"

#: Presses per transmitter per cell. Deterministic: ``_air`` seeds its
#: generator from the transmitter and the press number.
CAPTURE_PRESSES = 2
CAPTURE_TRANSMITTERS = ("esphome", "broadlink")


def map_split(pronto: str, gap_us: float) -> list[str]:
    """A Pronto cut at every space of ``gap_us`` or more, each piece
    keeping the space that closed it: the captures a receiver that ends
    a capture at the map's own frame gap hands over for one press."""
    words = [int(w, 16) for w in pronto.split()]
    head, body = words[:4], words[4:]
    tick = words[1] * 0.241246
    pieces: list[list[int]] = []
    current: list[int] = []
    for i in range(0, len(body) - 1, 2):
        current += [body[i], body[i + 1]]
        if body[i + 1] * tick >= gap_us:
            pieces.append(current)
            current = []
    if current:
        pieces.append(current)
    return [
        " ".join(f"{w:04X}" for w in [head[0], head[1], len(p) // 2, 0, *p])
        for p in pieces
    ]


def read_key_gap(matrix: ClimateMatrix) -> float | None:
    """The ``timing.gap_min`` of the listed family a read key forms for
    in this lattice, or None when no cell has a read key."""
    from custom_components.hair.event_parser import EventParser
    from custom_components.hair.field_readers import library, read_code

    maps = {m.protocol_id: m for m in library()}
    for cell in matrix.cells:
        if EventParser.pronto_read_key(cell.pronto) is None:
            continue
        family = read_code(cell.pronto).protocol_id
        if family in maps:
            return maps[family].timing.gap_min
    return None


def capture_presses(pronto: str, gap_us: float) -> list[str]:
    """Every capture-shaped press of one code, in a fixed order: per
    transmitter and press number, the whole press, then its pieces."""
    from .test_read_bytes_identity import _air

    out: list[str] = []
    for transmitter in CAPTURE_TRANSMITTERS:
        for press in range(CAPTURE_PRESSES):
            heard, _glitched = _air(pronto, press, transmitter)
            out.append(heard)
            out.extend(map_split(heard, gap_us))
    return out


async def capture_rows() -> dict:
    """The capture column: ``{source: {pairing: [row per press]}}``."""
    gaps = {
        source: read_key_gap(matrix) for source, matrix in golden_sources()
    }
    rows: dict[str, dict[str, list]] = {}
    identities: dict[str, object] = {}
    presses: dict[str, list[str]] = {}
    for source, name, bench, pressed in golden_benches():
        gap = gaps[source]
        if gap is None:
            continue
        if name == "same":
            identities.clear()
            presses.clear()
        out: list[str | None] = []
        for cell in pressed:
            if cell.pronto not in presses:
                presses[cell.pronto] = capture_presses(cell.pronto, gap)
            for press in presses[cell.pronto]:
                out.append(sent_row(
                    await bench.resolve(bench.hear(press, identities))
                ))
        rows.setdefault(source, {})[name] = out
    return rows
