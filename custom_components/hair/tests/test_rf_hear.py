"""RF hear, round 1: radio rows on the models, hearing, and the refusals.

The core ``radio_frequency`` platform is stubbed per test (``rf_platform``
below) rather than in the root conftest, so every other test keeps
seeing what a core below 2026.11 shows HAIR: no platform at all.
"""
from __future__ import annotations

import json
import sys
import types
from enum import StrEnum
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair import rf_frames, rf_receive
from custom_components.hair.const import (
    MEDIUM_RF,
    RF_FREQUENCY_SOURCE_RECEIVER,
    RF_FREQUENCY_SOURCE_SIGNAL,
    RF_FREQUENCY_SOURCE_WINDOW,
    RF_PROTOCOL,
    RF_SEND_UNSUPPORTED,
)
from custom_components.hair.models import (
    RF_ROW_FIELDS,
    CaptureResult,
    CommandCategory,
    CommandSource,
    IRCommand,
    IRDevice,
    IRTrigger,
    UnknownDevice,
    UnknownSignal,
    band_mhz,
)
from custom_components.hair.signal_monitor import SignalMonitor, normalize
from custom_components.hair.signal_store import SignalStore

FIXTURE = Path(__file__).parent / "fixtures" / "rf" / "it104-keyfob-433.json"
RECEIVER = "radio_frequency.rm4_pro_receiver"
ALWAYS_ON = "radio_frequency.always_on_receiver"


def _signed(edges):
    return [abs(v) if i % 2 == 0 else -abs(v) for i, v in enumerate(edges)]


@pytest.fixture(scope="module")
def captures():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["captures"]


@pytest.fixture(scope="module")
def keyfob(captures):
    return rf_frames.analyze(_signed(captures[0]["pulses"]))


def _rf_signal(analysis, **overrides) -> UnknownSignal:
    fields = {
        "id": "rf1",
        "fingerprint": analysis.fingerprint,
        "byte_hash": analysis.frame_hash,
        "protocol": RF_PROTOCOL,
        "code": None,
        "raw_timings": list(analysis.frame),
        "medium": MEDIUM_RF,
        "rf_frequency_hz": 433_920_000,
        "rf_frequency_source": RF_FREQUENCY_SOURCE_WINDOW,
        "rf_modulation": "OOK",
        "rf_frame_hash": analysis.frame_hash,
        "rf_repeats_observed": analysis.votes,
        "rf_frame_gap_us": analysis.gap_us,
        "rf_frame_gap_source": analysis.gap_source,
        "rf_header_shape": analysis.header_shape,
        "rf_short_mark_us": analysis.short_mark_us,
    }
    fields.update(overrides)
    return UnknownSignal(**fields)


def _state(entity_id, state="2026-11-03T20:00:00+00:00", **attributes):
    attributes.setdefault("device_class", "receiver")
    return types.SimpleNamespace(
        entity_id=entity_id, state=state, attributes=attributes
    )


class _Modulation(StrEnum):
    OOK = "ook"


@pytest.fixture
def rf_platform(monkeypatch):
    """A ``radio_frequency`` core platform: component, subscribe, signal."""
    platform = types.ModuleType("homeassistant.components.radio_frequency")
    const = types.ModuleType("homeassistant.components.radio_frequency.const")
    const.DATA_COMPONENT = "radio_frequency_component"
    subscriptions: list[dict] = []

    def async_subscribe_receiver(hass, entity_id, callback):
        record = {"entity_id": entity_id, "callback": callback, "live": True}
        subscriptions.append(record)

        def unsub():
            record["live"] = False

        return unsub

    class RadioFrequencyReceivedSignal:
        def __init__(self, timings, frequency=None, modulation=_Modulation.OOK):
            self.timings = timings
            self.frequency = frequency
            self.modulation = modulation

    platform.async_subscribe_receiver = async_subscribe_receiver
    platform.RadioFrequencyReceivedSignal = RadioFrequencyReceivedSignal
    platform.ModulationType = _Modulation
    platform.const = const
    monkeypatch.setitem(sys.modules, platform.__name__, platform)
    monkeypatch.setitem(sys.modules, const.__name__, const)
    platform.subscriptions = subscriptions
    return platform


