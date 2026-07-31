"""Smart Perm phase 1: REPLACE, carry-forward, Changed Codes.

The contracts under test (implementation brief Section 4, which is
itself the owner rulings of 2026-07-30 in buildable form):

- Replace is the ONLY path that changes a wig's codes. It validates,
  writes in place, stamps provenance, and rolls the content hash --
  and it refuses a code identical to the one already there, so
  "a marker exists" always implies "the hash rolled".
- Nothing edits a signed fitting. Replace re-binds the CALLING user's
  open draft and leaves everybody else's fittings to go stale by hash.
- Carry-forward is byte-exact or nothing, proven against the carry
  snapshot written at replace time -- never against the row key alone.
- Changed Codes rows join completeness like any other row, and a
  signal wig grows none of them because its signals already are rows.
- The listen window rides the Sniffer's subscriber feed and must never
  resolve on a Mirror row: that feed carries HAIR's own sends, so the
  filter is what stops a fitter's SEND from being captured as their
  remote's press.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.hair.const import DOMAIN, MIRROR_DEVICE_FP
from custom_components.hair.websocket_api import (
    ws_fitting_listen,
    ws_fitting_replace,
    ws_fitting_revert,
    ws_fitting_state,
)
from custom_components.hair.wig_fitting import (
    CARRY_KEY,
    FITTINGS_KEY,
    PROVENANCE_KEY,
    PROVENANCE_POWER_KEY,
    REPLACED_FROM_KEY,
    SECTION_CHANGED,
    FittingManager,
    carry_forward_seed,
    fitting_is_complete,
    fitting_is_valid,
    fitting_row_specs,
    fitting_rows,
    parse_fittings,
    pending_replaces,
    revertible_keys,
    shared_wig_text,
    wig_needs_share_strip,
)
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateMatrix,
    Wig,
    WigSignal,
    canonical_cells_json,
    canonical_signals_json,
    parse_wig,
    serialize_wig,
    wig_content_hash,
)

PRONTO_A = "0000 006D 0002 0000 0020 0040 0020 0040"
PRONTO_B = "0000 006D 0002 0000 0040 0020 0040 0020"
PRONTO_C = "0000 006D 0002 0000 0030 0030 0030 0060"
PRONTO_D = "0000 006D 0002 0000 0050 0010 0050 0010"

# The checklist the matrix fixture below derives, in walk order.
CHECKLIST_KEYS = [
    "on", "cool/auto/22", "dry/auto", "heat/auto/22", "cool/low/22",
    "cool/auto/16", "cool/auto/30", "off",
]


def _signal_wig(**extra) -> Wig:
    return Wig(
        name="TV",
        signals=[
            WigSignal(alias="Power On", pronto=PRONTO_A),
            WigSignal(alias="Power Off", pronto=PRONTO_B),
        ],
        extra=dict(extra),
    )


def _matrix_wig() -> Wig:
    """A matrix wig with one flat depth-0 extra riding along.

    The cool/auto branch runs 16 / 20 / 22 / 25 / 30 so the checklist
    still samples 22 as the median and 16 / 30 as the ends, which
    leaves ``cool/auto/25`` deliberately OUTSIDE the checklist: it is
    the cell the Changed Codes tests replace.
    """
    return Wig(
        name="Bedroom AC",
        kind="ac",
        signals=[WigSignal(alias="Sleep", pronto=PRONTO_C)],
        climate=ClimateMatrix(
            min_temp=16.0,
            max_temp=30.0,
            precision=1.0,
            modes=["cool", "dry", "heat"],
            fan_modes=["auto", "low"],
            swing_modes=[],
            off=PRONTO_A,
            on=PRONTO_B,
            cells=[
                ClimateCell(mode="cool", fan="auto", temp=16.0,
                            pronto=PRONTO_A),
                ClimateCell(mode="cool", fan="auto", temp=20.0,
                            pronto=PRONTO_D),
                ClimateCell(mode="cool", fan="auto", temp=22.0,
                            pronto=PRONTO_B),
                ClimateCell(mode="cool", fan="auto", temp=25.0,
                            pronto=PRONTO_C),
                ClimateCell(mode="cool", fan="auto", temp=30.0,
                            pronto=PRONTO_A),
                ClimateCell(mode="cool", fan="low", temp=22.0,
                            pronto=PRONTO_B),
                ClimateCell(mode="dry", fan="auto", pronto=PRONTO_A),
                ClimateCell(mode="heat", fan="auto", temp=22.0,
                            pronto=PRONTO_B, send_count=2),
            ],
        ),
    )


@pytest.fixture
def wigs_dir_path(tmp_path):
    d = tmp_path / "hair" / "wigs"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def manager(fake_hass, tmp_path):
    fake_hass.config.config_dir = str(tmp_path)
    return FittingManager(fake_hass, monitor=None)


def _write_wig(wigs_dir_path, wig, filename="tv.wig.json"):
    (wigs_dir_path / filename).write_text(
        serialize_wig(wig), encoding="utf-8"
    )
    return filename


def _read_wig(wigs_dir_path, filename="tv.wig.json"):
    result = parse_wig(
        (wigs_dir_path / filename).read_text(encoding="utf-8")
    )
    assert result.ok, result.errors
    return result.wig


def _index_of(wig: Wig, key: str) -> int:
    return [spec.key for spec in fitting_row_specs(wig)].index(key)


# ---------------------------------------------------------------------------
# Replace: signal wigs
# ---------------------------------------------------------------------------


class TestReplaceSignalWig:
    @pytest.mark.asyncio
    async def test_code_swapped_and_provenance_stamped(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        before = wig_content_hash(_read_wig(wigs_dir_path))

        result = await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        assert result["success"]
        await manager.async_flush()

        wig = _read_wig(wigs_dir_path)
        assert wig.signals[0].pronto == PRONTO_C
        assert wig.signals[1].pronto == PRONTO_B  # untouched
        marker = wig.signals[0].extra[PROVENANCE_KEY]
        assert marker["replaced"] == "captured"
        assert marker["date"]
        assert wig_content_hash(wig) != before
        assert result["content_hash"] == wig_content_hash(wig)

    @pytest.mark.asyncio
    async def test_pasted_source_recorded(self, manager, wigs_dir_path):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_replace(filename, 1, PRONTO_D, "pasted", "dab")
        await manager.async_flush()
        wig = _read_wig(wigs_dir_path)
        assert wig.signals[1].extra[PROVENANCE_KEY]["replaced"] == "pasted"

    @pytest.mark.asyncio
    async def test_repeat_replace_overwrites_the_marker(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_replace(filename, 0, PRONTO_C, "pasted", "dab")
        await manager.async_replace(filename, 0, PRONTO_D, "captured", "dab")
        await manager.async_flush()
        wig = _read_wig(wigs_dir_path)
        assert wig.signals[0].pronto == PRONTO_D
        assert wig.signals[0].extra[PROVENANCE_KEY]["replaced"] == "captured"

    @pytest.mark.asyncio
    async def test_invalid_pronto_refused_with_a_reason(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        result = await manager.async_replace(
            filename, 0, "not hex at all", "pasted", "dab"
        )
        assert not result["success"]
        assert result["code"] == "bad_pronto"
        assert result["error"]
        # Nothing written.
        assert _read_wig(wigs_dir_path).signals[0].pronto == PRONTO_A

    @pytest.mark.asyncio
    async def test_identical_code_refused(self, manager, wigs_dir_path):
        """A marker without a hash roll would append a Changed Codes row
        to a wig whose ledger never moved, demoting complete fittings
        under everyone holding one."""
        filename = _write_wig(wigs_dir_path, _signal_wig())
        result = await manager.async_replace(
            filename, 0, PRONTO_A.lower(), "pasted", "dab"
        )
        assert not result["success"] and result["code"] == "same_code"
        assert PROVENANCE_KEY not in _read_wig(wigs_dir_path).signals[0].extra

    @pytest.mark.asyncio
    async def test_bad_source_refused(self, manager, wigs_dir_path):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        result = await manager.async_replace(
            filename, 0, PRONTO_C, "rule-derived", "dab"
        )
        assert not result["success"] and result["code"] == "bad_source"

    @pytest.mark.asyncio
    async def test_bad_index_refused(self, manager, wigs_dir_path):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        result = await manager.async_replace(
            filename, 9, PRONTO_C, "pasted", "dab"
        )
        assert not result["success"] and result["code"] == "bad_index"

    @pytest.mark.asyncio
    async def test_other_users_signed_fitting_untouched_and_stale(
        self, manager, wigs_dir_path
    ):
        wig = _signal_wig()
        signed = {
            "handle": "someone-else",
            "date": "2026-07-29",
            "content_hash": wig_content_hash(wig),
            "confirmed": ["Power On", "Power Off"],
            "failed": [],
            "sig": "pretend-signature",
            "key": "pretend-key",
        }
        wig.extra[FITTINGS_KEY] = [signed]
        filename = _write_wig(wigs_dir_path, wig)

        await manager.async_replace(filename, 0, PRONTO_C, "captured", "dab")
        await manager.async_flush()

        after = _read_wig(wigs_dir_path)
        theirs = parse_fittings(after).fittings[0]
        assert theirs.handle == "someone-else"
        assert theirs.raw["sig"] == "pretend-signature"
        assert theirs.confirmed == ["Power On", "Power Off"]
        assert not theirs.draft
        # Tamper evidence working as designed.
        assert not fitting_is_valid(theirs, after)


# ---------------------------------------------------------------------------
# Replace: matrix wigs
# ---------------------------------------------------------------------------


class TestReplaceMatrix:
    @pytest.mark.asyncio
    async def test_cell_swapped_by_checklist_key(
        self, manager, wigs_dir_path
    ):
        wig = _matrix_wig()
        filename = _write_wig(wigs_dir_path, wig, "ac.wig.json")
        index = _index_of(wig, "cool/low/22")

        result = await manager.async_replace(
            filename, index, PRONTO_D, "captured", "dab"
        )
        assert result["success"] and result["row_key"] == "cool/low/22"
        await manager.async_flush()

        after = _read_wig(wigs_dir_path, "ac.wig.json")
        cell = next(
            c for c in after.climate.cells
            if c.mode == "cool" and c.fan == "low" and c.temp == 22.0
        )
        assert cell.pronto == PRONTO_D
        assert cell.extra[PROVENANCE_KEY]["replaced"] == "captured"
        # The cell that merely shared the old code is untouched.
        other = next(
            c for c in after.climate.cells
            if c.mode == "cool" and c.fan == "auto" and c.temp == 22.0
        )
        assert other.pronto == PRONTO_B
        assert PROVENANCE_KEY not in other.extra

    @pytest.mark.asyncio
    async def test_power_specials_hit_the_matrix_block(
        self, manager, wigs_dir_path
    ):
        wig = _matrix_wig()
        filename = _write_wig(wigs_dir_path, wig, "ac.wig.json")

        await manager.async_replace(
            filename, _index_of(wig, "on"), PRONTO_D, "captured", "dab"
        )
        await manager.async_flush()
        after = _read_wig(wigs_dir_path, "ac.wig.json")
        assert after.climate.on == PRONTO_D
        power = after.climate.extra[PROVENANCE_POWER_KEY]
        assert power["on"]["replaced"] == "captured"
        assert "off" not in power

        await manager.async_replace(
            filename, _index_of(after, "off"), PRONTO_C, "pasted", "dab"
        )
        await manager.async_flush()
        final = _read_wig(wigs_dir_path, "ac.wig.json")
        assert final.climate.off == PRONTO_C
        power = final.climate.extra[PROVENANCE_POWER_KEY]
        assert power["on"]["replaced"] == "captured"
        assert power["off"]["replaced"] == "pasted"

    @pytest.mark.asyncio
    async def test_hash_rolls_on_a_cell_change(
        self, manager, wigs_dir_path
    ):
        wig = _matrix_wig()
        filename = _write_wig(wigs_dir_path, wig, "ac.wig.json")
        before = wig_content_hash(wig)
        await manager.async_replace(
            filename, _index_of(wig, "dry/auto"), PRONTO_D, "pasted", "dab"
        )
        await manager.async_flush()
        assert wig_content_hash(
            _read_wig(wigs_dir_path, "ac.wig.json")
        ) != before


# ---------------------------------------------------------------------------
# The trap: the hash rolls mid-session
# ---------------------------------------------------------------------------


class TestDraftRebind:
    @pytest.mark.asyncio
    async def test_draft_follows_the_roll_and_keeps_other_verdicts(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_mark(filename, 1, "worked", "dab")

        result = await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        assert result["success"]
        # One verdict survives: the row whose bytes did not change.
        assert result["carried"] == 1
        await manager.async_flush()

        wig = _read_wig(wigs_dir_path)
        drafts = parse_fittings(wig).fittings
        assert len(drafts) == 1
        draft = drafts[0]
        assert draft.handle == "dab" and draft.draft
        assert draft.content_hash == wig_content_hash(wig)
        assert fitting_is_valid(draft, wig)
        assert draft.confirmed == ["Power Off"]  # replaced row reset
        assert draft.failed == []

    @pytest.mark.asyncio
    async def test_next_mark_does_not_mint_a_second_draft(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_flush()

        wig = _read_wig(wigs_dir_path)
        view = parse_fittings(wig)
        assert len(view.fittings) == 1
        assert view.fittings[0].confirmed == ["Power On"]

    @pytest.mark.asyncio
    async def test_failed_verdict_on_the_replaced_row_clears_too(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_mark(filename, 0, "failed", "dab")
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        await manager.async_flush()
        draft = parse_fittings(_read_wig(wigs_dir_path)).fittings[0]
        assert draft.failed == [] and draft.confirmed == []

    @pytest.mark.asyncio
    async def test_replace_survives_a_restart_mid_session(
        self, manager, wigs_dir_path, fake_hass
    ):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_mark(filename, 1, "worked", "dab")
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        await manager.async_flush()

        reborn = FittingManager(fake_hass, monitor=None)
        await reborn.async_mark(filename, 0, "worked", "dab")
        await reborn.async_flush()
        view = parse_fittings(_read_wig(wigs_dir_path))
        assert len(view.fittings) == 1
        assert set(view.fittings[0].confirmed) == {"Power On", "Power Off"}


# ---------------------------------------------------------------------------
# Carry-forward
# ---------------------------------------------------------------------------


class TestCarryForward:
    async def _fit_and_replace(self, manager, wigs_dir_path):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_mark(filename, 1, "worked", "dab")
        await manager.async_finish(filename, "dab", None, None, None)
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        await manager.async_flush()
        return filename

    @pytest.mark.asyncio
    async def test_new_session_seeds_everything_but_the_replaced_row(
        self, manager, wigs_dir_path
    ):
        await self._fit_and_replace(manager, wigs_dir_path)
        wig = _read_wig(wigs_dir_path)
        confirmed, failed = carry_forward_seed(wig, "dab")
        assert confirmed == ["Power Off"]
        assert failed == []

    @pytest.mark.asyncio
    async def test_seed_lands_in_the_draft_on_the_first_mark(
        self, manager, wigs_dir_path
    ):
        filename = await self._fit_and_replace(manager, wigs_dir_path)
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_flush()
        wig = _read_wig(wigs_dir_path)
        draft = next(
            f for f in parse_fittings(wig).fittings if f.draft
        )
        assert set(draft.confirmed) == {"Power On", "Power Off"}
        assert fitting_is_complete(
            parse_fittings(wig).fittings[-1], wig
        ) is False  # still a draft, so not complete

    @pytest.mark.asyncio
    async def test_send_times_is_not_carried(
        self, manager, wigs_dir_path
    ):
        """It described the old session's conditions, not this one's."""
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_mark(filename, 0, "worked", "dab")
        draft = parse_fittings(
            await manager._load(filename)
        ).fittings[0]
        draft.raw["send_times_used"] = 4
        await manager.async_finish(filename, "dab", None, None, None)
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        await manager.async_mark(filename, 1, "worked", "dab")
        await manager.async_flush()
        new_draft = next(
            f for f in parse_fittings(_read_wig(wigs_dir_path)).fittings
            if f.draft
        )
        assert new_draft.send_times_used is None

    @pytest.mark.asyncio
    async def test_renamed_row_does_not_carry(
        self, manager, wigs_dir_path
    ):
        """Byte-exact or nothing: a renamed alias is a different row,
        and its old verdict never attested this one."""
        await self._fit_and_replace(manager, wigs_dir_path)
        wig = _read_wig(wigs_dir_path)
        wig.signals[1].alias = "Standby"
        _write_wig(wigs_dir_path, wig)

        confirmed, failed = carry_forward_seed(
            _read_wig(wigs_dir_path), "dab"
        )
        assert confirmed == [] and failed == []

    @pytest.mark.asyncio
    async def test_hand_edited_bytes_do_not_carry(
        self, manager, wigs_dir_path
    ):
        """The anti-laundering case the digest snapshot was CHOSEN for
        (brief 4.4): the row key survives a hand edit outside HAIR, the
        bytes do not, and a verdict must never carry onto bytes nobody
        attested. Key intact, digest mismatch, no seed."""
        filename = await self._fit_and_replace(manager, wigs_dir_path)
        wig = _read_wig(wigs_dir_path, filename)
        # A hand edit outside HAIR: same alias, foreign bytes, no
        # replace op, no provenance, no hash bookkeeping.
        untouched = next(
            s for s in wig.signals if s.alias == "Power Off"
        )
        untouched.pronto = PRONTO_D
        (wigs_dir_path / filename).write_text(
            serialize_wig(wig), encoding="utf-8"
        )
        edited = _read_wig(wigs_dir_path, filename)
        confirmed, failed = carry_forward_seed(edited, "dab")
        assert confirmed == [] and failed == []

    @pytest.mark.asyncio
    async def test_sequential_replaces_verify_against_own_snapshots(
        self, manager, wigs_dir_path
    ):
        """Two rolls, no chaining (brief 4.4): each retired hash holds
        its own complete snapshot, and a fitting bound to EITHER old
        hash verifies directly against its own entry. After replacing
        both rows in turn, the fitting from before the first roll seeds
        nothing (both rows' bytes moved), and the fitting signed
        between the rolls seeds exactly the row the second roll left
        alone."""
        filename = _write_wig(wigs_dir_path, _signal_wig())
        # Fitting 1 on the original codes.
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_mark(filename, 1, "worked", "dab")
        await manager.async_finish(filename, "dab", None, None, None)
        # Roll 1: Power On -> C. Fitting 2 signs on the new codes.
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_finish(filename, "dab", None, None, None)
        # Roll 2: Power Off -> D.
        await manager.async_replace(
            filename, 1, PRONTO_D, "captured", "dab"
        )
        await manager.async_flush()

        wig = _read_wig(wigs_dir_path, filename)
        fittings = parse_fittings(wig).fittings
        current = wig_content_hash(wig)
        stale_hashes = {
            f.content_hash for f in fittings
            if f.content_hash != current
        }
        carry = wig.extra[CARRY_KEY]
        # One snapshot per retired hash a fitting still points at,
        # each complete over the rows of its own era -- no chaining.
        assert stale_hashes <= set(carry)
        for snapshot in carry.values():
            assert set(snapshot) == {"Power On", "Power Off"}
        # The latest prior fitting (post-roll-1) seeds the row roll 2
        # left alone: Power On (proven at C, still C). Power Off moved
        # to D and must come back untested.
        confirmed, failed = carry_forward_seed(wig, "dab")
        assert confirmed == ["Power On"]
        assert failed == []

    @pytest.mark.asyncio
    async def test_no_snapshot_means_no_seeding(
        self, manager, wigs_dir_path
    ):
        """A stale-hash fitting with no carry receipt cannot prove byte
        identity, so it carries nothing rather than trusting the key."""
        wig = _signal_wig()
        wig.extra[FITTINGS_KEY] = [{
            "handle": "dab",
            "date": "2026-07-29",
            "content_hash": "sha256:from-another-era",
            "confirmed": ["Power On", "Power Off"],
            "failed": [],
        }]
        assert carry_forward_seed(wig, "dab") == ([], [])

    @pytest.mark.asyncio
    async def test_another_users_fitting_does_not_seed_mine(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_mark(filename, 0, "worked", "someone-else")
        await manager.async_finish(
            filename, "someone-else", None, None, None
        )
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "someone-else"
        )
        await manager.async_flush()
        assert carry_forward_seed(_read_wig(wigs_dir_path), "dab") == ([], [])

    @pytest.mark.asyncio
    async def test_carry_map_pruned_when_no_fitting_references_it(
        self, manager, wigs_dir_path
    ):
        """No fittings at all: nothing to carry, so nothing is kept."""
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        await manager.async_flush()
        assert CARRY_KEY not in _read_wig(wigs_dir_path).extra

    @pytest.mark.asyncio
    async def test_carry_map_kept_while_a_fitting_still_points_at_it(
        self, manager, wigs_dir_path
    ):
        await self._fit_and_replace(manager, wigs_dir_path)
        wig = _read_wig(wigs_dir_path)
        carry = wig.extra[CARRY_KEY]
        signed = parse_fittings(wig).fittings[0]
        assert list(carry) == [signed.content_hash]
        # Digests, not whole codes: a snapshot on a 288-signal wig must
        # not cost a third of a megabyte of receipts.
        assert set(carry[signed.content_hash]) == {"Power On", "Power Off"}
        assert all(
            len(v) == 16 and " " not in v
            for v in carry[signed.content_hash].values()
        )

    @pytest.mark.asyncio
    async def test_rebound_draft_does_not_keep_the_old_snapshot_alive(
        self, manager, wigs_dir_path
    ):
        """The sweep runs AFTER the re-bind. A draft that just moved to
        the new hash is not a reason to keep a snapshot of the old one,
        and keeping it would leave dead receipts on every replace."""
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_mark(filename, 1, "worked", "dab")
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        await manager.async_flush()
        assert CARRY_KEY not in _read_wig(wigs_dir_path).extra

    @pytest.mark.asyncio
    async def test_dead_snapshot_swept_on_the_next_replace(
        self, manager, wigs_dir_path
    ):
        filename = await self._fit_and_replace(manager, wigs_dir_path)
        wig = _read_wig(wigs_dir_path)
        first_hash = parse_fittings(wig).fittings[0].content_hash
        # Drop the fitting that referenced the old hash, then replace
        # again: the orphaned snapshot goes with it.
        wig.extra.pop(FITTINGS_KEY, None)
        _write_wig(wigs_dir_path, wig)
        fresh = FittingManager(manager._hass, monitor=None)
        await fresh.async_replace(filename, 1, PRONTO_D, "pasted", "dab")
        await fresh.async_flush()
        assert first_hash not in _read_wig(wigs_dir_path).extra.get(
            CARRY_KEY, {}
        )


# ---------------------------------------------------------------------------
# Discard puts the codes back
# ---------------------------------------------------------------------------


class TestDiscardReverts:
    @pytest.mark.asyncio
    async def test_discard_restores_the_original_code(
        self, manager, wigs_dir_path
    ):
        """Discard is 'none of this happened', and a replace made
        during the session is part of it."""
        filename = _write_wig(wigs_dir_path, _signal_wig())
        before = wig_content_hash(_read_wig(wigs_dir_path))
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        result = await manager.async_discard(filename, "dab")
        assert result["success"] and result["reverted"] == 1
        await manager.async_flush()

        wig = _read_wig(wigs_dir_path)
        assert wig.signals[0].pronto == PRONTO_A
        assert PROVENANCE_KEY not in wig.signals[0].extra
        assert wig_content_hash(wig) == before
        assert FITTINGS_KEY not in wig.extra
        assert CARRY_KEY not in wig.extra
        assert REPLACED_FROM_KEY not in wig.extra

    @pytest.mark.asyncio
    async def test_discard_with_no_marks_still_reverts(
        self, manager, wigs_dir_path
    ):
        """Replacing without marking anything is still a session with
        something in it to throw away."""
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_replace(
            filename, 0, PRONTO_C, "pasted", "dab"
        )
        result = await manager.async_discard(filename, "dab")
        assert result["success"] and result["reverted"] == 1
        await manager.async_flush()
        assert _read_wig(wigs_dir_path).signals[0].pronto == PRONTO_A

    @pytest.mark.asyncio
    async def test_nothing_to_discard_still_errors(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        result = await manager.async_discard(filename, "dab")
        assert not result["success"] and result["code"] == "no_draft"

    @pytest.mark.asyncio
    async def test_repeat_replaces_revert_to_the_session_original(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_replace(
            filename, 0, PRONTO_C, "pasted", "dab"
        )
        await manager.async_replace(
            filename, 0, PRONTO_D, "captured", "dab"
        )
        await manager.async_discard(filename, "dab")
        await manager.async_flush()
        assert _read_wig(wigs_dir_path).signals[0].pronto == PRONTO_A

    @pytest.mark.asyncio
    async def test_finish_commits_the_replace(
        self, manager, wigs_dir_path
    ):
        """Signing is what makes a replace permanent. A discard in a
        LATER session must not undo an attested repair."""
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        await manager.async_finish(filename, "dab", None, None, None)
        await manager.async_flush()
        # The record STAYS (owner ruling): signing closes it to
        # discard, and leaves revert available forever.
        record = _read_wig(wigs_dir_path).extra[REPLACED_FROM_KEY]
        assert record["Power On"]["session"] is False
        assert record["Power On"]["pronto"] == PRONTO_A

        await manager.async_mark(filename, 1, "worked", "dab")
        await manager.async_discard(filename, "dab")
        await manager.async_flush()
        wig = _read_wig(wigs_dir_path)
        assert wig.signals[0].pronto == PRONTO_C
        assert wig.signals[0].extra[PROVENANCE_KEY]["replaced"] == "captured"

    @pytest.mark.asyncio
    async def test_another_users_later_replace_stands(
        self, manager, wigs_dir_path
    ):
        """Reverting a row somebody else has since replaced would be
        this session quietly editing their work. The row belongs to
        whoever touched it last, so dab's discard leaves it alone and
        only throws away dab's own verdicts."""
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_mark(filename, 1, "worked", "dab")
        await manager.async_replace(
            filename, 0, PRONTO_C, "pasted", "dab"
        )
        await manager.async_replace(
            filename, 0, PRONTO_D, "captured", "someone-else"
        )
        result = await manager.async_discard(filename, "dab")
        assert result["success"] and result["reverted"] == 0
        await manager.async_flush()
        wig = _read_wig(wigs_dir_path)
        assert wig.signals[0].pronto == PRONTO_D
        assert wig.signals[0].extra[PROVENANCE_KEY]["replaced"] == "captured"
        # And the original is still on record, so the chip can still
        # take it all the way back.
        assert wig.extra[REPLACED_FROM_KEY]["Power On"]["pronto"] == PRONTO_A

    @pytest.mark.asyncio
    async def test_discard_survives_a_restart(
        self, manager, wigs_dir_path, fake_hass
    ):
        """The undo record lives in the wig file, not in memory, so an
        HA restart cannot quietly make a replace permanent."""
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        await manager.async_flush()

        reborn = FittingManager(fake_hass, monitor=None)
        result = await reborn.async_discard(filename, "dab")
        assert result["reverted"] == 1
        await reborn.async_flush()
        assert _read_wig(wigs_dir_path).signals[0].pronto == PRONTO_A

    @pytest.mark.asyncio
    async def test_matrix_revert_clears_the_changed_row(
        self, manager, wigs_dir_path
    ):
        """A reverted cell was never replaced, so it must not leave a
        Changed Codes row behind claiming it was."""
        wig = _matrix_wig()
        filename = _write_wig(wigs_dir_path, wig, "ac.wig.json")
        index = _index_of(wig, "cool/low/22")
        await manager.async_replace(
            filename, index, PRONTO_D, "captured", "dab"
        )
        await manager.async_discard(filename, "dab")
        await manager.async_flush()
        after = _read_wig(wigs_dir_path, "ac.wig.json")
        cell = next(
            c for c in after.climate.cells
            if c.mode == "cool" and c.fan == "low"
        )
        assert cell.pronto == PRONTO_B
        assert PROVENANCE_KEY not in cell.extra
        assert [s.key for s in fitting_row_specs(after)] == CHECKLIST_KEYS

    @pytest.mark.asyncio
    async def test_matrix_power_revert_clears_the_block(
        self, manager, wigs_dir_path
    ):
        wig = _matrix_wig()
        filename = _write_wig(wigs_dir_path, wig, "ac.wig.json")
        await manager.async_replace(
            filename, _index_of(wig, "on"), PRONTO_D, "captured", "dab"
        )
        await manager.async_discard(filename, "dab")
        await manager.async_flush()
        after = _read_wig(wigs_dir_path, "ac.wig.json")
        assert after.climate.on == PRONTO_B
        assert PROVENANCE_POWER_KEY not in after.climate.extra

    @pytest.mark.asyncio
    async def test_pending_count_reaches_the_dialog(
        self, fake_hass, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        _wire_fitting(fake_hass, manager)
        conn = _make_connection()
        await ws_fitting_state(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/fitting/state",
            "filename": filename,
        })
        assert conn.send_result.call_args.args[1]["pending_replaces"] == 0

        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        await manager.async_flush()
        conn = _make_connection()
        await ws_fitting_state(fake_hass, conn, {
            "id": 2, "type": "hair/wigs/fitting/state",
            "filename": filename,
        })
        assert conn.send_result.call_args.args[1]["pending_replaces"] == 1


# ---------------------------------------------------------------------------
# What travels when a wig is shared
# ---------------------------------------------------------------------------


class TestSharePaths:
    @pytest.mark.asyncio
    async def test_stripped_fitting_takes_its_carry_snapshot_with_it(
        self, manager, wigs_dir_path
    ):
        """Owner bench 2026-07-31, from a downloaded pair: reverting a
        code invalidated the fitting that attested it, the share path
        correctly stripped that fitting, and the snapshot taken FOR it
        rode along keyed to an attestation no longer in the file."""
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_mark(filename, 1, "worked", "dab")
        await manager.async_finish(filename, "dab", None, None, None)
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        await manager.async_flush()

        wig = _read_wig(wigs_dir_path)
        # On disk the snapshot is live: the stale fitting still refers
        # to the hash it was taken at.
        assert wig.extra[CARRY_KEY]
        assert len(parse_fittings(wig).fittings) == 1

        shared = parse_wig(shared_wig_text(wig)).wig
        assert FITTINGS_KEY not in shared.extra  # stale, so stripped
        assert CARRY_KEY not in shared.extra     # and so is its snapshot

    def test_share_drops_session_bookkeeping_keeps_the_way_back(self):
        wig = _signal_wig()
        wig.extra[REPLACED_FROM_KEY] = {
            "Power On": {
                "pronto": PRONTO_A,
                "provenance": None,
                "by": "dab",
                "to": PRONTO_C,
                "session": True,
            },
        }
        wig.signals[0].pronto = PRONTO_C
        wig.signals[0].extra[PROVENANCE_KEY] = {
            "replaced": "captured", "date": "2026-07-31",
        }
        assert wig_needs_share_strip(wig)

        shared = parse_wig(shared_wig_text(wig)).wig
        record = shared.extra[REPLACED_FROM_KEY]["Power On"]
        # The codes travel, so the recipient can still put it back.
        assert record["pronto"] == PRONTO_A
        assert record["to"] == PRONTO_C
        assert "Power On" in revertible_keys(shared)
        # Whose session it was does not.
        assert "by" not in record and "session" not in record
        assert pending_replaces(shared, "dab") == 0


# ---------------------------------------------------------------------------
# Revert: the chip's way back
# ---------------------------------------------------------------------------


class TestRevert:
    @pytest.mark.asyncio
    async def test_revert_restores_the_shipped_code(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        before = wig_content_hash(_read_wig(wigs_dir_path))
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        result = await manager.async_revert(filename, 0, "dab")
        assert result["success"] and result["row_key"] == "Power On"
        await manager.async_flush()

        wig = _read_wig(wigs_dir_path)
        assert wig.signals[0].pronto == PRONTO_A
        assert PROVENANCE_KEY not in wig.signals[0].extra
        assert wig_content_hash(wig) == before
        assert REPLACED_FROM_KEY not in wig.extra

    @pytest.mark.asyncio
    async def test_revert_reaches_past_several_replaces(
        self, manager, wigs_dir_path
    ):
        """Owner ruling: back to what the wig came with, not to the
        previous repair attempt."""
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_replace(filename, 0, PRONTO_C, "pasted", "dab")
        await manager.async_replace(filename, 0, PRONTO_D, "captured", "dab")
        await manager.async_revert(filename, 0, "dab")
        await manager.async_flush()
        assert _read_wig(wigs_dir_path).signals[0].pronto == PRONTO_A

    @pytest.mark.asyncio
    async def test_revert_survives_signing(
        self, manager, wigs_dir_path
    ):
        """Owner ruling 2026-07-30: a capture that was proved and later
        turned out wrong is still fixable. The signed fitting goes
        stale by hash, which is what a hash is for."""
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_finish(filename, "dab", None, None, None)
        await manager.async_flush()

        wig = _read_wig(wigs_dir_path)
        signed = parse_fittings(wig).fittings[0]
        assert not signed.draft and fitting_is_valid(signed, wig)
        assert "Power On" in revertible_keys(wig)

        reborn = FittingManager(manager._hass, monitor=None)
        assert (await reborn.async_revert(filename, 0, "dab"))["success"]
        await reborn.async_flush()
        after = _read_wig(wigs_dir_path)
        assert after.signals[0].pronto == PRONTO_A
        # The attestation covered the replaced code; it is now stale.
        assert not fitting_is_valid(
            parse_fittings(after).fittings[0], after
        )

    @pytest.mark.asyncio
    async def test_revert_refused_with_nothing_on_record(
        self, manager, wigs_dir_path
    ):
        """A marker that arrived inside a shared wig has no earlier
        code here, so there is nothing to go back to."""
        wig = _signal_wig()
        wig.signals[0].extra[PROVENANCE_KEY] = {
            "replaced": "captured", "date": "2026-07-29",
        }
        filename = _write_wig(wigs_dir_path, wig)
        result = await manager.async_revert(filename, 0, "dab")
        assert not result["success"]
        assert result["code"] == "not_revertible"
        assert revertible_keys(_read_wig(wigs_dir_path)) == set()

    @pytest.mark.asyncio
    async def test_revert_restores_an_inherited_marker(
        self, manager, wigs_dir_path
    ):
        """A wig that arrived already carrying a marker keeps it when
        a local replace is reverted: the row goes back to the state
        this install received, not to no-marker-at-all."""
        wig = _signal_wig()
        wig.signals[0].extra[PROVENANCE_KEY] = {
            "replaced": "pasted", "date": "2026-07-29",
        }
        filename = _write_wig(wigs_dir_path, wig)
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        await manager.async_revert(filename, 0, "dab")
        await manager.async_flush()
        after = _read_wig(wigs_dir_path)
        assert after.signals[0].pronto == PRONTO_A
        assert after.signals[0].extra[PROVENANCE_KEY]["replaced"] == "pasted"

    @pytest.mark.asyncio
    async def test_revert_rebinds_the_draft_and_resets_the_row(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_mark(filename, 1, "worked", "dab")
        result = await manager.async_revert(filename, 0, "dab")
        assert result["carried"] == 1
        await manager.async_flush()
        wig = _read_wig(wigs_dir_path)
        draft = parse_fittings(wig).fittings[0]
        assert draft.content_hash == wig_content_hash(wig)
        assert draft.confirmed == ["Power Off"]

    @pytest.mark.asyncio
    async def test_matrix_revert_retires_the_changed_row(
        self, manager, wigs_dir_path
    ):
        """A wig that arrives carrying a repaired off-checklist cell
        lists it under Changed Codes and can still be taken back, and
        taking it back retires the row with it.

        Note the shape this exercises: a replace made in a session can
        only ever target a row the session walks, so on a matrix wig
        phase 1's own replaces always land on checklist rows. Changed
        Codes rows come from markers that arrived with the file -- and,
        from the next release, from lint and rule repair.
        """
        wig = _matrix_wig()
        cell = next(c for c in wig.climate.cells if c.temp == 25.0)
        cell.pronto = PRONTO_D
        cell.extra[PROVENANCE_KEY] = {
            "replaced": "captured", "date": "2026-07-29",
        }
        wig.extra[REPLACED_FROM_KEY] = {
            "cool/auto/25": {
                "pronto": PRONTO_C,
                "provenance": None,
                "by": "someone-else",
                "to": PRONTO_D,
                "session": False,
            },
        }
        filename = _write_wig(wigs_dir_path, wig, "ac.wig.json")

        loaded = _read_wig(wigs_dir_path, "ac.wig.json")
        assert [s.key for s in fitting_row_specs(loaded)] == [
            *CHECKLIST_KEYS, "cool/auto/25",
        ]
        assert "cool/auto/25" in revertible_keys(loaded)

        await manager.async_revert(
            filename, _index_of(loaded, "cool/auto/25"), "dab"
        )
        await manager.async_flush()
        after = _read_wig(wigs_dir_path, "ac.wig.json")
        cell = next(c for c in after.climate.cells if c.temp == 25.0)
        assert cell.pronto == PRONTO_C
        assert PROVENANCE_KEY not in cell.extra
        assert [s.key for s in fitting_row_specs(after)] == CHECKLIST_KEYS

    @pytest.mark.asyncio
    async def test_revertible_flag_reaches_the_dialog(
        self, fake_hass, manager, wigs_dir_path
    ):
        wig = _signal_wig()
        # Row 1 arrives with a marker and no record: a chip, but no way
        # back. Row 0 gets replaced here, so it has both.
        wig.signals[1].extra[PROVENANCE_KEY] = {
            "replaced": "pasted", "date": "2026-07-29",
        }
        filename = _write_wig(wigs_dir_path, wig)
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        await manager.async_flush()
        _wire_fitting(fake_hass, manager)
        conn = _make_connection()
        await ws_fitting_state(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/fitting/state",
            "filename": filename,
        })
        rows = conn.send_result.call_args.args[1]["rows"]
        assert rows[0]["provenance"]["replaced"] == "captured"
        assert rows[0]["revertible"] is True
        assert rows[1]["provenance"]["replaced"] == "pasted"
        assert rows[1]["revertible"] is False

    @pytest.mark.asyncio
    async def test_revert_command_routes_errors(
        self, fake_hass, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        _wire_fitting(fake_hass, manager)
        conn = _make_connection()
        await ws_fitting_revert(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/fitting/revert",
            "filename": filename, "signal_index": 0,
        })
        conn.send_result.assert_not_called()
        assert conn.send_error.call_args.args[1] == "not_revertible"

    @pytest.mark.asyncio
    async def test_revert_command_succeeds(
        self, fake_hass, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        _wire_fitting(fake_hass, manager)
        conn = _make_connection()
        await ws_fitting_revert(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/fitting/revert",
            "filename": filename, "signal_index": 0,
        })
        conn.send_error.assert_not_called()
        assert conn.send_result.call_args.args[1]["success"]
        await manager.async_flush()
        assert _read_wig(wigs_dir_path).signals[0].pronto == PRONTO_A


# ---------------------------------------------------------------------------
# Changed Codes rows
# ---------------------------------------------------------------------------


class TestChangedRows:
    @pytest.mark.asyncio
    async def test_replaced_off_checklist_cell_grows_a_changed_row(
        self, manager, wigs_dir_path
    ):
        wig = _matrix_wig()
        _write_wig(wigs_dir_path, wig, "ac.wig.json")
        assert "cool/auto/25" not in CHECKLIST_KEYS

        # The cell is not a checklist row, so it has to be addressed
        # through the wig directly -- exactly what a lint-flagged or
        # user-hunted cell will do once phase 2 lands.
        loaded = _read_wig(wigs_dir_path, "ac.wig.json")
        cell = next(c for c in loaded.climate.cells if c.temp == 25.0)
        cell.pronto = PRONTO_D
        cell.extra[PROVENANCE_KEY] = {
            "replaced": "captured", "date": "2026-07-30",
        }
        _write_wig(wigs_dir_path, loaded, "ac.wig.json")

        specs = fitting_row_specs(_read_wig(wigs_dir_path, "ac.wig.json"))
        assert [s.key for s in specs] == [*CHECKLIST_KEYS, "cool/auto/25"]
        changed = specs[-1]
        assert changed.section == SECTION_CHANGED
        assert changed.provenance["replaced"] == "captured"
        assert changed.mode == "cool" and changed.temp == 25.0

    def test_changed_rows_join_completeness(self):
        wig = _matrix_wig()
        cell = next(c for c in wig.climate.cells if c.temp == 25.0)
        cell.extra[PROVENANCE_KEY] = {"replaced": "pasted", "date": "x"}
        entry = {
            "handle": "dab",
            "date": "2026-07-30",
            "content_hash": wig_content_hash(wig),
            "confirmed": list(CHECKLIST_KEYS),
            "failed": [],
        }
        wig.extra[FITTINGS_KEY] = [entry]
        fitting = parse_fittings(wig).fittings[0]
        # The checklist alone is no longer the whole job.
        assert not fitting_is_complete(fitting, wig)
        entry["confirmed"] = [*CHECKLIST_KEYS, "cool/auto/25"]
        assert fitting_is_complete(parse_fittings(wig).fittings[0], wig)

    def test_replaced_checklist_cell_stays_in_place(self):
        wig = _matrix_wig()
        cell = next(
            c for c in wig.climate.cells
            if c.mode == "cool" and c.fan == "low"
        )
        cell.extra[PROVENANCE_KEY] = {"replaced": "captured", "date": "x"}
        specs = fitting_row_specs(wig)
        assert [s.key for s in specs] == CHECKLIST_KEYS
        row = next(s for s in specs if s.key == "cool/low/22")
        assert row.section == "fan"
        assert row.provenance["replaced"] == "captured"

    def test_power_marker_rides_its_checklist_row(self):
        wig = _matrix_wig()
        wig.climate.extra[PROVENANCE_POWER_KEY] = {
            "off": {"replaced": "pasted", "date": "x"},
        }
        specs = fitting_row_specs(wig)
        assert [s.key for s in specs] == CHECKLIST_KEYS
        assert specs[-1].key == "off"
        assert specs[-1].provenance["replaced"] == "pasted"
        assert specs[0].key == "on" and specs[0].provenance is None

    @pytest.mark.asyncio
    async def test_signal_wig_grows_nothing(self, manager, wigs_dir_path):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        await manager.async_flush()
        wig = _read_wig(wigs_dir_path)
        specs = fitting_row_specs(wig)
        assert [s.key for s in specs] == ["Power On", "Power Off"]
        assert all(s.section is None for s in specs)
        assert specs[0].provenance["replaced"] == "captured"

    def test_rows_are_deterministic_across_parses(self):
        wig = _matrix_wig()
        cell = next(c for c in wig.climate.cells if c.temp == 25.0)
        cell.extra[PROVENANCE_KEY] = {"replaced": "captured", "date": "x"}
        text = serialize_wig(wig)
        first = parse_wig(text).wig
        second = parse_wig(serialize_wig(parse_wig(text).wig)).wig
        assert [s.key for s in fitting_row_specs(first)] == \
            [s.key for s in fitting_row_specs(second)]
        assert fitting_rows(first) == fitting_rows(second)


# ---------------------------------------------------------------------------
# Round trip: receipts ride outside every hash
# ---------------------------------------------------------------------------


class TestReceiptsRoundTrip:
    def test_markers_and_carry_survive_serialize_parse(self):
        wig = _signal_wig()
        wig.signals[0].extra[PROVENANCE_KEY] = {
            "replaced": "captured", "date": "2026-07-30",
        }
        wig.extra[CARRY_KEY] = {"sha256:old": {"Power On": "abc123"}}
        back = parse_wig(serialize_wig(wig)).wig
        assert back.signals[0].extra[PROVENANCE_KEY]["replaced"] == "captured"
        assert back.extra[CARRY_KEY] == {"sha256:old": {"Power On": "abc123"}}

    def test_matrix_markers_survive_serialize_parse(self):
        wig = _matrix_wig()
        wig.climate.cells[0].extra[PROVENANCE_KEY] = {
            "replaced": "pasted", "date": "2026-07-30",
        }
        wig.climate.extra[PROVENANCE_POWER_KEY] = {
            "on": {"replaced": "captured", "date": "2026-07-30"},
        }
        back = parse_wig(serialize_wig(wig)).wig
        assert back.climate.cells[0].extra[PROVENANCE_KEY]["replaced"] \
            == "pasted"
        assert back.climate.extra[PROVENANCE_POWER_KEY]["on"]["replaced"] \
            == "captured"

    def test_signal_canonical_form_ignores_markers(self):
        plain = _signal_wig()
        marked = _signal_wig()
        marked.signals[0].extra[PROVENANCE_KEY] = {
            "replaced": "captured", "date": "2026-07-30",
        }
        marked.extra[CARRY_KEY] = {"sha256:old": {"Power On": "abc123"}}
        assert canonical_signals_json(marked.signals) == \
            canonical_signals_json(plain.signals)
        assert wig_content_hash(marked) == wig_content_hash(plain)

    def test_cells_canonical_form_ignores_markers(self):
        plain = _matrix_wig()
        marked = _matrix_wig()
        marked.climate.cells[0].extra[PROVENANCE_KEY] = {
            "replaced": "captured", "date": "2026-07-30",
        }
        marked.climate.extra[PROVENANCE_POWER_KEY] = {
            "off": {"replaced": "pasted", "date": "2026-07-30"},
        }
        assert canonical_cells_json(marked.climate) == \
            canonical_cells_json(plain.climate)
        assert wig_content_hash(marked) == wig_content_hash(plain)


# ---------------------------------------------------------------------------
# The WS surface
# ---------------------------------------------------------------------------


def _make_connection(username="dab"):
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    conn.send_event = MagicMock()
    conn.subscriptions = {}
    conn.user.name = username
    return conn


def _wire_fitting(fake_hass, manager, **extra):
    fake_hass.data[DOMAIN] = {"entry-1": {
        "device_manager": MagicMock(),
        "fitting_manager": manager,
        **extra,
    }}


class TestReplaceWebSocket:
    @pytest.mark.asyncio
    async def test_replace_command_writes_and_reports_the_new_hash(
        self, fake_hass, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        _wire_fitting(fake_hass, manager)
        conn = _make_connection()
        await ws_fitting_replace(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/fitting/replace",
            "filename": filename, "signal_index": 0,
            "pronto": PRONTO_C, "source": "captured",
        })
        conn.send_error.assert_not_called()
        payload = conn.send_result.call_args.args[1]
        assert payload["success"] and payload["row_key"] == "Power On"
        await manager.async_flush()
        assert payload["content_hash"] == wig_content_hash(
            _read_wig(wigs_dir_path)
        )

    @pytest.mark.asyncio
    async def test_replace_errors_route_through_the_fitting_shape(
        self, fake_hass, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        _wire_fitting(fake_hass, manager)
        conn = _make_connection()
        await ws_fitting_replace(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/fitting/replace",
            "filename": filename, "signal_index": 0,
            "pronto": "zzzz", "source": "pasted",
        })
        conn.send_result.assert_not_called()
        assert conn.send_error.call_args.args[1] == "bad_pronto"


class TestFittingStatePayload:
    @pytest.mark.asyncio
    async def test_changed_rows_and_provenance_reach_the_dialog(
        self, fake_hass, manager, wigs_dir_path
    ):
        wig = _matrix_wig()
        cell = next(c for c in wig.climate.cells if c.temp == 25.0)
        cell.extra[PROVENANCE_KEY] = {
            "replaced": "captured", "date": "2026-07-30",
        }
        filename = _write_wig(wigs_dir_path, wig, "ac.wig.json")
        _wire_fitting(fake_hass, manager)
        conn = _make_connection()
        await ws_fitting_state(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/fitting/state",
            "filename": filename,
        })
        payload = conn.send_result.call_args.args[1]
        # The payload's rows and the send/mark index are ONE list.
        assert payload["signals"] == [
            key for key, _, _ in fitting_rows(
                _read_wig(wigs_dir_path, "ac.wig.json")
            )
        ]
        changed = payload["rows"][-1]
        assert changed["key"] == "cool/auto/25"
        assert changed["section"] == SECTION_CHANGED
        assert changed["provenance"]["replaced"] == "captured"
        assert changed["mode"] == "cool" and changed["temp"] == 25.0

    @pytest.mark.asyncio
    async def test_signal_wig_payload_keeps_its_shape(
        self, fake_hass, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path, _signal_wig())
        _wire_fitting(fake_hass, manager)
        conn = _make_connection()
        await ws_fitting_state(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/fitting/state",
            "filename": filename,
        })
        payload = conn.send_result.call_args.args[1]
        assert payload["signals"] == ["Power On", "Power Off"]
        assert [(r["key"], r["section"]) for r in payload["rows"]] == [
            ("Power On", None), ("Power Off", None),
        ]
        assert all(r["provenance"] is None for r in payload["rows"])
        assert payload["carried"] is False
        # Signal rows stay minimal: no matrix display facts.
        assert "temp_role" not in payload["rows"][0]

    @pytest.mark.asyncio
    async def test_carry_preview_shown_before_the_first_mark(
        self, fake_hass, manager, wigs_dir_path
    ):
        """Opening a session after a replace must not look wiped and
        then conjure verdicts out of the first tap."""
        filename = _write_wig(wigs_dir_path, _signal_wig())
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_mark(filename, 1, "worked", "dab")
        await manager.async_finish(filename, "dab", None, None, None)
        await manager.async_replace(
            filename, 0, PRONTO_C, "captured", "dab"
        )
        await manager.async_flush()

        _wire_fitting(fake_hass, manager)
        conn = _make_connection()
        await ws_fitting_state(fake_hass, conn, {
            "id": 1, "type": "hair/wigs/fitting/state",
            "filename": filename,
        })
        payload = conn.send_result.call_args.args[1]
        assert payload["carried"] is True
        assert payload["draft"] is None
        by_key = {r["key"]: r for r in payload["rows"]}
        assert by_key["Power Off"]["confirmed"] is True
        assert by_key["Power On"]["confirmed"] is False


