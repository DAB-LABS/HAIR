# HAIR glossary

HAIR uses a barbershop vocabulary for its own features and the ordinary
Home Assistant vocabulary for everything else. This page defines both, so you
can read the rest of the docs, the panel, and the release notes without
guessing.

Terms are grouped rather than alphabetized, because most of them only make
sense next to their neighbors. Words in capitals (USE, PIN, LAST HEARD) are
written the way the panel shows them.

---

## The kinds of IR hardware

**Blaster.** *Half duplex.* A device that transmits infrared. Most blasters
can also learn a code when you ask them to, one at a time, and then they go
back to transmitting. Learning is a mode they enter, not something they are
always doing. Examples: Broadlink RM series, Tuya and Zigbee IR pucks, an
infrared LED on an ESPHome board.

**Transceiver.** *Full duplex.* A device that transmits and listens at the
same time, continuously, without being asked. This is what an automation
needs, because nobody is around to put a device into learning mode at the
moment somebody presses a remote. Examples: an ESPHome board carrying both a
receiver module and an emitter LED, SMLIGHT Ultima.

**Receiver.** A device that only listens. Less common on its own, and the word
Home Assistant's infrared platform uses for the listening half of any setup.
The Devices tab lists yours under Receivers.

**Half duplex and full duplex.** Borrowed from radio, and the precise way to
say the above. Half duplex means the device can send or receive, but only one
at a time, and on an IR blaster it only receives when told to. Full duplex
means both at once, always.

This matters because the difference between a blaster and a transceiver is not
what parts are inside the box. Strictly, a blaster contains a transmitter and
a receiver too, so it is a transceiver by the dictionary. What separates them
is whether those parts work at the same time. A transceiver in the sense used
here has two independent pieces of hardware, a receiver module on one pin and
an emitter LED on another, so neither has to wait for the other. A device where
listening is a mode it enters cannot do that, and no software can change it.

The practical consequence: **capture is a setup-time tool, listening is a
runtime one.** A blaster can feed the Sniffer perfectly well when you arm it
and press a button. It can never reliably fire a trigger.

**Blasters (Pluckable).** A narrower use of the word, and a section on the
Devices tab. It lists only vendor blasters that HAIR can pull already-learned
codes out of, which today means integrations with Plucker support. Every
pluckable blaster is a blaster; most blasters are not pluckable.

## Home Assistant terms HAIR sits on

**The `infrared` platform.** Home Assistant's own entity platform for infrared,
shipped in 2026.4 for sending and extended in 2026.6 for receiving. HAIR does
not talk to hardware. It uses this platform for everything, which is why any
hardware Home Assistant supports, HAIR supports.

**Emitter.** An entity on the `infrared` platform that can send. HAIR
discovers these automatically and lists them on the Devices tab. A blaster and
a transceiver both give you one.

**Receiver entity.** An entity on the `infrared` platform that can hear. HAIR
subscribes to every one it finds, including ones that appear after startup.
Only a transceiver or a dedicated receiver gives you one that is useful for
triggers.

**Proxy.** A device that forwards infrared between Home Assistant and hardware
that is not directly reachable.

**Entity.** The thing HAIR creates for you: a button, a media player, a
climate control, a switch, a light, a fan, a cover, a remote, or an event. It
lives in Home Assistant like any other entity, on dashboards and in
automations.

## The panel

**Sniffer.** Where signals land when a receiver hears them. Point a remote at
your receiver, press a button, and it appears here. Signals are grouped by
which remote they seem to have come from.

**Clipper.** Build a remote by pasting Pronto codes, for when you have codes
but no way to capture them live. Also where a remote built from your installed
code library lands.

**Plucker.** Pull codes that already live inside a vendor blaster into HAIR,
without re-learning each one at a receiver. Nothing is broadcast over the air
during a pluck.

**Closet.** Your shelf of portable code sets. Holds both the code library that
ships with Home Assistant's infrared library and your own files, organized by
brand.

**Mirror.** A log of every infrared command Home Assistant sends, whether
anything heard it or not. Useful for working out whether a send actually went
out and through which emitter. It is also a way to get codes into HAIR: press
a button in a vendor app, and if a receiver hears it, the code lands here.

**Devices tab.** Two sections. DEVICES holds the things HAIR sends codes to,
plus your Emitters, Receivers, Proxies, and pluckable Blasters. REMOTES holds
the handsets HAIR recognizes, with HAIR Triggers as the first card.

## Objects

**Signal.** One captured or pasted infrared code, before it belongs to
anything. Signals live in the catalog tabs.

**Command.** A signal that belongs to a Device and has a name. Commands are
what your entities actually fire.

**Device.** A HAIR Device: a named thing with a type, a set of commands, and
one or more emitters to send through. Making one creates the Home Assistant
entities. When this page says Device with a capital D, it means one of these.

**Remote.** A handset HAIR recognizes. A Remote holds triggers rather than
commands: press a button on the handset and its trigger fires. Each Remote is
its own device in Home Assistant, so its buttons show up by name in the
automation editor.

