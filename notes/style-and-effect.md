# Creative Style (colour) and Picture Effect together

On a Sony NEX the menu makes Creative Style and Picture Effect mutually exclusive:
selecting a Picture Effect greys out Creative Style. Since the film look rides on the
Creative Style colour matrices (Backup `0x00030001`) and the in-camera grain rides on a
Picture Effect (Soft Focus, see `grain-hook.md`), they appear to collide. This note is
the static RE of why, and how to have both. Addresses verified against `av-cam.bin`
(load base `0xc3441000`).

## Where the Creative Style colour matrix is applied

av-cam does **not** multiply the matrix — the develop colour stage (the SA/DSP YC engine,
VLIW, not statically decoded) does. av-cam only assembles a colour descriptor `T` and
hands it to that stage. In `T`: `T[0]` = RAM base of the colour block
(`0xc3ac2b94` bank 0 / `0xc3ac4894` mirror, bank chosen by the flag at
`[0xc3cab360+3]`); `T[6]` = the **slot/colour-mode byte** the stage uses to index
`base + 0x48 + 18*slot` (per-slot 3x3 matrix, as in the README).

Exactly four functions build the descriptor (the only literal refs to the block base):

| function | VA | path |
|---|---|---|
| `colorprm_build_capmode` | `0xc3507b13` | capture / SOOC JPEG (18 per-mode handlers `0xc37298xx`) |
| `colorprm_build_extract` | `0xc3508453` | capture (ExtractCaptureData) |
| `colorprm_build_A` | `0xc35070c7` | monitor / LiveView |
| `colorprm_build_B` | `0xc3507431` | monitor |

All four read the slot from **one global**, `ldrb rX,[0xc3bad724]` → `strb rX,[T,#6]`.
Read sites: capture `0xc3507b78` (bytes `00 7a`), extract `0xc35084a8`, monitor
`0xc3507128` (`12 7a`) and `0xc35074ac`. So the active slot is the byte at
**`0xc3bad724`**, fed from the menu colour-mode param `0x4039`
(`camprm_set_colormode` `0xc3461fdf`; `menu_style_to_colormode` `0xc36ded1b` = menu−1).

## Why the effect "disables" the style

There is **no Style/Effect fork inside av-cam** — they are orthogonal. The colour stage
always runs with slot `[0xc3bad724]`, regardless of Picture Effect. Picture Effect is a
separate capture stage: the sequencer dispatcher (record 1, `0xc362827e`) reads
`sel = ctx[0x23]` and jump-tables into one of five capture-pipeline classes
(case2 `0xc37ea898` = `Stage_SoftFocus` = the grain hook). `ctx[0x23]` is a pipeline
class (0..4), not a colour selection.

The mutual exclusion is imposed **above av-cam, in the userland menu**
(`viewUnified*.so` / libObj): choosing a Picture Effect greys out Creative Style and
sends colour-mode = Standard via `0x4039`. So with grain (Soft Focus) active the colour
stage still runs, just with the **Standard slot** — the Portrait/Landscape/Sunset
matrices simply aren't selected. The tone curve k0 (global, in p3) stays either way.
(One link not resolvable statically: whether the menu forces Standard *with its matrix*
or a neutral/off — one chart shot with Soft Focus settles it.)

## How to get colour + grain together

Shoot a chart with Picture Effect = Soft Focus first to see which slot the menu forces
(expected Standard = slot 0) and whether its matrix applies. Then:

- **Plan C — recommended, zero av-cam edits.** Write the film colour matrix into the slot
  the menu forces (Standard, via Backup `0x00030001` + mirror `0x00030008`, already a
  solved operation). Colour from Standard then applies under grain; tone = k0; grain = the
  existing hook. Cost: Standard becomes the film look for all shots (fine for this
  project); other styles still switch for non-film shooting. No firmware change, no risk.
- **Plan B — 2 bytes per site, if colour is actually nulled.** Force the slot: replace
  `ldrb rX,[rX,#8]` with `movs rX,#<slot>` at the builders — capture `0xc3507b78`
  (`<slot> 20`) and extract `0xc35084a8` (`<slot> 24`) are required; monitor `0xc3507128`
  (`<slot> 22`) and `0xc35074ac` (`<slot> 21`) for LiveView. Same-size Thumb-1 immediate,
  no cave. Delivered by the same LZPT p3 flash. Cost: the slot is forced for every shot
  (in-camera style switching stops).
- **Plan B-gated — force the slot only when Soft Focus is active** (keeps style switching):
  detour the capture builder (`0xc3507b78`) to a cave stub that sets `r0 = <slot>` iff the
  current Picture Effect is Soft Focus else `r0 = [0xc3bad724]`. Needs the global holding
  the current effect (candidate near `0xc3abe32c`; not yet pinned).
- Rejected: patching the menu (`viewUnified*.so`, different partition, UI risk); applying
  the 3x3 matrix per-pixel in the grain wrapper (heavy and redundant — the colour stage
  already runs).

Open tail: the exact writer of `[0xc3bad724]` (it comes through param pointer tables
`0xc381a6a4`/`0xc381aa54`, a registry copy, not a direct `str`), and the current-effect
global for the gated plan.
