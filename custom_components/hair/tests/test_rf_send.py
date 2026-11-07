"""RF send, T1: the wire frame, the frequency, the send and its echo.

The rules are ``rf-in-hair-plan.md`` 5.5, 5.7, 5.8 and 5.10, under the
send round's doors (``agent-exchange/rf-hear/rf-send-doors.md``). Core's
``radio_frequency.async_send_command`` and ``rf_protocols``'
``OOKCommand`` are faked here: every send these tests make is recorded,
never transmitted.
"""
from __future__ import annotations

import json
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair import rf_frames, rf_send, tx_gate
from custom_components.hair.const import (
    EVENT_RECEIVER_HEARD,
    MAX_SEND_COUNT,
    MEDIUM_RF,
    RF_ASSUMED_FRAME_GAP_US,
    RF_DEFAULT_SEND_COUNT,
    RF_PROTOCOL,
    CommandCategory,
    CommandSource,
)
from custom_components.hair.models import IRCommand, IRDevice, UnknownDevice
from custom_components.hair.tests.test_rf_hear import (
    FIXTURE,
    _component,
    _monitor,
    _rf_signal,
    _signed,
)

ATHOM_TX = "radio_frequency.athom_rf_transmitter"
RM4_TX = "radio_frequency.rm4_pro_rf_transmitter"
CC1101_TX = "radio_frequency.cc1101_transmitter"
BARE_TX = "radio_frequency.no_frequency_transmitter"
IR_TX = "infrared.living_room"
ATHOM_RX = "radio_frequency.athom_rf_receiver"

RANGES = {
    ATHOM_TX: [(433_920_000, 433_920_000)],
    RM4_TX: [(433_050_000, 434_790_000), (314_950_000, 315_250_000)],
    CC1101_TX: [(300_000_000, 928_000_000)],
    BARE_TX: [(0, 0)],
}


@pytest.fixture(scope="module")
def captures():
    """The bench keyfob through an RM4 Pro window, as round 1 reads it."""
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["captures"]


@pytest.fixture(scope="module")
def keyfob(captures):
    return rf_frames.analyze(_signed(captures[0]["pulses"]))


def _tx_state(entity_id, state="2026-11-07T08:00:00.000+00:00", **attributes):
    attributes.setdefault("device_class", "transmitter")
    attributes.setdefault("friendly_name", entity_id.split(".", 1)[1])
    return types.SimpleNamespace(entity_id=entity_id, state=state, attributes=attributes)


@pytest.fixture
def radio(monkeypatch, fake_hass):
    """Core's radio send and ``OOKCommand``, recorded; the gate reset."""
    tx_gate.reset_for_test()
    platform = types.ModuleType("homeassistant.components.radio_frequency")
    const = types.ModuleType("homeassistant.components.radio_frequency.const")
    const.DATA_COMPONENT = "radio_frequency_component"
    sent: list[tuple[str, object]] = []
    failing: dict[str, Exception] = {}

    async def async_send_command(hass, entity_id, command, context=None):
        if entity_id in failing:
            raise failing[entity_id]
        sent.append((entity_id, command))

    platform.async_send_command = async_send_command
    platform.const = const

    ook = types.ModuleType("rf_protocols.commands.ook")

    class OOKCommand:
        def __init__(self, *, frequency, timings, repeat_count=0, **_):
            self.frequency = frequency
            self.timings = timings
            self.repeat_count = repeat_count

        def get_raw_timings(self):
            return self.timings

    ook.OOKCommand = OOKCommand
    commands = types.ModuleType("rf_protocols.commands")
    commands.ook = ook
    root = types.ModuleType("rf_protocols")
    root.commands = commands
    for module in (platform, const, root, commands, ook):
        monkeypatch.setitem(sys.modules, module.__name__, module)

    fake_hass.data = {const.DATA_COMPONENT: _component(RANGES)}
    states = {e: _tx_state(e) for e in RANGES}
    states[IR_TX] = _tx_state(IR_TX, device_class="emitter")
    fake_hass.states.get = MagicMock(side_effect=lambda e: states.get(e))
    radio = types.SimpleNamespace(sent=sent, failing=failing, states=states)
    yield radio
    tx_gate.reset_for_test()


