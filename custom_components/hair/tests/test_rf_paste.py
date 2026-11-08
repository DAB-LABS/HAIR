"""RF send round, T3: reading a pasted radio code and editing with it.

The editor's radio code box takes a Flipper ``.sub``, a list of signed
timings, or Broadlink RF base64 (``rf_paste``). What a paste becomes is
what a capture would: one frame with its gap, its identity read back off
that frame by the function every later recomputation uses, and the
frequency with where it came from. The real RM4 Pro capture of a
DEWENWILS IT104 keyfob button (BroadSniff's fixture, an 0xB1 packet) is
the anchor.
"""
from __future__ import annotations

import base64
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair import rf_paste
from custom_components.hair.const import MEDIUM_RF, RF_PROTOCOL
from custom_components.hair.identity import canonical_fingerprint
from custom_components.hair.models import IRCommand, IRDevice, UnknownDevice, UnknownSignal
from custom_components.hair.tests.test_device_manager import manager  # noqa: F401
from custom_components.hair.tests.test_websocket_api import _make_signal_monitor

FIXTURE = Path(__file__).parent / "fixtures" / "rf_paste_it104_button_1_b1.hex"
IT104 = bytes.fromhex(FIXTURE.read_text().strip())
IT104_B64 = base64.b64encode(IT104).decode()

# An EV1527-shaped frame: sync mark, 24 bits of short-long pulses, and
# the gap. Two different "buttons" differ in their last bits.
SHORT, LONG, GAP = 350, 1050, 10850


def _frame(bits: str) -> list[int]:
    out: list[int] = []
    for bit in bits:
        out += [LONG, -SHORT] if bit == "1" else [SHORT, -LONG]
    return [*out, SHORT, -GAP]


PRONTO = "0000 006D 0002 0000 0010 0010 0010 0010"

BUTTON_A = "101100111000111100001010"
BUTTON_B = "101100111000111100000101"


def _broadlink(type_byte: int, timings: list[int]) -> bytes:
    """A Broadlink packet: type, repeat, length, ticks (0x00 escapes)."""
    tick = 1_000_000 / 32_768
    body = bytearray()
    for value in timings:
        ticks = round(abs(value) / tick)
        body += bytes([ticks]) if ticks < 256 else bytes([0, ticks >> 8, ticks & 0xFF])
    return bytes([type_byte, 0]) + len(body).to_bytes(2, "little") + bytes(body)


IR_PACKET_B64 = base64.b64encode(_broadlink(0x26, [9000, -4500, 560, -560])).decode()
DECODED_SUB = (
    "Filetype: Flipper SubGhz Key File\nFrequency: 433920000\n"
    "Protocol: Princeton\nKey: 00 00 00 00 00 12 34 56"
)


class TestTheRealCapture:
    def test_an_rm4_pro_capture_reads_with_its_own_carrier(self):
        result = rf_paste.validate(IT104_B64)
        assert result["ok"] is True
        assert result["format"] == "broadlink"
        assert (result["frames_found"], result["frames_agreeing"]) == (8, 8)
        assert (result["frequency_hz"], result["frequency_source"]) == (433_920_000, "signal")
        assert (result["gap_us"], result["gap_source"]) == (12_909, "measured")
        # One frame, its gap last, as a stored radio row holds it.
        assert result["frame"][0] > 0 and result["frame"][-1] == -12_909

    def test_the_identity_is_the_one_every_recomputation_gives(self):
        result = rf_paste.validate(IT104_B64)
        assert canonical_fingerprint(RF_PROTOCOL, None, result["frame"]) == result["fingerprint"]

    def test_a_sub_written_from_it_reads_back_the_same(self):
        first = rf_paste.validate(IT104_B64)
        again = rf_paste.validate(first["sub_text"])
        for key in ("frame", "fingerprint", "frame_hash", "frequency_hz", "gap_us"):
            assert again[key] == first[key], key
        assert (again["format"], again["gap_source"]) == ("sub", "measured")

    def test_bare_timings_read_the_same_code_and_ask_for_a_frequency(self):
        first = rf_paste.validate(IT104_B64)
        bare = rf_paste.validate(" ".join(str(v) for v in first["frame"]))
        assert bare["fingerprint"] == first["fingerprint"]
        assert (bare["frequency_hz"], bare["frequency_source"]) == (None, None)
        given = rf_paste.validate(" ".join(str(v) for v in first["frame"]), 433_920_000)
        assert (given["frequency_hz"], given["frequency_source"]) == (433_920_000, "user")


