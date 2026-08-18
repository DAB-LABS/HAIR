"""The echo expectation as a single-use ticket (signpost 4, Track 3).

Before pinning, an expectation was a BLANKET: it claimed every capture
matching its identity for its whole TTL. That is invisible while only
HAIR transmits -- nobody can press the button HAIR just pressed. Pinning
makes it visible and wrong: the handset is in a human's hand, and a
second deliberate press inside the window carries exactly the identity
the ticket is watching for, so the press was claimed as an echo and
eaten.

The ticket is spent once PER RECEIVER, which is what keeps the Mirror's
heard_by complete when several receivers hear one send, and what lets a
two-device fan-out (two device sends, two tickets) cover a receiver that
hears both echoes.

Expiry stays cleanup rather than mechanism: an unspent ticket still has
to die on the clock, or an emitter aimed away from every receiver leaves
one armed to eat a real press much later.
"""
from __future__ import annotations

from time import monotonic
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hair.const import MIRROR_DEVICE_FP
from custom_components.hair.signal_monitor import SignalMonitor

from .test_signal_monitor import (
    _make_event,
    _make_hair_store,
    _make_hass,
    _make_signal_store,
    _nec_event,
)

ATHOM = "infrared.athom_rx"
PUCK = "infrared.garage_workbench_ir_puck"


def _parsed_and_norm(code: str = "0x1234"):
    from custom_components.hair import signal_monitor as sm

    parsed = sm.EventParser.parse(_make_event(_nec_event(code)).data)
    return parsed, sm.normalize(parsed)


def _ticket(
    n,
    *,
    expires: float = 10**12,
    armed: bool = True,
    guard: bool = False,
) -> dict:
    """An expectation shaped exactly as record_send builds one.

    ``armed`` mirrors the beacon having fired (Track 3a). ``guard``
    keeps the post-send window open; it defaults CLOSED so the
    single-use tests below exercise ticket accounting rather than the
    guard standing in for it.
    """
    now = monotonic()
    return {
        "decoded_fp": n.decoded_fingerprint,
        "sig_fp": n.sig_fp,
        "row_key": n.decoded_fingerprint or n.sig_fp,
        "expires": expires,
        "sl": None,
        "garble_expires": 0.0,
        "cancel": None,
        "heard_future": None,
        "claimed_by": set(),
        "emitters": ["infrared.bench_tx_1"],
        "armed_at": (now - 10.0) if armed else None,
        "guard_until": (now + 10.0) if guard else 0.0,
    }


def _monitor_with_triggers():
    hass = _make_hass()
    store = _make_signal_store(hass)
    trigger_manager = MagicMock()
    monitor = SignalMonitor(hass, store, _make_hair_store(), trigger_manager)
    return monitor, trigger_manager


@pytest.mark.asyncio
async def test_the_first_matching_capture_is_still_claimed():
    """The echo suppression itself is unchanged -- one send, one echo,
    no trigger fire. Everything below is about the SECOND capture."""
    monitor, tm = _monitor_with_triggers()
    parsed, n = _parsed_and_norm()
    monitor._echo_expectations.append(_ticket(n))

    await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)

    tm.on_signal_captured.assert_not_called()


@pytest.mark.asyncio
async def test_a_second_press_at_the_same_receiver_fires():
    """THE bug this track exists to close. Two deliberate presses inside
    one expectation's TTL: the first is the echo, the second is a real
    press and must reach the triggers. Under the old blanket it was
    silently eaten, and a pinned volume ramp advanced one step per
    window instead of one per press."""
    monitor, tm = _monitor_with_triggers()
    parsed, n = _parsed_and_norm()
    monitor._echo_expectations.append(_ticket(n))

    await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)
    tm.on_signal_captured.assert_not_called()

    await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)
    assert tm.on_signal_captured.call_count == 1


@pytest.mark.asyncio
async def test_every_later_press_keeps_firing():
    """The ticket is spent once and stays spent -- it does not recover
    and start eating presses again while it lives out its TTL."""
    monitor, tm = _monitor_with_triggers()
    parsed, n = _parsed_and_norm()
    monitor._echo_expectations.append(_ticket(n))

    for _ in range(5):
        await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)

    assert tm.on_signal_captured.call_count == 4


