"""A stored send spacing is read for the block a row sends today (M1).

A spacing is the time from the start of one block to the start of the
next, decided once against the block the row built when it was minted
or saved. #213 moved Symphony from rebuild to replay, and a Dreo row
whose 160 ms spacing was estimated against a two-frame rebuilt block
went on to send a 157 to 266 ms capture with only the 10 ms minimum gap
between blocks. These pins cover the three rules in
``send_plan.effective_spacing_ms``, the record that rule 1 reads, the
load-time fill, the two send sites and the editor's read helper.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.const import (
    SEND_AIR_TIME_MAX_MS,
    SEND_SILENCE_FLOOR_US,
)
from custom_components.hair.decoders.sony import SonyCommand
from custom_components.hair.ir_command import (
    ProntoCommand,
    block_duration_us,
    raw_to_pronto,
)
from custom_components.hair.mint import mint_command
from custom_components.hair.models import IRCommand, IRDevice, UnknownSignal
from custom_components.hair.protocol_decode import try_decode_identity
from custom_components.hair.send_plan import (
    build_like_send_path,
    effective_spacing_ms,
    estimate_spacing_ms,
    fill_spacing_block,
    realised_air_ms,
    record_spacing_block,
    silence_us,
)
from custom_components.hair.wig_format import parse_wig

FIXTURES = Path(__file__).parent / "fixtures"
WIGS = FIXTURES / "wigs"
# What mint estimated for a Dreo row before #213: the rebuilt block was
# two Symphony frames, about 48 ms, and the estimate is block + 50 + 60.
OLD_DREO_SPACING = 160


def _dreo(alias: str) -> str:
    wig = parse_wig(
        (WIGS / "dreo-fan-dr-haf004s-perfect-fit.wig.json").read_text()
    ).wig
    return next(s.pronto for s in wig.signals if s.alias == alias)


def _row(code: str, *, cls=IRCommand, **knobs):
    """A row as a mint door leaves it, decoded fields and all."""
    raw = ProntoCommand(code).get_raw_timings()
    identity = try_decode_identity(raw)
    fields = dict(
        protocol="PRONTO", code=code, raw_timings=list(raw),
    )
    if identity is not None:
        fields.update(
            decoded_protocol=identity.protocol,
            decoded_address=identity.address,
            decoded_command=identity.command,
            decoded_fingerprint=identity.fingerprint,
            decoded_extras=dict(identity.extras) if identity.extras else None,
            decode_covers=identity.covers_capture,
        )
    if cls is IRCommand:
        fields["name"] = "row"
    fields.update(knobs)
    return cls(**fields)


def _legacy_dreo(alias: str = "Speed Up", count: int = 3) -> IRCommand:
    """A Dreo row minted before #213: 160 ms, no recorded block."""
    return _row(
        _dreo(alias), send_count=count, send_spacing_ms=OLD_DREO_SPACING
    )


def _block(timings_us: int):
    """A stand-in send block of exactly ``timings_us``."""
    return SimpleNamespace(get_raw_timings=lambda: [timings_us])


def _silence_ms(row) -> float:
    inner = build_like_send_path(row)
    block = block_duration_us(inner.get_raw_timings())
    spacing = effective_spacing_ms(
        row.send_spacing_ms, inner, row.send_count, row.send_spacing_block_us
    )
    return silence_us(block, spacing) / 1000


# ---------------------------------------------------------------------------
# Rule 2: a row with no record, sent at the minimum gap
# ---------------------------------------------------------------------------