**HAIR Triggers.** The built-in, catch-all Remote that has always been there.
Any trigger you do not give to a named Remote lives here, and it is the only
Remote whose triggers can be scoped to particular receivers.

**Add tile.** The dashed tile at the end of each grid on the Devices tab. Click
it to start a Device or Remote from scratch, or drop a code file on it (a wig,
a SmartIR file, a Flipper `.ir`, a LIRC conf, a Girr export) so the add dialog
opens already filled in.

**USE.** The button on any set of codes, in the Sniffer, Clipper, Plucker, or
Closet, that turns them into a Device or a Remote. It asks which one you want.
A count dot on the button says how many you have already made from that set.

**Make a Device / Make a Remote.** The two choices behind USE, and also the two
actions in a Device's or Remote's settings that build the matching other half:
a Device can build the Remote for its own handset, and a Remote the Device its
handset controls. HAIR then offers to pin the two together.

**Duplicate.** Copy a Device, commands and emitter assignments included, so you
only have to rename the clone.

**Alias.** The name you give a signal. Click the diamonds on a signal row to
set it. Names matter, because recognizable ones get mapped to actions for you.

**File-sourced.** A code that came from a file rather than through a receiver:
a wig, a Clipper paste, a Plucker pull. HAIR compares the shape of the signal
for these, so a Remote or trigger made from a file still hears the real
handset over the air.

## Codes and identity

**Pronto.** The text format HAIR stores every code in. It describes the raw
on and off timings of the signal plus its carrier frequency. Pronto is the
only paste format the Clipper accepts.

**Carrier frequency.** The rate the infrared LED pulses, usually around 38 kHz.
Most remotes use one of a handful of standard values, and HAIR can snap a
slightly-off capture onto the nearest standard one.

**Fingerprint.** How HAIR tells one button from another without knowing the
protocol. It classifies each pulse as short or long and uses the resulting
pattern as an identity, which survives the small timing differences between
one press and the next.

**Byte hash.** A second, finer identity used alongside the fingerprint. Some
remotes, Sony among them, encode every button with pulses that all classify
the same way, so the fingerprint alone would collapse the whole remote into
one signal. The byte hash separates them.

**Decode.** When HAIR recognizes a signal as a known protocol, it stores that
identity alongside the raw timings and can re-encode a clean version when
sending. The raw capture always stays authoritative.

**Protocol.** The encoding scheme a remote uses. HAIR knows several, including
NEC, Sony, Samsung, Sharp, RC-5, Kaseikyo and others. You do not need HAIR to
know your protocol for it to work, because raw replay works either way.

**NEC / PRONTO pill.** The small toggle on a command row for signals HAIR
decoded. It chooses whether to send a clean protocol-encoded version or replay
the raw capture exactly as heard. Try the other one if a device is fussy.

**LISTEN.** The button in the signal editor that captures a code fresh off the
handset in place of the one you are looking at.

## Sending

**Action mapping.** Explicitly telling HAIR which command drives which entity
feature. A media player only gets volume controls once you have mapped
commands to volume actions. Nothing is assumed, because an assumed control
that does not work is worse than no control.

**Emitter routing.** Which emitters a Device sends through. Give a Device one
emitter for a single room, or several to broadcast everywhere at once. (This is
separate from pinning, which is about Remotes; see Triggers below.)

**Ditto count.** How many repeat frames follow the main one, for protocols
that use them. Some receivers ignore a single frame and want a few. This
applies only to decoded signals that support it.

**Send times.** How many times the whole signal is transmitted, with a gap
between each. Useful for devices that need waking up before they listen, or
that expect two presses. This is separate from ditto count and applies to any
signal.

**Preset star.** The star on every command row of an air-conditioner Device.
Starred commands become presets on the thermostat card in Home Assistant,
named after the command. It works for learned commands and for states saved
out of the STATE MATRIX card. Presets are local to the device and do not
travel with a wig.

## Air conditioners

**State matrix.** An AC remote does not send buttons, it sends whole states:
every press carries the mode, fan, swing, and temperature the unit should
switch to. HAIR stores an AC as a lattice of those states, one code per cell,
and the climate entity looks up and sends the matching cell when you change
anything on the thermostat card.

**STATE MATRIX card.** The card on an AC Device's page where you browse the
lattice one branch at a time, see which state was last sent, send any state
directly, or press **+ Command** to save one you use often as a one-tap
command. An AC Remote shows the same card for listening.

**Cell.** One state in the matrix, and the code that sets it. The Power row at
the top of the card holds the off code and, when the file has one, a separate
on code.

**STATE chip.** The small marker on a command or trigger that was saved out
of the STATE MATRIX card, so you can tell it apart from a learned button.

**Saved state.** A command saved out of the STATE MATRIX card with
**+ Command**. It carries its state, so sending it, including as a preset,
moves the thermostat card.

**LAST HEARD.** On an AC Remote, the row naming the last state the handset
sent, when it arrived, and which receiver heard it. Press the handset and the
mode, fan, swing, and temperature it sent light up on the card and stay marked.

