"""The TDC-38 decoder (GH #206).

The MR401 / Magenta set-top box codes in the issue had no decoder, so
their identity fell to the byte hash, whose 20-cycle bin erases this
protocol's 12- and 24-cycle edges: every code of one length shared one
identity. These pins cover the decoder itself, the cut-final-frame rule
and its four bounds, the registry and transmit round trip, the Clipper
paste that refused the codes, and the load-time backfill that narrows a
trigger and a Sniffer row made under the old shared identity.
"""
from __future__ import annotations

import csv
import random
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.decoders import split_frames
from custom_components.hair.decoders.rc5 import RC5Command
from custom_components.hair.decoders.rc6 import RC6Command
from custom_components.hair.decoders.tdc38 import TDC38Command
from custom_components.hair.identity import (
    canonical_byte_hash,
    canonical_fingerprint,
)
from custom_components.hair.ir_command import ProntoCommand
from custom_components.hair.protocol_decode import (
    build_protocol_command,
    try_decode_identity,
)

FIELD = Path(__file__).parent / "fixtures" / "field-captures"
POWER_FINGERPRINT = "TDC38:0x00ca:0x16"
HALF = 315
GAP = -89000


def _posted() -> dict[str, str]:
    with (FIELD / "gh206-mr401-pronto.csv").open(encoding="utf-8") as handle:
        return {row["key"]: row["code"] for row in csv.DictReader(handle)}


POSTED = _posted()
AIR_POWER = (FIELD / "gh206-power-air.pronto").read_text(encoding="utf-8").strip()


def _raw(code: str) -> list[int]:
    return ProntoCommand(code).get_raw_timings()


def _frame(device: int, subdevice: int, function: int, **kw) -> list[int]:
    return TDC38Command(
        device=device, subdevice=subdevice, function=function, **kw
    ).get_raw_timings()


def _manchester(cells: list[int], half: int = HALF) -> list[int]:
    """Any Manchester frame: 1 = mark-then-space, trailing space stripped."""
    out: list[int] = []
    for bit in cells:
        for value in ((half, -half) if bit else (-half, half)):
            if out and (out[-1] > 0) == (value > 0):
                out[-1] += value
            else:
                out.append(value)
    if out and out[0] < 0:
        out.pop(0)
    if out and out[-1] < 0:
        out.pop()
    return out


def _bits(device: int, subdevice: int, function: int) -> list[int]:
    return (
        [1]
        + [(device >> i) & 1 for i in range(4, -1, -1)]
        + [(subdevice >> i) & 1 for i in range(4, -1, -1)]
        + [(function >> i) & 1 for i in range(6, -1, -1)]
    )


def _cut(frame: list[int], cells: int) -> list[int]:
    """The first ``cells`` cells of a frame, as a learn window would cut it.

    The final timing is a 120us stub of the next one, shorter than any
    window: the capture stopped inside it.
    """
    halves: list[int] = []
    for value in frame:
        units = 1 if abs(value) < 450 else 2
        halves.extend([1 if value > 0 else -1] * units)
    kept = halves[: 2 * cells]
    out: list[int] = []
    for sign in kept:
        value = sign * HALF
        if out and (out[-1] > 0) == (value > 0):
            out[-1] += value
        else:
            out.append(value)
    # A stub of the next timing: the window closed partway through it.
    out.append(-120 if out[-1] > 0 else 120)
    return out


def _join(*frames: list[int]) -> list[int]:
    out: list[int] = []
    for index, frame in enumerate(frames):
        if index:
            out.append(GAP)
        out.extend(frame)
    return out


def _jitter(timings: list[int], marks: float, spaces: float) -> list[int]:
    return [int(v * marks) if v > 0 else int(v * spaces) for v in timings]


# ---------------------------------------------------------------------------
# 1. The protocol
# ---------------------------------------------------------------------------


