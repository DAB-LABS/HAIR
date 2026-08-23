"""Combing: do a wig's codes agree with each other? (Smart Perm phase 2)

The contracts under test come from smartir-defects-and-repair.md, and the
two that cost the most to get wrong are pinned first:

- **A whole row sending one code for every temperature is CORRECT.** The
  device ignores temperature in that combination. Daikin does it in 19 rows
  of 40, Sharp in 8 of 12, Samsung across all of heat_cool. Treating those
  as duplicates would have produced 37 false positives against 5 real
  defects on the census sample. Only a PARTIAL collapse is a defect.
- **Strict frame-shape matching is right for a lattice and wrong for a
  flat remote.** Pulse-distance protocols spend one pair per bit, so every
  cell is the same length; bi-phase protocols (RC-5) merge adjacent
  same-level half-bits, so pair count varies with the command's own bits.
  A real twelve-button RC-5 remote runs 10, 11 and 12 pairs and none of it
  is broken.

Everything else follows the taxonomy: malformed frames are silent no-ops,
duplicated neighbours respond with the wrong state (the worst class),
missing cells are dead controls, stray bursts are harmless but reported,
and duplicate labels are ADVISORY forever because a toggle remote
legitimately puts one code under two names.
"""
from __future__ import annotations

import pytest

from custom_components.hair.wig_comb import (
    ADVISORY_CHECKS,
    CHECK_BYPASS_WITH_DITTOS,
    CHECK_COORDINATE_COLLISION,
    CHECK_DUPLICATE_LABELS,
    CHECK_DUPLICATED_NEIGHBOUR,
    CHECK_FRAME_SHAPE,
    CHECK_MALFORMED,
    CHECK_MISSING_CELL,
    CHECK_RAMP_DITTOS,
    CHECK_STRAY_BURST,
    CHECK_STRAY_CELL,
    MAX_STORED_FINDINGS,
    CombReport,
    Finding,
    comb_wig,
)
from custom_components.hair.wig_format import (
    ClimateCell,
    ClimateMatrix,
    Wig,
    WigSignal,
    validate_pronto,
)

# --- fixtures -------------------------------------------------------------


def _code(frames: list[int], seed: int = 0) -> str:
    """A valid Pronto whose frame shape is exactly ``frames``.

    ``seed`` varies the mark value so two codes of the same shape are not
    byte-identical -- otherwise every shape fixture would also trip the
    duplicate checks and the tests would be measuring two things at once.
    """
    pairs: list[tuple[int, int]] = []
    for count in frames:
        for i in range(count):
            space = 0x0500 if i == count - 1 else 0x0020
            pairs.append((0x0020 + seed, space))
    words = [0x0000, 0x006D, len(pairs), 0x0000]
    for mark, space in pairs:
        words += [mark, space]
    return " ".join(f"{w:04X}" for w in words)


def test_fixture_codes_are_valid_pronto():
    """If the fixtures were malformed as Pronto, every result below would
    be measuring the parser rather than the checks."""
    assert validate_pronto(_code([10])).valid
    assert validate_pronto(_code([10, 10], seed=3)).valid


def _pairs_for(pronto: str):
    """Burst pairs of a fixture code, for asserting on the population."""
    from custom_components.hair.wig_comb import _pairs

    return _pairs(pronto)


def _signal_wig(codes: dict[str, str]) -> Wig:
    return Wig(
        name="Remote",
        signals=[WigSignal(alias=a, pronto=p) for a, p in codes.items()],
    )


def _matrix_wig(cells: list[ClimateCell], **kw) -> Wig:
    matrix = ClimateMatrix(
        min_temp=kw.pop("min_temp", 16.0),
        max_temp=kw.pop("max_temp", 30.0),
        precision=kw.pop("precision", 1.0),
        modes=kw.pop("modes", []),
        fan_modes=kw.pop("fan_modes", []),
        swing_modes=kw.pop("swing_modes", []),
        off=kw.pop("off", _code([10], seed=90)),
        on=kw.pop("on", None),
        cells=cells,
    )
    return Wig(name="AC", signals=[], climate=matrix)


