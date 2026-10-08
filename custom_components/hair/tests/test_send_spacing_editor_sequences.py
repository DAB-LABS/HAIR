"""The editor's own calls keep the box, the record and the send agreeing.

The signal editor works a spacing out for one length and saves it with
that length (fix round of review M1). Each test here drives the real
websocket doors in the order ``ir-signal-editor.ts`` calls them, through
``_Editor``, a call-for-call stand-in for the editor's spacing code
(``_refreshSpacingInfo``, ``_onSpacingInput``, ``_onSendCountInput``,
``_onDittoInput``, the Bypass toggle and ``_save``): spacing info on
open, again on every change of code, count, ditto count or Bypass, then
Save. At the end the number in the box, the length the door recorded and
the spacing the real send plans must agree. The frontend has no test
runner, so ``TestTheEditorSource`` pins the TypeScript to the stand-in.
"""
from __future__ import annotations

import dataclasses
import functools
import gzip
import json
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair.const import (
    DOMAIN,
    SEND_AIR_TIME_MAX_MS,
    CommandSource,
)
from custom_components.hair.decoders.apple import AppleCommand
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
    estimate_spacing_ms,
    plausible_block_us,
    realised_air_ms,
    silence_us,
)
from custom_components.hair.tests.test_send_spacing_restated import (
    FIXTURES,
    OLD_DREO_SPACING,
    WIGS,
    _dreo,
    _row,
    _sony_row,
)
from custom_components.hair.websocket_api import (
    _pronto_frequency,
    _spacing_row_for_pronto,
    ws_clip_create_signal,
    ws_command_update,
    ws_send_spacing_info,
    ws_set_command_tx_force_raw,
    ws_unknown_signal_edit_pronto,
)

SRC = Path(__file__).parents[1] / "frontend" / "src"
# ir-tx-knobs.ts DITTO_PROTOCOLS: the only protocols whose ditto knob is on.
DITTO_PROTOCOLS = {"NEC", "APPLE"}


def _ok(conn) -> dict:
    assert not conn.send_error.called, conn.send_error.call_args
    return conn.send_result.call_args[0][1]


class _Editor:
    """ir-signal-editor.ts's spacing code, call for call."""

    def __init__(self, hass, *, device_id, row, command_id=None,
                 signal_id=None):
        self.hass = hass
        self.device_id = device_id
        self.command_id = command_id
        self.signal_id = signal_id
        self.is_command = command_id is not None
        # firstUpdated
        self.name = getattr(row, "name", None) or getattr(row, "alias", "")
        self.initial_pronto = row.code
        self.pronto = row.code
        self.initial_spacing = row.send_spacing_ms
        self.box = row.send_spacing_ms
        self.block = row.send_spacing_block_us
        self.count = row.send_count
        self.initial_ditto = row.repeat_count
        self.ditto = row.repeat_count
        self.initial_bypass = bool(row.tx_force_raw)
        self.bypass = self.initial_bypass
        self.protocol = row.decoded_protocol
        self.typed = False
        self.restated = False
        self.info: dict | None = None

    # ---- getters --------------------------------------------------------
    @property
    def payload(self):  # _spacingPayload
        return None if self.count <= 1 else self.box

    @property
    def block_for_save(self):  # _spacingBlockForSave
        return None if self.payload is None else self.block

    @property
    def ditto_disabled(self) -> bool:  # _dittoCountDisabled
        bypass = self.bypass if self.is_command else self.initial_bypass
        return bypass or (self.protocol or "").upper() not in DITTO_PROTOCOLS

    # ---- _refreshSpacingInfo -------------------------------------------
    def ask(self) -> dict:
        payload = self.payload
        before = self.box
        untouched = (
            not self.typed and payload is not None
            and payload == self.initial_spacing
        )
        restate = payload is not None and (self.block is not None or untouched)
        conn = MagicMock()
        ws_send_spacing_info(self.hass, conn, {
            "id": 1, "type": "hair/send_spacing_info",
            "pronto": self.pronto or None,
            "repeat_count": (
                self.initial_ditto if self.ditto_disabled else self.ditto
            ),
            "tx_force_raw": self.bypass,
            "send_count": self.count,
            "send_spacing_ms": payload,
            "send_spacing_block_us": self.block if restate else None,
            "restate": restate,
            "device_id": self.device_id if self.is_command else None,
            "command_id": self.command_id if self.is_command else None,
        })
        info = _ok(conn)
        self.info = info
        if (
            payload is not None and self.box == before
            and info["block_us"] is not None
        ):
            if restate and info["restated"] and info["effective_ms"] is not None:
                self.box = info["effective_ms"]
                self.restated = True
            self.block = info["block_us"]
        if self.box is None and self.count > 1 and info["estimate_ms"] is not None:
            self.box = info["estimate_ms"]
            self.block = info["block_us"]
        return info

    # ---- inputs ---------------------------------------------------------
    def type(self, value: int) -> None:  # _onSpacingInput
        self.box = value
        self.restated = False
        self.typed = True
        self.block = None
        self.ask()

    def type_unanswered(self, value: int) -> None:
        """_onSpacingInput with its answer still on the way."""
        self.box = value
        self.restated = False
        self.typed = True
        self.block = None

    def set_count(self, value: int) -> None:  # _onSendCountInput
        before = self.count
        self.count = max(1, min(value, 10))
        if (before <= 1) != (self.count <= 1) or self.box is not None:
            self.ask()

    def set_ditto(self, value: int) -> None:  # _onDittoInput
        self.ditto = max(0, min(value, 20))
        self.ask()

    def toggle_bypass(self) -> None:  # @toggle-bypass
        self.bypass = not self.bypass
        self.ask()

    def set_code(self, code: str) -> None:  # _onProntoInput, then _validate
        self.pronto = code
        if self.is_command:  # _syncPinToPronto
            self.bypass = (
                self.initial_bypass
                if code.strip() == self.initial_pronto.strip() else False
            )
        ident = try_decode_identity(ProntoCommand(code).get_raw_timings())
        self.protocol = ident.protocol if ident is not None else None
        self.ask()

    # ---- _save ----------------------------------------------------------
    async def save(self) -> None:
        ditto = None if self.ditto_disabled else self.ditto
        conn = MagicMock()
        if self.is_command:
            msg = {
                "id": 2, "type": "hair/command/update",
                "device_id": self.device_id, "command_id": self.command_id,
                "name": self.name, "pronto": self.pronto,
                "send_count": self.count,
                "send_spacing_ms": self.payload,
                "send_spacing_block_us": self.block_for_save,
            }
            if ditto is not None:
                msg["repeat_count"] = ditto
            await ws_command_update(self.hass, conn, msg)
            _ok(conn)
            # The pin rides its own command, after the content.
            if self.bypass != self.initial_bypass:
                pin = MagicMock()
                await ws_set_command_tx_force_raw(self.hass, pin, {
                    "id": 3, "type": "hair/command/set-tx-force-raw",
                    "device_id": self.device_id,
                    "command_id": self.command_id,
                    "tx_force_raw": self.bypass,
                })
                assert not pin.send_error.called
            return
        msg = {
            "id": 2, "device_id": self.device_id, "pronto": self.pronto,
            "alias": self.name, "send_count": self.count,
            "send_spacing_ms": self.payload,
            "send_spacing_block_us": self.block_for_save,
        }
        if ditto is not None:
            msg["repeat_count"] = ditto
        if self.signal_id is not None:
            msg.update(type="hair/unknown/signal/edit-pronto",
                       signal_id=self.signal_id)
            await ws_unknown_signal_edit_pronto(self.hass, conn, msg)
        else:
            msg["type"] = "hair/clip/create-signal"
            await ws_clip_create_signal(self.hass, conn, msg)
        _ok(conn)


