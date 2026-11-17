"""Rolling codes are never sent (owner ruling 2026-11-16 09:45 PT).

A row whose frame reads as a rolling-code family (KeeLoq, Somfy RTS) is
refused at the air, by ``rf_send.plan_radio_send``, so no door can put
one on the air. The doors that make a sendable thing say so up front:
Assign and its New Device tab refuse; Make a Device, from a catalog
remote or from a Remote, and Adopt make the device without those rows
and count them; a wig export leaves them out, named. A trigger is still
allowed: that is what these rows are for.

Frames come from the KeeLoq and Somfy decoder tests, which build them
from the datasheet and the write-up.
"""
from __future__ import annotations

import inspect
import logging
import types
from unittest.mock import patch

import pytest

from custom_components.hair import rf_family
from custom_components.hair.const import (
    MEDIUM_IR,
    MEDIUM_RF,
    RF_NO_FRAME,
    RF_ROLLING_CODE,
    CommandCategory,
)
from custom_components.hair.models import IRCommand, IRDevice, UnknownDevice
from custom_components.hair.rf_send import SendRefusedError, plan_radio_send, rolling_row
from custom_components.hair.tests.test_device_manager import (  # noqa: F401 (fixture)
    manager,
)
from custom_components.hair.tests.test_radio_trigger_signal import (  # noqa: F401 (fixtures)
    _make_device,
    _radio_trigger,
    _remote,
    _wire,
    catalog,
    store,
)
from custom_components.hair.tests.test_rf_family import _frame as _pt_frame
from custom_components.hair.tests.test_rf_family_keeloq import _bits as _kl_bits
from custom_components.hair.tests.test_rf_family_keeloq import _word as _kl_word
from custom_components.hair.tests.test_rf_family_somfy import _frame as _somfy_frame
from custom_components.hair.tests.test_rf_family_somfy import _plain as _somfy_plain
from custom_components.hair.tests.test_rf_hear import _rf_signal
from custom_components.hair.tests.test_rf_send import (  # noqa: F401 (fixtures)
    ATHOM_TX,
    _row,
    captures,
    keyfob,
    radio,
)

KEELOQ = _kl_word(_kl_bits())
SOMFY = _somfy_frame()


@pytest.fixture(autouse=True)
def _fresh_cache():
    rf_family._rolling_family.cache_clear()
    yield
    rf_family._rolling_family.cache_clear()


# ---------------------------------------------------------------------------
# What counts as rolling
# ---------------------------------------------------------------------------


class TestWhatIsRolling:
    def test_keeloq(self):
        assert rf_family.rolling_family(KEELOQ) == "keeloq"

    def test_somfy_while_its_label_is_off(self):
        """Refused for what it is, not for what the pill shows."""
        assert not rf_family.FAMILIES["somfy_rts"].shown
        assert rf_family.family_of(SOMFY) is None
        assert rf_family.rolling_family(SOMFY) == "somfy_rts"

    def test_a_somfy_frame_whose_checksum_fails_is_not_read(self):
        assert rf_family.rolling_family(_somfy_frame(_somfy_plain(good_check=False))) is None

    def test_a_partial_keeloq_word_is_neither_labelled_nor_refused(self):
        """The Athom cannot hold a whole word (HARF, 11-16): a partial word
        is not a clean read, and it cannot open anything either."""
        partial = _kl_word(_kl_bits()[:40])
        assert rf_family.family_of(partial) is None
        assert rf_family.rolling_family(partial) is None

    @pytest.mark.parametrize("frame", [
        _pt_frame(0x5A5A5A), None, [],
    ], ids=["a fixed code", "none", "empty"])
    def test_everything_else_is_not(self, frame):
        assert rf_family.rolling_family(frame) is None

    def test_a_decoder_that_raises_lets_the_code_through_and_says_so(self, caplog):
        def broken(_frame):
            raise ZeroDivisionError

        with patch.object(rf_family, "_SHAPES", (broken,)), caplog.at_level(logging.WARNING):
            assert rf_family.rolling_family(KEELOQ) is None
        assert "rolling-code check failed" in caplog.text

    def test_an_infrared_row_is_never_rolling(self):
        row = types.SimpleNamespace(medium=MEDIUM_IR, raw_timings=list(KEELOQ))
        assert rolling_row(row) is None


# ---------------------------------------------------------------------------
# The air
# ---------------------------------------------------------------------------