def _component(ranges_by_entity: dict[str, list[tuple[int, int]]]):
    def get_entity(entity_id):
        if entity_id not in ranges_by_entity:
            return None
        return types.SimpleNamespace(
            supported_frequency_ranges=ranges_by_entity[entity_id]
        )

    return types.SimpleNamespace(get_entity=get_entity)


# ---------------------------------------------------------------------------
# Item 1: the models
# ---------------------------------------------------------------------------


class TestModels:
    def test_band(self):
        assert band_mhz(433_920_000) == "433.9"
        assert band_mhz(433_420_000) == "433.4"
        assert band_mhz(315_000_000) == "315.0"
        assert band_mhz(None) is None
        assert band_mhz(0) is None

    def test_a_radio_signal_round_trips(self, keyfob):
        signal = _rf_signal(keyfob)
        data = signal.to_dict()
        assert data["medium"] == MEDIUM_RF
        assert data["band"] == "433.9"
        for name in RF_ROW_FIELDS:
            assert data[name] == getattr(signal, name)
        again = UnknownSignal.from_dict(data)
        for name in ("medium", *RF_ROW_FIELDS):
            assert getattr(again, name) == getattr(signal, name)
        assert again.to_dict() == data

    def test_band_does_not_round_trip(self, keyfob):
        data = _rf_signal(keyfob).to_dict()
        data["band"] = "868.3"  # a stale band written by anything
        again = UnknownSignal.from_dict(data)
        assert "band" not in again._extra
        assert again.to_dict()["band"] == "433.9"

    def test_an_infrared_record_carries_no_radio_keys(self):
        signal = UnknownSignal(
            id="ir1", fingerprint="f", protocol="PRONTO",
            code="0000 006D 0002 0000 0020 0040 0020 0040",
        )
        keys = set(signal.to_dict())
        assert not keys & {"medium", "band", *RF_ROW_FIELDS}
        command = IRCommand(
            name="Power", category=CommandCategory.POWER,
            source=CommandSource.CAPTURED, protocol="PRONTO",
            code="0000 006D 0002 0000 0020 0040 0020 0040",
        )
        assert not set(command.to_dict()) & {"medium", "band", *RF_ROW_FIELDS}

    def test_every_radio_key_is_declared(self, keyfob):
        """The known-keys guard (``test_unknown_keys``) for radio records.

        That guard builds default, infrared rows, which write no radio
        key; this writes a radio row of every model and checks each key
        it writes is one its parser declares, so none rides _extra.
        """
        from custom_components.hair.models import (
            _KNOWN_CATALOG_DEVICE,
            _KNOWN_COMMAND,
            _KNOWN_SIGNAL,
            _KNOWN_TRIGGER,
        )

        command = _rf_command(keyfob)
        device = UnknownDevice(
            id="d", fingerprint=keyfob.device_key, source="sniffed",
            medium=MEDIUM_RF, rf_header_shape="h0", rolling_state="none",
        )
        trigger = IRTrigger(signal_fingerprint="f", protocol=RF_PROTOCOL)
        for record, known in (
            (_rf_signal(keyfob).to_dict(), _KNOWN_SIGNAL),
            (command.to_dict(), _KNOWN_COMMAND),
            (device.to_dict(), _KNOWN_CATALOG_DEVICE),
            (trigger.to_dict(), _KNOWN_TRIGGER),
        ):
            assert not set(record) - known, set(record) - known

    def test_the_sl_pattern_comes_from_the_frame(self, keyfob):
        data = _rf_signal(keyfob).to_dict()
        assert data["sl_pattern"] == keyfob.sl_pattern
        assert len(data["sl_pattern"]) == 49

    def test_a_capture_becomes_a_radio_command(self, keyfob):
        parsed = CaptureResult(
            protocol=RF_PROTOCOL, code=None, raw_timings=list(keyfob.frame),
            medium=MEDIUM_RF, rf_frequency_hz=433_920_000,
            rf_frequency_source=RF_FREQUENCY_SOURCE_SIGNAL,
            rf_frame_hash=keyfob.frame_hash, rf_repeats_observed=8,
        )
        command = parsed.to_command("Button 1", CommandCategory.CUSTOM)
        assert command.medium == MEDIUM_RF
        assert command.rf_frame_hash == keyfob.frame_hash
        data = command.to_dict()
        assert data["band"] == "433.9"
        assert IRCommand.from_dict(data).to_dict() == data

    def test_device_and_trigger(self, keyfob):
        device = UnknownDevice(
            id="d", fingerprint=keyfob.device_key, source="sniffed",
            medium=MEDIUM_RF, rf_header_shape="h0", rolling_state="none",
        )
        data = device.to_dict()
        assert (data["medium"], data["rf_header_shape"], data["rolling_state"]) == (
            MEDIUM_RF, "h0", "none"
        )
        assert UnknownDevice.from_dict(data).to_dict() == data
        ir_device = UnknownDevice(id="i", fingerprint="x", source="sniffed")
        assert "medium" not in ir_device.to_dict()

        trigger = IRTrigger(
            signal_fingerprint=keyfob.fingerprint, protocol=RF_PROTOCOL,
        )
        assert trigger.medium == MEDIUM_RF
        assert trigger.to_dict()["medium"] == MEDIUM_RF
        assert IRTrigger.from_dict(trigger.to_dict()).medium == MEDIUM_RF
        infrared = IRTrigger(signal_fingerprint="x", protocol="PRONTO")
        assert "medium" not in infrared.to_dict()


