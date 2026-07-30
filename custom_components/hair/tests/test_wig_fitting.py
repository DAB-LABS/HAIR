"""Tests for the fitting layer (Perfect Fit).

Covers the pure format layer (parse / completeness / hash validity /
share stripping / summary) and the FittingManager session behavior:
marks write through to the wig file (debounce flushed explicitly),
survive a "restart" (a fresh manager reading the same file), finish
signs the draft, discard removes only the draft.
"""
from __future__ import annotations

import json

import pytest

from custom_components.hair.wig_fitting import (
    FITTINGS_KEY,
    FittingManager,
    fitting_is_complete,
    fitting_is_valid,
    fitting_summary,
    parse_fittings,
    shared_wig_text,
    wig_needs_share_strip,
)
from custom_components.hair.wig_format import (
    Wig,
    WigSignal,
    parse_wig,
    serialize_wig,
    signals_content_hash,
)

PRONTO = "0000 006D 0002 0000 0020 0040 0020 0040"
PRONTO_B = "0000 006D 0002 0000 0040 0020 0040 0020"


def _wig(fittings=None) -> Wig:
    extra = {}
    if fittings is not None:
        extra[FITTINGS_KEY] = fittings
    return Wig(
        name="Test Remote",
        signals=[
            WigSignal(alias="Power On", pronto=PRONTO),
            WigSignal(alias="Power Off", pronto=PRONTO_B),
        ],
        extra=extra,
    )


def _complete_fitting(wig: Wig, **overrides) -> dict:
    entry = {
        "handle": "tester",
        "date": "2026-07-20",
        "content_hash": signals_content_hash(wig.signals),
        "confirmed": ["Power On", "Power Off"],
        "failed": [],
    }
    entry.update(overrides)
    return entry


# ---------------------------------------------------------------------------
# Pure layer
# ---------------------------------------------------------------------------


class TestParseFittings:
    def test_no_fittings_key(self):
        view = parse_fittings(_wig())
        assert view.fittings == [] and view.warnings == []

    def test_valid_entry_parses(self):
        wig = _wig([_complete_fitting(_wig())])
        view = parse_fittings(wig)
        assert len(view.fittings) == 1
        f = view.fittings[0]
        assert f.handle == "tester"
        assert f.confirmed == ["Power On", "Power Off"]
        assert not f.draft

    def test_malformed_entries_warn_not_fatal(self):
        wig = _wig([
            "not a dict",
            {"handle": 42, "content_hash": "sha256:x"},
            {"handle": "ok"},  # missing content_hash
            {"handle": "ok", "content_hash": "sha256:x",
             "confirmed": [1, 2]},  # non-str list
            _complete_fitting(_wig()),
        ])
        view = parse_fittings(wig)
        assert len(view.fittings) == 1
        assert len(view.warnings) == 4

    def test_non_list_block_warns(self):
        wig = _wig()
        wig.extra[FITTINGS_KEY] = {"weird": True}
        view = parse_fittings(wig)
        assert view.fittings == []
        assert view.warnings

    def test_wig_parse_preserves_fittings_roundtrip(self):
        """The unknown-key contract carries fittings through an edit."""
        wig = _wig([_complete_fitting(_wig())])
        text = serialize_wig(wig)
        result = parse_wig(text)
        assert result.ok
        assert FITTINGS_KEY in result.wig.extra
        again = serialize_wig(result.wig)
        assert json.loads(again)[FITTINGS_KEY] == wig.extra[FITTINGS_KEY]


