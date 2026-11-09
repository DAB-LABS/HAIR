# Radio remotes

Home Assistant 2026.11 adds a radio frequency platform beside the infrared one. HAIR listens to every radio receiver on it, the same way it listens to infrared receivers. Press a button on a radio remote, such as a keyfob, a ceiling fan remote, a plug's handset or a doorbell, and the code shows up in the Sniffer as a row of its own. From there it works like any other code: give it an alias, assign it to a device, or make it a trigger.

This page covers what HAIR hears, which receivers work, and what to expect from different kinds of radio remote. [Windowed receivers](windowed-receivers.md) is the contract for integration authors.

## What you need

- **A Broadlink RM pro or RM4 pro** with [BroadSniff](https://github.com/DAB-LABS/broadsniff) 0.3.0 or later installed beside it, on Home Assistant 2026.11 or later. BroadSniff gives the Broadlink a radio receiver that is a capture device: it hears while a capture window is open.
- **An ESPHome radio receiver**, such as the Athom RF IR Remote in [`esphome/`](../esphome/), on Home Assistant 2026.12 and the matching ESPHome release. It is an always-on receiver: it hears all the time.

On older Home Assistant releases, HAIR runs as before, with no radio. HAIR picks up a new receiver on its own; there is nothing to turn on.

## Listening from the Sniffer

The receiver row at the top of the Sniffer has one pill per receiver, infrared and radio. A pill's `IR` or `RF` badge names the medium. A solid badge means the receiver is taking new codes right now; a light one means it is not. A pill glows each time HAIR takes a code from its receiver.

- **An always-on infrared receiver** is always solid. There is nothing to press.
- **A capture device:** press its pill to open a capture window. The pill turns green and drains until the window ends. The pickers on the pill set the next window's carrier, length and type, using the settings the integration names. They are inactive while a window is open, because a change applies to the next one.
- **An always-on radio receiver:** press its pill to open a capture window too. Without one, a radio receiver still hears the codes HAIR already knows: known rows keep counting and keep firing their triggers, but nothing new is filed. That keeps a neighbor's doorbell or a weather station from filling the Sniffer. HAIR keeps this window's length (5 seconds to 5 minutes) and type, set from the pill's pickers. The default is a sliding 30 seconds: every new code starts it over.

The glyphs at the right of the receiver row filter the remotes below: infrared, radio and hidden. The hidden glyph glows each time a hidden remote is heard.

### Finding the carrier (sweep)

A Broadlink can search for a remote's carrier itself. Pick **Sweep** in the pill's frequency picker, press the pill, then press and hold the remote's button until the pill shows the band. Sweep needs a remote that keeps transmitting while its button is held. Many keyfobs send one short burst however long the button is held, and never lock. For those, pick 433.92 MHz or 315 MHz instead.

## Bands

A radio row shows its **band**, such as 433.92 MHz. Receivers do not all report the same carrier for one remote: an RM4 Pro has reported 433.84 MHz for a keyfob that another receiver hears at 433.92 MHz. So HAIR moves a carrier within 150 kHz of a common band to that band. The bands are the list in [The wig format](wig-format.md#row-digests):

303.875, 310, 315, 318, 350, 390, 418, 433.42, 433.92, 868.35 and 915 MHz.

Any other carrier is shown rounded to the nearest 100 kHz. The same rule decides when two radio codes in a shared wig are the same code, so the band you see and the band a wig records always agree.

### Where the carrier comes from

HAIR records the best carrier it has for each code, in this order:

1. **The signal**, when the receiver measures the carrier and sends it with the code. A Broadlink with BroadSniff does.
2. **The window**, when the receiver names the carrier its open window listens on.
3. **The receiver**, when it declares exactly one frequency, such as an ESPHome receiver with `frequency:` set.

A code heard with none of these has no band until one is set in the code's editor. When a known code is heard again from a better source, the row takes the better carrier.

## How a press becomes a row

A radio remote repeats its code several times for each press. HAIR cuts what the receiver heard into frames and lets the whole frames vote; only a frame seen at least twice becomes a code. The winner is filed with its measured gap between repeats. Most cheap keyfobs, plugs and doorbells send a 24-bit code whose leading bits identify the remote and whose last bits name the button. HAIR puts those codes on one card by their first 16 bits, so one remote is one card however many buttons it has.

Receiver noise is kept out in three ways:

- a code needs two matching frames;
- a frame with too few edges to be a remote's code is counted as noise;
- an always-on receiver files new codes only inside a capture window.

## What to expect

- **Fixed-code remotes** work best: one button sends the same code every time. Most plugs, fans, doorbells and cheap keyfobs are fixed-code, as are garage-door openers from before the mid-1990s.
- **Rolling-code remotes**, such as most car keys, modern garage doors and gates, and Somfy blinds, send a different code each press, by design. HAIR files each press as a new row and cannot recognize the button.
- **Some remotes appear as several cards.** A remote whose code length changes with the button pressed can spread over several cards in the Sniffer.
- **Some remotes are not recognized yet.** Remotes that carry every bit in the gaps, with marks all one length, such as Nexa and KAKU, are not filed yet.
