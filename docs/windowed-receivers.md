# Windowed receivers

A guide for Home Assistant integration authors whose IR or RF receiver hears
codes only while a capture window is open: a hub that listens in a learn mode,
or a blaster that has to be told to start listening. If your receiver is on
Home Assistant's `infrared` or `radio_frequency` platform and says it works
this way, HAIR treats it as a capture device. It opens and closes the window
for the user, from the receiver's pill at the top of the Sniffer and whenever a
listen in HAIR needs one, and it hears the codes your receiver reports like
any other receiver's.

Nothing here names an integration. HAIR reads a few state attributes on your
receiver entity, and any integration that sets them gets the same treatment.

## The attributes

Set these as extra state attributes on the receiver entity itself, the
`InfraredReceiverEntity` or `RadioFrequencyReceiverEntity`.

| Attribute | Type | Required | What HAIR does with it |
|---|---|---|---|
| `capturing` | boolean | Yes | `true` while the window is open, `false` while it is closed. Its presence is what makes the receiver a capture device. |
| `capture_switch` | entity ID | Recommended | The entity HAIR turns on to open the window and off to close it. |
| `window_ends_at` | ISO 8601 timestamp | Optional | When the open window will close. HAIR's receiver pills drain toward it, and snap back to full when it moves. |
| `capture_mode` | `single`, `sliding` or `multiple` | Optional | Only `single` changes what HAIR does (below). |
| `capture_phase` | `sweeping`, `listening` or `null` | Optional | What an open window is doing (below). `sweeping`: the device is still searching for the carrier and hears no codes yet. `listening`: the device is hearing codes. `null` while the window is closed. Without it, an open window is taken to be listening. |
| `frequency_hz` | integer | Optional | The carrier, in Hz, the open window is listening on. HAIR uses it as the frequency of a code heard in that window when the signal itself carries none. `null` while sweeping or closed. |
| `frequency_select` | entity ID | Optional | A `select` that sets the carrier the next window listens on. HAIR offers it as the pill's frequency picker (below). |
| `frequency_options` | map | With `frequency_select` | What each of that select's options means: a carrier in Hz, or `sweep`. |
| `window_length` | entity ID | Optional | A `number` that sets how long the next window stays open, in seconds. HAIR offers it as the pill's length picker. |
| `capture_mode_select` | entity ID | Optional | A `select` that sets the next window's `capture_mode`. HAIR offers it as the pill's type picker. |

`capturing` must be a real boolean. A string such as `"on"` does not count.
Nothing else makes a receiver a capture device: in particular, a switch on the
receiver's device does not.

While your receiver is unavailable, Home Assistant writes no extra attributes,
so `capturing` is missing then. HAIR remembers which receivers have been
capture devices and keeps treating one as a capture device while it is
unavailable, with its controls disabled until it is back. An available
receiver without `capturing` is an ordinary, always-listening receiver.

Mark the receiver unavailable when its device stops answering, not only when
your integration unloads: while it still reports itself available, HAIR offers
it to Listen and tries to open a window that will never open.

### Capture modes

- `sliding` (or no `capture_mode`): each code moves `window_ends_at` later.
- `multiple`: the window keeps its end time however many codes arrive.
- `single`: the window closes after its first code.

When HAIR opens a window for a listen and the window closes before the listen
is done, HAIR opens it again, except in `single` mode, where the window is the
whole listen. The one exception is the Fix window, which waits for several
presses in a row: there a `single` window that closed after a code is opened
again, and one that closed empty ends the listen. A window that closes again
within half a second of HAIR opening it ends the listen with an error, so a
receiver that cannot really listen never puts HAIR in a loop.

HAIR closes a window only if HAIR opened it. A window the user opened from
your integration's own controls is left as it is.

### Sweeping