class TestCompletenessAndValidity:
    def test_complete(self):
        wig = _wig()
        f = parse_fittings(_wig([_complete_fitting(wig)])).fittings[0]
        assert fitting_is_complete(f, wig)
        assert fitting_is_valid(f, wig)

    def test_draft_never_complete_even_with_full_coverage(self):
        wig = _wig()
        f = parse_fittings(
            _wig([_complete_fitting(wig, draft=True)])
        ).fittings[0]
        assert not fitting_is_complete(f, wig)

    def test_failed_signal_never_complete(self):
        wig = _wig()
        f = parse_fittings(
            _wig([_complete_fitting(wig, failed=["Power Off"])])
        ).fittings[0]
        assert not fitting_is_complete(f, wig)

    def test_partial_coverage_not_complete(self):
        wig = _wig()
        f = parse_fittings(
            _wig([_complete_fitting(wig, confirmed=["Power On"])])
        ).fittings[0]
        assert not fitting_is_complete(f, wig)

    def test_alias_rename_breaks_hash(self):
        """Alias is inside the canonical form, so renames invalidate."""
        wig = _wig()
        f = parse_fittings(_wig([_complete_fitting(wig)])).fittings[0]
        wig.signals[0].alias = "Renamed"
        assert not fitting_is_valid(f, wig)


class TestShareStripping:
    def test_no_fittings_needs_no_strip(self):
        assert not wig_needs_share_strip(_wig())

    def test_complete_valid_fitting_survives_verbatim(self):
        wig = _wig([_complete_fitting(_wig())])
        assert not wig_needs_share_strip(wig)

    def test_draft_is_stripped(self):
        wig = _wig([_complete_fitting(_wig(), draft=True)])
        assert wig_needs_share_strip(wig)
        shared = json.loads(shared_wig_text(wig))
        assert FITTINGS_KEY not in shared

    def test_partial_is_stripped_complete_kept(self):
        base = _wig()
        wig = _wig([
            _complete_fitting(base),
            _complete_fitting(base, handle="other",
                              confirmed=["Power On"]),
        ])
        assert wig_needs_share_strip(wig)
        shared = json.loads(shared_wig_text(wig))
        assert len(shared[FITTINGS_KEY]) == 1
        assert shared[FITTINGS_KEY][0]["handle"] == "tester"

    def test_hash_invalid_fitting_is_stripped(self):
        wig = _wig([_complete_fitting(_wig(),
                                      content_hash="sha256:stale")])
        assert wig_needs_share_strip(wig)
        shared = json.loads(shared_wig_text(wig))
        assert FITTINGS_KEY not in shared

    def test_unparseable_entry_stripped_on_share(self):
        wig = _wig([_complete_fitting(_wig()), "mystery"])
        assert wig_needs_share_strip(wig)
        shared = json.loads(shared_wig_text(wig))
        assert shared[FITTINGS_KEY] == [wig.extra[FITTINGS_KEY][0]]

    def test_share_strip_leaves_wig_object_usable(self):
        wig = _wig([_complete_fitting(_wig(), draft=True)])
        shared_wig_text(wig)
        # On-disk representation unaffected: the draft is still there.
        assert wig.extra[FITTINGS_KEY]


class TestFittingSummary:
    def test_unfitted(self):
        s = fitting_summary(_wig(), "me")
        assert s["state"] is None and s["user_state"] is None
        assert s["total"] == 2

    def test_perfect_by_other(self):
        wig = _wig([_complete_fitting(_wig())])
        s = fitting_summary(wig, "me")
        assert s["state"] == "perfect"
        assert s["user_state"] is None
        assert s["others_complete"] == 1

    def test_user_draft_partial(self):
        wig = _wig([_complete_fitting(
            _wig(), handle="me", draft=True, confirmed=["Power On"],
        )])
        s = fitting_summary(wig, "me")
        assert s["state"] == "partial"
        assert s["user_state"] == "partial"
        assert s["user_draft"] is True
        assert s["confirmed"] == 1 and s["failed"] == 0

    def test_invalid_hash_excluded(self):
        wig = _wig([_complete_fitting(_wig(),
                                      content_hash="sha256:stale")])
        s = fitting_summary(wig, "me")
        assert s["state"] is None

    def test_failed_counts_surface(self):
        wig = _wig([_complete_fitting(
            _wig(), handle="me",
            confirmed=["Power On"], failed=["Power Off"],
        )])
        s = fitting_summary(wig, "me")
        assert s["failed"] == 1
        assert s["state"] == "partial"


