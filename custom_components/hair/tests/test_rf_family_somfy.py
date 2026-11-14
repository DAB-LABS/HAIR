"""Somfy RTS, detection only, held off (second decoder round).

Frames are built from the PushStack write-up's facts: 56 bits in 7
bytes, MSB first; byte 0 the key (0xA and a counter), byte 1 the command
and the checksum (the XOR of all nibbles is 0), bytes 2 and 3 the rolling
code, bytes 4 to 6 the address, little-endian; each byte from byte 1 on
XORed with the byte sent before it; Manchester at 604 us half-symbols, a
rising edge for 1; 2 or 7 hardware sync pairs of 2416 us, then a 4550 us
software sync and a half-symbol low; the 30415 us gap.
"""
from __future__ import annotations

import dataclasses
import random

import pytest

from custom_components.hair import rf_family, rf_frames
from custom_components.hair.rf_family import CERTAINTY_DECODED, family_of, family_payload
from custom_components.hair.tests.test_rf_family import _frame as _pt_frame
from custom_components.hair.tests.test_rf_family_keeloq import _bits as _kl_bits
from custom_components.hair.tests.test_rf_family_keeloq import _word as _kl_word
from custom_components.hair.tests.test_rf_family_space_first import _sf_frame

ADDRESS = 0x1A2B3C
ROLLING = 0x0123


def _plain(
    *, command: int = 2, address: int = ADDRESS, rolling: int = ROLLING,
    key: int = 0xA7, good_check: bool = True,
) -> list[int]:
    data = [
        key, command << 4, rolling >> 8, rolling & 0xFF,
        address & 0xFF, (address >> 8) & 0xFF, address >> 16,
    ]
    check = 0
    for byte in data:
        check ^= (byte >> 4) ^ (byte & 0x0F)
    if not good_check:
        check ^= 0x5
    data[1] |= check
    return data


def _obfuscate(plain: list[int]) -> list[int]:
    sent = [plain[0]]
    for byte in plain[1:]:
        sent.append(byte ^ sent[-1])
    return sent


def _frame(
    plain: list[int] | None = None,
    *,
    half: float = 604.0,
    sync_pairs: int = 7,
    mark_widening: float = 0.0,
    spread: float = 0.0,
    seed: int = 0,
    gap: int | None = 30415,
    broken: tuple[int, ...] = (),
) -> list[int]:
    """One frame as HAIR files it: sync pairs, the software sync, the
    Manchester bits, the gap."""
    rng = random.Random(seed)
    sent = _obfuscate(plain if plain is not None else _plain())
    bits = [(byte >> (7 - i)) & 1 for byte in sent for i in range(8)]
    # In quarter-symbols: a sync pair is 8 high and 8 low, the software
    # sync 15 high (about 4550) and 2 low (half a symbol), a bit 2 and 2.
    levels: list[int] = []
    for _ in range(sync_pairs):
        levels += [1] * 8 + [0] * 8
    levels += [1] * 15 + [0] * 2
    for index, bit in enumerate(bits):
        first, second = (0, 1) if bit else (1, 0)
        if index in broken:  # no edge in the middle: not Manchester
            first = second
        levels += [first, first, second, second]
    out: list[int] = []
    for level in levels:
        if out and (out[-1] > 0) == bool(level):
            out[-1] += 1 if level else -1
        else:
            out.append(1 if level else -1)

    def width(quarters: int) -> int:
        return round(abs(quarters) * half * 0.5 * (1 + rng.uniform(-spread, spread)))

    timed = []
    for count in out:
        value = width(count)
        if count > 0:
            timed.append(round(value + mark_widening))
        else:
            timed.append(-round(max(value - mark_widening, 1)))
    if timed[-1] < 0:
        timed.pop()
    if gap is not None:
        timed.append(-gap)
    return timed


