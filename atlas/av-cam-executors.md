# av-cam ISP executors + 3A — #2 white-spot pass (2026-10-17)

Fills the remaining av-cam white spots (owner task #2): **A2 tone/sharpen executor, C1 JPEG-encode, A3 3A**.
Method: 3 parallel sonnet RE agents on `av-cam-full.bin` + a live RAM dump (`av-cam-live.bin`). All addresses are VA
(file off = VA − 0xc3441000). Companion to `capture-orchestrator.md`.

## A2 — tone + sharpen executors (BOTH = fixed-function HW ISP blocks, ARM-programmed via MMIO + job shadow)
- **Tone:** already done — HW LUT `0xf4015300`, built by `tone_lut_build` 0xc3717996 (C-ISP-001, C-TONE-001..030).
- **Sharpen (NEW) = HW YAP block (Y APerture) at MMIO `0xf4015c00..0xf4015cdf`.** ARM writes it directly and
  mirrors into a RAM shadow image that flows with the job (same pattern as tone's `0xc3cbe0a4`).
  - Register map: `c00` 4 enable flags; `c04` 16-bit; `c10/c14/c18` = apgain/vapgain/hapgain; `c30..c4c` = 8 coring
    (v/h p0/p1/p2/aplk); `c50..c6c` mask; `c70..c7c`; `c80..cdc` zoukou/acm/yld/lpf.
  - Still path: `0xc36f7d3e` → `0xc3515a84` (c00/c04); **job_apc_gain_stl** `0xc3515334` (c10/14/18); **job_apc_coring_stl**
    `0xc35142ce` (c30..4c). ModeMain: `job_YC_ModeMain` 0xc373fffa → `0xc3512448(T_YapRam)`.
  - Caps (code clamps): apgain ≤ `0x1FF`, v/h gain ≤ `0x10`, coring ≤ `0x1FF`. `apgain = apgain·ladder >> 6`;
    ladder from byte tables `0xc3accfdc/0xc3accffc`, selector `[ctx+0x120+0x16/0x17]`.
  - **Apacon** (`0xc38a5958`+, IDs 0x78b0..0x78bf) is a pure COEFF-COMPUTE (12-bit ×3 groups + gain, clamp 0xFFF);
    it writes a software style param-DB (scratch `0xc3c50468` → DB via setters `0xc3732fdc`/`0xc3733012`), **not MMIO**.
    The static link Apacon-coeffs → YAP MMIO is NOT proven; they are separate lanes.
  - Shadow image: `base+0x1424+0x240`, base from handle id `0x2010` (`0xc37453ca`). Snapshot-back `0xc373ee00`.
  - Tuning (ladders, T_YapRam) is loaded at runtime from `/mnt/YC_FILE%04x.dat` (`0xc3740934`) → was runtime-only;
    the live dump confirms these addresses are **zero when the camera is idle** (populated only during capture).
- **Ceiling:** executor is HW (same opacity as tone/develop); the ARM programming side is fully mapped.

## C1 — JPEG encode = **DSP (SA, Zima core), program `sa_jpeg_enc_1unit.bin`** (not HW MMIO, not ARM)
- Chain: `Stage_DistEncodeFULL` `0xc37ed25c` → `DistEncode_Base` `0xc37ed060` (msg `0x560013`, task tsk_sdf_rec_00)
  → SDF `WrapJpegTanzEncode::MainProcess` `0xc386c4d8` → `ddl_jpeg_tanz_encode` `0xc3473cf6` → `dgi_jpeg_tanz_encode`
  `0xc352b9ec` (builds SA cmd, **FuncCode 0xE0** = encoder; 0xE8 = decoder) → `ddl_saJpegCalcStart` `0xc37732f0`
  → `0xc35af1f4(mailbox 0x101, cmd, 0x18)`.
- FuncCode 0xE0/0xE8 match `sa_jpeg_enc_1unit.bin` / `sa_jpeg_dec_1unit.bin` header byte[9]. ARM only does param
  validation, quant-table calc (`dgi_jpeg_qtable_*`), Huffman tables (`0xc398ba40`), marker templates (SOF `0xc398bc00`,
  SOS `0xc398bc20`).
- The old anchor "HW JPEG enc 0xc35dcxxx" is WRONG — that is `dgi_jpeg_common` trace code (no MMIO).
- **Ceiling:** the DCT/quant/Huffman is in `sa_jpeg_enc_1unit.bin` (VLIW, 17412 B) — needs VLIW disasm; the mailbox
  0x101 SA-server receiver is not in av-cam (cross-processor).

## A3 — 3A (AE/AWB/AF): **decision logic is cross-LSI (CAIF "CA" side); av-cam only APPLIES results**
- No "3A loop" and no metering/WB-calc/AF-peak algorithm in av-cam. Event-driven per-VD via `Sync/SyncTask.cpp`
  (`VD_Drive` 0xc35b8640), per-mode `Sync/Sequence_*.cpp`. The EN↔CA boundary = CAIF (`Stage_CaComm.cpp`,
  `CaifCom_Cap_RcvEvent` 0xc3467c26): av-cam = "EN", receives 3A results from "CA".
- **Statistics (HW):** IDT_OPD (kernel `idt_cam.bin`), outputs `out_opd_cc`/`out_opd_ec`; `DevOPDAfterCap` 0xc3683f7c.
- **AE apply (fully read):** `0xc37d5a6e` computes `svd=shut·mult−1` → imager vtable `CAM_IMAGER` (vtable 0xc3a455b4):
  SetExposure `0xc34c250e` (shadow regs 0xc3ca5036..66), gain `0xc34c27c6`→`0xc35c66f0` (shadow 0xc3ca508c/90) →
  sensor via P2S/SIF. `shut` arrives in `ctx+0x180+0x1c` from CA (`SyncModuleDataAll`) — not computed in av-cam.
- **AWB apply (fully read):** gains land in **PBE-H** (pre-demosaic): stage `Camera::Capture::PBEH` 0xc388a454 →
  `0xc38faa58` writes `wb_r`=[10:0]@SA-param `+0x64`, `wb_b`=[10:0]@`+0x68` (src `P+0x1e48/+0x1e4a`, defaults R=0x1d8
  B=0x1f1 if <0x81); executor = SA `sa_pbe_work`. Who fills `P+0x1e48` (the computed WB) = CA side, not found.
- **AF:** OPD stats config + scan sequences (`Sequence_ScanAF240` etc.) in av-cam; peak-search + lens commands = CA.
- **Ceiling:** 3A decisions live on the other LSI (CA) across CAIF — opaque from av-cam. Application path fully mapped.
- Live dump confirms AE active state `0xc3b9c9f8` (0x0103 patterns) and exposure shadow `0xc3ca5036` hold real values.

## Live RAM dump (new capability + artifact)
- `work/memdump/av-cam-live.bin` (13.6 MB, VA base 0xc3441000, 0xc3441000..0xc4141000), md5 `8fd2e139…`. Pulled via
  `pmca` service-shell `readMemory` (sudo -A + `askpass.sh` GUI; camera auto-switched mass-storage→service).
- Captures genuine runtime state for **persistent** regions (AE state, exposure/gain shadows, colour RAM copies
  `0xc3ac3494`+). But **entering service mode partially re-inits the capture app**: the stage-registry interface
  object `0xc34414d0` was FILLED when probed live (~70 pointers into DRAM heap `0xbf2fxxxx` = the registered C++
  stage objects) but reads back flash-like (empty) in the bulk dump taken in a fresh service session. YAP tuning
  tables are zero when idle (populated only mid-capture).
- ⇒ **Orchestrator runtime stage-order (capture-orchestrator.md §7) stays runtime-opaque:** the registry lives in
  DRAM `0xbf2fxxxx` and is cleared on service-mode entry; a reliable capture would need an in-operation dump, not the
  service shell. The transient probe did confirm the registry = ~70 DRAM stage-object pointers hung off `0xc34414d0`.
- Camera USB wedges after a large dump (MSC bulk write `GenericUsbException`) → needs a physical replug before the
  next live read.

## Net for #2
All three white spots are now classified to their exact static ceiling:
| area | executor | ceiling |
|---|---|---|
| A2 tone | HW LUT 0xf4015300 | HW-opaque; ARM side mapped |
| A2 sharpen | **HW YAP 0xf4015c00** | HW-opaque; ARM side + caps mapped |
| #3 3D colour LUT | **HW CamCore DEV: SRAM 0xf4017000, ctrl 0xf4015d00, writer 0xc34b4224** (C-COL-046b) | HW-opaque; full ARM load path + word format mapped |
| C1 JPEG | **DSP sa_jpeg_enc_1unit (FuncCode 0xE0, mailbox 0x101)** | VLIW kernel + SA server cross-processor |
| A3 3A | **CA LSI (cross-CAIF)**; av-cam applies (AE→imager, AWB→PBE-H) | decision logic off-chip |

**ISP executor family (all fixed-function HW at MMIO 0xf401xxxx, ARM-programmed + RAM shadow):** tone LUT `0xf4015300`,
YAP sharpen `0xf4015c00`, 3D colour LUT CamCore SRAM `0xf4017000` (ctrl `0xf4015d00`). DSP (SA) does develop/resize
(SPICA), PBE, JPEG-encode.

## Develop sub-stage executor map (A1 — complete, 2026-10-17)
`job_YC_ModeMain` (0xc373fffa, from 0xc350acd0; runs only when `Common[4]==0xb`) drives the develop blocks. Each block
resolves to a **HW CamCore ISP block (MMIO 0xf40xxxxx) or ARM — NONE go to DSP** (BL reachability depth 6 hit no
ExecuteOpenMSG from any setter/apply). Sync-apply path = `SetSyncDevelopParam` 0xc346c5f2.

| block | setter | HW executor (MMIO) | note |
|---|---|---|---|
| Dg (digital gain) | 0xc350b278 | **0xf4003200** (11×8B tbl, ctl f4003258, latch f4000100) | |
| Shd (shading) | 0xc36a54d8 | **0xf4003900/3940/3b00/3b80** | |
| Cas | 0xc3697c64 | **0xf4012000/2040/2080** (writer 0xc35938f2, 42×s16) | tables all-zero on 3N ⇒ pass-through |
| Nr | 0xc36c1fe2 | **0xf4014300/4340/4380/4a80** | (chroma NR; luma NR = DSP yknr) |
| Itp (demosaic) | 0xc350c150 | **0xf4014500/4540/4700/4740/4780/4800** | the full-res develop luma/interp |
| Pfr | 0xc350fb62 | **0xf4015000/5040/5080** (writer 0xc359419c) | purple-fringe? (hyp) |
| Yap (sharpen) | 0xc3512448 | 0xf4015c00 (known) | |
| Mov (movie/live) | 0xc350f372 | **0xf401c000** (RawNr f401c080, ITP f401c200/240) | movie path only |
| Clp | 0xc350bb0a | **ARM only** (black/OPB clamp, no MMIO in tree) | |
| Adj | 0xc3834b50 | **ARM only** (factory adjust sequences) | |
| Lga, Gra | 0xc350ed1e / 0xc350bc14 | **no-op** (`bx lr`) on 3N | |

### Colour matrix (the film-look 3×3) = HW CamCore DEV **0xf4015500** (NEW lever)
- Writer `0xc3593e0c`: `+0x0c..+0x2c` = 9×s16 3×3 (1.0 = 0x400), `+0/+4/+8` = 3 byte flags. CC chain:
  `SetDevelopParam 0xc3729be8` → `0xc3508ad6` → `0xc35088c0` → `0xc3593e0c`.
- Computed on ARM `0xc372e560`: base 3×3 (default identity `0xc39fdd60`, or `0xc372ab18()+0x22`, or RAM `0xc3ac3204`)
  + WB-derived gains from `[ctx+8]+0x140+0x40/44` (clamp 0x7ff → reciprocal 0x400000/g). Live value = **identity**
  (`0xc3c156da`, 0x400 diagonal) — so the base matrix drives the look; WB gains modulate.
- Full CC HW-block chain (ARM-written, order): `0xf4014200/4400/4900`, `0xf4015100`, **`0xf4015500` (matrix)**,
  `0xf4015600/5640/5680/56c0`, `0xf4015900/5940`, `0xf4015e00/5e40`, **3D-LUT `0xf4017000`** (C-COL-046b). The
  f4015100/5600/5900/5e00 blocks look clip/chroma/hue-like (layout only, unconfirmed).
- Movie matrix path: `0xc3592ba4` → `0xf401c308` (9×s13).
- **New colour lever candidate:** the base 3×3 at RAM `0xc3ac3204` / flash default `0xc39fdd60` — a Backup/RAM edit
  could shift the film-look matrix (parallel to the 3D-LUT `0x30004` lever, C-COL-046). Needs a runtime test (E-0067 style).

### New MMIO bases catalogued (beyond tone/YAP/3D-LUT)
latch `0xf4000100`; engine-ctl `0xf4000800`(ARC)/`0900`(CAS)/`0a00`(NR)/`0b00`(SIG)/`0c00`(DEV)/`0d00`(DEV-PFR)/`1000-1200`(MOV);
params per table above; CC/colour `0xf40142/44/49/51/55/56/59/5e xx`; movie `0xf401cxxx`.
**⇒ The entire still develop pipeline is a chain of HW CamCore ISP blocks (MMIO 0xf40xxxxx) + a few ARM-only/no-op
blocks; DSP handles only SPICA-resize / PBE-WB / yknr-lumaNR / JPEG. This is the COMPLETE still-pipeline executor map.**
Cross-refs: `02-capture-pipeline.md` (C-ISP-001/007, C-PIPE-*), `04-dsp-modules.md`, `capture-orchestrator.md`.
