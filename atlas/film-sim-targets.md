# Film-simulation targets → our colour stack (2026-10-12)

Mapping Fujifilm film simulations onto the NEX-3N colour levers we control, from TWO sources:
- **Measured** — the `friimaind/film-simulations-comparator` corpus (3 scenes × 20 sims, pixel-aligned
  JPEGs; cloned to `~/nex3n-dump/work/filmsim_cmp/`). Each sim measured as a **Provia→sim** transform
  (same scene, pixel-aligned): mean RGB shift, saturation ratio, per-channel gain, and a full
  **3D LUT** (built `classic-neg_from_provia.cube`, 17³, from 3 scenes; same script does any sim).
- **Qualitative** — imaging-resource "ultimate guide to Fuji's Film Simulations" (per-sim character +
  their colour-plots; Cloudflare-gated, read via headless browser). Plus Fuji's official "World of Film
  Simulation" episode stories (one per sim) linked from the guide.

## Our levers (colour half already SOLVED, E-0067/Q-7)
- **Colour matrix** (per style slot, Backup `0x30001`/`0x30008 +0x48+18*slot`) — global hue/sat.
- **Tone curve k0..k6** (p3 av-cam `0x5b006a`; debug `0x3007a`) — contrast / shadow-highlight shape.
- **Chroma-by-luminance 3D LUT** (CAP 3D-LUT, Backup `0x00030004/5`, 5 Y × 9 Cb × 9 Cr; byte `0x3F4`,
  node = plane*405 + Ynode*81 + Cb*9 + Cr) — **per-luma hue/sat shifts** (the complex part; proven on
  camera, E-0067).
- Saturation slider (×(1+0.13·s)); WB.

## Target table (measured sat/shift + guide character → levers)
| sim | measured (Provia→sim) | character (guide) | our levers | complexity |
|---|---|---|---|---|
| **Velvia** | sat **1.11×**, darker, gain>1 | highly saturated + contrasty; landscapes | sat↑ + tone (contrast↑) | GLOBAL (easy) |
| **Astia** | ~sat↑, soft | flat highlights, fast shadow drop, gentle skin | tone (flatten highlights) + mild sat | GLOBAL |
| **Classic Chrome** | sat **0.69×**, muted | lowest sat, harder shadows/softer highlights, Kodachrome hue shifts | sat↓ + tone (split) + **chroma-by-luma** | COMPLEX |
| **Pro Neg Std** | (muted) | very low contrast, muted (studio NS160) | tone (low contrast) + sat↓ | GLOBAL |
| **Pro Neg Hi** | (muted, more contrast) | like Std, more contrast + sat | tone (contrast↑) + mild sat↓ | GLOBAL |
| **Classic Neg** ★ | sat **0.65×**; **split-tone** (shadows cool-green `32→[24.8,28.9,26.2]`, highlights warm `192→[221,212,211]`) | low sat + HIGH contrast, slightly red-tinted, **"tone curve varies more between colours than any other"**, SUPERIA 100 | sat↓ + tone (contrast↑) + **chroma-by-luma (split-tone)** | COMPLEX — flagship |
| **Eterna** | sat **0.75×**, lifted/flat (gain~0.91) | desaturated, very low contrast (cine) | tone (flat, lifted) + sat↓ | GLOBAL |
| **Eterna BB** | (sat↓↓, contrast↑) | much lower sat, higher contrast, crushed shadows, gritty | tone (crush shadows, contrast↑) + sat↓ | GLOBAL |
| **Nostalgic Neg** | sat **1.27×**, warm (+R−B) | warm nostalgic | sat↑ + WB warm + chroma-by-luma | COMPLEX |
| **Reala Ace** | ~neutral (sat 1.04×) | balanced natural | ≈ base | GLOBAL |

