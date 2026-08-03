"""SAVE TO CLOSET: the plan the dialog draws, and the save it performs.

The plan is the whole reason the fitting session could die: everything
the old apparatus remembered between visits is recomputed here from the
device and the file, on the spot. So the tests that matter most are the
ones about ALIGNMENT -- a plan row pointing at the wrong command, or a
claim carrying the wrong name, would both look perfectly healthy in the
resulting file while attesting something nobody said.
"""
from __future__ import annotations

import json

from custom_components.hair.models import IRCommand, IRDevice
from custom_components.hair.wig_claims import RenameProposal, signals_block
from custom_components.hair.wig_export import build_wig_from_device
from custom_components.hair.wig_format import (
    VERDICT_NOT_ON_DEVICE,
    VERDICT_WORKED,
    Wig,
    WigSignal,
    serialize_wig,
    signal_row_digest,
)
from custom_components.hair.wig_save import (
    VARIANT_CREATE,
    VARIANT_UPDATE,
    Attestation,
    build_save_plan,
    create_text,
    update_text,
)

PRONTO_A = "0000 006D 0002 0000 0020 0040 0020 0040"
PRONTO_B = "0000 006D 0002 0000 0030 0040 0020 0040"
PRONTO_C = "0000 006D 0002 0000 0040 0040 0020 0040"


def _command(name, pronto, **kwargs):
    # Dittos default to none unless a test asks for them. IRCommand's
    # own default is 1, which is the catalog default rather than an
    # adopted wig's value -- and a row's ditto count is IN the digest,
    # so a fixture that let the default stand would quietly fail to
    # match the wig row it is meant to be a copy of.
    kwargs.setdefault("repeat_count", 0)
    return IRCommand(name=name, protocol="PRONTO", code=pronto, **kwargs)


def _device(commands, **kwargs):
    return IRDevice(name="Bench Fan", commands=list(commands), **kwargs)


class TestThePlanIsCreate:
    def test_a_device_from_nowhere_creates(self):
        plan = build_save_plan(_device([_command("On", PRONTO_A)]))
        assert plan.variant == VARIANT_CREATE
        assert plan.source_wig_id is None
        assert plan.source_missing is False

    def test_rows_carry_what_the_dialog_shows(self):
        command = _command(
            "On", PRONTO_A, send_count=3, repeat_count=2,
        )
        command.decoded_protocol = "NEC"
        plan = build_save_plan(_device([command]))
        row = plan.rows[0]
        assert row.alias == "On"
        assert row.send_count == 3
        assert row.ditto_count == 2
        assert row.bypass is False
        assert row.protocol == "NEC"
        assert row.command_id == command.id

    def test_a_skipped_signal_does_not_shift_the_rest(self):
        """THE ALIGNMENT TEST.

        A command with no usable Pronto never becomes a wig signal, so
        the two lists stop being parallel at that point. If the plan
        indexed the device by position, every row after the gap would
        carry the wrong command id -- and TEST would fire the wrong
        code while the person attested the right name.
        """
        good_one = _command("On", PRONTO_A)
        dud = IRCommand(name="Broken", protocol=None, code=None)
        good_two = _command("Off", PRONTO_B)
        plan = build_save_plan(_device([good_one, dud, good_two]))
        assert plan.skipped == 1
        assert [r.alias for r in plan.rows] == ["On", "Off"]
        assert [r.command_id for r in plan.rows] == [good_one.id, good_two.id]

    def test_a_converted_seed_is_remembered(self):
        plan = build_save_plan(
            _device([_command("On", PRONTO_A)], source_file="dreo.wig.json")
        )
        assert plan.converted_from == "dreo.wig.json"

    def test_a_source_wig_that_vanished_says_so(self):
        """Degrade to CREATE, but do not pretend the link never existed.

        Refusing would strand a working device with no way to save;
        silence would let the person believe they had updated the shop
        wig when they had minted a private copy.
        """
        plan = build_save_plan(
            _device([_command("On", PRONTO_A)], source_wig_id="u-gone"),
            source_wig=None,
        )
        assert plan.variant == VARIANT_CREATE
        assert plan.source_missing is True


