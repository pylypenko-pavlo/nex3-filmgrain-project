# Luma stage = sa_YKNR; luma output = chan18 (clmp r24) — the luma-grain target (2026-10-16)

The owner's chosen direction after PBE was shown to be chroma-only (E-0090): **find the stage that WRITES the luma
plane.** It is **sa_YKNR** (Y-channel noise reduction). Found by applying the same clamp→store output scan that
pinned PBE's chroma (chan3): in sa_yknr the dominant "finalize+emit" is **`clmp r8=clamp(r24) + st r8 -> chan18`**,
appearing **5× at a regular 0x6a0 stride** (per-tile plane walk) — the shape of a luma output written tile by tile.

## Evidence chan18 = LUMA (DeepSeek-confirmed, 3 converging signals)
- **source:** r24 ← port24 (the luma input stream; port24=luma proven on the sibling PBE module).
- **spatial regularity:** 5 stores at exact 0x6a0 spacing = tiled per-region plane output (0x4fe0, 0x5680, 0x5d20,
  0x63c0, 0x6a60 — file offsets in sa_yknr `sonygen/sabin_nex6/sa_yknr.bin`, 0xd104 bytes).
- **module identity:** YKNR = luma NR; its primary write IS the luma plane.
- These 5 stores sit in a **large dense VLIW region 0x3c00-0x6c78** (1551 bundles, reads port24 ×44, port2 ×44,
  port31 ×42) that the PRIOR yknr map MISSED (its "5 NOP-delimited clusters" did not include this region). So the
  prior luma-store hunt (E-0077/E-0079, cluster 5 @0xcbb0-0xcc38, r19) was looking in the wrong place — same class
  of error as E-0077's dead-0xce80 edit. **chan18 @0x4fe0… is the better candidate.**
- Residual gap (DeepSeek): chan18 is a channel id; without its consumer/routing map it could be a luma SCRATCH,
  not the final writeback. Camera confirms it.

## Verification test (FIRST, when camera returns) — mirror of the chan3=chroma test
Zero all 5 chan18 stores (datum → r31). Expect **BLACK / dark-luma frame, colour intact** (exactly analogous to
store-0→chan3 → desaturation). Caveats (DeepSeek): zero ALL 5 (else black-tile checkerboard); dark-grey-not-black
⇒ chan18 = luma+something or clamp floor ≠ 0; if colour also collapses ⇒ chan18 isn't an independent luma plane.
Build: patch op5 b==18 at the 5 sites → `st r31->chan18`; fix the yknr checksum (see Delivery).

## Luma-grain injection (after chan18 confirmed) — the DeepSeek noise design, applied to luma
Inject per-pixel noise into **r24 PRE-CLAMP** at each of the 5 sites (clamp then bounds it for free — least smear,
no second clamp). Only inject post-clamp (r8) if r24 has a live consumer after the clamp (then re-clamp needed).
The noise composition is identical to `grain-chroma-solution.md`:
```
pk  rp = port24 & MASK        ; per-pixel entropy (luma LSBs)
mul rp = rp * K1 ; add rp += SEED ; mul rp = rp * K2 ; pk rp = hi_slice  ; hash, SEED=per-frame scalar
; luma modulation: w = L*(1-L) (parabola, midtone peak)  via add/mul
mul rp = rp * w
add r24 += rp                 ; inject pre-clamp, then clmp r8=clamp(r24) -> chan18
```
Per-frame SEED via a free command-table slot (engine register-file image, `engine-command-table.md`) the scalar
advances per exposure — the one hard enabler, shared with the chroma solution.

## Delivery (RESOLVED — same mechanism as PBE)
- Channel: `/setting/` redirect via Backup **`0x00bd0002`, byte 597** (= 8*74+5, sa_yknr = file-id 74, row 74),
  set to `0x06`; module at `/setting/sa_yknr.bin`. **`deliver_setting.py` already does this** (OFF=597 hardcoded).
