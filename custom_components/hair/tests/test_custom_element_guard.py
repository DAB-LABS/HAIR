"""Every panel component registers through the guarded customElement.

frontend/src/decorators.ts wraps Lit's customElement so that a bundle
evaluated a second time in one page (a new version loading over an open
panel) skips a tag already defined instead of defining it again, which
throws and aborts the rest of the module. A file that imports the
decorator straight from lit skips that guard: five tangle files did, and
a phone reloading the panel after an upgrade logged "the name
ir-tangle-fix has already been used", with every component defined after
it missing until a full reload.
"""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).parent.parent / "frontend" / "src"
FROM_LIT = re.compile(
    r"import\s*\{([^}]*)\}\s*from\s*[\"']lit/decorators(?:/[\w-]+)?(?:\.js)?[\"']"
)
FROM_GUARD = re.compile(
    r"import\s*\{[^}]*\bcustomElement\b[^}]*\}\s*from\s*[\"']\./decorators\.js[\"']"
)


def _sources() -> list[Path]:
    return sorted(p for p in SRC.rglob("*.ts") if p.name != "decorators.ts")


def test_the_sources_are_found():
    assert len(_sources()) > 50


def test_no_file_imports_customElement_from_lit():
    offenders = [
        p.relative_to(SRC).as_posix()
        for p in _sources()
        for names in FROM_LIT.findall(p.read_text(encoding="utf-8"))
        if re.search(r"\bcustomElement\b", names)
    ]
    assert offenders == []


def test_every_registered_component_uses_the_guard():
    unguarded = [
        p.relative_to(SRC).as_posix()
        for p in _sources()
        if "@customElement(" in (text := p.read_text(encoding="utf-8"))
        and not FROM_GUARD.search(text)
    ]
    assert unguarded == []


def test_the_guard_still_guards():
    text = (SRC / "decorators.ts").read_text(encoding="utf-8")
    assert "customElements.get(name) ? noop : litCustomElement(name)" in text
