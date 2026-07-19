/**
 * Panel localization (v0.6.8 "French Braid", i18n Phase 0).
 *
 * A deliberately tiny module: flat JSON dictionaries compiled into the
 * single Rollup bundle, a module-level current language, and two
 * functions. No runtime fetches, no dependencies, no framework.
 *
 * - ``t(key, subs)`` returns the localized string for a flat namespaced
 *   key ("mirror.not_heard"), with ``{name}``-style substitutions.
 *   Fallback chain: active locale -> en -> the key itself (a visible
 *   key in the UI is a bug you can read).
 * - ``tp(key, count, subs)`` is the plural form: it appends the
 *   ``Intl.PluralRules`` category for the active locale to the key
 *   ("mirror.sends" -> "mirror.sends.one" / "mirror.sends.other" /
 *   "mirror.sends.few" ...), so three-form languages (pl, ru, cs) work
 *   without English-shaped if/else pluralization. The count is also
 *   provided as the ``{count}`` substitution.
 *
 * The top-level panel calls ``setPanelLanguage(hass.language)`` when
 * hass arrives or changes; everything else just imports ``t``.
 * Language resolution: exact tag -> base language -> en.
 *
 * BRAND NAMES ARE NEVER TRANSLATED (owner ruling, 2026-07-19): HAIR,
 * Sniffer, Clipper, Plucker, Mirror, Tweezer, and the wigs to come are
 * proper nouns and stay out of the dictionaries wherever they stand
 * alone. Taglines and sentences AROUND them translate; a brand name
 * inside a sentence rides as a substitution or literal.
 *
 * Adding a language: copy ``locales/en.json`` to ``locales/<lang>.json``,
 * translate the VALUES only, import it below, and add it to
 * ``DICTIONARIES``. The parity test (tests/test_locales.py) fails CI on
 * any missing or extra key, so a stale translation cannot ship blanks.
 */
import en from "./locales/en.json";
import fr from "./locales/fr.json";
import ja from "./locales/ja.json";

type Dictionary = Record<string, string>;

// Locales whose "_meta.review" key says "AI draft" ship live on purpose
// (owner ruling, 2026-07-19): imperfect-but-present beats English for
// that user, and visible strings recruit native reviewers. The marker
// key never renders; reviewers flip it in their review PR.
const DICTIONARIES: Record<string, Dictionary> = {
    en: en as Dictionary,
    fr: fr as Dictionary,
    ja: ja as Dictionary,
};

let _lang = "en";
let _requested = "en";
let _plurals = new Intl.PluralRules("en");

/** Resolve and set the active panel language (exact -> base -> en). */
export function setPanelLanguage(language: string | undefined): void {
    const tag = language || "en";
    if (tag !== _requested) {
        _requested = tag;
        try {
            // The requested tag (not the resolved dictionary key)
            // drives plural category selection and date formatting,
            // so pt-BR pluralizes and formats as pt-BR even while
            // reading the pt dictionary -- or the en one.
            _plurals = new Intl.PluralRules(tag);
        } catch {
            _plurals = new Intl.PluralRules("en");
        }
    }
    const requested = tag.toLowerCase();
    let resolved = "en";
    if (DICTIONARIES[requested]) {
        resolved = requested;
    } else {
        const base = requested.split("-")[0];
        if (DICTIONARIES[base]) resolved = base;
    }
    _lang = resolved;
}

/** Current resolved dictionary language. */
export function panelLanguage(): string {
    return _lang;
}

/** BCP-47 tag for Intl date/number formatting: the user's requested
 *  language, honored even when the dictionary fell back to en. */
export function formatLanguage(): string {
    return _requested;
}

/** Localize a flat key with optional {name}-style substitutions. */
export function t(
    key: string,
    subs?: Record<string, string | number>,
): string {
    const dict = DICTIONARIES[_lang];
    let s = dict?.[key] ?? (en as Dictionary)[key] ?? key;
    if (subs) {
        for (const [k, v] of Object.entries(subs)) {
            s = s.split(`{${k}}`).join(String(v));
        }
    }
    return s;
}

/** Slug an English vocabulary label to its dictionary key suffix.
 *  MUST stay in sync with the slug rule in tests/test_locales.py and
 *  the vocab-key generator ("Mode: Cool" -> "mode_cool"). */
function vocabSlug(label: string): string {
    return label
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/_+/g, "_")
        .replace(/^_+|_+$/g, "");
}

/**
 * Localize a backend-served vocabulary label (command template or
 * action label). The backend always speaks canonical English; the
 * panel renders the localized label, and whatever the user accepts
 * becomes the stored command name (command names are user data).
 * Unknown labels pass through unchanged, so a new backend label can
 * never render as a raw key.
 */
export function tv(label: string): string {
    const key = `vocab.${vocabSlug(label)}`;
    const dict = DICTIONARIES[_lang];
    return dict?.[key] ?? (en as Dictionary)[key] ?? label;
}

/** Localize a pluralized key: ``key.<pluralCategory>`` with {count}. */
export function tp(
    key: string,
    count: number,
    subs?: Record<string, string | number>,
): string {
    const category = _plurals.select(count);
    const dict = DICTIONARIES[_lang];
    const exact = `${key}.${category}`;
    const other = `${key}.other`;
    let s =
        dict?.[exact] ??
        dict?.[other] ??
        (en as Dictionary)[exact] ??
        (en as Dictionary)[other] ??
        key;
    s = s.split("{count}").join(String(count));
    if (subs) {
        for (const [k, v] of Object.entries(subs)) {
            s = s.split(`{${k}}`).join(String(v));
        }
    }
    return s;
}
