"""DAIKIN64: the field map, and a Power press heard by its role (GH #183).

A Daikin64 handset writes its clock and its two timers into every press,
so before this map a press never matched the state it named. The map
reads mode, fan and temperature and nothing else, so read-bytes identity
leaves the clock out of the key, as it does for DAIKIN152.

The frame carries no on/off. Its Power button sets one bit and leaves the
rest of the frame as the state the unit is in, so the file's power code
is a state code plus that bit, and a handset's Power press can be made at
any state. Schema v0.7 reads the bit as a ROLE, never as a state field: a
press whose bit is set has one identity, the role's, whatever state it
carries, so every matcher (the cell index, triggers, known commands)
hears every Power press as the power code, and only as that.

The facts come from IRremoteESP8266's Daikin64 description (layout,
timing, checksum; no code) and from the reporter's file on GH #183 (271
codes, every checksum holding; recorded in the map's derivation, not kept
here). The field pack is synthetic, built from the map the way the #183
file behaves: the clock moving between codes, dry forcing the fan, and
fan_only ignoring the temperature and pairing its fan labels. Like the
other packs it carries no "off"; ``_pack`` adds one.
"""
from __future__ import annotations

import dataclasses

import pytest

from custom_components.hair import field_readers as fr
from custom_components.hair.event_parser import EventParser
from custom_components.hair.identity import TIER_BYTE_HASH
from custom_components.hair.matrix_listener import build_cell_index
from custom_components.hair.wig_format import ClimateMatrix

from .test_cell_index_shared_keys import _match, _pack_matrix

# The published known-good state, bytes 0 to 7, least significant first:
# cool / med / 16, clock 07:20, both timers 22:00 and unset, power bit set.
KNOWN_GOOD = 0x7C16161607204216
_UNIT_US = 109 * 0.241246


