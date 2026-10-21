# Style ↔ grain coupling — "1 effect = 1 style + grain" (2026-10-13)

Can film-grain amplitude N be made to depend on the active Creative Style, given the
**proven** scalar pixel-write route into `sa_yknr` (trampoline at chunk+0x2fa, r13 = engine
tile window, writes per-tile luma, reaches the SOOC JPEG; N currently a baked constant)?

**Verdict (honest):** the 2-part design **LANDS on both sides in principle** and is reversible,
but it is **gated on ONE cheap on-camera probe** that static analysis cannot resolve — *does the
stock `sa_yknr` job parser copy the whole 0x1c CALC_START block verbatim into core RAM (so the
unused word reaches the hook for free → 2-edit design), or does it drop unused words (→ a third
edit in the statically-undecoded img0 parser is required)?* The av-cam side is fully pinned; the
module side has exactly one open bit, and the probe reuses the already-proven marker trampoline.

The parent's suggested "scrappier alternative" (#4 — read a style value already in engine RAM at
the hook, e.g. colour weights from Backup `0x0003010a`) is **a dead end for STYLE** and is ranked
last; reasons below (it rests on a conflation: `0x0003010a` is Soft-Focus kernels, not style).

Offline, static only. av-cam = `safeboot/out3n/nflasha3_unpacked_unpacked/av-cam.bin`
(6 554 072 B, md5 `d0003041f0a466db6b8ac5333e373458`, **VA = file + 0xc3441000**). Module =
stock `sa_yknr.bin` (53508 B, md5 `54acf2988273c0a1f98afc9940f34d60`). No file was modified.

---

## 0. The channel — why route A (param word) is the ONLY clean one

ARM (CPU1 av-cam) and the SA-DSP have **separate address spaces** (C-DSP-020, C-SYS-006): the DSP
scalar core cannot read ARM RAM, and ARM cannot read engine MMIO. So the active Creative Style —
which av-cam knows (it is an ARM-side global) — can reach the DSP trampoline **only through data
av-cam already sends the module**: the CALC_START parameter block. That is exactly the parent's
hypothesis (A) av-cam writes the style id into the block's unused word; (B) the module's scalar
side reads it and branches N. There is no second channel: reading engine RAM at the hook yields
no style signal (§5). So the whole question reduces to: *is there a free word in the block, is the
style reachable to fill it, and does that word arrive somewhere the trampoline can read?*

---

## 1. av-cam side — the 0x1c block, the free word, the style source (TASK 1) — PINNED

### 1.1 The builder and the flat 0x1c copy
`sa_func_YKNR_acquire` @ **VA 0xc37ebe60** (file 0x3aae60; strings at 0xc37ec290
"[IMAGING_CAP]:s: sa_func_YKNR_acquire error" confirm identity) builds a block on its stack and
sends it in two messages:
- **MSG1 (the 0x1c block):** `add r1,sp,#0x100; add r0,sp,#0x104; bl 0xc387809c` @0xc37ebf7e.
  Wrapper `0xc387809c` does `movs r2,#0x1c; mov r1,r4(=sp+0x104); mov r0,sp; bl 0xc3755340` —
  **`0xc3755340` is a flat serializer of 0x1c (28) bytes from `[r1]`.** So the on-wire block =
  **caller `sp+0x104 .. sp+0x120`, 7 words.** (This is the `movs r2,#0x1c` the prior scope note
  attributed to the builder; the 28-byte copy is here, in `0xc3755340`.)