class TestEncodeDecode:
    @pytest.mark.parametrize(
        ("device", "subdevice", "function"),
        [(0, 0, 0), (31, 31, 127), (6, 10, 22), (1, 0, 64), (16, 21, 85)],
    )
    @pytest.mark.parametrize("repeats", [0, 2])
    def test_round_trip(self, device, subdevice, function, repeats):
        timings = _frame(device, subdevice, function, repeat_count=repeats)
        decoded = TDC38Command.from_raw_timings(timings)
        assert decoded is not None
        assert (decoded.device, decoded.subdevice, decoded.function) == (
            device, subdevice, function,
        )
        assert decoded.repeat_count == repeats
        assert decoded.frames_explained == repeats + 1

    def test_every_value_of_every_field(self):
        """Every device and subdevice pair at both function extremes, and
        every function at three device/subdevice pairs."""
        cases = [(d, s, f) for d in range(32) for s in range(32) for f in (0, 127)]
        cases += [(d, s, f) for d, s in ((0, 0), (31, 31), (6, 10))
                  for f in range(128)]
        for device, subdevice, function in cases:
            decoded = TDC38Command.from_raw_timings(
                _frame(device, subdevice, function)
            )
            assert (decoded.device, decoded.subdevice, decoded.function) == (
                device, subdevice, function,
            )

    @pytest.mark.parametrize(
        "field", [{"device": 32}, {"subdevice": 32}, {"function": 128},
                  {"device": -1}],
    )
    def test_fields_are_bounds_checked(self, field):
        values = {"device": 6, "subdevice": 10, "function": 22, **field}
        with pytest.raises(ValueError):
            TDC38Command(**values)

    def test_the_encoder_matches_the_posted_codes_edge_for_edge(self):
        """The posted codes were generated from the IRP; ours must agree.

        Same edges, same signs, each within 1.5 percent (the Pronto
        rounds 315us to 12 carrier cycles of a 38kHz clock).
        """
        for name, code in POSTED.items():
            posted = split_frames(_raw(code), 8000)[0]
            identity = try_decode_identity(_raw(code))
            ours = _frame(identity.address >> 5, identity.address & 0x1F,
                          identity.command)
            assert len(ours) == len(posted), name
            for mine, theirs in zip(ours, posted, strict=True):
                assert (mine > 0) == (theirs > 0), name
                assert abs(abs(mine) - abs(theirs)) <= 0.015 * abs(theirs), name

    def test_a_held_press_repeats_with_the_irp_gap(self):
        # F=22 ends on a 0, so the frame ends on a mark and the gap is
        # the IRP's 89ms; F=23 ends on a 1, whose space joins the gap.
        ends_on_mark = _frame(6, 10, 22, repeat_count=1)
        ends_on_space = _frame(6, 10, 23, repeat_count=1)
        assert [v for v in ends_on_mark if v < -8000] == [-89000]
        assert [v for v in ends_on_space if v < -8000] == [-(89000 + HALF)]
        assert ends_on_mark[-1] > 0 and ends_on_space[-1] > 0


class TestThePostedCodes:
    def test_every_posted_code_is_device_6_subdevice_10(self):
        for name, code in POSTED.items():
            identity = try_decode_identity(_raw(code))
            assert identity is not None, name
            assert identity.protocol == "TDC38", name
            assert identity.address == (6 << 5) | 10, name
            assert identity.covers_capture is True, name
        assert len(POSTED) == 44

    def test_43_distinct_buttons_because_two_names_share_one_code(self):
        fingerprints = {
            name: try_decode_identity(_raw(code)).fingerprint
            for name, code in POSTED.items()
        }
        assert len(set(fingerprints.values())) == 43
        assert fingerprints["MenuHome"] == fingerprints["MenuMain"]

    def test_the_power_fingerprint_is_pinned(self):
        """Stored rows carry this exact string. A change to the label or
        to the address packing would strand every one of them."""
        identity = try_decode_identity(_raw(POSTED["PowerToggle"]))
        assert identity.fingerprint == POWER_FINGERPRINT

    def test_the_air_capture_is_the_posted_power_code(self):
        identity = try_decode_identity(_raw(AIR_POWER))
        assert identity is not None
        assert identity.fingerprint == POWER_FINGERPRINT
        assert identity.covers_capture is True


