# Grain via a complex-effect module — does Soft Focus / a Picture Effect beat sa_yknr as a host?

Assessment written 2026-10-14. Offline static analysis on the owner's own NEX-3N dump. Resolves
**angle A8** (`grain-angles-overview.md`: "host routine in another `sa_*` module", previously
"❓ unexplored, lowest confidence") and **option (1)** of the MODULE-GROW standing conclusion
(`dsp-grain-scope.md`: "another `sa_*` module/sub-image with large dead executable space at a
core-reachable DSP address to host the routine").

Legal basis: authorized personal interoperability RE on hardware the owner owns (EU Directive
2009/24/EC Art. 5(3)/6). 100 % offline, analysis/design, no binary edits.

---

## TOP-LINE VERDICT (read this first)

**No. A complex-effect module does NOT give a materially better grain injection point than
`sa_yknr`.** It wins on exactly one axis — *packaging/trigger* — and hits the identical three walls
on everything that actually blocked grain.

- **The only Picture Effect with a redirectable, size-legal, user-selected module is `sa_sftfcs`
  (Soft Focus).** `sa_tbox` (Miniature) is the only other effect module and it is **disqualified by
  size** (77 444 B > the ~53 508 B senser `writeFile` limit). Every other complex effect (Toy, Pop,
  Posterization, Retro, Soft High-Key, Partial Color, HC Mono, HDR Painting, Rich-Tone Mono,
  Watercolor, Illustration) has **no SA-DSP module at all** — it is ISP/YC hardware or a
  parameter-only art-effect path (C-MOD-030), so there is nothing to redirect.
- **Code space:** `sa_sftfcs` is **not** better than `sa_yknr`. Its teardown stubs are smaller/less
  clean (they flow straight into the literal pool, or the `wfi` is a live engine-sync wait with code
  continuing after it), and its big zero runs (104 B @ file `0xaa18`, 62 B @ `0x87e2`) sit at the
  **module tail past the loaded text** — non-addressable, exactly like yknr's tail runs. No ≥38 B
  branch-reachable executable cave at a pixel point. Same 16-B-class ceiling.
- **Output reach:** a genuine but *minor* plus — sftfcs's per-pixel output is **proven visible in the
  JPEG** (C-MOD-051) and is cleanly full-frame luma, whereas yknr's luma/chroma role "is not settled"
  (C-DSP-003). But **yknr's reach was also proven** (Probe S). The point that matters — a *modifiable*
  per-pixel point — is **VLIW** in sftfcs (convolution + blend run through `run_engine`), i.e. the
  same unauthorable engine whose output reg E-0077 proved unreachable. A complex effect is **more**
  VLIW-bound, not less.
- **Noise source:** same wall. sftfcs's kernels are smooth unity-gain blur weights (each sums to 256,
  C-MOD-021) — low entropy by construction, like yknr's smooth reciprocal LUT. No per-pixel counter,
  no LFSR, only a tile pointer (yknr's r13 again).

**The one durable takeaway:** *if* the scalar-space wall is ever broken independently (a V1–V5 trick
that yields a ≥38 B loop, or the external core-copier reversed to load code into free RAM `0x5000–
0x8000`), **then `sa_sftfcs` is the better HOST than `sa_yknr`** to carry the routine — purely because
"select Soft Focus → get grain" is exactly the owner's "1 effect = grain" goal, leaves normal
shooting pristine, and writes to a proven-visible output tile. That is a *conditional host-selection*
win, not a new way through the wall. A8 is therefore resolved: **✗ evaluated — same walls; sftfcs is
the better host only conditional on an independent scalar-space unlock.**

---

## TASK 1 — Inventory of imaging-effect modules

### Which effects map to a redirectable SA-DSP module (C-MOD-030, C-MOD-007)

| Picture Effect | SA module? | Per-pixel full-frame DSP pass? | Redirectable via `0x00bd0002`? |
|---|---|---|---|
| **Soft Focus** | **`sa_sftfcs`** (0x18) | **yes** — 3×3 + 5×5×2 convolution + blend | **yes** (file-id 55) |
| **Miniature** | **`sa_tbox`** (0x17) | **yes** — per-block processing via `run_engine` | yes (file-id 54) **but see size** |
| HDR Painting | — (`Start_Art_Effect` 0xa52b8) | — | no module |
| Rich-Tone Mono | — (`Start_Richtone_Monochrome` 0xa5ffa) | — | no module |
| Toy / Pop / Posterization / Retro / Soft High-Key / Partial Color / HC Mono | — (no `sa_func_*`) | ISP/YC hardware only | **no module** |
| Watercolor / Illustration | — (PARAMID only) | — | no module |

So the complex-effect host universe is **two modules**, and only **one** is viable (next).

### Candidate modules — file, size, redirect row (file == stock, md5-verified)

Path for all: `~/nex3n-dump/safeboot/out3n/nflasha8_unpacked_unpacked/sabin/` (== `sonygen/sa/3N_p8/`).

| Module | Role | Size (B) | md5 | codectype | file-id (= `0x00bd0000` slot) | `0x00bd0002` redirect byte offset `8·id+5` | Fits ~53 508 B write limit? |
|---|---|---|---|---|---|---|---|
| **`sa_sftfcs.bin`** | **Soft Focus** | **43 652** | `c64ce801…` | 0x18 | **55** | **0x1BD** | **yes ✓** |
| `sa_tbox.bin` | Miniature | 77 444 | `1c783c3c…` | 0x17 | 54 | 0x1B5 | **no ✗** (> limit) |
| `sa_yknr.bin` (baseline) | Luma NR | 53 508 | `54acf298…` | 0x1c | 74 | 0x255 | yes (at the limit; proven) |

Redirect-byte offsets derive from the verified rule (C-MOD-044, `05-delivery-and-safety.md:117`):
"`0x00bd0002` … byte `8·file-id + 5` of one row (dir_slot `0 ↔ 6`)". yknr's proven row 74 gives
`8·74+5 = 597 = 0x255`; sftfcs row 55 gives `8·55+5 = 445 = 0x1BD`; tbox row 54 gives `0x1B5`.

Write-limit: the proven `/setting` delivery is a senser `writeFile` bounded by ~53 508 B (the yknr
module size; `grain-angles-overview.md` "unlimited within the ~53 KB senser writeFile limit"). sftfcs
43 652 B is comfortably under; **tbox 77 444 B is over → cannot be replaced via the proven path**, which
removes Miniature from contention regardless of its internals. (`sa_kknr` 64 260, `sa_star` 473 732 are
also over, and are NR/role-unknown, not user-selected effects — not "effect = grain" triggers anyway.)

### Which run a per-pixel full-frame pass (not 3A / overlay)
From C-MOD-012 / C-MOD-030 / the §4.2 fingerprints (04-dsp-modules.md:829, C-MOD-051): `sftfcs` image 2
(text `0x6cc0`) reads **7 854 tiles (= 77×102) + 9 map windows from buffer A and writes the same tiles
to buffer B** — a full-frame per-pixel apply, and **"validates the method on a module whose pixel output
is visible in JPEGs"** (C-MOD-051). `tbox` processes the frame in blocks (149 / 256 `run_engine` calls
at two synthetic sizes, C-MOD-024). Both are genuine per-pixel full-frame passes — the inventory the
hypothesis wanted. The disqualifier is not "does it process pixels" but "can we modify the processing".