# ---------------------------------------------------------------------------
# Item 2 seams: identity helpers outside rf_frames
# ---------------------------------------------------------------------------


class TestIdentitySeams:
    def test_canonical_fingerprint_reads_a_radio_frame(self, keyfob):
        from custom_components.hair.identity import canonical_fingerprint

        assert canonical_fingerprint(RF_PROTOCOL, None, keyfob.frame) == (
            keyfob.fingerprint
        )

    def test_no_radio_timings_reach_the_infrared_decoders(self, keyfob):
        parsed = CaptureResult(
            protocol=RF_PROTOCOL, code=None, raw_timings=list(keyfob.frame),
            medium=MEDIUM_RF,
        )
        parsed.rf = keyfob
        boom = MagicMock(side_effect=AssertionError("an infrared reader ran"))
        with (
            patch("custom_components.hair.signal_monitor.try_decode_identity", boom),
            patch("custom_components.hair.signal_monitor.norm_fingerprint", boom),
            patch(
                "custom_components.hair.signal_monitor.EventParser.signal_fingerprint",
                boom,
            ),
        ):
            n = normalize(parsed)
        assert n.sig_fp == keyfob.fingerprint
        assert n.byte_hash == keyfob.frame_hash
        assert n.dev_fp == keyfob.device_key
        assert n.decoded_fingerprint is None and n.norm_fp is None
        assert n.code is None

    def test_no_infrared_send_path_for_a_radio_row(self, keyfob):
        from custom_components.hair.send_plan import build_like_send_path

        with pytest.raises(ValueError):
            build_like_send_path(_rf_signal(keyfob))


# ---------------------------------------------------------------------------
# Item 3: hearing
# ---------------------------------------------------------------------------


def _monitor(fake_hass):
    store = SignalStore(fake_hass)
    store._loaded = True
    store.schedule_save = MagicMock()
    store.async_save = AsyncMock()
    hair = MagicMock()
    hair.get_all_devices = MagicMock(return_value=[])
    hair.get_device = MagicMock(return_value=None)
    hair.async_save = AsyncMock()
    hair.match_command = MagicMock(return_value=None)
    return SignalMonitor(fake_hass, store, hair), store