@pytest.mark.asyncio
async def test_two_receivers_each_spend_their_own_ticket_slot():
    """One send heard by two receivers is still one send. Both hearings
    are echoes, neither fires, and heard_by gets both -- which is why
    consumption is per receiver rather than global."""
    monitor, tm = _monitor_with_triggers()
    parsed, n = _parsed_and_norm()
    # Seed the Mirror row the way record_send would, so heard_by has
    # something to enrich.
    await monitor._mirror_upsert(
        n, decoded_fp=n.decoded_fingerprint,
        echo_source="TV / Power -- via Emitter", reset_heard=True,
    )
    monitor._echo_expectations.append(_ticket(n))

    await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)
    await monitor._process_parsed_signal(parsed, receiver_entity_id=PUCK)

    tm.on_signal_captured.assert_not_called()
    row = monitor._signal_store.get_device_by_fingerprint(
        MIRROR_DEVICE_FP
    ).signals[0]
    assert sorted(row.heard_by) == sorted([ATHOM, PUCK])


@pytest.mark.asyncio
async def test_a_fan_out_mints_one_ticket_per_device_send():
    """Two pinned devices means two device sends, so a receiver that
    hears both echoes has a ticket for each. Neither hearing fires."""
    monitor, tm = _monitor_with_triggers()
    parsed, n = _parsed_and_norm()
    monitor._echo_expectations.append(_ticket(n))
    monitor._echo_expectations.append(_ticket(n))

    await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)
    await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)

    tm.on_signal_captured.assert_not_called()

    # Third hearing has no ticket left and is treated as a press.
    await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)
    assert tm.on_signal_captured.call_count == 1


@pytest.mark.asyncio
async def test_a_legacy_capture_with_no_receiver_spends_its_own_slot():
    """Legacy ESPHome-bridge captures carry no receiver id. None is a
    slot like any other, so the same one-claim rule applies to them."""
    monitor, tm = _monitor_with_triggers()
    parsed, n = _parsed_and_norm()
    monitor._echo_expectations.append(_ticket(n))

    await monitor._process_parsed_signal(parsed, receiver_entity_id=None)
    tm.on_signal_captured.assert_not_called()

    await monitor._process_parsed_signal(parsed, receiver_entity_id=None)
    assert tm.on_signal_captured.call_count == 1


@pytest.mark.asyncio
async def test_a_spent_ticket_does_not_block_a_different_send():
    """Spending the Power ticket must not make the next Volume send
    unprotected, nor vice versa -- tickets are per identity."""
    monitor, tm = _monitor_with_triggers()
    parsed_a, n_a = _parsed_and_norm("0x1234")
    parsed_b, n_b = _parsed_and_norm("0x5678")
    monitor._echo_expectations.append(_ticket(n_a))
    monitor._echo_expectations.append(_ticket(n_b))

    await monitor._process_parsed_signal(parsed_a, receiver_entity_id=ATHOM)
    await monitor._process_parsed_signal(parsed_a, receiver_entity_id=ATHOM)
    assert tm.on_signal_captured.call_count == 1

    # B's ticket is untouched by A's traffic.
    await monitor._process_parsed_signal(parsed_b, receiver_entity_id=ATHOM)
    assert tm.on_signal_captured.call_count == 1


@pytest.mark.asyncio
async def test_expiry_still_retires_a_ticket_nobody_spent():
    """Expiry is cleanup, not mechanism. An emitter aimed away from
    every receiver leaves its ticket unspent; it must die on the clock
    rather than sit armed and eat a real press an hour later."""
    monitor, tm = _monitor_with_triggers()
    parsed, n = _parsed_and_norm()
    monitor._echo_expectations.append(_ticket(n, expires=0.0))

    await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)

    assert tm.on_signal_captured.call_count == 1


# ---------------------------------------------------------------------------
# Track 3a: the beacon anchor, and the runaway it exists to prevent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_handsets_own_repeat_frames_cannot_spend_a_pre_send_ticket():
    """THE runaway regression, pinned.

    A Samsung press reaches the receiver as three captures about 110 ms
    apart. When a ticket was spendable the moment it was minted, frames
    two and three spent it before the Broadlink had transmitted; the
    real echo then found no ticket, was read as a genuine press, fired,
    retransmitted, echoed and bred -- 77 fires in 40 seconds.

    An unarmed ticket covers a send whose IR has not left, so it must
    claim nothing at all.
    """
    monitor, tm = _monitor_with_triggers()
    parsed, n = _parsed_and_norm()
    monitor._echo_expectations.append(_ticket(n, armed=False))

    for _ in range(3):
        await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)

    assert tm.on_signal_captured.call_count == 3
    assert monitor._echo_expectations[0]["claimed_by"] == set()