Some RF devices must find the remote's carrier before they can hear a code:
the user holds a button while the device sweeps the band, and only then does
it listen. Report this with `capture_phase`. While it reads `sweeping`, the
window is open (`capturing` is `true`) but nothing will be heard yet, and HAIR
tells the user to hold the button. When the device locks, set `capture_phase`
to `listening` and `frequency_hz` to the carrier it locked on. A sweep that
finds nothing ends the window like any other: set `capturing` to `false` and
`capture_phase` to `null`. Turning the capture switch off during a sweep must
cancel it.

A device that listens on a fixed or user-chosen carrier never sweeps. It can
report `listening` for the whole window, with `frequency_hz` set to that
carrier, or leave both attributes out.

`frequency_hz` is the carrier the window listens on, not a measurement of the
code. When your receiver can measure a code's own carrier, put it on the
received signal's `frequency`; HAIR prefers that over `frequency_hz`.

### The window's settings

A device whose window has settings of its own, such as the carrier to listen
on, how long to stay open, or the capture mode, can let the user set them from
HAIR. Declare the entity behind each one, and HAIR puts a small picker for it
on the receiver's pill. Choosing writes the entity through Home
Assistant's own services (`select.select_option`, `number.set_value`), so the
setting lives in your integration and applies however the window is opened.

- `frequency_select` names a `select`. HAIR does not guess what its options
  mean from their names: declare `frequency_options` beside it, a map from
  each option to its carrier in Hz, or to the word `sweep` for an option that
  makes the device sweep for the carrier. HAIR offers exactly the options in
  the map, in its order, and only when there are two or more. When the select
  is on an option the map leaves out, the picker shows the carrier the device
  reports in `frequency_hz` and does not offer that option.
- `window_length` names a `number` in seconds. HAIR offers the lengths it
  knows (10, 30 and 60 seconds, 2 and 5 minutes) that fall within the
  number's own `min` and `max`.
- `capture_mode_select` names a `select` whose options are the
  `capture_mode` values, `single`, `sliding` and `multiple`. HAIR offers the
  ones your select has.

```yaml
frequency_select: select.office_rm4_pro_rf_frequency
frequency_options:
  mhz_433_92: 433920000
  mhz_315: 315000000
  sweep: sweep
window_length: number.office_rm4_pro_capture_window
capture_mode_select: select.office_rm4_pro_capture_mode
```

The pickers cannot be used while the window is open; they show the settings
the window opened with, and after a sweep locks, the carrier it found. Declare
only what the user can change: a receiver on a single fixed carrier needs no
`frequency_select`. Each declaration follows the safety rule below, and one
that fails it is ignored on its own, without costing the others.

The pill's badge shows whether the receiver is taking new codes: solid while your window is open, light while it is closed. The pickers are inactive while a window is open, because a change applies to the next one. A receiver without `capturing` is not a capture device; if it is a radio receiver, HAIR keeps its own capture window for it, and none of this contract applies.

## Which entity HAIR toggles

HAIR resolves the entity that opens the window in this order:

1. **Your declaration**, the receiver's `capture_switch`, when it passes the
   safety rule below. It cannot be overridden: the receiver's pill offers no
   switch menu, and HAIR refuses to store a choice for the receiver. HAIR
   remembers the declaration while the receiver is unavailable, since Home
   Assistant drops the attribute then. Declare the switch whenever your device
   has more than one, such as an IR and an RF capture switch, so the user
   cannot pick the one that opens the wrong window.
2. **The user's choice.** For a capture device that declares nothing, a caret
   on its pill opens a menu of the switches on its device, with the one
   in use checked, then "Choose another..." for any switch or
   toggle helper. The choice is stored by the receiver's entity registry entry,
   so a rename keeps it. A choice stored before you declared is kept, and
   applies again if the declaration is removed.
3. **The device's only switch.** When the receiver's device has exactly one
   enabled `switch` entity, HAIR uses it, already checked in the menu.
4. **None.** The receiver's pill stays gray and cannot be pressed until the user
   chooses from its menu. HAIR does not guess between several
   switches by name: a wrong guess would toggle something the user never
   chose, such as a power switch.

