# Pipeline & effects — how a still is made, and where effects actually run

Consolidation of the 2026-10-14 pipeline research (4 fable agents over `av-cam.bin` +
`sabin/`). Answers the owner's question: **what is the full SOOC-JPEG pipeline, and how do the
Picture Effects that have no `sa_*` module work?** Raw per-agent notes:
`~/nex3n-dump/work/pipeline-research/0{1..4}-*.md`.

Scope: NEX-3N fw 1.00 / CXD4132, owner's own hardware, authorized interoperability RE (offline
static analysis only, nothing flashed). av-cam VA base `0xc3441000`; `file_off = VA − 0xc3441000 + 0xd4`.

---

## TL;DR

- **The pipeline is: sensor → IDT/OPD stats → RAW → OB-clamp → defect → develop(colour/tone/chroma)
  → picture-effect → NR → sharpen → resize → DRO/PBE → HW-JPEG.** The heavy per-pixel arithmetic is
  **not** on ARM — it is the **SA-DSP** (modules + the Apollo develop engine) and **fixed-function
  ISP-HW** (tone LUT, matrix, Apacon sharpen). ARM CPU1 (av-cam, Thumb-1) only orchestrates and writes
  parameters. No ARM write ever reaches the JPEG (C-PIPE-001/023).
- **Only TWO Picture Effects are file-loaded SA modules:** Soft Focus (`sa_sftfcs`) and Miniature
  (`sa_tbox`). Everything else is either a **HAPI `Start_*` call with no module** (Retro, Soft
  High-key, Rich-Tone Mono, HDR Painting) or **fixed-function ISP-HW driven by ARM params** (Toy, Pop,
  Posterization ×2, Partial Color ×4, HC Mono). The "complex effect = lots of memory = ideal grain
  host" intuition holds for the module effects **only**; the simple ones have no code to host in.
- **New host found this round:** the develop engine itself = **`sa_apollo4`** (Apollo, codectype 0x01)
  — an always-on, full-frame, programmable SA-DSP module. It joins `{sa_yknr, sa_sftfcs, sa_tbox}` as a
  grain-host candidate. Same hard constraint as all of them: the SA **scalar** core never touches
  pixels (C-DSP-020), so any host is a **VLIW-kernel** job (the wall the 2026-10-14 audit reopened on
  `sa_yknr`), not a scalar loop.

---

## 1. The pipeline, end to end (agent 4)

Ordered still-capture stages, each tagged with the processor that runs it and whether it is
**programmable code** (hookable) or **fixed-function HW** (LUT/param only).

| # | Stage | Does | Executor | Prog / HW | Evidence |
|---|---|---|---|---|---|
| 0 | IDT/OPD | AE/AWB/AF stats, LV sync | `idt_cam.bin` (detect side) | prog (not full-frame pixels) | C-PIPE-008/009 |
| 1 | RAW in | sensor read, OB black clamp (Clp) | Apollo SA-DSP datapath | HW-ish | C-PIPE-006 |
| 2 | Defect | hot/dead-pixel correct | **`sa_defect`** (0x14) | prog SA | C-PIPE-020 |
| 3 | **Develop** | WB → 3×3 slot matrix (linear) → base gamma → contrast/style curve → YCbCr601 → chroma×style → hue/sat → 8-bit | **Apollo = `sa_apollo4`** (0x01) + ISP-HW LUTs | **prog SA** (+HW LUT) | C-PIPE-007/015, C-ISP-003, **new** |
| 3a| Tone/gamma | 96-node HW LUT | fixed-func ISP-HW `0xf4015300` (`tone_lut_build` `0xc3717996`) | HW | C-ISP-001/002 |
| 4 | **Picture effect** | see §2–§3 | per class: SA module / HAPI / ISP-HW | mixed | C-ISP-004/005, §2 |
| 5 | Luma NR | late full-frame luma denoise | **`sa_yknr`** (0x1c) | prog SA (VLIW) | C-PIPE-021/025 |
| 5b| Chroma NR | chroma denoise | **`sa_kknr`** (0x0f) | prog SA | C-ISP-006 |
| 6 | Sharpen (Yap) | edge/coring per ISO/style | fixed-func ISP-HW **Apacon** (regs `0x78bx`, `YC_SetModeDependent_ApaconParam`) | HW | C-ISP-007 **(resolved)** |
| 7 | Shading (Shd) | lens-shading gain | ARM computes (`CalcLensShdGain`), applied in develop datapath | HW apply | C-ISP-008 **(resolved)** |
| 8 | Resize | scale (pre-BDRO) | **`sa_spica`** (0x16) + `spica_*_tap_*` | prog SA | C-PIPE-012 |
| 9 | DRO | 2-pass detail/contrast | **`sa_bdro2_bdex`** (0x10) | prog SA | C-PIPE-011 |
| 10| PBE | noise/detail | **`sa_pbe_work`** | prog SA | C-PIPE-013 |
| 11| Encode | still JPEG | **HW JPEG coder** behind `0xc35dcxxx`, task `tsk46_jpeg`→`0xc347427a` | HW | C-JPEG-001/004, **C-JPEG-005 resolved: `sa_jpeg_enc_*` NOT on stills path** |