# ---------------------------------------------------------------------------
# The manager: file-backed sessions
# ---------------------------------------------------------------------------


@pytest.fixture
def wigs_dir_path(tmp_path):
    d = tmp_path / "hair" / "wigs"
    d.mkdir(parents=True)
    return d


@pytest.fixture
def manager(fake_hass, tmp_path):
    fake_hass.config.config_dir = str(tmp_path)
    return FittingManager(fake_hass, monitor=None)


def _write_wig(wigs_dir_path, filename="test-remote.wig.json"):
    text = serialize_wig(_wig())
    (wigs_dir_path / filename).write_text(text, encoding="utf-8")
    return filename


def _read_wig(wigs_dir_path, filename="test-remote.wig.json"):
    result = parse_wig(
        (wigs_dir_path / filename).read_text(encoding="utf-8")
    )
    assert result.ok
    return result.wig


class TestManagerMarks:
    @pytest.mark.asyncio
    async def test_first_mark_creates_draft_in_file(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path)
        result = await manager.async_mark(filename, 0, "worked", "dab")
        assert result["success"]
        assert result["confirmed"] == 1
        await manager.async_flush()
        wig = _read_wig(wigs_dir_path)
        view = parse_fittings(wig)
        assert len(view.fittings) == 1
        draft = view.fittings[0]
        assert draft.draft and draft.handle == "dab"
        assert draft.confirmed == ["Power On"]
        assert fitting_is_valid(draft, wig)

    @pytest.mark.asyncio
    async def test_marks_survive_restart(self, manager, wigs_dir_path,
                                         fake_hass):
        """Owner ruling 2026-07-26: partials survive reboots."""
        filename = _write_wig(wigs_dir_path)
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_mark(filename, 1, "failed", "dab")
        await manager.async_flush()

        reborn = FittingManager(fake_hass, monitor=None)
        result = await reborn.async_mark(filename, 1, "worked", "dab")
        assert result["success"]
        await reborn.async_flush()
        wig = _read_wig(wigs_dir_path)
        view = parse_fittings(wig)
        assert len(view.fittings) == 1  # merged into the SAME draft
        assert set(view.fittings[0].confirmed) == {"Power On", "Power Off"}
        assert view.fittings[0].failed == []

    @pytest.mark.asyncio
    async def test_untested_clears_verdict(self, manager, wigs_dir_path):
        filename = _write_wig(wigs_dir_path)
        await manager.async_mark(filename, 0, "worked", "dab")
        result = await manager.async_mark(filename, 0, "untested", "dab")
        assert result["confirmed"] == 0 and result["failed"] == 0

    @pytest.mark.asyncio
    async def test_verdict_flip(self, manager, wigs_dir_path):
        filename = _write_wig(wigs_dir_path)
        await manager.async_mark(filename, 0, "worked", "dab")
        result = await manager.async_mark(filename, 0, "failed", "dab")
        assert result["confirmed"] == 0 and result["failed"] == 1

    @pytest.mark.asyncio
    async def test_perfect_ready_flag(self, manager, wigs_dir_path):
        filename = _write_wig(wigs_dir_path)
        r1 = await manager.async_mark(filename, 0, "worked", "dab")
        assert not r1["perfect_ready"]
        r2 = await manager.async_mark(filename, 1, "worked", "dab")
        assert r2["perfect_ready"]

    @pytest.mark.asyncio
    async def test_two_users_hold_independent_drafts(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path)
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_mark(filename, 1, "worked", "guest")
        await manager.async_flush()
        view = parse_fittings(_read_wig(wigs_dir_path))
        assert {f.handle for f in view.fittings} == {"dab", "guest"}

    @pytest.mark.asyncio
    async def test_bad_index_and_missing_wig(self, manager, wigs_dir_path):
        filename = _write_wig(wigs_dir_path)
        bad = await manager.async_mark(filename, 99, "worked", "dab")
        assert not bad["success"] and bad["code"] == "bad_index"
        missing = await manager.async_mark(
            "nope.wig.json", 0, "worked", "dab"
        )
        assert not missing["success"] and missing["code"] == "wig_not_found"


