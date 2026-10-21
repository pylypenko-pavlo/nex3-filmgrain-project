# DSP grain — scope (branch 2, after ARM injection was blocked)

Scoping doc for injecting film grain via the **SA-DSP**, written 2026-10-12 after E-0074
proved ARM-side pixel injection is architecturally blocked. Premise, constraints, ranked
sub-paths, critical path. This is a plan, not a result — nothing here is flashed yet.

## Why we are here
- ARM (CPU1 av-cam) **cannot write the imaging canvas**: the pixel pages are read-only for the
  CPU; writes data-abort via both `0xC` (cached) and `0xD` (uncached mirror), tiny or large,
  pre- or post-YKNR (E-0074, 7 flashes EXP-5..11).
- The pixels are owned and written by the **SA-DSP** (`sa_*` modules; `sa_yknr` = late luma-NR,
  codectype `0x1c`). So any pixel-level grain must come from the DSP side.

## Hard constraints (what makes this branch hard)
1. **VLIW ISA is unknown (Q-17) — but hard, not blocked (tooling scout 2026-10-12).** The scalar
   core never touches pixels (C-DSP-020); the pixel math is in the module's **engine / VLIW**
   pass (C-MOD-048), whose op3 codes are not decoded (C-DSP-010/015: bundle 64 b = 12 + 4×13,
   NOP `0x1f7`). Public state: the SA-DSP is a **Sony-proprietary 32-bit, 16-reg custom core**
   (OpenMemories); the ONLY public tool is `ma1co/SA-DSP` (Ghidra SLEIGH) which covers the
   **SCALAR** ISA only — matching our own `sadis.py`/`saemu` (C-DSP-007) — and has **no VLIW**.
   So the VLIW must be reversed from scratch. Shortcuts that make it tractable: **differential
   analysis** across CXD4132/CXD90014/CXD90045 (bundles are byte-identical, C-DSP-016 → several
   corpora of the same module), **semantic anchors** (modules with known algorithms + the av-cam
   param tables, like the Soft-Focus oracle), and asking the author (ma1co) directly. Verdict:
   scalar = tooled; VLIW = hard but not blocked.
2. **Scalar injection is already ruled out (Q-42 / C-PIPE-022).** The `sa_yknr` y3 scalar slot
   operates on DMA descriptors, not pixels; the shared buffer is the engine DMA aperture
   `0xf81400`, not the scalar-addressable 2 KB tile buffers. No scalar per-pixel loop exists
   (C-DSP-036). No module has a classic PRNG in scalar code (C-NR-025).
