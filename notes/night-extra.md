# NEX-3N: highlight floor, Phoenix violet sky, "warm Kodak" in the matrix

Static analysis and simulator only; the camera was not connected and nothing was written. Tags: **[verified]** = visible in bytes, code, EXIF or frame measurements; **[model]** = simulator prediction; **[hypothesis]** = unverified inference. Related: `notes/open-questions.md` sections 2-3, `notes/symbols-and-names.md` sections 7-8, `notes/colour-v6.md`, `notes/hue-tables.md`, `notes/tone-curve.md`.

Design scripts (not included): sky probe, warm matrix variants, warm comparison sheets, shoulder-probe generator; all ran with the simulator venv (`code/sim/`). Data: `data/looks/night_warm_variants.json`, `data/fx/changes.json`.

## 0. Summary

1. **Highlight floor: stage not found, no Backup control.** The main candidate from the previous session is ruled out:
   - makernote field `0x9405a+0x68a` is unrelated to the curve [verified on 67 frames]. It is the second half of `ChromaticAberrationCorrParams` (exiftool), and its two states A/B alternate **independently of style and contrast**;
   - `Clp` and `Lga` are raw-input stages (OB black clamp, level equalisation), not highlight stages.

   No new Backup lever, no blob that removes the floor. There is a **diagnostic blob** in mode 1 (1.5): it shows immediately whether the floor applies when the LUT comes from Backup. If it does not, the same blob gives a 180 -> 230 shoulder.
2. **Phoenix violet sky:** "phoenixsky" = v6 + **one byte** `0x163` (r4, Q0, byte 3 "blues/violets"): `fa -> 3a`, i.e. -6 -> +58 (delta +64).
   - Prediction from the Standard measurement: blues and violets +8 deg toward violet.
   - Simulator for Sunset: sky +10 deg, blues +3..+8 deg.
   - Worst case with camera gain x1.78: +19 deg on sky. Still less than the scans' +26 deg.
   - Previous r4 edits in Sunset gave ~0 deg or the **opposite sign** (2.2), which is why the experiment is needed.
3. **Warm Kodak (taste option):** "kodakwarm" = v6 with the slot 1 (Portra) matrix multiplied by diag(1.05, 1, 0.95) and slot 3 (UltraMax) by diag(1.05, 1, 0.92). 14 bytes differ, only in the matrices.
   - Greys warm on purpose: b* +3.7 (Portra) and +5.6 (UltraMax), a* +0.7..+0.8 [model; the matrix part of the simulator is confirmed on RAW+JPEG pairs].
   - r = 1.08 rejected: gives a pink cast to greys.

## 1. Highlight floor above Y' ~200

### 1.1 Makernote field `0x9405a+0x68a` is neither a control nor a trace of the curve [verified]

- exiftool reads this block as `ChromaticAberrationCorrParams` (int16s[32] from `0x66a`): `+0x68a` is elements 16..26. Around it are `VignettingCorrParams` and `DistortionCorrParams` of 11 values each, which are constant.
- Checked all 67 chart-session JPEGs. **State B (`1320 ... 156`) occurs with Standard c0**, **state A (`-272 ... 1392`)** occurs with Vivid, Portrait (c+3), Landscape and Sunset, and each style was also seen in the other state. The state depends on neither style, contrast nor WB. The two frame pairs behind the conclusion in `open-questions` 2.3 happened to land on A/B by chance.
- Standard c0 grey wedge in state A vs B: no difference. Two consecutive frames (B and A) match in G on all 21 steps within +-1 Y' (top 236 / 236). Another pair matches within +-2.
- The lens is a manual "E 27mm F2.8" focused at infinity, so the alternation is probably about how correction data is fetched [hypothesis]. **The field does not affect tone.** The `open-questions` 2.3 conclusion "toggles exactly when the curve is on" is wrong.

### 1.2 Stages of `job_YC_ModeMain` [verified by strings; role is hypothesis]

