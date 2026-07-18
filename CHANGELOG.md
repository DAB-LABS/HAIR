# Changelog

All notable changes to HAIR will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.3] - 2026-07-18 -- Mirror

### Added

- The Mirror tab: see what your house transmits. Every IR command sent through Home Assistant now appears as a row in a new panel tab, whether anything heard it or not -- HAIR device commands, catalog tests, automations, and even other integrations sending through the native infrared platform, caught the moment their emitter fires. Each row shows the send's identity (the assigned command name when there is one, else the decoded protocol identity), which emitter carried it, whether a receiver heard it back and in which room (resolved through the receiver's Home Assistant area), how it originated, and the running send count. A send that lands while you are watching blooms the row silver. Rows carry the same Assign, Test, and Trigger actions as everywhere else, plus the code viewer, so the Mirror doubles as a third way of importing codes: press a button in any vendor app whose blaster transmits through the infrared platform, and if a receiver hears it, the code lands in the Mirror one Assign away from living in HAIR. There is deliberately no delete: the Mirror is a log, and logs do not forget. Homes with no receiver at all simply see their sends without heard-back detail, and "not heard" reads as neutral information rather than an alarm, because plenty of setups are transmit-only on purpose.
- Triggers never fire on the house's own transmissions. When HAIR sends a command and a receiver hears the echo, that capture is attributed to the send and routed to the Mirror instead of the trigger and Sniffer pipeline. A trigger bound to a signal now means "when this arrives from the outside world", a physical remote or another app, and cannot feed back on HAIR's own output. The trigger dialog says so when you create one from a Mirror row.
- Clicking the Assign button on a signal that already has assignments opens a small picker: add another assignment, or click an existing one to jump straight to that device's card on the Devices tab. Exactly the flow the Trigger button has had since v0.5.7. The hover tooltip still summarizes the assignments for a quick glance.

### Changed

- Assigned signals stay visible in the Sniffer. Since v0.4.0, once a signal was assigned to a device command, re-pressing that button on the physical remote was silently swallowed, which made the Sniffer look broken exactly when everything was working: you assign a button, press it to celebrate, and nothing flashes. That suppression existed to keep HAIR's own transmissions out of the feed, and the Mirror's echo attribution now does that properly, so the suppression is gone. An assigned button flashes in the Sniffer forever, and a deleted signal row comes back the next time the button is pressed, the same way any signal appears when heard. Dismissing the remote remains the one way to hide activity you do not want to see.
- The row action buttons (Assign, Test, Trigger, Delete, Dismiss) now share one style module across every tab, so the chip anatomy and colors cannot drift apart again.

### Fixed

- The v0.6.1 known issue is retired: a trigger no longer loses its yellow badge when the startup heal merges duplicate rows. The identity matching was already in place end to end; the badge was orphaned because the merged-away row was gone from the Sniffer and the old suppression kept it from returning. With assigned signals staying visible, the next press of the button recreates its row and the badge re-attaches through the decoded identity, which also survives any future heal.

## [0.6.1] - 2026-07-18 -- Hot Towel Finish

### Fixed

