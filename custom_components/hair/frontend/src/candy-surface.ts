/**
 * Where the Candy Drawer opens, and how big it is.
 *
 * Pure on purpose (no DOM), so the choice and the sizes run under node in
 * the test suite. The drawer opens in a window of its own, so it can sit
 * beside Home Assistant while the panel is in use. It falls back to a
 * dialog inside the panel when a window of its own cannot be used:
 *
 * - the panel runs in the Home Assistant companion app, which hands
 *   ``window.open`` to the system browser;
 * - the screen is narrow (a phone);
 * - the browser blocked the window (``window.open`` returned null; the
 *   caller learns that only by trying).
 */

/** The pop-out's window name: a second click finds and focuses it. */
export const CANDY_POPUP_NAME = "hair-candy";
export const CANDY_POPUP_WIDTH = 720;
export const CANDY_POPUP_HEIGHT = 900;
/** The panel's own phone breakpoint. */
export const CANDY_NARROW_PX = 768;

export type CandySurface = "popout" | "dialog";

export interface SurfaceContext {
    /** Home Assistant's companion app (``hass.auth.external``). */
    external: boolean;
    /** The browser window's width in CSS pixels. */
    viewportWidth: number;
}

/** The surface to try first. A blocked pop-out still falls to the dialog. */
export function chooseSurface(ctx: SurfaceContext): CandySurface {
    if (ctx.external) return "dialog";
    if (ctx.viewportWidth <= CANDY_NARROW_PX) return "dialog";
    return "popout";
}

/** The ``window.open`` features string, kept inside the screen. */
export function popupFeatures(screenWidth?: number, screenHeight?: number): string {
    const width = screenWidth ? Math.min(CANDY_POPUP_WIDTH, screenWidth) : CANDY_POPUP_WIDTH;
    const height = screenHeight ? Math.min(CANDY_POPUP_HEIGHT, screenHeight) : CANDY_POPUP_HEIGHT;
    return `popup=yes,width=${width},height=${height},resizable=yes,scrollbars=yes`;
}

export interface Box {
    left: number;
    top: number;
    width: number;
    height: number;
}

/**
 * The dialog's overlay: the panel's own area (right of the sidebar, below
 * nothing), never the whole viewport. ``panel`` is the panel element's
 * rect, or null when it cannot be found (then the viewport).
 */
export function overlayBox(panel: Box | null, viewport: { width: number; height: number }): Box {
    if (!panel || panel.width <= 0) {
        return { left: 0, top: 0, width: viewport.width, height: viewport.height };
    }
    const left = Math.max(0, Math.min(panel.left, viewport.width));
    const top = Math.max(0, Math.min(panel.top, viewport.height));
    return {
        left,
        top,
        width: Math.max(0, Math.min(panel.width, viewport.width - left)),
        height: Math.max(0, viewport.height - top),
    };
}

/** The dialog window inside the overlay: up to 1100 x 820 with a 24 px
 * margin, or the whole overlay on a narrow one. */
export function dialogSize(overlay: Box): { width: number; height: number } {
    if (overlay.width <= CANDY_NARROW_PX) {
        return { width: overlay.width, height: overlay.height };
    }
    return {
        width: Math.min(1100, overlay.width - 48),
        height: Math.min(820, overlay.height - 48),
    };
}
