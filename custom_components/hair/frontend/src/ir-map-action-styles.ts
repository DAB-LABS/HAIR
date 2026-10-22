/**
 * The action-mapping label ("-> Power Toggle", or a muted "+ Action")
 * that opens the Map action popover.
 *
 * Moved out of ir-command-row.ts (heard state, round 2a) so a typed
 * Remote's button rows (ir-trigger-row.ts) draw exactly the label a
 * Device's command rows do. The rules, and the bench rulings recorded
 * beside them, are unchanged.
 */
import { css } from "lit";

export const mapActionStyles = css`
        .map-action-label {
            display: inline-grid;
            justify-items: center;
            align-items: center;
            background: none;
            border: none;
            padding: 0;
            /* Extra breathing room before TEST (bench ruling 2026-08-11,
               third look): .actions' own 4px flex gap read too tight
               between a plain-text label and the first real button --
               this only widens the label's own trailing edge, so the
               rest of the cluster (chip/test/trigger/edit/trash) keeps
               the standard 4px. */
            margin-right: 6px;
            font-size: 0.75rem;
            font-family: inherit;
            cursor: pointer;
            color: var(--secondary-text-color, #999);
        }
        .map-action-label > * {
            grid-area: 1 / 1;
        }
        .action-sizer {
            visibility: hidden;
            pointer-events: none;
        }
        .action-sizer,
        .action-visible {
            display: inline-flex;
            align-items: center;
            gap: 3px;
        }
        .map-action-label:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .map-action-label[data-mapped] {
            color: var(--primary-color);
        }
        .map-arrow {
            font-size: 0.8em;
        }
        /* Empty-state glyph (owner ruling 2026-08-11, fifth bench look):
           settles the "little glyph" question from the previous round --
           a plain "+" rather than chasing the U-turn arrow from an
           untraced comp. Stays the label's own muted gray; no separate
           color rule needed since it only ever renders in the unmapped
           branch, never alongside [data-mapped]'s blue. */
        .map-plus {
            font-size: 0.8em;
        }
        .map-action-label:hover:not(:disabled) .action-visible .map-label {
            text-decoration: underline;
        }
`;