---

## TASK 2 — Compare to `sa_yknr` on the three things that blocked grain

### (a) Code space — NOT better than yknr's 16 B/core

**Baseline (yknr, `grain-codecave.md` F1/F4/F6):** 16 B/core clean dead shutdown stub (`0xac58..0xac67`),
proven reachable to the JPEG by Probe S. Largest file zero runs — 99 B @ `0x9d` (header descriptor
space) and 56 B @ `0xd0c8` (module tail past loaded text) — are **non-addressable**. Real floor for a
periodicity-free per-pixel loop = **38 B / 19 instr** (46 with clamp), a hard SA-DSP ISA fact
(`grain-angles-overview.md`, external-expert + ISA verification) → yknr is ~2.4× short.

**sftfcs, disassembled this session** (`sadis.py`, text-relative; core bootstrap loads at DSP `0x3800`):
- Bootstrap is `503f/503e/5031/00b1 1b04 5031 00a1 0000` + 3 literals at `0x10/14/18` — it **falls
  straight through** `b 0x1c0` into main; there is **no 16 B dead shutdown stub appended to the
  bootstrap** the way yknr has one.
- Real teardown at file `0x234`: `ldr r1=0x48030; str r7; ldr r1=0x48258; str r7; wfi; nop; <literal
  pool: 0x240 .long 0x2000bffc, 0x248 .long 0x00048174>`. Dead space after the `wfi` = the single `nop`
  (2 B) before the pool. The other `wfi`s (file `0x141c`, `0x148c`) are **live engine-sync waits** —
  code (`ldr r2=0x48200; mov r14,#0; …`) continues immediately after, no dead tail.
- Byte-scan dead runs ≥ 6 B (199 of them): top are **104 B @ `0xaa18`** and **62 B @ `0x87e2`** — both
  at/near the module tail (file is 43 652; `0xaa18 = 43 544`) → **past the loaded text, non-addressable,
  same category as yknr's `0xd0c8` tail**. The largest *body* runs are **34 B @ `0x480e`** and
  **32 B @ `0x40`**, which fall in literal-pool / mis-decoded-config-table regions, not a clean
  executable cave, and are **still < the 38 B floor**.

