# Film-stock presets: colour + ISO-matched grain in one menu pick (plan)

> **⚠️ Grain blocker (07.10.2026):** the ARM grain hook this plan relies on does NOT reach
> the SOOC JPEG (DSP owns the YC buffer, handle-addressed). Reliable grain needs DSP-side
> injection into `idt_cam` VLIW `0xe800..0x13000` — see `dsp-grain-campaign.md`. The colour
> half of this plan (per-slot/per-effect matrices, menu renames) is unaffected.

Goal: the Creative Style menu becomes a list of film stocks. Picking one gives that
stock's colour AND its characteristic grain in a single SOOC JPEG, with the menu entries
renamed to the film names. This ties together the colour work (`style-and-effect.md`),
the grain hook (`grain-hook.md`) and the menu-string edit (`live-memory-and-delivery.md`).

## Why this works

The develop colour stage always reads the slot from the global `[0xc3bad724]`, and the
menu's Creative Style selection sets it (`style-and-effect.md`) — independent of any
Picture Effect. So the selected Creative Style already identifies "which film". If the
grain code reads the same `[0xc3bad724]` and applies a per-slot amount, one selection
drives both colour and grain. No Picture Effect needed, so the Style/Effect menu conflict
is sidestepped entirely.

Requirements:
1. **Per-slot colour matrix** — one film matrix per Creative Style slot in Backup
   `0x00030001` (+ mirror `0x00030008`). Already a solved operation; some stocks already
   have matrices (House → Portrait slot, Phoenix II → Sunset slot, see
   `house-phoenix-looks.md`); the rest need designing.
2. **Always-run grain keyed on the slot** — a grain hook that fires on every capture
   (not gated by a Picture Effect), reads `[0xc3bad724]`, and looks up a per-slot
   amplitude/character. (Soft Focus only runs when that effect is picked, which is
   incompatible with picking a Creative Style — so the grain hook must move to an
   always-run point. See "Open blocker".)
3. **Renamed menu entries** — the 6 visible Creative Style names in `string_*.uxc` on p8,
   edited the same way as "Soft Focus"→"Film Grain" (same-length in-place, LZPT p8 flash).

## Proposed presets (6 visible slots)

| slot (stock) | ISO | colour | grain character |
|---|---|---|---|
| Velvia | 100 | slide, saturated, contrasty, cool | very fine, tight (~±6–8) |
| Phoenix | 200 | warm, red-shifted, punchy | fine (~±10) |
| UltraMax | 400 | warm consumer neg | moderate (~±14) |
| House / Portra | 800 | neutral-warm, soft | visible (~±18–20) |
| Superia/Natura 1600 | 1600 | greenish, heavy | coarse (~±26, clumpier) |
| CineStill 800T | 800 (T) | tungsten/teal, **halation** | moderate (~±16) + red highlight bleed |

Grain amount scales with box-speed ISO (classic granularity-vs-speed). Slot → amplitude is
a tiny table in the grain routine. A "clean/off" slot (grain 0) can be kept too.

## Open blocker (the one real piece of RE left)

The always-run grain must write the buffer the encoder reads **when no Picture Effect is
active**. The current grain hook works via Soft Focus because `session[0x5e4]` is the
encode-input only when that stage runs; with no effect the encode-input is a different
buffer (develop output). Finding that buffer is in progress (the `p3_multibuf` probe
grains several candidate YC buffers with the effect skipped to see which reaches the
JPEG). Once pinned, the always-run hook grains it and reads `[0xc3bad724]` for the amount.

Hook options for "always run post-develop": the develop-complete step, or the JPEG encode
entry (localized to the `0xc35dcxxx` subsystem via `tsk46_jpeg`, see `grain-hook.md`).

## Advanced (later)

- **Halation (CineStill)**: bleed red/orange into the neighbourhood of clipped highlights
  — a spatial op (low-pass the red component around bright pixels) in the grain wrapper.
  Heavier than grain; attempt after the base presets work.
- **More than 6 stocks**: the hidden Creative Styles (IDs 6–12) are code-gated off by an
  unconditional loop in `viewUnified2.so` (`hidden-styles.md`); unlocking them (a menu-lib
  patch on the p3 rootfs) would free up to 13 slots = 13 stocks. Separate, riskier patch.

## Two-menu model (preferred): Styles = clean colour, Effects = colour + grain

A cleaner split that the hardware supports: keep the Creative Style menu as **clean film
colours (no grain)** and make each Picture Effect a **film colour + grain** preset. Both
menus get renamed to film names.