class TestTheFormats:
    def test_a_burst_votes(self):
        burst = _frame(BUTTON_A) * 5
        result = rf_paste.validate(" ".join(map(str, burst)))
        assert (result["frames_found"], result["frames_agreeing"]) >= (4, 4)
        assert result["gap_source"] == "measured"

    def test_commas_brackets_and_an_esphome_line(self):
        text = "[" + ", ".join(map(str, _frame(BUTTON_A) * 3)) + "]"
        assert rf_paste.validate(text)["ok"] is True

    def test_a_capture_that_started_on_a_space_or_mid_pulse(self):
        clean = rf_paste.validate(" ".join(map(str, _frame(BUTTON_A) * 4)))
        leading_space = rf_paste.validate(" ".join(map(str, [-5000, *_frame(BUTTON_A) * 4])))
        assert leading_space["fingerprint"] == clean["fingerprint"]
        # Unsigned and one slot late: every gap lands on a "mark".
        unsigned = [abs(v) for v in [700, *_frame(BUTTON_A) * 4]]
        shifted = rf_paste.validate(" ".join(map(str, unsigned)))
        assert shifted["fingerprint"] == clean["fingerprint"]

    def test_a_sub_split_across_lines_and_its_frequency(self):
        frame = _frame(BUTTON_A) * 3
        text = "\n".join([
            "Filetype: Flipper SubGhz RAW File", "Version: 1",
            "Frequency: 315000000", "Preset: FuriHalSubGhzPresetOok650Async",
            "Protocol: RAW",
            "RAW_Data: " + " ".join(map(str, frame[:31])),
            "RAW_Data: " + " ".join(map(str, frame[31:])),
        ])
        result = rf_paste.validate(text)
        assert (result["frequency_hz"], result["frequency_source"]) == (315_000_000, "signal")

    @pytest.mark.parametrize(("type_byte", "hz"), [(0xB2, 433_920_000), (0xD7, 315_000_000)])
    def test_broadlink_sends_assume_their_band(self, type_byte, hz):
        packet = _broadlink(type_byte, _frame(BUTTON_A) * 3)
        result = rf_paste.validate(base64.b64encode(packet).decode())
        assert (result["frequency_hz"], result["frequency_source"]) == (hz, "assumed")

    @pytest.mark.parametrize(("text", "code"), [
        ("", "rf_paste_empty"),
        ("   \n ", "rf_paste_empty"),
        ("not a code at all!", "rf_paste_unreadable"),
        (IR_PACKET_B64, "rf_paste_unreadable"),
        (DECODED_SUB, "rf_paste_unreadable"),
        ("350 -1050 350 -1050", "rf_paste_no_frame"),
    ])
    def test_refusals(self, text, code):
        result = rf_paste.validate(text)
        assert (result["ok"], result["code"]) == (False, code)

    def test_frames_that_do_not_agree(self):
        burst = _frame(BUTTON_A) + _frame(BUTTON_B) + _frame("000000000000111111111111")
        result = rf_paste.validate(" ".join(map(str, burst)))
        assert (result["ok"], result["code"]) == (False, "rf_paste_frames_disagree")

    def test_a_long_frame_writes_several_raw_data_lines(self):
        # A frame ending on a mark gets its gap; one ending on a space
        # keeps the space it has.
        text = rf_paste.to_sub([*[500, -500] * 400, 500], 433_920_000, 9000)
        lines = [line for line in text.splitlines() if line.startswith("RAW_Data:")]
        assert len(lines) == 2
        assert lines[-1].endswith("-9000")
        assert "Frequency: 433920000" in text
        ends_on_space = rf_paste.to_sub([500, -500, 500, -7000], 433_920_000, 9000)
        assert ends_on_space.rstrip().endswith("-7000")


