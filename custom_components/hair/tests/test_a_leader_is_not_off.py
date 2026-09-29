"""A shared leader is not Off (GH #183).

WHAT HAPPENED. A Daikin ARC43xxx handset sends a short leader block and
a gap before its three frames: 8 bytes, 8 bytes that carry the remote's
clock, then the 19-byte frame with the settings. The reporter's wig took
its states from a file that starts at frame 0, with no leader, but his
Off was captured from the real remote and starts with the leader. Every
handset press starts with the leader too. On 0.17.0 the byte hash was
computed on the code's first frame, so every press hashed like Off --
and ONLY like Off, so #178's refusal of a key many cells share never
fired. Every press matched Off at the byte-hash tier and the pin re-sent
Off to the unit.

WHY #187 FIXES IT. Off and every handset press read as DAIKIN152, which
is allowlisted, so their identities are computed on the settings frame
and differ exactly where the states differ. A leader, a constant frame
or a clock frame no longer decides anything.

THE LATTICE HERE IS SYNTHETIC. It is built from protocol constants and
the DAIKIN152 map's timing nominals, in the same shape as the report:
leaderless states, an Off with the leader, and handset presses made of
the leader, the constant frame, a clock frame that differs from the one
stored, and a state's settings frame. No code from the reporter's file
is in this repository.

Measured before and after (78 presses):

    8e7df70  whole press -> Off 78/78, its leader alone -> Off 78/78,
             a handset Off's settings frame alone -> nothing
    #187     whole press -> Off 0/78, every piece -> Off 0/78,
             stored Off -> Off, handset Off -> Off whole and split
"""
from __future__ import annotations

import pytest

from custom_components.hair.const import PRONTO_GAP_THRESHOLD
from custom_components.hair.field_readers import read_code
from custom_components.hair.identity import norm_fingerprint
from custom_components.hair.matrix_listener import build_cell_index
from custom_components.hair.wig_format import ClimateCell, ClimateMatrix, cell_key
from custom_components.hair.wig_identity import wig_signal_identity

# ---------------------------------------------------------------------------
# A DAIKIN152-shaped code from bytes (test-local on purpose: the reader
# tier must never gain an encoder, see test_field_readers)
# ---------------------------------------------------------------------------

_UNIT_US = 0x6D * 0.241246
_MARK, _ZERO, _ONE = 427, 458, 1312
_HEADER = (3448, 1740)
# Clears PRONTO_GAP_THRESHOLD, so a receiver hands each frame over on
# its own, which is how the report's captures arrived.
_GAP = 34000
_TAIL = 80000


def _units(us: float) -> int:
    return max(1, round(us / _UNIT_US))


def _checksummed(body: list[int]) -> list[int]:
    return [*body, sum(body) & 0xFF]


def _frame(data: list[int], end_us: int) -> list[tuple[int, int]]:
    pairs = [_HEADER]
    for byte in data:
        for bit in range(8):
            pairs.append((_MARK, _ONE if (byte >> bit) & 1 else _ZERO))
    return [*pairs, (_MARK, end_us)]


def _leader(end_us: int) -> list[tuple[int, int]]:
    return [(_MARK, _ZERO)] * 5 + [(_MARK, end_us)]


def _pronto(pairs: list[tuple[int, int]]) -> str:
    words = [0, 0x6D, len(pairs), 0]
    for mark, space in pairs:
        words += [_units(mark), _units(space)]
    return " ".join(f"{w:04X}" for w in words)


_CONSTANT = _checksummed([0x11, 0xDA, 0x27, 0x00, 0xC5, 0x00, 0x00])


def _clock(value: int) -> list[int]:
    return _checksummed([0x11, 0xDA, 0x27, 0x00, 0x42, value, 0x00])


def _settings(power: int, mode: int, temp: int, fan: int) -> list[int]:
    return _checksummed([
        0x11, 0xDA, 0x27, 0x00, 0x00, (mode << 4) | power, temp * 2, 0x00,
        (fan << 4) | 0x0F, 0x00, 0x00, 0x06, 0x60, 0x00, 0x00, 0xC0,
        0x00, 0x00,
    ])


_STORED_CLOCK = 0x21
_HANDSET_CLOCK = 0x5A
_OFF_SETTINGS = _settings(0, 3, 24, 0xA)


def _stored_state(settings: list[int]) -> str:
    """A wig state as the reporter's file holds it: no leader."""
    return _pronto(
        _frame(_CONSTANT, _GAP)
        + _frame(_clock(_STORED_CLOCK), _GAP)
        + _frame(settings, _TAIL)
    )