def _row(frame, **fields):
    defaults = {
        "name": "Button 1 on",
        "raw_timings": list(frame),
        "rf_frequency_hz": 433_920_000,
        "rf_frame_gap_us": None,
        "send_count": 4,
    }
    defaults.update(fields)
    return types.SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# The wire frame (doors section 1)
# ---------------------------------------------------------------------------


class TestWireFrame:
    def test_a_measured_gap_replaces_the_last_space(self):
        row = _row([400, -1200, 1200, -400, 400, -12_881], rf_frame_gap_us=12_881)
        assert rf_send.wire_frame(row) == [400, -1200, 1200, -400, 400, -12_881]

    def test_the_rows_gap_wins_over_the_frames_last_space(self):
        row = _row([400, -1200, 400, -6_000], rf_frame_gap_us=10_850)
        assert rf_send.wire_frame(row) == [400, -1200, 400, -10_850]

    def test_a_frame_ending_on_a_mark_gets_the_gap_appended(self):
        row = _row([400, -1200, 400], rf_frame_gap_us=10_850)
        assert rf_send.wire_frame(row) == [400, -1200, 400, -10_850]

    def test_no_gap_is_the_assumed_one(self):
        row = _row([400, -1200, 400])
        assert rf_send.wire_frame(row)[-1] == -RF_ASSUMED_FRAME_GAP_US

    def test_the_row_is_not_changed(self):
        frame = [400, -1200, 400, -6_000]
        row = _row(frame, rf_frame_gap_us=10_850)
        rf_send.wire_frame(row)
        assert row.raw_timings == frame


# ---------------------------------------------------------------------------
# The frequency (plan 5.7, doors section 3)
# ---------------------------------------------------------------------------


class TestFrequency:
    def test_a_range_that_holds_the_carrier_sends_it(self):
        fit = rf_send.choose_frequency(433_840_000, RANGES[RM4_TX])
        assert (fit.ok, fit.send_hz, fit.substituted, fit.code) == (
            True, 433_840_000, False, None
        )

    def test_a_fixed_transmitter_sends_its_own_value_nearby(self):
        fit = rf_send.choose_frequency(433_840_000, RANGES[ATHOM_TX])
        assert (fit.ok, fit.send_hz, fit.substituted) == (True, 433_920_000, True)

    def test_the_exact_value_on_a_fixed_transmitter_is_not_a_substitution(self):
        fit = rf_send.choose_frequency(433_920_000, RANGES[ATHOM_TX])
        assert (fit.ok, fit.send_hz, fit.substituted) == (True, 433_920_000, False)

    def test_the_tolerance_is_400_khz(self):
        assert rf_send.choose_frequency(433_520_000, RANGES[ATHOM_TX]).ok
        # Somfy's 433.42 is 500 kHz away: a different band, refused.
        far = rf_send.choose_frequency(433_420_000, RANGES[ATHOM_TX])
        assert (far.ok, far.code) == (False, "rf_frequency_unsupported")

    def test_315_is_refused_by_a_433_only_transmitter(self):
        fit = rf_send.choose_frequency(315_000_000, RANGES[ATHOM_TX])
        assert (fit.ok, fit.code) == (False, "rf_frequency_unsupported")
        assert rf_send.choose_frequency(315_000_000, RANGES[RM4_TX]).ok

    def test_a_wide_range_does_not_substitute(self):
        fit = rf_send.choose_frequency(303_875_000, RANGES[CC1101_TX])
        assert (fit.ok, fit.send_hz, fit.substituted) == (True, 303_875_000, False)

    def test_a_transmitter_that_declares_nothing(self):
        assert rf_send.choose_frequency(433_920_000, [(0, 0)]).code == "no_ranges"
        assert rf_send.choose_frequency(433_920_000, []).code == "no_ranges"
        assert rf_send.choose_frequency(433_920_000, None).code == "no_ranges"

    def test_a_row_with_no_frequency(self):
        assert rf_send.choose_frequency(None, RANGES[RM4_TX]).code == "rf_no_frequency"

    def test_the_hass_wrappers(self, radio, fake_hass):
        assert rf_send.transmitter_ranges(fake_hass, ATHOM_TX) == RANGES[ATHOM_TX]
        assert rf_send.transmitter_ranges(fake_hass, "radio_frequency.gone") == []
        fit = rf_send.transmitter_fit(fake_hass, ATHOM_TX, 433_840_000)
        assert (fit.ok, fit.substituted) == (True, True)
        fake_hass.data = {}
        assert rf_send.transmitter_ranges(fake_hass, ATHOM_TX) is None