3. **The target module lives in p8 — currently owner-gated, NOT a proven brick.** `sa_yknr` and
   31 other `sa_*.bin` are in p8 `/usr/sabin`; only `sa_dfdet.bin` is in p3 `/system/sabin`
   (C-DSP-001). p8 is marked FORBIDDEN, but the verdict legend is explicit: *"FORBIDDEN =
   owner's rule, no recovery known"* — i.e. **caution, because p8 recovery was never tested**,
   and the old notes disagree whether the updater repairs a bad p8 (C-SAFE-005 vs C-SAFE-006).
   Re-analysis 2026-10-12: p8 is very likely **recoverable** — the updater (recovery Linux on
   p1/Loader2) does NOT depend on p8/`/usr` (C-BOOT-037, C-DLV-019: in updater mode the
   imaging/SA stack is down, `/system` empty, but USB/storage/Backup are up and `/dev/nflashaX`
   are writable), so a trashed p8 still lets the camera enter the updater and re-flash
   `/dev/nflasha8`; WBI-zero applies to p8 too (C-DLV-009). Contrast p1 (truly jumper-only).
   **Precautions before any modified p8 write (owner's call to lift the gate):** (a) a **dry-run
   round-trip** — dump p8, md5, re-flash the SAME dump, confirm boot+capture (proves the
   flash+recovery cycle with zero image risk, like the Q-37 stock-copy approach); (b) a
   byte-exact stock p8 recovery image on hand (check the iCloud "stock full dump"); (c) confirm
   `flash_any.py` writes `/dev/nflasha8`; (d) charged battery (an interrupted write is the only
   real residual risk, and even that is updater-recoverable, unlike p1). Alternative delivery
   that avoids p8 entirely: **C-MOD-044** (hypothesis, not run) — one Backup byte redirects a
   module load to `/setting/` (writable). Either path works; the dry-run de-risks p8 directly.
4. **Modules are checksummed.** Each `sa_*.bin` ends with a `sum32le` trailer over all preceding
   u32 words (C-DSP-001); any edit must fix the trailer (easy once known).
5. **Real-time budget.** The engine runs the whole frame as 128×8 YUYV tiles (C-MOD-048,
   15 912 tile write-chains for 4912×3264). Extra per-pixel work risks the capture watchdog
   (the EXP-7..11 reboots were an MMU fault, but a watchdog is a separate real risk here).
6. **DSP-local MMIO is not ARM-visible** (C-DSP-020): the engine's registers / DMA aperture are
   in the DSP address space, not mapped in ARM physical memory → cannot be poked from av-cam.

## Ranked sub-paths (cheapest / most promising first)

### S1 — Module PARAMETER knob — CLOSED NEGATIVE (2026-10-12, opus RE)
**No additive grain/dither/noise-amplitude field exists in the av-cam → sa_yknr param path.**
The CALC_START block av-cam authors is **geometry-only, 0x1c bytes** (proven: builder
`sa_func_YKNR_start 0xc3878244` marshals with `movs r2,#0x1c`; caller `0xc37ebe60` fills 7
fields = buffers A/B/C + width `[OBJ+0x3e60]` / height `[OBJ+0x3e64]` / stride `[OBJ+0x3e50]` +
one unused word). The NR constants are baked into `sa_yknr.bin` (p8, C-MOD-026), not reachable
from p3/av-cam. The only p3/Backup lever is the **enable GATE** (NR level `[OBJ+0x15c]`,
C-NR-004/007; ISO window Backup `0x0003004a`, C-NR-011) — it only *disables* NR → leaves native
sensor noise (the "digital noise" look, rejected), cannot ADD structured grain. Chroma-NR
(`CCNR_Enc`) and sharpen executors are unmapped, no cleaner knob. Residual "maybe" (NOT cheap):
patch `sa_func_YKNR_start` to write extra words into job `+0x1c..` — but that first needs
decoding the DSP-side y0 job parser (C-MOD-046), i.e. it collapses into S3, not a p3 edit.
⇒ **S1 is dead as a cheap knob; grain falls back to S3 (VLIW).**

<details><summary>(original S1 plan, kept for the record)</summary>

#### S1 — Module PARAMETER knob (no VLIW, no p8 flash) — INVESTIGATE FIRST
ARM sends a **codectype in OPEN** and a **parameter block in CALC_START** to each module
(C-MOD-004, C-MOD-020). av-cam (which builds that block) is in **p3 = flashable**, and we have
patched it all session. If the `sa_yknr` (or the develop/CCNR) parameter block contains a
**noise / dither / NR-strength** field, we can set it from an av-cam p3 patch (or a Backup value)
— grain with zero VLIW work and zero p8 flash.
- Tasks: locate where av-cam assembles the `sa_yknr` CALC_START param block; map its fields;
  identify any dither/noise/strength term; find the develop/CCNR equivalents (chroma grain too).
- Prereq: none beyond av-cam RE (we have the tooling).
- Risk: such a field may simply not exist (NR has only *strength*, which reduces, not adds).
  A pure dither amplitude would be ideal; an NR-strength→0 only yields native noise (which the
  owner rejected as "digital noise" — a *dither* knob is different, it is injected/structured).
- Effort: LOW. Confidence: MEDIUM-LOW (depends on a field existing).
- **Recommended first probe.**
</details>

### S2 — HW dither / engine config via a module-init path
If the SA-DSP engine has a hardware dither/noise block (common for gamma/quantization dither),
it is configured either by a module parameter (→ S1) or by the module's own init code. If it is
parameter-driven, S1 covers it. If it is set by module code, it needs S3-class access.
- Effort: LOW to find (does a dither register exist?), HIGH to set if code-driven.
- Confidence: LOW (unknown whether such a block exists / is wired to stills).

### S3 — Modify a DSP imaging module's VLIW engine to ADD a grain term
The "real" injection: add a per-pixel pseudo-random ±N to luma inside the engine pass of an
imaging module, after the last NR (C-PIPE-025 logic carries over).
- Critical path / prereqs, in order:
  1. **SA-DSP VLIW tooling** (Q-17) — a disassembler + assembler for the ISA. *Gating; under
     research (feasibility: existing core to adapt vs reverse-from-scratch vs blocked).*
  2. A **PRNG/LFSR source** usable in a VLIW slot (no scalar PRNG exists, C-NR-025) — an MMIO
     noise source, a free LFSR, or a cheap VLIW xorshift within the cycle budget.
  3. A **p3-resident or redirectable** target module — `sa_dfdet.bin` is the only p3 `sa_*`;
     for anything in p8 we first need C-MOD-044 (redirect-to-`/setting/`) proven.
  4. Fix the `sum32` trailer (C-DSP-001).
  5. Stay within the engine cycle/DMA budget (C-MOD-048) or drop frames / watchdog.
- Effort: HIGH (weeks+, gated on tooling). Confidence: LOW until the gating tooling question
  is answered.

### S4 — DMA-roundtrip (reroute luma through a buffer we can touch) — likely dead
C-PIPE-022: a DMA-roundtrip breaks DMA-identity and costs ×38..×65 → almost certainly trips the
watchdog. Keep only as a last resort.

## Critical path & immediate next steps
1. **DONE** — Gating tooling scout (2026-10-12): scalar ISA tooled (`ma1co/SA-DSP`), **VLIW
   undocumented → reverse from scratch, hard but not blocked** (shortcuts: differential analysis
   across CXD4132/90014/90045, semantic anchors, ask ma1co).
2. **DONE** — S1 param-knob RE (2026-10-12): **CLOSED NEGATIVE** (no additive knob; param block is
   geometry-only; see S1 above).
3. **⇒ Only S3 (VLIW engine edit) remains for injected grain**, and it is a from-scratch reverse
   of a proprietary VLIW ISA — a MAJOR, multi-session, budget-heavy effort with uncertain payoff.
   This is a scale-of-investment decision for the owner, not a quick experiment.
   If pursued, the first concrete steps (research, no camera): (a) survey the VLIW bundles of a
   **semantic-anchor module** whose math we know (sa_yknr NR constants C-MOD-026, or a sharpen/
   convolution) to begin decoding op3 semantics (C-DSP-010/015); (b) in parallel, prove the
   **p8 dry-run round-trip** (camera-gated) to confirm delivery of a modified module; (c) survey a
   usable **PRNG/LFSR/MMIO-noise** source for the grain term (C-NR-025: none in scalar code).
4. Fallbacks if S3 is not pursued: the goal of *injected* grain is, with current access, blocked
   at an expensive VLIW reverse — state this honestly before committing budget.

## Delivery & safety (unchanged)
p3 whole-partition flash (28/0, recoverable) and Backup (reversible) only. **p8 stays FORBIDDEN**
— any p8-resident module needs the C-MOD-044 `/setting/` redirect first. Every DSP experiment is
one commit, risk-tiered as in START-HERE.

## VLIW recon (2026-10-12, Fable broad pass on the real corpus)
Ran the local tools (`sonygen/isa/{vliw,vengine,vdump,saemu}.py`) on real `sa_yknr.bin` + the
311-module cross-generation corpus. Findings:
- **Injection target located:** `sa_yknr` has **5 VLIW programs**; **P4 = y3** (file `0x0c9f0`, 218
  bundles, reads buffer A, writes B — C-MOD-048) is the one that finalizes luma. It has **~34%
  idle slots**, incl. in the per-tile finalize bundles at `0xcfd0 / 0xd080 / 0xd0b8`
  (`bff77ffff5432fff`) → physical room to insert one extra op per writeback bundle.
- **op3 → reads r24 is a UNIVERSAL invariant** (a=24 in 66–83% of op3 slots across yknr/kknr/
  sftfcs/spica/star) → an op-semantics oracle on ONE module transfers to all. (Streaming-source reg.)
- **Correction to C-DSP-014:** "op4 always writes r19" was a **sa_sftfcs-only artifact**; on
  sa_yknr op4's dst tops at r31/r26/r1, r19 absent. Per-program accumulator convention, not an ISA rule.
- **Writeback is DMA, not a VLIW store:** the VLIW computes a tile into engine-local RAM; the scalar
  side programs engine MMIO (`0x48200/0x48208/0x48230/0x48234`) to DMA it out. Reciprocal/normalize
  LUT (`65536*16/n`, C-MOD-026) source bytes at file `~0x238c` → engine `0x40078` at runtime. The 9
  NR immediates `(-8,32,16,16,-2,-2,-16,-2,0)` are **scattered** literal-pool movs, not a table.
- **Differential-diff oracle is DEAD:** bundle streams are **frozen across every version** in the
  corpus (kknr/sftfcs/spica/defect 3N↔6K↔64 = 0 bundle diff; star/tbox differ by thousands =
  wholesale recompiles, not isolable tweaks; sa_yknr exists only in 3N+nex6, same md5). So op3
  semantics must come from **oracle+emulation** (cross-module) + **scalar ablation**, not diffs.
- **No PRNG anywhere** (scalar C-NR-025, now confirmed in VLIW too — engine reads only DRAM A/C +
  control regs). Grain needs a *source of variation*: (a) **self-dither** from pixel low bits, or
  (b) a **DMA grain-LUT** reusing the reciprocal-LUT path (`0x238c`→`0x40078`), indexed per-pixel.
- **Blocker gating any real injection:** the **op3 "add"/multiply arithmetic semantics** are still
  unknown. → Angle 1 (op3 decode via the sftfcs blur oracle) is the linchpin, **running now (opus)**.

### Ranked follow-up angles (Fable; attack with targeted agents)
1. **op3 semantic decode via sa_sftfcs oracle** (opus, RUNNING) — pin an add/acc + a multiply from the
   known sharp→blur I/O; transfers to yknr. Unlocks everything.
2. **Scalar ablation oracle on sa_yknr** — perturb the 9 NR immediates + LUT (`0x238c`) in `saemu`,
   correlate with luma output; safe reversible lever + semantic cross-check.
3. **P4 (y3) writeback dataflow map** — trace the register feeding the DMA latch; inventory the free
   slots in `0xcfd0/0xd080/0xd0b8` → exact {bundle offset, free slot, target reg} for a one-op add.
4. **Grain-source feasibility** — self-dither vs DMA grain-LUT; verify the `0x238c→0x40078` copy and
   whether a 2nd LUT rides the same DMA.
5. **op6 role** — likely clamp/threshold (over-represented in NR/pixel modules); pin it so a grain add
   isn't clamped away.

## op3 decode — partial (2026-10-12, Angle 1, opus, sftfcs oracle)
- **Operand convention CONFIRMED:** slot = `op[12:10].a[9:5].b[4:0]`, **dst=b, src=a**; `r24` is a
  hardware streaming source (auto-advances on read), `r31` = zero/scratch (fill `7.31.31` = no-op).
- **op3 role CONFIRMED** = read the r24 stream into a reg (universal invariant).
- **Operation CLASSES present/necessary CONFIRMED** (multiply, accumulate, ÷256 shift, clamp) via the
  sftfcs runtime self-check "each kernel sums to 256" (C-MOD-021) + unity-gain.
- **op7 = accumulate: STRONG HYPOTHESIS, not confirmed** (dominant ~40–50% of slots; it IS the fill
  value `7.31.31`; feeds every accumulator; yields an ADD-rooted sum-of-products — op7=MUL would give
  product-of-sums, wrong for convolution). Multiply EXISTS but its opcode is NOT pinned (op4/op1/op2
  candidates). Weights arrive at runtime from **Backup `0x0003010a` → engine `0x40000..0x40020`**
  (C-MOD-019), folded into the engine coefficient path → that's WHY a standalone VLIW multiply is hard
  to isolate.
- **Oracle note:** the E-0028 `sf_{input,output}` pair is a downstream preview (stride 1280, 640px),
  NOT the SA tile buffers; no recoverable low-pass (HF ratios ~1, some >1) → too weak to bind
  opcodes. Reproduces the C-DSP-015 observability wall. So op-bindings rest on dataflow, not I/O.
- **Blur program located:** sftfcs prog0 file `0x2420`, inner loop `0x2710–0x2758`. **yknr P4 transfer
  PASS** (file `0x0c9f0`: op3 reads r24 74%, op7 40%, op6 reads r0 80% — identical vocabulary).
- **"pixel += N" sketch** (if op7=accumulate): one slot `op7 . a=<reg holding N> . b=<reg holding the
  luma>`= raw 13-bit `(7<<10)|(rN<<5)|rPix`, dropped into a free FILL slot (e.g. yknr P4 `0xcff0`
  `bffffffffffff32f`, S1-S3 fill). GATES: (a) confirm op7=accumulate; (b) which reg holds luma at the
  DMA latch (grain-scope angle 3); (c) a reg holding ±N (angle 4, grain source).
- **NEXT (critical, breaks the wall):** build a **controlled saemu oracle** — make the engine run
  concretely with a crafted single-weight kernel + known input (resolve the `eeee0001` param-check by
  supplying valid engine params/weights `0x40000`), to CONFIRM op7=accumulate and pin a multiply.
  Alternative: scalar-ablation on yknr's 9 NR immediates in saemu with output correlated (angle 2).

## op7 CONFIRMED + injection encoding ready (2026-10-12, controlled-oracle agent)
- **op7 = accumulate CONFIRMED** (structural/dataflow; MUL/SUB/MOV all REFUTED). Three independent
  lines: (1) a normalized all-positive-weight blur (C-MOD-021 kernel-sum-256) can ONLY be Σ(w·x) →
  op7=ADD; MUL gives Π(x), SUB signed, MOV loses taps; (2) repeated writes to one accumulator reg are
  only meaningful under accumulate (dead code otherwise); (3) impulse-kernel logic separates
  accumulate(=identity) from multiply(=0). No evidence contradicts. **Concrete value-level proof is
  architecturally impossible with the local tools** (saemu = scalar-only, 0009 run_engine logs only;
  vengine = symbolic, op7 hard-fixed to ADD; OpenMemories qemu has no SA-DSP engine). The only
  decisive concrete test is **on-camera**: craft an impulse kernel into Backup `0x0003010a` (sum=256 to
  pass the `eeee0001` self-check) and see if the Soft-Focus output is identity (accumulate) vs
  collapsed (multiply) — a reversible Tier-A oracle, if we want certainty before a Tier-B grain flash.
- **"luma += N" slot encoding (READY):** 13-bit `slot = (7<<10)|(rN<<5)|rLuma` (dst=b=luma, src=a=N).
  e.g. `r25 += r20` = `0x1E99`.
- **Host slot CONFIRMED:** yknr P4 bundle file `0x00cff0` = `0xbffffffffffff32f` has S1/S2/S3 = fill
  (free), S4 active (op4). Dropping `r25 += r20` into S3 → `0xbfffffffffd3332f` (only S3 changes).
- **Multiply opcode** not concretely pinned (candidate op4 → writes the r19 product-sum accumulator);
  **op6** = clamp/threshold candidate (reads r0 ~70%). Partial, non-blocking for an add-only grain.
- **Remaining blockers before a patch:** (a) which register holds luma at the DMA latch (angle 3,
  running); (b) a register holding ±N — **no PRNG/LFSR exists anywhere** (angle 4, the grain source).

## P4 luma plumbing MAPPED (2026-10-12, Angle 3) — 2 of 3 blockers closed
- **Luma register = `r19`** (primary), `r11` = parallel YUYV luma pair. Last kernel write `0xce18 S4
  op7 r22→r19`; thereafter r19 is ONLY accumulated (op7), never reloaded. Drained to engine-local RAM
  (then DMA) via reads into the r31 scratch port at `0xce90 / 0xcf20 / 0xcf30 / 0xcfe8`.
- **Insertion point = bundle file `0xce88`, free slot S1** (an all-free bubble between the last kernel
  write `0xce18` and the first drain `0xce90`): slot `op7 r21→r19` = **`0x1eb3`** → bundle word
  `0xbfffffffffffffff` → **`0xbfff59ffffffffff`** (S2-S4 still fill, S0 unchanged, no stream growth).
  COMMIT#1/#2 read r19 with no write between → emit `kernel_luma + N`.
- **Grain carrier register = `r21`** (never read/written in finalize `[0xce80,0xd0c8)` → holds N
  stably); alternates r4/r5/r12. NOT r31 (live drain port) or r16 (live rounding const).
- Full-luma grain needs r11 too: add `op7 r21→r11` = `0x1eab` (2-slot edit).
- Caveats (static-only): (1) latch identity (…→r31 = store) is a strong hypothesis, not byte-proven;
  the S0 12-bit lane is undecoded and could carry the per-cycle store → re-check if a commit is
  read-and-CLEAR (then insert `op7 r21→r19` upstream before EACH commit: `0xcf18` S2, `0xcfe0` S1);
  (2) an unknown op (1/2/4/5) may clamp r19 to [0,255] during drain → N applied pre-clamp (correct),
  magnitude bounded.
- **Remaining single blocker: the grain SOURCE** — how to deposit ±N into r21 (no PRNG anywhere) —
  Angle 4, running. Once solved → design the modified `sa_yknr` (fix sum32 trailer C-DSP-001) +
  delivery (p8 dry-run or C-MOD-044 `/setting` redirect).

## Build + delivery VERIFIED on real sa_yknr.bin (2026-10-12)
- File `~/nex3n-dump/safeboot/out3n/nflasha8_unpacked_unpacked/sabin/sa_yknr.bin` (53508 B, md5
  `54acf2988273c0a1f98afc9940f34d60`): magic `aa0a1391` ✓, container ver 2 ✓, **sum32 trailer matches**
  (`0xec52e8bf`, C-DSP-001). Bundle `0xce88` = `0xbfffffffffffffff` (confirmed all-fill bubble); `0xcff0`
  = `0xbffffffffffff32f`; `0xcfd0` = `0xbff77ffff5432fff` — all match the angle-3 map on the real file.
- **Build = trivial:** rewrite the insertion bundle(s) (e.g. `0xce88` → `0xbfff59ffffffffff` for
  `op7 r21→r19`) + the grain-source slots once known, then **recompute the sum32 trailer** (sum of all
  u32 words except the last → write as the last word). No LZPT inside the module; it's a flat container.
- **Delivery = REVERSIBLE, NO p8 flash** (supersedes the p8-flash worry): use **C-MOD-044 /setting
  redirect** (05-delivery table row 11, C-MOD-039/044): put the modified module at `/setting/sa_yknr.bin`
  (senser `writeFile`, channel 3) + flip ONE Backup byte `0x00bd0002` (the file-id's dir_slot → 6,
  channel 1 `bk w`) so the On-Demand Loader loads it from `/setting` instead of p8 `/usr/sabin`. Stock
  `/usr` stays untouched; revert = write the byte back to its saved value + `bk s`. **Q-37 de-risk:
  first redirect to a BYTE-IDENTICAL stock copy** to prove the redirect path works and the camera still
  captures, THEN swap in the grain-modified copy. Risk: a missing/rejected file → that module's OPEN
  fails → capture-sequence error, recovered by reverting the byte (C-MOD-044/045). This is Tier-A-ish
  (Backup + a /setting file), far safer than a p3/p8 raw flash.
- **So once the grain source (angle 4) lands, the whole experiment is: edit bundle + grain slots → fix
  sum32 → Q-37 stock-copy redirect dry-run → swap grain copy → shoot high ISO → inspect.**

## Grain source analysis (2026-10-12, Angle 4) — injection SOLVED; source needs the data path
- **VLIW slot has NO immediate field:** `op[2:0].a[4:0].b[4:0]`, both operands are 5-bit register
  indices; `r31`=0 is the ONLY free constant. Any mask/bias/shift-amount must already sit in a register
  → extracting low bits (self-dither) is expensive and needs a pre-set mask reg.
- **Opcode map update:** `op5` = **address/pointer generation (AGU)** — writes the stream-pointer regs
  (op5 `6→16/24/26/20`) that op3 then reads (new). `op4` = multiply (strong). `op6` = clamp/min-max
  (hypothesis, reads r0 80%). **`op1`/`op2` = UNDECODED** — the only AND/XOR/shift candidates.
- **Injection, given a reg holding ±N — SOLVED, fits in ONE existing bundle `0x00cff0`:** S1 `op3
  rPtr→rN` (fetch grain byte from a stream) `(3<<10)|(rPtr<<5)|rN`, S3 `op7 rN→rLuma` (add)
  `(7<<10)|(rN<<5)|rLuma`. No bundle added, no watchdog risk.
- **Grain source, ranked:** **#1 (chosen) DMA grain-LUT as a 2nd per-pixel stream** — bake a blue-noise
  ±N tile on our side (no DSP PRNG needed), DMA it into engine RAM like the input tile, op3 reads it
  from a spare stream pointer, op7 adds it. Uses ONLY confirmed ops; the engine supports multiple op3
  streams. **Blocker = the DATA PATH (scalar stream/DMA setup), not an opcode → needs scalar RE or a
  hardware probe.** #2 self-dither (needs op1/op2 decoded + a mask reg). #3 spatial dither
  (double-blocked). #4 neighbor-residual reuse (cheapest but image-correlated = re-sharpen, not grain).
- **Next: decode sa_yknr's SCALAR engine/stream setup** (buffers A/C, the op3 stream pointers, engine
  MMIO `0x48200/08/30/34`, weight `0x40000`, reciprocal-LUT `0x238c→0x40078`) → how to add a
  controllable noise stream. If undecodable statically → design the minimal on-camera probe.