### Use a switch, not a button

Expose the window as a `switch`: on while the window is open, and off once it
closes, whether it timed out, heard its code or was turned off. Turning it off
only closes the window. The switch's state tells HAIR and the user whether the
device is listening, and lets HAIR stop a window early. A `button` can only
start a window: HAIR has nothing to press to stop it and nothing to read but
`capturing`. HAIR toggles switches and toggle helpers only, so a device that
offers just a learn button cannot be driven from HAIR yet.

## The safety rule

HAIR toggles only:

- a `switch` entity on the receiver's own Home Assistant device, or
- an entity the user chose by hand, which must be a `switch` or an
  `input_boolean`.

HAIR sets a window's settings only through entities on the receiver's own
device, in the domain each declaration names: a `select` for
`frequency_select` and `capture_mode_select`, a `number` for `window_length`.
A declaration that names anything else is ignored, and its picker is not
shown. `frequency_options` counts only beside a `frequency_select` that
passes.

A `capture_switch` that names anything else, such as a switch on another
device or an entity in another domain, is ignored and logged once at debug
level, and the receiver is treated as declaring nothing: the user's choice
applies and the pill's menu offers the device's switches again. HAIR's
websocket commands take a receiver, never an entity to toggle, so nothing
outside these rules can be switched through HAIR.

## An example entity

A receiver with its window closed:

```yaml
entity_id: infrared.office_rm_mini_ir_receiver
attributes:
  friendly_name: Office RM mini IR receiver
  capturing: false
  capture_switch: switch.office_rm_mini_ir_capture
  window_ends_at: null
  capture_mode: sliding
```

The same receiver while its window is open:

```yaml
attributes:
  friendly_name: Office RM mini IR receiver
  capturing: true
  capture_switch: switch.office_rm_mini_ir_capture
  window_ends_at: "2026-10-19T09:13:10.000+00:00"
  capture_mode: sliding
```

`switch.office_rm_mini_ir_capture` is on the same device as the receiver.
Turning it on opens the window and sets `capturing` to `true`; turning it off,
or the window running out, sets it back to `false`.

An RF receiver that sweeps for the carrier, while it searches:

```yaml
entity_id: radio_frequency.office_rm4_pro_rf_receiver
attributes:
  friendly_name: Office RM4 pro RF receiver
  capturing: true
  capture_switch: switch.office_rm4_pro_rf_capture
  window_ends_at: "2026-10-19T09:13:10.000+00:00"
  capture_mode: single
  capture_phase: sweeping
  frequency_hz: null
```

and once it has locked:

```yaml
attributes:
  friendly_name: Office RM4 pro RF receiver
  capturing: true
  capture_switch: switch.office_rm4_pro_rf_capture
  window_ends_at: "2026-10-19T09:13:10.000+00:00"
  capture_mode: single
  capture_phase: listening
  frequency_hz: 433920000
```

[BroadSniff](https://github.com/DAB-LABS/broadsniff), which gives a Broadlink
RM a receiver, is the worked example. Its 0.1.0 sets `capturing` and
`window_ends_at` only, and HAIR uses the one IR capture switch on the device;
on an RF-capable model there are two switches, so the user chooses. From 0.2.0
it also declares `capture_switch` and `capture_mode`. From 0.3.0, an
RF-capable model also has an RF receiver with its own capture switch, which
reports `capture_phase` and `frequency_hz` and sweeps when the user sets the
RF frequency to sweep, and both receivers declare `window_length` and
`capture_mode_select`, the RF receiver also `frequency_select` with its
`frequency_options`, so the length, type and frequency are set from the
pill.

## If Home Assistant adopts a capture feature

The attribute names were chosen to map onto a capture feature on Home
Assistant's own infrared receiver, should core add one. If it does, this
contract will follow core's, and HAIR will read core's version.