class TestThePlanIsUpdate:
    def _wig(self):
        return Wig(
            name="Edifier R1280T",
            brand="Edifier",
            model="R1280T",
            notes="from the shop",
            wig_id="u-source",
            signals=[
                WigSignal(alias="On", pronto=PRONTO_A),
                WigSignal(alias="Mute", pronto=PRONTO_B),
                WigSignal(alias="Sleep", pronto=PRONTO_C),
            ],
        )

    def test_matched_rows_point_at_their_wig_row(self):
        wig = self._wig()
        plan = build_save_plan(
            _device([_command("On", PRONTO_A)], source_wig_id="u-source"),
            wig,
            "edifier.wig.json",
        )
        assert plan.variant == VARIANT_UPDATE
        assert plan.source_filename == "edifier.wig.json"
        assert plan.rows[0].matched is True
        assert plan.rows[0].wig_index == 0
        assert plan.rows[0].renamed is False

    def test_a_local_rename_surfaces_both_names(self):
        wig = self._wig()
        plan = build_save_plan(
            _device([_command("Power", PRONTO_A)], source_wig_id="u-source"),
            wig,
        )
        row = plan.rows[0]
        assert row.matched is True
        assert row.renamed is True
        assert row.alias == "Power"
        assert row.wig_alias == "On"

    def test_rows_the_device_lacks_feed_the_exclusion_picker(self):
        wig = self._wig()
        plan = build_save_plan(
            _device([_command("On", PRONTO_A)], source_wig_id="u-source"),
            wig,
        )
        assert [r.alias for r in plan.missing_rows] == ["Mute", "Sleep"]
        assert plan.missing_rows[0].digest == signal_row_digest(
            wig.signals[1]
        )

    def test_metadata_prefills_from_the_wig_not_the_device(self):
        """An UPDATE proposes the WIG's metadata back, unchanged.

        Prefilling from the device would smuggle a content change into
        an attestation: the adopter's local device name would arrive as
        a proposed rename of somebody else's wig.
        """
        plan = build_save_plan(
            _device([_command("On", PRONTO_A)], source_wig_id="u-source"),
            self._wig(),
        )
        assert plan.metadata["name"] == "Edifier R1280T"
        assert plan.metadata["brand"] == "Edifier"
        assert plan.metadata["notes"] == "from the shop"

    def test_a_listed_identifier_prefills_its_first_value(self):
        wig = self._wig()
        wig.identifiers = {"fcc_id": ["AAA", "BBB"]}
        plan = build_save_plan(
            _device([_command("On", PRONTO_A)], source_wig_id="u-source"),
            wig,
        )
        assert plan.metadata["fcc_id"] == "AAA"


class TestCreate:
    def _build(self, commands=None):
        return build_wig_from_device(
            _device(commands or [_command("On", PRONTO_A, send_count=3)])
        )

    def test_a_new_wig_gets_an_identity(self):
        text, result = create_text(self._build())
        assert result.wig_id
        assert json.loads(text)["wig_id"] == result.wig_id

    def test_a_plain_save_carries_no_fittings(self):
        text, result = create_text(self._build())
        assert "fittings" not in json.loads(text)
        assert result.attested == 0

    def test_the_authors_claims_are_born_with_the_wig(self):
        build = self._build()
        digest = signal_row_digest(build.wig.signals[0])
        text, result = create_text(
            build,
            Attestation(
                claims={digest: VERDICT_WORKED},
                handle="David",
                github="dab",
            ),
        )
        data = json.loads(text)
        assert result.attested == 1
        bundle = data["fittings"][0]
        assert bundle["handle"] == "David"
        assert bundle["rows"][0]["digest"] == digest
        assert bundle["rows"][0]["alias_at_claim"] == "On"

    def test_the_bundle_names_the_wig_it_was_born_on(self):
        """A claim that names a different wig is not a claim about this
        one. The id is minted during this same save, so the bundle can
        only get it by being assembled after the mint."""
        build = self._build()
        text, result = create_text(
            build,
            Attestation(
                claims={signal_row_digest(build.wig.signals[0]): VERDICT_WORKED}
            ),
        )
        data = json.loads(text)
        assert data["fittings"][0]["wig_id"] == data["wig_id"]
        assert data["wig_id"] == result.wig_id

    def test_an_exclusion_rides_with_its_reason(self):
        build = self._build([
            _command("On", PRONTO_A), _command("Sleep", PRONTO_B),
        ])
        digests = [signal_row_digest(s) for s in build.wig.signals]
        text, _ = create_text(
            build,
            Attestation(claims={
                digests[0]: VERDICT_WORKED,
                digests[1]: VERDICT_NOT_ON_DEVICE,
            }),
        )
        verdicts = {
            row["digest"]: row["verdict"]
            for row in json.loads(text)["fittings"][0]["rows"]
        }
        assert verdicts[digests[1]] == VERDICT_NOT_ON_DEVICE

    def test_an_unclaimed_row_is_absent_not_excluded(self):
        """Silence is not a verdict.

        Unchecking without a reason means no claim at all, which is a
        third state -- and it has to stay a third state, or every row
        somebody skipped would read as one they said did not work.
        """
        build = self._build([
            _command("On", PRONTO_A), _command("Sleep", PRONTO_B),
        ])
        digests = [signal_row_digest(s) for s in build.wig.signals]
        text, _ = create_text(
            build, Attestation(claims={digests[0]: VERDICT_WORKED})
        )
        rows = json.loads(text)["fittings"][0]["rows"]
        assert [row["digest"] for row in rows] == [digests[0]]


