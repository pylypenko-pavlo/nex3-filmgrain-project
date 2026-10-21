# Grain via VLIW noise-stream injection — the plan (2026-10-15)

After **two** rigorous walls — E-0085 (no per-pixel entropy *inside* the PBE VLIW) and E-0086 (the
`sa_sftfcs` scalar is an *orchestrator*; pixels never enter scalar-addressable memory, same as yknr) — the
owner chose the one remaining clean SOOC path: **make the VLIW engine itself add grain**, with the entropy
supplied from outside the engine.

## The core idea (why it beats both walls)

```
engine_output[p] = convolution(pixel neighbourhood)  +  noise_stream[p] * filmResponse(luma[p])
                   \__ what the engine already does __/   \____ the new term we inject ____/
```

- **Beats E-0085** (no entropy inside the VLIW): the entropy is NOT generated in the VLIW. A **scalar/ARM
  PRNG** writes a per-frame-random **noise plane** into a buffer; that buffer is fed to the engine as an
  **input stream** (the engine already reads pixel streams via op3 from DMA-programmed ports). The VLIW only
  *reads and adds* it — no internal position/entropy source needed.
- **Beats E-0086** (scalar can't reach pixels): we do NOT ask the scalar to touch pixels. The **engine**
  touches pixels (it already does — that's the blur). We only add one `op7 add` of the noise stream before
  the clamp/store.
- This is exactly the path E-0085 already pointed at ("ARM-side injection of a noise plane via IN-DMA — the
  `cmdtable` project"), now made concrete as *stream-in + one engine add*.

## Target stage — decide in Phase 0

| | **PBE** (`sa_pbe_work`) | **sftfcs** (Soft Focus) |
|---|---|---|
| runs | **every frame, every ISO** (universal) | only when Picture Effect = Soft Focus |
| output→JPEG | **proven** (E-0081/E-0084) | proven this session (Probe 0) |
| per-pixel value store | **proven** (E-0084) | n/a (engine) |
| analysis depth | deep (E-0081..85) | this session (E-0086) |
| gating | always on (grain on every shot) | effect-gated ("pick film mode") |
| **preferred** | **yes** — universal, last stage, most analyzed | fallback / if PBE has no free stream port |

PBE is the default target unless Phase 0 shows it has no free input-stream port or no editable slot before the
store, in which case sftfcs (or another stage) is evaluated. Gating preference ("shoot like film = choose a
mode") can be layered later (a param check), independent of the injection mechanism.

## Phases

### Phase 0 — FEASIBILITY (make-or-break, offline static RE). GO/NO-GO.
The whole approach lives or dies here; keep it cheap and honest.
0.1 **Decode the target VLIW microcode.** Locate the engine program (bundle blocks via NOP sig
    `0x1f70fb87dc3ee1f7`), map the stream reads (op3, `a`=port), the mul/add (op4/op7), clamp (op6), store
    (op5 AGU). Reuse the PBE map from E-0081..85 (`grain-injection-design.md`, `engine-command-table.md`).
0.2 **Free input-stream port?** Does the engine read from a port we can repurpose/add, and does the
    **engine command table** (`engine-command-table.md`) have a stream slot the scalar can point at our noise
    buffer? Count ports used vs available.
0.3 **Can the scalar feed a stream?** The scalar programs IN-DMA (`0x48200/08/10/18`, rtn `@0xa40`). Confirm
    we can add one IN-DMA stream from an SRAM/DRAM noise buffer to that port (mirror the existing setup).
0.4 **Editable slot before the store?** Is there a bundle slot (or room to add one) to insert `op7 add
    noise→acc` between the convolution result and the clamp/store?
→ **If 0.2 or 0.4 fail, the approach is dead — report it and stop.** Cheap kill.

### Phase 1 — VLIW EDIT LOOP de-risk (on-camera; the no-emulator problem)
C-DSP-015 (no VLIW emulator) is the top risk. Establish the edit→flash→observe loop before any grain:
1.1 Change ONE kernel coefficient in the engine program → shoot → blur strength visibly changes = **we can
    edit VLIW bundles correctly**. (Analogue of the scalar probe loop.)
1.2 Insert a provable no-op / identity op in a free slot → shoot → image unchanged = **we can add ops without
    breaking the engine**.
1.3 Optional: build a *partial* VLIW emulator from the decoded ops (op0/3/4/5/6/7) to pre-check edits — big
    risk-reducer; closes part of C-DSP-015.

### Phase 2 — STREAM FEED (scalar/ARM side; we own this — it's orchestration)
2.1 **Noise generator:** adapt `grain_loop.s` / xorshift32 to write a per-frame-random **noise plane** to an
    SRAM/DRAM buffer each frame (reseed per exposure → per-frame random). Scalar CAN write SRAM and program
    DMA (proven E-0086). Cross-ref `cmdtable` project (`~/nex3n-dump/handoff/BLOCKED-TASKS.md`, `cmdtable_*`).
2.2 **DMA the noise plane** to the chosen engine input port (clone the IN-DMA setup from 0.3).
2.3 **Validate the feed:** feed a CONSTANT (e.g. +40) instead of noise → shoot → whole image brightens by a
    fixed amount = the engine reads our stream and adds it. (First proof the term lands in the JPEG.)

### Phase 3 — THE ADD (flat grain)
3.1 Insert `op7 add noise_stream → result` before clamp/store.
3.2 Feed real noise (flat amplitude) → shoot flat grey at base ISO → **per-pixel grain on a flat field = goal
    mechanism reached.** Measure HP-std / ACF.
3.3 Shoot two frames → **0 % identical noise = per-frame random** (the thing every prior route failed).

### Phase 4 — LUMA MODULATION (film curve)
4.1 Add `op4 mul`: `noise * filmResponse(luma)` before the add — the engine HAS the pixel luma and a `mul`.
    `filmResponse` = the measured 16-pt curve (`grain-luma-response.md`, peak Y≈88) as an engine LUT/coeff.
4.2 Tune amplitude to ACROS-like σ (≈2.7–3.4). Expose a knob (SF 3-level byte, or a Backup param).

### Phase 5 — SHIP
Redirect delivery (proven, reversible — `deliver_sftfcs.py` pattern / Backup `0x00bd0002`), amplitude knob,
atlas retrospective, update `04-dsp-modules.md` + `engine-command-table.md`.

## Risks & kill-criteria
- **C-DSP-015 — no VLIW emulator (TOP RISK).** Mitigate: Phase 1 establishes the on-camera edit loop; 1.3
  builds a partial emulator. Every VLIW edit tiny + reversible; each validated on-camera, staged.
- **No free stream port / no editable slot (Phase 0.2/0.4).** → hard kill, reported early and cheaply.
- **Undecoded ops op1/op2.** Decode only as needed; op1≈pack/shift, op2=transform (E-0085).
- **VLIW crashes are HARD** — they take the USB/MSC interface down (E-0086 viz crash → `No devices found`,
  needs power-cycle). So: every edit minimal + reversible via `/setting` byte; recover by cold-boot.
- **Scope:** Phase 2 overlaps the dormant `cmdtable` ARM-noise-plane project — reuse it, don't restart it.

## First concrete step
**Phase 0.1 on PBE** — pull the PBE engine-command-table + microcode map from E-0081..85 and
`engine-command-table.md`/`grain-injection-design.md`, and answer 0.2 (free input-stream port?). That single
question gates everything; answer it before writing any kernel.

## State at plan time (2026-10-15)
- sftfcs scalar-grain thesis **falsified** (E-0086); camera left with the `vizsram` probe loaded + crashed
  (USB down) — **revert to stock `sa_sftfcs` pending** next session (`deliver_sftfcs_revert.py`, byte 445→0).
- Colour half remains SOOC-shippable (unaffected).
- Cross-refs: E-0081..E-0086, `grain-injection-design.md`, `engine-command-table.md`, `grain-luma-response.md`,
  `grain-codecave.md`, `grain-sftfcs-module-design.md` (now superseded), `cmdtable` handoff.

## PROGRESS — 2026-10-16 (E-0087; research via free DeepSeek v4.1 Flash + camera validation)
- **Phase 1 (VLIW add) DONE & byte-verified:** read a free engine input PORT into a scratch reg, add to r15
  before the op5 store. Edit (decoder-verified): `0x7310` S2→`read-stream a25 b10`; `0x7318` S3→`add a10 b15`.
- **Phase 2 target stage = PBE; the engine-input PORT mux = MMIO `0x48434`** (pbe scalar; **file = disasm +
  0x4c0**), low 6 bits = port, port 24 = 0x18. Per-frame DRAM handle via **doorbell `0x49804` → source reg
  `0x48208`**. IN path is **register-driven, not ring-descriptor**.
- **Phase 2 CONFIRMED on camera:** retargeting the mux off port 24 (one halfword at file `0x74c`
  `0x2473→0x2443`, sum32 Δ=−0x30) gave a **fully black frame, no hang** ⇒ (a) **ONE IN channel** (retarget
  steals the content), (b) the mux edit **reaches the SOOC JPEG** — model correct end-to-end.
- **Remaining = the CLONE:** duplicate the IN-DMA setup+entry to add a 2nd channel (mux=25 + a 2nd source from
  the noise doorbell) while keeping port 24. Then feed port 25 a per-frame noise buffer (ARM supplies the DRAM
  handle via the doorbell) and the Phase-1 add produces grain.
- **Methodology:** free DeepSeek (OpenCode headless API) + deterministic `vliw_decode.py`/`sadis` + camera as
  oracle. DeepSeek is accurate on exact-data tasks (mux, E1, Δ=−0x30 all verified); verify every byte with the
  correct text_base (0x4c0) — a disasm↔file slip looks like fabrication but isn't.

### 2-CHANNEL WALL (E-0088, 2026-10-16) — stream-injection blocked
The PBE engine has **exactly two IN-DMA channels, both essential: X = luma (`0x48434`), Y = chroma
(`0x48420`)** (camera-proven: retarget-X→black, retarget-Y→magenta glitch + texture). No spare channel ⇒
**no way to feed a per-frame noise plane into a free engine input port.** Phase-1 (add to r15) and Phase-2
(mux reaches JPEG) are proven; the blocked piece is the **noise SOURCE**. Re-think needed: another DSP DMA path
outside this engine's 2-channel bank, an ARM-fed plane via a different route (`cmdtable`, E-0085), or entropy
without a new stream. (Bonus: retarget-Y = a usable magenta-glitch Picture-Effect look.)

## TOOL — vliw_dis.py (2026-10-16)
Systematic SA-DSP VLIW microcode disassembler (full bundle decode + cross-bundle register dataflow + stream/
store/clamp labels). Decoded the PBE output pass (file 0x7000-0x74a8): `STREAM[port 24]`(luma)→ compute
(op2 `xf` ×17, op1 `pk` ×7, mul, clamp) → `r15 = clamp(r0)` → `STORE chan 3` @0x7318/30/60. Reads 3 ports
(24, 23, 31) but there are only 2 DMA channels ⇒ one port is non-DMA (entropy candidate — the live lead vs the
2-channel wall). Usage: `vliw_dis.py <mod.bin> <file_off> <count>`.
