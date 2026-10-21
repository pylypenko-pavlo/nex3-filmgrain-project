> **⛔ FALSIFIED 2026-10-15 by E-0086.** The central premise below — "data lives in scalar-addressable SRAM,
> so the module's scalar core can add grain to the pixels directly" — is **WRONG**. On-camera probing
> (Probe S/v2/v5/v6/v7 + the `vizsram` ground-truth crash) proved `sa_sftfcs` scalar is an **orchestrator**:
> it programs DMA + the VLIW engine, but pixels live in DRAM / the engine aperture and **never enter
> scalar-addressable SRAM** (the "334 SRAM refs" were descriptors/coefficients, not pixels). Same wall as
> yknr (C-PIPE-022). The scalar grain loop (`grain_loop.s`) and the measured curve stay valid and reusable,
> but **not via scalar store** — see `grain-vliw-injection-plan.md` for the live path (engine adds a
> scalar-fed noise stream). Document kept for the method/history; read the banner, not the claims.

# Grain via a custom sa_sftfcs module — the scalar-grain-loop prototype (2026-10-15)

After the PBE VLIW route hit a hard wall (E-0085: no per-pixel non-content source inside the VLIW),
the owner proposed the radical move: **write our own replacement for Soft Focus.** Research says this
**breaks the wall** — because a *module we author* controls its own data path, and `sa_sftfcs` works in
**scalar-addressable SRAM**, so the module's **scalar core can add grain to the pixels directly** — no
VLIW, no undecoded ops, no emulator.

## Why this works (the two findings that flip it)

1. **The module sets up its OWN DMA.** `sa_sftfcs` scalar code writes the engine DMA registers directly:
   `0x48200` (×21), `0x48208` (×31), `0x48218` (×15), `0x48210`, OUT `0x48230/34` — the IN/OUT stream
   setup is in the **module's scalar section** (runs on the SA-DSP scalar core), not only ARM. Disasm:
   `0x1414` str `0x10000`→[`0x48208`] (enable), `0x1484` str #2→[`0x48208`] (mode), `0x1506` str #2→
   [`0x48218`]; descriptor builder in the `0x13000` SRAM region; DMA-kick routine `@0xd28` parses a
   descriptor (dims/strides/addrs at +8/+12/+16/+28/+68/+72); `wfi` waits for completion. **So we, as the
   module author, control the pipeline** (contradicts the "streams are ARM-only" reading from the PBE
   assessment — it's the *module's* scalar wrapper).
2. **Data lives in scalar-addressable SRAM, NOT the engine aperture.** Address-literal classification of
   `sa_sftfcs`: **SRAM `0x13000–0x33300` region = 334 refs**, SRAM `0x9xxx–0xffff` = 197, DMA regs
   `0x48xxx` = 135, **engine aperture `0xf8xxxx` = just 1.** Unlike `sa_yknr` (pixels in the aperture
   `0xf81400`, scalar-unreachable — C-PIPE-022), **`sa_sftfcs` processes tiles in scalar SRAM.** The
   scalar does heavy 16-bit access (308 `strh`/`ldrh`, visible `strh r,[r8]` loops) → it reads/writes
   pixel buffers.

⇒ **The scalar core can loop over the tile pixels in SRAM and add grain** before the output DMA. The
whole E-0085 "no per-pixel entropy register" wall is irrelevant: the scalar is a real CPU (loops, mul,
mem, PRNG), it addresses each pixel, and it has all the entropy we want.

## The grain algorithm (all in the DECODED scalar ISA)

Per tile (128×8 YUYV = 1024 px), inside the module's scalar section, after IN-DMA / before OUT-DMA:
```
for each pixel p in the SRAM tile buffer:
    lcg = lcg*1664525 + 1013904223          # LCG PRNG, state in a SRAM global (persists across tiles)
    noise = (lcg >> 16) & 0xff  - 128        # signed per-pixel noise
    Y = luma(p)
    g = noise * filmResponse[Y>>4] >> SHIFT  # luma-modulated (16-pt curve, peak at Y≈88), SHIFT = amplitude
    Y = clamp(Y + g, 0, 255)
    write Y back to p
```
- **Per-pixel:** scalar loops over pixels. ✓
- **Per-frame-random:** the LCG state is a SRAM global → it advances continuously across tiles within a
  frame AND carries/ is reseeded across frames (seed from a frame-varying value, or free-run). ✓ — the
  exact thing the VLIW route could never get.
- **Luma-modulated:** `filmResponse[]` = the measured 16-pt curve (`grain-luma-response.md`, peak Y≈88),
  a small table in module data. ✓
- **Universal (flat/low-ISO):** grain is ADDED, independent of sensor noise. ✓
- **Amplitude knob:** `SHIFT`. **Strong→dial-down** by raising SHIFT.

## Delivery & trigger (ideal host properties)
- Redirect `sa_sftfcs` via Backup `0x00bd0002[0x1BD]` (= file-id 55·8+5 = **445**) → `0x00→0x06`, module
  at `/setting/sa_sftfcs.bin`. Proven/reversible (C-MOD-044).
- **Trigger = user selects Picture Effect → Soft Focus.** Exactly the owner's "pick one effect → grain,
  normal shooting untouched." Our module ignores the blur and just does input→+grain→output (we author
  it; we don't need soft focus).
- Size-legal: stock 43 652 B < ~53 KB write limit; our scalar loop + curve table add little.