- **Clp**: black clamp from the optical black area. Debug fields `PBEH:clp_on/clp_gr/clp_gb/clp_r/clp_b/clp_ofst`, errors `[YC-CLP ERROR]opbData`, `api_YC_CaptureRawReadExecuteClp`. Raw input, unrelated to post-tone highlights.
- **Lga**: "LightLvAdj", per-channel level equalisation (`lga_ave_r/gr/gb/b_L/R`). This is calibration block `0x30036`, **do not touch**. Also raw input.
- **Gra**: no strings. By its neighbourhood with Lga and the order in the signature, probably another raw-input stage (Gr/Gb) [hypothesis].
- So among the 13 stages of `job_YC_ModeMain` there is no obvious "after the tone LUT" candidate. The YC pipeline starts from raw data; tone and colour run in separate hardware blocks.

### 1.3 What the `0x3007a` bytes "read outside the substitution" do [verified by code]

- `+0xD2..+0xD5` (stock `00 00 00 01`) **go straight into gamma-block registers**:
  - monitor: function `0x2d7dba` -> `0x37d6d8` -> `0xf4015480`, `+484`, `+488`, `+4b8`;
  - capture: `0x2d7a04` -> `0x37ddb0`, same offsets in the register image `[0xc3cbe0a4]+0x80..`.

  Next to them are the LUT itself (`0xf4015300`, 0x180 B) and segment parameters (`0xf4015494..+4b4`). The three adjacent registers `0x480-0x488` look like per-channel R/G/B parameters, `0x4b8` like a mode/enable [hypothesis]. They are 8-bit enums, not curves, and do not look like a "floor" by data shape.
- `+0xE2`/`+0xE3` (stock `04 04`) are split into nibbles and go into bit fields of register `0xf401c304` (function `0x151d9c`, fields 2/4/2/4 bits). Meaning unknown.
- Side finding: block `0xf401c...` contains a **second hardware tone LUT**: `0xf401c700` (0xC0 B = 96 x u16) and `0xf401c800` (0xA0 B). It is filled instead of the usual one when `obj+0xC71 == 9`: paths `0x2d67ca`, `0x2d7718`, `0x2d7d86`, even/odd split done by `0x2d6738`. What mode 9 is remains unknown.
- **Bottom line:** no Backup byte with a visible hardware link looks like a highlight threshold or weight. Blind writes to `+0xD2..+0xD5`/`+0xE2..+0xE3` are still **not recommended**.

### 1.4 Floor model [hypothesis, consistent with measurement]

- The measurement is described by **"out ~ max(LUT, base - delta)", delta ~ 3..8 Y'**. The curve weight `w = (measured - base)/(curve - base)` at constant delta equals `delta/(base - curve)`. As the curve drops 10 -> 20 Y' below base, it falls 0.4 -> 0.2, exactly as in `open-questions` 2.1(e).
- Two consequences:
  - the stage knows the base (standard) tone, not only the LUT output;
  - the tone LUT can lower highlights only down to "base - delta".

  Where the stage gets the "base" (the second LUT, a parallel Y path, or elsewhere) was not found statically.

### 1.5 Diagnostic experiment: shoulder in mode 1 (optional; only after mode 1 itself is proven to work)

Goal: tell from one frame whether the floor applies when the **whole** LUT comes from Backup (mode 1, `notes/symbols-and-names.md` section 8). Whether "contrast or style enabled" flags are set in that case is not clear from code.

- **Blob** (property `0x0003007a`, generated by the shoulder-probe script; changes logged in `data/fx/changes.json`):
  - `+0x00..+0xBF` = 96 x u16: `Y_k = S(base(0,1)[X_k])`. **S is identity up to Y' 180, then a soft shoulder** (exponential with slope 1 at the joint) up to **Y' 230 at base white**. Values from `15, 30, 47 ...` to `923`, monotonic.
  - `+0xD7: 00 -> 01`. 163 bytes differ, everything else stock.