class TestWritingARow:
    def test_apply_replaces_identity_and_keeps_the_knobs(self):
        row = UnknownSignal(
            id="s1", fingerprint="old", protocol="PRONTO", code="x", raw_timings=[1]
        )
        row.send_count = 7
        row.alias = "Gate"
        result = rf_paste.validate(IT104_B64)
        rf_paste.apply_code(row, result)
        assert (row.medium, row.protocol, row.code) == (MEDIUM_RF, RF_PROTOCOL, None)
        assert row.raw_timings == result["frame"]
        assert (row.fingerprint, row.byte_hash) == (result["fingerprint"], result["frame_hash"])
        assert (row.rf_frequency_hz, row.rf_frequency_source) == (433_920_000, "signal")
        assert (row.rf_frame_gap_us, row.rf_frame_gap_source) == (12_909, "measured")
        assert (row.send_count, row.alias) == (7, "Gate")
        assert row.decoded_fingerprint is None

    def test_the_frequency_alone_is_the_users(self):
        row = types.SimpleNamespace(rf_frequency_hz=None, rf_frequency_source=None)
        rf_paste.set_frequency(row, 303_875_000)
        assert (row.rf_frequency_hz, row.rf_frequency_source) == (303_875_000, "user")


def _rf_row(signal_id, bits, **extra):
    result = rf_paste.validate(" ".join(map(str, _frame(bits) * 3)), 433_920_000)
    row = UnknownSignal(id=signal_id, fingerprint="x", raw_timings=[], **extra)
    rf_paste.apply_code(row, result)
    return row


class TestTheSnifferEdit:
    def _monitor(self, fake_hass, rows):
        monitor = _make_signal_monitor(fake_hass)
        monitor._signal_store.add_device(UnknownDevice(id="r1", fingerprint="fp", signals=rows))
        monitor._signal_store.async_save = AsyncMock()
        monitor._trigger_manager = MagicMock()
        monitor._trigger_manager.rewire = AsyncMock(
            return_value={"rewired": ["t1"], "skipped": []}
        )
        return monitor

    @pytest.mark.asyncio
    async def test_a_paste_replaces_the_code_and_rewires(self, fake_hass):
        monitor = self._monitor(fake_hass, [_rf_row("s1", BUTTON_A)])
        result = await monitor.edit_signal_rf("r1", "s1", rf_code=IT104_B64)
        assert result["success"] is True
        assert result["signal"]["rf_frequency_hz"] == 433_920_000
        assert result["triggers"] == {"rewired": ["t1"], "skipped": []}
        monitor._signal_store.async_save.assert_awaited()

    @pytest.mark.asyncio
    async def test_a_code_another_row_holds_is_refused(self, fake_hass):
        monitor = self._monitor(fake_hass, [_rf_row("s1", BUTTON_A), _rf_row("s2", BUTTON_B)])
        text = " ".join(map(str, _frame(BUTTON_B) * 3))
        result = await monitor.edit_signal_rf("r1", "s1", rf_code=text)
        assert (result["success"], result["code"]) == (False, "duplicate_signal")

    @pytest.mark.asyncio
    async def test_the_frequency_alone(self, fake_hass):
        monitor = self._monitor(fake_hass, [_rf_row("s1", BUTTON_A)])
        result = await monitor.edit_signal_rf("r1", "s1", rf_frequency_hz=433_420_000)
        assert result["signal"]["rf_frequency_hz"] == 433_420_000
        monitor._trigger_manager.rewire.assert_not_called()

    @pytest.mark.asyncio
    async def test_each_kind_takes_its_own_code(self, fake_hass):
        ir = UnknownSignal(id="s9", fingerprint="ir", protocol="PRONTO", code=PRONTO)
        monitor = self._monitor(fake_hass, [ir, _rf_row("s1", BUTTON_A)])
        result = await monitor.edit_signal_rf("r1", "s9", rf_code=IT104_B64)
        assert result["code"] == "wrong_medium_code"
        result = await monitor.edit_signal_pronto("r1", "s1", PRONTO)
        assert result["code"] == "wrong_medium_code"

    @pytest.mark.asyncio
    async def test_a_new_code_is_filed_under_its_new_identity(self, fake_hass):
        """Send review N9: the sticky-filing index follows the edit, so
        the next press of the new code files on this row."""
        from custom_components.hair.signal_store import _identity_keys

        monitor = self._monitor(fake_hass, [_rf_row("s1", BUTTON_A)])
        store = monitor._signal_store
        store.rebuild_signal_index()
        row = store.get_device("r1").signals[0]
        old_keys = set(_identity_keys(row.decoded_fingerprint, row.byte_hash, row.fingerprint))
        assert old_keys and old_keys <= set(store._sig_index)
        text = " ".join(map(str, _frame(BUTTON_B) * 3))
        await monitor.edit_signal_rf("r1", "s1", rf_code=text)
        new_keys = set(_identity_keys(row.decoded_fingerprint, row.byte_hash, row.fingerprint))
        assert new_keys and not new_keys & old_keys
        assert not old_keys & set(store._sig_index)
        for key in new_keys:
            assert [held.id for _dev, held in store._sig_index[key]] == ["s1"]

    @pytest.mark.asyncio
    async def test_a_bad_paste_says_why(self, fake_hass):
        monitor = self._monitor(fake_hass, [_rf_row("s1", BUTTON_A)])
        result = await monitor.edit_signal_rf("r1", "s1", rf_code="350 -1050")
        assert result["code"] == "rf_paste_no_frame"


