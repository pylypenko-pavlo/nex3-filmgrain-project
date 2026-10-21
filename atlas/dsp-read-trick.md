# DSP SRAM read trick — observing the `0x91f0` descriptor ring (2026-10-13)

How to OBSERVE the 6 DMA-descriptor-ring entries at DSP-internal SRAM `0x91f0` (16 B/entry =
`{addr, 0x40000000}`) so we can pick a FREE index for additive noise-stream injection. The ring
addresses are built at runtime (copier at `0xd80` marshals from a runtime stack buffer, not a file
constant — `engine-command-table.md` "STRUCTURE CLOSED"), so a static read is impossible and a **live
dump is required**. Design-only, offline, no binary edits.

**TL;DR verdict:** senser (ARM-side) almost certainly **cannot** reach `0x91f0` — it is on-chip DSP SRAM,
not ARM-mapped, and the `0x90000000` "mirror" is a mirror of *DRAM*, not of the DSP SRAM. The reliable
channel is the **already-proven Probe-S path**: a ≤16 B scalar stub reads a ring word and `str`s it into
the engine output tile; it rides the existing DMA-out into the SOOC JPEG; we recover the exact bytes
off-camera by taking the **median of each byte-position across the ~15 912 tiles** (redundancy beats JPEG
quantization). The catch is the **same 16 B code ceiling that blocks the grain loop**: one stub carries
~1 ring word reliably, so a full 6-entry readout is a **small handful of reversible `/setting` flashes**,
one word each. No single clean one-shot channel exists without the unbounded (but currently
low-confidence) run_engine/VLIW data-edit route.

---

## 0. Do this FIRST — the single cheapest confirm (no flash, no risk)

Before committing to any stub, spend one **no-flash senser session** (reads don't reboot, C-DLV-003;
fully reversible) to try to disprove the "senser can't read DSP SRAM" assumption. One `readMemory` sweep,
looking for the ring's unmistakable signature — the GO word **`0x40000000` repeating at a 16-byte
stride** — in the only candidate ARM-physical windows:

1. `readMemory(0x000091f0, 0x200)` — the literal low address (tests a flat/identity DSP↔ARM view).
2. `readMemory(0x900091f0, 0x200)` and `readMemory(0x800091f0, 0x200)` — the DRAM-mirror offsets
   (tests the hopeful "mirror" idea; see §2 for why this is expected to FAIL — it is DRAM, not SRAM).
3. Any documented SA candidate window (Q-29/Q-30, C-SYS-006/007) if one is on hand.

**Decode of the sweep:** if any window shows `40 00 00 40 00 00 00 ...` i.e. a word `== 0x40000000` every
0x10 bytes (and nonzero/zero `addr` words between), senser reaches the ring → the whole stub exercise is
unnecessary, read it directly. **Expected result: not found** (C-DSP-020 says the DSP-local view
`0x12800/0x13700/0x40000+/0x48000+` is not in ARM physical memory; `0x91f0`/`0x9000` are the same class of
on-chip SRAM). This test costs one USB session and settles it cheaply instead of assuming.

> Even cheaper tell if a Probe-S-class capture is in flight: Probe S writes `0xFFFFFFFF` into the output
> tile at `0x9000`-region each tile; if senser could see DSP SRAM, a read of that window mid-capture would
> show the white markers. But that is a transient timing race — the ring-signature sweep above is the
> clean, decisive, non-timing test. Run that one.

---

## 1. The proven primitive we reuse (no new mechanism to prove)

Probe S (PIXEL-WRITE ROUTE PROVEN, `dsp-grain-scope.md`): a 16 B scalar stub in the per-core dead tail
(`chunk+0x08`), reached by a `b` trampoline from the per-tile epilogue hook `chunk+0x2fa` (which catches
`r13` = engine tile window = end-of-tile ptr; **tile top-left = r13 − 0x800**, tile = 0x800 B = 128×8
YUYV). It wrote `0xFFFFFFFF` to each tile's top-left and **a clean grid of white dots appeared in the SOOC
JPEG** (vertical columns every 128 px, dots every 8 rows). So this is a confirmed, controllable
`scalar store → tile RAM → in-place DMA-out → YKNR → JPEG` channel.

