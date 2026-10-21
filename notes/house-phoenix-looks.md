# NEX-3N: House (Portrait slot) and Phoenix II (Sunset slot) matrices, block v3

Offline calculation; the camera was not touched. Design scripts (not included) ran in a numpy/pillow/scipy venv. Related: `notes/film-colorchecker-tests.md` (sections 3, 6-8), `notes/fuji-film-simulation-research.md`, `notes/hue-tables.md`, `notes/colour-v6.md`.

Tags: **[verified]** = measured on camera frames or follows from the bytes; **[model]** = linear-model prediction, not shot on camera; **[hypothesis]** = unconfirmed.

## 0. Summary

| Slot | v2 had | v3 (int16, 1.0 = 1024) | Row sums | det |
|---|---|---|---|---|
| 2 Portrait `+0x6c` | Gold 200 | **House** `1117,-3,-73 / 9,1216,-203 / -16,-11,1022` | 1041 / 1022 / 995 (+1.7 / -0.2 / -2.8 %) | 1.29 |
| 4 Sunset `+0x90` | ColorPlus 200 | **Phoenix II** `1082,47,-92 / 102,1150,-232 / 54,74,890` | 1037 / 1020 / 1018 (+1.3 / -0.4 / -0.6 %) | 1.05 |

Slots 0 (Standard), 1 (Portra 400) and 3 (UltraMax 400) stayed as in v2.

- Values: `data/looks/looks_v3.json` (plus `data/looks/v3_looks.json`, `data/looks/v3_T.json` with the linear-light look matrices). Check [verified]: block length 1536 bytes as in v2, only bytes `0x6c..0x7d` and `0x90..0xa1` differ. Before replacing, the script checked that v2 had Gold and ColorPlus from `looks_v2.json` at those positions.
- Written like v2: to both banks (`0x00030001` and `0x00030008`), see `notes/backup-params.md`.
- Previews (not included): Standard | look by model | scan reference.
- **Honest scale.** Both matrices are gentle, previews differ only slightly from Standard. Most of how the refs differ from Standard lives in tone (blacks, shoulder) and in frame content, not in 3x3 colour (section 4). House fits a matrix well: residual on the chart dE76 = 1.6. Phoenix fits badly: residual 4.4, worst patches magenta 10.9, blue 9.0, purple 7.4.

## 1. Measurement (metric)

