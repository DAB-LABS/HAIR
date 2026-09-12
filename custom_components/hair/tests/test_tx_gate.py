"""Tests for the transmit gate (emitter-change stagger).

The gate exists because two blasters keying up at once superimpose at
any receiver that hears both: the hybrid pulse train decodes as nothing,
fails the echo claim, and mints a junk Sniffer row (owner bench,
2026-07-18, dual-emitter SAMSUNG32 test).
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from custom_components.hair import tx_gate
from custom_components.hair.tx_gate import gated_send


@pytest.fixture(autouse=True)
def _fresh_gate():
    tx_gate.reset_for_test()
    yield
    tx_gate.reset_for_test()


def _recording_sender(log: list[str]):
    async def sender(hass, emitter_id, ir_cmd):
        log.append(emitter_id)

    return sender


@pytest.mark.asyncio
async def test_same_emitter_passes_without_stagger():
    """Back-to-back sends on ONE emitter never sleep -- the device queues
    its own bursts and SEND_REPEAT_GAP paces whole-frame repeats."""
    sent: list[str] = []
    sleeps: list[float] = []

    async def fake_sleep(s):
        sleeps.append(s)

    with patch.object(tx_gate.asyncio, "sleep", fake_sleep):
        await gated_send(None, "infrared.a", "cmd", _recording_sender(sent))
        await gated_send(None, "infrared.a", "cmd", _recording_sender(sent))

    assert sent == ["infrared.a", "infrared.a"]
    assert sleeps == []


@pytest.mark.asyncio
async def test_emitter_change_inserts_quiet_gap():
    """Switching emitters sleeps out the remainder of the stagger gap."""
    sent: list[str] = []
    sleeps: list[float] = []

    async def fake_sleep(s):
        sleeps.append(s)

    with patch.object(tx_gate.asyncio, "sleep", fake_sleep):
        await gated_send(None, "infrared.a", "cmd", _recording_sender(sent))
        await gated_send(None, "infrared.b", "cmd", _recording_sender(sent))

    assert sent == ["infrared.a", "infrared.b"]
    assert len(sleeps) == 1
    assert 0 < sleeps[0] <= tx_gate.EMITTER_STAGGER_GAP_S


@pytest.mark.asyncio
async def test_concurrent_callers_serialize():
    """The four tabs fire one test call per emitter concurrently
    (Promise.allSettled); the gate's lock serializes them so the sends
    never interleave in the air."""
    sent: list[str] = []
    in_flight = 0
    max_in_flight = 0

    async def sender(hass, emitter_id, ir_cmd):
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0)  # yield, giving overlap a chance to happen
        sent.append(emitter_id)
        in_flight -= 1

    async def fake_gap_sleep(s):
        return None

    with patch.object(tx_gate.asyncio, "sleep", fake_gap_sleep):
        await asyncio.gather(
            gated_send(None, "infrared.a", "cmd", sender),
            gated_send(None, "infrared.b", "cmd", sender),
        )

    assert sorted(sent) == ["infrared.a", "infrared.b"]
    assert max_in_flight == 1


@pytest.mark.asyncio
async def test_failed_send_still_stamps_the_gate():
    """A sender that raises still counts as air time: the blaster may
    have partially transmitted, so the next emitter change still waits."""
    sleeps: list[float] = []

    async def broken_sender(hass, emitter_id, ir_cmd):
        raise RuntimeError("emitter offline")

    async def fake_sleep(s):
        sleeps.append(s)

    with patch.object(tx_gate.asyncio, "sleep", fake_sleep):
        with pytest.raises(RuntimeError):
            await gated_send(None, "infrared.a", "cmd", broken_sender)
        sent: list[str] = []
        await gated_send(None, "infrared.b", "cmd", _recording_sender(sent))

    assert len(sleeps) == 1


@pytest.mark.asyncio
async def test_air_time_lengthens_the_hold():
    """A bundled burst keeps the air long after its own ack, so the
    next emitter waits on the air rather than on the stagger constant
    (send spacing, GH #151)."""
    sent: list[str] = []
    sleeps: list[float] = []

    async def fake_sleep(s):
        sleeps.append(s)

    with patch.object(tx_gate.asyncio, "sleep", fake_sleep):
        await gated_send(
            None, "infrared.a", "cmd", _recording_sender(sent), air_s=1.25
        )
        await gated_send(None, "infrared.b", "cmd", _recording_sender(sent))

    assert sent == ["infrared.a", "infrared.b"]
    assert len(sleeps) == 1
    assert 1.2 < sleeps[0] <= 1.25


@pytest.mark.asyncio
async def test_air_time_below_the_constant_changes_nothing():
    """An ordinary frame's air is well under the stagger gap, so the
    constant still wins and today's behaviour is unchanged."""
    sent: list[str] = []
    sleeps: list[float] = []

    async def fake_sleep(s):
        sleeps.append(s)

    with patch.object(tx_gate.asyncio, "sleep", fake_sleep):
        await gated_send(
            None, "infrared.a", "cmd", _recording_sender(sent), air_s=0.06
        )
        await gated_send(None, "infrared.b", "cmd", _recording_sender(sent))

    assert len(sleeps) == 1
    assert 0 < sleeps[0] <= tx_gate.EMITTER_STAGGER_GAP_S


@pytest.mark.asyncio
async def test_the_hold_does_not_block_the_same_emitter():
    """The hold is slept OUTSIDE the lock. A second send on the emitter
    that is already talking owes nothing, and must not queue behind
    another emitter's wait -- which is what holding the lock through a
    second and a half of quiet would do."""
    order: list[str] = []

    async def sender(hass, emitter_id, ir_cmd):
        order.append(emitter_id)

    # a keys up with 0.4s of planned air, so b owes 0.4s.
    await gated_send(None, "infrared.a", "cmd", sender, air_s=0.4)
    waiting = asyncio.create_task(gated_send(None, "infrared.b", "cmd", sender))
    await asyncio.sleep(0.02)  # let b reach its hold
    await gated_send(None, "infrared.a", "cmd", sender)
    assert order == ["infrared.a", "infrared.a"]
    await waiting
    assert order == ["infrared.a", "infrared.a", "infrared.b"]
