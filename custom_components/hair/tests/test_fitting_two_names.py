"""A wig, and a Perfect Fit: the two names and the saves between them.

Ruled 2026-09-16, retiring the partial-fitting question
perfect-or-nothing left open on 2026-08-07. There are two kinds of wig
and two names, and the second is the only one that is earned:

- **A wig.** Built by somebody, shared to help others. It may carry no
  attestation at all, or a signed fitting that covers some of its rows.
  No suffix, no badge, no tier of its own.
- **A Perfect Fit.** One person's claims cover every row of the wig in
  one fitting. Green tick, ``-perfect-fit`` in the download name.

Two fittings never add up, and that half is unchanged -- the tick, the
suffix and ``claims_summary`` mean exactly what they meant. What
changes is that the dialog stops REFUSING a fitting that covers part of
the wig, and that the vocabulary around it stops calling such a fitting
incomplete, scoped, or unfitted. Nothing went wrong with those wigs;
nobody has finished proving them yet.

The dialog half reads the TypeScript rather than running it, which is
the house tactic (see test_polish_rulings.py's own header). The backend
half runs.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hair.const import DOMAIN
from custom_components.hair.models import IRCommand, IRDevice
from custom_components.hair.websocket_api import ws_wigs_save
from custom_components.hair.wig_fitting import claims_ledger, claims_summary
from custom_components.hair.wig_format import (
    VERDICT_WORKED,
    Wig,
    WigSignal,
    download_filename,
    parse_wig,
    serialize_wig,
    signal_row_digest,
)
from custom_components.hair.wig_store import ensure_wigs_dir, wigs_dir

SRC = Path(__file__).parent.parent / "frontend" / "src"
LOCALES = SRC / "locales"
LOCALE_NAMES = (
    "en", "de", "es", "fr", "it", "ja", "nl", "pl", "pt", "ru",
)

PRONTO_A = "0000 006D 0002 0000 0020 0040 0020 0040"
PRONTO_B = "0000 006D 0002 0000 0030 0040 0020 0040"
PRONTO_C = "0000 006D 0002 0000 0040 0040 0020 0040"


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _block(text: str, opener: str) -> str:
    """One getter or method body, by its opening line."""
    assert opener in text, opener
    return text.split(opener, 1)[1].split("\n    }", 1)[0]


def _locale(stem: str) -> dict:
    return json.loads((LOCALES / f"{stem}.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------
# The dialog
# ---------------------------------------------------------------------


class TestTheDialogSavesAFittingOfAnySize:
    """``ir-save-perfect-dialog.ts``. The refusal that made a
    half-proved wig unsaveable is gone; everything that made a
    signature mean something is not."""

    def test_the_all_or_nothing_refusal_is_gone(self):
        """The one line this whole ruling is about. It read "armed but
        not every row attested, refuse", which is what turned an
        ordinary shared wig into something the dialog would not let
        you write."""
        text = _read("ir-save-perfect-dialog.ts")
        can_save = _block(text, "private get _canSave(): boolean {")
        assert "_fullyAttested" not in can_save
        # And the getter itself is gone, not merely unread: a dead
        # predicate is how the rule creeps back in.
        assert "_fullyAttested" not in text

    def test_the_oath_still_gates_anything_that_signs(self):
        """Nothing signs without the oath, in either verb. A save that
        claims nothing signs nothing, so it asks for no oath -- which
        is not a hole in the gate, it is the gate having nothing to
        stand in front of."""
        text = _read("ir-save-perfect-dialog.ts")
        can_save = _block(text, "private get _canSave(): boolean {")
        assert "this._hasClaims && !this._oath" in can_save
        signed = _block(text, "private get _signed(): boolean {")
        assert "this._hasClaims" in signed
        assert "this._oath" in signed

    def test_three_labels_by_what_the_save_writes(self):
        """Nothing claimed is a plain Save. Some rows claimed is a
        fitting. Every row checked is the earned name."""
        text = _read("ir-save-perfect-dialog.ts")
        label = _block(text, "private get _saveLabel(): string {")
        assert 'if (!this._hasClaims) return t("common.save");' in label
        assert 'this._isPerfectFit' in label
        assert '"wigs.save.save_perfect"' in label
        assert '"wigs.save.save_fitting"' in label

    def test_the_matrix_carve_out_label_is_retired(self):
        """"Save Fitting Record" existed for a fully-attested matrix
        carrying an exclusion -- a real record that was not a PERFECT
        FIT. That is now just a fitting, and one word covers both."""
        assert "save_record" not in _read("ir-save-perfect-dialog.ts")
        for stem in LOCALE_NAMES:
            assert "wigs.save.save_record" not in _locale(stem), stem

    def test_a_save_that_claims_nothing_sends_no_attest_block(self):
        """An empty block would ask the server to sign a record
        vouching for no rows. A rename with no claims still travels:
        proposing a name is a content edit the person ticked, not a
        claim about hardware."""
        text = _read("ir-save-perfect-dialog.ts")
        body = _block(
            text, "private async _saveDevice(): Promise<SaveResult> {"
        )
        assert "claims.length > 0 || renames.length > 0" in body
        assert "...(attest ? { attest } : {})" in body

    def test_the_progress_line_and_the_exclusion_note_stay(self):
        """The checklist still counts out loud. With a partial save
        allowed, "7 of 12 rows attested" stops being a countdown to
        the only acceptable answer and starts being a description --
        same string, better job."""
        text = _read("ir-save-perfect-dialog.ts")
        assert "wigs.save.attest_progress" in text
        assert "wigs.save.exclusion_note" in text

    def test_the_route_is_named_for_what_it_does(self):
        """"Validate for Perfect Fit" named the best case. The dialog
        is the one place a fitting of any size is recorded now, so the
        name says the act."""
        for name in ("ir-save-perfect-dialog.ts", "ir-save-route-dialog.ts"):
            text = _read(name)
            assert "wigs.route.fit_wig" in text, name
            assert "validate_perfect_fit" not in text, name
        for stem in LOCALE_NAMES:
            data = _locale(stem)
            assert "wigs.route.fit_wig" in data, stem
            assert "wigs.route.validate_perfect_fit" not in data, stem


class TestTheClosetShowsOneChip:
    """``ir-wigs.ts``. "Fitted" and "Not fitted" split the closet into a
    state and its absence, which said a wig nobody has finished proving
    is missing something."""

    def test_the_fitted_pair_is_replaced_by_one_perfect_chip(self):
        text = _read("ir-wigs.ts")
        assert "wigs.chip.perfect" in text
        assert "wigs.chip.fitted" not in text
        assert "wigs.chip.unfitted" not in text
        assert (
            'type FilterChip = "all" | "library" | "yours" | "perfect";'
            in text
        )

    def test_the_chip_is_keyed_on_the_ticks_own_state(self):
        """The old chip keyed on ``fitters > 0`` deliberately, so that
        a record carrying exclusions would not read as unfitted. With
        the pair gone the chip can key on the judgment itself, and the
        chip and the tick cannot disagree about a row."""
        text = _read("ir-wigs.ts")
        assert 'r.wig?.fitting?.state === "perfect"' in text
        assert 'w.fitting?.state === "perfect"' in text

    def test_the_tick_and_its_tooltip_are_untouched(self):
        text = _read("ir-wigs.ts")
        assert "wigs.fit_tick.perfect_by" in text
        assert "wigs.fit_tick.perfect" in text
        assert 'class="fit-tick' in text

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_no_locale_keeps_the_retired_chips(self, locale):
        data = _locale(locale)
        assert "wigs.chip.perfect" in data
        assert "wigs.chip.fitted" not in data
        assert "wigs.chip.unfitted" not in data


class TestTheLedgerCallsItAFitting:
    """``ir-claims-ledger.ts``. The badge named the bundle by what it
    lacked: "scoped", then "Incomplete". The row count beside it
    already says how far it got."""

    def test_the_badge_reads_fitting(self):
        text = _read("ir-claims-ledger.ts")
        assert "claims.tier_fitting" in text
        assert "claims.tier_scoped" not in text
        assert "claims.tier_perfect" in text

    def test_the_union_line_and_the_empty_line_are_untouched(self):
        """"7 of 12 rows proved between everyone" keeps counting the
        union, because it is true and worth knowing. It still never
        turns into a tick."""
        text = _read("ir-claims-ledger.ts")
        assert "claims.union" in text
        assert "claims.none" in text

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_every_locale_carries_the_renamed_key(self, locale):
        data = _locale(locale)
        assert "claims.tier_fitting" in data
        assert "claims.tier_scoped" not in data


class TestTheSupersedeDialogNamesAPartialFitting:
    """``ir-supersede-dialog.ts``. A PERFECT FIT retiring was named; a
    fitting covering part of the wig was discarded in silence. It is
    somebody's work on their own hardware either way."""

    def test_both_branches_render(self):
        text = _read("ir-supersede-dialog.ts")
        assert "supersede.fitted_perfect" in text
        assert "supersede.fitted_partial" in text
        # The wording that retired in 2026-08-07 does not come back
        # with the branch (ruling: do not restore "scoped").
        assert "scoped" not in text

    def test_the_partial_line_names_coverage_not_a_shortfall(self):
        text = _read("ir-supersede-dialog.ts")
        assert "covered: String(fitted.covered)" in text
        assert "total: String(fitted.total)" in text

    @pytest.mark.parametrize("locale", LOCALE_NAMES)
    def test_every_locale_carries_the_new_plural_family(self, locale):
        data = _locale(locale)
        for suffix in ("one", "other"):
            key = f"supersede.fitted_partial.{suffix}"
            assert key in data, f"{locale} missing {key}"
            for placeholder in ("{name}", "{who}", "{covered}", "{total}"):
                assert placeholder in data[key], f"{locale}:{key}"
        assert "supersede.fitted_scoped.one" not in data
        assert "supersede.fitted_scoped.other" not in data


