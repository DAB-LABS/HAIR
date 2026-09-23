"""Power codes are not state frames, and a power row is not a cell.

Two bugs the owner hit on the bench (2026-09-23) with a Fujitsu
AR-RBE1E adopted fresh from the closet, each blocking on its own:

1. **The comb judged Off against the state frames.** Fujitsu sends full
   state as a 16-byte frame and power-off as a 7-byte one, by design.
   The comb built one shape population out of every cell PLUS the power
   codes, so the modal shape was always the state frame and the
   device's own correct Off was reported ``malformed`` /
   ``comb.frame_short`` with ``{"frame": "0", "timings": "144"}``. That
   put Off in Needs attention, and an open row there blocks the Perfect
   Fit, so the wig could not be fitted at all.
2. **A power row fell into the cell repair path.** ``list_tangles``
   emits Off and On as ``cell`` rows keyed ``"off"`` / ``"on"``, and
   the doors searched ``matrix.cells`` for a cell of that name: no
   match, ``no_finding``, "That cell is gone". Capturing Off from
   another remote was unreachable.

The fixture here is Fujitsu-SHAPED, built from the bytes the owner's
device decodes to (``14 63 00 10 10 02 FD``, 56 bits at 38 kHz) and
16-byte state frames beside them, so the 7-versus-16-byte relationship
is the real one. It reproduces the bench finding exactly on the old
code: frame 0, 144 timings short.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.models import (
    CommandCategory,
    IRCommand,
    IRDevice,
)
from custom_components.hair.tangles import (
    APPLY_NO_FINDING,
    APPLY_NOTHING_TO_REVERT,
    POWER_RECORD_KEY,
    PROVENANCE_KEY,
    TARGET_CELL,
    PowerHolder,
    holders_for_target,
    is_power_key,
    list_tangles,
    read_repair,
    record_holders,
    repair_bytes,
    resolve_holder,
    target_is_gone,
    written_digest,
)
from custom_components.hair.websocket_api import (
    ws_device_tangles,
    ws_tangle_apply,
    ws_tangle_apply_batch,
    ws_tangle_keep,
    ws_tangle_listen,
    ws_tangle_plan,
    ws_tangle_pre_read,
    ws_tangle_revert,
    ws_tangle_revert_run,
    ws_tangle_test_send,
)
from custom_components.hair.wig_comb import (
    CHECK_FIELD_MISMATCH,
    CHECK_FRAME_SHAPE,
    CHECK_MALFORMED,
    DECLINE_POWER_CODE,
    comb_wig,
)
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateMatrix,
    Wig,
    parse_wig,
    validate_pronto,
)

FIXTURES = Path(__file__).parent / "fixtures"

#: The owner's Off, decoded: Fujitsu's short power-off command.
FUJITSU_OFF_BYTES = bytes([0x14, 0x63, 0x00, 0x10, 0x10, 0x02, 0xFD])
#: A 16-byte state frame in the same family's shape. The first five
#: bytes are the family's address, as the Off code above carries them.
FUJITSU_STATE_HEAD = bytes([0x14, 0x63, 0x00, 0x10, 0x10, 0xFE, 0x09, 0x30])

# Fujitsu AC timings, in Pronto units at 38 kHz (one unit is about
# 26.3 microseconds): leader, then one pair per bit, then a trailer.
_LEAD = (0x007E, 0x003C)
_MARK = 0x0011
_ZERO = 0x0011
_ONE = 0x002F
_TAIL = (_MARK, 0x0400)


def _fujitsu(data: bytes) -> str:
    """One Fujitsu-shaped frame carrying ``data``, LSB first.

    Shape is what the comb reads: 8 pairs per byte plus a leader and a
    trailer, so a 16-byte state frame is 130 pairs and the 7-byte
    power-off is 58. The difference is 72 pairs, which is the 144
    timings the bench stamp reported.
    """
    pairs: list[tuple[int, int]] = [_LEAD]
    for byte in data:
        for bit in range(8):
            pairs.append((_MARK, _ONE if (byte >> bit) & 1 else _ZERO))
    pairs.append(_TAIL)
    words = [0x0000, 0x006D, len(pairs), 0x0000]
    for mark, space in pairs:
        words += [mark, space]
    return " ".join(f"{w:04X}" for w in words)


def _state(mode: str, temp: float) -> str:
    """A distinct 16-byte state frame per coordinate."""
    tail = bytes([
        int(temp) & 0xFF, 0x01 if mode == "cool" else 0x04, 0x00, 0x00,
        0x00, 0x00, 0x20, (int(temp) * 7 + len(mode)) & 0xFF,
    ])
    return _fujitsu(FUJITSU_STATE_HEAD + tail)


MODES = ("cool", "heat")
TEMPS = (19.0, 20.0, 21.0, 22.0, 23.0, 24.0)


def _fujitsu_matrix(**kw) -> ClimateMatrix:
    cells = [
        ClimateCell(mode=mode, fan="auto", temp=temp, pronto=_state(mode, temp))
        for mode in MODES for temp in TEMPS
    ]
    return ClimateMatrix(
        min_temp=19.0, max_temp=24.0, precision=1.0,
        modes=list(MODES), fan_modes=["auto"], swing_modes=[],
        off=kw.pop("off", _fujitsu(FUJITSU_OFF_BYTES)),
        on=kw.pop("on", None),
        cells=cells, **kw,
    )


def _fujitsu_wig(**kw) -> Wig:
    return Wig(name="Fujitsu AR-RBE1E", signals=[],
               climate=_fujitsu_matrix(**kw))


# ---------------------------------------------------------------------------
# Bug 1: the comb
# ---------------------------------------------------------------------------


class TestTheCombLeavesPowerCodesAlone:
    def test_the_fixture_is_the_real_relationship(self):
        """If the fixture were not 16 bytes against 7, everything below
        would be measuring something else."""
        assert validate_pronto(_fujitsu(FUJITSU_OFF_BYTES)).valid
        assert validate_pronto(_state("cool", 22.0)).valid
        assert validate_pronto(_fujitsu(FUJITSU_OFF_BYTES)).burst_pair_count == 58
        assert validate_pronto(_state("cool", 22.0)).burst_pair_count == 130

    def test_a_short_power_code_raises_nothing(self):
        report = comb_wig(_fujitsu_wig())
        assert [f.to_dict() for f in report.findings if "off" in f.keys] == []

    @pytest.mark.parametrize("message", [
        "comb.frame_short", "comb.frame_missing", "comb.frame_shape",
    ])
    def test_none_of_the_shape_messages_name_it(self, message):
        report = comb_wig(_fujitsu_wig())
        assert [f.keys for f in report.findings if f.message == message] == []

    def test_an_on_code_of_its_own_shape_is_left_alone_too(self):
        on = _fujitsu(bytes([0x14, 0x63, 0x00, 0x10, 0x10, 0x03, 0xFC]))
        report = comb_wig(_fujitsu_wig(on=on))
        assert [f.keys for f in report.findings
                if "on" in f.keys or "off" in f.keys] == []

    def test_a_truncated_state_frame_is_still_malformed(self):
        """The check still works. One cell loses its last four bytes;
        it is reported, and the power code beside it still is not."""
        matrix = _fujitsu_matrix()
        victim = next(c for c in matrix.cells
                      if c.mode == "cool" and c.temp == 21.0)
        victim.pronto = _fujitsu(FUJITSU_STATE_HEAD + bytes([21, 0x01, 0, 0]))
        report = comb_wig(Wig(name="Fujitsu", signals=[], climate=matrix))
        bad = [f for f in report.findings if f.check == CHECK_MALFORMED]
        assert [f.keys for f in bad] == [["cool/auto/21"]]
        assert bad[0].message == "comb.frame_short"
        assert "off" not in [key for f in report.findings for key in f.keys]

    def test_the_power_code_does_not_vote_on_the_modal_shape(self):
        """Not a voter either. Six cells in each mode, all 130 pairs,
        and a 58-pair Off: if Off voted, a small lattice could take the
        power frame as normal and condemn every cell."""
        matrix = _fujitsu_matrix()
        matrix.cells = [c for c in matrix.cells if c.temp in (19.0, 20.0)]
        report = comb_wig(Wig(name="Fujitsu", signals=[], climate=matrix))
        assert [f.check for f in report.findings
                if f.check in (CHECK_MALFORMED, CHECK_FRAME_SHAPE)] == []

    def test_the_coverage_says_why_they_were_not_judged(self):
        """Declined, not silently skipped: the receipt has to be able to
        say the check ran and what it left out."""
        report = comb_wig(_fujitsu_wig())
        shape = report.coverage.to_dict()["checks"][CHECK_FRAME_SHAPE]
        assert shape["declined"][DECLINE_POWER_CODE] == 1
        assert shape["checked"] == len(MODES) * len(TEMPS)
        on = _fujitsu(bytes([0x14, 0x63, 0x00, 0x10, 0x10, 0x03, 0xFC]))
        both = comb_wig(_fujitsu_wig(on=on)).coverage.to_dict()
        assert both["checks"][CHECK_FRAME_SHAPE]["declined"][
            DECLINE_POWER_CODE] == 2

    def test_the_power_codes_are_still_counted(self):
        """They leave the shape population and nothing else: the code
        count still includes them, and the repeat check still reads
        them (the coverage above records both)."""
        report = comb_wig(_fujitsu_wig())
        assert report.coverage.codes == len(MODES) * len(TEMPS) + 1
        on = _fujitsu(bytes([0x14, 0x63, 0x00, 0x10, 0x10, 0x03, 0xFC]))
        assert comb_wig(_fujitsu_wig(on=on)).coverage.codes == (
            len(MODES) * len(TEMPS) + 2
        )

    def test_another_check_can_still_name_a_power_code(self):
        """THE OTHER HALF OF THE RULE. Only the shape population lets
        them go. The field tier reads Off with its power coordinate and
        still reports it when the bytes say the unit is on -- the
        DAIKIN216 defects fixture carries exactly that, and it is what
        raises the power row the doors below are driven through."""
        wig = _daikin_defects()
        named = [
            f for f in comb_wig(wig).findings
            if "off" in f.keys and f.check == CHECK_FIELD_MISMATCH
        ]
        assert len(named) == 1
        assert named[0].params["field"] == "comb.field.power"


# ---------------------------------------------------------------------------
# Every existing comb fixture
# ---------------------------------------------------------------------------


#: Findings per fixture wig, CAPTURED FROM THE BASE TREE (224e3f8) and
#: then corrected for this change: every count is the base's, and the
#: fixtures where a power code was being judged against the state
#: frames are the ones whose count dropped. The report lists them.
FIXTURE_FINDINGS = {
    "adapters/smartir_climate_swing.json": 0,
    "adapters/smartir_fan_1220.json": 1,
    "adapters/smartir_light_brightness.json": 0,
    "adapters/smartir_media_player_1000.json": 1,
    "field-packs/DAIKIN216.defects.json": 48,
    "field-packs/DAIKIN216.json": 40,
    "gh108/cecotec-forceclima-12650.json": 2,
    "wigs/dreo-fan-dr-haf004s-perfect-fit.wig.json": 1,
    "wigs/komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json": 52,
}


def _fixture_wigs():
    """Every combable fixture: the closet wigs, and the adapter sources
    converted the way the suite's other corpus sweeps convert them."""
    from custom_components.hair import wig_adapters as wa

    for path in sorted((FIXTURES / "wigs").glob("*.wig.json")):
        parsed = parse_wig(path.read_text(encoding="utf-8"))
        if parsed.wig is not None:
            yield f"wigs/{path.name}", parsed.wig
    for path in sorted(FIXTURES.rglob("*.json")):
        try:
            text = path.read_text(encoding="utf-8")
            if wa.sniff_format(text) not in ("smartir_climate", "smartir"):
                continue
            converted = wa.convert(text, str(path))
        except Exception:  # not every fixture is an adapter source
            continue
        for wig in converted.wigs:
            yield str(path.relative_to(FIXTURES)), wig