def _checks(wig: Wig) -> list[str]:
    return [f.check for f in comb_wig(wig).findings]


# ---------------------------------------------------------------------------
# The false-positive guard the census paid for
# ---------------------------------------------------------------------------


class TestWholeRowCollapse:
    def test_fully_collapsed_row_produces_nothing(self):
        """The 37-false-positives case, pinned. A device that ignores
        temperature in one combination sends one code for the whole row,
        and that is correct and load bearing -- the UI must not offer a
        control that does nothing, and the comb must not call it a bug."""
        one = _code([10], seed=1)
        cells = [
            ClimateCell(mode="cool", fan="auto", temp=float(t), pronto=one)
            for t in range(16, 31)
        ]
        assert comb_wig(_matrix_wig(cells)).findings == []

    def test_partial_collapse_is_the_defect(self):
        """The row proves the device responds to temperature, and then two
        adjacent values collide anyway."""
        cells = [
            ClimateCell(mode="cool", fan="auto", temp=float(t),
                        pronto=_code([10], seed=t))
            for t in range(16, 22)
        ]
        # 19 sends 18's code: set 19, get 18.
        cells[3].pronto = cells[2].pronto
        report = comb_wig(_matrix_wig(cells))
        dupes = [
            f for f in report.findings
            if f.check == CHECK_DUPLICATED_NEIGHBOUR
        ]
        assert len(dupes) == 1
        assert set(dupes[0].keys) == {"cool/auto/19", "cool/auto/18"}
        assert dupes[0].params == {"other": "18", "temp": "19"}

    def test_two_cell_row_is_not_judged(self):
        """Two temperatures sharing a code is as likely to be a two-step
        device as a defect. Not enough row to have an opinion."""
        one = _code([10], seed=2)
        cells = [
            ClimateCell(mode="dry", fan="auto", temp=20.0, pronto=one),
            ClimateCell(mode="dry", fan="auto", temp=21.0, pronto=one),
        ]
        assert CHECK_DUPLICATED_NEIGHBOUR not in _checks(_matrix_wig(cells))

    def test_collapsed_and_varying_rows_coexist(self):
        """Daikin's real shape: some rows ignore temperature, some do not.
        Only the row that contradicts itself is reported."""
        cells = []
        flat = _code([10], seed=5)
        for t in range(16, 22):
            cells.append(ClimateCell(mode="heat", fan="auto",
                                     temp=float(t), pronto=flat))
        for t in range(16, 22):
            cells.append(ClimateCell(mode="cool", fan="auto", temp=float(t),
                                     pronto=_code([10], seed=20 + t)))
        cells[-1].pronto = cells[-2].pronto
        dupes = [f for f in comb_wig(_matrix_wig(cells)).findings
                 if f.check == CHECK_DUPLICATED_NEIGHBOUR]
        assert len(dupes) == 1
        assert "cool/auto/21" in dupes[0].keys


# ---------------------------------------------------------------------------
# Frame shape: strict on a lattice
# ---------------------------------------------------------------------------