class TestManagerFinish:
    @pytest.mark.asyncio
    async def test_finish_signs_and_derives_perfect(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path)
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_mark(filename, 1, "worked", "dab")
        result = await manager.async_finish(
            filename, "dab", "DAB", "DAB-LABS", "bench verified"
        )
        assert result["success"]
        assert result["state"] == "perfect"
        wig = _read_wig(wigs_dir_path)
        f = parse_fittings(wig).fittings[0]
        assert not f.draft
        assert f.handle == "DAB"
        assert f.raw["github"] == "DAB-LABS"
        assert f.raw["note"] == "bench verified"
        assert fitting_is_complete(f, wig)

    @pytest.mark.asyncio
    async def test_finish_partial_derives_partial(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path)
        await manager.async_mark(filename, 0, "worked", "dab")
        result = await manager.async_finish(
            filename, "dab", None, None, None
        )
        assert result["state"] == "partial"
        f = parse_fittings(_read_wig(wigs_dir_path)).fittings[0]
        assert not f.draft and f.handle == "dab"

    @pytest.mark.asyncio
    async def test_finish_with_failure_is_partial(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path)
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_mark(filename, 1, "failed", "dab")
        result = await manager.async_finish(
            filename, "dab", None, None, None
        )
        assert result["state"] == "partial"
        assert result["failed"] == 1

    @pytest.mark.asyncio
    async def test_finish_without_draft_refuses(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path)
        result = await manager.async_finish(
            filename, "dab", None, None, None
        )
        assert not result["success"] and result["code"] == "no_draft"

    @pytest.mark.asyncio
    async def test_resume_after_finish_grows_same_fitting_not_new_row(
        self, manager, wigs_dir_path
    ):
        """Plan 5.1.4: forty signals today, two tomorrow = ONE fitting
        that grew. A mark after finish re-opens the user's signed
        fitting on the same hash as a draft; finish re-signs it."""
        filename = _write_wig(wigs_dir_path)
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_finish(filename, "dab", None, None, None)
        # Resume: new mark under the same username.
        await manager.async_mark(filename, 1, "worked", "dab")
        result = await manager.async_finish(
            filename, "dab", None, None, None
        )
        assert result["success"]
        wig = _read_wig(wigs_dir_path)
        fittings = parse_fittings(wig).fittings
        assert len(fittings) == 1  # one grown fitting, not two rows
        assert set(fittings[0].confirmed) == {"Power On", "Power Off"}


class TestManagerDiscard:
    @pytest.mark.asyncio
    async def test_discard_removes_draft_only(self, manager, wigs_dir_path):
        filename = _write_wig(wigs_dir_path)
        # A previously signed fitting from someone else.
        wig = _read_wig(wigs_dir_path)
        wig.extra[FITTINGS_KEY] = [
            _complete_fitting(wig, handle="other")
        ]
        (wigs_dir_path / filename).write_text(
            serialize_wig(wig), encoding="utf-8"
        )
        await manager.async_mark(filename, 0, "worked", "dab")
        result = await manager.async_discard(filename, "dab")
        assert result["success"]
        fittings = parse_fittings(_read_wig(wigs_dir_path)).fittings
        assert len(fittings) == 1
        assert fittings[0].handle == "other" and not fittings[0].draft

    @pytest.mark.asyncio
    async def test_discard_without_draft_refuses(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path)
        result = await manager.async_discard(filename, "dab")
        assert not result["success"] and result["code"] == "no_draft"

    @pytest.mark.asyncio
    async def test_discard_drops_empty_fittings_key(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path)
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_discard(filename, "dab")
        wig = _read_wig(wigs_dir_path)
        assert FITTINGS_KEY not in wig.extra


