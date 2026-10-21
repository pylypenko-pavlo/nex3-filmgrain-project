# Full-atlas build — systematic disassembly of NEX-3 internals (2026-10-17, in progress)

Goal (owner): disassemble ALL unexplored NEX-3 internals with DeepSeek, build the complete atlas. Method: per
area → extract structure/disasm → DeepSeek-refine → document into the right atlas page. Tracking below.

## Areas & status
| area | what | status |
|---|---|---|
| **B1 apollo4** | develop FRONT-END (raw→develop master) | ✅ role (DeepSeek) |
| B2 star | SCALER/resize (polyphase) | ✅ role |
| B3 tbox | Miniature effect | ✅ role |
| B4 dfdet | defect DETECTION | ✅ role |
| B5 bdro2_bdex | Bayer defect REPAIR | ✅ role |
| B6 kknr/defect/frc2 | skin-NR / defect-correct / chroma-fix | ✅ roles |
| **A1 av-cam develop/color** | colour-matrix application (film look) | ✅ DONE: full develop sub-stage HW map; colour matrix = HW CamCore 0xf4015500 (`av-cam-executors.md`) |
| A2 av-cam tone/sharpen | tone_lut_build 0x2d6996 → HW LUT 0xf4015300; Apacon 0x78b0 | ☐ |
| A-dispatch | capture stage-dispatch order (develop/SPICA 29x confirmed) | ✅ C-PIPE-030: C++ Stage registry, class-driven; runtime ORDER = IDA-gated (`capture-orchestrator.md`) |
| **A-fullimage** | av-cam.bin was only 6.55/15 MB; carved `av-cam-full.bin` | ✅ C-PIPE-029 — whole VA space now readable (0xc3bxxxxx, colour tables, RTTI) |
| A3 av-cam AWB/exposure/3A | auto algorithms | ☐ |
| C1 HW JPEG enc | 0xc35dcxxx MMIO (Q-4) | ☐ |
| D codecs/boot/idt/ODL | jpeg/avce/avcd/aac/zima; boot chain; idt_cam 3A; libObj | ☐ (low priority) |

Method note: VLIW modules via `vliw_dis.py` + bundle scans (port24=luma/port31=chroma reads, clamp→store
outputs = plane finalize). av-cam ARM via **capstone** (CS_ARCH_ARM/CS_MODE_THUMB, installed in pmca venv; VA=file+0xc3441000) — tone_lut_build @0xc3717996 confirmed readable. DeepSeek (`dsq.py`) for role synthesis
and semantics inference on extracted data (never raw — it hallucinates without bytes). Camera/runtime facts stay
open. Results fold into 04-dsp-modules (modules), 02-capture-pipeline (av-cam), 01-system-map.


## FINAL STATE (2026-10-17 ~01:15, autonomous session) — static ceiling reached

Done this session: module ROLES + still execution order (B, DeepSeek); av-cam ARM UNBLOCKED (capstone); capture-
dispatch confirmed (develop/SPICA 29×); full pipeline OVERVIEW capstone (02-capture-pipeline); module delivery-byte
MAP (flash any module, 05); T-1 command-table DECODED; red-team of negatives (07 §1d, reopened N1/N4/N5); grain
re-tests prepped (grain-roadmap).

Honest ceiling (why not more autonomously):
- **av-cam deep-RE (A1-A3, C1): tooling-gated.** capstone gives RAW disasm only; the stage dispatch + colour/tone
  application need IDA-level analysis (C++ vtables/deep refs). Specific functions can be hand-RE'd (slow) — e.g.
  Q-14's colour-slot writer is localized to the fn @0xc3a69e78 referencing 0xc3bad724 — but it's per-function slog.
- **grain injection (op5/two-bank): camera-gated.** The tracer can't pin the op semantics statically (g14-anomaly);
  the camera probes in 07 §1d resolve it.
- **HW blocks (JPEG enc, tone LUT, ISP arithmetic): opaque** (register interfaces only).
- **codecs/boot/idt (D): low value** for the stills/grain goal.

⇒ The atlas is as complete as static tooling allows; the remaining map is **camera-gated (grain) or IDA-gated
(av-cam deep) or HW-opaque**. Next real progress: tomorrow's camera session (grain re-tests + SPICA/yknr probes).

## UPDATE 2026-10-17 (orchestrator/router layer — "no white spots" pass)
Closed the previously-undisassembled **routers/orchestrators** layer (owner: "разобрали блоки, но не роутеры"):
- **Tooling unlock (C-PIPE-029):** `av-cam.bin` was only the first 6.55 MB of the 15 MB image → carved
  **`av-cam-full.bin`** (offset 0x8e00, VA base 0xc3441000). The whole address space (ARM region 0xc3bxxxxx, C++
  Stage registry/RTTI, colour tables) is now readable. This answers "why the data segment was missing" — it was
  never carved.
- **Orchestrator decoded (C-PIPE-030, `capture-orchestrator.md`):** the capture dispatch = a C++
  `Camera::Capture::Stage_*` registry (78 {Thumb dispatcher, ARM config} records at 0xc362997c), selected per step by
  the **picture-effect class `ctx[0x23]`**, invoked via a C++ interface singleton (0xc34414d0). 4-round DeepSeek
  decode. The table is statically unreferenced by design (pointer only in the runtime object). "What loads when" =
  picture-effect-class-driven stage selection, fully enumerated.
- **Static ceiling here:** only the runtime stage-invocation ORDER (C++ vtable walk per shot) is not statically
  linearizable — genuinely IDA/trace-gated, not a gap in coverage.

### QUEUED (owner-agreed 2026-10-17): order = do #1 now, #2 & #3 next
1. **[DONE 2026-10-17] Runtime-reach of the stage registry** — RESOLVED to its exact boundary (`capture-orchestrator.md`
   §5): interface `0xc34414d0` = **BSS/runtime-filled** (not a static vtable); **cross-core RULED OUT** (table +
   interface in no other partition); installer chain = header→`0xc3441050`→`0xc34412ac` = CRT/HW init (.data reloc +
   MMIO), stage install is deeper in the C++ app-init tree; table reached only via loader-relocated .data / C++ ctor —
   **no static code immediate forms it** (0 word, 0 movw/movt for VA or offset). Remaining sub-unknown (which ctor) =
   IDA/trace-gated. Answer: **object-held in av-cam's own BSS.**
2. **[DONE 2026-10-17] Remaining av-cam white spots** (`av-cam-executors.md`, 3 parallel agents + live dump):
   A2 sharpen = **HW YAP MMIO 0xf4015c00** (tone already = HW LUT 0xf4015300); C1 JPEG = **DSP `sa_jpeg_enc_1unit`**
   (FuncCode 0xE0, mailbox 0x101, not HW/not ARM); A3 3A = **decision logic on CA LSI via CAIF** (av-cam only applies:
   AE→imager vtable, AWB→PBE-H). All classified to exact ceiling. Live dump `work/memdump/av-cam-live.bin` (13.6MB).
3. **[DONE 2026-10-17] Colour consumer (C-COL-046b)** — = **HW CamCore (ISP DEV)**: writer `0xc34b4224` loads the
   3D LUT into HW SRAM `0xf4017000..787f` (8 banks trilinear), ctrl `0xf4015d00..d44`, in Stage_Develop; 2nd path =
   SA/DSP via SetDualRec (codetypes 3/4). SACC (0x1b) is not the applier. `0xc3bad724` was a misread (= debug flag,
   not colour master). Full chain in `av-cam-executors.md` / C-COL-046b. ISP executor map now complete.
