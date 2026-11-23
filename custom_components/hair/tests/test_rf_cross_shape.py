"""A frame two shapes fit: no label, no rolling identity, and rolling if
either shape says so.

Each family's own tests have every other shape refuse its frames, so on
clean and jittered frames this never happens. A damaged frame could, and
then HAIR takes nothing from either reading: the pill stays blank, the
press keeps an ordinary frame identity, and the send refusal errs safe.
"""
from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from custom_components.hair import rf_family
from custom_components.hair.rf_family import (
    _Fit,
    _ShapeRead,
    family_of,
    fits_two_shapes,
    rolling_family,
    rolling_identity,
)
from custom_components.hair.tests.test_rf_family import _frame as _pt_frame
from custom_components.hair.tests.test_rf_family_dooya import _word as _dooya_word
from custom_components.hair.tests.test_rf_family_keeloq import _bits as _kl_bits
from custom_components.hair.tests.test_rf_family_keeloq import _word as _kl_word
from custom_components.hair.tests.test_rf_family_nexa_sl import _frame as _nexa_frame
from custom_components.hair.tests.test_rf_family_somfy import _frame as _somfy_frame
from custom_components.hair.tests.test_rf_family_space_first import _sf_frame
from custom_components.hair.tests.test_rf_hear import RECEIVER

FRAME = (400, -400, 1200, -400, 400, -1200, 400, -12000)
OTHER = (900, -900, 900, -900, 900, -18000)


def _shape(key: str, fields=(), rolling=None, accepts=FRAME):
    """A made-up shape decoder that reads ``accepts`` as one family."""

    def decode(frame):
        if frame != accepts:
            return None
        return _ShapeRead(500, (_Fit(key, tuple(fields), rolling),))

    return decode


KEELOQ_FIELDS = (("serial", "1234567"), ("buttons", "1"))


@pytest.fixture(autouse=True)
def _fresh_caches():
    for cached in (
        rf_family._family_of, rf_family._rolling_family, rf_family._rolling_identity,
    ):
        cached.cache_clear()
    yield
    for cached in (
        rf_family._family_of, rf_family._rolling_family, rf_family._rolling_identity,
    ):
        cached.cache_clear()


class TestOneShape:
    def test_a_fixed_family_reads_as_before(self):
        with patch.object(rf_family, "_SHAPES", (_shape("ev1527"),)):
            assert family_of(FRAME) is not None
            assert fits_two_shapes(FRAME) is False
            assert rolling_family(FRAME) is None

    def test_a_rolling_family_is_keyed_by_remote_and_button(self):
        with patch.object(
            rf_family, "_SHAPES", (_shape("keeloq", KEELOQ_FIELDS, rolling=7),)
        ):
            identity = rolling_identity(FRAME)
            assert (identity.family, identity.remote, identity.button) == (
                "keeloq", "1234567", "1",
            )
            assert rolling_family(FRAME) == "keeloq"


class TestTwoShapes:
    def test_no_label(self):
        with patch.object(rf_family, "_SHAPES", (_shape("ev1527"), _shape("pt2262"))):
            assert family_of(FRAME) is None
            assert family_of(FRAME, include_hidden=True) is None
            assert fits_two_shapes(FRAME) is True

    @pytest.mark.parametrize("rolling_first", [True, False])
    def test_rolling_if_either_says_so(self, rolling_first):
        shapes = [_shape("ev1527"), _shape("keeloq", KEELOQ_FIELDS, rolling=7)]
        if rolling_first:
            shapes.reverse()
        with patch.object(rf_family, "_SHAPES", tuple(shapes)):
            assert rolling_family(FRAME) == "keeloq"
            assert family_of(FRAME) is None

    def test_no_rolling_identity(self):
        shapes = (_shape("keeloq", KEELOQ_FIELDS, rolling=7), _shape("ev1527"))
        with patch.object(rf_family, "_SHAPES", shapes):
            assert rolling_identity(FRAME) is None

    def test_a_shape_that_fits_another_frame_does_not_count(self):
        shapes = (_shape("ev1527"), _shape("pt2262", accepts=OTHER))
        with patch.object(rf_family, "_SHAPES", shapes):
            assert family_of(FRAME) is not None
            assert fits_two_shapes(FRAME) is False


