# Grain — wide / lateral re-analysis (2026-10-13)

A deliberate step **all the way back** from the injected-noise mechanism we have been inside for
many sessions. Written to *challenge the framing*, not re-confirm the blocked routes. Companion to
`grain-angles-overview.md` (the A1–A9 status map — knows it, looks past it), `dsp-grain-scope.md`
(S1–S4 detail, E-0074…E-0077), `scalar16-grain-ideas.md`, and the colour levers in
`colour-slots-lineup.md` / `film-sim-targets.md`. OFFLINE, analysis only, no binary touched.

Scope: NEX-3N fw 1.00 / CXD4132. Everything here rests on existing atlas claims (cited by ID);
nothing new was measured. New angles are marked with honest confidence and cost.

---

## 0. TL;DR verdict

**"A texture a stranger reads as film grain" in the SOOC JPEG is reachable now, cheaply, on the
already-solved reversible colour surface — but not as *injected* per-pixel noise.** The cheapest
path is to **expose and shape the sensor noise that is already in every frame** (NR/ISO gate +
chroma-by-luma LUT to make it luma-dominant + sharpen/coring to set its "bite" + tone/matrix to
lift it into the midtones). This needs **zero DSP code, zero VLIW, zero pixel-write** — only Backup
and (optionally) p3 levers we already own and revert.

**True injected grain** (aperiodic, exposure-independent, midtone-uniform) stays blocked exactly
where the overview says: 16 B/core scalar ceiling with no loader, and a VLIW path with no grain
source. The wide look did **not** find a new injection route that beats those — but it found that
we were solving the wrong problem (synthesising a noise source the chip already has) and that a
broad, reversible lever surface (**sharpen, JPEG quant, NR-gate, DRO**) was never once tested for
texture. Those are the genuinely new, cheap things to try.

---

## 1. The reframed problem statement

Old framing (what we optimised against for many sessions):

> *Get a per-pixel pseudo-random value N and ADD it to luma inside a DSP module, delivered
> reversibly via `/setting`.*

That framing baked in four assumptions. Reframed:

> **Produce, in the SOOC JPEG, a luminance micro-texture that a non-expert reads as "film grain,"
> using the cheapest controlled, reversible lever — whether that texture is injected, exposed, or
> emergent.**

The reframe moves the goal from a *mechanism* ("additive PRNG into luma") to a *perceptual end*
("reads as grain"), and opens the door to textures the camera can *already* make.

What a stranger actually reads as "film grain" (not what a signal engineer means):
- aperiodic luminance speckle visible in flat **midtones** (not just shadows);
- **low chroma** (film grain is near-monochrome; colour mottle reads as "cheap digital");
- a characteristic **size** (clumped, ~1.5–3 px at web resolution — not single-pixel hiss, not big
  blotches);
- present across the frame, **not** obviously tied to one 8×8 or 128×8 grid (periodicity kills it).

Keep this list; every angle below is judged against it, not against "is it a real PRNG."

---

## 2. The assumptions we challenge — and whether each holds

