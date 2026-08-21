# Changelog

All notable changes to HAIR will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.10.3] - 2026-08-21 -- Broad Sweep

### Added
- Learned-code store pluck: the Plucker reads the IR codes other integrations have stored inside Home Assistant. Broadlink (broadlink_remote_* stores) and Tuya Local (tuya_local_remote_* stores) ship as the first two providers. One card per discovered store in the Add Blaster dialog; one click imports every subdevice as a named plucked remote. Decoded codes re-encode canonically on transmit. Toggle commands import as named pairs. RF codes are counted and set aside with a receipt; failed learns receipt instead of importing; re-plucking a store is idempotent. Store files are opened read-only, always.
- Pluckable registry schema v2: a mechanism field (replay or storage); existing replay YAML is unchanged.

### Fixed
- The Plucker tab now shows when storage-pluck sources exist even with no replay vendor installed.
- Plucked command names now seed the signal alias, so store imports arrive named instead of as bare diamonds.
- The Add Blaster dialog renders its title again on current Home Assistant (headerTitle slot); other dialogs follow in a later pass.
- Plucker signal rows show the protocol pill and TX knob indicators (send times, ditto) like the Sniffer and Clipper.

## [0.10.2] - 2026-08-20 -- Fresh Scent

### Added

- **HAIR reads Tuya codes.** Files for a UFO-R11 or another Tuya IR
  blaster store their codes in Tuya's own compressed form, which HAIR
  could not open, so importing one gave you nothing usable. HAIR now
  reads that form and turns it into an ordinary code like any other,
  which means it can go out of any emitter you have, not just the
  blaster it came from. Sending through a UFO-R11 itself needs nothing
  from HAIR: Home Assistant 2026.8 added infrared support to MQTT, so a
  Zigbee2MQTT blaster shows up as an emitter HAIR already finds.

### Fixed

- **Importing a file HAIR cannot read no longer breaks the panel.** A
  SmartIR file whose codes are in a format HAIR does not understand
  could produce commands with nothing in them, and one of those was
  enough to make the Sniffer, the wig list and every device page answer
  with an error until you restarted, at which point the commands you
  were meant to repair had not been saved at all. A code with nothing in
  it is now simply treated as having no identity, one unreadable command
  is skipped with a note in the log instead of taking the page down with
  it, and cells that cannot be converted are reported as skipped at
  import time rather than turned into codes that transmit nothing.
  Closes #108.
- **The Sniffer files a new signal by what it actually is.** New captures
  used to be grouped by the shape of their radio burst, which two
  different handsets can share, so a new remote's buttons could end up
  spread around or land on another remote's card. A signal HAIR can read
  is now filed by what it says it is, so a new remote's buttons group
  together and stay off everyone else's card. Cards you already have are
  left exactly as they are: nothing is renamed, moved or regrouped, and a
  button you have pressed before goes on landing where it always has,
  keeping its name and its count. If you do want a signal refiled under
  the new rules, delete it and press the button again.

## [0.10.1] - 2026-08-19 -- Split Ends

### Fixed

- **The first press after a restart.** An air-conditioner Remote
  reads its lattice of states the first time it hears something, and
  that read used to happen while the press was arriving, so the press
  itself could be missed. Codes that send a single frame, which is
  most codes from a file, were the ones that lost it. HAIR now loads
  every lattice before it starts listening.
- **Deleting a Device left the Remotes pinned to it looking pinned.**
  The Remote kept the deleted Device on its list, so its card, its
  settings and the Mirror all said it was driving something, while a
  press went nowhere. Deleting a Device now unpins it everywhere, and
  a Remote carrying a pin to a Device that is already gone is tidied
  up on the next restart.
- **Changing a Device's type now gives you the new entity straight
  away.** Setting a Device adopted as Other to Fan, or to an air
  conditioner, saved the change but grew no Home Assistant entity
  until a restart. The old entity is now retired and the new one
  created as soon as you save, on the same device page. Closes GH
  #106.
- **The Remotes add tile reads the same at every count.** On an
  install with no named Remote yet, the dashed tile at the end of the
  Remotes section showed a different, larger, untranslated version of
  itself, and switched to the normal one as soon as a Remote existed.
  It is now the one tile, in your language, always.
- **HAIR now tells you when its catalog stops saving.** If Home
  Assistant refuses to write one of HAIR's files, HAIR raises a
  notification naming what stopped saving and warns in the log, once,
  and clears the notification itself when saving works again. Before
  this, saves could fail silently and captures were quietly not kept.
  One cause of that is closed too: a decoded value too large to store
  can no longer block the file, and the signal is simply kept
  undecoded, with the raw timings that are authoritative anyway.
- **Newer fields survive an older build's save.** Going back to an
  earlier HAIR and returning no longer strips settings the older build
  did not know about.

### Changed

- **The thermostat card follows every HAIR send.** Sending a state
  from the STATE MATRIX card, a saved state, a preset, a command row,
  a button entity, or a press on a pinned handset now moves the
  thermostat card in Home Assistant to what was sent, in the same
  breath as the send. Before, only the card's own controls moved it,
  so the air conditioner and the card could disagree. It follows what
  HAIR sends, not what it hears, and only when the send actually
  reached a blaster. Where a Device has power monitoring, the power
  sensor still has the last word on whether the unit is on or off.
  Closes GH #105.

## [0.10.0] - 2026-08-18 -- Remotes Have Been Buffed

### Added

- **Devices and Remotes.** The Devices tab now splits in two.
  DEVICES are the things HAIR sends codes to, a television or an air
  conditioner. REMOTES are the handsets HAIR recognizes: press a
  button on one and it fires a trigger you can automate on. HAIR
  Triggers, the catch-all that has always been there, is simply the
  first Remote in that section, and every Remote you make is its own
  device in Home Assistant, so its buttons appear by name in the
  automation editor's Device trigger list. The "+ Add" buttons are
  gone: the last tile in each section is a dashed tile you click to
  add, or drop a code file onto (a wig, a SmartIR file, a Flipper
  .ir, a LIRC conf, a Girr export) so the add dialog opens already
  filled in. One dialog serves both, with a source picker (the
  Closet, the Sniffer, the Clipper, the Plucker, an existing Device
  or Remote, or Manual) and the hardware in the same place: emitters
  for a Device, receivers for a Remote. Wherever HAIR shows a set of
  codes the button now reads USE and asks which of the two to make,
  with a count dot saying how many you have already made from that
  set. A Device's settings can build the matching Remote, a Remote's
  settings the matching Device. Making a trigger now asks which
  Remote owns it, HAIR Triggers by default; only HAIR Triggers
  offers a receiver picker, since a named Remote's triggers follow
  that Remote's own receivers. Requested by @Spamfast (GH #69), whose
  EyeTV-remote-as-keypad thread on the HA forum started this whole
  release, and by StePhan McKillen on the same thread.
