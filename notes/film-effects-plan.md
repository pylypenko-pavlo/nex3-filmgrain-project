# NEX-3N: "film" effects via Backup properties (static design)

Static design; the camera was not connected and nothing was written when this plan was made. All changes go only through Backup property writes in subsystem `0x0003` (same path as `0x00030001/08`, `0x00030106`). Based on `notes/backup-params.md` and `notes/sa-interface.md`.

Tags: **[bytes]** = verified against a Backup snapshot; **[code]** = from the av-cam disassembly; **[hypothesis]** = unverified, the first experimental frame should settle it.

Data: `data/fx/changes.json` is the full log of every change as `[step, property id, offset, old bytes, new bytes]`. The generator script built each modified property from the snapshot and asserted the old bytes before patching. Each modified property is a **complete** new value (256 B; 1536 B for `00030001`); the property blobs themselves are not included. Two screen targets were used: a glow chart (white shapes on black at several grey levels) and a white field.

## 0. Summary

| goal | lever | step | confidence |
|---|---|---|---|
| Grain at ISO 800-3200 (weaker luma NR, chroma NR kept) | NR-1 `0x30010/0x300b4 +0x0C` -> NR-2 `0x3001b/0x300be +0xD7` -> NR-3 `0x3004a +0xD2/D6/DA`; NR-4 (hi_gain) is a spare "dose control" instead of NR-1 | Session 1, W1-W3 (+W3b) | [code], image effect unverified |
| Soft sharpening without halos | SH-1 apgain `B0->60` (-45 %), then SH-2 coring x3 | Session 1, W4-W5 | [code] |
| Pro-Mist / glow | **only the LOW-level bytes** `0x3010a +6..+8`. Kernels are shared by all three levels, so they are left alone | Session 2, W6 (probe, 3 variants in one write) -> W7 (final) | layout [code], byte meaning [hypothesis] |
| Gentle vignette | PE-1, Toy curve `0x30040 +0xA2..+0xE1` down to -0.62 EV | Session 2, W6 | [code] |

Key conclusions:
1. **Effects do not stack.** Soft Focus and Toy Camera are different entries of the same Picture Effect menu, so "glow + vignette" at once is impossible. Global NR and sharpening apply under all modes.
2. **A vignette separate from Toy is impossible within Backup.** The Toy curve is separable as data but only active in Toy mode. Toy colour is probably one of the matrix slots in `0x30001` (Backup: findable and rewritable). Toy tone is one of the k15..k19 curves in firmware, outside Backup and out of scope. So the best achievable with Backup writes alone is "Toy tone + own gentle vignette + (later) own colour".
3. **Picture Effect probably disables Creative Style** [hypothesis: so in manuals of sibling Sony models, unverified on 3N]. If so, Soft Focus is shot without the Portra/House film matrices. The first frame of Session 2 shows this (style menu greyed out?), and optional colour tags (W1) show which matrix slot the effect uses.
4. The Soft Focus kernels are decoded byte by byte (3.1): low-pass filters normalised to 256, no negative lobes. How the three level bytes blend blurred with original is not visible in ARM code: the DSP routine `sa_sftfcs` does it (see `notes/sony-dsp-isa.md`). So probe W6 is a **one-factor experiment: the three level slots = three variants in one write**, and both Pro-Mist candidates are in it.

## Restrictions (all respected)