class TestDirtyCaptures:
    @pytest.mark.parametrize(
        ("marks", "spaces"), [(0.85, 1.12), (1.12, 0.85), (0.9, 0.9), (1.1, 1.1)]
    )
    def test_air_path_jitter(self, marks, spaces):
        for name in ("PowerToggle", "Back", "Digit1", "Search"):
            raw = _jitter(_raw(POSTED[name]), marks, spaces)
            expected = try_decode_identity(_raw(POSTED[name])).fingerprint
            identity = try_decode_identity(raw)
            assert identity is not None and identity.fingerprint == expected

    @pytest.mark.parametrize(
        ("mark", "space"), [(290, 290), (350, 350), (305, 335)]
    )
    def test_a_drifted_half_bit(self, mark, space):
        timings = _frame(6, 10, 22)
        rescaled = [
            int(v / HALF * mark) if v > 0 else int(v / HALF * space)
            for v in timings
        ]
        identity = try_decode_identity(rescaled)
        assert identity is not None and identity.fingerprint == POWER_FINGERPRINT

    def test_a_held_press_votes_and_covers(self):
        frame = _raw(POSTED["Back"])
        identity = try_decode_identity(_join(frame, frame, frame))
        assert identity.frames_total == 3
        assert identity.frames_explained == 3
        assert identity.covers_capture is True


class TestRejects:
    def test_seventeen_and_nineteen_cells(self):
        bits = _bits(6, 10, 22)
        assert TDC38Command.from_raw_timings(_manchester(bits[:-1])) is None
        assert TDC38Command.from_raw_timings(_manchester([*bits, 1])) is None

    def test_a_frame_opening_on_a_zero_cell(self):
        """Such a frame opens on a space, which the frame splitter drops,
        so what reaches the decoder is shifted by a half-bit; this one
        then fails the Manchester read. There is no start-cell check to
        reach: a frame always opens on a mark."""
        bits = _bits(6, 10, 22)
        bits[0] = 0
        assert TDC38Command.from_raw_timings(_manchester(bits)) is None

    def test_rc5_and_rc6(self):
        for timings in (
            RC5Command(address=5, command=0x35).get_raw_timings(),
            RC5Command(address=0, command=0).get_raw_timings(),
            RC6Command(address=0x04, command=0x0C).get_raw_timings(),
        ):
            assert TDC38Command.from_raw_timings(timings) is None

    def test_manchester_at_889us(self):
        rng = random.Random(206)
        for _ in range(50):
            bits = [1] + [rng.randrange(2) for _ in range(17)]
            assert TDC38Command.from_raw_timings(_manchester(bits, 889)) is None

    def test_a_23_cell_frame_on_a_320us_half_bit(self):
        """The 22-bit 320us Manchester family with a start cell: refused
        by the exact cell count, not by the windows."""
        rng = random.Random(56)
        for _ in range(50):
            bits = [1] + [rng.randrange(2) for _ in range(22)]
            assert TDC38Command.from_raw_timings(_manchester(bits, 320)) is None

    def test_tdc56_as_sent_is_refused(self):
        """The same frame on a 213us half-bit: its single half-bits fall
        below the 230us floor and its double ones in the dead zone."""
        timings = [int(v / HALF * 213) for v in _frame(6, 10, 22)]
        assert TDC38Command.from_raw_timings(timings) is None

    def test_a_stretched_tdc56_capture_reads_as_tdc38(self):
        """What the docstring admits: the windows cannot tell the two
        apart once a receiver stretches TDC-56 by 13 percent or more."""
        timings = [int(v / HALF * 213 * 1.15) for v in _frame(6, 10, 22)]
        assert TDC38Command.from_raw_timings(timings) is not None

    def test_a_timing_in_the_dead_zone(self):
        timings = _frame(6, 10, 22)
        index = next(i for i, v in enumerate(timings) if abs(v) > 450)
        timings[index] = 450 if timings[index] > 0 else -450
        assert TDC38Command.from_raw_timings(timings) is None


