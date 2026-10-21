# PBE engine block — the living map (2026-10-16, building toward the full picture)

Systematic reverse of the `sa_pbe_work` DSP engine (the last programmable stage before the HW JPEG encoder),
the target for grain injection. **Discipline: every finding goes on this map; what we can't yet see is marked
`⬜ WHITE SPOT`.** Built from the scalar orchestration (authoritative), microcode decode (`vliw_dis.py`),
camera ground-truth, and free-model (DeepSeek via `dsq.py`) structural reasoning — every byte claim verified
at text_base `0x4c0` (scalar) and against the camera.

## Overview (established)
- PBE runs **6 `run_engine` passes**. The engine reads **input STREAMS by PORT** (op3) and writes **output
  CHANNELS** (op5, 0..31). An **OUT-DMA** then streams SOME channels to DRAM Y/U/V buffers → the JPEG.
- **PORTS ≠ CHANNELS** (op3 ports vs op5 channels are different address spaces — do NOT cross-map port N↔chan N).
  [DeepSeek, sound.]

## Passes (scalar `run_engine` sites; file = disasm + 0x4c0)
| site | kind | microcode ptr (r0) | notes |
|---|---|---|---|
| 0x1e64 | inline | **0x6242** (also 0x62f6, 0x6441 seen in the ldrh seq) | r8=0x508e (per-pass params base?) |
| 0x1e84 | inline | 0x6441 / 0x62f6 / 0x0000 | |
| 0x1ec4 | wrapper | **r4 (runtime)** ⬜ | `mov r0,r4; run_engine` — ptr from caller |
| 0x21aa | wrapper | **r4 (runtime)** ⬜ | |
| 0x234a | wrapper | **r4 (runtime)** ⬜ | |
| 0x251a | wrapper | **r4 (runtime)** ⬜ | |
- ⬜ **WHITE SPOT: the 4 runtime passes** — microcode pointer comes in r4 from a higher caller; the bodies may
  even be DRAM-downloaded (not in this flash image). Need the r4-trace at each wrapper's caller.

## Microcode regions (static)
- **0x62e0–0x6950** (1648 B) — holds the inline entry points 0x6242/62f6/6441. ports read {0,23,24,25,31}.
- **0x6958–0x74c0** (2920 B) — **a CHROMA pass** (camera-proven): reads {port24 luma, port31 chroma}, writes
  chan3 (chroma). Store channels {18:18, 3:14, 25:9, 31:8, 19:6, 26:4, 15:4, …}. This is the region whose
  microcode edits I mistakenly chased as luma (chan3 is chroma).
- ⬜ The region/body that emits **LUMA** is NOT identified (likely a different, possibly runtime, pass).
- Classifier caveat: the current region scanner conflates ARM-scalar with VLIW bundles → boundaries unreliable.

## Inputs — PORTS (op3 read-stream)
| port | carries | evidence |
|---|---|---|
| **24** | LUMA input | camera: corrupting its engine-input mux (scalar `0x48434`, file 0x74c) → BLACK frame |
| **31** | CHROMA input | camera: corrupting its mux (`0x48420`, file 0x7c2) → magenta cast, structure intact |
| **23** | NOT DMA-fed (internal/coeff) | scalar has exactly **2 IN-DMA config blocks** (5 regs each): X=`0x48434/38/3c/40/44` (luma/port24), Y=`0x48420/24/28/2c/30` (chroma/port31). **No 3rd block for port 23** ⇒ port 23 is internal/constant, ARM can't feed it ⇒ **not a noise door** (E-0088 wall holds) |
| 0,25,6,7,12,13,26 | ⬜ (coeffs? neighbour taps? aux?) | read in the regions; roles unknown |