class TestManagerFlush:
    @pytest.mark.asyncio
    async def test_flush_refuses_to_resurrect_deleted_file(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path)
        await manager.async_mark(filename, 0, "worked", "dab")
        (wigs_dir_path / filename).unlink()
        await manager.async_flush()
        assert not (wigs_dir_path / filename).exists()

    @pytest.mark.asyncio
    async def test_shutdown_flushes_everything(
        self, manager, wigs_dir_path
    ):
        filename = _write_wig(wigs_dir_path)
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_shutdown()
        assert parse_fittings(_read_wig(wigs_dir_path)).fittings


# ---------------------------------------------------------------------------
# The send path
# ---------------------------------------------------------------------------


class _FakeMonitor:
    """Captures record_send; optionally resolves the heard future."""

    def __init__(self, hear_as: str | None = None, hear: bool = False):
        self.calls = []
        self._hear = hear
        self._hear_as = hear_as

    def record_send(self, command, source_label, emitter_entity_ids,
                    decoded_fingerprint=None, heard_future=None):
        self.calls.append({
            "label": source_label,
            "emitters": emitter_entity_ids,
            "decoded_fingerprint": decoded_fingerprint,
        })
        if self._hear and heard_future is not None:
            heard_future.set_result(self._hear_as)


@pytest.fixture
def _fast_heard_wait(monkeypatch):
    from custom_components.hair import wig_fitting

    monkeypatch.setattr(wig_fitting, "FITTING_HEARD_WAIT_S", 0.01)


class TestManagerSend:
    @pytest.mark.asyncio
    async def test_send_success_unheard(
        self, fake_hass, tmp_path, wigs_dir_path, _fast_heard_wait
    ):
        fake_hass.config.config_dir = str(tmp_path)
        fake_hass.states.get = lambda eid: object()
        monitor = _FakeMonitor(hear=False)
        manager = FittingManager(fake_hass, monitor)
        filename = _write_wig(wigs_dir_path)
        result = await manager.async_send(
            filename, 0, "infrared.test_emitter"
        )
        assert result["success"]
        assert result["heard"] is False
        assert monitor.calls[0]["label"] == "Fitting send: Power On"
        assert monitor.calls[0]["emitters"] == ["infrared.test_emitter"]

    @pytest.mark.asyncio
    async def test_send_heard_records_alias(
        self, fake_hass, tmp_path, wigs_dir_path, _fast_heard_wait
    ):
        fake_hass.config.config_dir = str(tmp_path)
        fake_hass.states.get = lambda eid: object()
        monitor = _FakeMonitor(hear=True, hear_as="infrared.rx")
        manager = FittingManager(fake_hass, monitor)
        filename = _write_wig(wigs_dir_path)
        result = await manager.async_send(
            filename, 0, "infrared.test_emitter"
        )
        assert result["success"] and result["heard"] is True
        # The heard alias flows into the next mark's draft evidence.
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_flush()
        f = parse_fittings(_read_wig(wigs_dir_path)).fittings[0]
        assert f.raw.get("heard") == ["Power On"]

    @pytest.mark.asyncio
    async def test_heard_evidence_collapses_to_count_on_finish(
        self, fake_hass, tmp_path, wigs_dir_path, _fast_heard_wait
    ):
        fake_hass.config.config_dir = str(tmp_path)
        fake_hass.states.get = lambda eid: object()
        monitor = _FakeMonitor(hear=True, hear_as=None)
        manager = FittingManager(fake_hass, monitor)
        filename = _write_wig(wigs_dir_path)
        await manager.async_send(filename, 0, "infrared.test_emitter")
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_finish(filename, "dab", None, None, None)
        f = parse_fittings(_read_wig(wigs_dir_path)).fittings[0]
        assert "heard" not in f.raw
        assert f.raw["signals_heard"] == 1

    @pytest.mark.asyncio
    async def test_send_unknown_emitter_refuses(
        self, fake_hass, tmp_path, wigs_dir_path
    ):
        fake_hass.config.config_dir = str(tmp_path)
        fake_hass.states.get = lambda eid: None
        manager = FittingManager(fake_hass, _FakeMonitor())
        filename = _write_wig(wigs_dir_path)
        result = await manager.async_send(filename, 0, "infrared.nope")
        assert not result["success"]
        assert result["code"] == "entity_not_found"

    @pytest.mark.asyncio
    async def test_send_bad_index_refuses(
        self, fake_hass, tmp_path, wigs_dir_path
    ):
        fake_hass.config.config_dir = str(tmp_path)
        fake_hass.states.get = lambda eid: object()
        manager = FittingManager(fake_hass, _FakeMonitor())
        filename = _write_wig(wigs_dir_path)
        result = await manager.async_send(filename, 7, "infrared.e")
        assert not result["success"] and result["code"] == "bad_index"


