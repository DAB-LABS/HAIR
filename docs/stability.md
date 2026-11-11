# What 1.x promises

HAIR follows [semantic versioning](https://semver.org/) from 1.0.0 on. This page says what that means in practice: what stays put across every 1.x release, and what may change without notice.

Patch releases (1.0.1) fix things. Minor releases (1.1.0) add things. Anything on the list below that has to change in a way that breaks a setup waits for 2.0, and the release before it says so in its notes.

## Kept for all of 1.x

**Entities.** The unique ids and entity ids of entities HAIR has already created do not change. An entity platform may gain features; none is taken away.

**Events and device triggers.** What your automations listen to keeps its names and its data fields: the `ir_command_received` event type of trigger event entities, the `hair_trigger_fired` and `hair_state_heard` events, and HAIR's device triggers. A Remote's "Last pressed" entity names its event types after the buttons, so renaming a button renames its type; that is how it is meant to work, and the `trigger_id` in the event data is what survives a rename. New fields may be added to event data; existing ones are not renamed or removed.

**Wig files.** Every 1.x release reads every wig format HAIR has written, `hair-wig/1` through `hair-wig/5`, and a wig HAIR exports is readable by every later 1.x release. A later 1.x may add a format version for a new kind of content, as `hair-wig/4` did for extra lattices and `hair-wig/5` did for radio codes. It still reads every earlier one, and HAIR keeps writing the lowest version a file's content needs, so a plain wig stays readable by older installs. The format itself is documented in [The wig format](wig-format.md).

**Stored data.** HAIR's storage migrates forward on update, from any earlier version. Moving back to an older version after an update is not supported.

**Home Assistant version.** `hacs.json` names the oldest Home Assistant release HAIR supports. It moves forward as Home Assistant retires the APIs HAIR uses, and the release notes say so one release ahead.

**Contracts with other integrations.** The `capture_switch` declaration for windowed receivers ([Windowed receivers](windowed-receivers.md)) and the pluckable registry format ([Making your integration pluckable](making-your-integration-pluckable.md)) stay as documented.

## Not promised

These are internal and may change in any release:

- The panel's websocket commands (`hair/*`). They exist for the panel and nothing else.
- The Candy Drawer's text layout and its feed. It is a live console for reading and pasting into an issue, not an interface to build on.
- Diagnostics output, log messages and their wording.
- Module layout, internal names, test fixtures, and anything under `custom_components/hair/` that is not described above.
- Panel layout, wording and translations.

## If something on the list breaks

That is a bug. Please [open an issue](https://github.com/DAB-LABS/HAIR/issues) with the version you updated from and to.
