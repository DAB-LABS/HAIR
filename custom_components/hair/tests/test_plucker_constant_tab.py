"""Source guards for the constant Plucker tab.

The tab used to hide when nothing could be plucked right now, and hid
hardest from the people it was built for. Twice: the 0.10.3 gate was
vendors-only, the fix made it vendors-or-stores, and both asked "is
there anything to pluck this second" of a surface whose job is to say
"could there ever be". The gate is deleted rather than widened a third
time.

These read the TypeScript rather than run it -- the tactic
test_polish_rulings.py and test_locales.py already use for the panel
source. There is no JS test harness in this repo, and a rule that only
lives in a comment is a rule that comes back. What is pinned here is
exactly what a reviewer would otherwise have to re-derive from a
screenshot months later:

- the tab has no gate at all, and nothing bounces you off it;
- the two ACTION PICKERS still have one, through one shared helper;
- the empty card exists, is source-driven, and is not a blank pane;
- the owner's copy is present verbatim in en, in every language, and
  keeps the tokens the parity suite cannot check for it.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

SRC = Path(__file__).parent.parent / "frontend" / "src"
LOCALES = SRC / "locales"
LOCALE_NAMES = ("en", "de", "es", "fr", "it", "ja", "nl", "pl", "pt", "ru")

#: The owner walked section 4 of plucker-constant-tab-plan.md line by
#: line and edited it; the Tuya Local line and the footer are their own
#: wording. Copied here so a well-meaning later edit to en.json has to
#: argue with a test rather than sail through review.
OWNER_COPY = {
    "pluck.empty.headline": (
        "Plucker copies IR codes out of integrations you already have, "
        "so remotes you taught other systems work here too."
    ),
    "pluck.empty.source.broadlink": (
        "Broadlink: codes you learned with remote.learn_command are "
        "stored on disk, and HAIR reads them from there. If you have "
        "only ever used your blaster to send, nothing is stored yet -- "
        "that is normal."
    ),
    "pluck.empty.source.tuya_local": (
        "Tuya Local: plucks codes already learned in the integration, "
        "and/or can copy codes by replaying them into a silent "
        "listener. Nothing is set up in it yet; add your IR device "
        "there first, and it will show up here."
    ),
    "pluck.empty.not_installed": (
        "{vendor}: not set up in this Home Assistant. If you use it, "
        "HAIR can pluck the codes it already knows."
    ),
    "pluck.empty.footer": (
        "Codes captured from a real remote live in the Sniffer; Plucker "
        "is only for codes stored inside other integrations or their "
        "devices."
    ),
}


def _read(name: str) -> str:
    return (SRC / name).read_text(encoding="utf-8")


def _locale(name: str) -> dict:
    return json.loads((LOCALES / f"{name}.json").read_text(encoding="utf-8"))


class TestTheGateIsGone:
    def test_the_panel_holds_no_plucker_gate(self):
        """Not renamed, not widened. Gone."""
        panel = _read("ha-panel-ir-devices.ts")
        assert "_pluckersAvailable" not in panel
        assert "_checkPluckers" not in panel or "_checkPluckers()`" in panel

    def test_the_tab_button_is_unconditional(self):
        """Rendered like the other five, in the plain run of buttons.

        Checked structurally rather than by the absence of a named flag,
        because the next way to reintroduce this bug is a new flag with
        a new name. What must hold is that the Plucker button follows
        its neighbour directly -- not from inside a `cond ? html`
        wrapper, which is exactly the shape the old gate had.
        """
        panel = _read("ha-panel-ir-devices.ts")
        head, _, _ = panel.partition(
            '@click=${() => this._switchTab("plucker")}'
        )
        assert _, "the Plucker tab button moved; re-point this guard"
        before = head[: head.rindex("<button")].rstrip()
        assert before.endswith("</button>"), (
            "the Plucker tab button is wrapped in something; it should sit "
            f"in the plain run of tabs. Preceded by: {before[-60:]!r}"
        )

    def test_nothing_bounces_you_off_the_tab(self):
        """The old gate switched you to Devices if the check came back
        false while you were standing on Plucker -- so the tab could
        vanish under you, mid-visit, with no explanation.

        Pinned as "no test of the active tab against plucker leads to a
        switch away", which is the shape of that bounce whatever the
        condition is named.
        """
        panel = _read("ha-panel-ir-devices.ts")
        for match in re.finditer(r'_activeTab === "plucker"', panel):
            window = panel[match.start(): match.start() + 200]
            assert '_switchTab("devices")' not in window, (
                "something still switches away from the Plucker tab: "
                f"{window[:120]!r}"
            )


class TestTheActionPickersKeepTheirs:
    def test_one_helper_not_a_copy_per_site(self):
        api = _read("api.ts")
        assert "export function anyPluckReadyNow" in api

    def test_the_helper_states_the_distinction_it_protects(self):
        """The sentence is load-bearing: it is what stops the next
        person collapsing the two rules back into one."""
        api = _read("api.ts")
        assert "discovery surfaces always show" in api.lower()
        assert "action pickers show what works now" in api.lower()

    @pytest.mark.parametrize(
        "name",
        ["ir-add-controlled-device-dialog.ts", "ir-add-trigger-remote-dialog.ts"],
    )
    def test_both_dialogs_go_through_the_helper(self, name):
        source = _read(name)
        assert "anyPluckReadyNow(this.pluckSources)" in source
        assert "pluckerConfigured" not in source

    def test_the_panel_hands_both_dialogs_the_sources(self):
        panel = _read("ha-panel-ir-devices.ts")
        assert panel.count(".pluckSources=${this._pluckSources}") == 2


class TestTheEmptyCard:
    def test_the_tab_body_renders_a_card_not_a_blank_pane(self):
        """Plan section 7's second verify item. The constant tab exposes
        whatever the zero-blaster state is, so that state has to be the
        card."""
        body = _read("ir-pluck.ts")
        assert "_renderEmpty()" in body
        assert 'ha-card class="empty"' in body

    def test_the_card_is_source_driven(self):
        body = _read("ir-pluck.ts")
        assert "pluckEmptyLines(this._pluckSources, t)" in body

    def test_the_card_carries_headline_and_footer(self):
        body = _read("ir-pluck.ts")
        assert 't("pluck.empty.headline")' in body
        assert 't("pluck.empty.footer")' in body

    def test_no_buttons_and_no_error_styling_in_the_card(self):
        """An empty Plucker is a normal condition and must read calm."""
        body = _read("ir-pluck.ts")
        card = body.split("private _renderEmpty()")[1].split("render()")[0]
        assert "<button" not in card
        assert "ha-alert" not in card
        assert "alert-type" not in card

    def test_the_add_remote_dialog_says_the_same_thing(self):
        """Same question, same answer, same helper -- answering 'nothing
        found' two ways would be two chances to drift."""
        dialog = _read("ir-pluck-add-remote-dialog.ts")
        assert "pluckEmptyLines(this._pluckSources, t)" in dialog

    def test_the_lines_follow_the_plans_rule(self):
        """ready anywhere -> silent; loaded -> its own key; not loaded
        -> the generic line with the vendor's name."""
        api = _read("api.ts")
        helper = api.split("export function pluckEmptyLines")[1]
        assert "Object.values(source.ready).includes(true)) continue" in helper
        assert '"pluck.empty.not_installed", { vendor: source.name }' in helper
        assert "`pluck.empty.source.${source.integration}`" in helper

    def test_a_source_with_no_string_says_nothing_rather_than_its_key(self):
        """t() falls back to en and then to the key itself, and a raw
        pluck.empty.source.foo on screen is worse than silence."""
        api = _read("api.ts")
        helper = api.split("export function pluckEmptyLines")[1]
        assert "if (line !== key) lines.push(line)" in helper