class TestEveryFixtureIsUnchanged:
    def test_the_counts_are_the_base_trees(self):
        counts = {
            name: len(comb_wig(wig).findings)
            for name, wig in _fixture_wigs()
        }
        assert counts == FIXTURE_FINDINGS

    def test_no_fixture_finding_names_a_power_code_on_shape(self):
        """No fixture LOST a finding to this change -- none of them had
        a power code judged against its state frames -- and none can
        gain one either."""
        for name, wig in _fixture_wigs():
            if wig.climate is None:
                continue
            named = [
                f.to_dict() for f in comb_wig(wig).findings
                if f.check in (CHECK_MALFORMED, CHECK_FRAME_SHAPE)
                and ("off" in f.keys or "on" in f.keys)
            ]
            assert named == [], name


# ---------------------------------------------------------------------------
# Bug 2: the resolver
# ---------------------------------------------------------------------------


class TestTheResolver:
    def test_a_power_key_resolves_to_the_matrix(self):
        matrix = _fujitsu_matrix()
        device = IRDevice(name="Fujitsu", climate_matrix=True)
        holder = resolve_holder(device, matrix, TARGET_CELL, "off")
        assert isinstance(holder, PowerHolder)
        assert repair_bytes(holder) == matrix.off

    def test_writing_it_writes_the_matrix(self):
        matrix = _fujitsu_matrix()
        device = IRDevice(name="Fujitsu", climate_matrix=True)
        holder = resolve_holder(device, matrix, TARGET_CELL, "off")
        holder.pronto = _state("cool", 22.0)
        assert matrix.off == _state("cool", 22.0)
        assert all(c.pronto != matrix.off or c.mode == "cool"
                   for c in matrix.cells)

    def test_the_record_rides_the_matrix(self):
        matrix = _fujitsu_matrix()
        device = IRDevice(name="Fujitsu", climate_matrix=True)
        holder = resolve_holder(device, matrix, TARGET_CELL, "off")
        holder.extra[PROVENANCE_KEY] = {"origin": "fix"}
        assert matrix.extra[POWER_RECORD_KEY] == {
            "off": {PROVENANCE_KEY: {"origin": "fix"}},
        }
        assert read_repair(holder) == {"origin": "fix"}
        # And it is swept up again when it empties, so a matrix nobody
        # has repaired serializes as it always did.
        holder.extra.pop(PROVENANCE_KEY)
        holder.tidy()
        assert POWER_RECORD_KEY not in matrix.extra

    def test_an_absent_on_code_resolves_to_nothing(self):
        matrix = _fujitsu_matrix()
        device = IRDevice(name="Fujitsu", climate_matrix=True)
        assert matrix.on is None
        assert resolve_holder(device, matrix, TARGET_CELL, "on") is None
        assert holders_for_target(device, matrix, TARGET_CELL, "on") == []

    def test_a_power_code_has_no_portholes(self):
        matrix = _fujitsu_matrix()
        device = IRDevice(name="Fujitsu", climate_matrix=True)
        device.add_command(IRCommand(
            name="Off", protocol="PRONTO", code=matrix.off, repeat_count=0,
            matrix_cell={"mode": None, "fan": None, "swing": None,
                         "temp": None},
        ))
        holders = holders_for_target(
            device, matrix, TARGET_CELL, "off", {"power": "off"})
        assert len(holders) == 1
        assert isinstance(holders[0], PowerHolder)

    def test_record_holders_covers_cells_power_and_commands(self):
        matrix = _fujitsu_matrix(on=_fujitsu(bytes([0x14, 0x63, 0x03])))
        device = IRDevice(name="Fujitsu", climate_matrix=True)
        device.add_command(IRCommand(name="Ionizer", protocol="PRONTO",
                                     code=_state("heat", 20.0),
                                     repeat_count=0))
        holders = record_holders(device, matrix)
        assert len(holders) == len(matrix.cells) + 2 + 1
        assert sum(isinstance(h, PowerHolder) for h in holders) == 2

    def test_the_words_never_say_cell_about_a_power_code(self):
        assert target_is_gone(TARGET_CELL, "off") == "The Off code is gone"
        assert target_is_gone(TARGET_CELL, "on") == "The On code is gone"
        assert target_is_gone(TARGET_CELL, "cool/auto/22") == (
            "That cell is gone")
        assert target_is_gone("command", "Ionizer") == "That command is gone"
        assert is_power_key("off") and is_power_key("on")
        assert not is_power_key("cool/auto/22")

    def test_the_next_listings_digest_reads_the_matrix(self):
        """What an override's attestation is keyed on. Before the
        resolver this had its own copy of the power lookup; now it asks
        the same question every door asks."""
        matrix = _daikin_defects().climate
        device = IRDevice(name="Daikin", climate_matrix=True)
        row = _power_row(list_tangles(device, matrix))
        assert written_digest(device, matrix, row) == row.digest
        matrix.off = matrix.cells[0].pronto
        assert written_digest(device, matrix, row) != row.digest


