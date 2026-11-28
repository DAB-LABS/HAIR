"""Security+ 1.0: the half-word reader, the pairing, replay and the guard.

The frames here come from the test's own encoder, written from the same
published description as the reader: they prove the code agrees with
itself, not with a real remote. A capture of a real one confirms it.
"""
from __future__ import annotations

import random
import types
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair import rf_frames, rf_secplus
from custom_components.hair.const import RF_MIN_FRAMES
from custom_components.hair.rf_family import rolling_family
from custom_components.hair.rf_replay import HELD, NEW, REPLAY, RollingReplay
from custom_components.hair.tests.test_rf_family import _frame as _pt_frame
from custom_components.hair.tests.test_rf_hear import (
    RECEIVER,
    _Modulation,
    _monitor,
    _state,
)

UNIT = 500


def _frame(symbols, sync, unit=UNIT):
    """One frame: the sync mark, then a space and a mark per symbol, each
    symbol four units long and its mark one, two or three of them."""
    out = [(sync + 1) * unit]
    for symbol in symbols:
        mark = (symbol + 1) * unit
        out += [-(4 * unit - mark), mark]
    return out


def _symbols(seed):
    rng = random.Random(seed)
    return [rng.randrange(3) for _ in range(20)], [rng.randrange(3) for _ in range(20)]


def _press(first, second, repeats=4, gap=58_000):
    edges = []
    for _ in range(repeats):
        edges += [*_frame(first, 0), -gap, *_frame(second, 2), -gap]
    return edges


class TestTheHalfReader:
    def test_both_frames_read_with_their_sync(self):
        first, second = _symbols(1)
        assert rf_secplus.read_half(_frame(first, 0)) == rf_secplus.Half(1, tuple(first))
        assert rf_secplus.read_half(_frame(second, 2)) == rf_secplus.Half(2, tuple(second))

    def test_the_unit_comes_from_the_frame(self):
        first, _ = _symbols(2)
        assert rf_secplus.read_half(_frame(first, 0, unit=430)).symbols == tuple(first)

    def test_a_trailing_gap_is_dropped(self):
        first, _ = _symbols(3)
        assert rf_secplus.read_half([*_frame(first, 0), -58_000]) is not None

    @pytest.mark.parametrize("change", ["sync1", "short", "long", "unit"])
    def test_anything_else_is_not_security_plus(self, change):
        first, _ = _symbols(4)
        frame = {
            "sync1": _frame(first, 1),
            "short": _frame(first[:19], 0),
            "long": _frame([*first, 1], 0),
            "unit": _frame(first, 0, unit=100),
        }[change]
        assert rf_secplus.read_half(frame) is None

    def test_a_fixed_code_frame_is_never_a_half(self):
        assert rf_secplus.read_half(_pt_frame(0x95A3C6)) is None


class TestTheGate:
    def test_the_body_gate_keeps_every_frame_of_a_press(self):
        first, second = _symbols(5)
        pieces = rf_frames.split_frames(_press(first, second))
        bodied = rf_frames.bodied_pieces(pieces)
        assert len(bodied) == len(pieces) == 8
        halves = [rf_secplus.read_half(piece.edges) for piece, _parts in bodied]
        assert [h.frame_no for h in halves] == [1, 2] * 4


class TestTheWord:
    def test_a_whole_press_in_one_capture_is_one_word(self):
        first, second = _symbols(6)
        bodied = rf_frames.bodied_pieces(rf_frames.split_frames(_press(first, second)))
        word = rf_secplus.pair_in_capture(bodied, rf_frames.vote, RF_MIN_FRAMES)
        assert word is not None
        one, two = rf_secplus.read_word(word.frame)
        assert (one.symbols, two.symbols) == (tuple(first), tuple(second))

    def test_one_half_alone_is_no_word(self):
        first, _ = _symbols(7)
        capture = ([*_frame(first, 0), -58000]) * 4
        bodied = rf_frames.bodied_pieces(rf_frames.split_frames(capture))
        assert rf_secplus.pair_in_capture(bodied, rf_frames.vote, RF_MIN_FRAMES) is None

    def test_a_word_is_never_sent_even_before_it_decodes(self):
        first, second = _symbols(8)
        frame = rf_secplus.word_frame(_frame(first, 0), _frame(second, 2), 58_000)
        assert rolling_family(frame) == "secplus_v1"

    def test_a_fixed_code_frame_keeps_its_family(self):
        assert rolling_family(_pt_frame(0x95A3C6)) is None


def _voted(frame):
    return types.SimpleNamespace(
        frame=frame, fingerprint="f" * 16, frame_hash="h" * 16, body_edges=41,
        votes=4, gap_us=58_000, gap_source="measured", sl_pattern="S",
    )