class TestTheLeadingMark:
    """The first mark of a frame is the start cell's single half-bit, and
    receivers stretch it. Bench, 2026-10-09: seven Broadlink-to-Athom
    captures arrived with it at 421 to 474us and did not decode."""

    @staticmethod
    def _bench() -> list[dict]:
        import json

        path = FIELD.parent / "air-path" / "tdc38-stretched-lead.json"
        return json.loads(path.read_text(encoding="utf-8"))["captures"]

    def test_the_bench_captures_decode_to_their_buttons(self):
        captures = self._bench()
        assert len(captures) == 7
        for capture in captures:
            raw = _raw(capture["received"])
            assert raw[0] > 420, "the fixture is the stretched case"
            identity = try_decode_identity(raw)
            expected = try_decode_identity(_raw(POSTED[capture["button"]]))
            assert identity is not None, capture["button"]
            assert identity.fingerprint == expected.fingerprint, capture["button"]
            assert identity.covers_capture is True, capture["button"]

    def test_a_held_press_stretched_on_every_frame(self):
        frame = _frame(6, 10, 22)
        frame[0] = 474
        identity = try_decode_identity(_join(frame, frame, frame))
        assert identity.fingerprint == POWER_FINGERPRINT
        assert (identity.frames_total, identity.frames_explained) == (3, 3)
        assert identity.covers_capture is True

    @pytest.mark.parametrize(("lead", "reads"), [
        (229, False), (230, True), (421, True), (600, True), (799, True),
        (800, False), (1200, False),
    ])
    def test_the_bound(self, lead, reads):
        frame = _frame(6, 10, 22)
        frame[0] = lead
        decoded = TDC38Command.from_raw_timings(frame)
        assert (decoded is not None) is reads

    def test_only_the_first_mark_is_widened(self):
        """Every other edge keeps its windows: a later single mark at
        474us still fails the frame."""
        frame = _frame(6, 10, 22)
        index = next(
            i for i, v in enumerate(frame) if i > 0 and 0 < v < 450
        )
        frame[index] = 474
        assert TDC38Command.from_raw_timings(frame) is None

    def test_a_cut_final_frame_may_start_stretched_too(self):
        frame = _frame(6, 10, 22)
        cut = _cut(frame, 10)
        cut[0] = 474
        identity = try_decode_identity(_join(frame, frame, cut))
        assert identity.covers_capture is True


# ---------------------------------------------------------------------------
# 2. The cut final frame: the four bounds, each both ways
# ---------------------------------------------------------------------------


