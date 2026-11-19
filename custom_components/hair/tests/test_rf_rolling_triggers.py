"""Rolling-code remotes as triggers.

A KeeLoq or Somfy RTS press changes part of its code every time. HAIR
files a clean read of one by its fixed part (KeeLoq serial and buttons,
Somfy address and command) in the decoded identity tier, so every press
of one button lands on one row and fires one trigger. A replay of a
press already heard is dropped. Sending stays refused, as before.

Frames are constructed from the datasheet layouts (the builders in
``test_rf_family_keeloq`` and ``test_rf_family_somfy``); no real remote
is needed.
"""
from __future__ import annotations

import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair import rf_family
from custom_components.hair.const import (
    DOMAIN,
    MEDIUM_RF,
    RF_PROTOCOL,
    RF_ROLLING_SEED,
)
from custom_components.hair.identity import TIER_DECODED, SignalIdentity
from custom_components.hair.models import CommandCategory, IRCommand
from custom_components.hair.rf_family import rolling_identity
from custom_components.hair.rf_replay import RollingReplay
from custom_components.hair.rf_send import rolling_row
from custom_components.hair.tests.test_rf_family_keeloq import SERIAL
from custom_components.hair.tests.test_rf_family_keeloq import _bits as _kl_bits
from custom_components.hair.tests.test_rf_family_keeloq import _capture as _kl_capture
from custom_components.hair.tests.test_rf_family_keeloq import _word as _kl_word
from custom_components.hair.tests.test_rf_family_somfy import ADDRESS
from custom_components.hair.tests.test_rf_family_somfy import _capture as _somfy_capture
from custom_components.hair.tests.test_rf_family_somfy import _frame as _somfy_frame
from custom_components.hair.tests.test_rf_family_somfy import _plain
from custom_components.hair.tests.test_rf_hear import (
    RECEIVER,
    _Modulation,
    _monitor,
    _state,
)
from custom_components.hair.tests.test_rf_paste import IT104_B64


@pytest.fixture(autouse=True)
def _fresh_caches():
    for cached in (rf_family._family_of, rf_family._rolling_family,
                   rf_family._rolling_identity):
        cached.cache_clear()
    yield
    for cached in (rf_family._family_of, rf_family._rolling_family,
                   rf_family._rolling_identity):
        cached.cache_clear()


def _keeloq(hopping: int, **kwargs) -> list[int]:
    return _kl_word(_kl_bits(hopping=hopping, **kwargs))


def _somfy(command: int, rolling: int) -> list[int]:
    return _somfy_frame(_plain(command=command, rolling=rolling))


# ---------------------------------------------------------------------------
# The identity
# ---------------------------------------------------------------------------


