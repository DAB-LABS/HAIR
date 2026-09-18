"""Every adapter fixture, and the format it sniffs as.

THE PIN ON THE SNIFFER. Import phase 1 replaces the if-chain in
``sniff_format`` with a probe registry, and the one thing that must not
move while it does is the answer for a file already in the repo. So the
table below is committed, every fixture is walked against it, and a
fixture with no row fails rather than passing quietly.

The table covers all five formats the tree had before this work plus
the two this patch adds, which is what makes it a pin rather than a
sample: the review found the old fixture set had no complete
``smartir_climate`` file at all, so the rank-40 probe -- the one the
fork work moves around -- was unpinned.

A row whose answer is ``None`` is a useful row and stays: the truncated
climate header is a real file that really does sniff as nothing,
because it is not valid JSON.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from custom_components.hair.wig_adapters import (
    FormatProbe,
    sniff,
    sniff_format,
)

FIXTURES = Path(__file__).parent / "fixtures" / "adapters"

#: file name -> the format it must sniff as. Exhaustive by construction:
#: the walk below fails on any fixture missing from it.
CENSUS: dict[str, str | None] = {
    # Flipper, both shapes plus the library file this patch refuses.
    "flipper_parsed_Apple_TV_Gen3_v2.ir": "flipper",
    "flipper_raw_mitsubishi-MSY-GE10VA.ir": "flipper",
    "flipper_library_tv.ir": "flipper_library",
    # Girr.
    "girr_commandset_root_sony.girr": "girr",
    "girr_irscrutinizer_export.girr": "girr",
    "girr_parameters_only_apple.girr": "girr",
    # LIRC: raw codes, space-encoded, and the two Manchester families
    # this patch teaches the reader.
    "lirc_raw_codes_lg_ac_lgirplus.conf.excerpt": "lirc",
    "lirc_space_enc_pre_data_futarque.lircd.conf": "lirc",
    "lirc_space_enc_sony_rm-w101.lircd.conf": "lirc",
    "lirc_rc5_shift_enc.lircd.conf": "lirc",
    "lirc_rc6_mode0.lircd.conf": "lirc",
    "lirc_rc6_mode0_address0.lircd.conf": "lirc",
    "lirc_rc6_mode6a.lircd.conf": "lirc",
    "lirc_four_remotes.lircd.conf": "lirc",
    # SmartIR: the generic shape, a complete climate file, a climate
    # file carrying the extra preset level, and a light file.
    "smartir_fan_1220.json": "smartir",
    "smartir_media_player_1000.json": "smartir",
    "smartir_light_brightness.json": "smartir",
    "smartir_climate_swing.json": "smartir_climate",
    "smartir_fork_climate_presets.json": "smartir_fork_climate",
    # Truncated on purpose: not valid JSON, so nothing claims it.
    "smartir_climate_1000_HEADER_ONLY.json.partial": None,
}


def _fixtures() -> list[Path]:
    return sorted(p for p in FIXTURES.iterdir() if p.is_file())


class TestCensus:
    def test_every_fixture_has_a_row(self):
        walked = {p.name for p in _fixtures()}
        missing = sorted(walked - set(CENSUS))
        assert not missing, (
            "these fixtures have no census row; add them to CENSUS with "
            f"the format they sniff as: {missing}"
        )

    def test_no_row_names_a_fixture_that_is_gone(self):
        walked = {p.name for p in _fixtures()}
        stale = sorted(set(CENSUS) - walked)
        assert not stale, f"CENSUS names fixtures that no longer exist: {stale}"

    @pytest.mark.parametrize("name", sorted(CENSUS))
    def test_fixture_sniffs_as_the_committed_format(self, name):
        text = (FIXTURES / name).read_text(errors="replace")
        assert sniff_format(text) == CENSUS[name]

    def test_every_registered_probe_is_pinned_by_a_fixture(self):
        """THE PIN ON THE PROBES, not only on the files.

        The walk above checks each fixture against its committed
        answer, which says nothing about a probe no fixture reaches. A
        probe nothing pins is a probe nothing tested: one shipped that
        way and refused stock light files, because the only file in the
        repo that could have caught it was missing three commands.

        A new probe therefore needs a fixture it fires on, in the table
        above, before it can ship.
        """
        from custom_components.hair.wig_adapters import _PROBES

        registered = {probe.name for probe in _PROBES}
        pinned = {value for value in CENSUS.values() if value}
        unpinned = sorted(registered - pinned)
        assert not unpinned, (
            "these probes are registered but no fixture pins them; add a "
            f"fixture each probe fires on and a CENSUS row for it: {unpinned}"
        )

    def test_no_census_row_names_a_format_nothing_produces(self):
        """The other direction: a row whose answer no probe can give."""
        from custom_components.hair.wig_adapters import _PROBES

        registered = {probe.name for probe in _PROBES}
        claimed = {value for value in CENSUS.values() if value}
        assert claimed <= registered, sorted(claimed - registered)

    def test_all_five_formats_that_predate_this_patch_are_covered(self):
        """The pin the plan asks for, stated as a set.

        Four of the five were covered before; ``smartir_climate`` was
        not, because the only climate fixture in the tree is truncated.
        """
        covered = set(CENSUS.values())
        assert {"flipper", "girr", "lirc", "smartir", "smartir_climate"} <= (
            covered
        )


class TestThePinCanFail:
    """A pin that cannot fail is decoration.

    The probe assertion above passes today, so this plants the exact
    shape it exists to catch -- a registered probe no fixture reaches
    -- and asserts it fails.
    """

    def test_an_unpinned_probe_fails_the_census(self, monkeypatch):
        from custom_components.hair import wig_adapters

        monkeypatch.setattr(
            wig_adapters,
            "_PROBES",
            (
                *wig_adapters._PROBES,
                FormatProbe("unpinned_format", 5, lambda text, parsed: False),
            ),
        )
        with pytest.raises(AssertionError) as raised:
            TestCensus().test_every_registered_probe_is_pinned_by_a_fixture()
        assert "unpinned_format" in str(raised.value)


class TestHintAndTies:
    """The tie machinery, which no shipped pair can reach.

    Every rank in the registry is distinct, so exactly one probe always
    holds the top matched rank and the refusal below cannot fire on any
    file. It is here for phase 2, which adds formats identified by
    punctuation rather than by a header word, and these tests reach it
    the only way it can be reached: by registering a second probe at a
    rank another one already holds.
    """

    def _with_probe(self, monkeypatch, probe: FormatProbe):
        from custom_components.hair import wig_adapters

        monkeypatch.setattr(
            wig_adapters, "_PROBES", (*wig_adapters._PROBES, probe)
        )

    def test_no_shipped_pair_can_tie(self):
        from custom_components.hair.wig_adapters import _PROBES

        ranks = [p.rank for p in _PROBES]
        assert len(ranks) == len(set(ranks))

    def test_a_tie_no_hint_can_settle_is_refused_and_names_both(
        self, monkeypatch
    ):
        self._with_probe(
            monkeypatch, FormatProbe("pretend", 10, lambda text, parsed: True)
        )
        # ``.txt`` names no format, so nothing can break the tie.
        result = sniff("begin remote\n  name  x\nend remote\n", "notes.txt")
        assert result.format is None
        assert set(result.candidates) == {"lirc", "pretend"}
        assert "will not guess" in (result.reason or "")

    def test_a_hint_breaks_a_tie_it_names(self, monkeypatch):
        self._with_probe(
            monkeypatch, FormatProbe("pretend", 10, lambda text, parsed: True)
        )
        text = "begin remote\n  name  x\nend remote\n"
        assert sniff(text, "notes.txt").format is None
        # ``.conf`` names lirc and only lirc, so the tie resolves to it.
        resolved = sniff(text, "remote.conf")
        assert resolved.format == "lirc"
        assert "by the filename extension" in (resolved.reason or "")
        assert set(resolved.candidates) == {"lirc", "pretend"}

    def test_a_hint_cannot_veto_the_only_match(self, monkeypatch):
        """A hint chooses between tied candidates and does nothing else."""
        text = "begin remote\n  name  x\nend remote\n"
        assert sniff(text, "remote.ir").format == "lirc"

    def test_a_hint_naming_no_matched_format_changes_nothing(self):
        """Content wins (GH #108). A hint can choose, never add."""
        text = "begin remote\n  name  x\nend remote\n"
        assert sniff(text, "x.json").format == "lirc"
        assert sniff("not a format at all", "x.ir").format is None
