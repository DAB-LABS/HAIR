"""The echo ticket's tolerant fallback (owner ruling 2026-08-18).

Finding B of the Remote Buffing dress rehearsal: setting a pinned matrix
Device's dial put three frames back through the Athom, the fuzzy garble
guard swallowed two, and the third was heard as a handset press and
fired the state trigger. The ticket claimed nothing because both
identities it held were computed from the FILE, which is not what a
receiver hands back.

Captures are the bench's own -- see ``fixtures/air-path/README.md``.
"""
from __future__ import annotations

import json
from time import monotonic
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair import signal_monitor as _sm
from custom_components.hair.ir_command import raw_to_pronto
from custom_components.hair.models import CaptureResult
from custom_components.hair.wig_identity import wig_signal_identity

from .test_tolerant_identity import air_captures, air_code


def echo_ticket(pronto: str, *, tolerant: bool = True) -> dict:
    """A ticket shaped exactly as record_send builds one for a cell send.

    ``tolerant=False`` is what shipped before the ruling: the ticket
    held only the identities computed from the FILE.

    ``sl`` is deliberately None so the fuzzy garble guard cannot stand
    in for the ticket. What these tests measure is the TICKET.
    """
    from custom_components.hair.identity import norm_fingerprint_of_code

    identity = wig_signal_identity(pronto)
    assert identity is not None
    now = monotonic()
    return {
        "decoded_fp": identity.decoded_fingerprint,
        "sig_fp": identity.fingerprint,
        "norm_fp": norm_fingerprint_of_code(pronto) if tolerant else None,
        "row_key": identity.decoded_fingerprint or identity.fingerprint,
        "expires": 10 ** 12,
        "sl": None,
        "garble_expires": 0.0,
        "cancel": None,
        "heard_future": None,
        "claimed_by": set(),
        "emitters": ["infrared.wi_fi_universal_remote_ir_emitter"],
        "armed_at": now - 0.2,
        "guard_until": now + 10.0,
    }


def echo_frames(count: int = 3) -> list:
    """Real Broadlink captures of C1, standing in for one echo.

    The bench's own case: a pinned matrix Device sent cool/auto/23 and
    the Athom heard three frames back. Broadlink captures because the
    Device transmits on the Broadlink.
    """
    rows = air_captures("C1", "broadlink")[:count]
    assert len(rows) == count
    frames = []
    for row in rows:
        values = json.loads(row["timings_us"])
        raw = [v if i % 2 == 0 else -abs(v) for i, v in enumerate(values)]
        frames.append(
            CaptureResult(
                protocol="PRONTO",
                code=raw_to_pronto(raw, frequency=38029),
                raw_timings=raw,
                frequency=38029,
            )
        )
    return frames


def echo_monitor():
    from custom_components.hair.signal_monitor import SignalMonitor

    from .test_signal_monitor import (
        _make_hair_store,
        _make_hass,
        _make_signal_store,
    )

    hass = _make_hass()
    trigger_manager = MagicMock()
    listener = MagicMock()
    listener.on_signal_captured = AsyncMock(return_value=[])
    monitor = SignalMonitor(
        hass, _make_signal_store(hass), _make_hair_store(),
        trigger_manager, listener,
    )
    return monitor, trigger_manager, listener


@pytest.mark.asyncio
async def test_every_frame_of_our_own_send_is_attributed_to_it():
    """Finding B from the dress rehearsal, closed.

    Setting a pinned matrix Device's dial put three frames back through
    the Athom. The ticket held the file's decoded and S/L identities,
    the air moved both, so the ticket claimed nothing: the fuzzy garble
    guard swallowed two frames and the third was heard as a handset
    press and fired the state trigger. Reproduced twice on the bench.

    With the ticket's tolerant fallback, all three are the send.
    """
    monitor, tm, listener = echo_monitor()
    monitor._echo_expectations.append(echo_ticket(air_code("C1")))

    for frame in echo_frames(3):
        await monitor._process_parsed_signal(
            frame, receiver_entity_id="infrared.athom_rx"
        )

    tm.on_signal_captured.assert_not_called()
    listener.on_signal_captured.assert_not_called()


@pytest.mark.asyncio
async def test_without_the_fallback_the_echo_reaches_the_triggers():
    """The same three frames against the ticket as it shipped."""
    monitor, tm, _listener = echo_monitor()
    monitor._echo_expectations.append(
        echo_ticket(air_code("C1"), tolerant=False)
    )

    for frame in echo_frames(3):
        await monitor._process_parsed_signal(
            frame, receiver_entity_id="infrared.athom_rx"
        )

    assert tm.on_signal_captured.call_count == 3


@pytest.mark.asyncio
async def test_a_decoded_capture_is_not_claimed_on_shape_alone():
    """A frame that decoded is answered by the decoded tier or not here.

    The ticket's tolerant fallback must not let a different code ride in
    on a shared shape; only a capture nothing could decode reaches it.
    """
    monitor, tm, _listener = echo_monitor()
    ticket = echo_ticket(air_code("C1"))
    ticket["decoded_fp"] = "NEC:0x1234:0x56"
    monitor._echo_expectations.append(ticket)

    frame = echo_frames(1)[0]
    with patch.object(
        _sm, "try_decode_identity",
        return_value=SimpleNamespace(
            protocol="NEC", address=0x99, command=0x01,
            fingerprint="NEC:0x0099:0x01", extras=None,
            # The real DecodedIdentity carries the coverage verdict
            # (GH #134); None is what an unjudgeable decode reports and
            # is what this stand-in should say.
            covers_capture=None,
        ),
    ):
        await monitor._process_parsed_signal(
            frame, receiver_entity_id="infrared.athom_rx"
        )

    assert tm.on_signal_captured.call_count == 1