# ---------------------------------------------------------------------------
# The count
# ---------------------------------------------------------------------------


class TestCount:
    def test_the_seed_is_what_one_press_carried(self):
        assert rf_send.seed_send_count(8) == 8
        assert rf_send.seed_send_count(1) == 2
        assert rf_send.seed_send_count(40) == MAX_SEND_COUNT
        assert rf_send.seed_send_count(None) == RF_DEFAULT_SEND_COUNT

    def test_the_count_is_clamped(self):
        frame = [400, -1200] * 24 + [400, -12_000]
        assert rf_send.send_count_for(_row(frame, send_count=50), frame) == MAX_SEND_COUNT
        assert rf_send.send_count_for(_row(frame, send_count=0), frame) == 1

    def test_the_air_time_cap_holds_a_long_frame(self):
        frame = [10_000, -10_000] * 40  # 800 ms a frame
        assert rf_send.send_count_for(_row(frame, send_count=10), frame) == 3

    def test_assign_seeds_a_radio_rows_count(self, keyfob):
        from custom_components.hair.signal_monitor import _apply_signal_provenance

        signal = _rf_signal(keyfob, rf_repeats_observed=8)
        command = IRCommand(name="b", raw_timings=list(keyfob.frame))
        _apply_signal_provenance(command, signal)
        assert command.send_count == 8
        # A count the caller passes wins, as for infrared.
        command = IRCommand(name="b", raw_timings=list(keyfob.frame))
        _apply_signal_provenance(command, signal, send_count=3)
        assert command.send_count == 3
        # A count somebody set on the row is kept.
        signal.send_count = 5
        command = IRCommand(name="b", raw_timings=list(keyfob.frame))
        _apply_signal_provenance(command, signal)
        assert command.send_count == 5


# ---------------------------------------------------------------------------
# The device send: dispatch by medium (doors section 2)
# ---------------------------------------------------------------------------


def _radio_command(frame, **fields) -> IRCommand:
    command = IRCommand(
        id="c1", name="Button 1 on", category=CommandCategory.CUSTOM,
        source=CommandSource.CAPTURED, protocol=RF_PROTOCOL, code=None,
        raw_timings=list(frame),
    )
    command.medium = MEDIUM_RF
    command.rf_frequency_hz = fields.pop("rf_frequency_hz", 433_920_000)
    command.rf_frame_gap_us = fields.pop("rf_frame_gap_us", 12_881)
    command.send_count = fields.pop("send_count", 4)
    for name, value in fields.items():
        setattr(command, name, value)
    return command


def _ir_command() -> IRCommand:
    return IRCommand(
        id="c2", name="Power", category=CommandCategory.POWER,
        source=CommandSource.CAPTURED, protocol="PRONTO",
        code="0000 006D 0002 0000 0020 0040 0020 0040",
    )


@pytest.fixture
def manager(fake_hass):
    from custom_components.hair.device_manager import DeviceManager
    from custom_components.hair.entity_factory import EntityFactory
    from custom_components.hair.storage import HAIRStore
    from custom_components.hair.tests.test_device_manager import _FakeStore

    with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
        store = HAIRStore(fake_hass)
        store._loaded = True
        factory = EntityFactory(fake_hass)
        with patch(
            "custom_components.hair.device_manager.dr.async_get",
            return_value=MagicMock(
                async_get_or_create=MagicMock(return_value=MagicMock(id="ha")),
                async_get_device=MagicMock(return_value=None),
                async_remove_device=MagicMock(),
            ),
        ):
            manager = DeviceManager(fake_hass, store, factory, "entry-1")
            manager._signal_monitor = MagicMock(return_value=None)
            yield manager


def _device(emitters, *commands) -> IRDevice:
    return IRDevice(
        id="dev1", name="Plug", device_type="custom",
        emitter_entity_ids=list(emitters), commands=list(commands),
    )


