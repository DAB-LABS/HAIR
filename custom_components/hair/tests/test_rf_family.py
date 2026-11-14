"""Family labels for radio codes: PT2262 and EV1527.

Fixtures are of two kinds only:

- synthetic frames generated here from the datasheet timings (the spec
  table in ``rf_family``), distorted the way the bench receivers were
  measured to distort them;
- the owner's own bench captures already in the repo (the IT104 keyfob
  through an RM4 Pro, and through an Athom one frame per capture).
"""
from __future__ import annotations

import gzip
import json
import random
from pathlib import Path

import pytest

from custom_components.hair import rf_family, rf_frames
from custom_components.hair.rf_family import (
    CERTAINTY_AMBIGUOUS,
    CERTAINTY_DECODED,
    LABEL_EV1527,
    LABEL_PT2262_OR_EV1527,
    family_of,
)

FIXTURES = Path(__file__).parent / "fixtures" / "rf"

# The keyfob's eight codes (bench, phase 0): button 1, 2, 3 on and off, ALL.
KEYFOB_ADDRESS = "950E4"
KEYFOB_DATA = set("13579BDF")


def _frame(
    code: int,
    *,
    unit: float = 400.0,
    mark_widening: float = 0.0,
    short_spread: float = 0.0,
    long_spread: float = 0.0,
    ratio: int = 3,
    sync: bool = True,
    gap_units: float | None = 31.0,
    bits: int = 24,
    seed: int = 0,
) -> list[int]:
    """A frame from the datasheet: 24 mark-first pairs of 1:3 or 3:1,
    first bit sent as the most significant, then the 1 T sync mark and
    (when measured) the 31 T gap, signed as a row stores it.

    ``mark_widening`` adds to every mark and takes from every space, as a
    receiver does; the spreads scale each short and long pulse by a
    random factor within that fraction; ``ratio`` 2 makes a 1:2 clone.
    """
    rng = random.Random(seed)

    def width(units: float, spread: float) -> float:
        return units * unit * (1 + rng.uniform(-spread, spread))

    out: list[int] = []
    for i in range(bits - 1, -1, -1):
        one = (code >> i) & 1
        long_units, short_units = ratio, 1
        if one:
            mark = width(long_units, long_spread) + mark_widening
            space = width(short_units, short_spread) - mark_widening
        else:
            mark = width(short_units, short_spread) + mark_widening
            space = width(long_units, long_spread) - mark_widening
        out += [round(mark), -round(max(space, 1))]
    if sync:
        out.append(round(width(1, short_spread) + mark_widening))
        if gap_units is not None:
            out.append(-round(gap_units * unit))
    else:
        out.pop()  # the last space runs into the gap the receiver cut
    return out


def _fields(result) -> dict[str, str]:
    return dict(result.fields)


class TestDatasheetFrames:
    def test_the_keyfob_code_is_an_ev1527(self):
        result = family_of(_frame(0x950E49))
        assert result.label == LABEL_EV1527
        assert result.certainty == CERTAINTY_DECODED
        assert _fields(result) == {"address": "950E4", "data": "9"}
        assert result.unit_us == 400

    def test_a_code_with_no_10_symbol_is_ambiguous(self):
        # Symbols 0 F 1 0 F F 0 0 1 0 0 1: pairs 00 01 11 00 01 01 00 00 11 00 00 11.
        code = int("000111000101000011000011", 2)
        result = family_of(_frame(code))
        assert result.label == LABEL_PT2262_OR_EV1527
        assert result.certainty == CERTAINTY_AMBIGUOUS
        assert _fields(result) == {"tri-state": "0F10FF001001", "code": f"{code:06X}"}

    def test_the_tri_state_reading_comes_first(self):
        result = family_of(_frame(int("01" * 12, 2)))
        assert [name for name, _ in result.fields] == ["tri-state", "code"]
        assert _fields(result)["tri-state"] == "F" * 12

    @pytest.mark.parametrize("unit", [71, 150, 263, 350, 390, 600, 1025])
    def test_any_oscillator_in_the_datasheets_range(self, unit):
        result = family_of(_frame(0x950E41, unit=unit))
        assert result.label == LABEL_EV1527 and result.unit_us == pytest.approx(unit, abs=2)


    def test_no_measured_gap(self):
        assert family_of(_frame(0x950E4F, gap_units=None)).label == LABEL_EV1527


