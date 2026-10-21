# Film on a colour chart: published tests, measurements, recipes for the NEX-3N

Research and measurements, 2026-10-04. Measured data is in `data/filmcharts/` (JSON results); the analysis scripts that produced it are not included in this repository. Related: notes/hue-tables.md (slot matrices and hue tables), notes/fuji-film-simulation-research.md (Fuji 3D-LUT mechanics, not repeated here).

Labels: **[measured]** = computed here from downloaded data; **[source]** = claim by the test author or manufacturer; **[opinion]** = subjective judgement by the author. dE = CIEDE2000, Lab D65 (sRGB). dh = hue-angle shift in Lab (negative = toward smaller angle: blue -> cyan, cyan -> green, yellow-green -> yellow; positive = red -> orange, magenta -> red). Cr = chroma ratio C*(film)/C*(reference).

---

## 0. Summary

1. **Good published "film on a ColorChecker" tests barely exist.** Three measurable sources were found:
   - **Pablo Maraver, 2025 (video + PetaPixel):** 14 films on a SpyderCheckr 24, one lamp, one scanner. The video contains "reference / film" frames with patches, which were measured here. It is the **only source** for Gold 200, UltraMax 400, ColorPlus 200, ProImage 100, Phoenix 200 (first version), Lomography Color 400, CineStill 50D/800T, Fujifilm 200. Caveat: he stretched channels on the grey scale (10 % / 90 %), so contrast and the tint of highlights/shadows are set by his normalisation. Film is compared with his rendering of the chart's reference values, not with a digital shot of the same scene.
   - **Tim Gray, 2010-2011 (125px.com + Flickr):** ColorChecker Passport, Ektar 100, Portra 160NC/VC, 400NC/VC, 800 (120) and Portra 400 (35 mm) with exposure brackets, lab minilab scan. Auto-corrected and heavily brightened scans, so tone and saturation are unusable; only hue shifts are usable.
   - **spektrafilm** (physical model built from datasheets): 13 negatives including Gold 200, UltraMax 400, Portra 160/400/800, Ektar, Vision3 50D/200T/250D/500T, Fuji C200/Pro 400H/X-tra 400. A ColorChecker was rendered through it on two papers.
