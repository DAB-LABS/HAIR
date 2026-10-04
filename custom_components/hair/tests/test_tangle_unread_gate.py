"""A code the map cannot read at all needs Use it anyway at a cell.

Before this, both apply gates refused only a reading that said
something else (``matches`` False). A code the lattice's map could not
read at all (``matches`` None, no ``protocol``) walked straight
through: a NEC or Samsung press pasted at a Daikin cell, a capture cut
short, or the family's own code with one timing out of the map's
windows. The last is the quiet one: same shape, so the comb declines
the field check and the row leaves Needs attention without a trace.

One predicate decides, on the verdict as a dict, for the single apply,
the batch, and which batch records carry the reading:
``declaration_needed``. Its scope is lattice cells. A flat command has
no label to read against, and the matrix's Off and On are frames
several families send outside their map's layout (no Fujitsu 128-bit
file on record has an Off its map reads), so those keep applying as
they did.

THESE ARE THE REAL DOORS: ``ws_tangle_apply`` and
``ws_tangle_apply_batch`` on the Komeco wig and the DAIKIN216 defects
pack, with codes that fail the map in each way it can be failed.
"""
from __future__ import annotations

import copy
import dataclasses
import inspect
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair import field_readers, tangles, websocket_api
from custom_components.hair.const import DOMAIN
from custom_components.hair.models import (
    CommandCategory,
    IRCommand,
    IRDevice,
)
from custom_components.hair.tangles import (
    APPLY_DISAGREEMENT_UNDECLARED,
    DECLARE_READS_OTHERWISE,
    DECLARE_UNREAD,
    FIELD_TIER_NO_LATTICE,
    TARGET_CELL,
    TRIM_UNREAD,
    TangleTarget,
    build_provenance,
    declaration_needed,
    find_trim,
    list_tangles,
    pre_read,
    read_lattice,
    read_repair,
)
from custom_components.hair.websocket_api import (
    ws_tangle_apply,
    ws_tangle_apply_batch,
)
from custom_components.hair.wig_comb import CHECK_FIELD_MISMATCH
from custom_components.hair.wig_format import Wig, WigSignal, cell_key, parse_wig

from .leg import strict_nec_available
from .test_field_sweep import PACKS, _pack_wig

FIXTURES = Path(__file__).parent / "fixtures"
KOMECO = (FIXTURES / "wigs"
          / "komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json")
DREO = (FIXTURES / "wigs"
        / "dreo-fan-dr-haf004s-perfect-fit.wig.json")
EDITOR = (Path(__file__).parents[1] / "frontend" / "src"
          / "ir-signal-editor.ts")

#: The refusal's code, as a literal. The panel matches on this exact
#: text, so a second code for the unread case would close its ladder.
REFUSAL = "reading_disagreed_required"

DONOR_CARD = "same-shift:temperature:1:donor"

# A plain NEC frame (address 0x00, command 0x0F): a different remote.
NEC = ("0000 006D 0022 0000 0159 00AC" + " 0016 0016" * 8
       + " 0016 0042" * 8 + " 0016 0016 0016 0042" * 4
       + " 0016 0042 0016 0016" * 4 + " 0016 0BBA")


def _samsung() -> str:
    """Samsung32, address 0x07 0x07, command 0x02 0xFD."""
    bits: list[int] = []
    for byte in (0x07, 0x07, 0x02, 0xFD):
        bits += [(byte >> index) & 1 for index in range(8)]
    words = ["0000", "006D", f"{len(bits) + 2:04X}", "0000", "00AB", "00AB"]
    for bit in bits:
        words += ["0016", "0041" if bit else "0016"]
    words += ["0016", "0BBA"]
    return " ".join(words)


SAMSUNG = _samsung()


def _body(pronto: str) -> tuple[list[str], list[str]]:
    words = pronto.split()
    once = int(words[2], 16)
    return words[:2], words[4:4 + 2 * once]