class TestFrequencyLadder:
    def _hass(self, state=None):
        hass = MagicMock()
        hass.data = {}
        hass.states.get = MagicMock(return_value=state)
        return hass

    def test_the_signal_wins(self):
        hass = self._hass(_state(RECEIVER, capture_phase="listening",
                                 frequency_hz=433_920_000))
        signal = types.SimpleNamespace(frequency=315_000_000)
        assert rf_receive.frequency_of(hass, RECEIVER, signal) == (
            315_000_000, RF_FREQUENCY_SOURCE_SIGNAL
        )

    def test_then_the_window_while_listening(self):
        signal = types.SimpleNamespace(frequency=None)
        listening = self._hass(_state(RECEIVER, capture_phase="listening",
                                      frequency_hz=433_920_000))
        assert rf_receive.frequency_of(listening, RECEIVER, signal) == (
            433_920_000, RF_FREQUENCY_SOURCE_WINDOW
        )
        sweeping = self._hass(_state(RECEIVER, capture_phase="sweeping",
                                     frequency_hz=433_920_000))
        assert rf_receive.frequency_of(sweeping, RECEIVER, signal) == (None, None)

    def test_then_a_fixed_receiver(self, rf_platform):
        signal = types.SimpleNamespace(frequency=None)
        hass = self._hass(_state(RECEIVER))
        component = _component({
            RECEIVER: [(433_920_000, 433_920_000)],
            "radio_frequency.wide": [(300_000_000, 928_000_000)],
            "radio_frequency.none": [(0, 0)],
        })
        hass.data[rf_platform.const.DATA_COMPONENT] = component
        assert rf_receive.frequency_of(hass, RECEIVER, signal) == (
            433_920_000, RF_FREQUENCY_SOURCE_RECEIVER
        )
        for other in ("radio_frequency.wide", "radio_frequency.none"):
            assert rf_receive.frequency_of(hass, other, signal) == (None, None)

    def test_without_the_platform(self):
        signal = types.SimpleNamespace(frequency=None)
        assert rf_receive.frequency_of(self._hass(None), RECEIVER, signal) == (
            None, None
        )


class TestHearing:
    async def _hear(self, fake_hass, captures, monitor):
        tasks = []
        fake_hass.async_create_task = MagicMock(side_effect=tasks.append)
        fake_hass.states.get = MagicMock(return_value=_state(
            RECEIVER, capturing=True, capture_phase="listening",
            frequency_hz=433_920_000,
        ))
        for index, capture in enumerate(captures):
            signal = types.SimpleNamespace(
                timings=_signed(capture["pulses"]), frequency=None,
                modulation=_Modulation.OOK,
            )
            with patch(
                "custom_components.hair.signal_monitor.time.time",
                return_value=1_000.0 + 10.0 * index,
            ), patch(
                "custom_components.hair.signal_monitor.time.monotonic",
                return_value=1_000.0 + 10.0 * index,
            ):
                monitor._on_rf_signal(signal, RECEIVER)
                while tasks:
                    await tasks.pop(0)

    @pytest.mark.asyncio
    async def test_the_keyfob_mints_seven_rows_on_one_card(self, fake_hass, captures):
        monitor, store = _monitor(fake_hass)
        await self._hear(fake_hass, captures, monitor)
        devices = store.get_all_devices()
        assert len(devices) == 1
        device = devices[0]
        assert device.medium == MEDIUM_RF
        assert device.rf_header_shape == "h0"
        assert len(device.signals) == 7
        for signal in device.signals:
            assert signal.medium == MEDIUM_RF
            assert signal.protocol == RF_PROTOCOL and signal.code is None
            assert signal.rf_frequency_hz == 433_920_000
            assert signal.rf_frequency_source == RF_FREQUENCY_SOURCE_WINDOW
            assert signal.rf_modulation == "OOK"
            assert signal.rf_repeats_observed in (8, 16)
            assert signal.to_dict()["band"] == "433.9"

    @pytest.mark.asyncio
    async def test_a_capture_with_no_frames_mints_nothing(self, fake_hass):
        monitor, store = _monitor(fake_hass)
        noise = [{"pulses": [300, 9_000] * 10 + [300]}]
        await self._hear(fake_hass, noise, monitor)
        assert store.get_all_devices() == []

    @pytest.mark.asyncio
    async def test_radio_is_never_claimed_as_an_echo(self, fake_hass, captures):
        monitor, store = _monitor(fake_hass)
        monitor._match_echo = AsyncMock(side_effect=AssertionError("echo ran"))
        await self._hear(fake_hass, captures[:2], monitor)
        assert len(store.get_all_devices()) == 1


