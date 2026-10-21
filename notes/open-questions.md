# NEX-3N: three open questions - a7 IV Creative Look, the stage after the tone LUT, Sunset warmth on AWB

Static analysis of files and already-captured frames only. Nothing written to the camera, no firmware emulation. Tags: **[verified]** = visible in bytes, code or a measurement; **[hypothesis]** = inference without verification. Addresses are file offsets in the 3N `av-cam` binary (VA = `0xc3441000` + offset). Related: notes/symbols-and-names.md, notes/tone-curve.md, notes/prior-art.md, README.md.

## 0. Summary
1. **a7 IV Creative Look: keys are public and the firmware unpacks with stock fwtool (PRs #52 + #53), but no matrices, hue tables or curves for the looks exist in plain form.** The a7 IV Backup only holds slider values. **FL and NT are all zero** (Sharpness 4, Range 3, Clarity 1), **IN has Fade = 3, SH has Fade = 6**, everything else zero. So the whole character of FL/IN/SH/NT is produced by IQ-processor code (`cpapp-b.bin`, module `PQD_Gamma`), not by a table. **The format does not resemble our block `0x00030001`**: no 3x3 int16 matrices or int8 tables in the a7 IV Backup. Ready-made FL/IN/SH numbers cannot be taken from Sony; only "Fade 3/6" as a hint.
2. **Highlight lift is neither a curve nor a stage that depends only on the LUT output** [verified arithmetically]. DSC09510's top step is 232.7/255, while the film k0 ceiling is 909/1023 = 226.6/255. No chain ending in that LUT can reach that high. For the same LUT output (~213), c0 gives 214.7 and c-3 gives 232. The stage sees something **besides** the LUT output. Measured behaviour: above Y' ~ 200 (input ~ 511 of 2047) a frame with a darkening curve **does not drop below "base without curve" minus 3...8 Y'**. Curve weight falls from ~1 to ~0.2. No Backup control found. (A makernote candidate was later ruled out, see 2.3.) **For a film shoulder: a tone LUT cannot pull highlights more than ~5 Y' below standard.**
3. **Sunset warmth on AWB is a per-channel linear multiplier before the tone curve** [verified by RAW+JPEG measurement]: R x1.40...1.44, G x1.06...1.09, B x0.60...0.64 relative to Standard, constant across 15 grey-scale steps. It is **not** in makernote `WB_RGBLevels`: Sunset and Standard have identical 657-667/256/430-435. So the shift is applied after the "AWB coefficients" are recorded, in the colour module `[CAMERA_MAIN_CC]` (it has its own style index, Sunset = 9, Autumnleaves = 11) [verified: index and name table]. **Backup ID and code location of the multiplier not found.** A practical substitute exists in the menu: AWB A-B shift (tag `WBShiftAB_GM`), but it is global, not per style.

## 1. a7 IV (ILCE-7M4) Creative Look

**Keys** [verified]. CXD90057 keys are in plain text in fwtool PR #52 (`fwtool/sony/constants.py`: `key_cxd90057_k0`, `key_cxd90057_k8`; two `AesCbcCrypter`s in `fdat.py`; model `0x01030081`). PR #53 adds LZX CAB. No own decryption code was written and no keys were derived.

**Firmware**: Ver. 6.02 (memory-card update file), unpacked with a scratch fwtool branch combining PR #52 + PR #53. Only `nflasha5` is not unpacked: it is WBI2, fwtool only knows WBI1.

**Where the looks live** [verified]:
- a7 IV Backup: `0110_backup/SYSIPSX-DSLR/{LS,LS_GLEE}/*.bin`, BK4 format, readable with our Backup dumper. All 32 regional files are identical.
- `BKID_APP_*` names come from a table in `lib/appFw.so` (0x5798a90, 7907 entries). ID = `0x02CF0000 | index`, e.g. `CREATIVE_LOOK_OPTION_CONTRAST<n>` = `0x02cf0d18 + 2n`.
- Slots 0-9 are presets. Order from the appFw enum: STANDARD, PORTRAIT, NEUTRAL, VIVID, BRILLIANT (VV2), FILM (FL), RETRO (IN), AIRY (SH), BLACK_WHITE, SEPIA. Plus unused FILM2/FILM3. Mapping to menu items inferred from order [hypothesis, reliable].

| Look | Contrast | Highlights | Shadows | Fade | Saturation | Sharpness | Sharp. Range | Clarity |
|---|---|---|---|---|---|---|---|---|
| NT | 0 | 0 | 0 | 0 | 0 | 4 | 3 | 1 |
| FL | 0 | 0 | 0 | 0 | 0 | 4 | 3 | 1 |
| IN | 0 | 0 | 0 | **3** | 0 | 4 | 3 | 1 |
| SH | 0 | 0 | 0 | **6** | 0 | 4 | 3 | 1 |

For comparison: PT has Sharpness 3 and Clarity 0, VV2 has Clarity 8. Ranges match the Help Guide (Fade 0..9): the stored number is exactly the menu value.

**Matrices, hue tables, curves not found**:
- a search for 3x3 int16 (scales 256...65536) in Backup found only near-identity housekeeping matrices;
- our 3N Standard matrix `1292,-180,-88` and segment signature `2,2,3,4,4,4,4,3,3` do not occur in a7 IV firmware;
- strings show the structure: the app sends the IQ processor a look number `PID_SET_COLOR_MODE` (0x402F) and sliders as separate PIDs (CONTRAST 0x4030, SATURATION 0x4031, SHARPNESS 0x4032, HIGHLIGHT 0x40F3, SHADOW 0x40F4, FADE 0x40F5, CLARITY 0x40F7, RGB_MATRIX 0x40BF);
- gamma is built by `cpapp-b.bin` (ARM32), module `PQD_Gamma`: `GetMainGamma`, `ContrastGamma[Shadow/Highlight]`, `SabunGamma`, `MakeGammaPointDataTable`. This suggests curves are assembled from points by code rather than stored as ready LUTs [hypothesis].

**What it gives us.** The format does not resemble the NEX-3N `0x00030001`. Only the idea "style = number + sliders in Backup" is shared. The only transferable hint is **Fade**: IN 3/9, SH 6/9. That is a black lift; our k0 with black ~12/255 works the same way. FL/IN/SH colour cannot be read as numbers from firmware. Next: Ghidra on `cpapp-b.bin` from `ColorMode`/`GetMainGamma`, and a WBI2 parser for `nflasha5` (memory snapshot; it may contain already-expanded tables).

## 2. The stage after the tone LUT (highlight lift)

### 2.1 Measurement [verified]
Data: `data/measurements/ramps.json` (JPEG G channel), RAW of DSC09419, base gamma (0,1) (2048 x u16), stock k0/k1, film k0 curve (see notes/tone-curve.md).

**(a) c0, base only.** 09509 vs `base(RAW*2043*s)`, s = 2.12 fitted on steps 3-12:
- error on steps 6-15 within +/-2 Y';
- top brighter by +2...+4.5 Y' (232 vs 236.6);
- +7 in shadows at step 3: the RAW came from a different frame (09419), a method limitation.

**(b) c-3 at the same exposure.** 09510 vs `k0film(09509)` (direct c0 -> c-3 mapping, no RAW):
```
input c0  197 207 215 221 226 230 233 235 237
k0(c0)    187 195 201 206 209 212 214 216 216
measured  187 199 209 217 223 226 230 232 233
```
Up to 197 agreement is +/-1.5 Y'; above it the gap is +4...+16. The measurement tracks "c0 minus 3.5...8".

**(c) Ceiling.** Max of film k0 = 909 -> 226.6/255, measured 232.7. So after the LUT there is a stage that can push output **above any LUT value**.

**(d) Not a function of LUT output.**
- LUT output ~213: c0 (09509) gives 214.7, c-3 (09510) gives >= 232;
- output 175: 09419 (c0) gives 176, 09420 (stock c-3) gives 187.

The stage knows the input (linear signal or "base"), not only Y' after the curve. Knee, JPEG range mapping, and a YC-matrix shift (stages that see only the output) are ruled out.

**(e) Where the threshold is.** In 09510, curve weight `w = (measured - base)/(curve - base)`:
- ~1.0...1.1 up to Y'c0 ~ 197;
- 0.68 at 207, then 0.4 -> 0.2 -> 0.16-0.19.

The sharp drop starts around input 511 of 2047, at the boundary between LUT grid segments 5 and 6 (`271...511` step 16 -> `543...1023` step 32).

For stock c-3 (09420, top input ~397) the weight is 0.3-0.5 already above Y' 140 (vs k0) or 0.5-0.7 (vs k1). No sharp threshold there. Those frames were shot on another day with AWB and the stock curve, so the "511" threshold rests on one frame [hypothesis about shape; existence is a fact].

### 2.2 Code [verified what is ruled out]
- `tone_lut_build` (`0x2d6996`) in all four branches (k7 family / contrast / style / base) loops over all **96** nodes and applies `curve[base(x)]` with a 0x3ff clip. No special handling of upper segments. The builder is not the cause.
- The monitor writes the LUT directly to `0xf4015300` (`0x37d6ec`); capture writes to buffer `[0xc3cbe09c]` (`0x37ddc8`, 0x180 bytes + 36 bytes of segments). On capture the LUT goes further into the YC pipeline with other stages. Pipeline composition from the signature `Camera::YC::job_YC_ModeMain(...)`: `Pfr, Dg, Itp, Cas, Clp, Nr, Yap, Shd, ShdOff, Adj, Mov, Lga, Gra`. Most likely candidates: **Clp** (clip) and **Lga/Gra** (gradation) [hypothesis from names].
- There is also a colour 3D LUT: `[CAMERA_MAIN_CC]: Create3DLUT ... Level ... BlkOfs Cr/Cb` and `CamCore Change 3D-Lut` (`0xc77c8`, 0x654 bytes of data via `[struct+0x90]`). Also post-tone. But a 3D LUT is a function of output colour, and (d) rules out a pure output function. Only fits if the LUT is rebuilt depending on contrast [hypothesis, unlikely].

### 2.3 Makernote trace [verified, then refuted]
In the decrypted Sony tag `0x9405a` (exiftool -v4; the field exiftool calls `ChromaticAberrationCorrParams`) at offset `+0x68a` there are 11 x int16 with two states:
- **A** `-272 -184 -112 -40 16 48 112 264 512 880 1392`;
- **B** `1320 1292 1240 1164 1064 940 792 616 440 280 156`.

Initially B appeared to coincide with "any contrast or style curve enabled". **Correction (notes/night-extra.md, 1.1):** checking all 67 frames 09416-09510 showed A/B alternate independently of style and contrast (Standard c0 occurs in B, Vivid in A), and c0 wedges in A and in B match within +/-1 Y'. It is the second half of `ChromaticAberrationCorrParams` and does not affect tone.

These arrays were not found in av-cam, sabin modules or Backup (int16/int32, LE/BE, stride 2-8).

### 2.4 Backup
Not found. In `0x3007a` (tone block), bytes `+0xD2...+0xD6`, `+0xE0...+0xE3`, `+0xE6` are read **outside** the override (see notes/symbols-and-names.md 7.2); meaning not established. First candidates for "highlight protection" [hypothesis]. Writing them blindly is not advised.

### 2.5 Consequences for a film shoulder
- A shoulder that **lowers** highlights below standard is pulled back almost to standard above Y' ~ 200: only -3...-8 Y' remain. The current k0 with white 909 actually yields white ~233/255, not 227.
- Working rule: design the curve so that for Y' > 200 it stays no lower than "base - 5". Build shoulder softness below 200, where the curve is honoured. Or accept a Standard-like top end.
- Test without firmware changes: same scene, Standard c-3 at +1 and +2 EV. If the threshold is tied to input ~511, at +1 EV the boundary moves one step down. If it moves in Y', the stage is level-dependent.

## 3. Sunset warmth on Auto WB

### 3.1 Measurement [verified]
Grey b* (`code/measure/ramp.py`, every other step):
```
09419 Standard AWB  0.0 0.1 1.0  2.6  2.8  2.4  2.1  1.6  0.7  0.3 -0.4
09416 Vivid AWB     0.0 0.1 0.4  2.6  3.2  3.9  3.7  3.0  1.4  0.2 -0.9
09418 Sunset AWB    0.0 0.8 3.4 17.0 25.4 30.8 29.1 29.0 26.7 23.8 21.4
09425 Sunset AWB    0.0 0.8 4.1 17.1 21.9 25.1 28.6 27.9 25.9 22.9 20.2
```
JPEG converted back to linear through inverse curves: Sunset = `k14(base)`, Standard = `base`. Sunset/Standard ratio on steps 4-18:
- 09418: **R 1.36...1.42, G 1.04...1.07, B 0.56...0.62**;
- 09425: **R 1.36...1.48, G 1.08...1.10, B 0.61...0.70**.

The ratio is nearly constant across tones, so it is a **multiplier in the linear domain before the tone curve**, a WB-type gain, not a post-tone Cb/Cr shift. Consistent with the earlier observation that warmth faded with muted matrices. These numbers include Sunset's own matrix/saturation gain, so the "pure" gain may be smaller [hypothesis].

### 3.2 Makernote [verified]
- `WB_RGBLevels`/`RedBalance`/`BlueBalance` for Sunset on AWB (09418: 667/256/430, 09425: 657/255/432) match Standard/Vivid/Portrait (657-666/256/431-435). **No shift in recorded coefficients.**
- On Custom 5500 K Sunset (09433, 09438) also has normal values. No warmth at fixed WB (earlier finding).
- Among all tags, the only stable difference of Sunset on AWB from other styles is `ColorMode = 4`.
- Conclusion: the warm multiplier is applied **after** AWB recorded its estimate, and only under AWB.

### 3.3 Code [verified what was found]
- Colour module `[CAMERA_MAIN_CC]` (code ~`0x3c8000...0x3ec000`, near `Create3DLUT`) keeps **its own style index** at `obj[0]+0x26`. A table (`0x3d6ea6`, jumps on `+0x26`, 15 values) maps it to a name and EXIF `ColorMode`:

  | CC index | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | **9** | 10 | **11** | 12 | 13 | 14 |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
  | name | Standard | Vivid | Neutral | Portrait | Landscape | BW | Clear | Deep | Light | **Sunset** | Nightview | **Autumnleaves** | Real | Sepia | BW |
  | EXIF ColorMode | 0 | 1 | 12 | 2 | 3 | 6 | 13 | 14 | 15 | **4** | 5 | **16** | 0 | 17 | 6 |

  The second row matches exiftool's `ColorMode` list, so the table is read correctly. A second copy of the names is at `0x3d8fd2`.
- Index `+0x26` is also read by `0x3cf214` (near functions using WB-calibration block `0x30002`: `0x3cfbe6`, `0x3d4f0c`, `0x3d9290`, `0x3dbd94`...), `0x3d0e00` and parameter packer `0x3dbff4` (`+0xabe`). First places to look for "if Sunset/Autumn and AWB then multiplier" [hypothesis].
- No `cmp #9`/`cmp #0xb` near the index reads. Selection is probably via an index table or in a DSP module.
- Scanning Backup `0x0003xxxx` blocks for "13-15 entries, nonzero for Sunset" tables gave only noise (2186 false hits). Blocks read by CC: `0x30000`, `0x30002` (calibration, **do not touch**), `0x30003`, `0x30004...07` (4 x 1280 B, look like per-condition calibration, not per-style), `0x30009`, `0x3000a`, `0x30057/58/5a`, `0x30068`, `0x3006a/6b`, `0x30078/79`, `0x3009b...9d`, `0x300ae`, `0x30102`, `0x3012b`, `0x3012f`. **The ID carrying the warm shift is not established.**

### 3.4 What can be done now
- **Menu, no edits:** AWB + A-B shift (EXIF tag `WBShiftAB_GM`). Same operation type (linear R/B gain) but for all styles.
- **Via Backup, our style only:** bake warmth into the slot **matrix** (`0x30001`, `+0x48+18*slot`). A per-channel multiplier before the matrix equals scaling matrix columns: `M' = M*diag(r, 1, b)`. With fixed WB this gives a warm "Kodak" look without AWB; with AWB the matrix adds warmth on top of neutral. Already-proven lever (looks v3-v5). Pick r/b by measurement; Sunset ~ r 1.3 / b 0.6 is very strong, for "Kodak" more like r 1.05-1.10 / b 0.90-0.95 [taste hypothesis]. Variants: `data/looks/` (warm variants).

## 4. Next (by value)
1. Recompute the k0 shoulder under rule 2.5 ("no lower than base - 5 for Y' > 200"). Pays more than chasing the stage.
2. Warmth for film styles via matrix columns (3.4). Pursue the Sunset AWB branch only if "warm only on AWB" is specifically required.
3. For section 2: Ghidra on `job_YC_ModeMain` and stages `Clp`/`Gra`/`Lga`.
4. For section 1: Ghidra on `cpapp-b.bin` (`PQD_Gamma`, `ColorMode`) and a WBI2 parser.

## Sources
- Own data: stock 3N `av-cam`, `data/measurements/ramps.json`, film k0 curve, a Backup export, test-chart frames DSC09416-09510 (+ARW 09417-09439).
- a7 IV: Sony firmware Ver. 6.02; ILCE-7M4 Help Guide "Creative Look"; github.com/ma1co/fwtool.py PR #52 (by DavidBuchanan314), PR #53.
- exiftool Sony.pm (tag 0x94xx decoding, ColorMode enumeration).