class TestTheAir:
    @pytest.mark.parametrize("frame", [KEELOQ, SOMFY], ids=["keeloq", "somfy"])
    def test_a_rolling_row_is_refused_before_anything_else_is_asked(
        self, fake_hass, frame,
    ):
        """Before the transmitter checks: no list of transmitters, however
        good, gets a rolling code on the air."""
        with pytest.raises(SendRefusedError) as err:
            plan_radio_send(fake_hass, _row(frame), [], "Garage")
        assert err.value.code == RF_ROLLING_CODE

    def test_an_empty_row_still_says_it_has_no_code(self, fake_hass):
        with pytest.raises(SendRefusedError) as err:
            plan_radio_send(fake_hass, _row([]), [], "Garage")
        assert err.value.code == RF_NO_FRAME

    def test_a_fixed_code_goes_on_as_before(self, fake_hass, keyfob, radio):  # noqa: F811
        plan = plan_radio_send(fake_hass, _row(keyfob.frame), [ATHOM_TX], "Plug")
        assert plan.attempted

    def test_a_decoder_that_raises_does_not_stop_the_send(
        self, fake_hass, keyfob, radio,  # noqa: F811
    ):
        def broken(_frame):
            raise ZeroDivisionError

        with patch.object(rf_family, "_SHAPES", (broken,)):
            plan = plan_radio_send(fake_hass, _row(keyfob.frame), [ATHOM_TX], "Plug")
        assert plan.attempted


# ---------------------------------------------------------------------------
# The doors
# ---------------------------------------------------------------------------


def _monitor(fake_hass, keyfob, *frames):  # noqa: F811
    """A catalog remote holding the keyfob's fixed row and one row per
    frame given, and a target device."""
    from custom_components.hair.signal_monitor import SignalMonitor
    from custom_components.hair.tests.test_decoded_tx_consistency import (
        _make_hair_store,
        _make_signal_store,
    )

    store = _make_signal_store(fake_hass)  # noqa: F811
    hair_store = _make_hair_store()
    monitor = SignalMonitor(fake_hass, store, hair_store)
    rows = [_rf_signal(keyfob)]
    rows += [
        _rf_signal(keyfob, id=f"roll{i}", raw_timings=list(frame))
        for i, frame in enumerate(frames, start=1)
    ]
    store.add_device(UnknownDevice(
        id="ud1", fingerprint=keyfob.device_key, source="sniffed",
        medium=MEDIUM_RF, signals=rows,
    ))
    device = IRDevice(id="hd1", name="Garage")
    hair_store.get_device.return_value = device
    return monitor, device


class TestTheAssignDoors:
    @pytest.mark.asyncio
    async def test_assign_refuses(self, fake_hass, keyfob):  # noqa: F811
        monitor, device = _monitor(fake_hass, keyfob, KEELOQ)
        result = await monitor.assign_signal(
            "ud1", "roll1", "hd1", "Open", "custom",
        )
        assert result["success"] is False
        assert result["code"] == RF_ROLLING_CODE
        assert device.commands == []

    @pytest.mark.asyncio
    async def test_the_new_device_tab_refuses(self, fake_hass, keyfob):  # noqa: F811
        monitor, _ = _monitor(fake_hass, keyfob, SOMFY)
        result = await monitor.assign_to_new_device(
            device_id="ud1", signal_id="roll1", device_name="Blinds",
            device_type="switch", emitter_entity_ids=[ATHOM_TX],
            command_name="Up", command_category="custom",
        )
        assert result["success"] is False
        assert result["code"] == RF_ROLLING_CODE

    @pytest.mark.asyncio
    async def test_a_fixed_row_is_assigned_as_before(self, fake_hass, keyfob):  # noqa: F811
        monitor, device = _monitor(fake_hass, keyfob, KEELOQ)
        result = await monitor.assign_signal("ud1", "rf1", "hd1", "On", "custom")
        assert result["success"] is True
        assert [c.name for c in device.commands] == ["On"]


class TestMakeADevice:
    @pytest.mark.asyncio
    async def test_from_a_catalog_remote(self, fake_hass, keyfob):  # noqa: F811
        monitor, device = _monitor(fake_hass, keyfob, KEELOQ, SOMFY)
        result = await monitor.copy_signals_to_device("ud1", "hd1")
        assert result == {"success": True, "copied": 1, "rolling_left_out": 2}
        assert len(device.commands) == 1
        assert rolling_row(device.commands[0]) is None

    @pytest.mark.asyncio
    async def test_from_a_remote(
        self, fake_hass, store, catalog, keyfob, radio,  # noqa: F811
    ):
        """The rolling trigger stays on the Remote; the Device is made
        without it."""
        fixed = _radio_trigger(keyfob)
        rolling = _radio_trigger(keyfob, name="Open", raw_timings=list(KEELOQ))
        remote = _remote(store, fixed, rolling)
        _wire(fake_hass, store, catalog)
        device, result = await _make_device(fake_hass, store, remote.id)
        assert [c.name for c in device.commands] == ["Button 1 on"]
        assert result["rolling_left_out"] == 1
        assert len(store.get_triggers_for_remote(remote.id)) == 2

    def test_the_make_device_door_passes_the_count_on(self):
        from custom_components.hair import websocket_api as ws

        source = inspect.getsource(ws.ws_create_device)
        assert 'result["rolling_left_out"] = rolling_left_out' in source


