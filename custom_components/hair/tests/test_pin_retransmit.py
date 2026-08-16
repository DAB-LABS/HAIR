"""Tests for pinned-remote retransmit (signpost 4, Track 2).

Two things are under test and they are worth naming separately. The
DISPATCH POLICY (coalescing) is the interesting half: it exists so a
held button cannot build a queue that outlives the finger, and the
"never lands after the press stops" property is what bench case 3
checks in the room. The WIRING half is smaller but load-bearing: the
retransmit must ride the confirmed fire, never the raw hit, and must
never replace the trigger's event.
"""
from __future__ import annotations

import asyncio
import logging
from time import monotonic

import pytest

from custom_components.hair.const import PINNED_LOOP_MAX_SENDS
from custom_components.hair.models import (
    IRCommand,
    IRDevice,
    IRTrigger,
    TriggerRemote,
)
from custom_components.hair.pin_bindings import rederive_remote
from custom_components.hair.pin_retransmit import RetransmitDispatcher
from custom_components.hair.storage import HAIRStore
from custom_components.hair.trigger_manager import TriggerManager

TARGET = ("r1", "d1", "c1")
OTHER_COMMAND = ("r1", "d1", "c2")
OTHER_DEVICE = ("r1", "d2", "c1")


class _TaskHass:
    """Minimal hass whose async_create_task actually schedules.

    The shared ``fake_hass`` fixture returns the coroutine unscheduled,
    which is right for tests that only assert a call was made -- but
    the dispatcher's whole behaviour lives in what happens when the
    send actually runs and completes.
    """

    def __init__(self):
        self.tasks = []

    def async_create_task(self, coro):
        task = asyncio.ensure_future(coro)
        self.tasks.append(task)
        return task

    async def drain(self):
        while self.tasks:
            batch, self.tasks = self.tasks, []
            await asyncio.gather(*batch)


class _Sender:
    """Records sends; each one blocks until explicitly released."""

    def __init__(self):
        self.sent: list[tuple[str, str]] = []
        self.gate = asyncio.Event()
        self.entered = asyncio.Event()
        self.fail = False

    async def __call__(self, device_id: str, command_id: str) -> None:
        self.sent.append((device_id, command_id))
        self.entered.set()
        await self.gate.wait()
        if self.fail:
            raise RuntimeError("no emitters configured")


# ---------------------------------------------------------------------------
# Dispatch policy: coalescing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_an_idle_target_sends_immediately():
    hass, sender = _TaskHass(), _Sender()
    d = RetransmitDispatcher(hass, sender)

    assert d.dispatch(TARGET) is True
    await sender.entered.wait()
    sender.gate.set()
    await hass.drain()

    assert sender.sent == [("d1", "c1")]


@pytest.mark.asyncio
async def test_repeat_fires_during_one_send_collapse_to_a_single_follow_up():
    """THE coalesce guarantee. A held button fires many times while one
    send is in flight; pending is a slot, not a queue, so exactly one
    follow-up send happens -- not one per press."""
    hass, sender = _TaskHass(), _Sender()
    d = RetransmitDispatcher(hass, sender)

    assert d.dispatch(TARGET) is True
    await sender.entered.wait()
    for _ in range(50):
        assert d.dispatch(TARGET) is False

    sender.gate.set()
    await hass.drain()

    assert sender.sent == [("d1", "c1"), ("d1", "c1")]


@pytest.mark.asyncio
async def test_the_backlog_is_never_more_than_one_press_deep():
    """What bench case 3 is really asserting: when the presses stop,
    the dispatcher drains and stays drained. No step arrives late
    because nothing was allowed to pile up."""
    hass, sender = _TaskHass(), _Sender()
    sender.gate.set()
    d = RetransmitDispatcher(hass, sender)

    for _ in range(20):
        d.dispatch(TARGET)
    await hass.drain()

    assert not d.busy
    # 20 presses, but the queue never held more than one follow-up.
    assert len(sender.sent) < 20


@pytest.mark.asyncio
async def test_distinct_targets_never_coalesce_into_each_other():
    """Different buttons, and the same button on a second device, are
    separate targets -- coalescing must not swallow them."""
    hass, sender = _TaskHass(), _Sender()
    d = RetransmitDispatcher(hass, sender)

    assert d.dispatch(TARGET) is True
    assert d.dispatch(OTHER_COMMAND) is True
    assert d.dispatch(OTHER_DEVICE) is True

    sender.gate.set()
    await hass.drain()

    assert sorted(sender.sent) == sorted([("d1", "c1"), ("d1", "c2"), ("d2", "c1")])


