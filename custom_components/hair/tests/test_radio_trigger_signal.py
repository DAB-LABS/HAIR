"""Radio triggers hold their own signal (owner ruling 2026-11-13).

A radio trigger used to hold only its identity, so "Make a Device" from a
radio Remote minted commands with nothing to send. Now every door that
makes a radio trigger writes the frame, the radio fields and the send
count onto it; "Make a Device" copies them back; a pass at setup fills
what was made before; and a press of the code fills what still waits.

The keyfob is the bench capture the radio send tests use. Every store
here is in memory.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair import models, rf_send
from custom_components.hair.const import (
    DOMAIN,
    MEDIUM_IR,
    MEDIUM_RF,
    RF_NO_FRAME,
    RF_PROTOCOL,
    CommandSource,
)
from custom_components.hair.identity import canonical_fingerprint
from custom_components.hair.ir_command import build_command
from custom_components.hair.mint import mint_command, mint_from_code
from custom_components.hair.models import (
    IRCommand,
    IRDevice,
    IRTrigger,
    TriggerRemote,
    UnknownDevice,
    copy_rf_signal,
    rf_needs_press,
)
from custom_components.hair.signal_monitor import SignalMonitor
from custom_components.hair.signal_store import SignalStore
from custom_components.hair.storage import HAIRStore
from custom_components.hair.tests.test_device_manager import (  # noqa: F401 (fixture)
    _FakeStore,
    manager,
)
from custom_components.hair.tests.test_rf_hear import _rf_signal
from custom_components.hair.tests.test_rf_send import (  # noqa: F401 (fixtures)
    ATHOM_TX,
    captures,
    keyfob,
    radio,
)
from custom_components.hair.tests.test_websocket_api import (
    _make_connection,
    _manager_for_device_creation,
)
from custom_components.hair.trigger_manager import TriggerManager
from custom_components.hair.websocket_api import (
    ws_create_trigger,
    ws_device_make_remote,
    ws_duplicate_trigger_remote,
    ws_trigger_remote_make_device,
    ws_wig_make_remote,
)
from custom_components.hair.wig_format import Wig, WigRf, WigSignal

PRONTO = "0000 006D 0002 0000 0020 0040 0020 0040"


# ---------------------------------------------------------------------------
# Rigs
# ---------------------------------------------------------------------------


@pytest.fixture
def store(fake_hass):
    with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
        hair = HAIRStore(fake_hass)
    hair._loaded = True
    hair.async_save = AsyncMock()
    return hair


@pytest.fixture
def catalog(fake_hass):
    cat = SignalStore(fake_hass)
    cat._loaded = True
    cat.schedule_save = MagicMock()
    cat.async_save = AsyncMock()
    return cat


def _file_row(catalog, signal, source="sniffed"):
    device = UnknownDevice(
        fingerprint="keyfob-card", protocol=RF_PROTOCOL, signals=[signal],
        source=source, medium=MEDIUM_RF,
    )
    catalog.add_device(device)
    catalog.index_signal(device, signal)
    return device


def _row(keyfob, **overrides):  # noqa: F811
    """The keyfob's button as a Sniffer row, with a count of its own."""
    overrides.setdefault("send_count", 6)
    return _rf_signal(keyfob, **overrides)


def _radio_command(keyfob, name="Button 1 on", **fields):  # noqa: F811
    command = IRCommand(name=name, protocol=RF_PROTOCOL)
    copy_rf_signal(_row(keyfob, **fields), command)
    command.byte_hash = keyfob.frame_hash
    return command


def _wire(hass, store, catalog=None, manager=None, monitor=None):  # noqa: F811
    hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager or _manager_for_device_creation(),
        "store": store,
        "signal_store": catalog,
        "signal_monitor": monitor or MagicMock(),
        "config_entry": SimpleNamespace(entry_id="entry-1"),
    }}
    return hass.data[DOMAIN]["entry-1"]


def _quiet():
    """The HA-side registrations every Remote door makes."""
    return [
        patch("custom_components.hair.websocket_api._register_trigger_remote_ha_device",
              return_value="ha-remote"),
        patch("custom_components.hair.event.sync_trigger_entities"),
        patch("custom_components.hair.event.sync_remote_entities"),
        patch("custom_components.hair.websocket_api.emitters_error", return_value=None),
    ]