class TestTheCommandEdit:
    def _device(self, manager):  # noqa: F811
        manager._entity_factory.async_update_entities = AsyncMock()
        result = rf_paste.validate(" ".join(map(str, _frame(BUTTON_A) * 3)), 433_920_000)
        cmd = IRCommand(id="c1", name="On", raw_timings=[])
        rf_paste.apply_code(cmd, result)
        ir = IRCommand(id="c2", name="Power", protocol="PRONTO",
                       code="0000 006D 0002 0000 0010 0010 0010 0010")
        device = IRDevice(name="Plug", commands=[cmd, ir])
        manager._store.add_device(device)
        return device

    @pytest.mark.asyncio
    async def test_a_radio_command_takes_a_paste(self, manager):  # noqa: F811
        device = self._device(manager)
        result = await manager.async_update_command(device.id, "c1", rf_code=IT104_B64)
        assert result["success"] is True
        cmd = manager._store.get_device(device.id).get_command("c1")
        assert cmd.rf_frame_gap_us == 12_909
        fp = canonical_fingerprint(RF_PROTOCOL, None, cmd.raw_timings)
        assert manager._store.match_command(None, fp, cmd.byte_hash) == (device.id, "c1")

    @pytest.mark.asyncio
    async def test_and_its_frequency_alone(self, manager):  # noqa: F811
        device = self._device(manager)
        result = await manager.async_update_command(device.id, "c1", rf_frequency_hz=315_000_000)
        assert result["success"] is True
        cmd = manager._store.get_device(device.id).get_command("c1")
        assert (cmd.rf_frequency_hz, cmd.rf_frequency_source) == (315_000_000, "user")

    @pytest.mark.asyncio
    async def test_each_kind_refuses_the_others_code(self, manager):  # noqa: F811
        device = self._device(manager)
        result = await manager.async_update_command(
            device.id, "c1", pronto="0000 006D 0002 0000 0040 0040 0040 0040"
        )
        assert result["code"] == "wrong_medium_code"
        result = await manager.async_update_command(device.id, "c2", rf_code=IT104_B64)
        assert result["code"] == "wrong_medium_code"
        result = await manager.async_update_command(device.id, "c2", rf_frequency_hz=433_920_000)
        assert result["code"] == "wrong_medium_code"


class TestTheValidateDoor:
    def test_it_answers_a_refusal_as_a_result(self):
        from custom_components.hair.websocket_api import ws_rf_validate

        conn = MagicMock()
        ws_rf_validate(MagicMock(), conn, {"id": 1, "text": "350 -1050"})
        assert conn.send_result.call_args.args[1]["code"] == "rf_paste_no_frame"
        ws_rf_validate(
            MagicMock(), conn, {"id": 2, "text": IT104_B64, "frequency_hz": 433_840_000}
        )
        answer = conn.send_result.call_args.args[1]
        assert (answer["ok"], answer["frequency_hz"], answer["frequency_source"]) == (
            True, 433_840_000, "user",
        )