Resolved holes this round: develop executor = Apollo SA (C-ISP-003); sharpen = Apacon HW (C-ISP-007);
shading apply site (C-ISP-008); `sa_jpeg_enc_*` has no OPEN/`sa_func_*JPEG*` → not used for stills
(C-JPEG-005). **Still unresolved (static wall):** SA-VLIW-vs-inline-HW split *inside* Apollo per
sub-step; `Stage_CCNR_Enc` executor; exact spatial-stage order; highlight-hold stage.

---

## 2. Effect dispatch — a 5-class pipeline selector, not a 14-way switch (agent 1)

`[ctx+0x23]` (the picture-effect "class" byte) is **0..4** — it selects a pipeline **shape**, not an
executor. ~14 menu effects collapse to **5 classes**. Mechanism:

- **51-entry step-table** at VA `0xc3629a04` (off `0x1e8a04`), pairs `{descriptor 0xc3bf15a8+0x14·k,
  thunk}`. Descriptors at `0xc3bf1xxx` are runtime data (outside the image). Thunks in two clusters:
  early `0xc36283f1…0xc3628b19` (develop/SPICA passes), late `0xc37f1625…0xc37f1b3d` (resize/encode-prep).
- **Every thunk re-reads `[ctx+0x23]`** and branches on `cmp r1,#0..3` (verified: record-1 dispatcher
  `0xc362827e`/`0xc36282ae`; thunks `0xc36283f0`, `0xc37f1624`). Same 5-way switch replicated across all
  51 steps. The class picks the *shape*; the executor is whatever that class's impl invokes.
- **Statically pinned:** **class 2 = Soft Focus** (→ `Stage_SoftFocus` `0xc37ea898` → `sa_sftfcs` OPEN
  at `0xc35a46bc`, `movs r2,#0x18; bl 0xc37551f6`). **class 4 = multi-frame** (HDR Painting →
  `0xc363faa0` → 0x21-way sub-disp `0xc35f8db4` reading `[ctx+0x1c0]`; Rich-Tone Mono, multi-frame).
- **Correction to the atlas:** the old heuristic OPEN micro-addresses (e.g. `0x163604`) don't land on the
  real instruction. True OPEN sites (byte-verified): `sa_sftfcs` `movs r2,#0x18` @ `0xc35a46bc`,
  `sa_tbox` `movs r2,#0x17` @ `0xc35a3830`; both feed `ExecuteOpenMSG 0xc37551f6`.
- **Not resolvable statically:** the effect→class map for classes **0/1/3** — `[ctx+0x23]` is set
  upstream from camprm (C-CTRL-019). Needs a **live camprm dump `0xc3abe32c..0xc3abe370` while toggling
  the Picture-Effect menu**. (One clean no-flash senser session — cheap, worth doing.)