- **MSG2 (`sa_func_YKNR_start`, VA 0xc3878244):** called next on success (`0xc37ebfd6`) with
  `r0 = ldrb[sp+0x104]` (w0's **low byte**), `r1 = ldrh[sp+0x100]`, `r2 = sp+0x108`, `r3 = sp+0xf0`.

Control-flow note (corrects a reading trap): the geometry field-fill at 0xc37ebf00..0xc37ebf60 is
on the **success** leg of `bl 0xc3606ba0` (`beq`, retval 0 = OK → `0xc37ebed8` → fields →
`0xc37ebf62` pack). The alternate leg logs an error. The field-fill is the normal path.

### 1.2 Field map of the 0x1c block (every store verified; base = caller `sp+0x104`)

| word | block off | av-cam stack | producer (instr) | meaning |
|---|---|---|---|---|
| **w0** | **+0x00** | sp+0x104 | **— no store anywhere in the function —** | **FREE / reserved word** (see 1.3) |
| w1 | +0x04 | sp+0x108 | `strh` @0xc37ebf08, `[obj0+0x39e2]` (u16; upper half left as stack garbage) | a u16 param |
| w2 | +0x08 | sp+0x10c | `str` @0xc37ebf44, `(stride<<3)` or `0` (4-predicate gate on [obj0+0x1c0]==9 etc.) | derived stride/size |
| w3 | +0x0c | sp+0x110 | `strh` @0xc37ebf4a, `[sp+0x80]` (u16; upper half garbage) | a u16 handle/param |
| w4 | +0x10 | sp+0x114 | `str` @0xc37ebf4e, `[sp+0x78]` (a handle from `0xc3606b1a/76`) | buffer/handle |
| w5 | +0x14 | sp+0x118 | `str` @0xc37ebf58, `[obj0+0x3e60]` | **width** |
| w6 | +0x18 | sp+0x11c | `str` @0xc37ebf5c, `[obj0+0x3e64]` | **height** |
| (—) | +0x1c | sp+0x120 | `str` @0xc37ebf60, `[obj0+0x3e50]` = **stride** | **OUTSIDE** the 0x1c copy — not sent in MSG1 |

`obj0` = `[r5]` (r5 = the acquire arg; obj0 reloaded into r4/r6/r7, callee-saved r4 survives the
`bl 0xc37ebde4` just before the pack). Note the geometry object here carries huge offsets
(+0x3e50/60/64) — it is the **capture-frame descriptor**, not the colour module's object (§1.4).

### 1.3 The unused word = **w0 (block offset +0x00)**
w0 is the only word with **no producer** anywhere in `sa_func_YKNR_acquire` (verified: full
`str/strh/strb/stm` scan of 0xc37ebe60..0xc37ec010 shows writes only at sp+0x108/10c/110/114/118/
11c/120 — never sp+0x100 or sp+0x104). w1/w3 are u16s whose **upper 16 bits** are also stack
garbage, but w0 is the one clean, whole-word free slot, matching the prior "ONE UNUSED word".
- **Caveat (must flag):** w0's **low byte is not inert in av-cam** — MSG2 (`sa_func_YKNR_start`)
  reads `ldrb[sp+0x104]`, saves it (`push{r0..}` → `[sp+0x9c]`), and at 0xc3878324 does
  `ldr r1,[sp,#0x9c]; bl 0xc37554de` — i.e. it serializes w0.low into the START message too.
  Since stock w0 is **uninitialised garbage and the camera works**, that field is a proven
  don't-care for the START handler; writing a small id (0..14) is within the existing garbage
  range → no new av-cam risk. (If one wants zero doubt, the probe in §6 also covers MSG2.)

### 1.4 The style source — reachable, object-independently — **camprm global**
The style index the colour module uses is `obj[0]+0x26` (C-COL-028: the `[CAMERA_MAIN_CC]` object,
15 values: Standard 0, Vivid 1, Neutral 2, Portrait 3, Landscape 4, BW 5, Clear 6, Deep 7, Light 8,
Sunset 9, Night 10, Autumn 11, Real 12, Sepia 13, BW 14). Corroborated: 14 `ldrh [obj,#0x26]` reads
cluster in the colour module 0xc3720000-region, and the class-byte builder at 0xc372bc46+ maps
`obj0[0x26]` → the `p8+0x49` class the LUT dispatcher consumes (colour-slots §0).

**But** that is the *colour* module's `obj[0]`. The YKNR acquire's `obj0 = [r5]` is the
capture-frame descriptor (geometry at +0x3e60), **not proven to be the same object** — so keying
the patch off `[r4+0x26]` here is unsafe without a probe. The robust, object-independent source is
the **camprm global**: `camprm_set_colormode` (VA 0xc3461fde) executes
`ldrb r0,[r0,#8]; str r0,[r1,#4]` with `r1 = 0xc3abe32c` (literal pool @0xc34620dc). Therefore

> **active ColorMode (0..14) = `*(u8*)(0xc3abe32c + 4)`** — a persistent RAM global, written when
> the user picks a style (C-CTRL-011 chain: menu `0x01070175` → pid 0x4039 → camprm 0xc3abe32c),
> valid at capture time, independent of whatever object the YKNR stage holds. (0xc3abe32c is
> RAM-only, beyond the file image — a fixed runtime address, exactly as a patch wants.)

### 1.5 av-cam patch sketch (p3 = flashable, **Tier B**)
Insert, anywhere after the field-fill and before the MSG1 pack (e.g. detour the two instructions
at 0xc37ebf7e `add r1,sp,#0x100 / add r0,sp,#0x104`), a 3-instruction write of the ColorMode into
w0, via a code-cave veneer (same detour technique as the proven DSP trampoline; p3 av-cam code
patches are already routine this session):

```
   veneer:
     ldr  rC, =0xc3abe32c      ; camprm base (4-byte literal in the cave)
     ldrb rC, [rC, #4]         ; rC = active ColorMode 0..14
     str  rC, [sp, #0x104]     ; w0 = style id   (full word; low byte also feeds MSG2, §1.3)
     add  r1, sp, #0x100       ; displaced originals
     add  r0, sp, #0x104
     b    back (0xc37ebf82)
```
Reversible: it is a p3 whole-partition flash (28/0, recoverable); revert = reflash stock
`current_p3`. No Backup, no p8.

---

## 2. Module side — where the param lands, and the hook (TASK 2) — one bit open

From the sa_yknr scalar decode (ma1co ISA, `rawdis.py`/`sadis.py`):

- **img0 scalar text = file 0x410..0x3eb0** (stack base 0x3000) is the engine-core control scalar
  (bootstrap + 5 `run_engine` launchers at 0x1f52/0x2506/0x2946/0x2d86/0x31c6 = the 5 VLIW
  programs). The **per-tile core chunks at 0xac50+** (where the hook lives) are copies loaded with
  stack base 0x4000.
- **Params reach the core as a per-tile job struct via pointer `r5`.** The per-tile pixel function
  (file 0xae80, the hook's function) reads `ldr r13,[r5+0]` (= tile window, the value the proven
  trampoline uses), `[r5+4]→r14`, and `[r5+ 8,0xc,0x10,0x14,0x18,0x1c,0x20,0x24,0x34,0x38,0x3c,0x40]`
  (buffer pointers + strides/counts). **The av-cam width/height/stride DO reach the core as these
  struct fields** — the geometry words of the 0x1c block are consumed.
- **Engine aperture 0x40000.. in sa_yknr is written with BAKED constants, not style:** func 0xaf68
  moves literal-pool values `0xb0005,0xd0003,0x90007,0xf0001,0x1000f,0x5000b` (pool 0xb09c..) into
  0x40000/4/8/0x10 — the module's own NR coefficients. No style, no Backup `0x0003010a` here.
- **The open bit (statically undecodable within budget):** img0 interleaves scalar code with VLIW
  / coefficient DATA tables, so the *exact* instruction that reads the 7 inbound words and the
  *block-offset → r5-struct-offset* mapping could not be isolated. Concretely: **it is unproven
  whether the parser DMAs the whole 0x1c block verbatim into core RAM (so w0 sits at some r5+K /
  fixed 0x4000+K the hook can read) or extracts only the geometry fields and drops w0.** That one
  distinction decides whether Part B is a 1-line trampoline read or also needs an img0 edit.

### Hook reachability (TASK 2 / #3)
At the hook (file 0xaf4a, `add sp,#0x50` right after `bl 0x348c`), the reliably-live value is
`r13 = [r5+0]` = tile window (proven by the marker trampoline). `r5` itself is *probably* still
live (not reloaded after the `bl`; if `0x348c` preserves it) but that is **unproven**. So:
- If the probe shows w0 lands at `r5+K`: trampoline does `ldr rS,[r5,#K]` (needs r5 live — probe
  confirms) **or** reads it from the fixed 0x4000+K slot (no r5 dependency — safer).
- If w0 does not reach core RAM: Part B additionally needs the img0 parser to stash w0 — and that
  parser is the one undecoded piece.

---

## 3. The design — 2-part, reversible, one probe-gate (TASK 3)

**Part A — av-cam (p3, Tier B):** §1.5 — write `*(u8*)(0xc3abe32c+4)` (ColorMode 0..14) into the
CALC_START block's **w0 (offset +0x00 = caller sp+0x104)**.

**Part B — module `sa_yknr` (via the proven `/setting` redirect + Backup byte `0x00bd0002[597]=6`,
Tier A; NO p8 flash):** extend the already-working per-tile trampoline so N/mask come from a
**per-ColorMode table** instead of a baked constant — exactly the `grain_bands.s` pattern, indexed
by style instead of by horizontal band:

```
   ; at the hook, load the style id that av-cam put in the block:
   ldr   rS, [<w0 location in core RAM, pinned by the §6 probe>]   ; rS = ColorMode 0..14
   ; clamp 0..14, index two 15-byte tables baked into the routine image:
   ldrb  r4, [Ntab, rS]     ; r4 = N(style)
   ldrb  r5, [Mtab, rS]     ; r5 = mask(style)
   ; ... existing xorshift + (lfsr & mask) - N  per-tile luma loop ...
```
Owner's lineup → suggested starting N (tune on camera): Standard/Velvia50 small, Vivid/House
slight, Portrait/Portra400 moderate, Landscape/Santa800 heavy, Sunset/Phoenix moderate-warm,
B&W/Acros moderate. All tables rebuild trivially; fix the `sum32` trailer (C-DSP-001); deliver via
the proven `/setting` redirect; revert = Backup byte → 0.

**Where it lands vs the one blocker:**
- **If the §6 verbatim-copy probe is POSITIVE** (w0 reaches core RAM at offset K): the design is a
  clean **2-edit** {av-cam w0 write} + {trampoline reads [core+K], tables N} — no img0 parser edit,
  no new undecoded work. This is the expected-good outcome.
- **If NEGATIVE** (parser drops w0): Part B must also edit the **img0 parser** to copy w0 into the
  r5-struct / a fixed core slot — and that parser is the single **statically-undecodable** piece
  (code/data interleave in 15 KB of img0). State plainly: *at that point the param-word route is
  blocked on decoding the img0 job parser*, and the fallback is to repurpose a word the module
  **already** propagates (write the style id into the **upper 16 bits of w1 or w3** — those halves
  are already garbage-on-wire and, if the parser copies the field as a 32-bit word into r5, the
  style id rides along in bits [31:16]; the same probe tells us which, see §6).

So: **not a hard blocker — a 1-probe-gated design.** The probe is cheap, reversible, and reuses
proven tooling.

---

## 4. Exact offsets (no fabrication; file ↔ VA via +0xc3441000)

| item | VA | file off | note |
|---|---|---|---|
| `sa_func_YKNR_acquire` (builder/caller) | 0xc37ebe60 | 0x3aae60 | fills the block; string-confirmed |
| MSG1 pack call (0x1c flat copy wrapper) | 0xc37ebf7e→0xc387809c→0xc3755340 | — | `movs r2,#0x1c` in 0xc387809c@0xc38780c4 |
| `sa_func_YKNR_start` (MSG2) | 0xc3878244 | 0x437244 | reads w0.low = ldrb[sp+0x104] |
| block base | caller sp+0x104 | — | 7 words w0..w6 at +0x00..+0x18 |
| **w0 (FREE word)** | sp+0x104 | — | no producer; carrier for style id |
| w5 width / w6 height | [obj0+0x3e60]/[+0x3e64] | — | geometry (consumed by module) |
| stride (outside block) | [obj0+0x3e50] | — | at sp+0x120, not in the 0x1c copy |
| `camprm_set_colormode` store | 0xc3461fe2 `str r0,[r1,#4]` | 0x20fe2 | r1 literal @0xc34620dc |
| **active ColorMode global** | **0xc3abe32c + 4** | RAM-only | u8, 0..14 (C-COL-028 enum) |
| colour-obj style index (alt source) | obj[0]+0x26 | — | C-COL-028; wrong object at this call site → prefer camprm |
| module per-tile fn (hook's fn) | — | 0xae80 | reads params via r5 |
| trampoline hook (proven) | — | core0 0xaf4a (chunk+0x2fa) | r13=[r5+0]=tile window |
| module engine coeffs (NOT style) | — | writer 0xaf68, pool 0xb09c | baked NR consts to 0x40000 |

---

## 5. Ranked alternative — #4 "read a style value already in engine RAM at the hook" (TASK 4)

**Rank: LAST — not viable for STYLE.** Three grounded reasons:

1. **The parent's example rests on a conflation.** Backup `0x0003010a` is **Soft-Focus** kernels
   for `sa_sftfcs` (C-ISP-004, C-FX-015, C-FX-022, C-MOD-030) — keyed by the *Soft-Focus picture
   effect + level*, **not Creative Style**, and only loaded when that effect is active. The
   "weights → engine 0x40000" statement in the grain scope came from the **sftfcs op7 oracle**,
   not from sa_yknr. (The per-slot *colour* weights live in Backup `0x30001/0x30008` and are
   consumed by the **develop/colour** module — a different engine job / core context, not live in
   sa_yknr's core RAM.)
2. **sa_yknr's engine RAM at the hook has no style signal.** The decode shows `0x40000..` in the
   YKNR core holds that module's **baked NR coefficients** (writer 0xaf68, fixed literals), the
   core struct holds **geometry + buffer pointers**, and the tile holds **luma pixels** (image-
   dependent, not a clean id — same objection as "neighbour-residual" grain, which is re-sharpen,
   not grain). Nothing there differs between Velvia and Portra at a fixed ISO.
3. **Even readability doesn't save it.** The scalar core *can* address 0x40000 (C-DSP-019 shows it
   writes coeffs there), so a hook read of 0x40000 is plausible — but it would return constants
   (no style), at best an ISO/NR-strength proxy, which is a *different feature* (grain-scales-with-
   noise), not the requested style coupling.

**Reliability / reversibility / effort vs route A (param word):**

| route | delivers style? | reliability | reversibility | effort |
|---|---|---|---|---|
| **A — param word (§3)** | **yes** (clean ColorMode id) | high *if* probe positive; else needs img0 parser (undecoded) | av-cam p3 flash (recoverable) + /setting+Backup (Tier A) — both revert | low–med (2 edits + 1 probe); med-high only if img0 edit forced |
| #4 — engine RAM at hook | **no** (no style signal present) | n/a | n/a | wasted — wrong signal |

So #4 is **not a scrappier path to the same goal**; it is a path to a *different* goal (ISO/noise-
keyed grain). If the owner ever *wants* ISO-keyed grain, revisit #4's 0x40000 read — but for
"1 style = 1 grain", route A is the only channel (§0).

---

## 6. Minimal on-camera probe (resolves the single open bit, Tier A/B, reversible)

Reuse the **proven marker trampoline** (it already renders arbitrary per-tile values into the JPEG):

**Probe P1 — verbatim-copy / landing-offset (decides 2-edit vs 3-edit, and pins K):**
1. Apply the §1.5 av-cam patch but write a **sentinel** (e.g. `0xA5A5A5A5`) into w0 instead of the
   ColorMode (p3 flash, revert = stock `current_p3`).
2. Swap in a **probe trampoline** (via the proven `/setting` redirect) that, at the hook, scans the
   per-tile struct `r5+0..0x40` **and** a window of fixed 0x4000-based core RAM for `0xA5`, and
   encodes "found at offset K" as the marker's horizontal position (or writes K into the first tile
   pixels).