class TestTheFixedPart:
    def test_every_keeloq_press_of_one_button_is_one_identity(self):
        reads = [rolling_identity(_keeloq(h)) for h in (1, 0xDEADBEEF, 0x12345678)]
        assert len({r.fingerprint for r in reads}) == 1
        assert reads[0].family == "keeloq"
        assert reads[0].remote == f"{SERIAL:07X}"
        assert reads[0].button == "S1"
        assert {r.rolling for r in reads} == {1, 0xDEADBEEF, 0x12345678}

    def test_low_battery_and_repeat_do_not_split_a_button(self):
        plain = rolling_identity(_keeloq(7))
        assert rolling_identity(_keeloq(8, vlow=1)).fingerprint == plain.fingerprint
        assert rolling_identity(_keeloq(9, rpt=1)).fingerprint == plain.fingerprint

    def test_another_button_or_remote_is_another_identity(self):
        one = rolling_identity(_keeloq(7))
        other_button = rolling_identity(_keeloq(7, buttons=("S2",)))
        other_remote = rolling_identity(_keeloq(7, serial=0x0BADCAF))
        assert len({one.fingerprint, other_button.fingerprint,
                    other_remote.fingerprint}) == 3
        assert other_button.device_key == one.device_key
        assert other_remote.device_key != one.device_key

    def test_a_seed_word_is_marked(self):
        seed = rolling_identity(_keeloq(7, buttons=("S0", "S1", "S2", "S3")))
        assert seed.seed is True
        assert rolling_identity(_keeloq(7)).seed is False

    def test_every_somfy_press_of_one_command_is_one_identity(self):
        reads = [rolling_identity(_somfy(2, counter)) for counter in (10, 11, 500)]
        assert len({r.fingerprint for r in reads}) == 1
        assert reads[0].family == "somfy_rts"
        assert reads[0].remote == f"{ADDRESS:06X}"
        assert reads[0].button == "2"
        assert [r.rolling for r in reads] == [10, 11, 500]

    def test_somfy_reads_while_its_label_is_off(self):
        assert rf_family.FAMILIES["somfy_rts"].shown is False
        assert rolling_identity(_somfy(2, 10)) is not None

    def test_a_fixed_code_has_no_rolling_identity(self):
        from custom_components.hair.tests.test_rf_family import _frame as _pt_frame

        assert rolling_identity(_pt_frame(0x95A3C6)) is None

    def test_a_bad_somfy_checksum_is_not_read(self):
        assert rolling_identity(_somfy_frame(_plain(good_check=False))) is None

    def test_a_decoder_that_raises_fails_open(self):
        def broken(_frame):
            raise ZeroDivisionError

        with patch.object(rf_family, "_SHAPES", (broken,)):
            assert rolling_identity(_keeloq(7)) is None

    def test_the_fingerprint_is_never_read_as_a_rejudged_label(self):
        from custom_components.hair.protocol_decode import stored_identity_is_stale

        frame = _keeloq(7)
        assert stored_identity_is_stale(rolling_identity(frame).fingerprint, frame) is False

    def test_the_rolling_part_is_not_a_field_and_not_in_the_repr(self):
        read = rolling_identity(_keeloq(0xDEADBEEF))
        assert "deadbeef" not in repr(read).lower()
        assert "3735928559" not in repr(read)
        fields = dict(rf_family.family_of(_keeloq(0xDEADBEEF)).fields)
        assert set(fields) == {"serial", "buttons", "low battery"}


# ---------------------------------------------------------------------------
# The replay check
# ---------------------------------------------------------------------------


class TestReplay:
    def test_a_keeloq_word_heard_before_is_refused(self):
        replay = RollingReplay()
        assert replay.accept(rolling_identity(_keeloq(1)))
        assert replay.accept(rolling_identity(_keeloq(2)))
        assert not replay.accept(rolling_identity(_keeloq(1)))
        assert replay.accept(rolling_identity(_keeloq(3)))

    def test_keeloq_is_kept_per_button(self):
        replay = RollingReplay()
        assert replay.accept(rolling_identity(_keeloq(1)))
        assert replay.accept(rolling_identity(_keeloq(1, buttons=("S2",))))

    def test_a_seed_word_is_never_checked(self):
        replay = RollingReplay()
        seed = rolling_identity(_keeloq(7, buttons=("S0", "S1", "S2", "S3")))
        assert replay.accept(seed) and replay.accept(seed)

    def test_somfy_shares_one_counter_across_its_buttons(self):
        replay = RollingReplay()
        assert replay.accept(rolling_identity(_somfy(2, 10)))  # Up
        assert replay.accept(rolling_identity(_somfy(4, 11)))  # Down
        assert not replay.accept(rolling_identity(_somfy(2, 10)))
        assert not replay.accept(rolling_identity(_somfy(1, 11)))

    def test_a_somfy_remote_pressed_out_of_range_is_not_stuck(self):
        replay = RollingReplay()
        assert replay.accept(rolling_identity(_somfy(2, 10)))
        assert replay.accept(rolling_identity(_somfy(2, 900)))
        assert not replay.accept(rolling_identity(_somfy(2, 500)))

    def test_the_somfy_counter_wraps(self):
        replay = RollingReplay()
        assert replay.accept(rolling_identity(_somfy(2, 0xFFFE)))
        assert replay.accept(rolling_identity(_somfy(2, 1)))

    def test_the_memory_is_bounded(self):
        from custom_components.hair import rf_replay

        replay = RollingReplay()
        for serial in range(rf_replay.MAX_REMOTES + 5):
            replay.accept(rolling_identity(_keeloq(1, serial=serial + 1)))
        assert len(replay._keeloq) == rf_replay.MAX_REMOTES