class TestTheCutFinalFrame:
    POWER = staticmethod(lambda: _frame(6, 10, 22))

    # Bound 1: only the FINAL frame may be cut.
    def test_a_cut_final_frame_is_explained(self):
        power = self.POWER()
        identity = try_decode_identity(_join(power, power, _cut(power, 10)))
        assert identity.fingerprint == POWER_FINGERPRINT
        assert (identity.frames_total, identity.frames_explained) == (3, 3)
        assert identity.covers_capture is True

    def test_a_cut_leading_frame_is_not(self):
        power = self.POWER()
        identity = try_decode_identity(_join(_cut(power, 10), power, power))
        assert identity.fingerprint == POWER_FINGERPRINT
        assert identity.covers_capture is False

    def test_a_cut_middle_frame_is_not(self):
        power = self.POWER()
        identity = try_decode_identity(_join(power, _cut(power, 10), power))
        assert identity.covers_capture is False

    # Bound 2: the value comes from whole frames; a cut frame never votes.
    def test_a_lone_cut_frame_decodes_to_nothing(self):
        power = self.POWER()
        for cells in (6, 10, 16):
            assert try_decode_identity(_cut(power, cells)) is None
        assert try_decode_identity(_join(_cut(power, 12), _cut(power, 12))) is None

    def test_the_cut_frame_does_not_vote(self):
        power = self.POWER()
        identity = try_decode_identity(_join(power, _cut(power, 12)))
        decoded = TDC38Command.from_raw_timings(_join(power, _cut(power, 12)))
        assert decoded.repeat_count == 0  # one vote, from the whole frame
        assert identity.covers_capture is True

    # Bound 3: at least six cells, every one agreeing with the winner.
    def test_six_agreeing_cells_are_enough(self):
        power = self.POWER()
        assert try_decode_identity(_join(power, _cut(power, 6))).covers_capture is True

    def test_five_are_not(self):
        power = self.POWER()
        assert try_decode_identity(_join(power, _cut(power, 5))).covers_capture is False

    def test_a_cut_frame_that_disagrees_is_not_explained(self):
        power = self.POWER()
        other_device = _frame(7, 10, 22)
        identity = try_decode_identity(_join(power, _cut(other_device, 10)))
        assert identity.fingerprint == POWER_FINGERPRINT
        assert identity.covers_capture is False

    @pytest.mark.parametrize("cells", [13, 14, 15, 16, 17])
    def test_a_cut_back_frame_after_a_power_frame_is_not_explained(self, cells):
        """The realistic disagreement: same remote, another button. Power
        (F=22) and Back (F=58) part at the 13th cell, the second bit of F,
        so every cut that reaches it disagrees; 17 cells is no longer a
        cut at all."""
        power, back = self.POWER(), _frame(6, 10, 58)
        identity = try_decode_identity(_join(power, _cut(back, cells)))
        assert identity.fingerprint == POWER_FINGERPRINT
        assert identity.covers_capture is False

    def test_a_cut_that_stops_before_f_confirms_the_remote_only(self):
        """Up to the 12th cell Back reads the same as Power, so such a cut
        is explained: it confirms the remote, and the value still comes
        from the whole Power frame."""
        power, back = self.POWER(), _frame(6, 10, 58)
        identity = try_decode_identity(_join(power, _cut(back, 12)))
        assert identity.fingerprint == POWER_FINGERPRINT
        assert identity.covers_capture is True

    def test_a_cut_frame_ending_in_a_long_silence_is_not_a_cut(self):
        """The final timing is not read, but it is bounded: a frame that
        ends in 3ms of silence (still inside the 8ms frame gap) stopped,
        it was not cut."""
        power = self.POWER()
        cut = _cut(power, 10)[:-1]
        if cut[-1] < 0:
            cut[-1] = -3000
        else:
            cut.append(-3000)
        identity = try_decode_identity(_join(power, power, cut))
        assert identity.covers_capture is False

    def test_a_whole_length_final_frame_is_not_a_cut(self):
        """A final frame of full length that fails to decode is a broken
        frame, not a cut one, and is never forgiven."""
        power = self.POWER()
        broken = list(power)
        broken[-1] = 120 if broken[-1] > 0 else -120  # last edge mangled
        assert TDC38Command.from_raw_timings(broken) is None
        identity = try_decode_identity(_join(power, broken))
        assert identity.covers_capture is False

    def test_a_different_whole_final_frame_is_not_forgiven(self):
        identity = try_decode_identity(_join(self.POWER(), _frame(6, 10, 58)))
        assert identity.covers_capture is False

    # Bound 4: nothing outside tdc38.py changed. RC-5, whose decoder has
    # no such rule, still reads a cut tail as not covering.
    def test_other_protocols_keep_their_accounting(self):
        rc5 = RC5Command(address=5, command=0x35).get_raw_timings()
        cut = rc5[: len(rc5) // 2]
        identity = try_decode_identity([*rc5, -100000, *rc5, -100000, *cut])
        assert identity.protocol == "RC5"
        assert identity.covers_capture is False

    def test_a_broadlink_learn_shaped_capture(self):
        """Four frames of one held press, the last cut by the learn window,
        every timing quantized to the Broadlink's 32.8us tick."""
        tick = 1_000_000 / 32_768
        power = _raw(POSTED["PowerToggle"])
        frame = split_frames(power, 8000)[0]
        capture = _join(frame, frame, frame, _cut(frame, 11))
        quantized = [int(round(v / tick) * tick) for v in capture]
        identity = try_decode_identity(quantized)
        assert identity.fingerprint == POWER_FINGERPRINT
        assert (identity.frames_total, identity.frames_explained) == (4, 4)
        assert identity.covers_capture is True


# ---------------------------------------------------------------------------
# 3. Transmit
# ---------------------------------------------------------------------------


def test_a_decoded_row_rebuilds_to_its_own_identity():
    command = build_protocol_command("TDC38", 0xCA, 0x16)
    assert isinstance(command, TDC38Command)
    rebuilt = try_decode_identity(command.get_raw_timings())
    assert rebuilt.fingerprint == POWER_FINGERPRINT


class TestTheCarrierDecidesRebuildOrReplay:
    """A row stored at another carrier is replayed, not rebuilt at 38kHz."""

    @staticmethod
    def _pronto(carrier: int, half: int) -> str:
        from custom_components.hair.ir_command import raw_to_pronto

        timings = [int(v / HALF * half) for v in _frame(6, 10, 22)]
        return raw_to_pronto([*timings, -89000], frequency=carrier)

    def _row(self, carrier: int, half: int):
        from custom_components.hair.models import IRCommand

        code = self._pronto(carrier, half)
        identity = try_decode_identity(_raw(code))
        assert identity is not None and identity.covers_capture is True
        return IRCommand(
            name="Power", protocol="PRONTO", code=code,
            frequency=ProntoCommand(code).modulation,
            decoded_protocol=identity.protocol,
            decoded_address=identity.address,
            decoded_command=identity.command,
            decoded_fingerprint=identity.fingerprint,
            decode_covers=identity.covers_capture,
        )

    def test_the_rule(self):
        from custom_components.hair.protocol_decode import (
            carrier_allows_rebuild,
        )

        assert carrier_allows_rebuild("TDC38", 38000) is True
        assert carrier_allows_rebuild("TDC38", 38029) is True
        assert carrier_allows_rebuild("TDC38", None) is True
        assert carrier_allows_rebuild("TDC38", 36032) is False
        assert carrier_allows_rebuild("TDC38", 40000) is False
        assert carrier_allows_rebuild("TDC38", 0) is False
        # Nothing else declares a rebuild carrier, so nothing else moves.
        assert carrier_allows_rebuild("SONY12", 38000) is True
        assert carrier_allows_rebuild("RC5", 56000) is True
        assert carrier_allows_rebuild("UNKNOWN", 1) is True

    def test_a_38khz_row_is_rebuilt(self):
        from custom_components.hair.send_plan import build_like_send_path

        sent = build_like_send_path(self._row(38000, HALF))
        assert isinstance(sent, TDC38Command)

    @pytest.mark.parametrize("carrier", [36000, 40000])
    def test_a_row_at_another_carrier_is_replayed_as_captured(self, carrier):
        from custom_components.hair.send_plan import build_like_send_path

        row = self._row(carrier, 320)
        sent = build_like_send_path(row)
        assert not isinstance(sent, TDC38Command)
        assert sent.modulation == row.frequency  # the captured carrier

    def test_the_backfill_stamps_the_verdict_and_the_send_still_replays(self):
        """The upgrade path: a stored 36kHz command gains its identity and
        a covering verdict on load, and is still sent as captured."""
        from custom_components.hair.models import IRCommand, IRDevice
        from custom_components.hair.send_plan import would_send_decoded
        from custom_components.hair.storage import HAIRStore

        code = self._pronto(36000, 320)
        device = IRDevice(name="Box")
        device.commands.append(IRCommand(
            name="Power", protocol="PRONTO", code=code,
            frequency=ProntoCommand(code).modulation,
        ))
        store = HAIRStore.__new__(HAIRStore)
        store._data = {device.id: device}
        assert store._backfill_decoded_fields() is True
        command = device.commands[0]
        assert command.decoded_fingerprint == POWER_FINGERPRINT
        assert command.decode_covers is True
        assert would_send_decoded(command) is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("carrier", "rebuilt"), [(38000, True), (36000, False)])
    async def test_the_device_send_path(self, fake_hass, carrier, rebuilt):
        from custom_components.hair.models import IRDevice
        from custom_components.hair.tests.test_decoded_tx_consistency import (
            _cmd_stub,
            _infrared_mod,
            _make_device_manager,
        )

        manager = _make_device_manager(fake_hass)
        device = IRDevice(name="Box", emitter_entity_ids=["infrared.e"])
        command = self._row(carrier, HALF if carrier == 38000 else 320)
        device.add_command(command)
        manager._store.add_device(device)
        sentinel = _cmd_stub()
        with (
            patch.object(_infrared_mod, "async_send_command", AsyncMock()),
            patch(
                "custom_components.hair.ir_command.build_decoded_command",
                return_value=sentinel,
            ) as bdc,
            patch(
                "custom_components.hair.ir_command.build_command",
                return_value=sentinel,
            ) as bc,
        ):
            await manager.async_send_command(device.id, command.id)
        assert bdc.called is rebuilt
        assert bc.called is not rebuilt

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("carrier", "rebuilt"), [(38000, True), (36000, False)])
    async def test_the_catalog_test_path(self, fake_hass, carrier, rebuilt):
        from custom_components.hair.models import UnknownDevice, UnknownSignal
        from custom_components.hair.signal_monitor import SignalMonitor
        from custom_components.hair.tests.test_decoded_tx_consistency import (
            _cmd_stub,
            _infrared_mod,
            _make_hair_store,
            _make_signal_store,
        )

        row = self._row(carrier, HALF if carrier == 38000 else 320)
        signal = UnknownSignal(
            id="s1", fingerprint="s1", protocol="PRONTO", code=row.code,
            frequency=row.frequency,
            decoded_protocol=row.decoded_protocol,
            decoded_address=row.decoded_address,
            decoded_command=row.decoded_command,
            decoded_fingerprint=row.decoded_fingerprint,
            decode_covers=True,
        )
        store = _make_signal_store(fake_hass)
        monitor = SignalMonitor(fake_hass, store, _make_hair_store())
        store.add_device(UnknownDevice(id="ud1", fingerprint="d", signals=[signal]))
        sentinel = _cmd_stub()
        with (
            patch.object(_infrared_mod, "async_send_command", AsyncMock()),
            patch(
                "custom_components.hair.ir_command.build_decoded_command",
                return_value=sentinel,
            ) as bdc,
            patch(
                "custom_components.hair.ir_command.build_command",
                return_value=sentinel,
            ) as bc,
        ):
            result = await monitor.test_signal("s1", "infrared.e")
        assert result["success"] is True
        assert bdc.called is rebuilt
        assert bc.called is not rebuilt


