/**
 * The shared "bloom" fire-glow animation (Trigger Remotes signpost 1,
 * Track B item 8: the third copy).
 *
 * Before this module the same 4-keyframe glow-and-fade existed twice,
 * independently: the trigger card's ``trigger-card-flash`` (gold, in
 * ir-device-list.ts) and the Mirror's ``mirror-bloom`` (silver, in
 * ir-mirror.ts). Same shape, same durations, same easing, different
 * colors -- exactly the kind of parallel implementation that drifts
 * (one gets a tuning pass, the other doesn't) rather than a real
 * duplicate that could be deleted outright. This module extracts the
 * SHAPE -- the keyframes, the timing, the reduced-motion guard, and the
 * sequence-numbered trigger logic that fixes a real bug -- and lets
 * each consumer supply its own color via CSS custom properties, so
 * ir-trigger-row's rows, the collapsed HAIR Triggers card, and the
 * Mirror's send rows all render the identical animation shape in their
 * own hue from one source.
 *
 * THE BUG THIS EXTRACTION FIXES (v0.7.2, "repeat-fire glow cut short"):
 * the pre-extraction trigger-card glow tracked a plain ``Set<string>``
 * and a bare ``setTimeout`` per fire:
 *
 *   glowIds.add(id); setTimeout(() => glowIds.delete(id), BLOOM_MS)
 *
 * A trigger firing twice within one BLOOM_MS window queues two
 * timeouts against the SAME id. The first timeout still fires at its
 * original T+BLOOM_MS and deletes the id -- cutting the second fire's
 * glow short, mid-animation, even though a fresh bloom had just
 * started. ``BloomTracker`` below fixes this the way the mockup's own
 * reference ``bloom(el)`` does: every trigger call stamps a new
 * sequence number for that id, and a pending timeout only clears the
 * glow if its OWN sequence is still the current one -- an earlier
 * timeout from a since-superseded fire is a no-op.
 */
import { css, unsafeCSS } from "lit";

/**
 * Milliseconds the glow class stays applied. Deliberately 100ms past
 * the 2.4s CSS animation (BLOOM_ANIMATION_S below): when the animation
 * finishes, the class's own static styles (the 100% keyframe, still
 * applied while the class is present) hold for one more beat before
 * the class drops and each consumer's own transition (border-color,
 * background) carries the soft exit. Matches the pre-extraction
 * trigger-card timing (2.4s animation / 2500ms class hold) that both
 * duplicates already agreed on.
 */
export const BLOOM_MS = 2500;

/** The CSS animation's own duration, as a template literal fragment. */
const BLOOM_ANIMATION_S = "2.4s";

/**
 * Sequence-numbered fire tracker. One instance per component; call
 * ``trigger(id, onSet, onClear)`` from a fire event, where ``onSet``
 * adds ``id`` to the component's own reactive glow state and
 * ``onClear`` removes it. See the module doc for the bug this fixes.
 */
export class BloomTracker {
    private _seqs = new Map<string, number>();

    trigger(id: string, onSet: () => void, onClear: () => void): void {
        const seq = (this._seqs.get(id) ?? 0) + 1;
        this._seqs.set(id, seq);
        // Force a real DOM mutation before (re-)applying the glow
        // class. A repeat fire while the class is already applied
        // renders the identical class string Lit already has on
        // screen -- no attribute change, so the CSS animation never
        // restarts and the glow only ever shows on the first fire
        // (bench catch 2026-08-14). Clearing now and re-setting two
        // frames later guarantees the browser sees a real
        // remove-then-add on every trigger, not just the first.
        onClear();
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                onSet();
                setTimeout(() => {
                    if (this._seqs.get(id) === seq) onClear();
                }, BLOOM_MS);
            });
        });
    }
}

/**
 * Shared bloom CSS. Spread into a consumer's ``static styles`` and add
 * ``.bloom`` to the element being glowed, e.g. ``class="trow ${bloomed
 * ? 'bloom' : ''}"``.
 *
 * Color is three CSS custom properties, each with a gold default (the
 * majority consumer -- trigger surfaces): ``--bloom-rgb`` (an unquoted
 * "R, G, B" triplet, consumed via ``rgba(var(--bloom-rgb), alpha)``,
 * the standard technique for a custom property holding a partial
 * value), ``--bloom-peak``, and ``--bloom-edge`` (the 0%/30% keyframe
 * border colors). A consumer wanting a different hue (the Mirror's
 * silver) overrides these three on its own ``.bloom`` rule -- see
 * ir-mirror.ts.
 */
export const bloomStyles = css`
    .bloom {
        --bloom-rgb: 212, 160, 23;
        --bloom-peak: #f5a623;
        --bloom-edge: #d4a017;
        animation: hair-bloom ${unsafeCSS(BLOOM_ANIMATION_S)} ease-out;
    }
    @keyframes hair-bloom {
        0% {
            background: rgba(var(--bloom-rgb), 0.18);
            border-color: var(--bloom-peak);
            box-shadow: 0 0 16px 4px rgba(var(--bloom-rgb), 0.4);
        }
        30% {
            background: rgba(var(--bloom-rgb), 0.1);
            border-color: var(--bloom-edge);
            box-shadow: 0 0 8px 2px rgba(var(--bloom-rgb), 0.2);
        }
        60% {
            background: rgba(var(--bloom-rgb), 0.06);
            box-shadow: 0 0 4px 1px rgba(var(--bloom-rgb), 0.1);
        }
        100% {
            background: transparent;
            box-shadow: none;
        }
    }
    @media (prefers-reduced-motion: reduce) {
        .bloom {
            animation: none;
        }
    }
`;
