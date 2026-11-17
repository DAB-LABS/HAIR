"""The radio pill, live.

``hair/rf/validate`` names a pasted code's family while it is being
edited, as infrared does: ``rf_family``, the object the saved row's pill
reads. It is read off the frame that will be stored, by the same reader
the saved row's pill uses (``rf_family.family_payload``), so the pill
while typing and the pill after Save cannot disagree. A family that is
held off shows nothing, an unrecognised code shows nothing, and a decoder
that fails costs the pill, never the answer.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair import rf_family, rf_paste
from custom_components.hair.models import UnknownSignal
from custom_components.hair.rf_family import LABEL_EV1527, family_payload
from custom_components.hair.tests.test_rf_family import _frame as _pt_frame
from custom_components.hair.tests.test_rf_family_keeloq import _bits as _kl_bits
from custom_components.hair.tests.test_rf_family_keeloq import _capture as _kl_capture
from custom_components.hair.tests.test_rf_family_somfy import _capture as _somfy_capture
from custom_components.hair.tests.test_rf_family_space_first import _sf_frame
from custom_components.hair.tests.test_rf_paste import IT104_B64


def _text(values) -> str:
    return " ".join(str(v) for v in values)


def _saved_pill(result):
    """The pill the row gets once the paste is saved: apply_code writes
    it, and the panel's rows go through family_payload."""
    row = UnknownSignal(id="s1", fingerprint="x", raw_timings=[])
    rf_paste.apply_code(row, result)
    return family_payload(row.raw_timings)


@pytest.fixture(autouse=True)
def _fresh_cache():
    rf_family._family_of.cache_clear()
    yield
    rf_family._family_of.cache_clear()


PASTES = {
    "the bench keyfob (RM4 Pro, 0xB1)": IT104_B64,
    "an EV1527 burst": _text(_pt_frame(0x95A3C6) * 4),
    "a PT2262 burst": _text(_pt_frame(0x555555) * 4),
    "an HT12E burst": _text(_sf_frame("101100111010") * 4),
    "a KeeLoq press": _text(_kl_capture(_kl_bits())),
}


class TestTheLivePillIsTheSavedPill:
    @pytest.mark.parametrize("paste", PASTES.values(), ids=PASTES.keys())
    def test_validate_names_what_the_saved_row_will(self, paste):
        result = rf_paste.validate(paste, 433_920_000)
        assert result["ok"] is True
        assert result["rf_family"] == _saved_pill(result)
        assert result["rf_family"] is not None

    def test_the_bench_keyfob_reads_as_ev1527(self):
        result = rf_paste.validate(IT104_B64)
        assert result["rf_family"]["label"] == LABEL_EV1527

    def test_the_door_carries_it(self):
        from custom_components.hair.websocket_api import ws_rf_validate

        conn = MagicMock()
        ws_rf_validate(MagicMock(), conn, {"id": 1, "text": IT104_B64})
        assert conn.send_result.call_args.args[1]["rf_family"]["label"] == LABEL_EV1527


class TestNothingIsShownThatIsNotProven:
    def test_a_family_that_is_held_off_shows_nothing(self):
        """Somfy RTS is decoded but not shown yet: no pill."""
        result = rf_paste.validate(_text(_somfy_capture()), 433_420_000)
        assert result["ok"] is True
        assert rf_family.family_of(result["frame"], include_hidden=True) is not None
        assert result["rf_family"] is None
        assert result["rf_family"] == _saved_pill(result)

    def test_an_unrecognised_code_shows_nothing(self):
        frame = []
        for width in (300, 900, 600, 1500, 300, 1200) * 6:
            frame += [width, -width]
        result = rf_paste.validate(_text([*frame, 300, -12000] * 3), 433_920_000)
        assert result["ok"] is True
        assert result["rf_family"] is None

    def test_a_refused_paste_carries_no_pill(self):
        result = rf_paste.validate("350 -1050")
        assert result["ok"] is False
        assert "rf_family" not in result

    def test_rf_raw_is_never_the_label(self):
        for paste in PASTES.values():
            pill = rf_paste.validate(paste, 433_920_000)["rf_family"]
            assert pill is None or "RF_RAW" not in pill["label"]


class TestADecoderFailure:
    def test_costs_the_pill_never_the_answer(self):
        def broken(_frame):
            raise ZeroDivisionError

        with patch.object(rf_family, "_SHAPES", (broken,)):
            result = rf_paste.validate(IT104_B64)
        assert result["ok"] is True
        assert result["rf_family"] is None
        assert result["fingerprint"]


class TestARollingCode:
    """The editor is told before Save that a pasted code is a rolling
    code, which HAIR never sends."""

    def test_a_keeloq_press_says_so(self):
        rf_family._rolling_family.cache_clear()
        result = rf_paste.validate(PASTES["a KeeLoq press"], 433_920_000)
        assert result["ok"] is True
        assert result["rf_rolling"] == "keeloq"

    def test_a_fixed_code_does_not(self):
        rf_family._rolling_family.cache_clear()
        result = rf_paste.validate(IT104_B64)
        assert result["rf_rolling"] is None

    def test_a_refused_paste_has_no_key(self):
        assert "rf_rolling" not in rf_paste.validate("350 -1050")