class TestFrameShapeMatrix:
    def _cells(self, shapes: dict[float, list[int]]) -> list[ClimateCell]:
        return [
            ClimateCell(mode="cool", fan="auto", temp=t,
                        pronto=_code(s, seed=int(t)))
            for t, s in shapes.items()
        ]

    def test_uniform_lattice_is_clean(self):
        cells = self._cells({float(t): [10] for t in range(16, 22)})
        assert comb_wig(_matrix_wig(cells)).findings == []

    def test_short_frame_is_malformed_with_a_diagnosis(self):
        shapes = {float(t): [10] for t in range(16, 22)}
        shapes[19.0] = [9]
        report = comb_wig(_matrix_wig(self._cells(shapes)))
        bad = [f for f in report.findings if f.check == CHECK_MALFORMED]
        assert len(bad) == 1
        assert bad[0].keys == ["cool/auto/19"]
        # A diagnosis, not an observation (findings Section 5).
        assert bad[0].params == {"frame": "0", "timings": "2"}

    def test_trailing_burst_is_stray_not_malformed(self):
        shapes = {float(t): [10] for t in range(16, 22)}
        shapes[20.0] = [10, 1]
        report = comb_wig(_matrix_wig(self._cells(shapes)))
        assert [f.check for f in report.findings] == [CHECK_STRAY_BURST]
        assert report.findings[0].keys == ["cool/auto/20"]

    def test_missing_repeat_frame_is_malformed(self):
        shapes = {float(t): [10, 10] for t in range(16, 22)}
        shapes[18.0] = [10]
        # The off code joins the shape population, so it has to be the
        # same two-frame shape or it is (correctly) reported as well.
        wig = _matrix_wig(self._cells(shapes), off=_code([10, 10], seed=90))
        bad = [f for f in comb_wig(wig).findings
               if f.check == CHECK_MALFORMED]
        assert len(bad) == 1
        assert bad[0].keys == ["cool/auto/18"]
        assert bad[0].params == {"missing": "1"}

    def test_power_codes_join_the_shape_check(self):
        cells = self._cells({float(t): [10] for t in range(16, 22)})
        wig = _matrix_wig(cells, off=_code([4], seed=77))
        keys = [f.keys[0] for f in comb_wig(wig).findings]
        assert "off" in keys


# ---------------------------------------------------------------------------
# Frame shape: loose on a flat remote
# ---------------------------------------------------------------------------


class TestFrameShapeFlat:
    def test_bi_phase_spread_is_not_flagged(self):
        """A real RC-5 remote: 10, 11 and 12 pairs, all correct. Strict
        modal matching would condemn five of these."""
        wig = _signal_wig({
            "On": _code([12], seed=1), "Off": _code([11], seed=2),
            "Candle": _code([11], seed=3), "Solid": _code([11], seed=4),
            "8 Hour": _code([11], seed=5), "6 Hour": _code([12], seed=6),
            "4 Hour": _code([12], seed=7), "Brighten": _code([11], seed=8),
            "Dim": _code([10], seed=9), "Fade": _code([11], seed=10),
            "2 Hour": _code([12], seed=11), "Flicker": _code([12], seed=12),
        })
        assert comb_wig(wig).findings == []

    def test_foreign_protocol_is_a_gross_outlier(self):
        """The same remote with one code from a different protocol
        family: three times the median length."""
        wig = _signal_wig({
            "On": _code([12], seed=1), "Off": _code([11], seed=2),
            "Candle": _code([11], seed=3), "Solid": _code([11], seed=4),
            "8 Hour": _code([34], seed=5), "6 Hour": _code([12], seed=6),
            "4 Hour": _code([12], seed=7), "Brighten": _code([11], seed=8),
            "Dim": _code([10], seed=9), "Fade": _code([11], seed=10),
            "2 Hour": _code([12], seed=11), "Flicker": _code([12], seed=12),
        })
        report = comb_wig(wig)
        assert [f.check for f in report.findings] == [CHECK_FRAME_SHAPE]
        assert report.findings[0].keys == ["8 Hour"]
        assert report.findings[0].params["pairs"] == "34"

    def test_a_much_shorter_code_is_also_an_outlier(self):
        wig = _signal_wig({
            f"K{i}": _code([12], seed=i) for i in range(6)
        } | {"Stub": _code([3], seed=99)})
        keys = [f.keys[0] for f in comb_wig(wig).findings
                if f.check == CHECK_FRAME_SHAPE]
        assert keys == ["Stub"]

    def test_too_few_codes_to_have_a_normal(self):
        wig = _signal_wig({
            "A": _code([10], seed=1), "B": _code([30], seed=2),
        })
        assert comb_wig(wig).findings == []


# ---------------------------------------------------------------------------
# Completeness and coordinates
# ---------------------------------------------------------------------------


