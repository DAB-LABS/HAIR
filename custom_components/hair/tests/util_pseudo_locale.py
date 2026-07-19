"""Pseudo-locale ("xx") generator for overflow smoke testing.

Wraps every English panel string in visible markers and pads it about
40 percent with middle dots, keeping ``{placeholder}`` tokens intact:

    "Place a receiver in earshot" -> "⟦Place a receiver in earshot·········⟧"

The point: load the panel with every string longer than English and
walk the tabs. Anything that truncates, clips, or overflows under the
padding will do the same for German or French, so it gets fixed before
a translation exists to reveal it.

The generated file is NOT shipped and NOT wired into the bundle. To
run the smoke test locally:

1. ``python custom_components/hair/tests/util_pseudo_locale.py``
   (writes ``frontend/src/locales/xx.json``)
2. In ``localize.ts``, temporarily change the import to
   ``import en from "./locales/xx.json";`` so the pseudo strings ride
   the default dictionary with zero language-selection gymnastics.
3. ``npm run build`` in ``frontend/``, load the panel, walk every tab
   and dialog.
4. Revert the import, delete ``xx.json``.

``make_pseudo`` is imported by ``test_locales.py`` so CI proves the
generator keeps placeholders and brand names intact.
"""
from __future__ import annotations

import json
from pathlib import Path

_LOCALES_DIR = Path(__file__).parent.parent / "frontend" / "src" / "locales"


def make_pseudo(en: dict[str, str]) -> dict[str, str]:
    """Return a padded pseudo-locale dictionary from English values."""
    out: dict[str, str] = {}
    for key, value in en.items():
        pad = "·" * max(2, int(len(value) * 0.4))
        out[key] = f"⟦{value}{pad}⟧"
    return out


def main() -> None:
    en = json.loads((_LOCALES_DIR / "en.json").read_text(encoding="utf-8"))
    target = _LOCALES_DIR / "xx.json"
    target.write_text(
        json.dumps(make_pseudo(en), indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {target} ({len(en)} keys)")


if __name__ == "__main__":
    main()