# ---------------------------------------------------------------------------
# The rig: real doors, a real device manager and signal monitor
# ---------------------------------------------------------------------------


@pytest.fixture
def rig(fake_hass):
    from custom_components.hair.signal_monitor import SignalMonitor
    from custom_components.hair.tests.test_decoded_tx_consistency import (
        _make_device_manager,
        _make_hair_store,
        _make_signal_store,
    )

    manager = _make_device_manager(fake_hass)
    signal_store = _make_signal_store(fake_hass)
    monitor = SignalMonitor(fake_hass, signal_store, _make_hair_store())
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager,
        "store": manager._store,
        "signal_store": signal_store,
        "signal_monitor": monitor,
        "trigger_manager": SimpleNamespace(rewire=AsyncMock(
            return_value={"rewired": [], "skipped": []}
        )),
    }}
    def _close(coro, *args, **kwargs):
        # The Mirror's bookkeeping is scheduled, not awaited, and is not
        # what these tests are about.
        coro.close()

    with (
        patch.object(signal_store, "async_save", AsyncMock()),
        patch.object(fake_hass, "async_create_task", side_effect=_close),
        # An emitter that holds an exact spacing, so no door refuses one.
        patch(
            "custom_components.hair.send_plan.emitter_platform",
            side_effect=lambda hass, entity_id: "esphome",
        ),
    ):
        yield SimpleNamespace(
            hass=fake_hass, manager=manager, monitor=monitor,
            signal_store=signal_store,
        )


def _device(rig, row: IRCommand) -> IRDevice:
    device = IRDevice(name="Fan", emitter_entity_ids=["infrared.e"])
    device.add_command(row)
    rig.manager._store.add_device(device)
    return device


def _command_editor(rig, device, row) -> _Editor:
    return _Editor(rig.hass, device_id=device.id, row=row, command_id=row.id)


async def _remote(rig):
    return await rig.monitor.create_manual_remote("Fan")


def _signal_editor(rig, remote, signal) -> _Editor:
    return _Editor(rig.hass, device_id=remote.id, row=signal,
                   signal_id=signal.id)


def _spy():
    from custom_components.hair import send_plan

    seen: list[tuple[int, int]] = []
    real = send_plan.plan_send

    def spy(inner, count, spacing, platform):
        seen.append((spacing, block_duration_us(inner.get_raw_timings())))
        return real(inner, count, spacing, platform)

    return seen, patch.object(send_plan, "plan_send", spy)


async def _command_sends(rig, device, row) -> tuple[int, int]:
    """(spacing, block) the device send plans for this row."""
    from custom_components.hair.tests.test_decoded_tx_consistency import (
        _infrared_mod,
    )

    seen, spying = _spy()
    with spying, patch.object(_infrared_mod, "async_send_command", AsyncMock()):
        await rig.manager.async_send_command(device.id, row.id)
    assert seen, "the send planned nothing"
    return seen[0]