def _cut(pronto: str) -> str:
    """The code with its last 40 pairs gone: a capture cut short."""
    head, body = _body(pronto)
    body = body[: len(body) - 80]
    return " ".join([*head, f"{len(body) // 2:04X}", "0000", *body])


def _one_bad_timing(pronto: str, at: int = 60) -> str:
    """One payload space set to about 5 ms: the same shape, unreadable."""
    words = pronto.split()
    words[4 + 2 * at + 1] = "00BE"
    return " ".join(words)


def _with_burst(pronto: str) -> str:
    """A stray single-pair burst after the code."""
    head, body = _body(pronto)
    if int(body[-1], 16) < 0x400:
        body[-1] = "0BBA"
    body = [*body, "0016", "0BBA"]
    return " ".join([*head, f"{len(body) // 2:04X}", "0000", *body])


def _wig(path: Path) -> Wig:
    parsed = parse_wig(path.read_text())
    assert parsed.wig is not None, parsed.errors
    return parsed.wig


LATTICES = {
    "komeco": lambda: _wig(KOMECO),
    "daikin216": lambda: _pack_wig("DAIKIN216.defects.json"),
}

#: What each map makes of a NEC frame. Both are failed readings, and
#: the gate keys on neither string.
NEC_DECLINED = {
    "komeco": field_readers.NO_MAP,
    "daikin216": field_readers.UNREADABLE,
}


def _wire(hass, tmp_path, matrix=None, signals=(), name="dev"):
    device = IRDevice(name=name, climate_matrix=matrix is not None,
                      emitter_entity_ids=["infrared.blaster"])
    for signal in signals:
        device.add_command(IRCommand(
            name=signal.alias, category=CommandCategory.CUSTOM,
            protocol="PRONTO", code=signal.pronto,
        ))
    manager = MagicMock()
    manager.get_device = MagicMock(return_value=device)
    manager.async_get_matrix = AsyncMock(return_value=matrix)
    manager.async_update_device = AsyncMock()
    hass.config.config_dir = str(tmp_path)
    hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager, "matrix_listener": MagicMock(),
    }}
    return device


def _conn():
    connection = MagicMock()
    connection.send_result = MagicMock()
    connection.send_error = MagicMock()
    return connection


async def _apply(hass, device, target, pronto, **extra):
    connection = _conn()
    payload = {
        "id": 1, "type": "hair/device/tangle/apply",
        "device_id": device.id, "target": target,
        "pronto": pronto, "tested": True, "source": "paste",
    }
    payload.update(extra)
    await ws_tangle_apply(hass, connection, payload)
    return connection


def _refused_with(connection) -> str | None:
    if not connection.send_error.called:
        return None
    return connection.send_error.call_args.args[1]


def _cell_row(listing):
    return next(row for row in listing.rows
                if row.target.kind == TARGET_CELL
                and row.target.coordinates.get("mode")
                and CHECK_FIELD_MISMATCH in row.classes)


# ---------------------------------------------------------------------------
# The predicate
# ---------------------------------------------------------------------------


class TestThePredicate:
    def _lattice(self):
        return read_lattice(_wig(KOMECO).climate)

    def test_a_reading_that_says_otherwise(self):
        lattice = self._lattice()
        target = TangleTarget(kind=TARGET_CELL, key="cool/low/off/20",
                              coordinates={"mode": "cool"})
        assert declaration_needed(
            lattice, target, {"matches": False, "protocol": "ZHLT01"},
        ) == DECLARE_READS_OTHERWISE

    def test_no_reading_at_a_cell(self):
        lattice = self._lattice()
        target = TangleTarget(kind=TARGET_CELL, key="cool/low/off/20",
                              coordinates={"mode": "cool"})
        assert declaration_needed(
            lattice, target, {"matches": None, "protocol": None},
        ) == DECLARE_UNREAD

    def test_a_reading_by_another_name_is_no_reading(self):
        """Compared with the lattice's own map, not with None: a
        verdict that one day names what a decoder made of the bytes
        cannot open the gate by doing so."""
        lattice = self._lattice()
        assert lattice.field_map.protocol_id == "ZHLT01"
        target = TangleTarget(kind=TARGET_CELL, key="cool/low/off/20",
                              coordinates={"mode": "cool"})
        assert declaration_needed(
            lattice, target, {"matches": None, "protocol": "NEC"},
        ) == DECLARE_UNREAD
        assert declaration_needed(
            lattice, target, {"matches": True, "protocol": "ZHLT01"},
        ) is None

    def test_not_at_the_power_rows(self):
        lattice = self._lattice()
        for key in ("off", "on"):
            target = TangleTarget(kind=TARGET_CELL, key=key,
                                  coordinates={"power": key})
            assert declaration_needed(
                lattice, target, {"matches": None, "protocol": None},
            ) is None, key

    def test_not_on_a_lattice_without_a_map(self):
        target = TangleTarget(kind=TARGET_CELL, key="cool/low/off/20",
                              coordinates={"mode": "cool"})
        assert declaration_needed(
            read_lattice(None), target, {"matches": None, "protocol": None},
        ) is None