class TestSendReviewPasteEdges:
    """Send review F3 to F6 and test gap 6 (2026-11-07): the paste edge
    cases the receive path already handles, or that no remote sends."""

    NOISE = ([50, -200], [120, -900, 80, -700])

    @pytest.mark.parametrize("frames", [3, 4])
    @pytest.mark.parametrize("noise", NOISE)
    def test_leading_noise_keeps_the_remotes_identity(self, frames, noise):
        """Noise sticks to the first frame; the rest still vote, with the
        paste's last frame counted by the gap it ended on."""
        clean = rf_paste.validate(" ".join(map(str, _frame(BUTTON_A) * frames)))
        noisy = rf_paste.validate(" ".join(map(str, noise + _frame(BUTTON_A) * frames)))
        assert clean["ok"] and noisy["ok"], noisy
        assert noisy["fingerprint"] == clean["fingerprint"]
        assert noisy["frame_hash"] == clean["frame_hash"]
        assert noisy["frames_agreeing"] >= 2

    @pytest.mark.parametrize("noise", NOISE)
    def test_one_clean_frame_behind_noise_is_refused_not_misread(self, noise):
        """Two frames, the first carrying the noise: one clean frame is
        too few to vote, and the longest piece is the noisy one."""
        noisy = rf_paste.validate(" ".join(map(str, noise + _frame(BUTTON_A) * 2)))
        assert (noisy["ok"], noisy["code"]) == (False, rf_paste.PASTE_FRAMES_DISAGREE)

    def test_clean_short_pastes_are_unchanged(self):
        for frames in (1, 2, 3):
            result = rf_paste.validate(" ".join(map(str, _frame(BUTTON_A) * frames)))
            assert result["ok"], (frames, result)

    def test_core_s_315_mhz_send_byte_reads_as_315(self):
        packet = _broadlink(0xB4, _frame(BUTTON_A) * 3)
        read = rf_paste.broadlink_rf_packet(packet)
        assert read.frequency_hz == 315_000_000
        assert read.frequency_source == rf_paste.SOURCE_ASSUMED
        other = rf_paste.broadlink_rf_packet(_broadlink(0xB2, _frame(BUTTON_A) * 3))
        assert other.frequency_hz == 433_920_000
        d7 = rf_paste.broadlink_rf_packet(_broadlink(0xD7, _frame(BUTTON_A) * 3))
        assert d7.frequency_hz == 315_000_000

    @pytest.mark.parametrize("value", ["-5", "0", "999999", "10000000001"])
    def test_a_sub_frequency_outside_1_mhz_to_10_ghz_is_no_frequency(self, value):
        raw = " ".join(map(str, _frame(BUTTON_A) * 3))
        sub = (
            "Filetype: Flipper SubGhz RAW File\nVersion: 1\n"
            f"Frequency: {value}\nProtocol: RAW\nRAW_Data: {raw}\n"
        )
        result = rf_paste.validate(sub)
        assert result["ok"]
        assert (result["frequency_hz"], result["frequency_source"]) == (None, None)

    def test_a_recorded_carrier_outside_the_range_falls_to_the_type(self):
        body = _broadlink(0xB1, _frame(BUTTON_A) * 3)
        # 0xB1 records its carrier in kHz at offsets 4 to 7, timings after.
        packet = body[:4] + (99_999_999).to_bytes(4, "little") + body[4:]
        packet = packet[:2] + (len(packet) - 4).to_bytes(2, "little") + packet[4:]
        read = rf_paste.broadlink_rf_packet(packet)
        assert read.frequency_hz == 433_920_000
        assert read.frequency_source == rf_paste.SOURCE_ASSUMED

    @pytest.mark.parametrize("value", ["100000000000000000000", "1000000"])
    def test_a_second_long_mark_or_space_is_refused(self, value):
        frame = " ".join(map(str, _frame(BUTTON_A) * 2))
        result = rf_paste.validate(f"{frame} 350 -{value}")
        assert (result["ok"], result["code"]) == (False, rf_paste.PASTE_UNREADABLE)

    def test_a_long_gap_under_a_second_is_kept(self):
        frame = _frame(BUTTON_A)[:-1]
        result = rf_paste.validate(" ".join(map(str, [*frame, -999_000, *frame, -999_000])))
        assert result["ok"], result