class TestTheHolder:
    def _halves(self, seed=9):
        first, second = _symbols(seed)
        return _voted(_frame(first, 0)), _voted(_frame(second, 2)), first, second

    @pytest.mark.parametrize("order", ["first", "second"])
    def test_the_two_halves_meet_in_either_order(self, order, monkeypatch):
        monkeypatch.setattr(
            rf_secplus.dataclasses, "replace",
            lambda obj, **kw: types.SimpleNamespace(**{**vars(obj), **kw}),
        )
        dropped = []
        holder = rf_secplus.HalfHolder(lambda rid, a: dropped.append(rid))
        one, two, first, second = self._halves()
        a, b = (one, two) if order == "first" else (two, one)
        assert holder.offer("rx", a, "a", 10.0) == (None, None, None)
        word, extra, passthrough = holder.offer("rx", b, "b", 10.1)
        assert passthrough is None and extra == ("a" if order == "first" else "b")
        halves = rf_secplus.read_word(word.frame)
        assert (halves[0].symbols, halves[1].symbols) == (tuple(first), tuple(second))
        assert dropped == []

    def test_a_half_that_waits_too_long_is_dropped(self):
        dropped = []
        holder = rf_secplus.HalfHolder(lambda rid, a: dropped.append(rid))
        one, two, *_ = self._halves()
        holder.offer("rx", one, None, 10.0)
        assert holder.offer("rx", two, None, 10.0 + rf_secplus.HALF_WAIT_S + 0.1) == (
            None, None, None,
        )
        assert dropped == ["rx"]

    def test_anything_else_passes_through(self):
        holder = rf_secplus.HalfHolder(lambda rid, a: None)
        other = _voted(_pt_frame(0x95A3C6))
        assert holder.offer("rx", other, None, 10.0) == (None, None, other)

    def test_receivers_are_apart(self):
        dropped = []
        holder = rf_secplus.HalfHolder(lambda rid, a: dropped.append(rid))
        one, two, *_ = self._halves()
        holder.offer("rx1", one, None, 10.0)
        assert holder.offer("rx2", two, None, 10.1) == (None, None, None)


class TestReplay:
    def _identity(self, rolling, fixed="0000ABCD"):
        return types.SimpleNamespace(
            family="secplus_v1", remote=fixed, button=fixed, rolling=rolling, seed=False,
        )

    def test_ahead_is_new_the_same_is_held_behind_is_replay(self):
        replay = RollingReplay()
        assert replay.check(self._identity(300), 1.0) == NEW
        assert replay.check(self._identity(300), 1.5) == HELD
        assert replay.check(self._identity(303), 5.0) == NEW
        assert replay.check(self._identity(300), 9.0) == REPLAY

    def test_far_ahead_is_still_a_press(self):
        replay = RollingReplay()
        replay.check(self._identity(300), 1.0)
        assert replay.check(self._identity(300 + 3 * 5_000), 5.0) == NEW

    def test_it_wraps_at_32_bits(self):
        replay = RollingReplay()
        replay.check(self._identity((1 << 32) - 2), 1.0)
        assert replay.check(self._identity(1), 5.0) == NEW


async def _hear(fake_hass, monitor, capture, at=1_000.0):
    tasks = []
    fake_hass.async_create_task = MagicMock(side_effect=tasks.append)
    fake_hass.states.get = MagicMock(return_value=_state(
        RECEIVER, capturing=True, capture_phase="listening", frequency_hz=390_000_000,
    ))
    signal = types.SimpleNamespace(
        timings=list(capture), frequency=None, modulation=_Modulation.OOK,
    )
    with patch(
        "custom_components.hair.signal_monitor.time.time", return_value=at,
    ), patch(
        "custom_components.hair.signal_monitor.time.monotonic", return_value=at,
    ):
        monitor._on_rf_signal(signal, RECEIVER)
        while tasks:
            await tasks.pop(0)


@pytest.mark.asyncio
class TestThroughTheMonitor:
    async def test_a_whole_press_files_one_row_holding_the_word(self, fake_hass):
        fake_hass.loop = MagicMock()
        fake_hass.loop.time = MagicMock(return_value=1_000.0)
        monitor, store = _monitor(fake_hass)
        monitor._trigger_manager = None
        first, second = _symbols(10)
        await _hear(fake_hass, monitor, _press(first, second))
        (device,) = store.get_all_devices()
        (row,) = device.signals
        halves = rf_secplus.read_word(row.raw_timings)
        assert (halves[0].symbols, halves[1].symbols) == (tuple(first), tuple(second))

    async def test_halves_voted_one_at_a_time_file_one_row(self, fake_hass):
        monitor, store = _monitor(fake_hass)
        monitor._trigger_manager = None
        first, second = _symbols(11)
        one = types.SimpleNamespace(
            timings=[], frequency=None, modulation=_Modulation.OOK,
        )
        bodied_one = rf_frames.bodied_pieces(
            rf_frames.split_frames(([*_frame(first, 0), -58000]) * 4))
        bodied_two = rf_frames.bodied_pieces(
            rf_frames.split_frames(([*_frame(second, 2), -58000]) * 4))
        tasks = []
        fake_hass.async_create_task = MagicMock(side_effect=tasks.append)
        fake_hass.states.get = MagicMock(return_value=_state(
            RECEIVER, capturing=True, capture_phase="listening",
            frequency_hz=390_000_000,
        ))
        with patch(
            "custom_components.hair.signal_monitor.time.time", return_value=1_000.0,
        ), patch(
            "custom_components.hair.signal_monitor.time.monotonic", return_value=1_000.0,
        ):
            monitor._emit_rf(rf_frames.vote(bodied_one), one, RECEIVER, frames=4)
            assert tasks == []
            monitor._emit_rf(rf_frames.vote(bodied_two), one, RECEIVER, frames=4)
            while tasks:
                await tasks.pop(0)
        (device,) = store.get_all_devices()
        (row,) = device.signals
        assert rf_secplus.read_word(row.raw_timings) is not None