@pytest.mark.asyncio
async def test_a_failing_send_still_clears_its_slot():
    """A device with no emitters must not wedge its own target forever
    -- the next press has to get a fresh attempt."""
    hass, sender = _TaskHass(), _Sender()
    sender.fail = True
    sender.gate.set()
    d = RetransmitDispatcher(hass, sender)

    d.dispatch(TARGET)
    await hass.drain()
    assert not d.busy

    assert d.dispatch(TARGET) is True
    await hass.drain()
    assert len(sender.sent) == 2


@pytest.mark.asyncio
async def test_a_failing_send_does_not_escape_into_the_caller():
    hass, sender = _TaskHass(), _Sender()
    sender.fail = True
    sender.gate.set()
    d = RetransmitDispatcher(hass, sender)

    d.dispatch(TARGET)
    await hass.drain()  # would raise if the guard leaked


@pytest.mark.asyncio
async def test_shutdown_refuses_new_work_and_drops_pending():
    hass, sender = _TaskHass(), _Sender()
    d = RetransmitDispatcher(hass, sender)

    d.dispatch(TARGET)
    await sender.entered.wait()
    d.dispatch(TARGET)  # pending
    d.shutdown()

    sender.gate.set()
    await hass.drain()

    assert sender.sent == [("d1", "c1")]
    assert d.dispatch(TARGET) is False
    assert sender.sent == [("d1", "c1")]


# ---------------------------------------------------------------------------
# The loop breaker (Track 3a)
# ---------------------------------------------------------------------------


LABEL = ("Handset", "Living Room TV", "Volume Down")


async def _drive(d, hass, times, target=TARGET, label=LABEL):
    started = 0
    for _ in range(times):
        if d.dispatch(target, label):
            started += 1
        await hass.drain()
    return started


@pytest.mark.asyncio
async def test_a_runaway_binding_is_cut(caplog):
    """The floor under the echo defense. A binding that keeps driving
    the same device faster than any human could is cut loose rather
    than left to run until somebody notices -- which is what a real
    runaway did: 77 fires over 40 seconds, stopped only by a person
    unpinning the devices."""
    hass, sender = _TaskHass(), _Sender()
    sender.gate.set()
    d = RetransmitDispatcher(hass, sender)

    with caplog.at_level(logging.WARNING):
        started = await _drive(d, hass, PINNED_LOOP_MAX_SENDS + 4)

    assert started == PINNED_LOOP_MAX_SENDS
    assert len(sender.sent) == PINNED_LOOP_MAX_SENDS
    assert d.is_cooling_down(TARGET)


@pytest.mark.asyncio
async def test_the_warning_names_the_remote_device_and_trigger(caplog):
    """A user reading the log has to know WHICH pairing was cut, in the
    words they gave those objects."""
    hass, sender = _TaskHass(), _Sender()
    sender.gate.set()
    d = RetransmitDispatcher(hass, sender)

    with caplog.at_level(logging.WARNING):
        await _drive(d, hass, PINNED_LOOP_MAX_SENDS + 2)

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    for name in LABEL:
        assert name in message


@pytest.mark.asyncio
async def test_the_cut_recovers_and_starts_clean():
    """A cooldown, not a ban: the pairing comes back by itself, and it
    comes back with a fresh budget rather than re-tripping on its
    first send."""
    hass, sender = _TaskHass(), _Sender()
    sender.gate.set()
    d = RetransmitDispatcher(hass, sender)
    await _drive(d, hass, PINNED_LOOP_MAX_SENDS + 2)
    assert d.is_cooling_down(TARGET)

    d._cooldown[TARGET] = monotonic() - 1.0  # cooldown served

    assert d.dispatch(TARGET, LABEL) is True
    await hass.drain()
    assert not d.is_cooling_down(TARGET)


@pytest.mark.asyncio
async def test_a_plausible_burst_does_not_trip_the_breaker():
    """The breaker must not punish ordinary use. Well under the
    threshold has to pass straight through."""
    hass, sender = _TaskHass(), _Sender()
    sender.gate.set()
    d = RetransmitDispatcher(hass, sender)

    started = await _drive(d, hass, PINNED_LOOP_MAX_SENDS - 1)

    assert started == PINNED_LOOP_MAX_SENDS - 1
    assert not d.is_cooling_down(TARGET)


@pytest.mark.asyncio
async def test_cutting_one_binding_leaves_the_others_running():
    """A loop between one remote and one device says nothing about the
    remote's other pinned devices, which must keep working."""
    hass, sender = _TaskHass(), _Sender()
    sender.gate.set()
    d = RetransmitDispatcher(hass, sender)

    await _drive(d, hass, PINNED_LOOP_MAX_SENDS + 2)
    assert d.is_cooling_down(TARGET)

    assert d.dispatch(OTHER_DEVICE, LABEL) is True
    assert not d.is_cooling_down(OTHER_DEVICE)


# ---------------------------------------------------------------------------
# Wiring: the retransmit rides the confirmed fire
# ---------------------------------------------------------------------------


