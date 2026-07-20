"""Localized command-vocabulary synonyms for assign-time auto-mapping.

The panel's locale dictionaries (``frontend/src/locales/*.json``) carry
a ``vocab.*`` section: every command-template and action label the
backend serves, localized per language. The backend itself never
localizes -- it speaks canonical English labels and stable action keys
over the wire, and the panel renders them through ``tv()`` (see
``localize.ts``; plan doc: multilingual-hair, section 3.3).

This module reads those same dictionaries in the other direction. When
a user accepts a localized template, the localized string becomes the
stored command name (command names are user data), and assign-time
auto-mapping should still recognize it. ``localized_auto_map()`` builds
a casefolded name -> action-key table across ALL shipped locales at
once: English establishes the bridge (a vocab slug maps to an action
iff its English label is an ``AUTO_MAP_RULES`` name), then every
locale's rendering of that slug joins the table. Names are unambiguous
across locales in practice; on a collision the first locale wins
(English first, then alphabetical) and we log it.

The build reads files, so it is primed once in ``async_setup_entry``
via the executor and cached for the process lifetime.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

LOCALES_DIR = Path(__file__).parent / "frontend" / "src" / "locales"
_VOCAB_PREFIX = "vocab."


def localized_auto_map(rules: dict[str, str]) -> dict[str, str]:
    """Return the casefolded localized-name -> action-key table.

    ``rules`` is the English ``AUTO_MAP_RULES`` table. The result is
    cached; the first call performs blocking file I/O, so prime it via
    the executor (``device_manager.prime_localized_auto_map``).
    """
    return _cached(tuple(sorted(rules.items())))


def reset_cache() -> None:
    """Drop the cached table (testing hook)."""
    _cached.cache_clear()


@lru_cache(maxsize=1)
def _cached(rules_key: tuple[tuple[str, str], ...]) -> dict[str, str]:
    return _build(dict(rules_key))


def _build(rules: dict[str, str]) -> dict[str, str]:
    files = _locale_files()
    if not files or files[0].stem != "en":
        _LOGGER.warning(
            "No English locale dictionary at %s; localized auto-map disabled",
            LOCALES_DIR,
        )
        return {}
    try:
        en_vocab = _vocab(files[0])
    except (OSError, ValueError):
        _LOGGER.warning(
            "Could not read %s; localized auto-map disabled", files[0]
        )
        return {}

    # English establishes the slug -> action bridge.
    action_by_slug = {}
    for slug, label in en_vocab.items():
        action = rules.get(label.casefold())
        if action:
            action_by_slug[slug] = action

    table: dict[str, str] = {}
    for path in files:
        if path is files[0]:
            vocab = en_vocab
        else:
            try:
                vocab = _vocab(path)
            except (OSError, ValueError):
                _LOGGER.warning("Skipping unreadable locale file %s", path)
                continue
        for slug, label in vocab.items():
            action = action_by_slug.get(slug)
            if not action:
                continue
            name = label.casefold()
            existing = table.get(name)
            if existing is None:
                table[name] = action
            elif existing != action:
                _LOGGER.info(
                    "Vocabulary collision: %r maps to both %s and %s; "
                    "keeping %s",
                    name,
                    existing,
                    action,
                    existing,
                )
    return table


def _locale_files() -> list[Path]:
    if not LOCALES_DIR.is_dir():
        return []
    return sorted(
        LOCALES_DIR.glob("*.json"), key=lambda p: (p.stem != "en", p.stem)
    )


def _vocab(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        key[len(_VOCAB_PREFIX):]: value
        for key, value in data.items()
        if key.startswith(_VOCAB_PREFIX) and isinstance(value, str)
    }
