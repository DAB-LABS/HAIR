"""The raw pin, end to end (Highlights, GH #78).

kno-te's Dreo Power code is a Symphony repeat-train: six or seven frames
with ~7 ms gaps, captured as one blob. HAIR decodes it, re-encodes one
clean frame, and the fan ignores it. The device-command toggle already
fixed that on a device; nothing else in the chain could say it.

What these tests protect is the CHAIN. The pin has to survive capture,
Test, assign, export, share, CLIP and adopt, and it dies silently at any
boundary that forgets to copy one field. Each hop below is a boundary
that was carrying ``send_count`` already and had to learn one more knob:

    sniffed / pasted signal
        -> Test           (signal_monitor.test_signal)
        -> assign         (_apply_signal_provenance)
        -> device command (device_manager gate)
        -> export         (wig_export -> bypass_protocol)
        -> wig file       (in the hash, only when true)
        -> adopt          (-> tx_force_raw again)
        -> CLIP           (three separate touch points)

A miss anywhere produces a wig that looks right, hashes right, fits
right, and transmits wrong.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hair import ir_command as _ir_command_mod
from custom_components.hair.models import IRCommand, UnknownSignal
from custom_components.hair.signal_monitor import _apply_signal_provenance
from custom_components.hair.wig_format import (
    Wig,
    WigSignal,
    parse_wig,
    serialize_wig,
    wig_content_hash,
)

from .test_capture_dittos import _infrared_mod
from .test_capture_dittos import _monitor as _make_monitor

PRONTO = "0000 006D 0002 0000 0020 0040 0020 0040"
# A second, byte-different code: the import path collapses byte-identical
# entries under its duplicate guard, so two rows need two codes.
_PRONTO_B = "0000 006D 0002 0000 0030 0050 0030 0050"
# A third distinct code, for replacing one of the two above.
_PRONTO_C = "0000 006D 0002 0000 0040 0060 0040 0060"


def _signal(**kw) -> UnknownSignal:
    base = {
        "fingerprint": "fp-1",
        "byte_hash": "bh-1",
        "protocol": "PRONTO",
        "code": PRONTO,
        "alias": "Power",
        "decoded_protocol": "SYMPHONY12",
        "decoded_address": 1,
        "decoded_command": 0xD81,
        "decoded_fingerprint": "symphony12:1:d81",
    }
    base.update(kw)
    return UnknownSignal(**base)


# ---------------------------------------------------------------------------
# The knob itself
# ---------------------------------------------------------------------------


class TestSignalKnob:
    def test_defaults_off(self):
        assert _signal().tx_force_raw is False

    def test_survives_store_round_trip(self):
        """It is a user decision, so it has to outlive a restart the way
        send_count and repeat_count already do."""
        sig = _signal(tx_force_raw=True)
        back = UnknownSignal.from_dict(sig.to_dict())
        assert back.tx_force_raw is True

    def test_an_old_record_without_the_key_loads(self):
        data = _signal().to_dict()
        del data["tx_force_raw"]
        assert UnknownSignal.from_dict(data).tx_force_raw is False


# ---------------------------------------------------------------------------
# Assign
# ---------------------------------------------------------------------------


class TestAssignCarry:
    def test_the_pin_crosses_onto_the_command(self):
        """``_apply_signal_provenance`` exists so a per-field copy lives
        in ONE place; its own docstring names the half-added-copy bug
        that motivated it."""
        command = IRCommand(name="Power", category="power")
        _apply_signal_provenance(command, _signal(tx_force_raw=True))
        assert command.tx_force_raw is True

    def test_an_unpinned_signal_leaves_the_command_alone(self):
        command = IRCommand(name="Power", category="power")
        _apply_signal_provenance(command, _signal())
        assert command.tx_force_raw is False

    def test_assign_does_not_disturb_the_other_knobs(self):
        command = IRCommand(name="Power", category="power")
        _apply_signal_provenance(
            command, _signal(tx_force_raw=True, send_count=3, repeat_count=2)
        )
        assert (command.tx_force_raw, command.send_count) == (True, 3)
        assert command.repeat_count == 2


# ---------------------------------------------------------------------------
# The two send gates
# ---------------------------------------------------------------------------


class TestSendGates:
    """The device gate already carried the clause. The catalog Test path
    did not, which is why kno-te's Clipper test also failed and looked
    like proof that his code was wrong rather than proof that HAIR was
    rebuilding it."""

    @pytest.mark.asyncio
    async def test_test_signal_skips_re_encode_when_pinned(self, fake_hass):
        sig = _signal(id="s1", tx_force_raw=True)
        monitor, _ = _make_monitor(fake_hass, sig)
        with (
            patch.object(_infrared_mod, "async_send_command", AsyncMock()),
            patch.object(
                _ir_command_mod, "build_decoded_command",
                return_value=object(),
            ) as bdc,
            patch.object(_ir_command_mod, "build_command"),
        ):
            result = await monitor.test_signal("s1", "infrared.e")
        assert result["success"]
        bdc.assert_not_called()

    @pytest.mark.asyncio
    async def test_test_signal_re_encodes_when_not_pinned(self, fake_hass):
        sig = _signal(id="s1")
        monitor, _ = _make_monitor(fake_hass, sig)
        with (
            patch.object(_infrared_mod, "async_send_command", AsyncMock()),
            patch.object(
                _ir_command_mod, "build_decoded_command",
                return_value=object(),
            ) as bdc,
            patch.object(_ir_command_mod, "build_command"),
        ):
            result = await monitor.test_signal("s1", "infrared.e")
        assert result["success"]
        bdc.assert_called_once()

    def test_the_device_gate_reads_the_flag(self):
        """Pinned by inspection rather than by driving a send: the gate
        is one line and its shape IS the contract."""
        import inspect

        from custom_components.hair import device_manager

        src = inspect.getsource(
            device_manager.DeviceManager.async_send_command
        )
        assert "and not command.tx_force_raw" in src


# ---------------------------------------------------------------------------
# Export and adopt
# ---------------------------------------------------------------------------


class TestExportAdoptRoundTrip:
    def test_export_maps_the_command_flag_onto_the_wig(self):
        from custom_components.hair.wig_export import build_wig_from_device

        device = MagicMock()
        device.name = "Dreo Fan"
        device.manufacturer = "Dreo"
        device.model = "DR-HAF004S"
        device.commands = [
            IRCommand(
                name="Power", category="power", protocol="PRONTO",
                code=PRONTO, tx_force_raw=True,
            ),
            IRCommand(
                name="Mode", category="mode", protocol="PRONTO",
                code=PRONTO,
            ),
        ]
        wig = build_wig_from_device(device).wig
        by_alias = {s.alias: s for s in wig.signals}
        assert by_alias["Power"].bypass_protocol is True
        assert by_alias["Mode"].bypass_protocol is False

    def test_the_flag_survives_the_file(self):
        wig = Wig(name="Dreo Fan", signals=[
            WigSignal(alias="Power", pronto=PRONTO, bypass_protocol=True),
        ])
        back = parse_wig(serialize_wig(wig)).wig
        assert back.signals[0].bypass_protocol is True

    def test_adopt_maps_it_back(self):
        """Without this half the marker exports and does nothing on the
        receiving end, which is the gap that made the whole feature
        necessary."""
        import inspect

        from custom_components.hair import websocket_api

        src = inspect.getsource(websocket_api)
        assert "command.tx_force_raw = sig.bypass_protocol" in src


# ---------------------------------------------------------------------------
# Wig -> Clipper, the three-part route
# ---------------------------------------------------------------------------


class TestWigToClipper:
    """CLIP is the route a shared wig most often takes into a device, and
    it crosses three separate functions. Missing any one drops the pin
    silently, so each is asserted on its own and then together."""

    def _closet(self, tmp_path, wig: Wig) -> tuple[str, str]:
        from custom_components.hair.code_library import wig_codebook_id

        wigs = tmp_path / "hair" / "wigs"
        wigs.mkdir(parents=True, exist_ok=True)
        (wigs / "dreo.wig.json").write_text(
            serialize_wig(wig), encoding="utf-8"
        )
        return str(tmp_path), wig_codebook_id("dreo.wig.json")

    def test_materialize_carries_it_into_the_entry(self, tmp_path):
        from custom_components.hair.code_library import materialize_wig

        config_dir, cb_id = self._closet(tmp_path, Wig(
            name="Dreo", signals=[
                WigSignal(alias="Power", pronto=PRONTO,
                          bypass_protocol=True),
                WigSignal(alias="Mode", pronto=PRONTO),
            ],
        ))
        entries = {
            e["name"]: e for e in materialize_wig(config_dir, cb_id)
        }
        assert entries["Power"]["bypass_protocol"] is True
        assert entries["Mode"]["bypass_protocol"] is False

    def test_matrix_cells_never_carry_it(self, tmp_path):
        """Ruling 1: signals only. The matrix send path is already an
        unconditional raw replay with no re-encode branch, so a flag
        there would describe behaviour that is not conditional on
        anything. The exemption expires if that ever changes."""
        from custom_components.hair.code_library import materialize_wig
        from custom_components.hair.wig_format import (
            ClimateCell,
            ClimateMatrix,
        )

        config_dir, cb_id = self._closet(tmp_path, Wig(
            name="AC", signals=[], climate=ClimateMatrix(
                min_temp=16.0, max_temp=30.0, off=PRONTO,
                cells=[ClimateCell(mode="cool", fan="auto", temp=20.0,
                                   pronto=PRONTO)],
            ),
        ))
        entries = materialize_wig(config_dir, cb_id, include_matrix=True)
        assert entries
        assert all(e["bypass_protocol"] is False for e in entries)

    @pytest.mark.asyncio
    async def test_import_manual_remote_stores_it(self, fake_hass):
        monitor, store = _make_monitor(fake_hass)
        await monitor.import_manual_remote("Dreo", [
            {"name": "Power", "code": PRONTO, "bypass_protocol": True},
            {"name": "Mode", "code": _PRONTO_B},
        ])
        device = next(
            d for d in store.get_all_devices() if d.label == "Dreo"
        )
        by_alias = {s.alias: s for s in device.signals}
        assert by_alias["Power"].tx_force_raw is True
        assert by_alias["Mode"].tx_force_raw is False

    @pytest.mark.asyncio
    async def test_a_library_entry_has_no_pin_to_carry(self, fake_hass):
        """The same asymmetry send_count already has: a library codebook
        carries no bypass intent, so its entries simply omit the key."""
        monitor, store = _make_monitor(fake_hass)
        await monitor.import_manual_remote("Lib", [
            {"name": "Power", "code": PRONTO},
        ])
        device = next(
            d for d in store.get_all_devices() if d.label == "Lib"
        )
        assert device.signals[0].tx_force_raw is False


# ---------------------------------------------------------------------------
# The whole chain in one pass
# ---------------------------------------------------------------------------


def test_full_chain_signal_to_adopted_command(tmp_path):
    """One assertion per boundary, in the order a real code travels.

    If this test fails, read which hop it stopped at: that is the
    boundary that forgot to copy the field.
    """
    from custom_components.hair.code_library import materialize_wig
    from custom_components.hair.wig_export import build_wig_from_device

    # 1. A sniffed signal the user pins to raw.
    signal = _signal(tx_force_raw=True)

    # 2. Assign it: the pin crosses onto the command.
    command = IRCommand(
        name="Power", category="power", protocol="PRONTO", code=PRONTO,
    )
    _apply_signal_provenance(command, signal)
    assert command.tx_force_raw is True, "died at assign"

    # 3. Export the device: the command flag becomes the wig field.
    device = MagicMock()
    device.name = "Dreo Fan"
    device.manufacturer = "Dreo"
    device.model = "DR-HAF004S"
    device.commands = [command]
    wig = build_wig_from_device(device).wig
    assert wig.signals[0].bypass_protocol is True, "died at export"

    # 4. Share the file and read it back.
    shared = parse_wig(serialize_wig(wig)).wig
    assert shared.signals[0].bypass_protocol is True, "died in the file"

    # 5. CLIP it onto a clipped remote.
    from custom_components.hair.code_library import wig_codebook_id

    wigs = tmp_path / "hair" / "wigs"
    wigs.mkdir(parents=True, exist_ok=True)
    (wigs / "dreo.wig.json").write_text(
        serialize_wig(shared), encoding="utf-8"
    )
    entry = materialize_wig(
        str(tmp_path), wig_codebook_id("dreo.wig.json")
    )[0]
    assert entry["bypass_protocol"] is True, "died at CLIP"

    # 6. And the adopted command reads it back off the wig signal.
    adopted = IRCommand(name="Power", category="power")
    adopted.tx_force_raw = shared.signals[0].bypass_protocol
    assert adopted.tx_force_raw is True, "died at adopt"


# ---------------------------------------------------------------------------
# The fitting: a pinned row is a checklist row, not an advisory one
# ---------------------------------------------------------------------------


class TestPinnedRowsAreStillProved:
    """Ruling 7.1, and the trap it names.

    The comb declines to judge a bypassed row, and it would be easy to
    let that exemption leak into the fitting as an ADVISORY row -- the
    path comb suspects already ride, where a row is sent and tested but
    carries no verdict and never counts toward completeness.

    That would be a false pass. A bypassed code is a real button on a
    real remote, and it is the button somebody had to go out of their
    way to repair. If it stopped counting, a fitter could complete and
    sign a fitting attesting every code EXCEPT the one that needed the
    work. What the pin buys is a chip, not an exemption.
    """

    def _wig(self) -> Wig:
        return Wig(name="Dreo Fan", signals=[
            WigSignal(alias="Power", pronto=PRONTO, bypass_protocol=True),
            WigSignal(alias="Mode", pronto=_PRONTO_B),
        ])

    def test_it_is_a_fitting_row(self):
        from custom_components.hair.wig_fitting import fitting_rows

        keys = [k for k, _, _ in fitting_rows(self._wig())]
        assert keys == ["Power", "Mode"]

    def test_it_is_not_advisory_in_the_session(self):
        from custom_components.hair.wig_comb import comb_wig, stamp_receipt
        from custom_components.hair.wig_fitting import session_row_specs

        wig = self._wig()
        stamp_receipt(wig, comb_wig(wig), "2026-08-01")
        specs = {s.key: s for s in session_row_specs(wig)}
        assert specs["Power"].advisory is False

    def test_it_counts_toward_completeness(self):
        """The assertion that makes the whole distinction real."""
        from custom_components.hair.wig_fitting import (
            fitting_is_complete,
            parse_fittings,
        )

        wig = self._wig()
        # Every row but the pinned one confirmed: NOT complete.
        wig.extra["fittings"] = [{
            "handle": "dab", "date": "2026-08-01",
            "content_hash": wig_content_hash(wig),
            "confirmed": ["Mode"], "failed": [],
        }]
        partial = parse_fittings(wig).fittings[0]
        assert not fitting_is_complete(partial, wig)

        # Add it and the fitting completes.
        wig.extra["fittings"][0]["confirmed"] = ["Mode", "Power"]
        full = parse_fittings(wig).fittings[0]
        assert fitting_is_complete(full, wig)

    def test_combing_a_pinned_wig_leaves_a_signed_fitting_alone(self):
        """Combing stamps a receipt without rolling the hash, and the
        pin does not change that."""
        from custom_components.hair.wig_comb import comb_wig, stamp_receipt

        wig = self._wig()
        before = wig_content_hash(wig)
        stamp_receipt(wig, comb_wig(wig), "2026-08-01")
        assert wig_content_hash(wig) == before


# ---------------------------------------------------------------------------
# REPLACE starts fresh
# ---------------------------------------------------------------------------


class TestReplaceStartsFresh:
    """Owner ruling 2026-08-01. A replace clears the pin; the strip shows
    what the NEW capture decoded as and the fitter chooses again.

    The code and the decision about how to send it are written in ONE
    hash roll, so the row never exists in a state where the bytes and
    that decision disagree -- which is the state a fitting would then
    attest.
    """

    @pytest.fixture
    def wig_on_disk(self, fake_hass, tmp_path):
        from custom_components.hair.wig_format import serialize_wig

        wigs = tmp_path / "hair" / "wigs"
        wigs.mkdir(parents=True)
        wig = Wig(name="Dreo", signals=[
            WigSignal(alias="Power", pronto=PRONTO, bypass_protocol=True),
            WigSignal(alias="Mode", pronto=_PRONTO_B),
        ])
        (wigs / "dreo.wig.json").write_text(
            serialize_wig(wig), encoding="utf-8"
        )
        fake_hass.config.config_dir = str(tmp_path)
        return wigs / "dreo.wig.json"

    @pytest.mark.asyncio
    async def test_replace_without_the_pin_clears_it(
        self, fake_hass, wig_on_disk
    ):
        from custom_components.hair.wig_fitting import FittingManager

        manager = FittingManager(fake_hass, monitor=None)
        result = await manager.async_replace(
            "dreo.wig.json", 0, _PRONTO_C, "captured", "dab",
        )
        assert result["success"]
        await manager.async_flush()

        wig = parse_wig(wig_on_disk.read_text()).wig
        assert wig.signals[0].bypass_protocol is False

    @pytest.mark.asyncio
    async def test_replace_can_set_the_pin_in_the_same_roll(
        self, fake_hass, wig_on_disk
    ):
        from custom_components.hair.wig_fitting import FittingManager

        manager = FittingManager(fake_hass, monitor=None)
        before = parse_wig(wig_on_disk.read_text()).wig
        result = await manager.async_replace(
            "dreo.wig.json", 1, _PRONTO_C, "captured", "dab",
            bypass_protocol=True,
        )
        assert result["success"]
        await manager.async_flush()

        wig = parse_wig(wig_on_disk.read_text()).wig
        assert wig.signals[1].bypass_protocol is True
        # One roll: the hash moved once, covering both the code and the
        # decision about it.
        assert wig_content_hash(wig) != wig_content_hash(before)
        assert result["content_hash"] == wig_content_hash(wig)

    @pytest.mark.asyncio
    async def test_replacing_another_row_leaves_this_ones_pin_alone(
        self, fake_hass, wig_on_disk
    ):
        from custom_components.hair.wig_fitting import FittingManager

        manager = FittingManager(fake_hass, monitor=None)
        await manager.async_replace(
            "dreo.wig.json", 1, _PRONTO_C, "pasted", "dab",
        )
        await manager.async_flush()
        wig = parse_wig(wig_on_disk.read_text()).wig
        assert wig.signals[0].bypass_protocol is True


class TestExportRecipeMapping:
    """The export boundary maps IRCommand.repeat_count -> ditto_count,
    exactly as it maps tx_force_raw -> bypass_protocol.

    The rename is the point: internally HAIR calls dittos
    ``repeat_count`` while humans say "repeats" for send counts, and the
    portable format is the one place that ambiguity dies.
    """

    def _device(self, *, repeat_count, tx_force_raw):
        from custom_components.hair.models import CommandCategory, IRDevice

        device = IRDevice(name="Dreo", device_type="fan")
        from custom_components.hair.models import IRCommand

        command = IRCommand(
            name="Power",
            category=CommandCategory.CUSTOM,
            protocol="PRONTO",
            code=PRONTO,
        )
        command.repeat_count = repeat_count
        command.tx_force_raw = tx_force_raw
        device.commands.append(command)
        return device

    def test_repeat_count_becomes_ditto_count(self):
        from custom_components.hair.wig_export import build_wig_from_device

        build = build_wig_from_device(
            self._device(repeat_count=2, tx_force_raw=False)
        )
        assert build.wig.signals[0].ditto_count == 2
        assert build.notes == []

    def test_a_pinned_command_exports_zero_dittos_with_a_receipt(self):
        """Bypass and dittos are mutually exclusive: a raw blob has no
        ditto grammar, and writing one would contradict the pin's whole
        promise. The drop is announced rather than silent."""
        from custom_components.hair.wig_export import build_wig_from_device

        build = build_wig_from_device(
            self._device(repeat_count=2, tx_force_raw=True)
        )
        sig = build.wig.signals[0]
        assert sig.bypass_protocol is True
        assert sig.ditto_count == 0
        assert len(build.notes) == 1
        assert "Power" in build.notes[0]

    def test_a_pinned_command_with_no_dittos_needs_no_receipt(self):
        from custom_components.hair.wig_export import build_wig_from_device

        build = build_wig_from_device(
            self._device(repeat_count=0, tx_force_raw=True)
        )
        assert build.wig.signals[0].ditto_count == 0
        assert build.notes == []