def test_an_out_of_range_identity_does_not_rebuild():
    assert build_protocol_command("TDC38", 0x400, 0x16) is None
    assert build_protocol_command("TDC38", 0xCA, 0x80) is None


# ---------------------------------------------------------------------------
# 4. The Clipper paste that #206 reported
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_clipper_accepts_43_and_refuses_only_the_duplicate():
    from custom_components.hair.signal_monitor import SignalMonitor
    from custom_components.hair.signal_store import SignalStore

    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(
        side_effect=lambda func, *args: func(*args)
    )
    store = SignalStore(hass)
    store._loaded = True
    hair_store = MagicMock()
    hair_store.get_all_devices = MagicMock(return_value=[])
    hair_store.match_command = MagicMock(return_value=None)
    monitor = SignalMonitor(hass, store, hair_store)

    refused = []
    with patch.object(store, "async_save", AsyncMock()):
        device = await monitor.create_manual_remote("MR401")
        for name, code in POSTED.items():
            result = await monitor.create_manual_signal(device.id, code, name)
            if not result["success"]:
                assert result["code"] == "duplicate_signal"
                refused.append(name)
    assert refused == ["MenuMain"]
    assert len(device.signals) == 43


# ---------------------------------------------------------------------------
# 5. The first load after the upgrade
# ---------------------------------------------------------------------------