- A single jittery pulse no longer splits an NEC button into two rows. Real receivers occasionally deliver a capture where one pulse measures in the dead zone between the protocol's two legal widths while every other pulse is fine; the strict decoder rightly rejected the frame, so the capture fell back to byte-level identity and became a second row for the same button. When the strict decode fails, HAIR now re-reads the frame leniently and accepts the result only if NEC's own built-in checksum validates, so a one-pulse wobble cannot fake a different button and a genuinely corrupt frame still decodes as nothing. Reported by @blalor with two captures of his Previous Track button, which are now permanent fixtures in the test suite.
- NEC captures that start with leftover repeat chatter from a previous press decode now. The decoder used to require the capture to open on the main frame's leader; HAIR now seeks forward past a stray repeat marker or partial burst to the true frame start. This was the class behind several bench remotes whose buttons never decoded.
- Air conditioner devices finally expose real target temperatures. The climate entity has supported temperature presets since the entity work landed, but nothing could create them from the UI. Commands named like "Temp 22" or "Temperature 26" now map themselves to the matching temperature step and register the degree value on the thermostat, the same way "Mode: Cool" and "Fan: High" have always self-mapped. Deleting a temp command retires its step. Found by @ripolltata (GH #45), who read the source and correctly identified a half-shipped feature; thank you for the precise report.
- The thermostat dial is draggable from the start. Without an initial target temperature the dial rendered no handle, and nothing could ever set the first target, so a preset-equipped AC was stuck read-only. The entity now starts at the middle preset; nothing transmits until you actually move it.
- The climate entity follows your installation's temperature unit instead of assuming Fahrenheit. Metric users' presets are Celsius now, as they always should have been.
- Samsung32 captures whose end pulse arrives fused with a following frame decode now. Some emitters replay the whole packet for repeats with no gap at the junction, welding the end pulse to the next frame's leader; the decoder tolerates the fused pulse while the protocol checksum keeps gating every decode. Found on the bench with real captures, which are now fixtures.

### Changed

- The most-recent-hit Assign button in the Sniffer wears a mint rim, and each new hit blooms it into a mint ring. The old pulse used the same green as the button fill, so the halo disappeared into it.
- The adopters table gains SMLIGHT Ultima native receiving (HA 2026.7), the second receiver source after ESPHome.
- The infrared-protocols test dependency cap moved from <8.0 to <9.0; upstream's 8.0.0 changes only Edifier code sets and keeps the command contract.

### Known issues

- When the startup heal merges duplicate rows, a trigger created on one of the merged rows can lose its yellow badge in the Sniffer, because the surviving row carries a different waveform identity. The trigger itself keeps firing normally; only the row badge and count display are affected. A proper fix (triggers following decoded identity, the way commands already do) is planned as its own release.

## [0.6.0] - 2026-07-17 -- Shave and a Haircut

### Added

- HAIR now decodes seven more protocols: Sony SIRC (12, 15, and 20-bit), Symphony (the ceiling-fan family), Philips RC-5 (including the RC5X extension), Samsung32, Sharp, Kaseikyo (the Panasonic family), and Marantz Extended. Until now only NEC signals got a decoded identity; every other remote leaned on the byte-level tiebreaker, which is exactly where the remaining rough edges lived. A decoded signal gets the strongest identity HAIR has: stable per-button matching that survives receiver jitter, clean re-encoded transmit instead of replaying captured timings, and the protocol name on the Sniffer row.
- The decoders live inside HAIR and are written in the shared infrared-protocols library's own style, because that library is their long-term home. Each one is headed upstream as a pull request; whenever a Home Assistant release bundles a library version that can decode one of these protocols itself, HAIR automatically defers to the library for that protocol, no update required. Until then the built-in decoder covers the gap. The diagnostics download lists which source is serving each protocol.
- RC-5 and Marantz remotes alternate a toggle bit between key presses so the receiver can tell "held" from "pressed twice". HAIR now tracks that state per command and flips it on every send, the way the original remotes do.

### Fixed

- One button is one row again, even on remotes without a decodable protocol in yesterday's HAIR. Day-one v0.5.8 reports showed the strict byte-level identity could split repeat presses of a single button into many Sniffer rows: the press length varies, so captures contain different numbers of repeated frames, and on some receivers the pulse widths wobble across a quantization edge between presses. The new decoders read the actual bits instead: a capture is split into its frames, each frame is decoded, and the majority decides, so a two-frame capture, a three-frame capture, and a jittery capture of the same button all produce the same identity. Reported by @loic.gouraud (twelve rows for twelve presses of one button) and @blalor (a duplicate row on an NEC remote) within a day of v0.5.8 -- thank you both for the fast, precise reports.
- Sniffer catalogs that already fragmented heal at startup: the existing load-time merge now runs with decoded identity available, so the split rows collapse into the oldest row, keeping its alias and summing its hit counts.
- The ceiling-fan class from GH #38 decodes now. Symphony remotes send a preamble frame or two and then repeat the button code for as long as the button is held, so every capture used to look different. The majority vote discards the preambles and the truncated tail, and all captures of a button collapse to one row. Thanks @mvdwetering for the ESPHome log that identified the protocol and the preamble detail; your captures are in the test suite.
- Sony remotes transmit reliably from the catalog now: decoded Sony signals re-encode canonical timings on Test and device TX, the same first-class treatment NEC has had since v0.4.0.

### Changed

- Decode-capable protocols no longer market themselves as "NEC today" in the docs. The registry reports itself in diagnostics, including whether each protocol is served by the bundled library or by HAIR's built-in decoder, and whether its transmit path re-encodes or replays raw.
- The infrared-protocols test dependency cap moved from <7.0 to <8.0; upstream's 7.x line keeps the same command contract (verified against source).

## [0.5.8] - 2026-07-14 -- Fine-Tooth Comb

### Fixed

- Triggers can now tell apart buttons on remotes whose signals look alike. Some remotes, Sony being the common one, encode their bits in pulse widths that all fall below the cutoff HAIR uses to sort pulses into short and long, so every button on the remote produces the same coarse pattern. The Sniffer already stored those buttons as separate signals, and their nicknames worked, but a trigger created for one button fired for all of them, which made the whole remote unusable as a control surface for automations. Triggers, the assigned-command matcher, and repeat suppression now use the byte-level identity that sits underneath the coarse pattern, so each button gets its own trigger. Reported by @loic.gouraud on the forum and by @somethingp (GH #43), with the same root cause behind @blalor's Sony remote report.
- Those same triggers now also survive the coarse pattern *changing between presses*. Sony's long pulse sits exactly on HAIR's short/long cutoff, so the identical button can read as one pattern when you store it and as another when the receiver hears it again; on the bench this made only 2 of 4 Sony triggers fire, seemingly at random. Every place HAIR asks "is this the same signal?" -- trigger matching, the assigned-command matcher, Sniffer row grouping, repeat suppression, and the green Assign dot -- now uses one tiered identity: the decoded protocol identity when both sides have one, else the byte-level identity, else the coarse pattern. The byte-level identity survives the flip exactly, so all four buttons fire reliably. Nothing that matched before stops matching: the coarse pattern is only ever consulted when nothing better exists on both sides. This is also @blalor's "hardly ever shows the same signal twice" report.
- Assigning one button on such a remote no longer swallows its siblings. Previously, assigning one signal to a device command made the other buttons on the remote match that command, so they disappeared from the Sniffer and re-pressing them looked like a press of the assigned button. The green Assign dot follows the same rule now, so it appears only on the row you actually assigned -- and both the suppression and the dot survive the pattern flip, so an assigned button no longer reappears in the Sniffer as a brand-new signal.
- A single press on remotes that transmit several frames per press now counts once, even when individual frames of that press land on opposite sides of the short/long cutoff. Sony sends four or five full frames each time you press a button; the dedup window slides and is keyed per trigger, so one press is one fire and one hit. Note for min-hits users on such remotes: one press now counts as exactly one hit, where it could previously count as two or three, so a trigger with a min-hits threshold may need the threshold revisited (it now genuinely means distinct presses).
- Editing a signal's Pronto code now re-points its trigger even when the change does not shift the coarse pattern, which is exactly the case on these remotes. Rewiring carries the full identity, decoded layer included.
- Sniffer catalogs that already contain flip-duplicates of the same button (one row per side of the cutoff) heal at startup: the rows merge into the oldest one, keeping its nickname and summing its hit counts.
- IR receivers are now discovered continuously instead of once at startup. Previously HAIR looked for receivers exactly once, when the integration loaded, so a proxy added later was never heard from until you manually reloaded the integration. Worse, if HAIR happened to load before your receiver's integration on a cold boot, it saw zero receivers and permanently switched to a legacy listening path that the recommended ESPHome configs do not even emit -- the "I installed it and nothing shows in the Sniffer" experience. Receivers are now picked up the moment they appear, released cleanly when they are removed, re-subscribed when an ESPHome device is reloaded or re-adopted (previously the subscription could be left pointing at a dead entity), and a final re-scan runs when Home Assistant finishes starting. The legacy path is now used only where it belongs: on HA 2026.4-2026.5, which lack the native receiver API. Reported twice by @blalor (forum posts #85 and #102) -- the second report is what cracked the first.

### Changed

- Existing triggers are upgraded gently: at startup each stored trigger whose code decodes as a known protocol (NEC today) gains the decoded identity, which is validated by the protocol's own checksum and therefore cannot mis-scope a trigger. The byte-level identity is deliberately NOT retrofitted onto old triggers -- a stored code that was snapped or re-encoded can hash differently from live captures, and a wrong hash would silence the trigger. Old triggers keep their broad matching; triggers created from now on carry the full identity from birth.
- When an upstream decoder for a boundary protocol lands (a Sony SIRC decoder for `infrared-protocols` is planned), the decoded tier takes over for it automatically with no further HAIR changes.

### Added

- Light devices gain Color Temp Warmer and Color Temp Cooler command templates, a `color_temp` command category, and name auto-mapping, so color temperature buttons captured from an IR ceiling light organize themselves like any other command. They are usable today through each command's button entity. Entity-level color temperature control (a temperature slider on the light) is deliberately not exposed yet; doing it honestly needs per-device calibration, and that is being designed separately. Thanks @nogic1008 (GH #40).

## [0.5.7] - 2026-07-05

### Added

- Location-aware triggers. A trigger's event now reports where the signal was received: the event data carries `receiver_entity_id` plus the receiver's `receiver_area_id` and `receiver_area_name`, resolved live from Home Assistant's area registry at fire time. You can now route an automation by room, for example mute only the speakers in the room whose receiver heard the button. Triggers also gain an optional Receiver scope in the trigger dialog: leave it on "Any receiver" (the default, unchanged behavior) or pick one or more receivers so the trigger fires only when one of them observes the signal. A single physical press heard by several receivers fires each matching trigger once. Requested by @blalor, with a workaround and independent endorsement from @Didgeridrew (GH #34).
- Multiple triggers on the same signal are now supported, so you can create one per room with different receiver scopes.
- Spanish (`es`) translation for the config flow and options dialogs. Contributed by @Waterbrain (GH #37, closes #36).

### Changed

- Signal-row indicators are now unified on a single corner-dot pattern. The Assign button shows a green dot when a signal is assigned to at least one device command, with a small count when it maps to more than one; hover for the list. The Trigger button shows a yellow dot, counted the same way, and the old solid-fill "trigger on" styling is gone. The Trigger button opens a small picker when a signal already has one or more triggers, so you can edit an existing one or add another.
- Assign and Trigger indicators now refresh live across browser tabs when a signal's assignments change.

### Fixed

- HAIR panel layout under Home Assistant 2026.7+. The `ha-top-app-bar-fixed` component now expects panel content slotted inside it; HAIR was rendering content as siblings, which caused the empty scroll container to expand to viewport height and push the page content down by roughly 1200 pixels (a sizeable forehead). Panel content is now slotted correctly. No change for users on HA 2026.6 or earlier. Reported by @Didgeridrew (GH #31).

### Added

- HAIR version number is now shown as a quiet centered footer at the bottom of the panel, so the installed version is identifiable at a glance without opening Settings.

## [0.5.5] - 2026-06-24

### Added

- Send times and Ditto count are now editable on every catalog signal (Sniffer, Clipper, Plucker) and every device command. Send times retransmits the full command. Ditto count appends repeat frames after the main frame; some strict receivers, notably commercial audio gear, require at least one to register the command. Both fields are also available in the assign dialog when assigning a sniffed signal to a HAIR device.
- HAIR observes NEC dittos at capture time and shows the count in the signal editor as a hint ("Observed at capture: N dittos"), so you can match Ditto count to what the remote emits.

### Fixed

- The Test button on catalog signals now honors Send times and Ditto count, matching the device-side Test behavior.
- The Ditto count chip on a command row, and the matching editor and assign-dialog inputs, all hide when the command or signal will transmit as raw Pronto (no decoded protocol, or the per-command NEC/PRONTO pill toggled to PRONTO). Previously they showed even though dittos do not fire on the raw replay path.

## [0.5.1] - 2026-06-23

### Fixed

- Tested and newly-assigned NEC commands now transmit clean decoded timings, so receivers that are strict on timing tolerance accept them on the first try. Reported by @frafall (GH #14 follow-up).

## [0.5.0] - 2026-06-22

### Added

- HAIR Plucker. A third capture tab, alongside the Sniffer and Clipper, that pulls IR codes already learned in a vendor blaster into HAIR as native signals, without re-learning each one at a receiver. HAIR registers a no-transmit observer emitter (the HAIR Tweezer) on HA's native `infrared` platform, asks the vendor integration to replay a stored code by name through that emitter, and captures the code before it becomes physical IR. Nothing is broadcast over the air during a pluck, and the blaster keeps working normally. Register a blaster with "+ Add Blaster" (vendor entity plus the appliance name you learned the codes under), then "+ Pluck Signal" with a stored command name. A plucked signal behaves like a sniffed or clipped one: test, alias, trigger, assign, or promote.
- Pluckable vendor registry. The Plucker works with any integration that can replay a stored code by name through a caller-chosen emitter. [Tuya Local](https://github.com/make-all/tuya-local) is the first to support it. Adding another vendor is a single YAML file in `custom_components/hair/pluckable/` with no HAIR code changes. The new guide [Making your integration pluckable](docs/making-your-integration-pluckable.md) explains the service contract for integration authors, and `custom_components/hair/pluckable/README.md` documents the registry file format.
- Blasters (Pluckable) section on the Devices tab. Lists the vendor blasters HAIR can pluck from, with an "Open in Plucker" action on each. Both the Plucker tab and this section appear only when a compatible blaster is configured. The Plucker requires HA 2026.6+ on the receiving side (where the `infrared` platform exports `InfraredEmitterEntity`).

### Changed

- The transmit-mode pill (NEC / PRONTO) and the send-count indicator on a device command now sit on the command name line, just to the right of the name, instead of in the row's action group.
- Refreshed the panel iconography: the Sniffer signal icon, the Devices remote icon, the Plucker tab and Blasters card (tweezers), and the Clipper tab (hair clippers).
- A Sniffer remote now pulses its row background when it receives a signal, which replaces the previous card-border flash. A collapsed card flashes as a whole; an expanded card flashes just its top row, leaving the signal list below readable.
- The "Open in Plucker" and trigger hit-count badges now render in uppercase to match the rest of the panel.

## [0.4.20] - 2026-06-19

### Added

- A single Pronto editor for signals and device commands. The old read-only "copy code" popover and the separate paste-a-signal dialog are replaced by one editor you open from the copy/edit glyph on any Sniffer signal, Clipper signal, or device command. It validates the code live (carrier frequency, burst pair count, S/L diamond preview), recognizes a known protocol as you type ("Recognized as NEC"), grows to fit the code so a long Pronto opens fully visible, and lets you copy the code by selecting it (with a keyboard hint, since the panel runs in a context where the browser blocks programmatic clipboard writes on plain http).
- Edit a stored Pronto in place. Change the code on a Sniffer signal, a Clipper signal, or a device command, and HAIR re-evaluates it as if freshly captured (new fingerprint, carrier, and decoded identity). If the edited signal or command has a trigger bound to it and the change shifts the S/L fingerprint, the trigger re-points to the new code automatically, and the editor names the trigger it moved.
- Snap an off-standard carrier to the nearest IR standard. On the Sniffer, when a captured signal's carrier reads off the common consumer standards, the editor shows an amber notice with a one-click "Snap to N kHz" button that re-encodes the Pronto at the nearest standard (30, 33, 36, 38, 40, or 56 kHz). Useful for a receiver whose frequency detection drifts a little. You review the result before saving.
- Rename a device command. Rename a command inline on its row or in the editor, and any action mappings that pointed at the old name follow it to the new name automatically. The editor names any trigger affected by the change.
- Send a command more than once per press. Each device command has a "Send times" count (1 to 10): set it when you assign the signal, or change it later in the command editor. HAIR transmits the whole command that many times with a short gap between sends, for devices that need a repeat to register. A small orange indicator on the command row shows the count when it is greater than 1. Requested by @AJErazzor (GH #29).

### Changed

- The transmit-mode toggle on a decoded command now reads as the protocol name (for example "NEC") for the clean re-encoded path and "PRONTO" for the captured-replay override, instead of "AUTO" and "RAW". Both states are colored to match the signal's S/L diamonds: blue for the decoded protocol, orange for the captured Pronto.

### Fixed

- Assigning a signal as a standard-action command now wires up the action mapping. Picking a name like "Fan: Auto", "Mode: Cool", or "Power" while assigning previously created the command but left it unmapped, so the ACTIONS button stayed blank and an AC's fan or mode never appeared on the climate entity. The assign path now applies the same auto-mapping the learn path does, including registering an AC's fan and HVAC modes.
- Reordering remotes on the Sniffer no longer snaps back. When the store held a low-hit remote that the Sniffer hides behind its noise filter (or a dismissed remote), the drag list left those out, the reorder was rejected, and the list silently reverted. A reorder now arranges the remotes you can see and leaves the hidden ones exactly where they are.

## [0.4.0] - 2026-06-09

### Added

- Pick a known device when creating a remote. The Create Remote dialog on the Clipper tab gains a Type dropdown: leave it on Blank remote for the usual remote you fill by pasting, or choose a manufacturer and model under "From code library" to materialize a remote pre-filled with one signal per button, each named for its function. The list is whatever device codes your installed Home Assistant infrared library carries (TVs from LG, Samsung, Vizio and Sharp, Sony PlayStation, a few audio and lighting devices). It is a shortcut for the supported devices, not a universal lookup -- anything not listed is still a paste-Pronto away.
- Protocol-decoded matching for NEC-family remotes. When HAIR can read a captured signal as NEC, it records the decoded identity alongside the raw timings. Pressing an already-assigned button is now recognized reliably even when the receiver path jitters the timings, so it no longer leaks back into the Sniffer as an unknown signal.
- Encode-from-decoded transmit. For commands HAIR decoded as NEC, Test and automations send clean, library-encoded timings instead of replaying the captured ones. A per-command toggle (AUTO / RAW) on the device detail lets you fall back to the captured timings for the rare device that wants them.

### Changed

- Transmit uses canonical NEC timings by default for decodable commands, with the per-command opt-out described above. Commands HAIR cannot decode transmit exactly as before.
- The Sniffer empty state now tells "no IR receiver is set up" apart from "no signals yet", so a missing receiver does not look like an idle one.
- The Assign and Trigger dialogs show a signal's name when you have given it one, instead of the raw diamond pattern.
- Diagnostics now report the installed infrared library version and a count of decoded commands by protocol.
- The Clipper now has a persistent "Delete remote" button on every remote, so a remote can be removed in one step instead of deleting each signal first. The confirmation names the remote and how many signals it holds.

### Fixed

- Replaying a captured NEC signal failed against some destinations that expect clean timings (for example a NAD C320BEE bridged setup), because the captured Pronto carried receiver-side timing distortion. Transmitting the re-encoded canonical timings fixes it. Reported by @frafall (GH #14).
- The code-library picker and diagnostics no longer do file-system work on the event loop. Building the manufacturer list and reading the installed library version now run in a worker thread, clearing the blocking-call warnings Home Assistant logged when opening the Create Remote dialog or downloading diagnostics.
- Panel components now register defensively, so a re-evaluated frontend bundle no longer throws a "name has already been used" error in the browser console. The panel rendered correctly either way, but the stray exception is gone.

### Removed

- The Broadlink capture provider. Its learn-mode output was never a sendable IR code, so capturing through it could not work. Broadlink transmit is unaffected. Broadlink receive belongs upstream in the Broadlink integration.

## [0.3.4] - 2026-06-08

### Fixed

- Distinct IR codes that share an S/L fingerprint are now kept as separate signals. Some protocols (the Panasonic and Kaseikyo family, the TCL family, and a handful of similar consumer remotes) have a "long" pulse that sits just below HAIR's S/L threshold, so genuinely different buttons produced the same S/L pattern. The Clipper's duplicate guard then refused the second paste as "already on this remote", and on the Sniffer the two signals collapsed into one. HAIR now adds a byte-level tiebreaker so signals that share a pattern but carry different timing are stored, named, tested, reordered, and assigned independently. Only an identical code is still treated as a duplicate. Reported by @SNMetamorph (GH #13 follow-up) and @akikun21 (GH #16).
- Empty Actions popover on Other-type device cards. The Actions button now hides on devices whose platform (remote) does not expose mappable feature actions, so it no longer opens an empty popover.

## [0.3.3] - 2026-06-07

### Fixed

- Updating a device while its entity was still being registered with Home Assistant could raise "Attribute hass is None for &lt;entity unknown.unknown=unknown&gt;" and roll back the change. The race fired most often when promoting a remote with several commands (each command-add fires a device update before the entity registration coroutine has finished). Affects every HAIR entity platform (media_player, climate, fan, light, switch, cover, remote, button). Each entity's update path now defers state writes until registration completes; the initial state captured at construction time is correct and is written when HA finishes adding the entity. Reported from a Seeed XIAO IR Mate user 2026-06-07.

## [0.3.2] - 2026-06-06

### Added

- Drag-to-reorder across the panel. Drag device cards on the Devices tab, remotes on the Sniffer and Clipper, and the signals within a remote on both tabs. On the Sniffer and Clipper a six-dot grip handle replaces each remote's leading icon (blue on the Sniffer, copper on the Clipper) and a lighter gray grip sits on each signal row; device cards drag by the whole card. The order you set persists across reloads.

### Changed

- The Sniffer and Clipper no longer order remotes by hit count. They use the manual order you set by dragging, and a newly seen remote or newly added signal appears at the top until you move it. Existing lists are seeded once from the previous hit-count order on upgrade so nothing jumps around.
- Renamed the Clipper's add buttons to match the Devices tab. The top-right "Create" is now "Add Remote" (mirroring "Add Device"), and the in-card "Create" is now "Add Signal". The in-card button is a lighter borderless text action instead of a pill.

### Fixed

- The Clipper no longer accepts a Pronto code that is already on the remote. Previously a repeated paste created a second signal with the same fingerprint that could not be used independently and broke reordering. Pasting a duplicate now returns a clear message, and any duplicate created by an earlier version is removed automatically on the next restart.

## [0.3.1] - 2026-06-06

### Added

- A copy control on every signal row (Sniffer and Clipper) opens a small popover showing the signal's raw Pronto code in a selectable box, with a Copy button. Copy works on plain http via a clipboard fallback, and the code is always selectable so you can copy it by hand if needed.

### Changed

- The Clipper's "Create" button moved to the top-right of the tab bar, matching the Devices tab's "Add Device" button (kept in the Clipper's copper accent). The Show Dismissed toggle stays in the Clipper header.

## [0.3.0] - 2026-06-06

### Added

- HAIR Clipper tab. A third panel tab for building virtual remotes by pasting Pronto hex codes, for when you have a code from a converter, a datasheet, or an ESPHome log but no live capture. Create a named remote, then add a signal per button by pasting its Pronto code. The Create Signal dialog validates the code live (a green/red check, the detected carrier frequency, the burst pair count, an S/L diamond preview, and specific error messages that tell you what to fix) and Enter creates the signal once it validates. Pasted signals are first-class peers of sniffed ones: Test, Trigger, Assign, and Promote all work identically.
- Signal aliases. Give any signal a nickname by clicking its S/L diamonds and typing. The alias ("alias" in copper, the name in the diamond blue) replaces the diamonds until you clear it, and an alias never claims to be a command, so the same signal can still become differently-named commands across devices. Available in both the Sniffer and Clipper.
- Two add-command paths on every HAIR device card. The device detail footer now offers "+ Sniffed Signal" and "+ Clipped Signal", jumping to the Sniffer or Clipper so you can add a command by capturing or by pasting.
- The Sniffer signal rows now show each signal's captured carrier frequency (e.g. 38 kHz), matching the Clipper signal rows.
- A clipped remote with no signals can be deleted directly from the Clipper tab (a remote that has signals is removed when its last signal is deleted).

### Changed

- Assigning a signal now keeps it. Previously, assigning a signal to a device consumed it and removed it from the Sniffer or Clipper. Now the signal is copied into the device and stays put, so one signal can be assigned to several devices or as several commands. Only Delete, Dismiss, and Clear All remove a signal, and there is no duplicate guard: assigning the same signal more than once is allowed.
- Clipped (manual) remotes are never auto-evicted. The buffer eviction that ages out old, low-activity sniffed signals now skips manual remotes entirely, so anything you build in Clipper is permanent until you delete it.
- The HAIR Device badge now matches the Promote badge in size and uses uppercase, and the Promote badge moved to a more vivid teal so it reads distinctly from the green.
- Each tab's remote names and cards carry their own accent. Sniffer remote names lead with the blue radio icon and their cards have a subtle blue stroke; Clipper remotes lead with the copper paperclip and a muted copper stroke. The two tabs read as a consistent family while keeping their own identity.
- Remote card titles collapse to a single line (name, counts, and the Promote or HAIR Device badge inline), and the remote name is now edited inline on hover, the same way aliases are, with no pencil icon.
- Header and per-card counts read singular at one ("1 remote", "1 signal", "1 hit").

### Fixed

- The row hover highlight no longer escapes the rounded corners of a card on either tab.

## [0.2.1] - 2026-06-04

### Fixed

- Sniffer would go silent for previously-seen remotes after a specific sequence of dismiss and assign actions, with no UI indication that anything was being dropped. Root cause was an orphaned entry in the persistent dismiss set that survived HA restarts and HACS reinstalls (the device record was removed when the last signal was assigned or deleted, but its fingerprint stayed in the dismiss list). Signals from affected remotes now reach the Sniffer again automatically on the next HA restart after upgrade thanks to a self-heal pass at load time. Reported by @KimmoJ (GH #9) and follow-up by @roblamoreaux.
- Buffer eviction's second pass could independently produce the same orphan when a dismissed device with a low hit count was evicted to make room for new signals. The eviction now skips dismissed devices in both passes.

### Changed

- "Clear All" in the Sniffer now also clears the dismiss list, matching the user mental model of "clear all means clear all." Previously the dismiss list survived Clear All, which contributed to silent orphan accumulation. Users who hit the orphan bug above can use Clear All as an alternative recovery route if they prefer not to wait for the self-heal on restart.
- The Sniffer's Clear All button has moved from the top toolbar to a position below the device list. The Show Dismissed toggle stays in the top toolbar. The relocation pairs visually with the new "clear everything including the dismiss list" semantic and adds a small scroll-past-it speed bump before the destructive action.
- In the Show Dismissed view, the Assign / Test / Trigger buttons on individual signals are now disabled until the remote is restored. Delete stays enabled so users can still clean up unwanted entries. Disabled buttons show a "Restore this remote first" tooltip on hover.

## [0.2.0] - 2026-06-03

### Added

- Native `InfraredReceiverEntity` support (HA 2026.6+). HAIR now subscribes to native receiver entities via `infrared.async_subscribe_receiver()` when available, enabling hardware-agnostic signal capture from any integration that implements the receiver entity. Falls back to the legacy ESPHome event bus bridge on HA 2026.4-2026.5 automatically.
- `NativeCaptureProvider` for capture sessions using native receiver entities. Discovered alongside ESPHome and Broadlink providers in the capture provider list.
- `raw_to_pronto()` encoder function in `ir_command.py` for converting raw signed microsecond timings to Pronto hex strings.
- Native receiver discovery in config flow hardware summary.
- `hair/receivers` WebSocket endpoint for frontend receiver entity listing.
- Receiver section in the Devices tab showing discovered native receiver entities.
- `excludeEntityIds` property on `ir-emitter-picker` to prevent receiver entities from appearing in emitter dropdowns.
- Drag-to-reorder for commands inside a device, backed by `hair/device/reorder-commands` and persisted across reloads.
- NATIVE / BRIDGE badges on receiver and proxy cards so the receive-path migration state is visible at a glance.
- Runtime bridge detection: HAIR listens for legacy `esphome.remote_received` events even in native mode and tags the corresponding hardware so users see which devices still rely on the YAML bridge.
- Device duplicate via `hair/device/duplicate`. Clones a device with all its commands, action mappings, and emitter assignments preserved in one click. Triggers stay attached to the original.
- Sniffer Test emitter picker. Replaces the silent "first emitter on first HAIR device" fallback with an explicit Send from dialog that broadcasts to every picked emitter at once and remembers the choice for the session.
- Card-level duplicate and delete corner actions on every device card so users can clone or remove a device without opening the detail view.
- Quiet blue glow on the Sniffer "Show Dismissed" button when previously hidden remotes are still firing, plus a persistent dot indicator until you click through. Surfaces dismissed-remote activity without re-exposing the signals in the live feed.
- "Show Dismissed" button tooltip reworded to "Restore previously hidden remotes" for clarity.
- Navigation button at the top of the HAIR panel on mobile viewports. Lets phone and tablet users return to the HA sidebar without relying on the edge-swipe gesture. Hidden on desktop.
- `EVENT_DISMISS_ACTIVITY` bus event fired (rate-limited) when a signal arrives from a remote in the dismiss set. Drives the Show Dismissed glow and dot.

### Changed

- Signal monitor refactored with dual-path architecture: native receiver API (primary) with legacy event bus fallback. Shared processing pipeline ensures consistent fingerprinting regardless of receive path.
- Event parser extended with `timings_to_raw()`, `parse_received_signal()`, and `is_native_repeat()` static methods for native `InfraredReceivedSignal` handling.
- Native Timing signals are converted to Pronto hex at the entry point, maintaining fingerprint consistency with the legacy path.
- Capture provider timeout handling improved for Python 3.10 compatibility.
- Panel JS bundle is now read off the event loop during integration startup, silencing HA's blocking-call warning.
- Trigger card trash icon visual style aligned with the device card trash icon for consistency.
- Sniffer signal row mobile layout: on viewports under 768 px, action buttons now sit on a dedicated row below the diamonds and meta instead of floating in the vertical middle of the row. Desktop layout unchanged.

### Fixed

- Missing Device name field in the Assign-to-New-Device dialog on HA 2026.5+. The dialog still used `ha-textfield`, which the same regression silenced for Add Device in v0.1.2 but was missed here. Replaced with a native input element so the field renders on all supported HA versions.
- HAIR Device badge in the Sniffer rendered taller than the Promote badge because the mixed-case text content produced a taller line-box than the uppercase Promote. Added explicit `display: inline-flex; line-height: 1.4` to bound the badge height so both badges read as the same visual weight.

## [0.1.2] - 2026-05-17

### Fixed

- Add "Add Device" button to the tab bar, visible in all states including the zero-device onboarding flow. Previously there was no way to add a device when hardware was detected but no HAIR devices existed yet.
- Fix missing Name field in the Add Device dialog on HA 2026.5+ (`ha-textfield` component no longer renders). Replaced with a native input element.
- Always show the HAIR Devices section header even when no devices exist, with an empty-state hint message.
- Remove redundant floating action button from bottom-right corner.

## [0.1.1] - 2026-05-16

### Fixed

- Fix TX failure on HA 2026.5+ ("Timing object cannot be interpreted as an integer"). The upstream `infrared-protocols` library removed the `Timing` dataclass in v2.0.0, changing `get_raw_timings()` from `list[Timing]` to `list[int]` with signed microseconds. HAIR's `ProntoCommand` and `RawTimingsCommand` adapters now return flat signed integers, compatible with both HA 2026.4 and 2026.5+.
- Add error logging to the send command WebSocket handler. Previously, TX errors were returned to the frontend but not logged in HA logs, making diagnosis difficult.

## [0.1.0] - 2026-05-15

### Added

- Config flow with hardware auto-detection (IR emitters and capture providers)
- Options flow for capture timeout and default repeat count
- Device CRUD via WebSocket API (12 commands under `hair/` prefix)
- Signal Sniffer with real-time IR signal monitoring and device grouping
- Pronto hex fingerprinting with S/L pulse-duration pattern analysis
- Per-signal hit counts, last-seen timestamps, and active indicators
- Inline device rename and promote-to-HAIR-device workflow in Sniffer
- Device-level dismiss/restore for noise filtering
- IR command capture orchestrator with asyncio-based resource locking
- Capture provider abstraction with ESPHome, Broadlink, and Mock implementations
- Multi-emitter TX support (broadcast to multiple IR emitters per device)
- Command template system with device-type-aware dropdown picker
- Action mapping system with popover UI for binding commands to entity features
- Entity platforms: `remote`, `media_player`, `climate`, `fan`, `light`, `switch`, `cover`, `button`
- Device manager with storage-backed persistence
- Admin panel (LitElement/TypeScript frontend) at `/hair` sidebar URL
- Branded header banner on admin panel
- Add Device dialog with name, type, and emitter picker
- Device detail view with inline expand, editable metadata, hardware cards, and command list
- Assign Signal dialog with template command picker and existing/new device modes
- Promote dialog for converting sniffer devices to managed HAIR devices
- HACS compatibility and CI workflow with HACS validation
- Unit test suite (383 tests) covering all backend modules