class _Patched:
    def __init__(self, patches):
        self._patches = patches

    def __enter__(self):
        for p in self._patches:
            p.start()

    def __exit__(self, *exc):
        for p in reversed(self._patches):
            p.stop()


async def _make_device(hass, store, remote_id, emitters=(ATHOM_TX,)):
    data = hass.data[DOMAIN]["entry-1"]
    conn = _make_connection()
    with _Patched(_quiet()):
        await ws_trigger_remote_make_device(hass, conn, {
            "id": 1, "type": "hair/trigger-remote/make-device",
            "name": "Plug", "remote_id": remote_id,
            "device_type": "switch", "emitter_entity_ids": list(emitters),
        })
    conn.send_error.assert_not_called()
    device = data["device_manager"].async_create_device.call_args[0][0]
    return device, conn.send_result.call_args[0][1]


def _assert_sends_like(fake_hass, command, source):
    """The send path plans exactly the source's signal."""
    plan = rf_send.plan_radio_send(fake_hass, command, [ATHOM_TX], "Plug")
    assert plan.attempted
    assert command.raw_timings == list(source.raw_timings)
    assert command.rf_frequency_hz == source.rf_frequency_hz
    assert command.rf_frame_gap_us == source.rf_frame_gap_us
    assert command.send_count == source.send_count
    assert plan.count == rf_send.send_count_for(command, plan.timings)


def _remote(store, *triggers, name="Keyfob"):
    remote = TriggerRemote(name=name)
    store.add_trigger_remote(remote)
    for trig in triggers:
        trig.trigger_remote_id = remote.id
        store.add_trigger(trig)
    return remote


def _radio_trigger(keyfob, name="Button 1 on", **fields):  # noqa: F811
    trig = IRTrigger(
        name=name, signal_fingerprint=keyfob.fingerprint,
        protocol=RF_PROTOCOL, byte_hash=keyfob.frame_hash,
    )
    if fields.pop("whole", True):
        copy_rf_signal(_row(keyfob, **fields), trig)
    return trig


# ---------------------------------------------------------------------------
# The model
# ---------------------------------------------------------------------------


class TestTheModel:
    def test_radio_trigger_round_trips(self, keyfob):  # noqa: F811
        trig = _radio_trigger(keyfob)
        back = IRTrigger.from_dict(json.loads(json.dumps(trig.to_dict())))
        assert back.raw_timings == trig.raw_timings
        assert back.send_count == 6
        for name in models.RF_ROW_FIELDS:
            assert getattr(back, name) == getattr(trig, name), name
        assert back.to_dict() == trig.to_dict()

    def test_radio_trigger_survives_an_older_build(self, keyfob, monkeypatch):  # noqa: F811
        """v1.2.0 knows ``medium`` and nothing else radio: the new keys
        ride in ``_extra`` and are written back by its save."""
        record = _radio_trigger(keyfob).to_dict()
        old_known = frozenset(
            k for k in models._KNOWN_TRIGGER
            if k == "medium" or k not in (*models._RF_KNOWN, "raw_timings", "send_count")
        )
        monkeypatch.setattr(models, "_KNOWN_TRIGGER", old_known)
        monkeypatch.setattr(models, "_trigger_rf_out", lambda t: {"medium": MEDIUM_RF})
        monkeypatch.setattr(models, "_trigger_rf_in", lambda d: {"medium": MEDIUM_RF})
        older = IRTrigger.from_dict(record)
        assert older.raw_timings is None  # the old build cannot read it
        saved = older.to_dict()
        assert saved["raw_timings"] == record["raw_timings"]
        assert saved["send_count"] == 6
        monkeypatch.undo()
        assert IRTrigger.from_dict(saved).raw_timings == record["raw_timings"]

    def test_infrared_trigger_record_is_byte_for_byte(self):
        trig = IRTrigger(
            id="t1", name="Power", signal_fingerprint="fp", protocol="PRONTO",
            code=PRONTO, created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        )
        assert sorted(trig.to_dict()) == sorted([
            "id", "name", "signal_fingerprint", "protocol", "code", "min_hits",
            "enabled", "source_device_id", "source_command_id", "created_at",
            "updated_at", "receiver_entity_ids", "byte_hash",
            "decoded_fingerprint", "order", "alias_history", "fire_count",
            "last_fired_at", "trigger_remote_id", "origin",
        ])
        assert IRTrigger.from_dict(trig.to_dict()).medium == MEDIUM_IR

    def test_a_v120_radio_trigger_loads_waiting(self, keyfob):  # noqa: F811
        record = {
            "id": "t1", "name": "B", "signal_fingerprint": keyfob.fingerprint,
            "protocol": RF_PROTOCOL, "code": None, "byte_hash": keyfob.frame_hash,
            "medium": MEDIUM_RF,
        }
        trig = IRTrigger.from_dict(record)
        assert trig.medium == MEDIUM_RF and rf_needs_press(trig)

    def test_no_mint_path_returns_a_radio_protocol_marked_infrared(self):
        for command in (
            mint_from_code(name="x", protocol=RF_PROTOCOL, code=None),
            mint_command(name="x", protocol=RF_PROTOCOL),
            IRCommand(protocol=RF_PROTOCOL),
            IRCommand.from_dict({"protocol": RF_PROTOCOL, "medium": "ir"}),
        ):
            assert command.medium == MEDIUM_RF

    def test_a_capture_gives_the_count_its_press_carried(self, keyfob):  # noqa: F811
        capture = SimpleNamespace(
            medium=MEDIUM_RF, raw_timings=list(keyfob.frame),
            rf_repeats_observed=5,
            **{n: None for n in models.RF_ROW_FIELDS if n != "rf_repeats_observed"},
        )
        trig = IRTrigger(protocol=RF_PROTOCOL)
        copy_rf_signal(capture, trig)
        assert trig.send_count == rf_send.seed_send_count(5)


