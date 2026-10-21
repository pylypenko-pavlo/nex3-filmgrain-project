> SUPERSEDED (2026-10-21). The DSP-side grain route described here is closed: it is blocked by hardware
> (see the root README, 'Results: grain'). The route that shipped is the Linux LD_PRELOAD shim in
> `code/grain-shim/`, runbooks `atlas/grain-linux-*`. This page is kept for the engine/VLIW
> findings; its 'next steps' and 'active path' wording is historical.

# Grain roadmap — end-to-end (2026-10-16 synthesis)

## POTENTIAL SOLUTIONS (ranked, 2026-10-17) — two tracks to universal luma grain
Both reach the DSP engine that does per-pixel luma; neither needs ARM to touch DSP SRAM (the scalar does, C-DSP-020
bypassed). See `sa-dsp-isa.md` (ISA), `engine-command-table.md` (ring/engine detail).

- **Track A — BYPASS the engine (feed noise as a 2nd input stream).** Scalar-only, no engine-microcode authoring.
  DeepSeek-ranked #1 feasibility. Design (being built): scalar PRNG fills a free SRAM tile → append a 7th DMA-ring
  descriptor `{noise_tile, 0x40000000}` at `0x91f0` (batch is 6/pass, `cmp r8,#6` @0x1070 → widen to 7) → engine adds
  the stream per-pixel = grain. Needs: free SRAM region, ring-append widen, scalar per-frame seed, scalar code-cave.
  Final proof = 1 camera shot (does the engine combine additively?).
- **Track C — "Soft Focus = grain" (CONFIRMED path, 2026-10-17, `grain-sftfcs-confirmed.md`).** Camera-confirmed:
  **sftfcs chan-3 = the Soft Focus JPEG luma output** (E-0098, idle→banding). User-selected effect, normal shooting
  stays clean (owner: the BEST option). Inject per-pixel noise into r11/r17 (chan-3 store sources). Remaining: the
  per-frame seed source. This is the active path. (Also camera-confirmed: yknr chan-3 = luma but HIGH-ISO only;
  SPICA/HW writes base-ISO luma = not DSP-injectable. The engine has NO in-engine entropy — seed must come from scalar.)
- **Track B — BREAK the engine wall (author one add-syllable in Region B).** T-1 found: to add grain inside the engine
  you insert "one VLIW add-syllable in Region B before the output store." Needs decoding the engine command stream's
  Region B (the per-pixel program) enough to author that syllable — the engine ISA is undocumented (not in ma1co).
  Harder, but the cleanest true per-pixel grain. Parallel investigation.
- **Shippable now (no wall):** chroma grain via PBE chan3 (proven) + high-ISO luma via NR-bypass. Doesn't need A or B.


The single actionable picture of how film grain gets into the NEX-3N SOOC JPEG, after mapping the DSP VLIW route
to the stage level (E-0090). Supersedes the scattered grain docs for "what to do next."

## The pipeline split (the key realization)
The SOOC develop pipeline processes **luma and chroma in SEPARATE DSP stages**, each a programmable SA-DSP VLIW
engine whose per-pixel output reaches the JPEG (E-0081/84):

| plane | stage (module) | editable output | injection register | delivery byte (Backup 0x00bd0002) |
|---|---|---|---|---|
| **chroma** | `sa_pbe_work` (PBE) | `chan3` (clmp r15=clamp(**r0**)) @0x7318/30/60 | **r0** pre-clamp | 573 (`deliver_pbe.py`) |
| **luma**   | `sa_yknr` (YKNR)   | `chan18` (clmp r8=clamp(**r24**)) ×5 @0x4fe0… | **r24** pre-clamp | 597 (`deliver_setting.py`) |

Both are reached the SAME way: a few VLIW ops added before the clamp/store, in the clean microcode region
(≥0x6000 for PBE; the 0x3c00-0x6c78 region for yknr). Film grain is primarily LUMINANCE → the **yknr/chan18 path
is the real goal**; the PBE/chan3 path is the parallel chroma capability + the proof-of-mechanism.