@pytest.mark.asyncio
async def test_the_beacon_arms_the_ticket_and_the_echo_is_then_claimed():
    """The other half: once IR has actually left, the echo is ours."""
    monitor, tm = _monitor_with_triggers()
    parsed, n = _parsed_and_norm()
    monitor._echo_expectations.append(_ticket(n, armed=False))

    await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)
    assert tm.on_signal_captured.call_count == 1  # pre-send, a real press

    monitor._arm_expectations_for("infrared.bench_tx_1", monotonic())

    await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)
    assert tm.on_signal_captured.call_count == 1  # the echo, suppressed


@pytest.mark.asyncio
async def test_arming_is_idempotent_across_several_emitter_beacons():
    """A multi-emitter send beacons once per emitter. The first beacon
    is when IR left; later ones must not slide the guard window
    forward and keep swallowing presses."""
    monitor, _ = _monitor_with_triggers()
    _, n = _parsed_and_norm()
    ticket = _ticket(n, armed=False)
    ticket["emitters"] = ["infrared.bench_tx_1", "infrared.bench_tx_2"]
    monitor._echo_expectations.append(ticket)

    monitor._arm_expectations_for("infrared.bench_tx_1", 100.0)
    monitor._arm_expectations_for("infrared.bench_tx_2", 500.0)

    assert ticket["armed_at"] == 100.0


@pytest.mark.asyncio
async def test_the_post_send_guard_catches_what_the_ticket_missed():
    """The safety floor. The ticket is spent for this receiver, but we
    transmitted this identity moments ago, so the capture is our own
    voice and must not reach the triggers however the bookkeeping got
    there."""
    monitor, tm = _monitor_with_triggers()
    parsed, n = _parsed_and_norm()
    monitor._echo_expectations.append(_ticket(n, guard=True))

    await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)
    await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)

    tm.on_signal_captured.assert_not_called()


@pytest.mark.asyncio
async def test_the_guard_is_a_window_not_a_budget():
    """It suppresses without consuming, so it keeps holding for as long
    as it is open rather than being used up by the first capture."""
    monitor, tm = _monitor_with_triggers()
    parsed, n = _parsed_and_norm()
    monitor._echo_expectations.append(_ticket(n, guard=True))

    for _ in range(4):
        await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)

    tm.on_signal_captured.assert_not_called()


@pytest.mark.asyncio
async def test_once_the_guard_closes_a_real_press_gets_through():
    """The guard is a floor, not a gag. It has to expire, or a pinned
    remote goes deaf to its own handset."""
    monitor, tm = _monitor_with_triggers()
    parsed, n = _parsed_and_norm()
    monitor._echo_expectations.append(_ticket(n, guard=False))

    await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)
    tm.on_signal_captured.assert_not_called()

    await monitor._process_parsed_signal(parsed, receiver_entity_id=ATHOM)
    assert tm.on_signal_captured.call_count == 1


@pytest.mark.asyncio
async def test_record_send_mints_an_unarmed_ticket():
    """The production creator must agree with the fixtures above: a
    freshly minted ticket is pre-send and claims nothing."""
    hass = _make_hass()
    store = _make_signal_store(hass)
    monitor = SignalMonitor(hass, store, _make_hair_store())
    _, n = _parsed_and_norm()

    from custom_components.hair import signal_monitor as sm

    with patch.object(sm, "normalize_command", lambda _c: n):
        monitor.record_send(
            object(), "TV / Power", ["infrared.bench_tx_1"],
            decoded_fingerprint=n.decoded_fingerprint, send_count=1,
        )

    exp = monitor._echo_expectations[0]
    assert exp["armed_at"] is None
    assert exp["emitters"] == ["infrared.bench_tx_1"]


@pytest.mark.asyncio
async def test_record_send_builds_a_ticket_with_an_empty_claim_set():
    """The production creator and the test fixtures must agree on the
    shape, or these tests prove nothing about the real path."""
    hass = _make_hass()
    store = _make_signal_store(hass)
    monitor = SignalMonitor(hass, store, _make_hair_store())
    _, n = _parsed_and_norm()

    from custom_components.hair import signal_monitor as sm

    # Same shape the Mirror suite uses: stub the normalization so the
    # test is about the expectation record, not about constructing a
    # transmittable Command.
    with patch.object(sm, "normalize_command", lambda _c: n):
        monitor.record_send(
            object(),
            "TV / Power",
            ["infrared.bench_tx_1"],
            decoded_fingerprint=n.decoded_fingerprint,
            send_count=1,
        )

    assert len(monitor._echo_expectations) == 1
    assert monitor._echo_expectations[0]["claimed_by"] == set()