class TestDeviceSend:
    @pytest.mark.asyncio
    async def test_a_radio_command_goes_only_to_radio_transmitters(
        self, manager, radio, keyfob
    ):
        command = _radio_command(keyfob.frame)
        manager._store.get_device = MagicMock(
            return_value=_device([IR_TX, ATHOM_TX, RM4_TX], command)
        )
        ir_send = AsyncMock()
        infrared = types.SimpleNamespace(async_send_command=ir_send)
        with patch.dict(sys.modules, {"homeassistant.components.infrared": infrared}):
            await manager.async_send_command("dev1", "c1")
        ir_send.assert_not_called()
        assert [e for e, _ in radio.sent] == [ATHOM_TX, RM4_TX]
        for _entity_id, cmd in radio.sent:
            assert cmd.frequency == 433_920_000
            assert cmd.repeat_count == 3  # send_count 4: the first plus three
            assert cmd.timings == rf_send.wire_frame(command)

    @pytest.mark.asyncio
    async def test_an_infrared_command_never_reaches_a_transmitter(
        self, manager, radio, keyfob
    ):
        manager._store.get_device = MagicMock(
            return_value=_device([IR_TX, ATHOM_TX], _ir_command())
        )
        reached: list[str] = []

        async def ir_send(hass, entity_id, command):
            reached.append(entity_id)

        infrared = types.ModuleType("homeassistant.components.infrared")
        infrared.async_send_command = ir_send
        with patch.dict(sys.modules, {"homeassistant.components.infrared": infrared}):
            await manager.async_send_command("dev1", "c2")
        assert reached == [IR_TX]
        assert radio.sent == []

    @pytest.mark.asyncio
    async def test_a_mixed_device_sends_each_command_to_its_own_kind(
        self, manager, radio, keyfob
    ):
        device = _device([IR_TX, ATHOM_TX], _radio_command(keyfob.frame), _ir_command())
        manager._store.get_device = MagicMock(return_value=device)
        reached: list[str] = []

        async def ir_send(hass, entity_id, command):
            reached.append(entity_id)

        infrared = types.ModuleType("homeassistant.components.infrared")
        infrared.async_send_command = ir_send
        with patch.dict(sys.modules, {"homeassistant.components.infrared": infrared}):
            await manager.async_send_command("dev1", "c1")
            await manager.async_send_command("dev1", "c2")
        assert [e for e, _ in radio.sent] == [ATHOM_TX]
        assert reached == [IR_TX]

    @pytest.mark.asyncio
    async def test_no_emitter_of_the_medium(self, manager, radio, keyfob):
        from custom_components.hair.device_manager import SendRefusedError

        manager._store.get_device = MagicMock(
            return_value=_device([ATHOM_TX], _ir_command())
        )
        with pytest.raises(SendRefusedError) as caught:
            await manager.async_send_command("dev1", "c2")
        assert caught.value.code == "no_emitter_for_medium"
        assert radio.sent == []

    @pytest.mark.asyncio
    async def test_a_315_row_refused_by_a_433_only_transmitter(
        self, manager, radio, keyfob
    ):
        from custom_components.hair.device_manager import SendRefusedError

        command = _radio_command(keyfob.frame, rf_frequency_hz=315_000_000)
        manager._store.get_device = MagicMock(return_value=_device([ATHOM_TX], command))
        with pytest.raises(SendRefusedError) as caught:
            await manager.async_send_command("dev1", "c1")
        assert caught.value.code == "rf_frequency_unsupported"
        assert "315" in str(caught.value)
        assert radio.sent == []

    @pytest.mark.asyncio
    async def test_the_315_row_goes_out_where_it_fits(self, manager, radio, keyfob):
        command = _radio_command(keyfob.frame, rf_frequency_hz=315_000_000)
        manager._store.get_device = MagicMock(
            return_value=_device([ATHOM_TX, RM4_TX], command)
        )
        await manager.async_send_command("dev1", "c1")
        assert [(e, c.frequency) for e, c in radio.sent] == [(RM4_TX, 315_000_000)]

    @pytest.mark.asyncio
    async def test_a_measured_carrier_is_substituted_on_a_fixed_transmitter(
        self, manager, radio, keyfob
    ):
        command = _radio_command(keyfob.frame, rf_frequency_hz=433_840_000)
        manager._store.get_device = MagicMock(
            return_value=_device([ATHOM_TX, RM4_TX], command)
        )
        await manager.async_send_command("dev1", "c1")
        assert [(e, c.frequency) for e, c in radio.sent] == [
            (ATHOM_TX, 433_920_000), (RM4_TX, 433_840_000),
        ]

    @pytest.mark.asyncio
    async def test_no_frequency_is_refused_and_says_where_to_set_it(
        self, manager, radio, keyfob
    ):
        from custom_components.hair.device_manager import SendRefusedError

        command = _radio_command(keyfob.frame, rf_frequency_hz=None)
        manager._store.get_device = MagicMock(return_value=_device([ATHOM_TX], command))
        with pytest.raises(SendRefusedError) as caught:
            await manager.async_send_command("dev1", "c1")
        assert caught.value.code == "rf_no_frequency"
        assert "editor" in str(caught.value)

    @pytest.mark.asyncio
    async def test_radio_not_loaded(self, manager, radio, keyfob, fake_hass):
        from custom_components.hair.device_manager import SendRefusedError

        fake_hass.data = {}
        manager._store.get_device = MagicMock(
            return_value=_device([ATHOM_TX], _radio_command(keyfob.frame))
        )
        with pytest.raises(SendRefusedError) as caught:
            await manager.async_send_command("dev1", "c1")
        assert caught.value.code == "rf_platform_not_loaded"

    @pytest.mark.asyncio
    async def test_a_transmitter_that_declares_nothing_is_skipped(
        self, manager, radio, keyfob
    ):
        from custom_components.hair.device_manager import SendRefusedError

        manager._store.get_device = MagicMock(
            return_value=_device([BARE_TX], _radio_command(keyfob.frame))
        )
        with pytest.raises(SendRefusedError) as caught:
            await manager.async_send_command("dev1", "c1")
        assert caught.value.code == "rf_frequency_unsupported"
        manager._store.get_device = MagicMock(
            return_value=_device([BARE_TX, ATHOM_TX], _radio_command(keyfob.frame))
        )
        await manager.async_send_command("dev1", "c1")
        assert [e for e, _ in radio.sent] == [ATHOM_TX]

    @pytest.mark.asyncio
    async def test_unavailable_and_failing_transmitters(
        self, manager, radio, keyfob
    ):
        radio.states[ATHOM_TX] = _tx_state(ATHOM_TX, state="unavailable")
        radio.failing[CC1101_TX] = OSError("no route")
        manager._store.get_device = MagicMock(
            return_value=_device([ATHOM_TX, CC1101_TX, RM4_TX], _radio_command(keyfob.frame))
        )
        notify = MagicMock()
        manager._notify_emitter_degraded = notify
        landed = await manager._async_broadcast_rf(
            manager._store.get_device("dev1"),
            manager._store.get_device("dev1").commands[0], "Button 1 on",
        )
        assert landed == {RM4_TX}
        problems = notify.call_args.args[1]
        assert set(problems) == {ATHOM_TX, CC1101_TX}
        assert notify.call_args.kwargs["medium"] == "rf"

    @pytest.mark.asyncio
    async def test_all_unavailable_is_todays_message(self, manager, radio, keyfob):
        radio.states[ATHOM_TX] = _tx_state(ATHOM_TX, state="unavailable")
        manager._store.get_device = MagicMock(
            return_value=_device([ATHOM_TX], _radio_command(keyfob.frame))
        )
        with pytest.raises(RuntimeError, match="unavailable"):
            await manager.async_send_command("dev1", "c1")
        assert radio.sent == []

    @pytest.mark.asyncio
    async def test_a_platform_that_does_not_repeat_is_looped(
        self, manager, radio, keyfob, monkeypatch
    ):
        monkeypatch.setitem(rf_send.NATIVE_REPEAT, "broadlink", False)
        monkeypatch.setattr(
            "custom_components.hair.send_plan.emitter_platform",
            lambda hass, entity_id: "broadlink" if entity_id == RM4_TX else "esphome",
        )
        manager._store.get_device = MagicMock(
            return_value=_device([ATHOM_TX, RM4_TX], _radio_command(keyfob.frame, send_count=3))
        )
        await manager.async_send_command("dev1", "c1")
        assert [(e, c.repeat_count) for e, c in radio.sent] == [
            (ATHOM_TX, 2), (RM4_TX, 0), (RM4_TX, 0), (RM4_TX, 0),
        ]

    @pytest.mark.asyncio
    async def test_the_entities_hear_about_a_landed_send(self, manager, radio, keyfob):
        manager._store.get_device = MagicMock(
            return_value=_device([ATHOM_TX], _radio_command(keyfob.frame))
        )
        with patch(
            "custom_components.hair.device_manager.async_dispatcher_send"
        ) as dispatch:
            await manager.async_send_command("dev1", "c1")
        assert dispatch.called