3. Shoot one high-ISO frame. **Marker present → the block is DMA'd verbatim; K is the landing
   offset → 2-edit design, trampoline reads [core+K].** **Absent → parser drops w0 → img0 edit
   needed (or switch the carrier to w1/w3 upper-half and re-run P1).**
   Revert: Backup byte `0x00bd0002[597]=0` + reflash stock p3.

**Probe P2 — style-signal scan (free bonus; no av-cam change):** probe trampoline reads candidate
core bytes (`r5+off`, fixed 0x4000 slots) and modulates the marker; shoot the **same scene under
Standard vs Vivid** and diff. Any byte that changes with style is a ready-made hook-readable style
channel that would skip Part A entirely. (Low expectation — geometry/NR params are ISO- not style-
keyed — but it is the cheapest possible shot and would collapse the whole design to one edit.)

Both probes are reversible and reuse the proven delivery; neither touches p8 or a prod partition.

---

## 7. One-line bottom line
av-cam side is fully pinned (free word = block **+0x00**; style = **`*(u8*)(0xc3abe32c+4)`**; patch
= one store before the 0x1c pack). Module side proves the geometry params reach the core via the
`r5` job struct but leaves **one bit open** — whether the unused word rides along verbatim —
resolvable by the P1 sentinel probe on the already-proven trampoline. Positive probe → clean 2-edit
reversible design. Negative → the img0 job parser (statically undecoded) is the single remaining
blocker, with w1/w3-upper-half as the fallback carrier. The parent's engine-RAM alternative (#4)
is dead for style (wrong signal) and ranks last.
