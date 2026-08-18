# Air-path fixtures

Real captures and real code sets from the air-path identity
characterization run of 2026-08-17 (report:
`scratch/air-path/air-path-report.md` on the exchange share). They are
the evidence behind the receiver-tolerant tier in `identity.py`, and
they are here so the claim can be re-checked rather than believed.

| File | What it is |
|---|---|
| `captures.csv.gz` | 51 captures of four codes, ten presses each per transmitter: the timings the Athom receiver actually delivered, with the identity HAIR stored for each. Columns: code, transmitter (esphome / broadlink / inject), first_seen, edge_count, fingerprint, byte_hash, decoded_fingerprint, timings_us. |
| `C1.pronto` `C2.pronto` | Two cells of the Mitsubishi SG15H lattice (cool/auto/23 and heat/low/20), as the FILE holds them. |
| `F1.pronto` | ACER RC-17DE0 Power, a short flat undecoded code, as the file holds it. |
| `D1.pronto` | A Samsung TV button: the decoded control. Every capture of it reads SAMSUNG32:0x0007:0x02 whatever the air does. |
| `sg15h-matrix.json.gz` | The 34 distinct codes of that 64-cell lattice (the unit ignores temperature in dry and fan_only, so sixteen cells share one code twice over), plus its off frame. |
| `acer-rc-17de0.json.gz` | The 16 signals of the ACER wig. |

The two transmitters are the extremes we can reach: `esphome` is a
microsecond-accurate ESP32 raw transmit, `broadlink` is a consumer
blaster on a 32.84 us tick. `inject` is the bench_rx service, which
hands HAIR the file's own timings and is the control -- it reproduces
the file identity exactly, which is what proves the miss is the air
path and not the identity code.