class TestGithubNormalization:
    @pytest.mark.asyncio
    async def test_leading_at_stripped(self, manager, wigs_dir_path):
        filename = _write_wig(wigs_dir_path)
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_finish(
            filename, "dab", None, "@DAB-LABS", None
        )
        f = parse_fittings(_read_wig(wigs_dir_path)).fittings[0]
        assert f.raw["github"] == "DAB-LABS"


# ---------------------------------------------------------------------------
# Send times (fine-tuned-fittings, v0.9.0)
# ---------------------------------------------------------------------------

from unittest.mock import AsyncMock, patch  # noqa: E402

from custom_components.hair.wig_fitting import (  # noqa: E402
    _read_send_times,
    fitting_send_times_max,
)


class TestReadSendTimes:
    """The one parse point: absent is not 1, garbage is not a claim."""

    def test_absent_is_none(self):
        assert _read_send_times({}) is None

    def test_explicit_none_is_none(self):
        assert _read_send_times({"send_times_used": None}) is None

    def test_string_is_none(self):
        assert _read_send_times({"send_times_used": "3"}) is None

    def test_bool_is_none(self):
        # bool subclasses int; True must not read as 1.
        assert _read_send_times({"send_times_used": True}) is None

    def test_clamped_low(self):
        assert _read_send_times({"send_times_used": 0}) == 1
        assert _read_send_times({"send_times_used": -1}) == 1

    def test_clamped_high(self):
        # A signature makes a value tamper-evident, not sane: a typo
        # of 1000 must never become a minute-long press.
        assert _read_send_times({"send_times_used": 1000}) == 10

    def test_plain_value(self):
        assert _read_send_times({"send_times_used": 3}) == 3


class TestSendTimesMax:
    """The single aggregation point: max, complete + current-hash only."""

    def test_empty_wig_returns_one(self):
        assert fitting_send_times_max(_wig()) == 1

    def test_max_across_fittings(self):
        base = _wig()
        wig = _wig([
            _complete_fitting(base),  # absent: contributes nothing
            _complete_fitting(base, handle="b", send_times_used=3),
            _complete_fitting(base, handle="c", send_times_used=2),
        ])
        assert fitting_send_times_max(wig) == 3

    def test_absent_never_coerced(self):
        wig = _wig([_complete_fitting(_wig())])
        assert fitting_send_times_max(wig) == 1

    def test_draft_excluded(self):
        wig = _wig([
            _complete_fitting(_wig(), draft=True, send_times_used=5),
        ])
        assert fitting_send_times_max(wig) == 1

    def test_stale_hash_excluded(self):
        # A fitting on old codes describes a different wig.
        wig = _wig([
            _complete_fitting(
                _wig(), content_hash="sha256:stale", send_times_used=7,
            ),
        ])
        assert fitting_send_times_max(wig) == 1

    def test_incomplete_excluded(self):
        wig = _wig([
            _complete_fitting(
                _wig(), confirmed=["Power On"], failed=["Power Off"],
                send_times_used=4,
            ),
        ])
        assert fitting_send_times_max(wig) == 1

    def test_unsigned_complete_counts(self):
        # Design 5.0: a measurement, not a vote. No sig required.
        wig = _wig([
            _complete_fitting(_wig(), send_times_used=3),
        ])
        assert "sig" not in wig.extra[FITTINGS_KEY][0]
        assert fitting_send_times_max(wig) == 3

    def test_garbage_value_ignored(self):
        wig = _wig([
            _complete_fitting(_wig(), send_times_used="lots"),
        ])
        assert fitting_send_times_max(wig) == 1


