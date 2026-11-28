"""Security+ 1.0: which presses share a card, and a half heard once.

A fixed code's third digit from the bottom says how it is laid out. Where
it is 2, the lowest digit names the button and the digits above the third
name the remote, so a remote's buttons share one card. The published
sample output of an open decoder has three buttons of one remote laid out
so, and those public values are the test here. Any other layout isn't
known, so each fixed code is its own card: the keypad samples from the
same output, and a made-up pair of buttons that agree in their lowest
digit and differ in the middle ones.

A half heard only once still makes a word when the two halves read as
one.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.hair import rf_frames, rf_secplus
from custom_components.hair.const import RF_MIN_FRAMES
from custom_components.hair.rf_family import rolling_identity
from custom_components.hair.rf_replay import NEW, RollingReplay
from custom_components.hair.tests.test_rf_hear import _monitor
from custom_components.hair.tests.test_rf_secplus import _encode, _frame, _hear, _press

# Published sample output: (rolling, fixed, button) for one remote's
# three buttons, remote 32445552.
REMOTE = 32445552
SAMPLE_BUTTONS = (
    (2320616982, 876029923, "1"),
    (3869428094, 876029922, "0"),
    (2731817112, 876029924, "2"),
)
# The same output's keypad: (rolling, fixed), third digit 0.
SAMPLE_KEYPAD = ((2615434900, 72906373), (2615434904, 595608121))
# Made up: two buttons, third digit 0, lowest digit 0 on both, apart in
# the fifth and sixth digits.
ONE_BUTTON = 1234567902
OTHER_BUTTON = 1234567497


def _bodied(timings):
    return rf_frames.bodied_pieces(rf_frames.split_frames(timings))


def _word(timings):
    return rf_secplus.pair_in_capture(_bodied(timings), rf_frames.vote, RF_MIN_FRAMES)


def _decoded(word):
    return rf_secplus.decode(*rf_secplus.read_word(word.frame))


def _word_of(fixed, rolling):
    one, two = _encode(fixed, rolling)
    return rf_secplus.word_frame(_frame(one, 0), _frame(two, 2), 58_000)


def _digit(fixed, n):
    return (fixed // 3 ** n) % 3


class TestARemotesLayout:
    def test_the_samples_are_laid_out_as_a_remote(self):
        assert {_digit(fixed, 2) for _, fixed, _ in SAMPLE_BUTTONS} == {2}

    def test_each_button_reads_as_published(self):
        identities = [rolling_identity(_word_of(f, r)) for r, f, _ in SAMPLE_BUTTONS]
        assert [(i.remote, i.button) for i in identities] == [
            (f"{REMOTE:07X}", b) for _, _, b in SAMPLE_BUTTONS
        ]

    def test_one_card_a_row_per_button(self):
        identities = [rolling_identity(_word_of(f, r)) for r, f, _ in SAMPLE_BUTTONS]
        assert len({i.device_key for i in identities}) == 1
        assert len({i.fingerprint for i in identities}) == 3

    def test_the_buttons_share_one_count(self):
        replay = RollingReplay()
        rolling, fixed, _ = SAMPLE_BUTTONS[0]
        assert replay.check(rolling_identity(_word_of(fixed, rolling)), 1.0) == NEW
        # Another button of the same remote, further on: a press.
        rolling, fixed, _ = SAMPLE_BUTTONS[2]
        assert replay.check(rolling_identity(_word_of(fixed, rolling)), 5.0) == NEW


class TestAnyOtherLayout:
    def test_the_made_up_pair_is_the_shape_meant(self):
        assert _digit(ONE_BUTTON, 2) == _digit(OTHER_BUTTON, 2) == 0
        assert ONE_BUTTON % 3 == OTHER_BUTTON % 3 == 0
        assert [n for n in range(20) if _digit(ONE_BUTTON, n) != _digit(OTHER_BUTTON, n)] == [4, 5]

    @pytest.mark.parametrize("pair", [
        (ONE_BUTTON, OTHER_BUTTON), tuple(f for _, f in SAMPLE_KEYPAD),
    ], ids=["made-up pair", "sample keypad"])
    def test_each_fixed_code_is_its_own_row_and_card(self, pair):
        one, two = (rolling_identity(_word_of(f, 1000 + n)) for n, f in enumerate(pair))
        assert (one.remote, two.remote) == tuple(f"{f:08X}" for f in pair)
        assert one.fingerprint != two.fingerprint
        assert one.device_key != two.device_key
        # Nothing names a button: no claim about which share a remote.
        assert one.button == two.button == ""

    def test_each_button_keeps_its_own_count(self):
        replay = RollingReplay()
        assert replay.check(rolling_identity(_word_of(OTHER_BUTTON, 900000000)), 1.0) == NEW
        # The other button's count is far below; it is not a replay.
        assert replay.check(rolling_identity(_word_of(ONE_BUTTON, 1500000000)), 5.0) == NEW

    def test_a_code_never_keys_a_remotes_card(self):
        # A whole code equal to a remote number still keys its own card.
        code = REMOTE * 3
        assert _digit(code, 2) != 2
        assert (
            rolling_identity(_word_of(code, 7)).device_key
            != rolling_identity(_word_of(876029923, 7)).device_key
        )


class TestOneCopyOfEachHalf:
    def test_is_a_word_when_the_halves_read_as_one(self):
        one, two = _encode(876029924, 2731817112)
        word = _word(_press(one, two, repeats=1))
        assert word is not None
        assert _decoded(word) == (876029924, 2731817112)

    def test_is_no_word_when_they_do_not(self):
        # Both halves read, but their rolling digits make a value too big
        # to have been sent: not a word, so the capture goes on as any
        # other.
        symbols = [2 if i % 2 == 0 else 1 for i in range(20)]
        capture = _press(symbols, symbols, repeats=1)
        halves = [rf_secplus.read_half(p.edges) for p, _ in _bodied(capture)]
        assert [h.frame_no for h in halves] == [1, 2]
        assert _word(capture) is None

    def test_copies_that_vote_vote_as_before(self):
        one, two = _encode(876029924, 2731817112)
        assert _decoded(_word(_press(one, two, repeats=4))) == (876029924, 2731817112)

    def test_copies_that_do_not_vote_fall_back_to_the_checked_copy(self):
        # Two copies of each that don't vote on their own: the best copy
        # of each is checked instead.
        one, two = _encode(876029924, 2731817112)
        assert _decoded(_word(_press(one, two, repeats=2))) == (876029924, 2731817112)

    def test_one_half_alone_is_still_no_word(self):
        one, _ = _encode(876029924, 2731817112)
        assert _word([*_frame(one, 0), -58_000]) is None


@pytest.mark.asyncio
class TestThroughTheMonitor:
    async def _monitor(self, fake_hass):
        fake_hass.loop = MagicMock()
        fake_hass.loop.time = MagicMock(return_value=1_000.0)
        monitor, store = _monitor(fake_hass)
        monitor._trigger_manager = None
        return monitor, store

    async def test_presses_of_one_copy_each_file_on_one_row(self, fake_hass):
        monitor, store = await self._monitor(fake_hass)
        for n, rolling in enumerate((1500000000, 1500000004, 1500000006)):
            one, two = _encode(ONE_BUTTON, rolling)
            await _hear(fake_hass, monitor, _press(one, two, repeats=1), at=1_000.0 + 10 * n)
        (device,) = store.get_all_devices()
        (row,) = device.signals
        assert row.hit_count == 3

    async def test_the_made_up_pair_is_two_cards(self, fake_hass):
        monitor, store = await self._monitor(fake_hass)
        presses = ((ONE_BUTTON, 1500000000), (OTHER_BUTTON, 900000000))
        for n, (fixed, rolling) in enumerate(presses):
            one, two = _encode(fixed, rolling)
            await _hear(fake_hass, monitor, _press(one, two), at=1_000.0 + 10 * n)
        devices = store.get_all_devices()
        assert len(devices) == 2
        assert all(len(device.signals) == 1 for device in devices)