def _heard(code: str) -> tuple[str, str | None, str | None]:
    """What a press of this code carries: S/L, byte hash, decoded."""
    identity = try_decode_identity(_raw(code))
    return (
        canonical_fingerprint("PRONTO", code, None),
        canonical_byte_hash(code),
        identity.fingerprint if identity else None,
    )


class _FakeBacking:
    def __init__(self, *args, **kwargs):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


def test_the_premise_one_byte_hash_for_every_button_of_one_length():
    power, back = POSTED["PowerToggle"], POSTED["Back"]
    assert canonical_byte_hash(power) == canonical_byte_hash(back)
    assert canonical_fingerprint("PRONTO", power, None) == canonical_fingerprint(
        "PRONTO", back, None
    )


@pytest.mark.asyncio
async def test_a_trigger_made_under_the_shared_identity_narrows_to_its_button():
    from custom_components.hair.storage import HAIRStore

    power = POSTED["PowerToggle"]
    fingerprint, byte_hash, _ = _heard(power)
    backing = _FakeBacking()
    backing._data = {
        "devices": [],
        "triggers": [{
            "id": "t_power",
            "name": "MR401 power",
            "signal_fingerprint": fingerprint,
            "byte_hash": byte_hash,
            "protocol": "PRONTO",
            "code": power,
        }],
    }
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock(
        side_effect=lambda func, *args: func(*args)
    )
    with patch(
        "custom_components.hair.storage._HAIRDeviceStore",
        lambda *a, **k: backing,
    ):
        store = HAIRStore(hass)
        await store.async_load()

    trigger = store.get_trigger("t_power")
    assert trigger.decoded_fingerprint == POWER_FINGERPRINT

    # Before: with no decoded identity on either side, a Back press met
    # the trigger at the byte hash and fired it. That is still what
    # happens to a press that fails to decode at all: the residual this
    # decoder does not close, named here so it is not mistaken for fixed.
    back_fp, back_hash, back_decoded = _heard(POSTED["Back"])
    assert trigger.matches_signal(back_fp, back_hash, None) is True

    # After: the decoded tier decides, and a mismatch there is final.
    assert store.get_triggers_for_signal(
        None, None, back_fp, back_hash, back_decoded
    ) == []
    power_fp, power_hash, power_decoded = _heard(power)
    assert store.get_triggers_for_signal(
        None, None, power_fp, power_hash, power_decoded
    ) == [trigger]
    air_fp, air_hash, air_decoded = _heard(AIR_POWER)
    assert air_decoded == POWER_FINGERPRINT
    assert trigger in store.get_triggers_for_signal(
        None, None, air_fp, air_hash, air_decoded
    )


