# Grain code-cave — can >16 B of grain code run in sa_yknr and reach the output?

Assessment written 2026-10-14, offline static analysis on the owner's own NEX-3N dump
(`sa_yknr.bin`, 53508 B, md5 `54acf2988273c0a1f98afc9940f34d60`). Answers the standing question
after MODULE-GROW was blocked (`dsp-grain-scope.md`): the proven per-tile hook gives only **16 B/core**
of dead code, and a real per-pixel luma grain loop is ~38–48 B. This doc assesses every route to
">16 B of grain code reaching the output", ranks them, and gives an honest top-line.

Legal basis: authorized personal interoperability RE on hardware the owner owns (EU Directive
2009/24/EC Art. 5(3)/6). 100% offline, analysis/design.

---

## TOP-LINE VERDICT (read this first)

**Real, full-frame injected film grain is NOT reachable on this hardware via these means.** Every
lever is independently capped:

- **16 B/core** is the only proven-dead executable space; a fresh full-blob scan found no second
  clean cave (the blob-tail zeros are embedded in the proven-live, E-0075/76-hang Region-A table).
- The SA-DSP **`b` range is ±0x1000 (±4 KB), not ±0x2000** (corrected below). The *return* branch
  limits any cave-chain to **2 stub tails ≈ 26 B usable**, and only on **one core per cluster** —
  so chaining yields **partial-frame** grain (≈2/5 of the frame), banded, not full-frame.
- Free DSP RAM `0x5000–0x8000` exists but **nothing in the module can load code into it** (external
  firmware places the cores; no in-module loader — confirmed, `dsp-grain-scope.md`), and **no single
  free-RAM address is reachable by branch from all 5 hooks** (core 0 reaches none).
- **No free module file space** for a routine or a noise tile (largest usable run 56 B at the file
  tail, not an executable DSP address; everything else < 32 B).
- **VLIW is unauthorable** (ISA undecoded, no engine emulator; the r19 bundle probes at
  0xcbf8/0xcc30 had *no* camera effect → the output reg is unreachable).
- **DMA copies, it does not accumulate** → a DMA-in to `0x9000` overwrites luma (destroys the
  image); it cannot *add* grain. And there is **no high-entropy table** in the module to use as a
  baked noise source (the reciprocal LUT at `0x40078`/file `~0x238c` is a smooth ramp, H=3.31).