- Not touched: `0x00030002`, all `0x00bc*` and `0x0132*`, calibrations with attribute 0x0a (`0x30036..38`, `0x30042/43`, `0x30051..54, 76..78, 86, 8f, a0, ae, 0102`, plus 0x48/0x68/0xe8/0x60), debug `0x00030056`, KKNR `0x30024`.
- In `0x0003010a` **only** `+0x00..+0x08` is edited. Not touched: `+0x09` (forced level), `+0x42..+0x47` and `+0x84..+0x8B` (read by SPICA), and the kernels (shared by three levels). The generator checks that SPICA zones are zero and unchanged.
- Dual banks are written identically: `0x30010<->0x300b4`, `0x3001b<->0x300be`, `0x3000c<->0x300b0`, `0x3000d<->0x300b1`, `0x3011f<->0x30120`, `0x30016<->0x300ba`, `0x30017<->0x300bb`, `0x30001<->0x30008`. Bank equality in the snapshot is verified [bytes]. `0x3004a`, `0x30049`, `0x30040`, `0x3010a` have no bank B.
- Values are read at startup, so a write needs a save plus reboot (leaving the updater) to take effect.
- Before the first write of each property, read it back and compare with the snapshot value. If different: stop, the plan was built from another state. For `0x30001/08` the current value is the v5 looks block.
- Charged battery only; long power-save timeout; kill the macOS `ptpcamerad` daemon before MTP access.

## 1. Noise reduction: order and bytes

What is known from code (`notes/backup-params.md` section 1):
- NR-1 removes the forced GHNR/GLNR sub-stages at all ISO <= 25600, assuming a normal frame is "mode 1" [hypothesis].
- NR-2 disables all G-NR only in range B (ISO > 1600).
- NR-3 closes the YKNR window (~ISO 200..6400). Whether YKNR suppresses luma or chroma is unknown.
- NR-4 changes `gnr_hi_gain_*`. By name, a parameter of the "high" G-NR sub-stage, i.e. the same GHNR that NR-1 disables [hypothesis]. So **NR-4 is not the step after NR-1 but its dosed alternative**: with NR-1 on, NR-4 likely changes nothing.

**Order (cumulative ladder, each step compared with the previous within the same session):**
1. **NR-1** first: most targeted, works at 800, 1600 and 3200, leaves chroma `cnr_on` alone.
2. **NR-2** only if 3200 still lacks grain. ISO 1600 is a built-in control: must not change.
3. **NR-3** last because YKNR's meaning is unknown. Main criterion is chroma sigma: if YKNR is chroma NR, revert (chroma NR must be kept).
4. **NR-4**: branch for "NR-1 too coarse or no effect": revert NR-1 and tune hi_gain (direction probe first).

### Bytes (old values verified against snapshot)

| step | Backup ID | offset | old -> new |
|---|---|---|---|
| NR-1 | `00030010`, `000300b4` | `+0x0C` | `01` -> `00` |
| NR-2 | `0003001b`, `000300be` | `+0xD7` (gnr_on, range B) | `01` -> `00` |
| NR-3 | `0003004a` | `+0xD2` / `+0xD6` / `+0xDA` | `00 0B` / `FF 0A` / `00 0B` -> `00 00` x3 |
| NR-4 probe | 8 hi_gain tables, ISO 3200 node (index 6) | L0 `3011f/30120 +0xD2, +0xE8`; L1 `30049 +0xBC`; L2 `30016/300ba +0xE4`, `30017/300bb +0x30`; L3 `30049 +0xD2`, `3004a +0x0C` | `0A`/`0B`/`08` -> `10` (u16 `10 00`) |
| NR-4 final | same 8 tables, nodes ISO 6400..800 (indices 5-8) | see `data/fx/changes.json` | -> `10` |

ISO axis (hypothesis, 0x600 = ISO 200): index 0 = ISO 204800 ... 5 = 6400, 6 = 3200, 7 = 1600, 8 = 800, 9 = 400, 10 = 200.

## 2. Sharpening

- **SH-1:** `0003000c` and `000300b0`, `+0x1C..+0x31`: 11 x `B0 00` -> 11 x `60 00` (176 -> 96, -45 %). The analysis suggested `40` (-64 %); the milder value is chosen because "film" sharpness means less halo, not mush. If overshoot drops by less than 30 %, next step is `40`.
- **SH-2:** coring x3 in both stages and both banks: `0003000c/000300b0 +0xCE..+0xE3` and `0003000d/000300b1 +0x5E..+0x73`. By ISO from high to low: `04 04 04 04 05 05 06 07 08 0A 0A` -> `0C 0C 0C 0C 0F 0F 12 15 18 1E 1E`.
  Observation [bytes]: stock coring is **lower** at high ISO than at low ISO (6 at 3200 vs 10 at 200). That makes sense only while NR eats the noise. With weaker NR, fine grain gets amplified by sharpening and turns "crunchy". So SH-2 belongs **after** the NR steps.
