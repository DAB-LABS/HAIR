"""The decode-trust rule at the Flipper import door.

HAIR transmits a decodable row from its decoded triple. A file can
state bytes that the encoder for that triple does not reproduce, and
the first cut of the protocol pack proved it: a ``NECext`` line with an
address of 0xFF or less rendered ``04 00 08 F7`` into the stored Pronto,
decoded to ``NEC:0x0004:0x08``, and both send paths rebuilt that triple
through the NEC encoder, which treats an address that small as 8-bit
and wrote ``04 FB 08 F7`` on the air (review round 2, finding 2). The
stored code moved; the frame did not.

The rule that closes it is the one the repo already has for captures:
a row whose stored bytes the decoded triple cannot reproduce is sent
raw. The importer now re-encodes the triple of every row it renders,
compares, and stores the row with ``bypass_protocol`` where they
differ. These tests follow such a row from the file to the emitter.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import homeassistant.components.infrared as _infrared_mod
import pytest

from custom_components.hair.const import CommandCategory, CommandSource
from custom_components.hair.ir_command import ProntoCommand
from custom_components.hair.mint import mint_command
from custom_components.hair.models import IRDevice
from custom_components.hair.send_plan import build_like_send_path, would_send_decoded
from custom_components.hair.tests.leg import strict_nec_available
from custom_components.hair.tests.test_decoded_tx_consistency import (
    _make_device_manager,
    _unwrap,
)
from custom_components.hair.wig_adapters import convert
from custom_components.hair.wig_identity import wig_signal_identity

LOW_ADDRESS_NECEXT = (
    "Filetype: IR signals file\nVersion: 1\n#\n"
    "name: Power\ntype: parsed\nprotocol: NECext\n"
    "address: 04 00 00 00\ncommand: 08 F7 00 00\n#\n"
)

#: A NECext line whose address is above 0xFF and whose fourth byte is
#: the complement: the encoder reproduces it exactly, so no bypass.
PLAIN_NECEXT = (
    "Filetype: IR signals file\nVersion: 1\n#\n"
    "name: Power\ntype: parsed\nprotocol: NECext\n"
    "address: 7A 85 00 00\ncommand: 1F E0 00 00\n#\n"
)


def _wire_bytes(timings) -> tuple[int, ...]:
    bits = [1 if -timings[3 + 2 * i] > 1100 else 0 for i in range(32)]
    return tuple(sum(bits[8 * b + i] << i for i in range(8)) for b in range(4))


def _adopt(text: str):
    """The row a wig adopt mints from the file's one signal."""
    result = convert(text, name_hint="t.ir")
    assert result.error is None and result.skipped == [], result.skipped
    signal = result.wigs[0].signals[0]
    identity = wig_signal_identity(signal.pronto)
    # The same call ``_mint_wig_command`` in websocket_api makes, with
    # the same carriage of the wig's bypass into ``tx_force_raw``.
    return signal, mint_command(
        name=signal.alias,
        category=CommandCategory.CUSTOM,
        source=CommandSource.IMPORTED,
        protocol="PRONTO",
        code=identity.pronto,
        raw_timings=list(identity.raw_timings),
        frequency=identity.frequency,
        repeat_count=signal.ditto_count,
        tx_force_raw=signal.bypass_protocol,
        identity=identity,
    )


class TestTheImportDoor:
    def test_the_stored_pronto_carries_the_files_bytes(self):
        signal, _ = _adopt(LOW_ADDRESS_NECEXT)
        assert _wire_bytes(ProntoCommand(signal.pronto).get_raw_timings()) == (
            0x04, 0x00, 0x08, 0xF7
        )

    def test_a_row_the_triple_cannot_reproduce_is_bypass(self):
        signal, command = _adopt(LOW_ADDRESS_NECEXT)
        if strict_nec_available():
            assert command.decoded_fingerprint == "NEC:0x0004:0x08"
            assert signal.bypass_protocol is True
            assert command.tx_force_raw is True
        else:
            # Nothing decodes it on the bare leg, so there is no triple
            # to distrust and the row replays as any raw row does.
            assert command.decoded_fingerprint is None
            assert signal.bypass_protocol is False

    def test_a_row_the_triple_reproduces_is_not_bypass(self):
        signal, command = _adopt(PLAIN_NECEXT)
        assert signal.bypass_protocol is False
        assert command.tx_force_raw is False
        if strict_nec_available():
            assert command.decoded_fingerprint == "NEC:0x857a:0x1f"
            assert would_send_decoded(command)


class TestBothSendPaths:
    """The frame on the air equals the stored Pronto, on both paths."""

    def test_send_plan_builds_the_stored_bytes(self):
        signal, command = _adopt(LOW_ADDRESS_NECEXT)
        stored = ProntoCommand(signal.pronto).get_raw_timings()
        sent = build_like_send_path(command).get_raw_timings()
        assert not would_send_decoded(command)
        assert _wire_bytes(sent) == _wire_bytes(stored) == (0x04, 0x00, 0x08, 0xF7)
        assert list(sent) == list(stored)

    @pytest.mark.asyncio
    async def test_the_device_manager_sends_the_stored_bytes(self, fake_hass):
        signal, command = _adopt(LOW_ADDRESS_NECEXT)
        manager = _make_device_manager(fake_hass)
        device = IRDevice(name="Amp", emitter_entity_ids=["infrared.e"])
        device.add_command(command)
        manager._store.add_device(device)
        with patch.object(
            _infrared_mod, "async_send_command", AsyncMock()
        ) as ir_send:
            await manager.async_send_command(device.id, command.id)
        ir_send.assert_awaited_once()
        sent = _unwrap(ir_send.call_args[0][2]).get_raw_timings()
        stored = ProntoCommand(signal.pronto).get_raw_timings()
        assert _wire_bytes(sent) == (0x04, 0x00, 0x08, 0xF7)
        assert list(sent) == list(stored)

    @pytest.mark.skipif(
        not strict_nec_available(), reason="the failure needs the NEC encoder"
    )
    def test_without_the_bypass_the_encoder_would_have_complemented(self):
        """The defect being prevented, measured rather than asserted."""
        _, command = _adopt(LOW_ADDRESS_NECEXT)
        command.tx_force_raw = False
        assert would_send_decoded(command)
        rebuilt = build_like_send_path(command).get_raw_timings()
        assert _wire_bytes(rebuilt) == (0x04, 0xFB, 0x08, 0xF7)