So: **accept the 16 B ceiling for injected grain.** The shippable result is colour (solved) + the
proven Probe S pixel-write demo (sparse speckle). The actual *grain look* the project wants is far
cheaper via the zero-code **native-noise-shaping** route (`grain-wide-analysis.md` §4-#1), which is
not "grain code" but reaches the perceptual goal.

The one injected-code experiment still worth a single flash — if a tech-demo of real per-tile grain
over part of the frame is wanted — is the **2-chunk stub-tail chain** (Path 2 below, core 0),
giving ~26 B for a per-tile-seeded full-tile loop over core 0's tiles. Needs-probe, partial-frame,
honestly marginal.

---

## Facts established fresh this session (disassembly-grounded)

All from `~/nex3n-dump/sonygen/isa/{sadis,vdump}.py` on the stock module (byte-identical to the
`safeboot/out3n/...` copy).

### F1. The dead region per core = 16 B stub tail + 4 B literal (confirmed by decode)
Core 0 blob loads at DSP `0x3000` (file `0xac50`). Bootstrap + shutdown stub:
```
file 0xac50 dsp 0x3000  505f  ldr sp,[pc,#20]   =0x4000   <- LIVE literal @0xac68
file 0xac52 dsp 0x3002  505e  ldr r14,[pc,#20]  =0x4000   <- LIVE literal @0xac68
file 0xac54 dsp 0x3004  5051  ldr r1,[pc,#20]   =0x31d0   <- LIVE literal @0xac6c (main entry)
file 0xac56 dsp 0x3006  00b1  bl  r1
file 0xac58 dsp 0x3008  ...   ___ 16 B DEAD SHUTDOWN STUB (8 slots) ___  <- Probe S lives here
...                           (ldr r1=0x48208; mov r2,#0; str; nop; wfi; nop; b 0xac5e; nop)
file 0xac68 dsp 0x3018  4000  .long 0x00004000  <- LIVE (bootstrap sp/r14 init)
file 0xac6c dsp 0x301c  31d0  .long 0x000031d0  <- LIVE (bootstrap main entry)
file 0xac70 dsp 0x3020  8208  .long 0x00048208  <- DEAD (only the stub read it) — reusable constant
```
Dead executable = **`0xac58..0xac67` (16 B)**; dead constant = **`0xac70` (4 B)**. The two literals
in between are live. Identical in all 5 cores (byte-identical blobs). This is the physical origin of
the ceiling and it is real.

### F2. The hook and return point
Core 0 per-tile epilogue hook = file `0xaf4a` (DSP `0x32fa`), stock instruction `a50f` =
`add sp,#0x50`; the return lands at `0xaf4c` (DSP `0x32fc`). Per core: hook = `base+0x2fa`,
return = `base+0x2fc`. Probe S overwrites the hook with `b` → stub tail, which re-executes the
displaced `add sp,#0x50` and branches back to `base+0x2fc`.

### F3. Branch range = ±0x1000, NOT ±0x2000 (corrects the brief and prior notes)
From the ISA (`sadis.py`): `b` target = `a + 4 + 2·signext12(disp)`, `disp ∈ [−2048, +2047]`
⇒ reach = `[a+4−4096, a+4+4094]` ≈ **a ± 0x1000 (±4 KB)**. Verified against the real `b 0xac5e`
in the stub. This halves every "reachable cave" estimate in the earlier docs.

### F4. The only dead executable space is the 16 B tails — no second clean cave
Full scan of the core-0 blob (`0xac50..0xb240`) for `0x0000`/`0xffff` runs ≥ 6 B: only three 6-B
nop gaps inside live code, plus ~24 B of zeros at the blob tail (`0xb226..0xb23e`). But the blob
tail is **not** clean padding — it sits immediately after live Region-A pointers
(`0x3198` @`0xb220`, `0x30f4` @`0xb224` — the "deref'd via ptrs 0x3034/30f4/3100/3198" of the engine
table) and contains a `b 0xb240` word at `0xb230`. This is inside the exact structure E-0075/76
proved **load-bearing** (overwriting the command-table region hard-hung the camera). Core 4's tail
overlaps the VLIW program region (the NOP bundle `f7e13edc87fb701f` appears at `0xc9f8`). ⇒ **No
usable second cave; 16 B/core stands.**

### F5. Reachability matrix (branch ±0x1000) — chaining is clustered and return-limited
Stub tails (DSP / file): core0 `0x3008`/`0xac58`, core1 `0x4008`/`0xb248`, core2 `0x4808`/`0xb838`,
core3 `0x8008`/`0xbe28`, core4 `0x8808`/`0xc418`.
- **Forward chain** (stub→stub): only `0↔1`, `1↔2` (cluster A = {0,1,2}, chain 0→1→2) and `3↔4`
  (cluster B = {3,4}). `0x4808→0x8008` = 0x3800 ≫ range.
- **Return** (stub→epilogue): epi0 reachable only from stubs {0,1}; epi3 from {3,4}. ⇒ the *last*
  chunk of a chain must be stub 0 or 1 (for core 0), limiting a returnable chain to **2 tails**.
- **Cluster A's middle tail (core 1) is shared** by any core-0 or core-2 chain ⇒ at most **one**
  core per cluster can host a 2-tail loop. Net: **≤ 2 cores** frame-wide can run a real loop; the
  other 3 get ≤ 16 B each.
- **Free RAM `0x5000–0x8000`:** reachable only piecewise (cores 1,2 ≈ `0x5000–0x5afc`; cores 3,4 ≈
  `0x72fe–0x8000`; **core 0 reaches none**); **intersection of all 5 hook reaches = EMPTY**.

### F6. No free file space, no noise source
Largest single-byte run in the whole file: 99 B of `00` in the header (`0x9d..0x100`, descriptor
space, unusable) and 56 B at the module tail (`0xd0c8..0xd100`, past the loaded text — not an
executable/addressable DSP region). All other runs < 32 B; total ~286 B scattered. Highest-entropy
256-B window H≈6.4 bits/byte (ordinary code density, not random); the reciprocal LUT (`~0x238c`)
is a smooth monotonic ramp, H=3.31. **No baked routine and no baked noise tile has a home.**

---

## Path-by-path assessment

### Path 1 — `run_engine` custom table / overwrite a dispensable program — **BLOCKED**
`run_engine r0` consumes a 24-slot register/descriptor table (Region A, slots `0x31..0x48`; decoded
in `engine-command-table.md` / `handoff/cmdtable_P4_dump.txt`) and runs one of the module's 5 VLIW
programs (clusters `0x34d8/0x3ad8/0x6c78/0x9a48/0xc9f8`).
- **Can't make the engine run our code:** authoring a grain VLIW program is blocked — the VLIW ISA's
  arithmetic/store semantics are undecoded, there is no engine emulator, and the on-camera r19
  bundle edits (0xcbf8/0xcc30) had **no JPEG effect** → the output luma is a DMA-OUT of an undecoded
  op5/AGU stream, not a reachable register (E-0077).
- **No dispensable program to overwrite:** sa_yknr does only luma NR; all 5 clusters are that
  pipeline. Removing/replacing one breaks the pass (or hangs, E-0075/76). No free space to *add* a
  6th program; the command-table region edits hang.
- **Narrow additive sub-idea** (edit one zero slot → DMA-in a noise stream + one `op7` add-syllable,
  `engine-command-table.md`): stays **needs-probe but blocked** — no noise source (F6), ring
  occupancy is runtime-built (needs a live DSP-SRAM read, possibly senser-unreachable, C-DSP-020),
  and it still needs the op7 source reg that the null r19 probes never confirmed.
- Verdict: **BLOCKED** (unauthorable VLIW + no dispensable program + table edits hang + no source).

### Path 2 — larger scalar cave reachable by branch — **BLOCKED (clean) / NEEDS-PROBE (partial)**
- A single clean cave > 16 B does **not** exist (F4). The blob-tail zeros are in the E-0075/76 hang
  region.
- **NEW: cross-core stub-tail chaining.** With range ±0x1000 the stub tails chain within clusters
  (F5). Because the *return* must reach the host's own epilogue, a returnable chain is **2 tails
  ≈ 26 B usable** (32 B raw − displaced `add sp,#0x50` − 1 forward `b` − 1 return `b`), plus the two
  dead literals (`host+0x20`, 4 B each) for constants. This **is** > 16 B and **does** reach the
  output (Probe S proved stub→tile→JPEG). **But:** (a) it steals a neighbour core's teardown stub,
  so that core can't also host a loop ⇒ **partial-frame** (≤ 2 cores frame-wide, cluster-A middle
  tail shared); (b) borrowing a *neighbour's* teardown stub is one unproven variable (Probe S showed
  a core's *own* teardown-stub destruction survives) → 1 flash to confirm; (c) 26 B fits a full-tile
  loop with a **per-tile seed** (aperiodic across tiles) but not a full xorshift32 (true emulsion
  grain). Verdict: **NEEDS-PROBE, partial-frame, marginal** — the best injected-code route, below.