## Build plan (staged, each reversible; revert = stock md5 c64ce801…)
1. **Probe S-sftfcs (first increment — confirm scalar reaches the output).** Insert a scalar write of a
   fixed marker into the tile buffer at the processing point → shoot → marker visible = scalar→output
   path confirmed (the sftfcs analogue of yknr's Probe S). Resolves the one residual risk.
2. **Pass-through check.** Make the module copy input→output (minimal/no blur) → shoot → normal image =
   our authored data path works.
3. **Grain v1.** Add the scalar grain loop (fixed amplitude, LCG, luma curve) → shoot flat dark/bright +
   a scene → per-pixel grain present on flat areas = goal reached. Measure HP-std/ACF vs ACROS.
4. **Tune** amplitude (SHIFT) + per-frame seed, iterate.

## Concrete build target — PINNED this session

From the OUT-DMA literal pool at `0x137c–0x1398` (`sa_sftfcs`):
```
0x1380 .long 0x00049000   0x1384 .long 0x00013000   0x1388 .long 0x000004c8 (1224)
0x138c .long 0x00000628   0x1390 .long 0x00013800    0x1394 .long 0x40000000 (DMA GO)
0x1398 .long 0x00048230 (OUT-DMA reg)   0x139c .long 0x00013700 (OUT descriptor)
```
- **The finished tile sits in SRAM `0x13000` (+ `0x13800`)** just before OUT-DMA; the OUT-DMA descriptor
  is built at `0x13700` and kicked by writing the GO word to `0x48230`. `0x13000` is scalar-addressable
  (the scalar reads/writes it throughout) → **we can overwrite/modify it from scalar code.**
- **Insertion point = immediately before the `0x48230` OUT-DMA kick (~`0x1398` / the descriptor-build at
  `0x1330–0x1374`)**: loop over the `0x13000` tile and add grain, then let the existing OUT-DMA stream it.
  Adding grain *here* (post-compute, pre-output) means it is NOT re-blurred by the sftfcs VLIW. ✓

## Open items still to pin (offline, next)
- **Tile layout at `0x13000`:** dims `0x4c8`(1224)/`0x628`(1576) and the Y/C packing & stride (is it
  planar Y then C, or YUYV?). Decode the descriptor fields `@0xd28` (+8/12/16/28/68/72) → pixel count &
  stride, so the scalar loop indexes luma correctly.
- **Code-insertion mechanics:** place the added scalar loop in a dead/pad region of the module (or extend
  within the 53 KB cap), branch to it from just before the `0x48230` kick and back; re-compute sum32.
- **Scalar PRNG + curve encoding:** LCG (`mul`+`add`, the SA-DSP scalar has `mul r2,r3`) with state in a
  SRAM global; 16-pt `filmResponse` as a small table (`ldrb`/`ldrh` lookup). Validate the whole loop
  offline with `saemu.py` (scalar emulator — works, unlike the absent VLIW one).

## Scalar grain loop — CODED & saemu-VALIDATED (2026-10-15)

Written in SA-DSP scalar asm (`~/nex3n-dump/work/filmgrain/grain_loop.s`, **62 bytes**), assembled with
`grain-scripts/saasm.py`, validated in `saemu`. **mul-free** (the ISA mov sign-extends 8-bit imm and the
assembler has no `mul`): PRNG = **xorshift32** (shifts+eor); luma-modulation = **shift-attenuation**
(noise `>>` a per-luma amount from a 16-entry table, no multiply). Entry regs: r1=tile ptr, r7=pixel
count, r2=PRNG state, r8=shift-table base, r11=baseshift (amplitude knob). Shift table (from the measured
curve, more grain = smaller shift): `[2,1,0,0,0,0,0,0,0,1,1,1,1,2,3,3]`.

saemu validation (flat tiles, `measure`):
| luma | 20 | 60 | 90 | 128 | 180 | 230 |
|---|---|---|---|---|---|---|
| grain std | 36.8 | 73.7 | **73.7** | 73.7 | 36.8 | 9.2 |

→ **peak in the midtones, falling to shadows/highlights — the film curve ✓.** Per-frame random: 0%
identical pixels between seeds ✓. Amplitude knob `baseshift` 0→4 ⇒ std 74→37→18→9→4.6 ✓ (ACROS ≈2.7–3.4
→ baseshift ≈4–5). **The grain engine is proven in software, no camera needed.** Remaining = wiring:
r1←the `0x13000` tile, r7←pixel count (tile dims), the table + PRNG state as module data (state in a SRAM
global → persists across tiles/frames for per-frame seed), inserted before the `0x48230` OUT-DMA kick;
plus code placement + re-sum32.

## First increment to build (when camera is back): Probe S-sftfcs
Minimal scalar insert before the `0x48230` kick that writes a **fixed marker** into the `0x13000` tile
(e.g. a constant or a coarse gradient) → shoot with Soft Focus selected → marker visible in the JPEG =
the scalar→OUT-DMA→JPEG path is confirmed (the sftfcs analogue of yknr's proven Probe S). Then swap the
marker for the grain loop.

## Why this beats everything prior
No VLIW emulator needed (scalar ISA is decoded + `saemu`-testable); no per-pixel-register wall (scalar
addresses pixels directly); per-frame-random + luma-modulated + universal all trivial in scalar C-like
code; clean user trigger (Soft Focus); reversible delivery. **This is the path to the full goal.**

*Cross-ref: E-0085 (PBE wall), `grain-luma-response.md` (the curve), `grain-codecave.md` (scalar ISA,
Probe S precedent), `02-capture-pipeline.md` C-ISP-004/C-FX-015 (sftfcs), C-MOD-044 (delivery). Research
this session: sftfcs DMA setup disasm, address-literal classification (334 SRAM vs 1 aperture).*
