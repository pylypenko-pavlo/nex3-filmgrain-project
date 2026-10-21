# Best-angles re-hunt (2026-10-14) — the parametric lever we under-weighted

Fresh ranking of every route to the film-grain goal, run after the full pipeline + effect map was
complete (`pipeline-and-effects.md`). Mandate: with the whole picture in hand, find the best angle and
any false-negative. Offline analysis only — nothing built or flashed this pass; referenced probe `.bin`s
pre-exist. Raw: `~/nex3n-dump/work/pipeline-research/05-best-angles.md`.

---

## Verdict

The owner's instinct holds — there **is** an under-weighted angle and a real false-negative — but
**not on the injection side.** Every *injected* route still converges on the same VLIW-output wall or the
16-byte scalar ceiling. The missed lever is **parametric**: shape the camera's own sensor noise into a
grain-like texture using Backup blocks we can already write, with the proven colour-slot delivery. No
code, no VLIW, fully reversible — and **shippable today.**

The false-negative: the project rejected "digital noise" as a grain substitute — but that judgement was
about **raw, unshaped** noise. **Shaped** noise (chroma killed, lifted into midtones, cored for bite) —
which is visually what film grain *is* — was **never built or measured** (C-NR-019 left open). That is
the test to run.

---

## Ranking (feasibility · effort · reversibility · trigger-isolation · grain quality)

| # | Angle | Shippable? | Quality | Verdict |
|---|---|---|---|---|
| **1** | **Parametric — shape native sensor noise** | **now** | MED (never measured) | **RECOMMENDED** |
| 2 | VLIW `cc38` output-store probe (audit FN-1) | needs unlock | HIGH *iff* it unlocks | **runner-up (research)** |
| 3 | Scalar per-tile speckle (audit FN-2) | now, but sparse | LOW (dust, not grain) | cheap check only |
| 4 | Baked noise tile (audit FN-4) | needs unlock | HIGH | settle the cap, but VLIW-dependent |
| 5 | HW dither/quantise register in yknr engine-config MMIO | — | — | **CLOSED — no such register (firm negative, ran 2026-10-14)** |

Notes on the ranking:
- **Angle 1 (parametric)** — gate NR (`0x3004a`→0, NR-3 / C-NR-011) so sensor noise survives → kill its
  chroma with the proven chroma-by-luma LUT `0x30004/5` (E-0067 reaches the JPEG, 5/6 styles) → set bite
  with sharpen coring `0x30106` → lift into midtones with a tone k-curve (C-TONE-007). All Tier-A Backup,
  reversible. The quality is MED and, critically, **unmeasured** — that's the whole point.
- **Angle 2 (VLIW)** — the decisive "VLIW unreachable" test genuinely never ran (E-0077 hit dead filler;
  E-0079's r19 probes were underpowered). Best entry is **`sa_yknr`**, *not* `sa_apollo4` (upstream of NR
  → grain would be re-smoothed, bigger surface doesn't help) and *not* `sa_sftfcs` (best *trigger* but
  more VLIW-bound). `cc38force.bin` already built. Even on unlock, two unknowns remain (does the store
  accumulate; where is the noise source).
- **Angle 3 (scalar)** — audit FN-2 is a legit catch (r13 ping-pongs between 2 values; the ring address
  and r8/r9 were never tried; `r8seed.bin` built), **but** the 16-byte ceiling still caps it at *sparse
  dust*, not grain. The grain docs over-read this as "grain is BACK" — correct that: FN-2 removes one
  blocker, it does not deliver grain.
- **Angle 4 (baked tile)** — the "~53 KB writeFile cap" is indeed unverified (one no-flash senser session
  settles it), but DMA **overwrites** rather than adds, so consuming a tile needs the same VLIW unlock as
  Angle 1/2.