Frame downscaled to 900 px long side. Scanner borders and the black gap of half-frame pairs are discarded: rows/columns with sigma(Y') < 6 and mean < 25 or > 235. Lab D65 from sRGB.

- **black / white / mid** = 1st, 99th and 50th percentile of Y' (Rec.709 on encoded values, 0..1).
- **C** = median C* over pixels with 10 < L* < 95; **hsvS** = median (max-min)/max.
- **wb** = mean RGB of pixels with 35 < L* < 70 divided by the three-channel mean.
- **Neutral tint** = median a*, b* of pixels with C* < 10 in L* bands of 20.
- **Hue sectors** (Lab h, pixels with C* > 12): red/magenta 330-30 deg, skin/orange 30-70, yellow 70-105, green 105-165, cyan 165-235, blue 235-300, violet 300-330. Per sector: share, mean C*, circular mean h. Pooling uses C* percentiles 50/75/90, 40k pixels per frame.

**Sets.**
- REFS: 39 reference film scans (the "house look" target).
- PHX: 24 Phoenix II scans (A7II camera scans).
- NEX Standard: only frames where slot 0 is guaranteed stock (two live frames). Frames shot with tag matrices loaded were excluded.
- NEX Portrait (a July set, Portrait, sat -1, contrast +1, 6000K, stock matrix = M0). Their chroma is divided by **1.098**: the measured ratio of chart C18 Portrait s-1 c+1 to Standard 0, both on stock matrices and Auto WB [verified].

Re-measuring older medians: refs black 0.050 (was 0.063), white 0.903 (0.907), hsvS 0.206 (0.239), wb [1.074, 1.018, 0.929] (was [1.06, 1.02, 0.93]). The black/chroma difference comes from border removal and metric; the old metric is unknown.

## 2. What the measurements show [verified, but frames are not paired]

| | REFS | PHX scans | NEX (Standard-equiv.) |
|---|---|---|---|
| black / white | 0.050 / 0.903 | **0.110** / 0.895 | 0.04 / 0.92 |
| C* median | 9.3 | 6.6 | 11.9 |
| C* p50/75/90 (pooled) | 13 / 21 / 31 | 12 / 20 / 29 | 14 / 23 / 39 |
| neutral a*, b* at L 40-60 | -1.2, **+2.6** | +1.2, **-1.4** | (warm interior scenes: +6..+7 b*) |
| neutral at L 60-80 | -0.8, +0.7 | +2.2, -2.3 | - |
| shadow chroma L < 20 | 4.9 | **2.2** | 8.5 |
| h skin / yellow / green | 56.5 / 84 / 116 | 57 / 86 / 121 | 55 / 88 / 115 |
| h blue (sector) | 257 | **282**, share 22 % | 286 (share 1 %) |

Conclusions the design relies on:
1. **Chroma.** Refs and Standard have nearly equal median and p75 (0.91-0.93), but the p90 "tail" is shorter in refs (0.79). Global k for House = **0.87**, the geometric mean of the three ratios. Matches the consumer C-41 consensus (Maraver Cr 0.85-0.92) and the x0.85-0.9 recommendation from the Fuji research.
2. **Tint.** Refs neutrals are warm (b* +1..+2.6 in shadows/mids) and almost neutral in highlights. Standard on the chart at fixed WB: a* ~ -1, b* ~ -1..-2. So a shift of ~ +3..+4 b* is needed.
3. **Phoenix II in these scans does not look like Maraver's Phoenix I.** Neutral is slightly cool-magenta, not yellow-green. Blue sky is saturated and drifts toward violet (h 282 vs 257 for refs) rather than collapsing into orange. Overall chroma low, shadows nearly colourless, blacks lifted (0.110). Maraver's hint (B->M->R drift toward orange) was applied only weakly, in reds and magentas; where it contradicts the scans, the scans win.
4. **Method limitation.** Scenes differ: NEX frames are warm interiors, refs are street and sky. So absolute C and wb over scenes **are not usable as a target**. Only percentile ratios, per-sector hue angles and near-neutral tint were used as targets, all checked on the chart.

## 3. Method

1. Source: chart frame (Standard, Custom WB), 24 patches, converted to linear sRGB.
2. Per-patch target: Lab Standard -> h + dh(h), C*k*c(h), L + dL(h). Functions defined by control points with periodic interpolation. Greys get tint only (da, db).
3. Look matrix T (linear light, relative to Standard output) = D(tint) . (I + P), rows of P sum to 0. Greys keep luminance; D sets the tint. D is fitted to the mid-grey tint subject to **|row sum - 1024| <= 3 %**. P (6 DOF) is fitted by weighted dE76 (skin x3, clipped patches excluded) with a penalty for leaving [0, 1].
4. Slot matrix = S(1/boost) . T . M0, where S(k) = k*I + (1-k)*1*w^T, w = Rec.709. Boost: Portrait = 1 (design choice), Sunset = 1.14. Grey and luminance preservation stays exact.
5. Constraint checks: |elements| <= 1216 (< 3000), det > 0, linear chart values 0.013..0.79, no clipping.

Targets (dh in degrees, c = chroma multiplier on top of k):
- **House**: k 0.87. Reds +3, skin +4 (warmer), yellows 0, foliage -3 (toward yellow). **Cyan and blues 0 (explicit no-teal rule)**, c 0.95; magenta c 0.9. Tint da +0.1, db +1.15 (all the 3 % limit allows).
- **Phoenix**: k 0.82. Blues and violets c 1.2-1.25 (saturated sky from scans), blue lightness -4, blue +5 toward violet. Reds +8, magenta +10 (Maraver direction), greens -6 and c 1.1 (yellow-green grass from scans). Tint da +0.4, db +0.3 (scans neutral or cooler).

## 4. Predicted effect on the chart [model]

Cr = C(look)/C(Standard), dh in degrees, dE76 to target. Target in parentheses.

| Patch | House Cr | House dh | Phoenix Cr | Phoenix dh |
|---|---|---|---|---|
| dark skin | 0.89 (0.87) | +4.2 (+3.4) | 0.86 (0.82) | +5.5 (+2.8) |
| light skin | 0.93 (0.87) | +4.1 (+3.8) | 0.91 (0.82) | +4.5 (0) |
| blue sky | 0.86 (0.83) | +0.9 (0) | 0.94 (1.01) | +3.8 (+2.2) |
| foliage | 0.86 | -1.9 (-2.0) | 0.86 (0.88) | -0.9 (-5.0) |
| orange | 0.86 | +0.9 (+2.2) | 0.81 | +1.6 (0) |
| purplish blue | 0.86 (0.83) | -1.4 (0) | 0.95 (0.97) | +0.9 (+5.1) |
| moderate red | 0.86 | +4.1 (+3.0) | 0.82 | +5.7 (+5.8) |
| purple | 0.83 (0.80) | -1.7 (0) | 0.89 (0.82) | -0.9 (**+7.5**) |
| yellow-green | 0.86 | -0.8 (-2.9) | 0.86 (0.90) | 0.0 (**-5.9**) |
| blue | 0.84 | -2.6 (0) | 0.95 (0.90) | +0.1 (**+6.3**) |
| green | 0.83 | -1.5 (-1.3) | 0.85 | -0.4 (-4.3) |
| red | 0.87 | +3.0 (+3.2) | 0.80 | +3.8 (+4.1) |
| yellow | 0.86 | -0.1 (-1.7) | 0.85 | +0.7 (-3.4) |
| magenta | 0.82 (0.80) | +0.5 | 0.81 (0.67) | +0.5 (**+9.7**) |
| cyan | 0.84 (0.83) | **+2.8** (0, toward blue, not teal) | 0.91 (1.00) | +6.6 (0) |
| **mean dE76, 18 patches** | **1.6** | | **4.4** | |

Greys (n8..n3.5), a*, b* at fixed WB. Standard: (-0.8..-1.5, -1.9..-0.5).
- House (model A, WB before matrix): (-0.7..-1.1, **+0.1..+0.5**): noticeably warmer than Standard, not as warm as refs.
- Phoenix (model A): (-0.2..-0.8, -1.1..-0.3), close to Standard.

## 5. What the matrix cannot do (residual)

**House:**
1. **Warmth is incomplete.** The +-3 % row limit gives db ~ +1.5 vs the needed +3..+4, about 2 b* short of refs. Without breaking the limit this can only come from WB: shift A+1..A+2 or 6000K (as in the recipe `Portrait C+1/S-1/6000K A2`), i.e. WB is the photographer's choice. Alternatively raise the limit to +-6 %: matrix with `tint=(0.5, 3.5)` gives b* ~ +2.9 with row sums +5.5 / -0.8 / -8.4 %.
2. **The Portrait tone curve works against House** [verified on v1, Portrait vs Standard chart]. Portrait shadows are lighter (n3.5 L 34 vs 33, black 21-23 vs 19-21), white darker (86 vs 88). Refs want deep black and bright white. A matrix cannot fix this. With sliders at 0 House is slightly softer than refs. To match refs exactly use Contrast +1 (as in the July recipe). Portrait c+1 curve equals Standard c0: greys 85/78/66/49/24/6 vs 85/79/67/49/24/6 [verified].
3. **Shadow and highlight chroma.** Refs have cleaner shadows (C 4.9 at L < 20 vs 8.5 for NEX) and highlights (4.2 vs 6). A matrix scales all levels equally; such suppression needs a register in the YC path, which has not been found.
4. **Portrait may add a little chroma** [verified, ambiguous]: +6 % by patch median, +2 % by mean, more than the slider steps predict. Design choice k = 1. If House on camera looks denser than refs, set House boost to 1.05.

**Phoenix:**
1. Rotating the B->M->R sector (purple, magenta, blue +-6..10 deg) and the yellow-green foliage shift are out of reach for a matrix: it rotates everything at once and skin follows (+4.5 deg where target is 0). This is exactly the conclusion of `notes/film-colorchecker-tests.md` section 7. Needs per-sector int8 tables (`notes/hue-tables.md`).
2. **Lifted blacks (0.110) with nearly colourless shadows.** That is the curve. The Sunset tone instead **deepens** blacks (n3.5 L 30 vs 33, black 14-16 vs 19-21 for Standard) [verified, v1]. With sliders at 0 Phoenix is more contrasty than scans. Closer: Contrast -1..-2, but those are no longer "correct defaults".
3. Saturated sky with low overall chroma is only partly achieved: sky 0.94, blue 0.95 at global 0.82.

## 6. Auto WB vs Daylight

- **Phoenix in Sunset** [verified on stock and v1 Sunset]: in **Auto WB** the camera shifts the WB target warm, greys get b* ~ +20, the frame turns amber-orange. That is no longer the scanned Phoenix (neutral or cool) but closer to the "warm Phoenix" of descriptions. In **Daylight / fixed WB** there is no warmth, the look is neutral-cool like the scans. Recommendation: fixed WB; Auto WB as a deliberate "sunset" variant.
- **House in Portrait**: Portrait has no AWB bias of its own (greys identical vs Standard) [verified]. In Auto WB House warmth = +1.5 b* on top of what AWB picks. In Daylight greys come out ~ +0.3 b*.

## 7. Risk: grey tint on camera may drift [hypothesis]

On v1 (one session, Custom WB) Portrait, Landscape and Sunset gave greys (-3..-5, -3..-5), Vivid gave (-1, -1), while the model predicted Standard (-1, -2) for all. Partly explained by the **"WB gain after the matrix" hypothesis**: effective transform = G.M.M0^-1.G^-1. Fitting G = (1.19, 1, 0.77) reduces grey error 3.6 -> 2.3 dE but barely helps colour patches (4.65 -> 4.35). Frame-to-frame noise in b* is +-3, so unproven.
- Not a problem for v3: both matrices are close to M0. Under the G hypothesis House gets **warmer** (b* +1.1..+1.7) and Phoenix more neutral (~0). The sign of the tint is right under either model.
- Check: shoot the chart Standard / Portrait / Sunset in one session at fixed Daylight and compare greys with section 4.

## 8. Reproduce

Pipeline of the design scripts (not included): set statistics -> sector percentiles -> style chroma boost from v1 -> fit (int16, checks, block + `looks_v3.json`) -> previews. Look targets are a SPECS table of `k`, `tint`, `cf`, `dh`; change them and refit, the script re-checks limits and the byte diff.
