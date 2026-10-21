# scalar16 grain — what fits in ≤16 bytes of SA-DSP scalar code

Design study, 2026-10-13. Question posed after MODULE-GROW was blocked (see
`dsp-grain-scope.md` → "⛔⛔ MODULE-GROW BLOCKED"): the only genuinely-dead
executable space is the **16-byte stub tail per core**. *What is the cleverest
thing that reads as film grain in ≤16 bytes — or an honest verdict that nothing
does?* This is a paper design (OFFLINE, files on disk, nothing flashed), grounded
on disassembly of the real stock `sa_yknr.bin` and the proven Probe S stub.

## TL;DR — VERDICT: NO 16-byte scalar scheme gives real film grain

Two **independent** walls, each sufficient on its own, and the second is new here:

1. **Code-space wall (physical, newly pinned).** The tightest conceivable
   full-tile in-place luma loop — using every compact idiom in the ISA — is
   **exactly 9 instructions = 18 bytes**, *with the noise operation reduced to a
   single op*. The 9th instruction physically lands on file offset `0xac68`, the
   **live `0x00004000` stack-pointer literal** the core bootstrap reads at
   `0xac50/0xac52`. You are **one instruction (2 bytes) short**, and that last slot
   is not free space — it is a load-bearing constant. A loop cannot be placed.
2. **Entropy wall (unchanged, confirmed).** Even if it fit, a *single*-op mangle is
   not grain: self-folding a pixel's own bits is deterministic → flat midtones
   (exactly where grain must live) stay perfectly flat; XOR-ing with the address is
   a fixed spatial pattern, **identical in every 128×8 tile** → a static periodic
   dither, not aperiodic emulsion grain. Real grain needs an evolving PRNG
   (~72 B, proven elsewhere) — 4.5× over budget.

The best thing that *fits* 16 B and does *something* is **sparse per-tile
pseudo-random speckle** (≤3 writes/tile). It is honest to call it dust/speckle,
**not grain**: it covers ~0.3 % of the frame (math below) and tiles partition the
frame, so the picture never "fills in."

---

## 1. Budget, nailed down from the real stub

### 1a. Instruction width — confirmed
All SA-DSP **scalar** instructions are 16-bit (2 bytes). (The 8-byte units are
VLIW *engine* bundles — a different core, out of scope here.) So **16 bytes = 8
scalar instruction slots.** Confirmed against `sadis.py` OP8/OP12/OP16 tables and
the live stub.

### 1b. The dead slot is the per-core shutdown stub (decoded)
Stock core0 blob begins at file `0xac50`; the dead "stub tail" is at chunk+`0x08`
= `0xac58`. Decoded stock bootstrap:

```
0xac50: ldr sp,[pc]  ; =0x4000      <- init: stack top          (reads literal @0xac68)
0xac52: ldr r14,[pc] ; =0x4000      <- init                      (reads literal @0xac68)
0xac54: ldr r1,[pc]  ; =0x31d0      <- init: main entry          (reads literal @0xac6c)
0xac56: bl  r1                      <- call per-core main (contains the per-tile fn + hook)
0xac58: ldr r1,[pc]  ; =0x48208     ] ___ SHUTDOWN STUB = the 16 dead bytes ___
0xac5a: mov r2,#0                   ]     (runs once at core teardown after main returns:
0xac5c: str r2,[r1]                 ]      poke engine MMIO 0x48208=0, then halt)
0xac5e: nop                         ]
0xac60: wfi                         ]
0xac62: nop                         ]
0xac64: b   0xac5e                  ]     (spin in wfi forever)
0xac66: nop                         ]
0xac68: .long 0x00004000            <<< LIVE literal: sp / r14 init constant
0xac6c: .long 0x000031d0            <<< LIVE literal: main entry constant
0xac70: .long 0x00048208            <<< DEAD literal (only the shutdown stub read it) — REUSABLE
```