async def _signal_sends(rig, signal) -> tuple[int, int]:
    """(spacing, block) the catalog Test plans for this signal."""
    from custom_components.hair.tests.test_decoded_tx_consistency import (
        _infrared_mod,
    )

    seen, spying = _spy()
    with spying, patch.object(_infrared_mod, "async_send_command", AsyncMock()):
        result = await rig.monitor.test_signal(signal.id, "infrared.e")
    assert result["success"] is True, result
    assert seen, "the test send planned nothing"
    return seen[0]


def _agree(editor: _Editor, row, sent: tuple[int, int]) -> None:
    """The box at Save, the stored row, its record and the send agree."""
    spacing, block = sent
    assert row.send_spacing_ms == editor.box, "the box is what was stored"
    assert row.send_spacing_block_us is not None
    assert abs(row.send_spacing_block_us - block) <= 2_000, (
        "the record is the length the send builds"
    )
    assert spacing == editor.box, "the send uses the number in the box"


def _reopen(rig, row, **ids) -> _Editor:
    again = _Editor(rig.hass, row=row, **ids)
    again.ask()
    return again


def _apple_code() -> str:
    raw = AppleCommand(command=0x02, pair_id=0x01).get_raw_timings()
    return raw_to_pronto(raw, frequency=38000)