# ---------------------------------------------------------------------------
# Bug 2: every door, on a power row
# ---------------------------------------------------------------------------


def _key_of(cell) -> str:
    from custom_components.hair.wig_format import cell_key

    return cell_key(cell)


def _power_row(listing):
    return next(
        row for row in listing.rows
        if row.target.kind == TARGET_CELL and is_power_key(row.target.key)
    )


def _daikin_defects() -> Wig:
    """The shipped DAIKIN216 defects pack, converted. Its Off reads as
    power-on under the ratified DAIKIN216 map, which is a real finding
    on a real power code and the row every door below is driven on."""
    from custom_components.hair import wig_adapters as wa

    path = FIXTURES / "field-packs" / "DAIKIN216.defects.json"
    converted = wa.convert(path.read_text(encoding="utf-8"), str(path))
    wig = next(w for w in converted.wigs if w.climate is not None)
    return wig


@pytest.fixture
def wired(fake_hass, tmp_path):
    """A Daikin device whose Off carries a field-mismatch of its own.

    Not a shape finding: shape no longer looks at power codes, and the
    doors still have to work for the checks that do.
    """
    matrix = _daikin_defects().climate
    device = IRDevice(name="Daikin", climate_matrix=True,
                      emitter_entity_ids=["infrared.blaster"])
    device.add_command(IRCommand(
        name="Ionizer", category=CommandCategory.CUSTOM,
        protocol="PRONTO", code=matrix.cells[0].pronto, repeat_count=0,
    ))
    manager = MagicMock()
    manager.get_device = MagicMock(return_value=device)
    manager.async_get_matrix = AsyncMock(return_value=matrix)
    manager.async_update_device = AsyncMock()
    manager.async_test_send = AsyncMock(return_value={"infrared.blaster"})
    listener = MagicMock()
    fake_hass.config.config_dir = str(tmp_path)
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": manager, "matrix_listener": listener,
        "store": MagicMock(get_all_devices=MagicMock(return_value=[device])),
    }}
    return fake_hass, device, matrix, manager, listener


