# Engine command-table (`run_engine r0`) — PARTIAL (2026-10-13, blocked mid-analysis)

Reversing the SA-DSP engine orchestration — the lever the external expert flagged to bypass the 16 B
scalar code-space ceiling (delegate the per-pixel work to the engine, whose program/data live in the
module, not the 16 B stub). Analysis was HALTED by a safety classifier mid-trace (per the rotation rule it
was NOT reworded/retried). Partial findings captured below; the full decode (Tasks 2–5) is pending a
model rotation (sonnet/fable) or a next budget window.

## Partial findings (established before the block)
- **5 `run_engine r0` sites** in sa_yknr's scalar text: `0x1b42, 0x20f6, 0x2536, 0x2976, 0x2db6` (= P0–P4).
- **r0 values** feeding them: P0 = `0xc0000000` (a flag-shaped word); P1–P4 = `0x3180 / 0x4114 / 0x4914 /
  0x8114`. These map into the **per-core blob regions** — the SAME "live data" area whose overwrite hung
  the camera in E-0075/76 → consistent with these command tables being **load-bearing** (don't blindly
  overwrite).
- **Command-list format (P2/P3/P4 targets):** a uniform indexed command list of `[24-bit arg][8-bit
  opcode]` words, opcodes in range `0x31..0x42`; the arg at index `0x34` = `0x800` = the tile size. The
  **P1 target decoded as scalar code**, so r0 is NOT a uniform raw-table pointer across all 5 calls — the
  exact per-call semantics need more tracing.

## Command/parameter table STRUCTURE DECODED (2026-10-13, orchestrator, offline)
The `[24-bit arg][opcode]` shape resolved: **opcode/index = the HIGH byte** (file bytes `val_lo val_mid
val_hi idx`), value = low 24 bits. The P4 table (file `0xbf34`; P2 `0xb354` / P3 `0xb944` byte-identical)
is a **dense indexed parameter/register-slot table, indices `0x31..0x48` (24 entries)**:
- `0x34 = 0x800` (tile size ✓); `0x35 / 0x37 / 0x3c / 0x48 = 0x8000` (recurring — buffer/region base?);
  `0x3d` and `0x45` carry a **flag bit `0x80`** on the index; small values `0x3e=0x807`, `0x40=0x08`,
  `0x41=0x038009`, `0x42=0x0a`, `0x46=0x0b`, `0x47=0x07`; the rest are 0.
- Table **ends at index `0x48`**; what follows (`0x00/0x01×3/0x18xx…`) is a different structure (packed
  data / a second list).
- Full decoded dump (handoff artifact for the external expert): `~/nex3n-dump/handoff/cmdtable_P4_dump.txt`.
- **Open = the SLOT SEMANTICS:** which indices set src/dst buffer base, DMA stream descriptor
  (base/stride/len), VLIW-program select/launch, weight/LUT DMA, sync — and which is the DMA-OUT (→ the
  A7 noise-stream insertion point + the E-0077 output-luma write). This is the question now with the expert.
- **Significance / what it gives us:** `run_engine` went from an opaque black box to a **24-slot editable
  CONFIG table**. That is the lever the expert flagged: if a slot sets an input-stream descriptor, grain
  can be injected by **editing a few config bytes (no code, no 16 B ceiling, no VLIW-op semantics)** —
  point the engine at a baked noise tile, which is the only route to real clumped grain (A7). It also
  likely contains the OUTPUT-buffer slot → resolves E-0077 (where the final luma is written, which the
  VLIW edit at `0xce88` missed). HONEST limits: (1) we have the STRUCTURE, not yet the slot SEMANTICS
  (which index = what — the open question); (2) these tables sit in the LIVE per-core regions (overwrite
  hung the camera, E-0075/76) → edits must be surgical/additive; (3) a noise stream still needs a VLIW op
  to read+add it. So this is the biggest concrete step toward a **code-free** grain injection, not yet a
  solution.

## Two glued regions + E-0077 EXPLAINED (2026-10-13, external expert on the full dump)
The `run_engine r0` target is **TWO structures back-to-back**, not one command list:
- **Region A = a register-file IMAGE** (slots `0x31..0x48`, monotonic index ⇒ `engine_reg[idx]=value`, a
  shadow-register/descriptor dump — NOT an opcode dispatch). The stray `0x29` mid-sequence = a real
  command (barrier/kick), not a slot.
- **Region B = the inline VLIW PROGRAM**, right after Region A (starts `0x188f000a`; packed 16-bit
  syllables ×2/u32, families 0x18xx/0x50xx/0x6xxx/0x0cxx, stepping lane regs 8f/9f/af/bf/cf/df/ef).
- **E-0077 RESOLVED:** the VLIW edit at `0xce88` had no effect because it was in **Region B**, while the
  FINAL luma write is a **DMA-OUT descriptor from Region A** (programmed to engine MMIO `0x48230/0x48234`).
  The real grain injection point is the DMA-out source / a Region-B syllable that feeds it — not the VLIW
  luma register.
- **P2≡P3≡P4 byte-identical** ⇒ buffer identity is NOT in the table; the four `0x8000` slots are offsets
  into a WINDOW the scalar core re-sets before each `run_engine` (real addr = slot_base + window_base).
  ⇒ diffing tables is useless; **trace the scalar setup + the MMIO writes** (done → handoff files).
- Expert's slot-map hypothesis (confidence varies): `0x31-0x33`=geometry; `0x34`=tile size; `0x35/37/3c/48`
  =4 buffer bases (in/scratch/LUT/out); `0x40/42/46/47`=selectors/IDs; `0x41=0x038009`=DMA-descriptor body
  (stride 0x0380 + id 0x09); FLAG bit (0x3d/0x45) = "slot triggers an action, not just stores".
- **Grain plan (expert):** DON'T retarget the reciprocal-LUT stream (it feeds normalization → garbage).
  Instead ADD a DMA-in descriptor into a currently-zero slot (candidates: 0x31/32/33/36/38/39/3a/3b/3f/43/44)
  pointing at a baked noise tile, **+** a Region-B VLIW syllable that reads it and adds to luma (2 surgical
  edits; needs a free reg + free buffer base + a barrier to avoid a DMA race). Confirm the output slot by
  which value the scalar code stores to `0x48230/0x48234`.
- Handoff artifacts for the expert (private): `~/nex3n-dump/handoff/cmdtable_P4_dump.txt` (Region A decode),
  `cmdtable_mmio_trace.txt` (scalar DMA-setup trace). Next extract (expert priority): ordered P4 MMIO trace
  (slot→register), scalar window setup per call, P0/P1 tables, the run_engine handler (A/B boundary).

## DMA mechanism FULLY MAPPED + grain path (2026-10-13, expert on the MMIO trace)
- **DMA register map (confirmed from the scalar trace):** IN `0x48200` (addr/kick, writes `0xfffffffe`),
  `0x48208` (enable, 1/`0x10000`), `0x48210` (2nd IN channel or stride — unclear), `0x48218` (mask/mode,
  `0x3e`/2); OUT `0x48230` (addr/kick), `0x48234` (descriptor/base); `0x48000` channel-enable mask; status
  poll `0x94dc`/`0x94e0`/`0x94e4`. **Sync = wfi + poll** (kick, then wait on `0x94dc`). Each DMA synchronous.