class TestTracker:
    def _hass(self, states):
        hass = MagicMock()
        hass.data = {}
        hass.states.get = MagicMock(side_effect=lambda eid: states.get(eid))
        hass.states.async_all = MagicMock(
            side_effect=lambda domain=None: list(states.values())
        )
        return hass

    @pytest.fixture(autouse=True)
    def _trackers(self, monkeypatch):
        self.added = []
        self.removed = []
        self.watch = []
        monkeypatch.setattr(
            rf_receive, "async_track_state_added_domain",
            lambda hass, domain, cb: self.added.append(cb) or (lambda: None),
        )
        monkeypatch.setattr(
            rf_receive, "async_track_state_removed_domain",
            lambda hass, domain, cb: self.removed.append(cb) or (lambda: None),
        )
        monkeypatch.setattr(
            rf_receive, "async_track_state_change_event",
            lambda hass, ids, cb: self.watch.append((list(ids), cb)) or (lambda: None),
        )

    def _live(self, platform):
        return sorted(s["entity_id"] for s in platform.subscriptions if s["live"])

    def test_a_capture_device_and_an_always_on_one_are_both_subscribed(
        self, rf_platform
    ):
        states = {
            RECEIVER: _state(RECEIVER, capturing=False),
            ALWAYS_ON: _state(ALWAYS_ON),
        }
        heard = []
        tracker = rf_receive.RfReceiverTracker(
            self._hass(states), lambda signal, rid: heard.append((signal, rid))
        )
        tracker.async_start()
        assert tracker.subscribed == sorted([ALWAYS_ON, RECEIVER])
        assert self._live(rf_platform) == sorted([ALWAYS_ON, RECEIVER])
        # Each subscription hands captures to the monitor with its receiver.
        for sub in rf_platform.subscriptions:
            sub["callback"]("sig")
        assert sorted(heard) == [("sig", ALWAYS_ON), ("sig", RECEIVER)]

    def test_it_survives_a_reload(self, rf_platform):
        states = {RECEIVER: _state(RECEIVER, capturing=False)}
        tracker = rf_receive.RfReceiverTracker(self._hass(states), lambda *a: None)
        tracker.async_start()
        _, on_state = self.watch[-1]
        # Unavailable across the reload: released.
        down = _state(RECEIVER, state="unavailable", capturing=False)
        states[RECEIVER] = down
        on_state(types.SimpleNamespace(data={"entity_id": RECEIVER, "new_state": down}))
        assert tracker.subscribed == []
        # Back: a fresh subscription on the new entity object.
        up = _state(RECEIVER, capturing=False)
        states[RECEIVER] = up
        on_state(types.SimpleNamespace(data={"entity_id": RECEIVER, "new_state": up}))
        assert tracker.subscribed == [RECEIVER]
        assert len(rf_platform.subscriptions) == 2
        assert [s["live"] for s in rf_platform.subscriptions] == [False, True]

    def test_it_follows_a_rename(self, rf_platform):
        renamed = "radio_frequency.garage_receiver"
        states = {RECEIVER: _state(RECEIVER, capturing=False)}
        tracker = rf_receive.RfReceiverTracker(self._hass(states), lambda *a: None)
        tracker.async_start()
        del states[RECEIVER]
        self.removed[0](types.SimpleNamespace(data={"entity_id": RECEIVER}))
        states[renamed] = _state(renamed, capturing=False)
        self.added[0](types.SimpleNamespace(data={"entity_id": renamed}))
        assert tracker.subscribed == [renamed]
        assert self._live(rf_platform) == [renamed]

    def test_stop_releases_everything(self, rf_platform):
        states = {RECEIVER: _state(RECEIVER, capturing=False)}
        tracker = rf_receive.RfReceiverTracker(self._hass(states), lambda *a: None)
        tracker.async_start()
        tracker.async_stop()
        assert tracker.subscribed == []
        assert self._live(rf_platform) == []

    def test_without_the_platform_nothing_subscribes(self):
        states = {RECEIVER: _state(RECEIVER, capturing=False)}
        tracker = rf_receive.RfReceiverTracker(self._hass(states), lambda *a: None)
        tracker.async_start()
        assert tracker.subscribed == []


