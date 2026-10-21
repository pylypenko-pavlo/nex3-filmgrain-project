# NEX-3N firmware atlas — index and schema

Start with the root `../README.md`, then `START-HERE.md`.

Single source of truth for what is known about the NEX-3N (fw 1.00, CXD4132) image pipeline
and firmware. Written for machines first (agents grep by ID), humans second (Mermaid diagrams).
Older notes in `../notes/` and the WorkPersonal `reference/nex3n-*.md` files (author's private trees, not in this repo) are the archive;
the atlas cites them, it does not copy them.

## Pages

| file | scope |
|---|---|
| `01-system-map.md` | chips/cores, partitions, files, who loads whom |
| `02-capture-pipeline.md` | path of a still frame: sensor → ISP → DSP stages → encode → card |
| `capture-orchestrator.md` | the stage router: C++ `Camera::Capture::Stage_*` registry, picture-effect-class dispatch, `av-cam-full.bin` unlock (C-PIPE-029/030) |
| `av-cam-executors.md` | #2 white spots: sharpen=HW YAP `0xf4015c00`, JPEG=DSP `sa_jpeg_enc_1unit`, 3A=cross-LSI(CAIF); live RAM dump |
| `sa-dsp-isa.md` | SA-DSP = 16-bit scalar RISC (ma1co ISA, `sadis.py`) + undocumented `run_engine` coprocessor = the grain wall |
| `grain-sftfcs-confirmed.md` | sftfcs: chan-3 is the CHROMA output, not luma; the injection plan is blocked (corrected). Closed route, kept for the module map. |
| `03-control-flow.md` | how parameters travel: menu → Backup → av-cam → descriptors → ISP/DSP |
| `04-dsp-modules.md` | catalogue of every `sa_*.bin` and every `idt_cam` overlay |
| `05-delivery-and-safety.md` | what can be written where, how to roll back, tools |
| `06-experiment-log.md` | every on-camera experiment, E-IDs |
| `07-open-questions.md` | open questions ranked, which experiment closes each; decision tree |
| `_extract/` | raw per-source extractions (working material, not authoritative) |

### Grain, DSP-side route (CLOSED 2026-10-19, hardware-blocked; kept for the engine findings)
| file | scope |
|---|---|
| `grain-roadmap.md` | the historical end-to-end plan of the closed route: the pipeline split (PBE=chroma / yknr=luma), ordered next steps |
| `pbe-engine-map.md` | PBE (`sa_pbe_work`) = CHROMA processor; full VLIW map, chan3=chroma, luma passthrough |
| `luma-stage-yknr.md` | YKNR (`sa_yknr`) = LUMA processor; chan18=luma output; verification module built |
| `grain-chroma-solution.md` | chroma-grain design (PBE chan3 + per-frame-seed/luma-LSB-hash noise) |
| `engine-command-table.md` / `grain-injection-design.md` | engine config/OUT-DMA; the per-frame SEED slot + noise-staging blockers |

### Grain, the route that shipped (Linux LD_PRELOAD shim)
| file | scope |
|---|---|
| `../code/grain-shim/` | the shim, codec, tools |
| `grain-linux-*` | stage runbooks in order, start at `START-HERE.md` |

## Claim record (the unit of the atlas)

```
### C-<AREA>-<NNN>: <one-line claim, present tense, specific>
- status: verified-hw | verified-code | hypothesis | refuted | unknown
- evidence: <file + address/offset, dump name, experiment E-ID, measurement>
- source: <note path and section the claim came from>
- date: YYYY-MM-DD (when established or last re-checked)
- relates: <other claim IDs: supports / conflicts / supersedes>
- scope: nex3n-fw1.00 | CXD4132 | SA-platform | unknown
```

Scope meaning (field `scope`, added 2026-10-09):
- `nex3n-fw1.00` — shown only for this body and firmware (NEX-3N, fw 1.00, region CX76201_CE). **Default.**
- `CXD4132` — holds for the chip generation: the same bytes/code were checked in another CXD4132 body
  (NEX-6 v1.03 tree `~/nex3n-dump/sonygen/sabin_nex6`, NEX-F3 v1.01; author's private trees, not in this repo).
- `SA-platform` — holds across SA-DSP generations: checked against at least one CXD90014 body
  (A7 II `~/nex3n-dump/sonygen/sabin_7M2V401`, a6000 `sabin_6000V321`, Backup dumps `sonygen/bk_6000.txt`, `bk_7m2.txt`; author's private trees, not in this repo)
  and, where stated, CXD90045 (`sabin_7M3V401`, `sabin_6400V200`).
- `unknown` — the record is about another body or the comparison is not possible.

Status meaning:
- `verified-hw` — observed on the camera (photo, live memory read, flash result).
- `verified-code` — read directly in code/data (disassembly, table decode), not run.
- `hypothesis` — inferred, plausible, not checked.
- `refuted` — checked and false; keep the record, say what replaced it.
- `unknown` — question recorded as a placeholder.

Areas: `SYS` cores/chips · `PART` partitions/files · `BOOT` load chain · `MEM` memory map, buffers ·
`PIPE` capture stages · `CTRL` sequencer/dispatch/params path · `ISP` fixed-function blocks ·
`DSP` SA-DSP ISA/engine · `MOD` SA modules · `IDT` idt_cam overlays · `BK` Backup store ·
`COL` colour · `TONE` tone curves · `NR` noise/sharpening · `FX` picture effects/styles ·
`JPEG` encode · `LNX` Linux userland · `DLV` delivery/flashing · `SAFE` safety/recovery · `TOOL` tooling.

## Experiment record

```
### E-<NNNN>: <short name>  (YYYY-MM-DD)
- image: <file>, md5 <...>   | or: Backup write <block>, | or: live memory op
- change: <what exactly differs from baseline>
- observed: <what the camera did, verbatim from the session where possible>
- conclusion: <what it proves>  confidence: high | medium | low
- caveats: <why the conclusion may be wrong>
- claims: <C-IDs created/updated>
```

## Rules
- Every claim has one ID forever; corrections change `status` and add `relates: supersedes`.
- An `unknown` placeholder that is later answered is closed with `status: refuted` (the statement "this is
  not known" no longer holds) and `relates: answered by <ID>`; its evidence keeps the old search record.
- `scope` defaults to `nex3n-fw1.00`. A wider scope needs evidence named in `evidence` (byte-identical file,
  identical table bytes, or the same code read in the other body's dump). A record without a `scope` line is
  read as `nex3n-fw1.00`. Anything published outside this repo inherits the scope of the claims it rests on.
- There is no separate gap-plan page: the ranked table in `07-open-questions.md` §2 is the plan
  (writing a dedicated plan page was stopped by a safety filter on 2026-10-09 and is not retried). Extract-local IDs (`F-*`, `G-MOD-*` in `_extract/G-*`, `H-*`, `R` items)
  are temporary and mapped to final IDs in the trace tables (07 §6). Note: `_extract/G-q2-module-resolver.md`
  uses `G-MOD-nnn` as temporary claim IDs.
- No claim without `evidence` + `source`; if the evidence is "a note said so", status is at most `hypothesis`.
- Addresses: av-cam VA (base `0xc3441000`) unless prefixed; idt_cam offsets are file offsets inside the
  module (inner p3 offset `0x980e00`); say which.