**Conclusion:** sftfcs has, if anything, **less** usable dead scalar cave than yknr (denser live code,
engine-sync `wfi`s, teardown→pool). "More total code" did **not** translate into "more dead,
branch-reachable, scalar-executable space at a pixel point." Same 16-B-class wall; no ≥38 B cave.

### (b) Output reach — a *tie-to-cleaner* story, but the modifiable point is VLIW

- **Reaches the JPEG: yes, and provably** — C-MOD-051 (sftfcs image-2 output visible in JPEGs) and a
  cleaner full-frame luma than yknr (whose luma/chroma role "is not settled", table at 04-dsp:644).
  So on "does the output reach the final JPEG" sftfcs is slightly *better documented* than yknr.
- **But the per-pixel point where we could land `Y += noise` is VLIW.** The Soft Focus apply is a
  convolution + blend executed through `run_engine` on the module's VLIW clusters (C-MOD-022: 3×3 once
  at kernels `0x12800/0x12840`, 5×5 twice at `0x12880/0x128c0`; C-MOD-023: three blend weights in
  64ths). sftfcs *is* the VLIW blur oracle (C-DSP-015, `dsp-grain-scope.md` Angle 1). That is the **same
  engine** whose per-pixel output register is a DMA-OUT of an undecoded op5/AGU stream and which
  **E-0077 proved unreachable** (`op7 r19→r19` at the yknr finalize bundle produced no JPEG change). A
  scalar hook could in principle add noise to buffer B *after* the engine (the Probe-S pattern) — but
  that is gated on the 38 B scalar cave of (a), which sftfcs does not have.

### (c) Noise source — same wall

No per-pixel-varying value better than yknr's. sftfcs's only per-pixel state is a tile pointer (yknr's
r13 again), and its tables are **smooth, low-entropy by construction** — every 3×3/5×5 kernel sums to
256 (unity gain, C-MOD-021), analogous to yknr's smooth reciprocal LUT (H=3.31, no texture). No
counter, no LFSR, no high-entropy table to DMA as baked noise. The VLIW self-dither route is also dead
for the same reason as yknr (13-bit slot has no immediate field; only free const r31=0).

### Scorecard

| Blocker | sa_yknr (baseline) | sa_sftfcs (Soft Focus) | Better? |
|---|---|---|---|
| Dead scalar cave | 16 B/core (proven) | ≤ ~2 B teardown tails; body runs ≤ 34 B in data; big runs non-addressable tail | **No** (same/worse) |
| ≥38 B branch-reachable exec cave | none | none | **No** |
| Output reaches JPEG | yes (Probe S) | yes (C-MOD-051), cleaner luma | marginal yes |
| Modifiable per-pixel point | VLIW (E-0077 null) | **VLIW** (convolution/blend) | **No** (same wall) |
| Noise source (per-pixel / table) | none (r13 ping-pong, smooth LUT) | none (tile ptr, unity-sum kernels) | **No** |
| Trigger / normal-shoot isolation | runs on EVERY frame | **only when Soft Focus selected** | **Yes** ← the one real win |

---

## TASK 3 — Best host + concrete plan (conditional)

**Pick: `sa_sftfcs` (Soft Focus)** — the only user-selected Picture Effect whose module is
redirectable and size-legal, with a proven-visible full-frame output. Use it *only if* the
scalar-space wall is broken independently; otherwise it is blocked exactly like yknr.

**Redirect (proven mechanism, C-MOD-044 — identical to the yknr route, different row):**
1. `bk r 0x00bd0002` (read the whole ODL dir-slot block), save it.
2. Set the dir_slot nibble of **byte `0x1BD`** (`8·55+5`, the sftfcs row) from `0` to `6`
   (p8 `/usr/sabin` → `/setting/`).
3. `writeFile('/setting/sa_sftfcs.bin', <modified copy>)` (43 652 B, under the limit).
4. `bk s`, zero the WBI first sector, cold boot.
- **Reverse:** write byte `0x1BD` back to `0x00` from the updater; the stock `/usr/sabin` copy is
  untouched (C-SAFE-016). Revert target = stock md5 `c64ce801…`.

