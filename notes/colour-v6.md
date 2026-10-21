# NEX-3N: colour v6 (matrices and hue tables for slots 1-4)

Pure colour design done offline with the simulator (`code/sim/`). The camera was not touched for this step. Related: `notes/simulator.md`, `notes/hue-tables.md`, `notes/house-phoenix-looks.md`, `notes/film-colorchecker-tests.md`.

Tags: **[measured]** = camera frames (chart sessions v3/v4/v5, Daylight WB); **[model]** = simulator prediction; **[hypothesis]** = too little data.

## 0. Summary

- **Block:** property `0x00030001`, 1536 bytes, same format as v5. Differs from v5 in **79 bytes**, all inside the slot 1-4 matrices (`0x5a..0xa1`) and records r1-r4 (`0x118..0x16b`). Slot 0 (matrix `+0x48`, record `+0x100`) and every other byte are identical to v5. The design script checks itself: row sums within +-3 %, det > 0, table bytes fit int8. Designed values: `data/looks/v6_design_report.json`.
- **Comparison sheets** (not included): per row three frames, v5 | v6 | scan reference. In the Portra row v5 is a real camera JPEG; in other rows v5 is simulated.
- **Design scripts (not included)** ran in this order: `calib -> chart_eval -> scene -> design -> phoenix -> assemble -> verify_chart -> scene_v6 -> sheets`.
- **Step size.** Every change is half a step toward target, capped at 6 deg and 10 % chroma per patch, and at 8 units per table byte (final max 5). Differences are visible only side by side. Deliberate, see section 1 on camera gain.

| slot | look | main v5 mismatch [measured] | what v6 does [model] |
|---|---|---|---|
| 1 Vivid | Portra 400 | skin/orange/orange-yellow ~0 deg instead of +14..+23 deg (Maraver) and +5 deg (reference scans); cyan -12 deg vs target -5 deg | skin/orange +4..+6 deg toward yellow, cyan +3 deg, chroma -4..-9 % on reds and blues |
| 2 Portrait | House | warm colours not muted: skin/reds Cr ~1.00 vs target 0.87; on scenes chroma = Standard, refs are -9..-16 % | skin/reds -5..-8 % chroma, magenta -4 deg, yellows/foliage +1..+3 deg away from yellow |
| 3 Landscape | UltraMax 400 | skin **-12 deg** (toward red), orange -8 deg, orange-yellow -7 deg; Maraver says +6..+12 deg | skin/orange/orange-yellow +5..+7 deg, magenta -3 deg |
| 4 Sunset | Phoenix II | on scenes chroma ~ Standard (0.94-0.97), scans 0.77-0.85; yellow 0.74 (collapse after v4) | matrix only: chroma -6..-11 % without losing sky, greys -1.2 b* (cooler); yellow region half-reverted toward v3 |

## 1. Calibration: how much stronger the camera reacts than the simulator [measured]

Matrices in v3, v4 and v5 are identical, so the chart difference v3->v4 and v3->v5 is the pure response to the tables. Session drift was removed using the Standard frame of the same session. Compared with the simulator's prediction on the same patches.

| region | slope camera/simulator for dh | corr. | for dC |
|---|---|---|---|
| reds/skin | 0.97 | 0.82 | 0.56 |
| yellows/greens | 1.47 | 0.63 | unreliable (drift) |
| cyans/sky | 1.35 | 0.99 | 1.41 |
| blues/violet | **1.78** | 0.86 | 1.34 |