class TestTheRecordAsksThePredicate:
    """The record says a reading failed where the gate refused, and
    nowhere else. Keyed on ``protocol is None`` it would go silent the
    day a verdict names what a decoder made of the bytes, while the gate
    (compared with the lattice's own map) still held them: the refusal
    and the record disagreeing about the same code."""

    def _note(self, matrix, key, disagreed):
        lattice = read_lattice(matrix)
        device = IRDevice(name="record", climate_matrix=True)
        row = next(row for row in list_tangles(device, matrix).rows
                   if row.target.key == key)
        record = build_provenance(
            source="paste", prior_pronto=row.pronto, lattice=lattice,
            row=row, tested=True, disagreed=disagreed)
        return record["reading_disagreed"]

    def test_a_decoder_named_protocol_still_records_declined(self):
        matrix = _wig(KOMECO).climate
        key = _cell_row(list_tangles(
            IRDevice(name="record", climate_matrix=True), matrix,
        )).target.key
        note = self._note(matrix, key, {
            "matches": None, "protocol": "NEC",
            "declined": field_readers.NO_MAP,
            "decoded": {"protocol": "NEC"},
        })
        assert note == {"user_attested": True,
                        "declined": field_readers.NO_MAP,
                        "decoded_as": "NEC"}

    def test_not_at_the_off_row_the_gate_leaves_alone(self):
        """A declared write at Off needed no declaration, so the record
        carries the attestation and nothing about a failed reading."""
        matrix = _wig(KOMECO).climate
        matrix.off = matrix.cells[0].pronto
        note = self._note(matrix, "off", {
            "matches": None, "protocol": None,
            "declined": field_readers.NO_MAP,
            "decoded": {"protocol": "KASEIKYO56"},
        })
        assert note == {"user_attested": True}


# ---------------------------------------------------------------------------
# T6: the single apply
# ---------------------------------------------------------------------------


CANDIDATES = {
    "nec": lambda row: NEC,
    "samsung": lambda row: SAMSUNG,
    "cut": lambda row: _cut(row.pronto),
    "one-bad-timing": lambda row: _one_bad_timing(row.pronto),
}