class TestMeasuredReceivers:
    @pytest.mark.parametrize("seed", range(40))
    def test_the_rm4_pros_mark_widening(self, seed):
        result = family_of(_frame(0x950E4B, mark_widening=60, short_spread=0.08,
                                  long_spread=0.03, seed=seed))
        assert _fields(result) == {"address": "950E4", "data": "B"}

    @pytest.mark.parametrize("seed", range(40))
    def test_the_athoms_spread(self, seed):
        result = family_of(_frame(0x950E43, mark_widening=20, short_spread=0.30,
                                  long_spread=0.10, seed=seed))
        assert _fields(result) == {"address": "950E4", "data": "3"}

    def test_widening_at_a_fast_oscillator(self):
        # 150 us units with the RM4 Pro's 60 us: marks 40 percent long.
        result = family_of(_frame(0x950E45, unit=150, mark_widening=60))
        assert _fields(result) == {"address": "950E4", "data": "5"}


class TestRefusals:
    def test_a_1_to_2_clone_is_not_forced_into_1_to_3(self):
        assert family_of(_frame(0x950E49, ratio=2)) is None

    @pytest.mark.parametrize("bits", [12, 20, 23, 25, 28, 32])
    def test_another_length(self, bits):
        assert family_of(_frame(0x950E49 & ((1 << bits) - 1) | (1 << (bits - 1)),
                                bits=bits)) is None

    def test_a_corrupt_duration(self):
        """One stretched duration, as the RM4 Pro's capture seam makes: a
        refusal, never a misreading (the vote drops such frames first)."""
        frame = _frame(0x950E49)
        frame[24] = 4750
        assert family_of(frame) is None

    def test_a_pair_far_from_4_units(self):
        """Marks still split 1:3, but one pair runs 60 percent long (a
        space stretched by noise): every pair must be 4 T."""
        frame = _frame(0x950E49)
        frame[11] = round(frame[11] * 1.6) if frame[11] < -800 else frame[11] - 1000
        assert family_of(frame) is None

    def test_a_long_sync_mark(self):
        frame = _frame(0x950E49)
        frame[-2] = 1250
        assert family_of(frame) is None

    def test_no_sync_mark(self):
        """24 pairs that lost their last space read exactly like 23 pairs
        and a sync, so a frame without its sync mark is not read."""
        assert family_of(_frame(0x950E47, sync=False)) is None

    def test_a_gap_far_from_31_units(self):
        assert family_of(_frame(0x950E49, gap_units=80)) is None

    def test_nothing(self):
        assert family_of(None) is None and family_of([]) is None


class TestBench:
    """The owner's own captures of the IT104 keyfob."""

    def test_the_rm4_pro_captures(self):
        data = json.loads((FIXTURES / "it104-keyfob-433.json").read_text())
        seen = set()
        for capture in data["captures"]:
            timings = [v if i % 2 == 0 else -v for i, v in enumerate(capture["pulses"])]
            analysis = rf_frames.analyze(timings)
            assert analysis is not None
            result = family_of(analysis.frame)
            assert result is not None, capture["ts"]
            assert result.label == LABEL_EV1527
            fields = _fields(result)
            assert fields["address"] == KEYFOB_ADDRESS
            assert fields["data"] in KEYFOB_DATA
            seen.add(fields["data"])
        assert len(seen) >= 3

    def test_the_athom_frames(self):
        """One frame per capture: every whole frame the vote would keep
        reads as the keyfob."""
        with gzip.open(FIXTURES / "athom" / "athom-433-it104-150us-6ms-presses.json.gz") as f:
            data = json.loads(f.read())
        read = 0
        for _second, timings in data["captures"]:
            for piece, parts in rf_frames.bodied_pieces(rf_frames.split_frames(timings)):
                if len(parts.body) != 49:
                    continue
                edges = list(piece.edges[:-1] if piece.gap else piece.edges)
                frame = [v if i % 2 == 0 else -v for i, v in enumerate(edges)]
                if piece.gap:
                    frame.append(-piece.gap)
                result = family_of(frame)
                if result is None:
                    continue
                read += 1
                assert result.label == LABEL_EV1527
                assert _fields(result)["address"] == KEYFOB_ADDRESS
        assert read >= 50