# ---------------------------------------------------------------------------
# Each door, then "Make a Device"
# ---------------------------------------------------------------------------


async def _promote(fake_hass, store, catalog, source):
    row = _row(fake_hass.keyfob)
    card = _file_row(catalog, row, source=source)
    remote = _remote(store)
    monitor = SignalMonitor(fake_hass, catalog, store)
    result = await monitor.copy_signals_to_trigger_remote(card.id, remote.id)
    assert result["success"]
    return remote, row


class TestTheDoors:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("source", ["sniffed", "manual"])
    async def test_sniffer_and_clipper_radio_remote_make_a_device_that_sends(
        self, fake_hass, store, catalog, keyfob, radio, source,  # noqa: F811
    ):
        """``manual`` is the Clipper's catalog source; the Plucker's goes
        through the same door."""
        fake_hass.keyfob = keyfob
        remote, row = await _promote(fake_hass, store, catalog, source)
        (trig,) = store.get_triggers_for_remote(remote.id)
        assert not rf_needs_press(trig)
        _wire(fake_hass, store, catalog)
        device, result = await _make_device(fake_hass, store, remote.id)
        (command,) = device.commands
        assert command.medium == MEDIUM_RF and command.protocol == RF_PROTOCOL
        assert command.byte_hash == keyfob.frame_hash
        _assert_sends_like(fake_hass, command, row)
        assert result["needs_press"] == []

    @pytest.mark.asyncio
    async def test_mixed_remote_makes_both_kinds(self, fake_hass, store, keyfob, radio):  # noqa: F811
        ir = IRTrigger(
            name="Power", protocol="PRONTO", code=PRONTO,
            signal_fingerprint=canonical_fingerprint("PRONTO", PRONTO, None),
        )
        remote = _remote(store, ir, _radio_trigger(keyfob))
        _wire(fake_hass, store)
        device, _ = await _make_device(fake_hass, store, remote.id, [ATHOM_TX, "infrared.e"])
        power, button = device.commands
        assert power.medium == MEDIUM_IR and power.raw_timings
        assert button.medium == MEDIUM_RF
        _assert_sends_like(fake_hass, button, _row(keyfob))

    @pytest.mark.asyncio
    async def test_infrared_make_device_unchanged(self, fake_hass, store):
        ir = IRTrigger(name="Power", protocol="PRONTO", code=PRONTO, byte_hash="bh1")
        remote = _remote(store, ir)
        _wire(fake_hass, store)
        device, _ = await _make_device(fake_hass, store, remote.id, ["infrared.e"])
        expected = mint_from_code(
            name="Power", protocol="PRONTO", code=PRONTO, byte_hash="bh1",
            claimed_fingerprint=None, source=CommandSource.CAPTURED,
        )
        got = device.commands[0].to_dict()
        want = expected.to_dict()
        for key in ("id", "created_at"):
            got.pop(key)
            want.pop(key)
        assert got == want

    @pytest.mark.asyncio
    async def test_device_to_remote_to_device_still_sends(
        self, fake_hass, store, keyfob, radio,  # noqa: F811
    ):
        source = IRDevice(name="Plug", commands=[_radio_command(keyfob)])
        store.add_device(source)
        manager = _manager_for_device_creation()  # noqa: F811
        manager.get_device = MagicMock(return_value=source)
        data = _wire(fake_hass, store, manager=manager)
        conn = _make_connection()
        with _Patched(_quiet()):
            await ws_device_make_remote(fake_hass, conn, {
                "id": 2, "type": "hair/device/make-remote",
                "device_id": source.id, "name": "Plug remote",
            })
        remote_id = conn.send_result.call_args[0][1]["id"]
        (trig,) = store.get_triggers_for_remote(remote_id)
        assert trig.raw_timings == source.commands[0].raw_timings
        data["device_manager"] = _manager_for_device_creation()
        device, _ = await _make_device(fake_hass, store, remote_id)
        _assert_sends_like(fake_hass, device.commands[0], source.commands[0])

    @pytest.mark.asyncio
    async def test_wig_to_remote_to_device_still_sends(self, fake_hass, store, keyfob, radio):  # noqa: F811
        frame = list(keyfob.frame)
        while frame and frame[-1] < 0:
            frame.pop()
        wig = Wig(name="Keyfob", signals=[WigSignal(
            "Button 1", "", send_count=5,
            rf=WigRf(433_920_000, frame, frame_gap_us=10_850),
        )])
        _wire(fake_hass, store)
        conn = _make_connection()
        with _Patched([
            *_quiet(),
            patch("custom_components.hair.wig_store.load_wig", return_value=wig),
            patch("custom_components.hair.wig_store.backfill_wig_id", return_value=None),
        ]):
            await ws_wig_make_remote(fake_hass, conn, {
                "id": 3, "type": "hair/wigs/make-remote",
                "filename": "keyfob.wig", "name": "Keyfob",
            })
        conn.send_error.assert_not_called()
        remote_id = conn.send_result.call_args[0][1]["id"]
        (trig,) = store.get_triggers_for_remote(remote_id)
        assert trig.send_count == 5 and trig.rf_frame_gap_us == 10_850
        device, _ = await _make_device(fake_hass, store, remote_id)
        command = device.commands[0]
        assert rf_send.plan_radio_send(fake_hass, command, [ATHOM_TX], "Plug").attempted
        assert command.raw_timings == trig.raw_timings and command.send_count == 5

    @pytest.mark.asyncio
    async def test_duplicated_radio_remote_keeps_its_frames(self, fake_hass, store, keyfob):  # noqa: F811
        source = _remote(store, _radio_trigger(keyfob))
        _wire(fake_hass, store)
        conn = _make_connection()
        with _Patched(_quiet()):
            await ws_duplicate_trigger_remote(fake_hass, conn, {
                "id": 4, "type": "hair/trigger-remote/duplicate",
                "remote_id": source.id, "new_name": "Copy",
            })
        conn.send_error.assert_not_called()
        copies = [
            t for t in store.get_all_triggers() if t.trigger_remote_id != source.id
        ]
        assert len(copies) == 1
        assert copies[0].raw_timings == list(keyfob.frame)
        assert copies[0].send_count == 6

    @pytest.mark.asyncio
    @pytest.mark.parametrize("where", ["command", "row", "neither"])
    async def test_create_trigger_radio_fills(self, fake_hass, store, catalog, keyfob, where):  # noqa: F811
        msg = {
            "id": 5, "type": "hair/trigger/create", "name": "Button 1 on",
            "signal_fingerprint": keyfob.fingerprint, "protocol": RF_PROTOCOL,
            "byte_hash": keyfob.frame_hash,
        }
        manager = MagicMock()  # noqa: F811
        if where == "command":
            device = IRDevice(name="Plug", commands=[_radio_command(keyfob)])
            manager.get_device = MagicMock(return_value=device)
            msg["source_device_id"] = device.id
            msg["source_command_id"] = device.commands[0].id
        elif where == "row":
            _file_row(catalog, _row(keyfob))
        _wire(fake_hass, store, catalog, manager=manager)
        conn = _make_connection()
        with _Patched(_quiet()):
            await ws_create_trigger(fake_hass, conn, msg)
        conn.send_error.assert_not_called()
        (trig,) = store.get_all_triggers()
        if where == "neither":
            assert rf_needs_press(trig)
        else:
            assert trig.raw_timings == list(keyfob.frame) and trig.send_count == 6

    @pytest.mark.asyncio
    async def test_make_device_mints_a_waiting_trigger_flagged_and_lists_it(
        self, fake_hass, store, keyfob, radio,  # noqa: F811
    ):
        waiting = _radio_trigger(keyfob, name="Button 2", whole=False)
        remote = _remote(store, _radio_trigger(keyfob), waiting)
        _wire(fake_hass, store)
        device, result = await _make_device(fake_hass, store, remote.id)
        assert [c.name for c in device.commands] == ["Button 1 on", "Button 2"]
        flagged = device.commands[1]
        assert flagged.medium == MEDIUM_RF and flagged.protocol == RF_PROTOCOL
        assert flagged.byte_hash == keyfob.frame_hash and not flagged.raw_timings
        assert result["needs_press"] == [{"command_id": flagged.id, "name": "Button 2"}]
        assert result["copied"] == 2
        with pytest.raises(rf_send.SendRefusedError) as caught:
            rf_send.plan_radio_send(fake_hass, flagged, [ATHOM_TX], "Plug")
        assert caught.value.code == RF_NO_FRAME


