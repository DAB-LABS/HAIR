"""What a minted successor carries, and what it must not.

Three findings from the owner's bench run of the thinning patch
(2026-09-22), all of them in the SHARED write-through and exporter, so
all of them show up on a repair exactly as they do on a trim:

- **The descriptive fields were lost.** A device knows its name, its
  type and its codes. Brand, model, notes and the identity anchors live
  on the wig alone, so a wig built from the device started blank in all
  of them and the successor arrived without the brand and model its
  source had.
- **Portholes were minted as flat signals.** A command carrying
  ``matrix_cell`` is a VIEW of a lattice cell, not a code of its own.
  The exporter wrote it out beside the matrix, so the next person
  adopted "Cool 22" as a plain command sitting next to a lattice that
  already holds cool / 22, no longer a view of anything.
- **Deleting a porthole did not tell the live copies.** It writes the
  matrix through ``async_delete_cell``, which refreshes the manager's
  cache but sends no signal, so a running climate entity kept offering
  the cell until the next restart.

Driven through a real adopt and a real closet, on both paths.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.hair.matrix_store import SIGNAL_MATRIX_CHANGED
from custom_components.hair.models import CommandSource, IRCommand, IRDevice
from custom_components.hair.tests.test_matrix_thin import (
    PR19,
    SOURCE,
    _adopt,
    _call,
    _komeco,
    _load,
    _p,
    _thin,
)
from custom_components.hair.tests.test_tangles_writethrough import (
    KOMECO,
    _repair_the_donors,
    _wire,
)
from custom_components.hair.websocket_api import (
    ws_delete_command,
    ws_device_matrix_thin,
    ws_wig_make_device,
)
from custom_components.hair.wig_comb import comb_wig, stamp_receipt
from custom_components.hair.wig_export import (
    build_wig_from_device,
    carry_descriptive,
)
from custom_components.hair.wig_format import (
    Wig,
    WigSignal,
    normalize_kind,
    parse_wig,
    serialize_wig,
)
from custom_components.hair.wig_store import ensure_wigs_dir, wigs_dir


@pytest.fixture
def no_signing(monkeypatch):
    monkeypatch.setattr(
        "custom_components.hair.fitting_signing.async_get_private_key",
        AsyncMock(return_value=None),
    )


@pytest.fixture
def dispatched(monkeypatch):
    """Every signal the websocket layer sends, in order."""
    sent: list = []
    monkeypatch.setattr(
        "custom_components.hair.websocket_api.async_dispatcher_send",
        lambda _hass, signal, *args: sent.append((signal, *args)),
    )
    return sent


@pytest.fixture
async def repair_bench(fake_hass, tmp_path):
    """The repair path's harness: an adopted Komeco with real findings,
    wired the way ``test_tangles_writethrough`` wires it."""
    parsed = parse_wig(KOMECO.read_text(encoding="utf-8"))
    assert parsed.wig is not None, parsed.errors
    wig = parsed.wig
    stamp_receipt(wig, comb_wig(wig), "2026-08-22")
    ensure_wigs_dir(tmp_path)
    (wigs_dir(tmp_path) / SOURCE).write_text(
        serialize_wig(wig), encoding="utf-8")
    devices = _wire(fake_hass, tmp_path)
    await _call(ws_wig_make_device, fake_hass, {
        "id": 1, "type": "hair/wigs/make-device", "filename": SOURCE,
        "name": "Komeco", "device_type": "ac",
        "emitter_entity_ids": ["infrared.blaster"],
    })
    return fake_hass, devices[0], tmp_path, wig


@pytest.fixture
async def thin_bench(fake_hass, tmp_path):
    """The thinning path's harness: the same wig, adopted through the
    manager ``test_matrix_thin`` wires, whose matrix calls are real."""
    device, manager, listener = await _adopt(fake_hass, tmp_path, _komeco())
    return fake_hass, device, tmp_path, manager, listener


DESCRIPTIVE = ("brand", "model", "notes", "kind")


def _assert_carried(successor: Wig, source: Wig) -> None:
    """Every descriptive field the source had, on the successor.

    ``kind`` is compared through ``normalize_kind``: the bundled Komeco
    says ``airconditioner``, which the list retired in favour of ``ac``,
    and a mint stamps the current word from the device type. That is
    the same kind, spelled as the list spells it today, not a loss.
    """
    for name in ("brand", "model", "notes"):
        assert getattr(successor, name) == getattr(source, name), name
    assert successor.kind == normalize_kind(source.kind)
    assert successor.identifiers == source.identifiers


def _porthole(name: str, coords: dict) -> IRCommand:
    return IRCommand(
        name=name, protocol="PRONTO", code=_p(7000 + len(name)),
        source=CommandSource.MATRIX, repeat_count=0,
        matrix_cell=dict(coords), comb_suspect=True,
    )


def _flat(name: str, n: int) -> IRCommand:
    return IRCommand(name=name, protocol="PRONTO", code=_p(n),
                     repeat_count=0)


# ---------------------------------------------------------------------------
# The exporter, on its own
# ---------------------------------------------------------------------------


class TestTheExporter:
    def _device(self):
        device = IRDevice(name="Bedroom AC", climate_matrix=True)
        device.commands = [
            _flat("Ionizer", 8001),
            _porthole("Cool 22", {"mode": "cool", "fan": "auto",
                                  "swing": None, "temp": 22.0}),
            _flat("Sleep timer", 8002),
        ]
        return device

    def test_a_porthole_is_never_a_flat_signal(self):
        build = build_wig_from_device(self._device())
        assert [s.alias for s in build.wig.signals] == [
            "Ionizer", "Sleep timer",
        ]
        assert len(build.sources) == 2

    def test_the_sources_still_line_up_with_the_signals(self):
        """``build_save_plan`` reads ``sources[i]`` for signal ``i``; a
        filter that dropped the row but kept its id would hand every row
        after it the wrong command."""
        device = self._device()
        build = build_wig_from_device(device)
        by_id = {c.id: c.name for c in device.commands}
        assert [by_id[cid] for cid in build.sources] == [
            s.alias for s in build.wig.signals
        ]

    def test_a_porthole_is_not_counted_as_skipped(self):
        """Skipped means a code that could not be exported. This one is
        exported, as a cell."""
        assert build_wig_from_device(self._device()).skipped == 0

    def test_a_matrix_device_of_portholes_alone_still_exports(self):
        device = IRDevice(name="Bedroom AC", climate_matrix=True)
        device.commands = [_porthole("Cool 22", {"mode": "cool"})]
        build = build_wig_from_device(device, _komeco().climate)
        assert build.wig is not None
        assert build.wig.signals == []
        assert len(build.wig.climate.cells) == 1156


class TestCarryDescriptive:
    def _source(self) -> Wig:
        return Wig(
            name="Komeco KOS 09QC 3HX", signals=[],
            brand="Komeco", model="KOS 09QC 3HX", kind="airconditioner",
            notes="Based on the 1581 codeset.",
            identifiers={"chipset": "ZHLT01", "aliases": ["Chigo"]},
        )

    def test_it_fills_every_empty_field(self):
        built = Wig(name="Bedroom AC", signals=[])
        assert sorted(carry_descriptive(built, self._source())) == [
            "brand", "identifiers", "kind", "model", "notes",
        ]
        for name in DESCRIPTIVE:
            assert getattr(built, name) == getattr(self._source(), name)
        assert built.identifiers == self._source().identifiers

    def test_it_never_overwrites_what_the_device_already_has(self):
        built = Wig(name="Bedroom AC", signals=[], brand="Fujitsu",
                    kind="airconditioner",
                    identifiers={"chipset": "AR-RBE1E"})
        carried = carry_descriptive(built, self._source())
        assert sorted(carried) == ["model", "notes"]
        assert built.brand == "Fujitsu"
        assert built.kind == "airconditioner"
        assert built.identifiers == {"chipset": "AR-RBE1E"}

    def test_the_identifiers_are_copied_not_shared(self):
        source = self._source()
        built = Wig(name="Bedroom AC", signals=[])
        carry_descriptive(built, source)
        built.identifiers["chipset"] = "changed"
        built.identifiers["aliases"].append("Eurom")
        assert source.identifiers == {
            "chipset": "ZHLT01", "aliases": ["Chigo"],
        }

    def test_a_source_with_nothing_to_give_changes_nothing(self):
        built = Wig(name="Bedroom AC", signals=[])
        assert carry_descriptive(built, Wig(name="Bare", signals=[])) == []
        assert built.brand is None


# ---------------------------------------------------------------------------
# The repair path
# ---------------------------------------------------------------------------


class TestARepairsSuccessor:
    @pytest.mark.asyncio
    async def test_it_carries_brand_model_notes_and_kind(
            self, repair_bench, no_signing):
        hass, device, tmp_path, source = repair_bench
        result = await _repair_the_donors(hass, device)
        successor = _load(tmp_path, result["wig"]["filename"])
        _assert_carried(successor, source)
        assert successor.brand == "Komeco"

    @pytest.mark.asyncio
    async def test_it_does_not_mint_portholes_as_signals(
            self, repair_bench, no_signing):
        hass, device, tmp_path, _source = repair_bench
        device.commands.extend([
            _porthole("Cool 22", {"mode": "cool", "fan": "auto",
                                  "swing": "off", "temp": 22.0}),
            _flat("Ionizer", 8003),
        ])
        result = await _repair_the_donors(hass, device)
        successor = _load(tmp_path, result["wig"]["filename"])
        aliases = [s.alias for s in successor.signals]
        assert "Cool 22" not in aliases
        assert aliases == ["Ionizer"]
        # The cell the porthole looks at is still in the lattice.
        assert len(successor.climate.cells) == 1156


# ---------------------------------------------------------------------------
# The thinning path
# ---------------------------------------------------------------------------


class TestAThinsSuccessor:
    @pytest.mark.asyncio
    async def test_it_carries_brand_model_notes_and_kind(
            self, thin_bench, no_signing, dispatched):
        hass, device, tmp_path, _m, _l = thin_bench
        source = _load(tmp_path, SOURCE)
        result = await _call(ws_device_matrix_thin, hass, _thin(device, PR19))
        successor = _load(tmp_path, result["wig"]["filename"])
        _assert_carried(successor, source)
        assert len(successor.climate.cells) == 834

    @pytest.mark.asyncio
    async def test_a_surviving_porthole_is_not_minted_as_a_signal(
            self, thin_bench, no_signing, dispatched):
        """The bench case: three portholes survived the trim and rode
        out as three flat commands beside the lattice."""
        hass, device, _tmp, _m, _l = thin_bench
        device.commands.extend([
            _porthole("Cool 22", {"mode": "cool", "fan": "auto",
                                  "swing": "off", "temp": 22.0}),
            _porthole("Heat 25", {"mode": "heat", "fan": "auto",
                                  "swing": "off", "temp": 25.0}),
            _flat("Ionizer", 8004),
        ])
        result = await _call(ws_device_matrix_thin, hass, _thin(device, PR19))
        assert result["thinned"]["portholes_removed"] == []
        successor = _load(_tmp, result["wig"]["filename"])
        assert [s.alias for s in successor.signals] == ["Ionizer"]
        # Both portholes are still on the DEVICE: their cells survived.
        assert {"Cool 22", "Heat 25"} <= {c.name for c in device.commands}


# ---------------------------------------------------------------------------
# Deleting a porthole
# ---------------------------------------------------------------------------


class TestDeletingAPorthole:
    @pytest.mark.asyncio
    async def test_it_tells_everything_that_holds_a_copy(
            self, thin_bench, no_signing, dispatched):
        hass, device, _tmp, manager, listener = thin_bench
        porthole = _porthole("Cool 22", {"mode": "cool", "fan": "auto",
                                         "swing": "off", "temp": 22.0})
        device.commands.append(porthole)
        await _call(ws_delete_command, hass, {
            "id": 3, "type": "hair/command/delete",
            "device_id": device.id, "command_id": porthole.id,
        })
        assert (SIGNAL_MATRIX_CHANGED, device.id) in dispatched
        listener.invalidate.assert_called_with(device.id)
        matrix = await manager.async_get_matrix(device.id)
        assert len(matrix.cells) == 1155

    @pytest.mark.asyncio
    async def test_an_ordinary_command_delete_signals_nothing(
            self, thin_bench, no_signing, dispatched):
        """No cell moved, so nothing holding a lattice needs waking."""
        hass, device, _tmp, _m, listener = thin_bench
        flat = _flat("Ionizer", 8005)
        device.commands.append(flat)
        await _call(ws_delete_command, hass, {
            "id": 4, "type": "hair/command/delete",
            "device_id": device.id, "command_id": flat.id,
        })
        assert dispatched == []
        listener.invalidate.assert_not_called()


def test_the_exporter_keeps_real_signals_out_of_the_lattices_way():
    """A flat signal beside a matrix is still exported: thinning and
    the porthole rule never touch them (thinning-plan.md 10)."""
    device = IRDevice(name="Bedroom AC", climate_matrix=True)
    device.commands = [_flat("Ionizer", 8006)]
    build = build_wig_from_device(device, _komeco().climate)
    assert [s.alias for s in build.wig.signals] == ["Ionizer"]
    assert isinstance(build.wig.signals[0], WigSignal)
