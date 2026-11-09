/**
 * The homepage's IR and RF filter glyphs (item 14): a pair on the
 * Devices header and a pair on the Remotes header, each filtering the
 * cards below it, as plain functions so the node tests run the rules
 * the panel runs.
 */
import type { Medium } from "./types.js";

/** Which media the homepage shows. Both on by default. */
export interface MediaShow {
    ir: boolean;
    rf: boolean;
}

export const MEDIA_SHOW_DEFAULT: MediaShow = { ir: true, rf: true };

/** The homepage's two sections, each with its own pair of glyphs that
 *  filters the cards below it, and the Sniffer's remote list, whose IR
 *  and RF glyphs are remembered the same way (its hidden eye is not). */
export type HomeSection = "devices" | "remotes";
export type MediaSection = HomeSection | "sniffer";

/** The key a browser keeps one section's choice under. Each section is
 *  its own pair of toggles. */
export function mediaShowKey(section: MediaSection): string {
    return section === "sniffer"
        ? "hair.sniffer.media_show"
        : `hair.homepage.media_show.${section}`;
}

/** This browser's storage for the filter glyphs, or nothing where a
 *  page has none (tests) or the browser refuses it. */
export function browserStorage(): Storage | undefined {
    try {
        return typeof window !== "undefined" ? window.localStorage : undefined;
    } catch {
        return undefined;
    }
}

/** Whether a Device or Remote card shows: a lit glyph for any medium it
 *  uses. A card that uses both shows while either is lit; a card with
 *  no medium yet (a new, empty device) shows while either is lit. */
export function mediaShows(show: MediaShow, media: readonly Medium[] | undefined): boolean {
    if (!media || media.length === 0) return show.ir || show.rf;
    return media.some((m) => (m === "rf" ? show.rf : show.ir));
}

/** Whether every card shows, which is when the device grid can be
 *  reordered. */
export function mediaShowsEverything(show: MediaShow): boolean {
    return show.ir && show.rf;
}

/** A stored choice, read back defensively: anything unreadable is the
 *  default. */
export function parseMediaShow(raw: string | null | undefined): MediaShow {
    if (!raw) return { ...MEDIA_SHOW_DEFAULT };
    try {
        const v = JSON.parse(raw) as Partial<MediaShow> | null;
        return {
            ir: typeof v?.ir === "boolean" ? v.ir : MEDIA_SHOW_DEFAULT.ir,
            rf: typeof v?.rf === "boolean" ? v.rf : MEDIA_SHOW_DEFAULT.rf,
        };
    } catch {
        return { ...MEDIA_SHOW_DEFAULT };
    }
}

/** This browser's choice. Storage can be missing or refuse (a private
 *  window, blocked site data); the default then stands. */
export function loadMediaShow(
    storage: Pick<Storage, "getItem"> | undefined,
    section: MediaSection,
): MediaShow {
    try {
        return parseMediaShow(storage?.getItem(mediaShowKey(section)));
    } catch {
        return { ...MEDIA_SHOW_DEFAULT };
    }
}

export function saveMediaShow(
    storage: Pick<Storage, "setItem"> | undefined,
    section: MediaSection,
    show: MediaShow,
): void {
    try {
        storage?.setItem(mediaShowKey(section), JSON.stringify({ ir: show.ir, rf: show.rf }));
    } catch {
        // Not remembered in this browser; the toggle still works.
    }
}