class TestTheSingleApply:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("candidate", list(CANDIDATES))
    @pytest.mark.parametrize("lattice_name", list(LATTICES))
    async def test_refused_undeclared_and_recorded_declared(
            self, fake_hass, tmp_path, lattice_name, candidate):
        matrix = LATTICES[lattice_name]().climate
        device = _wire(fake_hass, tmp_path, matrix=matrix)
        row = _cell_row(list_tangles(device, matrix))
        pronto = CANDIDATES[candidate](row)
        verdict = pre_read(
            read_lattice(matrix), pronto, row.target.coordinates)
        assert verdict.protocol is None
        assert verdict.matches is None
        if candidate == "nec":
            assert verdict.declined == NEC_DECLINED[lattice_name]

        live = {cell_key(cell): cell for cell in matrix.cells}
        was = live[row.target.key].pronto
        refused = await _apply(fake_hass, device, row.id, pronto)
        assert _refused_with(refused) == REFUSAL
        assert live[row.target.key].pronto == was

        connection = await _apply(
            fake_hass, device, row.id, pronto, reading_disagreed=True)
        connection.send_error.assert_not_called()
        assert live[row.target.key].pronto == pronto
        note = read_repair(live[row.target.key])["reading_disagreed"]
        assert note["user_attested"] is True
        assert note["declined"] == verdict.declined
        decoded = (verdict.decoded or {}).get("protocol")
        if decoded:
            assert note["decoded_as"] == decoded
        else:
            assert "decoded_as" not in note
        # Samsung32 decodes on both legs; NEC only where the library's
        # strict decoder is installed (see leg.py).
        named = {"samsung": "SAMSUNG32"}
        if strict_nec_available():
            named["nec"] = "NEC"
        if candidate in named:
            assert note["decoded_as"] == named[candidate]

    @pytest.mark.asyncio
    async def test_the_real_off_at_the_off_row_needs_nothing(
            self, fake_hass, tmp_path):
        """The Off row is not gated: several families send an Off their
        map does not read. Here the Off slot carries a cell's code, so
        the comb files a power finding, and the real Off goes back in
        undeclared."""
        matrix = _wig(KOMECO).climate
        real_off = matrix.off
        matrix.off = matrix.cells[0].pronto
        device = _wire(fake_hass, tmp_path, matrix=matrix)
        row = next(row for row in list_tangles(device, matrix).rows
                   if row.target.key == "off")
        connection = await _apply(fake_hass, device, row.id, real_off)
        connection.send_error.assert_not_called()
        assert matrix.off == real_off

    @pytest.mark.asyncio
    async def test_a_flat_device_with_no_map_takes_a_paste(
            self, fake_hass, tmp_path):
        dreo = _wig(DREO)
        device = _wire(fake_hass, tmp_path, signals=dreo.signals,
                       name="Dreo")
        listing = list_tangles(device, None)
        assert listing.field_tier == FIELD_TIER_NO_LATTICE
        row = listing.rows[0]
        connection = await _apply(fake_hass, device, row.id, NEC)
        connection.send_error.assert_not_called()
        assert device.get_command(row.target.command_id).code == NEC

    @pytest.mark.asyncio
    async def test_a_flat_device_a_map_reads_takes_a_paste(
            self, fake_hass, tmp_path):
        """The case ``lattice.readable`` alone gets wrong. A map reads
        these buttons (the TCL112 vote is cast for a flat device too),
        but a button has no label to read a code against, and the panel
        calls this device unmapped, so a press it accepts must not be
        refused here."""
        cells = _pack_wig("TCL112.json").climate.cells[:12]
        signals = [WigSignal(alias=f"Button {index}", pronto=cell.pronto)
                   for index, cell in enumerate(cells)]
        # A second name over one code: a duplicate-labels row.
        signals[3] = WigSignal(alias=signals[3].alias,
                               pronto=signals[2].pronto)
        device = _wire(fake_hass, tmp_path, signals=signals, name="TCL")
        assert read_lattice(None, Wig(name="TCL", signals=signals)).readable
        listing = list_tangles(device, None)
        assert listing.field_tier == FIELD_TIER_NO_LATTICE
        row = listing.rows[0]
        connection = await _apply(fake_hass, device, row.id, NEC)
        connection.send_error.assert_not_called()
        assert device.get_command(row.target.command_id).code == NEC


# ---------------------------------------------------------------------------
# T7: the batch
# ---------------------------------------------------------------------------