- **Revert:** the stock `0x0003007a` value; verified byte-identical to the snapshot (attr 08, single bank).
- **Why mid = Standard:** only one variable changes, the highlights. Black and mid are Standard c0, so any difference above 180 is the shoulder.
- **Grey scale prediction** (G, exposure 1/80, f/4.5, ISO 800, Daylight):
  ```
  Standard c0              ... 170 185 197 207 214 221 226 229 232 235 236
  shoulder, no floor       ... 170 185 195 203 208 213 216 217 219 221 221
  shoulder, floor base-8   ... 170 184 195 203 208 213 218 221 224 227 228
  ```
- **Frames:** WB Daylight, M, DRO off.
  1. Same session, mode 0: Standard c0 at 1/80 and at **+1 EV**.
  2. Write, read back = written.
  3. Standard c0 at 1/80 and +1 EV, then Vivid c0 at 1/80.
  4. Revert, read back = original.

  At +1 EV the top of the wedge goes to base white. Then "no floor" = top <= 230, "floor" = top >= (c0 at +1 EV) - 8, i.e. around 242 or more. A difference > 10 Y', readable from one frame.
- **Reading:**
  - top follows the "no floor" row (+-3) -> no floor in mode 1. A film shoulder is then one Backup write, and mode 1 becomes the main tone path;
  - top holds at "c0 - 3..8" -> the floor sits after the LUT on any path. The shoulder must then be built below 200, as in the `open-questions` 2.5 rule;
  - dark or linear frame -> mode 1 did not take, revert immediately (same failure as in `symbols-and-names` section 8).
- **Risk:** same as any mode-1 write (one block, one bank). Only if mode 1 with a film curve has already worked.

## 2. Phoenix violet sky: single-byte experiment on r4

### 2.1 What changes [verified by bytes]

- Sunset record r4 = `0x00030001 +0x160` (24 B). Q0 = `+0x160..+0x163` = `-48 -33 -35 -6` (v6). Byte 3 is the blues/violets region (~250..335 deg Lab).
- **`0x163: fa -> 3a` (-6 -> +58).** Nothing else: the block differs from v6 by exactly one byte. Q2 byte 3 (`+0x16b`) = 35 left as is.
- Why byte 3 and not 2: real Phoenix sky sits at the border of regions 2 and 3 (chart patch at 247 deg), and in scans it is 26 deg "more violet". Byte 3 pulls blues toward violet, byte 2 rotates cyans and teals. Also v4->v5 showed Sunset barely reacts to byte 2 (2.2). If byte 3 fails, the next candidate is Q0 byte 2 in the negative direction.

### 2.2 How Sunset responded before [verified, chart]

Sunset dh minus Standard drift of the same session:
- **v3->v4:** region 3 +41 units (Q0+Q2), region 2 +26, region 1 -20.
  - Standard model expected: blue flower +5 deg, cyan -10 deg, yellows -4 deg.
  - Got: blue flower -6.9 deg, cyan +7.3 deg, foliage and yellows +4..+5 deg.

  **All three signs reversed**, magnitude about half.
- **v4->v5:** region 2 -52 units. Model: +20 deg on cyan. Got -3.9 deg cyan and -2.9 deg sky, raw Sunset dh ~ 0.
- So in Sunset the r4 records act with a weak and reversed response, or barely at all. Possibly linked to the `-128` marker in Q1 [hypothesis]. The simulator does not know this (`colour-v6` section 1).

### 2.3 Prediction for delta +64 (chart patches, dh in deg)

| patch | Lab h (Std) | simulator, Sunset | Standard model | worst case x1.78 |
|---|---|---|---|---|
| blue sky | 247 | +10.1 (chroma +9 %) | +13.8 | +18.6 |
| blue flower | 277 | +7.5 (+12 %) | +8.5 | +15.4 |
| purplish blue | 288 | +6.1 (+10 %) | +7.6 | +13.7 |
| purple | 308 | +5.3 (+10 %) | +4.8 | +8.7 |
| blue | 299 | +3.3 | +4.4 | +8.0 |
| cyan | 230 | +10.7 | +12.4 | +16.7 |
| magenta | 336 | +1.4 (+9 %) | +1.2 | - |
| reds, skin, yellows, greens | - | 0 | 0 | 0 |