class TestUpdate:
    def _wig(self):
        return Wig(
            name="Edifier",
            wig_id="u-source",
            signals=[
                WigSignal(alias="On", pronto=PRONTO_A, send_count=3),
                WigSignal(alias="Mute", pronto=PRONTO_B, ditto_count=1),
            ],
        )

    def test_the_signals_block_comes_back_byte_identical(self):
        """Hard rule 3, through the save layer this time.

        An attestation PR that also rewrote content would arrive looking
        like a content change, and a maintainer would have to diff it to
        find out it was not.
        """
        wig = self._wig()
        text = serialize_wig(wig)
        new_text, _ = update_text(
            text,
            wig,
            Attestation(
                claims={signal_row_digest(wig.signals[0]): VERDICT_WORKED}
            ),
        )
        assert signals_block(new_text) == signals_block(text)

    def test_the_claim_carries_the_wigs_name_not_the_devices(self):
        wig = self._wig()
        new_text, _ = update_text(
            serialize_wig(wig),
            wig,
            Attestation(
                claims={signal_row_digest(wig.signals[0]): VERDICT_WORKED}
            ),
        )
        row = json.loads(new_text)["fittings"][0]["rows"][0]
        assert row["alias_at_claim"] == "On"

    def test_a_rename_in_the_same_save_is_the_name_the_claim_records(self):
        """Otherwise the bundle says On beside a row the same commit
        renames to Power, and a later reader concludes the rename came
        after the claim -- the one thing alias_at_claim exists to say."""
        wig = self._wig()
        digest = signal_row_digest(wig.signals[0])
        new_text, _ = update_text(
            serialize_wig(wig),
            wig,
            Attestation(
                claims={digest: VERDICT_WORKED},
                renames=[RenameProposal(digest, "On", "Power")],
            ),
        )
        data = json.loads(new_text)
        assert data["signals"][0]["alias"] == "Power"
        assert data["fittings"][0]["rows"][0]["alias_at_claim"] == "Power"

    def test_a_rename_that_matches_nothing_is_reported(self):
        wig = self._wig()
        digest = signal_row_digest(wig.signals[0])
        _, result = update_text(
            serialize_wig(wig),
            wig,
            Attestation(
                claims={digest: VERDICT_WORKED},
                renames=[RenameProposal(digest, "Nonexistent", "Power")],
            ),
        )
        assert result.stale_renames == ["Nonexistent"]

    def test_claims_append_rather_than_replace(self):
        wig = self._wig()
        digest = signal_row_digest(wig.signals[0])
        first, _ = update_text(
            serialize_wig(wig), wig,
            Attestation(claims={digest: VERDICT_WORKED}, handle="A"),
        )
        from custom_components.hair.wig_format import parse_wig

        second, _ = update_text(
            first, parse_wig(first).wig,
            Attestation(claims={digest: VERDICT_WORKED}, handle="B"),
        )
        handles = [b["handle"] for b in json.loads(second)["fittings"]]
        assert handles == ["A", "B"]

    def test_unparseable_text_refuses(self):
        assert update_text(
            "{not json", self._wig(), Attestation(claims={"d": VERDICT_WORKED})
        ) is None