def _bcd(value: int) -> int:
    return ((value // 10) << 4) | (value % 10)


def _with_checksum(data: list[int]) -> list[int]:
    data = list(data)
    nibbles = [n for byte in data for n in (byte & 0xF, byte >> 4)][:15]
    data[7] = (data[7] & 0x0F) | ((sum(nibbles) & 0xF) << 4)
    return data


def _state(mode: int, fan: int, temp: int, *, power: bool = False,
           clock: int = 17 * 60, low: int = 0x07) -> list[int]:
    """One frame as eight bytes. ``low`` is byte 7's low nibble without
    the power bit (swing, sleep and bit 2 are all set in the #183 file)."""
    return _with_checksum([
        0x16, mode | (fan << 4), _bcd(clock % 60), _bcd(clock // 60 % 24),
        0x54, 0x23, _bcd(temp), (low & 0x7) | (0x08 if power else 0),
    ])


def _train(data: list[int]) -> list[int]:
    """The press on the air, signed microseconds, as a receiver hands it."""
    timings = [9800, -9800, 9800, -9800, 4600, -2500]
    for byte in data:
        for bit in range(8):
            timings += [350, -(954 if byte >> bit & 1 else 382)]
    timings += [350, -20300, 4600]
    return timings


def _pronto(data: list[int]) -> str:
    units = [max(1, round(abs(t) / _UNIT_US)) for t in _train(data)]
    units.append(4000)  # the closing gap
    words = ["0000", "006D", f"{len(units) // 2:04X}", "0000"]
    return " ".join(words + [f"{u:04X}" for u in units])


MAP = next(m for m in fr.library() if m.protocol_id == "DAIKIN64")

def _pack() -> ClimateMatrix:
    """The pack as a lattice, with an Off the way the #183 file writes
    one: cool / auto / 16 with the power bit set."""
    matrix = _pack_matrix("DAIKIN64.json")
    return dataclasses.replace(
        matrix, off=_pronto(_state(0x2, 0x1, 16, power=True, clock=1095)))


def _key(data: list[int]) -> str | None:
    return EventParser.pronto_read_key(_pronto(data))


def _role(code: str) -> int | None:
    return fr.read_role(fr.read_code(code, [MAP]), MAP, fr.ROLE_POWER_TOGGLE)


def _read(data: list[int]) -> fr.Reading:
    return fr.read_train(_train(data), [MAP])


class TestTheMap:
    def test_it_reads_the_state_and_keeps_the_power_bit_apart(self):
        assert [spec.name for spec in MAP.fields] == [
            "mode", "fan_speed", "temperature",
        ]
        assert list(MAP.roles) == [fr.ROLE_POWER_TOGGLE]

    def test_the_known_good_state_reads_and_its_checksum_holds(self):
        data = [(KNOWN_GOOD >> (8 * i)) & 0xFF for i in range(8)]
        reading = _read(data)
        assert reading.protocol_id == "DAIKIN64"
        assert reading.frames == (tuple(data),)
        (rule,) = MAP.integrity
        assert fr.check_integrity(reading, rule) is True
        assert fr.read_role(reading, MAP, fr.ROLE_POWER_TOGGLE) == 1

    def test_a_flipped_data_bit_fails_the_checksum(self):
        data = _state(0x2, 0x1, 24)
        data[6] ^= 0x01
        (rule,) = MAP.integrity
        assert fr.check_integrity(_read(data), rule) is False
        assert EventParser.pronto_read_key(_pronto(data)) is None


class TestTheKey:
    def test_the_clock_and_timers_are_not_in_it(self):
        one = _state(0x2, 0x8, 24, clock=7 * 60 + 5)
        two = _state(0x2, 0x8, 24, clock=19 * 60 + 41)
        two[4], two[5] = 0x00, 0x91
        two = _with_checksum(two)
        assert one != two
        key = EventParser.pronto_read_key(_pronto(one))
        assert key is not None
        assert EventParser.pronto_read_key(_pronto(two)) == key

    def test_a_power_press_has_the_roles_key_at_every_state(self):
        presses = [
            _state(mode, fan, temp, power=True, clock=clock)
            for mode, fan, temp, clock in (
                (0x2, 0x1, 16, 600), (0x8, 0x2, 21, 61), (0x1, 0x1, 30, 1439),
            )
        ]
        keys = {_key(p) for p in presses}
        assert len(keys) == 1 and None not in keys
        states = {_key(_state(0x2, 0x1, 16)), _key(_state(0x8, 0x2, 21))}
        assert not keys & states

    def test_a_power_press_and_its_state_differ_for_every_matcher(self):
        """Triggers and known commands key on (fingerprint, byte hash).
        Every DAIKIN64 code has the same S/L fingerprint, so the byte
        hash is all that tells Power from the state it was made at."""
        plain = _pronto(_state(0x8, 0x2, 21))
        power = _pronto(_state(0x8, 0x2, 21, power=True))
        assert EventParser.pronto_byte_hash(plain) != (
            EventParser.pronto_byte_hash(power))

    def test_swing_and_sleep_are_not_in_it(self):
        """Set in every code of the one file, so not fields yet: a
        handset with swing off still finds its state."""
        file_like = _pronto(_state(0x2, 0x1, 22, low=0x7))
        swing_off = _pronto(_state(0x2, 0x1, 22, low=0x4))
        assert EventParser.pronto_read_key(file_like) == (
            EventParser.pronto_read_key(swing_off))

    def test_states_differ(self):
        keys = {
            EventParser.pronto_read_key(_pronto(_state(mode, fan, temp)))
            for mode in (0x2, 0x8)
            for fan in (0x1, 0x8, 0x4, 0x2, 0x9, 0x3)
            for temp in (16, 23, 30)
        }
        assert len(keys) == 36


class TestThePack:
    """The synthetic pack, built the way the GH #183 file behaves."""

    def test_every_code_reads_and_its_checksum_holds(self):
        matrix = _pack()
        codes = [c.pronto for c in matrix.cells] + [matrix.off]
        assert len(codes) == 271  # as many as the #183 file
        (rule,) = MAP.integrity
        for code in codes:
            reading = fr.read_code(code, [MAP])
            assert reading.protocol_id == "DAIKIN64", code[:40]
            assert fr.check_integrity(reading, rule) is True

    def test_the_clock_moves_inside_the_file(self):
        matrix = _pack()
        clocks = {
            fr.read_code(c.pronto, [MAP]).frames[0][2:4] for c in matrix.cells
        }
        assert len(clocks) > 20

    def test_only_its_off_code_sets_the_power_bit(self):
        matrix = _pack()
        assert _role(matrix.off) == 1
        assert not any(_role(c.pronto) for c in matrix.cells)

    def test_its_off_is_cool_auto_16_plus_the_bit(self):
        matrix = _pack()
        twin = next(
            c for c in matrix.cells
            if (c.mode, c.fan, c.temp) == ("cool", "auto", 16.0)
        )
        off = fr.read_code(matrix.off, [MAP]).frames[0]
        state = fr.read_code(twin.pronto, [MAP]).frames[0]
        assert off[1] == state[1] and off[6] == state[6]
        assert off[7] & 0x0F == (state[7] & 0x0F) | 0x08


class TestTheCellIndex:
    @pytest.fixture(scope="class")
    def index(self):
        return build_cell_index(_pack())

    def test_its_off_twin_state_is_heard_as_itself(self, index):
        press = _pronto(_state(0x2, 0x1, 16, clock=9 * 60 + 13))
        assert _match(index, press) == ("cool/auto/16", None, TIER_BYTE_HASH)

    def test_a_handset_press_at_another_minute_finds_its_state(self, index):
        press = _pronto(_state(0x2, 0x9, 27, clock=23 * 60 + 59))
        assert _match(index, press) == ("cool/quiet/27", None, TIER_BYTE_HASH)

    def test_power_pressed_at_a_state_the_lattice_holds_is_off(self, index):
        """The case the role exists for: cool / low / 25 is a cell, and a
        Power press made there is still Power."""
        for mode, fan, temp in ((0x2, 0x8, 25), (0x1, 0x1, 19), (0x4, 0x4, 30)):
            press = _pronto(_state(mode, fan, temp, power=True, clock=362))
            assert _match(index, press) == ("off", "off", TIER_BYTE_HASH)

    def test_a_damaged_power_press_is_not_heard(self, index):
        press = _state(0x2, 0x8, 25, power=True)
        press[6] ^= 0x10
        result = _match(index, _pronto(press))
        assert result is None or result[0] != "off"


@pytest.mark.asyncio
async def test_the_listener_hears_a_power_press_at_a_held_state_as_off():
    """End to end through ``on_signal_captured``, at a state the file
    holds, with the train passed as the signal monitor passes it."""
    from unittest.mock import MagicMock

    from custom_components.hair.matrix_listener import MatrixListener
    from custom_components.hair.models import TriggerRemote
    from custom_components.hair.wig_identity import wig_signal_identity

    from .test_matrix_listener import _hass, _store_with

    matrix = _pack()
    remote = TriggerRemote(id="r1", name="Daikin handset", climate_matrix=True)
    store = _store_with(remote)
    hass = _hass(store)
    hass.async_create_task = MagicMock()
    listener = MatrixListener(hass, store, MagicMock(), MagicMock())
    listener._matrix_cache["r1"] = matrix
    listener._index_cache["r1"] = build_cell_index(matrix)
    recorded = []
    listener._record = lambda remote, hit, *a, **k: recorded.append(hit)

    for power in (True, False):
        press = _state(0x2, 0x8, 25, power=power, clock=3 * 60 + 30)
        identity = wig_signal_identity(_pronto(press))
        heard = await listener.on_signal_captured(
            identity.fingerprint, identity.byte_hash,
            identity.decoded_fingerprint, None, capture=_train(press),
        )
        assert heard == ["r1"]
        listener._recent_hits.clear()
    assert [(hit.power, hit.cell_key) for hit in recorded] == [
        ("off", "off"), (None, "cool/low/25"),
    ]