## Outputs — CHANNELS (op5 store) and their mapping to Y/U/V
| chan | role | evidence |
|---|---|---|
| **3** | CHROMA output | camera: store 0 → desaturation (RGB 135/127/121→116/118/116), NOT black |
| **25** | NOT luma (SCRATCH) | camera: zero all chan25 stores → NORMAL frame |
| **18** | NOT luma (SCRATCH) | camera: zero all 20 chan18 stores (incl 8 in pass 0x6800) → NORMAL frame |
| ~~18/19/26~~ | **TESTS VOID** | ⚠️ camera "normal" was MEANINGLESS: all their op5-slots were in **junk gaps between coherent runs** (verified: chan18 20/20, chan19 8/8, chan26 4/4 slots in-gap). I patched non-bundle data → no change → false "eliminations". Classifier straw-grab. |
| **9** | NOT luma (SCRATCH, REAL test) | camera: zero 2 coherent stores @0x6af8/0x6b18 → NORMAL ("чисто"). Valid elimination. |
| **31** | **LOAD-BEARING (essential)** | camera: zero ALL 28 coherent chan31 stores → **silent CRASH** (USB down, cold-boot needed). ⇒ chan31 is NOT null-sink; it's used as both inter-pass feedback AND likely final output. Clusters in port24-heavy runs. **Still the leading luma candidate** — but zeroing all 28 also broke feedback → crash. Need surgical test. |
| **? = LUMA (Y)** | ⬜ **"luma=channel" hypothesis EXHAUSTED** | tested 9(normal), 25(normal), 31-final(normal, inert padding), 3=chroma; 31-all→crash(feedback). **No op5-stored channel is luma.** |