class TestMatrix:
    """A sampled checklist attests a lattice, so it binds the lattice.

    The rows still bind their own bytes -- hard rule 1 does not get an
    exemption here -- but a person who walked twelve sampled cells is
    vouching for the set those twelve were drawn from, and the set is
    what cells_hash pins.
    """

    def _matrix(self):
        from custom_components.hair.wig_format import (
            ClimateCell,
            ClimateMatrix,
        )

        return ClimateMatrix(
            min_temp=16.0, max_temp=30.0, off=PRONTO_A,
            modes=["cool", "heat"], fan_modes=["auto"],
            cells=[
                ClimateCell(mode="cool", fan="auto", temp=16.0,
                            pronto=PRONTO_A),
                ClimateCell(mode="cool", fan="auto", temp=30.0,
                            pronto=PRONTO_B),
                ClimateCell(mode="heat", fan="auto", temp=22.0,
                            pronto=PRONTO_C),
            ],
        )

    def _device(self):
        device = IRDevice(name="Bedroom AC", commands=[
            _command("Sleep", PRONTO_C),
        ])
        device.climate_matrix = True
        return device

    def test_the_plan_says_it_is_a_matrix(self):
        plan = build_save_plan(self._device(), matrix=self._matrix())
        assert plan.matrix is True
        assert plan.unit == "C"

    def test_the_checklist_becomes_rows(self):
        plan = build_save_plan(self._device(), matrix=self._matrix())
        modes = {r.mode for r in plan.rows if r.section == "modes"}
        assert modes == {"cool", "heat"}

    def test_the_lattice_leads_and_the_extras_follow(self):
        """A person reads the checklist as the device and the flat
        extras as the leftovers, which is what they are."""
        plan = build_save_plan(self._device(), matrix=self._matrix())
        assert plan.rows[0].section is not None
        assert plan.rows[-1].alias == "Sleep"
        assert plan.rows[-1].section is None

    def test_a_checklist_row_carries_no_command(self):
        """It addresses a CELL. TEST sends by coordinate, so a command
        id here would point at something that is not the row."""
        plan = build_save_plan(self._device(), matrix=self._matrix())
        cells = [r for r in plan.rows if r.section is not None]
        assert cells and all(r.command_id == "" for r in cells)
        assert all(r.mode or r.power for r in cells)

    def test_rows_still_bind_their_own_bytes(self):
        from custom_components.hair.wig_format import row_digest

        plan = build_save_plan(self._device(), matrix=self._matrix())
        row = next(r for r in plan.rows if r.mode == "heat")
        assert row.digest == row_digest(PRONTO_C, 0, False)

    def test_the_plan_reports_the_lattice_hash(self):
        from custom_components.hair.wig_format import cells_content_hash

        matrix = self._matrix()
        plan = build_save_plan(self._device(), matrix=matrix)
        assert plan.cells_hash == cells_content_hash(matrix)

    def test_the_bundle_binds_the_lattice(self):
        from custom_components.hair.wig_format import cells_content_hash

        matrix = self._matrix()
        build = build_wig_from_device(self._device(), matrix)
        digest = signal_row_digest(build.wig.signals[0])
        text, _ = create_text(
            build,
            Attestation(
                claims={digest: VERDICT_WORKED},
                cells_hash=cells_content_hash(matrix),
            ),
        )
        bundle = json.loads(text)["fittings"][0]
        assert bundle["cells_hash"] == cells_content_hash(matrix)
        # Hard rule 6's naming rule: never content_hash.
        assert "content_hash" not in bundle

    def test_the_exported_wig_carries_the_lattice(self):
        """Without this a matrix device exported only its depth-0
        extras and the thousands of cells that ARE the device were
        silently left behind."""
        build = build_wig_from_device(self._device(), self._matrix())
        assert build.wig.climate is not None
        assert len(build.wig.climate.cells) == 3

    def test_a_matrix_with_no_extras_still_exports(self):
        device = IRDevice(name="Bare AC")
        device.climate_matrix = True
        build = build_wig_from_device(device, self._matrix())
        assert build.wig is not None
        assert build.wig.signals == []


