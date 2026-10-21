# Grain injection design — P4 luma noise (sa_yknr)

Status: 2026-10-14. Offline static analysis on the owner's own NEX-3N dump. Module
`sonygen/sa/3N_p8/sa_yknr.bin` (single image `YKNR_0__0x01`, desc 0x100, **text file
0x410..0x3eb0** = text-rel 0..0x3aa0, total file 0xd104). Disassembly via
`sonygen/isa/{sadis,vdump}.py` (run from the isa dir; `-I` breaks their local `import slots`).

**Headline: Task 1 is resolved, and it overturns the handoff's framing.** The E-0077 null
result was a *region error*, not a fact about r19. The "Region B inline VLIW at file 0xbfa8"
does not exist — those bytes are a copy of the scalar `run_engine` wrapper. The real linchpin
and the corrected probe are below.

---

## 0. Two proven corrections to the prior model (read first)

### 0a. "Region B VLIW at file 0xbfa8" is scalar code, not VLIW
`regionB_P4.txt` labels file 0xbfa8 as the inline VLIW program start (`0x188f000a`). It is not.
Decoded as 16-bit scalar syllables it is the **exact `run_engine` wrapper prolog**:

```
0xbfa8: 000a 188f   op000a ; str r8,[sp,#-4]!
0xbfac: 189f 18af   str r9 ; str r10,[sp,#-4]!
0xbfb0: 18bf 18cf   str r11; str r12
0xbfb4: 18df 18ef   str r13; str r14
0xbfb8: 00df 68f8   str lr ; ldr r8,[sp,#32]
...    1b40 0009    mov r0,r4 ; run_engine r0
```

This is byte-identical to the P4 handler prolog at text-rel 0x2d94 (file 0x31a4). The signature
`0a008f18` occurs 10+ times across the file (text copies at file 0x1f30/0x24e4/0x2924/0x2d64/0x31a4
= the five P0..P4 wrappers; data-region copies at 0x4dd4/0x5474/0x5b14/0x61b4/0x6854/0xbfa8/...).
The "stepping lane regs 8f/9f/af/bf/cf/df/ef" the expert read as VLIW lanes are just r8..r14 in
push/pop. And `regionB_P4.txt` lines 0xc030..0xc04c (`0x00048208 0x00048200 0x000094e0 0x00048218
...`) are the **literal pool** of that scalar function — the DMA MMIO addresses. So file
0xbf34..~0xc050 is one *loadable overlay* = `[param table 0xbf34..0xbfa4][scalar wrapper + its
literal pool]`, matching the known overlay layout (C-IDT-001). **Region A (the param table) is
real; "Region B VLIW" is a mislabel.**

### 0b. The E-0077 edit site 0xce80/0xce88 is a coefficient tail, not executed VLIW
`vdump` of file 0xce80..0xcef8 shows near-all-`0xff` filler bundles:

```
00ce80 8fffffffffffffff   S0=8ff  ffff ffff ffff ffff
00ce88 bfffffffffffffff   S0=bff  ffff ffff ffff ffff    <- E-0077 edited S1 here (idle 0x1fff -> op7 r19)
00ce90 bffffffff54fff10   S0=bff  ffff 7.31.29 2.19.31 7.24.16
00cec0 b54fffffffffffff   S0=b54  ffff ffff ffff ffff
```

These are not compute bundles (one S0 nibble group + 0xff idle slots = packed signed
coefficients / padding). sa_yknr has **5 VLIW programs** (C-MOD-026) = **5 NOP-delimited clusters**
(the NOP bundle is `0x1f70fb87dc3ee1f7`):

| cluster | file range | #nops | location |
|---|---|---|---|
| 1 | 0x34d8..0x3630 | 9 | in text |
| 2 | 0x3ad8..0x3bf8 | 5 | in text |
| 3 | 0x6c78..0x6f80 | 16 | data overlay |
| 4 | 0x9a48..0x9b90 | 11 | data overlay |
| 5 | **0xc9f8..0xcc20** | 7 | data overlay |

**0xce80 sits 0x260 bytes past the end of cluster 5** (the last program) — in its trailing
coefficient table. E-0077 edited dead data, so of course it had no JPEG effect. That null tells us
*nothing* about whether r19 is the output luma. It was the wrong address.

---

## 1. TRUE output-luma write (the linchpin) — RESOLVED

