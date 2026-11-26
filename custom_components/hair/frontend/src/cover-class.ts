/**
 * A cover's device class (GH #313), the pure half.
 *
 * A screen Device, and a Remote typed as a screen, can say what kind of
 * cover it is. Home Assistant takes its icon and its open and closed
 * words from that. The kinds are the backend's
 * (models.py COVER_DEVICE_CLASSES), in the same order; shade is the
 * default and is stored as no choice at all. Kept free of lit so the
 * test harness can run it under node.
 */
import type { CoverDeviceClass } from "./types.js";

export const COVER_DEVICE_CLASSES: readonly CoverDeviceClass[] = [
    "awning",
    "blind",
    "curtain",
    "shade",
    "shutter",
    "garage",
    "gate",
];

export const COVER_DEVICE_CLASS_DEFAULT: CoverDeviceClass = "shade";

/** The kind the menu shows for a stored value: the value when it is one
 * of the kinds, and shade for none or anything else. */
export function coverClassShown(
    stored: string | null | undefined,
): CoverDeviceClass {
    return (COVER_DEVICE_CLASSES as readonly string[]).includes(stored ?? "")
        ? (stored as CoverDeviceClass)
        : COVER_DEVICE_CLASS_DEFAULT;
}

/** What a choice saves as: null for shade, the default, so a cover left
 * on it stores nothing; the kind otherwise. */
export function coverClassForSave(
    chosen: CoverDeviceClass,
): CoverDeviceClass | null {
    return chosen === COVER_DEVICE_CLASS_DEFAULT ? null : chosen;
}

/** The locale key of a kind's name. */
export function coverClassLabelKey(kind: CoverDeviceClass): string {
    return `devsettings.cover_class_${kind}`;
}
