# Film grain-vs-luminance response (the amplitude envelope for procedural grain)

Measured 2026-10-15 from real film scans, for the PBE procedural-grain kernel. Film grain is
**luminance-dependent** (owner's insight): strongest in the lower-midtones, suppressed in deep shadows
(little exposed silver) and in highlights. The procedural grain amplitude must be modulated by this
curve, or it reads as flat digital noise, not film.

## The curve (normalized `filmResponse(luma)`)

Measured by: high-pass residual (`luma − gaussian_blur`), robust σ (MAD) per luma bin, edges masked out
(flattest ~55% by gradient), averaged over Portra 400/800, Ektar 100, ColorPlus 200 scans
(`~/nex3n-dump/filmcharts/flickr/`). Script: `~/nex3n-dump/work/filmgrain/measure_grain_vs_luma.py`.

| luma (0–255) |  8 | 24 | 40 | 56 | 72 | **88** |104 |120 |136 |152 |168 |184 |200 |216 |232 |248 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| response    |.22|.55|.87|.97|.99|**1.00**|.96|.96|.79|.70|.64|.55|.45|.24|.16|.09|

- **Peak at luma ≈ 88** (lower-midtone). Steep rise out of shadows (.22→.87 over luma 8→40), broad
  plateau 56–120 (≈.96–1.0), gentle decline through the highlights (.79 @136 → .09 @248).
- Shape is consistent across films (per-film σ differs — Ektar fine ≈2–5, Portra 800 coarse ≈12 — but
  the *normalized shape* is the same midtone-peaked curve). Grain *size* and overall *amount* are
  separate knobs (film stock / the kernel's amplitude); this curve is only the **luma envelope**.

## How the kernel uses it

Procedural grain formula (PBE VLIW, `12-pbe-grain-kernel.md`):
```
r15 += PRNG(position) · filmResponse(r15) · amplitude
```
- `PRNG(position)` — per-pixel pseudo-random (universal; present on flat/low-ISO areas too — this is why
  procedural beats sensor-noise, which NR cleans away before PBE, E-0081/arm test).
- `filmResponse(r15)` — **this curve**, as a small LUT indexed by r15's high bits (≈16 nodes above), or a
  cheap polynomial peaking at luma 88. Makes the grain look like film (midtone-peaked).
- `per-frame seed` — offsets the PRNG so the pattern differs between captures (a fixed pattern = digital
  "fixed-pattern noise", rejected). Seed source under investigation (`13-perframe-seed.md`): a VLIW-readable
  counter, a frame-varying param, or a content reduction (per-scene).
- `amplitude` — overall strength knob (needs the VLIW shift op, undecoded — the open amplitude-control gap
  from `12-pbe-grain-kernel.md` §4).

## Status / caveats

- The curve is from *print/positive* film scans (what the final image looks like) — the right domain, since
  we modulate the output pixel. [measured, one pass; JPEG/downscale may flatten absolute σ but preserves the
  shape].
- A cleaner re-measure from a scanned **step wedge** (uniform patches at known densities) would tighten the
  shape; the Flickr-scan method already gives a clear, film-consistent envelope.
- Cross-ref: `12-pbe-grain-kernel.md` (kernel), `13-perframe-seed.md` (seed), E-0081 (injection reachable),
  `best-angles-2026-10-14.md`.