### Final-run structure (0x7290-0x74b0, fully disassembled)
- **0x7290-0x7398** = real VLIW: `rd port24`(luma taps→r30/r10/r12) + accumulate; **3 real op5 stores `r15=clamp(r0) → chan3`** @0x7318/0x7330/0x7360 = **CHROMA out, datum r15** (matches E-0087's edit site — it added to chroma, not luma).
- **0x73a0-0x74b0** = `add r31+=r31` **padding/wind-down**; the "chan31 stores" (st r27/r31→chan31) sit inside this junk ⇒ inert (zero→normal confirmed).
- **Last real store of the whole module = r15→chan3 (chroma) @0x7360.** Luma read ×33, **never op5-stored.**
- ⚫ **CONCLUSION: PBE's only clear op5 output is CHROMA (chan3, datum r15). LUMA flows through a register accumulator (r24/r0 from upstream passes), consumed by OUT-DMA — NOT a zeroable channel.** Grain-into-luma ⇒ inject into the luma accumulator register in a port24-heavy pass, not a channel store. Which register carries final luma = the new white spot (needs upstream r24/r0 trace or a positive camera test: add a constant to a candidate reg → luma brightens = found).
- **OUT-DMA descriptor construction (scalar 0xcb0-0xcf4):** builds a descriptor at DRAM **0x8800** from a table
  indexed `[0x8800 + r6*16 + 52]` (r6 = plane/channel loop index), fields: [0]=chan-binding (from DRAM table),
  [28]=10, [32]=2, [20]/[24]/[36]/[40]=runtime. Then **TWO ring bases are programmed to 0x48234: 0x9000 (@0xcf0)
  and 0x9800 (@0xa78)** ⇒ **two OUT-DMA planes (likely Y-plane + chroma-plane separately).** The channel→plane
  binding comes from the DRAM table `[0x8800+…]` ⇒ **runtime-opaque confirmed from a 2nd angle.** Which ring is
  luma (0x9000 vs 0x9800) is the clean empirical question if a register-probe is inconclusive.
- **OUT-DMA kick decoded (scalar 0xa78-0xa84):** `MMIO[0x48234] ← 0x9800` (ring base), then `MMIO[0x48230] ← 1`
  (kick). The **channel→Y/U/V map is in the ring descriptor at DRAM 0x9800, built at RUNTIME** — plus the
  lookup tables `0x8948 / 0x8988 / 0x89c4` (literal pool @0x9fc/0xa0c/0xa14) are all **> module size 0x7504 ⇒
  DRAM addresses**. ⇒ **the authoritative static path is BLOCKED (DRAM-runtime-opaque).** The channel→luma
  mapping can only be resolved **empirically** (zeroing a channel's stores → black=luma / desaturate=chroma /
  normal=scratch). This is not a straw-grab: the systematic pass-map narrowed luma to **{19,26,9}** first.

## CONSOLIDATED STATE (2026-10-16, after full channel sweep + crashes)
**Camera-solid facts:** port24=luma-in, port31=chroma-in; **chan3=chroma out** (datum r15, @0x7318/30/60);
corrupt port24-in → BLACK (luma flows through PBE).
**Channel sweep result (all coherent-verified):** zeroing tested channels gives only three outcomes —
NORMAL (scratch: 9, 25, 15), CRASH (feedback: 31-all, {17,4,5}, {21,10,11}), or DESATURATE (chroma: 3).
**NO channel zeroes to BLACK.** ⇒ **Luma does NOT exit via a zeroable op5 channel** — it's carried in a
register accumulator (r0/r24 are the inter-pass carriers; r0→r15→chan3 is chroma) and consumed by OUT-DMA
through a non-op5 path. The bracket's **vertical stripes on the RAW stage** (from {21,10,11}) = per-column
corruption, i.e. those channels touch early/positional output (a lead, but they also crash → feedback-coupled).

**THE TOOLING WALL (honest):** the VLIW/data classifier cannot reliably separate 64-bit bundles from scalar/
coefficient data (the by-datum histogram shows ~every reg→~every channel = impossible ⇒ false bundles admitted).
So the store map and register-dataflow are NOISY, and each camera guess risks a crash. Root cause: the **engine
microcode base is unknown** — run_engine(r0=0x6242/0x62f6/0x6441…) entry values are NOT file offsets (not
8-aligned; deltas not ÷8; index*8 overflows the 30 KB module) ⇒ **microcode is (at least partly) DRAM-resident/
copied at init**, and the 4 runtime passes' bodies may not be in this flash at all. Without the flash↔DRAM
microcode map (or a VLIW emulator) the pass boundaries stay unreliable.

**What IS cleanly hookable:** the CHROMA path — chan3, datum r15, final pass 0x7290-0x7398; E-0087 proved a
register-add before that store reaches the JPEG. LUMA register injection needs the luma accumulator pinned,
which the current tooling can't do reliably.

## ⚫ VISUAL BREAKTHROUGH (2026-10-16, frames pulled from SD /Volumes/Untitled/DCIM)
Workflow upgrade: the SD card mounts as mass-storage → **pull JPEGs and view them directly** (sips -Z + read),
no more verbal description. Viewed chan11-zero (DSC09678) and another (DSC09677):
- **LUMA STRUCTURE SURVIVES every channel-zero** — the scene is always readable in luminance (table, objects,
  window, folds). The damage is always in **CHROMA**: heavy pink/purple/magenta casts, block-wise colour
  corruption, + fine scanline stripe overlays.
- Combined with "corrupt port24-IN → BLACK": **luma ENTERS PBE (port24) and passes through ROBUSTLY to output;
  PBE's op5 channels compute CHROMA.** chan3/11/21 = chroma; zeroing them wrecks colour, not luma.
- ⇒ **Channel injection in PBE = CHROMA grain (colour noise), NOT luma grain.** For film LUMINANCE grain the
  only handle is the **luma passthrough = the port24 read itself** (no "luma accumulator" exists — luma isn't
  computed, it flows). Luma grain ⇒ perturb the port24-read value (r30) in a pass, before output.
- Visual catalog (per channel, zeroed): chan3→desaturate, chan21→magenta, chan11→pink+block chroma+stripes,
  chan10/17/4/5→crash (feedback), chan9/25/15→normal (scratch).

## ⚫ LUMA MAP (2026-10-16, taint-trace + scalar + DeepSeek; camera off)
**Luma is PROCESSED by PBE and emitted via a REGISTER→OUT-DMA path, before the final chroma pass.** Details:
- **Taint trace** (port24 reads = LUMA taint, propagated through mov/pk/xf/mul/add/clamp across all clean passes):
  luma FIRST appears in pass **0x6310** (reads port24 **×61**, stores NOTHING via op5) into regs **r12, r13** —
  this is the **luma-convolution/working pass**. Luma taint persists (r12/r13) and spreads to {10,11,12,19,30}
  by the final pass. The "no op5 store" + heavy luma reads ⇒ luma result leaves 0x6310 in a REGISTER.
- **Empirical (camera):** doubling/amplifying r30 in the FINAL pass 0x7290 → **NO luma change** ⇒ the luma plane
  is already emitted BEFORE 0x7290 runs (0x7290 = chroma-only: stores chan3). Two independent reasons it did
  nothing: (a) luma already DMA'd, (b) op2 `xf` is a nonlinear transfer that can squash a linear amplify.
- **OUT-DMA = a PER-PLANE LOOP** (scalar 0xa70-0xcf6): plane counter **r9**; `r9 & 1 == 0 → ring base 0x9800`,
  `r9 odd → ring base 0x9000`; both funnel to the **shared kick** at 0xa7e (`MMIO[0x48230]=1`). So the engine
  emits 2 planes (Y + chroma) by alternating the ring base, kicking each. Descriptor built at DRAM 0x8800 from
  `[0x8800+r6*16+52]` (runtime). Microcode entry **0x6800** is loaded at scalar 0x506 (`r6=0x6800`).
- **op2 `xf`** = unary NONLINEAR transfer (abs / square / LUT / threshold — DeepSeek; appears in luma chain
  `xf r30=xf(r16)`). Not identity/linear. Breaks magnitude reasoning; taint still propagates conservatively.

**⇒ Luma-grain injection point = the luma pass (0x6310) output, BEFORE its DMA kick** — NOT the final chroma
pass. The staged (untested) `lumaCarriers.bin` doubles {11,12,13,19,10} in the final-pass padding; by this map
it will likely show no luma change (too late).

**LUMA EXPORT REGISTER = r13 @ end of pass 0x6310 (DeepSeek, high-confidence reasoning).** In the pass tail
0x6488-0x6538, **r13 is the only invariant register** — never written, only preserved (`mov r13=r13` @0x64d8 =
keep-alive) and read (`mov r1=r13` @0x6500). That is exactly the shape of "value computed earlier, held for
OUT-DMA export." (r12 = transient raw tap, re-read 6×, ends pk(r16); r24 = intermediate accumulator consumed by
r14.) **⇒ NEXT CAMERA TEST: inject a per-pixel perturbation into r13 in a free slot at 0x6538** (or last r13
write before the luma kick) → view whether LUMINANCE changes. Caveat: must confirm r13 isn't overwritten
between 0x6538 and the luma DMA kick (needs the run_engine→ring→kick ordering, still partly traced).

