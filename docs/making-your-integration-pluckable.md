# Making your integration pluckable

A guide for Home Assistant integration authors whose hardware stores IR codes
in its own memory, app, or cloud. If your integration can replay a stored code
by name through a chosen emitter, HAIR can pull those codes into Home Assistant
as native signals, and your users stop being locked into your silo. This page
explains what "pluckable" means, how HAIR does the plucking, the one service
contract you need to expose, how Tuya Local did it first, and what we suggest
you do.

## What "pluckable" means

Plenty of IR hardware learns codes into a private store: a vendor app, a cloud
account, or on-device memory. Those codes work, but only through that vendor's
own transmit path. A user who learned 30 buttons into a vendor blaster cannot
move them anywhere. They are stuck.

An integration is "pluckable" when it lets a caller ask it to replay one of
those stored codes, by name, through any emitter on Home Assistant's native
`infrared` platform rather than only through the vendor's own hardware. Once
that is true, HAIR can point the replay at an emitter it controls, catch the
code in flight, and store it as a native HAIR signal. The user keeps their
codes without re-learning a single button.

This is the same spirit as the rest of HAIR: move IR codes out of vendor
clouds, blaster memory, and config files, and into Home Assistant itself.

## Why it matters to your users

Today, a user coming from a vendor blaster with codes already learned has only
one way to get those codes into a hardware-agnostic setup: physically re-learn
each one at an IR receiver, button by button. For 30 to 50 codes that is real
friction, and it is friction your own users feel.

Becoming pluckable removes it. Their existing investment in learning codes
carries forward. Your hardware keeps working as before, and it also becomes a
good on-ramp instead of a dead end. Nothing about being pluckable stops a code
from still firing through your hardware the normal way.

## How HAIR plucks a code

HAIR does not talk to your hardware and does not read your storage format. It
uses one seam: HA's `infrared` platform lets a `Command` be sent to a chosen
emitter entity.

```
infrared.async_send_command(emitter_entity_id, command)
        -> the chosen emitter's async_send_command() runs
```

HAIR registers its own emitter on that platform, a no-transmit observer called
the HAIR Tweezer. When a `Command` is routed to the Tweezer, the Tweezer does
not drive an IR LED. It captures the `Command` object and hands it to HAIR's
normal signal pipeline (fingerprint, decode, store). No IR is broadcast during
a pluck.

So the whole flow, when a user plucks one code, is:

```
HAIR asks your integration to replay code "pwr_on"
   through emitter = the HAIR Tweezer
        -> your service builds the Command from its store
        -> infrared.async_send_command(tweezer, command)
        -> Tweezer.async_send_command(command) captures it
        -> HAIR stores it as a native signal
```

Your integration never has to know HAIR exists. It just has to be willing to
send a stored code through an emitter the caller names.

## The contract

To be pluckable, expose one Home Assistant service that meets all of the
following. Tuya Local's `send_learned_ir_command` is the reference shape.

1. Replay a stored code by name. The user picks a command by the name it was
   learned under (for example "pwr_on"), not by pasting a raw code blob. HAIR's
   pluck dialog collects exactly that one name and passes it to your service.

2. Accept a caller-chosen target emitter. The service must take an emitter
   entity id and route the code to that emitter via
   `infrared.async_send_command(emitter_entity_id, command)`. If the caller
   names your own blaster, the code fires from your hardware as usual. If the
   caller names a different emitter, the code goes there instead. This single
   parameter is what makes the integration pluckable. Without it, the code can
   only ever fire from your own hardware and HAIR cannot catch it.

3. Build a real `infrared` platform `Command`. Construct the `Command` from
   your stored code (Pronto, raw timings, whatever you hold) and send it
   through the platform. HAIR is hardware-agnostic and takes whatever the
   platform `Command` carries.

4. Await the full send. The service should `await` the send chain through
   `infrared.async_send_command` so the `Command` is delivered before the call
   returns. HAIR captures inside that await, so a synchronous await makes the
   pluck deterministic. A fire-and-forget call invites a race.