class _Monitor:
    """The Sniffer's subscriber feed, as the listen door uses it."""

    def __init__(self):
        self.subscribers = []

    def subscribe(self, cb):
        self.subscribers.append(cb)

    def unsubscribe(self, cb):
        if cb in self.subscribers:
            self.subscribers.remove(cb)

    def emit(self, summary):
        for cb in list(self.subscribers):
            cb(summary)


def _signal_store(pronto: str):
    """The Sniffer's store, as the shared arm reads a capture out of it."""
    signal = MagicMock()
    signal.code = pronto
    signal.protocol = "PRONTO"
    signal.decoded_fingerprint = None
    signal.decoded_protocol = None
    signal.heard_by = ["infrared.receiver"]
    seen = MagicMock()
    seen.get_signal_by_id = MagicMock(return_value=signal)
    store = MagicMock()
    store.get_device = MagicMock(return_value=seen)
    return store


def _conn():
    connection = MagicMock()
    connection.send_result = MagicMock()
    connection.send_error = MagicMock()
    return connection


async def _door(handler, hass, payload, *, expect_error=None):
    connection = _conn()
    await handler(hass, connection, payload)
    if expect_error is None:
        connection.send_error.assert_not_called()
        return connection.send_result.call_args.args[1]
    assert connection.send_error.call_args.args[1] == expect_error
    return connection.send_error.call_args.args[2]