---

## 3. Effect → executor map

Bold = statically pinned in the binary.

| Effect | Executor | Module? | Grain-host? |
|---|---|---|---|
| **Soft Focus** | **`sa_sftfcs` (0x18)**, class 2, OPEN `0xc35a46bc`; Backup `0x3010a` | **yes, redirectable** (file-id 55, byte `0x1BD`, 43 652 B < limit) | **only redirectable one** — but per-pixel apply is VLIW (same wall as `sa_yknr`) |
| Miniature | `sa_tbox` (0x17), OPEN `0xc35a3830`; Backup `0x30109` | yes but **size-disqualified** (77 444 B > write limit) | no (too big to redirect) |
| Retro Photo, Soft High-key | **HAPI `Start_Art_Effect`** `0xc34e62b8` → builder `0xc34e5f40` | **no module** | **no — param-only HAPI job** |
| HDR Painting | **HAPI `Start_HDR`**, class 4 → `0xc35f8db4` | **no module** | **no — param-only HAPI job** |
| Rich-Tone Mono | **HAPI `Start_Richtone_Monochrome`** `0xc34e6ffa`, class 4 multi-frame | **no module** | **no — param-only HAPI job** |
| Off, Toy, Pop, Posterization Color/B&W, Partial Color ×4, HC Mono | **fixed-function ISP/YC** (ARM params only) | **no module, no `Start_*`** | **no — no code host** |

**The six fixed-function effects (agent 3, firmware-proven no code host):**

| Effect | HW stage | Param source |
|---|---|---|
| Toy Camera | radial vignette (SHD multiply) + matrix + tone + chroma | `CalcLensShdGainToy` `0xc368b408` → Backup `0x30040+0xA2` (32×u16, edge≈−3.1 EV) |
| Pop Color | slot matrix + chroma/sat | matrix `0x30001/08 +0x48+18·slot`; chroma ×(1+0.13·Sat) |
| Posterization Color | tone HW LUT, stepped per R,G,B | `tone_lut_build 0xc3717996` → 96 nodes, k16 threshold |
| Posterization B&W | tone LUT + chroma→0 | as above + mono |
| Partial Color ×4 | hue-keyed chroma (keep one hue) | hue/chroma consumer; **exact key block not located** (open item) |
| HC Mono | steep tone LUT + chroma→0 | `tone_lut_build`, k16; "grain" = sensor noise amplified by the curve (C-PIPE-004), not a generator |

Three independent confirmations the six have no host: (1) no SA OPEN for any of them (only sftfcs/tbox
have OPEN sites); (2) **no string anchor** anywhere in `av-cam.bin` for Toy/Pop/Posterization/Partial/HC
— only `Art_Effect`/`Richtone` strings exist; (3) class-3 dispatch `0xc37df2e8` = param-marshal only
(two `bl` + job-descriptor fill, no OPEN, no pixel loop). Killed false lead: `ExtractColor`/`extract_color`
belong to **FC subject-tracking** (`fc_alg_extract_color.cpp`), **not** Partial Color.

**The four HAPI art filters (agent 2 — the key "hidden host?" question, answered NO):** Retro, Soft
High-key, Rich-Tone Mono, HDR Painting run through a **uniform HAPI imaging-filter interface**, not a
module and not a programmable engine. Decisive new evidence: the whole `Start_*` family shares one
signature — `Start_X(PRM_REQ_FILTER_X*, Image*, Image*, Image*, uint, uint)` — and **Soft Focus and
Miniature use the same interface**. So "HAPI filter" is *not* a different executor from the module
effects; the split is on the far side: SF's handler does a real DSP OPEN (`movs r2,#0x18; bl 0xc37551f6`
→ `ExecuteOpenMSG 0xc375526c` = `sa_sftfcs`), the four art filters do **not**. Their bodies only marshal
`PRM_REQ_FILTER_*` params + 3 `Image*` buffers into a job (generic builder `0xc34e5f40`/`0xc34e6c80`,
tag `0x9a`, submit `0xc3660660` cmd `0x81`), log, free — **no `ExecuteOpenMSG`, no codectype, no
`sa_func_*`, no `0xf4xxxxxx` ISP-register write**; the sub-effect is just an enum byte in the PRM struct
(range-checked 1..3). Corroborated by C-MOD-003 (20 OPEN-sites, no art-effect codectype) and C-MOD-005
(no ART_EFFECT/RICHTONE/HDR in the `sa_func_*` list). **The owner's "complex effect = room to host
grain" intuition inverts here:** the pipeline room is real but sits on the far side of a param-only
request, in fixed HW/VLIW that is not addressable, redirectable, or programmable from anything we
control. These four are a step *down* from Soft Focus — they remove the one lever (a redirectable module
file) without adding another.