class TestTheBatch:
    async def _batch(self, hass, device, cluster, supplied, **extra):
        connection = _conn()
        payload = {
            "id": 1, "type": "hair/device/tangle/apply_batch",
            "device_id": device.id, "cluster": cluster.id, "tested": True,
            "tested_targets": list(cluster.members), "candidates": supplied,
        }
        payload.update(extra)
        await ws_tangle_apply_batch(hass, connection, payload)
        return connection

    @pytest.mark.asyncio
    async def test_supplied_codes_the_map_cannot_read(
            self, fake_hass, tmp_path):
        matrix = _wig(KOMECO).climate
        device = _wire(fake_hass, tmp_path, matrix=matrix)
        listing = list_tangles(device, matrix)
        cluster = next(c for c in listing.clusters if c.id == DONOR_CARD)
        rows = {row.id: row for row in listing.rows}
        keys = [rows[member].target.key for member in cluster.members]
        supplied = dict.fromkeys(cluster.members, NEC)
        live = {cell_key(cell): cell for cell in matrix.cells}
        before = {key: live[key].pronto for key in keys}

        refused = await self._batch(fake_hass, device, cluster, supplied)
        assert _refused_with(refused) == REFUSAL
        assert {key: live[key].pronto for key in keys} == before

        connection = await self._batch(
            fake_hass, device, cluster, supplied, reading_disagreed=True)
        connection.send_error.assert_not_called()
        for key in keys:
            assert live[key].pronto == NEC, key
            note = read_repair(live[key])["reading_disagreed"]
            assert note["declined"] == field_readers.NO_MAP, key
            if strict_nec_available():
                assert note["decoded_as"] == "NEC", key
            else:
                assert "decoded_as" not in note, key

    def test_both_handlers_ask_the_one_predicate(self):
        for handler in (websocket_api.ws_tangle_apply,
                        websocket_api.ws_tangle_apply_batch):
            source = inspect.getsource(handler)
            assert "declaration_needed(" in source, handler.__name__
            assert '["matches"] is False' not in source, handler.__name__
            assert "verdict.matches is False" not in source, (
                handler.__name__)


# ---------------------------------------------------------------------------
# T8: one refusal code
# ---------------------------------------------------------------------------


class TestOneRefusalCode:
    def test_the_unread_case_shares_the_mismatch_code(self):
        """The panel raises its ladder on this literal. The unread
        refusals above are pinned to it at the door too."""
        assert APPLY_DISAGREEMENT_UNDECLARED == REFUSAL

    def test_the_panel_reads_the_code_where_the_client_puts_it(self):
        """The websocket client rejects with the server's plain
        ``{code, message}`` object, so the code is on ``err.code`` and
        never inside the message text. Both roads that can be refused
        (paste and capture) have to look there, or the ladder never
        rises and the refusal shows as a plain error."""
        text = EDITOR.read_text(encoding="utf-8")
        paste = text.split("private async _applyToTangle(", 1)[1].split(
            "\n    /** The ladder, from either road", 1)[0]
        capture = text.split("const message = IrSignalEditor._tangleError(err);",
                             1)[1].split("} finally {", 1)[0]
        for body in (paste, capture):
            assert "(err as { code?: unknown } | null)?.code" in body
            assert f'code === "{REFUSAL}"' in body
        assert 'this._raiseTangleLadder(this._pronto, "paste");' in paste
        assert 'this._raiseTangleLadder(pronto, "capture");' in capture

    def test_a_refused_paste_is_told_it_is_a_paste(self):
        """The press road's third rung says "we keep hearing a different
        press", which is false after one paste and points the wrong way
        for a code from another remote. Now that a refused paste raises
        the ladder, it gets a sentence of its own, and the press keeps
        the one it had."""
        text = EDITOR.read_text(encoding="utf-8")
        ladder = text.split("private _raiseTangleLadder(", 1)[1].split(
            "\n    }\n", 1)[0]
        squashed = " ".join(ladder.split())
        assert ('this._error = source === "paste" '
                '? t("tangles.paste_mismatch_noread") '
                ': t("tangles.listen_mismatch_3_noread");') in squashed
        locales = EDITOR.parent / "locales"
        english = json.loads(
            (locales / "en.json").read_text(encoding="utf-8"))
        sentence = english["tangles.paste_mismatch_noread"]
        assert "press" not in sentence.lower()
        assert "\u2014" not in sentence


# ---------------------------------------------------------------------------
# T9: a fix the listing offers is one the apply accepts undeclared
# ---------------------------------------------------------------------------


