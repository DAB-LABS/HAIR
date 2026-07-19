# v0.6.0 - Shave and a Haircut

HAIR now reads eight IR protocols instead of one. This release adds decoders for Sony SIRC (12, 15, and 20 bit), Philips RC-5 (including the RC5X extension), Samsung32, Sharp, Kaseikyo (the Panasonic family), Symphony (the ceiling fan family), and Marantz Extended, joining the NEC support HAIR has had since v0.4.0.

## Why the decoders live in HAIR

HAIR has always leaned on Home Assistant's shared infrared-protocols library for protocol knowledge, and staying aligned with the platform is still the plan. But the library currently decodes very few protocols, and that gap was causing real pain for real users: one button splitting into a dozen Sniffer rows, remotes that never got a stable identity, triggers that could not tell buttons apart. Waiting for the library to grow was costing too much.

So the decoders ship inside HAIR, written in the library's own style, and each one is headed upstream as a pull request. HAIR checks the bundled library first for every protocol, every time it starts. The moment a Home Assistant release ships a library version that can decode one of these protocols itself, HAIR steps aside and uses it, automatically, with no update needed. The built-in decoders are a bridge, not a fork.

## What this fixes

One button is one row again. The day after v0.5.8 shipped, two sharp-eyed users reported that repeat presses of a single button could still split into separate rows: press length varies, so captures contain different numbers of repeated frames, and some receivers wobble pulse widths between presses. The new decoders read the actual bits. A capture is split into its frames, each frame is decoded, and the majority decides, so a short tap, a long press, and a jittery capture of the same button all produce the same identity. Thanks to @loic.gouraud (twelve rows for twelve presses of one button) and @blalor for the fast, precise reports; your captures are permanent test fixtures now.

Catalogs that already fragmented heal at startup. The split rows collapse into the oldest row, keeping its nickname and summing its hit counts. No manual cleanup needed.

The ceiling fan class from GH #38 decodes now. Symphony remotes send preamble frames and then repeat the button code while the button is held, so every capture used to look different. The majority vote handles both. Thanks to @mvdwetering, whose ESPHome log identified the protocol and the preamble detail.

Decoded signals also transmit better: Test and device TX re-encode clean canonical timings instead of replaying captured ones, the same treatment NEC has had. And RC-5 and Marantz remotes get proper toggle handling: HAIR tracks the toggle bit per command and alternates it on every send, the way the original remotes do.

## Verified on hardware

Sony 12, 15, and 20 bit, Sharp, Kaseikyo, Samsung32, RC-5, and NEC were all verified live on real receivers and emitters before this release, including full transmit-to-receive loopbacks and a physical Sharp TV remote. Two decoder bugs were found and fixed during that bench work that no simulated test would have caught.

## Also in this release

The diagnostics download now lists every registered protocol, whether it is served by the bundled library or by HAIR's built-in decoder, and whether its transmit path re-encodes or replays raw.

Full details in the [CHANGELOG](https://github.com/DAB-LABS/HAIR/blob/main/CHANGELOG.md).
