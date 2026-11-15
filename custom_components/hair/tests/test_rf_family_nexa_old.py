"""Old fixed-code Nexa, KAKU and Intertechno (held off; second round).

A PT2262 word at T = 350 us whose symbols are only 0 and X (F), with
b8 to b10 reading 0 X X, from the elektronikforumet description: house
A to P in b0 to b3, unit 1 to 16 in b4 to b7, X counting as 1 with b0
lowest, and b11 X for on.
"""
from __future__ import annotations

import dataclasses

import pytest

from custom_components.hair import rf_family
from custom_components.hair.rf_family import (
    CERTAINTY_AMBIGUOUS,
    FAMILIES,
    family_of,
    family_payload,
)
from custom_components.hair.tests.test_rf_family import _frame


def _tri(house: str, unit: int, on: bool) -> str:
    def symbols(value: int) -> str:
        return "".join("F" if (value >> i) & 1 else "0" for i in range(4))

    return symbols(ord(house) - ord("A")) + symbols(unit - 1) + "0FF" + ("F" if on else "0")


def _nexa(tri: str, **kw) -> list[int]:
    bits = "".join({"0": "00", "1": "11", "F": "01"}[s] for s in tri)
    kw.setdefault("unit", 350.0)
    kw.setdefault("gap_units", 32.0)
    return _frame(int(bits, 2), **kw)


@pytest.fixture
def only(monkeypatch):
    """Show only the named families for one test."""

    def show(*keys: str) -> None:
        table = {
            key: dataclasses.replace(spec, shown=key in keys)
            for key, spec in FAMILIES.items()
        }
        monkeypatch.setattr(rf_family, "FAMILIES", table)
        rf_family._family_of.cache_clear()

    yield show
    rf_family._family_of.cache_clear()


def _fields(result) -> dict[str, str]:
    return dict(result.fields)


class TestHeldOff:
    def test_it_is_off(self):
        assert FAMILIES["nexa_old"].shown is False

    def test_an_old_nexa_word_reads_as_pt2262_or_ev1527_with_no_nexa(self):
        result = family_of(_nexa(_tri("B", 3, True)))
        assert result.label == "PT2262 or EV1527"
        assert result.certainty == CERTAINTY_AMBIGUOUS
        assert "Nexa" not in result.label
        assert "Proove" not in family_payload(_nexa(_tri("B", 3, True)))["aliases"]

    def test_its_aliases_are_the_ones_its_page_names(self):
        assert FAMILIES["nexa_old"].aliases == ("Proove",)

    def test_include_hidden_names_it(self):
        result = family_of(_nexa(_tri("B", 3, True)), include_hidden=True)
        assert result.label == "PT2262 or EV1527 or Nexa"


def _nexa_fit(frame: list[int]) -> dict[str, str]:
    """Old Nexa's own fields, read from the shape's fit. PT2262 always fits
    beside it, so a label shows the shape's shared fields instead (ruling
    2026-11-15); the decoder's reading is held here."""
    read = rf_family._pt2262_ev1527(tuple(frame))
    fits = {fit.key: dict(fit.fields) for fit in read.fits}
    return fits["nexa_old"]


class TestTheFields:
    @pytest.mark.parametrize("house,unit,on", [
        ("A", 1, False), ("B", 3, True), ("C", 2, True), ("H", 8, False),
        ("I", 9, True), ("M", 13, False), ("P", 16, True),
    ])
    def test_house_unit_and_state(self, house, unit, on):
        assert _nexa_fit(_nexa(_tri(house, unit, on))) == {
            "house": house, "unit": str(unit), "state": "on" if on else "off",
        }

    def test_shown_alone_it_is_ambiguous_with_the_shared_fields(self, only):
        """PT2262 also fits, so even shown alone the label is ambiguous and
        carries the shape's tri-state and code (ruling 2026-11-15)."""
        only("nexa_old")
        tri = _tri("B", 3, True)
        result = family_of(_nexa(tri))
        assert result.label == "Nexa"
        assert result.certainty == CERTAINTY_AMBIGUOUS
        assert [name for name, _ in result.fields] == ["tri-state", "code"]
        assert _fields(result)["tri-state"] == tri

    def test_the_pages_own_table(self):
        """B is X000 and 2 is X000: b0 is the lowest."""
        tri = "F000" + "F000" + "0FF" + "F"
        assert _nexa_fit(_nexa(tri)) == {"house": "B", "unit": "2", "state": "on"}

    @pytest.mark.parametrize("seed", range(10))
    def test_both_receivers(self, seed):
        tri = _tri("D", 5, True)
        assert _nexa_fit(_nexa(tri, mark_widening=60, seed=seed))["house"] == "D"
        frame = _nexa(tri, short_spread=0.3, long_spread=0.1, seed=seed)
        assert _nexa_fit(frame)["unit"] == "5"


class TestRefusals:
    def test_a_1_symbol_is_not_nexa(self, only):
        only("nexa_old")
        tri = _tri("B", 3, True)
        assert family_of(_nexa("1" + tri[1:])) is None

    @pytest.mark.parametrize("middle", ["000", "FFF", "F0F", "0F0"])
    def test_b8_to_b10_must_read_0ff(self, only, middle):
        only("nexa_old")
        tri = _tri("B", 3, True)
        assert family_of(_nexa(tri[:8] + middle + tri[11])) is None

    def test_an_ev1527_code_is_not_nexa(self, only):
        only("nexa_old")
        assert family_of(_frame(0x950E49)) is None