def test_a_sniffer_row_that_merged_several_buttons_keeps_its_own():
    from custom_components.hair.models import UnknownDevice, UnknownSignal
    from custom_components.hair.signal_store import _transform_loaded

    power = POSTED["PowerToggle"]
    fingerprint, byte_hash, _ = _heard(power)
    device = UnknownDevice(label="MR401")
    device.signals = [
        UnknownSignal(
            id="s1", protocol="PRONTO", code=power,
            fingerprint=fingerprint, byte_hash=byte_hash,
            alias="Power / Back", hit_count=7,
        )
    ]
    devices, _dismissed, dirty = _transform_loaded(
        {"devices": [device.to_dict()], "dismissed": []}
    )
    loaded = next(iter(devices.values()))
    row = loaded.signals[0]
    assert dirty is True
    assert row.decoded_fingerprint == POWER_FINGERPRINT
    assert row.decode_covers is True
    assert (row.alias, row.hit_count) == ("Power / Back", 7)

    back = _heard(POSTED["Back"])
    assert loaded.get_signal(*back) is None, "Back now gets its own row"
    assert loaded.get_signal(*_heard(power)) is row


def test_a_device_command_gains_its_identity_on_load():
    from custom_components.hair.models import IRCommand, IRDevice
    from custom_components.hair.storage import HAIRStore

    device = IRDevice(name="Media Receiver")
    device.commands.append(
        IRCommand(name="Back", protocol="PRONTO", code=POSTED["Back"])
    )
    store = HAIRStore.__new__(HAIRStore)
    store._data = {device.id: device}
    assert store._backfill_decoded_fields() is True
    command = device.commands[0]
    assert command.decoded_fingerprint == "TDC38:0x00ca:0x3a"
    assert command.decode_covers is True
    assert store._backfill_decoded_fields() is False