class TestRule2TheClampedSend:
    """The trigger is exact: the send would be clamped to the minimum
    gap, which is a stored spacing no longer than block plus 10 ms."""

    def test_rule2_fires_at_block_plus_10ms(self):
        inner = _block(100_000)
        assert silence_us(100_000, 110) == SEND_SILENCE_FLOOR_US
        assert effective_spacing_ms(110, inner, 3, None) == (
            estimate_spacing_ms(inner)
        )

    def test_rule2_fires_below_block_plus_10ms(self):
        inner = _block(100_000)
        assert effective_spacing_ms(60, inner, 3, None) == (
            estimate_spacing_ms(inner)
        )

    def test_rule2_does_not_fire_at_block_plus_11ms(self):
        inner = _block(100_000)
        assert effective_spacing_ms(111, inner, 3, None) == 111

    def test_a_squeezed_row_off_the_floor_is_left_alone(self):
        """The known limit: silence that shrank from 250 to 90 ms is not
        a clamped send, and an older row cannot say what it was."""
        inner = _block(200_000)
        assert effective_spacing_ms(290, inner, 3, None) == 290

    @pytest.mark.parametrize(
        "alias", ["Power", "Speed Up", "Oscillate Vertical", "Timer", "Mode"]
    )
    def test_a_pre_213_dreo_row_gets_its_gap_back(self, alias):
        row = _legacy_dreo(alias)
        inner = build_like_send_path(row)
        block = block_duration_us(inner.get_raw_timings())
        assert silence_us(block, OLD_DREO_SPACING) == SEND_SILENCE_FLOOR_US
        assert _silence_ms(row) > 100

    def test_the_dreo_row_at_x3(self):
        row = _legacy_dreo("Speed Up", 3)
        inner = build_like_send_path(row)
        spacing = effective_spacing_ms(160, inner, 3, None)
        assert spacing == estimate_spacing_ms(inner)
        assert realised_air_ms(inner, 3, spacing) <= SEND_AIR_TIME_MAX_MS


# ---------------------------------------------------------------------------
# Rule 3: the cap, the count never touched
# ---------------------------------------------------------------------------


class TestRule3TheCap:
    def test_near_the_cap_the_spacing_is_cut_to_fit(self):
        row = _legacy_dreo("Mode", 10)
        inner = build_like_send_path(row)
        spacing = effective_spacing_ms(160, inner, 10, None)
        assert spacing > OLD_DREO_SPACING
        assert spacing < estimate_spacing_ms(inner)
        assert realised_air_ms(inner, 10, spacing) <= SEND_AIR_TIME_MAX_MS
        assert realised_air_ms(inner, 10, spacing + 1) > SEND_AIR_TIME_MAX_MS

    def test_never_tighter_than_the_stored_value(self):
        """Even the floor does not fit: the stored value goes out as it
        always did (the send path has never enforced the cap)."""
        inner = _block(400_000)
        assert effective_spacing_ms(30, inner, 10, None) == 30

    def test_a_cut_never_goes_below_the_stored_value(self):
        """Rule 1 wants 420 (the block grew 100 ms from its 180 ms
        record); at x10 only 302 fits, which is below the stored 320, so
        the send stays at 320 rather than going tighter than before."""
        from custom_components.hair.send_plan import (
            _largest_fitting_spacing_ms,
        )

        assert _largest_fitting_spacing_ms(280_000, 10) == 302
        assert effective_spacing_ms(320, _block(280_000), 10, 180_000) == 320

    def test_the_count_is_not_an_output(self):
        row = _legacy_dreo("Mode", 10)
        effective_spacing_ms(160, build_like_send_path(row), 10, None)
        assert row.send_count == 10


