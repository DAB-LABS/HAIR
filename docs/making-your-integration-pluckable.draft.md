# Making your integration pluckable

A user pairs your IR blaster with their Home Assistant. They sit on the
couch with their TV remote and learn thirty buttons into your vendor app:
Power, Volume Up, Mute, every input source, every favorite channel. It
took an evening. The codes work, they fire IR through your hardware, life
is good.

Then they decide they want those codes to live in Home Assistant
directly, not just be addressable through your integration. Maybe they
bought a new blaster. Maybe they want one HA event to fire two TVs in
different rooms. Maybe they just want their IR captures portable the same
way Z-Wave devices are portable. So they install HAIR (or any tool like
it) and discover the only path is to re-learn all thirty buttons one at a
time at a separate ESPHome receiver. An evening's worth of clicking the
same buttons in front of a different antenna. That is friction your users
feel, even if they never tell you about it.

If your integration can do one specific thing, HAIR can pull those codes
in for them by name -- no re-learning, no air-broadcast, nothing for the
user to do beyond typing the names they already know. The "one thing" is
a Home Assistant service that replays a stored code by name through a
caller-chosen target emitter on HA's native `infrared` platform. Tuya
Local was the first to ship one (`tuya_local.send_learned_ir_command`),
and HAIR's Plucker turns it into a single dialog the user runs through.

This page explains what that contract looks like, what it costs you, and
how Tuya Local actually did it. If you're skimming, the short version is
that it's one service with one extra parameter, and the rest of your
integration does not change.

## Why bother

Becoming pluckable is additive. The same service, pointed at your own
blaster, still fires IR the normal way. Nothing about your existing user
flows changes. What changes is that your hardware stops being a dead end
for power users. They can carry their codes forward without losing what
they invested in learning them, and they're more likely to recommend your
hardware to others because of it.

There's also an architectural argument. HAIR is hardware-agnostic by
design. It does not read your storage format, does not parse your wire
protocol, does not even know your integration exists at the code level.
The seam it uses is HA's `infrared` platform, the one HA core added in
2026.4 for exactly this kind of thing. If your integration speaks that
seam, every tool downstream of HA's infrared platform works with you
automatically. The Plucker is the first such tool. There will be more.

## The contract

Four points. If your integration meets all four, it's pluckable, and the
rest of this document is how to wire it up.

1. **Replay a stored code by name.** The user picks a command by the name
   they learned it under (`pwr_on`, `Volume Up`, whatever) and HAIR
   passes that name to your service. Not a raw blob, not an opaque id --
   the friendly name your app uses.

2. **Accept a caller-chosen target emitter.** Your service takes an
   emitter entity id as a parameter and routes the code through
   `infrared.async_send_command(emitter_entity_id, command)`. If the
   caller names your own blaster, the code fires from your hardware. If
   the caller names a different emitter, the code goes there instead.
   This one parameter is what makes the integration pluckable. Without
   it, the code can only ever fire from your own hardware and HAIR has
   no way to catch it.

3. **Build a real `infrared` platform `Command`.** Whatever your stored
   format is (Pronto, raw timings, base64, vendor-specific), construct
   the `Command` from it and send it through the platform. HAIR takes
   whatever the platform `Command` carries, no further unpacking needed.

4. **Await the send.** `await` the dispatch chain through
   `infrared.async_send_command` so the `Command` is delivered before
   your service call returns. HAIR captures inside that await, so a
   synchronous await makes the pluck deterministic. Fire-and-forget
   invites a race.

Minimum HA on the receiving side is 2026.6, where the `infrared`
platform exports `InfraredEmitterEntity` (the class HAIR's observer
extends).

## Tuya Local: how it actually looks

Before Tuya Local 2026.6.2, transmit was a closed loop. The code never
touched HA's `infrared` platform:

```
remote.send_command -> Tuya Local handler -> Tuya hardware -> IR LED
```

Tuya Local 2026.6.2 shipped `tuya_local.send_learned_ir_command`. It
builds the `Command` from Tuya's learned-code storage and sends it
through the platform, targeting a caller-chosen emitter:

```
tuya_local.send_learned_ir_command
   -> Command built from Tuya storage
   -> infrared.async_send_command(emitter_entity_id, command)
   -> the chosen emitter's async_send_command()
```

The call looks like this, with the target emitter pointed at HAIR's
observer:

```yaml
action: tuya_local.send_learned_ir_command
target:
  entity_id: remote.ir_remote_garage
data:
  command: pwr_on
  device: candles
  emitter_entity_id: infrared.hair_tweezer
```

`command` is the stored name. `device` is Tuya's appliance grouping
(which HAIR carries as its appliance field; if your store is flat, you
don't need it). `emitter_entity_id` is the target. Point that last value
at your own blaster and the code fires from your hardware; point it at
HAIR's observer and HAIR catches it. Same service, same code, different
destination. That's the whole trick.

## How HAIR uses your service (under the hood)

HAIR registers its own emitter on HA's `infrared` platform: a no-transmit
observer called the HAIR Tweezer. When a `Command` is routed to the
Tweezer, the Tweezer does not drive an LED. It captures the `Command`
and hands it to HAIR's normal signal pipeline (fingerprint, decode,
store). No IR is broadcast during a pluck.

End to end:

```
HAIR asks your integration to replay code "pwr_on"
   through emitter = the HAIR Tweezer
        -> your service builds the Command from its store
        -> infrared.async_send_command(tweezer, command)
        -> Tweezer.async_send_command(command) captures it
        -> HAIR stores it as a native signal
```

Your integration never has to know HAIR exists, never has to add HAIR
as a dependency, never has to special-case the Tweezer entity. It just
has to be willing to dispatch a stored code through an emitter the
caller names.

## A few things we learned building the receiving side

Some of these you'd figure out anyway, but they're worth saying out loud
because they're the things we wish we'd known up front.

Pick clear parameter names. `emitter_entity_id` reads well and matches
the platform vocabulary. Keep it a normal service field so it shows up
in Developer Tools and any caller can set it. Same for the command-name
field -- `command` is fine. Whatever you pick, it should look obvious in
the Services UI without needing the docs open.

Raise readable errors. If a required parameter is missing or a code name
isn't in storage, raise a normal Home Assistant error with a clear
message. HAIR catches these and surfaces them to the user with your
integration name as a prefix, so a Tuya error becomes "Tuya: device must
be specified" in the Pluck dialog. Cryptic exceptions become cryptic
prefixed exceptions.

If you group codes under an appliance, keep the grouping in the service
parameters. Tuya does (`device: candles`). HAIR carries one appliance
field per blaster for exactly this. If your store is flat, you don't
need the field, and HAIR won't ask the user for one.

Advertise `LEARN_COMMAND`. If your `remote.*` entities set
`RemoteEntityFeature.LEARN_COMMAND` in `supported_features`, HAIR (and
other tools) can discover which of your entities hold learnable codes.

## Wiring it into HAIR

Once your integration ships the service, getting HAIR to offer your
hardware in the Plucker tab is a single YAML file in HAIR's repo. No
HAIR Python changes. You describe your service shape (its domain, name,
target parameter, and how to fill its data from the three values HAIR
supplies) in one file, schema-check it, open a one-file PR.

The full field reference, the placeholder rules, the standalone schema-
check command, and the pull-request checklist are in the registry guide:

- [`custom_components/hair/pluckable/README.md`](https://github.com/DAB-LABS/HAIR/blob/main/custom_components/hair/pluckable/README.md)

The Tuya Local entry,
[`tuya_local.yaml`](https://github.com/DAB-LABS/HAIR/blob/main/custom_components/hair/pluckable/tuya_local.yaml),
is a complete worked example you can copy from.

## Summary

Expose one service that replays a stored code by name through a
caller-chosen `infrared` emitter, await it, and you're pluckable. HAIR
points that service at its own observer, catches the code, and stores it
as a native signal. Your users keep the codes they already learned, your
hardware becomes an on-ramp into Home Assistant instead of a silo they
have to leave things behind in, and the Plucker tab adds your
integration's entry on its own.

Tuya Local did it first. We'd like yours to be next.
