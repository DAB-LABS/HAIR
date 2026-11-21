"""Device Settings as cards that open, with one accent.

- Every section is a card: a heading button with the section's name over
  a one-line summary, and its fields under it while open.
- Cards come in one order: Power, Climate sensors, Speed cycle, Pinned
  remotes, then Make a Remote, a card with its button and nothing to
  open.
- The first card a device gets opens with the dialog, and so does one
  holding a validation problem; that card's summary says the problem.
- One accent for every section, Power included, with a dark and a light
  value, from hair-colors.ts through settings-section-styles.ts, and only
  on a card's edges: the open card's outline, its action buttons and the
  focus ring. Inside a card everything is the panel's neutral colours.
  No section keeps a colour of its own.
- Power has one heading: the card's. The Power button tick comes first.

Source pins; the dialog is a Lit element and has no node driver.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

COMPONENT = Path(__file__).parent.parent
SRC = COMPONENT / "frontend" / "src"
LOCALES = SRC / "locales"


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _method(text: str, name: str) -> str:
    body = text[text.index(name):]
    return body[: body.index("\n    }\n")]


DIALOG = "ir-device-settings-dialog.ts"
STYLES = "settings-section-styles.ts"


class TestTheCards:
    def test_every_section_is_a_card_in_one_order(self):
        body = _method(_read(DIALOG), "private _renderBody()")
        order = [
            body.index('"power",\n'),
            body.index('"climate",\n'),
            body.index('"speed_cycle",\n'),
            body.index('"relay",\n'),
            body.index("this._renderConvertSection()"),
            body.index('class="dialog-actions"'),
        ]
        assert order == sorted(order)
        assert body.count("this._renderCard(") == 4
        order_line = (
            'CARD_ORDER: readonly CardKey[] = ["power", "climate", "speed_cycle", "relay"]'
        )
        assert order_line in _read(DIALOG)

    def test_the_heading_is_a_button_that_says_whether_it_is_open(self):
        card = _method(_read(DIALOG), "private _renderCard(")
        assert '<h3 class="card-heading">' in card
        assert 'type="button"' in card
        assert 'aria-expanded=${open ? "true" : "false"}' in card
        assert 'aria-controls="card-body-${key}"' in card
        assert "@click=${() => this._toggleCard(key)}" in card
        assert '<span class="card-title">${title}</span>' in card
        assert '<span class="card-sum">${summary}</span>' in card

    def test_a_closed_card_keeps_its_fields_in_the_dom(self):
        card = _method(_read(DIALOG), "private _renderCard(")
        assert 'id="card-body-${key}" ?hidden=${!open}' in card
        assert "?hidden=${!this._cardShows(key)}" in card

    def test_make_a_remote_is_a_card_with_its_button(self):
        convert = _method(_read(DIALOG), "private _renderConvertSection()")
        assert 'class="card card-action section-convert"' in convert
        assert "card-action-btn" in convert
        assert 'class="card-head"' not in convert and "_toggleCard" not in convert
        assert "@click=${this._requestMakeRemote}" in convert

    def test_the_relay_card_shows_when_it_did_before(self):
        text = _read(DIALOG)
        shows = _method(text, "private _cardShows(")
        assert 'if (key === "relay") return this._showsRelay();' in shows
        assert "return settingsSections(this.device).includes(key);" in shows


class TestWhatOpens:
    def test_the_first_card_and_a_problem_card_open(self):
        first = _method(_read(DIALOG), "firstUpdated(): void {")
        assert "CARD_ORDER.find((key) => this._cardShows(key))" in first
        assert "const problem = this._problemCard();" in first
        assert "[first, problem]" in first

    def test_the_problem_card_follows_the_validation_order(self):
        """_validationError checks the speed count first, then the
        power thresholds; the card follows the same order."""
        text = _read(DIALOG)
        problem = _method(text, "private _problemCard(")
        assert "if (!this._validationError) return null;" in problem
        assert "Number.isNaN(speedStepsForSave(this._speedSteps))" in problem
        validation = _method(text, "private get _validationError()")
        assert validation.index("speedStepsForSave") < validation.index("this._sensorChoice")

    def test_a_problem_card_says_the_problem(self):
        text = _read(DIALOG)
        for name, key in (
            ("private _powerSummary()", '"power"'),
            ("private _speedCycleSummary()", '"speed_cycle"'),
        ):
            summary = _method(text, name)
            assert f"this._problemCard() === {key}" in summary
            assert "this._validationError" in summary

    def test_toggling_never_closes_another_card(self):
        toggle = _method(_read(DIALOG), "private _toggleCard(")
        body = " ".join(toggle.split("{", 1)[1].split())
        assert body == (
            "const open = new Set(this._open); "
            "if (open.has(key)) open.delete(key); "
            "else open.add(key); "
            "this._open = open;"
        )


class TestOneAccent:
    def test_the_values_live_in_hair_colors(self):
        colors = _read("hair-colors.ts")
        assert 'export const SECTION_ACCENT_DARK = "#03a9f4";' in colors
        assert 'export const SECTION_ACCENT_LIGHT = "#0277bd";' in colors

    def test_the_styles_switch_on_the_dark_attribute(self):
        styles = _read(STYLES)
        assert "SECTION_ACCENT_DARK, SECTION_ACCENT_LIGHT" in styles
        assert re.search(
            r":host \{\s*--section-accent: \$\{unsafeCSS\(SECTION_ACCENT_LIGHT\)\};", styles
        )
        assert re.search(
            r":host\(\[dark\]\) \{\s*--section-accent: \$\{unsafeCSS\(SECTION_ACCENT_DARK\)\};",
            styles,
        )
        assert 'this.toggleAttribute("dark", Boolean(this.hass?.themes?.darkMode));' in _read(
            DIALOG
        )

    def test_no_section_keeps_a_colour_of_its_own(self):
        dialog = _read(DIALOG)
        for old in ("#8e3b3b", "#b05050", "#58a6d8", "#888888", "data:image/svg+xml"):
            assert old not in dialog, old
        assert "settingsSectionStyles," in dialog
        styles = _read(STYLES)
        assert not re.findall(r"#[0-9a-fA-F]{3,6}\b", styles)

    def test_one_chevron_for_every_card_and_select(self):
        styles = _read(STYLES)
        assert styles.count("data:image/svg+xml") == 1
        assert re.search(r"\.card-fold,\s*\.select-chevron \{", styles)
        assert "background-color: var(--secondary-text-color);" in styles

    def test_the_rule_is_written_down(self):
        head = _read(STYLES).split("*/", 1)[0]
        assert "THE RULE." in head
        assert "One accent, --section-accent" in head
        assert "and only on the edges of a card" in " ".join(head.split())


def _rules(styles: str) -> dict[str, str]:
    """Each rule's selector and body, comments dropped."""
    styles = re.sub(r"/\*.*?\*/", "", styles, flags=re.S)
    return {
        " ".join(sel.split()): body
        for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", styles)
    }