## FIRST GRAIN EXPERIMENT — READY TO FLASH (2026-10-12)
The grain-source agent (sonnet) delivered concrete, in-memory-verified module edits; I built + sum32-
cross-checked the PoC on the real `sa_yknr.bin`. Delivery (C-MOD-044 /setting redirect) is fully worked
out offline. Flash WITH the owner present (needs the updater shell + a high-ISO test shot).

### Images (built, verified)
- **Q-37 (delivery proof):** stock `sa_yknr.bin` (md5 `54acf2988273c0a1f98afc9940f34d60`) byte-identical —
  proves the /setting redirect loads the module and the camera still captures. No build.
- **PoC (op7/r19 validation):** `~/nex3n-dump/work/filmgrain/sa_yknr_poc.bin` (md5
  `ac6faf3a188d3b2318f360968e35f39d`). ONE bundle edit: file `0xce85` `ff`→`39` ⇒ bundle `0xce80`
  `0x8fffffffffffffff`→`0x8fff39ffffffffff` = slot S1 `op7 r19→r19` (`r19 += r19`, luma ×2 pre-clamp);
  trailer `0xd101` recomputed ⇒ sum32 `0xec5222bf` (matches the agent). Only 2 bytes differ from stock.
  Predicted at high ISO: period-8 banding (≈2Y in 4/8 push positions) IF op7=accumulate & r19=luma &
  delivery works — a concrete confirmation of the whole chain. (Agent also prepared Probe S = scalar
  poke writing a white 4px marker per tile, and Probe K = a param-RAM const; build those if the PoC is
  ambiguous.)

