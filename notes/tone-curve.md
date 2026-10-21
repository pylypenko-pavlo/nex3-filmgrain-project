# NEX-3N: still-image tone curves and the Contrast slider (static analysis + measurements)

Tags: **[verified]** = from bytes/code or matches chart measurement; **[hypothesis]**. Related: `notes/hue-tables.md`, `notes/backup-params.md`.

Scope note: this repo covers the curve data format and the measurements only. How the curves could be replaced in the camera is deliberately out of scope.

## 0. Summary

1. **Tone curves are constants in the main camera binary (`av-cam`), not in the Backup settings store.** A bank of 21 curves: 1024 x uint16 each (10-bit in -> 10-bit out), starting at file offset `0x5b006a`, stride `0x800`: curve k = `0x5b006a + 0x800*k` [verified: all monotonic; k3/k10/k20 are identity].
2. **Contrast slider -3..+3 = curves k0..k6** (k3 identity) [verified by measurement: c+3 -> k6, error 4.1 vs 15.1 for identity; c-3 -> k0/k1, 2.4-4.5 vs 6.1].
3. **The style adds its own curve:** Vivid, Landscape and Sunset -> **k14** (S-curve); Portrait -> the Contrast -2 curve (k1) [verified by measurement: error 1.2-2.8 vs 4.1-4.6 for identity; Portrait 2.0 vs 6.0].
4. **There is no tone data in Backup.** The only related item is a 96-node grid at property `0x0003007a`. It is also passed to the hardware as the breakpoints, so editing it changes only the sampling density, not the curve shape [verified by code]. **Tone cannot be changed through the settings store.**

## 1. Structure [verified by code; addresses = offsets in the 3N `av-cam` binary, load base 0xc3441000, RW data: file 0x612a54 <-> VA 0xc3c94b74]

- **LUT build function**: `0x2d6996`.
  - For each of 96 nodes `x_i` (grid from Backup `0x0003007a`, `+0x00..+0xbf`: 2,4..64 step 2, ..., 512..1023 step 64, tail 1023) it computes
    `y_i = Cstyle[ Cgroup2[ Ccontrast[ base(x_i) ] ] ]` (group order approximate, see below);
  - the result goes to the hardware structure. The grid itself is copied there too (`0x2d677e`: 96 values from 0x3007a), plus 9 segment parameters from `0x3007a+0xc0` (`2,2,3,4,4,4,4,3,3`, looks like log2 of the step per segment).
- **Base gamma** `base`: pointer table at RW `0x634668` (VA `0xc3cb6788`), index `[obj+0xbc0+0x19]*8 + [obj+0xbc0+0x16]*4`. Points to curves in the RO area `0x597dfa..0x5af0xx` (= `VA - 0xc3441000`), two per mode.
- **Pointer table for the 21 tone curves**: RW `0x634748` (VA `0xc3cb6868`), 27 slots:

  | slots | index from | curves | meaning |
  |---|---|---|---|
  | +0x00 (0..6) | `[r1+0x1b]` | k0..k6 | **Contrast -3..+3** (k3 = 1:1) |
  | +0x1c (7..13) | `[r1+0x1d]` | k7..k13 (k10 = 1:1) | "density" family: mid 417 -> 586 at q256 161 -> 349 [hypothesis: DRO or luminance correction] |
  | +0x38 (14..26) | `[obj+0xbe1]` | k14, k15, k16, k17, k18, k20, k19, k20.. | style/effect curves: **k14 = S (Vivid/Landscape/Sunset)**, k15 = stronger S (q256 177), k16 = threshold (posterisation or high-contrast mono [hypothesis]), k17 = black lifted from 64 (Soft High-key [hypothesis]), k18 = soft (q256 305, q768 692), k19 = very strong S |

  Indices are runtime-structure bytes set by the style and contrast code. They are not in Backup [not found in the 180 blocks of 0x0003].
- Curves operate in the **encoded domain** (after base gamma, 0..1023). Hence `Y'_style ~ Ck(Y'_Standard)` on a grey ramp, which is how the measurements matched.

### Curve data format (summary)