# ---------------------------------------------------------------------------
# The gate: one per medium
# ---------------------------------------------------------------------------


class TestGate:
    @pytest.mark.asyncio
    async def test_a_radio_send_does_not_wait_on_an_infrared_burst(self, monkeypatch):
        tx_gate.reset_for_test()
        slept: list[float] = []

        async def sleep(seconds):
            slept.append(seconds)

        monkeypatch.setattr(tx_gate.asyncio, "sleep", sleep)
        send = AsyncMock()
        await tx_gate.gated_send(None, IR_TX, "ir", send, air_s=2.0)
        await tx_gate.gated_send(None, ATHOM_TX, "rf", send, medium="rf")
        assert slept == []
        # Within a medium the stagger holds as before.
        await tx_gate.gated_send(None, RM4_TX, "rf", send, medium="rf")
        assert len(slept) == 1 and slept[0] > 0
        tx_gate.reset_for_test()


# ---------------------------------------------------------------------------
# The Sniffer's Test (doors section 2, addendum a)
# ---------------------------------------------------------------------------


class TestTest:
    def _store_row(self, store, keyfob, **overrides):
        store.add_device(UnknownDevice(
            id="d", fingerprint=keyfob.device_key, source="sniffed",
            medium=MEDIUM_RF, signals=[_rf_signal(keyfob, **overrides)],
        ))

    @pytest.mark.asyncio
    async def test_a_radio_row_is_sent_and_says_at_what(self, fake_hass, radio, keyfob):
        monitor, store = _monitor(fake_hass)
        self._store_row(store, keyfob, rf_frequency_hz=433_840_000, send_count=3)
        result = await monitor.test_signal("rf1", ATHOM_TX)
        assert result == {
            "success": True, "sent": True,
            "frequency_hz": 433_920_000, "substituted": True,
        }
        (entity_id, command), = radio.sent
        assert entity_id == ATHOM_TX and command.repeat_count == 2

    @pytest.mark.asyncio
    async def test_the_refusals(self, fake_hass, radio, keyfob):
        monitor, store = _monitor(fake_hass)
        self._store_row(store, keyfob, rf_frequency_hz=None)
        assert (await monitor.test_signal("rf1", ATHOM_TX))["code"] == "rf_no_frequency"
        assert (await monitor.test_signal("rf1", IR_TX))["code"] == "emitter_wrong_medium"
        store.get_all_devices()[0].signals[0].rf_frequency_hz = 315_000_000
        result = await monitor.test_signal("rf1", ATHOM_TX)
        assert result["code"] == "rf_frequency_unsupported"
        assert radio.sent == []

    @pytest.mark.asyncio
    async def test_a_failing_transmitter(self, fake_hass, radio, keyfob):
        monitor, store = _monitor(fake_hass)
        self._store_row(store, keyfob)
        radio.failing[ATHOM_TX] = OSError("gone")
        result = await monitor.test_signal("rf1", ATHOM_TX)
        assert (result["success"], result["code"]) == (False, "send_failed")