How each effect gets its own matrix *without* painting pixels in the effect path: the
develop colour stage reads the slot from `[0xc3bad724]` *before* the effect stage runs, so
colour can't be changed from inside the (later) grain hook. Instead hook the **colour
builder** `colorprm_build_capmode` (`0xc3507b13`, read site `0xc3507b78`): if a Picture
Effect is active, set the slot to that effect's dedicated film slot; otherwise use
`[0xc3bad724]` as normal. This is Plan B-gated from `style-and-effect.md` generalised to a
per-effect slot table. One hook gives every effect its own colour (it keys on *which
effect is active*, not on a stage), so even effects we don't add grain to still get their
colour. Grain is added only on the effect stages we hook.

- **Styles** (6 Creative Style slots): clean colour, no grain (grain hook sees no active
  effect → does nothing).
- **Effects**: colour (via the colour-builder slot override) + grain (via the stage hook).
  - **Soft Focus** is the confirmed grain hook, and it has **Low / Mid / High** levels →
    three colour+grain presets under one entry (Phoenix 200 / UltraMax 400 / House 800),
    if the selected level is readable at the hook.
  - **Miniature** has its own stage (another grain+colour slot, e.g. Velvia 100).
  - Other effects (Toy/Pop/Posterization/…) are ISP blocks — colour override still works,
    grain is harder.

Needs, beyond the base plan: the **current-Picture-Effect global** (so the colour builder
knows which effect is active — Agent B's open tail, candidate near `0xc3abe32c`), the
**Soft Focus level** value (to split Low/Mid/High), a small **effect→slot** table, and the
menu-string renames for both Creative Style and Picture Effect entries. Grain on a given
effect still needs that effect's encode-input buffer (the always-run/encode-buffer item in
the base plan).

## Implementation RE status (verified against av-cam.bin)

**Native grain — there is none (confirmed).** No reusable grain/noise/dither generator
exists in av-cam or the `sa_*.bin` modules. The only "noise" is: the ADF **noise-reduction**
LUT (`[ADF]…NOISE TABLE…`, subtractive — the kknr/yknr NR modules consume it; cannot be run
in reverse), audio noise (AAC perceptual noise substitution, system sounds), and the H.264
SEI `film_grain_characteristics` validator in the AVC video encoder (a decoder-side hint for
video playback, never baked into pixels, not set on the 3N, not in the stills path). The
mono effects (Rich-tone Mono `Start_Richtone_Monochrome` `0xc34e6ffa`, HC Mono) have no
grain. A numeric sweep for PRNG/LCG/xorshift constants across av-cam and every SA module
found only the AAC LCG. → the synthetic xorshift grain (`grain-hook.md`) is the only option.

**Per-effect vs per-style selector.**
- Colour slot (Creative Style) = global `[0xc3bad724]`, read cleanly in capture
  (`colorprm_build_capmode` `0xc3507b78` and the 18 per-mode handlers `0xc37298xx`). So
  distinguishing presets by **style slot** is easy.
- The capture path only carries the **class** `ctx[0x23]` (0..4), not the full ~14-effect
  index — ~14 effects collapse to 5 classes before the stage. To bind a different film to
  each *effect*, the Picture-Effect param id is needed. Mechanism found: the camprm registry
  (`{flag,pid,setter}` x207 at `0xc3968d08..0xc39696bc`); colormode is pid `0x4039` → setter
  `camprm_set_colormode 0xc3461fdf` → writes `[0xc3abe32c+4]`; the camprm picture/colour
  block is **`0xc3abe32c`** (picture fields pids `0x403a..0x403e/0x404e/0x4051/0x4060/0x40ca`
  → `[+8..+0x1c]`). The exact picture-effect pid is **not pinnable statically** (the block is
  reached via a handle pointer in capture, not a literal) → confirm with a **live senser dump
  of `0xc3abe32c..0xc3abe370` while toggling Picture Effect in the menu**.

**Effect stage class map (for strip-and-replace).** case0 `0xc37deb92`, case1 `0xc37dfca2`,
case2 `0xc37ea898` (Stage_SoftFocus), case3 `0xc37df2c0` are **one family** — all open the
same YC canvas via `0xc366eb00(2, packed_geom)` and reach the encode-input buffer region, so
all four are hookable the same way as Soft Focus (wrap the dispatcher bl sites). case4
`0xc363faa0` is special/multi-frame (its own 0x21-way sub-dispatcher `0xc35f8db4`, no single
YC canvas, returns code 3) → not cleanly hookable. **Rule (do NOT wholesale-replace — that
breaks develop→effect→encode):** wrap = call the native stage (keep dataflow) → overwrite the
encode-input buffer with our colour+grain → return the native success code. The native effect
output is replaced because we overwrite the encode-input after it.

**Remaining to build the two-menu presets:**
1. live senser dump → pin the Picture-Effect param id/offset in `0xc3abe32c` (for per-effect
   colour+grain).
2. multibuf probe on case0/1/3 → confirm which YC buffer is encode-input without Soft Focus
   (the always-run buffer).
3. per-slot/per-effect film matrices (Backup), effect→film table, menu-string renames.