class TestTheAccentStaysOnTheEdges:
    """Inside a card the colours are the panel's neutral ones; the blue
    is left to the open card's outline, its buttons and the focus ring."""

    EDGES = frozenset({".card.open", ".card-head:focus-visible", ".card-action-btn"})

    def test_only_the_edges_use_the_accent(self):
        rules = _rules(_read(STYLES))
        users = {sel for sel, body in rules.items() if "var(--section-accent)" in body}
        assert users == self.EDGES

    def test_inside_a_card_is_neutral(self):
        rules = _rules(_read(STYLES))
        assert "color: var(--primary-text-color);" in rules[".card-title"]
        borders = rules[
            '.settings-section select, .settings-section input[type="text"], '
            '.settings-section input[type="number"], .settings-section .source-field'
        ]
        assert "border-color: var(--divider-color);" in borders
        assert "accent-color: var(--primary-text-color);" in rules[
            '.settings-section input[type="checkbox"]'
        ]
        assert "var(--secondary-background-color)" in rules[".card"]
        assert "background: var(--section-wash);" in rules[".settings-section .live-readout"]


class TestPowerHasOneHeading:
    def test_no_heading_inside_any_section(self):
        text = _read(DIALOG)
        for name in (
            "private _renderPowerSection()",
            "private _renderClimateSection()",
            "private _renderSpeedCycleSection()",
            "private _renderRelaySection()",
        ):
            assert "<h3" not in _method(text, name), name

    def test_the_tick_comes_before_the_source(self):
        power = _method(_read(DIALOG), "private _renderPowerSection()")
        assert power.index('t("devsettings.power_toggles_label")') < power.index(
            'id="source-label"'
        )

    def test_the_old_heading_keys_are_gone(self):
        for path in SRC.rglob("*.ts"):
            text = path.read_text(encoding="utf-8")
            assert "power_section_label" not in text, path.name
            assert "power_button_label" not in text, path.name


NEW_KEYS = (
    "devsettings.power_title",
    "devsettings.sum_power_none",
    "devsettings.sum_power_watts",
    "devsettings.sum_climate_none",
    "devsettings.sum_speed_count",
    "devsettings.sum_speed_unset",
    "devsettings.sum_speed_off",
)


class TestTheWords:
    def test_english(self):
        en = json.loads((LOCALES / "en.json").read_text(encoding="utf-8"))
        assert en["devsettings.power_title"] == "Power"
        assert en["devsettings.sum_power_none"] == "No source · state from what HAIR sends"
        assert en["devsettings.sum_power_watts"] == "{name} · on above {watts} W"
        assert en["devsettings.sum_climate_none"] == "No room sensors"
        assert en["devsettings.sum_speed_count"] == "Speeds: {count}"
        assert en["devsettings.sum_speed_unset"] == "Number of speeds not set"
        assert en["devsettings.sum_speed_off"] == "Off is a step"

    @pytest.mark.parametrize("path", sorted(LOCALES.glob("*.json")), ids=lambda p: p.stem)
    def test_every_locale(self, path):
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in NEW_KEYS:
            assert data.get(key), key
            assert "—" not in data[key], key
        assert data["devsettings.sum_power_watts"].count("{name}") == 1
        assert data["devsettings.sum_power_watts"].count("{watts}") == 1
        assert data["devsettings.sum_speed_count"].count("{count}") == 1
        assert "devsettings.power_section_label" not in data
        assert "devsettings.power_button_label" not in data

    def test_the_summaries_use_their_keys(self):
        text = _read(DIALOG)
        for key in NEW_KEYS:
            assert f'"{key}"' in text, key