- **Output luma = DMA-out to SRAM `0x9000`** (paired `0x9800` = +0x800 next tile) via `0x48230/34`.
  Confirmed in scalar code (refs at `0xa2a/0xaf4/0xf20/0x10ca/0x11b8`). The `0x8000` table values are
  engine-internal region-selects (weights world `0x40000`); the `0x9xxx` are absolute SRAM the scalar
  programs → that's why P2≡P3≡P4 (table same, scalar routes buffers).
- **Descriptor RING @ SRAM `0x91f0`, 16 B/entry:** `[+0]=addr/count`, `[+4]=0x40000000` (GO bit). Indexed
  `idx<<4` (pattern `ldr r1,[sp,r0]; lsl r1,#4; add 0x91f0; str addr,[r1]; str 0x40000000,[r1,#4]`;
  sites `0xa42/a66`, `0x1036/1078`, `0x14b8`, `0x160c`, `0x16de/16fc/176e/17c4`). Other SRAM: `0x9504/0x9508`.
- **GRAIN PATH (expert, additive = no overwrite):** append a ring descriptor `{noise_tile_addr, 0x40000000}`
  at a FREE index → kick an IN channel (`0x48200`←kick, `0x48208`←enable) → poll `0x94dc` → **one VLIW
  add-syllable in Region B** before the output store. Failure modes: occupied ring idx → hang; no barrier →
  DMA race; stage tile inside `0x9000-0x9fff`/`0x94xx` → clobber out/status; register clobber (prolog saves
  r8-r14) → need a dead lane reg at the output store. Handoff artifacts: `cmdtable_P4_dump.txt`,
  `cmdtable_mmio_trace.txt`; full scalar disasm regenerable via `sadis.py 0x400 0x2e00`.

## STRUCTURE CLOSED → grain is one live measurement away (2026-10-13, expert round 3 + my copier trace)
- **Confirmed:** descriptor = 16 B `{addr, 0x40000000(GO)}`; input ring base `0x91f0`; output base `0x9000`
  (pair `0x9800`); OUT regs `0x48230`(addr/kick)+`0x48234`(desc); status `0x94dc/0x94e0` (poll+wfi).
- **Ring batch = exactly 6 descriptors/pass** (`cmp r8,#6; bfc` loops at `0x1070`, `0xf82`). Descriptor
  index = a runtime stack variable (`ldr r1,[sp,r0]`). Prologues P0..P4 byte-identical; passes differ only
  by `r4→r0` (command-table ptr) + buffer ptrs in stack slots `[sp,#32..56]` → r8..r14 just before
  run_engine (`0x2da6-0x2db2`); a pass-type dispatcher at `0xd20` (3 modes; P4 finalize = own branch).

## SRAM-STAGING BLOCKER BYPASSED — the scalar writes DSP SRAM directly (2026-10-17)
Re-examined with the correct ISA model (`sa-dsp-isa.md`: 16-bit scalar + engine). The C-DSP-020 blocker was "**ARM**
can't write DSP SRAM" — but the **SCALAR runs ON the DSP and provably reads/writes SRAM `0x9xxx`**. Confirmed in
`sa_yknr` scalar: literals/accesses to `0x9000`(out), `0x9800`(pair), `0x91f0`(ring), buffers `0x93e0/94dc/94e0/94e4/
9504/9508`, DMA regs `0x48200/08/30/34`, GO `0x40000000` — the ring-descriptor build `{addr,0x40000000}@0x91f0` is
scalar code. ⇒ **the noise tile is staged by the SCALAR (which we author), not ARM → C-DSP-020 is NOT the blocker for
grain.** The T-1 grain path becomes scalar-only and bypasses authoring the (undocumented) engine microcode:
1. scalar PRNG loop fills a FREE SRAM tile (avoid `0x9000` out / `0x91f0` ring / active `0x94xx` buffers — find free space);
2. scalar appends a 7th ring descriptor `{noise_tile, 0x40000000}` (batch is 6/pass, `cmp r8,#6` @0x1070 — widen to 7);
3. engine consumes it as a 2nd input stream (additive ⇒ grain) — IF the engine combines streams additively (camera test).
Per-frame SEED: scalar PRNG needs a per-frame-varying seed — find a scalar-readable timer/frame-counter (open).
DeepSeek synthesis (2026-10-17, free gateway) ranked this #1 feasibility; weights-port (`0x40000`) perturb = blur not
grain; no dither/seed engine register exists in `0x40000-0x40100` (those are conv taps + geometry).
**Remaining (static):** find a free SRAM tile region + the exact ring-append site to widen 6→7 + a scalar seed source +
a scalar code cave for the PRNG. **Remaining (camera):** confirm the engine adds the 2nd stream (one shot). This is the
live grain path; no engine-microcode authoring needed. Cross-ref `grain-roadmap.md`, `sa-dsp-isa.md`.

### The input-count is DATA-DRIVEN — widening the loop auto-adds a stream (2026-10-17, DeepSeek-assisted)
Decoded the per-entry descriptor builder **`fn 0x714`** and the pass loop:
- Each pass loop (`cmp r8,#6` @**0x1070**, siblings @0xf82/0x11de/0x11ea/0x1232 — one per pass P0..P4) calls `fn 0x714`
  six times (r8=0..5), r5=stream index, r6=`[sp,112]`.
- **`fn 0x714`** builds a 16-B descriptor at `base([sp,#24]) + (*counter)*16` = `{ [+0]=addr (56*idx + geom[r11]) &
  0x3fffffff, [+4]=0x380000|flag, [+8]=0x3f0000|(size>>3), [+12]=0x401f1f }`, then **increments the counter `*[sp,#28]`
  (@0x782-786)**. That counter = **the number of input streams the engine consumes** (data-driven, not a constant).
- ⇒ **To add a 7th input stream: change the loop bound `cmp r8,#6 → #7`** (at 0x1070 and the per-pass siblings). `fn
  0x714` then auto-builds a 7th descriptor AND auto-bumps the engine count to 7. No manual descriptor/count write.
  The 7th stream's SRAM addr = `56*6 + geom` (the next slot after the 6 inputs).
- **First camera test (no PRNG, minimal):** widen one pass loop 6→7, shoot. If luma changes vs baseline ⇒ the engine
  adds the 7th stream (grain path confirmed). Then point/fill that slot with noise + a per-frame seed.
- **Open (static):** is `56*6+geom` a safe, data-bearing SRAM slot (clean test vs crash)? which pass loop(s) to widen
  first? the `0x380000`/`0x3f0000|size`/`0x401f1f` descriptor format fields for the 7th; a scalar per-frame seed +
  cave (only ~16 B nop cave @0x30b4) for the PRNG tile-fill. **Open (camera):** does the engine's per-pixel program
  actually read the Nth input additively, or only a fixed set? (the one-shot test answers this).

