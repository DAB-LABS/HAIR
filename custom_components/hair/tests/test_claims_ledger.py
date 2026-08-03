"""The ledger: everything a reader can honestly say about attestations.

It replaced a tab inside the fitting dialog, and the point of the
replacement is what these tests assert. The old tab sat next to
controls that could edit the rows it was reporting on. The new one is a
pure read whose whole payload is derived from the file, which buys two
properties the old one could not have:

- It cannot lie about staleness, because there is no stored state to go
  stale. A row edited after somebody proved it reports as orphaned the
  next time anybody opens the dialog.
- It cannot disagree with the closet row's check, because both ask the
  same predicate (``bundle_is_complete``).

The third thing tested here is the honesty of the ORPHAN. A claim about
a row that no longer exists is not deleted and not counted as coverage.
Somebody really did prove that recipe; it just is not the recipe on the
file any more, and either hiding it or crediting it would misdescribe
what the wig has behind it.
"""
from __future__ import annotations

import pytest

from custom_components.hair.wig_claims import append_claims
from custom_components.hair.wig_fitting import claims_ledger, claims_summary
from custom_components.hair.wig_format import (
    VERDICT_NOT_ON_DEVICE,
    VERDICT_WORKED,
    ClaimsBundle,
    ClimateCell,
    ClimateMatrix,
    RowClaim,
    Wig,
    WigSignal,
    cells_content_hash,
    wig_row_digests,
)

PRONTO_A = "0000 006D 0002 0000 0020 0040 0020 0040"
PRONTO_B = "0000 006D 0002 0000 0030 0040 0020 0040"
PRONTO_C = "0000 006D 0002 0000 0040 0060 0040 0060"


def _wig() -> Wig:
    return Wig(name="TV", wig_id="u-1", signals=[
        WigSignal(alias="On", pronto=PRONTO_A),
        WigSignal(alias="Off", pronto=PRONTO_B),
    ])


def _matrix_wig() -> Wig:
    matrix = ClimateMatrix(
        min_temp=18.0,
        max_temp=30.0,
        off=PRONTO_A,
        cells=[
            ClimateCell(mode="cool", fan="auto", temp=22.0, pronto=PRONTO_A),
            ClimateCell(mode="heat", fan="auto", temp=24.0, pronto=PRONTO_B),
        ],
    )
    return Wig(name="AC", wig_id="u-2", signals=[], climate=matrix)


def _attest(wig: Wig, verdicts, handle="David", **kw) -> None:
    """Sign one bundle over the wig's CURRENT rows and append it."""
    digests = wig_row_digests(wig) or [
        f"cell-{i}" for i in range(len(verdicts))
    ]
    append_claims(wig, ClaimsBundle(
        wig_id=wig.wig_id or "u-1",
        handle=handle,
        rows=[
            RowClaim(alias_at_claim=f"row{i}", digest=d, verdict=v)
            for i, (d, v) in enumerate(zip(digests, verdicts, strict=True))
        ],
        **kw,
    ))