def _handset(settings: list[int], clock: int = _HANDSET_CLOCK) -> str:
    """A press as the handset sends it: the leader first."""
    return _pronto(
        _leader(_GAP)
        + _frame(_CONSTANT, _GAP)
        + _frame(_clock(clock), _GAP)
        + _frame(settings, _TAIL)
    )


_STORED_OFF = _handset(_OFF_SETTINGS, clock=_STORED_CLOCK)


def _lattice() -> tuple[ClimateMatrix, dict[str, list[int]]]:
    cells: list[ClimateCell] = []
    settings: dict[str, list[int]] = {}
    for mode_name, mode in (("cool", 3), ("heat", 4)):
        for fan_name, fan in (("auto", 0xA), ("low", 3), ("high", 5)):
            for temp in range(18, 31):
                body = _settings(1, mode, temp, fan)
                cell = ClimateCell(
                    mode=mode_name, fan=fan_name, swing=None,
                    temp=float(temp), pronto=_stored_state(body),
                )
                cells.append(cell)
                settings[cell_key(cell)] = body
    matrix = ClimateMatrix(
        min_temp=18, max_temp=30, precision=1.0, modes=["cool", "heat"],
        fan_modes=["auto", "high", "low"], swing_modes=[],
        off=_STORED_OFF, cells=cells,
    )
    return matrix, settings


def _split(pronto: str) -> list[str]:
    """The pieces a receiver delivers: one per gap."""
    words = [int(w, 16) for w in pronto.split()]
    head, body = words[:4], words[4:]
    pieces: list[list[int]] = []
    current: list[int] = []
    for i in range(0, len(body) - 1, 2):
        current += [body[i], body[i + 1]]
        if body[i + 1] >= PRONTO_GAP_THRESHOLD:
            pieces.append(current)
            current = []
    if current:
        pieces.append(current)
    return [
        " ".join(f"{w:04X}" for w in [head[0], head[1], len(p) // 2, 0, *p])
        for p in pieces
    ]


def _heard(index, pronto: str) -> str | None:
    """What the capture path would report: a power name, a cell key or
    None. Every tier is consulted, the normalized one included."""
    identity = wig_signal_identity(pronto)
    assert identity is not None
    result = index.match(
        identity.decoded_fingerprint, identity.fingerprint,
        identity.byte_hash, norm_fingerprint(identity.raw_timings),
        identity.decode_covers,
    )
    if result is None:
        return None
    hit, _tier = result
    return hit.power or hit.cell_key


@pytest.fixture(scope="module")
def lattice():
    matrix, settings = _lattice()
    return matrix, settings, build_cell_index(matrix)


class TestTheShapeIsTheReportedOne:
    """If these drift, the tests below stop meaning what they say."""

    def test_off_presses_and_states_all_read_as_daikin152(
        self, lattice,
    ):
        # The leaderless state read as nothing until the DAIKIN152
        # leader became optional; now all three forms read.
        matrix, settings, _ = lattice
        assert read_code(matrix.off).protocol_id == "DAIKIN152"
        state = matrix.cells[0]
        assert read_code(state.pronto).protocol_id == "DAIKIN152"
        press = _handset(settings[cell_key(state)])
        assert read_code(press).protocol_id == "DAIKIN152"

    def test_every_press_opens_with_the_off_codes_own_leader(self, lattice):
        matrix, settings, _ = lattice
        leader = _split(matrix.off)[0]
        for body in settings.values():
            assert _split(_handset(body))[0] == leader

    def test_a_receiver_splits_each_press_into_four(self, lattice):
        matrix, settings, _ = lattice
        assert len(_split(matrix.off)) == 4
        for body in settings.values():
            assert len(_split(_handset(body))) == 4


class TestNoPressIsHeardAsOff:

    def test_no_whole_press_matches_off(self, lattice):
        _, settings, index = lattice
        offenders = [
            key for key, body in settings.items()
            if _heard(index, _handset(body)) == "off"
        ]
        assert offenders == []

    def test_no_piece_of_a_split_press_matches_off(self, lattice):
        _, settings, index = lattice
        offenders = [
            (key, n)
            for key, body in settings.items()
            for n, piece in enumerate(_split(_handset(body)))
            if _heard(index, piece) == "off"
        ]
        assert offenders == []


class TestOffIsStillOff:

    def test_the_stored_off_matches_off(self, lattice):
        matrix, _, index = lattice
        assert _heard(index, matrix.off) == "off"

    def test_a_handset_off_with_a_new_clock_matches_off_whole(self, lattice):
        _, _, index = lattice
        assert _heard(index, _handset(_OFF_SETTINGS)) == "off"

    def test_its_settings_frame_alone_matches_off(self, lattice):
        """The piece a splitting receiver hands over last."""
        _, _, index = lattice
        assert _heard(index, _split(_handset(_OFF_SETTINGS))[-1]) == "off"