### Engine interface + Track B (break the wall) — next static step (2026-10-17)
The `run_engine` wrapper is byte-identical at every call site (e.g. 0x1b20-0x1b42, 0x20d4-0x20f6):
`op000a` (opcode 0x000a, undocumented prefix) → push {r8-r14,lr} → load **r8..r14 = 7 buffer pointers** from
`[sp,#32..56]` → `mov r0,r4` (r0 = COMMAND TABLE ptr, a static table in the module) → `run_engine r0`.
⇒ engine inputs = {r0 command table} + {7 buffer ptrs r8-r14} + the pre-written config regs (0x40000 weights port,
0x40100 geom). **Track B** (author one add-syllable in Region B to add noise before the output store) and Track A both
converge on decoding the **r0 command table**. DeepSeek verdict: Track A first (scalar-only, lower risk); Track B is
realistic ONLY if Region B is a simple regular `[24-bit arg][8-bit opcode]` stream — needs the full add/store semantic
slice. **Highest-value next static step (both tracks):** dump the complete r0 command table for one yknr pass, find the
A/B boundary (Region A reg-file `0x31..0x48` + `0x29` barrier → first Region B record), and locate the output-store
opcode. r0=r4 is set by the caller before the wrapper — trace r4's source (a static module table) to find the bytes.
- **I checked the "static template" hope — it FAILS:** the copier at `0xd80` copies 12×16-B records from a
  **runtime stack buffer `[sp,#12]`** (not a file constant), and marshals the ring by `r9<<4` from it. So
  the descriptor ADDRESSES are runtime-built ⇒ occupancy is NOT statically knowable; a **live dump is
  required** (expert concurs).
- **⇒ Task (1) blocker = ONE live measurement:** read ring `0x91f0` (all 6 × 16 B) + `0x9000` (first
  16-32 B) **right before run_engine P4**, plus `[sp,#32..56]` for P2/P3/P4. Gives the free index + confirms
  `0x9000`=final surface vs scatter-list. Then: if a free slot among the 6 → clean additive write
  `{noise_addr, GO}`; if all 6 busy → move the batch bound (`cmp #6→#7`) + extend the marshal source (2 edits).
- **⚠ OPEN feasibility:** `0x91f0`/`0x9000` are **DSP SRAM** — per C-DSP-020 the DSP address space may NOT
  be ARM-visible, so a senser (ARM-side) read may not reach them. If not, the dump needs a DSP-side read
  trick (inject scalar code to copy the ring into an ARM-readable region / the output) — itself an experiment.
- **Grain recipe (once the index is known):** (1) noise table resident in module (like reciprocal-LUT
  `0x238c→0x40078`), DMA'd into free SRAM (outside `0x9000-0x9fff`/`0x94xx`); (2) `{noise_addr, GO}` into the
  free `0x91f0` index; (3) barrier free (wfi+poll serializes); (4) one Region-B syllable: load the new
  stream + add to luma into a dead lane reg, before the output store.
- Handoff artifacts: `cmdtable_P4_dump.txt`, `cmdtable_mmio_trace.txt`, `cmdtable_followup.txt` (private).

## Pending (superseded above; original block hit here)
- Full command-table field decode (which VLIW program, I/O buffers, DMA stream setup `0x48200/08/30/34`,
  stream pointers/lengths, the `0x238c→0x40078` LUT DMA).
- **A7 DMA-LUT verdict:** can a command-table edit add/retarget a SECOND input stream (a baked noise tile)
  that an added op3 reads + op7 adds to luma? (= the only path to real clumped grain.)
- **E-0077 resolution:** where the engine actually writes the output luma (since `0xce88→r19` didn't reach
  the JPEG) → the true grain insertion point.