## The one shared hard enabler: per-frame-random SEED
Per-pixel spread (luma LSBs) and luma-modulation (parabola) are cheap in-engine. The hard requirement is
**per-frame decorrelation at EVERY ISO** (incl. base, where sensor noise is too low to supply it). It needs a
**per-frame-random SEED in a microcode-readable register**, supplied by the scalar. This is WITHIN the scalar's
proven powers: the scalar can write engine CONFIG/command-tables (it does so normally) — only writing PIXELS is
closed (E-0086). So: a minimal scalar write of a per-frame value (frame counter / HW timer / LCG step) into a free
**command-table slot** (Region A = engine register-file image, `engine-command-table.md`) that the microcode reads
as SEED. The microcode then `hash(luma_LSBs, SEED)` → white-ish per-pixel per-frame noise.

## Ordered next steps (camera required for 1–2, 5–7)
1. **Confirm chan18 = luma** (yknr). Flash `sa_yknr_chan18test.bin` (BUILT, md5 0c26cf04) → cold-boot → shoot a
   scene → pull+view. Black/dark luma + colour intact ⇒ confirmed. (Mirror of chan3=chroma.) `luma-stage-yknr.md`.
2. **Confirm the add reaches luma** (yknr). Add a constant to r24 before one chan18 store → flat luma shift. Then
   the chroma equivalent on PBE r0 (re-confirm E-0087 on the chroma accumulator).
