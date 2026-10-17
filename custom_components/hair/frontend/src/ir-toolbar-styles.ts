/**
 * The section header every tab draws (icon, title, count, tagline).
 *
 * Each tab keeps its own .toolbar-title rules; this fragment comes last
 * in each tab's static styles and adds only the layout the narrow view
 * needs, so the six headers behave as one.
 *
 * - The wrap is unconditional, from myml's PR #209 ("Wrap the toolbar
 *   tagline instead of squeezing it"): a no-op wherever the row already
 *   fits, and elsewhere the tagline drops to a line of its own instead
 *   of being squeezed into a narrow column beside the title.
 * - The count never breaks inside itself: "(7 remotes)" stays whole.
 * - Below the panel's 768px breakpoint the tagline always takes the
 *   second line, smaller, lined up under the title text, and without
 *   the "- " that separates it on one line (mobile pass, 2026-10-17).
 *   Desktop keeps today's one-line form.
 */
import { css } from "lit";

export const toolbarStyles = css`
    .toolbar-title {
        flex-wrap: wrap;
    }
    .toolbar-count {
        white-space: nowrap;
    }
    @media (max-width: 768px) {
        .toolbar-title {
            row-gap: 2px;
        }
        .toolbar-tagline {
            flex-basis: 100%;
            padding-left: 32px;
            font-size: 0.7rem;
            line-height: 1.35;
        }
        .toolbar-dash {
            display: none;
        }
    }
`;