Two layers:

**Physical egress (proven, scalar, exact).** The finalized luma tile leaves the engine by a
**DMA-OUT of SRAM `0x9000`** (next-tile pair `0x9800`), programmed by scalar code:
- OUT descriptor reg `0x48234` ← `0x9000` : MMIO trace `0xaec` (ldr r8=0x48234) / `0xaf4`
  (ldr r2=0x9000) / `0xafc` (`str r13,[r8]`), and `0x10c4/0x10c8` / `0x10ca` (ldr r1=0x9000).
- OUT addr/kick reg `0x48230` ← 1 : `0x10cc` (`str r0,[r8]`, r8=0x48230).
- Sync = `wfi` + poll `0x94dc/0x94e0`.

So **grain must be present in SRAM `0x9000` before the OUT kick fires.** That is the single
physical gate; everything upstream only matters insofar as it changes `0x9000`.

**Who writes `0x9000`:** the engine, during `run_engine` of the P4 finalize pass. The store is a
VLIW bundle in the **P4 program = cluster 5 (0xc9f8..0xcc20)** — *not* 0xce80. Evidence this is the
P4 program: it is the last of the 5 programs, and E-0077's author believed 0xce80 (immediately
after it) was the "P4 finalize" region. Its tail carries the finalize compute, and **r19 is a
dominant destination there** — the hypothesis E-0077 meant to test but tested at the wrong offset:

```
00cbb0 1f70f187944ee257   .  0.15.03 0.15.05 0.19.23 0.18.23     <- writes r19,r18 (op0.a.b, b=dst)
00cbb8 1f70f187884c8244   .  0.15.03 0.15.02 0.19.04 0.18.04     <- writes r19,r18
00cbf8 1f1f59fa4e1e70d3  1f1 7.21.19 7.20.19 4.07.19 4.06.19     <- op7/op4 accumulate into r19
00cc30 1f7f59fa4e1e70d3   .  7.21.19 7.20.19 4.07.19 4.06.19
00cc38 f1c78f000701c000  f1c 3.24.30 0.00.01 6.00.14 0.00.00     <- f1c-family stream/AGU setup (op3 read, op6 clamp)
```

The recurring **`f1c78f00…` words (0xcc38, 0xce78)** are AGU/stream-descriptor setups (op3 read
r24-stream + op6 clamp) that plausibly point the engine's output stream at the `0x9000` window —
i.e. the store is an **op5/AGU stream write**, not a plain register store, which is why "edit a
register" probes are fragile.

**Honest limit:** the *exact* bundle+register that commits to `0x9000` is not statically pinned —
the op5/AGU store semantics are undecoded and there is no VLIW emulator (the standing gap). But it
is now localized to **0xcbb0..0xcc38 inside cluster 5**, a ~0x90-byte window, instead of the dead
0xce80. That is the difference between "needs an emulator" and "needs one cheap probe."

### 1a. Minimal camera probe to pin the store (replaces the dead 0xce80 probe)
Goal: find which bundle's result lands in `0x9000`. Shoot a flat mid-grey wall each time; a hit =
the tile visibly changes (flat shift / clip / banding at the 128×8 tile grid).

1. **Constant-force probe (preferred).** In cluster 5, change the `f1c78f00…` store/AGU word at
   **0xcc38** (or its sibling patterns) so the streamed value is forced — e.g. redirect op3's
   source `a=24` to a register known-constant, or zero the op6 clamp input. If the tile goes
   flat/black → that word feeds the output store. One shot per candidate; 3–4 candidates
   (0xcc38, 0xcbf8, 0xcbb8, 0xcc30) binary-search the store in ≤4 flashes.
2. **r19×2 probe, done right.** Repeat E-0077's *intended* test but at a **real r19 write**:
   bundle **0xcbf8** (`7.21.19` = op7 into r19) — add a second op7 r19→r19 in a free slot. If the
   wall blows to white, r19 *is* on the output path (contradicting the stale E-0077 "conclusion",
   which was void). If not, r19 is intermediate and the store rides the AGU word → go to probe 1.

Either probe is one `/setting` byte edit + one shot, and it closes Task 1 definitively.

---

## 2. The add-syllable (Task 2) — DESIGN, exact bytes pending the §1a probe