- **Angle 5 (dither register) — RAN, CLOSED.** Full disasm of stock `sa_yknr` engine-config: every write
  is benign — the `0x48xxx` DMA register file (channel/go/descriptor/status), `0x40xxx` AGU geometry, and
  `0x9xxx` SRAM config structs + the `0x91f0` ring. **No dither / quantise-step / rounding / noise / bias
  / clean-vs-textured register exists.** NR cleanliness is *computed* (reciprocal-division magic
  `0xcccd/0xaaab/0x9249…` = ÷3/5/7/9 + the VLIW taps), not gated by a HW mode bit — nothing to flip. The
  best mode-shaped reg (`0x48218←{2,0x3e}`) is a DMA byte-lane mask downstream of all pixel math (flipping
  it corrupts transfer geometry, not grain), and the marshal copier at file `0xd80` never even writes the
  `0x48xxx`/`0x40xxx` world. **This removes the last "injection without VLIW" hope.** (DRO / JPEG-quant /
  mode-9 second LUT remain amplifier layers under Angle 1, not hosts.)

---

## Single recommended next move — EXP-P (parametric) — PREMISE FIRMWARE-VALIDATED

**De-risk done (offline, 2026-10-14):** the one fear — that `0x3004a`→0 gates only an *early* NR while
the always-on late `sa_yknr` re-smooths luma before encode — is **disproved in code.** Findings
(`07-expp-noise-survival.md`):
- **`0x3004a +0xD2..+0xDC` IS the yknr ISO-enable window** — the late luma-NR's own on/off gate, not a
  separate early NR. Enable predicate `0xc3516760` reads the window from the RAM image of `0x3004a+0xC0`;
  zeroing those bytes makes `lo ≤ ISO ≤ hi` fail at every ISO → **yknr off → native noise reaches the
  JPEG.** ("NR-3" = the yknr off switch.)
- **yknr strength = writable Backup table `0x3004c`** (13 tables × 11 B, C-NR-007), ISO-interpolated by
  builder `0xc35162a0`. So yknr can be **weakened** (`0x3004c`→low) or **killed** (`0x3004a` window→0) —
  both pure Backup, no module/code edit. (The module has no strength/dither toggle — `06-…` confirms.)
- **HC Mono is effectively EXP-P already running:** E-0047's near-native HP-std 2.7–3.4 / ACF ≈0.58 is
  unsmoothed demosaiced sensor noise (yknr in its bypass lane) amplified by the steep tone curve — real
  proof noise survives to the JPEG in a shipping mode.

**The recipe (one Tier-A Backup session, high ISO — all writable Backup, reversible):**
1. **Kill the late luma-NR:** `0x3004a +0xD2..+0xDC → 0` (zero only that range — `+0xE7` is KKNR, shared;
   polarity/3rd-pair not fully nailed, so zero the whole `+0xD2..+0xDC` to be safe). Or tune via
   `0x3004c`→low instead of a hard kill.
2. **Optional — let native amplitude through:** weaken G-NR (`0x30010/b4`, `0x3001b/be +0xD7`,
   hi-gain `0x3011f/0x30049`) *(code-read only, unmeasured)*.
3. **Shape the surviving noise into grain:** chroma-kill `0x30004/5` (proven to reach JPEG, E-0067) +
   steep tone k-curve (lift shadows/midtones, C-TONE-007) + sharpen coring `0x30106` for bite.
4. Shoot a flat mid-grey + a real scene at high ISO; **measure** HP-std and ACF against the in-house
   ACROS yardstick (E-0047: HP-std 2.7–3.4, ACF lag-1 ≈ 0.58). Stranger reads it as grain → **ship**
   (colour lineup + grain = the whole public post).

**Runner-up, same camera sitting:** flash the **`ce70` output-store probe** (one byte `0xce70: e3→03`,
built this round) to settle whether the VLIW output is reachable. ⚠️ The old **`cc38force` is DEAD** —
the VLIW decode (below) proved `0xcc38` is upstream of the store and writes two dead registers; do NOT
flash it. `r8seed` (scalar per-tile source) still valid as a secondary. Revert = stock `54acf298`.

**Offline (no flash):** ~~Angle-5 dither-register pass~~ **done — closed, no register.** Probe-target
results below.

---

## Probe-target results (offline, ran 2026-10-14)