class TestCompleteness:
    def test_hole_in_a_temperature_run(self):
        """Sharp's real defect: auto/auto runs 18, 19, 21, 22. Home
        Assistant offers the 20 and nothing happens."""
        cells = [
            ClimateCell(mode="auto", fan="auto", temp=float(t),
                        pronto=_code([10], seed=t))
            for t in (18, 19, 21, 22)
        ]
        report = comb_wig(_matrix_wig(cells))
        holes = [f for f in report.findings if f.check == CHECK_MISSING_CELL]
        assert len(holes) == 1
        assert holes[0].params == {"branch": "auto/auto", "temps": "20"}
        assert holes[0].keys == ["auto/auto/20"]

    def test_sparse_branches_do_not_invent_holes(self):
        """Matrices are sparse by construction: depth varies per branch
        and the census found 158 explicit nulls. Only a gap inside a run
        somebody captured is a hole."""
        cells = [
            ClimateCell(mode="cool", fan="auto", temp=float(t),
                        pronto=_code([10], seed=t))
            for t in (18, 19, 20)
        ] + [
            ClimateCell(mode="dry", fan="auto", pronto=_code([10], seed=60)),
            ClimateCell(mode="fan_only", fan="low",
                        pronto=_code([10], seed=61)),
        ]
        assert CHECK_MISSING_CELL not in _checks(_matrix_wig(cells))

    def test_half_degree_precision_does_not_invent_holes(self):
        cells = [
            ClimateCell(mode="cool", fan="auto", temp=t,
                        pronto=_code([10], seed=int(t * 2)))
            for t in (20.0, 20.5, 21.0, 21.5)
        ]
        wig = _matrix_wig(cells, precision=0.5)
        assert CHECK_MISSING_CELL not in _checks(wig)

    def test_undeclared_vocabulary_is_a_stray(self):
        cells = [
            ClimateCell(mode="cool", fan="auto", temp=float(t),
                        pronto=_code([10], seed=t))
            for t in (18, 19, 20)
        ] + [ClimateCell(mode="turbo", fan="auto", temp=20.0,
                         pronto=_code([10], seed=70))]
        report = comb_wig(_matrix_wig(cells, modes=["cool"]))
        stray = [f for f in report.findings if f.check == CHECK_STRAY_CELL]
        assert len(stray) == 1 and stray[0].keys == ["turbo"]

    def test_empty_vocabulary_means_unstated_not_forbidden(self):
        cells = [
            ClimateCell(mode="cool", fan="auto", temp=float(t),
                        pronto=_code([10], seed=t))
            for t in (18, 19, 20)
        ]
        assert CHECK_STRAY_CELL not in _checks(_matrix_wig(cells, modes=[]))

    def test_coordinate_collision(self):
        cells = [
            ClimateCell(mode="cool", fan="auto", temp=float(t),
                        pronto=_code([10], seed=t))
            for t in (18, 19, 20)
        ] + [ClimateCell(mode="cool", fan="auto", temp=19.0,
                         pronto=_code([10], seed=80))]
        report = comb_wig(_matrix_wig(cells))
        hits = [f for f in report.findings
                if f.check == CHECK_COORDINATE_COLLISION]
        assert len(hits) == 1
        assert hits[0].keys == ["cool/auto/19"]
        assert hits[0].params == {"count": "2"}


# ---------------------------------------------------------------------------
# Advisories
# ---------------------------------------------------------------------------