def _sending_manager(fake_hass, tmp_path):
    fake_hass.config.config_dir = str(tmp_path)
    fake_hass.states.get = lambda eid: object()
    return FittingManager(fake_hass, _FakeMonitor())


class TestSendTimesSession:
    @pytest.mark.asyncio
    async def test_override_beats_row_value(
        self, fake_hass, tmp_path, wigs_dir_path, _fast_heard_wait
    ):
        manager = _sending_manager(fake_hass, tmp_path)
        filename = _write_wig(wigs_dir_path)
        gated = AsyncMock()
        with patch("custom_components.hair.tx_gate.gated_send", gated):
            result = await manager.async_send(
                filename, 0, "infrared.e", send_times=3,
            )
        assert result["success"]
        assert gated.await_count == 3

    @pytest.mark.asyncio
    async def test_no_control_uses_row_default(
        self, fake_hass, tmp_path, wigs_dir_path, _fast_heard_wait
    ):
        manager = _sending_manager(fake_hass, tmp_path)
        filename = _write_wig(wigs_dir_path)
        gated = AsyncMock()
        with patch("custom_components.hair.tx_gate.gated_send", gated):
            result = await manager.async_send(filename, 0, "infrared.e")
        assert result["success"]
        assert gated.await_count == 1

    @pytest.mark.asyncio
    async def test_loop_clamped(
        self, fake_hass, tmp_path, wigs_dir_path, _fast_heard_wait
    ):
        manager = _sending_manager(fake_hass, tmp_path)
        filename = _write_wig(wigs_dir_path)
        gated = AsyncMock()
        with patch("custom_components.hair.tx_gate.gated_send", gated):
            await manager.async_send(
                filename, 0, "infrared.e", send_times=1000,
            )
        assert gated.await_count == 10

    @pytest.mark.asyncio
    async def test_record_lands_on_mark(
        self, fake_hass, tmp_path, wigs_dir_path, _fast_heard_wait
    ):
        manager = _sending_manager(fake_hass, tmp_path)
        filename = _write_wig(wigs_dir_path)
        with patch("custom_components.hair.tx_gate.gated_send",
                   AsyncMock()):
            await manager.async_send(
                filename, 0, "infrared.e", send_times=3, username="dab",
            )
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_flush()
        f = parse_fittings(_read_wig(wigs_dir_path)).fittings[0]
        assert f.send_times_used == 3

    @pytest.mark.asyncio
    async def test_record_is_monotonic(
        self, fake_hass, tmp_path, wigs_dir_path, _fast_heard_wait
    ):
        """Owner ruling 2026-07-30: lowering the control never lowers
        the record. Raise to 3, prove a signal, drop to 1 for the next:
        the claim stays 3."""
        manager = _sending_manager(fake_hass, tmp_path)
        filename = _write_wig(wigs_dir_path)
        with patch("custom_components.hair.tx_gate.gated_send",
                   AsyncMock()):
            await manager.async_send(
                filename, 0, "infrared.e", send_times=3, username="dab",
            )
            await manager.async_mark(filename, 0, "worked", "dab")
            await manager.async_send(
                filename, 1, "infrared.e", send_times=1, username="dab",
            )
            await manager.async_mark(filename, 1, "worked", "dab")
        await manager.async_flush()
        f = parse_fittings(_read_wig(wigs_dir_path)).fittings[0]
        assert f.send_times_used == 3

    @pytest.mark.asyncio
    async def test_send_writes_existing_draft_directly(
        self, fake_hass, tmp_path, wigs_dir_path, _fast_heard_wait
    ):
        """Handoff 4.2: once a draft exists, the send itself persists
        the record; no further mark is needed for it to survive."""
        manager = _sending_manager(fake_hass, tmp_path)
        filename = _write_wig(wigs_dir_path)
        await manager.async_mark(filename, 0, "worked", "dab")
        with patch("custom_components.hair.tx_gate.gated_send",
                   AsyncMock()):
            await manager.async_send(
                filename, 1, "infrared.e", send_times=3, username="dab",
            )
        await manager.async_flush()
        f = parse_fittings(_read_wig(wigs_dir_path)).fittings[0]
        assert f.send_times_used == 3

    @pytest.mark.asyncio
    async def test_bare_test_send_creates_no_draft(
        self, fake_hass, tmp_path, wigs_dir_path, _fast_heard_wait
    ):
        """First mark creates the draft; a test send never does."""
        manager = _sending_manager(fake_hass, tmp_path)
        filename = _write_wig(wigs_dir_path)
        with patch("custom_components.hair.tx_gate.gated_send",
                   AsyncMock()):
            await manager.async_send(
                filename, 0, "infrared.e", send_times=3, username="dab",
            )
        await manager.async_flush()
        assert parse_fittings(_read_wig(wigs_dir_path)).fittings == []

    @pytest.mark.asyncio
    async def test_record_survives_restart(
        self, fake_hass, tmp_path, wigs_dir_path, _fast_heard_wait
    ):
        """THE 4.2 test: an HA restart mid-fitting must not roll a
        tested-at-3 claim back to 1 through the resume path."""
        manager = _sending_manager(fake_hass, tmp_path)
        filename = _write_wig(wigs_dir_path)
        with patch("custom_components.hair.tx_gate.gated_send",
                   AsyncMock()):
            await manager.async_send(
                filename, 0, "infrared.e", send_times=3, username="dab",
            )
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_flush()

        # Restart: fresh manager, empty sessions.
        reborn = FittingManager(fake_hass, monitor=None)
        assert reborn.session_send_times(filename) is None
        await reborn.async_mark(filename, 1, "worked", "dab")
        await reborn.async_finish(filename, "dab", None, None, None)
        f = parse_fittings(_read_wig(wigs_dir_path)).fittings[0]
        assert f.raw["send_times_used"] == 3
        assert not f.draft

    @pytest.mark.asyncio
    async def test_finish_signs_the_record(
        self, fake_hass, tmp_path, wigs_dir_path, _fast_heard_wait
    ):
        manager = _sending_manager(fake_hass, tmp_path)
        filename = _write_wig(wigs_dir_path)
        with patch("custom_components.hair.tx_gate.gated_send",
                   AsyncMock()):
            await manager.async_send(
                filename, 0, "infrared.e", send_times=2, username="dab",
            )
        await manager.async_mark(filename, 0, "worked", "dab")
        await manager.async_mark(filename, 1, "worked", "dab")
        await manager.async_finish(filename, "dab", None, None, None)
        f = parse_fittings(_read_wig(wigs_dir_path)).fittings[0]
        assert f.raw["send_times_used"] == 2
        # Inside the signed payload when signing succeeded (the sandbox
        # may lack the cryptography package; the field is present
        # either way).
        if "sig" in f.raw:
            from custom_components.hair.fitting_signing import (
                verify_fitting,
            )

            assert verify_fitting(f.raw) == "valid"
