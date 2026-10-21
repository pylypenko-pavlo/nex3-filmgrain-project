# NEX-3N: hue/saturation tables in Backup property 0x00030001 (int8, 24-byte records)

Status: decoded from two chart experiments. Camera: NEX-3N fw 1.00. The block is mirrored in `0x00030008` (second bank) — always write both identically.

## Verified

- Style record: `+0x100 + 24*r`, r = style slot (0 Standard, 1 Vivid, 2 Portrait, 3 Landscape, 4 Sunset; slot 4 carries the marker `80 80 80 80`). Same slot order as the matrices (`+0x48 + 18*r`).
- A record = 6 "quads" of 4 int8 each: `Qk` at `+0x100 + 24*r + 4*k`.
- **Bytes inside a quad = 4 hue regions** (byte test, one session, frames DSC09478-81 vs base DSC09483-86):

  | byte j | region (Lab hue of the chart patch) | Q0, per +1 unit |
  |---|---|---|
  | 0 | reds, skin, magentas (~335..60 deg) | -0.25 deg/unit (red -35 deg at +134) |
  | 1 | oranges, yellows, yellow-greens (~60..140 deg) | +0.20 deg/unit (+18..+29 deg at +138) |
  | 2 | blue-greens, cyans, sky (~170..250 deg) | -0.39 deg/unit (-15..-37 deg at +94) |
  | 3 | blues, violets, purples (~250..335 deg) | +0.13 deg/unit (+9..+22 deg at +128) |

  Rotation sign alternates between neighbouring regions: a positive value pulls reds and cyans clockwise, yellows and blues counter-clockwise (in Lab hue angle).
- **Q0 = hue rotation** (verified).
- **Q1 = per-region saturation** (strong hypothesis, nearly verified): Vivid with Q1 zeroed (was -40/-29/-16/-40) gains chroma in proportion to |original|: reds +18, yellows +13, cyans +2..+9, blues +22. Negative = muting.
- Standard binary test (Q0, Q2, Q4 zeroed) fits the model "Q0, Q2, Q4 are all hue rotation with the same gain": predicted cyans -40 deg (measured -35), reds -11.5 (measured -6..-8), yellows +2 (measured +2..+4), blues +2 (measured ~0).

## Hypotheses

- **H4 (rejected by the band test below):** record = 3 bands x (hue, saturation) x 4 regions: (Q0 hue, Q1 sat), (Q2 hue, Q3 sat), (Q4 hue, Q5 sat), bands possibly by luminance or chroma. Argument: Q0/Q2/Q4 are large and hue-like (cyan byte -38..-46 in all three), Q3/Q5 small like saturation trims.
- Against full additivity: Q2 alone (Vivid) and Q4 alone (Landscape) move cyans only -6..-9 deg, but together with Q0 in Standard -35 deg. Consistent either with chart patches falling into different bands or with interpolation between bands.
- Consumer in the main camera binary (CC module, `Create3DLUT` 0x3d03c4..0x3d08d4) only receives a pointer to the whole block (`msg[0]` = 0xc3ac2b94); code reading `+0x100..` specifically was not found. The 5x9x9 LUT is apparently built from the matrix plus these records.
- Cross-session noise: +-3 dC, +-5 deg dh (controls Portrait 09475/09485, Sunset 09477/09487). Sunset under Auto WB is noisier in yellows (-11..-13 dC).

## Band test (performed)

Goal: confirm Q1 = saturation and find the axis of Q3/Q5/Q2. All changes in the yellow and red regions, where the chart has patches of varying lightness (yellows: foliage L~40 -> yellow-green L~70 -> yellow L~80; reds: dark skin ~38, red ~42, moderate red ~52, light skin ~66).

