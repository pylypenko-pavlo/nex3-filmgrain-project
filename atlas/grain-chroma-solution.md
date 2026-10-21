# Chroma grain solution — PBE VLIW chan3 injection (2026-10-16)

The one reachable per-pixel injection on this camera is the **PBE VLIW output** (proven E-0081/E-0084: the PBE
engine writes per-pixel VALUES that reach the SOOC JPEG). This session (E-0089…, `pbe-engine-map.md`) established
that **PBE's editable output is CHROMA** (`chan3`), while luma passes through untouched by the microcode. So the
first deliverable the owner asked for — a CHROMA-grain solution — is built on the chan3 path.

> Honest scope: film grain is primarily *luminance*. Chroma grain alone is NOT the end goal; it is (a) the
> capability PBE actually gives us, and (b) a full proof of the per-pixel noise-injection mechanism (source →
> hash → luma-mod → add → store) that transfers directly to luma the day a luma-writing stage opens. Luma remains
> blocked: PBE = chroma only (this session, 3 negative luma-register tests r30/r13/port24-retarget); yknr/sftfcs
> scalar routes closed (E-0079/85/86). See `07-open-questions.md`.

## Injection point (proven reachable)
Final PBE pass, chroma store: `0x7318` / `0x7330` / `0x7360` = `clmp r15=clamp(r0) + st r15 -> chan3`. The
chroma value is `r0` (pre-clamp accumulator) → clamped into `r15` → stored. Two equivalent injection spots:
- **Pre-clamp (preferred):** add noise to `r0` in a free slot of a bundle *before* the store bundle (e.g. 0x7308/
  0x7310), so `clmp r15=clamp(r0+noise)` keeps the result in range automatically.
- **Post-clamp (E-0087 style):** add noise to `r15` between the clamp and the store — but clamp already happened,
  so large noise can overflow; needs its own clamp. Pre-clamp is cleaner.

## Noise design (DeepSeek v4.1, 2026-10-16) — per-pixel, per-frame-random, luma-modulated
No external noise plane is available (2 IN-DMA channels both used, E-0088; descriptor-ring extend blocked, see
`grain-injection-design.md` §3/§4). So entropy is composed from **two in-engine sources**:
- **per-PIXEL** = the luma LSBs (`port24` low 4-5 bits) — already noise-like and per-pixel (contains real sensor
  read/photon noise, which is itself partly per-frame-random in shadows).
- **per-FRAME** = a scalar-written **SEED** coefficient, advanced by an ARM xorshift once per exposure → guarantees
  frame-to-frame decorrelation independent of scene content (the single hard requirement; option (a), the robust one).

Op sequence (between the accumulate and the chan3 clamp/store; mnemonic — exact bytes via `vliw_enc.py`):
```
rd   rp  <- port24            ; luma tap (per-pixel) — already read in these bundles
pk   rp  = rp & MASK          ; keep low 4-5 bits = per-pixel entropy
mul  rp  = rp * K1            ; K1 odd mix constant
add  rp  = rp + SEED          ; SEED = per-frame scalar coefficient  <-- frame decorrelation
mul  rp  = rp * K2            ; K2 odd — avalanche, high bits go white
pk   rp  = hi_slice(rp)       ; extract a small signed codeword, zero-mean (subtract BIAS)
; luma modulation (parabola, peak at mid-grey): w = L*(1-L) scaled
add  rw  = L + Cm1            ; Cm1 = -1 const  -> (L-1)
mul  rw  = L * rw             ; = L*(L-1) = -(L*(1-L))   (sign folded into the add below)
mul  rp  = rp * rw            ; amplitude peaks in midtones, ->0 in shadows/highlights
add  r0  = r0 + rp            ; INJECT into chroma accumulator, before clmp r15=clamp(r0)
```
Constants `MASK/K1/K2/BIAS/Cm1` and the amplitude scale are chosen so the injected excursion stays within the
clamp range. `r31=0` supplies the clean zero for centering.

## The SEED path — the key enabler (= DeepSeek's "scalar-written coefficient the microcode reads")
The engine's **command-table (Region A)** is a *register-file image* — `engine_reg[idx] = value` for slots
`0x31..0x48`, loaded into the engine before the VLIW program runs (`engine-command-table.md`). Many slots are 0
(free candidates in yknr: 0x31/32/33/36/38/39/3a/3b/3f/43/44). **If the scalar writes a per-frame xorshift value
into a free command-table slot that maps to a GP register the microcode reads, that register IS the SEED.** This
is the robust, content-independent per-frame source.
- Open: locate **PBE's** command-table (yknr's is at file 0xbf34; PBE's own must be found) + a free slot whose
  index maps to a microcode-readable register + the scalar write-site to advance the seed per frame.
- Fallback (stepping stone, no seed): skip the SEED add → grain is per-pixel + luma-modulated but FIXED per scene
  (fails the per-frame-random bar). Useful ONLY to prove the injection+hash+modulation chain on camera first.

## Staged build/test plan (camera needed)
1. **Prove the add reaches chroma** (1 shot): add a constant to `r0` before 0x7318 → flat chroma shift in the JPEG
   (re-confirms E-0087 on the chroma accumulator). View the frame (SD pull — see `nex3n-sd-frame-view`).
2. **Prove per-pixel from luma LSBs** (1 shot): `pk rp=port24&MASK; add r0+=rp` → chroma grain texture appears,
   fixed per scene. Confirms the per-pixel path + hash.
3. **Add luma modulation** (1 shot): multiply by the parabola → grain peaks in midtones, clean shadows/highlights.
4. **Add the per-frame SEED** (needs the command-table slot + scalar seed write): two consecutive frames → 0%
   identical noise = per-frame-random achieved.
5. **Amplitude knob + ship:** expose via a Backup param / an engine-table slot; deliver via the proven
   `/setting` redirect (`deliver_pbe.py`, Backup 0x00bd0002[573]); reversible.

## What is exact vs open
- EXACT: injection point (0x7318/30/60, chroma=r0→r15→chan3); the add reaches the JPEG (E-0087); delivery channel.
- DESIGN (DeepSeek), not yet byte-built: the hash + parabola op sequence (needs free slots near the store + the
  SEED register).
- OPEN (needs camera / more RE): free slots around 0x7310-0x7318 for ~8 ops (may need to spill into the padding
  or an adjacent bundle); the per-frame SEED command-table slot + scalar write; `pk`/`xf` exact field semantics.

## Cross-refs
`pbe-engine-map.md` (PBE = chroma processor, the full map), `grain-injection-design.md` (yknr OUT-DMA/ring, the
noise-staging blockers), `engine-command-table.md` (Region A register-file image = the SEED slot source),
`06-experiment-log.md` E-0081/84/87/0089+. Tools: `vliw_dis.py`/`vliw_enc.py`, DeepSeek `dsq.py`.