3. **Locate the SEED slot** (static + 1 camera probe). Find yknr/PBE command-table (Region A) + a free slot the
   microcode reads; scalar code-cave to write a per-frame counter there. (The historically-blocked piece —
   `engine-command-table.md`; do it on whichever stage's command-table resolves first.)
4. **Build the hash op sequence** (`grain-chroma-solution.md` / `luma-stage-yknr.md`): `pk` luma LSBs → mul/add/mul
   avalanche with SEED → parabolic luma-mod → add into r0 (chroma) / r24 (luma). Needs free VLIW slots at the
   store bundles (cannibalise `add r31+=r31` fillers) + the free `pk`/`xf` field semantics.
5. **Prove per-pixel** (1 shot): hash without SEED → fixed-per-scene grain texture (per-pixel + luma-mod works).
6. **Prove per-frame-random** (2 shots): add SEED → 0% identical noise between two frames of the same scene.
7. **Ship:** amplitude knob (Backup param / table slot), tune σ to ACROS-like (≈2.7-3.4, `grain-luma-response.md`),
   deliver via `/setting` redirect (reversible), atlas retrospective.

## SHIP-NOW track — chroma grain + NR-bypass luma grain (parallel to the emulator)
Controlled universal LUMA injection is blocked on the AGU-store wall (confirmed at ISO 16000: yknr runs/denoises
but chan18/cluster5/AGU-segment edits = null → they miss the undecoded AGU luma store). The emulator is the real
unlock. In parallel, a REAL combined grain ships from what already works:
- **Chroma grain (any ISO):** PBE `chan3` / `r0` pre-clamp injection (reachable, proven E-0081/84/87). Per-pixel
  luma-LSB hash + per-frame SEED + parabola luma-mod (`grain-chroma-solution.md`).
- **Luma grain at HIGH ISO via NR-bypass (proven E-0080):** weaken/skip YKNR so native high-ISO SENSOR noise
  SURVIVES as luma grain (YKNR is ISO-gated, C-NR-007: off at ISO 200, on at high ISO; at ISO 16000 it visibly
  denoises — bypassing it reveals the grain for free). Reaches the JPEG trivially (normal pipeline minus NR).
  Delivery via the yknr NR-strength Backup/param lane (E-0080 `EXP-P`), reversible.
- **Combined effect:** chroma grain at every ISO + luma grain that rises with ISO (film-like: more grain in
  low light). HONEST gap vs the goal: no controlled LUMA grain at BASE ISO (no sensor noise to reveal there) —
  that piece waits for the emulator → AGU luma store. 
- Tuning: match σ to ACROS (`grain-luma-response.md`); expose an amplitude knob; ship behind a mode/param.
Build order: (1) PBE chroma grain v1 (per-pixel, luma-mod); (2) layer NR-bypass for high-ISO luma; (3) add the
per-frame SEED; (4) revisit base-ISO luma once the emulator pins the yknr AGU store.

## DEFINITIVE executor map (2026-10-17) — grain ceiling confirmed, SPICA-luma path REFUTED
The full still-pipeline executor map is now complete (`av-cam-executors.md`, `capture-orchestrator.md`):
- **HW fixed-function ISP blocks (MMIO 0xf401xxxx, ARM-programmed + RAM shadow image):** tone LUT `0xf4015300`,
  YAP sharpen `0xf4015c00`, **3D colour LUT = CamCore DEV SRAM `0xf4017000` / ctrl `0xf4015d00` / writer `0xc34b4224`**
  (in Stage_Develop — this is where the develop colour/tone is applied to full-res stills).
- **DSP (SA) modules:** SPICA (develop/resize), PBE (chroma pre-demosaic WB), JPEG-encode (`sa_jpeg_enc_1unit`), yknr (luma NR).
- **Consequence for grain:** the full-res still **develop luma is HW CamCore + DSP-SPICA resize** — neither is a
  per-pixel luma-injection point (SPICA luma edits were camera-null E-earlier; CamCore is HW-opaque). The **SPICA
  base-ISO-luma hypothesis below is REFUTED**: SPICA is resize, the develop luma is written by HW CamCore. ⇒ the ONLY
  injectable DSP luma touch on a still remains **yknr** (ISO-gated). Universal luma grain still requires the
  camera-gated path: **yknr ungate (av-cam 0xd5850 00→01) + op5 injection** (§REOPENED N5). Chroma grain via PBE chan3
  stays the proven lane. No new static luma path exists — confirmed by the complete executor map.

## BASE-ISO luma = SPICA (the develop stage) — the path to UNIVERSAL luma grain (2026-10-16) [REFUTED, see above]
yknr is ISO-gated (off at base ISO) so it can't do base-ISO luma. Tracing where the luma channel comes from at
base ISO (owner's question): the "develop core 0xc37ea42e" is actually **`Camera::Capture::SPICA`** (C-PIPE-026) —
**develop is merged into SPICA's resize job.** So **sa_spica (codectype 0x16, file-id 53) = the develop stage
that writes the YC-canvas luma, and it runs ALWAYS (every ISO, not NR-gated).** ⇒ **SPICA is the ISO-independent
luma injection target.**
- SPICA is a DSP VLIW module (injectable like yknr): reads port24 (luma) ×90; its **luma program = 0x41e0-0x5300
  (port24 ×59)**, output channels chan7(×22)/chan3(×11)/chan31. (The chan14 clamp→store ×7 is in the OTHER
  program 0xc40 — not luma; avoided the yknr-chan18 trap.)
- Unlike yknr, SPICA's chan3/chan7 store datums are DIVERSE (resize filter, not a clean op5 a7→chan3) — so the
  exact luma store needs a camera probe to pin.
- **READY-TO-FLASH probe:** `sa_yknr`→no; **`work/filmgrain/sa_spica_chan3test.bin`** (md5 a6ad5287, zeros 11
  chan3 stores in the luma program; sum32 ✓) + **`deliver_spica.py`** (Backup 0x00bd0002 **byte 429**, 
  `/setting/sa_spica.bin`). NEXT CAMERA: flash → cold-boot → shoot at **BASE ISO 200** (SPICA always runs):
  luma darkens/changes ⇒ SPICA chan3 writes base-ISO luma ⇒ the universal luma injection point. If null, try
  chan7, then the clamp→store finalize of program 0x41e0.
- If SPICA confirmed → inject luma-LSB noise into its luma store's GP source (same op5/two-bank method as yknr) +
  per-frame SEED (0x40000 reg) → **universal luma grain at every ISO** (SPICA always runs). This closes the goal.

## What's EXACT vs OPEN (honest)
- EXACT: both injection points + registers; both delivery bytes + sum32 checksum; the add reaches the JPEG (E-0087);
  the noise design (DeepSeek).
- OPEN: (a) chan18=luma camera confirmation; (b) the SEED slot + scalar write (the #1 blocker for per-frame-random);
  (c) free VLIW slots for ~8 hash ops at the store bundles; (d) `pk`/`xf` exact field semantics (needs the LUT or
  a probe). None require an emulator; each is one cheap camera probe or a bounded static trace.

## REOPENED grain re-tests for next camera session (from the 2026-10-17 DeepSeek red-team, 07 §1d)
Several "closed" negatives are false-negative risk — re-test before concluding (highest-leverage first):
1. **N5 ungate yknr (universal luma via our CONFIRMED store).** yknr luma store = op5 a7→chan3 (E-0091, confirmed).
   It's ISO-gated OFF at base ISO. Force it ON at base ISO, then the store edit works at every ISO:
   - Gate (C-NR-007, predicate 0xd5760): NR-level byte `CommonRam+0x15C` + ISO window in **Backup `0x3004a` at
     `+0xD2..+0xDC`** (~ISO 200..6400). **Edit: widen the window low bound to base ISO (bk w)** — reversible, no
     flash. Then re-shoot the `sa_yknr_lumastore.bin` (zero) at ISO 200: luma now darkens/grains ⇒ yknr runs at
     base ⇒ inject grain into the store for UNIVERSAL luma. (Prep: confirm the exact `0x3004a+0xD2` ISO-window
     byte layout on camera first.)
   - **EXACT ungate (av-cam patch, from the predicate RE C-NR-029):** force the gate ON = patch the OFF-sink's
     return value. File **0xd5850: `00`→`01`** (`movs r0,#0`→`movs r0,#1` at 0xc3516850) → predicate always ON →
     yknr runs at every ISO/mode/NR-level. ONE byte, reversible (01→00). BUT this is an **av-cam p3 flash**
     (riskier than Backup/module-redirect; C-DLV-022 channel). SAFER base-ISO route = **SPICA** (always-on, no
     gate) — prefer the SPICA chan3 probe over ungating yknr unless SPICA fails.
2. **N1 noise source (maybe NOT blocked).** The 2-mux "wall" only proved the muxes are load-bearing. Re-test by
   ADDING a channel: dump the yknr 6-entry IN-DMA ring (0x91f0) for a free slot; ring 6→7 (grain-injection-design
   §3: file 0x1392[0]/0x1480[0] `0x68→0x78` + a 7th `{noise,GO}` descriptor). Blocker: SRAM staging (C-DSP-020).
3. **N4 PBE-luma (NOT disproven).** The r30/r13 doubles were GP-register edits (void per N2). Re-test the DATA
   PATH: repoint PBE's luma OUTPUT descriptor to an alt buffer / edit a PBE luma coeff, not a scalar register.
4. **N3 op5 bank:** re-run the r7-add in a PROVEN-LIVE lane (adjacent to a lane whose a-edit visibly changes out).
5. **N6 in-engine entropy:** look for ISP dither/rounding or LFSR blocks (a free per-pixel noise source).


## ISA CORRECTION (2026-10-17, `sa-dsp-isa.md`): the "VLIW" is layer-2 ENGINE, the wall is undocumented
The SA-DSP is **two layers**: (1) 16-bit scalar RISC (readable — ma1co ISA / `sadis.py`) that (2) launches an **engine
coprocessor** via `run_engine r0` (the per-pixel processor; its command stream = the "64-bit VLIW bundles" we edited,
e.g. yknr ~0xcd80). **ma1co documents layer 1 but NOT the engine** (`run_engine` = "local, not in ma1co"). So the
op5/two-bank/g14 material below describes the **engine command stream** (layer 2), whose opcode semantics are
undocumented/unobservable/un-emulated = the real wall. The grain edits targeted the correct region. NEW angle being
pursued: reverse the scalar's engine-command-table **construction** (producer side) for an injectable dither/seed field
(parameter-level, bypasses engine authoring).

## op5/two-bank injection = CAMERA-GATED (static tracer confirms, 2026-10-17) [= layer-2 engine stream, see above]
Rebuilt the two-bank dataflow tracer (op3→GP, op1 pk GP→CHAN, op5 CHAN→CHAN move) and traced yknr's luma store
CHAN[3]. It roots at a pack@0xcc98 from GP **g14**, with NO port24 leaf in the window — the SAME anomaly under
every op→bank assignment tried. ⇒ the exact op5/op1/op3 bank semantics are NOT statically resolvable (HW behavior);
the injection register can only be pinned by the camera probes in 07 §1d / the N3 re-test (op7 add in a proven-live
lane). Static RE has reached its ceiling here; the grain-injection point is a camera task, not a static one.

## Flagged lead (don't lose)
Retargeting port24→port31 in PBE luma pass 0x6310 gave FAINT per-column vertical lines — the only positive
luma-adjacent VLIW signal in PBE. Revisit to understand why PBE's luma read faintly reaches output
(`pbe-engine-map.md`).

Cross-refs: `pbe-engine-map.md`, `luma-stage-yknr.md`, `grain-chroma-solution.md`, `engine-command-table.md`,
`grain-injection-design.md`, `06-experiment-log.md` E-0090. Tools: `vliw_dis.py`/`vliw_enc.py`, DeepSeek `dsq.py`.
View frames off the SD card directly (`nex3n-sd-frame-view`).