class TestWhatItReports:
    def test_an_unattested_wig_has_no_entries(self):
        ledger = claims_ledger(_wig(), "David")
        assert ledger["entries"] == []
        assert ledger["total"] == 2
        assert ledger["covered"] == 0

    def test_one_complete_attestation(self):
        wig = _wig()
        _attest(wig, [VERDICT_WORKED, VERDICT_WORKED])
        entry = claims_ledger(wig, "David")["entries"][0]
        assert entry["handle"] == "David"
        assert entry["complete"] is True
        assert entry["worked"] == 2
        assert entry["excluded"] == 0
        assert entry["orphaned"] == 0
        assert [r["verdict"] for r in entry["rows"]] == ["worked", "worked"]

    def test_an_exclusion_is_not_a_failure_and_not_silence(self):
        """The three states are worked, excluded, and unclaimed. An
        excluded row is a claim -- "not on my device" -- and it is why
        the bundle is scoped rather than perfect."""
        wig = _wig()
        _attest(wig, [VERDICT_WORKED, VERDICT_NOT_ON_DEVICE])
        entry = claims_ledger(wig, "David")["entries"][0]
        assert entry["complete"] is False
        assert (entry["worked"], entry["excluded"]) == (1, 1)

    def test_entries_are_in_file_order_not_yours_first(self):
        wig = _wig()
        _attest(wig, [VERDICT_WORKED, VERDICT_WORKED], handle="kno-te")
        _attest(wig, [VERDICT_WORKED, VERDICT_WORKED], handle="David")
        entries = claims_ledger(wig, "David")["entries"]
        assert [e["handle"] for e in entries] == ["kno-te", "David"]
        assert [e["mine"] for e in entries] == [False, True]

    def test_mine_matches_case_insensitively_and_stripped(self):
        wig = _wig()
        _attest(wig, [VERDICT_WORKED, VERDICT_WORKED], handle=" DAVID ")
        assert claims_ledger(wig, "david")["entries"][0]["mine"] is True

    def test_no_username_makes_nothing_yours(self):
        wig = _wig()
        _attest(wig, [VERDICT_WORKED, VERDICT_WORKED])
        assert claims_ledger(wig, None)["entries"][0]["mine"] is False

    def test_the_note_and_github_ride_along(self):
        wig = _wig()
        _attest(
            wig, [VERDICT_WORKED, VERDICT_WORKED],
            github="kno-te", note="Verified on the actual unit",
        )
        entry = claims_ledger(wig, "David")["entries"][0]
        assert entry["github"] == "kno-te"
        assert entry["note"] == "Verified on the actual unit"


class TestTheOrphan:
    """The property the whole dialog exists for."""

    def test_editing_a_row_orphans_only_that_claim(self):
        wig = _wig()
        _attest(wig, [VERDICT_WORKED, VERDICT_WORKED])
        wig.signals[0].pronto = PRONTO_C

        entry = claims_ledger(wig, "David")["entries"][0]
        assert [r["present"] for r in entry["rows"]] == [False, True]
        assert entry["orphaned"] == 1
        assert entry["complete"] is False

    def test_an_orphan_is_shown_not_dropped(self):
        """Deleting it would be the easy render and the dishonest one:
        the person really did prove that recipe."""
        wig = _wig()
        _attest(wig, [VERDICT_WORKED, VERDICT_WORKED])
        before = claims_ledger(wig, "David")["entries"][0]["rows"]
        wig.signals[0].pronto = PRONTO_C
        after = claims_ledger(wig, "David")["entries"][0]["rows"]
        assert len(after) == len(before) == 2

    def test_an_orphan_never_counts_toward_coverage(self):
        wig = _wig()
        _attest(wig, [VERDICT_WORKED, VERDICT_WORKED])
        assert claims_ledger(wig, "David")["covered"] == 2
        wig.signals[0].pronto = PRONTO_C
        assert claims_ledger(wig, "David")["covered"] == 1

    def test_a_rename_orphans_nothing(self):
        """Aliases are outside the digest, deliberately, so that
        renaming a row cannot invalidate somebody's proof of it."""
        wig = _wig()
        _attest(wig, [VERDICT_WORKED, VERDICT_WORKED])
        wig.signals[0].alias = "Power On"
        entry = claims_ledger(wig, "David")["entries"][0]
        assert entry["orphaned"] == 0
        # ...and the ledger still shows what it was CALLED when claimed.
        assert entry["rows"][0]["alias"] == "row0"

    def test_the_pin_is_an_edit_like_any_other(self):
        wig = _wig()
        _attest(wig, [VERDICT_WORKED, VERDICT_WORKED])
        wig.signals[1].bypass_protocol = True
        entry = claims_ledger(wig, "David")["entries"][0]
        assert entry["orphaned"] == 1