class TestRealFamiliesFitOneShape:
    @pytest.mark.parametrize("seed", range(3))
    def test_each_familys_own_frames(self, seed):
        frames = {
            "pt2262": _pt_frame(0x950E49, seed=seed, short_spread=0.2),
            "space first": _sf_frame("101000111110", seed=seed, short_spread=0.2),
            "keeloq": _kl_word(_kl_bits(), seed=seed, short_spread=0.2),
            "somfy": _somfy_frame(spread=0.1, seed=seed),
            "dooya": _dooya_word(spread=0.1, seed=seed),
            "nexa sl": _nexa_frame(spread=0.1, seed=seed),
        }
        for name, frame in frames.items():
            assert len(rf_family._fitting_reads(tuple(frame))) == 1, name
            assert fits_two_shapes(frame) is False, name


def _broken(_frame):
    raise ZeroDivisionError


class TestFailure:
    def test_a_decoder_that_raises_says_one_shape_and_logs(self, caplog):
        with patch.object(rf_family, "_SHAPES", (_broken,)), caplog.at_level(logging.WARNING):
            assert fits_two_shapes(FRAME) is False
        assert "_broken failed; its shape is skipped" in caplog.text

    @pytest.mark.parametrize("broken_first", [False, True])
    def test_a_decoder_that_raises_never_hides_a_rolling_read(self, broken_first, caplog):
        shapes = [_shape("keeloq", KEELOQ_FIELDS, rolling=7), _broken]
        if broken_first:
            shapes.reverse()
        with patch.object(rf_family, "_SHAPES", tuple(shapes)), caplog.at_level(logging.WARNING):
            assert rolling_family(FRAME) == "keeloq"
            identity = rolling_identity(FRAME)
            assert (identity.remote, identity.button) == ("1234567", "1")
            assert fits_two_shapes(FRAME) is False
        assert "_broken failed; its shape is skipped" in caplog.text

    def test_on_a_real_keeloq_word(self):
        from custom_components.hair.tests.test_rf_rolling_guard import KEELOQ

        with patch.object(rf_family, "_SHAPES", (*rf_family._SHAPES, _broken)):
            assert rolling_family(KEELOQ) == "keeloq"

    @pytest.mark.parametrize("frame", [None, [], ()])
    def test_no_frame(self, frame):
        assert fits_two_shapes(frame) is False


# --- the flag the panel reads -----------------------------------------------


class TestTheAmbiguousCount:
    def test_counts_until_a_clean_code(self):
        from custom_components.hair.rf_window import UnreadLedger

        ledger = UnreadLedger()
        assert ledger.readable("r", ambiguous=True) is True
        ledger.readable("r", ambiguous=True)
        assert ledger.fields("r")["ambiguous_radio"] == 2
        assert ledger.fields("r")["ambiguous_window_opened_at"] is not None
        assert ledger.readable("r") is True
        assert ledger.fields("r")["ambiguous_radio"] == 0
        assert ledger.fields("r")["ambiguous_window_opened_at"] is None

    def test_it_is_not_the_unread_count(self):
        from custom_components.hair.rf_window import UnreadLedger

        ledger = UnreadLedger()
        ledger.unread("r")
        ledger.readable("r", ambiguous=True)
        # A code that voted clears "can't read"; two shapes asks again.
        assert (ledger.count("r"), ledger.ambiguous("r")) == (0, 1)

    def test_a_new_window_starts_again(self):
        from custom_components.hair.rf_window import UnreadLedger

        ledger = UnreadLedger()
        ledger.readable("r", ambiguous=True)
        assert ledger.opened("r") is True
        assert ledger.ambiguous("r") == 0


@pytest.mark.asyncio
class TestAPressTwoShapesFit:
    async def test_the_row_asks_again_and_the_press_still_files(self, fake_hass):
        from custom_components.hair.tests.test_rf_unread import _hear, _windowed

        monitor, store = _windowed(fake_hass)
        with patch.object(rf_family, "fits_two_shapes", return_value=True):
            await _hear(fake_hass, monitor, _pt_frame(0x95A3C6) * 4)
        fields = monitor.rf_always_on.unread.fields(RECEIVER)
        assert fields["ambiguous_radio"] == 1
        assert fields["unread_radio"] == 0
        # Nothing is decided from it: the press files as it would.
        assert len(store.get_all_devices()) == 1

    async def test_a_clean_press_clears_it(self, fake_hass):
        from custom_components.hair.tests.test_rf_unread import _hear, _windowed

        monitor, _store = _windowed(fake_hass)
        with patch.object(rf_family, "fits_two_shapes", return_value=True):
            await _hear(fake_hass, monitor, _pt_frame(0x95A3C6) * 4)
        await _hear(fake_hass, monitor, _pt_frame(0x5A5A5A) * 4)
        assert monitor.rf_always_on.unread.ambiguous(RECEIVER) == 0