### Delivery — C-MOD-044 /setting redirect (reversible, NO p8 flash)
`sa_yknr` = row **74** of Backup `0x00bd0002` (`4a00 9300 1c 00 01 00`); **dir_slot = byte at block
offset `74*8+5 = 597 (0x255)`**, change `0`→`6` to redirect its load to `/setting/`.
Procedure (updater shell, owner present):
1. **Q-37 dry-run first** (byte-identical copy): `swritefile.py` the STOCK `sa_yknr.bin` → `/setting/sa_yknr.bin`.
2. `bk r 00bd0002` → save the whole 800-B block; set byte 597 = `0x06`; `bk w 00bd0002 <block>`; `bk s`.
3. WBI zero + **cold boot**. Shoot high ISO (YKNR must run, C-NR-007). Camera should capture normally
   (= redirect works, stock copy = no visual change). If capture errors → revert (step 5) and rethink.
4. If Q-37 OK → `swritefile.py` the **PoC** `sa_yknr_poc.bin` → `/setting/sa_yknr.bin` (overwrite), cold
   boot, shoot high ISO. Inspect for the predicted period-8 luma banding.
5. **Revert anytime:** set byte 597 back to `0x00`, `bk w`, `bk s`, WBI zero, cold boot → stock
   `/usr/sabin/sa_yknr.bin` loads, camera fully stock. (C-SAFE-016: a bad redirect only fails that
   module's OPEN = capture error, reverted by this byte; updater/Backup don't depend on av-cam/ODL.)
