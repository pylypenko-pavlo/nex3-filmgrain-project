# Fuji film simulation mechanics and what transfers to the NEX-3N

Research, 2026-10-04. Goal: understand **which operations a Fuji film simulation consists of**, and estimate what can be reproduced with the NEX-3N (CXD4132 BIONZ) controls. Background for the settings-store work. Target look: warm neutral, muted-clean colour, soft contrast, deep clean black, bright white, **no teal and no oversaturation**.

Source labels:
- **[Fuji]** official Fujifilm text, documented;
- **[measured]** numerical measurement of 3D LUTs (section 2), reproducible;
- **[community]** enthusiast opinion or empirics;
- **[not found]** searched, no public data.

---

## 0. Summary

1. **A Fuji simulation is not a "filter" but five layers.** (a) a tone curve on the neutral axis; (b) a global chroma cut or boost; (c) luminance-dependent chroma: shadows and highlights are cleaned more than the midtones; (d) per-hue hue and chroma shifts; (e) for Classic Neg and Nostalgic Neg, also a luminance-dependent neutral tint: greenish shadows, warm middle. On top: Color Chrome Effect / FX Blue (darkening of saturated colours) and DR (underexposure plus shadow lift).
2. **The neutral axis of "ordinary" simulations is neutral.** Provia, Astia, Classic Chrome, Pro Neg and Eterna keep grey grey: |a*|,|b*| <= 0.3 across the scale [measured]. The "Kodak Gold" warmth in Fuji recipes comes from a **WB shift**, not the simulation. Example: Kodak Gold on Classic Chrome uses WB Daylight **+4 R / -5 B** [community, fujixweekly]. This layer already exists on the Sony: A-B / G-M shift.
3. **The single largest contributor is one knob: global chroma.** Classic Chrome vs Provia = **x0.76**, Eterna x0.78, Pro Neg Std x0.88, Pro Neg Hi x0.95. One chroma multiplication closes **55-60 %** of the CC<->Provia difference: mean dE 10.8 -> 4.7 [measured]. That is exactly global saturation or a per-style chroma gain.
4. **Second by weight: chroma vs luminance.** CC chroma in shadows L*<10 is x0.49, midtones x0.83-0.85, highlights x0.70 [measured]. Hence "clean blacks and clean whites without colour mud". A saturation +/-3 knob cannot do this. It needs a shadow/highlight chroma-suppression register in the YC path, if one exists, or an ISO/luminance ladder.
5. **Tone curve.** The detail that reads as "deep black": CC and Pro Neg Hi have deeper shadows than Provia. At 1 % reflectance L* = 2.8 and 2.4 vs 4.7 for Provia; at 0.25 %, 0.3 and 0.1 vs 1.3. Midtones and highlights almost the same or slightly brighter [measured]. Fuji says of CC: "hard shadows, highlights keep a soft gradation" [Fuji]. A symmetric contrast knob +/-3 only approximates this.
6. **Per-hue shifts add only ~1 dE on average**, but are visible in two places: sky and foliage. CC moves sky **toward cyan** (-12...-18 deg in blues) [measured]; Fuji says "removed the magenta component from the sky" [Fuji]. Classic Neg moves foliage **+20...+40 deg toward teal** [measured]. **For a "no teal" target these are exactly the shifts not wanted**, so per-hue tables can be skipped.
7. **Numerically the target is closest to Pro Neg Hi with Classic Chrome's tone.** Nearly uniform chroma (x0.9-0.95), deep shadows, shadow chroma x0.49, bright highlights, hue shifts within +/-5 deg. That is mostly **curve + one saturation + chroma-vs-luminance + WB**: three or four knobs, no 3D LUT. Classic Chrome's sky and Classic Neg's foliage would need per-hue tables, and those are not wanted.
8. **Fuji firmware: no public data on how simulation parameters are stored** [not found]. All known emulations (Adobe, abpy, darktable solver, RawTherapee) are **black box**: shoot a chart RAW+JPEG and fit. Nobody has reversed Fuji code.

---

## 1. What Fujifilm documents (officially)