class TestSignatureState:
    def test_an_unsigned_bundle_reports_unsigned(self):
        wig = _wig()
        _attest(wig, [VERDICT_WORKED, VERDICT_WORKED])
        entry = claims_ledger(wig, "David")["entries"][0]
        assert entry["signed"] is None
        assert entry["key_fingerprint"] is None

    def test_a_signed_bundle_verifies(self):
        pytest.importorskip("cryptography")
        from .test_fitting_signing import _keypair_b64

        priv, _pub = _keypair_b64()
        wig = _wig()
        digests = wig_row_digests(wig)
        append_claims(wig, ClaimsBundle(
            wig_id="u-1", handle="David",
            rows=[
                RowClaim(alias_at_claim="x", digest=d, verdict=VERDICT_WORKED)
                for d in digests
            ],
        ), priv)
        entry = claims_ledger(wig, "David")["entries"][0]
        assert entry["signed"] == "valid"
        assert entry["key_fingerprint"]

    def test_a_tampered_bundle_reports_invalid_but_keeps_its_claims(self):
        """A bad signature discredits the attribution, never the data.
        The rows are still there and still legible."""
        pytest.importorskip("cryptography")
        from .test_fitting_signing import _keypair_b64

        priv, _pub = _keypair_b64()
        wig = _wig()
        append_claims(wig, ClaimsBundle(
            wig_id="u-1", handle="David",
            rows=[
                RowClaim(alias_at_claim="x", digest=d, verdict=VERDICT_WORKED)
                for d in wig_row_digests(wig)
            ],
        ), priv)
        wig.extra["fittings"][0]["handle"] = "somebody-else"

        entry = claims_ledger(wig, "David")["entries"][0]
        assert entry["signed"] == "invalid"
        assert len(entry["rows"]) == 2


class TestTheMatrixLattice:
    def test_a_checklist_row_is_never_orphaned(self):
        """Found on the box, 2026-08-03: a signed, current, complete
        Panasonic checklist reported all eight of its rows orphaned.

        A matrix wig has no flat row digests BY DESIGN -- its claims
        bind the lattice as a set and its rows are coordinates -- so
        per-row presence was being tested against an empty set, which
        answers "no" for everything. The set-level question is the only
        one this shape can answer, and ``lattice_current`` answers it.
        """
        wig = _matrix_wig()
        _attest(
            wig, [VERDICT_WORKED, VERDICT_WORKED],
            cells_hash=cells_content_hash(wig.climate),
        )
        entry = claims_ledger(wig, "David")["entries"][0]
        assert entry["orphaned"] == 0
        assert all(r["present"] for r in entry["rows"])
        assert entry["complete"] is True

    def test_a_checklist_bundle_pins_the_lattice_it_sampled(self):
        wig = _matrix_wig()
        stamp = cells_content_hash(wig.climate)
        _attest(wig, [VERDICT_WORKED, VERDICT_WORKED], cells_hash=stamp)
        entry = claims_ledger(wig, "David")["entries"][0]
        assert entry["cells_hash"] == stamp
        assert entry["lattice_current"] is True

    def test_a_moved_lattice_is_reported(self):
        """Unlike a flat wig there is no per-row way to say which part
        survived: the bundle vouched for a SET, and the set moved."""
        wig = _matrix_wig()
        _attest(
            wig, [VERDICT_WORKED, VERDICT_WORKED],
            cells_hash=cells_content_hash(wig.climate),
        )
        wig.climate.cells[0].pronto = PRONTO_C
        assert (
            claims_ledger(wig, "David")["entries"][0]["lattice_current"]
            is False
        )

    def test_a_flat_wig_has_no_lattice_verdict(self):
        wig = _wig()
        _attest(wig, [VERDICT_WORKED, VERDICT_WORKED])
        assert (
            claims_ledger(wig, "David")["entries"][0]["lattice_current"]
            is None
        )

    def test_a_matrix_wig_reports_no_flat_rows(self):
        wig = _matrix_wig()
        _attest(wig, [VERDICT_WORKED, VERDICT_WORKED])
        ledger = claims_ledger(wig, "David")
        assert ledger["matrix"] is True
        assert ledger["total"] == 0