Two facts make it an exfil channel, not just a grain channel:
- The SA-DSP **scalar core writes `0x91f0` itself** (it marshals the ring) ⇒ `0x91f0` is scalar-addressable
  ⇒ a scalar stub can **READ** it with a plain `ldr`.
- The scalar store into the output tile reaches the JPEG (Probe S) ⇒ a scalar stub can **WRITE** observed
  bytes where we can read them.

Everything below is just "what to read, how to encode it into the tile, and how to decode it back."

---

## 2. Why the ARM side can't shortcut this (kills two hopeful angles)

- **DSP on-chip SRAM is off the ARM bus.** C-DSP-020: the DSP-local view is not mapped in ARM physical
  memory. `0x91f0` (ring) and `0x9000` (output tile) are tiny on-chip SRAM addresses, the same class as the
  listed-unmapped `0x12800/0x13700/0x40000+/0x48000+`. senser `readMemory` (PFUNC MemoryDump `0xff03`,
  C-DLV-001) reads **ARM physical** addresses; ARM-phys `0x000091f0` is low boot/unmapped space, not the
  DSP's on-chip `0x91f0`.
- **The `0x90000000` "mirror" is a DRAM mirror, not an SRAM mirror.** E-0046: the 256 MB of physical DRAM
  is mirrored at `0x80xxxxxx`/`0x90xxxxxx` (and av-cam sees the uncached alias as `0xD0000000+`). That
  mirror reflects the **DRAM pools** (`0x84000000+`), where the DMA engine moves *pixel tiles* — it does
  **not** reflect the DSP's on-chip SRAM where the *ring* lives. So reading `0x900091f0` just reads low
  DRAM, not the ring. This corrects the "maybe the mirror exposes it" hope in the brief: it does not.
- **Writing the ring into the ARM-readable encode canvas, then senser-reading it raw, is strictly worse
  than the JPEG.** The scalar stub *could* write ring words as pixels into the output tile, which DMAs out
  to the YC canvas in DRAM that ARM reads for JPEG encode (handle `OBJ+0x39e0`, `DRAM_A+off`). In principle
  senser could then read those bytes raw (no JPEG loss). But E-0069 already walked this exact wall:
  resolving the canvas base live is the unsolved Q-40 pointer-leak problem, the canvas is transient, and
  **service-mode entry re-zeros av-cam `.bss`** (C-DLV-004) — which is precisely why that effort
  **pivoted to "read it from the SOOC JPEG instead, no senser, so the `.bss` problem does not apply."** We
  inherit that conclusion: **the JPEG is the robust channel; the senser-canvas route is a demoted fallback.**

---

## 3. Ranked exfil designs

| # | design | channel | code cost | reliability | verdict |
|---|--------|---------|-----------|-------------|---------|
| **D1** | **word-splat + cross-tile median** | JPEG | 16 B/flash (~1 word) | **high** (median over ~15 912 tiles) | **WINNER** — proven path, staged over a few flashes |
| D2 | occupancy micro-readout (GO high-byte only) | JPEG | 16 B/flash (~2 entries) | high (0x40 vs 0x00 trivially separable) | best if we only need the free-index map |
| D3 | senser read of `0x91f0` directly | ARM | 0 | ~0 (SRAM not ARM-mapped) | do the §0 confirm, then discard |
| D4 | write ring into encode canvas, senser-read raw | ARM/DRAM | 16 B + base-resolve | low (transient + `.bss` clear, E-0069) | fallback only |
| D5 | run_engine / VLIW data-edit copies ring → tile | JPEG | unbounded (file edit) | low (E-0077 broke our VLIW luma model; ring may be outside VLIW data space) | only if a one-shot full dump is mandatory |
| D6 | EXIF / status register / timing side-channel | — | — | none (no DSP→EXIF path; EXIF is ARM-authored) | dead |