# ---------------------------------------------------------------------------
# The decode, and whole presses through the monitor
# ---------------------------------------------------------------------------


def _digits(value, count=20):
    out = []
    for _ in range(count):
        value, digit = divmod(value, 3)
        out.append(digit)
    return out[::-1]


def _encode(fixed, rolling):
    """The two frames' symbols for a fixed and a rolling code, from the
    published description: the rolling code's 32 bits reversed and its
    top bit cleared, both codes in base 3, then per frame a rolling digit
    and a fixed digit sent as (fixed + running sum) mod 3."""
    mirrored = int(f"{rolling:032b}"[::-1], 2) & ((1 << 31) - 1)
    rolling_digits, fixed_digits = _digits(mirrored), _digits(fixed)
    halves = []
    for start in (0, 10):
        running, symbols = 0, []
        for r, f in zip(rolling_digits[start:start + 10], fixed_digits[start:start + 10],
                        strict=True):
            symbols.append(r)
            running += r
            symbols.append((f + running) % 3)
            running += f
        halves.append(symbols)
    return halves


class TestTheDecode:
    def test_the_worked_example(self):
        """40 symbols worked by hand from the published description: they
        check the decode against our own reading of it, not a remote."""
        first = rf_secplus.Half(1, tuple(int(c) for c in "00100002221000012101"))
        second = rf_secplus.Half(2, tuple(int(c) for c in "12010012210202201100"))
        assert rf_secplus.decode(first, second) == (876029924, 2731817112)

    @pytest.mark.parametrize("fixed, rolling", [
        (876029922, 2731817116), (292009974 * 3 + 1, 2), (0, 0), (3 ** 20 - 1, 4294967294),
    ])
    def test_encode_then_decode(self, fixed, rolling):
        one, two = _encode(fixed, rolling)
        assert rf_secplus.decode(
            rf_secplus.Half(1, tuple(one)), rf_secplus.Half(2, tuple(two)),
        ) == (fixed, rolling)

    def test_a_rolling_value_too_big_to_have_been_sent_is_no_word(self):
        first = rf_secplus.Half(1, (2,) * 20)
        second = rf_secplus.Half(2, (2,) * 20)
        assert rf_secplus.decode(first, second) is None

    def test_the_identity_is_the_remote_and_its_button(self):
        from custom_components.hair.rf_family import rolling_identity

        one, two = _encode(876029923, 2731817112)
        identity = rolling_identity(rf_secplus.word_frame(_frame(one, 0), _frame(two, 2), 58_000))
        assert (identity.family, identity.remote, identity.button, identity.rolling) == (
            "secplus_v1", f"{876029923 // 27:07X}", "1", 2731817112,
        )


def _press_of(fixed, rolling):
    one, two = _encode(fixed, rolling)
    return _press(one, two)


@pytest.mark.asyncio
class TestPressesThroughTheMonitor:
    async def _monitor(self, fake_hass):
        fake_hass.loop = MagicMock()
        fake_hass.loop.time = MagicMock(return_value=1_000.0)
        monitor, store = _monitor(fake_hass)
        monitor._trigger_manager = None
        return monitor, store

    async def test_three_presses_of_a_button_are_one_row(self, fake_hass):
        monitor, store = await self._monitor(fake_hass)
        for n, rolling in enumerate((2731817112, 2731817116, 2731817118)):
            await _hear(fake_hass, monitor, _press_of(876029924, rolling), at=1_000.0 + 10 * n)
        (device,) = store.get_all_devices()
        (row,) = device.signals
        assert row.hit_count == 3

    async def test_another_button_is_its_own_row_on_the_remotes_card(self, fake_hass):
        monitor, store = await self._monitor(fake_hass)
        await _hear(fake_hass, monitor, _press_of(876029924, 2731817112), at=1_000.0)
        await _hear(fake_hass, monitor, _press_of(876029923, 2731817120), at=1_010.0)
        (device,) = store.get_all_devices()
        assert len(device.signals) == 2

    async def test_an_old_word_played_back_is_dropped(self, fake_hass):
        monitor, store = await self._monitor(fake_hass)
        await _hear(fake_hass, monitor, _press_of(876029924, 2731817116), at=1_000.0)
        await _hear(fake_hass, monitor, _press_of(876029924, 2731817112), at=1_010.0)
        (device,) = store.get_all_devices()
        (row,) = device.signals
        assert row.hit_count == 1

    async def test_a_word_is_never_sent(self, fake_hass):
        frame = rf_secplus.word_frame(*(_frame(h, s) for h, s in zip(
            _encode(876029924, 2731817112), (0, 2), strict=True)), 58_000)
        assert rolling_family(frame) == "secplus_v1"