def _apple_row(**knobs) -> IRCommand:
    code = _apple_code()
    return mint_command(
        name="Play", protocol="PRONTO", code=code,
        identity=try_decode_identity(ProntoCommand(code).get_raw_timings()),
        **knobs,
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


class TestCommandsThroughTheEditor:
    @pytest.mark.asyncio
    async def test_bypass_alone(self, rig):
        """M1: Bypass on a three-frame Sony capture. The box moves by the
        change of length on the toggle, the save records the length for
        the Bypass state on screen although the pin is written after the
        content, and the send uses the box."""
        row = _sony_row(frames=3, send_count=3, repeat_count=0)
        device = _device(rig, row)
        ed = _command_editor(rig, device, row)
        ed.ask()
        opened, opened_block = ed.box, ed.block
        gap = opened * 1000 - opened_block
        ed.toggle_bypass()
        assert ed.box != opened, "the toggle moved the box"
        assert abs((ed.box * 1000 - ed.block) - gap) <= 1_000, "same gap"
        await ed.save()
        assert row.tx_force_raw is True
        _agree(ed, row, await _command_sends(rig, device, row))
        again = _reopen(rig, row, device_id=device.id, command_id=row.id)
        assert again.box == ed.box and again.restated is False

    @pytest.mark.asyncio
    async def test_bypass_and_a_count_change(self, rig):
        """M1 as found: Bypass plus a count change in one save."""
        row = _sony_row(frames=3, send_count=3, repeat_count=0)
        device = _device(rig, row)
        ed = _command_editor(rig, device, row)
        ed.ask()
        gap = ed.box * 1000 - ed.block
        ed.toggle_bypass()
        ed.set_count(5)
        assert abs((ed.box * 1000 - ed.block) - gap) <= 1_000
        await ed.save()
        assert (row.tx_force_raw, row.send_count) == (True, 5)
        sent = await _command_sends(rig, device, row)
        _agree(ed, row, sent)
        assert silence_us(sent[1], sent[0]) > 50_000, "a real gap, not the floor"
        again = _reopen(rig, row, device_id=device.id, command_id=row.id)
        assert again.box == ed.box and again.restated is False

    @pytest.mark.asyncio
    async def test_a_ditto_change(self, rig):
        """M2: an Apple row, whose ditto knob is on, from one ditto to
        four. The box moves with the block before Save, so the save never
        records a longer block against the old number."""
        row = _apple_row(send_count=3, repeat_count=1)
        device = _device(rig, row)
        ed = _command_editor(rig, device, row)
        ed.ask()
        assert not ed.ditto_disabled
        opened, opened_block = ed.box, ed.block
        ed.set_ditto(4)
        assert ed.block - opened_block > 2_000, "four dittos are longer"
        assert ed.box - opened == round((ed.block - opened_block) / 1000)
        await ed.save()
        assert row.repeat_count == 4
        sent = await _command_sends(rig, device, row)
        _agree(ed, row, sent)
        assert silence_us(sent[1], sent[0]) > 10_000, "not left on the floor"

    @pytest.mark.asyncio
    async def test_a_row_whose_ditto_knob_is_off(self, rig):
        """A Sony row repeats its frame by its ditto count although the
        knob is off for it, so the length is asked about with the row's
        own count: the one Save leaves in place and the send builds."""
        row = _sony_row(send_count=3, repeat_count=1)
        device = _device(rig, row)
        ed = _command_editor(rig, device, row)
        ed.ask()
        assert ed.ditto_disabled
        ed.set_count(4)
        ed.type(300)
        await ed.save()
        _agree(ed, row, await _command_sends(rig, device, row))

    @pytest.mark.asyncio
    async def test_a_typed_number_is_kept_for_the_code_as_it_is(self, rig):
        """A number typed in the box is the person's, even on the floor:
        it takes the length of the code it was typed for and is sent as
        typed."""
        row = _row(_dreo("Speed Up"), send_count=3,
                   send_spacing_ms=OLD_DREO_SPACING)
        device = _device(rig, row)
        ed = _command_editor(rig, device, row)
        ed.ask()
        assert ed.restated is True
        ed.type(150)
        assert ed.box == 150 and ed.restated is False
        await ed.save()
        _agree(ed, row, await _command_sends(rig, device, row))


class TestCommandsSavedBeforeTheFirstAnswer:
    @pytest.mark.asyncio
    async def test_an_unknown_length_is_saved_as_unknown(self, rig):
        """L2: an older Dreo row saved before the editor's first answer
        sends null for the length, the door records nothing, and rule 2
        still widens the send. The box then reopens on the send's value."""
        row = _row(_dreo("Speed Up"), send_count=3,
                   send_spacing_ms=OLD_DREO_SPACING)
        device = _device(rig, row)
        ed = _command_editor(rig, device, row)
        await ed.save()  # no answer yet
        assert row.send_spacing_ms == OLD_DREO_SPACING
        assert row.send_spacing_block_us is None
        spacing, _ = await _command_sends(rig, device, row)
        assert spacing == estimate_spacing_ms(build_like_send_path(row))
        again = _reopen(rig, row, device_id=device.id, command_id=row.id)
        assert again.restated is True and again.box == spacing

    @pytest.mark.asyncio
    async def test_a_known_length_is_kept(self, rig):
        """A recorded row saved before the first answer saves its own
        record with its own number."""
        row = _sony_row(send_count=3, repeat_count=1)
        recorded = row.send_spacing_block_us
        device = _device(rig, row)
        ed = _command_editor(rig, device, row)
        await ed.save()
        assert row.send_spacing_block_us == recorded
        _agree(ed, row, await _command_sends(rig, device, row))


class TestTheDoorWithoutTheEditor:
    async def _update(self, rig, device, row, **fields):
        conn = MagicMock()
        msg = {"id": 9, "type": "hair/command/update",
               "device_id": device.id, "command_id": row.id}
        msg.update(fields)
        await ws_command_update(rig.hass, conn, msg)
        return _ok(conn)

    @pytest.mark.asyncio
    async def test_a_ditto_change_from_an_api_caller_keeps_the_gap(self, rig):
        """M2 through the door alone: Sony x3, ditto 1 to 4, the spacing
        sent back unchanged and no length. The record stays, so rule 1
        moves the send by the change of block and the gap is kept."""
        row = _sony_row(send_count=3, repeat_count=1)
        device = _device(rig, row)
        before = row.send_spacing_ms * 1000 - row.send_spacing_block_us
        await self._update(rig, device, row, repeat_count=4,
                           send_spacing_ms=row.send_spacing_ms)
        spacing, block = await _command_sends(rig, device, row)
        assert abs((spacing * 1000 - block) - before) <= 1_000

    @pytest.mark.asyncio
    async def test_null_means_unknown_and_missing_means_measure(self, rig):
        """An explicit null records nothing; only a missing field (an API
        caller, or a panel from before this change) is measured."""
        told = _sony_row(send_count=3, repeat_count=1)
        left_out = _sony_row(send_count=3, repeat_count=1)
        told_device = _device(rig, told)
        left_out_device = _device(rig, left_out)
        await self._update(rig, told_device, told, send_spacing_ms=300,
                           send_spacing_block_us=None)
        await self._update(rig, left_out_device, left_out,
                           send_spacing_ms=300)
        assert told.send_spacing_block_us is None
        assert left_out.send_spacing_block_us == block_duration_us(
            build_like_send_path(left_out).get_raw_timings()
        )

    @pytest.mark.asyncio
    async def test_a_row_set_to_send_once_records_nothing(self, rig):
        row = _sony_row(send_count=3, repeat_count=1)
        device = _device(rig, row)
        await self._update(rig, device, row, send_count=1)
        assert row.send_spacing_block_us is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "value",
        ["64200", True, 64200.0, 0, -1, SEND_AIR_TIME_MAX_MS * 1000 + 1,
         [64200], {"us": 64200}],
    )
    async def test_an_implausible_length_is_unknown(self, rig, value):
        """Bound-checked, never trusted: anything but a positive whole
        number no longer than the air-time cap records nothing, and the
        save itself still goes through."""
        row = _sony_row(send_count=3, repeat_count=1)
        device = _device(rig, row)
        await self._update(rig, device, row, send_spacing_ms=300,
                           send_spacing_block_us=value)
        assert row.send_spacing_ms == 300
        assert row.send_spacing_block_us is None

    def test_no_schema_refuses_a_length(self):
        """The doors' schemas take the length as anything, so a bad one
        is read as unknown rather than failing the save."""
        source = (Path(__file__).parents[1] / "websocket_api.py").read_text()
        assert source.count(
            'vol.Optional("send_spacing_block_us"): object,'
        ) == 4  # three save doors and the spacing-info read

    def test_the_bounds(self):
        cap = SEND_AIR_TIME_MAX_MS * 1000
        assert plausible_block_us(1) == 1
        assert plausible_block_us(cap) == cap
        assert plausible_block_us(cap + 1) is None
        assert plausible_block_us(0) is None
        assert plausible_block_us(False) is None
        assert plausible_block_us(None) is None


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------


