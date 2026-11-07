"""RF send round, T6: pasting a radio code into the Clipper.

``hair/clip/create-signal`` takes ``rf_code`` (and ``rf_frequency_hz``)
in place of ``pronto``; the paste is read by ``rf_paste.validate`` and
written by ``apply_code``, exactly as the radio editor does, so a
Clipper row and the same code edited in are one row. The panel opens the
radio editor empty for it, and edits a radio Clipper row there too.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair import rf_paste
from custom_components.hair.const import DOMAIN, MEDIUM_RF, RF_PROTOCOL
from custom_components.hair.identity import canonical_fingerprint
from custom_components.hair.tests.test_rf_paste import (
    BUTTON_A,
    BUTTON_B,
    IT104_B64,
    _frame,
)
from custom_components.hair.tests.test_websocket_api import _make_signal_monitor
from custom_components.hair.websocket_api import ws_clip_create_signal

SRC = Path(__file__).parent.parent / "frontend" / "src"


def _text(bits: str) -> str:
    return " ".join(map(str, _frame(bits) * 3))


def _wire(hass, monitor):
    hass.data[DOMAIN] = {"entry-1": {
        "device_manager": MagicMock(),
        "signal_monitor": monitor,
        "trigger_manager": MagicMock(),
    }}


@pytest.fixture
def monitor(fake_hass):
    monitor = _make_signal_monitor(fake_hass)
    monitor._signal_store.async_save = AsyncMock()
    return monitor


class TestTheMonitor:
    @pytest.mark.asyncio
    async def test_a_paste_becomes_a_radio_row(self, monitor):
        remote = await monitor.create_manual_remote("Fobs")
        result = await monitor.create_manual_rf_signal(
            remote.id, IT104_B64, alias=" Button 1 ", send_count=4,
        )
        assert result["success"] is True
        row = monitor._signal_store.get_device(remote.id).signals[0]
        assert row.medium == MEDIUM_RF
        assert row.protocol == RF_PROTOCOL and row.code is None
        assert row.source == "manual"
        assert row.alias == "Button 1" and row.send_count == 4
        # An RM4 Pro capture says its own carrier.
        assert row.rf_frequency_hz and row.rf_frequency_source == "signal"
        assert row.fingerprint == canonical_fingerprint(RF_PROTOCOL, None, row.raw_timings)
        # The same paste through the editor's path gives the same row.
        validated = rf_paste.validate(IT104_B64)
        assert (row.fingerprint, row.byte_hash) == (
            validated["fingerprint"], validated["frame_hash"],
        )
        assert result["signal"]["medium"] == MEDIUM_RF

    @pytest.mark.asyncio
    async def test_a_given_frequency_is_the_users_and_none_is_kept(self, monitor):
        remote = await monitor.create_manual_remote("Fobs")
        await monitor.create_manual_rf_signal(
            remote.id, _text(BUTTON_A), rf_frequency_hz=433_420_000,
        )
        await monitor.create_manual_rf_signal(remote.id, _text(BUTTON_B))
        a, b = monitor._signal_store.get_device(remote.id).signals
        assert (a.rf_frequency_hz, a.rf_frequency_source) == (433_420_000, "user")
        # Bare timings say no carrier: the row is kept, and is not sent
        # until a frequency is set in the editor.
        assert b.rf_frequency_hz is None

    @pytest.mark.asyncio
    async def test_a_code_already_on_the_remote_is_refused(self, monitor):
        remote = await monitor.create_manual_remote("Fobs")
        await monitor.create_manual_rf_signal(remote.id, _text(BUTTON_A))
        result = await monitor.create_manual_rf_signal(remote.id, _text(BUTTON_A))
        assert (result["success"], result["code"]) == (False, "duplicate_signal")

    @pytest.mark.asyncio
    async def test_a_bad_paste_says_why(self, monitor):
        remote = await monitor.create_manual_remote("Fobs")
        result = await monitor.create_manual_rf_signal(remote.id, "350 -1050")
        assert result["code"] == "rf_paste_no_frame"
        result = await monitor.create_manual_rf_signal(remote.id, "")
        assert result["code"] == "rf_paste_empty"

    @pytest.mark.asyncio
    async def test_only_a_clipped_remote_takes_one(self, monitor):
        from custom_components.hair.models import UnknownDevice

        monitor._signal_store.add_device(UnknownDevice(id="heard", fingerprint="fp"))
        result = await monitor.create_manual_rf_signal("heard", IT104_B64)
        assert result["code"] == "not_manual"
        result = await monitor.create_manual_rf_signal("nope", IT104_B64)
        assert result["code"] == "device_not_found"


class TestTheDoor:
    @pytest.mark.asyncio
    async def test_rf_code_takes_the_radio_path(self, fake_hass, monitor):
        _wire(fake_hass, monitor)
        remote = await monitor.create_manual_remote("Fobs")
        conn = MagicMock()
        with patch.object(monitor._signal_store, "async_save", AsyncMock()):
            await ws_clip_create_signal(fake_hass, conn, {
                "id": 1, "type": "hair/clip/create-signal",
                "device_id": remote.id, "rf_code": _text(BUTTON_A),
                "rf_frequency_hz": 433_920_000, "alias": "A", "send_count": 2,
            })
        conn.send_error.assert_not_called()
        signal = conn.send_result.call_args.args[1]["signal"]
        assert signal["medium"] == MEDIUM_RF
        assert signal["rf_frequency_hz"] == 433_920_000
        assert signal["send_count"] == 2

    @pytest.mark.asyncio
    async def test_a_refusal_carries_its_code(self, fake_hass, monitor):
        _wire(fake_hass, monitor)
        remote = await monitor.create_manual_remote("Fobs")
        conn = MagicMock()
        await ws_clip_create_signal(fake_hass, conn, {
            "id": 1, "device_id": remote.id, "rf_code": "nonsense",
        })
        assert conn.send_error.call_args.args[1] == "rf_paste_unreadable"

    @pytest.mark.asyncio
    async def test_no_code_at_all_is_refused(self, fake_hass, monitor):
        _wire(fake_hass, monitor)
        conn = MagicMock()
        await ws_clip_create_signal(fake_hass, conn, {"id": 1, "device_id": "r"})
        assert conn.send_error.call_args.args[1] == "invalid_format"

    def test_the_schema_takes_one_code_not_both(self):
        """The test stub drops websocket schemas, so the declaration is
        pinned: pronto and rf_code are one exclusive group."""
        source = " ".join(
            (SRC.parent.parent / "websocket_api.py").read_text(encoding="utf-8").split()
        )
        assert 'vol.Exclusive("pronto", "code"): str,' in source
        assert 'vol.Exclusive("rf_code", "code"): vol.All(str, vol.Length(max=200_000)),' in source


class TestThePanel:
    def _flat(self, name: str) -> str:
        return " ".join((SRC / name).read_text(encoding="utf-8").split())

    def test_the_clipper_opens_the_radio_editor_empty(self):
        clips = self._flat("ir-clips.ts")
        assert '@click=${(e: Event) => this._openCreateRfSignal(device.id, e)}' in clips
        assert (
            "${this._createRfDeviceId ? html`<ir-rf-editor .api=${this.api} "
            ".deviceId=${this._createRfDeviceId} @signal-created=${this._onSignalCreated}"
        ) in clips

    def test_a_radio_clipper_row_is_edited_and_tested_as_radio(self):
        clips = self._flat("ir-clips.ts")
        assert '${sig.code || sig.medium === "rf" ? renderEditBtn(' in clips
        assert '${this._editSignal?.signal.medium === "rf" ? html`<ir-rf-editor' in clips
        assert '.media=${[this._testDialog.signal.medium ?? "ir"]}' in clips
        assert 'const at = substitutedHz(results);' in clips
        assert "<span>${clipCarrier(sig)}</span>" in clips

    def test_the_editor_creates_when_it_has_no_row(self):
        editor = self._flat("ir-rf-editor.ts")
        assert "return this.signalId === null && this.commandId === null;" in editor
        assert "const result = await this.api.createRfSignal({" in editor
        assert 'this._fire("signal-created", result);' in editor
        assert "if (this._creating && !this._codeChanged) return false;" in editor
        api = self._flat("api.ts")
        assert "createRfSignal(payload: {" in api

    def test_every_new_string_is_in_every_language(self):
        keys = (
            "clips.add_rf_signal", "clips.add_rf_signal_title", "rfedit.new_signal",
            "panel.tagline.clips",
        )
        en = json.loads((SRC / "locales" / "en.json").read_text(encoding="utf-8"))
        assert en["panel.tagline.clips"] == "Build remotes by pasting known IR and radio codes"
        for path in (SRC / "locales").glob("*.json"):
            words = json.loads(path.read_text(encoding="utf-8"))
            for key in keys:
                assert words.get(key), (path.name, key)
                assert "—" not in words[key], (path.name, key)
