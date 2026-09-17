# IR hardware and integration guide

HAIR does not talk to infrared hardware directly. It works through Home
Assistant's native `infrared` platform, so anything that exposes an infrared
entity is available to HAIR automatically, and anything that does not is
invisible to it no matter how good the hardware is.

The compatibility table lives in the README. This page is about the parts
that table cannot tell you: how to set each kind of hardware up, what each
one can and cannot do, and what goes wrong in practice.

---

## ESPHome

The most capable option, and the only one that has done both directions from
the beginning. Transmit since HA 2026.4, native receive since 2026.6.

### The receiver setting that matters most

```yaml
remote_receiver:
  id: ir_rx
  pin:
    number: GPIO8
    inverted: true
    mode:
      input: true
      pullup: true
  tolerance: 25%
  idle: 100ms
  filter: 200us
```

**`idle` decides when a capture ends.** It is the amount of silence that has
to pass before the receiver decides the transmission is over. ESPHome
defaults it to 10ms, and for infrared that is too short.

Plenty of real remotes leave gaps longer than 10ms inside a single press.
Air conditioners are the worst case, because they send long state messages in
sections: a Daikin leaves about 35ms between sections, and some leave more.
When `idle` is shorter than the gap, the receiver stops early and hands you a
piece of a message, then starts again on the next piece.

What that looks like from the outside is one button press producing several
signals, or several remotes appearing in the Sniffer that you do not own. If
you are seeing that, `idle` is the first thing to change. **Use `100ms`.**
That is comfortably above any within-message gap we have measured and still
well below the silence between two separate presses.

The trade-off at the high end is that a held button, which sends the same
frame over and over, can merge into one long capture. That is usually what
you want, and it is easy to spot.

**`filter` rejects short noise.** It is the shortest pulse the receiver will
believe, defaulting to 50us. Raising it to around 200us throws away most
electrical and optical noise without touching any real IR protocol, since the
shortest real pulse in common use is around 400us. Worth doing if your
Sniffer shows one-pulse signals or you are near LED strips, fluorescent
lighting, or plasma displays, all of which emit infrared noise.

**`tolerance`** is how much timing drift the decoders accept. 25% is a good
default and rarely needs changing.

**`buffer_size`** defaults to 10kB on ESP32 and 1kB on ESP8266. Long air
conditioner messages can overflow the smaller buffer. If you are on an
ESP8266 and long codes arrive truncated, raise it.

### `dump: all` is for diagnosis, not for running

`dump: all` runs every protocol decoder ESPHome has and logs what each one
thinks it saw. It is genuinely useful when you are working out what a remote
speaks. It is also noisy, and several of those decoders will confidently
report protocols your hardware cannot physically receive, which sends people
chasing ghosts. Turn it on to investigate, turn it off afterwards.

### Registering with Home Assistant

Exposing the transmitter and receiver on the `infrared` platform is what
makes them visible to HAIR. See the reference configuration in the README.
If you are on HA 2026.4 or 2026.5, native receive does not exist yet and the
README has a legacy bridge section for you.

---

## Broadlink

Transmit only, since HA 2026.5. There is no receive support, so a Broadlink
cannot feed the Sniffer. If a Broadlink is all you have, you can still build
devices in HAIR by pasting codes or importing wig files, and you can pull in
codes you have already learned. You just cannot capture off the air.

### What Pluck can and cannot see

HAIR's Plucker reads the codes Home Assistant has stored for your blaster.
Home Assistant writes that file only when a `remote.learn_command` succeeds.

Two things follow from that, and they account for most of the confusion:

**A blaster you have only ever transmitted through has nothing to pluck.**
No learn, no file. The Plucker tab is still there and will tell you so.

**Codes you learned in the Broadlink phone app are not there either.** Those
live in your Broadlink cloud account. Home Assistant never signs in to it and
never sees them. The same blaster ends up with two separate libraries that
know nothing about each other. If you want app-learned codes in HAIR, the
route is to learn them again in Home Assistant.

This applies to every RM model Home Assistant supports. The integration lists
`RM4MINI`, `RM4PRO`, `RMMINI`, `RMMINIB` and `RMPRO` for both infrared and
remote, so there is no older-versus-newer split. The variable is whether that
blaster has ever learned inside Home Assistant.