# ---------------------------------------------------------------------------
# Edits
# ---------------------------------------------------------------------------


class TestEdits:
    @pytest.mark.asyncio
    async def test_radio_edit_rewire_carries_the_new_frame(self, fake_hass, store, keyfob):  # noqa: F811
        trig = _radio_trigger(keyfob)
        store.add_trigger(trig)
        manager = TriggerManager(fake_hass, store, MagicMock())  # noqa: F811
        edited = _row(keyfob, rf_frame_gap_us=12_345, send_count=3)
        edited.raw_timings = [*keyfob.frame[:-1], -12_345]
        await manager.rewire(
            keyfob.fingerprint, "new-fp", RF_PROTOCOL, None,
            old_byte_hash=keyfob.frame_hash, new_byte_hash="new-hash",
            source_row=edited,
        )
        assert trig.raw_timings == edited.raw_timings
        assert trig.rf_frame_gap_us == 12_345 and trig.send_count == 3
        assert trig.byte_hash == "new-hash"

    @pytest.mark.asyncio
    async def test_infrared_rewire_takes_no_row(self, fake_hass, store):
        trig = IRTrigger(name="P", signal_fingerprint="fp", protocol="PRONTO", code=PRONTO)
        store.add_trigger(trig)
        await TriggerManager(fake_hass, store, MagicMock()).rewire(
            "fp", "fp2", "PRONTO", PRONTO, source_row=_row(SimpleNamespace(
                fingerprint="x", frame_hash="y", frame=[1, -2], votes=1, gap_us=None,
                gap_source=None, header_shape=None, short_mark_us=None,
            )),
        )
        assert trig.raw_timings is None and trig.medium == MEDIUM_IR

    @pytest.mark.asyncio
    async def test_frequency_edit_leaves_triggers_alone(self, manager, keyfob):  # noqa: F811
        """A frequency-only edit changes no identity, so nothing is
        rewired, and records are self-contained copies (ruling,
        2026-11-13)."""
        command = _radio_command(keyfob)
        device = IRDevice(name="Plug", commands=[command])
        manager._store.add_device(device)
        trig = _radio_trigger(keyfob)
        manager._store.add_trigger(trig)
        tm = MagicMock()
        tm.rewire = AsyncMock()
        result = await manager.async_update_command(
            device.id, command.id, rf_frequency_hz=315_000_000,
            trigger_manager=tm,
        )
        assert result["success"], result
        assert command.rf_frequency_hz == 315_000_000
        tm.rewire.assert_not_awaited()
        assert trig.rf_frequency_hz == 433_920_000