- Risk tier: ~Tier A (Backup byte + a /setting file, both reversible) — far safer than a p3/p8 raw flash.
- Caveat: when ODL re-reads the `0x00bd0002` table is unproven (C-MOD-045) → always cold boot after the
  byte change.

## ✅ DELIVERY PROVEN end-to-end (2026-10-12, on camera)
The `/setting` redirect (C-MOD-044) WORKS — proven on hardware, reversible, no p8 flash.
- **Verified config (senser read):** `0x00bd0001` slot 6 prefix = `/setting/`; `0x00bd0002` row 74 =
  `4a 00 93 00 1c 06 01 00` (sa_yknr, dir_slot byte[597]=`0x06`). File at `/setting/sa_yknr.bin`, readback MATCH.
- **Decisive proof:** delivered a **code-corrupted** sa_yknr (bytes `0x1000..0x6000` zeroed) → cold boot →
  high-ISO capture **ERRORS** ("writing to memory card unable…"). Zeroed code can't run → the capture
  pipeline broke → **our `/setting` module is what loads.** Reverted to stock → camera normal again.
- **Why PoC/bad-magic looked like "nothing":** they DID load, they were just ineffective edits —
  the VLIW PoC (`op7 r19+=r19` at bundle `0xce80`) produced no visible luma change (that bundle/region
  is likely a map/strength pass or runs once, NOT the per-pixel luma — the sonnet caveat), and the
  bad-magic edit ran because the DSP loader does **not** validate the container magic/sum32.
