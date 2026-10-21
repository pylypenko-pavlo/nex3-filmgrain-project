> SUPERSEDED (2026-10-21). The DSP-side grain route described here is closed: it is blocked by hardware
> (see the root README, 'Results: grain'). The route that shipped is the Linux LD_PRELOAD shim in
> `code/grain-shim/`, runbooks `atlas/grain-linux-*`. This page is kept for the engine/VLIW
> findings; its 'next steps' and 'active path' wording is historical.

# Grain — the sftfcs path (2026-10-17 camera session + 2026-10-17 eve CORRECTION)

> **CORRECTION (2026-10-17 eve, camera-verified E-0099..E-0104): two earlier beliefs were WRONG.**
> 1. **`chan 3` is CHROMA (Cr-dominant), NOT luma.** Storing a constant into chan-3 shifts Cr (pink = Cr↑213),
>    storing a stream puts chaos into Cr (std 51) while Y keeps the scene. E-0098's "banding" was chroma banding
>    (unnoticed on a near-monochrome terminal scene). ⇒ chan-3 grain = colour-speckle, not film (luma) grain.
> 2. **The 0x6000-0x6900 program is a ROUTING/MUX stage, not a compute stage.** `mov`/`st`/`rd` operate on data
>    **lanes** (streams); `add`/`mul`/`pk`/`xf`/`clmp` operate on a **separate ALU register file**. Arithmetic
>    here does NOT change what is stored — only changing the **operand** (which lane `mov`/`st` reads) does.
>    So grain cannot be *added* arithmetically in this stage; the luma is pre-computed upstream and merely routed.
>
> Net: the "select Soft Focus → get luma grain here" plan as written is **blocked**. See
> "Camera session 2026-10-17 eve" below for the evidence and the revised direction.

The original (now-corrected) claim was: sftfcs `chan 3` = the Soft Focus luma output that reaches the JPEG. Builds on
`sa-dsp-isa.md` (16-bit scalar + `run_engine` coprocessor), `engine-command-table.md`, `grain-via-effects.md`.

## The still-pipeline luma-write map (this session, camera-verified)
| module | VLIW luma output | camera result | role |
|---|---|---|---|
| **yknr** | **`st r7 → chan 3`** @0xcd80-0xce70 | **HIT** (zero→dark luma, E-0091; ISO-differential) | luma NR, **ISO-gated (high-ISO only)** |
| yknr chan 6 | `st → chan 6` @0xcc78-0xccb0 | NULL (E-0094) | dead/internal channel |
| yknr 0xcc38 clamp | — | NULL (E-0095) | internal |
| **SPICA** | chan 3 / **chan 7** | NULL both (E-earlier, E-0097) | resize; does NOT write the full-res still luma |
| **sftfcs** | **`st r11/r17/r7/r15 → chan 3`** @0x6558-0x6878 (47 stores) | **HIT** (zero→vertical banding, E-0098) | Soft Focus effect, user-selected |
| develop luma (base ISO) | — | HW CamCore `0xf4014500` (Itp) | HW, not DSP-injectable |

**Key conclusions:**
- The full-res still **develop luma is HW CamCore** (SPICA/apollo4 edits = null on all channels incl. chan-7). No DSP
  module writes the base-ISO still luma → **no universal base-ISO DSP luma grain.**
- The only DSP modules whose VLIW output reaches a still luma: **yknr** (chan 3, high-ISO only) and **sftfcs** (chan 3,
  Soft Focus mode). → grain via DSP is either **high-ISO (yknr)** or **Soft Focus (sftfcs)**.
- **Channel numbers are abstract per pass** — the physical buffer is a runtime DRAM descriptor (opaque, C-DSP-020).
  That is why wrong-channel probes (yknr chan-6, SPICA chan-3/7) were NULL while the real output channel (chan-3 in
  yknr & sftfcs) HIT. Lesson: confirm the output channel by a zero-test before injecting.