class TestTheLargestFittingSpacing:
    """``_largest_fitting_spacing_ms`` is the largest spacing the cap
    accepts by ``realised_air_ms``'s own arithmetic, never one short."""

    @staticmethod
    def _fits(block_us: int, count: int, spacing: int) -> bool:
        return realised_air_ms(_block(block_us), count, spacing) <= (
            SEND_AIR_TIME_MAX_MS
        )

    def test_the_candle_at_ten_sends(self):
        """The Amazon Candles "On" capture rebuilt as RC-5 with one
        ditto, 138.0 ms: 318 fits at x10, which the old search missed."""
        from custom_components.hair.send_plan import (
            _largest_fitting_spacing_ms,
        )

        capture = json.loads(
            (FIXTURES / "grouping" / "candle-on-air.json").read_text()
        )
        code = capture["code"]
        row = mint_command(
            name="On", protocol="PRONTO", code=code, send_count=10,
            repeat_count=1,
            identity=try_decode_identity(ProntoCommand(code).get_raw_timings()),
        )
        inner = build_like_send_path(row)
        block = block_duration_us(inner.get_raw_timings())
        assert _largest_fitting_spacing_ms(block, 10) == 318
        assert realised_air_ms(inner, 10, 318) <= SEND_AIR_TIME_MAX_MS
        assert realised_air_ms(inner, 10, 319) > SEND_AIR_TIME_MAX_MS

    @pytest.mark.parametrize("count", [2, 3, 5, 7, 10])
    def test_it_is_the_largest_across_blocks(self, count):
        from custom_components.hair.const import (
            SEND_SPACING_MAX_MS,
            SEND_SPACING_MIN_MS,
        )
        from custom_components.hair.send_plan import (
            _largest_fitting_spacing_ms,
        )

        for block_us in range(1_000, 1_500_001, 4_999):
            best = _largest_fitting_spacing_ms(block_us, count)
            if best is None:
                assert not self._fits(block_us, count, SEND_SPACING_MIN_MS)
                continue
            assert SEND_SPACING_MIN_MS <= best <= SEND_SPACING_MAX_MS
            assert self._fits(block_us, count, best), (block_us, best)
            if best < SEND_SPACING_MAX_MS:
                assert not self._fits(block_us, count, best + 1), (
                    block_us, best,
                )


# ---------------------------------------------------------------------------
# Rule 1: a recorded block keeps its silence
# ---------------------------------------------------------------------------


def _sony_row(frames: int = 1, **knobs):
    """A Sony row; ``frames`` > 1 is a held-press capture, whose raw
    replay is several frames long where the rebuild is one."""
    raw = SonyCommand(
        address=1, address_bits=5, command=0x15, repeat_count=frames - 1
    ).get_raw_timings()
    code = raw_to_pronto(raw, frequency=40000)
    return mint_command(
        name="Volume", protocol="PRONTO", code=code, raw_timings=list(raw),
        frequency=40000,
        identity=try_decode_identity(ProntoCommand(code).get_raw_timings()),
        **knobs,
    )


class TestRule1TheRecord:
    def test_mint_records_the_block_it_estimated_against(self):
        row = _sony_row(send_count=3, repeat_count=2)
        assert row.send_spacing_ms is not None
        assert row.send_spacing_block_us == block_duration_us(
            build_like_send_path(row).get_raw_timings()
        )

    def test_the_bypass_toggle_keeps_the_silence(self):
        row = _sony_row(frames=3, send_count=3, repeat_count=0)
        before = _silence_ms(row)
        block_before = row.send_spacing_block_us
        row.tx_force_raw = True
        block_after = block_duration_us(build_like_send_path(row).get_raw_timings())
        assert abs(block_after - block_before) > 2_000, "the toggle moved the block"
        assert abs(_silence_ms(row) - before) <= 1

    def test_a_repeat_count_change_keeps_the_silence(self):
        row = _sony_row(send_count=3, repeat_count=1)
        before = _silence_ms(row)
        row.repeat_count = 4
        block_after = block_duration_us(build_like_send_path(row).get_raw_timings())
        assert abs(block_after - row.send_spacing_block_us) > 2_000
        assert abs(_silence_ms(row) - before) <= 1

    def test_an_unchanged_block_sends_the_stored_value(self):
        row = _sony_row(send_count=3, send_spacing_ms=300)
        inner = build_like_send_path(row)
        assert effective_spacing_ms(300, inner, 3, row.send_spacing_block_us) == 300

    def test_a_drift_within_two_ms_sends_the_stored_value(self):
        """Receiver jitter in a re-measured block does not move the
        number; a drift past 2 ms moves it by the drift."""
        assert effective_spacing_ms(300, _block(101_900), 3, 100_000) == 300
        assert effective_spacing_ms(300, _block(98_100), 3, 100_000) == 300
        assert effective_spacing_ms(300, _block(103_000), 3, 100_000) == 303
        assert effective_spacing_ms(300, _block(97_000), 3, 100_000) == 297

    def test_a_record_beats_the_floor_rule(self):
        """A recorded row is never re-estimated: its own number is kept
        when its block has not moved, even on the floor."""
        inner = _block(100_000)
        assert effective_spacing_ms(105, inner, 3, 100_000) == 105


