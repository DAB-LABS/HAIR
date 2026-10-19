# Windowed receivers

A guide for Home Assistant integration authors whose IR receiver hears codes
only while a capture window is open: a hub that listens in a learn mode, or a
blaster that has to be told to start listening. If your receiver is on Home
Assistant's `infrared` platform and says it works this way, HAIR treats it as a
capture device. It opens and closes the window for the user, from the
Sniffer, the Devices tab and the code editor, and it hears the codes your
receiver reports like any other receiver's.

Nothing here names an integration. HAIR reads a few state attributes on your
receiver entity, and any integration that sets them gets the same treatment.

## The attributes

Set these as extra state attributes on the `InfraredReceiverEntity` itself.

| Attribute | Type | Required | What HAIR does with it |
|---|---|---|---|
| `capturing` | boolean | Yes | `true` while the window is open, `false` while it is closed. Its presence is what makes the receiver a capture device. |
| `capture_switch` | entity ID | Recommended | The entity HAIR turns on to open the window and off to close it. |
| `window_ends_at` | ISO 8601 timestamp | Optional | When the open window will close. HAIR's Listen chips drain toward it, and snap back to full when it moves. |
| `capture_mode` | `single`, `sliding` or `multiple` | Optional | Only `single` changes what HAIR does (below). |

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

## Which entity HAIR toggles

HAIR resolves the entity that opens the window in this order:

The capture device's card on the Devices tab shows one RX-CAPTURE chip, split
in two: the main part starts and stops a capture, and its caret opens a menu of
switches with the one in use checked. The chip's tooltip names that switch.

1. **Your declaration**, the receiver's `capture_switch`, when it passes the
   safety rule below. It cannot be overridden: the card's menu lists your
   switch alone, and HAIR refuses to store a choice for the receiver. HAIR
   remembers the declaration while the receiver is unavailable, since Home
   Assistant drops the attribute then. Declare the switch whenever your device
   has more than one, such as an IR and an RF capture switch, so the user
   cannot pick the one that opens the wrong window.
2. **The user's choice.** For a capture device that declares nothing, the menu
   lists the switches on its device, then "Choose another..." for any switch or
   toggle helper. The choice is stored by the receiver's entity registry entry,
   so a rename keeps it. A choice stored before you declared is kept, and
   applies again if the declaration is removed.
3. **The device's only switch.** When the receiver's device has exactly one
   enabled `switch` entity, HAIR uses it, already checked in the menu.
4. **None.** The chip and the card's icon stay grey, and a click on the chip
   opens the menu, until the user chooses. HAIR does not guess between several
   switches by name: a wrong guess would toggle something the user never
   chose, such as a power switch.

## The safety rule

HAIR toggles only:

- a `switch` entity on the receiver's own Home Assistant device, or
- an entity the user chose by hand, which must be a `switch` or an
  `input_boolean`.

A `capture_switch` that names anything else, such as a switch on another
device or an entity in another domain, is ignored and logged once at debug
level, and the receiver is treated as declaring nothing: the user's choice
applies and the card's menu offers the device's switches again. HAIR's
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

[BroadSniff](https://github.com/DAB-LABS/broadsniff), which gives a Broadlink
RM a receiver, is the worked example. Its 0.1.0 sets `capturing` and
`window_ends_at` only, and HAIR uses the one IR capture switch on the device;
on an RF-capable model there are two switches, so the user chooses. From 0.2.0
it also declares `capture_switch` and `capture_mode`.

## If Home Assistant adopts a capture feature

The attribute names were chosen to map onto a capture feature on Home
Assistant's own infrared receiver, should core add one. If it does, this
contract will follow core's, and HAIR will read core's version.