So the reusable region is **8 code slots (`0xac58..0xac67`) + exactly one 32-bit
data literal (`0xac70`)**. The two literals in between (`0xac68`, `0xac6c`) are
read by the core's init bootstrap and must be treated as **live** — reclaiming
them is an unproven camera gamble that, if wrong, corrupts the stack pointer and
kills the core. This is the physical origin of the "16-byte" ceiling.

### 1c. The proven Probe S stub (the reference), decoded
`sa_yknr_probeS.bin` diff vs stock → the working 16-byte stub at `0xac58` is
*exactly* 8 slots:

```
add sp,#0x50          ; (1) MANDATORY — re-exec the displaced epilogue instr (hook overwrote it)
mov r1,r13            ; (2) r1 = engine tile window = end-of-tile ptr
ldr r2,[pc] ; =0x800  ; (3) r2 = tile size (literal @0xac70 repurposed 0x48208 -> 0x800)
sub r1,r2            ; (4) r1 = tile top-left = r13 - 0x800
mov r2,#-1           ; (5) r2 = 0xFFFFFFFF (white)
str r2,[r1,#0]       ; (6) marker word 0
str r2,[r1,#4]       ; (7) marker word 1
b   0xaf4c           ; (8) MANDATORY — return into stock epilogue
```

Fixed cost = **2 slots** (displaced `add sp,#0x50` + return `b`). Base-pointer
setup = **3 slots** (and the `ldr [pc]` literal trick already compresses `0x800`
from 2 instrs to 1). **Payload = 3 slots.** Probe S spent them on a 2-pixel white
marker → the proven clean grid of dots in the SOOC JPEG.

### 1d. Compact idioms that exist (and still aren't enough)
From the ISA (`sadis.py`): post-increment loads/stores **do** exist
(`ldrb [s],#1`, `ldrh [s],#2`, `strb [d],#1`, `strh [d],#2`), r0-indexed
addressing exists (`ldrb d,[s,r0]`, `strb s,[d,r0]` — **r0 is a hard-wired index
operand**, costs no register field), `cmp.gts d,#0` is a 1-instr compare-to-zero,
and `ldr d,[pc,#off]` fetches any 32-bit constant in one instr. What does **not**
exist: any decrement-and-branch / hardware loop counter / compare-and-branch
fusion (branches are `bfs`/`bfc` on the single `fr` flag only), and any
add-to-memory / load-with-ALU. So loop control floors at *advance + test +
branch*, and memory work floors at *load + store* with a separate mangle.

---

## 2. Why coverage forces a full-tile loop (the sparse trap)

- Frame 4912×3264 ≈ **16.0 M pixels**; the engine tiles it as **15 912** blocks of
  128×8 = 1024 pixels (1024 luma bytes) each. The hook fires **once per tile**.
- The 5 DSP cores partition the frame; tiles are **disjoint** 128×8 regions. There
  is no persistent cross-tile state and each tile is visited exactly once, so a
  tile's coverage is whatever its single 16-byte call writes — it does **not**
  accumulate across calls.
- Film grain is a texture over ~**every** pixel (shaped by the midtone visibility
  window). To approach that, each call must touch ~all 1024 luma bytes ⇒ **a loop
  over the tile is mandatory.** A no-loop stub writes a fixed handful:
  - 3 payload slots → ≤3 `strb` (3 luma px) or ≤3 `str` (6 luma px, corrupts 6
    chroma). **3–6 px / 1024 = 0.3–0.6 % coverage, everywhere.** Reads as sparse
    speckle/dust, never as grain.

So the whole question collapses to: **does a full-tile in-place luma loop fit in 8
slots?**

---

## 3. The code-space proof: the tightest loop is 18 bytes, and slot 9 is live

Tightest possible full-tile loop, using the r0-indexed mode so the moving index
*is* the free index register (no separate base-pointer setup), the free literal
preloaded with `-0x800`, and the mangle shrunk to a single op. Verified
encodings, placed at the real stub `0xac58`:

```
0xac58: a50f  add sp,#0x50          ; (1) displaced epilogue  [MANDATORY]
0xac5a: 5050  ldr r0,[pc] ; =-0x800 ; (2) r0 = -tilesize = index of tile top-left (literal @0xac70)
loop:
0xac5c: 05d5  ldrb r5,[r13,r0]      ; (3) load luma at r13+r0 (r13=end; r0 steps -0x800..-2, always even=luma)
0xac5e: 2605  eor  r5,r0            ; (4) <-- the ENTIRE "noise": 1 op (index-keyed xor)
0xac60: 0e5d  strb r5,[r13,r0]      ; (5) store luma back
0xac62: a020  add  r0,#2            ; (6) advance index (skip chroma)
0xac64: 0090  cmp.gts r0,#0         ; (7) fr = (r0 > 0)
0xac66: dff9  bfc  loop             ; (8) loop while r0 <= 0
0xac68: b170  b    0xaf4c           ; (9) return  <-- LANDS ON LIVE LITERAL 0x00004000 (@0xac68)
```

- **9 instructions = 18 bytes.** Even after deleting the base-pointer setup (folded
  into `r13+r0`), compressing the constant to the free literal, and reducing the
  noise to one op, you need 9 slots.
- The 9th (the mandatory return `b 0xaf4c`) sits at `0xac68` = the **live
  `0x00004000` stack-pointer/r14 init constant**. Overwriting it makes `ldr sp,[pc]`
  / `ldr r14,[pc]` load garbage at core init → dead core. (Not even the clean
  "load-reject" failure — a hard wedge, consistent with the E-0075/76 hangs.)