# ---------------------------------------------------------------------------
# The refusals
# ---------------------------------------------------------------------------


class TestRefusals:
    @pytest.mark.asyncio
    async def test_the_catalog_test_send_is_refused(self, fake_hass, keyfob):
        monitor, store = _monitor(fake_hass)
        store.add_device(UnknownDevice(
            id="d", fingerprint=keyfob.device_key, source="sniffed",
            medium=MEDIUM_RF, signals=[_rf_signal(keyfob)],
        ))
        fake_hass.states.get = MagicMock(return_value=_state("infrared.tx"))
        result = await monitor.test_signal("rf1", "infrared.tx")
        assert result["success"] is False
        assert result["code"] == RF_SEND_UNSUPPORTED

    @pytest.mark.asyncio
    async def test_a_pronto_edit_is_refused(self, fake_hass, keyfob):
        monitor, store = _monitor(fake_hass)
        store.add_device(UnknownDevice(
            id="d", fingerprint=keyfob.device_key, source="sniffed",
            medium=MEDIUM_RF, signals=[_rf_signal(keyfob)],
        ))
        result = await monitor.edit_signal_pronto(
            "d", "rf1", "0000 006D 0002 0000 0020 0040 0020 0040"
        )
        assert result["success"] is False
        # rf_edit_unsupported until the RF send round, which edits a
        # radio row as a radio code and refuses Pronto as the other
        # medium's code (rf-send-doors.md section 5).
        assert result["code"] == "wrong_medium_code"


def _rf_command(keyfob) -> IRCommand:
    command = IRCommand(
        id="c1", name="Button 1", category=CommandCategory.CUSTOM,
        source=CommandSource.CAPTURED, protocol=RF_PROTOCOL, code=None,
        raw_timings=list(keyfob.frame),
    )
    command.medium = MEDIUM_RF
    command.rf_frequency_hz = 433_920_000
    return command


class TestDeviceSend:
    @pytest.fixture
    def manager(self, fake_hass):
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
                yield DeviceManager(fake_hass, store, factory, "entry-1")

    def _device(self, keyfob) -> IRDevice:
        return IRDevice(
            id="dev1", name="Keyfob", device_type="custom",
            emitter_entity_ids=["infrared.tx"], commands=[_rf_command(keyfob)],
        )

    @pytest.mark.asyncio
    async def test_a_radio_command_is_refused_before_any_emitter(
        self, manager, keyfob
    ):
        from custom_components.hair.device_manager import RfSendUnsupportedError

        manager._store.get_device = MagicMock(return_value=self._device(keyfob))
        with pytest.raises(RfSendUnsupportedError) as caught:
            await manager.async_send_command("dev1", "c1")
        assert caught.value.code == RF_SEND_UNSUPPORTED

    @pytest.mark.asyncio
    async def test_a_pronto_edit_of_a_radio_command_is_refused(self, manager, keyfob):
        manager._store.get_device = MagicMock(return_value=self._device(keyfob))
        result = await manager.async_update_command(
            "dev1", "c1", pronto="0000 006D 0002 0000 0020 0040 0020 0040"
        )
        assert result["success"] is False
        # rf_edit_unsupported until the RF send round, which edits a
        # radio row as a radio code and refuses Pronto as the other
        # medium's code (rf-send-doors.md section 5).
        assert result["code"] == "wrong_medium_code"


class TestWigExport:
    def test_radio_rows_are_skipped_and_named(self, keyfob):
        from custom_components.hair.wig_export import build_wig_from_device

        ir = IRCommand(
            id="c0", name="Power", category=CommandCategory.POWER,
            source=CommandSource.CAPTURED, protocol="PRONTO",
            code="0000 006D 0002 0000 0020 0040 0020 0040",
        )
        device = IRDevice(
            id="dev1", name="Mixed", device_type="custom",
            commands=[ir, _rf_command(keyfob)],
        )
        built = build_wig_from_device(device)
        assert built.skipped == 1
        assert any("Button 1" in note for note in built.notes)
        assert built.sources == ["c0"]