class TestDuplicateLabels:
    def test_toggle_remote_is_advisory_not_suspect(self):
        """Power On and Power Off sharing one toggle code is correct.
        Reported so a human can look; never counted, never merged."""
        toggle = _code([11], seed=1)
        wig = _signal_wig({
            "Power On": toggle, "Power Off": toggle,
            "Volume Up": _code([11], seed=2),
            "Volume Down": _code([11], seed=3),
            "Mute": _code([11], seed=4),
        })
        report = comb_wig(wig)
        assert [f.check for f in report.findings] == [CHECK_DUPLICATE_LABELS]
        assert report.findings[0].advisory
        # The chip stays dark: an advisory is not a suspect.
        assert report.suspects == 0

    def test_identical_aliases_are_not_a_group(self):
        same = _code([11], seed=1)
        wig = _signal_wig({"A": same, "B": _code([11], seed=2)})
        wig.signals.append(WigSignal(alias="A", pronto=same))
        assert CHECK_DUPLICATE_LABELS not in _checks(wig)

    def test_matrix_wigs_do_not_run_the_label_check(self):
        """A lattice has coordinates, not labels; its duplicate story is
        the partial-collapse check."""
        one = _code([10], seed=1)
        cells = [
            ClimateCell(mode="cool", fan="auto", temp=float(t), pronto=one)
            for t in range(16, 22)
        ]
        assert CHECK_DUPLICATE_LABELS not in _checks(_matrix_wig(cells))


# ---------------------------------------------------------------------------
# The report and its receipt
# ---------------------------------------------------------------------------


class TestReport:
    def test_severity_order_worst_first(self):
        report = CombReport(findings=[
            Finding(check=CHECK_STRAY_BURST, keys=["c"], message="x"),
            Finding(check=CHECK_DUPLICATED_NEIGHBOUR, keys=["a"], message="x"),
            Finding(check=CHECK_MALFORMED, keys=["b"], message="x"),
        ])
        assert list(report.counts()) == [
            CHECK_DUPLICATED_NEIGHBOUR, CHECK_MALFORMED, CHECK_STRAY_BURST,
        ]

    def test_findings_sort_worst_first(self):
        shapes = {float(t): [10] for t in range(16, 24)}
        shapes[20.0] = [10, 1]   # stray burst
        shapes[21.0] = [9]       # malformed
        cells = [
            ClimateCell(mode="cool", fan="auto", temp=t,
                        pronto=_code(s, seed=int(t)))
            for t, s in shapes.items()
        ]
        cells[2].pronto = cells[1].pronto  # duplicated neighbour
        checks = _checks(_matrix_wig(cells))
        assert checks[0] == CHECK_DUPLICATED_NEIGHBOUR
        assert checks.index(CHECK_MALFORMED) < checks.index(CHECK_STRAY_BURST)

    def test_receipt_shape(self):
        shapes = {float(t): [10] for t in range(16, 22)}
        shapes[19.0] = [9]
        cells = [
            ClimateCell(mode="cool", fan="auto", temp=t,
                        pronto=_code(s, seed=int(t)))
            for t, s in shapes.items()
        ]
        receipt = comb_wig(_matrix_wig(cells)).to_receipt("2026-07-31")
        assert receipt["version"] == 2
        assert receipt["date"] == "2026-07-31"
        assert receipt["suspects"] == 1
        assert receipt["counts"] == {CHECK_MALFORMED: 1}
        assert receipt["findings"][0]["check"] == CHECK_MALFORMED
        assert receipt["findings"][0]["keys"] == ["cool/auto/19"]
        assert "truncated" not in receipt

    def test_receipt_truncates_but_the_count_stays_exact(self):
        """A 2,689-cell Mitsubishi with 91 duplicate groups must not
        write a novel into the wig file."""
        many = CombReport(findings=[
            Finding(check=CHECK_MALFORMED, keys=[f"k{i}"], message="x")
            for i in range(MAX_STORED_FINDINGS + 25)
        ])
        receipt = many.to_receipt("2026-07-31")
        assert len(receipt["findings"]) == MAX_STORED_FINDINGS
        assert receipt["truncated"] == 25
        assert receipt["suspects"] == MAX_STORED_FINDINGS + 25
        assert receipt["counts"][CHECK_MALFORMED] == MAX_STORED_FINDINGS + 25

    def test_messages_are_keys_not_prebaked_english(self):
        shapes = {float(t): [10] for t in range(16, 22)}
        shapes[19.0] = [9]
        cells = [
            ClimateCell(mode="cool", fan="auto", temp=t,
                        pronto=_code(s, seed=int(t)))
            for t, s in shapes.items()
        ]
        for finding in comb_wig(_matrix_wig(cells)).findings:
            assert finding.message.startswith("comb.")
            assert " " not in finding.message

    def test_unparseable_code_does_not_abort_the_wig(self):
        wig = _signal_wig({
            "A": _code([12], seed=1), "B": _code([12], seed=2),
            "C": _code([12], seed=3), "D": _code([12], seed=4),
        })
        wig.signals.append(WigSignal(alias="Broken", pronto="not hex"))
        comb_wig(wig)  # must not raise

    @pytest.mark.parametrize("wig", [
        Wig(name="Empty", signals=[]),
        Wig(name="One", signals=[WigSignal(alias="A", pronto=_code([10]))]),
    ])
    def test_degenerate_wigs_are_clean(self, wig):
        assert comb_wig(wig).findings == []