**Trigger (the owner's "1 effect = grain"):** user sets **Picture Effect → Soft Focus**. Only then does
the hijacked module load; every other mode and effect leaves sftfcs unloaded, so **normal shooting and
all other effects are untouched** — the cleanest realization of the goal, and strictly better than
yknr (which runs on every frame).

**Where it fails — the injection itself (same as yknr):** to put grain into the output you need one of
- a **scalar RMW loop** in a dead cave → **blocked**: no ≥38 B branch-reachable cave (Task 2a) and no
  noise source (Task 2c); or
- a **VLIW `op7` add** in a free bundle lane of sftfcs's blur program (`dsp-grain-scope.md`: prog0 file
  `0x2420`, inner loop `0x2710–0x2758`) → **injection is code-space-free**, but blocked on the grain
  **source** (no immediate, no noise stream without scalar DMA setup) and on the still-unproven
  "does that program's output reg reach the JPEG" (E-0077 was null on yknr's equivalent).

**Needs a camera probe** (all reversible `/setting`, high-ISO, revert = stock `c64ce801`):
- P-sftfcs-1: redirect sftfcs to a **byte-identical** copy, select Soft Focus, confirm it still loads
  and applies (generalizes yknr Q-37 to row 55). Gates everything.
- P-sftfcs-2 (only if a ≥38 B cave or free-RAM loader ever appears): a Probe-S analog — does a scalar
  write to buffer B inside the per-tile apply reach the JPEG? Expected yes by C-MOD-051, but moot until
  the cave exists.
- P-sftfcs-3 (VLIW): `op7 r19→r19` in a free lane of prog0's `0x2710–0x2758` loop — does it reach the
  JPEG? Same ladder and same null-risk as the yknr `0xce88` probe.

**Reversibility:** full. Single Backup byte + one `/setting` file; stock partition never written.

---

## TASK 4 — Honest verdict

**The hypothesis's premise is false in the way that matters.** "Complex effects do heavy per-pixel
full-frame processing, therefore more code + working memory + a host for grain" conflates *total code*
with *dead, branch-reachable, scalar-executable space at a pixel point*, and ignores that the heavy
per-pixel work is **VLIW** — the exact engine the project cannot author (ISA undecoded, output reg a
DMA-OUT, E-0077 null, no emulator). A complex effect is **more** VLIW-bound than yknr, not less.

Concretely:
- **Room:** sftfcs gives *no more* usable dead scalar code than yknr — arguably less (≤2 B teardown
  tails vs yknr's 16 B stub; its big zero runs are non-addressable module tail). Still < the 38 B floor.
- **Output reach:** proven (C-MOD-051) and cleaner luma than yknr — a real but minor plus; yknr's reach
  was already proven, so this does not unblock anything.
- **Noise source:** none — smooth unity-sum kernels, tile pointer only, same as yknr.

So on the three blockers it is the **same walls**. The only thing a complex-effect host genuinely buys
is **packaging**: "select Soft Focus → grain, normal capture untouched, output provably visible." That
makes **`sa_sftfcs` the preferred host *conditional on* an independent scalar-space unlock** (a V1–V5
16-byte-space trick, or reversing the external core-copier to load a routine into free RAM `0x5000–
0x8000`) — options that live OUTSIDE any effect module. It is not a new route through the wall.

**A8 resolved:** from "❓ unexplored" → **"✗ evaluated — effect modules hit the same 16-B-class /
VLIW-output / no-source walls as sa_yknr; `sa_sftfcs` is the better *host* for the routine and the
*trigger*, but only once the scalar-space problem is solved elsewhere."** Recommendation unchanged:
ship colour (reachable, reversible) + the proven Probe-S pixel-write demo; full additive grain remains
the documented hard frontier, with the DMA-LUT-piggyback (A7) and the 16-byte-space tricks (V1–V5) as
the only live hopes — now also knowing that when one lands, Soft Focus is where to host it.

---

## Reproduce
```
cd ~/nex3n-dump/sonygen/isa
PY=~/nex3n-dump/.venv/bin/python
SFT=~/nex3n-dump/sonygen/sa/3N_p8/sa_sftfcs.bin      # md5 c64ce801, == safeboot copy
$PY -I sadis.py "$SFT"                                # scalar disasm (bootstrap @0, teardown @0x234)
# dead-run scan: zero/0xff runs >=6 B  -> top body run 34 B @0x480e, tail 104 B @0xaa18 (non-addr)
# redirect byte: 8*file_id+5  -> sftfcs(55)=0x1BD, tbox(54)=0x1B5, yknr(74)=0x255  (C-MOD-044)
```
Sizes/ids: `04-dsp-modules.md` C-MOD-007 (file-ids), :637/:642/:644 (module table); output-reach
C-MOD-051; effect→module map C-MOD-030; redirect C-MOD-044 / `05-delivery-and-safety.md:117`;
38 B floor + VLIW-null `grain-angles-overview.md`; VLIW source wall `dsp-grain-scope.md`.