**State heard trigger.** The trigger every AC Remote offers in Home Assistant's
automation editor. It fires on any state the handset sends and hands mode,
fan, swing, and temperature to your automation as data. Browse to one state
and press **+ Trigger** if you want a trigger for exactly that state instead.

## Triggers

**Trigger.** Turning an infrared signal into something Home Assistant can
automate on. When a receiver hears the signal, an event entity fires, and your
automation runs. This is how a physical remote button drives your smart home.
Every trigger belongs to a Remote, HAIR Triggers by default.

**Minimum hits.** How many presses within a short window before the trigger
fires, so an accidental single press does not set something off.

**Tap and hold.** A single tap on a handset counts once. Holding a button
steps about three times a second, through the trigger and through any Device
the Remote is pinned to.

**Pin / PINNED.** Pin a Remote to a Device and pressing the handset sends the
matching command out that Device's emitters; HAIR works out which button
matches which command. Open the **PIN** row on a Remote's header or the
**PINNED** row on a Device's and tick the other side. One Remote can drive
several Devices and one Device can be driven by several Remotes. If a pairing
ever runs away, HAIR cuts that one pairing for a minute and writes a warning
naming the Remote, the Device, and the command; the handset's triggers keep
firing throughout.

**Echo.** Home Assistant hearing its own transmissions. If your house has both
a blaster and a transceiver, your receivers hear what your emitters send. HAIR
identifies these, routes them to the Mirror, and never lets them fire
triggers or pinned sends, which would otherwise create a feedback loop.

**Not heard.** In the Mirror, a send no receiver caught. Neutral, not an alarm,
since many setups are transmit-only; it is how you spot a dead LED or a
misaimed emitter. The **Not heard** pill and the **Emitter** dropdown narrow
the Mirror to what you are chasing.

## Device settings

**Power sensor.** Any Device that plausibly draws current can be pointed at a
power reading, such as a smart plug's wattage. Set two thresholds and the
Device counts as off at or below the lower one and on at or above the higher
one. A reading that crosses a threshold overrides what HAIR assumed from the
last command sent, so a device switched off with its original remote stops
claiming to be on.

**Room sensors.** On a state-matrix climate Device, a temperature sensor, a
humidity sensor, or both, shown live under the thermostat card. Display only.

## The Closet

**Wig.** A portable code set: one JSON file holding one remote's codes, in a
small documented format. See [the wig format](wig-format.md).

**Codebook.** A code set installed with Home Assistant's core infrared code
library. Codebooks hang in the Closet next to your own wigs and can be used
the same way.

**CLIP.** Turn a Closet entry into a working remote on the Clipper tab, ready
to test before you make anything from it. Clipping the same entry again
updates the existing remote rather than making a second one.

**Save to Closet.** From a Device's detail view, file the Device as a wig.
Three routes: **Save as New** files a fresh wig and leaves the original alone;
**Update Closet Wig** brings the shared file up to date with your Device;
**Validate for Perfect Fit** starts a fitting.

**Origin.** Where a wig's codes came from: captured off real hardware, plucked
from a vendor integration, or converted from another format. It is shown
plainly, because a converted code set has never touched your hardware and may
not work first time.

**Import funnel.** The drop bar on the Closet, which accepts wig files, SmartIR
JSON, Flipper Zero `.ir` files, LIRC `lircd.conf` files, and Girr exports and
turns them into wigs. Anything a conversion cannot handle is written into the
wig's notes with the reason.

**Supersede.** When a file you drop is a newer version of a wig you already
have, HAIR offers to replace the old one instead of filing a duplicate.

**Comb.** The check every arriving wig gets, without hardware: do its codes
agree with each other? It catches a cell that quietly sends its neighbor's
code, a frame too short to register, or a gap in a temperature run. The comb
glyph on a Closet row stays grey until something is checked, glows yellow when
a finding needs a look, and red for the neighbor's-code mix-up.

## Fittings

**Fitting.** Proof that a wig's codes actually work on real hardware, and the
proof travels with the file from then on. You run one from **Save to Closet**,
**Validate for Perfect Fit**, and hit **TEST** on each row of the checklist.

**Perfect Fit.** A finished fitting: every row of a flat wig checked, or every
dimension of a state-matrix wig checked or honestly excluded ("not on my
device", "could not make it work"). There is no partial grade. Only perfect-fit
wigs can graduate into generated Home Assistant integrations.

**Signature.** The proof on a fitting. Your verdicts tie to a key generated on
your own install, not to the name you type, so nobody can edit your results or
fit in your name. Fitting the same wig again later replaces your old
signature.

**Changes with new fitting.** The section of the fitting screen that lists
commands your Device has gained or dropped since the wig was last saved, so
you can review them before you sign.

**Store pluck** -- importing the IR codes another integration has learned and persisted inside Home Assistant, by reading its storage file directly. The store decides the decoder; files are read-only. (v0.10.3)