# ---------------------------------------------------------------------------
# The comb does not judge a deliberate repeat-train
# ---------------------------------------------------------------------------


class TestBypassIsSkipped:
    """A bypassed signal is a repeat-train BY DEFINITION (Highlights,
    GH #78), which is exactly the profile the outlier check exists to
    flag. Ship the pin without this and kno-te's wig lands in the closet
    with a red glow claiming its Power code is broken, when it is the
    one code on that remote that is right.

    Skipping means BOTH halves: the row is not judged, and it does not
    vote on what normal looks like. Judging-only would leave a
    seven-frame code in the population deciding the median for a remote
    whose every other button is one frame.
    """

    def _dreo(self, bypass: bool) -> Wig:
        """kno-te's remote in miniature: eleven ordinary buttons and one
        Power code that is the same frame sent seven times."""
        wig = _signal_wig({
            f"Button {i}": _code([11], seed=i) for i in range(11)
        })
        wig.signals.append(WigSignal(
            alias="Power", pronto=_code([11] * 7, seed=40),
            bypass_protocol=bypass,
        ))
        return wig

    def test_unpinned_the_repeat_train_is_flagged(self):
        """The behaviour the pin exists to suppress: without it the comb
        is right to complain, because an unannounced seven-frame code
        among single-frame siblings really is suspicious."""
        report = comb_wig(self._dreo(bypass=False))
        assert [f.keys[0] for f in report.findings] == ["Power"]
        assert report.findings[0].check == CHECK_FRAME_SHAPE

    def test_pinned_it_is_silent(self):
        report = comb_wig(self._dreo(bypass=True))
        assert report.findings == []
        assert report.suspects == 0

    def test_the_skip_is_recorded_not_silent(self):
        """"Nothing wrong with this row" and "nobody looked at this row"
        are different claims, the same distinction the receipt already
        draws between clean and absent."""
        report = comb_wig(self._dreo(bypass=True))
        assert report.skipped == ["Power"]
        receipt = report.to_receipt("2026-08-01")
        assert receipt["skipped"] == ["Power"]

    def test_a_clean_wig_records_no_skips(self):
        wig = _signal_wig({
            f"K{i}": _code([11], seed=i) for i in range(6)
        })
        report = comb_wig(wig)
        assert report.skipped == []
        assert "skipped" not in report.to_receipt("2026-08-01")

    def test_the_pinned_row_does_not_drag_the_population(self):
        """THE half that is easy to get wrong. With the seven-frame code
        still voting, the median moves far enough that the eleven honest
        single-frame buttons start looking short: one false positive
        silenced, several manufactured."""
        wig = self._dreo(bypass=True)
        report = comb_wig(wig)
        assert report.findings == []

        # And the same wig with the pin removed from the population only
        # (judgement suppressed, vote kept) would be a different answer.
        shapes = [
            len(_pairs_for(sig.pronto))
            for sig in wig.signals if not sig.bypass_protocol
        ]
        assert len(set(shapes)) == 1, "the honest buttons agree"

    def test_two_pinned_rows_both_skip(self):
        wig = self._dreo(bypass=True)
        wig.signals[0].bypass_protocol = True
        report = comb_wig(wig)
        assert report.skipped == ["Button 0", "Power"]
        assert report.findings == []

    def test_a_pinned_row_is_never_a_suspect_for_the_fitting(self):
        """It reaches the fitting as an ordinary checklist row instead,
        which is the point: it is a real button on a real remote and it
        has to be proved like any other."""
        from custom_components.hair.wig_comb import stamp_receipt, suspect_keys

        wig = self._dreo(bypass=False)
        stamp_receipt(wig, comb_wig(wig), "2026-08-01")
        assert suspect_keys(wig) == ["Power"]

        # Now pin it: the finding stops being raised at all, and even a
        # stale receipt naming it stops surfacing it.
        wig.signals[-1].bypass_protocol = True
        assert suspect_keys(wig) == []

    def test_matrix_cells_are_unaffected(self):
        """Ruling 1: cells have no pin, so nothing about a matrix wig's
        comb changes."""
        cells = [
            ClimateCell(mode="cool", fan="auto", temp=float(t),
                        pronto=_code([10], seed=t))
            for t in range(16, 22)
        ]
        wig = _matrix_wig(cells)
        report = comb_wig(wig)
        assert report.findings == []
        assert report.skipped == []