class TestEveryOfferIsAcceptedUndeclared:
    def _offers(self, matrix):
        listing = list_tangles(
            IRDevice(name="offers", climate_matrix=True), matrix)
        lattice = read_lattice(matrix)
        for row in listing.rows:
            if not row.donor:
                continue
            verdict = pre_read(
                lattice, row.donor["pronto"], row.target.coordinates)
            origin = (row.donor.get("reasoning") or {}).get("origin")
            yield row, origin or "donor", declaration_needed(
                lattice, row.target, verdict.as_dict())

    def test_every_pack_and_the_komeco_wig(self):
        """The field packs are sparse (five temperatures a column), so
        they offer no donor on their own; the Komeco wig is where the
        donors are. Counted, so the sweep cannot pass by finding
        nothing."""
        offered = 0
        matrices = [(path.name, _pack_wig(path.name).climate)
                    for path in sorted(PACKS.glob("*.json"))
                    if not path.name.endswith("-manifest.json")]
        matrices.append(("komeco", _wig(KOMECO).climate))
        for name, matrix in matrices:
            for row, origin, needed in self._offers(matrix):
                assert needed is None, (name, row.id, origin, needed)
                offered += 1
        assert offered >= 48

    def test_a_trim_of_a_readable_cell_is_offered_and_accepted(self):
        matrix = _wig(KOMECO).climate
        live = {cell_key(cell): cell for cell in matrix.cells}
        key = "heat_cool/high/off/24"
        live[key].pronto = _with_burst(live[key].pronto)
        trims = [(row, needed) for row, origin, needed in self._offers(matrix)
                 if origin == "trim" and row.target.key == key]
        assert len(trims) == 1
        assert trims[0][1] is None

    def test_a_trim_the_map_cannot_read_is_not_offered(self):
        """A cell the map already declines (one bad timing), plus a
        stray burst. The trim removes the burst and leaves bytes nothing
        reads, which both apply roads would hold for a declaration the
        Fixes ready card cannot ask for. So it is not offered, and the
        row is a recapture."""
        matrix = _wig(KOMECO).climate
        live = {cell_key(cell): cell for cell in matrix.cells}
        key = "heat_cool/high/off/24"
        live[key].pronto = _with_burst(_one_bad_timing(live[key].pronto))
        listing = list_tangles(
            IRDevice(name="trim", climate_matrix=True), matrix)
        row = next(row for row in listing.rows if row.target.key == key)
        assert not row.donor
        trimmed, why = find_trim(
            row.pronto, copy.deepcopy(row.findings), read_lattice(matrix),
            key, row.target.coordinates)
        assert trimmed is None
        assert why == TRIM_UNREAD
        cluster = next(c for c in listing.clusters if row.id in c.members)
        assert cluster.mechanic == "recapture"

    def test_a_decoder_naming_the_trimmed_bytes_does_not_offer_it(
            self, monkeypatch):
        """The trim gate compares with the lattice's own map, as the
        cell gate does, so a verdict that one day names what a decoder
        made of the bytes still leaves the trim unoffered."""
        matrix = _wig(KOMECO).climate
        live = {cell_key(cell): cell for cell in matrix.cells}
        key = "heat_cool/high/off/24"
        live[key].pronto = _with_burst(_one_bad_timing(live[key].pronto))
        listing = list_tangles(
            IRDevice(name="trim", climate_matrix=True), matrix)
        row = next(row for row in listing.rows if row.target.key == key)
        real = tangles.pre_read

        def named(*args, **kwargs):
            verdict = real(*args, **kwargs)
            if verdict.protocol is None:
                verdict = dataclasses.replace(verdict, protocol="NEC")
            return verdict

        monkeypatch.setattr(tangles, "pre_read", named)
        trimmed, why = find_trim(
            row.pronto, copy.deepcopy(row.findings), read_lattice(matrix),
            key, row.target.coordinates)
        assert trimmed is None
        assert why == TRIM_UNREAD
