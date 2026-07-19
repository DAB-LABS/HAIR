# HAIR v0.6.7 -- Shampoo

A cleanup-and-hardening release. The panel got a deep lather under the hood, and two real transmission bugs found on the bench are fixed.

## The air is a shared medium

Two fixes in this release come from the same physics: infrared is sound for light, and two things talking at once make noise.

**Multi-emitter sends are staggered.** When a device broadcasts through two blasters, or you test a signal out of several emitters at once, both used to key up at the same instant. Any receiver in range of both heard a superimposed hybrid, a perfectly valid pulse train that decodes as nothing, and it landed in the Sniffer as a junk row. HAIR now serializes every transmission it originates and inserts a short quiet gap whenever the transmitting emitter changes. Multi-emitter commands come out clean, and each burst decodes on its own. Same-emitter pacing is untouched.

**Garbled echoes are recognized as the house's own voice.** A send that comes back damaged (reflections, marginal range, protocol timing quirks) used to miss the echo claim and mint a junk Sniffer row per mangle. Send expectations now carry the transmitted frame's shape. An unclaimed, undecodable capture arriving inside the send window that resembles what just went out is claimed as a garbled echo: the Mirror row is marked heard, because a mangled echo still proves the LED fired, and the Sniffer never sees it. Captures that decode cleanly are never swallowed, no matter how similar, so pressing a real button moments after a test is always safe.

## Mirror polish

- Unknown-send rows explain themselves. A foreign send that no receiver heard now reads "Unknown IR signal sent" with a plain sentence naming the blaster and the remedy: place a receiver in earshot to catch the next send.
- Mirror rows are individual rounded cards, and a send that lands while you watch blooms the whole card in silver, on the same rhythm as the trigger glow.
- Heard-back wording says "last heard", describing the most recent send rather than over-claiming history.
- "+ Mirrored Signal" joins Sniffed and Clipped in the device footer. The third road for getting codes into a device gets its road sign.

## Fixes and polish

- The Promote dialog's name field could render as an empty box you could not type in. Rebuilt on the same plain input every other dialog uses. The suggested name pre-fills and Enter creates.
- Count dots render their digits on tabular figures with one shared optical nudge, so a 1, a 2, and a 9 all sit identically in the circle.
- Add-signal actions in the Clipper and Plucker are quiet accent-colored text buttons in each tab's color.

## Under the hood

Eleven dialogs now draw from one shared style module, the third extraction in the family after the popovers and the action chips. Roughly 700 lines are gone at pixel parity, and every shared style and string now lives in exactly one place, which is groundwork for translations down the road.

Update through HACS. Full changelog in the repository.

~ DAB