- SH-3 (Apacon `0x30106`) is not planned: in an earlier experiment it shifted Sunset saturation.

## 3. Soft Focus -> "Pro-Mist / glow"

### 3.1 Verified

- **[code] `0x465cf8`:** level comes from `ImageParam+0x6C`. 0 -> bytes `+6,+7,+8`; 2 -> `+0,+1,+2`; 1 or anything else -> `+3,+4,+5`. Bytes are stored **as is** (`ldrb` -> `str`, no scaling) into the DSP param block at `+0x28`, `+0x2C`, `+0x34`. ARM does not write field `+0x30`. Kernels are copied with fixed lengths: `+0x10` and `+0x30` 0x12 B each (9 x u16), `+0x50` and `+0x90` 0x32 B each (25 x u16). SPICA zones are not part of the copy.
- **[code]** The HAPI (preview) path reads the same bytes. The log contains job `job_YC_CaptureDevelopResizeSftfcs`, i.e. Soft Focus is preceded by "develop + **resize**". Hypothesis: blur runs on a downscaled copy.
- **[bytes] Kernels:** all four are u16 LE, all taps positive (signedness indistinguishable from the data; no negative lobes, so a pure low-pass), **each sums to exactly 256**: Q8 normalisation, DC gain 1.0. The effect itself cannot brighten the image, only redistribute light.

| kernel | offset | form | sigma x / y, px of working grid | 1D MTF at 0.1 / 0.25 / 0.5 cyc/px |
|---|---|---|---|---|
| K1 3x3 | `+0x10` | near box `28 28 28 / 29 30 29 / 28 28 28` | 0.82 / 0.81 | 0.87 / 0.34 / -0.33 |
| K2 3x3 | `+0x30` | `9 65 9 / 10 70 10 / 9 65 9` | **0.47** / 0.81 | x: 0.96 / 0.78 / 0.56 |
| K3 5x5 | `+0x50` | near box, 10..12 | 1.40 / 1.40 | 0.65 / -0.18 / 0.20 |
| K4 5x5 | `+0x90` | outer columns zero | **0.80** / 1.39 | x: 0.88 / 0.37 / -0.27 |

  **[hypothesis, strong]:** K1/K3 act on Y, K2/K4 on chroma in 4:2:2. Horizontal sigma of K2 and K4 is ~0.57 of K1 and K3, vertical is the same, exactly what horizontally halved chroma implies. So there are only two "radii": small (sigma 0.8) and large (sigma 1.4 px of the working grid).
- **Level bytes [bytes]:** L0 `06 16 10`, L1 `0E 18 08`, L2 `16 1A 00`. Patterns: b0 rises 6 -> 14 -> 22; b1 rises 22 -> 24 -> 26; b2 falls 16 -> 8 -> 0; **b0 + b2 = 22 at all three levels**.

### 3.2 Blending hypotheses (none verified)

- **H-A:** b0 is the blur mix strength, alpha ~ b0/32 (0.19 / 0.44 / 0.69). Out = (1-alpha)*orig + alpha*blurred.
- **H-B:** b0 and b2 weight the large and small kernels (constant sum): as level rises, weight moves from small to large radius while total blur share (22/32 ~ 0.69?) stays the same.
- **H-T:** b2 is a luminance threshold above which things "glow" (0 on High, so everything glows). Under H-T, "glow mostly in highlights" is reachable with b2 > 16.
- **b1** (22..26): radius, iteration count or glow gain, unknown.

Distinguishing them with the stock baseline frames B0 (L/M/H):
- H-A: fine detail loss grows with level: 0.81 / 0.56 / 0.31 of original.
- H-B: fine detail loss nearly equal at all levels, glow width grows.
- H-T: on the glow chart, glow around dark squares vanishes earlier than around bright ones, most visibly on Low.