class TestTheListingRaisesThePowerRow:
    @pytest.mark.asyncio
    async def test_the_row_is_there_and_names_the_power_code(self, wired):
        hass, device, _matrix, _m, _l = wired
        listing = await _door(ws_device_tangles, hass, {
            "id": 1, "type": "hair/device/tangles", "device_id": device.id,
        })
        row = next(r for r in listing["rows"] if r["target"]["key"] == "off")
        assert row["target"]["kind"] == TARGET_CELL
        assert row["target"]["coordinates"] == {"power": "off"}
        assert row["id"] == "cell:off"


class TestEveryDoorOnAPowerRow:
    @pytest.mark.asyncio
    async def test_pre_read(self, wired):
        hass, device, _matrix, _m, _l = wired
        result = await _door(ws_tangle_pre_read, hass, {
            "id": 1, "type": "hair/device/tangle/pre-read",
            "device_id": device.id, "target": "cell:off",
            "pronto": _fujitsu(FUJITSU_OFF_BYTES),
        })
        assert "matches" in result

    @pytest.mark.asyncio
    async def test_test_send(self, wired):
        hass, device, _matrix, manager, _l = wired
        await _door(ws_tangle_test_send, hass, {
            "id": 1, "type": "hair/device/tangle/test-send",
            "device_id": device.id, "pronto": _fujitsu(FUJITSU_OFF_BYTES),
        })
        manager.async_test_send.assert_awaited_once_with(
            device.id, _fujitsu(FUJITSU_OFF_BYTES), send_count=1,
            heard_future=ANY,
        )

    @pytest.mark.asyncio
    async def test_listen(self, wired):
        """LISTEN resolves the row like any other and reads the capture
        back against the power code's own coordinates. It writes
        nothing, so there is nothing to land in a cell -- what is pinned
        here is that the arm happens at all, which it could not before:
        an unresolvable target refuses with ``unknown_target``."""
        hass, device, matrix, _m, _l = wired
        hass.data[DOMAIN]["entry-1"]["signal_monitor"] = _Monitor()
        hass.data[DOMAIN]["entry-1"]["signal_store"] = _signal_store(
            matrix.off)
        connection = _conn()
        connection.subscriptions = {}
        await ws_tangle_listen(hass, connection, {
            "id": 1, "type": "hair/device/tangle/listen",
            "device_id": device.id, "target": "cell:off",
        })
        connection.send_error.assert_not_called()
        assert connection.send_result.call_args.args[1] == {"listening": True}

        hass.data[DOMAIN]["entry-1"]["signal_monitor"].emit({
            "device_id": "d", "device_fingerprint": "f", "signal_id": "s",
            "protocol": "PRONTO", "code": matrix.off,
        })
        event = connection.send_event.call_args.args[1]
        assert event["target"] == "cell:off"
        # Read against the power code's own coordinates, not a cell's:
        # the matrix's own Off bytes come back as a match.
        # Read against the power code's OWN coordinates: the verdict
        # claims power off, because that is what this target is, and
        # says the bytes read as power on. A cell lookup could not have
        # produced either half of that sentence.
        verdict = event["verdict"]
        assert verdict["claims"] == {"power": "off"}
        assert verdict["reads_as"]["power"] == "on"
        assert verdict["mismatches"] == ["power"]

    @pytest.mark.asyncio
    async def test_listen_refuses_a_power_target_that_is_not_flagged(
        self, wired,
    ):
        """The refusal path still works, and it is the row lookup that
        refuses -- not a cell search that never knew about power."""
        hass, device, _matrix, _m, _l = wired
        hass.data[DOMAIN]["entry-1"]["signal_monitor"] = _Monitor()
        hass.data[DOMAIN]["entry-1"]["signal_store"] = _signal_store("")
        connection = _conn()
        connection.subscriptions = {}
        await ws_tangle_listen(hass, connection, {
            "id": 1, "type": "hair/device/tangle/listen",
            "device_id": device.id, "target": "cell:on",
        })
        assert connection.send_error.call_args.args[1] == "unknown_target"

    @pytest.mark.asyncio
    async def test_apply_writes_the_matrix_and_never_a_cell(self, wired):
        hass, device, matrix, _m, _l = wired
        before = [c.pronto for c in matrix.cells]
        fresh = _fujitsu(FUJITSU_OFF_BYTES)
        result = await _door(ws_tangle_apply, hass, {
            "id": 1, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": "cell:off",
            "source": "capture", "pronto": fresh, "tested": True,
        })
        assert result["applied"] is True
        assert matrix.off == fresh
        assert [c.pronto for c in matrix.cells] == before
        record = matrix.extra[POWER_RECORD_KEY]["off"][PROVENANCE_KEY]
        assert record["origin"] == "fix"
        assert record["tier"] == "accepted"
        assert record["prior"]["pronto"] != fresh

    @pytest.mark.asyncio
    async def test_apply_no_longer_says_that_cell_is_gone(self, wired):
        """The bench refusal. The row resolves now, so the only way to
        see the message is to ask for a power code the matrix lacks."""
        hass, device, matrix, _m, _l = wired
        matrix.on = None
        message = await _door(ws_tangle_apply, hass, {
            "id": 1, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": "cell:on",
            "source": "capture", "pronto": _fujitsu(FUJITSU_OFF_BYTES),
            "tested": True,
        }, expect_error=APPLY_NO_FINDING)
        assert "cell" not in message

    @pytest.mark.asyncio
    async def test_revert_puts_the_matrix_back(self, wired):
        hass, device, matrix, _m, _l = wired
        original = matrix.off
        fresh = _fujitsu(FUJITSU_OFF_BYTES)
        await _door(ws_tangle_apply, hass, {
            "id": 1, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": "cell:off",
            "source": "capture", "pronto": fresh, "tested": True,
        })
        result = await _door(ws_tangle_revert, hass, {
            "id": 2, "type": "hair/device/tangle/revert",
            "device_id": device.id, "target": "cell:off",
        })
        assert result["reverted"] is True
        assert matrix.off == original
        # And the record is swept up, so the block serializes as it did.
        assert POWER_RECORD_KEY not in matrix.extra

    @pytest.mark.asyncio
    async def test_revert_with_nothing_repaired_is_refused(self, wired):
        hass, device, _matrix, _m, _l = wired
        await _door(ws_tangle_revert, hass, {
            "id": 1, "type": "hair/device/tangle/revert",
            "device_id": device.id, "target": "cell:off",
        }, expect_error=APPLY_NOTHING_TO_REVERT)

    @pytest.mark.asyncio
    async def test_plan_and_apply_batch_and_revert_run(self, wired):
        hass, device, matrix, _m, _l = wired
        original = matrix.off
        fresh = _fujitsu(FUJITSU_OFF_BYTES)
        listing = list_tangles(device, matrix)
        row = _power_row(listing)
        cluster = next(c for c in listing.clusters if row.id in c.members)
        plan = await _door(ws_tangle_plan, hass, {
            "id": 1, "type": "hair/device/tangle/plan",
            "device_id": device.id, "cluster": cluster.id,
            "candidates": {row.id: fresh},
        })
        assert row.id in plan["candidates"]
        result = await _door(ws_tangle_apply_batch, hass, {
            "id": 2, "type": "hair/device/tangle/apply-batch",
            "device_id": device.id, "cluster": cluster.id,
            "tested": True, "tested_targets": [row.id],
            "candidates": {row.id: fresh},
        })
        assert result["applied"] == 1
        assert matrix.off == fresh
        run = result["run"]
        undone = await _door(ws_tangle_revert_run, hass, {
            "id": 3, "type": "hair/device/tangle/revert-run",
            "device_id": device.id, "run": run,
        })
        assert undone["reverted"] == 1
        assert matrix.off == original

    @pytest.mark.asyncio
    async def test_keep(self, wired):
        hass, device, matrix, _m, _l = wired
        result = await _door(ws_tangle_keep, hass, {
            "id": 1, "type": "hair/device/tangle/keep",
            "device_id": device.id, "target": "cell:off", "tested": True,
        })
        assert result["attested"] is True
        assert result["record"]["target"] == "off"
        # The answer settles the row: it leaves the work list.
        settled = list_tangles(device, matrix)
        assert [r.target.key for r in settled.rows
                if is_power_key(r.target.key)] == []

    @pytest.mark.asyncio
    async def test_a_cell_row_still_behaves_exactly_as_before(self, wired):
        """The shared resolver is not a power-only path: a cell row
        still writes its cell and its portholes."""
        hass, device, matrix, _m, _l = wired
        row = next(
            r for r in list_tangles(device, matrix).rows
            if not is_power_key(r.target.key)
        )
        victim = next(c for c in matrix.cells
                      if _key_of(c) == row.target.key)
        device.add_command(IRCommand(
            name="Porthole", protocol="PRONTO", code=victim.pronto,
            repeat_count=0, matrix_cell=dict(row.target.coordinates),
        ))
        fresh = matrix.cells[-1].pronto
        await _door(ws_tangle_apply, hass, {
            "id": 1, "type": "hair/device/tangle/apply",
            "device_id": device.id, "target": row.id,
            "source": "capture", "pronto": fresh, "tested": True,
            "reading_disagreed": True,
        })
        assert victim.pronto == fresh
        porthole = next(c for c in device.commands if c.name == "Porthole")
        assert porthole.code == fresh
        assert read_repair(porthole) is not None
        assert POWER_RECORD_KEY not in matrix.extra


