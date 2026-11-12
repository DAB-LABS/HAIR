/**
 * The Candy Drawer's subscription, for either host (the pop-out and the
 * in-panel dialog).
 *
 * Single static captures come only to a subscription that asked for
 * them (``static: true``), so turning the Static chip on or off
 * resubscribes. The new subscription is opened before the old one is
 * closed, so the server never sees the drawer leave: its static counts
 * and the ditto memo live only while someone is subscribed.
 *
 * The old subscription keeps printing until the new one is open: the
 * server answers a subscribe before it sends that subscription anything,
 * so switching at the answer loses nothing and prints nothing twice. A
 * resubscribe the server refuses leaves the old one open and printing.
 * Of several quick toggles, only the last one's subscription stays.
 */
import type { HairApi } from "./api.js";
import type { CandyEvent } from "./candy-text.js";

export class CandyFeed {
    /** The latest subscribe asked for. */
    private requested = 0;
    /** The subscribe whose events print. */
    private active = 0;
    private unsubscribe: (() => Promise<void>) | null = null;
    private stopped = false;

    constructor(
        private readonly api: HairApi,
        private readonly onEvent: (event: CandyEvent) => void,
    ) {}

    /** Subscribe, or subscribe again with Static on or off. */
    start(withStatic = false): void {
        if (this.stopped) return;
        const attempt = ++this.requested;
        this.api
            .subscribeCandy(
                (event) => {
                    if (attempt === this.active) this.onEvent(event);
                },
                { static: withStatic },
            )
            .then((unsubscribe) => {
                if (this.stopped || attempt !== this.requested) {
                    // Stopped, or a later toggle has been asked for.
                    void unsubscribe().catch(() => undefined);
                    return;
                }
                const previous = this.unsubscribe;
                this.active = attempt;
                this.unsubscribe = unsubscribe;
                if (previous) void previous().catch(() => undefined);
            })
            .catch(() => {
                /* Refused (an admin-only stream): the old one, if any, stays. */
            });
    }

    /** Unsubscribe for good. */
    stop(): void {
        this.stopped = true;
        this.active = -1;
        const unsubscribe = this.unsubscribe;
        this.unsubscribe = null;
        if (unsubscribe) void unsubscribe().catch(() => undefined);
    }
}
