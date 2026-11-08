/**
 * A sentence at the bottom of the panel, over everything, for a few
 * seconds: the homepage's toast, shared so the Sniffer and the Clipper
 * can say why a Test was refused without taking over the row's Test
 * button (send review N14).
 */
import { css } from "lit";

/** How long a refusal stays up, in milliseconds. */
export const BOTTOM_TOAST_MS = 5000;

export const bottomToastStyles = css`
    .bottom-toast {
        position: fixed;
        bottom: 24px;
        left: 50%;
        transform: translateX(-50%);
        max-width: min(560px, calc(100vw - 32px));
        background: var(--primary-color);
        color: white;
        padding: 8px 16px;
        border-radius: 6px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        z-index: 100;
    }
`;