| item | value |
|---|---|
| element | uint16 little-endian, 0..1023 |
| length | 1024 entries (2 KiB) per curve |
| domain | encoded (post base gamma) 10-bit in -> 10-bit out |
| bank | 21 curves, stride 0x800 |
| identity curves | k3, k10, k20 |

## 2. Grey ramp measurements (21 steps, layout in `data/measurements/chart_layout.json`) [verified]

Y' (0..255) at source-screen steps 0, 13, ..., 255:
```
Std c0  (09419) 0 0 3 8 17 29 43 59 76 96 114 127 140 152 161 168 175 181 186 189 191
Std c-3 (09420) 0 1 5 14 26 39 52 67 82 100 115 127 138 147 155 163 169 175 179 183 186
Std c+3 (09421) 0 0 1 3 7 13 23 43 65 89 113 132 150 165 177 186 194 200 205 209 212
v5 Std  (09498) 0 0 3 8 19 33 48 65 85 105 123 138 151 165 175 183 190 195 200 204 207
Vivid   (09499) 0 0 2 6 13 24 40 59 80 103 122 138 153 167 176 184 191 197 202 206 209
Portrait(09500) 0 0 3 11 24 38 52 68 85 104 120 133 145 158 167 175 182 187 192 196 199
Landsc. (09501) 0 0 2 5 12 23 39 60 82 105 125 140 155 168 178 186 192 197 202 206 208
Sunset  (09502) 0 0 2 5 13 23 39 58 78 101 121 136 151 165 175 183 190 195 201 205 208
```
All pivot around the middle (step 128 -> Y' ~ 114). Ramp measurement: `code/measure/ramp.py` (affine fit of the 24-patch grid to the layout); raw ramp data in `data/measurements/ramps.json`.

## 3. Settings-store null test

The only Backup candidate, `0x0003007a`, feeds the hardware as both X and sample points, so editing it should have **zero** effect on the ramp; that would be the confirmation. Test (1 Standard frame, compare with 09498):
- `0x0003007a`, uint16 at `+0x00..+0x3f` (nodes 0..31, x = 2..64): replace with x/2 (1, 2, 3 ... 32). Expected from code: no change beyond noise (+-2 Y'). If shadows darken noticeably, the hardware uses its own grid and 0x3007a gives a tone trick without firmware changes.

## 4. Designing a film curve (curve domain, 0..1023 in and out)

- Reference scans: black (1st percentile Y') ~ 0.050-0.063, white (99th) ~ 0.903-0.907. NEX Standard: 0.04 / 0.92. So: **slightly lifted but clean black** and **compressed soft shoulder**, not crushed black.
- Shape: `C(x) = lo + (hi - lo) * S(x/1023)`, lo ~ 0.05*1023 ~ 50 at input 0 (keep monotonic, `C(0)` >= 40), hi ~ 0.91*1023 ~ 930, S a smooth film function:
  - toe: slope at zero ~ 0.6-0.8 (clean, not collapsed shadows);
  - mid near identity: `C(512) ~ 505-515`, density preserved, slider still works around 0;
  - shoulder: start compressing at x ~ 700, reach hi at 1023 with zero slope (soft highlights).
- Combination with the slider: if the curve replaces k0, Contrast -3 = film in any style; other contrast steps stay stock.
- Offline check: run the measured Standard ramp (09498) through the new C and compare percentiles with refs (black/white/mid): `np.interp(Y'/255*1023, 0..1023, C)`.

Designed film curve (offline, "film_k0"): black 55, white 909, soft S. Knots at inputs 0..1023 step 128: `[55, 139, 243, 362, 487, 612, 730, 832, 909]`. Full 1024-point curve: `data/curves/film_k0.json`.

## 5. Not verified

- Exact composition order of groups (contrast <-> group2 <-> style) and meaning of the k7..k13 group.
- Whether the curve applies to Y or to RGB (affects shadow saturation).
- Table "style -> slot +0x38" (k14 shared by Vivid/Landscape/Sunset per measurement; what Sunset does beyond k14 in the blacks is not separated).