# ---------------------------------------------------------------------------
# The repair pass at setup
# ---------------------------------------------------------------------------


def _broken_command(keyfob, name="Button 1 on"):  # noqa: F811
    """What "Make a Device" minted from a radio Remote before the fix,
    as v1.2.0 stored it."""
    record = mint_from_code(name=name, protocol=RF_PROTOCOL, code=None,
                            byte_hash=keyfob.frame_hash).to_dict()
    record["medium"] = "ir"
    for key in list(record):
        if key.startswith("rf_") or key == "band":
            record.pop(key)
    return IRCommand.from_dict(record)


class TestTheRepair:
    def test_repair_fills_trigger_from_row(self, store, catalog, keyfob):  # noqa: F811
        _file_row(catalog, _row(keyfob))
        trig = _radio_trigger(keyfob, whole=False)
        store.add_trigger(trig)
        assert store.repair_radio_signals(catalog) is True
        assert trig.raw_timings == list(keyfob.frame) and trig.send_count == 6

    def test_repair_fills_trigger_from_command(self, store, catalog, keyfob):  # noqa: F811
        store.add_device(IRDevice(name="Plug", commands=[_radio_command(keyfob)]))
        trig = _radio_trigger(keyfob, whole=False)
        store.add_trigger(trig)
        assert store.repair_radio_signals(catalog) is True
        assert trig.raw_timings == list(keyfob.frame)

    def test_repair_prefers_the_row_to_a_command(self, store, catalog, keyfob):  # noqa: F811
        """The Sniffer row is what the air said; a device command may have
        been edited since. Each holds a different count here."""
        _file_row(catalog, _row(keyfob, send_count=6))
        store.add_device(IRDevice(name="Plug", commands=[
            _radio_command(keyfob, send_count=3),
        ]))
        trig = _radio_trigger(keyfob, whole=False)
        store.add_trigger(trig)
        store.repair_radio_signals(catalog)
        assert trig.send_count == 6

    def test_repair_flags_when_neither(self, store, catalog, keyfob):  # noqa: F811
        trig = _radio_trigger(keyfob, whole=False)
        store.add_trigger(trig)
        assert store.repair_radio_signals(catalog) is False
        assert rf_needs_press(trig)

    def test_repair_mends_device_command(self, store, catalog, keyfob):  # noqa: F811
        broken = _broken_command(keyfob)
        assert broken.medium == MEDIUM_RF  # read off the protocol on load
        store.add_device(IRDevice(name="Plug", commands=[broken]))
        _file_row(catalog, _row(keyfob))
        assert store.repair_radio_signals(catalog) is True
        assert broken.raw_timings == list(keyfob.frame)
        assert broken.send_count == 6 and broken.rf_frequency_hz == 433_920_000

    def test_repair_mends_a_command_from_a_filled_trigger(self, store, catalog, keyfob):  # noqa: F811
        broken = _broken_command(keyfob)
        store.add_device(IRDevice(name="Plug", commands=[broken]))
        store.add_trigger(_radio_trigger(keyfob))
        assert store.repair_radio_signals(catalog) is True
        assert broken.raw_timings == list(keyfob.frame)

    def test_repair_ignores_the_broken_command_in_the_index(self, store, catalog, keyfob):  # noqa: F811
        """The empty command shares the code and comes first; the source
        is the device command that holds the frame."""
        store.add_device(IRDevice(name="Made", commands=[_broken_command(keyfob)]))
        store.add_device(IRDevice(name="Plug", commands=[_radio_command(keyfob)]))
        trig = _radio_trigger(keyfob, whole=False)
        store.add_trigger(trig)
        store.repair_radio_signals(catalog)
        assert trig.raw_timings == list(keyfob.frame)

    def test_repair_is_idempotent(self, store, catalog, keyfob):  # noqa: F811
        _file_row(catalog, _row(keyfob))
        store.add_trigger(_radio_trigger(keyfob, whole=False))
        store.add_device(IRDevice(name="Plug", commands=[_broken_command(keyfob)]))
        assert store.repair_radio_signals(catalog) is True
        before = json.dumps(store._serialize(), sort_keys=True)
        assert store.repair_radio_signals(catalog) is False
        assert json.dumps(store._serialize(), sort_keys=True) == before

    def test_nothing_waiting_costs_one_walk(self, store, keyfob, caplog):  # noqa: F811
        """No waiting row: no catalog lookup, no index built, no save, and
        nothing logged above DEBUG."""
        store.add_trigger(_radio_trigger(keyfob))
        store.add_trigger(IRTrigger(name="P", protocol="PRONTO", code=PRONTO))
        store.add_device(IRDevice(name="Plug", commands=[_radio_command(keyfob)]))
        catalog = MagicMock()
        store._rebuild_command_index = MagicMock()
        store._radio_frames_by_hash = MagicMock(return_value={})
        with caplog.at_level("INFO", logger="custom_components.hair.storage"):
            assert store.repair_radio_signals(catalog) is False
        catalog.find_filed_signal.assert_not_called()
        store._radio_frames_by_hash.assert_not_called()
        store._rebuild_command_index.assert_not_called()
        assert not caplog.records

    def test_old_store_with_no_radio_triggers_is_untouched(self, store, catalog):
        store.add_trigger(IRTrigger(name="P", protocol="PRONTO", code=PRONTO))
        store.add_device(IRDevice(name="TV", commands=[IRCommand(
            name="Power", protocol="PRONTO", code=PRONTO,
        )]))
        before = json.dumps(store._serialize(), sort_keys=True)
        assert store.repair_radio_signals(catalog) is False
        assert json.dumps(store._serialize(), sort_keys=True) == before

    @pytest.mark.asyncio
    async def test_setup_saves_through_the_guarded_save(self, fake_hass, catalog, keyfob):  # noqa: F811
        """The pass's save is the store's own, which reports a refused
        write once rather than swallowing it."""
        with patch("custom_components.hair.storage._HAIRDeviceStore", _FakeStore):
            hair = HAIRStore(fake_hass)
        hair._loaded = True
        hair._health.guarded_save = AsyncMock()
        _file_row(catalog, _row(keyfob))
        hair.add_trigger(_radio_trigger(keyfob, whole=False))
        assert hair.repair_radio_signals(catalog)
        await hair.async_save()
        hair._health.guarded_save.assert_awaited_once()