Bundle = 64-bit LE: `S0[63:52]` (12b) + four 13-bit slots `S1..S4`, each = `op[12:10].a[9:5].b[4:0]`
(dst=b, src=a). Idle slot = `0x1f7` (`op0.a15.b23`), fill = `0x1fff`. Known ops: op3 = read
r24-stream, op7 = accumulate (b += a), op4 = mul, op5 = AGU/stream-pointer, op6 = clamp(hyp).

The add-syllable goes **in the P4 program (cluster 5), in the bundle immediately before the store
identified in §1**, using two currently-idle slots:
- **op3 read** the new noise stream into a free reg `Rn` (e.g. slot `3.24.Rn` — op3 reads the
  r24 stream engine into Rn; needs the noise stream wired as the stream op3 pulls, see §4).
- **op7 add** `Rn` into the luma accumulator that feeds the store (the reg found in §1, call it
  `Ry`): slot `7.Rn.Ry` (Ry += Rn).

Place both in idle (`0x1f7`) lanes of an existing bundle in 0xcbb0..0xcc30 so no compute is
displaced, and before the AGU store word (0xcc38). Exact 64-bit before/after bytes require: (a) the
store reg `Ry` from §1a, (b) a provably-dead lane reg `Rn`, (c) confirmation op3 can be pointed at
a *second* stream. **All three are camera-probe / emulator outputs, not statically derivable** —
flagged.

---

## 3. Ring `#6 -> #7` extend (Task 3) — bound edit EXACT; 7th descriptor needs a stub

The DMA-in descriptor ring is at SRAM `0x91f0`, 16 B/entry `{[+0]=addr/count, [+4]=0x40000000(GO)}`,
indexed `idx<<4`. The kick loop runs **exactly 6** (`cmp.eq r8,#6`). Two loop sites, both halfword
`0x8068`:

| what | text-rel | **file offset** | bytes now | bytes for `#7` |
|---|---|---|---|---|
| kick-loop bound A | 0xf82 | **0x1392** | `68 80` | `78 80` |
| kick-loop bound B | 0x1070 | **0x1480** | `68 80` | `78 80` |

`cmp.eq r8,#7` encodes as `0x8078` (op4=8, i8=7, rd=r8). So the bound bump is **one byte each**:
`0x1392[0]: 0x68→0x78` and `0x1480[0]: 0x68→0x78`.

**But the bound bump alone kicks an unwritten slot → DMA hang.** The 7th slot is ring index 6 =
`0x91f0 + 6*16 = 0x9250`, and the descriptors are **runtime-built**: the marshal copier at 0xd80
copies 12×16-B records from a runtime stack buffer `[sp,#12]` (loop `cmp r4,#12` @0xda2;
per-index ring writes `str addr,[r1]; str 0x40000000,[r1,#4]` with `r1 = 0x91f0 + idx<<4` at the
DMA-setup routines 0xa40/0x1030). Nothing in the module statically writes index 6. So the extend is:

1. the two 1-byte bound edits above (exact), **plus**
2. a scalar insertion that writes `0x9250 = {noise_src, 0x40000000}` *before* the kick loop runs
   (e.g. `mov` the noise source addr into the slot, two stores). The existing `wfi`+poll barrier
   then serializes the noise DMA ahead of the engine read — no extra barrier needed.

Item 2 is **not a byte-patch**; it needs ~8–12 B of code at a point dominating the kick loop. Honest
flag: that code-cave + the stable `noise_src` address both depend on the live SRAM map (§4, C-DSP-020).

---

## 4. Noise staging (Task 4) — model clear; blocked on free space + SRAM map

Model (reciprocal-LUT precedent, C-MOD-026/C-IDT-010): a resident table in the module is DMA'd to an
engine address — sa_yknr's `65536*16/n` LUT lives at engine `0x40078..0x400e0`, file source ~0x238c.
A noise tile would be staged the same way: resident bytes → DMA-in → free SRAM → op3 stream.

Two hard blockers found:

- **No free space in the module.** Full scan of sa_yknr.bin for runs ≥64 B of `0x00`/`0xff` returns
  **only one 0x63-byte run (file 0x9d..0x100) in the header** — unusable. There is nowhere to bake a
  1024-B (128×8) noise tile, nor even a 256-B tiled one. Options: (a) overwrite an unused overlay/LUT
  (risky — the live regions hung the camera in E-0075/76); (b) **generate noise algorithmically**
  (a small LFSR/xorshift in a scalar stub) instead of a baked table — most robust given (a); (c)
  reuse an existing high-entropy table already in the module as a pseudo-noise source.