### 3.3 Size prediction

For K1/K3 the effective sigma in the full frame (4912 px wide) = sigma_work x s x sqrt(N), where s is the copy downscale and N the number of passes (both unknown).

| s \ N | 1 | 22 (if b1 = pass count) |
|---|---|---|
| 1 (full res) | 0.8-1.4 px | 3.8-6.6 px |
| 2 | 1.6-2.8 | 7.6-13 |
| 4 | 3.2-5.6 | 15-26 |
| 8 | 6.5-11 | 30-53 |

- With s = 1 and N = 1 there is no "glow", only slight softness (3 sigma <= 4 px). Stock Sony Soft Focus does not look like that, so expect s >= 4 and/or N > 1 [hypothesis]. Baseline B0 gives sigma from the edge profile of the white rectangle (ESF -> LSF); that calibrates the table.
- **MTF estimate for grain and fine detail** (>= 0.25 cyc/px of full frame, where H ~ 0 for sigma >= 2 px): MTF ~ 1 - alpha. Noise sigma ratio on a flat patch "SF / no SF" ~ 1 - alpha: the simplest way to measure alpha, no special target needed.
- **Glow in numbers:** blending is probably in gamma-encoded YCbCr (after develop). Then just outside a white (255) edge on black the lift is ~ alpha*255/2, decaying as a Gaussian of sigma. For alpha = 0.094 that is ~12 codes (about L* +4..5 on black). The light source itself dims by the same amount.

### 3.4 Probe W6 = three one-factor variants in one write

Each slot differs from **stock Low** by one byte. All new values lie within the stock range (b0 minimum lowered from 6 to 3; zero only in b2, where High already has it), reducing the risk of the DSP seeing unfamiliar values.

| slot (menu item if L0 = Low) | offset | old -> new | tests | also candidate |
|---|---|---|---|---|
| L0 (Low) | `+0x06..+0x08` | `06 16 10` -> **`03 16 10`** | b0 = strength? | **Pro-Mist A** (if H-A: alpha ~ 0.09) |
| L1 (Mid) | `+0x03..+0x05` | `0E 18 08` -> `06 1A 10` | b1 with rest as Low | - |
| L2 (High) | `+0x00..+0x02` | `16 1A 00` -> **`06 16 00`** | b2 with rest as Low (small kernel weight or threshold) | **Pro-Mist B** (if H-B: large radius only, share 6/32) |

Final W7: Pro-Mist A or B (Low replaced, Mid/High stock; verified the only difference is `+0x06..+0x08`). All variants are listed in `data/fx/changes.json`.

Reading the result (B1 vs B0, stock Low as anchor):
- **L0 probe:** alpha roughly halved, glow sigma unchanged -> H-A confirmed, Pro-Mist = A (b0 = 2..4 to taste). Almost no change -> b0 is not strength, look at L2.
- **L2 probe:** glow wider, detail loss smaller -> H-B, Pro-Mist = B. Glow appears around dark squares that did not glow on stock Low -> H-T. Then "glow only in highlights" = **b2 above 16** (e.g. `03 16 18`). That extrapolates beyond stock, so separate write and separate check.
- **L1 probe:** wider glow -> b1 = radius/passes (the "halation" knob); brighter without widening -> b1 = gain.

Pass criterion for Pro-Mist: noise sigma ratio at ISO 1600 SF/off = 0.88..0.95 (grain mostly intact); glow at a white edge visible (black lift >= 5 codes at 1 sigma); mean lightness of grey patches shifted by no more than +-2 L*. Fail: detail loss above 15 %, or no glow at all.

## 4. Vignette: PE-1

- `00030040 +0xA2..+0xE1` (32 x u16): linear stock `2000 1F17 ... 04C0 03D7` (edge x0.12 ~ -3.1 EV) -> quadratic `2000 1FFD 1FF4 ... 1633 1583 14CD`, where g_i = 1 - 0.35*(i/31)^2 and edge x0.65 = **-0.62 EV**.
- The last node `+0xE0` also acts as a "floor" in one code branch. So corners will not go darker than x0.65 even if node 31 corresponds to the short-side edge rather than the corner.
- Prediction with node proportional to r: mid-radius x0.91 (-0.13 EV), corner x0.65. In the output JPEG the falloff will be **stronger** because the Toy S-curve (firmware, not edited) sits on top.
- Separability: see 0, point 2: only as data; the mode always brings Toy tone with it.

