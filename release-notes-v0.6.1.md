v0.6.1 (Hot Towel Finish) is a cleanup release: small, verified fixes with a waiting user attached to nearly every one.

**NEC capture recovery.** Two new recovery passes for real-world captures the strict decoder rightly rejects. A capture that is one jittery pulse away from valid is re-read leniently and accepted only if NEC's own checksum validates, so a single dead-zone pulse can no longer split one button into two rows (reported by @blalor, whose two captures are now permanent test fixtures). And captures that open with leftover repeat chatter from a previous press are now sought to their true frame start before decoding.

**Real thermostats for IR air conditioners.** Name your AC commands "Temp 22", "Temp 24", "Temp 26" while assigning and HAIR wires the rest: each command maps to its temperature step, the climate card grows a real draggable thermostat bounded to your steps, and setting a temperature snaps to the nearest step and transmits the matching command. Deleting a temp command retires its step. Found by @ripolltata (GH #45), who read the source and caught a half-shipped feature. The climate entity also now follows your installation's temperature unit (metric users: your presets are Celsius, as they always should have been) and starts the dial at your middle step so there is a handle to grab.

**Samsung32 fused end pulses decode.** Some emitters replay the whole packet for repeats with no gap at the junction, welding the frame's end pulse to the next frame's leader. The decoder now tolerates the fused pulse; the protocol checksum still gates every decode. Found on the bench with real hardware.

**Sniffer hit glow.** The most-recent-hit Assign button wears a mint rim and blooms a mint ring on each new hit, replacing the old same-green pulse that disappeared into the button fill.

Also: the adopters table gains SMLIGHT Ultima native receiving (HA 2026.7), and the test dependency cap moves to infrared-protocols <9.0.

**Known issue.** When the startup heal merges duplicate rows, a trigger created on one of the merged rows can lose its yellow badge in the Sniffer (the surviving row carries a different waveform identity). The trigger keeps firing normally; only the badge display is affected. The proper fix, triggers following decoded identity the way commands already do, is planned as its own release.

Full changelog: https://github.com/DAB-LABS/HAIR/blob/main/CHANGELOG.md