# ---------------------------------------------------------------------------
# A row that sends once
# ---------------------------------------------------------------------------


class TestASingleSend:
    def test_it_is_not_touched_and_records_nothing(self):
        row = _row(_dreo("Speed Up"), send_count=1, send_spacing_ms=160)
        assert fill_spacing_block(row) is False
        assert row.send_spacing_block_us is None
        record_spacing_block(row)
        assert row.send_spacing_block_us is None
        assert effective_spacing_ms(
            160, build_like_send_path(row), 1, None
        ) == 160


# ---------------------------------------------------------------------------
# The load-time fill
# ---------------------------------------------------------------------------


class TestTheFill:
    def _store(self, commands):
        from custom_components.hair.storage import HAIRStore

        device = IRDevice(name="Fan", commands=list(commands))
        store = HAIRStore.__new__(HAIRStore)
        store._data = {device.id: device}
        return store, device

    def test_it_fills_a_plausible_row_and_skips_the_rest(self):
        plausible = _sony_row(send_count=3, send_spacing_ms=300)
        plausible.send_spacing_block_us = None
        clamped = _legacy_dreo("Speed Up", 3)
        once = _row(_dreo("Power"), send_count=1, send_spacing_ms=160)
        no_spacing = _row(_dreo("Timer"), send_count=3)
        store, _ = self._store([plausible, clamped, once, no_spacing])
        assert store._backfill_spacing_block() is True
        assert plausible.send_spacing_block_us is not None
        assert clamped.send_spacing_block_us is None, "stays on rule 2"
        assert once.send_spacing_block_us is None
        assert no_spacing.send_spacing_block_us is None
        # The spacing itself is never written.
        assert (plausible.send_spacing_ms, clamped.send_spacing_ms) == (300, 160)

    def test_a_second_load_changes_nothing(self):
        plausible = _sony_row(send_count=3, send_spacing_ms=300)
        plausible.send_spacing_block_us = None
        store, device = self._store([plausible, _legacy_dreo("Mode", 3)])
        assert store._backfill_spacing_block() is True
        snapshot = [c.to_dict() for c in device.commands]
        assert store._backfill_spacing_block() is False
        assert [c.to_dict() for c in device.commands] == snapshot

    @pytest.mark.asyncio
    async def test_the_real_load_saves_once_and_then_not_at_all(self):
        from custom_components.hair.storage import HAIRStore

        plausible = _sony_row(send_count=3, send_spacing_ms=300)
        plausible.send_spacing_block_us = None
        device = IRDevice(name="TV", commands=[plausible])

        class _Backing:
            def __init__(self, *a, **k):
                self._data = {"devices": [device.to_dict()], "triggers": []}
                self.saves = 0

            async def async_load(self):
                return self._data

            async def async_save(self, data):
                self.saves += 1
                self._data = data

        backing = _Backing()
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(
            side_effect=lambda func, *args: func(*args)
        )
        with patch(
            "custom_components.hair.storage._HAIRDeviceStore",
            lambda *a, **k: backing,
        ):
            store = HAIRStore(hass)
            await store.async_load()
            first = backing.saves
            loaded = next(iter(store._data.values())).commands[0]
            assert loaded.send_spacing_block_us is not None
            again = HAIRStore(hass)
            await again.async_load()
        assert first >= 1
        assert backing.saves == first, "a second load must not save"

    def test_the_catalog_fill_is_idempotent_too(self):
        from custom_components.hair.models import UnknownDevice
        from custom_components.hair.signal_store import _transform_loaded

        plausible = _sony_row(send_count=3, send_spacing_ms=300)
        signal = UnknownSignal(
            id="s1", protocol="PRONTO", code=plausible.code,
            raw_timings=list(plausible.raw_timings or []),
            send_count=3, send_spacing_ms=300,
        )
        device = UnknownDevice(label="Remote", signals=[signal])
        devices, _d, _dirty = _transform_loaded(
            {"devices": [device.to_dict()], "dismissed": []}
        )
        filled = next(iter(devices.values())).signals[0]
        assert filled.send_spacing_block_us is not None
        _devices, _d, dirty_again = _transform_loaded(
            {"devices": [d.to_dict() for d in devices.values()], "dismissed": []}
        )
        assert dirty_again is False


