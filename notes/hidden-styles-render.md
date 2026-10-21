# Rendering the hidden Creative Styles — and why there is nothing to unlock

Goal: render the 7 menu-hidden Creative Styles (Neutral, Clear, Deep, Light, Night Scene,
Autumn leaves, Sepia) on clean frames with the simulator, using their **real** firmware
parameters if those can be identified.

## Mapping result (honest): no distinct hidden-style parameters exist in the 3N data

Searched statically for a `style value -> colour-matrix slot / tone-curve` mapping for all 13
styles. Findings (all verified):

- The only readable `style -> slot` table is for sharpening: `0x000300af +0x70` =
  `00 01 02 03 04 05 ff ff ff ff ff ff ff`. The 6 visible styles map to slots 0..5; **all 7
  hidden styles (menu IDs 6..12) map to `0xff`** — no dedicated slot. The twin table at `+0xa0`
  is all `0xff`. There is no colour or curve equivalent.
- The colour-matrix slot is selected on the **DSP**, not in ARM: the literal `0x300af` appears
  only in av-cam's data pool, not in slot-selection code.
- The colour block `0x00030001` physically holds **10 working matrices (slots 0..9), not 17**:
  slots 6/7 are byte-identical to Standard, 8/9 are one muted matrix. There are **no 7 distinct
  matrices** behind the hidden styles.
- Per-style slider defaults (`0x0107...`) are all zero except Portrait (+1/-1/-1).

**Conclusion:** the hidden styles are not seven ready-made parameter sets that were merely hidden
from the menu — the 3N firmware has no distinct colour/tone data for them. The most likely result
of forcing a hidden style past the menu is a render ≈ Standard (its default) — hypothesis,
consistent with the `0xff` table and the duplicate matrices.

Confirmed-from-firmware: only the 6 visible styles (slots 0..5; measured curves
Vivid/Landscape/Sunset = k14, Portrait = k1, Standard/B&W = identity).

## Renders

`code/sim/render_hidden.py` renders all 13 styles on clean Standard frames.
- 6 visible styles use real parameters.
- 7 hidden styles are tagged `(guess)`: Standard matrix + simulator knobs (chroma / curve / hue)
  set from Sony's published style descriptions. **These are approximations, not 3N parameters.**

Output (JPEGs, git-ignored): `OUT_DIR/hidden_styles_<frame>.jpg`. Env: `NEX3N_FRAMES_DIR`,
`OUT_DIR`, plus the simulator's own vars (see `simulator.md`).

Takeaway for the project: unlike colour and tone (which are real, Backup-settable data), the
hidden styles have no underlying data to expose — approximating them as colour looks in the 6
available slots is the only route to those moods.