class TestTheOwnersCopy:
    @pytest.mark.parametrize("key", sorted(OWNER_COPY))
    def test_en_is_verbatim(self, key):
        assert _locale("en")[key] == OWNER_COPY[key]

    @pytest.mark.parametrize("name", LOCALE_NAMES)
    def test_every_language_has_all_five(self, name):
        locale = _locale(name)
        for key in OWNER_COPY:
            assert key in locale, f"{name}.json is missing {key}"
            assert locale[key].strip(), f"{name}.json has {key} blank"

    @pytest.mark.parametrize("name", LOCALE_NAMES)
    def test_the_service_and_product_names_ride_through(self, name):
        """The parity suite guards HAIR / Sniffer / Plucker because they
        are in its brand list. These are not, and they are just as
        untranslatable: an integration domain and two product names a
        person has to type or go looking for."""
        locale = _locale(name)
        assert "remote.learn_command" in locale["pluck.empty.source.broadlink"]
        assert "Broadlink" in locale["pluck.empty.source.broadlink"]
        assert "Tuya Local" in locale["pluck.empty.source.tuya_local"]
        assert "Home Assistant" in locale["pluck.empty.not_installed"]

    @pytest.mark.parametrize("name", LOCALE_NAMES)
    def test_the_vendor_slot_survives(self, name):
        assert "{vendor}" in _locale(name)["pluck.empty.not_installed"]

    @pytest.mark.parametrize("name", LOCALE_NAMES)
    def test_no_em_dash_anywhere_in_the_new_copy(self, name):
        """House rule: spaced double hyphen, never an em-dash."""
        locale = _locale(name)
        for key in OWNER_COPY:
            assert "—" not in locale[key], f"{name}.json:{key}"

    def test_a_source_key_exists_for_every_shipped_provider(self):
        """A provider with no line of its own contributes nothing to the
        card, by design -- so the two that ship must have one."""
        from custom_components.hair.learned_code_stores import PROVIDERS

        en = _locale("en")
        for provider in PROVIDERS:
            assert f"pluck.empty.source.{provider.integration}" in en