# ---------------------------------------------------------------------------
# Hearing, end to end
# ---------------------------------------------------------------------------


async def _hear(fake_hass, monitor, captures):
    tasks = []
    fake_hass.async_create_task = MagicMock(side_effect=tasks.append)
    fake_hass.states.get = MagicMock(return_value=_state(
        RECEIVER, capturing=True, capture_phase="listening",
        frequency_hz=433_920_000,
    ))
    for index, capture in enumerate(captures):
        signal = types.SimpleNamespace(
            timings=list(capture), frequency=None, modulation=_Modulation.OOK,
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


def _with_triggers(monitor):
    manager = MagicMock()
    manager.on_signal_captured = MagicMock(return_value=[])
    monitor._trigger_manager = manager
    return manager


def _decoded_fingerprints(manager) -> list:
    return [call.args[6] for call in manager.on_signal_captured.call_args_list]


def _kl_press(hopping: int, **kwargs) -> list[int]:
    return _kl_capture(_kl_bits(hopping=hopping, **kwargs))


@pytest.mark.asyncio
class TestHearing:
    async def test_three_keeloq_presses_are_one_row(self, fake_hass):
        monitor, store = _monitor(fake_hass)
        manager = _with_triggers(monitor)
        await _hear(fake_hass, monitor, [_kl_press(h) for h in (11, 22, 33)])
        devices = store.get_all_devices()
        assert len(devices) == 1
        assert len(devices[0].signals) == 1
        row = devices[0].signals[0]
        assert row.hit_count == 3
        expected = rolling_identity(row.raw_timings).fingerprint
        assert row.decoded_fingerprint == expected
        assert _decoded_fingerprints(manager) == [expected] * 3

    async def test_another_button_is_another_row_on_the_same_card(self, fake_hass):
        monitor, store = _monitor(fake_hass)
        _with_triggers(monitor)
        await _hear(fake_hass, monitor, [
            _kl_press(11), _kl_press(12, buttons=("S2",)), _kl_press(13),
        ])
        devices = store.get_all_devices()
        assert len(devices) == 1
        assert sorted(s.hit_count for s in devices[0].signals) == [1, 2]

    async def test_two_remotes_are_two_cards(self, fake_hass):
        monitor, store = _monitor(fake_hass)
        _with_triggers(monitor)
        await _hear(fake_hass, monitor, [
            _kl_press(11), _kl_press(12, serial=0x0BADCAF),
        ])
        assert len(store.get_all_devices()) == 2

    async def test_a_replayed_press_fires_nothing(self, fake_hass):
        monitor, store = _monitor(fake_hass)
        manager = _with_triggers(monitor)
        await _hear(fake_hass, monitor, [_kl_press(11), _kl_press(22), _kl_press(11)])
        assert manager.on_signal_captured.call_count == 2
        assert store.get_all_devices()[0].signals[0].hit_count == 2

    async def test_somfy_presses_are_one_row_and_a_replay_is_dropped(self, fake_hass):
        monitor, store = _monitor(fake_hass)
        manager = _with_triggers(monitor)
        await _hear(fake_hass, monitor, [
            _somfy_capture(_plain(rolling=10)),
            _somfy_capture(_plain(rolling=11)),
            _somfy_capture(_plain(rolling=10)),
        ])
        rows = store.get_all_devices()[0].signals
        assert len(rows) == 1 and rows[0].hit_count == 2
        assert manager.on_signal_captured.call_count == 2

    async def test_a_fixed_code_is_unchanged(self, fake_hass):
        from custom_components.hair.tests.test_rf_family import _frame as _pt_frame

        monitor, store = _monitor(fake_hass)
        manager = _with_triggers(monitor)
        await _hear(fake_hass, monitor, [_pt_frame(0x95A3C6) * 4])
        assert store.get_all_devices()[0].signals[0].decoded_fingerprint is None
        assert _decoded_fingerprints(manager) == [None]

    async def test_the_row_still_cannot_be_sent(self, fake_hass):
        monitor, store = _monitor(fake_hass)
        _with_triggers(monitor)
        await _hear(fake_hass, monitor, [_kl_press(11)])
        assert rolling_row(store.get_all_devices()[0].signals[0]) == "keeloq"


class TestATriggerMatchesEveryPress:
    def test_on_the_decoded_tier(self):
        first, later = _keeloq(1), _keeloq(2)
        trigger = SignalIdentity(
            rolling_identity(first).fingerprint, "hash-of-press-1", "fp-1",
            decode_covers=True,
        )
        press = SignalIdentity(
            rolling_identity(later).fingerprint, "hash-of-press-2", "fp-2",
            decode_covers=True,
        )
        assert trigger.match_tier(press) == TIER_DECODED


# ---------------------------------------------------------------------------
# The paste and trigger doors
# ---------------------------------------------------------------------------


class TestPaste:
    def test_a_pasted_press_is_its_button(self):
        from custom_components.hair import rf_paste
        from custom_components.hair.models import UnknownSignal

        text = " ".join(str(v) for v in _kl_press(11))
        result = rf_paste.validate(text, 433_920_000)
        row = UnknownSignal(id="s1", fingerprint="x", raw_timings=[])
        rf_paste.apply_code(row, result)
        assert row.decoded_fingerprint == rolling_identity(_keeloq(99)).fingerprint
        assert row.decode_covers is True

    def test_a_pasted_fixed_code_has_no_decoded_identity(self):
        from custom_components.hair import rf_paste
        from custom_components.hair.models import UnknownSignal

        row = UnknownSignal(id="s1", fingerprint="x", raw_timings=[])
        rf_paste.apply_code(row, rf_paste.validate(IT104_B64))
        assert row.decoded_fingerprint is None


def _hass_with_command(fake_hass, frame):
    from custom_components.hair.storage import HAIRStore

    store = HAIRStore(fake_hass)
    store._loaded = True
    store.async_save = AsyncMock()
    command = IRCommand(id="c1", name="Open", category=CommandCategory.CUSTOM)
    command.medium = MEDIUM_RF
    command.protocol = RF_PROTOCOL
    command.raw_timings = list(frame)
    command.rf_frequency_hz = 433_920_000
    device = SimpleNamespace(get_command=lambda _cid: command)
    manager = MagicMock()
    manager.get_device = MagicMock(return_value=device)
    fake_hass.data[DOMAIN] = {
        "e1": {
            "store": store,
            "device_manager": manager,
            "config_entry": SimpleNamespace(entry_id="e1"),
        }
    }
    return store


async def _create_trigger(fake_hass):
    from custom_components.hair.websocket_api import ws_create_trigger

    conn = MagicMock()
    with patch("custom_components.hair.event.sync_trigger_entities"), patch(
        "custom_components.hair.event.sync_remote_entities"
    ), patch("custom_components.hair.pin_bindings.rederive_all_pinned"):
        await ws_create_trigger(fake_hass, conn, {
            "id": 1, "type": "hair/trigger/create", "name": "Garage",
            "min_hits": 1, "receiver_entity_ids": [],
            "source_device_id": "d1", "source_command_id": "c1",
        })
    return conn


@pytest.mark.asyncio
class TestTheTriggerDoor:
    async def test_a_rolling_button_makes_a_trigger_on_its_fixed_part(self, fake_hass):
        frame = _keeloq(11)
        store = _hass_with_command(fake_hass, frame)
        conn = await _create_trigger(fake_hass)
        assert not conn.send_error.called
        (trigger,) = store.get_all_triggers()
        assert trigger.decoded_fingerprint == rolling_identity(frame).fingerprint

    async def test_a_seed_word_makes_no_trigger(self, fake_hass):
        store = _hass_with_command(
            fake_hass, _keeloq(11, buttons=("S0", "S1", "S2", "S3")),
        )
        conn = await _create_trigger(fake_hass)
        assert conn.send_error.call_args.args[1] == RF_ROLLING_SEED
        assert store.get_all_triggers() == []