class TestAdopt:
    def test_a_rolling_wig_row_mints_a_row_the_check_catches(self):
        from custom_components.hair.websocket_api import _command_from_wig_signal
        from custom_components.hair.wig_format import WigRf, WigSignal
        from custom_components.hair.wig_identity import wig_rf_identity

        frame = list(KEELOQ)
        gap = -frame.pop()
        sig = WigSignal("Open", "", rf=WigRf(433_920_000, frame, frame_gap_us=gap))
        command = _command_from_wig_signal(sig, wig_rf_identity(sig.rf), set(), {}, 1)
        assert rolling_row(command) == "keeloq"

    @pytest.mark.parametrize("name", ["ws_wig_make_device", "ws_wigs_supersede"])
    def test_adopt_and_its_top_up_check_before_they_add(self, name):
        from custom_components.hair import websocket_api as ws

        source = inspect.getsource(getattr(ws, name))
        check = source.index("rolling_row(command)")
        assert check < source.index("device.add_command(command)", check)


class TestTheExport:
    def test_a_rolling_row_is_left_out_and_named(self, keyfob):  # noqa: F811
        from custom_components.hair.wig_export import build_wig_from_device

        device = IRDevice(id="hd1", name="Garage")
        for name, frame in (("On", keyfob.frame), ("Open", KEELOQ)):
            command = IRCommand(name=name, category=CommandCategory.CUSTOM)
            command.medium = MEDIUM_RF
            command.raw_timings = list(frame)
            command.rf_frequency_hz = 433_920_000
            device.add_command(command)
        build = build_wig_from_device(device)
        assert [s.alias for s in build.wig.signals] == ["On"]
        assert build.skipped == 1
        assert any(n.startswith("Open is a rolling code") for n in build.notes)
        assert not any("trigger" in n for n in build.notes)


class TestTriggersStayAllowed:
    def test_the_trigger_doors_do_not_check(self):
        """A rolling row is a trigger by design: nothing on the way to one
        asks."""
        from custom_components.hair import signal_monitor, websocket_api

        for module, name in (
            (signal_monitor.SignalMonitor, "copy_signals_to_trigger_remote"),
            (websocket_api, "ws_create_trigger"),
        ):
            assert "rolling" not in inspect.getsource(getattr(module, name))


def test_the_message_says_why_and_promises_nothing():
    """The message is plain words, for the log and until the panel's own
    line; it makes no trigger promise until rolling triggers ship."""
    from custom_components.hair.const import RF_ROLLING_CODE_MESSAGE

    assert "rolling code" in RF_ROLLING_CODE_MESSAGE
    assert "never sends" in RF_ROLLING_CODE_MESSAGE
    assert "trigger" not in RF_ROLLING_CODE_MESSAGE


class TestThePanelIsToldFirst:
    """``rf_rolling`` on every radio row the panel gets, so a door can
    say it before the press (Gertrude, HARF, 2026-11-16)."""

    def _rows(self, keyfob):  # noqa: F811
        from custom_components.hair.websocket_api import _augment_rf_family

        rows = [
            {"medium": MEDIUM_RF, "raw_timings": list(KEELOQ)},
            {"medium": MEDIUM_RF, "raw_timings": list(SOMFY)},
            {"medium": MEDIUM_RF, "raw_timings": list(keyfob.frame)},
            {"medium": MEDIUM_IR, "raw_timings": list(KEELOQ)},
        ]
        _augment_rf_family(rows)
        return rows

    def test_each_radio_row_says_whether_it_is_rolling(self, keyfob):  # noqa: F811
        rows = self._rows(keyfob)
        assert [r.get("rf_rolling") for r in rows[:3]] == ["keeloq", "somfy_rts", None]
        assert "rf_rolling" not in rows[3]

    def test_a_decoder_that_raises_leaves_the_row_sendable(self, keyfob):  # noqa: F811
        def broken(_frame):
            raise ZeroDivisionError

        with patch.object(rf_family, "_SHAPES", (broken,)):
            rows = self._rows(keyfob)
        assert [r.get("rf_rolling") for r in rows[:3]] == [None, None, None]

    def test_the_detected_push_carries_it(self):
        from custom_components.hair import signal_monitor

        source = inspect.getsource(signal_monitor)
        assert 'summary["rf_rolling"] = rolling_family(signal.raw_timings)' in source