class TestSignalsThroughTheEditor:
    async def _created(self, rig, code: str, count: int = 3):
        """A new Clipper signal through the editor: paste, count, Save."""
        remote = await _remote(rig)
        blank = SimpleNamespace(
            name="Speed", code=code, send_spacing_ms=None,
            send_spacing_block_us=None, send_count=1, repeat_count=1,
            tx_force_raw=False, decoded_protocol=try_decode_identity(
                ProntoCommand(code).get_raw_timings()
            ).protocol,
        )
        ed = _Editor(rig.hass, device_id=remote.id, row=blank)
        ed.ask()
        ed.set_count(count)
        assert ed.box is not None, "the box fills with the estimate"
        await ed.save()
        signal = remote.signals[0]
        return remote, signal, ed

    @pytest.mark.asyncio
    async def test_a_new_signal(self, rig):
        _, signal, ed = await self._created(rig, _dreo("Speed Up"))
        _agree(ed, signal, await _signal_sends(rig, signal))

    @pytest.mark.asyncio
    async def test_a_ditto_and_count_change(self, rig):
        remote, signal, _ = await self._created(rig, _apple_code())
        ed = _signal_editor(rig, remote, signal)
        ed.ask()
        opened, opened_block = ed.box, ed.block
        ed.set_ditto(4)
        ed.set_count(5)
        assert ed.block - opened_block > 2_000
        await ed.save()
        assert (signal.repeat_count, signal.send_count) == (4, 5)
        _agree(ed, signal, await _signal_sends(rig, signal))
        assert ed.box > opened

    @pytest.mark.asyncio
    async def test_a_code_change(self, rig):
        """A signal re-captured as a longer code keeps its gap: the box
        moves by the change of length before Save."""
        remote, signal, _ = await self._created(rig, _dreo("Speed Up"))
        ed = _signal_editor(rig, remote, signal)
        ed.ask()
        gap = ed.box * 1000 - ed.block
        ed.set_code(_dreo("Power"))
        assert abs((ed.box * 1000 - ed.block) - gap) <= 1_000
        await ed.save()
        _agree(ed, signal, await _signal_sends(rig, signal))
        again = _reopen(rig, signal, device_id=remote.id, signal_id=signal.id)
        assert again.box == ed.box and again.restated is False

    @pytest.mark.asyncio
    async def test_a_new_signal_typed_before_its_answer(self, rig):
        """Typed, then saved before the answer that would give the number
        a length: Save says unknown, and the new signal records nothing."""
        remote = await _remote(rig)
        code = _dreo("Speed Up")
        blank = SimpleNamespace(
            name="Speed", code=code, send_spacing_ms=None,
            send_spacing_block_us=None, send_count=1, repeat_count=1,
            tx_force_raw=False, decoded_protocol=None,
        )
        ed = _Editor(rig.hass, device_id=remote.id, row=blank)
        ed.set_count(3)
        ed.type_unanswered(300)
        await ed.save()
        signal = remote.signals[0]
        assert (signal.send_spacing_ms, signal.send_spacing_block_us) == (300, None)
        spacing, _ = await _signal_sends(rig, signal)
        assert spacing == 300

    @pytest.mark.asyncio
    async def test_an_edit_typed_before_its_answer(self, rig):
        remote, signal, _ = await self._created(rig, _dreo("Speed Up"))
        ed = _signal_editor(rig, remote, signal)
        ed.ask()
        ed.type_unanswered(300)
        await ed.save()
        assert (signal.send_spacing_ms, signal.send_spacing_block_us) == (300, None)
        spacing, _ = await _signal_sends(rig, signal)
        assert spacing == 300

    @pytest.mark.asyncio
    async def test_a_signal_set_to_send_once_records_nothing(self, rig):
        remote, signal, _ = await self._created(rig, _dreo("Speed Up"))
        assert signal.send_spacing_block_us is not None
        conn = MagicMock()
        await ws_unknown_signal_edit_pronto(rig.hass, conn, {
            "id": 5, "type": "hair/unknown/signal/edit-pronto",
            "device_id": remote.id, "signal_id": signal.id,
            "pronto": signal.code, "send_count": 1,
        })
        _ok(conn)
        assert signal.send_spacing_block_us is None

    @pytest.mark.asyncio
    async def test_a_save_before_the_first_answer(self, rig):
        """L2 for a signal: an older Dreo signal saved before any answer
        records nothing, and the Test send still widens it."""
        remote = await _remote(rig)
        signal = _row(
            _dreo("Speed Up"), cls=UnknownSignal, id="old", fingerprint="old",
            send_count=3, send_spacing_ms=OLD_DREO_SPACING, source="manual",
        )
        remote.signals.insert(0, signal)
        ed = _signal_editor(rig, remote, signal)
        await ed.save()
        assert signal.send_spacing_block_us is None
        spacing, _ = await _signal_sends(rig, signal)
        assert spacing == estimate_spacing_ms(build_like_send_path(signal))
        again = _reopen(rig, signal, device_id=remote.id, signal_id=signal.id)
        assert again.restated is True and again.box == spacing


# ---------------------------------------------------------------------------
# Matrix rows and the carrier: the stand-in is the row the save leaves
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=1)
def _decoded_fixture_codes() -> tuple[tuple[str, str], ...]:
    """(protocol, Pronto) for every Pronto in the test fixtures that
    decodes: the corpus the round-3 review measured matrix rows over."""
    pattern = re.compile(r"\b0000(?: [0-9A-Fa-f]{4}){5,}")
    found: set[str] = set()
    for path in FIXTURES.rglob("*"):
        if not path.is_file():
            continue
        try:
            if path.suffix == ".gz":
                with gzip.open(path) as handle:
                    raw = handle.read()
            else:
                raw = path.read_bytes()
        except OSError:
            continue
        for match in pattern.finditer(raw.decode("utf-8", "ignore")):
            found.add(" ".join(match.group(0).split()).upper())
    out = []
    for code in sorted(found):
        try:
            ident = try_decode_identity(ProntoCommand(code).get_raw_timings())
        except Exception:
            continue
        if ident is not None:
            out.append((ident.protocol, code))
    return tuple(out)