| # | Assumption we operated under | Verdict after the wide look |
|---|---|---|
| **A** | Grain must be **injected** per-pixel noise. | **FALSE / drop it.** The sensor already supplies a true, free, per-pixel, aperiodic noise field every frame (this is *why* NR exists). We spent the project trying to synthesise a PRNG the chip does not contain (C-NR-025) when the real thing is upstream of NR. The lateral move is to **shape**, not inject. (§3, §4-#1.) |
| **B** | `sa_yknr` is the wrong/limited place; a better host module exists (A8). | **The place is RIGHT; the *mechanism* is the limit.** `sa_yknr` is the **last full-frame luma stage before the encoder**, and the encoder is a handle-only HW coder (C-JPEG-002/004). Grain after YKNR needs no spatial correlation (C-PIPE-025); grain *before* it (pbe_work, kknr, spica) is smoothed by YKNR → must be pre-correlated and ≥ native amplitude to survive (C-PIPE-025). So **earlier `sa_*` hosts are worse, not better** — A8 is demoted by pipeline order, not promoted. There is no later software host (encode = HW). |
| **C** | Native sensor noise = "digital noise" ≠ film grain, so it was **rejected**. | **PARTLY FALSE — rejected too early.** What was rejected was *raw, unshaped* high-ISO noise (luma+chroma, shadow-weighted, un-sharpened). Film-vs-digital difference is *structure* (`film-sim-targets.md` §note-on-grain) — and structure is exactly what our chroma-LUT + sharpen/coring + tone levers manipulate. Shaped native noise is a different object from raw native noise. Not yet tried. (§4-#1.) |
| **D** | The only reversible delivery surface worth using is the `/setting` module edit (+ the Backup colour blocks). | **FALSE — the surface is much wider and under-used.** Reversible/recoverable and *never tested for texture*: sharpen ladder **`0x30106`** + Apacon regs `0x78b0..` (C-CTRL-018, Backup, Tier A); **NR ISO-window `0x3004a`** / NR runtime gate `CommonRam+0x15C` (C-NR-011, C-CTRL-017); **JPEG quant tables** in p3 av-cam `0x54afb2` (C-DSP-023, Tier B flash); DRO/BDRO strength (C-PIPE-011, lever unmapped). (§3.) |
| **E** | "Film grain" means true film grain (aperiodic, exposure-independent, uniform over the midtones). | **Over-scoped for the finish line.** The finish line (`START-HERE`) is a Reddit "X100-for-the-poor" post a stranger reproduces. A stranger judges the *look of the posted shots*, which are high-ISO-ish anyway. Exposure-independent midtone-uniform grain is a purist target that the hardware makes expensive; a convincing high-ISO grain look is cheap and shippable. (§5 verdict.) |
| **F** | The 16-B scalar primitive is useful only as a (too-small) per-pixel loop. | **Mostly holds, but one use is unexplored:** use the 16 B not to *run a loop* but to *poke a register* — i.e. enable a hardware quantise/dither block **if one exists** (S2, never pursued). Probe S already proves a scalar MMIO poke works (it writes `0x48208`). This is the only injected-side idea the 16-B ceiling does not kill, because it needs no loop. Confidence that such a block exists: **low-unknown** (no evidence found, not ruled out). (§4-#4.) |
| **G** | The grain source problem is "no PRNG → synthesise one." | **Wrong problem.** The system has exactly one abundant aperiodic per-pixel source — the sensor — and our whole mechanism fight (self-dither has no entropy; DMA-LUT needs a stream we can't set up; xorshift needs 72 B we don't have) is an attempt to *recreate* it downstream. Reframed: the source is not missing, it is being *removed* by NR. Stop removing it; shape what remains. (§4-#1.) |

The two that actually move the project are **A/C/G** (shape the sensor noise) and **D** (a wide
unused reversible lever surface). **B** is the important *negative*: stop hunting for a better
injection host — there isn't one.

---

## 3. Wide map — levers / surfaces / stages we have NOT fully explored

Pipeline order (C-PIPE-007 + stage table, 02 §): raw → WB → **3×3 matrix** → **base-gamma HW LUT**
→ **contrast/style curve** → **YCbCr/chroma × sat** → **hue** → [ **NR: YKNR/KKNR/PBE** → **sharpen:
YAP/coring/Apacon** → **DRO: BDRO ×2** → **picture-effect** → **resize: SPICA** ] → **develop/YC
canvas** → **HW JPEG encode**.

Grain-relevant levers along it, with how fully we've used each **for texture** (not colour):

| stage / block | lever | surface + tier | reversible? | used for texture? | grain relevance |
|---|---|---|---|---|---|
| NR gate | ISO window `0x3004a`; runtime `CommonRam+0x15C`; NR level `[OBJ+0x15c]` | Backup A / runtime | yes | **no** (only noted it "leaves digital noise") | **the exposure tap for native grain** — decides where noise survives |
| chroma-by-luma 3D-LUT | `0x30004/5` (per-Y Cb/Cr scale) | Backup A | **proven** (E-0067) | colour only | **kill chroma of the noise → luma-dominant = film-like**; shape per-Y so midtone noise survives |
| sharpen | `0x30106` ladder + Apacon `0x78b0..` (`YC_SetModeDependent_*`) | Backup A + p3 | yes (A for ladder) | **barely** (C-NR-019: "no sharpness measured") | **sets grain "bite"/size**: low coring + gain amplifies HF noise into visible speckle |
| tone / base gamma | k0..k6 curves `0x5b006a`; HW LUT `0xf4015300` | p3 B (proven precedent k0) | yes (reflash) | colour/tone | **lifts shadow noise into the midtones** (grain must live in midtones) |
| DRO | BDRO ×2, `SetBdroIdtData` | unmapped strength | unknown | **no** | local-contrast boost raises midtone noise visibility; strength lever not located |
| JPEG quant | quant table (zigzag order) av-cam `0x54afb2`; `src/dgi_jpeg_qtable.c` | p3 B | yes (reflash) | **never** | coarse HF-AC quant → structured HF texture/dither (block-correlated — see caveat) |
| matrix row-sums / sat | `0x30001/08`, sliders `0x0107xxxx` | Backup A | proven | colour | overall chroma of noise; mild |
| DSP module (`sa_yknr`) via `/setting` | scalar 16-B poke; VLIW free lanes | /setting A-ish | **proven delivery** | pixel-write proven (Probe S) | injected route — **blocked** (16 B ceiling / no VLIW source), see overview |
| HW quantise/dither register (if any) | poke via 16-B scalar stub | /setting A-ish | n/a | **never looked** | the one injected idea the 16-B ceiling doesn't kill (S2) — existence unknown |

**Delivery-surface answer (assumption D):** `/setting` is **not** the only reversible surface.
The **Backup attr-08/0x60 block set** (sharpen `0x30106`, NR gate `0x3004a`, chroma-LUT, matrices,
sliders) is a *large, proven-reversible, barely-used-for-texture* surface, and **p3 whole-partition
flash** (28/0, recoverable) reaches tone curves, Apacon code and the JPEG quant table. Forbidden
stays forbidden (p8, p1, `dmode`, env.txt LD_PRELOAD, calibration/defect blocks, `0x30056/24/4c`).

**Dead ends confirmed by the wide look (don't reopen):**
- **Live observability** to close the VLIW model gap: MSDump-to-card is **CLOSED NO** (C-MOD-032:
  retail `/mnt` is a ramfs, not the card). No emulator has the SA-DSP engine. So the VLIW
  output-luma bundle can only be found by an on-camera probe ladder — no offline shortcut exists.
- **A better injection host module (A8):** pipeline order (C-PIPE-025) makes every candidate worse
  than `sa_yknr`. Drop it.

---

## 4. Ranked NEW / reframed angles (honest feasibility + cost)

### #1 — Expose + SHAPE native sensor noise ("grain from what's already there") — **RECOMMENDED**
**The lateral move.** Do not inject; **stop NR from deleting the sensor's own aperiodic noise, then
sculpt it to read as grain**, using only levers we own and revert:
1. **Gate NR** so native luma noise survives in the target ISO band (Backup ISO window `0x3004a`,
   and/or NR level) — C-NR-011, C-CTRL-017. This is the entropy source. It is **real, per-pixel,
   aperiodic, and free** — the thing C-NR-025 says we cannot synthesise.
2. **Kill the chroma** of that noise with the proven chroma-by-luma LUT (`0x30004/5`) so it reads as
   near-monochrome luminance grain, not colour mottle (E-0067 proves the LUT reaches the JPEG and
   can shrink chroma per Y). This is the single biggest "digital → film" structural fix.
3. **Set the grain size/bite** with the sharpen lever (`0x30106` / Apacon): low coring threshold +
   modest gain turns fine hiss into clumped, visible speckle. (Under-tested — C-NR-019.)
4. **Lift it into the midtones** with tone (k-curve shadow lift) so grain is where the eye expects
   it, not only crushed into shadows.

- **Feasibility:** HIGH — every lever is already reachable and reversible; #1/#2 are Tier A Backup,
  proven surfaces. No DSP code, no VLIW, no pixel-write, no p8.
- **Cost:** low (a Backup write session + chart/shot iteration). Ships on the colour surface.
- **Honest limitation:** native noise is **ISO-dependent** (strong only at high ISO) and
  **shadow-weighted**, whereas true film grain is exposure-independent and midtone-uniform. So this
  gives a *convincing high-ISO grain look*, not exposure-independent grain. For the Reddit finish
  line that is almost certainly enough; state the scope ("grain look in the high-ISO band") plainly.
- **Why we tunnel-visioned past it:** the owner rejected "digital noise" early (`07`, `START-HERE`)
  — but that was raw noise, before chroma-kill + sharpen-shape + tone-lift. Shaped ≠ raw.

### #2 — Sharpen/coring as a dedicated grain-texture lever — **cheap, pairs with #1**
Treat the sharpen stage (`0x30106` ladder + Apacon `0x78b0..`, C-CTRL-018/ C-ISP-007) as a *texture*
control, not a detail control. With NR gated (from #1), coring threshold and gain set how much HF
noise becomes grain and how large the clumps read. The executor is unknown but the **params are
ARM/Backup** and largely reversible — we can sweep them without decoding the executor.
- **Feasibility:** MEDIUM-HIGH (lever exists and is reachable; response is unmeasured, C-NR-019).
- **Cost:** low. **Best used as the "bite" knob on top of #1, not alone.**

### #3 — JPEG quantisation-table texture — **new, cheap, but weak alone**
The still encoder is a HW coder reading quant tables in **p3 av-cam** (`0x54afb2`, zigzag order;
`src/dgi_jpeg_qtable.c`; C-DSP-023, C-JPEG-004). **Never touched.** Coarsening the high-frequency AC
quant steps injects structured HF energy ("mosquito"/dither texture) into every 8×8 block.
- **Feasibility:** MEDIUM (p3 reflash, reversible; table location known, format standard).
- **Honest quality:** the artefact is **8×8-block-correlated** — periodic at the block grid, which
  is the opposite of aperiodic grain (fails the periodicity test in §1). On its own it reads as
  "low-quality JPEG," not film. **Value:** as a *roughening* layer under #1 it can add fine bite
  cheaply; as a standalone grain source it's a no. Flag it as a tried-and-honestly-weak lever.

### #4 — 16-B scalar stub used to ENABLE a HW quantise/dither block (not to loop) — **unknown, one probe**
The only *injected* idea the 16-B ceiling does not kill. Probe S proves a scalar MMIO poke reaches
effect (it writes `0x48208`). If the SA engine has a quantise/round/dither register (common in
gamma/quantise hardware; S2 in `dsp-grain-scope.md`), **16 B is plenty to set it** — no loop, no
grow, no VLIW. The engine then does the per-pixel work for free.
- **Feasibility:** UNKNOWN. **No evidence such a register exists** (grep of pipeline/module/questions
  docs: nothing on "dither"/"quantize" in the SA engine) — but it was never searched for in the
  module scalar/engine-config code either. Honest: not ruled out, not supported.
- **Cost to resolve:** one offline pass over `sa_yknr`'s engine-config writes (which MMIO offsets the
  scalar sets around `0x48200/08/30/34` and `0x40000..`) looking for an unaccounted round/dither
  field; then one reversible `/setting` probe. Low cost to *check*, could be a clean win or a quick no.
- **Why it's new:** every prior scalar idea assumed "run the grain loop myself." This assumes "ask
  the hardware to." Different lever entirely.

### #5 — Hybrid: scalar seed + VLIW add — **analysed, fails for a nameable reason**
Tempting ("combine the two proven primitives"): scalar 16-B stub writes one per-tile value into an
engine-RAM slot/register that a free VLIW `op7` lane then adds to luma. **It does not give grain:**
one value added to a whole tile = a **uniform per-tile brightness step** → visible **128×8 tile
blocking**, not grain (and tile-boundary banding looks *worse* than clean). To vary per *pixel* the
VLIW would need an aperiodic per-pixel stream, which is the DMA-grain-LUT whose setup needs the
scalar DMA code that doesn't fit 16 B — the exact A6/A7 wall. So the hybrid collapses to the same
blockers. **Record it as closed-with-reason so it isn't re-proposed.**

### #6 — Wildcards (flagged, low priority)
- **Multi-frame / exposure tricks:** out of reach without new code on the capture sequencer; and
  multi-frame *averaging* would *reduce* noise (anti-grain). Skip.
- **Optical / lens:** physical, not a firmware lever; off-scope for a reproducible repo guide.
- **Accept a per-tile texture:** rejected — it's periodic at the tile grid (fails §1), the same
  reason #5 fails.
- **Picture-effect (`sa_sftfcs`) convolution via Backup `0x3010a`:** it's a *low-pass* blur
  (anti-grain), only active when Soft Focus is selected (conflicts with Creative Style), and the
  weights are already conflated in `style-grain-coupling.md` §5. Not a grain host.

---

## 5. Verdict — is "film-grain look in the SOOC JPEG" reachable, and by the cheapest path?

**Yes for the perceptual goal; no for the purist goal.**

- **Reachable now, cheaply:** a texture a stranger reads as film grain, via **#1 (shape native
  sensor noise) + #2 (sharpen bite) + the proven chroma-LUT**, all on the reversible colour surface,
  no binary modified. This is the **cheapest path to the perceived end** and it ships alongside the
  already-solved colour lineup — the full "X100-for-the-poor" post becomes *colour + a high-ISO grain
  look*, both reproducible and revertible. Honest scope to state in the post: the grain look lives in
  the high-ISO band and is shadow-weighted (it is shaped sensor noise, not exposure-independent
  emulsion grain).

- **Not reachable cheaply (unchanged):** true **injected**, exposure-independent, midtone-uniform
  grain. The overview's verdict stands — 16 B/core scalar ceiling with no loader (A2/A3), VLIW
  injection free but **no grain source** (A5 no immediate, A6/A7 scalar-DMA ceiling), and
  (E-0077) the known VLIW luma bundles show no effect with no emulator to close the model gap. The
  wide look **did not** find a new injection route that beats these. It found that we were solving
  the wrong problem.

**The one genuinely new injected idea worth a cheap check:** **#4** — whether a HW quantise/dither
register exists that a 16-B scalar poke can enable. Low cost to investigate offline, could be a
clean win or a fast no. Everything else injected is honestly blocked.

**Bottom line / what changed:** the project's grain wall is real *for injection*, but the goal was
mis-scoped and the lever surface under-used. The sensor hands us a perfect per-pixel aperiodic noise
field for free; NR deletes it; our levers can keep and shape it. Stop trying to rebuild that field
downstream. **Recommended next (all reversible, owner-present where a shot is needed):** (a) one
Backup session running #1+#2 — NR-gate + chroma-kill + sharpen-bite — and read the result on a
high-ISO midtone wedge; (b) in parallel offline, the #4 engine-register search. Keep the injected
VLIW/16-B tracks as the documented hard frontier, not the main line.