# ---------------------------------------------------------------------------
# The record travels and is written by the doors
# ---------------------------------------------------------------------------


class TestTheRecord:
    def test_it_round_trips_and_an_old_row_writes_no_key(self):
        row = _sony_row(send_count=3)
        assert IRCommand.from_dict(row.to_dict()).send_spacing_block_us == (
            row.send_spacing_block_us
        )
        assert "send_spacing_block_us" not in IRCommand(name="x").to_dict()
        signal = UnknownSignal(id="s", send_spacing_ms=200, send_spacing_block_us=9000)
        assert UnknownSignal.from_dict(signal.to_dict()).send_spacing_block_us == 9000
        assert "send_spacing_block_us" not in UnknownSignal(id="t").to_dict()

    def test_it_is_on_both_rosters(self):
        from custom_components.hair.models import (
            _CLONE_SKIPS,
            _KNOWN_COMMAND,
            _KNOWN_SIGNAL,
        )

        assert "send_spacing_block_us" in _KNOWN_COMMAND - _CLONE_SKIPS
        assert "send_spacing_block_us" in _KNOWN_SIGNAL

    def test_assign_carries_it_and_a_set_spacing_measures_fresh(self):
        from custom_components.hair.signal_monitor import _apply_signal_provenance

        signal = UnknownSignal(id="s", send_count=3, send_spacing_ms=200,
                               send_spacing_block_us=12_345)
        command = IRCommand(name="c")
        _apply_signal_provenance(command, signal)
        assert command.send_spacing_block_us == 12_345

        sony = _sony_row(send_count=3)
        signal = UnknownSignal(
            id="s", protocol="PRONTO", code=sony.code,
            raw_timings=list(sony.raw_timings or []),
            send_count=3, send_spacing_ms=200, send_spacing_block_us=1,
        )
        command = IRCommand(name="c", protocol="PRONTO", code=sony.code,
                            raw_timings=list(sony.raw_timings or []))
        _apply_signal_provenance(
            command, signal, send_spacing_ms=250, set_send_spacing=True
        )
        assert command.send_spacing_ms == 250
        assert command.send_spacing_block_us == block_duration_us(
            build_like_send_path(command).get_raw_timings()
        )

    @pytest.mark.asyncio
    async def test_the_command_save_door_records_the_block(self, fake_hass):
        from custom_components.hair.tests.test_decoded_tx_consistency import (
            _make_device_manager,
        )

        manager = _make_device_manager(fake_hass)
        row = _legacy_dreo("Speed Up", 3)
        device = IRDevice(name="Fan", emitter_entity_ids=["infrared.e"])
        device.add_command(row)
        manager._store.add_device(device)
        await manager.async_update_command(
            device.id, row.id, send_spacing_ms=265, set_send_spacing=True,
        )
        assert row.send_spacing_ms == 265
        assert row.send_spacing_block_us == block_duration_us(
            build_like_send_path(row).get_raw_timings()
        )

    @pytest.mark.asyncio
    async def test_a_knob_only_save_keeps_the_record(self, fake_hass):
        """A ditto change without a spacing in the payload leaves the
        record alone, so rule 1 keeps the silence at send time."""
        from custom_components.hair.tests.test_decoded_tx_consistency import (
            _make_device_manager,
        )

        manager = _make_device_manager(fake_hass)
        row = _sony_row(send_count=3, repeat_count=1)
        recorded = row.send_spacing_block_us
        before = _silence_ms(row)
        device = IRDevice(name="TV", emitter_entity_ids=["infrared.e"])
        device.add_command(row)
        manager._store.add_device(device)
        await manager.async_update_command(device.id, row.id, repeat_count=4)
        assert row.send_spacing_block_us == recorded
        assert abs(_silence_ms(row) - before) <= 1

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
    async def test_the_clipper_paste_door_records_the_block(self):
        monitor, store = self._monitor()
        with patch.object(store, "async_save", AsyncMock()):
            device = await monitor.create_manual_remote("Fan")
            res = await monitor.create_manual_signal(
                device.id, _dreo("Speed Up"), send_count=3, send_spacing_ms=265
            )
        assert res["success"]
        sig = device.signals[0]
        assert sig.send_spacing_ms == 265
        assert sig.send_spacing_block_us == block_duration_us(
            build_like_send_path(sig).get_raw_timings()
        )

    @pytest.mark.asyncio
    async def test_the_signal_edit_door_records_only_a_set_spacing(self):
        """A code edit that sets the spacing measures the new block; one
        that leaves the spacing alone keeps the old record, so rule 1
        moves the spacing with the code."""
        monitor, store = self._monitor()
        with patch.object(store, "async_save", AsyncMock()):
            device = await monitor.create_manual_remote("Fan")
            await monitor.create_manual_signal(
                device.id, _dreo("Speed Up"), send_count=3, send_spacing_ms=265
            )
            sig = device.signals[0]
            speed_up = sig.send_spacing_block_us
            await monitor.edit_signal_pronto(device.id, sig.id, _dreo("Power"))
            assert sig.send_spacing_block_us == speed_up
            await monitor.edit_signal_pronto(
                device.id, sig.id, _dreo("Power"),
                send_spacing_ms=325, set_send_spacing=True,
            )
        power = block_duration_us(build_like_send_path(sig).get_raw_timings())
        assert abs(power - speed_up) > 2_000
        assert sig.send_spacing_block_us == power