- **Delivery procedure that works (owner present):**
  1. senser `writeFile('/setting/sa_yknr.bin', module)` (readback MATCH).
  2. senser `writeBackup(0x00bd0002, …byte597=6…)` + `saveBackup(0)` (we also did one updater WBI-zero
     `dd /dev/nflasha5`; later file swaps loaded on cold boot, so a single WBI-zero suffices).
  3. cold boot; shoot high ISO (YKNR must run). Scripts: `~/nex3n-dump/work/filmgrain/deliver_setting.py`,
     `deliver_revert.py` (byte→0 + delete file).
  - Gotcha: the UPDATER path is USB-flaky after many mode switches → a full camera power-cycle resets it;
    the **senser** path (silent, no on-screen step) is the reliable one for file+Backup.
- **NEXT:** now that delivery is proven, design a module edit with a GUARANTEED visible effect. The VLIW
  `0xce80` edit missed; options: (a) the agent's **Probe S** scalar-poke (writes a white marker into the
  tile — tests the scalar→tile→JPEG route directly, independent of the op7 hypothesis); (b) target the
  TRUE per-pixel-luma bundle (re-RE which of the 5 y3 programs is the pixel-pass vs map/strength pass).

## ✅✅ PIXEL-WRITE ROUTE PROVEN — grain mechanism found (2026-10-12, on camera)
Delivered the agent's **Probe S** (scalar poke, sum32 `0x6f18eb56`, 109 B, verified byte-exact):
a trampoline at chunk+`0x2fa` → the dead stub tail writes `0xFFFFFFFF` (white) to each engine tile's
top-left (`r1 = tile − 0x800`, r13=P5 window) after the pixel-pass. On camera (high ISO, redirect active):
**a clean regular grid of white markers appears in the SOOC JPEG** — vertical dotted columns spaced one
tile-width (128 px) apart, dots every 8 rows (the 128×8 YUYV tile grid). So **a scalar write into the
engine tile RAM reaches the JPEG, per-tile, controllably** (scalar → tile RAM → in-place DMA-out → YKNR →
JPEG). This is the WORKING grain-injection route — no VLIW edit, no ARM pixel write (both of which failed).
- Significance: two milestones tonight — (1) `/setting` delivery proven, (2) a CPU-reachable pixel-write
  path into the JPEG proven. The whole "grain" blocker (pixels were DSP-isolated) is broken: the SA-DSP
  **scalar** core CAN write the tile, and it reaches output.
- **NEXT (the actual grain):** replace the fixed 2-px white marker with a **per-pixel noise loop** over
  the tile's Y even-bytes (±N xorshift/LFSR in SA-DSP scalar). Needs more code space than the 16-B stub
  tail → grow the chunk (load-chain descriptor `w[5]` + terminator) or find dead space; write the loop in
  the SA-DSP scalar ISA (tooled: `sonygen/isa/sadis.py`). Amplitude ±N tunable; later per-slot grain if
  the style is reachable from the scalar side. Images/scripts in `~/nex3n-dump/work/filmgrain/`.

## ✅✅✅ GRAIN MODULE BUILT — ready for dry-run flash (2026-10-13, opus build agent)
Two disassembly-verified modules built from stock `sa_yknr.bin`, both **53508 B** (no file growth), sum32
algorithm cross-checked against stock (`0xec52e8bf`) and probeS (`0x6f18eb56`).

### Trampoline anatomy (recovered + verified from the probeS diff)
- **5 DSP cores, NOT 5 passes.** Per-core blobs at file `0xac50/0xb240/0xb830/0xbe20/0xc410` (stride `0x5f0`),
  byte-identical but for per-core address constants (DSP bases `0x3000/4000/4800/8000/8800`). Live inside
  sub-image desc3 (`0x9e60`, text `0xa170..0xd0d0`); core-base table at `0x9ea0` =
  `3000,4000,4800,8000,8800,0(terminator)`.
- **Hook = chunk+`0x2fa`** (per-core: `0xaf4a/0xb53a/0xbb2a/0xc11a/0xc70a`), the per-tile fn **epilogue**
  `add sp,#0x50`, one instruction before `r13` is restored → catches `r13` = **engine tile window =
  end-of-tile ptr**; **tile top-left = r13 − 0x800**; tile = `0x800` B = **128×8 YUYV**. Rewritten to a
  backward branch to the routine. The `+0x20` dead literal repurposed to the `0x800` constant.