## sftfcs chan-3 injection — CONFIRMED live (E-0098)
- **Confirmation:** `sa_sftfcs_chan3zero.bin` (idled all 47 `op5→chan3` stores in 0x6500-0x6900) → cold-boot, Picture
  Effect = Soft Focus, shoot → **visible vertical banding** across the frame (idled stores leave tile columns stale).
  ⇒ chan 3 is the Soft Focus luma that reaches the JPEG.
- **Store sources:** r11 (dominant, ~15×), r17 (~12×), r7, r15, r19, r25, r27 — the 47 chan-3 stores (0x6558-0x6878).
  The output is tile/column-interleaved (hence the banding).
- **The blend** `add r0 += r24` @0x6548 is NOT the main output (r24≈0 at the blend; a 0x6500 `add r24+=r24` probe was
  NULL, E-0096 — it only touches 1/7 stores via r15). Grain must go into **r11/r17** (the dominant sources), not r24.
- **Injection = add a per-pixel noise term to r11/r17 before their chan-3 stores.** (design in progress — the 0x6500
  bundle has 4 idle slots but is before the per-pixel stream load; r11/r17 compute sites being pinned.)

## The remaining piece: a per-pixel/per-frame-random NOISE source (the hard enabler)
Comprehensive VLIW analysis (DeepSeek, all three modules) confirms: **the engine computes NO in-engine entropy** — no
LFSR, counter, hash, or position-random. So grain needs a noise value supplied. Two tiers:
1. **Fixed-pattern "grain" (demo, in progress):** a per-pixel deterministic term (e.g. a function of the per-bundle
   STREAM port-24 luma sample r30) added to r11/r17 → visible grain-like texture (same every frame). Proves the
   texture lays into Soft Focus end-to-end.
2. **Real film grain (ship):** per-frame-random SEED → PRNG → per-pixel noise. The seed must come from the SCALAR (a
   frame counter / timer the scalar writes into an engine-readable register/port). **Seed source = the open hunt.**

## Camera / dump operational facts (this session)
- **Module delivery is reversible & instant:** `/setting` redirect byte (yknr 597, spica 429, sftfcs 445) + writeFile;
  **no cold-boot needed when the redirect byte is already set** (module re-read per capture) → fast flash→shoot→view
  iteration. First-time byte 0x00→0x06 may need one cold-boot.
- **senser readMemory limits:** reaches av-cam flash + av-cam RAM (0xc3xxxxx) only, **~one read per service session**;
  `0xbf…` DRAM (C++ heap / stage registry) and DSP SRAM (0x9xxx/0x91f0) return GenericUsbException / zeros — so the
  runtime channel→buffer bindings are NOT dumpable. The filled interface object at 0xc34414d0 (242/256 words, 99
  registry pointers into 0xbf2fxxxx) is readable but its targets are not.
- Camera wedges after a large dump → physical replug. Unmount the SD volume before each senser session.
- **Tooling:** `dsq_xpl.py` = Experiential Labs gateway client (free `deepseek-v4.1-flash`, key in env not code) — used
  for the comprehensive VLIW synthesis; `vliw_dis.py`/`vliw_enc.py` (engine bundles), `sadis.py` (16-bit scalar).

## xf-LUT chokepoint — RULED OUT, injection map pinned (2026-10-17, static)

Owner asked: is there a single `xf` (LUT) all chan-3 output passes through, so one LUT reprogram = grain?
Full backward dataflow trace of all 47 chan-3 stores over the engine region `0x6000-0x6900`
(`tmp/store_trace.py`, `tmp/xf_scan.py`), corroborated by DeepSeek:

**Verdict: NO xf chokepoint, for two independent reasons (C-DSP-031).**
1. **0 of the 47 chan-3 stores are an xf output.** Final producer of the stored register:
   `mov 23, rd 15, add 4, mul 4, pk 1, xf 0`. The 36 `xf` ops in the region feed intermediate
   compute (`0x6018-0x6118`) and a POST-store block (`0x6940-0x6970`: `r15=xf(r16)` ×7) — none reach the stores.