- **Pin a Remote to a Device.** Pressing the handset then sends the
  matching command out that Device's emitters, with HAIR working out
  which button matches which command. Open the PIN row on a Remote's
  header or the PINNED row on a Device's and tick the other side.
  One Remote can drive several Devices and one Device can be driven
  by several Remotes. HAIR never re-fires its own transmissions, so
  a pinned handset sitting next to the receiver does not loop; if a
  pairing ever does run away, HAIR cuts that one pairing for a
  minute and writes a warning naming the Remote, the Device and the
  command, while the handset keeps firing its triggers throughout.
  The Mirror marks pinned sends with their own chip. Requested by
  @bwarden (GH #90), who wanted a DVR remote heard in one room to
  drive the DVR in another.
- **Air-conditioner handsets can be Remotes.** An AC Remote carries
  the same STATE MATRIX card an AC Device has, but for listening:
  press the handset and the mode, fan, swing and temperature it sent
  light up together and stay marked, with a LAST HEARD row naming
  the last state, when it arrived, and which receiver heard it.
  Browse to a state and click + Trigger to fire on exactly that
  state; the trigger carries a STATE chip. For every state at once,
  the Remote's Home Assistant device offers a "State heard" trigger
  that fires on any state and hands mode, fan, swing and temperature
  to your templates. Pin an AC Remote to an AC Device and every
  state the handset sends is re-sent by the Device, so Home
  Assistant and the wall remote never disagree. There is no SEND on
  a Remote's card by design; the handset is the test.
- **Thermostat presets by star.** Every command row on an
  air-conditioner Device has a star. Click it and that command
  becomes a preset on the thermostat card in Home Assistant, named
  what the command is named; click again to remove it. It works for
  learned commands and for states saved out of the STATE MATRIX card
  with + Command. Presets are local to the device and do not travel
  with a wig. Requested by @mode0192 (GH #96) as native AC favourites;
  the listening side of an AC Remote covers the state-tracking half of
  that request.
- **Ten languages.** Every new word in this release is translated in
  all ten panel languages, including the "State heard" trigger name
  as it reads in the automation editor.

### Changed

- **Codes that came from a file now recognize the real handset.**
  Remotes and triggers made from a wig, from the Clipper or from the
  Plucker now match the real handset over the air, and a Device made
  from a wig recognizes its own handset's presses for pinning.
  Before this release only codes HAIR had learned through a receiver
  matched reliably. HAIR compares the shape of the signal for
  file-sourced codes, which is tolerant of the small timing
  differences every receiver adds; codes learned through a receiver
  are unchanged. Air-conditioner handsets send the longest codes,
  and this is where the difference shows most.
- **Mirror filter, settings, headers and finish.** The Mirror's
  filter row is now four pills, Search, All, Not heard, and an
  Emitter dropdown listing every emitter with its count, and it
  neither grows nor wraps however many emitters you have. Device and
  Remote settings share one layout: sections with dividers, and a
  footer reading Delete on the left, Duplicate and Save on the
  right. Device and Remote headers line their rows up, with a
  Device's type under its name and the close and settings controls
  in the same corners on both. The dashed add tile sits back until
  you hover or drag onto it and names the file types it takes,
  Create is green in every create dialog, and a long emitter name
  shortens with the full name on hover.

### Fixed

- **A tap counts once, a hold steps.** A single tap on a handset
  now counts once and holding a button steps about three times a
  second, through its trigger and through any Device it is pinned
  to, where handsets that repeat their whole code while held
  (Samsung televisions among them) could previously count one tap
  two or three times.

## [0.9.10] - 2026-08-10 -- Quick Wash

### Fixed

- **Broadlink RM4 Pro commands work again.** The 0.9.8 change that
  trimmed the leftover capture pause for Zigbee blasters left
  outgoing codes with no trailing pause at all, and RM4 Pro
  firmware garbles codes that end that way. Sends now finish with
  a short bounded pause that satisfies both the RM4 Pro and the
  Zigbee 16-bit limit. Files imported under 0.9.8 or 0.9.9 heal
  automatically; nothing needs re-importing. Reported by
  @Lilian877 (GH #98).

## [0.9.9] - 2026-08-10 -- Straight Iron

### Fixed

- **Linked room sensors now update the climate card the moment the
  sensor changes.** The 0.9.8 sensor mirror read the linked
  temperature and humidity sensors correctly but never announced a
  new reading to Home Assistant, so the climate card kept showing
  the last value it had been told about until the next command or
  power correction happened to refresh it; the HAIR settings
  dialog, which reads the sensor directly, looked right the whole
  time. The card now updates the instant the sensor does, including
  right after a restart. Reported by @mode0192 (GH #91) the same
  day the feature shipped.

## [0.9.8] - 2026-08-09 -- Wig Primping & Device Settings

### Changed

- **A wig is a perfect fit or it is nothing -- the fitted tier
  retires.** The Validate for Perfect Fit checklist now starts every
  row grey and unchecked instead of pre-checked: the click is the
  attestation, so the default claim is nothing until you make it.
  Signing only arms once every row carries a claim; there is no
  longer a partial "fitted" save on a flat wig. Exclusion reasons
  ("not on my device", "could not make it work") are now offered
  only on a matrix's dimension checklist, where a lattice genuinely
  cannot be edited cell by cell the way commands can -- a flat wig's
  rows are either checked or left for another day.
- **Download names, closet ticks, and supersede warnings all speak
  the same two words now.** The `-fitted` download suffix, the
  amber "scoped" closet tick, and the matching supersede-warning
  tier are all retired along with the fitted tier itself. A wig's
  download is `-perfect-fit` or plain; its closet row shows the
  perfect check or nothing. Older files that already carry a
  partial attestation still parse, still count in the ledger, and
  still show there as "Incomplete" -- this only changes what the
  authoring UI can produce going forward.
- **Command rows keep a constant height now.** The code fingerprint
  (the S/L diamond pattern on a captured Pronto command) moved to
  its own line under the row instead of stacking under the name, so
  a long AC/matrix code no longer stretches the row taller than its
  neighbors. The drag handle moved up to sit beside the name that
  goes with it, rather than floating at the center of however tall
  the row happened to be.
- **Sends no longer carry the leftover pause from a Broadlink
  capture.** A code learned on a Broadlink RM ends with about 100ms
  of silence baked in by the device's own capture timeout, not part
  of the signal. HAIR used to send that pause along with the code;
  some 16-bit emitters (Tuya and ZoSung blasters reached through
  Zigbee2MQTT, for example) rejected the whole code outright once
  the pause pushed a value over their format's limit. Sends now stop
  at the last real mark instead. A newly imported SmartIR file also
  stores its codes without that pause, so the same source file
  imported before and after this version yields two distinct wigs --
  deliberate, and supersession is there to resolve it if the two
  ever meet in the same shop. Reported by @yacinbm (GH #93).
- **State-matrix devices get a Power row, and their type stops being
  editable.** The STATE MATRIX card now shows an Off chip above Mode
  (and an On chip too, for the rare unit that needs an explicit wake
  code) -- pick one to send or save a power press the same way a cell
  already could; picking a power chip and picking a cell are mutually
  exclusive, and the Set line always names whichever one Send would
  actually send. A matrix device's Type field is now a fixed label
  instead of a dropdown: the lattice only exists because the device
  is an air conditioner, and changing the type out from under it used
  to tear the climate entity down mid-flight and orphan the cells, so
  the control that could do that is gone.

### Added

- **The comb gate.** A comb-flagged cell now has to be attested
  before a matrix fitting can sign: on a matrix, flagged cells join
  the checklist as their own coordinate-named rows, check only, no
  exclusion picker. Testing a flagged code and finding it works is
  enough to check it and move on; a code that really is broken gets
  fixed on the device and the repair rides the usual porthole path.
  Flat wigs mark a comb-flagged row so the fitter can see which ones
  earned the suspicion, though every row there needs a check either
  way.
- **A settings button on the device detail page, and a power sensor
  behind it.** Devices that can plausibly draw current (AC, media
  player, fan, light, switch) now show a small settings icon beside
  the emitter picker. It opens a dialog where you can point a power
  sensor at the device and set two thresholds in watts: the device
  is treated as off at or below the lower one and on at or above the
  higher one, with a live reading shown once a sensor is picked.
  Readings from a configured sensor override the device's assumed
  on/off state, including across a Home Assistant restart -- so a
  device switched off with its own remote no longer sits there
  claiming to be on until the next command is sent.
- **Assumed state now survives a restart.** Switches, lights, fans,
  media players, and climate devices restore their last-known state
  when Home Assistant restarts, instead of resetting to a blank
  default. A configured power sensor still gets the final say once
  it reports in.
- **Climate devices can show a room's actual temperature and
  humidity.** The same settings dialog gains a second section on
  matrix-based climate devices: point it at a temperature sensor, a
  humidity sensor, or both, and the thermostat card shows a live
  reading under each once picked. Display only -- nothing here
  changes what HAIR sends or assumes, and a sensor reporting in a
  different unit than the installation converts automatically.

### Fixed

- **A state-matrix climate device's saved temperature could drift to
  nonsense across repeated restarts.** Home Assistant reports a
  climate entity's temperature in the installation's display unit;
  restore was storing that number straight into the entity's native
  setpoint without converting back, so a matrix device whose file
  unit differs from the installation's display unit compounded one
  unconverted conversion every restart (23C became 73.4, then 164,
  then 327, and on). The entity's target temperature now persists in
  its own native unit across restarts, converts only on the one-time
  fallback for an entity that has never done so yet, and clamps to
  the device's own range regardless of source, so any setpoint
  already corrupted by this self-heals to a sane value the next time
  Home Assistant restarts. Preset-mode climate devices were never
  affected. Flagged by a live bench review after this release's other
  changes had already been verified; caught before release.

## [0.9.7] - 2026-08-07 -- Second Fitting

### Added

- **Save to Closet now asks what you mean, up front.** Clicking SAVE
  TO CLOSET opens a small decision window with three routes and a
  one-line summary of how your device differs from its wig. **Save
  as New** mints a fresh wig and leaves the existing one alone --
  with a name prefill that steps around collisions. **Update Closet
  Wig** brings your existing file up to match the device: a simple
  edit when nothing changed, a full replacement when it did, with
  the stakes named before you commit -- which signals are added or
  removed, and whose fittings would retire. **Validate for Perfect
  Fit** is the ceremony: every signal vouched with TEST in reach, a
  "Changes with new fitting" section showing exactly what this
  fitting adds and removes, and your signed claim bound to the file
  it describes. A device that never came from a wig simply offers
  Save and Perfect Fit; there is nothing to update.

- **A wig remembers where it came from.** A replacement carries its
  full ancestry, so a closet that still holds any ancestor
  recognizes the successor on arrival and offers to replace rather
  than file a twin: the old file steps aside, devices repoint to
  the successor, and the new commands can be sent to those devices
  in the same step. Importing an ORIGINAL after its successor is
  already on the shelf warns the other way around. Keep Both and
  Cancel are always one click away, and nothing is ever deleted
  without saying so first.

- **One person, one current word.** Fitting a wig you already
  proved -- same install, unchanged content -- now replaces your
  earlier signing rather than stacking a duplicate, and the fitting
  window says so before you sign: "You've already proven this wig."
  Your green check, and who counts as "you", now key on the
  install's signing key rather than the typed name.

- **Download names come from the wig itself.** Composed from brand,
  kind, and model, with the fitting tier as a hyphenated suffix
  (`-fitted`, `-perfect-fit`) drawn from the wig's own claims -- so
  the filename can never disagree with what the file proves, and
  the shop accepts it as named.

- **Air conditioners are full citizens of all of this.** Matrix
  wigs walk every save route, and a TEST press on a climate cell
  now reports sent/heard like any other signal when the receiver
  hears the echo.

### Changed

- **The panel got a smaller hat.** The banner image is replaced by
  a compact brand block aligned with the content, returning that
  screen space to your devices.
- A general polish pass across the save dialogs and receipts:
  replace receipts are a single plain notification, warnings say
  their piece before the save instead of after, helpers and combing
  reports sit where and how you expect them, and copy is tighter
  across all ten languages.

### Fixed

- Saving a matrix wig through the new routes could fail with an
  unknown error while still writing the file.
- The confirmation after a save could be torn down before it ever
  painted, on all three routes.
- The Update route could stay hidden until a hard page refresh
  after saving a new wig.
- Deleting a wig left devices holding a pointer to the deleted
  file.
- The closet's "used by" chip could light up on both an ancestor
  and its successor for the same device; the device's own record
  now decides.

## [0.9.6] - 2026-08-04 -- Hotfix: unknown is not down

### Fixed

- **A fresh install could not send its first command, ever.** An infrared emitter's state is the timestamp of its last send, which means it reads "unknown" until the first command goes out. HAIR's emitter pre-skip treated "unknown" like "unavailable" and skipped it, so on a clean setup every emitter was skipped and every send failed with "All emitters unavailable" -- the first command could never happen because no command had happened yet. Existing setups hit the same wall after a restart. Only genuinely unavailable emitters are skipped now; a never-used emitter gets its chance, and an emitter that is actually dead is still caught by the per-send guard that was always the real protection. Reported by @Lilian877 and @Warpshock (GH #83), whose cross-hardware reports made the diagnosis quick.
- **The emitter picker painted never-used blasters amber.** The same wrong assumption in the panel: a brand-new emitter showed as Unavailable before it had ever been asked to send anything. It now shows as On, which is the truth -- unproven is not broken.

## [0.9.5] - 2026-08-03 -- The Fitting Room

### Added

- **Proving a wig is now something you do on the device, not in a dialog.** The old fitting room was a separate session with its own row of controls, its own send button and its own idea of what "worked" meant, and it sat between you and the device rather than on it. It is gone. You adopt a wig, press the buttons on the real device the way you would use it, and sign once at SAVE TO CLOSET. The attestation is a checklist of the rows you are claiming, next to the tick that arms it.
- **An attestation is now a set of claims about rows, not a claim about a file.** Every row carries a digest of its transmit recipe -- the bytes, the repeat frames, and whether the encoder is bypassed -- and a claim binds to that. Edit one code and every other claim on the file survives, where before a single change invalidated the whole attestation. Renaming a row survives too, because names were never in the digest.
- **A row you do not have is no longer a row you failed.** A claim can say a code worked, or that it is not on your device, or that you could not make it work. The last two are exclusions rather than failures, so a person with the two-button version of a remote can honestly attest the buttons they have.
- **The fittings count on the save dialog is a door.** It said how many people had proved the wig and left them unreachable. Clicking it opens the ledger: who attested what, when, whether they signed, and per-row verdicts including the rows they deliberately excluded. A claim about a row whose bytes were edited afterwards is shown as orphaned rather than quietly dropped, because somebody really did prove that recipe.
- **The comb report leads with what a finding does to you.** Three buckets, worst present first: will do the wrong thing, will be ignored, cosmetic. Only one class of finding makes a device answer a press and land in the wrong state, and it now says so instead of sitting in a card that looks like all the others. An empty bucket does not render, because a card reading "0 will do the wrong thing" is reassurance wearing the costume of a warning. The count carries a denominator, since 48 findings is catastrophic on a seven-button remote and unremarkable on a 750-cell lattice.
- **Combing a class opens into facts rather than repetitions.** Twenty-two frame-shape findings on one air conditioner turned out to be three facts: eleven codes sending one burst pair too many, ten sending two, one sending three. Findings that say the same thing are now grouped under that sentence once, with their coordinates listed beneath it.
- **The comb report says where the flagged codes actually are.** Under the footer there is now a line telling you either to adopt the wig, and that every flagged code becomes a row on the device wearing a comb glyph, or that they are already rows on a named device, with a button that takes you there. That a comb suspect surfaces as an ordinary command row is the thing nobody would guess.
- **Some codes have to be sent exactly as captured, and a wig can say so.** When HAIR recognises a signal it rebuilds it cleanly from the decoded value instead of replaying your recording, which strips receiver noise and is almost always the right thing. It is the wrong thing when a remote's repeats are baked into the capture: a fan that wants six frames gets one and does nothing. The per-command raw switch already existed, but it lived on the device and nowhere else, so the knowledge died the moment you shared the codes. Signals now carry the choice themselves, from the Sniffer or Clipper where you first meet the problem all the way into the wig, and it sits inside each row's transmit recipe, so a claim binds it. A wig you repaired arrives working for the next person.
- **A wig carries the whole recipe for sending its codes, not just the codes.** Some receivers refuse a lone frame: they want the repeat pattern a real remote sends when you hold a button down, and a code rebuilt as one clean frame does nothing. That repeat count now travels in the wig and sits inside each row's digest, so a code proven with its repeats is proven with its repeats on every install.
- **Send counts stopped being part of a wig's identity, on purpose.** How many times to press is about your room, not about the device: distance, blaster power, the angle through a cabinet door. Five people proving the same codes at three, four and five sends are proving the same rows, so their claims accumulate on one file instead of forking it five ways. The count still travels as the author's suggested floor.
- **The protocol chip is everywhere the codes are.** The pill that shows what a signal decoded as, and lets you switch it to raw, sits on Sniffer rows, Clipper rows and device commands alike. It reads BYPASS when a code is pinned to raw, and it is not there at all when nothing decoded.
- **Set a signal to send twice and you can see that you did.** The send-count and repeat markers that device commands have always shown appear on Sniffer and Clipper signals too, following the same rules everywhere, including staying hidden on a code pinned to raw, where repeat frames never reach the air and showing a count for them would be a lie.
- **Combing runs itself the moment a wig arrives.** Drop a file into the closet, or adopt one into a live device, and the report opens on its own. Those codes have never been checked against each other on your install, and finding out that 48 of them disagree is worth knowing before you start pressing buttons rather than after.

### Changed

- **Emitters are cards you turn on and off.** The dropdown that spent a chip announcing what it had just added is gone. Every emitter you have is shown, and being assigned is simply the chip being on. They were never a choice between blasters -- HAIR broadcasts to all of them and succeeds if one lands -- and the old shape said otherwise.
- **An unreachable blaster now says so.** Home Assistant already knew which emitters were unavailable and HAIR already skipped them when sending, and the panel had never mentioned it: a device could list a blaster that had been unplugged for a week with nothing on screen to say why nothing happened. An assigned emitter that is not answering is amber now.
- **Row-level DELETE is a trash can.** Nine of them, in the Sniffer, Clipper, Plucker, Mirror, closet and device rows, where a word cost more room than it earned among four other controls. Everything that deletes is now the same ember colour whether it wears a word or a can. The seven page-level and dialog deletes keep their words, and so do the three CLEAR ALLs, which mean something different.
- **The device page's type and emitters stopped looking like a form from 2004.** An 80px column was reserved for two words, leaving the controls floating in whatever was left. Each label sits above its own control now.
- **The install instructions moved above the fold in all ten READMEs,** and HAIR is in the HACS default store as of 2026-08-01, so they no longer tell you to add a custom repository.
- **Wigs written by this release need this release.** The file's format stamp moved to `hair-wig/3` and older HAIRs refuse it with a message asking you to update. That refusal is the feature: this release changed how a row's identity is computed, and an older install would compute the old answer and tell you a perfectly good file looked tampered with.
- **ADOPT DEVICE is now just ADOPT.** The noun was doing no work next to a device card, so the Sniffer, Clipper, Plucker and Closet buttons all shortened together.
- **Repeat frames are an NEC feature, and HAIR says so.** The ditto count used to be offered on any signal HAIR could decode. Only NEC appends the short repeat frame the setting describes; on other protocols the same number either duplicates the whole signal, which send times already do, or does nothing. The setting now appears only where it means something, and existing values are still shown wherever they were set.
- **The closet takes one file at a time.** It used to accept a whole handful, hang every one of them, and then tell you about the last, with the others arriving unreceipted. Dropping more than one now politely declines the lot, so nothing lands that you did not see land.
- **The protocol chip moved off the command name and into a column,** so it stops sliding left and right down the page as command names change length and lines up with the edit glyph the way the Sniffer and Clipper chips already did.

### Fixed

- **A matrix wig could never show which device it was adopted into.** The match between a wig and its devices walked the wig's flat signals, and an air conditioner wig has none -- its codes are lattice cells, and cells are not commands, so there was nothing on either side to compare. Every matrix wig read as adopted by nobody, forever: the closet's linked chip stayed dark and the adopt popover never appeared, no matter how many times you had adopted it. Devices have recorded which wig they came from since 0.9.5, and the match now uses it.
- **Exporting a matrix device dropped the lattice.** A device export of an air conditioner wrote the flat extras and left the state matrix behind, so the file described a remote with a power button and nothing else. **Anything you exported from an air conditioner before this build should be exported again.**
- **The ledger opened behind the dialog that opened it.** Home Assistant 2026.7 moved its dialogs into the browser's top layer, which sits above every z-index there is, so the ledger was both invisible and unclickable. Closing it also used to close the save dialog with it, losing the form you were filling in.
- **The Plucker's CLEAR ALL was never translated.** It shipped a hardcoded English string where both its siblings did the right thing, so it read "Clear All" in nine languages.
- **The device page's DELETE DEVICE wore a dialog heading's label,** which meant neither surface could ever be worded for where it sits.
- **The trigger trash in the device list was not a button,** just an icon with a click handler, so it had been unreachable by keyboard for as long as it had shipped.
- **A comb report on a large lattice ran off the bottom of the screen** with nowhere to scroll, losing both ends of itself on a laptop.
- **Closet rows line up.** Library rows carry no DELETE and no comb glyph, and because a row's buttons anchor to its right edge, every absence dragged the rest sideways. Missing controls now hold their places, empty.
- **Code-checker findings sit next to their explanation.** The finding's name and its diagnosis were separated by a gutter sized for the longest name any remote could produce; the column is now as wide as the names actually present.
- **A raw pin on an air-conditioner state is refused, not swallowed.** A state matrix has nowhere to record a per-cell raw pin, so the request used to be accepted and silently discarded. The API now refuses it and the panel no longer offers it.

## [0.9.1] - 2026-07-31 -- Smart Perm

### Added

- **Fix a bad code from inside the fitting.** Every fitting row grows a fourth button, REPLACE, alongside Send / Worked / Did not. Open it and a strip appears under the row with a box for a Pronto code and a LISTEN button: press LISTEN, point the real remote at one of your receivers, press the button, and the capture lands in the box for you to look at before anything is saved. On a matrix wig the strip tells you which state to set the remote to first, which is what makes a captured cell the strongest repair there is -- the remote's own display is the state, so what it sends is the cell, whole and correct. A capture that did not decode cleanly is flagged and still allowed; the button reads "Replace anyway" and the send-and-judge loop is right there to settle it.
- **Your other verdicts survive the repair.** Replacing a code changes the wig, so its identity changes with it and fittings that attested the old codes are marked outdated. That is the tamper evidence doing its job, and it used to mean starting over. Now the session you are in follows the change, and the next session you start seeds itself from your last fitting for every row whose code is byte-for-byte what it was. Only the rows that actually changed come back untested. One bad button on a 288-signal remote is fit-one-and-re-sign, not fit-288-again.
- **Changed codes get proved.** On a matrix wig, a replaced cell that the dimension checklist does not already sample is listed in a new **Changed codes** section at the bottom of the session, with the same four buttons as any other row. The checklist samples dimensions; this is where the cells you touched by hand get their own confirmation.
- **And you can take a replacement back.** Every replaced row keeps the code the wig came with. Hover its chip and it offers to put that code back; click twice, and it does. It reaches past however many times the row has been replaced, so it always returns the file's own original rather than the last repair attempt, and it stays available after you have signed a fitting -- a capture you proved and later found wrong is still fixable. Putting a code back rolls the identity to what it was, which correctly marks any fitting that attested the replaced code as outdated.
- **Discard means none of this happened.** Discarding a session now puts back the codes it replaced, not just the verdicts about them. Signing is what makes a repair permanent to the session; a row somebody else has replaced since is left alone.
- **The ledger points at what failed.** A failed count on a ledger row is now a link: it opens the session at the first row that fitting failed, with Replace one click away.

- **Combing: find out what is wrong with a file you just imported.** Five of six real SmartIR climate files carry defective codes, and they survive conversion perfectly because conversion is a transcode and transcodes are supposed to be faithful. They are invisible to a human reading the file and invisible to a fitting, which attests dimensions rather than individual cells. HAIR now **combs** every wig as it is imported and tells you what it found: frames that are short or malformed (the device silently ignores the press), a cell that sends its neighbour's code (the device responds and looks like it worked while setting the wrong state), holes in a temperature run, states nothing advertises, and duplicate coordinates. None of it needs a protocol decoder, so it works on vendors nobody has written one for.
- **A comb in the closet row.** Every wig row grows a comb beside the download glyph, in the same quiet grey as the others. It picks up a yellow glow when combing found something and a red one when a cell is sending its neighbour's code, which is the class worth interrupting you for. Clicking it combs the wig and opens the report. A wig nobody has combed looks the same as a clean one deliberately, because absent is not the same as clean, and the tooltip says which.
- **Bigger files can be dropped.** The drop zone accepted 1 MB of text where the format itself allows 16, so the largest climate files -- exactly the ones most likely to carry defects -- could not be imported by dropping them. That is now 4 MB. Anything larger still goes in through the `hair/wigs` folder.

### Changed

- Replacing a code with the code already on that row is refused rather than silently recorded, so a provenance marker in a wig file always means the codes genuinely changed.
- SmartIR sequences that repeat one code are still folded into a send count, but the fold is now named in the import receipt instead of happening quietly. It is the one place import transforms rather than transcodes.

## [0.9.0] - 2026-07-30 -- Fine-tuned Fittings

### Added

- **A device that needs three presses can now say so.** Some devices miss a single IR send and respond every time at three -- a fact about distance, blaster power, and angle, not about the codes. The fitting session grows a **send times** control: raise it when the device misses, and every send in the session transmits that many times. What you used is recorded on the fitting as `send_times_used`, inside the signed entry, so the evidence travels with the wig. The record only ever rises during a session (a signal proven at three stays claimed at three, even if you drop back down for the next one), and it survives a Home Assistant restart mid-fitting.
- **The next person's adopt picks it up.** ADOPT DEVICE now seeds new commands -- and every cell of a matrix wig -- from the highest send times any fitter needed, so a wig fitted at three answers the first press on a fresh install with nothing to tune. The wig's own per-signal `send_count` still wins where it is higher, and the value is clamped to 1..10 everywhere it is read.
- **The ledger shows the evidence.** Fittings that carry the field display "at N sends" alongside their coverage. Fittings recorded before this release show nothing there, deliberately: absent means unknown, not 1, so old fittings never silently claim a measurement they did not make.



### Fixed

- **The startup freeze at flood scale.** `SignalStore.async_load()` ran its duplicate-healing pass directly on Home Assistant's event loop, and the pass was quadratic. Once the unknown-signal store grew large enough, every boot froze all of Home Assistant -- HTTP included -- for the duration; at 104,000 stored signals that was about 15 minutes of apparent death per start, with no warning from HA's blocking-call detector because the work is pure CPU, not I/O. The load transform now runs off the event loop in an executor job, and the heal is rewritten from pairwise rescans to hash lookups with identical merge results (pinned by test against the old algorithm). The same 104k-signal store now heals in under a second, and a store of any size can no longer stall the rest of Home Assistant. Reported by @carlmiller99 (GH #72) with a py-spy-profiled analysis that isolated both the freeze and its root cause; this release exists because of that report.

### Changed

- **HAIR no longer listens to RF receivers.** Combined RF/IR hardware (Athom's RF IR Remote and similar ESPHome `ir_rf_proxy` builds) can expose its RF receivers as `infrared` platform entities, and HAIR subscribed to every receiver in the domain. That was the root cause behind the freeze above: ambient radio chatter is not IR, never decodes, and on the reporting install minted 500 phantom remotes and 340MB of stored noise in 33 hours. HAIR now skips receivers that read as RF (by registry naming: an `rf` token or an MHz-band token such as `433mhz`, without an `ir` token) at subscription, in capture-provider discovery, and in the receiver picker, logging each skip once. Stated plainly: if you were deliberately sniffing RF remotes through one of these receivers, those captures stop with this release, and there is no toggle to bring them back yet. RF as a proper, explicit opt-in is on the roadmap; excluding it silently by default is the honest interim, because HAIR cannot decode or replay what it was storing. The Home Assistant core platform currently exposes no attribute distinguishing RF from IR receivers, so naming is the discriminator available; if a receiver of yours is wrongly skipped, the log line names it and an `ir` token in its name restores the subscription.

### Added

- **The unknown-signal store is capped.** Two new bounds on sniffed signals: 200 per remote and 20,000 total (the existing 500-remote cap stays). When a cap is hit the oldest signals are evicted first, aliased rows last, and a warning names the remote and the receiver it was heard by. Clipped and plucked remotes are user creations and are never touched. Eviction is capacity protection, not hiding: an evicted signal reappears the moment its button is genuinely pressed again. A store already past the caps is trimmed once at load, so an install sitting on a flooded store recovers on its first boot after upgrading with no manual `.storage` surgery.



### Added

- **SmartIR climate files now import.** Dropping a SmartIR climate JSON on the closet converts it into a wig carrying a structured state matrix instead of refusing it. The importer walks the file the way the corpus is actually shaped -- mode, then fan, then swing, then temperature, with depth detected per branch -- keeps every mode, fan, and swing word verbatim, and brings the file's flat extras (sleep timers, LED toggles, one-shot codes) across as ordinary buttons riding alongside the matrix. Matrix wigs write the new `hair-wig/2` format; everything else stays v1, so older installs keep reading the wigs they already have. Documented in [the wig format](docs/wig-format.md). Together with the adopt path below, this answers the standing stateful-remote request (GH #62, thanks @avonpohle).
- **Adopt a matrix wig and you get a fully-controlled air conditioner.** ADOPT DEVICE on a climate wig creates a real `climate` entity where every combination of mode, fan speed, swing, and temperature is one complete IR code: each change resolves to its exact cell and transmits the whole state, the way AC remotes actually work. Swing and temperature controls light up only when the matrix carries those dimensions. The matrix is stored as its own file next to the device, so renaming a device never rewrites megabytes of Pronto.
- **Dimension-check fittings.** Fitting a 300-state matrix does not mean 300 sends. The session builds a checklist of 12 to 20 sends that walk every mode, every fan speed, every swing position, and the temperature extremes -- each dimension proven along its own axis stands in for the lattice, and the claim sentence in the dialog says exactly that. A fitted matrix wig keeps the green check and wears a cold blue glow, the stateful signature.
- **The state matrix card.** A matrix device's detail page grows a cold-blue STATE MATRIX card: browse the lattice one branch at a time (mode, fan, and swing chips, then that branch's temperatures as tiles, with the state the entity last transmitted wearing the glow), set a state and SEND it, or press "+ Command" to save the state as a named command. Saved states land in the commands list with a small STATE chip and work everywhere a command works. The Map action is absent on matrix devices on purpose: matrix climate reads the matrix, never the mapping.
- **CLIP on matrix wigs, gated.** Clipping a matrix wig onto the Clipper is back, behind a confirm that counts what it will mint -- "up to" N signals, an honest ceiling, with a slow-to-browse warning on the big ones -- because 2,689 rows should be a choice, not a surprise. Minted rows are named in the state grammar ("cool / fan: auto / 22"), and the clipped remote carries a stamp back to its source wig.
- **The adopt signpost.** Adopting a wig-stamped Clipper remote flat now passes a signpost first: the dialog names the source wig and the flat cost in real signal counts, then offers "Adopt the wig instead" beside the quiet "Adopt flat anyway". A wig that has since left the closet drops the wig road and says so.
- **Temperature units handled properly.** The climate block carries an optional `unit` ("C" or "F", default "C" -- the SmartIR corpus is Celsius by convention). Machine keys stay file-native forever; the entity declares the file's unit and Home Assistant converts the thermostat display both ways; panel displays convert dynamically to your install's unit; and names minted from a cell (the matrix clip, saved state commands) freeze in the install's unit at that moment and never rewrite. Preset-mode ACs are untouched and stay unit-agnostic -- the design splits the two on purpose, applying the lesson @ripolltata's metric report taught us back in GH #45.

### Changed

- On all three acquisition tabs (Sniffer, Clipper, Plucker) the expanded card's footer actions moved up into the card header, next to ADOPT DEVICE, and the footer row is gone: ADOPT DEVICE, ADD TO CLOSET, DISMISS (Sniffer only), DELETE, delete last everywhere. The delete button drops the "remote" / "blaster" wording for a bare Delete -- the card header already names the thing.

### Limitations

Stated plainly, because an importer that oversells is worse than none. Files from Xiaomi-controller sources whose codes are Raw are refused: that Raw is a proprietary compressed format, not timing data, and HAIR will not pretend to convert it. Roughly half a percent of corpus cells are unconvertible for other reasons and are skipped, with the reason written into the wig's notes; modes with no Home Assistant equivalent are skipped the same way, with receipts. Sparse matrices are honored -- a state absent from the file stays absent in HAIR, which never invents a cell. The dimension check attests that each dimension works along its own axis, not that all several hundred cells were individually fired. And imported files are treated as Celsius by convention unless they say otherwise, matching the corpus; there is no unit guessing.

The state model also explains a long-standing capture confusion (GH #16, @akikun21's TCL split AC): an AC remote's "buttons" capture as near-identical codes because every press transmits a full-state snapshot, not a button. Capturing one press is capturing one cell of the matrix; for a unit with a published SmartIR climate file, the matrix import above is today's answer.

## [0.8.1] - 2026-07-28 -- Adopt Device

### Added

- **Adopt Device.** Every code set now becomes a HAIR device in one step, from wherever you meet it. Closet wigs, Sniffer remotes, Clipper remotes, and Plucker blasters all carry one green ADOPT DEVICE button. A numbered dot on the button shows how many HAIR devices already run those codes; clicking through lists them with navigation to each, plus an entry to adopt again. Adopting from a wig copies every signal as a named command with protocol identities stamped fresh and recognizable names auto-mapped to entity actions, and the device type dropdown is seeded from the wig's kind.
- **The code library joined the closet properly.** Built-in library rows (rendered from the infrared-protocols codes package) now carry FIT, ADOPT DEVICE, and download alongside CLIP. Fitting a library codebook first snapshots it into your closet as a wig, since fittings live in wig files; repeat fittings land in the same file by content hash, so its ledger accumulates. Adopting creates the device directly with nothing written to the closet, and download hands you the rendered wig file. Snapshots carry origin `library` with the codebook id and library version in the notes, and the render is deterministic, so fittings of the same library version are comparable across installs.
- **A dead emitter now tells you** (follow-up to the GH #65 resilience fix). When a send skips or fails an emitter, HAIR raises one persistent notification naming the blaster and the reason. One notice per emitter that replaces itself instead of stacking, and it dismisses itself the next time that emitter answers a send.
- Closet search now matches the kind and product identifier fields, so a UPC typed straight off the box (or "candles") finds the wig.

### Changed

- The Clipper's "+ Add Remote" and the Devices tab's "+ Add Device" buttons are now simply "+ Add", ahead of a planned split between controlled devices and trigger remotes. The docs say "+ Add" now too.
- The "Make HAIR Device" and linked-count chips on Sniffer, Clipper, and Plucker cards retired in favor of the ADOPT DEVICE button described above.
- Closet row buttons reordered and recolored for consistency: ADOPT DEVICE green and first, FIT blue, CLIP copper, DELETE last. Button spacing in the closet and the Mirror now matches the signal rows everywhere else.
- The v0.6.1 changelog entry about fused Samsung32 end pulses was reworded with a dated correction note; an earlier version asserted an emitter replay mechanism that code review could not support. The captures and the fix stand.

### Fixed

- SmartIR imports whose Base64 codes arrive with their padding stripped (a common shape in circulated files) convert now instead of being refused.
- The kind hint in the wig editor no longer overlaps its input box.

## [0.8.0] - 2026-07-28 -- Perfect Fit

### Added

- **Fittings.** A wig can now be proven on real hardware, and the proof travels with the file. FIT on any closet wig opens a fitting session: pick an emitter, send each signal, mark WORKED or DID NOT. Marks persist into the wig file as you make them, so a fitting survives closing the dialog, restarts, and updates; pressing FIT again resumes with untested signals first. When every signal works the session turns green and FINISH records the fitting under your name, with an optional GitHub handle. Complete fittings ride inside the wig on download and share; partial or in-progress fittings stay local, so a shared wig never carries half a claim. The closet shows a green check on fitted wigs, yellow while partial (your own perfect fit gets a small glow), with fitted and not-fitted filter chips, and each wig keeps a ledger of every fitting, opened from the status chips in the session.
- **Fitting signatures.** Recorded fittings are signed with an ed25519 key generated on the install (the `cryptography` package Home Assistant already ships). A signature proves a fitting was not altered or forged after recording; the ledger shows signed, unsigned, and signature-mismatch states distinctly. Unsigned fittings remain valid as self-reported records. No Home Assistant identifier, raw or hashed, is ever written into a wig.
- **Wig kind.** An optional `kind` field says what the device is ("candles", "soundbar", "tv"). Asked once at the signing screen when a wig has none, editable in the wig editor, auto-stamped when exporting fan, AC, light, and screen devices. Suggestions plus free entry; values squash to one lowercase word.
- **Product identifiers.** Wigs can carry FCC ID, UPC, ASIN, and verified-OEM anchors (single values or lists, for rebadged device families sold under several listings), editable in the wig editor and Add to Closet. Off-brand hardware stays findable when its brand and model mean little. Documented in [the wig format](docs/wig-format.md).
- A Fitting Send provenance chip in the Mirror, so a long fitting session never reads as mystery traffic.

### Fixed

- **One unavailable emitter no longer fails a multi-emitter send** (GH #65, thanks @rvgfox). Sends now succeed when at least one emitter fires, skip emitters Home Assistant already knows are down, log exactly which emitter failed and why, and only error when every emitter is unreachable, with a plain message instead of a raw driver string. RC-5 toggle and Dyson counter state now advance when at least one send lands, so a late emitter failure cannot desync a device that already received the frame.

### Changed

- The Spanish panel translation was reviewed by a native speaker (thanks @Waterbrain, GH #67), and the German README summary by @EckeFL (GH #64).

## [0.7.2] - 2026-07-24 -- HACS Haircut

### Changed

- The Dyson protocol decoder, shipped as a beta in 0.7.1, is now part of the stable release. The code is unchanged from the beta: HAIR decodes each Dyson frame, keeps device and button as the signal's identity so the rolling mod-4 counter does not split one button into many, and advances that counter on every send so consecutive presses are always accepted.
- Packaging and validation. The manifest now declares its `http` dependency and has its keys sorted, and an invalid `icons.json` was removed, so HAIR passes Home Assistant's hassfest checks. None of this changes how HAIR runs; it clears the last requirement for listing in the HACS default store.

## [0.7.1] - 2026-07-20 -- Blow Dry

### Added

- A Dyson protocol decoder (beta, hardware verification in progress). Dyson fans rotate a mod-4 counter in every IR frame and reject a replayed value, which is why stored captures only worked about a third of the time (reported by @Esp32-zapper, GH #33). HAIR now decodes the frame, treats device+button as the signal's identity so rotating presses collapse to one signal, and advances the counter on every send so consecutive commands are always accepted. Applies to sends from HAIR devices and to catalog Test presses.

### Fixed

- Girr import accepts all four root elements the spec allows; a file whose root is a bare commandSet or command now imports as one remote named from the file.
- Girr files that hoist protocol parameters to the commandSet level now skip with the accurate "re-export with Pronto included" message instead of "no usable representation".

## [0.7.0] - 2026-07-20 -- Big Wig

### Added

- The Closet: a new panel tab for portable code sets, called wigs -- one JSON file per remote, raw Pronto as the payload, in a small documented format anyone can write (`docs/wig-format.md`). Library codebooks and your own wig files hang on one shelf, organized by brand, searchable, with signal-name peek on every entry.
- An import funnel on the Closet's drop bar: SmartIR JSON (all four encodings; climate files refused with an explanation), Flipper Zero `.ir` (raw and parsed), LIRC `lircd.conf` (raw codes and space-encoded remotes), and Girr exports from IrScrutinizer all convert into wigs on drop. Anything a conversion skips is written into the wig's notes with a reason.
- Add to Closet on every Sniffer, Clipper, and Plucker remote and on HAIR devices; CLIP on every closet entry to materialize it as a working Clipper remote. Re-clipping updates the existing remote instead of duplicating it.
- Make HAIR Device (formerly Promote) now carries the whole remote: every signal arrives as a named command, recognizable names auto-map to entity actions, and the new device stays linked to its source remote with a live device chip on all three catalog tabs.
- Direct fan speed levels: map Speed 1 through Speed 10 commands and the fan entity gets a real percentage slider that fires the matching level in one send. Contributed by @feiming (#54).
- Per-remote delete on the Sniffer, with confirmation; a deleted sniffed remote returns if a receiver hears it again.

### Fixed

- Climate devices with only a power command mapped now expose a synthetic AUTO mode so they can be turned on from the climate card; the mode retires itself once a real HVAC mode is mapped. Reported by @Mesmer88 (GH #58).

### Changed

- Tab order is now Devices, Sniffer, Clipper, Plucker, Closet, Mirror, with uppercase tab labels and a per-tab accent color (Devices green, Clipper copper, Closet oxblood, Mirror silver).
- Device cards on the Devices tab truncate long names before they reach the corner actions.

## [0.6.9] - 2026-07-20 -- Trim

### Fixed

- The panel footer reported v0.6.7 on v0.6.8 installs. The version constant in the panel source missed the release bump; it now reads the shipped version, and a new test pins the footer constant and the compiled bundle to manifest.json so the footer can never drift from the real version again.

### Changed

- Fresh README screenshots: the device detail and action mapping shots now show the current UI (including the Custom... action entry), the Mirror tab appears in the README for the first time, the assigned and trigger popovers get a row, and a Japanese panel screenshot shows the ten-language support doing its job.

## [0.6.8] - 2026-07-19 -- French Braid

### Added

- HAIR speaks ten languages. The panel and the setup wizard ship in English, Spanish, French, Japanese, German, Polish, Portuguese (pt and pt-BR), Dutch, Italian, and Russian, following your Home Assistant profile language automatically with English fallback. Every non-English locale was drafted by a programming assistant and is marked "reviewer wanted" inside its dictionary file; native-speaker reviews are one-file PRs, and the reviewer's name goes in the file. See "Adding a language" in CONTRIBUTING.
- Command vocabulary localizes end to end. Template names and action labels render in your language, an accepted template stores the localized name (your data, your language), and assign-time auto-mapping recognizes the vocabulary of every shipped language at once, so a command named "Allumer", "Einschalten", or "電源オン" wires itself the same way "Power On" always has.
- Plural grammar done properly. Polish and Russian counts render through CLDR plural rules (1 sygnał / 2 sygnały / 5 sygnałów), not English-shaped if/else. Dates and timestamps follow the panel language too.
- The Map action popover gains a Custom... entry: type any action key (temp_30, and the like) directly, no re-import needed to fix a mistyped mapping.
- Nokia32 (RC-MM) decoding, the first guest decoder in the registry, contributed by @rohrsh with identity support for Foxtel boxes. Captured Nokia32 signals now carry decoded identities like the other seven local protocols.
- A parity test suite makes translations safe to contribute: key parity, placeholder parity, brand-name preservation, and vocabulary coverage all fail CI before a stale or broken translation can ship blanks.

### Fixed

- The stray "Templates" button in the Assign dialog's custom-name mode is now a Cancel button, which is what it always did.

### Changed

- Every string in the panel now lives in one dictionary file per language instead of being scattered through the components; 428 strings extracted at pixel parity.

## [0.6.7] - 2026-07-19 -- Shampoo

### Added

- Multi-emitter sends are staggered. Two blasters keying up at the same instant superimpose in the air, and any receiver in range of both hears a hybrid pulse train that decodes as nothing. HAIR now serializes every transmission it originates and inserts a short quiet gap whenever the transmitting emitter changes, so multi-emitter device commands and multi-emitter tests each come out clean. Same-emitter bursts are unaffected, and sends from other integrations remain outside HAIR's control.
- Garbled echoes are recognized as the house's own voice. A HAIR send that comes back damaged (reflections, marginal range, protocol timing quirks) used to miss the echo claim and mint a junk Sniffer row per mangle. Send expectations now carry the transmitted frame's shape; an unclaimed, undecodable capture arriving inside the send window that resembles what just went out is claimed as a garbled echo, marks the Mirror row heard, and never reaches the Sniffer. Captures that decode cleanly are never swallowed, so pressing a real button moments after a test is safe.
- "+ Mirrored Signal" joins Sniffed and Clipped in the device footer. The third road for getting codes into a device gets its road sign.
- Unknown-send rows explain themselves. A foreign send that no receiver heard now reads "Unknown IR signal sent" with a plain sentence naming the blaster and what to do about it, in place of a mysterious grey row with disabled buttons.

### Fixed

- The Promote dialog's name field could render as an empty, unfocusable shell. It was the panel's last dialog built on a lazily-loaded Home Assistant element; rebuilt on the same plain input every other dialog uses. The suggested name pre-fills and Enter creates.
- The Mirror's silver bloom now follows the trigger glow's exact lifecycle: bright, fade, one last pass, gentle exit.

### Changed

- Eleven dialogs now draw from one shared style module, the third extraction after the popovers and the action chips. Roughly 700 lines lighter at pixel parity, and groundwork for translations: every shared style and string now lives in exactly one place.
- Mirror rows are individual rounded cards, and a send that lands while you watch blooms the whole card. Count dots render digits on tabular figures so every number sits identically in its circle. Heard-back wording says "last heard", describing the most recent send. Add-signal actions in the Clipper and Plucker are quiet accent-colored text buttons matching each tab's color.

## [0.6.6] - 2026-07-18 -- Mirror

### Added

- The Mirror tab: see what your house transmits. Every IR command sent through Home Assistant now appears as a row in a new panel tab, whether anything heard it or not -- HAIR device commands, catalog tests, automations, and even other integrations sending through the native infrared platform, caught the moment their emitter fires. Each row shows the send's identity (the assigned command name when there is one, else the decoded protocol identity), which emitter carried it, whether a receiver heard it back and in which room (resolved through the receiver's Home Assistant area), how it originated, and the running send count. A send that lands while you are watching blooms the row silver. Rows carry the same Assign, Test, and Trigger actions as everywhere else, plus the code viewer, so the Mirror doubles as a third way of importing codes: press a button in any vendor app whose blaster transmits through the infrared platform, and if a receiver hears it, the code lands in the Mirror one Assign away from living in HAIR. Delete on a Mirror row clears the entry, and the row returns the next time that signal is sent -- the same come-back-when-heard behavior signals have everywhere else, so clearing out old experiments never damages the audit. Homes with no receiver at all simply see their sends without heard-back detail, and "not heard" reads as neutral information rather than an alarm, because plenty of setups are transmit-only on purpose.
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
- Samsung32 captures whose end pulse arrives fused with a following frame decode now. Real captures show the end pulse can arrive welded to the next frame's leader with no gap at the junction; the decoder tolerates the fused pulse while the protocol checksum keeps gating every decode. Found on the bench with real captures, which are now fixtures. (Wording corrected 2026-07-28: an earlier version of this entry asserted a specific emitter replay mechanism that later code review could not support; the captures and the fix stand.)

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