## 5. Sessions

A session is one sitting under constant light. Within it, steps are: write -> save -> reboot -> frames. The baseline for each step is the previous step's frames in the same session. Frames from different sessions are not compared (Standard day-to-day dE 10.5).

**Common settings:** tripod, M, f/5.6, WB Daylight 0, Standard 0/0/0, DRO and Auto HDR off, Long Exp NR off, High ISO NR = Normal (except where noted), JPEG Fine 16M, Picture Effect Off (except 5.2). Target displayed full screen, True Tone/Night Shift off, fixed screen brightness. Shutter recomputed with ISO for equal exposure.

**Measurements:**
- sigma L* and sigma C = sqrt(sigma a*^2 + sigma b*^2) in the central 25 % of grey patches n8/n6.5/n5/n3.5. `code/measure/measure.py` grid needs a `.std()` added; it currently returns means only.
- Black/white edge profile: overshoot % = (max - plateau)/(white - black) and 10-90 % width in px.

### 5.1 Session 1: global NR and sharpening (5 writes + options)

**Frame set F** per step:
- F1-F4: chart **slightly defocused** so the screen pixel grid disappears and patches stay flat; ISO 200, 800, 1600, 3200.
- F5-F6: chart in focus on an edge and text; ISO 200 and 1600.
- F7: the same live scene (dark interior with a lamp) at ISO 3200.

| step | write | shoot | expectation | pass / fail | revert |
|---|---|---|---|---|---|
| A0 | none (read back, compare with original) | F + free references: F4 with High ISO NR = Low; F5 with Sharpness -3 | - | - | - |
| A1 | NR-1 on both banks. Optionally colour tags in `00030001/08` in the same write | F; with tags also Toy Normal and Soft Focus Low on the colour chart, ISO 200, in focus | sigma L* at 800-3200 x1.3 or more, sigma C unchanged | sigma L*(1600, 3200) >= x1.25 and sigma C <= x1.15 -> keep. < x1.1 -> "no effect", revert and take NR-4 branch (A3b). > x2.5 or colour blotches -> revert, NR-4 branch | original |
| A2 | NR-2 on both banks; if tags were used, restore v5 looks in `00030001/08` | F | only 3200 moves | 3200 >= x1.2 vs A1, **1600 within 0.9-1.1** (control), sigma C <= x1.15. If 1600 moved -> ISO-axis hypothesis wrong (record), judge by image | original |
| A3 | NR-3 | F | - | sigma L* >= x1.15 with sigma C <= x1.15 -> keep. sigma C grows -> YKNR is chroma, revert | original |
| A3b (branch) | only if NR-1 reverted: NR-4 probe (12 properties; for `3004a` with or without NR-3) | F1-F4 | 3200 node changes, 1600 is control | sigma L* at 3200 up -> "0x10 = bypass" correct, write NR-4 final (nodes 6400..800). Down -> inverted scale, next probe `04`. Unchanged -> hi_gain is irrelevant to this frame | original |
| A4 | SH-1 | F | edge overshoot drops | overshoot >= -30 % with 10-90 % width <= +30 % -> keep. Otherwise try `40` or revert | original |
| A5 | SH-2 (on top of SH-1, or alone if SH-1 reverted), both stages, both banks | F | less "salt" in patches, large edge as before | overshoot within +-10 % of A4, sigma L* at 1600/3200 lower by 5-20 %, grain visually finer -> keep. Texture gone (sigma -30 % or more) -> revert | original |

Session 1 result = set of kept steps; together they are the "global film processing". If the free High ISO NR = Low in A0 gives the same sigma L* as NR-1, the NR-1 write is unnecessary.