2. **Even if they did, an `xf` LUT is a deterministic function of value** → it can only reshape tone per
   luma-level (fixed), it **cannot generate per-pixel random grain.** A deliberately dithered LUT on per-pixel
   luma gives luma-driven texture, but flat regions band/contour and there is no per-frame independence. Grain
   must be an **additive per-pixel term** (`op7 add`). DeepSeek agreed (Q3).

**The 47 stores collapse to a small, bounded source set (C-DSP-032):**
| stored reg | produced by | # stores | note |
|---|---|---|---|
| **r17** | `mov r17=r15` @0x64f8 | **11** | copy of r15 |
| **r11** | `rd r11=STREAM[port 16]` | **15** | pixel stream; reloaded @0x6638/0x6808/0x6830/0x6848 |
| **r7** | `mov r7=r15` @0x6408 | **7** | copy of r15 |
| r19 | `mul r19*=r14` @0x60a0 | 4 | |
| r13 | `add`/`mov` @0x6738/0x66c0 | 3 | |
| r23 | `mov r23=r15` @0x6500 | 2 | copy of r15 |
| r15,r25,r27,r9,r3 | mov/mul/pk/rd | 1 each | |

- **r15 is stable across the copy points:** no writer between `0x6410` and `0x64f8`; first writer in the region is
  `0x6520`. So r7, r17, r23 are all copies of ONE live-in `r15` value. r15's real producer is **above `0x6000` /
  the loop back-edge** ⇒ `0x6000-0x6900` is **one iteration of an outer per-pixel/per-tile loop** (the undocumented
  engine loop = the wall). Each pass loads this pixel/tile's r15, r11 (port 16), etc. ⇒ **per-pass grain = tile
  grain that varies per tile and per frame** — exactly the owner's accepted spec ("тайловое зерно приемлимо",
  "построить на данных с готового кадра").

