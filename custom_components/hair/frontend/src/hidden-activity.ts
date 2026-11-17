/**
 * Something you have hidden is still arriving: the ring and the dot.
 *
 * The Sniffer's eye has done this since v0.2.0: a press from a hidden
 * remote rings the eye in the Sniffer's blue and leaves a dot on it
 * until the person shows hidden remotes again. The owner asked for the
 * same on the IR and RF glyphs (2026-11-16, 13:08 and 13:11 PT): when a
 * medium is switched off and a signal of that medium arrives, its glyph
 * does exactly what the eye does. So the eye's behaviour lives here,
 * once, and every glyph that needs it holds one of these.
 *
 *   ping()      one arrival: the ring plays again from the start, and
 *               the dot is set. Every press rings again: the class
 *               comes off and goes back on two frames later, so the
 *               browser restarts the animation (owner bench, 19:35).
 *   clearDot()  the person has looked: the dot goes. The ring runs out
 *               on its own.
 *
 * Nothing is stored: a reload clears the dot, as it always did for the
 * eye.
 */
import { css, type ReactiveController, type ReactiveControllerHost } from "lit";

/** How long the ring holds: about 1.3 s longer than a hit flash, so it
 *  is discoverable, not loud (the v0.2.0 plan). */
export const HIDDEN_GLOW_HOLD_MS = 3800;

/** The pure part, for the node tests: what one arrival and one look do
 *  to the state. */
export interface HiddenActivityState {
    glow: boolean;
    dot: boolean;
}

export function afterPing(_: HiddenActivityState): HiddenActivityState {
    return { glow: true, dot: true };
}

export function afterLook(state: HiddenActivityState): HiddenActivityState {
    return { glow: state.glow, dot: false };
}

export class HiddenActivity implements ReactiveController {
    glow = false;
    dot = false;
    private _timer: ReturnType<typeof setTimeout> | null = null;

    constructor(private readonly _host: ReactiveControllerHost) {
        _host.addController(this);
    }

    ping(): void {
        this.dot = afterPing(this).dot;
        if (this._timer !== null) {
            clearTimeout(this._timer);
            this._timer = null;
        }
        this.glow = false;
        this._host.requestUpdate();
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                this.glow = true;
                this._host.requestUpdate();
                this._timer = setTimeout(() => {
                    this.glow = false;
                    this._timer = null;
                    this._host.requestUpdate();
                }, HIDDEN_GLOW_HOLD_MS);
            });
        });
    }

    clearDot(): void {
        if (!this.dot) return;
        this.dot = afterLook(this).dot;
        this._host.requestUpdate();
    }

    hostDisconnected(): void {
        if (this._timer !== null) {
            clearTimeout(this._timer);
            this._timer = null;
        }
        this.glow = false;
    }
}

/** The ring around the glyph, the halo on its icon and the dot on its
 *  upper right, for any `.show-glyph` (filter-glyph-styles.ts). In the
 *  theme's primary color, the blue people read as "a signal just
 *  arrived"; no fixed color of its own. */
export const hiddenActivityStyles = css`
    .show-glyph.hidden-glow {
        animation: hidden-pulse 3.8s ease-out;
    }
    .show-glyph.hidden-glow ha-svg-icon,
    .show-glyph.hidden-glow .hair-proto {
        animation: hidden-eye 3.8s ease-out;
    }
    @keyframes hidden-eye {
        0% {
            color: var(--primary-color);
            filter: drop-shadow(0 0 0 transparent);
        }
        12% {
            color: var(--primary-color);
            filter: drop-shadow(0 0 6px color-mix(in srgb, var(--primary-color) 95%, transparent))
                drop-shadow(0 0 2px color-mix(in srgb, var(--primary-color) 90%, transparent));
        }
        60% {
            color: var(--primary-color);
            filter: drop-shadow(0 0 4px color-mix(in srgb, var(--primary-color) 60%, transparent));
        }
        100% {
            filter: drop-shadow(0 0 0 transparent);
        }
    }
    @keyframes hidden-pulse {
        0% {
            box-shadow: 0 0 0 0 transparent;
        }
        12% {
            box-shadow:
                0 0 0 2px color-mix(in srgb, var(--primary-color) 85%, transparent),
                0 0 12px 4px color-mix(in srgb, var(--primary-color) 55%, transparent);
        }
        70% {
            box-shadow:
                0 0 0 1px color-mix(in srgb, var(--primary-color) 40%, transparent),
                0 0 6px 2px color-mix(in srgb, var(--primary-color) 30%, transparent);
        }
        100% {
            box-shadow: 0 0 0 0 transparent;
        }
    }
    @media (prefers-reduced-motion: reduce) {
        .show-glyph.hidden-glow,
        .show-glyph.hidden-glow ha-svg-icon,
        .show-glyph.hidden-glow .hair-proto {
            animation: none;
            color: var(--primary-color);
        }
    }
    /* Beside the glyph's upper right, not on it (owner, 2026-11-17 08:07
       PT: about 10% smaller, "hanging right next to it instead of
       covering part of it"). The button is 28 x 24 with an 18 px icon
       centred, so a 7 px dot in the button's top right corner reaches
       only the icon box's empty corner, and stays inside the button's own
       hit area, clear of the next glyph. Full blue even on an unlit
       glyph, which is greyed by color, not opacity
       (filter-glyph-styles.ts). */
    .hidden-dot {
        position: absolute;
        top: 0;
        right: 0;
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--primary-color);
        box-shadow: 0 0 4px color-mix(in srgb, var(--primary-color) 55%, transparent);
        pointer-events: none;
    }
`;