### D1 — word-splat + cross-tile median (WINNER)

**Idea.** Each per-tile invocation reads ONE chosen ring word and `str`s it at a fixed in-tile position.
Because the stub runs once per output tile and every tile is DMA'd to its frame slot, the SAME 4-byte
splat lands at every tile position in the frame (Probe-S grid geometry). Off-camera, we take the **median
of each of the 4 byte-positions across all ~15 912 copies** → the JPEG DCT/quantization error (which
varies per tile because each splat sits in different surrounding image content) averages out, and we
recover the exact stored bytes. Redundancy, not per-bit contrast, is what makes raw byte values survive
JPEG — this is the key move that lets a tiny stub carry real data.

**Concrete 16 B stub** (reads entry 0's `addr` word; all encodings verified against `saasm.py`):

```
; stub in the per-core dead tail chunk+0x08, entered by `b` from hook chunk+0x2fa.
; r13 = tile window (live at the hook). Builds src=0x91f0, splats [src] at the tile.
  mov  r2,#0x91     ; 9912   r2 = 0x91
  lsl  r2,#8        ; f082   r2 = 0x9100
  add  r2,#0xf0     ; af02   r2 = 0x91f0   (entry0.addr)
  ldr  r3,[r2]      ; 0a23   r3 = [0x91f0] = entry0.addr word
  str  r3,[r13]     ; 153d   write 4 bytes at tile window (Probe-S store class 0x15)
  ret               ; 0003
```
6 instr = 12 B, leaving 4 B (2 instr) for the frame convention — replay the displaced hook instruction
(`add sp,#0x50`) and `b` back to `chunk+0x2fc` exactly as Probe S does, instead of `ret`, if the tail is
entered inline rather than called. (If you prefer the proven top-left target `r13−0x800` for cleaner
registration, that costs 3 more instr — `mov r0,#1; lsl r0,#11; sub r1,r0` with `mov r1,r13` — which
overflows 16 B; so for the top-left target, split to 2 flashes or use the tighter 2-word form in D2.)

**Re-targeting per flash (one-line rebuild, no new RE):** entry *i*'s `addr` is at `0x91f0 + 16i`, its
`GO` at `+4`:

| entry | addr @ | GO @ | base build |
|------:|:------:|:----:|------------|
| 0 | `0x91f0` | `0x91f4` | `mov r2,#0x91; lsl r2,#8; add r2,#0xf0` |
| 1 | `0x9200` | `0x9204` | `mov r2,#0x92; lsl r2,#8`  *(add #0 elided)* |
| 2 | `0x9210` | `0x9214` | `… add r2,#0x10` |
| 3 | `0x9220` | `0x9224` | `… add r2,#0x20` |
| 4 | `0x9230` | `0x9234` | `… add r2,#0x30` |
| 5 | `0x9240` | `0x9244` | `… add r2,#0x40` |

So: change 1–2 immediate bytes, rebuild (`build.py` pattern — re-emit routine, patch all 5 cores
identically, **recompute the sum32 trailer** C-DSP-001), redeliver via the proven `/setting` redirect,
shoot one high-ISO frame, revert. Each flash yields one ring word, byte-exact, from one JPEG.

**Flash budget:** to pick a free index we need the 6 GO words (occupancy) = up to 6 flashes, or 3 with the
2-word-per-stub form (D2). To also read the 6 `addr` words (to confirm `0x9000` is the final surface vs a
scatter-list, and to choose a safe noise-staging address), up to 6 more. A few reversible shots total.

**Why not fewer flashes in one stub?** The 16 B ceiling. A general copy loop needs ~7 instr of setup
(build `0x91f0` = 3; build `r13−0x800` dst = 4) before any body — it does not fit (§4). And the index
**cannot** be derived from the tile to splat "entry *i* on tile *i*": the output tile RAM is
**double-buffered** (`0x9000`/`0x9800`), so r13 ping-pongs between two values and carries **no global tile
counter**, and there is no persistent writable scalar word to keep one (same reason `grain_bands` was
deferred). So multi-flash (or a roomier routine we don't have) it is.

### D2 — occupancy micro-readout (if we only need the free-index map)

We do not need full 32-bit addresses to pick a free slot — we need 6 occupancy bits. An entry is occupied
iff its GO word `== 0x40000000`, i.e. iff the **single byte at `0x91f0 + 16i + 7` is `0x40`** (free ⇒
`0x00`). That byte is trivially separable under JPEG + median. A 2-entry-per-flash stub (verified-class
ops; uses the imm-offset `ldrb`/`strb` forms the ISA supports):

```
  mov  r2,#0x91 ; lsl r2,#8 ; add r2,#0xf7   ; r2 = 0x91f7 (entry0 GO high byte)
  mov  r1,r13                                 ; dst = tile window
  ldrb r3,[r2]      ; entry0 occupancy byte
  strb r3,[r1]      ; tile[0]
  ldrb r3,[r2,#16]  ; entry1 occupancy byte (+0x10)
  strb r3,[r1,#2]   ; tile[2]  (even byte = luma)
  <return convention>
```
~8 instr; 3 flashes cover all 6 entries. Decode: median the luma at tile offsets 0 and 2 across all tiles
→ `≈0x40` = occupied, `≈0x00` = free. **If all 6 read occupied** (the expected case per
`engine-command-table.md`: "Ring batch = exactly 6 descriptors/pass"), the plan is the documented
2-edit extend (`cmp #6 → #7` + extend the marshal source) and the "free index" is the new index 6 — the
measurement then just **confirms** that and, via D1 on the `addr` words, picks the staging address.

### D3 — direct senser read

Covered in §0/§2: do the one no-flash confirm sweep, expect negative, discard. Zero cost, removes the
assumption.

### D4 — write ring into the encode canvas, senser-read raw

Avoids JPEG lossiness but needs the canvas base resolved live and read within the capture window, against
the `.bss`-clear-on-service-entry problem that already killed this for grain (E-0069). Keep only as a
fallback if, for some reason, byte-exact addresses prove unrecoverable even with cross-tile median (they
should be recoverable).

### D5 — run_engine / VLIW data-edit (the "unbounded code" route)

The command table (Region A register-file image + Region B inline VLIW, `engine-command-table.md`) is
editable **data** with no 16 B ceiling, so in principle a VLIW syllable could copy ring words into the
output tile in one pass → a one-shot full 6-entry dump. Two reasons it is **not** the first choice:
(1) the VLIW addresses engine regs (`0x40000+`) and tile RAM; whether it can even read scalar SRAM
`0x91f0` is unproven; (2) **E-0077** showed our VLIW luma model is wrong (`op7 r19→r19` at `0xce88`
produced no JPEG change), so we cannot currently place a trustworthy write. Revisit only if a single-flash
full dump becomes mandatory and the VLIW output path gets re-pinned.

### D6 — EXIF / status / timing

No path: EXIF is authored by ARM (av-cam), which cannot see the DSP ring; the status words `0x94dc/0x94e0`
are DMA poll flags, not ring contents; a timing side-channel can't carry 24 bytes of addresses. Dead.

---

## 4. Code-space analysis — the exfil hits the SAME wall as the grain

- **Only 16 B/core is dead** (`chunk+0x08` tail; Probe S proved it reaches the JPEG).
- **`chunk+0x13c` is LIVE** — E-0075/E-0076 hard-hung the camera (even the loop-free fixed-marker write at
  that footprint hung) ⇒ those bytes are a live engine table.
- **Module-grow is blocked** — no in-module loader; the 5 core blobs are pre-relocated and file-contiguous
  up to the VLIW programs; the tails are **not chainable at runtime** (core3@`0x8000` − core2@`0x4808` =
  `0x3800` > the `b` ±0x2000 range), so a core's hook cannot reach a roomier neighbour.
- **Budget inside 16 B (8×2 B instr):** forming the ring pointer `0x91f0` = 3 instr; forming the proven
  top-left dst `r13−0x800` = 4 instr ⇒ 7 instr of setup before any `ldr`/`str` ⇒ a copy loop does **not
  fit**. Dropping the dst to `[r13]` (end-of-tile, slightly less clean but still in the DMA'd tile) frees 3
  instr, leaving room for exactly **one `ldr`+`str`** word plus the return convention. Hence **~1 ring
  word per flash**; 2 with the byte-wise D2 form.

**Honest consequence:** there is **no clean single-shot channel** for all 6×`{addr,GO}` within the proven
means. The cheap, low-risk, reversible answer is a **staged multi-flash** D1/D2 readout decoded via
cross-tile median. A true one-shot dump would require D5 (unbounded code), which is presently
low-confidence. This is the same code-space ceiling that gates the grain itself — observing the ring is
not easier than feeding it, and we should budget it as "a few more reversible `/setting` shots," not "one
measurement."

---

## 5. Decode procedure (off-camera, from the SOOC JPEG)

1. **Locate the tile grid.** Probe-S geometry: splats recur at `(x mod 128, y mod 8)` across the frame
   (128×8 YUYV tiles). Find the offset by correlating against a high-contrast calibration splat (write a
   known `0xFF`/`0x00` anchor in the spare stub bytes on the first flash).
2. **Harvest.** For each tile cell, sample the splat's luma byte(s) at the known in-tile offset; collect
   the full set across all ~15 912 tiles.
3. **Median per byte-position** → the stored value, robust to JPEG quantization (error decorrelates across
   tiles because each splat's DCT context differs).
4. **Calibrate levels** with the GO word's known bytes (`0x40`,`0x00`) and the `0xFF`/`0x00` anchor — a
   2–3 point map correcting any JPEG gamma/level shift, so `addr` bytes land on true 8-bit values.
5. **Read out:** occupancy = GO-high ≈ `0x40` (busy) / `0x00` (free) per entry → the free-index map; and
   the recovered `addr` words → confirm `0x9000` is the final surface and choose a noise-staging address
   **outside** `0x9000-0x9fff`/`0x94xx` (clobbering those breaks the output/status, per
   `engine-command-table.md`).

Optional, same channel, extra flashes: the P2/P3/P4 buffer pointers in stack slots `[sp,#32..56]` (DSP
stack = on-chip SRAM, same read class) — splat `[sp+32]…[sp+56]` the same way to resolve `slot_base +
window_base`.

---

## 6. One-paragraph honest standing

senser cannot read the ring (confirm it with the §0 no-flash sweep, but expect negative — it is on-chip
SRAM and the `0x90000000` mirror is DRAM). The robust, proven channel is Probe-S's `scalar → tile → JPEG`
path with **cross-tile median** decoding, which recovers byte-exact ring words — but the **16 B code
ceiling limits one stub to ~1 word**, so the full occupancy + address readout is a **small series of
reversible `/setting` flashes** (≈3 for occupancy via D2, up to ~12 for every `addr`+`GO`), each a
one-constant rebuild decoded from a single high-ISO JPEG. There is no clean one-shot read without the
unbounded run_engine/VLIW route, which is currently low-confidence (E-0077). Recommended path: §0 confirm
→ D2 occupancy (3 flashes) → if a free slot exists, D1 on that slot's neighbours to pick the staging
address; if all 6 busy (expected), proceed to the documented `#6→#7` extend and use D1 only to fix the
staging address and confirm `0x9000`.
```