**r13 overwrite check (static):** r13 is BUILT in pass 0x6310 (`add r13+=r30` @0x63b8, from luma taps) and
kept-alive (`mov r13=r13` @0x64d8), THEN overwritten in later passes (`add r13+=r3` @0x6958 chroma region;
`mov r13=r5` @0x6ee8 in pass 0x6ea8). ⇒ r13@0x6310 survives to export **only if the luma DMA kicks right after
pass 0x6310**, before the chroma passes reuse r13 as scratch. This kick-ordering can't be pinned statically
(microcode-base opacity: run_engine entry values 0x6242/0x62f6/0x6441/0x6800 aren't file offsets). **The camera
test resolves it directly:** inject per-pixel noise into r13 at 0x6538 → luma changes ⇒ r13@0x6310 = luma
export AND luma kicks after 0x6310; no change ⇒ luma kicks later / r13 overwritten first → move injection to the
last r13-build before the kick. This is the single decisive next-camera experiment.

### ⚠️ UNEXPLAINED LEAD — revisit (flagged by owner, don't lose it)
**lumaSrc test** (DSC09685): retargeting ALL 61 `port24→port31` reads inside luma pass **0x6310** produced
**faint vertical lines across the whole frame** (thin, per-column; luma structure otherwise intact). This is the
**ONLY positive luma-adjacent signal** from any VLIW edit (r30/r13 doubling = pure zero). Meaning: pass 0x6310
DOES reach the output, in a faint **per-column** pattern. Hypotheses to test later: (a) it's the chroma-guide
bleeding a per-column artifact (0x6310 builds the chroma edge-guide; feeding it chroma instead of luma shifts
columns); (b) 0x6310 feeds a weak luma term that IS per-column-structured → amplifying/isolating it could expose
the luma handle. NEXT when camera returns: amplify this effect (stronger per-column perturbation in 0x6310) and
watch whether LUMINANCE or only chroma moves; binary-split the 61 reads to find which taps cause the lines.

### Remaining white spots (genuinely runtime/undecoded — not laziness)
- ⬜ Exact luma output register + WHICH ring (0x9000 vs 0x9800) is Y: needs the scalar run_engine→ring→kick
  ordering fully traced (control-flow heavy) AND the DRAM descriptor source field. r9-parity picks the ring;
  the plane↔content binding is in DRAM `[0x8800+…]`.
- ⬜ op2 `xf` exact function (needs the xf LUT/decode).
- ⬜ Engine microcode base: run_engine(r0=0x6242/0x62f6/0x6441/0x6800…) values are NOT file offsets (not
  8-aligned); microcode partly DRAM-resident. The 4 runtime (r4) passes may not be in this flash.
- ⬜ The chroma taint tracking is noisy (op2 xf undecoded) — chan3 datum showed taint None not C; trust the
  camera (chan3=chroma) over the tracer for chroma.

## Grain target (once the map is complete)
Add a per-pixel noise plane fed through a stream port (AGU = per-pixel position, E-0089) into the **LUMA**
output before its store, luma-modulated. Needs: the luma channel + its pass/store site + a free stream to feed
noise (the sacrificed/bit-packed chroma channel, E-0089).

## Next extractions (systematic, DeepSeek's plan — fill the white spots)
1. **OUT-DMA window** — scalar writing 0x40000–0x4000c + the descriptor before the 0x48230 kick → the
   authoritative chan→Y/U/V map. (highest value)
2. **r4-trace** at 0x1ec4/0x21aa/0x234a/0x251a callers → the 4 runtime microcode entries → map those bodies.
3. **Params table at r8=0x508e** (loaded @0x1e64) → per-pass config / channel-select values.
4. **Classifier fix** (split ARM-16bit from VLIW-64bit by alignment/opcode-space) → reliable region boundaries.
5. **ONE decisive camera experiment** (after the store sites are enumerated): patch every op5 store to emit its
   **channel-index** as the value → one frame → read which tag lands in Y vs U vs V → complete chan→buffer map.

## Tools
`vliw_dis.py` (VLIW disassembler + dataflow), `vliw_enc.py` (slot encoder/patcher), `dsq.py` (DeepSeek
request/response shim), `sadis.py` (scalar). Camera deliver/revert: `deliver_pbe.py` / `deliver_pbe_revert.py`
(Backup `0x00bd0002[573]`).

## Camera state
Reverted to stock PBE after the chan25 test (pending confirm). Probes built: `sa_pbe_work_{E1retarget,
Yretarget,stageA,D1,VAL,chan25}.bin` (all reverted / supersed​ed).