**Injection map for flashing (C-DSP-033) — dead slots pinned:**
- **PRIMARY (cleanest, 20/47 stores): grain the r15 lineage.** Around `0x6408` and `0x64f8` the non-store slots are
  `mov r23=r15` fillers (r23 = scratch dump, written 198×) ⇒ **plentiful dead slots.** Plan: `pk r23=pk(r15)`
  (noise = luma low-bits = the frame's own micro-texture) in a dead slot, then `add r7 += r23` / `add r17 += r23`
  in the next bundle's dead slot (intra-bundle slots read pre-bundle state, so compute-then-add spans two bundles).
  One build grains r7+r17+r23 ≈ 20 stores. Tile-grain, luma-correlated, per-frame-varying.
- **SECONDARY (15/47): r11 = port 16 stream.** Dead slot in each store bundle = `S1 mov r6=r24`. Fiddlier: reload
  (`rd r11`, S3) and store (S4) share a bundle, so the add must land in a bundle between a reload and its store,
  per reload group (`0x6638/0x6808/0x6830/0x6848`). Gives intra-tile variation (port 16 = real pixel stream).
- **TERTIARY: r19 (4, `0x60a0` busy — skip first pass), r13 (3).**
- **Midtone mask (A(L)=L·(MAX−L)):** `M = xf(L)` via a parabola LUT, `term = mul(noise, M)`, `target += term` —
  no divide needed (DeepSeek Q2). Add after the core grain is visible.

## STATIC RISK SWEEP (2026-10-17, DeepSeek + disasm — before any flash)
Ran every statically-checkable pre-flash risk through the `explabs` DeepSeek lane + disassembly corpus
(`tmp/pk_corpus.py`, `tmp/timing_s0.py`, port map). Results change the plan and save camera cycles:

- **`pk()` is almost certainly a HIGH-bit / requantize-pack, NOT a low-bit micro-texture extractor**
  (DeepSeek conf 0.65-0.75; C-DSP-034). Corpus: `pk` feeds `xf` **LUT indices** (`0x6050`,`0x60f0`), `mul`
  factors, and `clamp` inputs — all want a bounded/coarse code. `pk(r7)`=`pk(luma)` results are mostly dead.
  ⇒ **the original `pk(r15)=noise` PRIMARY plan would likely have flashed to a smooth/invisible dud.** Needs
  ONE runtime trap to confirm, not a guess.
- **VLIW timing = pre-bundle read, write-at-end, NO intra-bundle forwarding** (C-DSP-035). Proof: `0x6808`
  `S3 rd r11` + `S4 st r11` emits the r11 from 2 bundles earlier. ⇒ **the grain `add` must land in the bundle
  BEFORE the store, never same-bundle.**
- **The engine ISA has NO sub / shift / and / xor / immediate** (only mov,pk,xf,rd,mul,st,clmp,add). ⇒ a
  zero-mean high-pass (sharp−blur) is not directly buildable; noise must come from a stream or a LUT, not arithmetic.
- **Stream ports in the store region:** port 24 (r30, 90 reads) = the per-pixel LUMA stream (matches PBE taint
  analysis, `pbe-engine-map.md`); **port 16 (r11, 7 reads) is the stream stored DIRECTLY to chan-3** (15 stores)
  ⇒ r11/port-16 = the confirmed per-pixel data that reaches output = best real-noise handle. (C-DSP-036)
- **`xf` = nonlinear transfer whose LUTs are DMA-loaded from OUTSIDE the module** (pbe: "lookup tables > module
  size"). ⇒ the "dithered xf-LUT = grain" shortcut is HARD (LUT not in the flashable module file) — dropped.
- **Blur/finality (Q4) — CLOSED to LOW (C-DSP-037, 2026-10-17 later-program trace).** Mapped every `st→chan3`
  in the module (77 total, 18 clusters). The module is a scalar dispatcher + **many small engine programs**
  (one per `run_engine`) scattered across the file. Real chan-3 writers: **ours 0x6558-0x6878 (47)**, 0x8408
  (×3), **0x9f60-0xa658 (×9)**, a couple small/early ones; the lone singletons (0x6a08 `bfffff…` degenerate,
  etc.) are data/misaligned. Decoded the later chan-3 programs:
  - **None reads "chan 3" as an input.** Every program's inputs are STREAM **ports** (24=luma, 16, 5, 7, 8, 10,
    13, 17, 19, 20, 26, 31). There is NO in-place `read-chan3 → convolve → write-chan3` low-pass pattern in the
    static code. Inter-stage data flows through runtime-bound ports, not re-read channels.
  - The later chan-3 programs are **multi-port merge** (0x9f60 reads 8 distinct ports) or **per-pixel point
    transfers** (clamp/xf), **not single-plane neighbor-tap spatial blurs** (contrast our own blur kernel at
    0x6440-0x6498, a long `add r2+=tap` accumulation — none of the later programs has that shape over our plane).
  - **E-0098 proves our data reaches the JPEG with spatial structure intact** (zeroing ours → banding; if a later
    program re-generated chan-3 our zeros would be overwritten, no banding). ⇒ ours is the surviving/final luma.
  - **Residual = runtime buffer binding** (a later program's port could be bound to our output buffer — opaque,
    C-DSP-020). This is NOT closeable statically, but it is **exactly what Flash #1 (constant-sanity) tests**: if a
    big constant added to our chan-3 appears undiminished in the JPEG, nothing downstream smooths or heavily
    compresses it. ⇒ **spatial-blur risk ruled out structurally; the only realistic downstream effect is tone/
    amplitude compression (tunable by amplitude), and Flash #1 closes it empirically.**

## Camera session 2026-10-17 eve — the flash experiments (E-0099..E-0104)
Delivery confirmed working this session and **no cold-boot needed** (module re-read per capture — chan3zero banded
immediately after a plain writeFile). All on the sftfcs `/setting` redirect (byte 445 = 0x06).

| E-ID | module (md5) | change | camera result | conclusion |
|---|---|---|---|---|
| E-0099 | flash1_sanity (7c85a2) | `add r7+=r15` @0x6410, `add r17+=r15` @0x6500 (after the committing movs) | **no effect** (FFT-flat) | arithmetic AFTER the mov doesn't reach the store |
| E-0100 | chan3zero (7dc18d) | idle all 47 `st→chan3` | **fine vertical comb** (whole frame) | delivery OK; store presence matters; no cold-boot needed |
| E-0101 | datumr31 (36b375) | all 47 `st r31→chan3` | **uniform PINK** (Cr→213) | store VALUE controllable via operand; chan-3 drives **Cr/chroma** |
| E-0102 | datumr30 (dd0033) | all 47 `st r30→chan3` | scene + green/red bands + fine per-pixel texture (Cr std 51) | per-pixel source routable via operand; chan-3 = chroma; r30 range≠chan-3 range |
| E-0103 | movsrc (4c6248) | `mov r7=r31`, `mov r17=r31` (change mov SOURCE) | **whole frame GREEN** | changing the mov source operand DOES change the stored value |
| E-0104 | premov (12736a) | `add r15+=r15` BEFORE the movs | **no effect** | arithmetic BEFORE the mov ALSO doesn't reach |

**What this proves (C-DSP-038, C-DSP-039):**
- **`mov`/`st`/`rd` act on data LANES; `add`/`mul`/`pk`/`xf`/`clmp` act on a SEPARATE ALU register file** (same 0-31
  indices, different namespace). Changing a lane OPERAND (mov source, st datum) changes the output; ALU arithmetic on
  a register — before OR after the mov — never reaches the store. The 0x6000-0x6900 program is a **router/mux** over
  pre-computed (live-in) lane data, not a compute stage. (E-0099/E-0103/E-0104)
- **chan-3 = CHROMA (Cr-dominant), not luma.** (E-0101/E-0102; Y/CbCr analysis of the frames.)

⇒ **Both pillars of the old plan fall:** can't *add* grain arithmetically in this stage, and chan-3 isn't luma anyway.

## Mechanism & injection method (2026-10-17 autonomous static analysis + DeepSeek, C-DSP-040)
DeepSeek synthesis of the 6 experiments + module-wide disasm settles the mechanism:

- **Why E1/E2 (inserted adds) failed but E3/E4/E5 (operand edits) worked: the inserted bundles were DEAD / not on
  the executed run_engine path for those stores** — NOT a lane/ALU register-file split. The r7/r17 store datums are
  **live-in** (routed by the executed `mov r7=r15`@0x6408 from a value computed in an earlier program); a fresh `add`
  in an adjacent/NOP bundle never becomes that datum. E3 edits the executed mov source; E4/E5 edit the executed store
  datum ⇒ both land. **Rule: edit an EXISTING live op, never insert into a spare/NOP slot.**
- **Module-wide (`tmp/inflow_sites.py`): EVERY output channel has stores whose datum is produced by an in-flow
  `add/mul/clmp/pk/xf` 1-5 bundles before the store** (e.g. in 0x6500: `st r13→chan3` with `r13=add(r16)@0x6738`;
  0x2370 is compute-heavy: 74 add + 21 mul, reads port24×11). So arithmetic→store is the NORMAL pattern — grain can
  ride an existing compute op.
- **Injection method (the reliable one):** for a target store `st rX→chanY` whose datum is `rX=add(rZ)@off`, **edit
  that existing add's source operand** → `add rX += rNoise` (trades rZ for noise), or edit an existing `mul rX*=rZ` →
  `mul rX*=rNoise` to modulate. Do NOT add luma-to-luma (port24) — that shifts brightness, not grain; use a small /
  per-pixel-decorrelated source, or rely on a following `clmp` to bound it.

**The one thing still camera-gated (decisive fork):** only **lane-operand** edits (mov source, st datum) are
camera-proven. Whether editing an existing **arithmetic** op (add/mul) reaches output is predicted by the
dead-bundle model but NOT yet proven (an alternative lane/ALU-split model would say no). **E-0105 settles it.**

## Turnkey next-session battery (`work/filmgrain/`)
1. **E-0105 — decisive add-edit test (BUILT: `sa_sftfcs_addedit.bin`, md5 14d29b10).** Edits the EXISTING `add
   r13+=r16`@0x6738 → `add r13+=r13` (doubles r13, which feeds `st r13→chan3` at 0x6740 & 0x6758). If those 2 chan-3
   columns shift (FFT/diff) ⇒ **editing an existing arithmetic op reaches output ⇒ additive grain is buildable.** If
   not ⇒ only lane-routing works (grain = replace a lane). *Flash first next session — it's the fork everything hangs on.*
2. **Luma lane is almost certainly NOT in the 0x6500 program.** 0x6500's only high-count output is chan-3=chroma (47);
   its other outputs (chan 5/12/13/28/31) have just 2-7 stores each — too few for a full luma plane. So the still luma
   is produced by **another program or HW.** Camera-finder plan: idle the big full-plane channels (module-wide totals:
   **chan 0=88, chan 1=78, chan 31=72, chan 17=63, chan 8=55**) in their producing programs, Y/CbCr-diff each. Leads
   from static: 0x9f60 writes chan 8 & 9 with **port24-luma taint** (`tmp/taint.py`); 0x2370 is a port24-compute stage
   (74 add/21 mul) writing chan 0/11/12/18. **Finder modules BUILT** (`build_lumafinder.py`, datum→r31 over 0x6000-0xa660):
   `sa_sftfcs_r31_ch8.bin` (22 stores, md5 cf062a7b), `…_ch0.bin` (42, 35a4b75e), `…_ch1.bin` (41, 45b8d8f3),
   `…_ch17.bin` (39, 930150ce). Flash each next session + Y/CbCr-diff: the one whose edit shifts **Y** (not Cr) = the
   still luma lane. (Note: the static descriptor→channel map is a dead end — the command table is runtime-built, r4 is
   never a static literal; see `engine-command-table.md` "sftfcs engine-launch structure".)
3. Once luma lane known + E-0105 result: build grain by editing the luma store's in-flow add/mul operand to a
   decorrelated per-pixel source (method above). **Injection sites PRE-LOCATED per candidate** (so grain = a 1-line
   edit once the lane is confirmed):
   - **chan 17 (best leverage): 18 add/mul-fed stores; `add r29`@0x69c0 alone feeds 6+ of them** → one operand edit
     grains 6+ luma pixels.
   - chan 0: 6 sites (e.g. `add r6`@0x79f8→st@0x7a30; `mul r0`@0x7a40→st@0x7a50).
   - chan 1: 6 sites (`add r13`@0x8fe8/0x9968/0x9e38 each feed a store).
   - chan 8: 7 sites (`mul r2`@0x6030; `mul r31`@0x8250/0x82b8).
   Grain edit = change that op's source operand from its current reg to a decorrelated per-pixel noise reg (NOT port24
   luma → that's brightness). Noise-source selection is the last open piece (needs the lane confirmed + a camera check).

Housekeeping: `/setting` sftfcs currently holds `premov` (≈ stock visually). Revert redirect byte 445 → 0x00 (and
yknr 597, spica 429) to leave the camera fully stock when pausing.

Cross-refs: `grain-roadmap.md`, `grain-via-effects.md`, `engine-command-table.md`, `sa-dsp-isa.md`, `06-experiment-log.md`.

## Camera session 2026-10-19 — the crash wall + what's SAFE (E-0105..E-0109)
Resumed flashing. Hard-won, firm findings:

| E-ID | edit | result | lesson |
|---|---|---|---|
| E-0105 | edit existing `add r13+=r16`@0x6738 → `add r13+=r13` (2 chan-3 stores) | inconclusive (2/47 cols too subtle without baseline; FFT confounded by JPEG chroma subsample + photographed-screen perspective) | subtle arithmetic-reach tests unreadable |
| E-0106 | `sa_sftfcs_r31_ch8` (chan-8 datum→r31) | **BROKE SAVE** | chan-8 = critical internal (port24-luma-tainted intermediate), not an output |
| E-0107 | chan-8 datum→r30 (valid stream) | **BROKE SAVE** | crash is structural, not divide-by-zero; r30 no safer than r31 for internals |
| E-0108 | `sa_sftfcs_r31_ch13` (chan-13 datum→r31) | **BROKE SAVE** | chan-13 (co-stored with chan-3) also a critical intermediate |
| E-0109 | `addeditV2`: edit `mul r19*=r19`@0x60a0 + `add r13+=r13`@0x6738 | **BROKE SAVE** (wedged USB → physical replug) | **r13 & r19 are SHARED registers** (static: r13 read by 3 movs, r19 by 6 adds + a chan-5 store) → editing their arithmetic corrupts other paths → crash |

**FIRM conclusions (C-DSP-041):**
- **Only editing a store's DATUM OPERAND is safe** (localized — changes just what that store reads). Proven: datum→r31/r30/idle on chan-3 all SAVED fine (E-0100/0101/0102). Editing shared ARITHMETIC registers crashes the save pipeline (global corruption).
- **chan-3 (Cr) is the ONLY safe/terminal output of the sftfcs DSP program.** chan-8, chan-13 (and the arithmetic intermediates) are load-bearing internals that crash the save when corrupted by any value.
- **Y (luma) = HW, confirmed by elimination.** No safe DSP output carries Y; Y survives chan-3 corruption (E-0102 scene stayed visible); luma-tainted DSP channels are crash-prone intermediates. ⇒ **luma grain via Soft Focus is impossible** (DSP writes only chroma in SF; HW does the luma softening).
- **Additive grain is blocked:** every chan-3-feeding arithmetic register is SHARED (no dead/local accumulator), and inserted ops are dead (C-DSP-038). So "chroma + injected noise" via arithmetic crashes.
- **`Y = Y`, chroma is luma-orthogonal:** a pure-Cr grain gives ΔY = 0.299·1.402·ΔCr − 0.587·0.714·ΔCr = 0 exactly. So chroma grain can't make B&W luma grain — but luma-MODULATED fine Cr grain IS authentic COLOUR-film grain (the chosen target).

## 3 prepared experiments — color grain via SAFE datum-replace (built, ready; owner reviews before flashing)
All REPLACE-based (datum-operand only) → no crash. Honest limit: no luma-modulation (midtone-peak needs arithmetic = crash); amplitude is uniform/texture-correlated, not film-midtone-peaked.
1. **Raw chroma stream** `sa_sftfcs_chan3_r11.bin` (md5 a7cf9608): all 47 chan-3 datums → r11 (port16 per-pixel chroma, correct scale). Tests: is port16 chroma naturally noisy (→ grain) or NR-smooth.
2. **Chroma scramble** `sa_sftfcs_scramble.bin` (md5 79f18680): 43/47 datums → pseudo-random valid chroma regs (pool {3,7,9,11,13,15,17,19,23,25,27}, seed 1337) → each output pixel reads a decorrelated tile-position chroma = manufactured per-pixel colour noise (works even if chroma is smooth; amplitude ∝ local chroma texture).
3. **Mild scramble** `sa_sftfcs_scramble_mild.bin` (md5 159d1d26): every-3rd datum scrambled (15/47) → subtle, film-plausible amount.
Flash order: 1 (natural source) → 2 (manufactured) → 3 (tune). Camera currently STOCK (the r11 flash was cancelled, not written).