### 5.2 Session 2: effects (2 writes)

Global state = Session 1 result, unchanged, so the baseline is shot again.

| step | write | shoot | pass / fail |
|---|---|---|---|
| B0 | none | Soft Focus L/M/H and Off: glow chart at ISO 400; defocused chart at ISO 1600 (sigma -> alpha); live scene with a light source. Toy Normal and Off: white field at ISO 200, lens stopped down 1 stop. Record whether Creative Style is available with the effect on | Calibration 3.2-3.3: alpha and sigma of stock levels, confirm L0 = Low. The stock linear Toy curve shows how node maps to radius: EV loss linear in r -> node proportional to r |
| B1 | SF probe + PE-1 (different modes, no interference) | same SF L/M/H and Toy frames | SF per table 3.4. PE-1: corner/centre ratio (sRGB -> linear, divided by Off frame) 0.55-0.75, no rings or steps -> keep. Otherwise revert `00030040` |
| B2 | Pro-Mist A or B (or new `03 16 18` under H-T) | SF L/M/H on glow chart + live scene | Low = chosen Pro-Mist; **Mid and High must match B0**: built-in check that stock is back |

Revert of all effects: original `0003010a` and `00030040`.

Total: **2 sessions, 7 writes** (plus branch A3b and maybe one Soft Focus refinement write). Session 2 can follow Session 1 directly; B0 frames are still mandatory.

## 6. Verified vs not

**Verified (bytes/code):**
- All old bytes (asserted by the generator) and bank equality.
- Level -> bytes -> DSP fields mapping for Soft Focus.
- Kernel copy lengths and no overlap with SPICA zones.
- Kernel normalisation (sum 256) and their sigma/MTF.
- Stock Toy curve (-3.06 EV).

**Hypotheses closed by the first frames:**
- Meaning of b0/b1/b2; copy downscale and pass count in Soft Focus.
- Low = L0.
- Whether Picture Effect disables Creative Style, and which matrix slot Toy and Soft Focus use (tags in A1).
- "Mode 1" for NR-1; the ISO axis; hi_gain direction; luma vs chroma YKNR.
- Node <-> radius mapping of the Toy curve.

**Out of scope:** Toy tone (firmware curve), style renaming (firmware), true grain synthesis.

## Addendum: DSP constraints for Soft Focus (from `notes/sony-dsp-isa.md` section 15, disassembly per ma1co's spec)

- Each of the four kernels in `0x0003010a` (+0x10, +0x30 3x3; +0x50, +0x90 5x5) must sum to **exactly 256**, otherwise the DSP returns `0xeeee0008/09`.
- Each of the three level bytes must be **<= 64**, and their sum **<= 64**, otherwise `0xeeee0004`.
- Pass order: the 3x3 pair once, then the 5x5 pair twice (per ma1co; the earlier conclusion was the reverse).
- Script-checked: SF probe, Pro-Mist A, Pro-Mist B and the original all pass (kernel sums 256, levels <= 64).

## Real grain in-camera: angles (2026-10-06)

Goal restated: a film look with colour + tone + **real grain** + "simulations", ideally as in-camera *selectable effects*. Findings from static analysis of av-cam and the settings store.

### Grain source A - native sensor noise (the realistic path)
The only real, in-camera grain that does not need new DSP code is the sensor's own photon/read noise, which is genuine analog grain. The image pipeline removes it with several NR stages; preserving it gives grain:
- **YC::NR (G-NR)** and **YKNR** are the luma-noise stages; **cnr/KKNR** are chroma. They are gated by the runtime "High ISO NR" level (`CommonRam+0x15C`, 0..3) and by per-ISO windows in the settings store (`0x0003001b`, `0x0003004a`, etc.; see `notes/backup-params.md`). **NR level 0 disables YKNR.**
- Film-like recipe: shoot higher ISO, drop luma NR (level/windows) but **keep chroma NR on** so grain is monochromatic like film, and add a touch of sharpening/soft blur to give it structure. Grain scales with ISO - authentic (choosing ISO ~= choosing film speed). Base-ISO frames are genuinely clean, so base-ISO grain is not available this way.
- This is selectable in-camera (the High ISO NR menu item + the Creative Style for colour) and composes with any colour look. Settings-store tuning only; no firmware write.