# ---------------------------------------------------------------------
# The backend
# ---------------------------------------------------------------------


def _conn():
    conn = MagicMock()
    conn.send_result = MagicMock()
    conn.send_error = MagicMock()
    return conn


def _command(name, pronto):
    return IRCommand(
        name=name, protocol="PRONTO", code=pronto, repeat_count=0
    )


def _wire(hass, tmp_path, device):
    hass.config.config_dir = str(tmp_path)
    ensure_wigs_dir(tmp_path)
    store = MagicMock()
    store.get_device = MagicMock(
        side_effect=lambda did: device if did == device.id else None
    )
    store.get_all_devices = MagicMock(return_value=[device])
    manager = MagicMock()
    manager.async_update_device = AsyncMock()
    hass.data[DOMAIN] = {
        "entry-1": {"store": store, "device_manager": manager}
    }
    return manager


def _closet_wig(tmp_path, wig, filename="edifier.wig.json"):
    ensure_wigs_dir(tmp_path)
    path = wigs_dir(tmp_path) / filename
    path.write_text(serialize_wig(wig), encoding="utf-8")
    return path


def _three_row_wig():
    return Wig(
        name="Edifier", wig_id="u-source",
        signals=[
            WigSignal(alias="On", pronto=PRONTO_A),
            WigSignal(alias="Off", pronto=PRONTO_B),
            WigSignal(alias="Mute", pronto=PRONTO_C),
        ],
    )


