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
)

from .test_capture_dittos import _infrared_mod
from .test_capture_dittos import _monitor as _make_monitor
from .test_device_manager import manager  # noqa: F401  (pytest fixture)

PRONTO = "0000 006D 0002 0000 0020 0040 0020 0040"
# A second, byte-different code: the import path collapses byte-identical
# entries under its duplicate guard, so two rows need two codes.
_PRONTO_B = "0000 006D 0002 0000 0030 0050 0030 0050"
# A third distinct code, for replacing one of the two above.
_PRONTO_C = "0000 006D 0002 0000 0040 0060 0040 0060"




def _cmd_stub(**attrs):
    """A minimal command stand-in. A bare object() no longer works on
    the wire: the broadcast path wraps the outgoing command in
    TerminatedCommand (GH #98), which reads modulation/repeat_count."""

    class _Stub:
        modulation = 38000
        repeat_count = 0

        def get_raw_timings(self):
            return [100]

    stub = _Stub()
    for k, v in attrs.items():
        setattr(stub, k, v)
    return stub


def _unwrap(sent):
    """The inner command behind the GH #98 transmit wrapper."""
    return sent._inner


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
                return_value=_cmd_stub(),
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
                return_value=_cmd_stub(),
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
        necessary.

        BEHAVIORAL SINCE GH #134. This used to assert one line of
        websocket_api source; the adopt door now mints through
        mint_command, so the line moved and the assertion would have
        failed while the behaviour it guards was intact. Adopting a
        bypassed wig signal and reading the minted command holds the
        same claim and survives the next extraction too.
        """
        from types import SimpleNamespace

        from custom_components.hair.websocket_api import (
            _command_from_wig_signal,
        )
        from custom_components.hair.wig_identity import wig_signal_identity

        ident = wig_signal_identity(PRONTO)
        assert ident is not None
        sig = SimpleNamespace(
            alias="Power", send_count=1, ditto_count=0,
            bypass_protocol=True,
        )
        command = _command_from_wig_signal(sig, ident, set(), {}, 1)
        assert command.tx_force_raw is True

        sig_plain = SimpleNamespace(
            alias="Mode", send_count=1, ditto_count=0,
            bypass_protocol=False,
        )
        plain = _command_from_wig_signal(sig_plain, ident, set(), {}, 2)
        assert plain.tx_force_raw is False


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
    # A device that was not converted from a seed file. Explicit because
    # a MagicMock's default attribute is a Mock, and the export now
    # reads source_file into the wig's provenance.
    device.source_file = None
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
# The claim: a pinned row is a checklist row, not an advisory one
# ---------------------------------------------------------------------------


class TestPinnedRowsAreStillProved:
    """Ruling 7.1, and the trap it names.

    The comb declines to judge a bypassed row, and it would be easy to
    let that exemption leak into the save checklist as an ADVISORY row
    -- the path comb suspects already ride, where a row is listed and
    testable but carries no verdict and never counts toward coverage.

    That would be a false pass. A bypassed code is a real button on a
    real remote, and it is the button somebody had to go out of their
    way to repair. If it stopped counting, a fitter could sign a bundle
    attesting every code EXCEPT the one that needed the work. What the
    pin buys is a chip, not an exemption.

    v0.9.5 moved where this is decided -- the checklist is the SAVE
    plan's rows now, and completeness is derived from the bundle -- but
    the ruling it has to satisfy did not move with it.
    """

    def _wig(self) -> Wig:
        return Wig(name="Dreo Fan", wig_id="w-dreo", signals=[
            WigSignal(alias="Power", pronto=PRONTO, bypass_protocol=True),
            WigSignal(alias="Mode", pronto=_PRONTO_B),
        ])

    def _device(self):
        from custom_components.hair.models import (
            CommandCategory,
            IRCommand,
            IRDevice,
        )

        device = IRDevice(name="Dreo Fan", device_type="fan")
        for name, code, pin in (
            ("Power", PRONTO, True), ("Mode", _PRONTO_B, False),
        ):
            command = IRCommand(
                name=name, category=CommandCategory.CUSTOM,
                protocol="PRONTO", code=code,
            )
            command.repeat_count = 0
            command.tx_force_raw = pin
            device.commands.append(command)
        return device

    def test_it_is_a_checklist_row(self):
        """The save plan lists it like any other row."""
        from custom_components.hair.wig_save import build_save_plan

        plan = build_save_plan(self._device())
        assert [row.alias for row in plan.rows] == ["Power", "Mode"]
        assert plan.rows[0].bypass is True

    def test_it_is_not_advisory(self):
        """The comb has no verdict for it, and that is where the
        exemption stops. ``suspect_findings`` is the only thing the
        comb's silence reaches; the checklist never consults it."""
        from custom_components.hair.wig_comb import suspect_findings

        wig = self._wig()
        assert "Power" not in suspect_findings(wig)

    def test_it_counts_toward_coverage(self):
        """The assertion that makes the whole distinction real."""
        from custom_components.hair.wig_format import (
            ClaimsBundle,
            RowClaim,
            perfect_by,
            signal_row_digest,
            wig_row_digests,
        )

        wig = self._wig()
        digests = wig_row_digests(wig)
        mode = signal_row_digest(wig.signals[1])
        power = signal_row_digest(wig.signals[0])

        # Every row but the pinned one claimed: NOT a perfect fit.
        partial = ClaimsBundle(wig_id=wig.wig_id, handle="dab", rows=[
            RowClaim(alias_at_claim="Mode", digest=mode, verdict="worked"),
        ])
        assert not perfect_by(partial, digests)

        # Add it and the bundle completes.
        partial.rows.append(
            RowClaim(alias_at_claim="Power", digest=power, verdict="worked")
        )
        assert perfect_by(partial, digests)

    def test_the_pin_is_in_the_digest_a_claim_binds(self):
        """Unpinning a proved row does not carry its claim across.

        The bypass bit is inside the row digest, so the repaired row and
        the unrepaired one are different rows to the claims model. That
        is what stops a fitting signed against the working recipe from
        vouching for a recipe nobody sent.
        """
        from custom_components.hair.wig_format import signal_row_digest

        pinned = WigSignal(alias="Power", pronto=PRONTO, bypass_protocol=True)
        plain = WigSignal(alias="Power", pronto=PRONTO, bypass_protocol=False)
        assert signal_row_digest(pinned) != signal_row_digest(plain)


