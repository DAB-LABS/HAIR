# Field captures

Real captures contributed by people running HAIR, kept here so a claim
about what the air actually delivers can be re-checked rather than
believed. Same purpose as `../air-path/`, different source: those are
the bench's own, these came in from outside.

| File | What it is |
|---|---|
| `arc486a1-orthobot.pronto` | One press of a Daikin ARC486A1 air conditioner remote, 293 burst pairs: a short preamble frame, a 25.1 ms rest, then three long frames separated by 35.1 ms rests, and a 100.0 ms tail. |
| `gh206-mr401-pronto.csv` | 44 Pronto codes for a Telekom MR401 set-top box remote, one per button, as posted in GH #206. TDC-38. |
| `gh206-power-air.pronto` | One press of the Power button of the same family, captured off the air by the reporter of GH #206. |

## arc486a1-orthobot.pronto

Captured by forum user Orthobot (Mel) and posted on 2026-09-05 to the
HAIR community thread, after raising `remote_receiver`'s `idle` to
100 ms. Contributed publicly to the project with no conditions
attached; kept verbatim, byte for byte as posted.

It is here because it is the shape the decode-trust reviews kept
reaching for as the worst case and never had a real example of: the
35 ms gaps INSIDE one press are longer than the 10 ms idle the shipped
configurations used to ship with, which is what split a single press
into several codes and made one remote look like several. It is also
long enough to be a real test of the send-spacing entry cap, which is
the other thing the tests below use it for.

## gh206-mr401-pronto.csv and gh206-power-air.pronto

Posted publicly by MaxRower in GH #206 on 2026-10-08: the CSV is the list
in the issue body, kept verbatim with its header, and the `.pronto` file
is the capture of the Power button from the first comment on the issue.

They are here because they are the codes the issue was about: no decoder
read them, buttons whose codes had the same length shared one identity
(four identities for the 44 codes), and the Clipper accepted one code of
each length and refused the rest as "already on this remote". They are TDC-38
(device 6, subdevice 10 on every button). MenuHome and MenuMain in the
list are the same code. The air capture decodes to the same value as the
listed PowerToggle; it differs in layout (once section rather than
repeat) and in receiver jitter, not in content.