2. **No chart tests at all** for Harman **Phoenix II**, **SantaColor 100/800**, CineStill 400D, Lomography 800, Fuji Superia (other than the X-tra 400 model), Kodak Aerocolor. Indirect evidence: a Rangefinderforum request from 2026-07-23 for exactly such scans got no answers in 2+ months ([RFF](https://www.rangefinderforum.com/threads/looking-for-it8-colorchecker-scans-shot-on-film.4819895/)). Reddit and Photrio are closed to automated search (login wall, Cloudflare): **not searched, a gap**.
3. **SantaColor 100 = Kodak Aerocolor IV 2460** [source: [Freestyle](https://www.freestylephoto.com/1230135-SANTACOLOR-100-ISO-35mm-x-36-exp.-Color-Negative-Film), [DPReview](https://www.dpreview.com/news/5111575666/film-friday-santacolor-100-35mm-color-negative-film-aerial-surveillance-film-stock)]. No Aerocolor profile in spektrafilm or in tests. **The origin of SantaColor 800 was not established.** Sellers say "not respooled motion-picture film, process as Portra 800" (search snippets, no datasheet).
4. **Common picture for Kodak negatives on a chart** [measured, all three sources agree in sign]: blues and blue-violets shift toward cyan (dh -7 to -37 deg on purplish blue / blue sky / blue flower), foliage and yellow-green toward yellow (dh -5 to -20), skin and oranges toward yellow (dh +5 to +23), magentas and purples desaturate the most (Cr 0.4-0.7). This is the "blue <-> gold" axis that Maraver also describes.
5. **A 3x3 matrix plus a tone curve removes about half the difference** [measured]. On Maraver's data mean dE reference -> film is 6-9. A tone curve alone gives 4.3-7.7, curve plus matrix 2.5-4.6. The remainder (3-4 dE) is mostly the blue and cyan patches, i.e. **a hue rotation in one sector only**, which a matrix cannot do. Per-hue-sector int8 tables are needed (notes/hue-tables.md).
6. **Ranking "matrix plus contrast is enough"** (section 7): LomoChrome '92 > Fujifilm 200 ~ Lomography 400 ~ Portra 400 ~ Portra 160 > ColorPlus ~ Ektar ~ UltraMax ~ CineStill 50D > Gold 200 > ProImage (doubtful data) >> **Phoenix** and **CineStill 800T** (unsuitable: need per-channel curves and sector rotation).
7. **spektrafilm separates films weakly.** The paper difference (Portra Endura vs Crystal Archive) is comparable to the difference between films. In 0.3.4 all negatives share the same DIR-coupler parameters ([source](https://github.com/andreavolpato/spektrafilm), `runtime/params_builder.py::_apply_film_specifics`). Correlation of its hue shifts with Maraver: 0.3-0.7 for Kodak Portra/Ektar/Gold/UltraMax, negative for 800T. Use it as "direction labels", not truth. The author and users note the model is more saturated on a chart than a real RA-4 scan ([pixls #726](https://discuss.pixls.us/t/spectral-film-simulations-from-scratch/48209?page=36)).

---

## 1. Sources per film

| Film | What exists | Chart / light / scan | Digital reference | Measurable |
|---|---|---|---|---|
| **Harman Phoenix 200 (I)** | Maraver | SpyderCheckr 24 / high-CRI LED, lamp CCT = camera WB / camera scan (Valoi easy35 + Nikon + Nikkor 55 macro f/8), 10/90 % normalisation | rendered reference values | yes (video frame) |
| **Harman Phoenix II** | datasheet only (D55 spectrogram) [PDF](https://firstcall-photographic.co.uk/cdn/shop/files/Harman_Phoenix_II_Data_Sheet.pdf); reviews without a chart ([AP](https://amateurphotographer.com/review/harman-phoenix-ii-review/): "deep reds were rendered as a dark orange" [opinion]) | - | - | **no test** |
| **SantaColor 100** (= Aerocolor IV) | nothing with a chart | - | - | **no** |
| **SantaColor 800** | nothing; emulsion origin unknown | - | - | **no** |
| **Kodak Gold 200** | Maraver; spektrafilm | as above; datasheet model | - | yes |
| **Kodak UltraMax 400** | Maraver; spektrafilm | - | - | yes |
| **Kodak ProImage 100** | Maraver (he says it "may have had some trouble exposing... or development", conclusions conditional) | - | - | conditional |
| **Kodak ColorPlus 200** | Maraver; Flickr exposure bracket without chart ([album](https://www.flickr.com/photos/149409562@N06/albums/72157702269631325/)) | - | - | yes (Maraver only) |
| **Kodak Portra 160** | Maraver; spektrafilm; Tim Gray (160NC/VC only, discontinued) | - | - | yes |
| **Kodak Portra 400** | Maraver; spektrafilm; Tim Gray 35 mm 2011 ([album](https://www.flickr.com/photos/tgray1/albums/72157625883846979)) | TG: Passport, daylight and 3200K, bracket -4...+6, Precision Camera scan | no | yes |
| **Kodak Portra 800** | spektrafilm; Tim Gray 120 ([album](https://www.flickr.com/photos/tgray1/albums/72157623780927110)) | TG: sun / window / mixed, NCPS scan | no | TG overexposed; hue only |
| **Kodak Ektar 100** | Maraver; spektrafilm; Tim Gray 120 ([album](https://www.flickr.com/photos/tgray1/albums/72157623780898802)) | TG: Passport in sun, bracket -3...+4 | no | yes |
| **Fuji Superia / C200 / Pro 400H** | spektrafilm (X-tra 400, C200, Pro 400H); Maraver's "Fujifilm 200" is the new US-made one, not C200 | - | - | model |
| **CineStill 400D** | nothing with a chart | - | - | **no** |
| **CineStill 800T** (+ Candido 800, both Vision3 500T) | Maraver (shot under his LED, i.e. daylight/neutral) | - | - | yes |
| **CineStill 50D** | Maraver | - | - | yes |
| **Lomography CN 400** | Maraver (rolls from Lomography) | - | - | yes |
| **Kodak Vision3 50D/200T/250D/500T** | spektrafilm | model | - | model |
| Film Onehundred 100, LomoChrome '92 | Maraver | - | - | yes (off-list) |

Maraver links: [video](https://www.youtube.com/watch?v=AVFTtE-8C94), [PetaPixel](https://petapixel.com/2025/11/17/the-color-science-behind-the-most-popular-35mm-films-available-today/). His method [source, subtitles 07:02-09:05]: SpyderCheckr 24; adjustable-CCT lamp, no stray light; one camera; Nikkor 50/1.8 at f/2.8, exposure by shutter only (plus 1-stop safety bracket); development at one lab; camera scan; camera WB equals lamp CCT; then "linear stretching, no contrast curves, RGB channels hit the same values at 10% black and 90% white" on the grey scale. Tim Gray: [125px.com](https://125px.com/articles/photography/film/kodak-film-comp/) ("minilab scanning... relatively consistent").

**Datasheets** (curves and spectral sensitivities for physical models):
- Kodak Gold 200, E-7022, June 2023 ([PDF](https://www.kodakprofessional.com/sites/default/files/wysiwyg/pro/resources/E7022%20Gold%20tech%20sheet.pdf)).
- Kodak Portra 400, e4050 ([PDF](https://125px.com/docs/film/kodak/e4050-Portra-400.pdf)). spektrafilm builds Portra 400 from it (2016) [spektrafilm README].
- Harman Phoenix 200 (I) TIS, November 2023: only a spectrogram for 2856K tungsten; **no** characteristic or dye curves ([PDF](https://www.macodirect.de/media/pdf/58/77/ae/HP2011_Datenblatt_d.pdf)).
- Harman Phoenix II TIS, July 2025: D55 spectrogram, no curves. On the difference from Phoenix I: "more normal contrast, colour balance and finer grain... wider exposure latitude... still... creative, experimental film" [source].
- Datasheet numbers for UltraMax, ColorPlus, ProImage and Aerocolor were **not found** (not invented). spektrafilm does have UltraMax 400, so its author had data.

---

## 2. Method

- **Maraver**: 15 "Reference color | <film>" frames from the video (1080p). The 4x6 grid is located automatically; median of a 50x50 px square in each patch centre; overlay checked visually. The reference grid is identical across frames to 1e-13. SpyderCheckr 24 layout: rows "greys", "primaries", "orange-yellow...", "skin..." (names in the JSON). Patches rendered by him in sRGB, converted to Lab D65.
- **Tim Gray**: 4 grid corners placed by hand with bilinear interpolation, median of 12-18 px. Reference: X-Rite ColorChecker24 "After November 2014" (from colour-science), D50 -> D65 Bradford, to sRGB.
- **spektrafilm 0.3.4**: synthetic chart (same X-Rite values) in linear sRGB on an 18 % grey background. `lut_mode` (no grain, halation or auto-exposure), printed on Kodak Portra Endura and Fujifilm Crystal Archive Type II with the project's neutral filter database. Output in linear sRGB.
- **Fit models**: (0) global tone curve only (lift + gain*x^gamma in linear space, fitted on the grey row); (A) 3x3 matrix; (B) matrix plus global curve; (C) matrix plus a separate curve per channel (models luminance-dependent tint). Fitted on dE in Lab. A "recipe" = two-stage fit: curve on greys first, then the matrix with the curve fixed. The matrix is normalised so rows sum to 1024; row sums are reported separately as "tint".

**Confounds (important):**
- In Maraver's data, tone and neutral are partly set by his 10/90 % stretch: shadows are lifted (grey L 27.5 -> 34-38 for almost every film), white drops to L ~ 91. Hence curve gamma ~ 0.65-0.8 for everything, a **property of the processing, not the film**. However, the tint of mid-greys after the stretch **is real**: it is the difference in channel gammas (crossover).
- Maraver's "saturation" metric is an unsigned percentage deviation (subtitles: UltraMax "+7.15 %", LomoChrome/Portra 400/Phoenix "drops 21, 18, 16 %"). Measured C* in Lab is below reference for every film. Part of this is contrast loss from the stretch: with the "curve first" fit, the equivalent matrix saturation is 0.9-1.0 for most.
- Tim Gray: minilab scan with auto-exposure. Portra 400/800 are +20...+45 L* overexposed, so chroma and tone there belong to the scan, not the film. Hue shifts used with caution.
- spektrafilm shows a **print** (RA-4), not a Frontier/Noritsu scan. Paper sets black and white (L 9-11 / 81-85) and the S-curve.

---

## 3. Maraver: per-patch measurements [measured]

Mean over 18 colour patches; greys separately. "Hue deg / Sat %" = bars from his charts ([hue](https://petapixel.com/assets/uploads/2025/11/Film-hue-fidelity-results.jpg), [sat](https://petapixel.com/assets/uploads/2025/11/film-saturation-results.jpg)), read off by pixel.

| Film | mean dE | mean \|dh\| (ours) | Hue deg (his) | Sat % (his, unsigned) | Cr (sum C) | Cr by L: <45 / 45-65 / >=65 | Grey L~51: a*, b* | Grey L~27: a*, b* |
|---|---|---|---|---|---|---|---|---|
| UltraMax 400 | 6.2 | 7.9 | 6.2 | 7.2 | **0.92** | 0.95 / 0.85 / 0.94 | -8.6, -3.5 | -9.0, -0.3 |
| Ektar 100 | 7.1 | 7.6 | 6.4 | 15.4 | 0.79 | 0.82 / 0.70 / 0.83 | -1.9, -2.5 | -4.0, -0.1 |
| Portra 400 | 8.2 | 8.0 | 7.6 | 18.0 | 0.76 | 0.83 / 0.66 / 0.79 | -0.4, +3.4 | +0.5, +6.7 |
| Portra 160 | 6.6 | 9.9 | 7.8 | 12.8 | 0.79 | 0.78 / 0.77 / 0.82 | -5.7, -0.1 | -6.6, +1.1 |
| Fujifilm 200 | 6.2 | 7.8 | 7.9 | 10.8 | 0.86 | 0.93 / 0.74 / 0.90 | -2.6, +6.3 | -0.3, +6.5 |
| Lomography 400 | 6.0 | 9.6 | 9.2 | 8.2 | 0.87 | 0.91 / 0.76 / 0.91 | -2.8, +2.0 | -1.9, +2.7 |
| ColorPlus 200 | 6.6 | 10.5 | 10.0 | 8.0 | 0.87 | 0.92 / 0.75 / 0.92 | -4.2, +4.6 | -2.1, +9.2 |
| ProImage 100 | 13.3 | 13.8 | 11.6 | ~28 | 0.59 | 0.70 / 0.54 / 0.53 | -7.7, -10.8 | -5.3, -3.7 |
| Gold 200 | 8.9 | 14.5 | 11.7 | 11.3 | 0.85 | 0.90 / 0.73 / 0.90 | -7.4, +4.6 | **-8.0, +14.6** |
| CineStill 50D | 9.4 | 17.6 | 13.2 | 12.1 | 0.81 | 0.83 / 0.69 / 0.88 | -12.5, +7.3 | -9.3, +4.8 |
| CineStill 800T / Candido | 10.3 | 24.0 | 21.6 | 15.8 | 0.71 | 0.71 / 0.64 / 0.75 | **-13.7, -8.1** | -14.7, -9.2 |
| **Phoenix 200 (I)** | **14.5** | **40.0** | 32.4 | 16.1 | 0.83 | 0.74 / 0.81 / 0.91 | **-13.1, +27.1** | -8.6, +17.1 |
| (Film Onehundred 100) | 6.9 | 9.6 | 8.7 | 11.9 | 0.80 | 0.91 / 0.85 / 0.67 | - | - |
| (LomoChrome '92) | 8.7 | 10.0 | 10.2 | 21.1 | 0.58 | 0.60 / 0.59 / 0.55 | - | - |

Our mean |dh| reproduces his hue ranking (rank differences only inside the 6-10 deg cluster), which validates the patch extraction.
On "Cr by L": the middle band is lowest everywhere, but it contains the blue and magenta patches that desaturate most. **This is not evidence of luminance-dependent chroma**, just hue and L confounded. A pure L dependence cannot be isolated from 18 patches.

### Shifts on key patches (dh deg, Cr in brackets) [measured]

| Film | dark skin | light skin | blue sky | foliage | orange | yellow | red | green | cyan | blue | magenta | purple | purplish blue | blue flower |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Phoenix (I) | +25 (1.08) | +39 (1.70) | **-84** (0.77) | -4 (1.43) | +16 (0.95) | +10 (0.72) | **+29** (0.89) | 0 (0.97) | -38 (0.92) | -34 (**0.29**) | **+62** (0.66) | **+103** (0.88) | -46 (0.35) | **+154** (0.21) |
| Gold 200 | +21 (1.48) | +15 (0.82) | **-36** (1.00) | -19 (1.34) | +13 (0.81) | -4 (0.94) | +9 (0.82) | -6 (0.92) | -18 (0.92) | -2 (0.91) | +9 (0.43) | 0 (0.62) | -37 (0.63) | -39 (0.54) |
| ColorPlus 200 | +11 (1.38) | +8 (0.89) | -29 (0.92) | -19 (1.19) | +5 (0.86) | -4 (0.98) | +4 (0.88) | -15 (0.86) | -14 (0.92) | -2 (0.89) | +6 (0.58) | +4 (0.80) | -24 (0.66) | -27 (0.52) |
| UltraMax 400 | +6 (1.14) | +12 (0.74) | -18 (1.07) | +2 (1.22) | +9 (0.81) | +2 (1.03) | -1 (0.93) | -1 (1.07) | -12 (0.88) | -2 (0.83) | -3 (0.67) | -8 (1.17) | -18 (0.72) | -20 (0.69) |
| ProImage 100 (doubtful) | +5 (0.91) | -19 (0.16) | -19 (0.95) | 0 (0.52) | +10 (0.45) | +7 (0.61) | -1 (0.66) | -2 (0.51) | -8 (0.82) | -10 (0.76) | -25 (0.40) | -18 (0.89) | -28 (0.59) | -31 (0.57) |
| Portra 160 | +7 (0.80) | +8 (0.68) | -20 (0.85) | +2 (1.08) | +5 (0.71) | +5 (0.89) | -10 (0.83) | -2 (0.90) | -13 (0.79) | -10 (0.70) | -2 (0.67) | -20 (0.86) | -21 (0.57) | -22 (0.57) |
| Portra 400 | +14 (1.21) | **+23** (0.65) | -7 (0.74) | -14 (1.04) | +16 (0.70) | +6 (0.86) | +6 (0.75) | -5 (0.82) | -5 (0.71) | 0 (0.85) | +1 (0.49) | +1 (0.78) | -8 (0.60) | -16 (0.56) |
| Ektar 100 | +13 (1.16) | +5 (0.62) | -11 (0.79) | -4 (0.89) | +12 (0.75) | +2 (0.90) | +6 (0.90) | -2 (0.77) | -6 (0.73) | -5 (0.74) | +5 (0.60) | -6 (0.85) | -16 (0.55) | -9 (0.57) |
| Lomography 400 | +2 (1.33) | +5 (0.95) | -28 (0.97) | -17 (1.03) | 0 (0.88) | -3 (0.99) | +4 (0.99) | -13 (0.78) | -19 (0.91) | -3 (0.82) | +9 (0.63) | -4 (0.92) | -27 (0.63) | -27 (0.52) |
| Fujifilm 200 | +2 (1.22) | +15 (0.93) | -18 (0.75) | -13 (1.22) | +10 (0.83) | +1 (0.98) | +1 (0.88) | -10 (0.89) | -9 (0.85) | 0 (0.91) | +9 (0.61) | +13 (0.95) | -12 (0.68) | -6 (0.49) |
| CineStill 800T | +35 (0.58) | **-77** (**0.15**) | -40 (0.85) | +38 (1.02) | +10 (0.74) | -4 (0.82) | +11 (0.86) | +19 (0.76) | -29 (0.84) | -12 (0.55) | -18 (0.55) | -18 (0.86) | -41 (0.47) | -43 (0.45) |
| CineStill 50D | +29 (1.12) | +26 (0.93) | -44 (1.02) | -2 (1.09) | +18 (0.76) | +1 (0.94) | +11 (0.76) | +1 (0.82) | -20 (0.96) | -3 (0.93) | +13 (0.37) | -21 (0.54) | -34 (0.69) | -59 (0.53) |

Full tables including per-patch L: `data/filmcharts/maraver_results.json` (patch values: `maraver_patches.json`).

---

## 4. spektrafilm: datasheet model [measured on the model]

| Film | mean dE (Endura / CA2) | \|dh\| (Endura / CA2) | Cr (Endura / CA2) | Cr by L <45 / 45-65 / >=65 (Endura) |
|---|---|---|---|---|
| Portra 160 | 6.9 / 6.2 | 10.9 / 8.6 | 0.92 / 0.95 | 0.95 / 0.96 / 0.84 |
| Portra 400 | 6.5 / 6.0 | 9.3 / 7.3 | 0.95 / 0.98 | 1.01 / 0.99 / 0.85 |
| Portra 800 | 5.8 / 5.4 | 7.5 / 5.3 | 0.94 / 0.96 | 1.02 / 0.96 / 0.84 |
| Ektar 100 | 7.4 / 6.5 | 10.4 / 7.8 | 0.98 / 1.01 | 1.05 / 1.03 / 0.86 |
| Gold 200 | 6.0 / 5.6 | 7.4 / 5.9 | 0.96 / 0.98 | 1.03 / 0.99 / 0.85 |
| UltraMax 400 | 5.5 / 5.2 | 7.0 / 4.4 | 0.95 / 0.98 | 1.04 / 0.98 / 0.84 |
| Vision3 50D | 5.3 / 5.1 | 7.0 / 4.4 | 0.93 / 0.94 | 1.02 / 0.94 / 0.84 |
| Vision3 250D | 5.9 / 5.8 | 7.7 / 5.6 | 0.91 / 0.92 | 1.01 / 0.91 / 0.82 |
| Vision3 200T | 6.5 / 6.2 | 8.7 / 6.6 | 0.93 / 0.94 | 1.06 / 0.91 / 0.81 |
| Vision3 500T | 6.8 / 6.5 | 9.7 / 7.2 | 0.89 / 0.89 | 1.01 / 0.88 / 0.79 |
| Fuji C200 | 6.6 / 6.0 | 8.9 / 5.8 | **1.07 / 1.10** | 1.20 / 1.11 / 0.89 |
| Fuji Pro 400H | 6.8 / 6.0 | 9.9 / 6.3 | 0.97 / 0.99 | 1.08 / 0.98 / 0.84 |
| Fuji X-tra 400 | 7.2 / 6.7 | 9.6 / 6.7 | **1.12 / 1.15** | 1.27 / 1.17 / 0.92 |

- **Print tone** is the same for all Kodak films (Endura paper): reference L 21/36/51/67/81/95 -> 9-11 / 28-30 / 50 / 66-68 / 76-78 / 81-83. Shadows crushed, white limited by paper. Fuji C200 and X-tra 400 are more contrasty: L36 -> 24-26, L67 -> 70-71.
- **Stable chroma-vs-L dependence in the model:** light colours (L >= 65) lose 10-20 % chroma, dark ones keep or gain. An effect of the paper and S-curve.
- **Neutral tint:** neutrals are balanced by the filter database, residual |a*|, |b*| <= 3. On Crystal Archive light greys go yellow (b* up to +5 on white).
- Cross-check with Maraver (dh correlation over 18 patches): Portra 400 0.60/0.64; Ektar 0.64/0.70; Gold 0.64/0.69; UltraMax 0.42/0.62; Portra 160 0.31/0.54; Vision3 50D<->CineStill 50D 0.44/0.73; Vision3 500T<->800T -0.29/-0.14. Mean absolute mismatch 7-12 deg. Signs agree on blue sky, purplish blue, blue flower and (for Portra) foliage. For 800T the model "prints neutral", while Maraver shot tungsten film under his lamp (lamp CCT = camera WB, exact value unstated), hence the mismatch.

Data: `data/filmcharts/sf_results.json`, `sf_recipes2.json`, raw patches `sf_out_*.json`.

## 5. Tim Gray: hue shifts only [measured, lab auto-scan]

| Film | blue sky | cyan | blue | yellow | orange-yellow | magenta | purple | blue flower | purplish blue |
|---|---|---|---|---|---|---|---|---|---|
| Ektar 100 (120, sun, box speed) | -34 | -26 | -14 | 0 | +1 | +16 | +21 | +26 | -16 |
| Portra 400 (35 mm, correct exposure) | -30 | -34 | -15 | +15 | +18 | -6 | +8 | -1 | -17 |
| Portra 800 (120, sun, box speed; overexposed) | -20 | -18 | -23 | +3 | +10 | +15 | +26 | +18 | -17 |

Portra 400 grey scale after auto-scan: L 21/36/51 -> 13/59/82, which is scan overexposure, not the film. **Do not use tone or chroma numbers from these frames.** Blue sky and cyan go -20...-34 deg in all three: stronger than Maraver (-7...-20), same sign.

Data: `data/filmcharts/tg_patches.json`, `tg_results.json`.

---

## 6. Per film: what it looks like and how to simulate it

Recipe format: **(a) matrix** (`Mnorm_1024`, rows sum to 1024, linear sRGB "neutral -> film"; tint separately as relative R/G/B row sums, best done on camera as a WB shift); **(b) tone / contrast**; **(c) what the matrix cannot do**. Residual dE: tone only -> tone + matrix (Maraver data, `data/filmcharts/maraver_recipes2.json`).

### Harman Phoenix 200 (first version) - Maraver; Phoenix II measured by nobody
**Look** [measured]: largest hue departure (|dh| 40). The blue -> magenta -> red sector **collapses into orange and brown**: magenta +62, purple +103, blue flower +154 with Cr 0.21 (turns grey-beige), red +29, light skin +39 with Cr 1.70 (yellow-orange). Blues darken and lose colour (blue Cr 0.29, L -10), sky goes turquoise (-84). Foliage more saturated than reference (Cr 1.43). Mid-greys after the 10/90 stretch are yellow-green (a* -13, b* +27 at L 51): channel curves diverge strongly in the midtones. Matches Maraver [source]: "unable to reproduce any hue from blue to red, notably including magenta... blues... very low brightness... violets, magentas and reds... displaced toward orange". Harman on Phoenix II [source]: "more normal contrast, colour balance", so II should be milder; **by how much is unknown**.
**Simulation:** (a) best matrix `[[980,-135,179],[182,703,139],[-65,191,898]]`, tint R/G/B = 1.10 / 1.21 / 0.68 (strongly yellow-green). Tone plus matrix still leaves **6.5 dE**: worst purple 17.7, blue 12.2. (b) Per-channel curves give 3.7 dE, so the main part of the look is **different channel gammas** (green-yellow middle with neutral ends). (c) Collapsing B->M->R into orange needs per-hue-sector tables: a matrix cannot rotate one sector by +60...+150. **Matrix plus contrast is not enough.**

### Kodak Gold 200 - Maraver plus spektrafilm (large spread)
**Look** [measured, Maraver]: the "blue <-> gold" axis. Blue sky, purplish blue and blue flower go cyan by -36...-39, foliage yellow (-19, Cr 1.34), skin warmer (dark +21 with Cr 1.48, light +15), magenta fades strongly (Cr 0.43). Shadows yellow-olive (L 27: a* -8, b* +15), middle slightly green-yellow. Maraver [opinion]: "slightly warmer version of ColorPlus... reds even more orange". spektrafilm has the same sign but 2-4x milder (|dh| 7.4 vs 14.5).
**Simulation:** (a) `[[1203,119,-298],[90,952,-18],[5,-4,1022]]`, tint 1.05 / 1.08 / 0.87 (warm). The key is -298: B is subtracted from R, so blue "does not redden" and goes cyan while warm tones redden. Tone only 6.9 -> tone + matrix 4.6. (b) Soft shoulder, warm shadows. (c) Worst after matrix: foliage 6.2, turquoise 5.5, purplish blue 5.5. Foliage yellowing while sky goes cyan is a sector rotation. Matrix plus WB covers **about 2/3**.

### Kodak ColorPlus 200 - Maraver only
**Look** [measured]: a "softer" Gold. Sky -29, blue flower -27, purplish blue -24, foliage -19, green -15, skin +8...+11; highest chroma of the trio after UltraMax (Cr 0.87). Warm shadows (b* +9 at L 27). Maraver considers Fujifilm 200 ~ ColorPlus [opinion, from vectorscope]. The matrices here differ notably (-275 vs -55 in R<-B), so **this similarity is neither confirmed nor refuted**.
**Simulation:** (a) `[[1076,224,-275],[57,960,7],[11,-44,1056]]`, tint 1.06 / 1.04 / 0.90. 5.3 -> 3.9 dE; worst purple 6.8, foliage 5.7. (b) Warm shadows. (c) As Gold, weaker.

### Kodak UltraMax 400 - Maraver plus spektrafilm
**Look** [measured]: most accurate and most saturated Kodak (Cr 0.92; equivalent matrix saturation after the curve 1.08). Small shifts: sky -18, blue flower -20, purplish blue -18, cyan -12, orange-yellow +12, light skin +12. Mid-greys slightly green-cool (a* -8.6, b* -3.5). Maraver [source]: "most saturated and most accurate... exceeds the reference saturation in hues from blue to cyan". spektrafilm: |dh| 7.0 / 4.4.
**Simulation:** (a) `[[1218,-15,-179],[24,1014,-14],[11,-43,1056]]`, tint 0.91 / 1.08 / 1.01 (greenish). 5.2 -> 3.9; worst blue 7.2, cyan 6.9. (b) Normal contrast. (c) A little cyan and blue. **Fits matrix plus contrast well.**

### Kodak ProImage 100 - unreliable data
[measured] Very washed out: Cr 0.59, light skin Cr 0.16, all L above reference by +5...+23. Maraver [source]: "I may have had some trouble exposing this film or... development... taken cautiously". **No recipe.** Direction as other Kodaks: blues to cyan (-10...-31).

### Kodak Portra 160 - Maraver plus spektrafilm
**Look** [measured]: even, "characterless". |dh| 9.9 mostly from the blue sector (purple -20, purplish blue -21, blue flower -22, sky -20, cyan -13), skin +7...+8, red -10. Chroma uniformly below reference (0.78 / 0.77 / 0.82 by L band), neutral slightly green (a* -5...-7). Maraver [opinion]: "very high tonal fidelity... excellent ability to reproduce skin tones".
**Simulation:** (a) near-identity `[[1036,24,-36],[3,974,47],[14,-14,1024]]`, tint 0.92 / 1.07 / 1.01. Tone only 4.3 -> 3.6. **Almost the whole look is the curve plus ~0.8 saturation plus a small green WB shift.** (c) The blue sector -20 is the only thing needing tables.

### Kodak Portra 400 - three sources, consensus on sign
**Look** [measured]: Maraver: Cr 0.76 (one of the palest), skin and oranges to yellow (+14...+23), foliage -14, blue flower -16, sky nearly in place (-7), warm shadows and middle (b* +3...+7). Tim Gray: sky -30, cyan -34, yellow +15, orange-yellow +18. spektrafilm: sky -10/-17, foliage -20/-11, yellow-green -19/-13. **Consensus of three:** purplish blue to cyan (-8 / -17 / -17), foliage to yellow (-14 / -20...-11 / -9), sky to cyan (spread -7...-30). Orange-yellow: two of three sources +14...+18. Maraver [opinion]: "significant desaturation... even and balanced... only blue stands out, giving the film a cool tone".
**Simulation:** (a) `[[912,129,-17],[75,982,-34],[3,41,980]]`, tint 1.04 / 1.05 / 0.91 (warm). Equivalent saturation 0.90. 5.4 -> 3.5. (b) Soft contrast, warm shadows. (c) Blue 8.7, blue flower 5.4, cyan 5.4. **Fits matrix plus contrast well.**

### Kodak Portra 800 - spektrafilm only (Tim Gray overexposed)
[model] The most "accurate" Portra in the model (|dh| 7.5 / 5.3, Cr 0.94 / 0.96). Matrix (CA2) `[[1061,53,-91],[-13,976,62],[4,62,958]]`, 4.2 -> 3.1. **No real chart test.**

### Kodak Ektar 100 - three sources
**Look** [measured]: Maraver: |dh| 7.6, Cr 0.79, oranges and skin to yellow (+11...+13), purplish blue -16, turquoise +19, sky -11, neutral slightly cool (b* -2). Tim Gray: sky -34, cyan -26, while magenta and purple go the other way +16...+26 (to red). spektrafilm: sky -12/-19, purplish blue -19/-20, yellow-green -22/-14. Consensus: **sky and purplish blue to cyan**. Magentas disagree (Maraver +/-5, TG +16...+26). Maraver [opinion]: "red shift results in orange-tinted skin... desaturates many hues... evenly". The "slide-like" saturation usually attributed to Ektar [opinion, common lore] **is not visible on a chart**: chroma <= reference in both Maraver and the model.
**Simulation:** (a) `[[943,97,-16],[32,963,30],[-23,53,994]]`, tint nearly neutral 1.02 / 1.01 / 0.97. 4.5 -> 3.9; residual in blue 10.0 and cyan 7.8, i.e. all in the blue sector.

### Fuji: Fujifilm 200 (new), C200, Superia X-tra 400, Pro 400H
- **Fujifilm 200** [measured, Maraver]: close to ColorPlus in direction but milder (|dh| 7.8). Matrix `[[950,129,-55],[48,1007,-30],[10,-16,1029]]`, tint 1.11 / 1.03 / 0.86 (warm, yellow). 4.6 -> 3.3. Fits a matrix well.
- **C200 / X-tra 400** [model]: the only ones with chroma **above** reference (1.07-1.15), especially in darks (1.20-1.31 at L < 45), and more contrasty than Kodak in the midtones. X-tra matrix (CA2) `[[857,234,-66],[14,962,48],[-155,145,1034]]`: strong cross-coupling of the blue channel. **No real chart.**
- **Pro 400H** [model]: Cr 0.97-0.99, matrix (CA2) `[[1022,218,-216],[-2,992,35],[8,-4,1020]]`. No chart.

### Lomography Color Negative 400 - Maraver
[measured] Saturated (Cr 0.87), "blue <-> gold" axis almost like ColorPlus: sky -28, blue flower -27, purplish blue -27, cyan -19, foliage -17, green -13, neutral slightly warm (b* +2). Maraver [opinion]: "likely a modified version of [UltraMax]... speculative". By matrix it is not UltraMax: `[[1084,232,-292],[17,992,14],[-17,40,1001]]` vs `[[1218,-15,-179],...]`. 4.9 -> 3.4, fits well.

### CineStill 800T / Candido 800 (Vision3 500T) - Maraver under non-tungsten light
[measured] Primarily **WB mismatch plus crossover**: greys blue-green (a* -14, b* -8 at L 27-51), light skin nearly colourless and cool (Cr 0.15, dh -77), foliage and green toward cyan (+19...+38), sky and blues -40, moderate red -27. Tint 0.76 / 1.12 / 1.11. Tone plus matrix leaves **7.2 dE** (blue 14.9, light skin 13.2). spektrafilm with a neutral print shows something entirely different (|dh| 7-10). So "800T look in daylight" = WB for 3200K plus different channel curves. **Not achievable with a matrix**: needs a WB shift and per-channel curves. Halation is a separate spatial effect, absent on a chart.

### CineStill 50D - Maraver
[measured] |dh| 17.6: sky -44, blue flower -59, purplish blue -34, skin +26...+29 (to yellow), magenta Cr 0.37, mid-greys green-yellow (a* -12, b* +7). Tone plus matrix 4.0, per-channel curves bring it to 2.8. Partly matrix-friendly.

### Vision3 250D (closest relative of "cinema film in daylight") - spektrafilm only
[model] |dh| 7.7 / 5.6, Cr 0.91-0.92, matrix (CA2) `[[1009,96,-81],[-4,982,47],[3,68,953]]`. **No real chart.**

---

## 7. What a matrix does and does not do: summary and ranking

Residual dE (Maraver data): **0** tone only -> **B** tone + matrix -> **C** matrix + per-channel curves.

| Film | 0 | B | C | Verdict |
|---|---|---|---|---|
| LomoChrome '92 | 7.2 | **2.5** | 2.2 | matrix (strong desaturation 0.70) plus contrast |
| Fujifilm 200 | 4.6 | 3.3 | 2.9 | matrix plus WB |
| Lomography 400 | 4.9 | 3.4 | 3.4 | matrix plus WB |
| Film Onehundred 100 | 5.4 | 3.4 | 2.4 | matrix; per-channel curves help |
| Portra 400 | 5.4 | 3.5 | 3.1 | matrix plus WB plus soft contrast |
| Portra 160 | 4.3 | 3.6 | 3.0 | mostly curve and saturation |
| ColorPlus 200 | 5.3 | 3.9 | 3.5 | matrix plus WB; residual foliage and purple |
| Ektar 100 | 4.5 | 3.9 | 3.8 | residual only blue and cyan (sector) |
| UltraMax 400 | 5.2 | 3.9 | 3.6 | matrix plus WB |
| CineStill 50D | 7.7 | 4.0 | 2.8 | matrix plus per-channel curves |
| Gold 200 | 6.9 | 4.6 | 3.1 | matrix plus per-channel curves (warm shadows) |
| ProImage 100 | 7.7 | 5.1 | 4.3 | doubtful data |
| Phoenix (I) | 14.1 | 6.5 | 3.7 | **needs per-channel curves and sector tables** |
| CineStill 800T | 9.0 | 7.2 | 5.1 | **needs WB, per-channel curves and tables** |

What all Kodak and Lomography films share and **a matrix does**: a negative R<-B element (-180 to -300) plus a positive R<-G. Blue stops "reddening" and moves to cyan, warm becomes warmer. That is the "blue-gold" axis, and it is linear.
What **a matrix does not do** (by number of films where it tops the residual): blue and cyan patches (Ektar, Portra 400/160, UltraMax, Lomo 400, ProImage), purple (ColorPlus, Portra 160, Phoenix), foliage (Gold, ColorPlus, Fuji 200). A matrix rotates hue "all at once". To send the sky to cyan without turning skin green you need **per-hue-sector int8 corrections** in Backup block `0x00030001` (notes/hue-tables.md).
Luminance-dependent tint (warm/olive shadows of Gold/ColorPlus/Portra 400, green-yellow middle of Phoenix and CineStill 50D, cold-green 800T): **neither a matrix nor global contrast**. Not available on the camera unless per-channel curves are found.

---

## 8. Transferring to the NEX-3N (hypothesis at the time of writing)

The matrices above are "neutral render -> film" in linear sRGB. If a camera slot maps camRGB to a linear sRGB-like output (an assumption at this stage), the new slot matrix = `M_look * M_cam`, rows renormalised to 1024. Computed from the stock M0 (`1292,-180,-88 / -44,1340,-272 / -24,-108,1156`), `data/looks/slot_candidate_matrices.json`:

| Look | Slot (int16, 1.0 = 1024) | Tint R/G/B -> move into WB shift |
|---|---|---|
| Portra 400 (Maraver) | `1146,10,-132 / 53,1277,-306 / -21,-50,1095` | 1.04 / 1.05 / 0.91 -> toward A (warm) |
| Portra 160 (Maraver) | `1307,-147,-136 / -39,1269,-206 / -6,-129,1159` | 0.92 / 1.07 / 1.01 -> toward G |
| Gold 200 (Maraver) | `1520,-24,-471 / 73,1232,-281 / -17,-114,1156` | 1.05 / 1.08 / 0.87 -> A plus a little G |
| ColorPlus 200 (Maraver) | `1353,133,-462 / 31,1245,-252 / -9,-171,1204` | 1.06 / 1.04 / 0.90 -> A |
| UltraMax 400 (Maraver) | `1542,-215,-303 / -13,1324,-287 / -9,-170,1203` | 0.91 / 1.08 / 1.01 -> G |
| Ektar 100 (Maraver) | `1186,-37,-125 / -2,1250,-224 / -55,-31,1110` | ~neutral |
| Lomography 400 (Maraver) | `1365,144,-484 / -22,1295,-249 / -47,-50,1121` | 1.07 / 1.02 / 0.91 -> A |
| Fujifilm 200 (Maraver) | `1194,8,-178 / 18,1311,-305 / -11,-131,1166` | 1.11 / 1.03 / 0.86 -> A |
| Portra 800 (model, CA2) | `1340,-108,-208 / -60,1272,-188 / -20,-21,1065` | ~neutral |
| Vision3 250D (model, CA2) | `1271,-43,-204 / -48,1280,-207 / -21,-12,1058` | ~neutral |

Phoenix and 800T are deliberately excluded: a matrix gives less than half the effect there (section 7). Contrast: Maraver's curves are distorted by normalisation, the model's come from paper. So **contrast should be tuned against your own reference scans**, not these numbers. Saturation: the matrix equivalent is 0.9-1.0 for nearly all. The visible "paleness" of Portra 400 / Ektar / Portra 160 in chroma (Cr 0.76-0.79) comes from the soft curve and desaturation of blues/magentas, not from a global multiplier.

How these candidates were actually used on the camera: notes/house-phoenix-looks.md and notes/colour-v6.md.

---

## 9. Gaps and unverified items
- **Phoenix II, SantaColor 100/800, CineStill 400D, Superia (real, not modelled), Lomo 800, Aerocolor:** no published charts (within accessible search).
- Reddit (r/AnalogCommunity, r/spektrafilm) and Photrio cannot be read automatically (login wall, Cloudflare); single posts may exist there. Check manually in a browser.
- In the pixls thread after post #736, a user promised a "Portra 400 <-> Fuji DPII, chart, -3...+3 EV" series ([pixls](https://discuss.pixls.us/t/spectral-film-simulations-from-scratch/48209?page=36)). Not available at measurement time; check later.
- Maraver promised a "Part 2" with other films [source, subtitles]. If it includes Phoenix II or Santa, it closes the main gaps.
- The most reliable path for your own films (Phoenix II, Santa 800, UltraMax) is to **shoot a chart yourself** on the same roll as the subjects, next to a NEX frame. That replaces all of section 6 with a direct "digital -> your own scan pipeline" measurement and removes the confounds of someone else's scan and normalisation.

## 10. Reproducing

Analysis scripts not included. Outline of the pipeline that produced `data/filmcharts/`: extract patches from video frames with an overlay check; fit models 0/A/B/C (-> `maraver_results.json`); two-stage tone-then-matrix recipes (-> `maraver_recipes2.json`); render spektrafilm charts per film and paper (-> `sf_out_*.json`, `sf_results.json`, `sf_recipes2.json`); Tim Gray patches (-> `tg_*.json`).

Pitfalls: Reddit `search.json` returns 403 even via curl_cffi (login required). Photrio and RFF are behind Cloudflare (RFF opens via Playwright). YouTube timedtext is empty without a PO token; subtitles via `yt-dlp --write-auto-subs`. In colour-science 0.4.6 Bradford is `method='Von Kries', transform='Bradford'`. In spektrafilm `lut_mode=True` is required, otherwise it auto-exposes per frame. The spektrafilm venv is ~2 GB (PySide/napari).