- **DMA-in target SRAM is unknown and un-mappable from ARM.** The target must be outside
  `0x9000-0x9fff` (output) and `0x94xx` (status), and outside the ring `0x91f0`/`0x9250` and the used
  `0x9504/0x9508`. But per **C-DSP-020** the DSP SRAM is **not ARM-visible** (E-0078 §0 confirmed:
  senser reads of `0x91f0`/`0x9000` return zeros/DRAM mirror). So a free SRAM window cannot be picked
  by a static read. It must be found via the **E-0078 exfil channel** (a scalar epilogue stub that
  copies a candidate SRAM word into the tile and reads it back from the JPEG) — proven to work.

---

## 5. Recommended path — the VLIW/DMA chain is not the cheapest route

E-0078 proved a **16-B scalar stub at the per-tile epilogue hook** (`chunk+0x2fa → chunk+0x08`)
reads DSP SRAM and writes the tile buffer `[r13-0x800]`, and **it lands in the SOOC JPEG** (grid of
dots at the 128×8 tile grid). That means the scalar side can already deposit grain into the `0x9000`
tile before DMA-out — **without touching the VLIW at all**, sidestepping the undecoded op5/AGU store
and the §4 DMA-in entirely.

The only limit is code-cave size: the proven hook gives 16 B (fits a splat, not a per-pixel loop;
a `0x9000` grain loop over 1024 bytes + LFSR is ~38–48 B). So the **primary recommendation** is:

> Find/relocate a larger code cave reachable from the per-tile epilogue and write a scalar grain
> loop: for each of the 1024 luma bytes in the tile, `Y += lfsr_step() & mask` (clamp). Noise is
> algorithmic (no module free space needed), the write target is the already-proven `0x9000` tile,
> and delivery is the proven `/setting` + epilogue-hook channel.

Secondary (if a clumped/structured grain that only the engine can do is wanted): the VLIW
add-syllable of §2 + the ring extend of §3 + staging of §4 — gated on the §1a probe and the SRAM map.

---

## 6. Task status

| task | status | what's exact | what's blocked |
|---|---|---|---|
| 1. true output write | **RESOLVED** | DMA-OUT of SRAM `0x9000` via `0x48234`/`0x48230`; store localized to cluster-5 bundles 0xcbb0..0xcc38; E-0077 explained as a region error (0xce80 = coefficient tail) | exact store reg/bundle → 1 camera probe (§1a) |
| 2. add-syllable | **DESIGNED** | slot format, op3-read + op7-add placement before the 0xcc38 store | exact 64-bit bytes → needs §1a store reg + a dead lane reg |
| 3. ring 6→7 extend | **PARTLY EXACT** | bound bump: file 0x1392[0] and 0x1480[0], `0x68→0x78` | 7th-slot descriptor write at `0x9250` needs a ~10-B stub + stable noise_src addr |
| 4. noise staging | **BLOCKED** | model = resident table → DMA-in (recip-LUT precedent) | no module free space (use LFSR); free SRAM target needs E-0078 exfil probe (C-DSP-020) |

**No `.bin` built:** the chain is not clean (store reg unconfirmed, no staging space, 7th-slot write
needs code). Per the brief, build is deferred until §1a resolves the store and §4 resolves staging.
The cheap unblock is the single §1a camera probe; the robust product is the §5 scalar-loop path.

---

### Reproduce
```
cd ~/nex3n-dump/sonygen/isa
MOD=~/nex3n-dump/sonygen/sa/3N_p8/sa_yknr.bin
python vdump.py $MOD 0xc9f8 0xcc40      # P4 program (cluster 5) incl. the store tail
python vdump.py $MOD 0xce40 0xcf00      # the 0xff coefficient tail E-0077 wrongly edited
python sadis.py $MOD 0xd80 0xde0        # marshal copier (12x16B, runtime-built)
python sadis.py $MOD 0xf70 0xf94        # kick-loop bound A (cmp r8,#6 @ 0xf82 / file 0x1392)
python sadis.py $MOD 0x1066 0x1078      # kick-loop bound B (cmp r8,#6 @ 0x1070 / file 0x1480)
```
