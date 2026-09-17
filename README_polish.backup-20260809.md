<p align="center">
  <img src="https://raw.githubusercontent.com/DAB-LABS/HAIR/main/images/HAIR-readme-hero-v0.2.png" alt="HAIR Full Service barbershop banner with the TX mascot welcoming the new RX mascot at the shop entrance, RX IS HERE speech bubble overhead" width="900" />
</p>

<p align="center">
  <a href="README.es.md">Español</a> ·
  <a href="README.fr.md">Français</a> ·
  <a href="README.ja.md">日本語</a> ·
  <a href="README.de.md">Deutsch</a> ·
  <a href="README.pl.md">Polski</a> ·
  <a href="README.pt.md">Português</a> ·
  <a href="README.nl.md">Nederlands</a> ·
  <a href="README.it.md">Italiano</a> ·
  <a href="README.ru.md">Русский</a>
</p>

# HAIR

HAIR turns IR remotes into native Home Assistant entities. Point any remote at an IR receiver and press a button, and HAIR gives you back a device, a button, and an event you can automate. No vendor cloud, no YAML, nothing learned into somebody else's box.

## Install

### HACS (recommended)

[![Open your Home Assistant instance and open the HAIR repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=DAB-LABS&repository=HAIR&category=integration)

Click the button above, then **Download**, then restart Home Assistant.

Or find it by hand:

1. Open **HACS** in your Home Assistant sidebar.
2. Search for **HAIR**.
3. Click it, then **Download**.
4. Restart Home Assistant.

### Manual

1. Copy `custom_components/hair` into your HA `custom_components/` directory.
2. Restart Home Assistant.

### Add the integration

1. Go to **Settings > Devices & Services**.
2. Click **Add Integration** and search for "HAIR".
3. The config flow auto-detects your IR emitters and receivers.
4. Find **HAIR** in the sidebar.

## Requirements

- Home Assistant **2026.4** or later. **2026.6+** is recommended for native IR receivers.
- **To capture (RX):** an integration exposing HA's native `InfraredReceiverEntity`. ESPHome IR receivers work day one; SMLIGHT Ultima receivers work natively since HA 2026.7; any other adopter works automatically.
- **To send (TX):** at least one integration on HA's native `infrared` platform, such as ESPHome, [Tuya Local](https://github.com/make-all/tuya-local), Broadlink, or SMLIGHT.

These integrations have adopted the `infrared` platform:

| Integration | TX | RX | Pluck | Since |
|---|---|---|---|---|
| [ESPHome](https://esphome.io/) | Yes | Yes | No | 2026.4 (TX), 2026.6 (native RX) |
| [Tuya Local](https://github.com/make-all/tuya-local) | Yes | No | Yes | TX 2026.4, Pluck 2026.6.2 |
| [Broadlink](https://www.home-assistant.io/integrations/broadlink/) | Yes | No | No | 2026.5 |
| [SMLIGHT](https://www.home-assistant.io/integrations/smlight/) | Yes | Yes | No | TX 2026.5, native RX (Ultima) 2026.7 |

As more integrations adopt the `infrared` platform, HAIR picks them up automatically.

## Quick start

To go from a fresh install to a working button:

1. Point your remote at the IR receiver and press a button. HAIR shows it live on the **Sniffer** tab.
2. Hover over the remote's name and click it to rename it (optional).
3. Click **ADOPT**. HAIR creates a device with a button entity for every signal you captured.
4. Open the device and press one of its buttons. Home Assistant sends the code through your emitter.

## Capture a remote

The Sniffer is a live listener. It shows every signal your receivers hear, groups signals by the remote they came from, and filters out repeat frames from a held-down button.

To capture a remote:

1. Open the **Sniffer** tab.
2. Point the remote at your receiver and press buttons. Each source remote appears as a card, expandable to show its individual signals with an S/L diamond fingerprint.
3. Click a signal's diamond pattern to give it an alias, so you can tell buttons apart before you assign them.
4. Click **Test** on a signal to fire it through an emitter and confirm it works.
5. Click a signal to assign it to a device, or **ADOPT** the whole remote to make a new one.

When you assign a signal, pick a name from the device-type template list (Power On, Volume Up, Mode: Cool) or type your own, and set a Send Times count if the device needs a command repeated to register; you can change this later in the editor. For an AC device, naming commands "Temp 22" or "Temp 24" wires them straight into the climate card's thermostat control, stepped to whatever temperatures you name. Assigning copies the signal into the device rather than removing it from the Sniffer, so you can assign the same signal to several devices or commands; an assigned row keeps flashing when you press its button, so you can tell the remote is still alive. Drag the grip handle on a remote, or on a signal row, to reorder them; the order sticks.

A remote that leaks in from outside (a neighbor's clicker, for example) can be hidden with **Dismiss** and brought back later with **Show Dismissed**. A dot lights up on that button if a dismissed remote is still transmitting in the background. Delete on a remote or a single signal clears it, but anything a receiver hears again comes right back; Dismiss is the tool for keeping a remote hidden for good. A remote whose codes already run a device shows a numbered dot on its **ADOPT** button, so you can jump to those devices or adopt another copy for a second room.

![Sniffer showing captured signals with S/L diamond fingerprints, trigger buttons, and hit counts](images/screenshots/sniffer-signals.png)

## Turn signals into a device

Any captured, pasted, or plucked signal can become a full HAIR device with matching Home Assistant entities.

To promote a captured remote into a device:

1. In the Sniffer, hover over the remote's name and click it to rename it. Do this before adopting, so the new device is not stuck with an auto-generated name like "Unknown Remote 1".
2. Click **ADOPT** on the remote.
3. HAIR creates a device profile and the matching HA entity (`media_player`, `climate`, `fan`, and so on), with every signal arriving as a named command.
4. Open the device and click **ACTIONS** on a command to map it to an entity action, such as `turn_on` or `volume_up`. Only mapped actions show up as controls, so an entity never claims a feature your remote does not have.

There are five other ways to start a device:

- **From scratch** -- click **+ Add** on the Devices tab, name it, pick a type, and choose which emitters should carry its commands.
- **From the Clipper** -- paste a Pronto hex code for each button instead of capturing it live, for codes you have on paper but not in the air. HAIR validates the code as you type and shows the same S/L fingerprint you see in the Sniffer. Pronto is the only paste format, and a code already on the remote is refused, so a remote never ends up with two identical signals.
- **From the Plucker** -- pull codes already learned into a vendor blaster, such as a Tuya Local IR blaster, into HAIR by name. Nothing is transmitted over the air, and the vendor blaster keeps working normally.
- **From the Closet** -- adopt a wig, SmartIR file, Flipper Zero file, LIRC file, or Girr file straight into a device; see [Import codes](#import-codes-smartir-and-the-closet).
- **Duplicate an existing device** -- click the duplicate icon on any device card to clone it, commands and emitter assignments included, then rename the copy. Useful for a second identical AC unit, or a sandbox copy for testing action mappings.

<p align="center"><img src="images/screenshots/promote-dialog.png" alt="Adopt dialog for creating a new HAIR device from an unknown remote" width="420"></p>

## Set up an air conditioner

An AC remote does not send single buttons, it sends whole states: every press carries the complete mode, fan, swing, and temperature the unit should switch to. HAIR handles that as a climate entity driven by a full state matrix instead of a list of commands.

To set one up:

1. Drop a SmartIR climate JSON file onto the **Closet** (or find one already there).
2. Click **ADOPT** on the entry.
3. HAIR creates a fully-controlled `climate` entity. Change the temperature or mode on the thermostat card, and HAIR looks up and sends the matching code.

Swing and temperature controls appear only when the file's matrix actually has those dimensions. The device's detail page grows a STATE MATRIX card where you can browse the lattice one branch at a time, see which state was last transmitted, send any state directly, or press **+ Command** to save one you use often as a one-tap command. Temperatures display in your install's unit while the file's native numbers stay untouched underneath; climate files are read as Celsius unless they say otherwise. To prove the matrix works on your hardware, run **Validate for Perfect Fit** (see [Fit a wig](#fit-a-wig)); the checklist covers 12 to 20 rows for the modes, fan speeds, swing positions, and temperature extremes instead of every cell.

A few limits to know: files whose codes are stored as Xiaomi-controller Raw are refused, because that format is proprietary rather than timing data; a small share of corpus cells (roughly half a percent) cannot be converted and are skipped, with the reason written into the wig's notes. HAIR never invents a code for a state the file does not carry.

## Import codes (SmartIR and the closet)

The Closet is where portable code sets, called wigs, live. Two kinds of entries hang there: codebooks installed with Home Assistant's core infrared code library, and your own wig files, organized by brand. Search covers brand, name, and product identifiers like UPC, FCC ID, or ASIN, so a barcode typed off the box finds its wig. The Closet also converts several outside formats the moment you drop them in.

To import a file:

1. Open the **Closet** tab.
2. Drag a file onto the tab, or click **Browse**. HAIR reads it, converts it if needed, and shows a receipt naming the brand it filed under.
3. If the codes are already in your closet, the receipt turns yellow and lists every place they already hang. If the file supersedes a wig you already have, HAIR offers to replace the old one instead of filing a duplicate.
4. Click **ADOPT** to turn the entry straight into a device, or **CLIP** to test it on the Clipper first.

Five formats convert on drop: wig files (`.wig.json`, filed as-is), SmartIR JSON (media player, fan, and climate, in all four SmartIR encodings), Flipper Zero `.ir` files, LIRC `lircd.conf` files, and Girr exports. Anything a conversion has to skip is written into the wig's notes with a reason, so a partial import is never silent.

Every arrival is also combed on the way in. Combing is a different question from fitting: a fitting asks whether a code works on your hardware, combing asks whether a wig's codes agree with each other, and it can answer that on its own, without hardware or a protocol decoder. It catches things like a cell that quietly sends its neighbor's code, a frame too short for the device to register, or a gap in an otherwise complete temperature run. The comb glyph on a closet row stays plain grey until something is checked, glows yellow when a finding needs a look, and glows red for the one class worth interrupting you for: the neighbor's-code mix-up, since the device answers and looks like it worked while quietly setting the wrong state.

![Closet tab with brand shelves, count chips, the oxblood drop bar, and library and personal wigs side by side](images/screenshots/closet.png)

## Share a wig

To share a device you have built:

1. Open the device's detail view.
2. Click **Save to Closet**.
3. Pick a route: **Save as New** files a fresh wig and leaves the original alone. **Update Closet Wig** brings the shared file up to date with your device, and warns you first if the update would retire someone else's fitting. **Validate for Perfect Fit** proves every command works on real hardware, see [Fit a wig](#fit-a-wig) below.

**Validate for Perfect Fit** only appears on a device that came from a wig in the first place. A device built from scratch just sees Save.

## Fit a wig

A wig in your closet is a saved set of codes. A fitting is proof those codes actually work, and the proof travels with the file from then on.

To fit a wig:

1. Adopt the wig onto a device and use it normally until you trust it.
2. Open the device, click **Save to Closet**, and choose **Validate for Perfect Fit**.
3. Hit **TEST** on each row of the checklist. HAIR reports SENT, or SENT and HEARD if a receiver caught the transmission.
4. If your hardware genuinely cannot manage a command, mark that row "could not make it work" instead of skipping it. Three people excluding the same row tells you something real is going on.
5. If your device has gained or dropped commands since the wig was last saved, review the **Changes with new fitting** section before you sign.
6. Sign. Your verdicts tie to a key generated on your own install, not the name you type, so nobody can edit your results or fit in your name. Fitting the same wig again later just replaces your old signature.

To fix a broken code, do it on the device itself, not in the fitting screen: open the command, paste in a corrected Pronto code or press **LISTEN** to capture it fresh, then save. Run **Update Closet Wig** afterward to push the fix back to the shared file (state-matrix AC wigs are the exception; they repair in place and recomb automatically). A repaired wig is a different wig, so a change to any command starts a brand new fitting carrying only your signature, current until someone else fits the corrected version too.

Give the device a beat between presses so you can watch it react before marking a row. Fittings are what make a shared wig trustworthy, and only fitted wigs can graduate into generated Home Assistant integrations.

## Set up triggers

Any IR signal can fire a Home Assistant automation as a native event entity.

To create a trigger:

1. Click the trigger button on a signal row. There are four places to find one: a command on a device, a signal in the Sniffer, a signal in the Clipper, or a recorded send in the Mirror.
2. Set **min hits** (1 to 10) if you want to require more than one press before the trigger fires. This filters out stray or accidental presses.
3. Save. HAIR creates an `event` entity (for example `event.hair_triggers_tv_power`) under a shared "HAIR Triggers" device.
4. Use that entity as a trigger condition in HA's automation editor. Its card flashes amber in the panel whenever it fires.

A trigger created from a Sniffer or Clipper row reacts to a raw signal without needing it assigned to a device first. A trigger created from a Mirror row only fires on signals arriving from outside Home Assistant; the house's own sends never fire it, so an automation cannot trigger on its own output.

<p align="center"><img src="images/screenshots/trigger-dialog.png" alt="Create Trigger dialog with S/L diamond pattern and min hits setting" width="420"></p>

## Use the Mirror

The Mirror logs every IR command Home Assistant sends, at the moment it is sent, and whether a receiver heard it land.

To use it:

1. Send a command from a device, a Test button, an automation, or another integration on the `infrared` platform.
2. Open the **Mirror** tab and find the row.
3. Check the heard-back column. "Not heard" is neutral, not an alarm, since many setups are transmit-only, but it is how you spot a dead IR LED, a misaimed emitter, or an offline device without pointing a phone camera at anything.
4. Use the filter chips or search to narrow the list to one emitter or protocol.
5. Click **Assign** on a row to turn a command another app sent into a HAIR command, or **Trigger** to turn it into an automation trigger.

Repeat sends of the same command bump one row's count instead of piling up. Deleting a row just clears the entry; it comes back the next time that signal is sent. The Mirror is also the third road for importing codes, next to the Clipper (paste) and the Plucker (pull by name): press a button in any vendor app whose blaster transmits through the `infrared` platform, and if a receiver hears it, the code appears in the Mirror ready to assign.

![Mirror tab logging every HA-originated IR send with provenance chips, heard-by areas, and send counts](images/screenshots/mirror-tab.png)

## Everything else

### How it works

HAIR does not talk to hardware directly. It sits on HA's native `infrared` platform for both capture and send, so any integration that adopts the platform works with HAIR automatically, and signals are matched with S/L pulse-duration fingerprinting rather than per-protocol decoding.

### The Devices tab

The main view groups your setup into cards: **HAIR Devices** (your managed profiles; drag to reorder, duplicate or delete from the corners of the card), **Triggers** (active automation triggers, flashing amber when one fires), **Emitters** and **Receivers** (your IR hardware, each showing a TX or RX badge, with `-NATIVE` or `-BRIDGE` marking which path a receiver is using), **Proxies** (hardware with both TX and RX on one board), and **Blasters** (pluckable vendor blasters, shown only when one is configured).

![Devices overview showing HAIR Devices, Triggers, Emitters, Receivers, and Proxies](images/screenshots/devices-overview.png)

### Editing signals and commands

Every signal and command has a copy/edit glyph that opens a single editor: read the raw Pronto code, copy it, or replace it by pasting a new code or pressing **LISTEN** to capture it fresh off the remote. Editing updates the fingerprint and decoded identity, and moves any trigger bound to that signal along with it. Renaming a command updates any action mapping that pointed at the old name. A device command is a copy of the signal it was assigned from, so editing a catalog signal in the Sniffer or Clipper does not change commands already assigned from it; edit the command on the device itself to change what that device transmits. If a signal's carrier reads off the common IR standards, the editor offers a "Snap to N kHz" button that re-encodes it to the nearest standard (30, 33, 36, 38, 40, or 56 kHz) before you save.

### A few more things

- **Emitter routing** -- each device can be pinned to one emitter or broadcast through several, so an AC command stays in one room while a TV Power command reaches every room at once.
- **Mobile navigation** -- a back-to-sidebar button appears on phone and tablet screens.
- **Ten languages** -- the panel and setup wizard follow your Home Assistant profile language automatically; see [Translations](#translations) below.

### Entity platforms

| Type | HA entity | Controls |
|------|-----------|----------|
| Media Player | `media_player` | Power, volume, mute, source, channels, navigation, transport |
| AC | `climate` | HVAC modes, temperature presets or a full state matrix, fan modes, swing |
| Fan | `fan` | Power, speed stepping or direct speed levels (1-10), oscillate |
| Light | `light` | On/off, brightness stepping |
| Switch | `switch` | On/off |
| Screen | `cover` | Open, close, stop |
| Other | `remote` | Generic IR command sender |

Every device also gets a `remote` entity for arbitrary Pronto codes and a `button` entity for each learned command.

### ESPHome hardware

If your ESPHome device already has `remote_transmitter` and `remote_receiver` blocks, one addition registers both on HA's native `infrared` platform:

```yaml
infrared:
  - platform: ir_rf_proxy
    name: IR Emitter
    id: ir_proxy_tx
    remote_transmitter_id: ir_tx     # your remote_transmitter id
  - platform: ir_rf_proxy
    name: IR Receiver
    id: ir_proxy_rx
    receiver_frequency: 38kHz
    remote_receiver_id: ir_rx        # your remote_receiver id
```

Reflash, and the Devices tab shows the emitter with a `TX-NATIVE` badge and the receiver with `RX-NATIVE`.

For ready-made configs for common ESP32 boards (XIAO Smart IR Mate, Athom RF IR Remote, M5Stack IR Unit, generic ESP32s), see [`esphome/`](esphome/) in this repo.

<details>
<summary><b>Starting from scratch? The complete minimal YAML (TX + RX + registration)</b></summary>

```yaml
# --- IR Transmitter (TX) ---
remote_transmitter:
  id: ir_tx
  pin: GPIO9        # your IR LED pin
  carrier_duty_percent: 50%
  non_blocking: true

# --- IR Receiver (RX) ---
remote_receiver:
  id: ir_rx
  pin:
    number: GPIO8   # your IR receiver data pin
    inverted: true
    mode:
      input: true
      pullup: true
  dump: all
  tolerance: 25%
  idle: 10ms

# --- Register both on HA's native infrared platform ---
infrared:
  - platform: ir_rf_proxy
    name: IR Emitter
    id: ir_proxy_tx
    remote_transmitter_id: ir_tx
  - platform: ir_rf_proxy
    name: IR Receiver
    id: ir_proxy_rx
    receiver_frequency: 38kHz
    remote_receiver_id: ir_rx
```

</details>

<details>
<summary>Legacy bridge for HA 2026.4-2026.5 (only if you cannot upgrade)</summary>

Before native `InfraredReceiverEntity` shipped in HA 2026.6, HAIR received signals over an event-bus bridge. If you are stuck on 2026.4 or 2026.5, add this to your ESPHome device's `remote_receiver` block:

```yaml
remote_receiver:
  id: ir_receiver
  pin:
    number: GPIO5   # your IR receiver data pin
    inverted: true
  dump: pronto
  on_pronto:
    then:
      - homeassistant.event:
          event: esphome.remote_received
          data:
            protocol: "PRONTO"
            code: !lambda 'return x.data;'
```

This fires every IR signal as a `homeassistant.event` on the HA bus, and the HAIR Sniffer subscribes automatically. The panel shows `RX-BRIDGE` on the receiver card while this path is in use. When you upgrade to 2026.6+, add the `infrared` platform receiver entry above and reflash; HAIR switches over automatically, and you can remove the `on_pronto:` block once `RX-NATIVE` appears.

</details>

### Translations

HAIR speaks ten languages, and eight of them need a native-speaker review. Spanish has one already (thanks @Waterbrain). French, Japanese, German, Polish, Portuguese, Dutch, Italian, and Russian were drafted by a programming assistant and are marked "reviewer wanted" inside each dictionary file. A native-speaker pass over one file is all it takes, and your name goes in the file as its reviewer. See [Adding a language](CONTRIBUTING.md#adding-a-language).

<details><summary>See the panel translated -- the same device detail in Spanish, the one translation with a native-speaker review</summary>

![Device detail rendered in Spanish with translated action badges and buttons, native-speaker reviewed by @Waterbrain](images/screenshots/device-detail-translated.png)

</details>

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### License

MIT. See [LICENSE](LICENSE) for details.