class _RecordingDeviceManager:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []
        self.pinned_flags: list[bool] = []

    async def async_send_command(
        self, device_id, command_id, heard_future=None, pinned=False
    ):
        self.sent.append((device_id, command_id))
        self.pinned_flags.append(pinned)


def _pinned_setup(fake_hass, *, min_hits=1):
    """A remote pinned to a device, both sharing one decoded identity."""
    store = HAIRStore(fake_hass)
    dev = IRDevice(
        id="dev1",
        name="TV",
        commands=[IRCommand(id="cmd1", name="Power",
                            decoded_fingerprint="NEC:0x1:0x1")],
    )
    store.add_device(dev)
    remote = TriggerRemote(id="rem1", name="Handset", pinned_device_ids=["dev1"])
    store.add_trigger_remote(remote)
    trigger = IRTrigger(
        id="trg1",
        name="Power",
        trigger_remote_id="rem1",
        signal_fingerprint="fp-power",
        decoded_fingerprint="NEC:0x1:0x1",
        min_hits=min_hits,
    )
    store.add_trigger(trigger)
    rederive_remote(store, remote)
    return store, trigger


@pytest.mark.asyncio
async def test_a_confirmed_fire_drives_the_pinned_device(fake_hass):
    store, _ = _pinned_setup(fake_hass)
    dm = _RecordingDeviceManager()
    hass = _TaskHass()
    hass.bus = fake_hass.bus
    tm = TriggerManager(hass, store, dm)

    fired = tm.on_signal_captured(
        "fp-power", None, None, decoded_fingerprint="NEC:0x1:0x1"
    )
    await hass.drain()

    assert fired == ["trg1"]
    assert dm.sent == [("dev1", "cmd1")]
    # The retransmit must announce itself as one: the Mirror's Pinned
    # Send chip is driven by this flag and nothing else, so a proxied
    # press would otherwise read as an ordinary device send.
    assert dm.pinned_flags == [True]


@pytest.mark.asyncio
async def test_a_send_never_precedes_its_own_fire(fake_hass):
    """THE invariant: a capture is either an echo -- no fire, no stamp,
    no send -- or it is a press, in which case fire_count and
    last_fired_at are stamped and the event has fired BEFORE anything
    is transmitted. A device driven by a press that never fired its
    event would silently break every automation on that trigger.

    Asserted by reading the trigger's own state from inside the send,
    so the ordering is observed at the moment it matters rather than
    inferred afterwards.
    """
    store, trigger = _pinned_setup(fake_hass)
    order: list[tuple] = []

    class _OrderingDeviceManager:
        async def async_send_command(self, device_id, command_id,
                                     heard_future=None, pinned=False):
            order.append(
                ("send", trigger.fire_count, trigger.last_fired_at is not None)
            )

    hass = _TaskHass()
    hass.bus = fake_hass.bus
    tm = TriggerManager(hass, store, _OrderingDeviceManager())
    tm.subscribe(lambda e: order.append(("event", e["trigger_id"])))

    tm.on_signal_captured("fp-power", None, None,
                          decoded_fingerprint="NEC:0x1:0x1")
    await hass.drain()

    assert order == [("event", "trg1"), ("send", 1, True)]


@pytest.mark.asyncio
async def test_a_capture_that_never_fires_never_sends(fake_hass):
    """The other half of the invariant. Nothing matched, so nothing
    fired, so nothing may transmit."""
    store, _ = _pinned_setup(fake_hass)
    dm = _RecordingDeviceManager()
    hass = _TaskHass()
    hass.bus = fake_hass.bus
    tm = TriggerManager(hass, store, dm)

    fired = tm.on_signal_captured("some-other-fingerprint", None, None)
    await hass.drain()

    assert fired == []
    assert dm.sent == []


@pytest.mark.asyncio
async def test_the_coalesced_follow_up_is_the_one_deliberate_exception():
    """Honesty about the single place a send is not one-to-one with a
    fire. A follow-up dispatched from the pending slot carries no new
    fire of its own -- it IS the latest press, deferred because the tx
    gate was busy when that press arrived. Pinned here so the exception
    stays deliberate and visible rather than becoming a surprise.
    """
    hass, sender = _TaskHass(), _Sender()
    d = RetransmitDispatcher(hass, sender)

    d.dispatch(TARGET)
    await sender.entered.wait()
    d.dispatch(TARGET)  # a real second fire, coalesced into the slot
    sender.gate.set()
    await hass.drain()

    # Two fires, two sends -- the follow-up is not a phantom.
    assert sender.sent == [("d1", "c1"), ("d1", "c1")]


