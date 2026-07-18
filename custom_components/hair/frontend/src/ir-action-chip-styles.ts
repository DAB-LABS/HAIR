/**
 * Shared action-chip styles.
 *
 * The row action buttons (Assign / Test / Trigger / Delete / Dismiss) were
 * duplicated across every tab that renders signal or command rows, which is
 * exactly how the popover CSS drifted before ir-popover-styles extracted it
 * in v0.5.7. This module is the same cure for the chips: one source of truth
 * for the chip anatomy and the semantic palette, spread into each consumer:
 *
 *   static styles = [actionChipStyles, css`...component-specific...`];
 *
 * Component-specific treatments stay local to their components: the
 * Sniffer's recent-latest / recent-previous / mint glow classes, the
 * Plucker's pluck button, and any layout margins. This module owns only
 * what every tab must agree on -- base chip anatomy plus the semantic
 * colors (assign green, test primary, trigger gold, delete ember,
 * dismiss neutral) and the position anchor the corner count-dots need.
 *
 * Consumers: ir-signal-monitor, ir-clips, ir-pluck, ir-device-detail,
 * ir-mirror (v0.6.3, the first tab to NEVER carry its own copy).
 */
import { css } from "lit";

export const actionChipStyles = css`
    .action-btn {
        background: none;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        padding: 4px 10px;
        font-size: 0.75rem;
        font-weight: 500;
        font-family: inherit;
        color: var(--primary-color);
        cursor: pointer;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        transition: background 150ms ease, color 150ms ease,
                    border-color 150ms ease, box-shadow 300ms ease;
    }
    .action-btn:hover {
        background: var(--secondary-background-color);
    }
    .action-btn:disabled {
        opacity: 0.5;
        cursor: default;
    }

    /* Semantic chip colors -- the one palette, everywhere. */
    .action-btn.assign-btn {
        color: #2e7d32;
        border-color: rgba(46, 125, 50, 0.3);
        position: relative; /* anchor for the green assignment dot */
    }
    .action-btn.assign-btn:hover {
        background: rgba(46, 125, 50, 0.08);
    }
    .action-btn.test-btn {
        color: var(--primary-color);
    }
    .action-btn.trigger-btn {
        color: #b89930;
        border-color: rgba(184, 153, 48, 0.3);
        position: relative; /* anchor for the yellow trigger dot */
    }
    .action-btn.trigger-btn:hover {
        background: rgba(184, 153, 48, 0.08);
    }
    .action-btn.delete-btn {
        color: #e65100;
        border-color: rgba(230, 81, 0, 0.25);
    }
    .action-btn.delete-btn:hover {
        background: rgba(230, 81, 0, 0.08);
    }
    .action-btn.dismiss-btn {
        color: var(--secondary-text-color);
        border-color: var(--divider-color);
        position: relative; /* anchor for the dot indicator */
    }
`;