| frame | slot | offset | was (v3) | set to | expectation |
|---|---|---|---|---|---|
| 1 | Standard r0 | `+0x105` (Q1 byte1) | -36 (`dc`) | +90 (`5a`) | yellows dC +20..+30, dh ~0 -> Q1 = yellow saturation |
| 2 | Vivid r1 | `+0x125` (Q3 byte1) | -9 (`f7`) | +110 (`6e`) | if Q3 = band-2 saturation: dC rises only for some yellows (by L) |
| 3 | Portrait r2 | `+0x145` (Q5 byte1) | -17 (`ef`) | +110 (`6e`) | same for band 3 |
| 4 | Landscape r3 | `+0x150` (Q2 byte0) | -6 (`fa`) | +120 (`78`) | if Q2 = band-2 hue: reds rotate ~-30 deg, not uniformly in L |

Written identically to `0x00030001` and `0x00030008`; all other bytes from the v3 looks. Reverted to v3 afterwards.

### Results (DSC09488-91 vs base 09483-86; Sunset control 09487 -> 09492: noise dC +-8, dh +-5 deg) [verified]

| frame | change | response |
|---|---|---|
| 09488 Standard | Q1 byte1 `+0x105` -36 -> +90 | yellows/greens/oranges/skin dC +12..+34, L +5..+10; **reds rotate +14..+33 deg** (leakage) |
| 09489 Vivid | Q3 byte1 `+0x125` -9 -> +110 | almost like Q1: dC +16..+25, same red rotation, L +3..+8 |
| 09490 Portrait | Q5 byte1 `+0x145` -17 -> +110 | weak: yellows and greens dC +7..+8 |
| 09491 Landscape | Q2 byte0 `+0x150` -6 -> +120 | reds and dark skin dh -28..-34 deg, light skin -17, magenta dC +22, dh -13: **same as Q0 byte0** |

- Response is the same on patches with L 24..75, so **bands are not by luminance**. H4 "3 luminance bands" is rejected.
- (Q0, Q1) ~ (Q2, Q3) = (hue, "saturation"). Pair (Q4, Q5) acts weaker; by what criterion is unknown (candidates: LutMode CAP/MOV/MON, or a chroma band).
- Q1/Q3 "saturation" is not pure: byte1 raises chroma in 60..140 deg and also rotates reds and skin toward orange. Possibly Q0/Q1 are two components of an ab-plane offset per region rather than (h, C) [hypothesis].
- Q0 and Q2 corrections add (Standard binary test matched the sum), and Q2 alone gives the same response as Q0 per unit. So in v4 the required shift is **split half/half between Q0 and Q2** (and Q1/Q3): same total effect, each byte further from the int8 limit, and if the pairs turn out to serve different paths (e.g. still vs live view), the still image still gets at least half the effect.

## How to design a look with these tables