def _three_command_device():
    return IRDevice(
        name="Speakers",
        commands=[
            _command("On", PRONTO_A),
            _command("Off", PRONTO_B),
            _command("Mute", PRONTO_C),
        ],
        source_wig_id="u-source",
    )


@pytest.fixture
def _no_signing(monkeypatch):
    monkeypatch.setattr(
        "custom_components.hair.fitting_signing.async_get_private_key",
        AsyncMock(return_value=None),
    )


class TestAnEmptyChecklistIsNotAnAttestation:
    """The hole the ruling opened onto. Until now the dialog could not
    reach save with nothing ticked, so nothing had to stop an empty
    bundle from being signed -- and nothing did. A save with nothing
    ticked is an ordinary thing to do now, so the guard is the
    difference between a wig with no fitting and a wig carrying a
    signature that vouches for nothing."""

    @pytest.mark.asyncio
    async def test_a_create_with_empty_claims_writes_no_bundle(
        self, fake_hass, tmp_path, _no_signing
    ):
        device = IRDevice(name="Fan", commands=[_command("On", PRONTO_A)])
        _wire(fake_hass, tmp_path, device)
        conn = _conn()
        await ws_wigs_save(
            fake_hass, conn,
            {
                "id": 1, "type": "hair/wigs/save", "device_id": device.id,
                "mode": "create", "name": "Bench Fan",
                "attest": {"claims": [], "handle": "David"},
            },
        )
        result = conn.send_result.call_args[0][1]
        assert result["attested"] == 0
        written = json.loads(
            (wigs_dir(tmp_path) / result["filename"]).read_text()
        )
        assert "fittings" not in written
        # The wig itself is written, which is the whole point: this is
        # a plain save that happened to arrive with an empty sheet.
        assert written["name"] == "Bench Fan"
        assert len(written["signals"]) == 1

    @pytest.mark.asyncio
    async def test_an_update_with_empty_claims_and_no_edits_refuses(
        self, fake_hass, tmp_path, _no_signing
    ):
        """Honest refusal rather than a rewrite: an empty sheet over an
        unchanged file would produce a shop PR that says nothing."""
        wig = _three_row_wig()
        path = _closet_wig(tmp_path, wig)
        before = path.read_text()
        device = _three_command_device()
        _wire(fake_hass, tmp_path, device)
        conn = _conn()
        await ws_wigs_save(
            fake_hass, conn,
            {
                "id": 1, "type": "hair/wigs/save", "device_id": device.id,
                "mode": "update",
                "attest": {"claims": [], "handle": "David"},
            },
        )
        assert conn.send_error.call_args[0][1] == "nothing_to_update"
        assert path.read_text() == before

    @pytest.mark.asyncio
    async def test_an_update_with_empty_claims_still_writes_metadata(
        self, fake_hass, tmp_path, _no_signing
    ):
        """A metadata edit is a content PR on its own terms, and an
        empty sheet riding along with it changes nothing about that --
        except that no bundle is appended."""
        wig = _three_row_wig()
        path = _closet_wig(tmp_path, wig)
        device = _three_command_device()
        _wire(fake_hass, tmp_path, device)
        conn = _conn()
        await ws_wigs_save(
            fake_hass, conn,
            {
                "id": 1, "type": "hair/wigs/save", "device_id": device.id,
                "mode": "update", "brand": "Edifier",
                "attest": {"claims": [], "handle": "David"},
            },
        )
        result = conn.send_result.call_args[0][1]
        assert result["attested"] == 0
        after = json.loads(path.read_text())
        assert after["brand"] == "Edifier"
        assert "fittings" not in after

    @pytest.mark.asyncio
    async def test_a_rename_with_no_claims_is_proposed_and_signs_nothing(
        self, fake_hass, tmp_path, _no_signing
    ):
        """The one reason an empty-claims block still arrives from the
        dialog. The rename lands, and no signature goes on the file to
        say somebody proved something they did not."""
        wig = _three_row_wig()
        path = _closet_wig(tmp_path, wig)
        device = _three_command_device()
        device.commands[0].name = "Power"
        _wire(fake_hass, tmp_path, device)
        conn = _conn()
        await ws_wigs_save(
            fake_hass, conn,
            {
                "id": 1, "type": "hair/wigs/save", "device_id": device.id,
                "mode": "update",
                "attest": {
                    "claims": [],
                    "handle": "David",
                    "renames": [{
                        "digest": signal_row_digest(wig.signals[0]),
                        "alias_at_claim": "On",
                        "alias": "Power",
                    }],
                },
            },
        )
        assert not conn.send_error.called
        after = json.loads(path.read_text())
        assert [s["alias"] for s in after["signals"]] == [
            "Power", "Off", "Mute",
        ]
        assert "fittings" not in after