# ---------------------------------------------------------------------------
# The echo and the Mirror (plan 5.10, doors section 6, addendum d)
# ---------------------------------------------------------------------------


def _plan(row, *transmitters, on_air=433_920_000):
    timings = rf_send.wire_frame(row)
    count = rf_send.send_count_for(row, timings)
    plan = rf_send.RadioSend(
        timings=timings, count=count, air_s=rf_send.burst_air_s(timings, count)
    )
    for entity_id in transmitters:
        plan.attempted.append(entity_id)
        plan.fits[entity_id] = rf_send.TransmitterFit(
            True, on_air, on_air != row.rf_frequency_hz, None
        )
    return plan


class TestEcho:
    async def _hear(self, fake_hass, monitor, timings_list, receiver=ATHOM_RX):
        """Captures through the receive path, one per entry, a frame apart."""
        tasks = []
        fake_hass.async_create_task = MagicMock(side_effect=tasks.append)
        fake_hass.bus = MagicMock()
        for timings in timings_list:
            signal = types.SimpleNamespace(timings=list(timings), frequency=None, modulation="ook")
            monitor._on_rf_signal(signal, receiver)
            while tasks:
                await tasks.pop(0)

    def _armed_send(self, fake_hass, monitor, row, *transmitters):
        fake_hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())
        plan = _plan(row, *transmitters)
        monitor.record_send_rf(row, plan, "Plug / Button 1 on")
        ticket = monitor._echo_expectations[-1]
        monitor._arm_expectation(ticket, ticket.get("armed_at") or 0.0)
        ticket["armed_at"] = 0.0
        ticket["expires"] = float("inf")
        return plan, ticket

    @pytest.mark.asyncio
    async def test_the_ticket_holds_the_receive_paths_identity(
        self, fake_hass, keyfob
    ):
        monitor, _ = _monitor(fake_hass)
        fake_hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())
        row = _radio_command(keyfob.frame)
        monitor.record_send_rf(row, _plan(row, ATHOM_TX), "Plug / Button 1 on")
        ticket = monitor._echo_expectations[-1]
        assert ticket["medium"] == MEDIUM_RF
        assert ticket["sig_fp"] == keyfob.fingerprint
        assert ticket["sl"] is None and ticket["norm_fp"] is None
        assert ticket["claim_budget"] == 1

    @pytest.mark.asyncio
    async def test_hairs_own_send_is_claimed_and_goes_nowhere_else(
        self, fake_hass, keyfob, captures
    ):
        """The negative the PR quotes: a Mirror heard_by, no Sniffer row,
        no trigger, no hair_receiver_heard (addendum d section 1)."""
        monitor, store = _monitor(fake_hass)
        row = _radio_command(keyfob.frame)
        self._armed_send(fake_hass, monitor, row, ATHOM_TX)
        marked = []

        async def mark(row_key, receiver):
            marked.append((row_key, receiver))

        monitor._mirror_mark_heard = mark
        triggers = MagicMock()
        monitor._trigger_manager = triggers
        fired = []
        with patch.object(monitor, "_note_heard", side_effect=fired.append):
            # The keyfob's own press capture: the same frames HAIR sent.
            await self._hear(fake_hass, monitor, [_signed(captures[0]["pulses"])])
        assert marked == [(keyfob.fingerprint, ATHOM_RX)]
        assert store.get_all_devices() == []
        assert fired == []
        assert not triggers.on_signal_captured.called

    @pytest.mark.asyncio
    async def test_another_code_inside_the_window_is_a_press(
        self, fake_hass, keyfob, captures
    ):
        """'On' sent, 'off' pressed straight after: never swallowed."""
        monitor, store = _monitor(fake_hass)
        other = next(
            c for c in captures[1:]
            if rf_frames.analyze(_signed(c["pulses"])).fingerprint != keyfob.fingerprint
        )
        self._armed_send(fake_hass, monitor, _radio_command(keyfob.frame), ATHOM_TX)
        with patch.object(monitor, "_mirror_mark_heard", AsyncMock()) as mark:
            await self._hear(fake_hass, monitor, [_signed(other["pulses"])])
        mark.assert_not_called()
        assert len(store.get_all_devices()) == 1

    @pytest.mark.asyncio
    async def test_an_infrared_ticket_never_claims_a_radio_capture(
        self, fake_hass, keyfob, captures
    ):
        monitor, store = _monitor(fake_hass)
        _, ticket = self._armed_send(fake_hass, monitor, _radio_command(keyfob.frame), ATHOM_TX)
        ticket["medium"] = "ir"  # the same identity, the other medium
        await self._hear(fake_hass, monitor, [_signed(captures[0]["pulses"])])
        assert len(store.get_all_devices()) == 1

    @pytest.mark.asyncio
    async def test_a_radio_ticket_never_claims_an_infrared_capture(self, fake_hass, keyfob):
        from custom_components.hair.signal_monitor import NormalizedSignal

        monitor, _ = _monitor(fake_hass)
        _, ticket = self._armed_send(fake_hass, monitor, _radio_command(keyfob.frame), ATHOM_TX)
        infrared = NormalizedSignal(
            protocol="PRONTO", code=None, raw_timings=[], frequency=38_000,
            sig_fp=ticket["sig_fp"], device_address=None, dev_fp="x",
            byte_hash=None, decoded_protocol=None, decoded_address=None,
            decoded_command=None, decoded_fingerprint=None, decoded_extras=None,
        )
        assert await monitor._match_echo(infrared, "infrared.rx") is None

    @pytest.mark.asyncio
    async def test_the_budget_is_one_burst_per_receiver(
        self, fake_hass, keyfob, captures
    ):
        monitor, store = _monitor(fake_hass)
        _, ticket = self._armed_send(fake_hass, monitor, _radio_command(keyfob.frame), ATHOM_TX)
        ticket["guard_until"] = 0.0
        with patch.object(monitor, "_mirror_mark_heard", AsyncMock()):
            frames = _signed(captures[0]["pulses"])
            await self._hear(fake_hass, monitor, [frames], receiver=ATHOM_RX)
            await self._hear(
                fake_hass, monitor, [frames], receiver="radio_frequency.rm4_pro_receiver"
            )
            assert store.get_all_devices() == []
            # A third hearing on the first receiver is a press again.
            await self._hear(fake_hass, monitor, [frames], receiver=ATHOM_RX)
        assert len(store.get_all_devices()) == 1

    @pytest.mark.asyncio
    async def test_the_mirror_row_carries_the_radio_fields(self, fake_hass, keyfob):
        monitor, store = _monitor(fake_hass)
        fake_hass.bus = MagicMock()
        row = _radio_command(keyfob.frame, rf_frequency_hz=433_840_000)
        plan = _plan(row, ATHOM_TX, on_air=433_920_000)
        upserts = []
        fake_hass.async_create_task = MagicMock(side_effect=upserts.append)
        monitor._friendly_name = lambda e: "Athom RF transmitter"
        monitor.record_send_rf(row, plan, "Plug / Button 1 on")
        for coro in upserts:
            await coro
        mirror = next(d for d in store.get_all_devices() if d.source == "echo")
        signal = mirror.signals[0]
        assert signal.medium == MEDIUM_RF
        assert signal.rf_frequency_hz == 433_920_000  # what went on the air
        assert signal.fingerprint == keyfob.fingerprint
        assert signal.echo_source == "Plug / Button 1 on -- via Athom RF transmitter"
        assert signal.send_count == plan.count

    def test_a_radio_transmitter_beacon_arms_its_ticket(self, fake_hass, keyfob):
        monitor, _ = _monitor(fake_hass)
        fake_hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())
        row = _radio_command(keyfob.frame)
        monitor.record_send_rf(row, _plan(row, ATHOM_TX), "Plug / Button 1 on")
        ticket = monitor._echo_expectations[-1]
        assert ticket["armed_at"] is None
        old = _tx_state(ATHOM_TX, state="2026-11-07T08:00:00.000+00:00")
        new = _tx_state(ATHOM_TX, state="2026-11-07T08:00:01.000+00:00")
        monitor._on_emitter_beacon(types.SimpleNamespace(
            data={"entity_id": ATHOM_TX, "old_state": old, "new_state": new},
            context=None,
        ))
        assert ticket["armed_at"] is not None

    def test_a_foreign_radio_send_waits_for_a_radio_echo(self, fake_hass):
        monitor, _ = _monitor(fake_hass)
        old = _tx_state(ATHOM_TX, state="2026-11-07T08:00:00.000+00:00")
        new = _tx_state(ATHOM_TX, state="2026-11-07T08:00:01.000+00:00")
        monitor._on_emitter_beacon(types.SimpleNamespace(
            data={"entity_id": ATHOM_TX, "old_state": old, "new_state": new},
            context=None,
        ))
        assert monitor._foreign_pending[ATHOM_TX]["medium"] == MEDIUM_RF

    @pytest.mark.asyncio
    async def test_a_foreign_infrared_send_does_not_claim_a_radio_press(
        self, fake_hass, captures
    ):
        monitor, store = _monitor(fake_hass)
        old = _tx_state(IR_TX, state="2026-11-07T08:00:00.000+00:00", device_class="emitter")
        new = _tx_state(IR_TX, state="2026-11-07T08:00:01.000+00:00", device_class="emitter")
        monitor._on_emitter_beacon(types.SimpleNamespace(
            data={"entity_id": IR_TX, "old_state": old, "new_state": new},
            context=None,
        ))
        assert IR_TX in monitor._foreign_pending
        await self._hear(fake_hass, monitor, [_signed(captures[0]["pulses"])])
        assert len(store.get_all_devices()) == 1
        assert IR_TX in monitor._foreign_pending

    def test_the_receiver_heard_event_name_is_the_doors(self):
        assert EVENT_RECEIVER_HEARD == "hair_receiver_heard"