- Slots 1-3: the simulator gets the direction right (corr. 0.73-0.93) but the camera responds up to 1.8x stronger. That explains the v4 overshoot. In the v6 design the table response is multiplied by these factors.
- **Slot 4 (Sunset): the simulator does not predict the table response.** Correlation with camera -0.54 (v4) and -0.19 (v5). For v5 it promised cyan +17.5 deg, the camera gave +3.4 deg. So in Sunset record r4 works differently from the `code/sim/hue.py` model (probably because of the -128 marker in Q1) [hypothesis]. Therefore Phoenix in v6 is changed **by matrix only**: the Sunset matrix was verified on RAW+JPEG pairs.
- **Chart noise** [measured]. Repeat of Standard (two consecutive frames): mean |dh| 1.9 deg (p90 4.7 deg), |dC| 4.7 (p90 10.5). Cross-session control: House tables are identical in v4 and v5, yet yellow and green differed between sessions by -12..-15 chroma. Conclusion: **the "UltraMax yellows/greens -16..-26 chroma" reading in the v5 report is mostly session drift, not a table effect.**

## 2. Where v5 stands (chart, estimate from three sessions) [measured + model]

v5 estimate per patch = mean of three sessions (v3, v4, v5). v3 and v4 readings are translated to v5 via the simulator with section 1 factors; spread between sessions 0.3-5 deg. Phoenix uses only the v5 session. Targets:
- Portra and UltraMax: Maraver per patch. For chroma only the per-patch pattern is compared, not the overall level (Maraver's level is set by a 10/90 % stretch).
- House and Phoenix: targets from `notes/house-phoenix-looks.md` section 4.

Everything is relative to Standard from the same session.

| look | rms dh to target, v5 | rms Cr error, v5 | median Cr (look/Std) |
|---|---|---|---|
| Portra 400 | 10.0 deg | 0.22 (pattern) | 0.95 |
| House | 4.1 deg | 0.08 | 0.90 (target 0.87) |
| UltraMax 400 | 10.7 deg | 0.21 (pattern) | 1.02 |
| Phoenix II | 3.6 deg | 0.12 | 0.91 (target 0.82) |

Largest mismatches are in the section 0 table. Also:
- House moderate red +12 deg vs target +3 deg;
- UltraMax cyan -18 deg vs target -12 deg.

**Scenes.** 19 frames (live test frames from the v5 session plus a set of July frames), each run JPEG->JPEG with sliders at 0 and compared with scans using the metric from house-phoenix section 1.
- **These frames contain almost no sky or blues** (blue sector 0-1 % of pixels). Sky, blues and Phoenix's violet sky are checked **on the chart only**.
- Chroma ratio to Standard (p50/75/90): refs/Std 0.88/0.91/0.84, House v5 1.03/1.01/1.02. Phoenix scans 0.84/0.85/0.77, Phoenix v5 0.97/0.94/0.97. Portra scans 0.94/0.94/0.84, Portra v5 1.03/1.01/1.05. Subjects differ, so absolute values are guidance, not targets.
- Skin sector hue angle: Portra scans 61 deg, Standard 56 deg, Portra v5 57 deg (confirms Maraver's sign). UltraMax v5 53 deg: skin drifts toward red.
- Greens: refs 122 deg, House 114 deg, Standard 117 deg. House greens are yellower than refs, so v6 stopped pulling foliage toward yellow.

## 3. What changed in v6

Method (design script):
- Step target = half the distance from the v5 estimate to target, capped at +-6 deg and +-10 %.
- Solved by bounded ridge least squares. Skin weighted x3, Portra moderate red x2.5.
- Parameters:
  - matrix: 6 degrees of freedom **preserving v5 row sums** (greys do not move);
  - table: one "rotation" and one "saturation" per region. Each unit is added equally to Q0 and Q2 (rotation) or Q1 and Q3 (saturation), as in v4/v5. Q4/Q5 untouched.

| slot | matrix v5 -> v6 (1.0 = 1024) | row sums | Q0..Q3, delta vs v5 per region (red/yellow/cyan/blue) |
|---|---|---|---|
| 1 Portra | `1061,99,-136 / 75,1241,-292 / 9,45,970` -> `1068,110,-154 / 96,1239,-311 / 51,25,948` | 1024 x3 (as v5) | Q0,Q2: -3 +3 -2 -1; Q1,Q3: -4 +2 -4 -2 |
| 2 House | `1117,-3,-73 / 9,1216,-203 / -16,-11,1022` -> `1116,-4,-71 / 19,1222,-219 / 13,-10,992` | 1041/1022/995 (as v5) | Q0,Q2: +2 +1 -2 0; Q1,Q3: -4 0 0 -1 |
| 3 UltraMax | `1391,-79,-288 / 28,1270,-274 / 31,-40,1033` -> `1350,-57,-269 / 45,1258,-279 / 34,-56,1046` | 1024 x3 (as v5) | Q0,Q2: 0 +2 -3 -3; Q1,Q3: -5 +3 +1 -1 |
| 4 Phoenix | `1082,47,-92 / 102,1150,-232 / 54,74,890` -> `1035,94,-94 / 114,1131,-225 / 70,122,842` | 1035/1020/1034 (+1.1/-0.4/+1.0 %) | Q0b1 -38->-33, Q2b1 2->7; rest as v5 |

- **Phoenix:** M6 = D . S(0.94) . M5. S(k) = desaturation preserving grey and luminance, D = diag(1, 1, 1.015) = cooling. Greys: b* -1.2, a* +0.1 [model]. Chroma of warms and greens -6..-11 %, sky and blue -0..-3 %. So the relative saturation of the sky rises, as in the scans.
- **Half-revert of the Phoenix yellow region** [hypothesis, from measurement]. In v4/v5 byte 1 in Q0/Q2 was moved by -10 to push foliage "toward yellow". In both sessions the camera instead gave foliage +2..+3 deg and yellow chroma -15. Target missed, yellow collapsed to Cr 0.74. +5 on each byte returns half the step toward v3, where yellow was ~0.95. Effect estimated only from those two measurements: the simulator does not work for Sunset.
- **Compared with v4.** Largest table change in v6 is 5 units per byte. v4 had up to 34.

**Byte diff v5 -> v6** (offset: old->new):
`0x05a 25->2c; 0x05c 63->6e; 0x05e 78->66; 0x060 4b->60; 0x062 d9->d7; 0x064 dc->c9; 0x066 09->33; 0x068 2d->19; 0x06a ca->b4;` (slot 1 matrix)
`0x06c 5d->5c; 0x06e fd->fc; 0x070 b7->b9; 0x072 09->13; 0x074 c0->c6; 0x076 35->25; 0x078 f0->0d; 0x079 ff->00; 0x07a f5->f6;` (slot 2)
`0x07c fe->e0; 0x07e 6f->46; 0x080 b1->c7; 0x082 e0->f3; 0x084 1c->2d; 0x086 f6->ea; 0x088 ee->e9; 0x08a 1f->22; 0x08c d8->c8;` (slot 3)
`0x08e 09->16; 0x090 3a->0b; 0x092 2f->5e; 0x094 a4->a2; 0x096 66->72; 0x098 7e->6b; 0x09a 18->1f; 0x09c 36->46; 0x09e 4a->7a; 0x0a0 7a->4a;` (slot 4)
`0x118 df->dc; 0x119 db->de; 0x11a f9->f7; 0x11b de->dd; 0x11c da->d6; 0x11d e1->e3; 0x11e f1->ed; 0x11f d3->d1; 0x120 ff->fc; 0x121 0d->10; 0x122 d1->cf; 0x123 10->0f; 0x124 07->03; 0x125 f6->f8; 0x126 01->fd; 0x127 fa->f8;` (r1)
`0x130 cc->ce; 0x131 db->dc; 0x132 00->fe; 0x134 de->da; 0x137 e2->e1; 0x138 f4->f6; 0x139 0b->0c; 0x13a d5->d3; 0x13c 04->00; 0x13f fc->fb;` (r2)
`0x149 e2->e4; 0x14a fa->f7; 0x14b e0->dd; 0x14c dc->d7; 0x14d e4->e7; 0x14e f0->f1; 0x14f d9->d8; 0x151 0e->10; 0x152 d2->cf; 0x153 18->15; 0x154 08->03; 0x155 f3->f6; 0x156 fc->fd; 0x157 f6->f5;` (r3)
`0x161 da->df; 0x169 02->07` (r4)

Written to the camera the same way as v5: both banks, `0x00030001` and `0x00030008` (see `notes/backup-params.md`).

## 4. v6 prediction [model, slots 1-3 corrected by section 1]

| look | rms dh to target | Cr error | median Cr | scenes, chroma/Std p50/75/90 |
|---|---|---|---|---|
| Portra | 10.0 -> **8.0 deg** | 0.22 -> 0.21 | 0.95 -> 0.92 | 1.03/1.01/1.05 -> 1.03/1.01/1.01 |
| House | 4.1 -> **3.1 deg** | 0.077 -> **0.045** | 0.90 -> 0.87 | 1.03/1.01/1.02 -> 0.99/0.96/0.95 |
| UltraMax | 10.7 -> **7.9 deg** | 0.21 -> 0.18 | 1.02 -> 1.00 | 1.06/1.05/1.13 -> 1.07/1.05/1.09 |
| Phoenix | ~ unchanged in dh (matrix only: -1.7..+2.4 deg) | 0.12 -> 0.10 | 0.91 -> 0.85 | 0.97/0.94/0.97 -> 0.88/0.87/0.89 |

For Phoenix the chart verification reports rms 4.6 deg. Not to be trusted: it includes the simulator's r4 table prediction, which is wrong for Sunset (section 1).

## 5. Honest assessment: what is within noise and what to verify on camera

Simulator noise ~2.6 dE residual on chroma. Chart noise: +-2..5 deg hue, +-5..10 chroma (up to 15 across sessions).

- **Above noise, expect a visible effect:**
  - UltraMax: skin, orange, orange-yellow +5..+7 deg;
  - Portra: skin, orange, orange-yellow +4..+6 deg;
  - Phoenix: overall chroma -9..-11 % on warms. This is the matrix, which is modelled reliably.
- **At the noise edge** (a single chart frame will not show them):
  - House: skin/red chroma -5..-8 %, magenta -4 deg;
  - Portra: cyan +3 deg;
  - UltraMax: magenta -3 deg;
  - Phoenix grey tint -1.2 b*.
- **Within noise, direction only:** all corrections <= 2 deg and <= 4 % (House and UltraMax yellows/greens, Portra and UltraMax blues).
- **Not verified at all:**
  - Sunset response to reverting r4 byte 1: hypothesis from two measurements, the simulator is useless here;
  - strength of table response in the red region: slope 0.97 with large scatter. For moderate red the camera gave 2-5x the prediction in v4. If Portra reds shift visibly toward orange, revert `rot r0` first (byte 0 in Q0/Q2: `0x118`, `0x120`).
- **How to verify.** Chart in Standard + 4 styles under Daylight in one session right after writing; then a second session with the same frames (noise). Compare against the v5 session via the chart evaluation. Prefer **RAW+JPEG**: the pair reduces monitor/lighting noise.
  - A "before" frame on v5 in the same session removes cross-session drift. Best order: v5 -> frames -> write v6 -> frames.

## 6. Next (not done)

- **Phoenix violet sky is unsolved.** Sky on the chart +4.8 deg vs +26 deg in scans (different subjects though). The matrix rotates sky only together with skin. Table r4 in Sunset does not follow the model. Needs a single-byte experiment on r4: Q0 byte 3 = +40, a Daylight frame next to the base. It will show how Sunset responds in the blue region.
- **Portra: overall scene chroma stayed ~ Standard**, scans are -6..-16 %. Subjects do not match, so untouched. If Portra on camera looks denser than scans, apply a global S(0.95) in the slot 1 matrix.
- Sky and blues verified only on the chart: preview frames contain no sky. Need 2-3 outdoor frames with sky in every style.