class TestLatticeDivergence:
    """A checklist bundle binds cells_hash, which is a SET. So a device
    whose lattice has moved away from the wig's cannot sign the wig's
    checklist: doing so would bind bytes the fitter never tested.
    """

    def _wig_matrix(self):
        from custom_components.hair.wig_format import (
            ClimateCell,
            ClimateMatrix,
        )

        return ClimateMatrix(
            min_temp=16.0, max_temp=30.0, off=PRONTO_A,
            modes=["cool"], fan_modes=["auto"],
            cells=[
                ClimateCell(mode="cool", fan="auto", temp=24.0,
                            pronto=PRONTO_A),
                ClimateCell(mode="cool", fan="auto", temp=25.0,
                            pronto=PRONTO_B),
            ],
        )

    def _source_wig(self):
        return Wig(
            name="AC", wig_id="u-source", signals=[],
            climate=self._wig_matrix(),
        )

    def test_matching_lattices_do_not_diverge(self):
        from custom_components.hair.wig_save import lattice_diff

        assert lattice_diff(self._wig_matrix(), self._wig_matrix()) == []

    def test_a_repaired_cell_reads_as_changed(self):
        from custom_components.hair.wig_save import lattice_diff

        device = self._wig_matrix()
        device.cells[0].pronto = PRONTO_C
        changes = lattice_diff(device, self._wig_matrix())
        assert [(c.kind, c.label) for c in changes] == [("changed", "Cool 24")]

    def test_a_deleted_cell_reads_as_deleted(self):
        """Delete through a porthole row removes the cell, and that is
        ordinary lattice divergence at save -- through the same propose
        gate as a repair."""
        from custom_components.hair.wig_save import lattice_diff

        device = self._wig_matrix()
        device.cells.pop(0)
        changes = lattice_diff(device, self._wig_matrix())
        assert [(c.kind, c.label) for c in changes] == [("deleted", "Cool 24")]

    def test_propose_writes_the_repair_and_marks_it(self):
        from custom_components.hair.wig_fitting import PROVENANCE_KEY
        from custom_components.hair.wig_save import apply_lattice, lattice_diff

        device = self._wig_matrix()
        device.cells[0].pronto = PRONTO_C
        wig = self._source_wig()
        changes = lattice_diff(device, wig.climate)
        assert apply_lattice(wig, device, changes) == 1
        assert wig.climate.cells[0].pronto == PRONTO_C
        assert wig.climate.cells[0].extra[PROVENANCE_KEY]["replaced"] is True

    def test_propose_moves_only_what_was_proposed(self):
        """Copying the device's whole lattice over the wig's would carry
        differences nobody proposed and turn a targeted repair into a
        wholesale overwrite."""
        from custom_components.hair.wig_save import apply_lattice, lattice_diff

        device = self._wig_matrix()
        device.cells[0].pronto = PRONTO_C
        device.cells[1].pronto = PRONTO_C
        wig = self._source_wig()
        only_first = [
            c for c in lattice_diff(device, wig.climate) if c.temp == 24.0
        ]
        apply_lattice(wig, device, only_first)
        assert wig.climate.cells[0].pronto == PRONTO_C
        assert wig.climate.cells[1].pronto == PRONTO_B

    def test_propose_binds_the_new_lattice_hash(self):
        from custom_components.hair.wig_format import cells_content_hash
        from custom_components.hair.wig_save import lattice_diff, update_text

        device = self._wig_matrix()
        device.cells[0].pronto = PRONTO_C
        wig = self._source_wig()
        text = serialize_wig(wig)
        changes = lattice_diff(device, wig.climate)
        new_text, result = update_text(
            text, wig,
            Attestation(claims={"d" * 16: VERDICT_WORKED}),
            device_matrix=device, cell_changes=changes,
        )
        data = json.loads(new_text)
        assert result.cells_proposed == 1
        expected = self._wig_matrix()
        expected.cells[0].pronto = PRONTO_C
        assert data["fittings"][0]["cells_hash"] == cells_content_hash(expected)

    def test_a_proposing_save_re_combs(self):
        from custom_components.hair.wig_save import lattice_diff, update_text

        device = self._wig_matrix()
        device.cells[0].pronto = PRONTO_C
        wig = self._source_wig()
        new_text, _ = update_text(
            serialize_wig(wig), wig, None,
            device_matrix=device,
            cell_changes=lattice_diff(device, wig.climate),
        )
        assert "comb" in json.loads(new_text)

    def test_an_attestation_only_update_leaves_the_receipt_alone(self):
        """Its content did not move, so its receipt is still true."""
        wig = self._source_wig()
        wig.extra["comb"] = {"version": 1, "date": "2026-01-01",
                             "suspects": 3, "counts": {}, "findings": []}
        new_text, _ = update_text(
            serialize_wig(wig), wig,
            Attestation(claims={"d" * 16: VERDICT_WORKED}),
        )
        assert json.loads(new_text)["comb"]["date"] == "2026-01-01"