class TestRecipeAdvisories:
    """Two things the recipe can encode that deserve a look rather than
    a verdict. Both advisory forever."""

    def _wig(self, **kw):
        from custom_components.hair.wig_format import Wig, WigSignal

        return Wig(name="R", signals=[WigSignal(**kw)])

    def test_bypass_with_dittos_fires(self):
        """HAIR's exporter can never write this pair, so seeing it means
        a human hand-edited the file."""
        report = comb_wig(self._wig(
            alias="Power", pronto=_code([10]),
            bypass_protocol=True, ditto_count=3,
        ))
        checks = {f.check for f in report.findings}
        assert CHECK_BYPASS_WITH_DITTOS in checks

    def test_bypass_alone_is_silent(self):
        report = comb_wig(self._wig(
            alias="Power", pronto=_code([10]), bypass_protocol=True,
        ))
        checks = {f.check for f in report.findings}
        assert CHECK_BYPASS_WITH_DITTOS not in checks

    def test_a_high_ditto_on_a_ramp_button_fires(self):
        report = comb_wig(self._wig(
            alias="Volume Up", pronto=_code([10]), ditto_count=8,
        ))
        checks = {f.check for f in report.findings}
        assert CHECK_RAMP_DITTOS in checks

    def test_a_high_ditto_on_a_plain_button_is_silent(self):
        """The NAD case: 8 dittos on Power is device grammar, and the
        comb must not second-guess it."""
        report = comb_wig(self._wig(
            alias="Power", pronto=_code([10]), ditto_count=8,
        ))
        checks = {f.check for f in report.findings}
        assert CHECK_RAMP_DITTOS not in checks

    def test_a_modest_ditto_on_a_ramp_button_is_silent(self):
        report = comb_wig(self._wig(
            alias="Volume Up", pronto=_code([10]), ditto_count=2,
        ))
        checks = {f.check for f in report.findings}
        assert CHECK_RAMP_DITTOS not in checks

    def test_both_stay_out_of_the_suspect_population(self):
        """Advisories never count and never light the closet chip."""
        report = comb_wig(self._wig(
            alias="Volume Up", pronto=_code([10]),
            bypass_protocol=True, ditto_count=8,
        ))
        assert CHECK_BYPASS_WITH_DITTOS in ADVISORY_CHECKS
        assert CHECK_RAMP_DITTOS in ADVISORY_CHECKS
        # Both fired, and neither is a suspect.
        assert {f.check for f in report.findings} == {
            CHECK_BYPASS_WITH_DITTOS, CHECK_RAMP_DITTOS,
        }
        assert all(f.check in ADVISORY_CHECKS for f in report.findings)
