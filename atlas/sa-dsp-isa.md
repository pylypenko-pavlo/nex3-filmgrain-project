# SA-DSP ISA — the correct two-layer model (2026-10-17 correction)

Corrects/clarifies the "VLIW" framing used across the grain docs. Authoritative source: **ma1co's SA-DSP Ghidra
plugin** (`sonygen/ma1co-SA-DSP/`, SLEIGH spec `data/languages/dsp.slaspec`) — the community RE of Sony BIONZ SA-DSP.

## The SA-DSP is TWO layers, not one VLIW

1. **16-bit scalar core** — a clean SH-like RISC. This is what `sa_*.bin` modules are **mostly made of** and what
   runs the per-module orchestration.
   - 16 GP regs `r0..r15` (r15≈sp), `lr`, 1-bit flag `fr`; 16-bit little-endian instructions, alignment 2.
   - Full ISA (ma1co `dsp.slaspec`): nop/cfr/sfr/ret/wfi; mov/ldr/str (byte/half/word, reg-offset, post-inc,
     pc-relative); add/sub/mul/and/orr/eor/mvn/neg/shifts; cmp.* (eq/geu/ges/gtu/gts/nand); branches b/bl/bfs/bfc;
     **float** fadd/fsub/fmul/fdiv/ftosi/fsito. No delay slots.
   - **Tooling we already have:** `sonygen/isa/sadis.py` (partial disassembler, matches ma1co). ma1co's plugin adds
     Ghidra **decompilation** (C pseudocode) — stronger; not yet installed here.
   - **This layer is fully readable and AUTHORABLE** (normal RISC; caves, noise math, etc. are straightforward IF the
     pixel data is reachable from scalar — see below).

2. **The "engine" coprocessor** — launched by the scalar op **`run_engine r0`** (op16=`0x0009`; `r0` = pointer to a
   **command table**). The engine does the heavy **per-pixel** work (convolution/blend/transfer). Its command stream
   is the 8-byte-periodic data we previously read as "64-bit 4-slot VLIW bundles" (e.g. yknr `~0xcd80`, the region the
   grain edits targeted). `run_engine` appears **~30× in yknr, ~33× in sftfcs** (per-tile/per-pass).
   - **ma1co does NOT document the engine** — `sadis.py` marks `run_engine` (0x0009) as *"local, not in ma1co."* So the
     engine command/opcode semantics are **not available from the best community source**, nor observable (DSP SRAM
     unreadable, C-DSP-020), nor emulated (saemu doesn't execute it). **This is the real grain wall.**

## What this fixes about the grain docs
- The grain-injection work (op5=st / two-bank / g14 anomaly / "VLIW bundle" edits) was operating on **layer 2 (the
  engine command stream)** — the correct region, NOT a misdecode of scalar. The camera effects (zeroing stores → dark
  luma) were real edits to the engine stream.
- "We disassembled a lot of VLIW" = mostly **layer 1 scalar** (readable) + the **layer-2 stream** (edited but its
  opcode semantics never pinned). The wall is layer 2's **undocumented engine**, not a lack of disassembly.
- So: **why the wall stands** = the per-pixel engine's command semantics are undocumented (not even ma1co),
  unobservable (SRAM closed), and un-emulated — authoring it blind is the blocker; scalar GP edits don't reach it
  (E-0086, under the layer-2 model).

## The new angle (producer-side) — OPEN, being pursued
The scalar (layer 1, readable/decompilable) **BUILDS the engine command table** before each `run_engine`. Reverse the
**construction code** (the instructions that populate `r0`'s table at the 30 yknr / 33 sftfcs sites) to recover the
command FORMAT from the producer side — and look for an **injectable field** (a dither/seed/noise-source selector, or
an unused slot) that feeds the engine a per-pixel/per-frame entropy **without authoring engine microcode**. That would
be a parameter-level grain injection = a way *into* the engine, bypassing the authoring wall. Cross-ref
`engine-command-table.md` (T-1 partial decode). Camera-independent; uses `sadis.py` + gateway model.

Cross-refs: `grain-roadmap.md`, `engine-command-table.md`, `04-dsp-modules.md`, `grain-via-effects.md`
(sftfcs host assessment — its "VLIW per-pixel point" = this layer-2 engine). Tools: `sonygen/isa/sadis.py`,
`sonygen/ma1co-SA-DSP/` (Ghidra plugin).