### Path 3 — DMA-fill a pre-baked grain tile onto `0x9000` — **BLOCKED**
- **DMA copies, it does not accumulate.** A DMA-in to the output SRAM `0x9000` *overwrites* luma →
  destroys the image; it cannot *add* grain. No evidence of a DMA read-modify-write/accumulate mode
  in the mapped register set (`0x48200/08/30/34`).
- **No noise source and no scratch tile** (F6): no module free space to bake a 128×8 noise tile, and
  the only high-entropy-ish tables don't exist (reciprocal LUT is a smooth ramp).
- To *add* rather than overwrite, you need a scalar RMW loop (→ the 16 B/26 B code-cave problem) or a
  VLIW `op7` (→ Path 1, blocked). Verdict: **BLOCKED** (overwrite-not-add + no source).

### Path 4 — two-hook / chaining a per-frame point with the per-tile hook — **BLOCKED (no site)**
A per-frame hook could amortize setup (e.g. fill a noise LUT into free RAM once; per-tile hook reads
it). But: there is **no proven per-frame hook site with free code space** (the pre-core driver /
loader is all live; same 16 B / no-free-space ceiling), filling free RAM needs a code loop there is
no room for, and the per-tile read-add is still the ~18 B loop that doesn't fit 16 B. It **moves** the
ceiling, it doesn't remove it. Verdict: **BLOCKED** (no site, same wall).

### Path 5 — other mechanisms
- **VLIW `op7`→r19 at a free bundle slot** (injection is code-space-free): blocked on the grain
  *source* (no immediate field; no noise stream; DMA-LUT needs the scalar ceiling) and on the
  repeatedly-null "does r19 reach the JPEG" question. **Needs-probe, low confidence.**
