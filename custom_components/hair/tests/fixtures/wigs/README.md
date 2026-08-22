# Shop wigs, kept here as permanent regression fixtures

Two real files from the WigShop, both carrying real field defects, both
CC0. That combination is rare enough to be worth saying out loud: a
defect nobody invented, in a file we are allowed to keep forever.

Source: https://github.com/DAB-LABS/WigShop (CC0 1.0, see that repo's
LICENSE and the contributor declaration in its CONTRIBUTING.md).

| File | Origin | What it is here for |
|---|---|---|
| `dreo-fan-dr-haf004s-perfect-fit.wig.json` | WigShop PR #18, merged | Two of its seven buttons carry repeats that disagree with each other. Oscillate Horizontal splits 11, 12, 12, 12, 12, 12 and Speed Down 14, 12, 12, 13. The comb passed it clean before the repeat check existed, and was right to: nothing compared a signal's frames to its own other frames. Power is pinned to raw and is the pinned-to-raw coverage case. |
| `komeco-airconditioner-kos-09qc-3hx-perfect-fit.wig.json` | WigShop PR #19 | A 1,156-cell ZH/LT-01 lattice that is structurally flawless and semantically wrong: heat_cool at fan medium sends T+1 from 19 through 31 on all four swing modes, 52 cells. Release one uses it as the false-positive guard -- every structural check must stay silent on it -- and release two's field sweep is pinned to find exactly those 52 cells. |

Do not edit either file. They are evidence, and a fixture that gets
tidied stops being evidence.