# ---------------------------------------------------------------------------
# The owner's path, end to end
# ---------------------------------------------------------------------------


class TestTheBenchDevice:
    """A device adopted BEFORE the fix, whose wig's comb stamp still
    carries the Off finding. It must lose the row without re-adopting,
    and the Perfect Fit must stop being blocked by it."""

    def _stamped_wig(self) -> Wig:
        wig = _fujitsu_wig()
        wig.extra["comb"] = {
            "version": 2, "combed": "2026-09-23", "suspects": 1,
            "findings": [{
                "check": "malformed", "keys": ["off"],
                "message": "comb.frame_short",
                "params": {"frame": "0", "timings": "144"},
            }],
        }
        return wig

    @pytest.mark.asyncio
    async def test_the_off_row_is_gone_without_re_adopting(
            self, fake_hass, tmp_path):
        wig = self._stamped_wig()
        assert wig.extra["comb"]["findings"][0]["keys"] == ["off"]
        device = IRDevice(name="Fujitsu", climate_matrix=True,
                          emitter_entity_ids=["infrared.blaster"])
        manager = MagicMock()
        manager.get_device = MagicMock(return_value=device)
        manager.async_get_matrix = AsyncMock(return_value=wig.climate)
        manager.async_update_device = AsyncMock()
        fake_hass.config.config_dir = str(tmp_path)
        fake_hass.data[DOMAIN] = {"entry-1": {
            "device_manager": manager, "matrix_listener": MagicMock(),
        }}
        listing = await _door(ws_device_tangles, fake_hass, {
            "id": 1, "type": "hair/device/tangles", "device_id": device.id,
        })
        # THE LISTING RE-COMBS. It reads the device's live lattice
        # through project_device and comb_wig; the wig's stored stamp is
        # never consulted, so the stale finding cannot raise a row.
        assert [r["target"]["key"] for r in listing["rows"]] == []
        # And that is what the Save dialog gates the fit on.
        assert listing["rows"] == []
        assert json.dumps(listing["coverage"])