- Use slots 1-4 only (keep Standard slot 0 as reference).
- **Blues -> cyan (Kodak-like):** rotate region 3 toward cyan: byte 3 in Q0/Q2/Q4 more negative (~ -40..-60, i.e. -5..-8 deg); keep Q1 byte 3 at -40 (don't oversaturate).
- **Reds/magentas -> orange (Phoenix-like convergence):** byte 0 in Q0/Q2/Q4 more negative (-0.25 deg/unit -> -15 deg needs ~ -60 relative to current); magentas partly in region 3 (byte 3 Q0 slightly more negative). Hue convergence = rotation toward a common centre: reds and yellows toward each other (byte 0 toward orange, byte 1 more negative so yellows go toward orange).
- **Anti-teal (House look):** don't pull cyans and greens toward blue-green. Rotate region 2 toward sky/blue without green (byte 2 of Q0 closer to 0 or positive), region-2 saturation (Q1 byte 2) ~ -30..-40; yellow-greens (byte 1) slightly toward yellow (Q0 byte 1 more negative) for warmer foliage.
- Per-region saturation lives in Q1; for "muted but clean" colour Q1 ~ -40..-50 on all regions, skin (byte 0) -30.
- Suppressing colour in shadows/highlights **cannot be done with these tables** (response does not depend on L 24..75). Another mechanism is needed (not found).

## v4: tables for slots 1-4 [model, not shot on camera]

Data: `data/looks/looks_v4_tables.json` (units, old and new quads, per-patch prediction). Differences from v3 are only in `0x118..0x16b` (54 bytes); matrices and the Standard r0 record untouched.

**Model.** Per-unit response for each chart patch taken directly from frames:
- hue: byte test Q0 b0..b3 (09478-81);
- region-1 "saturation": 09488;
- regions 0, 2, 3 saturation synthesised: same relative chroma gain 0.32 %/unit, with region weights from the byte test, hue leakage = 0 [hypothesis].

Target = film residual after matrix and tone:
- Portra 400 and UltraMax 400: recomputed from Maraver chart data (two-stage fit, `recipe2.py`; per-patch dh and Cr);
- House: targets from `notes/house-phoenix-looks.md` section 4, plus anti-teal (cyan and blue-green +5 deg toward blue), muted foliage (Cr 0.93), warmer skin (+3 deg);
- Phoenix II: same note section 4 (target minus matrix prediction).

Solver: ridge least squares, total at most +-60 units per byte-region, each byte within [-100, 100]. Q4/Q5 left as in v3.

| slot | look | Q0 | Q1 | Q2 | Q3 |
|---|---|---|---|---|---|
| 1 Vivid `+0x118` | Portra 400 | -31 -35 -14 -48 | -32 -35 -13 -57 | 1 16 -54 2 | 13 -14 4 -18 |
| 2 Portrait `+0x130` | House | -52 -37 0 -14 | -34 -24 -21 -30 | -12 11 -43 14 | 4 -14 -4 -4 |
| 3 Landscape `+0x148` | UltraMax 400 | -28 -27 -8 -36 | -31 -29 -20 -47 | -3 17 -48 21 | 13 -14 -7 -18 |
| 4 Sunset `+0x160` | Phoenix II | -48 -38 -9 -6 | **-128 x4 (untouched)** | -2 2 -29 35 | 0 0 0 0 (untouched) |

**Predicted on the chart** (dh deg / dC vs v3 of the same style):
- Portra 400: blue flower -7/-3, purplish blue -3/-6, magenta -4/-2, cyan +5/-2, blue-green +3, moderate red -3/+2. Sky and skin nearly unchanged.
- UltraMax 400: purplish blue -1/-4, blue flower -3/-3, cyan +2/-3, foliage and yellow-green +1.5 deg.
- House: cyan +5 (from teal toward blue), sky +2, dark skin +1, greens dC -1.5..-2, magenta dC -1.6.
- Phoenix II: cyan -7, blue-green -4, yellow-green and foliage -3.5 deg (toward yellow) with dC -3..-7, blue flower +7, magenta +4, purple +3, skin -3.

**Honest scale.** Post-matrix residuals for Portra and UltraMax are small and patchy (foliage -11 deg while yellow-green +2 deg in the same region). Table regions only cover their mean, so most predictions are within chart noise (+-5 deg, +-8 dC). Visible effects are expected for Phoenix (cyan/greens/blues) and Portra blues.

**Sunset r4.** In v3, Q1 = `80 80 80 80` (-128), Q3 = Q5 = 0, yet Sunset is **not** desaturated (chroma higher than Standard), so -128 is more likely a flag "don't apply saturation from this record" or a special mode than a minimum [hypothesis]. Q1/Q3/Q5 untouched in v4; Phoenix gets only hue rotation in Q0/Q2. Whether Sunset honours its record at all is **untested**. One-frame check: set `+0x160` (Q0 byte0 r4) = +100, shoot Sunset at fixed WB; reds should move ~ -30 deg. If not, r4 is ignored and Phoenix must be done via the matrix or moved to another slot.

**v4 verification plan:** 4 frames (Vivid, Portrait, Landscape, Sunset), Daylight WB, same position, compared against base 09484-87. Watch purplish blue, blue flower and cyan (Portra), cyan and yellow-green (Phoenix).