def _capture(plain: list[int] | None = None, *, repeats: int = 4) -> list[int]:
    """A whole press: the wake-up, the first frame (2 sync pairs), then
    repeats (7 sync pairs)."""
    out = [9415, -89565]
    out += _frame(plain, sync_pairs=2)
    for _ in range(repeats):
        out += _frame(plain, sync_pairs=7)
    return out


@pytest.fixture
def shown(monkeypatch):
    spec = dataclasses.replace(rf_family.FAMILIES["somfy_rts"], shown=True)
    monkeypatch.setitem(rf_family.FAMILIES, "somfy_rts", spec)
    rf_family._family_of.cache_clear()
    yield
    rf_family._family_of.cache_clear()


def _fields(result) -> dict[str, str]:
    return dict(result.fields)


class TestHeldOff:
    def test_it_is_off(self):
        assert rf_family.FAMILIES["somfy_rts"].shown is False

    def test_a_frame_reads_as_nothing_while_off(self):
        rf_family._family_of.cache_clear()
        assert family_of(_frame()) is None

    def test_it_is_read_with_the_hidden_families(self):
        result = family_of(_frame(), include_hidden=True)
        assert result.label == "Somfy RTS"
        assert result.certainty == CERTAINTY_DECODED


class TestWriteUpFrames:
    def test_a_frame(self, shown):
        result = family_of(_frame())
        assert result.label == "Somfy RTS"
        assert result.certainty == CERTAINTY_DECODED
        assert _fields(result) == {"address": "1A2B3C", "command": "2"}
        assert result.unit_us == 604
        assert result.aliases == ()

    @pytest.mark.parametrize("command", [1, 2, 3, 4, 5, 6, 8, 9, 10])
    def test_every_command_in_the_table_as_a_number(self, shown, command):
        assert _fields(family_of(_frame(_plain(command=command))))["command"] == str(command)

    @pytest.mark.parametrize("address", [0x000001, 0x800000, 0xFFFFFF, 0x10203])
    def test_the_address_is_little_endian(self, shown, address):
        assert _fields(family_of(_frame(_plain(address=address))))["address"] == f"{address:06X}"

    @pytest.mark.parametrize("pairs", [2, 7])
    def test_the_first_frame_and_the_repeats(self, shown, pairs):
        assert family_of(_frame(sync_pairs=pairs)).label == "Somfy RTS"

    @pytest.mark.parametrize("half", [520.0, 604.0, 640.0, 700.0])
    def test_the_clock_is_read_from_the_sync(self, shown, half):
        """The write-up's 604 and a commenter's 640 (from a patent), and a
        drifted clock either side."""
        assert _fields(family_of(_frame(half=half)))["address"] == "1A2B3C"

    @pytest.mark.parametrize("half", [420.0, 800.0])
    def test_the_clock_follows_the_sync_not_604(self, shown, half):
        """At these widths a fixed 604 would misread the halves."""
        assert _fields(family_of(_frame(half=half)))["address"] == "1A2B3C"

    @pytest.mark.parametrize("key", [0xA0, 0xAF, 0x37])
    def test_any_key(self, shown, key):
        """One commenter says the 0xA is not constant; the key is not
        checked."""
        assert family_of(_frame(_plain(key=key))) is not None

    def test_both_last_bits(self, shown):
        """A final 0 ends on a low half that runs into the gap."""
        seen = set()
        for address in range(0x10203, 0x10213):
            plain = _plain(address=address)
            seen.add(_obfuscate(plain)[6] & 1)
            assert _fields(family_of(_frame(plain)))["address"] == f"{address:06X}"
        assert seen == {0, 1}


class TestTheRollingPart:
    def test_no_field_carries_it(self, shown):
        payload = family_payload(_frame())
        assert {f["name"] for f in payload["fields"]} == {"address", "command"}

    def test_a_new_rolling_code_and_key_change_no_field(self, shown):
        one = family_payload(_frame(_plain(rolling=ROLLING, key=0xA1)))
        two = family_payload(_frame(_plain(rolling=0xBEEF, key=0xA9)))
        assert one == two