class TestItCannotDisagreeWithTheCheck:
    """Both readings ask ``bundle_is_complete``. A person looking at a
    green check beside a ledger entry that reads "scoped" has found a
    bug in HAIR, not a fact about their wig.
    """

    @pytest.mark.parametrize("verdicts,state", [
        ([VERDICT_WORKED, VERDICT_WORKED], "perfect"),
        ([VERDICT_WORKED, VERDICT_NOT_ON_DEVICE], "scoped"),
    ])
    def test_flat(self, verdicts, state):
        wig = _wig()
        _attest(wig, verdicts)
        summary = claims_summary(wig, "David")
        entry = claims_ledger(wig, "David")["entries"][0]
        assert summary["state"] == state
        assert entry["complete"] is (state == "perfect")

    def test_matrix(self):
        wig = _matrix_wig()
        _attest(wig, [VERDICT_WORKED, VERDICT_WORKED])
        assert claims_summary(wig, "David")["state"] == "perfect"
        assert claims_ledger(wig, "David")["entries"][0]["complete"] is True

    def test_union_coverage_is_reported_but_never_completes_anybody(self):
        """Two people who each proved a different row: the union is
        total, and neither entry is complete."""
        wig = _wig()
        digests = wig_row_digests(wig)
        for handle, digest in (("David", digests[0]), ("kno-te", digests[1])):
            append_claims(wig, ClaimsBundle(
                wig_id="u-1", handle=handle,
                rows=[RowClaim(
                    alias_at_claim="x", digest=digest, verdict=VERDICT_WORKED,
                )],
            ))
        ledger = claims_ledger(wig, "David")
        assert ledger["covered"] == 2
        assert [e["complete"] for e in ledger["entries"]] == [False, False]
        assert claims_summary(wig, "David")["state"] == "scoped"


class TestTheWebsocketRead:
    @pytest.mark.asyncio
    async def test_it_returns_the_ledger_for_a_wig_on_disk(
        self, fake_hass, tmp_path
    ):
        from custom_components.hair.websocket_api import ws_wigs_claims
        from custom_components.hair.wig_format import serialize_wig

        wigs = tmp_path / "hair" / "wigs"
        wigs.mkdir(parents=True)
        wig = _wig()
        _attest(wig, [VERDICT_WORKED, VERDICT_WORKED])
        (wigs / "tv.wig.json").write_text(
            serialize_wig(wig), encoding="utf-8"
        )
        fake_hass.config.config_dir = str(tmp_path)

        connection = _FakeConnection("David")
        await ws_wigs_claims(
            fake_hass, connection,
            {"id": 1, "type": "hair/wigs/claims", "filename": "tv.wig.json"},
        )
        assert connection.result["filename"] == "tv.wig.json"
        assert connection.result["entries"][0]["handle"] == "David"
        assert connection.result["entries"][0]["mine"] is True

    @pytest.mark.asyncio
    async def test_a_missing_wig_is_an_error_not_an_empty_ledger(
        self, fake_hass, tmp_path
    ):
        """An empty ledger means "nobody has attested this"; a missing
        file means something else entirely, and conflating them would
        show a reassuring dialog about a wig that is not there."""
        from custom_components.hair.websocket_api import ws_wigs_claims

        (tmp_path / "hair" / "wigs").mkdir(parents=True)
        fake_hass.config.config_dir = str(tmp_path)

        connection = _FakeConnection("David")
        await ws_wigs_claims(
            fake_hass, connection,
            {"id": 1, "type": "hair/wigs/claims", "filename": "gone.wig.json"},
        )
        assert connection.result is None
        assert connection.error == "not_found"

    def test_there_is_no_write_command_beside_it(self):
        """Structural, not stylistic. The ledger's read-only-ness is the
        whole reason it could be lifted out of the fitting dialog, and a
        claims mutation command appearing next to it would quietly
        rebuild the thing v0.9.5 removed."""
        import inspect

        from custom_components.hair import websocket_api

        source = inspect.getsource(websocket_api)
        assert '/wigs/claims"' in source
        for verb in ("claims/set", "claims/mark", "claims/delete",
                     "claims/update", "claims/edit"):
            assert verb not in source, verb


class _FakeConnection:
    def __init__(self, username: str | None):
        self.user = type("U", (), {"name": username})()
        self.result = None
        self.error = None

    def send_result(self, _id, payload):
        self.result = payload

    def send_error(self, _id, code, _message):
        self.error = code