| Simulation | What Fuji says | Source |
|---|---|---|
| Classic Chrome | Lowest saturation of all simulations; second-hardest tonality; **hard shadows, soft graded highlights**; aim: "tell the story through tone" | [Fuji JP, "Film Simulation no Sekai #2"](https://www.fujifilm-x.com/ja-jp/stories/the-world-of-film-simulation-episode-2) |
| Classic Chrome | Not a copy of a specific film but the atmosphere of documentary magazines; **magenta component removed from the sky**; **saturation and hue of reds and greens controlled** | [Fuji, Film Simulation "CLASSIC CHROME"](https://www.fujifilm-x.com/en-us/stories/film-simulation-classic-chrome/) |
| Classic Neg | Key idea **"color (color-by-color) contrast"**: a separate luminance tonality per colour: for one colour input->output is linear, for another output below a luminance threshold is lowered -> "veiled" look and contrast between colours. Saturation below Provia. Best with slight overexposure. Modelled on Superia; key zones: foliage, blues, skin | [Fuji, X-Pro3 Stories #2](https://www.fujifilm-x.com/en-nz/stories/x-pro3-stories-2-learning-from-film/) |
| Color Chrome Effect | For saturated subjects "adds depth and detail" in reds, greens and yellows; three strengths. Inspired by Fortia 50 | [Fuji, film-simulation](https://www.fujifilm-x.com/global/film-simulation/); [fujixweekly](https://fujixweekly.com/2019/04/03/fujifilm-x-t30-new-feature-color-chrome-effect) |
| General principle | Colour reproduction tuned for "comfort and naturalness" after ensuring a certain colorimetric accuracy | [Fuji, film-simulation](https://www.fujifilm-x.com/global/film-simulation/) |

**Fujifilm patent US7092122B2** ("Image processing device and method") [patent; not tied to a specific simulation]. Saturation is changed with weights that depend on **hue** (a protected zone around skin, H* ~ 45 deg), on **saturation level** (increase suppressed for both low-saturation and near-limit colours) and on **lightness** (change suppressed in highlights and shadows), with smooth transitions. Exactly the "chroma = f(hue, sat, L)" structure seen in section 2. Documented as a mechanism, but Fuji does not state that simulations are built this way. [Google Patents US7092122](https://patents.google.com/patent/US7092122).

**DR100/200/400** [community, consistent with RAW behaviour]: the camera underexposes by 1 or 2 stops (hence the minimum ISO), then lifts shadows and midtones in the JPEG render while keeping a long highlight shoulder. The shift is recorded in the RAW. Sources: [jmpeltier](https://www.jmpeltier.com/fujifilm-dynamic-range-settings), [fujirumors](https://www.fujirumors.com/?p=143525). Sony analogue: exposure compensation -0.3...-0.7 plus shadow lift (DRO/curve).

**Color Chrome Effect per pixel** [community]: darkens saturated colours, more in dark areas, which pulls out gradation there. Saturation does not increase. Observation by s7habo (pixls.us), reproducible with a saturation-and-luminance mask. [pixls.us](https://discuss.pixls.us/t/what-is-color-chrome-effect-and-how-to-achieve-it/18760).

**Highlight/Shadow tone (-2...+4)**: separate shoulder and toe adjustments on top of the simulation curve. Evident from how recipes use them; official mechanics [not found].

---

## 2. Measurement: what simulations do numerically

### Data source and why it is (partly) trustworthy

- Repository **[abpy/FujifilmCameraProfiles](https://github.com/abpy/FujifilmCameraProfiles)** (updated 2025-11-22): 32^3 `.cube` 3D LUTs in sRGB for Provia, Astia, Velvia, Classic Chrome, Pro Neg Std/Hi, Eterna, Reala Ace, Classic Neg, Nostalgic Neg and Bleach Bypass.
- **Provenance: two steps from Fuji.** Fuji JPEG -> Adobe camera-matching profiles (Adobe fits them on RAW+JPEG charts) -> abpy interpolates samples from ACR exports (X-Trans 4) -> LUT. Sources: [README](https://github.com/abpy/FujifilmCameraProfiles), [pixls.us](https://discuss.pixls.us/t/fujifilm-film-simulation-profiles-for-adobe-and-other-raw-processors/38197).
- **Classic Neg and Nostalgic Neg** have no Adobe matching profiles; abpy built those LUTs separately. In 2023 the author had no Classic Neg camera; how the 2025 versions were made is undocumented -> **least trusted** (marked "(!)" below). The Classic Neg neutral is also +8 L* brighter in the midtones than the others, possibly a different exposure anchor.
- LUT input is "linear contrast" (camera without tone curve) in sRGB encoding, output is the final image. So curve and colour live in one LUT and can be separated by measurement.
- **Method.** Run through the LUT with trilinear interpolation: neutral ramp, hue rings in CIELAB at several L*/C*, 40-60k random points. Everything compared **against Provia output**: Provia is "standard", the closest analogue of Sony Standard. Analysis scripts not included in this repository.

### 2a. Tone curve (neutral): scene reflectance -> output L*

| Reflectance | 0.25 % | 0.5 % | 1 % | 2 % | 4.5 % | 9 % | 18 % | 36 % | 60 % | 90 % |
|---|---|---|---|---|---|---|---|---|---|---|
| Provia | 1.3 | 2.4 | 4.7 | 12.1 | 28.6 | 47.2 | 66.5 | 84.3 | 94.9 | 99.1 |
| Astia | 1.2 | 2.2 | 3.9 | 10.4 | 27.9 | 48.0 | 67.1 | 83.1 | 94.3 | 99.0 |
| **Classic Chrome** | **0.3** | **1.1** | **2.8** | **8.9** | 26.5 | 46.9 | **68.4** | **85.4** | 95.3 | 99.2 |
| Pro Neg Std | 1.6 | 2.9 | 5.9 | 14.3 | 29.9 | 47.2 | 66.5 | 84.3 | 94.9 | 99.1 |
| **Pro Neg Hi** | **0.1** | **0.8** | **2.4** | **8.2** | 26.7 | 47.2 | 66.1 | 84.3 | **96.4** | **99.7** |
| Eterna | 2.3 | 4.8 | 9.8 | 17.5 | 30.2 | 47.0 | 66.3 | 82.6 | 92.8 | 98.9 |
| Velvia | 0.0 | 0.2 | 1.6 | 7.0 | 27.4 | 47.6 | 65.4 | 83.8 | 96.8 | 99.7 |
| Reala Ace | 1.0 | 2.1 | 5.8 | 14.5 | 29.5 | 47.0 | 70.9 | 87.5 | 95.6 | 99.4 |
| Classic Neg (!) | 1.5 | 2.2 | 3.8 | 9.9 | 25.0 | 47.8 | 74.4 | 90.7 | 97.3 | 98.8 |

Curve slope, dL* per stop relative to 18 % grey [measured]:

| Stops | -5 | -4 | -3 | -2 | -1 | 0 | +1 | +2 | +2.3 |
|---|---|---|---|---|---|---|---|---|---|
| Provia | 1.6 | 5.1 | 11.8 | 17.2 | 19.3 | 19.2 | 16.4 | 7.5 | 4.9 |
| Classic Chrome | 1.3 | 3.6 | 12.3 | 18.7 | **21.8** | 19.6 | 15.3 | 6.9 | 4.5 |
| Pro Neg Std | **2.0** | **6.5** | 11.6 | **15.6** | 18.9 | 19.2 | 16.4 | 7.5 | 4.9 |
| Pro Neg Hi | 1.3 | 3.2 | 12.7 | 19.6 | 19.2 | 19.3 | 17.8 | 6.1 | 2.4 |
| Eterna | **3.7** | **7.2** | 9.1 | 13.8 | 19.3 | 17.9 | 14.9 | **10.8** | **7.2** |
| Classic Neg (!) | 1.1 | 3.9 | 10.4 | 17.2 | **27.4** | 22.7 | **11.4** | **2.7** | 1.7 |

Observations:
- **Classic Chrome** = Provia with a lowered toe: deep shadows and a steep section at -1 stop. Middle and highlights 1-2 L* brighter, same shoulder. Matches Fuji's "hard shadows, soft highlights" [Fuji + measured].
- **Pro Neg Std** differs from Provia **only by a raised toe** (lighter shadows); above -1 stop the curves are identical. A "soft" look.
- **Pro Neg Hi**: deep shadows like CC plus **brighter whites**: 96.4 vs 94.9 at 60 %. Shorter shoulder.
- **Eterna**: flat at both ends.
- **Classic Neg** (!): very steep middle and a quickly rolled-off shoulder, i.e. "negative-like" highlight compression.

### 2b. Neutral tint vs luminance (a*, b*)

- Provia, Astia, CC, Pro Neg Std/Hi, Eterna, Velvia, Reala: |a*|,|b*| <= 0.5 at 2 %, 18 % and 90 %. **The neutral is neutral.**
- Classic Neg (!): shadows at 2 % a* = -2.1 (green), middle 18 % a* = +3.5 b* = +3.5 (warm-red), highlights ~0. This is **luminance split-toning**, consistent with Fuji's "per-luminance tonality" [measured + Fuji].
- Nostalgic Neg: middle b* = +4.8 (amber), toward highlights b* = +1.4.

### 2c. Per-hue chroma and hue vs Provia (input L*=55, C*=35, midtone)

Cell format: chroma multiplier / hue shift in degrees. "+" = counter-clockwise in h_ab (red -> yellow -> green -> blue).

| input h | 0 magenta-red | 30 red | 60 orange/skin | 90 yellow | 120 yellow-green | 150 green | 180 teal | 210 cyan | 240 sky | 270 blue | 300 violet | 330 magenta |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Classic Chrome | 0.73/+3 | 0.75/+1 | 0.76/0 | 0.77/-2 | 0.72/-2 | 0.80/+5 | 0.94/+3 | 1.00/-6 | 0.95/**-15** | 0.76/**-18** | **0.60**/-5 | 0.66/+3 |
| Pro Neg Std | 0.92/-5 | 0.87/-5 | 0.82/0 | 0.84/+2 | 0.85/-1 | 0.85/-3 | 1.03/-4 | 1.01/-9 | 0.92/-9 | 0.86/-3 | 0.91/-2 | 0.93/-4 |
| Pro Neg Hi | 0.96/-4 | 0.92/-3 | 0.89/-2 | 0.91/-1 | 0.90/-3 | 0.89/-3 | 1.01/-2 | 0.99/-2 | 0.95/+3 | 1.02/+6 | 1.06/-2 | 0.99/-5 |
| Astia | 0.94/+2 | 0.94/-1 | 0.91/+1 | 0.98/+2 | 0.96/-5 | 0.83/+2 | 0.84/**+21** | 1.04/**+27** | 1.12/+18 | 1.15/+3 | 1.02/-4 | 0.91/-1 |
| Eterna | 0.76/+1 | 0.77/+4 | 0.77/+5 | 0.75/+2 | 0.68/-1 | 0.69/0 | 0.96/0 | 0.99/-10 | 0.83/-13 | 0.70/-9 | 0.70/-3 | 0.73/-1 |
| Classic Neg (!) | 0.71/+15 | 0.79/+5 | 0.78/0 | 0.76/-4 | **0.61**/+4 | 0.69/**+27** | 0.84/**+41** | 1.05/+23 | 0.92/+5 | **0.51**/+1 | **0.41**/+22 | 0.54/+22 |
| Velvia | 1.16/-4 | 1.11/+4 | 1.25/+1 | 1.17/+2 | 1.15/0 | 1.08/-3 | 1.02/-1 | 1.01/+13 | 1.11/+16 | 1.24/+10 | 1.40/+2 | 1.41/-1 |

The same rings at L* = 35/75/88 and per-object breakdowns (skin, sky, foliage, red, yellow at three lightness levels) were also computed. Key points:
- **Skin** (h ~ 55-60): CC chroma x0.72-0.86, hue -3...-8 (toward red, not yellow). Pro Neg Std x0.75-0.89, -1...-5. Astia x1.0-1.27, +4...+5 (toward yellow, "peachier").
- **Sky** (h ~ 235-245): CC -11...-14 **toward cyan**, x0.83-0.90. Astia the opposite +11...+16 (toward blue), x1.1-1.2. Pro Neg Std -2...-7.
- **Foliage** (h ~ 135): CC x0.65-0.77, hue almost unchanged. Classic Neg x0.47-0.67 and **+12...+18 toward teal**. Pro Neg Std x0.82-0.92.
- **Yellows in highlights** (L 80): CC x0.67, Pro Neg Std x0.85. Saturated light yellows are suppressed, part of "clean whites".
- **Blues and violets in Classic Chrome** are suppressed most (x0.60-0.76). That is why CC looks "dry".

### 2d. Chroma as a function of luminance (median over all hues, vs Provia, L* bins of 10)

| Provia output L* | 0-10 | 10-20 | 20-30 | 30-40 | 40-50 | 50-60 | 60-70 | 70-80 | 80-90 | 90-100 |
|---|---|---|---|---|---|---|---|---|---|---|
| Classic Chrome | **0.49** | 0.75 | 0.80 | 0.83 | 0.85 | 0.83 | 0.80 | 0.75 | 0.72 | **0.70** |
| Pro Neg Std | 0.80 | 0.81 | 0.84 | 0.85 | 0.86 | 0.87 | 0.90 | 0.91 | 0.89 | 0.87 |
| Pro Neg Hi | **0.49** | 0.87 | 0.96 | 1.00 | 0.96 | 0.94 | 0.95 | 0.97 | 0.98 | 0.92 |
| Eterna | 1.06 | 0.78 | 0.76 | 0.76 | 0.78 | 0.78 | 0.77 | 0.75 | 0.75 | 0.82 |
| Reala Ace | 1.15 | 1.10 | 1.03 | 0.98 | 0.95 | 0.93 | 0.86 | 0.78 | 0.77 | 0.79 |
| Classic Neg (!) | 0.51 | 0.61 | 0.66 | 0.69 | 0.74 | 0.72 | 0.70 | 0.63 | 0.52 | **0.42** |

Chroma barely depends on the **saturation level**: across C* 0 to 60+ the multiplier changes by +/-0.05. Exceptions: Reala Ace (saturated colours suppressed more, 0.95 -> 0.84) and Classic Neg (0.76 -> 0.66). There is **no** Color-Chrome-style compression of saturated colours in the base LUTs: it is a separate option [measured].

### 2e. How many knobs are needed: layer decomposition (mean dE76 to target; base = Provia output)

| Simulation | unchanged | + curve | + 1 saturation | + saturation(L) | + 12 hues (chroma, hue) | + 12 hues x 5 lightness |
|---|---|---|---|---|---|---|
| Classic Chrome | 10.8 | 10.8 | **4.7** | 4.2 | 3.4 | 2.8 |
| Pro Neg Std | 6.0 | 6.1 | **3.6** | 3.5 | 2.5 | 2.1 |
| Pro Neg Hi | 4.1 | 3.9 | 3.5 | 3.4 | 2.5 | 2.3 |
| Eterna | 10.8 | 10.6 | **4.3** | 4.3 | 3.8 | 3.4 |
| Astia | 5.1 | 5.1 | 5.1 | 4.5 | **3.3** | 2.9 |
| Reala Ace | 9.8 | 9.7 | 7.2 | 6.0 | 5.0 | 4.1 |
| Classic Neg (!) | 20.7 | 20.4 | 11.3 | 10.6 | **6.3** | 5.3 |
| Velvia | 11.1 | 11.1 | 7.1 | 6.7 | 5.6 | 5.1 |

The ~2-3 dE floor is mostly the coarseness of the model's bins; it does not mean "the rest needs a LUT". Mean dE over random colours underweights the curve: shadows are a small fraction of the volume but visually important. So the curve is judged separately via 2a.

Conclusions [measured]:
- **CC, Eterna and Pro Neg Std** are almost entirely "Provia + curve + one saturation". The per-hue layer removes another ~1 dE, mostly sky to cyan and red to orange.
- **Astia** is per-hue: same global saturation, teal and cyan rotated toward blue.
- **Classic Neg** cannot be assembled without per-hue and per-luma layers (11.3 -> 6.3), and also needs a neutral tint. Independently confirmed by the darktable solver: Nostalgic Neg is not solvable with stock modules [community, [jssfr.de](https://jssfr.de/dtsolve/2026-01-02-darktable-styles-fujifilm.html)].
- Adobe's DCPs model simulations with a LookTable of **72 hues x 12 saturations x 16 lightness levels** (visible in abpy's `xml tables/*.txt`). The lightness index being needed is indirect confirmation that chroma-vs-luminance matters.

---

## 3. Fuji firmware and parameter storage

- **[not found]** No public analysis of simulation tables in X-series firmware. The darktable styles were made "with a numerical solver fitting parameters to OOC JPEGs"; the author notes "no Fujifilm code was reverse-engineered" ([jssfr.de](https://jssfr.de/dtsolve/2026-01-02-darktable-styles-fujifilm.html)). Adobe also matches against charts ([talkphotography](https://www.talkphotography.co.uk/threads/applying-fuji-film-simulations-to-raw-files.664131/post-7966453)).
- Publicly available are only the EXIF setting tags (FilmMode, Highlight/ShadowTone, Color, ColorChromeEffect, ColorChromeFXBlue, Clarity -5000...5000, etc.) in [ExifTool](https://exiftool.org/forum/index.php?msg=68002). Metadata, not tables.

---

## 4. Worked examples with numbers

| What | Numbers | Status |
|---|---|---|
| Curves, per-hue chroma and hue for 10 simulations | sections 2a-2d | [measured] on abpy LUTs (Adobe matching, X-Trans 4) |
| DCP LookTable 72x12x16 + 128-point ToneCurve per simulation | `xml tables/*.txt` in [abpy/FujifilmCameraProfiles](https://github.com/abpy/FujifilmCameraProfiles) | [community], machine-readable |
| Kodak Gold 200 on X-Trans III/IV | Classic Chrome, DR-Auto, Highlight -2, Shadow +1, Color +3, Sharp -2, NR -4, Grain Strong, CCE Off, WB Daylight **+4R -5B** | [community, fujixweekly 2020](https://fujixweekly.com/2020/04/16/my-fujifilm-x-t30-kodak-gold-200-film-simulation-recipe/) |
| Kodak Gold 200 on X-Trans V | CC, DR400, Highlight -1.5, Shadow +0.5, Color +3, CCE Weak, FX Blue Off, WB Daylight +4R -5B, Clarity -2 | [community, fujixweekly 2023](https://fujixweekly.com/2023/10/24/kodak-gold-200-fujifilm-x-t5-x-trans-v-film-simulation-recipe/) |
| Classic Chrome from a ColorChecker | RAW->JPEG fitting procedure in RawTherapee, HaldCLUT; no numbers in the thread | [community, pixls.us](https://discuss.pixls.us/t/classic-chrome-haldclut-like-the-x-t2-for-rt/1797) |

Reading the Kodak Gold recipe through the mechanics: CC (x0.76 chroma, deep shadows, sky to cyan) + **Color +3** brings chroma back to roughly Provia level. Result: CC tone and curve, near-standard saturation, warmth from the WB shift. So popular "Kodak recipes" use CC for its **curve and per-hue behaviour**, and undo its saturation cut [interpretation].

Academic: "Deep Analog" (arXiv 2608.14702, Aug 2026): a 3D LUT predicted from one reference frame, plus separate tone matching, grain and halation ([arXiv](https://arxiv.org/pdf/2608.14702)). Supports the general "tone separately, colour via 3D LUT" scheme, but says nothing about Fuji.

---

## 5. What transfers to the NEX-3N: knobs vs Fuji mechanics, by visual importance for the target look

The assumed Sony knobs (per-style and per-ISO chroma-gain ladders, global contrast/saturation/sharpness +/-3, WB A-B / G-M, DRO) come from the initial brief; what the registers actually do had to be measured (see notes/backup-params.md, notes/hue-tables.md).

| # | Layer | Fuji (measured) | NEX-3N equivalent | Simple knob enough? |
|---|---|---|---|---|
| 1 | **Global chroma** | CC x0.76, Pro Neg Std x0.88, Pro Neg Hi x0.95 | Saturation -1...-2 or per-style chroma gain | **Yes**, closes more than half the difference |
| 2 | **Warmth** | Not in the simulations; warmth in recipes = WB shift (+4R -5B ~ toward amber) | WB A-B shift toward A, optionally G-M slightly toward M | **Yes** |
| 3 | **Curve toe: deep clean black** | CC/PNHi: L* 2.4-2.8 at 1 % vs 4.7 for Provia; 0.1-0.3 at 0.25 % | Contrast +1 partly; DRO **Off** (DRO does the opposite, lifts shadows) | **Partly**: symmetric contrast also touches highlights; ideally an asymmetric curve or black-level offset if a register is found |
| 4 | **Chroma vs luminance: clean shadows and highlights** | CC shadows x0.49, highlights x0.70; PNHi shadows x0.49 | Look for shadow/highlight chroma-suppression registers in the YC path (typical low-light / highlight chroma suppression blocks) | **No** with global knobs; whether a register exists is unknown |
| 5 | **Bright whites / shoulder** | PNHi 96.4 vs 94.9 at 60 %, shorter shoulder | Exposure +0.3, contrast | Yes, approximately |
| 6 | **Skin** | CC/PN Std: chroma x0.72-0.89, hue -1...-8 toward red; Astia: toward yellow, x1.0-1.27 | Creative Style choice: Sony Portrait has its own per-hue skin handling; per-style chroma ladders | Only via style choice; finely via a per-hue table |
| 7 | **Sky to cyan, foliage to teal** | CC sky -12...-18, CN foliage +20...+40 | - | **Not wanted**: this is the "teal" to avoid. Keep sky as Standard or move slightly toward blue like Astia |
| 8 | **Mute blues and violets** | CC x0.60-0.76 at 270-330 | Per-hue gain if available | Desirable, not essential |
| 9 | **Color Chrome Effect** | Darkening of saturated reds, yellows, greens; not in base LUTs | Per-hue value scale if the YC hue table has a lightness term | No simple knob, low priority |
| 10 | **Neutral split-tone** (Classic Neg) | Green shadows, warm middle | - | Not needed for this look |

**Target profile in measurement terms** (Provia as base): Pro Neg Hi or CC curve (deep toe, bright shoulder) + chroma x0.85-0.9 uniformly + chroma x0.5 below L*10 and x0.75 above L*85 + WB shift toward amber + skin per Pro Neg Std (x0.85, -3 deg) + **no** sky-to-cyan shift. Items 1-3 and 5 are existing knobs. Item 4 is what to look for in firmware first: the main source of "cleanness" that Sony Standard lacks.

**Verifying on your own camera** (recommendation): shoot a ColorChecker plus grey scale RAW+JPEG with the chosen style, render the RAW to "linear contrast" sRGB and run the same metrics (curve, chroma per hue and per luminance). That yields the Sony equivalent of section 2 and shows directly which register changes what. Tools for this in the repository: `code/measure/` and the simulator `code/sim/` (notes/simulator.md).

---

## Sources
- [Fujifilm - Film Simulation "CLASSIC CHROME"](https://www.fujifilm-x.com/en-us/stories/film-simulation-classic-chrome/)
- [Fujifilm JP - Film Simulation no Sekai #2](https://www.fujifilm-x.com/ja-jp/stories/the-world-of-film-simulation-episode-2)
- [Fujifilm - X-Pro3 Stories #2 Learning from Film (Classic Neg)](https://www.fujifilm-x.com/en-nz/stories/x-pro3-stories-2-learning-from-film/)
- [Fujifilm - Film Simulation (Color Chrome Effect)](https://www.fujifilm-x.com/global/film-simulation/)
- [Fujifilm patent US7092122B2](https://patents.google.com/patent/US7092122)
- [abpy/FujifilmCameraProfiles (LUTs, DCP tables)](https://github.com/abpy/FujifilmCameraProfiles)
- [pixls.us - Fujifilm film simulation profiles](https://discuss.pixls.us/t/fujifilm-film-simulation-profiles-for-adobe-and-other-raw-processors/38197)
- [pixls.us - Classic Chrome HaldCLUT](https://discuss.pixls.us/t/classic-chrome-haldclut-like-the-x-t2-for-rt/1797)
- [pixls.us - what is color chrome effect](https://discuss.pixls.us/t/what-is-color-chrome-effect-and-how-to-achieve-it/18760)
- [jssfr.de - darktable styles mimicking Fujifilm (solver)](https://jssfr.de/dtsolve/2026-01-02-darktable-styles-fujifilm.html)
- [fujixweekly - Kodak Gold 200 (X-T30)](https://fujixweekly.com/2020/04/16/my-fujifilm-x-t30-kodak-gold-200-film-simulation-recipe/), [Kodak Gold 200 (X-T5)](https://fujixweekly.com/2023/10/24/kodak-gold-200-fujifilm-x-t5-x-trans-v-film-simulation-recipe/), [Color Chrome Effect](https://fujixweekly.com/2019/04/03/fujifilm-x-t30-new-feature-color-chrome-effect)
- [jmpeltier - DR settings](https://www.jmpeltier.com/fujifilm-dynamic-range-settings), [fujirumors - DR400 curve](https://www.fujirumors.com/?p=143525)
- [ExifTool forum - Fuji tags](https://exiftool.org/forum/index.php?msg=68002), [talkphotography - Adobe matching](https://www.talkphotography.co.uk/threads/applying-fuji-film-simulations-to-raw-files.664131/post-7966453)
- [arXiv 2608.14702 - Deep Analog](https://arxiv.org/pdf/2608.14702)