### Do not hand-edit the codes file

Home Assistant keeps its own copy of that file in memory and will rewrite it
from memory when it next saves, so edits made underneath it tend to disappear
or need a restart dance to survive. HAIR only ever reads it, never writes.

### Do not run learned codes through a normaliser

There is a habit in the Broadlink world of taking a learned code, pushing it
through a third-party converter to tidy up the timings, and writing the result
back. We do not recommend it. Those tools vary in quality, at least one of
them has shipped a header preset with a decimal point in the wrong place, and
a code that looks fine can be structurally broken in a way that only shows up
later.

HAIR already does this for you, correctly, when it plucks. Any code it can
identify is rebuilt from the protocol definition rather than replayed as it
was captured, so it goes out cleaner than it came in. Codes it cannot
identify are kept exactly as they are.

### A known accuracy issue

The Python library Home Assistant uses to talk to Broadlink hardware carries
an incorrect timing constant, and everything sent through a Broadlink comes
out roughly 7% short as a result. Learning and replaying on the same Broadlink
hides this, because the same error runs in both directions and cancels out.
A code that came from anywhere else does not get that cancellation.

In practice most devices tolerate it. Some do not, and the symptom is a code
that works from one blaster and does nothing from the Broadlink. We have
reported it upstream with measurements and a fix is proposed. If you hit it,
the workaround is to send that particular device's codes through a different
emitter, which HAIR supports since emitters are chosen per device.

---

## MQTT and Zigbee2MQTT

Since HA 2026.8, MQTT carries the `infrared` platform in both directions.
This is the cheapest route into HAIR, because it reaches the inexpensive
Zigbee and Tuya IR hubs through Zigbee2MQTT with no extra work: ZS06,
UFO-R11, UFO-R4Z, QAIRZPRO and similar.

Two caveats matter before you buy one.

### The receiver only listens in a short window

These hubs do not listen continuously. They have a learning mode that stays
open for a short time and then closes, and after a capture the hub closes it
itself. So a press outside that window is simply not heard.

For occasional captures you can arm it by hand each time. For anything more,
you will want an automation that re-arms the learn mode on a timer, which is
a common pattern in the Zigbee2MQTT community. Continuous capture the way an
ESPHome receiver does it is not available on this hardware.

### Long codes can be rejected

Zigbee2MQTT packs each timing value into two bytes when it sends, which caps
any single value at 65,535 microseconds. Most codes are nowhere near that.
Codes converted from other sources sometimes are, usually because they carry
a long trailing gap from whatever captured them originally, and those get
refused outright rather than sent short.

HAIR trims that trailing gap before transmitting for exactly this reason, so
codes going out of HAIR are safe. A code you paste in from elsewhere and send
by another route may not be.

---

## SMLIGHT

Transmit since HA 2026.5. Native receive arrived in 2026.7 and is Ultima
hardware only. Primarily Zigbee coordinators with infrared as a secondary
feature, which makes them a reasonable choice if you already own one.

---

## Troubleshooting index

**One button press creates several signals, or remotes I do not own appear
in the Sniffer.** Your receiver is ending captures too early. Raise `idle` to
`100ms`. See the ESPHome section.

**The Sniffer shows signals with only one or two pulses.** Noise. Raise
`filter` to around `200us` and check what is in the receiver's line of sight.
LED strips are a common culprit.

**A long air conditioner code arrives in two pieces.** Same cause as the
first entry. Raise `idle`.

**The Plucker shows no codes, or an empty tab.** That blaster has not learned
anything inside Home Assistant yet. Codes learned in a vendor phone app do
not count.

**Only one code per device appears when plucking.** The codes are being read
as duplicates of each other, which usually means they are damaged in the same
way and HAIR cannot tell them apart. If they have been through a third-party
converter, that is where to look first.

**A code works from one blaster and does nothing from a Broadlink.** Likely
the timing accuracy issue above. Assign that device to a different emitter.

**A code is refused by a Zigbee or Tuya hub.** Probably over the 65,535
microsecond limit on a single value, usually a long trailing gap.

**Nothing appears in HAIR at all.** Check that your integration actually
exposes infrared entities. `remote` entities are the older style and HAIR
cannot use them. The README table lists what has adopted the platform.