- **Native-noise-shaping** (`grain-wide-analysis.md` §4-#1): shape the sensor's own per-pixel noise
  with the NR gate + chroma-by-luma LUT + sharpen/coring + tone lift — **zero DSP code**, Backup/p3
  levers, reversible, already-proven surfaces. This is **not "grain code"** but it **reaches the
  grain look**, which is the project's actual goal. **Buildable now; recommended for the look.**

---

## Ranking

| # | Route | Gives > 16 B reaching output? | Full-frame? | Verdict |
|---|---|---|---|---|
| 1 | **2-chunk stub-tail chain (Path 2)** | **yes, ~26 B** | **no (≤2/5, banded)** | **needs-probe** — best injected-code option |
| 2 | Native-noise-shaping (Path 5) | no (no code) | yes | **buildable** — best path to the *look* |
| 3 | 16 B speckle on all 5 cores (status quo) | no (16 B) | yes (speckle) | buildable (Probe S proven) |
| 4 | VLIW op7→r19 (Path 5) | n/a (code-free inject) | yes if it worked | needs-probe, repeatedly null |
| 5 | run_engine additive DMA (Path 1) | — | — | blocked (VLIW + source + ring) |
| 6 | DMA-fill grain tile (Path 3) | — | — | blocked (overwrite-not-add) |
| 7 | Two-hook (Path 4) | — | — | blocked (no site) |

---

## Most promising injected-code route — exact offsets (Path 2, core 0)

**What:** host a ~26 B per-tile-seeded luma grain loop across **two** stub tails, run from core 0's
hook, covering core 0's tiles. (Core 3 can host an identical chain in cluster B; the other 3 cores
get ≤ 16 B.)

**Layout (DSP / file):**
- Hook `0xaf4a` (DSP `0x32fa`): overwrite `a50f` → `b 0x3008` (to core-0 stub tail). *(= Probe S.)*
- **Part 1** @ core-0 stub tail `0xac58` (DSP `0x3008`), 8 slots:
  `add sp,#0x50` (displaced) · seed from r13 · ≤5 payload · `b 0x4008` (→ core-1 stub tail).
  Forward branch in range: `0x4008 − 0x300c = 0xFFC = 4092 ≤ 4094` ✓ (disp 2046, the tight edge).
- **Part 2** @ core-1 stub tail `0xb248` (DSP `0x4008`), 8 slots:
  ≤7 payload (loop body + control) · `b 0x32fc` (→ core-0 epilogue). Return in range:
  `0x32fc − 0x400c = −0xD10 = −3344` ✓.
- Constants: dead literals at `0xac70` (DSP `0x3020`) and `0xb268` (DSP `0x4020`), 4 B each.
- **Write target = proven:** the loop writes the luma even-bytes of the tile at `r13 − 0x800`
  (SRAM `0x9000` window) → reaches the SOOC JPEG (Probe S / E-0078).

**Algorithm that fits ~26 B** (per-tile-seeded, aperiodic across tiles): `x = r13` (tile ptr, unique
per tile); loop the 1024 luma bytes with `x = x*k + c` (or an xorshift step if it fits), `Y =
clamp(Y + ((x>>n)&mask) − bias)`, `strb`, `ptr += 2`, `cmp/bfc`. Character ≈ structured per-tile
grain — better than 16 B speckle, short of true xorshift32 emulsion grain. Assembler/encodings:
`<scratch>/grain-scripts/saasm.py`, `grain_single.s`.

**Probes required (one flash each, reversible `/setting` redirect, revert = stock md5 `54acf298`):**
1. Overwrite core 1's teardown stub with core-0 part-2 code and shoot high-ISO — does capture
   survive borrowing a *neighbour's* teardown stub? (Expected yes; Probe S survived own-stub
   destruction.) If it hangs → chaining is dead, keep the 16 B ceiling.
2. If capture survives, run the full chain and read core 0's grain off a flat high-ISO frame —
   confirm the core→region map doesn't make it an ugly stripe.

**Honest limits:** partial-frame (≤ 2/5), banded by the unknown core→region map; the 26 B seed-loop
is grain-ish, not emulsion grain; and the whole thing only matters if partial grain is acceptable as
a tech demo. For a convincing *full-frame* grain look, prefer native-noise-shaping (Path 5 #2).

---

## Reproduce
```
cd ~/nex3n-dump/sonygen/isa
MOD=~/nex3n-dump/sonygen/sa/3N_p8/sa_yknr.bin        # == safeboot copy, md5 54acf298
python sadis.py $MOD                                  # whole module (text-rel)
# core-0 bootstrap + stub tail + hook were decoded via the file-offset helper in this doc's session
# (DSP addr for core0 = file - 0xac50 + 0x3000); stub tails at blob+0x08, hook at blob+0x2fa.
```
Branch-range and reachability math: `b` target = `a+4+2·signext12(disp)`, disp∈[−2048,2047] ⇒ ±0x1000.
Core bases DSP {0x3000,0x4000,0x4800,0x8000,0x8800}, file {0xac50,0xb240,0xb830,0xbe20,0xc410},
blob stride 0x5f0.