class _FakeSubscribeMonitor:
    def __init__(self) -> None:
        self.subscribers: list = []

    def subscribe(self, cb) -> None:
        self.subscribers.append(cb)

    def unsubscribe(self, cb) -> None:
        if cb in self.subscribers:
            self.subscribers.remove(cb)

    def emit(self, summary) -> None:
        for cb in list(self.subscribers):
            cb(summary)


def _fake_store(signal=None, device_fp="dev-1"):
    store = MagicMock()
    device = MagicMock()
    device.fingerprint = device_fp
    device.get_signal_by_id = MagicMock(return_value=signal)
    store.get_device = MagicMock(return_value=device)
    return store


def _capture(code=PRONTO_C, protocol="PRONTO", decoded_fp="NEC:0x1:0x2"):
    signal = MagicMock()
    signal.code = code
    signal.protocol = protocol
    signal.decoded_fingerprint = decoded_fp
    signal.decoded_protocol = "NEC"
    signal.heard_by = ["infrared.living_room"]
    return signal


def _summary(device_fp="dev-1"):
    return {
        "device_id": "dev-1",
        "device_fingerprint": device_fp,
        "signal_id": "sig-1",
        "protocol": "PRONTO",
        "code": PRONTO_C,
    }


class TestListen:
    def _arm(self, fake_hass, manager, monitor, store):
        _wire_fitting(
            fake_hass, manager,
            signal_monitor=monitor, signal_store=store,
        )
        conn = _make_connection()
        ws_fitting_listen(fake_hass, conn, {
            "id": 7, "type": "hair/wigs/fitting/listen",
        })
        return conn

    def test_first_capture_resolves_the_window_once(
        self, fake_hass, manager
    ):
        monitor = _FakeSubscribeMonitor()
        conn = self._arm(
            fake_hass, manager, monitor, _fake_store(_capture())
        )
        assert conn.send_result.call_args.args[1] == {"listening": True}

        monitor.emit(_summary())
        event = conn.send_event.call_args.args[1]
        assert event["type"] == "fitting_capture"
        assert event["pronto"] == PRONTO_C
        assert event["decoded"] is True
        assert event["receiver"] == "infrared.living_room"

        # One shot: a second press after the window closed is ignored,
        # and the subscription is gone.
        monitor.emit(_summary())
        assert conn.send_event.call_count == 1
        assert monitor.subscribers == []
        assert 7 not in conn.subscriptions

    def test_mirror_rows_never_resolve_it(self, fake_hass, manager):
        """The subscriber feed carries HAIR's OWN sends. Without this
        filter, pressing SEND on the row being replaced would drop
        HAIR's transmission into the box as the remote's press."""
        monitor = _FakeSubscribeMonitor()
        conn = self._arm(
            fake_hass, manager, monitor,
            _fake_store(_capture(), device_fp=MIRROR_DEVICE_FP),
        )
        monitor.emit(_summary(device_fp=MIRROR_DEVICE_FP))
        conn.send_event.assert_not_called()
        assert monitor.subscribers  # still listening

    def test_non_pronto_capture_keeps_listening(
        self, fake_hass, manager
    ):
        """Raw timings that would not encode: nothing to put in the box,
        so the window stays open instead of closing on nothing."""
        monitor = _FakeSubscribeMonitor()
        conn = self._arm(
            fake_hass, manager, monitor,
            _fake_store(_capture(code=None, protocol=None)),
        )
        monitor.emit(_summary())
        conn.send_event.assert_not_called()
        assert monitor.subscribers

    def test_undecoded_capture_still_lands_in_the_box(
        self, fake_hass, manager
    ):
        """Warn-and-allow: a rough capture is the user's call."""
        monitor = _FakeSubscribeMonitor()
        conn = self._arm(
            fake_hass, manager, monitor,
            _fake_store(_capture(decoded_fp=None)),
        )
        monitor.emit(_summary())
        event = conn.send_event.call_args.args[1]
        assert event["type"] == "fitting_capture"
        assert event["decoded"] is False

    def test_timeout_closes_the_window(self, fake_hass, manager):
        monitor = _FakeSubscribeMonitor()
        conn = self._arm(
            fake_hass, manager, monitor, _fake_store(_capture())
        )
        # The scheduled callback, as hass.loop.call_later received it.
        _delay, on_timeout = fake_hass.loop.call_later.call_args.args
        on_timeout()
        assert conn.send_event.call_args.args[1] == {
            "type": "fitting_listen_timeout",
        }
        assert monitor.subscribers == []

        monitor.emit(_summary())
        assert conn.send_event.call_count == 1

    def test_cancel_unsubscribes(self, fake_hass, manager):
        monitor = _FakeSubscribeMonitor()
        conn = self._arm(
            fake_hass, manager, monitor, _fake_store(_capture())
        )
        assert 7 in conn.subscriptions
        conn.subscriptions[7]()
        assert monitor.subscribers == []
        monitor.emit(_summary())
        conn.send_event.assert_not_called()