# ---------------------------------------------------------------------------
# The next press
# ---------------------------------------------------------------------------


def _press(keyfob):  # noqa: F811
    return SimpleNamespace(
        medium=MEDIUM_RF, raw_timings=list(keyfob.frame),
        rf_frequency_hz=433_920_000, rf_frequency_source="window",
        rf_modulation="OOK", rf_frame_hash=keyfob.frame_hash,
        rf_repeats_observed=keyfob.votes, rf_frame_gap_us=keyfob.gap_us,
        rf_frame_gap_source=keyfob.gap_source, rf_header_shape=keyfob.header_shape,
        rf_short_mark_us=keyfob.short_mark_us,
    )


class TestTheNextPress:
    def test_press_fills_a_waiting_trigger_and_its_commands(self, store, keyfob):  # noqa: F811
        trig = _radio_trigger(keyfob, whole=False)
        store.add_trigger(trig)
        broken = _broken_command(keyfob)
        store.add_device(IRDevice(name="Plug", commands=[broken]))
        assert store.fill_waiting_radio(
            _press(keyfob), keyfob.fingerprint, keyfob.frame_hash
        ) == 2
        assert trig.raw_timings == list(keyfob.frame)
        assert broken.raw_timings == list(keyfob.frame)
        assert trig.send_count == rf_send.seed_send_count(keyfob.votes)

    def test_press_fills_disabled_and_other_scope_triggers(self, store, keyfob):  # noqa: F811
        """Same code, so filled; filling fires nothing."""
        off = _radio_trigger(keyfob, whole=False)
        off.enabled = False
        scoped = _radio_trigger(keyfob, whole=False)
        scoped.receiver_entity_ids = ["radio_frequency.elsewhere"]
        for trig in (off, scoped):
            store.add_trigger(trig)
        store.fill_waiting_radio(_press(keyfob), keyfob.fingerprint, keyfob.frame_hash)
        assert not rf_needs_press(off) and not rf_needs_press(scoped)
        assert off.fire_count == 0 and scoped.fire_count == 0

    def test_a_press_of_another_code_fills_nothing(self, store, keyfob):  # noqa: F811
        trig = _radio_trigger(keyfob, whole=False)
        store.add_trigger(trig)
        assert store.fill_waiting_radio(_press(keyfob), "other-fp", "other-hash") == 0
        assert rf_needs_press(trig)

    def test_a_burst_of_presses_is_one_save(self, fake_hass, store, keyfob):  # noqa: F811
        monitor = SignalMonitor(fake_hass, MagicMock(), store)
        handles = []

        def call_later(delay, cb):
            handle = MagicMock()
            handle.callback = cb
            handles.append(handle)
            return handle

        fake_hass.loop.call_later = MagicMock(side_effect=call_later)
        store.add_trigger(_radio_trigger(keyfob, whole=False))
        store.add_trigger(_radio_trigger(keyfob, name="B2", whole=False))
        store.fill_waiting_radio = MagicMock(return_value=1)
        for _ in range(3):
            monitor._fill_waiting_radio(_press(keyfob), keyfob.fingerprint, keyfob.frame_hash)
        assert len(handles) == 3
        assert all(h.cancel.called for h in handles[:2])
        assert not handles[2].cancel.called
        store.async_save.assert_not_called()
        fake_hass.async_create_task = MagicMock(side_effect=lambda coro: coro.close())
        handles[2].callback()
        store.async_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_a_heard_press_fills_through_the_capture_path(
        self, fake_hass, store, catalog, keyfob, captures,  # noqa: F811
    ):
        """End to end: the keyfob heard on a radio receiver fills the
        Remote's waiting button and the device command made from it."""
        from custom_components.hair.tests.test_rf_hear import TestHearing

        trig = _radio_trigger(keyfob, whole=False)
        store.add_trigger(trig)
        broken = _broken_command(keyfob)
        store.add_device(IRDevice(name="Plug", commands=[broken]))
        monitor = SignalMonitor(fake_hass, catalog, store)
        await TestHearing()._hear(fake_hass, captures[:1], monitor)
        assert trig.raw_timings == list(keyfob.frame)
        assert broken.raw_timings == list(keyfob.frame)

    def test_the_echo_path_fills_nothing(self):
        """The fill sits behind the echo return in the capture path."""
        import inspect

        source = inspect.getsource(SignalMonitor._process_parsed_signal)
        echo = source.index("        if echo:\n")
        fill = source.index("self._fill_waiting_radio(")
        assert echo < fill < source.index("on_signal_captured(")


# ---------------------------------------------------------------------------
# The refusals
# ---------------------------------------------------------------------------


class TestTheRefusal:
    def test_empty_radio_command_refuses_in_radio_words_radio_path(self, fake_hass, radio):  # noqa: F811
        command = IRCommand(name="B", protocol=RF_PROTOCOL)
        with pytest.raises(rf_send.SendRefusedError) as caught:
            rf_send.plan_radio_send(fake_hass, command, [ATHOM_TX], "Plug")
        assert caught.value.code == RF_NO_FRAME
        assert "no code to send" in str(caught.value)
        assert "frequency" not in str(caught.value)

    def test_empty_radio_command_refuses_in_radio_words_infrared_path(self):
        with pytest.raises(ValueError) as caught:
            build_command(protocol=RF_PROTOCOL, code=None, raw_timings=None)
        assert "radio command has no code to send" in str(caught.value)
        assert "IR" not in str(caught.value)

    def test_the_infrared_refusal_is_unchanged(self):
        with pytest.raises(ValueError) as caught:
            build_command(protocol="NEC", code=None, raw_timings=None)
        assert str(caught.value) == (
            "Cannot build IR command: no Pronto hex code and no raw timings"
        )
