"""Locale dictionary parity, placeholder, and vocabulary coverage.

Phase 0 of multilingual HAIR (v0.6.8 "French Braid"): these tests are
the contract that makes adding a language a two-file PR. A locale file
that is missing keys, invents keys, drops a ``{placeholder}``, or
translates a brand name fails here instead of silently shipping blanks.

Two dictionary families are covered:

- ``frontend/src/locales/*.json`` -- flat panel dictionaries consumed
  by ``localize.ts`` (``t``/``tp``/``tv``).
- ``translations/*.json`` -- nested Home Assistant integration
  translations (config flow etc.), same parity rule applied to the
  full key paths.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from custom_components.hair.command_templates import (
    ACTION_OPTIONS,
    COMMAND_TEMPLATES,
)

from .util_pseudo_locale import make_pseudo

COMPONENT_DIR = Path(__file__).parent.parent
LOCALES_DIR = COMPONENT_DIR / "frontend" / "src" / "locales"
TRANSLATIONS_DIR = COMPONENT_DIR / "translations"

# Owner ruling (2026-07-19): brand names are proper nouns and are never
# translated. Any brand token present in an English value must survive
# verbatim in every translation of that value.
BRAND_NAMES = ("HAIR", "Sniffer", "Clipper", "Plucker", "Mirror", "Tweezer")

# CLDR plural categories appended by tp() in localize.ts.
PLURAL_CATEGORIES = ("zero", "one", "two", "few", "many", "other")

# The pseudo-locale is generated locally and never shipped; if one is
# lying around it is exempt from the shipped-locale contract.
_EXEMPT_STEMS = {"xx"}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _placeholders(value: str) -> set[str]:
    return set(re.findall(r"\{(\w+)\}", value))


def _slug(label: str) -> str:
    """Vocab slug rule -- MUST match vocabSlug() in localize.ts."""
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", label.lower())).strip(
        "_"
    )


def _is_added_plural_variant(key: str) -> bool:
    """True if ``key`` is a plural-category variant of an en family."""
    base, _, suffix = key.rpartition(".")
    return suffix in PLURAL_CATEGORIES and f"{base}.other" in EN


def _frontend_locales() -> list[Path]:
    return sorted(
        p
        for p in LOCALES_DIR.glob("*.json")
        if p.stem != "en" and p.stem not in _EXEMPT_STEMS
    )


def _backend_locales() -> list[Path]:
    return sorted(p for p in TRANSLATIONS_DIR.glob("*.json") if p.stem != "en")


def _nested_paths(data: dict, prefix: str = "") -> set[str]:
    out: set[str] = set()
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out |= _nested_paths(value, path)
        else:
            out.add(path)
    return out


EN = _load(LOCALES_DIR / "en.json")


class TestReviewMarker:
    """Every panel locale declares its review status in-file.

    The reserved "_meta.review" key never renders; it tells the next
    person opening the file (or browsing GitHub) whether these strings
    are source, an assistant draft awaiting a native speaker, or reviewed.
    Parity already forces the key into every locale because en carries
    it; these tests pin the semantics.
    """

    def test_en_declares_source(self):
        assert EN.get("_meta.review") == "source"

    @pytest.mark.parametrize(
        "path", _frontend_locales(), ids=lambda p: p.stem
    )
    def test_translations_declare_their_status(self, path):
        status = _load(path).get("_meta.review", "")
        assert status, f"{path.name} is missing the _meta.review marker"
        assert status != "source", (
            f"{path.name} claims to be the source dictionary; expected "
            "a 'Programming-assistant draft ...' or 'reviewed by ...' status"
        )


class TestEnglishDictionary:
    def test_flat_string_values(self):
        for key, value in EN.items():
            assert isinstance(value, str), f"{key} is not a string"
            assert "." in key, f"{key} is not namespaced"

    def test_plural_families_have_other(self):
        """Every pluralized key family carries the CLDR 'other' form.

        tp() falls back exact -> other -> en, so 'other' is the one
        category that must exist for every family in every language.
        """
        for key in EN:
            base, _, suffix = key.rpartition(".")
            if suffix in PLURAL_CATEGORIES:
                assert f"{base}.other" in EN, f"{base} family missing .other"


class TestFrontendLocaleParity:
    @pytest.mark.parametrize(
        "path", _frontend_locales(), ids=lambda p: p.stem
    )
    def test_key_parity(self, path):
        locale = _load(path)
        missing = sorted(set(EN) - set(locale))
        # Extra keys are allowed ONLY as added plural categories of an
        # English plural family: Polish needs mirror.signals.few and
        # .many that English never has. Anything else extra is a typo.
        extra = sorted(
            key
            for key in set(locale) - set(EN)
            if not _is_added_plural_variant(key)
        )
        assert not missing, f"{path.name} missing keys: {missing[:8]}"
        assert not extra, f"{path.name} extra keys: {extra[:8]}"

    @pytest.mark.parametrize(
        "path", _frontend_locales(), ids=lambda p: p.stem
    )
    def test_placeholder_parity(self, path):
        locale = _load(path)
        for key, en_value in EN.items():
            want = _placeholders(en_value)
            got = _placeholders(locale.get(key, ""))
            assert got == want, (
                f"{path.name}:{key} placeholders {got} != {want}"
            )
        # Added plural variants (.few/.many) must match the placeholder
        # set of the family's English .other form.
        for key in set(locale) - set(EN):
            if _is_added_plural_variant(key):
                base, _, _ = key.rpartition(".")
                want = _placeholders(EN[f"{base}.other"])
                got = _placeholders(locale[key])
                assert got == want, (
                    f"{path.name}:{key} placeholders {got} != {want}"
                )

    @pytest.mark.parametrize(
        "path", _frontend_locales(), ids=lambda p: p.stem
    )
    def test_brand_names_untranslated(self, path):
        locale = _load(path)
        for key, en_value in EN.items():
            for brand in BRAND_NAMES:
                # ASCII lookarounds, not \b: in "HAIRデバイス" the kana
                # is a \w character, so \b would miss the brand even
                # though it rides through verbatim.
                pattern = rf"(?<![A-Za-z0-9]){brand}(?![A-Za-z0-9])"
                if re.search(pattern, en_value):
                    assert re.search(pattern, locale.get(key, "")), (
                        f"{path.name}:{key} lost brand name {brand!r}"
                    )


class TestVocabularyCoverage:
    """The vocab.* section mirrors the backend label tables exactly."""

    def _backend_labels(self) -> dict[str, str]:
        labels: dict[str, str] = {}
        for templates in COMMAND_TEMPLATES.values():
            for template in templates:
                labels.setdefault(_slug(template.name), template.name)
        for options in ACTION_OPTIONS.values():
            for _key, label in options:
                labels.setdefault(_slug(label), label)
        return labels

    def test_every_backend_label_has_vocab_key(self):
        for slug, label in self._backend_labels().items():
            key = f"vocab.{slug}"
            assert key in EN, f"en.json missing {key} for label {label!r}"
            assert EN[key] == label, (
                f"{key} is {EN[key]!r}, backend serves {label!r}"
            )

    def test_no_orphan_vocab_keys(self):
        known = {f"vocab.{slug}" for slug in self._backend_labels()}
        orphans = sorted(
            key for key in EN if key.startswith("vocab.") and key not in known
        )
        assert not orphans, f"vocab keys with no backend label: {orphans}"

    def test_slugs_do_not_collide(self):
        seen: dict[str, str] = {}
        for labels in (
            [t.name for ts in COMMAND_TEMPLATES.values() for t in ts],
            [lb for opts in ACTION_OPTIONS.values() for _k, lb in opts],
        ):
            for label in labels:
                slug = _slug(label)
                assert seen.setdefault(slug, label) == label, (
                    f"slug {slug!r} claimed by both "
                    f"{seen[slug]!r} and {label!r}"
                )


class TestTranslatedReadmes:
    """Every shipped panel locale has a truncated README at the repo
    root, and its version stamp matches the manifest.

    The stamp is the drift guard: refreshing the translated READMEs is
    a release-protocol step, and this test makes shipping a release
    without the refresh a CI failure instead of a silent staleness.
    """

    REPO_ROOT = COMPONENT_DIR.parent.parent
    MANIFEST = COMPONENT_DIR / "manifest.json"

    def _version(self) -> str:
        return json.loads(self.MANIFEST.read_text(encoding="utf-8"))[
            "version"
        ]

    @pytest.mark.parametrize(
        "path", _frontend_locales(), ids=lambda p: p.stem
    )
    def test_readme_exists_and_stamp_is_current(self, path):
        readme = self.REPO_ROOT / f"README.{path.stem}.md"
        assert readme.is_file(), (
            f"README.{path.stem}.md missing at repo root; every shipped "
            "locale carries a truncated translated README"
        )
        text = readme.read_text(encoding="utf-8")
        stamp = f"v{self._version()}"
        assert stamp in text, (
            f"README.{path.stem}.md is stale: expected the {stamp} "
            "version stamp; refresh the translated READMEs for this "
            "release"
        )
        # The ownership invitation must survive every refresh.
        assert "CONTRIBUTING.md#adding-a-language" in text


class TestPanelVersionStamp:
    """The panel footer version constant tracks manifest.json.

    v0.6.8 shipped with the footer still reading 0.6.7 because the
    constant was a comment-enforced convention ("bump alongside
    manifest.json"). Conventions drift; tests do not. The bundle check
    catches the other half of the mistake: bumping the source constant
    but forgetting to rebuild the shipped JS.
    """

    PANEL_TS = (
        COMPONENT_DIR / "frontend" / "src" / "ha-panel-ir-devices.ts"
    )
    PANEL_BUNDLE = (
        COMPONENT_DIR / "frontend" / "dist" / "ha-panel-ir-devices.js"
    )
    MANIFEST = COMPONENT_DIR / "manifest.json"

    def _version(self) -> str:
        return json.loads(self.MANIFEST.read_text(encoding="utf-8"))[
            "version"
        ]

    def test_footer_constant_matches_manifest(self):
        version = self._version()
        text = self.PANEL_TS.read_text(encoding="utf-8")
        assert f'const HAIR_VERSION = "{version}";' in text, (
            "ha-panel-ir-devices.ts HAIR_VERSION is stale; bump it to "
            f"{version} to match manifest.json"
        )

    def test_shipped_bundle_carries_current_version(self):
        version = self._version()
        bundle = self.PANEL_BUNDLE.read_text(encoding="utf-8")
        assert f'"{version}"' in bundle, (
            f"frontend/dist bundle does not contain {version}; run "
            "'npm run build' in frontend/ after bumping HAIR_VERSION"
        )


class TestBackendTranslationParity:
    @pytest.mark.parametrize("path", _backend_locales(), ids=lambda p: p.stem)
    def test_key_path_parity(self, path):
        en_paths = _nested_paths(_load(TRANSLATIONS_DIR / "en.json"))
        locale_paths = _nested_paths(_load(path))
        missing = sorted(en_paths - locale_paths)
        extra = sorted(locale_paths - en_paths)
        assert not missing, f"{path.name} missing: {missing[:8]}"
        assert not extra, f"{path.name} extra: {extra[:8]}"


class TestPseudoLocale:
    def test_keys_and_placeholders_survive(self):
        pseudo = make_pseudo(EN)
        assert set(pseudo) == set(EN)
        for key, value in EN.items():
            assert _placeholders(pseudo[key]) == _placeholders(value)

    def test_values_are_longer(self):
        pseudo = make_pseudo(EN)
        for key, value in EN.items():
            assert len(pseudo[key]) > len(value), key

    def test_brand_names_survive(self):
        pseudo = make_pseudo(EN)
        for key, value in EN.items():
            for brand in BRAND_NAMES:
                if re.search(rf"\b{brand}\b", value):
                    assert brand in pseudo[key]