class TestAFittingThatCoversPartOfTheWig:
    """k of N. It is signed, appended, counted and listed -- and it is
    not a Perfect Fit, which is the only thing that stays reserved."""

    @pytest.mark.asyncio
    async def test_it_is_signed_appended_and_listed(
        self, fake_hass, tmp_path, _no_signing
    ):
        wig = _three_row_wig()
        path = _closet_wig(tmp_path, wig)
        device = _three_command_device()
        _wire(fake_hass, tmp_path, device)
        conn = _conn()
        await ws_wigs_save(
            fake_hass, conn,
            {
                "id": 1, "type": "hair/wigs/save", "device_id": device.id,
                "mode": "update",
                "attest": {
                    "claims": [
                        {
                            "digest": signal_row_digest(wig.signals[0]),
                            "verdict": VERDICT_WORKED,
                        },
                        {
                            "digest": signal_row_digest(wig.signals[1]),
                            "verdict": VERDICT_WORKED,
                        },
                    ],
                    "handle": "David",
                },
            },
        )
        result = conn.send_result.call_args[0][1]
        assert result["attested"] == 2

        saved = parse_wig(path.read_text()).wig
        assert saved is not None
        ledger = claims_ledger(saved, None)
        assert len(ledger["entries"]) == 1
        entry = ledger["entries"][0]
        assert entry["handle"] == "David"
        assert entry["complete"] is False
        assert entry["worked"] == 2
        assert ledger["covered"] == 2
        assert ledger["total"] == 3

    @pytest.mark.asyncio
    async def test_it_earns_no_tick_and_no_suffix(
        self, fake_hass, tmp_path, _no_signing
    ):
        """The half that does not change. Two of three rows proved is a
        real record and not a claim that the wig works."""
        wig = _three_row_wig()
        path = _closet_wig(tmp_path, wig)
        device = _three_command_device()
        _wire(fake_hass, tmp_path, device)
        conn = _conn()
        await ws_wigs_save(
            fake_hass, conn,
            {
                "id": 1, "type": "hair/wigs/save", "device_id": device.id,
                "mode": "update",
                "attest": {
                    "claims": [{
                        "digest": signal_row_digest(wig.signals[0]),
                        "verdict": VERDICT_WORKED,
                    }],
                    "handle": "David",
                },
            },
        )
        saved = parse_wig(path.read_text()).wig
        assert saved is not None
        summary = claims_summary(saved, None)
        assert summary["state"] is None
        assert summary["fitters"] == 1
        assert summary["covered"] == 1
        assert summary["total"] == 3
        assert summary["perfect_by"] == []
        assert download_filename(saved) == "edifier.wig.json"

    @pytest.mark.asyncio
    async def test_covering_every_row_still_earns_both(
        self, fake_hass, tmp_path, _no_signing
    ):
        wig = _three_row_wig()
        path = _closet_wig(tmp_path, wig)
        device = _three_command_device()
        _wire(fake_hass, tmp_path, device)
        conn = _conn()
        await ws_wigs_save(
            fake_hass, conn,
            {
                "id": 1, "type": "hair/wigs/save", "device_id": device.id,
                "mode": "update",
                "attest": {
                    "claims": [
                        {"digest": signal_row_digest(s),
                         "verdict": VERDICT_WORKED}
                        for s in wig.signals
                    ],
                    "handle": "David",
                },
            },
        )
        saved = parse_wig(path.read_text()).wig
        assert saved is not None
        summary = claims_summary(saved, None)
        assert summary["state"] == "perfect"
        assert summary["perfect_by"] == ["David"]
        assert download_filename(saved) == "edifier-perfect-fit.wig.json"