class TestLabelsOnly:
    def test_the_result_is_plain_json(self):
        json.dumps(family_of(_frame(0x950E49)).to_dict())

    def test_identity_does_not_move(self):
        """Labelling a frame changes nothing the identity is made from."""
        frame = _frame(0x950E49)
        before = rf_frames.analyze(frame * 3)
        family_of(frame)
        after = rf_frames.analyze(frame * 3)
        assert (before.fingerprint, before.frame_hash) == (after.fingerprint, after.frame_hash)

    def test_the_module_imports_nothing_from_home_assistant(self):
        source = Path(rf_family.__file__).read_text()
        assert "homeassistant" not in source


# ---------------------------------------------------------------------------
# Where the label travels
# ---------------------------------------------------------------------------


class TestWhereItTravels:
    def test_the_drawers_slots(self):
        from custom_components.hair.rf_family import family_slots

        assert family_slots(_frame(0x950E49)) == {
            "protocol": "EV1527",
            "family_fields": [
                {"name": "address", "value": "950E4"}, {"name": "data", "value": "9"},
            ],
        }
        assert family_slots(_frame(0x950E49, ratio=2)) == {
            "protocol": None, "family_fields": None,
        }

    def test_a_radio_frame_event_and_a_send_carry_it(self):
        from custom_components.hair import candy_feed

        frame = _frame(0x950E41)
        event = candy_feed.rf_frame_event(
            ts=0.0, entity_id="radio_frequency.rx", name="RX", frame=frame,
            gap_us=12_400, gap_source="measured", fingerprint="fp", frame_hash="h",
            body_edges=49, frequency_hz=433_920_000, frequency_source="signal",
            raw=frame,
        )
        assert event["protocol"] == "EV1527"
        assert event["family_fields"][1] == {"name": "data", "value": "1"}

    def test_static_carries_none(self):
        from custom_components.hair import candy_feed

        summary = candy_feed.rf_static_summary_event(
            ts=0.0, entity_id="radio_frequency.rx", name="RX", count=3, since=0.0,
        )
        assert summary["protocol"] is None and summary["family_fields"] is None

    def test_the_doors_label_radio_rows_only(self):
        from custom_components.hair.websocket_api import _augment_rf_family

        rows = [
            {"medium": "rf", "raw_timings": _frame(0x950E49)},
            {"medium": "rf", "raw_timings": _frame(0x950E49, ratio=2)},
            {"raw_timings": [9000, -4500, 560]},
        ]
        _augment_rf_family(rows)
        assert rows[0]["rf_family"]["label"] == LABEL_EV1527
        assert rows[1]["rf_family"] is None
        assert "rf_family" not in rows[2]

    @pytest.mark.asyncio
    async def test_a_minted_row_carries_it_on_the_door_and_the_push(self, fake_hass):
        """A keyfob press through the receive path: the detected push and
        the Sniffer's remote door both carry the row's label, and the
        stored row does not."""
        from unittest.mock import MagicMock

        from custom_components.hair.const import DOMAIN, EVENT_SIGNAL_DETECTED
        from custom_components.hair.websocket_api import ws_get_unknown_device

        from .test_candy_radio import _hear, _monitor
        from .test_websocket_api import _make_connection

        data = json.loads((FIXTURES / "it104-keyfob-433.json").read_text())
        pulses = data["captures"][0]["pulses"]
        capture = [v if i % 2 == 0 else -v for i, v in enumerate(pulses)]
        monitor, store, _ = _monitor(fake_hass)
        await _hear(fake_hass, monitor, [capture])
        pushed = [
            c.args[1] for c in fake_hass.bus.async_fire.call_args_list
            if c.args[0] == EVENT_SIGNAL_DETECTED
        ]
        assert pushed and pushed[-1]["rf_family"]["label"] == LABEL_EV1527
        device = store.get_all_devices()[0]
        assert "rf_family" not in device.signals[0].to_dict()
        fake_hass.data[DOMAIN] = {
            "entry-1": {"device_manager": MagicMock(), "signal_monitor": monitor}
        }
        conn = _make_connection()
        await ws_get_unknown_device(
            fake_hass, conn,
            {"id": 1, "type": "hair/unknown/device", "device_id": device.id},
        )
        row = json.loads(json.dumps(conn.send_result.call_args[0][1]))["signals"][0]
        assert row["rf_family"]["fields"][0] == {"name": "address", "value": "950E4"}

    def test_a_failing_decoder_costs_one_row_its_label_not_the_page(
        self, monkeypatch
    ):
        from custom_components.hair import rf_family
        from custom_components.hair.websocket_api import _augment_rf_family

        bad = _frame(0x950E4B)
        real = rf_family.family_payload

        def payload(frame):
            if frame == bad:
                raise ZeroDivisionError
            return real(frame)

        monkeypatch.setattr(rf_family, "family_payload", payload)
        rows = [
            {"medium": "rf", "raw_timings": bad},
            {"medium": "rf", "raw_timings": _frame(0x950E49)},
        ]
        _augment_rf_family(rows)
        assert rows[0]["rf_family"] is None
        assert rows[1]["rf_family"]["label"] == LABEL_EV1527

    @pytest.mark.asyncio
    async def test_a_failing_decoder_never_costs_a_press_its_event(
        self, fake_hass, monkeypatch
    ):
        """The ruling: a decoder bug must never cost a press its event."""
        from custom_components.hair import rf_family
        from custom_components.hair.const import EVENT_SIGNAL_DETECTED

        from .test_candy_radio import _hear, _monitor

        def payload(frame):
            raise ZeroDivisionError

        monkeypatch.setattr(rf_family, "family_payload", payload)
        data = json.loads((FIXTURES / "it104-keyfob-433.json").read_text())
        pulses = data["captures"][0]["pulses"]
        capture = [v if i % 2 == 0 else -v for i, v in enumerate(pulses)]
        monitor, _store, _ = _monitor(fake_hass)
        await _hear(fake_hass, monitor, [capture])
        pushed = [
            c.args[1] for c in fake_hass.bus.async_fire.call_args_list
            if c.args[0] == EVENT_SIGNAL_DETECTED
        ]
        assert pushed and pushed[-1]["rf_family"] is None
        assert pushed[-1]["medium"] == "rf"

    @pytest.mark.asyncio
    async def test_a_devices_radio_command_carries_it(self, fake_hass):
        from unittest.mock import patch

        from custom_components.hair.models import IRDevice
        from custom_components.hair.websocket_api import _device_full

        from .test_candy_radio import _command

        command = _command(_frame(0x950E4B))
        device = IRDevice(id="d1", name="Bench Plug", device_type="switch",
                          commands=[command])
        with patch("custom_components.hair.websocket_api._ha_device_id",
                   return_value=None):
            full = await _device_full(fake_hass, device)
        assert full["commands"][0]["rf_family"]["fields"][1] == {
            "name": "data", "value": "B",
        }
        assert "rf_family" not in command.to_dict()