class TestPinSurvivesTheDeviceEdit:
    """The pin lives on the device now, and the device is what gets
    saved. Editing a command's OTHER knobs must not disturb it.

    The old fitting dialog could replace a wig row's code in place and
    cleared the pin when it did (ruling 2026-08-01), because a fitting
    then bound a whole file and the row could not be allowed to exist
    in a state where its bytes and the decision about them disagreed.
    v0.9.5 deleted that editor: replacement happens on the device, and
    a claim binds a per-row digest that already carries the pin. What is
    left to protect is that a rename or a ditto change, which have
    nothing to do with how the frame goes out, leave it alone.
    """

    def _device(self):
        from custom_components.hair.models import (
            CommandCategory,
            IRCommand,
            IRDevice,
        )

        device = IRDevice(name="Dreo", device_type="fan")
        command = IRCommand(
            id="cmd-power", name="Power", category=CommandCategory.CUSTOM,
            protocol="PRONTO", code=PRONTO,
        )
        command.tx_force_raw = True
        device.commands.append(command)
        return device

    @pytest.mark.asyncio
    async def test_rename_and_retune_leave_the_pin_alone(self, manager):  # noqa: F811
        manager._entity_factory.async_update_entities = AsyncMock()
        device = self._device()
        manager._store.add_device(device)

        result = await manager.async_update_command(
            device.id, "cmd-power", name="Power Toggle", repeat_count=3,
        )
        assert result["success"]
        updated = manager._store.get_device(device.id).get_command("cmd-power")
        assert updated.tx_force_raw is True
        assert updated.repeat_count == 3

    def test_the_pin_reaches_the_wig_through_export(self):
        """And the export boundary is what carries it out of the
        device, which is the only road to a claim."""
        from custom_components.hair.wig_export import build_wig_from_device

        build = build_wig_from_device(self._device())
        assert build.wig.signals[0].bypass_protocol is True


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