★ = recommended flagship. **Classic Neg** is the perfect showcase: its defining trait — the tone curve
varying per colour / cool-shadow-warm-highlight split-tone — IS exactly our chroma-by-luminance lever
(the one thing simple sat/tone presets can't do and we proved works). It's also the trendy "X100 look".

## How to bake a sim onto the NEX-3N (recipe)
1. Pick a target; build its measured `*_from_provia.cube` (script in `/tmp/filmsim_an/buildlut.py`,
   change `SIM=`). The LUT is the relative grade Provia→sim.
2. Decompose it into our levers: luma mapping → **tone k-params**; global sat → **saturation/matrix**;
   per-luma hue/sat (split-tone, per-colour) → **chroma-by-luma 3D LUT** (fit the LUT's chroma shift at
   the 5 Y nodes into the 5×9×9 geometry).
3. Caveat: the measured grade is Provia→sim; our base (v5+k0) ≠ Provia, so it transfers the CHARACTER,
   not pixel-exact. Fine-tune on camera against the comparator/reference (grey-wedge via `ramp.py` +
   eyeball the comparator).
4. GLOBAL sims = tone+sat only (quick). COMPLEX sims = add the chroma-by-luma LUT.

## Note on grain (ties to the DSP work)
The guide's ACROS-grain section states the thesis plainly: **film grain ≠ digital noise** (different
structure) — which is exactly why we inject structured grain at the DSP (`sa_yknr`) rather than leave
sensor noise. Clean colour base (above) + injected grain = the full "film-for-the-poor" recipe.

## Real 35mm film stocks (parvec "Film Recipes 1" — analysis, 2026-10-12)
Owner downloaded parvec's FREE Lightroom preset pack (13 real emulsions); parsed the `.xmp`
(local only — the raw preset numbers are the creator's IP, NOT committed; only our derived mapping is).
Source: parvec.es 35mm color science project. Films: Portra 160/400, Ektar 100, Gold 200, Color Plus
200, Ultramax 400, Cinestill 50D, Candido 800T, Lomography Color 400, LomoChrome 92' 400, Phoenix 200,
Fujifilm 200, Film One Hundred 100.

**Where the "film look" lives (dominant across all 13):**
- Basic tone (Contrast/Highlights/Shadows/Whites/Blacks) = **untouched**. Character is NOT global contrast.
- **Per-colour desaturation (HSL Sat)** — every film pulls greens/yellows/magentas negative (e.g. Portra
  400 Red−35/Magenta−32; Ektar greens/aquas/blues ~−25; LomoChrome magenta−71). → our chroma-by-luma
  LUT's per-hue Cb/Cr scaling + the saturation lever.
- **Split-toning + colour-grade (tonal tints)** — the colour cast per tonal range: Candido 800T cool-blue
  shadows (hue 196); Gold 200 warm shadows (56) + cool highlights (187); Cinestill 50D red highlights
  (359, halation-ish); Portra subtle; Phoenix strong warm highlights (59/52). Midtone-hue: warm (Fuji 49,
  Phoenix 64, ColorPlus 52, Ektar 36) or cyan (Portra 160 =140, Cinestill 153, Gold 184). → **this is
  exactly our chroma-by-LUMINANCE lever** (shadow tint at low Y, highlight tint at high Y, midtone at mid
  Y) — the thing generic sat/tone presets can't do and we PROVED works (E-0067).
- A **custom RGB tone curve** per film → our tone k-params.

**Takeaway:** the real-film recipes decompose onto our stack as {per-hue sat → chroma-by-luma + sat;
tonal tints (split-tone/grade) → chroma-by-LUMA; tone curve → tone k}. Confirms our unique lever
(chroma-by-luminance) is the correct and necessary tool for an authentic film look — not a nice-to-have.
Combined with the Fuji-sim measured LUTs, we now have a numeric target library covering BOTH Fuji
simulations and real 35mm stocks. Raw parsed data kept locally (`/tmp/parvec.json`, `~/Downloads/Film
recipes PARVEC Pack 1/`); re-parse with `/tmp/parse_parvec.py`.