_MATRIX_KINDS = {
    "matrix source": {"source": CommandSource.MATRIX},
    "matrix cell": {"matrix_cell": {"mode": "cool", "temp": 24}},
}


def _matrix_row(code: str, kind: str, **knobs) -> IRCommand:
    knobs.setdefault("send_count", 3)
    return mint_command(
        name="Cool 24", protocol="PRONTO", code=code,
        raw_timings=list(ProntoCommand(code).get_raw_timings()),
        frequency=_pronto_frequency(code),
        identity=try_decode_identity(ProntoCommand(code).get_raw_timings()),
        **_MATRIX_KINDS[kind], **knobs,
    )


def _send_block(row) -> int:
    return block_duration_us(build_like_send_path(row).get_raw_timings())


def _plain_block(code: str, **knobs) -> int:
    inner = build_like_send_path(_spacing_row_for_pronto(code, **knobs))
    return block_duration_us(inner.get_raw_timings())


def _rca_matrix_code() -> str:
    """An RCA capture whose matrix row replays a longer block than the
    rebuild: the case the review found (56.5 ms measured, 188.7 sent)."""
    for protocol, code in _decoded_fixture_codes():
        if protocol != "RCA":
            continue
        row = _matrix_row(code, "matrix source")
        if _send_block(row) - _plain_block(code, repeat_count=row.repeat_count) > 2_000:
            return code
    raise AssertionError("no RCA fixture replays longer as a matrix row")


class TestMatrixRows:
    def _info(self, rig, code, **fields) -> dict:
        conn = MagicMock()
        msg = {
            "id": 1, "type": "hair/send_spacing_info", "pronto": code,
            "repeat_count": 1, "tx_force_raw": False, "send_count": 3,
            "send_spacing_ms": None, "restate": False,
        }
        msg.update(fields)
        ws_send_spacing_info(rig.hass, conn, msg)
        return _ok(conn)

    @pytest.mark.parametrize("kind", sorted(_MATRIX_KINDS))
    def test_every_decoded_fixture_code(self, rig, kind):
        """The editor's length is the send's for every decoded fixture
        code as a matrix row, and the corpus does hold rows where the
        stand-in alone would have measured a rebuild the send never
        builds (RCA and Kaseikyo among them)."""
        codes = _decoded_fixture_codes()
        assert len(codes) > 100
        diverged_without: set[str] = set()
        for i, (protocol, code) in enumerate(codes):
            row = _matrix_row(code, kind, repeat_count=1)
            row.name = f"Cool {i}"
            device = _device(rig, row)
            info = self._info(
                rig, code, device_id=device.id, command_id=row.id,
            )
            assert abs(info["block_us"] - _send_block(row)) <= 2_000, (
                protocol, code[:40],
            )
            if abs(_plain_block(code, repeat_count=1) - _send_block(row)) > 2_000:
                diverged_without.add(protocol)
        assert {"RCA", "KASEIKYO64"} <= diverged_without

    @pytest.mark.asyncio
    async def test_a_typed_spacing_is_sent_as_typed(self, rig):
        """The review's case: an RCA capture as a MATRIX row at x3. A
        typed 400 was stored against the rebuild's 56.5 ms and sent at
        532; it is now stored against the replay and sent at 400. (A
        matrix-cell porthole saves through its lattice and is covered by
        the length check above.)"""
        row = _matrix_row(_rca_matrix_code(), "matrix source")
        device = _device(rig, row)
        ed = _command_editor(rig, device, row)
        ed.ask()
        ed.type(400)
        await ed.save()
        sent = await _command_sends(rig, device, row)
        _agree(ed, row, sent)
        assert sent[0] == 400

    @pytest.mark.asyncio
    async def test_bypass_toggled_on_a_matrix_row(self, rig):
        """What the person changes comes from the screen; only the
        matrix provenance comes from the stored row."""
        row = _matrix_row(_rca_matrix_code(), "matrix source")
        device = _device(rig, row)
        ed = _command_editor(rig, device, row)
        ed.ask()
        ed.toggle_bypass()
        ed.set_count(4)
        await ed.save()
        assert (row.tx_force_raw, row.send_count) == (True, 4)
        _agree(ed, row, await _command_sends(rig, device, row))
        again = _reopen(rig, row, device_id=device.id, command_id=row.id)
        assert again.box == ed.box and again.restated is False

    def test_the_stored_row_lends_only_its_matrix_provenance(self):
        code = _rca_matrix_code()
        stored = _matrix_row(code, "matrix cell", repeat_count=4,
                             tx_force_raw=True)
        stored.frequency = 40_000
        stand_in = _spacing_row_for_pronto(
            code, repeat_count=0, tx_force_raw=False, like=stored,
        )
        assert stand_in.matrix_cell == stored.matrix_cell
        assert stand_in.matrix_cell is not stored.matrix_cell
        assert stand_in.source == stored.source
        assert (stand_in.repeat_count, stand_in.tx_force_raw) == (0, False)
        assert stand_in.frequency == _pronto_frequency(code)

    def test_no_command_id_lends_nothing(self, rig):
        """Signals and new commands measure exactly as before."""
        code = _rca_matrix_code()
        stand_in = _spacing_row_for_pronto(code, repeat_count=1)
        assert (stand_in.source, stand_in.matrix_cell) == (None, None)
        row = _matrix_row(code, "matrix source", repeat_count=1)
        device = _device(rig, row)
        plain = _plain_block(code, repeat_count=1)
        assert self._info(rig, code, device_id=device.id)["block_us"] == plain
        assert self._info(rig, code)["block_us"] == plain

    def test_an_unknown_or_foreign_command_id_is_ignored(self, rig):
        code = _rca_matrix_code()
        row = _matrix_row(code, "matrix source", repeat_count=1)
        _device(rig, row)
        other = _device(rig, _sony_row(send_count=3, repeat_count=1))
        plain = _plain_block(code, repeat_count=1)
        foreign = self._info(
            rig, code, device_id=other.id, command_id=row.id,
        )
        unknown = self._info(
            rig, code, device_id=other.id, command_id="no-such-command",
        )
        assert foreign["block_us"] == unknown["block_us"] == plain

    @pytest.mark.asyncio
    async def test_the_save_door_judges_the_air_time_of_the_replay(self, rig):
        """The update door measures the same stand-in: at x10 a spacing
        that fits the rebuild but not the replay the matrix row sends is
        refused, rather than stored and sent over the cap."""
        row = _matrix_row(_rca_matrix_code(), "matrix source", send_count=10)
        device = _device(rig, row)
        inner = build_like_send_path(row)
        rebuild = build_like_send_path(
            _spacing_row_for_pronto(row.code, repeat_count=row.repeat_count)
        )
        spacing = next(
            s for s in range(200, 1001)
            if realised_air_ms(inner, 10, s) > SEND_AIR_TIME_MAX_MS
            and realised_air_ms(rebuild, 10, s) <= SEND_AIR_TIME_MAX_MS
        )
        conn = MagicMock()
        await ws_command_update(rig.hass, conn, {
            "id": 7, "type": "hair/command/update",
            "device_id": device.id, "command_id": row.id,
            "pronto": row.code, "send_count": 10,
            "send_spacing_ms": spacing,
        })
        assert conn.send_error.called
        assert conn.send_error.call_args[0][1] == "spacing_air_time"