All four follow-up probes ran (B/C/D here; A folded into the EXP-P section above). Raw:
`~/nex3n-dump/work/pipeline-research/0{7,8,9}-*.md`, `10-sa-star.md`.

**B — VLIW decode of `0xcc38..0xce80` (`08-yknr-vliw-decode.md`) — the actionable one.**
- **The real output store is the `op5.a07.b03` family in S4** (`0xcd80/cd88/cd98/cdd0/ce30/ce38/ce70`,
  last commit `0xce70`); `r3` is the write-only output-stream pointer = the SRAM `0x9000`/`0x9800` tile
  window. DMA-out is the downstream scalar kick (`0x48234←0x9000`, `0x48230←1`).
- **`cc38force` is DEAD** — `0xcc38` is upstream (no op5; two op3 reads + a clamp) and both regs it
  writes (r28, r30) are overwritten unused at `0xcc40`. It could never move the output. (Not an op3-`a`
  issue — op3-`a` IS a real operand, varies module-wide.)
- **Decisive probe = `0xce70` S4, `op5.a07.b03 → op5.a00.b03`, one byte `0xce70: e3→03`** — forces the
  final store's *source*, never the `b03` pointer → no hang risk; a flat-grey wall going flat/black/clipped
  proves the block drives the visible output. Whole-tile amplifier cross-check: `0xcd38` S4; second stream
  `0xccb0` S4.
- **r19 is vestigial here** (2 writes, 0 reads in-block) → E-0079's "double-r19" probes were structurally
  inert. The real luma accumulator is **r1** (op4-mul ×14; op3-stream→op4→r1→op1-pack→r2→op5-store). The
  **grain add-slot** = `op7 Grain→r1` just before the final pack at `0xce68` (must displace a housekeeping
  lane — the block has zero idle slots). Corrects C-DSP-014 ("op4 always→r19" is sftfcs-specific).

**C — cross-model sabin diff (`09-cross-model-sabin.md`) — clean negative, favours the 3N.** No sibling
(a6000/a7II = CXD90014, a6400/a7III = CXD90045, NEX-6 = CXD4132 twin) exposes any grain/dither/texture
control; zero string hits across all six. Shared kernels are structurally frozen generation to generation
(recompiled, not re-architected); later `sa_apollo` added one core-tile but the same 13 kernels, no new
noise/dither stage. **The 3N's `sa_yknr` has no successor in later bodies** (NR folded into lfnr/zoom_nr)
→ later designs make the luma-NR route *less* reachable → **the 3N is the most favourable body for the
noise-survival angle.**

**D — `sa_star` identified (`10-sa-star.md`) — NOT a host.** It is the **By-Pixel Super-Resolution**
engine behind **Auto Portrait Framing** (`Camera::Capture::STAR`, `Start_Super_Resolution`), codectype
0x1a — not astro. Grain-host NO on four grounds: undeliverable (473 KB ≈ 9× the ~53 KB writeFile limit),
writes a *separate* framed output (not the default SOOC JPEG), rare trigger (portrait-framing only), and
no code room (fixed-function super-res driver, same VLIW wall).

**Net:** the offline follow-ups closed the exploratory angles (C, D — both negatives) and made the
injection runner-up actionable (B — real probe = `ce70`, not the dead `cc38`). Nothing dislodges EXP-P as
the shippable-now move.

---

## The distinction to carry

- **Shippable today:** parametric / colour (Backup writes, proven delivery). This is the path to a
  publishable result *now*.
- **Needs the VLIW unlock:** every injection route (yknr, apollo, sftfcs, baked tile).
- **Correctly closed (not a false-negative):** the ARM-side injection path (E-0074) — stays shut.

*Analysis/ranking only; no binary built or edited, no flash. Cross-ref: `audit-2026-10-14.md`,
`pipeline-and-effects.md`, `grain-angles-overview.md`, `colour-slots-lineup.md`, `02-capture-pipeline.md`
(C-NR-011/019, C-TONE-007, E-0047, E-0067).*