class TestMeasuredReceivers:
    @pytest.mark.parametrize("seed", range(10))
    def test_the_rm4_pros_mark_widening(self, shown, seed):
        frame = _frame(mark_widening=60, seed=seed)
        assert _fields(family_of(frame))["address"] == "1A2B3C"

    @pytest.mark.parametrize("seed", range(10))
    def test_a_receivers_spread(self, shown, seed):
        frame = _frame(spread=0.15, seed=seed)
        assert _fields(family_of(frame))["address"] == "1A2B3C"


class TestHairFilesTheFrame:
    def test_a_whole_press_votes_a_frame_that_reads_as_somfy(self, shown):
        capture = rf_frames.analyze(_capture())
        assert capture is not None
        assert family_of(capture.frame).label == "Somfy RTS"

    def test_the_wake_up_alone_is_not_a_frame(self, shown):
        assert family_of([9415, -89565]) is None


class TestRefusals:
    def test_a_bad_checksum_is_not_read(self, shown):
        assert family_of(_frame(_plain(good_check=False))) is None
        assert family_of(_frame(_plain(good_check=False)), include_hidden=True) is None

    @pytest.mark.parametrize("pairs", [1, 8])
    def test_another_count_of_sync_pairs(self, shown, pairs):
        assert family_of(_frame(sync_pairs=pairs)) is None

    def test_a_lost_bit(self, shown):
        frame = _frame()
        del frame[30:32]
        assert family_of(frame) is None

    def test_a_long_width_in_the_data(self, shown):
        frame = _frame()
        frame[30] = frame[30] * 4
        assert family_of(frame) is None

    @pytest.mark.parametrize("width", [2416, 3200, 6000])
    def test_a_software_sync_of_another_width(self, shown, width):
        frame = _frame()
        index = 14  # after 7 sync pairs
        assert frame[index] > 4000
        frame[index] = width
        assert family_of(frame) is None

    def test_an_uneven_sync_pair(self, shown):
        frame = _frame()
        frame[0] = 1200
        assert family_of(frame) is None

    def test_a_width_of_three_half_symbols(self, shown):
        frame = _frame()
        index = next(
            i for i in range(16, len(frame) - 1) if abs(frame[i]) > 1000
        )
        frame[index] = round(frame[index] * 1.5)
        assert family_of(frame) is None

    @pytest.mark.parametrize("value", [0, 1])
    def test_a_bit_with_no_middle_edge(self, shown, value):
        """A bit held at its second half, between neighbours that keep
        every width at one or two halves: the bits and the checksum are
        as sent, so only the Manchester rule refuses it."""
        bits = [
            (byte >> (7 - i)) & 1 for byte in _obfuscate(_plain()) for i in range(8)
        ]
        index = next(
            i for i in range(1, len(bits) - 1)
            if bits[i] == value and bits[i - 1] != value and bits[i + 1] == value
        )
        assert family_of(_frame()) is not None
        assert family_of(_frame(broken=(index,))) is None


class TestEveryShapeRefusesTheOthers:
    @pytest.mark.parametrize("seed", range(5))
    def test_somfy_is_read_by_its_shape_only(self, seed):
        frame = tuple(_frame(spread=0.1, seed=seed))
        assert rf_family._manchester_somfy(frame) is not None
        assert rf_family._pt2262_ev1527(frame) is None
        assert rf_family._space_first_1_2(frame) is None
        assert rf_family._mark_first_1_2(frame) is None

    @pytest.mark.parametrize("seed", range(5))
    def test_the_other_shapes_are_not_somfy(self, seed):
        for frame in (
            _pt_frame(0x950E49, seed=seed, short_spread=0.2),
            _sf_frame("101000111110", seed=seed, short_spread=0.2),
            _sf_frame("1011001110001111000011010101", unit=400, gap_units=23,
                      seed=seed, short_spread=0.2),
            _kl_word(_kl_bits(), seed=seed, short_spread=0.2),
        ):
            assert rf_family._manchester_somfy(tuple(frame)) is None