# ---------------------------------------------------------------------------
# The two send sites
# ---------------------------------------------------------------------------


class TestTheSendSites:
    @pytest.mark.asyncio
    async def test_the_device_send_plans_the_effective_spacing(self, fake_hass):
        from custom_components.hair.tests.test_decoded_tx_consistency import (
            _infrared_mod,
            _make_device_manager,
        )

        manager = _make_device_manager(fake_hass)
        row = _legacy_dreo("Speed Up", 3)
        device = IRDevice(name="Fan", emitter_entity_ids=["infrared.e"])
        device.add_command(row)
        manager._store.add_device(device)
        seen = []
        from custom_components.hair import send_plan

        real = send_plan.plan_send

        def spy(inner, count, spacing, platform):
            seen.append(spacing)
            return real(inner, count, spacing, platform)

        with (
            patch.object(_infrared_mod, "async_send_command", AsyncMock()),
            patch.object(send_plan, "plan_send", spy),
        ):
            await manager.async_send_command(device.id, row.id)
        inner = build_like_send_path(row)
        assert seen and set(seen) == {estimate_spacing_ms(inner)}
        assert row.send_spacing_ms == OLD_DREO_SPACING, "never rewritten"

    @pytest.mark.asyncio
    async def test_the_catalog_test_plans_the_effective_spacing(self, fake_hass):
        from custom_components.hair.models import UnknownDevice
        from custom_components.hair.signal_monitor import SignalMonitor
        from custom_components.hair.tests.test_decoded_tx_consistency import (
            _infrared_mod,
            _make_hair_store,
            _make_signal_store,
        )

        row = _legacy_dreo("Speed Up", 3)
        signal = _row(
            row.code, cls=UnknownSignal, id="s1", fingerprint="s1",
            send_count=3, send_spacing_ms=OLD_DREO_SPACING,
        )
        store = _make_signal_store(fake_hass)
        monitor = SignalMonitor(fake_hass, store, _make_hair_store())
        store.add_device(UnknownDevice(id="ud1", fingerprint="d", signals=[signal]))
        seen = []
        from custom_components.hair import send_plan

        real = send_plan.plan_send

        def spy(inner, count, spacing, platform):
            seen.append(spacing)
            return real(inner, count, spacing, platform)

        with (
            patch.object(_infrared_mod, "async_send_command", AsyncMock()),
            patch.object(send_plan, "plan_send", spy),
        ):
            result = await monitor.test_signal("s1", "infrared.e")
        assert result["success"] is True
        assert seen == [estimate_spacing_ms(build_like_send_path(row))]


# ---------------------------------------------------------------------------
# The editor's read helper
# ---------------------------------------------------------------------------