- You cannot shave a slot: `add sp,#0x50` is required for stack correctness;
  `b 0xaf4c` is the only way back (the stub can't fall through into live literals);
  `ldrb`+`strb` are both required for in-place RMW; `add/cmp/bfc` is the minimum
  loop control in an ISA with no dbnz. **8 slots is a hard floor for the skeleton,
  leaving zero for the operation.**

And note line (4): even in the 18-byte version the "noise" is `eor r5,r0`, where r0
runs the **same** `-0x800..-2` sequence in every tile → a **fixed** diagonal XOR
texture repeated on every 128×8 block. That is a periodic screen, not grain (wall #2).

---

## 4. Ranked ideas

| # | Idea | Fits 16 B? | Reads as grain? | Why |
|---|------|:---:|:---:|-----|
| 1 | **Sparse r13-keyed speckle** (no loop; 3 payload slots write noise at tile-relative positions, value/position keyed to r13) | ✅ yes | ❌ no | 0.3–0.6 % coverage, disjoint tiles → sparse dust, not a texture. *Best thing that fits.* |
| 2 | **Full-tile index-walk RMW loop, 1-op mangle** (§3) | ❌ **18 B**; slot 9 hits live literal | ❌ no | 1-op mangle = periodic dither (wall #2) even if it fit. Shows we're exactly 2 bytes short. |
| 3 | **Self-dither** (`Y ^= Y>>k`, fold own bits) | ❌ needs loop (≥10 slots: mov+lsr+eor in body) | ❌ no | Deterministic per value → flat midtones stay flat = zero grain where it matters. |
| 4 | **Free noise stream XOR** (read a "random" memory region + read pixel + xor + store) | ❌ no (2 loads/iter, ≥11 slots) | ~ | Would be the best *character* but two load streams blow the loop budget wide open. This is really the VLIW DMA-grain-LUT idea, not a 16-B scalar one. |
| 5 | **Store-only pre-baked noise word** (loop `str`-ing a blue-noise literal, no read) | ❌ (still ≥8 skeleton) | ❌ no | Overwrites luma = destroys the image; and repeats one 4-byte pattern. |
| 6 | **Full xorshift32 grain** (`grain_single.s`, the real thing) | ❌ **72 B** | ✅ yes | The only thing that *is* grain — 4.5× over budget, no home in-module (confirmed in `dsp-grain-scope.md`). |

---

## 5. Best concrete sequence that FITS (idea #1) — honest label: speckle, not grain

If the owner wants to *see* the best-possible-16-B case on camera (as a
coverage/entropy demo, not as "grain"), this is it: three noise writes per tile at
a per-tile-varying position, so it is at least **aperiodic** across tiles (an
improvement over Probe S's fixed grid), while staying inside 8 slots + the one free
literal.

```
; free literal @0xac70 = 0x9E3779B9 (a scrambling odd constant; any varied word works)
0xac58: add sp,#0x50          ; (1) displaced epilogue              [MANDATORY]
0xac5a: mov  r1,r13           ; (2) r1 = end-of-tile ptr
0xac5c: ldr  r2,[pc];=const   ; (3) r2 = 0x9E3779B9  (literal @0xac70)
0xac5e: mul  r1,r2            ; (4) r1 = r13*const  -> per-tile pseudo-random word (r13 varies per tile)
0xac60: and  r1,r2            ; (5) fold into a small in-tile byte offset-ish index (mask via the const's low bits)
0xac62: str  r2,[r13,r1]      ; (6) write a 4-byte noise word at r13+r1 (r1 = r13-seeded offset, < tile)
0xac64: str  r2,[r13,#-4]     ; (7) one more at a fixed corner (cheap 2nd sample)
0xac66: b    0xaf4c           ; (8) return                          [MANDATORY]
```

Caveats, stated plainly:
- This writes **2 words (≈4 luma px + corrupts 4 chroma) per tile ⇒ ~0.4 %
  coverage.** It will look like **sparse, faintly-random colored dust**, not film
  grain. The chroma corruption (word stores hit U/V) tints the dots — to stay
  luma-only you'd drop to `strb` and ~0.2 % coverage.
- The `and r1,r2` masking to keep the offset inside the tile is approximate; a
  clean bound needs another slot we don't have, so in practice pick the const so
  its low bits already bound the offset (e.g. mask built into the literal), or
  accept an occasional write into the neighbor tile (1–2 px bleed).
- **It is not grain.** I would build it only if explicitly wanted as the
  "ceiling demo," and I'd name the output file to say *speckle*, never *grain*.

The 18-byte loop (§3) is **not buildable** in this slot at all — slot 9 destroys a
live constant. I did **not** write any `.bin`; this is design only, and I will not
overwrite any existing file.

---

## 6. Where real grain actually lives (pointers, not scope here)

The negative here is specific to **≤16 B of scalar code in the sa_yknr stub tail.**
It does **not** close the project. From `dsp-grain-scope.md`, the live frontiers:

- **VLIW route** — *no code-space wall at all*: drop `op3` (read a stream) + `op7`
  (accumulate) into existing free bundle slots (host slot confirmed at bundle
  `0x00cff0`; luma reg = r19). Blocked instead on the **grain-source data path**
  (a DMA grain-LUT ridden in as a 2nd per-pixel stream) and on decoding `op1`/`op2`
  for self-dither. This is the one with headroom.
- **Cross-module host** — another `sa_*` sub-image with a *large* dead executable
  region at a core-reachable DSP address could hold the 72-B xorshift loop, called
  from the yknr stub (branch-range permitting). Unsurveyed.
- **Accept the ceiling** — ship the proven colour path + the Probe S pixel-write
  demo; full additive scalar grain stays the hard open item.

**Bottom line:** 16 scalar bytes buys a *loop skeleton with no room for the
operation* (we're exactly 2 bytes / one live-literal short) and, separately, has
no entropy source. The clever maximum is aperiodic sparse speckle at sub-1 %
coverage. Real grain is a VLIW-stream or cross-module problem, not a 16-byte
scalar one.
