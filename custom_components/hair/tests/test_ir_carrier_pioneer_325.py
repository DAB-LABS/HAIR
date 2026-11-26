"""A pasted IR code the rebuild would not reproduce is sent as written (GH #325).

Pioneer is NEC's frame layout at 40kHz, so a Pioneer Pronto decodes as
NEC. Before this fix a pasted or edited one was saved as rebuildable and
went out as a 38kHz NEC frame with a ditto, which the receiver in the
report ignored. Imports were already protected by the reproduce check in
``wig_adapters``; the paste and edit doors had none.

Two parts. ``carrier_allows_rebuild`` knows NEC is rebuilt at 38kHz, so
an NEC-shaped row stored at 40kHz is replayed at every send site. And
the doors that take a code from the user ask ``rebuild_reproduces`` and
save the row with ``tx_force_raw`` set when the answer is no, so the
panel shows it as sent as written.

The Pioneer frame is written here from the protocol's timings (leader
8480/4240, unit 530, a one at three units, NEC's address, inverse,
command, inverse layout), not taken from any person's capture.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.hair.ir_command import ProntoCommand, raw_to_pronto
from custom_components.hair.models import IRCommand, IRDevice
from custom_components.hair.protocol_decode import (
    carrier_allows_rebuild,
    rebuild_reproduces,
    try_decode_identity,
)
from custom_components.hair.send_plan import (
    build_like_send_path,
    would_send_decoded,
)

PIONEER_UNIT_US = 530
PIONEER_LEADER_US = (8480, 4240)
PIONEER_PERIOD_US = 106_000
NEC_UNIT_US = 562
NEC_LEADER_US = (9000, 4500)
NEC_PERIOD_US = 108_000


def _frame(
    data: tuple[int, int, int, int],
    *,
    unit: int,
    leader: tuple[int, int],
    period: int,
) -> list[int]:
    """One NEC-layout frame, bytes sent LSB first, padded to ``period``."""
    timings = [leader[0], -leader[1]]
    for byte in data:
        for bit in range(8):
            one = (byte >> bit) & 1
            timings += [unit, -(3 * unit if one else unit)]
    timings.append(unit)
    timings.append(-(period - sum(abs(t) for t in timings)))
    return timings


def _pioneer_pronto(carrier: int = 40_000) -> str:
    """Pioneer A5 12 (``A5 5A 12 ED``), one frame, as a Pronto."""
    frame = _frame(
        (0xA5, 0x5A, 0x12, 0xED),
        unit=PIONEER_UNIT_US, leader=PIONEER_LEADER_US,
        period=PIONEER_PERIOD_US,
    )
    return raw_to_pronto(frame, frequency=carrier)


def _nec_pronto(data=(0x04, 0xFB, 0x08, 0xF7), carrier: int = 38_000) -> str:
    frame = _frame(
        data, unit=NEC_UNIT_US, leader=NEC_LEADER_US, period=NEC_PERIOD_US,
    )
    return raw_to_pronto(frame, frequency=carrier)


def _identity(pronto: str):
    return try_decode_identity(ProntoCommand(pronto).get_raw_timings())


def _carrier(pronto: str) -> int:
    return ProntoCommand(pronto).modulation


def _pioneer_rows_at(carrier: int) -> str:
    pronto = _pioneer_pronto(carrier)
    assert _identity(pronto).protocol == "NEC"  # Pioneer reads as NEC
    return pronto


# ---------------------------------------------------------------------------
# The rule
# ---------------------------------------------------------------------------


class TestTheCarrierRule:
    def test_nec_is_rebuilt_only_near_38khz(self):
        assert carrier_allows_rebuild("NEC", 38_000) is True
        assert carrier_allows_rebuild("NEC", 38_029) is True  # Pronto 006D
        assert carrier_allows_rebuild("NEC", 37_000) is True
        assert carrier_allows_rebuild("NEC", 39_000) is True
        assert carrier_allows_rebuild("NEC", None) is True
        assert carrier_allows_rebuild("NEC", 39_860) is False  # Pronto 0068
        assert carrier_allows_rebuild("NEC", 36_000) is False
        assert carrier_allows_rebuild("NEC", 0) is False

    def test_tdc38_and_the_rest_are_unchanged(self):
        assert carrier_allows_rebuild("TDC38", 38_029) is True
        assert carrier_allows_rebuild("TDC38", 40_000) is False
        assert carrier_allows_rebuild("SONY12", 40_000) is True
        assert carrier_allows_rebuild("RC5", 36_000) is True
        assert carrier_allows_rebuild("UNKNOWN", 1) is True

    def test_the_pronto_carrier_words(self):
        assert _carrier(_pioneer_pronto(40_000)) == pytest.approx(39_860, abs=10)
        assert _carrier(_pioneer_pronto(38_000)) == pytest.approx(38_029, abs=10)


class TestRebuildReproduces:
    def test_a_40khz_pioneer_paste_does_not(self):
        pronto = _pioneer_rows_at(40_000)
        assert rebuild_reproduces(_identity(pronto), _carrier(pronto)) is False

    def test_the_same_frame_at_38khz_does(self):
        pronto = _pioneer_rows_at(38_000)
        assert rebuild_reproduces(_identity(pronto), _carrier(pronto)) is True

    def test_a_clean_nec_code_does(self):
        pronto = _nec_pronto()
        assert rebuild_reproduces(_identity(pronto), _carrier(pronto)) is True

    def test_nothing_decoded_is_nothing_to_judge(self):
        assert rebuild_reproduces(None, 40_000) is True

    def test_an_nec_frame_the_rebuild_cannot_say_does_not(self):
        """``04 00 08 F7`` is an extended address the rebuild reads as
        ``04``, and sends back as ``04 FB``: another code. A paste of it
        is sent as written; stored rows are not touched."""
        pronto = _nec_pronto((0x04, 0x00, 0x08, 0xF7))
        identity = _identity(pronto)
        assert identity is not None and identity.protocol == "NEC"
        assert rebuild_reproduces(identity, _carrier(pronto)) is False


# ---------------------------------------------------------------------------
# What a stored row sends
# ---------------------------------------------------------------------------


def _row(pronto: str, **knobs) -> IRCommand:
    identity = _identity(pronto)
    return IRCommand(
        name="Power", protocol="PRONTO", code=pronto,
        frequency=_carrier(pronto),
        decoded_protocol=identity.protocol,
        decoded_address=identity.address,
        decoded_command=identity.command,
        decoded_fingerprint=identity.fingerprint,
        decode_covers=identity.covers_capture,
        **knobs,
    )


class TestWhatGoesOut:
    def test_a_40khz_nec_shaped_row_is_replayed_as_written(self):
        """Even without the flag: the carrier rule alone keeps it raw,
        so a row saved before this fix sends its own bytes too."""
        pronto = _pioneer_pronto(40_000)
        row = _row(pronto, repeat_count=1)
        assert would_send_decoded(row) is False
        sent = build_like_send_path(row)
        assert sent.modulation == pytest.approx(39_860, abs=10)
        assert list(sent.get_raw_timings()) == list(
            ProntoCommand(pronto).get_raw_timings()
        )

    def test_the_same_frame_at_38khz_rebuilds_as_nec(self):
        row = _row(_pioneer_pronto(38_000), repeat_count=1)
        assert would_send_decoded(row) is True
        sent = build_like_send_path(row)
        assert type(sent).__name__ == "NECCommand"

    def test_a_receiver_capture_of_nec_at_38khz_rebuilds_as_today(self):
        """Receivers report no carrier, so a capture is stored at the
        default 38kHz and decodes as NEC: rebuilt, dittos and all."""
        from custom_components.hair.const import DEFAULT_CARRIER_FREQUENCY

        timings = _frame(
            (0x04, 0xFB, 0x08, 0xF7),
            unit=NEC_UNIT_US, leader=NEC_LEADER_US, period=NEC_PERIOD_US,
        )
        identity = try_decode_identity(timings)
        row = IRCommand(
            name="Power", protocol="RAW", raw_timings=timings,
            frequency=DEFAULT_CARRIER_FREQUENCY, repeat_count=2,
            decoded_protocol=identity.protocol,
            decoded_address=identity.address,
            decoded_command=identity.command,
            decoded_fingerprint=identity.fingerprint,
            decode_covers=identity.covers_capture,
        )
        assert would_send_decoded(row) is True
        sent = build_like_send_path(row)
        assert type(sent).__name__ == "NECCommand"
        assert sent.repeat_count == 2

    def test_turning_the_flag_off_on_a_40khz_row_still_replays(self):
        """The plan's 'flipping it rebuilds' cannot hold at 40kHz: the
        carrier rule replays the row either way. At 38kHz it does."""
        assert would_send_decoded(
            _row(_pioneer_pronto(40_000), tx_force_raw=False)
        ) is False
        assert would_send_decoded(
            _row(_pioneer_pronto(38_000), tx_force_raw=False)
        ) is True


# ---------------------------------------------------------------------------
# The doors
# ---------------------------------------------------------------------------


def _device_with(manager) -> tuple[IRDevice, IRCommand]:
    """A device holding one 38kHz NEC command to edit."""
    row = _row(_nec_pronto())
    device = IRDevice(name="Receiver", emitter_entity_ids=["infrared.e"])
    device.add_command(row)
    manager._store.add_device(device)
    return device, row


class TestTheCommandEditor:
    @staticmethod
    def _manager(fake_hass):
        from custom_components.hair.tests.test_decoded_tx_consistency import (
            _make_device_manager,
        )

        return _make_device_manager(fake_hass)

    @pytest.mark.asyncio
    async def test_a_40khz_paste_saves_raw_and_sends_its_own_bytes(self, fake_hass):
        manager = self._manager(fake_hass)
        device, row = _device_with(manager)
        pronto = _pioneer_pronto(40_000)
        res = await manager.async_update_command(device.id, row.id, pronto=pronto)
        assert res["success"]
        assert row.decoded_protocol == "NEC"
        assert row.tx_force_raw is True
        sent = build_like_send_path(row)
        assert sent.modulation == pytest.approx(39_860, abs=10)
        assert list(sent.get_raw_timings()) == list(
            ProntoCommand(pronto).get_raw_timings()
        )

    @pytest.mark.asyncio
    async def test_the_same_frame_at_38khz_saves_without_the_flag(self, fake_hass):
        manager = self._manager(fake_hass)
        device, row = _device_with(manager)
        res = await manager.async_update_command(
            device.id, row.id, pronto=_pioneer_pronto(38_000)
        )
        assert res["success"]
        assert row.tx_force_raw is False
        assert would_send_decoded(row) is True

    @pytest.mark.asyncio
    async def test_a_rename_keeps_the_users_choice(self, fake_hass):
        """The editor sends the code with every save. A rename of a
        40kHz row the user turned back to rebuild is left that way."""
        manager = self._manager(fake_hass)
        device, row = _device_with(manager)
        pronto = _pioneer_pronto(40_000)
        await manager.async_update_command(device.id, row.id, pronto=pronto)
        assert row.tx_force_raw is True
        await manager.async_set_command_tx_force_raw(device.id, row.id, False)
        assert row.tx_force_raw is False
        res = await manager.async_update_command(
            device.id, row.id, name="Power On", pronto=pronto
        )
        assert res["success"]
        assert row.name == "Power On"
        assert row.tx_force_raw is False

    @pytest.mark.asyncio
    async def test_a_38khz_nec_code_saves_as_today(self, fake_hass):
        manager = self._manager(fake_hass)
        device, row = _device_with(manager)
        res = await manager.async_update_command(
            device.id, row.id, pronto=_nec_pronto((0x04, 0xFB, 0x09, 0xF6))
        )
        assert res["success"]
        assert row.tx_force_raw is False
        assert would_send_decoded(row) is True


class TestTheClipperDoors:
    @staticmethod
    def _monitor():
        from custom_components.hair.signal_monitor import SignalMonitor
        from custom_components.hair.tests.test_signal_monitor import (
            _make_hair_store,
            _make_hass,
            _make_signal_store,
        )

        hass = _make_hass()
        store = _make_signal_store(hass)
        return SignalMonitor(hass, store, _make_hair_store()), store

    @pytest.mark.asyncio
    async def test_a_40khz_paste_saves_raw(self):
        monitor, store = self._monitor()
        with patch.object(store, "async_save", AsyncMock()):
            device = await monitor.create_manual_remote("Receiver")
            res = await monitor.create_manual_signal(
                device.id, _pioneer_pronto(40_000), tx_force_raw=False
            )
        assert res["success"]
        signal = device.signals[0]
        assert signal.decoded_protocol == "NEC"
        assert signal.tx_force_raw is True

    @pytest.mark.asyncio
    async def test_a_38khz_paste_saves_as_today(self):
        monitor, store = self._monitor()
        with patch.object(store, "async_save", AsyncMock()):
            device = await monitor.create_manual_remote("Receiver")
            res = await monitor.create_manual_signal(
                device.id, _pioneer_pronto(38_000)
            )
        assert res["success"]
        assert device.signals[0].tx_force_raw is False

    @pytest.mark.asyncio
    async def test_an_edit_to_40khz_saves_raw_and_a_resave_keeps_the_choice(self):
        monitor, store = self._monitor()
        with patch.object(store, "async_save", AsyncMock()):
            device = await monitor.create_manual_remote("Receiver")
            await monitor.create_manual_signal(device.id, _nec_pronto())
            signal = device.signals[0]
            assert signal.tx_force_raw is False
            pronto = _pioneer_pronto(40_000)
            res = await monitor.edit_signal_pronto(device.id, signal.id, pronto)
            assert res["success"]
            assert signal.tx_force_raw is True
            await monitor.set_signal_tx_force_raw(device.id, signal.id, False)
            await monitor.edit_signal_pronto(
                device.id, signal.id, pronto, alias="Power On"
            )
        assert signal.alias == "Power On"
        assert signal.tx_force_raw is False


class TestTheSpacingStandIn:
    """The spacing doors measure the row as the save will leave it."""

    def test_a_new_40khz_code_is_measured_raw(self):
        from custom_components.hair.websocket_api import _spacing_row_for_pronto

        row = _spacing_row_for_pronto(_pioneer_pronto(40_000))
        assert row.tx_force_raw is True
        assert would_send_decoded(row) is False

    def test_a_38khz_code_is_measured_as_today(self):
        from custom_components.hair.websocket_api import _spacing_row_for_pronto

        row = _spacing_row_for_pronto(_pioneer_pronto(38_000))
        assert row.tx_force_raw is False
        assert would_send_decoded(row) is True

    def test_an_unchanged_code_keeps_the_pin_on_screen(self):
        from custom_components.hair.websocket_api import _spacing_row_for_pronto

        pronto = _pioneer_pronto(40_000)
        stored = _row(pronto, tx_force_raw=False)
        row = _spacing_row_for_pronto(pronto, tx_force_raw=False, like=stored)
        assert row.tx_force_raw is False
