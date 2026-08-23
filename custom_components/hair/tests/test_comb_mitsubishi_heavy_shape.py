"""The family the 2.6 ms floor cannot protect (R1 follow-up).

Mitsubishi Heavy encodes a logical ONE as a space of roughly 3600 us and
separates two presses by roughly 7600 us. Both facts are ordinary on
their own and together they defeat both halves of the separator search:

- the one-bit is 3.6 ms, so it clears the absolute floor that keeps a
  Fujitsu bit space from being mistaken for a frame gap, and
- the real gap is only about 2.1 times the one-bit, so it fails the
  ratio test that keeps a boundary distinct from the data below it.

Which way it fails depends on the payload. A code with FEW one-bits
leaves the long spaces rare enough to pass the quarter guard, so the
search takes the zero-to-one step and cuts the frame at every one-bit,
producing debris that then disagrees with itself. A code with MANY
one-bits fails the quarter guard, and the real gap fails the ratio, so
nothing is found at all -- including in a capture that plainly holds
three presses.

Neither may produce a finding. Where the search cannot trust a
separator the honest answer is a coverage line, and that is what these
tests pin. Timings are synthesized from the family's documented shape
(`field-map-derivation-report-2.md` section 5, and the census row that
puts the 152-bit Mitsubishi Heavy family at a 3270/1640 leader) rather
than taken from any file, so nothing here depends on a corpus.
"""
from __future__ import annotations

import random

from custom_components.hair.wig_comb import (
    CHECK_FRAME_DISAGREEMENT,
    DECLINE_SEPARATOR_UNCLEAR,
    DECLINE_SINGLE_FRAME,
    comb_wig,
    frame_disagreement,
)
from custom_components.hair.wig_format import Wig, WigSignal

# One Pronto unit at the 38 kHz carrier the family transmits on.
US_PER_UNIT = 1_000_000 / 38000.0

LEADER_MARK_US = 3270
LEADER_SPACE_US = 3600  # the worst case: indistinguishable from a one
BIT_MARK_US = 400
ZERO_SPACE_US = 800
ONE_SPACE_US = 3600
FRAME_GAP_US = 7600
TRAILER_US = 20000


def _units(microseconds: float) -> int:
    return max(1, round(microseconds / US_PER_UNIT))


def _mitsubishi_heavy(bits: str, presses: int = 1) -> str:
    """A Mitsubishi-Heavy-shaped capture: leader, 152 bits, per press."""
    pairs: list[tuple[int, int]] = []
    for press in range(presses):
        pairs.append((_units(LEADER_MARK_US), _units(LEADER_SPACE_US)))
        for index, bit in enumerate(bits):
            if index == len(bits) - 1:
                closing = FRAME_GAP_US if press < presses - 1 else TRAILER_US
            else:
                closing = ONE_SPACE_US if bit == "1" else ZERO_SPACE_US
            pairs.append((_units(BIT_MARK_US), _units(closing)))
    words = [0x0000, 0x006D, len(pairs), 0x0000]
    for mark, space in pairs:
        words += [mark, space]
    return " ".join(f"{w:04X}" for w in words)


def _payload(ones: int, seed: int = 3, width: int = 152) -> str:
    """A 152-bit payload carrying ``ones`` one-bits, scattered."""
    chosen = set(random.Random(seed).sample(range(width), ones))
    return "".join("1" if i in chosen else "0" for i in range(width))


SPARSE = _payload(ones=12)
DENSE = _payload(ones=76)


def _wig(codes: dict[str, str]) -> Wig:
    return Wig(
        name="Mitsubishi Heavy",
        signals=[
            WigSignal(alias=alias, pronto=code)
            for alias, code in codes.items()
        ],
    )


def _declined(wig: Wig) -> dict[str, int]:
    coverage = comb_wig(wig).coverage.to_dict()
    return coverage["checks"][CHECK_FRAME_DISAGREEMENT]["declined"]


class TestSparseOnes:
    """Few one-bits: the quarter guard passes and the zero-to-one step
    looks exactly like a separator. It is not one."""

    def test_one_press_produces_no_finding(self):
        assert frame_disagreement(_mitsubishi_heavy(SPARSE)) is None

    def test_three_presses_produce_no_finding(self):
        assert frame_disagreement(_mitsubishi_heavy(SPARSE, 3)) is None

    def test_it_declines_rather_than_guessing(self):
        """The search found something shaped like a boundary, cut on it,
        and got fragments instead of repeats. Saying so is the point: the
        code was not checked, and the receipt has to carry that."""
        assert _declined(_wig({"Cool 24": _mitsubishi_heavy(SPARSE)})) == {
            DECLINE_SEPARATOR_UNCLEAR: 1,
        }

    def test_a_whole_clean_lattice_stays_silent(self):
        wig = _wig({
            f"Cool {temp}": _mitsubishi_heavy(_payload(12, seed=temp))
            for temp in range(18, 31)
        })
        assert comb_wig(wig).findings == []


class TestDenseOnes:
    """Many one-bits: the long spaces are too common to be boundaries, and
    the real gap is only 2.1 times the one-bit, so nothing is found."""

    def test_one_press_produces_no_finding(self):
        assert frame_disagreement(_mitsubishi_heavy(DENSE)) is None

    def test_three_presses_produce_no_finding(self):
        assert frame_disagreement(_mitsubishi_heavy(DENSE, 3)) is None

    def test_it_declines_with_a_reason(self):
        """Either reason is honest here and the wording of both says the
        same thing to a reader: nothing was compared. What must never
        happen is a finding, or a coverage line claiming a check ran."""
        declined = _declined(_wig({"Cool 24": _mitsubishi_heavy(DENSE, 3)}))
        assert sum(declined.values()) == 1
        assert set(declined) <= {
            DECLINE_SINGLE_FRAME, DECLINE_SEPARATOR_UNCLEAR,
        }

    def test_a_whole_clean_lattice_stays_silent(self):
        wig = _wig({
            f"Heat {temp}": _mitsubishi_heavy(_payload(76, seed=temp))
            for temp in range(18, 31)
        })
        assert comb_wig(wig).findings == []


class TestTheDensitySweep:
    """The failure moves with the payload, so the pin has to as well.

    One-bit counts from very sparse to very dense, single and multi
    press, each with its own scattering. Not one of them may produce a
    finding, and not one of them may be counted as checked.
    """

    def test_no_density_produces_a_finding(self):
        for ones in range(4, 80, 4):
            for presses in (1, 2, 3):
                for seed in (1, 2, 3):
                    code = _mitsubishi_heavy(
                        _payload(ones, seed=seed), presses)
                    vote = frame_disagreement(code)
                    assert vote is None, (ones, presses, seed, vote)

    def test_no_density_is_counted_as_checked(self):
        for ones in range(4, 80, 4):
            for presses in (1, 2, 3):
                wig = _wig({
                    "Cool 24": _mitsubishi_heavy(_payload(ones), presses),
                })
                coverage = comb_wig(wig).coverage.to_dict()
                repeats = coverage["checks"][CHECK_FRAME_DISAGREEMENT]
                assert repeats["checked"] == 0, (ones, presses)
                assert sum(repeats["declined"].values()) == 1