class TestTheCarrier:
    def _tdc38_at(self, frequency: int) -> str:
        code = next(c for p, c in _decoded_fixture_codes() if p == "TDC38")
        raw = ProntoCommand(code).get_raw_timings()
        return raw_to_pronto(list(raw), frequency=frequency)

    @pytest.mark.asyncio
    async def test_an_off_carrier_tdc38_row(self, rig):
        """A TDC-38 code stored at 36 kHz is replayed at send (the carrier
        rule); the editor now measures it with the carrier the door
        stores, so a typed number goes out as typed."""
        code = self._tdc38_at(36_000)
        ident = try_decode_identity(ProntoCommand(code).get_raw_timings())
        assert ident is not None and ident.protocol == "TDC38"
        row = mint_command(
            name="Back", protocol="PRONTO", code=code,
            raw_timings=list(ProntoCommand(code).get_raw_timings()),
            frequency=_pronto_frequency(code), send_count=3, identity=ident,
        )
        assert row.frequency == 36_000
        device = _device(rig, row)
        ed = _command_editor(rig, device, row)
        ed.ask()
        assert abs(ed.info["block_us"] - _send_block(row)) <= 2_000
        ed.type(300)
        await ed.save()
        sent = await _command_sends(rig, device, row)
        _agree(ed, row, sent)
        assert sent[0] == 300

    def test_the_stand_in_carries_the_door_carrier(self):
        assert _pronto_frequency(self._tdc38_at(36_000)) == 36_000
        assert _spacing_row_for_pronto(self._tdc38_at(36_000)).frequency == 36_000
        assert _pronto_frequency("not a code") is None


# ---------------------------------------------------------------------------
# Imports, assign, the refusal wording, the note
# ---------------------------------------------------------------------------


