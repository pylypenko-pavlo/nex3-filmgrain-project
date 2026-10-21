# NEX-3N JPEG pipeline simulator (colour and tone)

Looks are designed on a computer, without the camera: a RAW or an existing JPEG is pushed through a model of the camera's pipeline with any colour block (Backup property `0x00030001`), creative style and tone curve. Related notes: README (slots, look versions v1-v5), `notes/hue-tables.md`, `notes/tone-curve.md`, `notes/house-phoenix-looks.md`.

Tags: **[verified]** = confirmed by RAW+JPEG pairs or by code; **[model]** = empirical fit; **[hypothesis]** = data equally explained by several variants.

## 0. Summary

1. **The simulator works.** Code: `code/sim/`. Two modes:
   - RAW -> JPEG;
   - JPEG -> JPEG: a frame shot with a known style and block is re-rendered as another style or block.

   There is a batch run with a contact sheet and a validation report.
2. **Accuracy on a ColorChecker target** (dE76, chromatic patches / greys):
   - RAW->JPEG, training (13 frames): 2.6 / 0.9;
   - RAW->JPEG, held-out (9 frames: other WB, WB shifts, Sunset, permutation matrices): **3.3 / 1.8**;
   - JPEG->JPEG between styles (18 pairs v1/v3/v4/v5/binary, not used in fitting): **4.2** vs 7.7 for the null model "nothing changes".

   The floor is set by the measurement tool itself: a target shown on a monitor gives 4.7 dE between two frames with identical settings (5 control pairs; up to 14 on single patches). RAW+JPEG pairs do not have this noise: both files are the same exposure.
3. **Established on RAW+JPEG pairs** [verified]:
   - the slot matrix is applied to **white-balanced camera RGB in linear light**, with no intermediate space. Model error 4.1 vs 13.8 if WB is applied after the matrix. An extra 3x3 before or after the matrix adds nothing;
   - **the ARW stores in SR2 `ColorMatrix` exactly the slot matrix the frame was shot with** (visible on tagged frames and frames with a muted matrix). This is a free check for any future write;
   - the applied WB coefficients exist only in the ARW (`SR2:WB_RGGBLevels`). `Sony:WB_RGBLevels`, present in the JPEG too, is an auto-WB estimate, not the coefficients (in a series with Custom WB the coefficients are constant while `WB_RGBLevels` drifts);
   - Contrast curves are applied **per channel to RGB**, not to Y: 1.8 vs 3.7 dE at c-3/k0 and c+3/k6;
   - **the Saturation slider is a chroma multiplier 1 + 0.13*s** in YCbCr (-3 -> 0.625, +3 -> 1.375).
4. **Emulation of `Create3DLUT` (part B) was done**, but it is useless for looks. The function does not read the 24-byte hue records; it scales and repacks a ready reference 3D LUT (section 4). Hue tables are therefore modelled empirically (section 3).

## 1. Usage

```
cd code/sim
# RAW: any block/style/curve; --wb asshot|daylight|cloudy|shade|tungsten|...|R,B; --full = full resolution
python sim.py --raw <frame>.ARW --block looks_v5 --style sunset --curve film --out out/x.jpg
# JPEG: source block by frame number (session log in block.py) or --src-block
python sim.py --jpg <frame>.JPG --block my.hex --style portrait --ev -1 --out out/y.jpg
# contact sheet: frame x 5 styles of a block
python batch.py --block looks_v5 --curve film --out out/sheet.jpg
python validate.py          # validation tables (cache/validate.txt)
python fit_final.py         # refit parameters (cache/params.npz, cache/fit_report.txt)
```

- `--block`: path to a hex dump of the colour block or a named block. `--matrix "9 numbers"` replaces the slot matrix. Raw property dumps are not shipped; designed matrices and hue-table values are in `data/` as JSON.
- `--curve` replaces the **style curve**: `k0...k20` (the 21 curves from the firmware), `film` (the fitted film curve, see `notes/tone-curve.md`) or your own `.npy` with 1024 values. The Contrast curve is applied before it, as in the camera.
- `--k0 film|orig` - what sits in k0 (Contrast -3). Default `film`, since the film curve was installed there on the test camera.
- Fitted parameters (`cache/params.npz`) and the firmware curve cache (`cache/tone_k.npy`) are not shipped; regenerate with `chart.py` + `fit_final.py` from your own RAW+JPEG target frames. Reading the firmware curves and the `emu3dlut.py`/`avdis.py`/`xref.py` tools expect a user-supplied, unpacked firmware image (`av-cam`, path via env var `NEX3N_AVCAM`); none is shipped.