### Grain source B - the firmware's own grain generator (exists, but limited)
- `PICTURE_EFFECT_ROUGH_MONOCHROME` is present in `libObj` and av-cam, driven by the generic **`ART_EFFECT`** filter (`Camera::HAPI::Start_Art_Effect`). Rough Monochrome is Sony's grainy-B&W effect, so the hardware/firmware *can* synthesise grain - but (1) it is monochrome, and (2) on the NEX-3N it is almost certainly not wired into the menu (same situation as Watercolor/Illustration, `notes/hidden-styles.md`), so exposing it would need a menu-code change. Its grain path (inside the ART_EFFECT DSP module) is not parameter-exposed for colour use.
- Per-effect NR profiles exist: the NR code branches on `picture_effect`, and for `picture_effect == 9` it forces the G-NR high-frequency gains to pass-through (`hi_gain = 0x10 = 1.0`), i.e. that effect preserves HF detail/noise. So "grain" is partly already an effect-dependent behaviour.
- The HEVC `film_grain_characteristics` SEI exists in the video codec only (grain synthesis for video decode) - not usable for stills.

### Picture-effect enumeration (from libObj, code order)
`TOY_CAMERA, POSTERIZATION, PART_COLOR, ROUGH_MONOCHROME, SOFT_FOCUS, HDR_ART, MINIATURE, WATERCOLOR, ILLUSTRATION, TOY_CAMERA_SHADING, ... RICHTONE_MONOCHROME, RETRO_PHOTO, POP_COLOR, SOFT_HIGH_KEY`. (String order; the numeric menu IDs are filtered separately in `viewUnified`, as for Creative Styles.)

### Composition for "film simulations as effects"
- Colour: the 6 Creative Style slots (Backup matrices/hue, the v6 looks) - already selectable.
- Tone: global film curve via the settings debug path (mode 2).
- Grain: High ISO NR off + chroma NR on, higher ISO (source A).
- Halation/glow: the Soft Focus picture effect tuned (`0x0003010a`) to a subtle highlight bloom.
All four are in-camera selections or settings-store tuning; none needs a firmware-partition write or decoding the VLIW.

### ART_EFFECT filter parameters - can the grain be applied to colour? (No)
Analysed the ART_EFFECT interface to see if Rough Monochrome's grain could be reused on a colour image.
- The art filters are driven by a generic pair **`PARAMID_ARTFILTER_FILTER_ID` + `PARAMID_ARTFILTER_FILTER_LEVEL`** (which effect, one level). Each effect also has its own data level: `PARAMID_DATA_ROUGH_MONOCHROME_LEVEL`, `TOY_CAMERA_LEVEL`, `POSTERIZATION_LEVEL`, etc. For Rough Monochrome the **only** tunable is its LEVEL (grain strength). There is **no colour/mono flag and no separate grain output**.
- So grain and the monochrome conversion are fused inside the Rough-Monochrome filter id, produced together by the module's VLIW program. Separating them (grain on colour) would require editing that VLIW code - the op3 wall (sections 16-22). **Verdict: the built-in grain generator cannot be applied to colour via parameters.**
- Invoking it at all: Rough Monochrome is not in the 3N menu (the effect list is built by a UI converter in `viewUnified2`, as for Creative Styles); no writable property / PTP path to set the picture effect outside the menu was found, so reaching it would need a menu-code change (firmware write). Even then it is B&W only.
- Grain strength *is* a parameter (LEVEL), so if the effect were ever reachable it would give an adjustable grainy **B&W** film look - a separate (monochrome) avenue, not colour grain.
- Conclusion: for colour film grain, the native-sensor-noise path (grain source A: higher ISO + luma NR off, chroma NR on) remains the only in-camera, no-flash route; the firmware grain generator is locked to B&W behind the same two walls.