class TestTheSupersedeBlockCarriesCoverage:
    """The confirm names a retiring partial fitting by what it covers,
    so the two numbers ride with the grade instead of being fetched
    from the ledger separately."""

    def test_detect_supersession_reports_covered_and_total(self, tmp_path):
        from custom_components.hair.wig_format import (
            ClaimsBundle,
            RowClaim,
            claims_bundle_out,
        )
        from custom_components.hair.wig_save import detect_supersession

        ancestor = _three_row_wig()
        bundle = ClaimsBundle(
            wig_id="u-source",
            handle="Ann",
            rows=[RowClaim(
                alias_at_claim="On",
                digest=signal_row_digest(ancestor.signals[0]),
                verdict=VERDICT_WORKED,
            )],
        )
        ancestor.extra["fittings"] = [claims_bundle_out(bundle)]
        _closet_wig(tmp_path, ancestor)

        successor = Wig(
            name="Edifier", wig_id="u-new",
            signals=list(ancestor.signals),
            supersedes=["u-source"],
        )
        block = detect_supersession(tmp_path, successor, [])
        assert block is not None
        assert block["old_fittings"]["state"] is None
        assert block["old_fittings"]["count"] == 1
        assert block["old_fittings"]["handles"] == ["Ann"]
        assert block["old_fittings"]["covered"] == 1
        assert block["old_fittings"]["total"] == 3