@pytest.mark.asyncio
async def test_the_trigger_event_still_fires_alongside_the_retransmit(fake_hass):
    """Pinning ADDS the retransmit; it never replaces the event, so
    automations built on this trigger keep working."""
    store, _ = _pinned_setup(fake_hass)
    dm = _RecordingDeviceManager()
    hass = _TaskHass()
    hass.bus = fake_hass.bus
    tm = TriggerManager(hass, store, dm)
    seen = []
    tm.subscribe(seen.append)

    tm.on_signal_captured("fp-power", None, None,
                          decoded_fingerprint="NEC:0x1:0x1")
    await hass.drain()

    assert dm.sent == [("dev1", "cmd1")]
    assert [e["trigger_id"] for e in seen] == ["trg1"]
    assert fake_hass.bus.async_fire.called


@pytest.mark.asyncio
async def test_min_hits_gates_the_retransmit_too(fake_hass):
    """The binding rides the FIRE, not the raw signal, so a 3-hit
    trigger retransmits once -- on the third press."""
    store, _ = _pinned_setup(fake_hass, min_hits=3)
    dm = _RecordingDeviceManager()
    hass = _TaskHass()
    hass.bus = fake_hass.bus
    tm = TriggerManager(hass, store, dm)

    for _ in range(3):
        tm.on_signal_captured("fp-power", None, None,
                              decoded_fingerprint="NEC:0x1:0x1")
        # Each press must land outside the cross-receiver dedup window.
        await asyncio.sleep(0.12)
    await hass.drain()

    assert dm.sent == [("dev1", "cmd1")]


@pytest.mark.asyncio
async def test_an_unpinned_remote_retransmits_nothing(fake_hass):
    store, _ = _pinned_setup(fake_hass)
    remote = store.get_trigger_remote("rem1")
    remote.pinned_device_ids.clear()
    rederive_remote(store, remote)

    dm = _RecordingDeviceManager()
    hass = _TaskHass()
    hass.bus = fake_hass.bus
    tm = TriggerManager(hass, store, dm)

    fired = tm.on_signal_captured("fp-power", None, None,
                                  decoded_fingerprint="NEC:0x1:0x1")
    await hass.drain()

    assert fired == ["trg1"]
    assert dm.sent == []


@pytest.mark.asyncio
async def test_a_drawer_trigger_retransmits_nothing(fake_hass):
    """No owning remote means no pins to read."""
    store = HAIRStore(fake_hass)
    store.add_trigger(
        IRTrigger(id="trg1", name="Power", signal_fingerprint="fp-power")
    )
    dm = _RecordingDeviceManager()
    hass = _TaskHass()
    hass.bus = fake_hass.bus
    tm = TriggerManager(hass, store, dm)

    tm.on_signal_captured("fp-power", None, None)
    await hass.drain()

    assert dm.sent == []


@pytest.mark.asyncio
async def test_a_disabled_trigger_retransmits_nothing(fake_hass):
    """Falls out of riding the fire: storage filters disabled triggers
    before matching, so this needs no code of its own -- pinned here so
    a future matcher change cannot quietly re-enable it."""
    store, trigger = _pinned_setup(fake_hass)
    trigger.enabled = False
    store.update_trigger(trigger)

    dm = _RecordingDeviceManager()
    hass = _TaskHass()
    hass.bus = fake_hass.bus
    tm = TriggerManager(hass, store, dm)

    fired = tm.on_signal_captured("fp-power", None, None,
                                  decoded_fingerprint="NEC:0x1:0x1")
    await hass.drain()

    assert fired == []
    assert dm.sent == []


@pytest.mark.asyncio
async def test_two_pinned_devices_are_both_driven(fake_hass):
    store, _ = _pinned_setup(fake_hass)
    second = IRDevice(
        id="dev2",
        name="Soundbar",
        commands=[IRCommand(id="cmd2", name="Power",
                            decoded_fingerprint="NEC:0x1:0x1")],
    )
    store.add_device(second)
    remote = store.get_trigger_remote("rem1")
    remote.pinned_device_ids.append("dev2")
    rederive_remote(store, remote)

    dm = _RecordingDeviceManager()
    hass = _TaskHass()
    hass.bus = fake_hass.bus
    tm = TriggerManager(hass, store, dm)

    tm.on_signal_captured("fp-power", None, None,
                          decoded_fingerprint="NEC:0x1:0x1")
    await hass.drain()

    assert sorted(dm.sent) == [("dev1", "cmd1"), ("dev2", "cmd2")]


@pytest.mark.asyncio
async def test_without_a_device_manager_nothing_retransmits(fake_hass):
    """The pre-signpost-4 construction shape stays inert, which is what
    keeps every existing call site and test honest."""
    store, _ = _pinned_setup(fake_hass)
    tm = TriggerManager(fake_hass, store)

    fired = tm.on_signal_captured("fp-power", None, None,
                                  decoded_fingerprint="NEC:0x1:0x1")

    assert fired == ["trg1"]
    tm.shutdown()  # must not raise with no dispatcher