**How to design a look.** Edit a block (slot matrix and/or hue record) -> run `batch.py` on your frames -> inspect the sheet. Only then write to the camera. For RAW frames the matrix can be verified later via the `ColorMatrix` of the resulting ARW.

## 2. Pipeline model (stage order)

```
cam = (raw - black)/white, half resolution (2x2 Bayer quad)          rawio.py
x   = cam * WB  (SR2 WB_RGGBLevels/1024)                             [verified]
y   = M_slot * x  (int16/1024, linear light)                         [verified]
e   = F(y) per channel, code 0...1023 (base gamma, monotone spline)  [model]
e   = C_style(C_contrast(e)) per channel                             [verified for Contrast; style: see below]
YCbCr(601): chroma * boost(style) * (1 + 0.13*Sat)                    [verified for Sat; boost = model]
H0(angle)                       - common hue residual (Fourier)      [model]
hue stage(record - Standard record)                                  [model, section 3]
-> sRGB 8 bit
```

- **Style curves.** Vivid/Landscape/Sunset = k14 [verified: Sunset k14 2.25 vs 4.4 for k15]. Portrait = k1: on the single RAW frame (c+1) k1 and k2 are indistinguishable (2.31 / 2.37); k3 and k18 are worse. For c0, k1 is confirmed by the grey ramp in `notes/tone-curve.md`.
- **Colour stage before or after the tone curve - indistinguishable** (2.60 vs 2.61). "After" chosen.
- **Style boost on top of the tables:** Vivid x1.06, Portrait x1.11, Landscape x0.96, Sunset x1.07 [model]. The earlier +11/+14/+14% were the total difference vs Standard; most of it is now explained by the native Q1 records (less negative in Vivid and Portrait).
- **Marker -128 in Sunset Q1** [hypothesis]. "Same as Standard", "0" and "literally -128" give identical error (absorbed by the boost). Only the first is physically plausible (boost 1.07; "0" needs 0.73, "literal" needs 2.78). Chosen.
- **Parameters:** `cache/params.npz`, 65 numbers.

## 3. Hue tables: empirical model [model]

Four axes in the CbCr plane, piecewise linear (`hue.py`). A colour between adjacent axes j and j+1 is decomposed onto them; axis j is rotated by r_j and scaled by s_j:

- r_j = alpha_j * (Q0 + 1.03*Q2 + 0.55*Q4)_j;
- ln s_j = beta_j * (Q1 + 0.62*Q3 + 0.11*Q5)_j.

Fitted values:

| region | axis angle in CbCr | alpha, deg/unit | beta, %/unit |
|---|---|---|---|
| 0 reds | 100 deg | -0.22 | 1.11 |
| 1 yellows | 172 deg | +0.22 | 0.89 |
| 2 cyans | 268 deg | -0.17 | 0.78 |
| 3 blues | 342 deg | +0.22 | 1.19 |

- **Agreement with hand measurements** (`notes/hue-tables.md`): alternating alpha signs (there: -0.25 / +0.20 / -0.39 / +0.13 deg/unit); Q2 ~ Q0 and Q3 ~ Q1 (weight 1.03 on Q2); the Q4/Q5 pair is weaker.
- **"Leakage"** (yellow Q1 turns reds towards orange) falls out of the geometry: red lies between axes 0 and 1, and stretching axis 1 pulls it.
- **Training:** all 13 RAW frames plus 12 JPEG pairs (binary, bytes, bands, e1 experiments) as "base -> target" within a session; drift removed using the grey ramp. **Test:** v4<->v5 (same session) and v5<->v3.
- **Held-out JPEG pairs:** chroma 5.6 vs 6.6 for the null model, with control noise 4.7. The v4/v5 table changes lie almost entirely within target noise, so **the model's accuracy on subtle edits (+/-10 units) cannot be verified with this target.** Large edits (e1: zeroing, +/-100 units) are reproduced in direction but undershoot: 9.1 vs 28 for the null model.
- Absolute RAW->JPEG chroma error does not go below ~2.6 dE. Tried: black offset, matrix in a power domain, chroma-magnitude nonlinearity, an extra 3x3 - **none helped**. The residual is frame-dependent: in auto-WB frames up to 4 dE; light skin and yellow-green oversaturated. Cause unknown (candidate: the static 3D LUT from section 4).

## 4. Part B: emulating `Create3DLUT` (unicorn) [verified by emulation]

`emu3dlut.py` runs av-cam code at 0x3d03c4 (Thumb, VA = file + 0xc3441000) with stubbed structures. The function is self-contained; the only calls are two loggers, stubbed. Findings:

- Strings: `Create3DLUT 0x%X > 0x%X Level:%d ConvSD:%d BlkOfs Cr:%X, Cb:%X` and `NullError RefAdr/BufAdr`. It is a **copy of a reference LUT** (`RefAdr` = `[obj+0xa0]`) **into a hardware buffer**. It does not read the hue tables from Backup.
- **Grid:** Y nodes 0, 64...256 (5), Cb/Cr nodes -128...128 step 32 (9x9). Stores int8 deltas for three planes (presumably dY, dCb, dCr), clamped +/-63, packed 7 bits per word for hardware (order from table 0xc3a1852e).
- **Level 1...7** scales the reference LUT by Level/8; 0 or >=8 copies as-is. Emulation gave 0.249 / 0.500 / 0.750 at Level 2/4/6.
- With flag `[p0+0x2d]=1`, 6 sector values are added to plane 0. Each CbCr node blends two adjacent sectors with weights from table 0xc3a18138 (weights sum to 255). The result is **luminance by hue** (6 sectors), not our 4x6 records. The source of these 6 bytes and of the reference LUT was not found.
- `ConvSD` converts deltas between YCbCr 601 and 709: constants 0.108, 0.2045, 0.989, -0.111, 4/3 and a companding table.

**Why emulation gives no LUT for a block.** This function has neither the input (reference LUT) nor a consumer of the `+0x100...` records. Learning how the hardware interpolates the LUT would again require fitting to frames. So the simulator has no separate 3D-LUT stage: if the camera applies a static per-style LUT, its contribution sits in H0 and boost. Nearby: `Copy3DLUT`/`Copy2DLUT` and `LutMode Change CAP/MOV/MON`. The 2D LUT is a candidate consumer of the hue tables [hypothesis], not analysed.

## 5. Validation (details in `cache/fit_report.txt`, `cache/validate.txt`, generated)

**RAW->JPEG on the target (per frame).**
- Worst: Sunset with a permutation matrix (5.4) and Sunset in auto WB (3.7). Sunset may do something beyond k14 in the blacks: greys 3.0.
- WB-shift frames: 3.2-3.4, greys 1.3-2.6.
- Luminance everywhere |dL| < 1.5.

**JPEG->JPEG on live frames** (handheld, re-framed, so compared after shift alignment; reliable when r > 0.9). Median dE, model / null:
- v5 -> Sunset / Landscape (+0.3 EV) / Portrait (-1.3 EV): **3.1 / 3.3; 3.2 / 6.6; 2.2 / 15.7**;
- v1 -> Portrait 3.2 / 5.6, Landscape 4.2 / 4.3;
- v1 -> Vivid 3.8 / 3.1 and **Sunset 5.6 / 3.9: worse than null.** This is the v1 ColorPlus matrix in Custom WB; cause not found;
- a low-correlation series (r 0.65-0.77) is unreliable per pixel. Per hue sector the model wins: |dh| 1.6 deg vs 3.0 deg for null.

## 6. Limitations and next steps

- **Data.** All RAWs are of a monitor-displayed target with native tables. No RAWs of real scenes. The fit rests on 24 colours under various matrices; real-world skin, foliage and sky are not verified absolutely.
- **Not modelled:** distortion correction, vignetting, sharpening/NR, DRO, auto WB. WB comes from the ARW or is set manually. Clipping is not recovered in JPEG mode.
- **Next step** that would really raise accuracy: shoot **ARW+JPEG** on the current v5 - target at Daylight in all 5 styles plus 5-10 outdoor scenes - then `chart.py` and `fit_final.py`. This gives an absolute check of the v5 tables without monitor noise (target noise cancels within a RAW+JPEG pair).

## 7. Files (`code/sim/`)

- `sim.py` (CLI), `batch.py` (contact sheet), `pipeline.py` (forward and inverse pipeline), `model.py` (gamma, curves, YCbCr, H0, Lab), `hue.py` (table model), `block.py` (block parsing + "frame -> block" session log), `rawio.py` (ARW and EXIF).
- `chart.py` - patch extraction, RAW<->JPEG alignment per patch; caches `cache/pairs.npy`, `cache/jpg_patches.npy`.
- `fit.py` - data, train/test split, hypothesis switches (`FLAG`, `HUE_POS`, `CPOS`, `BLK`, `MG`, `CP`, `PORTRAIT_CURVE`); `fit_final.py`; `validate.py`.
- `emu3dlut.py` (unicorn), `avdis.py` and `xref.py` (disassembler and call search over the user-supplied firmware image), `cache/tone_k.npy` (21 curves read from av-cam; generated, not shipped).