- Manual single-byte test on Standard: +0.07..+0.17 deg/unit -> **+4..+11 deg** on blues.
- Given 2.2, the realistic Sunset range is **-5 deg (reversed) to +19 deg**. The ceiling is below the scan target (+26 deg), so no overshoot even in the worst case.
- Side effect if it works: blues slightly more saturated (+4..+12 %). Acceptable for Phoenix: scans have higher relative sky saturation.
- Delta +46 (i.e. +40 as in `colour-v6` section 6) rejected: with Sunset response ~0.5x it would give 2-4 deg, within chart noise (+-2..5 deg).

### 2.4 Frames and decision

- Write to **both banks**: `0x00030001` and `0x00030008`. Read back = v6 before, = phoenixsky after.
- **Frames** (WB Daylight, M, RAW+JPEG):
  1. Before: chart Standard + Sunset.
  2. After: chart Standard + Sunset, then Sunset again (noise).
  3. One frame of real sky in Sunset before and after, same framing and exposure.
- **Evaluation:** chart-evaluation approach, Sunset dh minus Standard dh on the 5 blue patches and cyan.
  - Mean over blues >= +4 deg -> Sunset follows r4 in the right direction. Then tune magnitude: keep or raise to +80..+90.
  - <= -4 deg -> reversed sign in Sunset. Next: move `0x163` negative from -6.
  - |delta| < 3 deg -> r4 does nothing in the blue region. Do violet sky with the matrix (together with skin) or move Phoenix to another slot.
- **Revert:** v6 to both banks.

## 3. Warm Kodak in the slot matrix (taste option, not a correction)

### 3.1 Calculation [model for greys and patches; matrix confirmed RAW+JPEG]

`M' = M_v6 . diag(r, 1, b)` = per-channel gain before the matrix (`open-questions` 3.4). int16, det > 0. **Row sums leave 1024 on purpose**, so greys warm up. Delta vs v6 of the same slot, greys from a Custom 5500 K chart frame.

| slot | r / b | matrix | row sums (%) | da* / db* greys | dh skin / sky, cyan / greens |
|---|---|---|---|---|---|
| 1 Portra | v6 | `1068,110,-154 / 96,1239,-311 / 51,25,948` | 1024 x3 | - | - |
| 1 | **1.05 / 0.95** (chosen) | `1121,110,-146 / 101,1239,-295 / 54,25,901` | +6.0 / +2.1 / -4.3 | **+0.7 / +3.7** | 0..-1 / +0.1, -6.9 / -2..-4 |
| 1 | 1.05 / 0.92 | `1121,110,-142 / 101,1239,-286 / 54,25,872` | +6.3 / +2.9 / -7.1 | +0.1 / +5.5 | +2 / -7, -12 / -2..-4 |
| 1 | 1.08 / 0.95 | `1153,110,-146 / 104,1239,-295 / 55,25,901` | +9.1 / +2.3 / -4.2 | +1.7 / +4.1 | -1.4..-1.8 / +6, -6 / -3..-6 |
| 1 | 1.08 / 0.92 | `1153,110,-142 / 104,1239,-286 / 55,25,872` | +9.5 / +3.2 / -7.0 | +1.0 / +5.9 | ~0 / -1, -11 / -3..-6 |
| 3 UltraMax | v6 | `1350,-57,-269 / 45,1258,-279 / 34,-56,1046` | 1024 x3 | - | - |
| 3 | 1.05 / 0.95 | `1418,-57,-256 / 47,1258,-265 / 36,-56,994` | +7.9 / +1.6 / -4.9 | +1.3 / +3.7 | ~0 / +1, -5 / -2..-6 |
| 3 | **1.05 / 0.92** (chosen) | `1418,-57,-247 / 47,1258,-257 / 36,-56,962` | +8.8 / +2.3 / -8.0 | **+0.8 / +5.6** | +1..+3 / -5, -9 / -2..-6 |
| 3 | 1.08 / 0.95 | `1458,-57,-256 / 49,1258,-265 / 37,-56,994` | +11.8 / +1.8 / -4.8 | +2.5 / +4.2 | -1 / +8, -5 / -3..-8 |
| 3 | 1.08 / 0.92 | `1458,-57,-247 / 49,1258,-257 / 37,-56,962` | +12.7 / +2.5 / -7.9 | +2.0 / +6.0 | ~0 / +3, -9 / -3..-9 |