- Checksum: **sum32 of body[:-4] at len-4** — verified identical to PBE (stock trailer 0xec52e8bf = sum32 ✓).
- Reversible: byte → `0x00`. Crashes take USB down → cold-boot (same as PBE).

## READY-TO-FLASH test (built this session, camera was off)
**`~/nex3n-dump/work/filmgrain/sa_yknr_chan18test.bin`** (md5 `0c26cf0417a1be445efa05c0576ea603`) — zeros the 5
chan18 stores (datum→r31) with a valid sum32 trailer. Next camera session: flash via
`deliver_setting.py sa_yknr_chan18test.bin` → cold-boot → shoot a scene → pull+view the frame. BLACK/dark luma,
colour intact ⇒ chan18 = luma CONFIRMED → proceed to the luma-grain injection (r24 pre-clamp).

## op5/dataflow DECODE PROGRESS (2026-10-16, E-0092 + DeepSeek + channel tracer)
- **Luma store sites CONFIRMED** = `op5 a7→chan3` @0xcd80-0xce70 (changing their `a` field reaches the JPEG:
  a=7→a=31 = NR-bypass grain, ISO-gated, E-0091). But **adding to GP register r7 (op7→r7) had ZERO effect** →
  op5's `a` is NOT the GP register op7 writes.
- **Two-bank model (DeepSeek, consistent):** a GP/compute bank (op0/2/4/6/7) and a separate channel/output bank;
  **op1 pk bridges GP→channel**, op3 rd fills channels from ports, op5 moves channel→channel (a=src-chan,
  b=dst-chan; a=31=null). So the luma datum enters the channel bank only via an op1-pack of a GP register.
- **Channel dataflow tracer** (dual-bank, built this session): chan3's value roots at a **pack @0xcc98** from a
  **GP r14 compute chain**. ⇒ candidate injection = add noise to **GP r14 before 0xcc98** (NOT r7, NOT the store).
- **OPEN contradiction (needs camera to resolve):** the tracer shows chan3 rooted at g14 with no explicit port24
  leaf — either the model's op3/op5 roles are still slightly off, or the pixel enters r14 upstream of the window.
  The op5/op1 exact bank semantics aren't fully pinned (C-DSP-015). Resolve empirically.

### RANKED next-session camera probes (resolve op5 + pin luma injection; shoot at ISO 16000 where yknr runs)
1. **Pack-root probe:** zero/alter the op1 pack @0xcc98 (change its GP source a) → if luma changes, chan3 roots
   there → inject noise into that pack's GP source. (Tests the tracer's chan3→pack@0xcc98→g14 claim.)
2. **chan7 producer probe:** alter `op5 a=10→chan7` @0xcd30 (a=10→a=31) → if luma changes, chan7 feeds the store
   → inject into chan7's GP producer (r10 before 0xcd30).
3. **r1/r14 inject:** add a per-pixel luma tap to **r14** (or r1) in a dead lane *immediately before* the pack
   that feeds chan3 → if luma brightens, that GP reg is the injection point → swap the tap for luma-LSB noise.
Each is one `/setting` flash + shots at ISO 200 (control) & 16000. Noise design once pinned: luma-LSB via pk →
op2 xf scramble → op7 add into the GP reg before the pack (DeepSeek, `ds_op5`), + per-frame SEED via a free
`0x40000` engine-reg slot (C-DSP-019). Camera left with `sa_yknr_r7inject.bin` → revert (byte 597→0) or overwrite.

## Status
LEAD, high-confidence, DeepSeek-sanity-checked, verification module BUILT (not yet camera-verified — camera off).
Open: camera confirmation (chan18=luma); free command-table slot for the per-frame SEED; free VLIW slots for the
~8 hash ops at the 5 store bundles. Cross-refs: `grain-chroma-solution.md`
(identical noise design), `pbe-engine-map.md` (sibling chroma map), `grain-injection-design.md` (prior yknr OUT-DMA
/ the cluster-5 misdirection), `06-experiment-log.md` E-0090. Tools: `vliw_dis.py`/`vliw_enc.py`, DeepSeek `dsq.py`.