class TestTheEditor:
    def _ask(self, fake_hass, **payload):
        from custom_components.hair.tests.test_send_spacing_doors import _wire
        from custom_components.hair.websocket_api import ws_send_spacing_info

        _wire(fake_hass)
        conn = MagicMock()
        msg = {"id": 1, "type": "hair/send_spacing_info"}
        msg.update(payload)
        ws_send_spacing_info(fake_hass, conn, msg)
        return conn.send_result.call_args[0][1]

    def test_the_stored_value_is_restated_for_todays_block(self, fake_hass):
        code = _dreo("Speed Up")
        result = self._ask(
            fake_hass, pronto=code, send_count=3,
            send_spacing_ms=OLD_DREO_SPACING, restate=True,
            send_spacing_block_us=None,
        )
        inner = build_like_send_path(_legacy_dreo("Speed Up", 3))
        assert result["restated"] is True
        assert result["effective_ms"] == estimate_spacing_ms(inner)
        # The air figure describes the number the box will show.
        assert result["air_ms"] == realised_air_ms(inner, 3, result["effective_ms"])
        assert result["floor_hit"] is False

    def test_a_typed_number_is_taken_as_typed(self, fake_hass):
        result = self._ask(
            fake_hass, pronto=_dreo("Speed Up"), send_count=3,
            send_spacing_ms=OLD_DREO_SPACING,
        )
        assert result["restated"] is False
        assert result["effective_ms"] == OLD_DREO_SPACING
        assert result["floor_hit"] is True


# ---------------------------------------------------------------------------
# Every fixture wig, before and after
# ---------------------------------------------------------------------------


def _wig_rows():
    for path in sorted(WIGS.glob("*.wig.json")):
        wig = parse_wig(path.read_text()).wig
        for signal in wig.signals:
            yield path.name, signal


@pytest.mark.parametrize("count", [2, 3, 5, 10])
def test_the_fixture_wigs_move_only_where_a_rule_says(count):
    """For every signal of every fixture wig, as a freshly minted row
    and as an older row with no record: the planned spacing equals the
    stored one except where rule 2 fires (an older row on the floor)."""
    moved = []
    for name, signal in _wig_rows():
        minted = mint_command(
            name=signal.alias, protocol="PRONTO", code=signal.pronto,
            send_count=count, repeat_count=signal.ditto_count,
            tx_force_raw=signal.bypass_protocol,
            identity=try_decode_identity(
                ProntoCommand(signal.pronto).get_raw_timings()
            ),
        )
        if minted.send_spacing_ms is None:
            continue
        inner = build_like_send_path(minted)
        block = block_duration_us(inner.get_raw_timings())
        # Freshly recorded: nothing moves.
        assert effective_spacing_ms(
            minted.send_spacing_ms, inner, count, minted.send_spacing_block_us
        ) == minted.send_spacing_ms, (name, signal.alias)
        # The same row without a record, at its own estimate and at a
        # few hand-set values around the floor.
        for stored in (minted.send_spacing_ms, block // 1000 + 10,
                       block // 1000 + 11, block // 1000 + 60):
            after = effective_spacing_ms(stored, inner, count, None)
            clamped = silence_us(block, stored) == SEND_SILENCE_FLOOR_US
            if after != stored:
                moved.append((name, signal.alias, stored, after))
                assert clamped, (name, signal.alias, stored, after)
            elif clamped:
                # Rule 2 fired but rule 3 kept the stored value.
                assert realised_air_ms(
                    inner, count, estimate_spacing_ms(inner)
                ) > SEND_AIR_TIME_MAX_MS
    assert moved, "the floor cases must exercise rule 2"


def test_the_probe_numbers_hold():
    """The report's figures, pinned so they cannot drift unnoticed."""
    report = {}
    for alias in ("Power", "Speed Up", "Mode"):
        row = _legacy_dreo(alias, 3)
        inner = build_like_send_path(row)
        block = block_duration_us(inner.get_raw_timings())
        spacing = effective_spacing_ms(160, inner, 3, None)
        report[alias] = (round(block / 1000), spacing,
                         round(silence_us(block, spacing) / 1000))
    assert json.loads(json.dumps(report)) == {
        "Power": [214, 325, 111],
        "Speed Up": [157, 265, 108],
        "Mode": [266, 375, 109],
    }