All variants: `data/looks/night_warm_variants.json`.

### 3.2 Previews and choice [model]

- Comparison sheets (not included), per row: v6 | 1.05/0.95 | 1.05/0.92 | 1.08/0.95 | 1.08/0.92.
- 31 test frames (live interior and outdoor frames plus a July daylight set). The median tint of near-grey pixels shifts by b* +2..+4, with r = 1.08 also a* +1..+2. On outdoor frames with grey walls this **reads as a pink film on the greys**.
- **Choice:**
  - Portra: r 1.05 / b 0.95, gentle warmth, skin in place;
  - UltraMax: r 1.05 / b 0.92, yellow-warm like the stock itself, no pink.

  This is taste, not a target hit: Maraver has no "warm greys" target (greys are normalised there).
- **Block:** differs from v6 in 14 bytes, only in the slot 1 and 3 matrices:
  ```
  0x05a 2c->61; 0x05e 66->6e; 0x060 60->65; 0x064 c9->d9; 0x066 33->36; 0x06a b4->85;  (slot 1)
  0x07e 46->8a; 0x082 f3->09; 0x083 fe->ff; 0x084 2d->2f; 0x088 e9->ff; 0x08a 22->24; 0x08e 16->c2; 0x08f 04->03  (slot 3)
  ```
  Bytes outside matrices and hue records equal the snapshot `0x00030001` block: verified, 0 differences. Slots 0, 2, 4 and all hue records = v6.

### 3.3 Caveats

- Greys shift **under any WB**. On Daylight this is the warm Kodak. On AWB the warmth sits on top of neutral and AWB will not eat it: the matrix sits after WB (`notes/simulator.md` 0.3).
- R row sum +6..+9 % -> R channel clips about 0.1 EV earlier. In bright warm highlights (sunset, sunlit skin) red detail goes slightly earlier [hypothesis from arithmetic].
- Sky and cyan: Portra variant -7 deg (toward teal), UltraMax -5..-9 deg [model]. In character for Kodak, but sky on scenes is unverified by the simulator: the frames have none.
- Not combinable with phoenixsky as is: both are v6 + their own edit. Try one at a time; if both are liked, merge into one block.

### 3.4 Frames

- Write to both banks. Read back = v6 before.
- Chart at Daylight: Standard + Vivid + Landscape before and after. Plus 2-3 outdoor scenes (grey wall, skin, sky) in Vivid and Landscape before and after.
- Watch greys: b* should rise by about +3..+6, a* no more than +1.
- Revert: v6.

## Sources

- Chart-session frames (EXIF via exiftool 13.10, `Sony.pm` Tag9405a: `0x066a ChromaticAberrationCorrParams int16s[32]`), grey wedge via `code/measure/ramp.py`.
- av-cam (3N): functions `0x2d7dba`, `0x2d79e0`/`0x2d7a04`, `0x37d6d8`, `0x37ddb0`, `0x151d9c`, `0x151de4`, `0x2d6738`, `0x2d676e`; literals `0x2d7dfc` (`0xc3ac615c` = `0x3007a+0xC0`) and `0x2d7e34` (`+0xE0`). Strings `PBEH:clp_*`, `lga_ave_*`, `[YC-CLP ERROR]`.
- Simulator `code/sim/` (fitted on RAW+JPEG pairs). Chart: sessions v3/v4/v5.