- **Undecoded-encoding sub-check** (expert's tip): is there a post-increment STORE or a flag-setting
  `add/sub rd,#imm` hiding in the rare encodings? Either drops the scalar floor.

## T-1 DECODE via DeepSeek (the external implementer; 2026-10-17)
Fed the Region-A dump + DMA facts to DeepSeek (free, OpenCode). Decode (reasoning from the table + 4-IN/2-OUT
DMA + the 6-deep ring):
- **The 6 ring descriptors/pass = 4 IN channels (0x48200/08/10/18) + 2 OUT (0x48230/34)** — 1:1, not coincidence.
- **The four `0x8000` slots (0x35/0x37/0x3c/0x48) = the per-pass BASE pointers, one per IN channel** (placeholder
  value; the scalar overwrites the real base each pass → the slot VALUE can't tag in/scratch/LUT/out).
- **The two FLAG slots (0x3d, 0x45) = the two OUT/action descriptors** (flag bit = "drives an action"); output
  luma = DMA-OUT 0x9000/0x9800.
- **0x41=0x038009 = the DMA descriptor BODY** (stride 0x0380=896B + id 0x09). **An input descriptor = a TUPLE:
  base (a 0x8000 slot) + stride/id (0x41) + count (0x34=0x800 tile). 0x40/42/46/47 = id/selector siblings.**
- **To add a noise input (REAL grain):** the Region-A slots BUILD the ring; they don't add a stream by themselves.
  The **ring @0x91f0 is the execution queue** — a noise tile needs a RING ENTRY on an IN channel. Options:
  (a) extend the kick loop 6→7 + write a 7th ring entry `{noise_addr, GO}` — ONLY if a 5th IN channel
  (0x48220/0x48228) exists; else (b) **repurpose an existing IN channel's descriptor**. Also update the 0x29
  barrier's completion count (6→7) or it hangs.
- **Safest zero slots to repurpose for the new descriptor fields: 0x39/0x3a/0x3b** (contiguous mid-block run,
  far from geometry 0x31-34 and the output/FLAG block 0x3e-48). NOT 0x31/32/33 (geometry), 0x43/44 (inside the
  output descriptor), 0x36/38 (aux of bases 0x35/37).
- **Still needed (DeepSeek's missing windows):** (1) the scalar per-pass base-patch routine → maps each 0x8000
  slot to its IN channel (in/scratch/LUT/out); (2) the inline VLIW op3 source operand → which buffer index the
  engine READS (the noise-input candidate); (3) whether a 5th IN channel exists (0x48220/28). (1)+(3) are
  statically extractable; (2) ties to the op5/two-bank decode.
- **Grain verdict (T-1b):** REAL clumped-grain via a baked blue-noise tile is MECHANICALLY possible = a ring entry
  on a (freed/5th) IN channel + a VLIW op3-read + op7-add to luma. Blockers remain: free IN channel (4 shown),
  and SRAM staging (DSP SRAM not ARM-visible, C-DSP-020). But the command-table/ring mechanism is now decoded.


- **IN-channel correction (MMIO trace, 2026-10-17):** only `0x48200/08/10/18` IN regs exist (NO 5th channel
  0x48220/28) — that is ONE IN DMA engine + the 6-deep ring = the DMA-op QUEUE. So the noise-input path is **ring
  6→7** (grain-injection-design.md §3: two 1-byte bound edits file 0x1392[0]/0x1480[0] `0x68→0x78` + a 7th ring
  descriptor `{noise_tile, GO}` written by a scalar stub), NOT "add a 5th IN channel". DeepSeek's 4-channel read
  was off; the ring-descriptor model (grain-injection-design §3/§4) is the correct one. Blockers unchanged: the
  ring is runtime-built (needs a scalar stub to write the 7th entry) + DSP-SRAM staging not ARM-visible (C-DSP-020).

## Next — ROTATION EXHAUSTED → handed off (2026-10-13) [SUPERSEDED above by the DeepSeek decode]
The command-table reverse is blocked across the enactable rotation: **opus** = classifier false-positive
mid-trace (dumping the engine command stream); **sonnet** = infra hang at launch, reproduced ×2 (died at
127 B, no work done); **fable** = classifier block on the related 16-byte sub-task earlier. Per the owner's
handoff rule, the full spec is collected in the private `~/nex3n-dump/handoff/BLOCKED-TASKS.md` (T-1) for an
external implementer or a fresh-setup run — it is pure ANALYSIS (no flash), doable by hand in any
disassembler. The `[24-bit arg][opcode]` command-list shape (opcodes `0x31..0x42`, arg `0x34`=tile size) is
the thread to pull; start from the partial findings above.

## sftfcs engine-launch structure (2026-10-17 autonomous, static — the Soft Focus module)
Decoded `sa_sftfcs.bin` scalar (`sadis.py`, from `sonygen/isa/`), distinct from the yknr analysis above:
- **ONE `run_engine` only** — `op000a`@0x200c → push {r8-r14,lr} → `mov r0,r4` → `run_engine r0`@0x2022. (yknr had 5.)
  ⇒ sftfcs = a SINGLE engine program launched once; the VLIW sub-regions found earlier (0x2370, 0x6000-0x6900 the
  chroma router, 0x9f60-0xa660) are sub-regions of that one program reached by its internal (undocumented) control flow.
- **OUT-DMA ring base = SRAM `0x13800`** (yknr used 0x91f0). Descriptor build: `r1 = 0x13800 + (idx<<4)`; writes
  `[r1+0]=1`, `[r1+4]=0x40000000` (GO); kicks `0x48230` (kick1) / `0x48234`←0x13800 then `0x48230`←1 (kick2); IN/enable
  via `0x48200/08/18`, enable `0x48208`←0x10000. OUT regs = **0x48230 (addr/kick) + 0x48234 (desc base)**, same as yknr.
- **r4 (the command-table ptr) is RUNTIME-BUILT, verified:** grepped the whole scalar — there is NO `ldr r4,[pc,..]`
  that loads a table pointer (the few `ldr r4,[pc]` load small constants 0x1c / 0x701f412); r4 at `run_engine` is
  assembled from register math (`orr r4,r0`@0x1f26, `add r4,#-1`@0x1f52, `mov r4,rX`, `ldr r4,[sp/r9,#40]`). ⇒ **the
  command table / OUT descriptors are NOT a static constant in the module file** — they live in a runtime/live region
  (as for yknr). So the descriptor→channel→Y/Cr map is **not statically decodable** (nothing static to read), and a
  live dump of the ring (DSP SRAM `0x13800`) is likely not ARM-reachable (C-DSP-020). This is a genuine runtime-opacity
  limit — NOT the safety-classifier false-positive that halted the yknr pass once. ⇒ the camera luma-finder (idle a
  candidate channel, Y/CbCr-diff) is the faster AND only clear route to the luma lane; the static map is a dead end.

## sftfcs scalar-noise-stream path — mapped, runtime-buffer blocker (2026-10-19, DeepSeek-assisted)
Owner chose the scalar route to TRUE additive grain (VLIW-operand add is exhausted — see
grain-sftfcs-confirmed.md "crash wall": engine fully packed, r6=store-address, scratch regs loop-carry/crash).
Idea: scalar adds per-pixel noise to the engine's INPUT buffer between the input-DMA fill and `run_engine`
(@0x2022) → engine processes chroma+noise = real add, no VLIW edit.

Mapped (sadis.py on sa_sftfcs scalar):
- **SRAM: 0x13000 = descriptor/scratch area, 0x13700 = IN ring, 0x13800 = OUT ring.** DMA regs IN
  0x48200(kick,0xfffffffd)/0x48208(en,2)/0x48218, OUT 0x48230/34, also 0x48004/0x48024; sync = reg-write + `wfi`.
- **Input-fill loop @0x144c-0x1478:** addr = 0x13000 + idx*0xd8 (stride 0xd8=216 B/row), calls **fn 0xd28**
  per row, then kicks IN DMA. fn 0xd28 = descriptor builder: it READS the real pixel-buffer addresses from
  **command-table fields** (r4+8/12/16/28/32/36/…, r7+56/60) and writes OUT desc (0x48234←0x13800).
- **Injection window 0x14a6-0x2008:** several DMA passes (0x48208/0x48200/0x48234 + wfi @0x1576/157a/15b4/
  1640/168c) + a long `bl r8/r0/r12` processing chain (0x1848-0x1942), then `run_engine @0x2022`. ~132 scalar
  NOPs scattered (possible caves).
- **BLOCKER (DeepSeek risk #1, confirmed by fn 0xd28):** the pixel buffers are **runtime-addressed** (command-
  table-pointed), NOT the static 0x13000 (which is descriptor/scratch → writing it crashes, matching our camera
  crashes). So a static "add noise to 0x13000" loop is wrong.

**Realistic path (multi-session):** (1) trace the pixel-buffer-address register through the scalar to just
before 0x2022 (find where input pixel data actually lands in SRAM) — OR live-dump DSP SRAM (C-DSP-020: may
not be ARM-readable); (2) identify chroma bytes in the buffer (stride 0xd8; format unknown — 108px×2B YCbCr422?);
(3) author + hand-assemble a scalar noise loop in a cave, hooked after the last IN-DMA `wfi`, before 0x2022
(save/restore r0-r3,fr); (4) per-frame seed — candidates: **0x13700+20 (ring index, read @0x2070)**, 0x40014
(MMIO @0x20e4). Minimal first proof (DeepSeek Q5): add a CONSTANT to the real pixel buffer before run_engine,
see if chroma shifts. Scalar has no confirmed strb/strh in decode — may be word-wise only (needs the full opcode
table / an assembler). Known str encodings: `str r1,[r2]`=0x1512, `str r8,[r9]`=0x1589, `str r10,[r12]`=0x15ac.

## sftfcs STEP-1 pixel-buffer trace — DONE (2026-10-19, static trace + DeepSeek cross-check)
Traced the pixel-buffer address register through the sftfcs scalar (setup 0x1380-0x143e, fill loop 0x1440-0x14ae,
**fn 0xd28 in full 0xd28-0x111e**, IN-ring build 0x14c6-0x1504, run_engine wrapper 0x200c-0x2022). Disasm dumps +
DeepSeek Q&A in job tmp (`dis_fn_d28.txt`, `dis_setup_fill.txt`, `ds_q2.txt`). Findings — several CORRECT the old notes:

1. **`0x13000` is NOT a flat pixel buffer — it's a DOUBLE-BUFFERED (ping-pong) array of per-tile descriptor/param
   structs.** Base `0x13000`; ping-pong half-stride `0x1b0`=432 B (`r2 = 0x13000 + (pp^idx)*0x1b0`, pp=`[sp,#52]`
   eor-toggled); within a half, per-tile-row entry stride `0xd8`=216 B (the fill-loop "stride" — it's the STRUCT
   size, not a pixel row). Each struct holds runtime geometry (words at +32/+36/+40/+56/+60) and **dereferenced
   POINTERS at +0xc0/+0xc4/+0xc8** (fn 0xd28 @0xfd2: `r1=r13+0xbc`; `r7=[r1+4]`=+0xc0, `r0=[r1+8]`=+0xc4,
   `r14=[r1+12]`=+0xc8, then `ldrsb [r7]`→`strb [dest]`). ⇒ writing raw noise to 0x13000 corrupts descriptors =
   explains EVERY past "write 0x13000" camera crash. (Confirms + refines the old "descriptor/scratch" note.)
2. **Engine config per pass:** from `[struct+124]` fields +56/+60 → MMIO `0x40000/04` (minus 1); from `[struct+0xbc]`
   7 words [+0..+24] → `0x40008,0c,…` (minus 1) = tile geometry. (setup 0x13b2-0x140e, repeated 0x1510-0x154e.)
3. **fn 0xd28 builds the OUTPUT ring** at `0x13800+(idx<<4)` (16-B: [+0]=addr&0x3fffffff, [+4]=GO|size,
   [+8]=…, [+12]=`0x180707`/`0x100707`) and sets OUT desc-base `0x48234←0x13800`. Per-tile OUT addr is
   runtime-computed (struct×geom + cmd-table fields +12/16/32/36/40/44 + stack). **DeepSeek cross-check: 0x13800 =
   OUTPUT** (decided by `0x13800→0x48234`); the byte-copies in fn 0xd28 move only ~4-8 B of per-tile metadata
   (plausibly chroma Cb/Cr de-interleave: 2 B × 4, src [struct+0xc0] → dest planes [r4+60]/[r4+80]/[r4+100]).
4. **IN ring `0x13700`** (built 0x14c6-0x1504, 12-B entries) holds `{[+0]=1 (enable), [+8]=tile_idx + pp_offset}`
   = **SELECTORS/indices, NOT pixel addresses.** IN channel 0x48200/08/18 kicked separately.
5. **⇒ The raw INPUT-pixel SRAM address is not a single static constant NOR a plainly-readable ring field.** It is
   distributed across (a) the runtime-filled pointers in the 0x13000 ping-pong struct (+0xc0/c4/c8), (b) engine
   config 0x40000+, (c) the engine's own index→addr mapping from the 0x13700 selectors. Static trace cannot yield
   an absolute "add noise here" address → this IS the genuine runtime-opacity wall (consistent w/ C-DSP-020 +
   earlier "r4 runtime-built"). Reading the addr back from the 0x13800 ring is WRONG (that's output).
6. **strb/strh RESOLVED — they EXIST and are used** (`strb r1,[r5]`=0x0d15, `strb r1,[r2,r0]`=0x0e12; OP8 table:
   strb=0x0d/0e/0f/10, strh=0x11/12/13/14). Supersedes the old "no confirmed strb/strh → word-wise only" note ⇒
   a step-3 hook CAN write individual chroma bytes.

**Refined NEXT step (supersedes old step-1):** the only runtime-safe hook is **pointer-relative**, not absolute-address.
Determine what the three dereferenced struct pointers **[struct+0xc0]/[+0xc4]/[+0xc8]** (and dests [r4+60/80/100])
actually point at — is one of them the **chroma INPUT** plane? If yes, a scalar hook can `ldr` that pointer at
runtime and `strb`-add noise to the pointed bytes (no absolute address, no live dump needed). That is the true
step-2 target. Minimal camera proof unchanged (DeepSeek Q5): add a CONSTANT via that pointer before run_engine,
see if chroma shifts. If the pointers turn out to be output/metadata only, fall back to live DSP-SRAM dump (C-DSP-020).

## sftfcs STEP-2 — the input buffer addr is STATICALLY DERIVABLE (2026-10-19, trace + DeepSeek-verified) ★
> ⚠⚠ **CORRECTED BY FABLE 2026-10-19 — read "STEP-2 CORRECTION" at the very end of this file BEFORE acting.**
> The META-claim (addresses are static-derivable, runtime-opacity too strong) HOLDS. But the ACTIONABLE parts
> below are WRONG: (1) **SRC1=[struct+0xc0] is the engine OUTPUT 4×2 block, NOT the chroma INPUT**; (2) k is only
> **{0,1}** (2-iter loop) so the k=7/8 addrs (0x11c00/0x12400) are out-of-table ARTIFACTS — real SRC1 = 0xB400/
> 0xD400 (pp0) · 0xBC00/0xDC00 (pp1); (3) **run_engine @0x2022 is UNREFERENCED dead code** — the executed launch
> is `bl 0x194` @0x1412/0x15ac; (4) **no NOP cave** exists on the executed path. Correct grain target = `struct[+164]`
> (UYVY input tile). Keep reading only for the audit trail; the CORRECTION section is authoritative.

**This partially OVERTURNS the "runtime-buffer blocker."** Traced who POPULATES the 0x13000 struct pointer
fields (+0xc0/c4/c8) that fn 0xd28 dereferences: it's **`fn 0x4c8`** (per-tile, called from the loop @0x12be;
sibling `fn 0x628`@0x12fa, which does NOT touch +0xc0). `fn 0x4c8` composes the fields from a **STATIC in-module
byte table `LUT_C` @ text `0x1e38`** (also 0x1e18/0x1e20/0x1e28), indexed by the tile param `k`:
- `r7 = LUT_C[k] << 11` (<<11 = ×0x800 = tile size); then
  `struct[+0xC0] = (LUT_C[k]*2+1) << 10`  (= **SRC1**),
  `struct[+0xC4] = 0x0420 + r7` (SRC2), `struct[+0xC8] = 0x0430 + r7` (SRC3), +0xBC=0x0301+r7, +0xCC/D0/D4=0x0440/48/4c+r7.
- `LUT_C` bytes (k=0..8) = `17 1b 00 00 00 00 1c 23 24`. ⇒ e.g. k=7(0x23): SRC1=`0x11C00`,SRC2=`0x11C20`,SRC3=`0x11C30`;
  k=8(0x24): SRC1=`0x12400`,SRC2=`0x12420`,SRC3=`0x12430` — all in SRAM range (~0x9000-0x13fff).
- **These ARE scalar-readable SRAM addresses, PROVEN:** fn 0xd28 does `ldrsb [SRC1]` — a scalar byte load only
  works on a scalar address ⇒ SRC1 is SRAM, not an engine-internal region offset. (DeepSeek-verified Q1-Q4.)
- **NOT re-patched** between populate (fn 0x4c8) and use: grep of the `0xbc` struct-offset shows only fn 0x4c8
  WRITES it; setup 0x13c8 + fn 0xd28 only READ it. Resolves DeepSeek's one flagged uncertainty.
- **The engine ALSO gets SRC1 as input:** setup @0x13de reads `struct[+0xC0]` and writes `(SRC1-1)` to **engine
  config port `0x4000c`** (the 7 words struct[+0xbc..+0xd4] → 0x40008..0x40020 = per-tile engine input params).
  So SRC1 is (a) static-derivable, (b) scalar-dereferenced for a 2-way chroma de-interleave, (c) handed to the
  engine as its input address. ⇒ **SRC1 = the per-tile CHROMA INPUT buffer SRAM base.**

**⇒ GRAIN HOOK (concrete, verified design):** pointer-relative, no live dump, no VLIW edit:
`ldr rX,[0x13000 + k*0xD8 + 0xC0]` (= SRC1 at runtime) → `strb`-add noise into `[rX + off]` across the chroma
bytes, inserted after the engine-config programming / IN-DMA wfi, BEFORE `run_engine @0x2022`. strb/strh confirmed
usable. Per-tile loop over k. (Static-address variant also possible since SRC1 = LUT_C[k]-derived, but
pointer-relative is safest — descriptor is authoritative.)

**Corrections to older notes:** (1) "ONE run_engine only" is WRONG — `fn 0x194` (0x194-0x1bc) is a run_engine
wrapper `bl`'d @0x1412 (before the fill loop), so sftfcs runs the engine ≥2× (0x1aa + inline 0x2022), like yknr.
(2) The "pixel buffers purely runtime-addressed, not static" blocker is **too strong for sftfcs** — the per-tile
buffer bases are composed from static module LUTs.

**Still OPEN (camera-only):** does the engine's per-pixel program actually treat SRC1's bytes as the chroma it
outputs (vs an intermediate/coeff)? Minimal proof: write a CONSTANT via `[struct+0xC0]` for one tile before
0x2022, shoot Soft Focus, see if that tile's chroma shifts. That single camera shot validates the whole hook.

## sftfcs STEP-2 CORRECTION — fable independent re-derivation (2026-10-19) ★ AUTHORITATIVE
Fable re-derived the whole STEP-2 chain from the binary (cfg.py reachability + raw byte dumps, read-only) and
found the actionable conclusions were WRONG. Corrected picture (each point re-verified by me against the disasm):

**STILL TRUE (meta-claim holds):** per-tile buffer SRAM bases ARE statically derivable = `LUT[k] << 11`; the old
"pixel buffers purely runtime-addressed, not static" blocker is too strong for sftfcs. strb/strh exist. `fn 0x194`
is a run_engine wrapper (not "ONE run_engine").

**WRONG in the original STEP-2 (corrected):**
1. **k is only {0,1}.** The sole caller of fn 0x4c8 is the loop 0x12ac-0x1306: inner idx r8 runs `r13*2 .. (r13+1)*2`
   (2 values), tile index r10=k starts 0 and +1 → **exactly 2 tiles, k∈{0,1}**. The LUTs are 8-byte with 2 live
   entries. ⇒ my `k=7/8 → 0x11C00/0x12400` were OUT-OF-TABLE artifacts. Real SRC1=(LUT_C[k]*2+1)<<10 =
   pp0: 0xB400(k0)/0xD400(k1); pp1: 0xBC00/0xDC00.
2. **Ping-pong selects the LUT PAIR.** fn 0x4c8 @0x4f4: `ldr r1,[sp,#16](=pp); cmp.eq#0; bfs 0x5ec`. pp≠0 → tables
   `0x1e18`(→struct+164) & `0x1e38`(→+0xC0..); pp==0 → `0x1e10` & `0x1e30`. Bytes: 0x1e10=`0a 0c`, 0x1e18=`10 12`,
   0x1e20=`14 18`, 0x1e28=`15 19`, 0x1e30=`16 1a`, 0x1e38=`17 1b`.
3. **SRC1=[struct+0xC0] is the engine OUTPUT, not chroma input.** fn 0xd28 copies FROM SRC1/2/3 INTO planes the
   COMMAND TABLE points to (r8=cmdtbl: dest=cmdtbl[+60]/[+80]/[+100]+off; `r6=r5+2` is the SAME plane, not a 2nd
   ⇒ my "CbCr de-interleave" was wrong). SRC1→4×2 bytes, SRC2/3→2×2 (SRC1 = full-res, SRC2/3 = subsampled). And
   fn 0xd28 runs AFTER the engine (reached from the 0x144c loop, post `bl 0x194`). ⇒ **SRC1 = per-tile engine output
   (a 4×2 downscale of a 64×32 tile) exported to runtime planes.** Writing noise there = no visible grain.
4. **run_engine @0x2022 is UNREFERENCED dead code** (literals 0x200c/0x2038 appear nowhere in text; 0x194 appears
   at 0x156c/0x16b0 = the `bl 0x194` sites @0x1412 and 0x15ac, r0=r4=0x1c static cmd table). The executed engine
   launches are **`bl 0x194` @0x1412 (pp1 pass) and @0x15ac (pp0 pass)**. (Caveat: 0x200c could be an external
   entry; irrelevant to the main flow.)
5. **No usable NOP cave** on the executed path 0x14a6-0x2022 (only isolated single NOPs). The 0x1e08-0x1e6e and
   0x1fa0-0x200a "caves" are DATA (LUT padding / a word table). ⇒ a hook needs a TRAMPOLINE, not an in-place cave.

**CORRECTED GRAIN TARGET + HOOK (fable, camera-pending):**
- **The INPUT tile is `struct[+164]` = `LUT_A[k]<<11`** (pp1: 0x8000/0x9000; pp0: 0x5000/0x6000), written by **fn 0x628**
  (@0x682-0x6c2) as **32 rows × 128 bytes in UYVY** (groups `[r7+32],[r7],[r7+64],[r7]` = U,Y,V,Y edge-padding synth),
  BEFORE the engine runs. **Chroma = bytes 0 (U) & 2 (V)** of each 4-byte group.
- **Hook point:** after fn 0x628 fills struct[+164] (i.e. after the 0x1280-0x1308 populate loop), BEFORE `bl 0x194`
  @0x1412 (and the pp0 pass before 0x15ac). Write noise to U/V bytes of struct[+164] (static addr OR
  `ldr [struct+164]`-relative).
- **Code space:** no cave ⇒ options (fable): (a) hijack `ldr r2,=0x194; bl r2` @0x1410-0x1412 → trampoline into the
  0x1e42 padding (30 B, reachable by a direct `b`, but tight for a save/restore loop); (b) dead code 0x2038-0x20d0
  (~0x94 B) as a cave (risk: maybe an external entry); (c) grow text (needs shifting the 2nd image desc @raw 0x2c20
  + name table). **(a)/(b) need care — verify before building.**

**OPEN (static):** confirm fn 0x628's UYVY layout + exact struct[+164] stride; pick/validate the trampoline site.
**OPEN (camera):** does the engine actually consume struct[+164] as its chroma input (vs an intermediate)? Minimal
proof: write a CONSTANT into struct[+164] U/V bytes for one tile before `bl 0x194`, shoot Soft Focus, see if chroma
shifts. **Lesson:** STEP-2's first pass trusted hand-computed addresses past a 2-entry table and assumed 0x2022 was
live — fable's cfg + loop-bound check caught both. Cross-check address math against loop bounds + reachability next time.

## sftfcs STEP-3 — grain hook design, static-complete + buildable (2026-10-19, fable; spot-verified by me) ★
Target = the chroma bytes of the engine's UYVY INPUT tile. Hook = a trampoline into dead code; CONSTANT-write proof
first, then per-pixel noise. Everything below is static-complete; the ONE unproven link (engine really outputs these
bytes as chroma) is the camera shot. Spot-checked by me: encodings, trampoline control-flow, register liveness.

**The input tile (fn 0x628, 0x628-0x6c2):** writes **32 rows × 128 B = 0x1000 B (64px×32, 4:2:2)** in **UYVY**
(`[U,Y,V,Y]` per 4-B group) to base **`struct[+164] = LUT_A[k]<<11`** (pp1: 0x8000/0x9000, pp0: 0x5000/0x6000),
BEFORE the engine. **CHROMA = EVEN bytes** of the tile: `off%4==0 → U`, `off%4==2 → V`; odd = luma Y. ⇒ writing all
even bytes over [base, base+0x1000) is pure-chroma (ΔY=0).

**Input-pointer evidence (strong, static):** the engine-config block (pass1 0x13a4-0x140e; pass2 ~0x14f0-0x15aa) does
`ldr r5,[r5,#40]` (= struct+0xA4 value = tile base) then `add r5,#-2`, and **r5 is untouched until `bl 0x194`**; fn 0x194
only saves/restores r8-r14+lr then `mov r0,r4; run_engine`. So **r5 = tilebase-2 is LIVE into run_engine** ⇒ it's an
engine input operand = the input-tile pointer. (Config ports 0x40008-0x40020 come from struct[+0xbc..+0xd4] = the
LUT_C ~0xB800 OUTPUT buffers — a separate path. So input=r5/0x8000-tile, outputs=port buffers.)

**Engine launch = `bl 0x194`** (run_engine wrapper) @**0x1412** (pass1) and @**0x15ac** (pass2); the launch is
`ldr r2,=0x194; bl r2`, literal `0x00000194` at text **0x156c** (pass1) and **0x16b0** (pass2). `run_engine @0x2022`
is dead (unreferenced). Hook window = after fn 0x628 fills the tile (loop 0x12ac-0x1306) and after config, i.e. at the
launch; struct[+164] is final there (no DMA refills it; config touches only r1-r3 + ports).

**Trampoline = dead code @0x2038-0x20d0 (~148 B).** Proven dead: cfg.py recursive-descent from all 17 entries does NOT
reach 0x2038/0x200c/0x2022; no literal/word in image-0 references them; not a descriptor entry; the "second image"
(desc @raw 0x2c20) is a SEPARATE address space and can't branch in. (0x1e42 padding = only 30 B, too small; growing
text = invasive.) Residual risk: an undocumented host secondary entry (low, recoverable — camera STOCK, flash on
approval only).

**THE HOOK (constant-write proof, pass1):**
- **Insertion = patch the 4-byte literal at text `0x156c`: `0x00000194 → 0x00002038`.** No instruction bytes change;
  `bl r2` @0x1412 now sets lr=0x1414 and vectors into the cave, which tail-branches to the real wrapper (lr preserved),
  whose `ret` returns to 0x1414. (For full-frame effect also patch pass2's literal @0x16b0; pass1 alone = minimal proof.)
- **Cave body overwriting 0x2038** (uses only r0-r3 = dead/reloaded after 0x1414; preserves r4=cmd, r5=tileptr; no `bl`):
```
2038: 1b53  mov r3,r5        ; r3 = tilebase-2
203a: a023  add r3,#2        ; r3 = tilebase (first U byte)
203c: 9000  mov r0,#0        ; counter
203e: 9401  mov r1,#0x40     ; constant chroma value
2040: 5032  ldr r2,[pc,#12]  ; r2 = 0x1000 (@0x2050)
2042: 0d13  strb r1,[r3]     ; write const to even byte (U or V)
2044: a023  add r3,#2        ; skip the luma odd byte
2046: a020  add r0,#2
2048: 2e20  cmp.eq r0,r2
204a: dffa  bfc 0x2042
204c: 5022  ldr r2,[pc,#8]   ; r2 = 0x194 (@0x2054)
204e: 00a2  b r2             ; tail-call wrapper -> ret to 0x1414
2050: .long 0x00001000
2054: .long 0x00000194
```
Encodings verified vs sadis tables + real dump (`strb`=0x0d.., `mov rN,#0x40`=0x94 0N, `b rN`=0x00a.., `cmp.eq`=0x2e..,
`add rN,#imm`=0xa.., `ldr [pc]`=op4 0x5). The two pc-rel offsets + the bfc offset are position-locked to base 0x2038 —
recompute if relocated. First-proof target SRAM = `(r5)+2 @0x1412` over 0x1000 B (abs: pp1 0x8000/k0 or 0x9000/k1).

**Risks:** (1) PRIMARY — struct+0xA4 might not be the engine's chroma input (undocumented engine); r5-live-into-engine
is strong evidence but camera-decides; fallback = noise the port-programmed (0xB800) buffers. (2) reg clobber — cave
must keep r4/r5 + use no `bl` (satisfied). (3) pp/k timing — reading r5 (not a static addr) auto-targets the right
half. (4) only k=0's tile noised if the engine does both k per run → partial effect (fine for proof). (5) cave
external-entry (low, recoverable).

**STATUS:** static design complete + buildable, no unencodable ops. **NEXT = build the module + CONSTANT camera proof.**
⚠ Building the .bin is non-destructive; **FLASHING is destructive/physical → owner approval required** (camera STOCK).

## sftfcs STEP-3 CAMERA RESULT — E-1 CONSTANT hook HUNG the capture (2026-10-19)
Built `sa_sftfcs_graintest.bin` (md5 549059bb…): patch literal @text 0x156c `0x194→0x2038` + cave @0x2038 writing
const 0x40 to all EVEN bytes over [r5+2, +0x1000) then tail-call `b 0x194`. Flashed (writeFile MATCH, byte445=0x06).
Shot Soft Focus → **capture HUNG on finalize**: camera stuck on the post-capture review screen, didn't auto-return;
"card not ready" on playback; could still return to shooting (NOT a hard brick). ⇒ the DSP never signalled capture
complete → ARM waited forever on the JPEG write. Camera recoverable (owner chose to iterate, not revert).
- **Diagnosis (static, post-mortem):** r5=tilebase-2 is CORRECT (`ldr r5,[r5,#40]; add r5,#-2` @0x13d8/0x13e0, untouched
  to 0x1412) — write target was right, not a stray pointer. Control-flow/regs clean (cave touches only r0-r3; r4/r5
  preserved; `b 0x194` keeps lr=0x1414). **BUT `bl 0x194` @0x1412 is INSIDE the outer loop 0x1268-0x14b4 (runs
  [sp,#12]× per capture)** → our cave ran N times, each doing 0x800 strb. Leading cause = **write volume/latency**
  (N×0x800 strb before each engine run blew the capture-time budget / a watchdog), or secondarily the write
  disrupting the engine's read of the tile. NOT a wrong target, NOT a control-flow bug.
- **E-2 built (`sa_sftfcs_graintest2.bin`, md5 7e9b8dae…):** identical but COUNT literal @0x2050 `0x1000→0x20` (32 B =
  16 chroma samples). Latency ↓128×. If it captures (tiny chroma marks, no hang) ⇒ cause was volume → scale up. If it
  still hangs ⇒ writing the tile pre-engine is itself the problem → fall back to a NO-OP cave (trampoline only, `ldr
  r2,=0x194; b r2`, no write) to prove the control-flow, then rethink the write (smaller sub-span / write engine
  OUTPUT instead / guard to run once via an SRAM flag).
- **Bug caught pre-flash (kept for the record):** fable's cave had `0x204c: 5022` (ldr from 0x2058=garbage); correct
  is `0x5012` (off=1 → 0x2054). I fixed it before building. Always round-trip the patched module through sadis.py.
- **STATUS: E-2 built, awaiting camera reconnect + flash (owner approval).** Flash flow in grain-RESTART.md.

## sftfcs STEP-3 — E-2 + NO-OP both HUNG → the TRAMPOLINE is the problem, not the write (2026-10-19) ★
- **E-2 (count 0x20, tiny write) HUNG the capture** — same symptom as E-1. ⇒ NOT write volume/latency.
- **E-3 `sa_sftfcs_noop.bin` (cbbdb35e) = NO-OP cave** (trampoline only: redirect launch literal 0x156c→0x2038; cave
  = `ldr r2,=0x194; b r2`; NO write) — **ALSO HUNG.** A no-op trampoline is functionally identical to stock
  (`bl 0x194`→wrapper→engine→ret to 0x1414). Its hanging proves the WRITE was never the cause — **routing the
  engine launch through the cave @0x2038 itself breaks capture.**
- **Static isolation (post E-3):** literal `0x156c` is consumed ONLY by 0x1410 (not shared; 0x16b0 only by 0x15aa) →
  the redirect affects only pass1's launch, nothing else. NOTHING references 0x2038/0x200c/0x2022 (no u16/u32 anywhere)
  → not a handler pointer, not reached by a data table. ⇒ the hang = **branching to 0x2038 does not execute.**
- **CONCLUSION (H1): the dead-code tail 0x200c-0x20d0 is loaded in the module file but is NOT in the scalar's
  executable window** — you cannot branch there and run. fable's "trampoline into dead code 0x2038" was WRONG:
  dead-in-file ≠ executable-as-branch-target. This is the old **"scalar code-space ceiling"** wall surfacing: no
  injected code runs outside the active region.
- **E-4 built `sa_sftfcs_noop1e42.bin` (d60770e5):** same no-op but cave @**0x1e42** — padding INSIDE the active code
  span (0x194-0x1f00), vs 0x2038 which is past it. Decisive test: captures ⇒ 0x1e42 is executable, 0x2038 was the
  problem → build the write-loop at 0x1e42 (30 B free, enough for a tight loop). HANGS ⇒ no executable cave space
  exists at all → the scalar-write approach is blocked by the code-space wall → PIVOT (VLIW substitution fallback
  `spread12`, or the engine command-table route, or accept colour-error grain).
- **Lesson:** a NO-OP trampoline is the right first camera test for ANY code-injection hook — it isolates
  "can we even run code here" from "does our payload work." Should have flashed the no-op FIRST, before the write.
- **STATUS: E-4 (0x1e42 no-op) built, awaiting camera reconnect + flash.**

## sftfcs STEP-3 — CAMERA RESULTS E-4..E-7 (2026-10-19) ★ grain injection PROVEN; cave = 30 B only
- **E-4 `sa_sftfcs_noop1e42.bin` (d60770e5) = no-op cave @0x1e42 → CAPTURED FINE.** ⇒ 0x1e42 (padding INSIDE the
  active code span, before the live teardown stub 0x1e60) IS executable; the trampoline mechanism works
  (redirect launch literal 0x156c→0x1e42; `ldr r2,=0x194; b r2`). Confirms 0x2038 failed because it's OUTSIDE the
  executable window, not because of the trampoline.
- **E-5 `sa_sftfcs_grain1e42.bin` (bd5fd653) = write-loop @0x1e42** (30 B, const 0x40 → all EVEN=chroma bytes of
  struct[+164] tile, count 0x1000 via `lsl r2,#6`) → **CAPTURED, visible GREEN CHROMA.** 🎯 **Chroma injection into
  struct[+164] reaches the SOOC JPEG — confirmed. The write path works.** Artifact = **vertical green stripes**
  (we hooked only pass1 @0x1412; pass2 @0x15ac does the interleaved alternate columns unmodified) = confirms the
  **column-interleaved two-pass** structure. Green = flat 0x40 in U&V (both < neutral 128). Frame saved:
  `work/filmgrain/results/E5_grain1e42_const40_pass1_greenstripes.JPG`. (First real write test; E-1/E-2 had hung on
  the non-exec 0x2038, so the write itself was only tested here.)
- **E-7 `sa_sftfcs_grainadd.bin` (914d568f) = ADDITIVE loop chained 0x1e42 + `b 0x1e62` → cave2 @0x1e62** (ptr²-hash
  delta 0..7 added to chroma) → **HUNG.** Since E-4/E-5 (self-contained @0x1e42) worked and only the CHAIN to
  0x1e62 was new ⇒ **0x1e62 (padding AFTER the live stub 0x1e60) is NOT executable** (same as 0x2038). **The "30+16"
  chain FAILS; usable executable cave = ONLY the 30 B at 0x1e42.**
- **Consequence:** 30 B holds a flat-constant chroma write (proven) but NOT an additive per-pixel loop (~36 B:
  ldrb+hash+add+strb+ptr+++cmp+bfc+tail+literal). Real grain (additive + PRNG + per-frame seed) needs a BIGGER
  executable region → the only source is REPURPOSING existing EXECUTED scalar code (clean-out), since dead-in-file
  regions aren't executable. (Investigation in progress.)
- **Net proven:** the scalar CAN inject chroma that reaches the JPEG (struct[+164], pass-hooked, additive-capable);
  the blocker is now purely executable-code-space, not the mechanism.

## sftfcs STEP-3 — E-8: fn 0x628 is NOT the injection point (camera FALSIFIED fable, 2026-10-19) ★
- **E-8 `sa_sftfcs_628test.bin` (37764849):** minimal test of the "repurpose fn 0x628" idea — patched fn 0x628's
  own synth loop to write CONSTANT chroma (0x698 `ldrsb r1,[r5]`→`mov r1,#0x40`; 0x6ac `ldrsb r2,[r6]`→`mov r2,#0x40`),
  NO launch redirect, 4 bytes changed. Module loaded (readback md5 matched).
- **RESULT: stock Soft Focus, NO green at all** (capture fine). ⇒ **modifying fn 0x628 does NOT reach the output.**
  Contrast E-5 grain1e42 (write the SAME tile addr but right before `run_engine` @0x1412) → green. Same tile, different
  TIME → **the effective write must happen just before run_engine; fn 0x628 (@0x12fa, earlier) is too early.**
- **Why:** the engine's real input tile is (re)loaded between fn 0x628 and the launch — most likely a **DMA loads the
  actual image over it** (so fn 0x628's scalar writes are overwritten), and/or still-capture takes a different branch
  in fn 0x628's prologue (0x650-0x682 has several conds → 0xba0/0x744/0x8dc; the 0x684 loop I patched may be a dead
  path for this mode). Either way: **fable's "fn 0x628 = injection site / ~1590 B of space" is FALSIFIED by the camera.**
  (Also fable's size was wrong — fn 0x628 is 0x628-0x6d8 = 176 B, ret @0x6d8, not 1590 B.)
- **Confirmed injection point = ONLY the launch hook** (scalar write to the engine input tile in the window AFTER the
  last input-DMA, right before `run_engine`). That is the 0x1e42 cave (30 B), the single proven-effective spot.
- **Path forward:** keep the launch hook (redirect 0x156c→0x1e42), and from the 30 B cave `bl` to a LARGER noise
  subroutine placed in executable space (a real executed function body), so it runs at launch time (post-DMA) with
  r5=tileptr live. `bl rX` (register) has no range limit; the target must be genuinely executable (a live function's
  space) AND its normal use must not break capture when overwritten (or its normal call be neutralized). Finding that
  safe host is the open task. The 30 B cave itself can only hold: setup + `bl sub` + tail-call (fits). **Lesson
  (again): the camera, not static reachability, decides what reaches the output — test the injection TIMING, not just
  "can code run here."**