class TestSpacingsFromElsewhere:
    def _dreo_wig_signal(self, alias: str):
        """A Dreo wig row as exported before #213, x3 at the rebuilt-block
        estimate, with the identity the adopt door derives for it."""
        from custom_components.hair.wig_format import parse_wig
        from custom_components.hair.wig_identity import wig_signal_identities

        wig = parse_wig(
            (WIGS / "dreo-fan-dr-haf004s-perfect-fit.wig.json").read_text()
        ).wig
        identities = wig_signal_identities(wig)
        i = next(n for n, s in enumerate(wig.signals) if s.alias == alias)
        sig = dataclasses.replace(
            wig.signals[i], send_count=3, send_spacing_ms=OLD_DREO_SPACING
        )
        return sig, identities[i]

    def test_a_wig_from_before_213_adopts_with_no_record(self):
        """M3: Adopt Device (``ws_wig_make_device``) and the supersession
        top-up both mint through
        ``_command_from_wig_signal``. The wig's spacing was set against an
        older block, so it gets no record, and rule 2 widens it."""
        from custom_components.hair.websocket_api import (
            _command_from_wig_signal,
        )

        sig, ident = self._dreo_wig_signal("Mode")
        command = _command_from_wig_signal(sig, ident, set(), {}, 1)
        assert command.send_spacing_ms == OLD_DREO_SPACING
        assert command.send_spacing_block_us is None
        from custom_components.hair.send_plan import effective_spacing_ms

        assert effective_spacing_ms(
            command.send_spacing_ms, build_like_send_path(command), 3, None
        ) == 375

    def test_both_wig_doors_mint_through_it(self):
        source = (Path(__file__).parents[1] / "websocket_api.py").read_text()
        for door in ("async def ws_wigs_supersede(",
                     "async def ws_wig_make_device("):
            body = source.split(door, 1)[1].split("\n@websocket_api", 1)[0]
            assert "_command_from_wig_signal(" in body, door
        assert source.count("_command_from_wig_signal(") == 3  # def + 2

    def test_mint_measures_only_its_own_estimate(self):
        code = _dreo("Mode")
        ident = try_decode_identity(ProntoCommand(code).get_raw_timings())
        handed = mint_command(name="m", protocol="PRONTO", code=code,
                              send_count=3, send_spacing_ms=160,
                              identity=ident)
        estimated = mint_command(name="m", protocol="PRONTO", code=code,
                                 send_count=3, identity=ident)
        told = mint_command(name="m", protocol="PRONTO", code=code,
                            send_count=3, send_spacing_ms=375,
                            send_spacing_block_us=265_795, identity=ident)
        assert handed.send_spacing_block_us is None
        assert estimated.send_spacing_block_us == block_duration_us(
            build_like_send_path(estimated).get_raw_timings()
        )
        assert told.send_spacing_block_us == 265_795

    def test_an_assign_at_count_one_records_nothing(self):
        """L1: a recorded x3 signal assigned to send once."""
        from custom_components.hair.signal_monitor import (
            _apply_signal_provenance,
        )

        signal = _row(
            _dreo("Speed Up"), cls=UnknownSignal, id="s", fingerprint="s",
            send_count=3, send_spacing_ms=265, send_spacing_block_us=156_700,
        )
        once = IRCommand(name="once")
        _apply_signal_provenance(once, signal, send_count=1)
        thrice = IRCommand(name="thrice")
        _apply_signal_provenance(thrice, signal, send_count=3)
        assert once.send_spacing_block_us is None
        assert thrice.send_spacing_block_us == 156_700


class TestTheWords:
    def test_one_send_fits(self, fake_hass):
        from custom_components.hair.websocket_api import _check_send_spacing

        inner = SimpleNamespace(get_raw_timings=lambda: [2_500_000])
        assert realised_air_ms(inner, 1, 1000) <= SEND_AIR_TIME_MAX_MS
        _, error = _check_send_spacing(
            fake_hass, 1000, send_count=2, inner=inner, emitter_entity_ids=[],
        )
        assert error is not None
        assert error[1].endswith("at most 1 send fits at this spacing")

    def test_the_note_is_true_in_every_case(self):
        """L5: one note for a shift, a widening and a cut to the cap, in
        all eleven dictionaries, and none of them still says the code changed
        length."""
        en = json.loads((SRC / "locales" / "en.json").read_text())
        assert en["editor.spacing_restated"] == (
            "The spacing has been adjusted to fit this code, so there is a "
            "real gap between sends. Save to keep it."
        )
        for path in sorted((SRC / "locales").glob("*.json")):
            note = json.loads(path.read_text())["editor.spacing_restated"]
            assert note and "\u2014" not in note, path.name
        assert len(list((SRC / "locales").glob("*.json"))) == 11


# ---------------------------------------------------------------------------
# The TypeScript the stand-in stands in for
# ---------------------------------------------------------------------------


class TestTheEditorSource:
    """No frontend test runner exists, so these pin ir-signal-editor.ts
    to ``_Editor``: each is a line the stand-in relies on."""

    source = (SRC / "ir-signal-editor.ts").read_text()

    def _method(self, name: str) -> str:
        start = self.source.index(f"    private {name}(")
        end = self.source.index("\n    }\n", start)
        return self.source[start:end]

    def test_a_ditto_change_asks_again(self):
        assert "this._refreshSpacingInfo()" in self._method("_onDittoInput")

    def test_the_bypass_toggle_asks_again(self):
        handler = self.source.split("@toggle-bypass=", 1)[1].split("}}", 1)[0]
        assert "this._refreshSpacingInfo()" in handler

    def test_every_save_sends_the_length(self):
        save = self.source.split("private async _save()", 1)[1]
        save = save.split("\n    }\n", 1)[0]
        assert save.count(
            "send_spacing_block_us: this._spacingBlockForSave"
        ) == 3

    def test_the_length_asked_about_is_the_one_sent(self):
        body = self.source.split("private async _refreshSpacingInfo()", 1)[1]
        body = body.split("\n    }\n", 1)[0]
        assert re.search(
            r"repeat_count: this\._dittoCountDisabled\s*\?\s*this\.initialDitto",
            body,
        )
        assert "tx_force_raw: this._bypass" in body
        assert "if (ask !== this._spacingAsk) return;" in body
        assert "this._spacingBlockUs = info.block_us;" in body
        assert "command_id: this._isCommand ? this.commandId : null" in body

    def test_typing_forgets_the_length(self):
        typed = self._method("_onSpacingInput")
        assert "this._spacingBlockUs = null;" in typed
        assert "this._spacingTyped = true;" in typed

    def test_the_editor_opens_on_the_record(self):
        assert (
            "this._spacingBlockUs = this.initialSendSpacingBlockUs;"
            in self.source
        )