---

## 4. The grain-injection surface, after this round

Programmable (hookable) pixel stages — the ONLY candidate grain hosts:

| Host | When it runs | Redirectable file? | Injection point | Verdict |
|---|---|---|---|---|
| **`sa_yknr`** | every frame (late luma NR) | yes (byte `0x597`, proven) | scalar trampoline proven (pixel-write ok); grain = VLIW output block `0xcc38..0xce80` **(audit reopened — never probed)** | **primary — pending the reopened VLIW probe** |
| **`sa_apollo4`** (Apollo develop) | **every frame, full-frame** | yes (has OPEN/`sa_func_*`) | VLIW kernel (develop arithmetic) | **new candidate — biggest always-on surface; VLIW wall unexplored** |
| **`sa_sftfcs`** (Soft Focus) | **only when SF selected** (class 2) | **yes** (file-id 55) | VLIW apply (3×3+5×5×2) | **best trigger-isolated host** — "select SF → grain"; VLIW wall same as yknr |
| `sa_tbox` (Miniature) | when Mini selected | **no** (77 444 B > limit) | VLIW | out (size) |
| `sa_kknr/bdro2/pbe/spica/star` | various | mostly yes | VLIW/SA | secondary, unexplored |
| ARM `YCC_FULL` point | post-develop | n/a | one ARM per-pixel write (C-PIPE-024) | known-hard (ARM path closed C-PIPE-023) |

**The through-line:** every real host converges on the **same VLIW-injection question**. The simple
effects were a dead end (no code). The win from the effects angle is **not a new mechanism** but a
**trigger**: Soft Focus = "one effect = grain, normal capture untouched." The new structural prize is
**Apollo** (always-on, full-frame develop) — if the VLIW route opens, Apollo hosts grain on every shot
without an effect selection. Both ride on the audit's reopened VLIW output probe (`sa_yknr`
`0xcc38..0xce80`) being the thing to settle next.

---

## 5. Open items (ranked)

1. **Settle the VLIW output route** (`sa_yknr` `0xcc38..0xce80`) — the 2026-10-14 audit's reopened
   probe. Gates `sa_yknr`, `sa_apollo4`, AND `sa_sftfcs` at once (all VLIW). Two built probes ready.
2. **Live camprm dump** `0xc3abe32c..0xc3abe370` while toggling the Picture-Effect menu → closes the
   effect→class (0/1/3) map. One no-flash senser session.
3. ~~Agent 2 (HAPI filters) — hidden baked-DSP host?~~ **CLOSED: no.** Art_Effect/HDR/Rich-Tone are
   param-only HAPI jobs, no module, no uploaded program, no code host (see §3).
4. Apollo internals — SA-VLIW vs inline-HW split per develop sub-step (static wall; needs on-camera).
5. Partial Color chroma-key param block (minor).

---

*Sources: `~/nex3n-dump/work/pipeline-research/01-effect-dispatch.md` (dispatch),
`03-isp-param-effects.md` (fixed-function six), `04-pipeline-map.md` (stage map); `02-hapi-filters.md`
pending. Cross-ref: `grain-via-effects.md`, `audit-2026-10-14.md`, `02-capture-pipeline.md`,
`grain-angles-overview.md`.*