Minimum Home Assistant version for the receiving side is 2026.6, where the
`infrared` platform exports `InfraredEmitterEntity` (the class HAIR's Tweezer
extends). HA 2026.5 exports only the base `InfraredEntity`.

## How Tuya Local did it (the worked example)

Before Tuya Local 2026.6.2, transmit was a closed loop. The code never touched
HA's `infrared` platform:

```
remote.send_command -> Tuya Local handler -> Tuya hardware -> IR LED
```

Tuya Local 2026.6.2 shipped `tuya_local.send_learned_ir_command`. It builds the
`Command` from Tuya's own learned-code storage and sends it through the
platform, targeting a caller-chosen emitter:

```
tuya_local.send_learned_ir_command
   -> Command built from Tuya storage
   -> infrared.async_send_command(emitter_entity_id, command)
   -> the chosen emitter's async_send_command()
```

The call looks like this, with the emitter pointed at HAIR's Tweezer:

```yaml
action: tuya_local.send_learned_ir_command
target:
  entity_id: remote.ir_remote_garage
data:
  command: pwr_on
  device: candles
  emitter_entity_id: infrared.hair_tweezer
```

`command` is the stored name, `device` is Tuya's appliance grouping, and
`emitter_entity_id` is the target emitter. Point that last value at your own
blaster and the code fires from Tuya hardware; point it at the HAIR Tweezer and
HAIR catches it. Same service, same code, different destination. That is the
whole trick. Tuya Local is the first integration to ship this, which is what
made the Plucker possible.

## What we suggest

If you are adding a service like this, a few recommendations from building the
receiving side:

- Name the target parameter clearly. `emitter_entity_id` reads well and matches
  the platform vocabulary. Keep it a normal service field so it shows up in
  Developer Tools and can be set by any caller.
- Address codes by their learned name. A name is something a user recognizes
  and can type. A raw blob is not, and it defeats the point of pulling
  organized codes across.
- Await the send. Deliver the `Command` synchronously through
  `infrared.async_send_command` rather than scheduling it and returning early.
- Advertise `LEARN_COMMAND`. If your `remote.*` entities set
  `RemoteEntityFeature.LEARN_COMMAND` in `supported_features`, HAIR (and other
  tools) can discover which of your entities hold learnable codes.
- Group by appliance if you do. If your store organizes codes under an
  appliance or device name (as Tuya does), keep that grouping in the service
  parameters. HAIR carries one appliance field for exactly this. If your store
  is flat, you do not need it.
- Raise clear errors. If a required parameter is missing or a code is unknown,
  raise a normal Home Assistant error with a readable message. HAIR surfaces
  your message to the user with your integration name in front of it.
- Do not break the normal path. Being pluckable is additive. The same service,
  pointed at your own blaster, should still fire IR the usual way.

## Once your integration is pluckable

Wiring a pluckable vendor into HAIR is a single YAML file, no HAIR Python
changes. You describe the service shape (its domain and name, the target
parameter, and how to fill its data from the three values HAIR supplies) in one
registry file, and HAIR offers your hardware in the Plucker tab.

The full field reference, the placeholder rules, how to schema-check the file
without a HAIR dev setup, and the pull-request checklist are in the registry
guide:

- [`custom_components/hair/pluckable/README.md`](../custom_components/hair/pluckable/README.md)

The Tuya Local entry, [`tuya_local.yaml`](../custom_components/hair/pluckable/tuya_local.yaml),
is a complete worked example you can copy from.

## Summary

Expose one service that replays a stored code by name through a caller-chosen
`infrared` emitter, await it through `infrared.async_send_command`, and you are
pluckable. HAIR points that service at its own observer emitter, catches the
code, and stores it as a native signal. Your users keep the codes they already
learned, and your hardware becomes an on-ramp into Home Assistant rather than a
silo they have to leave things behind in. Tuya Local did it first; we would
like yours to be next.