- **Vertical frame-row is NOT available at the hook** (DMA-dest MMIO `0x48210/30/34` is written only in the
  pre-core driver, never in the per-tile fn) → true frame-row banding unreachable here; banding is per-core.

### Grain loop (luma-only, cheap — no multiply/Monte-Carlo)
Per-tile LFSR seed = tile address; xorshift32 (`x^=x<<13; x^=x>>17; x^=x<<5`); `noise=(lfsr&mask)−N`;
`Y=clamp(Y+noise,0,255)`; `strb; ptr+=2` (skip chroma). Clobbers **r0–r5** only. 72-B routine; source in
`<scratch>/grain-scripts/grain_single.s`. Character approximates filmgrain-cli (luma texture),
not the Monte-Carlo algorithm.

### Code space — HONEST CAVEAT (the one on-camera-unverified step)
Only **16 B proven-dead** per core (bootstrap tail); the ~884-B region after it is a **LIVE engine table**
(entries indexed `0x30..0x48`, deref'd via ptrs `0x3034/30f4/3100/3198`). The 72-B routine is placed at
chunk+`0x13c` (`0xad8c..0xadd6`), overwriting only the **high-index entries (~0x37..0x48)**, preserving every
explicitly-referenced target. **Liveness of those overwritten high-index entries is NOT statically provable**
→ **MANDATORY Q-37 `/setting` dry-run first** (shoot one high-ISO frame; on capture error/corruption, revert
Backup `0x00bd0002` byte 597→0 = stock). If load-bearing, the real fix is to reverse the desc3 core-copier
and grow the module into free DSP RAM `0x5000–0x8000` (on-camera RE).

### Built files (in `~/nex3n-dump/work/filmgrain/`)
- **`sa_yknr_grain.bin`** — all 5 cores uniform N=8/mask=15. md5 `43784d9f751f5ec1cb7010a88b496914`, sum32
  `0xd20a7fce`. Changed: routines `0xad8c/b37c/b96c/bf5c/c54c` (+0x4a each), hooks (2 B) `0xaf4a/b53a/bb2a/
  c11a/c70a`, trailer `0xd100..0xd104`.
- **`sa_yknr_bands.bin`** — cores 1-4 N={4,8,12,16} (masks 7/15/31/31), **core0 = stock (control)**. md5
  `727e4db101a179050155d4d98c9dcd7c`, sum32 `0x3db296cb`. (core0 `0xac50..0xb240` byte-identical to stock.)

### Band → N map + caveat
Banding is **per-core fixed amplitude** → **4 amplitudes {4,8,12,16} + 1 control** in one frame. The
**core→frame-region spatial mapping is NOT statically known** (the 5 cores split the frame some way —
stripes/interleave/blocks) → the 5 zones appear in whatever arrangement the engine's tile dispatch uses;
the owner reads the actual layout off the first high-ISO shot and picks a zone. Guaranteed property: 4
distinct amplitudes + control, one frame. A **true 8-band** version (`grain_bands.s`, counter-based,
`{0,2,3,4,6,8,12,16}` via `counter>>11`) is written + round-trip-verified but needs a loaded writable RAM
word + the module grow — deferred.

### Delivery & NEXT
Deliver via `/setting` redirect (`deliver_setting.py`), owner present, high-ISO shot; revert
`deliver_revert.py`. **Next (owner present): flash `sa_yknr_bands.bin` as a dry-run** — capture OK ⇒ the
high-index table was dead (route fully clear) and the amplitude zones are visible ⇒ pick the look; capture
error ⇒ revert, table is load-bearing, do the module grow. Per-style amplitude (`1 effect=1 style+grain`) =
`style-grain-coupling.md` (y0-parser + av-cam style-id, agent running). Scripts/assembler:
`<scratch>/grain-scripts/` (TODO: move into repo `code/` for reproducibility).

## ⛔ PLACEMENT DEAD — the chunk+0x13c table is LIVE (2026-10-13, E-0075/E-0076)
On-camera isolation KILLED the chunk+`0x13c` placement:
- **E-0075:** `sa_yknr_bands.bin` (grain loop at chunk+`0x13c`) **hard-hung** the camera on high-ISO capture
  (worse than a load-reject). Two variables vs the working Probe S (loop + new placement) → not isolable.
- **E-0076:** `sa_yknr_probeS_reloc.bin` — the PROVEN fixed-marker write (NO loop) at the SAME chunk+`0x13c`
  footprint — **also hard-hung.** One variable → **DECISIVE: the hang is the PLACEMENT, not the loop.** The
  high-index engine-table bytes `0xad8c..0xadd6` are **live** (the per-tile pass uses them); overwriting
  them wedges the DSP. All three reverts to stock were clean (delivery/rollback rock-solid).
- **Standing conclusion:** the only genuinely-dead code space is Probe S's **16B stub tail** (chunk+`0x08`),
  too small for a grain loop. The grain loop itself is **unproven** (never ran at a valid location).
- **ONLY remaining path = MODULE-GROW:** reverse the desc3 **core-copier** (hardware copy driver at `0xa170`,
  core-base table `0x9ea0` = `3000,4000,4800,8000,8800,0`) to copy an extra routine blob into **free DSP RAM
  `0x5000–0x8000`** (the gap between the per-core stacks), then `bl` to it from each 16B stub tail. Then
  re-test the (un-relocated) grain loop there. This is a from-scratch reverse of the copier format (how it
  reads base/length/terminator) — an offline RE task + one on-camera verify. **Not a quick experiment.**
- Delivery/rollback remain proven & reversible; camera is STOCK + working.

## ⛔⛔ MODULE-GROW BLOCKED inside sa_yknr (2026-10-13, research agent)
The grow has no in-module route — disassembly-grounded:
- **The core-copier is NOT in this module.** The "loader" at file `0xa170` does engine-MMIO bring-up
  (`0x48030/48100/48024/48004` poll+config), not a memcpy; the word-copy loops are register-restore
  epilogues. The 5 core blobs are **pre-relocated** (per-core constants baked in) and **file-contiguous**
  (stride `0x5f0`, zero gaps; core4 ends exactly at the VLIW programs `0xca00`). Placement to DSP
  `0x3000..0x8800` is done by the **EXTERNAL DSP firmware/boot loader**, directed by the core-base table
  in every sub-image header (`desc+0x40` = `{5 bases, 0}`). Copier format is external → undecodable here.
- **Table can't be extended:** `desc+0x40 {5 bases,0}` is immediately followed by live MMIO params
  (`48000,48200` at +0x58/+0x5c). Source is firmware-sequential (a 6th source = the live VLIW programs).
  Making a 6th blob ours → insert `0x5f0` (file → ~55 KB > senser limit, cascades every post-`0xca00`
  pointer) or overwrite live VLIW (breaks the engine).
- **Alternatives all dead:** (a) per-core space above a core's own stack doesn't exist (contiguous +
  descending stack); (b) live-table reuse dead (E-0075/76); (c) only the **16 B stub tails** are dead —
  too small for a 72 B loop, and not chainable (`0x4808→0x8008` = `0x3800` > branch range), each core
  needs its own for its own hook.
- **Free-RAM windows mapped** (`0x5000–0x8000` 12 KB, `0x9000+`) — unused in the static core map, but
  RAM-backing/executability is EXTERNAL → needs a probe. Built `sa_yknr_probe_freeram.bin` (md5
  `e12806a43906f7a317f974c233a8b098`): stub in the proven-dead tail writes a marker to `0x5000`
  (captures ⇒ benign RAM; hang ⇒ live/unmapped, retry `0x9000+`). **But even a pass does NOT unlock the
  grow** — there is no in-module way to LOAD code into that window.
- **STANDING CONCLUSION:** full-tile **scalar** additive grain has **no home in `sa_yknr` via the /setting
  path** (16 B/core ceiling, no self-loader). The grain loop is not buggy — it has nowhere to run. Real
  options are OUTSIDE this module: **(1)** another `sa_*` module/sub-image with large dead executable space
  at a core-reachable DSP address to host the routine; **(2)** the **VLIW route** — NO code-space wall
  (insert `op3`+`op7` into existing free bundle slots), blocked instead on the grain-SOURCE data path
  (DMA grain-LUT stream) and undecoded `op1`/`op2` (self-dither); **(3)** firmware/boot-level (out of
  scope for an offline module edit); **(4)** accept the ceiling (ship colour — fully reachable — + the
  proven pixel-write demo; full additive grain stays the hard open frontier).

## VLIW grain — INJECTION is free, the SOURCE is blocked (2026-10-13, VLIW agent)
The VLIW route removes the code-space ceiling for *injection* but re-hits the wall on the grain source.
- **op1/op2 decode (structural, 1.37M slots / 242 modules):** both are **general ALU ops** (operands spread,
  unlike op3 a=r24 / op5 ptr / op6 a=r0). **op1** has a unary signature (10% `a==b`, highest of any binary-
  shaped op) → likely a **shift** (the ÷256-normalize op, which must exist and is otherwise unassigned).
  **op2** combines into r19/r25 (sub or min/max shape). **Which is shift vs sub/AND/XOR/min-max is NOT
  statically resolvable** (vengine symbolic, saemu scalar-only, no VLIW engine emulator) → on-camera ladder.
- **Self-dither BLOCKED independent of op semantics:** the 13-bit slot has **no immediate field** (`op.a.b`,
  both register indices; only free const **r31=0**). A bounded ±N needs a mask/shift-amt/bias already in a
  register; the free finalize lanes (0xce88 S1-S4) set none, and r31=0 yields only `+0`/`×0`/`mov 0`. Live
  regs (r16 rounding const, r21 stale) = an UNKNOWN constant = uniform brightness shift, not per-pixel grain.
- **DMA grain-LUT BLOCKED by the scalar ceiling:** VLIW side feasible (op5 AGU sets a 2nd stream pointer,
  op3 reads a baked blue-noise LUT, op7 adds → REAL grain), but baking + DMA-ing that 2nd stream needs
  **scalar** engine-DMA setup (`0x48200/08/30/34`) = the exact 16 B/core ceiling. Doesn't fit.
- **BUILT foundation probe** `~/nex3n-dump/work/filmgrain/sa_yknr_vliw_probe.bin` (md5
  `7d1bb24e99f240a94e9a959c94b90fef`, sum32 `0xec5222bf`, 53508 B): single bundle edit `0xce88`
  `bfffffffffffffff→bfff39ffffffffff` = S1 **`op7 r19→r19`** (luma ×2, per-pixel, pre-clamp). **Tests
  whether 0xce88→r19 reaches the JPEG** (the prior PoC at `0xce80` showed nothing). High-ISO: brighten/clip
  ⇒ the VLIW free-lane→r19→JPEG chain is LIVE (op1/op2 ladder can proceed); no change ⇒ the VLIW branch is
  as dead as the old PoC → abandon. Reversible /setting, 8-byte edit.
- **op1/op2 on-camera ladder** (same bundle, 8 B reversible edits): `op1 r19→r19` (slot `0x0673`) →
  darken=shift, brighten=add, black=xor, unchanged=or/mov; `op2 r19→r19` (`0x0a73`) likewise.
- **Bottom line:** VLIW sidesteps code-space for injection but **both grain-source routes are blocked**
  (self-dither = no immediate; DMA-LUT = scalar ceiling). The two genuine unknowns (does 0xce88→r19 reach
  the JPEG; op1/op2 semantics) need **on-camera probes** — next camera session.
