# Extract C: Backup store, colour, tone, NR/sharpness/vignette, effects/styles, control path, ISP-vs-DSP split

Working material, NOT authoritative. Extracted from notes only; nothing here was re-verified on the camera or in firmware by the extractor.
Schema: `atlas/00-index.md`. Claim IDs are temporary (`C-<AREA>-<NNN>`), to be renumbered when merged into the atlas.

Status rule used (as requested): the status reflects what the source note itself says about how the fact was obtained.
- verified-hw = the note says it was observed on the camera (frames, RAW+JPEG pair, flash read-back, live write).
- verified-code = the note says it was read in code/data (disassembly, table decode, bytes of `Backup_post-revert.bin`), not run.
- hypothesis = plan, model, or not checked. The simulator's empirical models count as hypothesis.
- Per `00-index.md` rules, even "verified" labels here rest on a note; the atlas editor should keep that in mind.

Source aliases (all `ref/` = `~/Library/Mobile Documents/com~apple~CloudDocs/WorkPersonal/reference/`):
- BP = ref/nex3n-backup-params.md (04-05.10.2026)
- HT = ref/nex3n-hue-tables.md (05.10)
- TC = ref/nex3n-tone-curve.md (05.10)
- V6 = ref/nex3n-colour-v6.md (05.10)
- SIM = ref/nex3n-simulator.md (05.10)
- HS = ref/nex3n-hidden-styles.md (06.10)
- HSR = ref/nex3n-hidden-styles-render.md (06.10)
- OQ = ref/nex3n-open-questions.md (05.10)
- NE = ref/nex3n-night-extra.md (05->06.10)
- FXP = ref/nex3n-film-effects-plan.md (05.10)
- MOR = ref/nex3n-morning-2026-10-06.md
- SYM = ref/nex3n-symbols-and-names.md (05.10; sections 0-8 read)
- SE = ~/nex3n-research/notes/style-and-effect.md (undated)
- FPP = ~/nex3n-research/notes/film-presets-plan.md (banner dated 07.10)
- RD = ~/nex3n-research/README.md
- REC = WorkPersonal/nex-3n-film-recipes.md (2026-07-09)
- IDX = WorkPersonal/CLAUDE.md index lines for the nex3n-* notes (and MEMORY.md line "nex3n firmware hack status")

Address conventions: av-cam addresses in BP/TC/SYM/OQ/NE are file offsets in `av-cam.bin` (VA = +0xc3441000) unless written as a full 0xc3xxxxxx VA; SE/FPP use full VAs (0xc35.., 0xc36.., 0xc37..). HS addresses are vaddr inside `lib/viewUnified2.so` / libObj.

---

## Section A. Which Backup blocks are safe to write, which are never to be touched

### A1. Written on the camera, camera kept working (verified-hw)
| block | what | evidence/source |
|---|---|---|
| `0x00030001` + mirror `0x00030008` (write both, identical) | colour block: matrices, hue records; looks v1..v5 written many times, byte tests, tag matrices | IDX ("запись в Backup безопасна и проверена"), HT, V6, SIM, MOR header |
| `0x00030106` (single bank) | Apacon sharpness ladder; one experiment 04.10: step 5 80->32 (it lowered Sunset saturation, see C-NR-018) | BP 2.2 |
| p3 av-cam tone region (NOT Backup, raw flash) | k0 replaced by film curve, 38 sectors 8849-8886; read-back md5 matched; camera booted | TC "ЗАПИСАНО в камеру" |

### A2. Designed, byte lists checked against `Backup_post-revert.bin`, NEVER run on the camera (all hypothesis for effect; code-level for layout)
Rule in every plan: read `bk r <id>` first and compare to `<id>_orig.hex`; write both banks where a bank B exists; `bk r` after write must equal written; rollback = original bytes.
| block(s) | change | source |
|---|---|---|
| `0x30010` + `0x300b4`, offset +0x0C | NR-1: 01->00 (drop forced GHNR/GLNR) | BP 1.2, FXP 1 |
| `0x3001b` + `0x300be`, +0xD7 | NR-2: 01->00 (G-NR off above ISO 1600) | BP 1.3, FXP 1 |
| `0x3004a` (one bank), +0xD2/D6/DA | NR-3: close YKNR ISO window (-> 00 00) | BP 1.4 |
| hi_gain tables `0x3011f/0x30120`, `0x30049`, `0x30016/0x300ba`, `0x30017/0x300bb`, `0x3004a` | NR-4: set u16 to 0x10 at selected ISO nodes | BP 1.5, FXP 1 |
| `0x3000c` + `0x300b0`, +0x1C..+0x31 | SH-1: apgain B0 -> 60 (FXP) or 40 (BP) | BP 2.3, FXP 2 |
| `0x3000c/0x300b0` +0xCE..+0xE3 and `0x3000d/0x300b1` +0x5E..+0x73 | SH-2: coring x3 | BP 2.4, FXP 2 |
| `0x30040` (one bank), +0xA2..+0xE1 | PE-1: soft Toy vignette curve | BP 3, FXP 4 |
| `0x3010a` (one bank), ONLY +0x00..+0x08 | Soft Focus level bytes (probe, then Pro-Mist A/B) | FXP 3.4 |
| `0x3007a` (one bank), +0xD7 and indices | tone mode 2 (6 bytes) / mode 1 (96 u16 + flag) | SYM 7.3, 8.2, MOR Session 0 |
| `0x30033` +0x00 | lens shading master gate 01->00: described but not recommended (menu "Shading Comp." safer) | BP 4 |
| `0x30001/08` v6, `v6_phoenixsky` (1 byte `0x163` fa->3a), `v6_kodakwarm` (14 bytes, matrices of slots 1 and 3) | colour variants, not written; do not combine phoenixsky + kodakwarm in one write | V6, NE 2-3, MOR |

### A3. Sub-range prohibitions inside otherwise writable blocks
- `0x0003010a`: touch only +0x00..+0x08. Never +0x09 (forced level), +0x42..+0x47 and +0x84..+0x8B (read by SPICA), never the kernels (shared by 3 levels). DSP limits: each of 4 kernels sums to exactly 256 else DSP error `0xeeee0008/09`; each level byte <=64 and the three level bytes sum <=64 else `0xeeee0004` (FXP appendix; ma1co spec). Source: FXP 0, appendix.
- `0x0003007a`: do not write blind `+0xD2..+0xD6`, `+0xE0..+0xE3`, `+0xE6` (they feed hardware registers, meaning unknown). In mode 2, do not override the base gamma (`+0xD9`, `+0xE7` must stay `FF`): an empty base row makes the capture path fall back to the Backup LUT (probably a dark linear frame). Source: SYM 7.2, NE 1.3.
- `0x0003004c`/YKNR table fields and `0x30024` (KKNR): leave alone (meaning not decoded / skin smoothing). Source: BP 1.1, FXP 0.
- Phoenix/Sunset slot (r4): Q1/Q3/Q5 of r4 contain the marker `80 80 80 80`/zeros; v4+ deliberately do not touch them. Source: HT v4, V6.

### A4. NEVER TOUCH (verbatim from the notes)
- `0x00030002`: white-balance calibration of this unit. (BP, FXP, MOR, RD)
- `0x00bc0000`, `0x00bc0002`, `0x01320000` and everything `0x00bc*`, `0x0132*`: defect-pixel maps. (BP, RD)
- Lens-shading and sensor calibration, everything with attribute 0x0a in `0x0003`: `0x00030036/37/38` (sjob_LightLvAdj, lga_ave_*), `0x00030042/43`, `0x00030051..54`, `0x76..78`, `0x86`, `0x8f`, `0xa0`, `0xae`, `0x0102`, and everything with attributes 0x48/0x68/0xe8/0x60. Attribute 0x0a = "protected from reset" (per-unit data); general tables are 0x08. (BP)
- `0x00030056`: debug block (log switches, forced ISO for NR), read by dozens of modules; only as a last resort. (BP 1.6, FXP 0)
- `0x00030024` KKNR (FXP 0).
- p8 breakage is not recoverable in software: the loader enters the updater only via jumper or a file on p2 (IDX line for nex3n-firmware-hacking.md). Relevant to any p3/p8 flash plan (SAFE area, not this extract's scope).

---

## Section B. Claims

### BK: Backup store

### C-BK-001: Subsystem `0x0003` holds about 180 property blocks that av-cam caches in RAM at boot
- status: verified-code
- evidence: `bk0003_cache_init` 0x1819cc (called from fn_7c18) registers `Backup_reg_cb` for all 180 IDs; ID list at 0x61d1dc, alternate list 0x61d4b0, RAM address list 0x61d784; blocks read with one `Backup_read_multi` at 0x18183e
- source: SYM 0 item 3, SYM 2; RD "Key findings"
- date: 2026-10-05
- relates: C-BK-002, C-BK-004

### C-BK-002: A write to a cached `0x0003` ID is copied into the RAM copy immediately (callback 0x1819a2 = memcpy), so `bk w 00030001` acts from the next frame without reboot
- status: verified-code (the note adds "matches our experience" that colour-block experiments worked at once; no explicit reboot test recorded)
- evidence: callback 0x1819a2; `0x181f4a` re-reads one ID on request; colour RAM copies 0xc3ac2b94 (0x30001) and 0xc3ac4894 (0x30008)
- source: SYM 0 item 3, SYM 2
- date: 2026-10-05
- relates: C-BK-003 (conflicts)

### C-BK-003: After `bk w ... bk s` a reboot (exit from updater) is needed before values take effect
- status: hypothesis
- evidence: stated as a rule in the effects plan ("Значения читаются при старте"); not tested separately; conflicts with C-BK-002
- source: FXP section 0 "Ограничения"
- date: 2026-10-05
- relates: conflicts C-BK-002

### C-BK-004: Many blocks have a twin "bank B" at another ID; both banks are byte-identical in the snapshot; which bank loads is decided by a runtime flag, so both must be written identically
- status: verified-code (twins and equality from bytes; flag location from code)
- evidence: pairs `0x3000c..0x30018 <-> 0x300b0..0x300bc`, `0x3001a/1b <-> 0x300bd/be`, `0x3001e/1f <-> 0x300c1/c2`, `0x30027..30 <-> 0x300d0..d9`, `0x3003c <-> 0x300e5`, `0x30044..47 <-> 0x300ed..f0`, `0x3011f <-> 0x30120`, `0x30001 <-> 0x30008`; loader uses the alternate list when `[0xc3c9f2dc+0xc]==1 && [0xc3c9f2dc]!=0` (0x1819ee); the flag's value on this unit is unknown
- source: BP "Общие правила записи", SYM 2, FXP 0
- date: 2026-10-05
- relates: C-BK-005, C-BK-006

### C-BK-005: Blocks `0x30033`, `0x30040`, `0x30049`, `0x3004a`, `0x30106`, `0x3007a`, `0x3010a` have no bank B (write one bank)
- status: verified-code
- evidence: not present in the alternate list; `0x3007a` attr 08, one bank
- source: BP general rules, FXP 0, SYM 7.1
- date: 2026-10-05
- relates: C-BK-004

### C-BK-006: `0x30001` and `0x30008` are two separate colour blocks in RAM (not an A/B pair); each per-frame builder picks one by a flag
- status: verified-code
- evidence: builders 0xc60c6, 0xc6430, 0xc7452 choose `0x30008` if `ctx[1]->+0x14 == 1`; 0xc6b12 by `[0xc3cab360+3]`; what flag +0x14 means is unknown; both blocks identical in stock
- source: SYM 2
- date: 2026-10-05
- relates: C-BK-004, C-CTRL-001

### C-BK-007: Attribute 0x0a in `0x0003` marks per-unit calibration data protected from reset; general tables carry 0x08
- status: verified-code
- evidence: attribute scan of the snapshot `Backup_post-revert.bin`
- source: BP "НЕ ТРОГАТЬ НИКОГДА"
- date: 2026-10-05
- relates: Section A4

### C-BK-008: `0x00030056` is a shared debug block; `+0x0A=02` with `+0x04=X` substitutes ISO for the whole NR (0x2b6ce8); `+0x20` selects the logging module (3 NR, 4 YAP, 6 KKNR)
- status: verified-code
- evidence: av-cam 0x2b6ce8
- source: BP 1.6
- date: 2026-10-05
- relates: C-NR-001

### C-BK-009: Block `0x000300af` (StaticSetInfo) contains exactly two 13-entry style tables: `+0x70` = `00 01 02 03 04 05 ff ff ff ff ff ff ff`, `+0xa0` = all `ff`; there is no colour or tone style table there
- status: verified-code
- evidence: full scan of `0x300af` in `Backup_post-revert.bin`; the literal 0x300af occurs twice in av-cam, both only in a data pool (BKID cache list), no read of +0x70 in code
- source: HSR 1.2, HSR 4
- date: 2026-10-06
- relates: C-BK-010, C-FX-009

### C-BK-010: The `+0x70` table is the style->sharpness-slot map (visible styles 0..5 -> slots 0..5, hidden 6..12 -> `ff` = no dedicated slot)
- status: hypothesis
- evidence: attribution to sharpness comes from "task hint and code"; the table is indexed base+0x70 but the address literal is not in code
- source: HSR 0 item 2, 1.2
- date: 2026-10-06
- relates: C-BK-009, C-FX-009

### C-BK-011: Per-style slider defaults live in BKIDs `0x0107xxxx`; `liro_read_creative_style` (0x2a0f2a) maps the 13 style values to (contrast, saturation, sharpness) BKID triples
- status: verified-code
- evidence: jump table at 0x2a0f2a; table v->BKID in SYM 3; v=6 and v=14 have no saturation
- source: SYM 3, HSR 1.5
- date: 2026-10-05
- relates: C-CTRL-003

### C-BK-012: In the snapshot all 13 styles have default sliders 0/0/0 except Portrait +1/-1/-1
- status: verified-code (bytes read from `Backup_post-revert.bin`)
- evidence: values read for the triples of C-BK-011. CAVEAT: the owner's own recipe parks exactly Portrait C+1/S-1/Sh-1 and says Creative Style remembers its sliders per style, so this may be a user setting, not a factory default
- source: HSR 1.5; REC "Сохранение на камере"
- date: 2026-10-06
- relates: C-TONE-004, C-FX-029; contradiction (c) item 6

### C-BK-013: `0x01070175` byte 0 holds the selected Creative Style menu item (currently 02)
- status: verified-code
- evidence: read by `liro_read_creative_style`
- source: SYM 3
- date: 2026-10-05
- relates: C-CTRL-002

### C-BK-014: Userland (libObj, libmprctrl, all .so) has no PARAM_ID->BKID tables for `0x0003`; the subsystem lives only inside av-cam; the block roles in `bkid_names.txt` are the project's own names
- status: verified-code
- evidence: search through userland; 51 string hints exist only for neighbouring subsystems (e.g. `0x0092001f` BKID_UPM_DEBUG_DISLABLE_DFS_TRANS, `0x00560001..7` BKID_SDF_QTBL_*)
- source: SYM 0 item 7
- date: 2026-10-05
- relates: none

### C-BK-015: The literal `0x00030001` also appears dozens of times in av-cam as a message/parameter ID (e.g. `fn_29d134(0x30001, ...)` when sending the style), not as BKID; literal searches without context mislead
- status: verified-code
- evidence: SYM 2 "Ложные ссылки"
- source: SYM 2
- date: 2026-10-05
- relates: C-BK-001

### C-BK-016: Writing Backup properties through the PMCA updater shell (`bk r/w/s`, MTP, confirm on camera screen) is a safe proven path; the project's rule is Backup only, no p3/p8 writes unless explicit
- status: verified-hw
- evidence: repeated colour writes v1..v5 with the camera working; MOR "проверенный безопасный путь"; workflow needs a charged battery, Power Save 30 min, `pkill -9 -f ptpcamerad` before MTP
- source: IDX (nex3n-firmware-hacking.md line), FXP 0, MOR
- date: 2026-10-05
- relates: Section A1

### C-BK-017: The snapshot `Backup_post-revert.bin` was taken 2026-10-04 20:11; afterwards the camera received only `0x30001/08` (tags, then v1..v5) and the p3 tone write
- status: hypothesis
- evidence: stated by the planner; every plan therefore requires a `bk r` check against `<id>_orig.hex` before the first write of each property
- source: FXP section 0 warning
- date: 2026-10-05
- relates: Section C

### C-BK-018: Properties `0x66xxxx`-class curves in the store are display/video-out gamma and do not affect JPEG
- status: hypothesis
- evidence: only the README summary states it; no evidence in the source set read here
- source: RD "Key findings"
- date: undated
- relates: C-TONE-001

### C-BK-019: liro.ko exposes the full Backup API (nread, read_setting_attr, get_datasize, get_attribute, read/_multi/_async, write/_vsize/_multi/_async, sync_subsystem/all, reg_cb/unreg_cb, reset(_subsystem/_all), check, read_4Byte); av-cam uses `Backup_read`=0xc3676ab3, `Backup_read_multi`=0xc3676af9, `Backup_reg_cb`=0xc3676bfb, `Backup_write`=0xc3676b8d
- status: verified-code
- evidence: `liro.ko .rel.init.data` slot table (shift +0x24), 1050 `Backup_read` calls
- source: SYM 0 item 1, SYM 1
- date: 2026-10-05
- relates: none

### COL: colour

### C-COL-001: Colour block `0x00030001` (1536 B) is mirrored in `0x00030008`; both are written in every experiment
- status: verified-hw
- evidence: v1..v5 writes to both; byte-diff lists in V6
- source: HT header, V6 end of 3, RD
- date: 2026-10-05
- relates: C-BK-006

### C-COL-002: Per-slot colour matrix = 9 x int16 LE at `+0x48 + 18*slot`, 1024 = 1.0
- status: verified-hw
- evidence: RGB-permutation "tag" matrices read back from ARW `SR2:ColorMatrix`
- source: RD, SIM 0 item 3, HT
- date: 2026-10-05
- relates: C-COL-003, C-COL-007

### C-COL-003: Slot map: Standard 0 (+0x48), Vivid 1 (+0x5a), Portrait 2 (+0x6c), Landscape 3 (+0x7e), Sunset 4 (+0x90); hue record r is bound to slot r
- status: verified-hw
- evidence: tag-matrix experiments; HT uses the same order for records `+0x100+24*r`
- source: RD, HT "Что проверено", HSR 1.1
- date: 2026-10-05
- relates: C-COL-002, C-CTRL-004; contradiction (c) item 8

### C-COL-004: B&W slot could not be identified from a monochrome frame; HSR assumes slot 5 by menu-order scheme with a matrix about Standard
- status: unknown
- evidence: RD says unidentified; HSR 2 marks slot 5 as "по схеме" (not measured)
- source: RD; HSR 2
- date: 2026-10-06
- relates: C-FX-010

### C-COL-005: Stock matrices: slots 0 and 2 = `1292,-180,-88 / -44,1340,-272 / -24,-108,1156`; slot 1 has a different G row (`1400/-332`); slots 3 and 4 = `1292,-220,-48 / -44,1360,-292 / -24,-108,1156`
- status: verified-code
- evidence: bytes of the stock block
- source: RD
- date: undated
- relates: C-COL-002

### C-COL-006: The matrix acts on white-balanced camera RGB in linear light, without an intermediate space (error 4.1 vs 13.8 if WB is applied after the matrix); an extra 3x3 before/after changes nothing
- status: verified-hw
- evidence: RAW+JPEG pairs of the chart (DSC09416-09510 range), `pipeline.py`
- source: SIM 0 item 3, SIM 2
- date: 2026-10-05
- relates: C-ISP-005

### C-COL-007: ARW writes the slot matrix of the shot into SR2 `ColorMatrix` exactly; free check for any future matrix write
- status: verified-hw
- evidence: frames with tag matrices and muted matrices
- source: SIM 0 item 3
- date: 2026-10-05
- relates: C-COL-002

### C-COL-008: Applied WB coefficients exist only in ARW (`SR2:WB_RGGBLevels`); `Sony:WB_RGBLevels` in JPEG is an auto-WB estimate (DSC09431-38: Custom coefficients constant while `WB_RGBLevels` wander)
- status: verified-hw
- evidence: DSC09431-09438
- source: SIM 0 item 3
- date: 2026-10-05
- relates: C-COL-031

### C-COL-009: Rows of a matrix summing to 1024 leave neutrals unchanged (colour-only change); row sums != 1024 tint the greys
- status: verified-hw
- evidence: chart measurements; NE 3 (kodakwarm) deliberately moves sums to tint greys (model)
- source: RD "How the parameters move the image", NE 3.1
- date: 2026-10-05
- relates: C-COL-033, C-COL-037

### C-COL-010: Uniform desaturation S = k*I + (1-k)*1*w^T (Rec.709 w) keeps grey and luma; a strongly muted matrix halves mean chart chroma (43.7 -> 21.7)
- status: verified-hw
- evidence: chart (muted-matrix frames)
- source: RD
- date: undated
- relates: C-COL-009

### C-COL-011: Saturation slider = chroma multiplier 1 + 0.13*s in YCbCr (-3 -> 0.625, +3 -> 1.375); measured mean chroma 28.0 / 43.7 / 48.1 / 59.3 at -3 / 0 / +1 / +3
- status: verified-hw
- evidence: chart frames; RAW+JPEG fit
- source: SIM 0 item 3; RD
- date: 2026-10-05
- relates: C-COL-012

### C-COL-012: Styles add their own chroma on top of the matrix; the amount is disputed: RD says Vivid +11 %, Landscape +14 %, Sunset +14 %, Portrait none; SIM later fits x1.06 / x1.11 (Portrait) / x0.96 / x1.07 after accounting for the differing native Q1 records
- status: hypothesis
- evidence: model fits (`params.npz`); RD figures measured as total difference vs Standard
- source: RD; SIM 2
- date: 2026-10-05
- relates: contradiction (c) item 11

### C-COL-013: Hue record for slot r = 24 int8 at `+0x100 + 24*r` = 6 quads (Q0..Q5) x 4 values; slot 4 (Sunset) has marker `80 80 80 80` in Q1
- status: verified-hw
- evidence: byte tests (DSC09478-81 vs base 09483-86)
- source: HT "Что проверено"; RD
- date: 2026-10-05
- relates: C-COL-014

### C-COL-014: The 4 bytes of a quad = 4 hue regions: byte0 red/skin/magenta (~335..60 deg), byte1 orange/yellow/yellow-green (60..140), byte2 cyan/sky (170..250), byte3 blue/violet (250..335)
- status: verified-hw
- evidence: byte test, one session
- source: HT
- date: 2026-10-05
- relates: C-COL-015

### C-COL-015: Q0 = hue rotation per region, per unit: -0.25 / +0.20 / -0.39 / +0.13 deg (regions 0..3); neighbouring regions rotate in opposite directions
- status: verified-hw
- evidence: byte tests (red -35 deg at +134, yellow +18..+29 at +138, cyan -15..-37 at +94, blue +9..+22 at +128)
- source: HT
- date: 2026-10-05
- relates: C-COL-018

### C-COL-016: Q1 and Q3 raise chroma in their region: Q1 byte1 (+0x105) -36->+90 gave dC +12..+34 and L +5..+10 on yellow/green/orange/skin; Q3 byte1 (+0x125) -9->+110 about the same; Q5 byte1 (+0x145) only +7..+8
- status: verified-hw
- evidence: frames DSC09488-91 vs base 09483-86; control Sunset 09487->09492 noise dC +-8, dh +-5 deg
- source: HT "Результат теста полос"
- date: 2026-10-05
- relates: C-COL-017, C-COL-019

### C-COL-017: "Saturation" quads are not pure: the Q1 byte1 raise also rotates reds/skin towards orange by +14..+33 deg ("leakage"); possibly Q0/Q1 are two components of the ab-plane shift, not (h, C)
- status: verified-hw (the leakage); hypothesis (the ab-plane interpretation)
- evidence: DSC09488, 09489
- source: HT
- date: 2026-10-05
- relates: C-COL-016

### C-COL-018: Q2 alone has the same effect as Q0 (Landscape Q2 byte0 `+0x150` -6->+120: reds and dark skin dh -28..-34 deg, light skin -17, magenta dC +22 dh -13); Q0 and Q2 add up (binary Standard test consistent with the sum)
- status: verified-hw
- evidence: DSC09491; binary test (Q0,Q2,Q4 zeroed): predicted cyan -40 deg vs measured -35, reds -11.5 vs -6..-8
- source: HT
- date: 2026-10-05
- relates: C-COL-015

### C-COL-019: Pair (Q4, Q5) acts weaker than (Q0,Q1)/(Q2,Q3); the criterion is unknown (candidates: LutMode CAP/MOV/MON, or a chroma band)
- status: unknown
- evidence: weak response in 09490; no discriminating test
- source: HT
- date: 2026-10-05
- relates: C-COL-016

### C-COL-020: "3 luminance bands" hypothesis (H4) is refuted: the response is the same on patches with L 24..75
- status: refuted
- evidence: DSC09488-91 tests
- source: HT "Результат теста полос"
- date: 2026-10-05
- relates: C-COL-021

### C-COL-021: The hue records cannot suppress colour in shadows/highlights (no L dependence); another mechanism is needed and was not found
- status: verified-hw
- evidence: same tests
- source: HT "Как писать свой look"
- date: 2026-10-05
- relates: C-COL-020, see Section F (chroma-by-luminance gap)

### C-COL-022: Zeroing the whole hue record of a slot raises chroma by +33 % and shifts greys green (a* -7..-11): the stock values are a desaturating, slightly anti-green trim
- status: verified-hw
- evidence: e1 test
- source: RD table; SIM 3 (e1)
- date: 2026-10-05
- relates: C-COL-016

### C-COL-023: The camera responds to table edits up to 1.8x more strongly than a per-unit linear model (slope camera/simulator by hue: red 0.97, yellow/green 1.47, cyan/sky 1.35, blue/violet 1.78), so steps should be small (about 10-20 units, v6 uses <=5)
- status: verified-hw
- evidence: `calib.py` on v3->v4 and v3->v5 differences (matrices identical in v3/v4/v5)
- source: V6 section 1; RD
- date: 2026-10-05
- relates: C-COL-046

### C-COL-024: In Sunset (slot 4) the record r4 does not behave like the model: correlation with the camera -0.54 (v4), -0.19 (v5); v3->v4: all three signs opposite (blue flower -6.9 deg instead of +5, cyan +7.3 instead of -10, yellow +4..+5 instead of -4); v4->v5: cyan -3.9 instead of +20
- status: verified-hw
- evidence: chart sessions v3/v4/v5 minus Standard drift
- source: V6 section 1; NE 2.2
- date: 2026-10-05
- relates: C-COL-025, C-COL-042

### C-COL-025: The Sunset marker `-128` in Q1 is a flag ("do not apply saturation from this record") or a special mode, not a minimum, because Sunset is not desaturated
- status: hypothesis
- evidence: Sunset chroma higher than Standard; three model variants fit equally
- source: HT v4 "Sunset r4"; SIM 2
- date: 2026-10-05
- relates: C-COL-024

### C-COL-026: `Create3DLUT` (av-cam 0x3d03c4) copies a reference 3D LUT (`[obj+0xa0]`) into a hardware buffer; it does not read the 24-byte hue records. Grid: Y nodes 0,64..256 (5) x Cb/Cr -128..128 step 32 (9x9), int8 deltas of 3 planes, limit +-63, 7-bit packing; `Level` 1..7 scales by Level/8; with flag `[p0+0x2d]=1` six sector luma values are added; `ConvSD` converts between 601 and 709
- status: verified-code (emulated with unicorn)
- evidence: `emu3dlut.py`; strings `Create3DLUT 0x%X > 0x%X Level:%d ConvSD:%d BlkOfs Cr:%X, Cb:%X`, `NullError RefAdr/BufAdr`; source of reference LUT and of the 6 sector bytes not found
- source: SIM 4; HT (older, says LUT is built from matrix and records)
- date: 2026-10-05
- relates: C-COL-027; contradiction (c) item 10

### C-COL-027: The consumer of the `+0x100..` hue records is not found in av-cam; the 2-D LUT (`Copy2DLUT`, `LutMode Change CAP/MOV/MON`) is a candidate
- status: hypothesis
- evidence: `Create3DLUT` only receives a pointer to the whole block (`msg[0]`=0xc3ac2b94) and has no read of +0x100
- source: HT "Гипотезы"; SIM 4
- date: 2026-10-05
- relates: C-COL-026, C-COL-028

### C-COL-028: av-cam does not multiply the matrix and has no ARM read of `+0x48` from the colour block pointer; the stage that picks `base+0x48+18*slot` is the DSP/HAPI side
- status: hypothesis
- evidence: no ARM access to +0x48 found (negative result); SE states the colour develop stage is the SA/DSP YC engine (VLIW, not decoded); four builders only hand over the pointer and the slot byte
- source: SYM 2 "Потребление"; SE "Where the Creative Style colour matrix is applied"; HSR 1.3
- date: 2026-10-05
- relates: C-CTRL-004, C-ISP-004

### C-COL-029: The colour module `[CAMERA_MAIN_CC]` keeps its own style index in `obj[0]+0x26` (15 values: Standard 0, Vivid 1, Neutral 2, Portrait 3, Landscape 4, BW 5, Clear 6, Deep 7, Light 8, Sunset 9, Nightview 10, Autumnleaves 11, Real 12, Sepia 13, BW 14) and maps it to the EXIF `ColorMode` (Sunset 4, Autumn 16, ...)
- status: verified-code
- evidence: jump table at 0x3d6ea6, second copy of names 0x3d8fd2; matches the exiftool ColorMode list; readers 0x3cf214, 0x3d0e00, packer 0x3dbff4 (+0xabe)
- source: OQ 3.3
- date: 2026-10-05
- relates: C-COL-003 (index spaces differ: CC index vs matrix slot), contradiction (c) item 8

### C-COL-030: On Auto WB, Sunset greys are multiplied (linear, before the tone curve) by R x1.40..1.44, G x1.06..1.09, B x0.60..0.64 relative to Standard, constant over 15 grey steps (b* up to ~+30 on Sunset vs ~+3 on Standard)
- status: verified-hw
- evidence: DSC09418/09425 ramps converted through inverse curves (Sunset = k14∘base, Standard = base); includes the matrix/chroma gain of Sunset, so the pure gain may be smaller
- source: OQ 3.1
- date: 2026-10-05
- relates: C-COL-031, C-COL-032

### C-COL-031: Sunset warmth is not in the recorded WB coefficients (`WB_RGBLevels` 657-667/256/430-435 same as Standard) and absent on fixed WB (Custom 5500 K, DSC09433/09438); the only stable tag difference is `ColorMode = 4`. So the multiplier is applied after the AWB estimate is stored, only under AWB
- status: verified-hw
- evidence: makernote of all frames
- source: OQ 3.2; RD (older wording: "shift of the auto-WB target")
- date: 2026-10-05
- relates: C-COL-030; contradiction (c) item 9

### C-COL-032: The place and Backup ID of the Sunset-AWB warm multiplier are not found (scan of 0x0003xx blocks for 13-15 entry tables with a Sunset-specific entry gave 2186 false hits; first candidates: functions reading CC index +0x26 near the WB-calibration users)
- status: unknown
- evidence: OQ 3.3; SYM 4 (no AWB strings in av-cam, chain via `fn_1feec`/0x2001a/0x2217a not walked)
- source: OQ 3.3; SYM 4
- date: 2026-10-05
- relates: C-COL-030

### C-COL-033: Warmth can be baked into a slot matrix as M' = M*diag(r,1,b); chosen taste options Portra r=1.05/b=0.95, UltraMax r=1.05/b=0.92 (grey b* +3.7 / +5.6); r=1.08 gives pink greys
- status: hypothesis
- evidence: simulator (matrix path confirmed by RAW+JPEG, the outcome not shot); blob `00030001_v6_kodakwarm.hex` differs from v6 in 14 bytes
- source: OQ 3.4; NE 3
- date: 2026-10-05
- relates: C-COL-037

### C-COL-034: Current colour looks written on the camera: v5 = Vivid -> Portra 400, Portrait -> House, Landscape -> UltraMax 400, Sunset -> Phoenix II (Standard slot 0 left as reference)
- status: verified-hw
- evidence: v5 shot in sessions DSC09498-09502, 09503-07; MOR "Состояние камеры на старт"
- source: MOR; V6 section 2; HT
- date: 2026-10-05
- relates: Section C

### C-COL-035: v6 colour (79 bytes differ from v5, all inside matrices of slots 1-4 and records r1-r4; max table edit 5 units/byte) is designed with the simulator, NOT written
- status: hypothesis
- evidence: `00030001_looks_v6.hex`; predicted rms hue error to target Portra 10.0->8.0, House 4.1->3.1, UltraMax 10.7->7.9; most changes within chart noise
- source: V6 0, 4, 5
- date: 2026-10-05
- relates: C-COL-034, C-COL-023

### C-COL-036: `v6_phoenixsky` = v6 + one byte `0x163` (r4 Q0 byte3) fa->3a (-6->+58) to push Sunset blues/sky towards violet; expected +4..+11 deg, but earlier Sunset r4 edits gave ~0 or reversed sign
- status: hypothesis
- evidence: simulator +10 deg sky; worst case x1.78 = +19 deg; scan target +26 deg
- source: NE 2
- date: 2026-10-05
- relates: C-COL-024

### C-COL-037: `v6_kodakwarm` raises row sums of slots 1 and 3 by +6..+9 % in R, so R clips about 0.1 EV earlier; greys warm on any WB
- status: hypothesis
- evidence: arithmetic from matrices
- source: NE 3.3
- date: 2026-10-05
- relates: C-COL-033

### C-COL-038: In `0x00030001` group 1 only 10 working matrices exist (slots 0-9): slots 6 and 7 equal Standard byte for byte, slots 8 and 9 are one "blurred" low-saturation matrix; slots >=10 are garbage overlapping the hue-record zone; group 2 at `+0x400` has 7 matrices (slot 6 = identity). So there are no 7 distinct matrices for the 7 hidden styles; the older "17 matrices" count included overlapping records
- status: verified-code
- evidence: byte inspection of `Backup_post-revert.bin`
- source: HSR 0 item 3, HSR 4
- date: 2026-10-06
- relates: C-FX-009; contradiction (c) item 7

### C-COL-039: Pairs of 8-byte records at `0x30001 +0x2aa..0x2e7` (e.g. `00 00 0a f8 07 e8 c6 ad / 00 00 17 f7 08 ee 42 53`) look like per-style corrections, purpose unknown
- status: unknown
- evidence: bytes only
- source: SYM 4
- date: 2026-10-05
- relates: C-COL-032

### C-COL-040: Simulator accuracy (delta E76, chroma patches/greys): RAW->JPEG train 2.6/0.9, hold-out 3.3/1.8, JPEG->JPEG between styles 4.2 vs 7.7 for the null model; floor set by the monitor target: two identical shots differ by 4.7 dE (patches up to 14)
- status: verified-hw
- evidence: `validate.py`, `cache/fit_report.txt`
- source: SIM 0 item 2
- date: 2026-10-05
- relates: C-COL-041

### C-COL-041: Hue-table behaviour is modelled empirically with 4 axes in CbCr (angles 100/172/268/342 deg; alpha -0.22/+0.22/-0.17/+0.22 deg/unit, beta 1.11/0.89/0.78/1.19 %/unit; r = alpha*(Q0+1.03*Q2+0.55*Q4), ln s = beta*(Q1+0.62*Q3+0.11*Q5)); it cannot be checked on fine (+-10) edits with the monitor target
- status: hypothesis
- evidence: fit on 13 RAW + 12 JPEG pairs; chroma 5.6 vs 6.6 null model at noise 4.7
- source: SIM 3
- date: 2026-10-05
- relates: C-COL-015, C-COL-026

### C-COL-042: The simulator does not predict the Sunset slot (e1 and tables) and has an unexplained excess error on Sunset greys (3.0) and permuted-matrix Sunset 9438 (5.4); v1 Sunset -> worse than null (5.6 vs 3.9)
- status: verified-hw
- evidence: validate.txt
- source: SIM 5; V6 section 1
- date: 2026-10-05
- relates: C-COL-024

### C-COL-043: Session-to-session drift is large (Standard day to day dE 10.5; House table yellows/greens differed by -12..-15 chroma between sessions with identical tables); every experiment needs a same-session baseline; RAW+JPEG pairs avoid monitor noise
- status: verified-hw
- evidence: V6 section 1 repeat test (9508/9509 mean |dh| 1.9 deg, |dC| 4.7)
- source: RD; V6 section 1; FXP 5
- date: 2026-10-05
- relates: C-COL-044

### C-COL-044: Chart noise: +-2..5 deg hue, +-5..10 chroma (up to 15 between sessions)
- status: verified-hw
- evidence: repeats
- source: V6 5
- date: 2026-10-05
- relates: C-COL-043

### C-COL-045: Sony Creative Look on a7 IV (ILCE-7M4 fw 6.02) stores only slider values in Backup (FL/NT all zero; IN Fade 3; SH Fade 6; Sharpness 4, Range 3, Clarity 1); no 3x3 matrices or int8 hue tables in the same format as `0x00030001`; look character is computed by the IQ processor (`cpapp-b.bin`, `PQD_Gamma`)
- status: verified-code
- evidence: decrypted firmware via fwtool PR #52/#53 keys; `bkdump.py`; no 3N matrix `1292,-180,-88` in the a7 IV firmware
- source: OQ 1
- date: 2026-10-05
- relates: none

### C-COL-046: v4 table edits (up to 34 units per byte) overshot the target; v6 limits edits to <=5
- status: verified-hw
- evidence: v4 chart result vs model
- source: V6 section 1, 3
- date: 2026-10-05
- relates: C-COL-023

### TONE: tone curves

### C-TONE-001: 21 tone curves (1024 x uint16, 10-bit in -> 10-bit out) are constants in av-cam.bin (p3) at `0x5b006a + 0x800*k`, monotone; k3, k10, k20 are identity; they are NOT in Backup
- status: verified-code
- evidence: av-cam.bin; 180 blocks of 0x0003 scanned, no curves
- source: TC 0 item 1, 4
- date: 2026-10-05
- relates: C-TONE-005

### C-TONE-002: Contrast slider -3..+3 = curves k0..k6 (k3 identity)
- status: verified-hw
- evidence: wedge measurement: c+3 -> k6 error 4.1 vs 15.1 (identity); c-3 -> k0/k1 2.4-4.5 vs 6.1
- source: TC 0 item 2
- date: 2026-10-05
- relates: C-TONE-005

### C-TONE-003: Vivid, Landscape and Sunset use style curve k14 (S-curve); Sunset may do more in the blacks
- status: verified-hw
- evidence: wedge errors 1.2-2.8 vs 4.1-4.6 identity; Sunset 2.25 vs 4.4 with k15 (RAW fit); excess grey error 3.0 in Sunset
- source: TC 0 item 3; SIM 2, 5
- date: 2026-10-05
- relates: C-TONE-004

### C-TONE-004: Portrait uses a curve equal to Contrast -2 (k1) at its measured settings; this is hard to reconcile with the stored Portrait default of c+1 (which would be k4)
- status: verified-hw (the measurement); contradiction noted
- evidence: wedge 09500: error 2.0 vs 6.0 identity; one RAW frame at c+1 cannot separate k1 from k2 (2.31 / 2.37)
- source: TC 0 item 3; SIM 2; HSR 1.4 (claims "consistent with c+1/s-1")
- date: 2026-10-05
- relates: C-BK-012; contradiction (c) item 6

### C-TONE-005: Pointer table in RW `0x634748` (VA 0xc3cb6868) has 27 slots: +0x00 (0..6) = contrast k0..k6; +0x1c (7..13) = a "density" family k7..k13 (k10 identity); +0x38 (14..26) = style/effect curves
- status: verified-code
- evidence: indices come from runtime bytes `[r1+0x1b]`, `[r1+0x1d]`, `[obj+0xbe1]`; not found in Backup
- source: TC 1
- date: 2026-10-05
- relates: C-TONE-006

### C-TONE-006: Corrected style-slot content: slots 14..27 = `k20, k14, k15, k16, k17, k18, k20, k19, k20 x5`, so style index 0 = k20 (identity) and index 1 = k14; k0 is reachable only via contrast
- status: verified-code
- evidence: pointers read from RW table 0x634748
- source: SYM 7.1 (corrects TC 1 which listed `k14, k15, k16, k17, k18, k20, k19, k20`)
- date: 2026-10-05
- relates: C-TONE-005; contradiction (c) item 3

### C-TONE-007: Meaning of k15..k19 and the k7 family: k15 stronger S, k16 threshold (posterize or High-contrast mono), k17 raised black (Soft high-key), k18 soft, k19 very strong S; k7..k13 = "density" family (DRO or brightness correction)
- status: hypothesis
- evidence: shape of the curves only
- source: TC 1; SYM 7.2
- date: 2026-10-05
- relates: C-FX-028

### C-TONE-008: Curves work in the encoded domain after the base gamma (0..1023), so Y'_style = C_k(Y'_Standard) on grey wedges
- status: verified-code (design); verified-hw (measured wedges match)
- evidence: wedges; `tone_lut_build`
- source: TC 1
- date: 2026-10-05
- relates: C-TONE-002

### C-TONE-009: Contrast curves are applied per R,G,B channel, not to Y (1.8 vs 3.7 dE for c-3/k0 and c+3/k6)
- status: verified-hw
- evidence: RAW+JPEG pairs
- source: SIM 0 item 3
- date: 2026-10-05
- relates: C-TONE-002; supersedes TC 5 "Применяется ли кривая к Y или к RGB" (open)

### C-TONE-010: `tone_lut_build` (0x2d6996) computes 96 Y values; composition is by priority, not a product of all groups: if the k7 family is on, `y = contrast[k7fam[base(x)]]`; else if contrast is on, `contrast[base(x)]`; else if style is on, `style[base(x)]`; else `base(x)`. So with contrast on (any non-zero slider), the style curve is not applied
- status: verified-code
- evidence: branches 0x2d6a32..0x2d6b30; the loop covers all 96 nodes in all four branches
- source: SYM 7.1; OQ 2.2
- date: 2026-10-05
- relates: C-TONE-011; contradiction (c) item 3

### C-TONE-011: Measured composition: Standard c-3 equals `k0(base(0,1)[x])` (error 1.82 vs 6.76 base only), Standard c0 equals base (2.90)
- status: verified-hw
- evidence: DSC09510, DSC09509 vs `0x597dfa` base
- source: SYM 8.1
- date: 2026-10-05
- relates: C-TONE-010

### C-TONE-012: Base gamma table `0xc3cb6788` (file 0x634668): 28 rows x 2 columns of pointers, 24 non-empty; each curve is 2048 x u16 (11-bit in, 10-bit out) plus 13 u16 tail (9 segment params `2,2,3,4,4,4,4,3,3`, row number, column flag); empty rows: 2, 9, 12, 19..27, column 0 missing in 10..18
- status: verified-code
- evidence: SYM 7.2, 8.1; supersedes TC 1 "1024 -> 1024"
- source: SYM 8.1
- date: 2026-10-05
- relates: C-TONE-013

### C-TONE-013: Photo base gamma = row 0, column 1 (file `0x597dfa`), input scale 2043 ~ 2047, fit error 0.92 Y' of 255 on RAW frame DSC09419 (next best (7,1) 1.24, (6,1) 1.31 with unexplained scales); confirmed on one RAW frame only
- status: verified-hw
- evidence: RAW grey wedge vs JPEG, 24 candidate curves
- source: SYM 8.1
- date: 2026-10-05
- relates: C-TONE-012

### C-TONE-014: The 96 tone-LUT X nodes: `x = (2*(k+1)*(seglen>>p) + segstart)*g/256 - 1`, seglen `8,8,16,32,64,128,256,512,1024`, segstart `0,16,32,64,128,256,512,1024,2048`; at g=256 equals table 0xc39d8adc (`3,7,...,127` step 4, `135..255` step 8, `271..511` step 16, `543..1023` step 32, `1151..2047` step 128, then 2047 x8); g from `obj+0xbe4`, photo g ~ 1
- status: verified-code
- evidence: 0x2d6ba8
- source: SYM 8.1
- date: 2026-10-05
- relates: C-TONE-015

### C-TONE-015: Backup `0x0003007a` layout: `+0x00..+0xBF` = 96 x u16 (stock = (X+1)/2 exactly: 2,4,...,64, 68..128, ..., 1023 x9), `+0xC0..+0xD1` = 9 x u16 segment params (copied in order 1,0,3,2,5,4,7,6,8; stock `2,2,3,4,4,4,4,3,3`), `+0xD7` = debug mode byte (stock 0); attr 08, one bank
- status: verified-code
- evidence: element-wise comparison with X nodes
- source: SYM 3, 7.4, 8.1
- date: 2026-10-05
- relates: C-TONE-016

### C-TONE-016: `+0xD7` modes: 1 = after the normal computation the 96 LUT values are overwritten by `0x3007a` u16[0..95] (Y values, whole chain incl. base gamma replaced; used also as the fallback if the normal calc returns an error); 2 = curve indices forced from Backup; 3 = hardware LUT dumped to RAM
- status: verified-code
- evidence: 0x2d8644 (capture), 0x2d676e (monitor); byte copied to `obj+0xbe2`; read only by 0x2d7124, 0x2d79e0 and the two override functions; NOT run on the camera
- source: SYM 0 item 5, 3, 7
- date: 2026-10-05
- relates: C-TONE-017, C-TONE-018; supersedes TC 0 item 4

### C-TONE-017: Mode 2 byte table: `+0xD9` base row (<0x1C), `+0xE7` base column (<2), `+0xDB` contrast curve k0..k6 (<7; if !=3 sets contrast enable), `+0xDD` k7 family (<7), `+0xDF` group via table 0xc3c10b9c (<6, 7 = none), `+0xE5` style curve index (<0x0E, if !=0 sets style enable); out-of-range value = "do not override"; stock values `00,03,03,07,00,01` are NOT neutral; override is global (all styles, sliders, monitor and capture) and enables are only set, never cleared
- status: verified-code
- evidence: functions 0x2d7e38 (monitor), 0x2d7f88 (capture)
- source: SYM 7.1, 7.2
- date: 2026-10-05
- relates: C-TONE-016, C-TONE-019

### C-TONE-018: Mode 1 freezes one base gamma (0,1) for everything (ISO, DRO, contrast slider and style S-curves stop working) and also acts on the live view
- status: verified-code
- evidence: SYM 8.2 "Ограничения"
- source: SYM 8.2
- date: 2026-10-05
- relates: C-TONE-016

### C-TONE-019: Planned experiment T2-k0 (mode 2): bytes `D7 00->02, D9->FF, DB 03->00, DD->FF, E5->FF, E7->FF` should put the film k0 on all styles at any contrast slider (Standard c0 ~ Standard c-3, black ~12/255); mode 1 blob `3007a_mode1_film.hex` (162 bytes differ) and `3007a_mode1_shoulder.hex` (163 bytes) exist; none written
- status: hypothesis
- evidence: blobs in `~/nex3n-dump/work/fx/`; rollback `3007a_mode{1,2}_orig.hex` equals `0x3007a` of `Backup_post-revert.bin`
- source: SYM 7.3, 8.2; NE 1.5; MOR Session 0
- date: 2026-10-05
- relates: C-TONE-016, C-TONE-020

### C-TONE-020: Null test: editing `0x3007a +0x00..0x3f` in mode 0 should leave the wedge unchanged (the data is not used in mode 0), contrary to TC's reading that it is a sampling grid whose edit would change the dark wedge
- status: hypothesis
- evidence: code reading only; TC proposed the test, SYM says the reason differs
- source: TC 3; SYM 3
- date: 2026-10-05
- relates: C-TONE-016

### C-TONE-021: `0x3007a +0xD2..+0xD5` (stock `00 00 00 01`) go straight into gamma-block hardware registers (monitor: 0x2d7dba -> 0x37d6d8 -> 0xf4015480, +484, +488, +4b8; capture: 0x2d7a04 -> 0x37ddb0); `+0xE2/+0xE3` (stock `04 04`) become nibble bit fields of register `0xf401c304` (0x151d9c, fields 2/4/2/4 bits); semantics unknown
- status: verified-code
- evidence: addresses listed
- source: NE 1.3
- date: 2026-10-05
- relates: C-ISP-002

### C-TONE-022: A second hardware tone LUT exists at `0xf401c700` (96 x u16) and `0xf401c800` (0xA0 B); it is filled instead of the usual one when `obj+0xC71 == 9` (paths 0x2d67ca, 0x2d7718, 0x2d7d86; 0x2d6738 does even/odd layout); what mode 9 is, is unknown
- status: verified-code
- evidence: addresses listed
- source: NE 1.3
- date: 2026-10-05
- relates: C-ISP-003

### C-TONE-023: The tone LUT is written to hardware at `0xf4015300` (monitor, 0x37d6ec) or into capture buffer `[0xc3cbe09c]` (0x37ddc8, 0x180 B + 36 B of segment params) and then flows through the YC pipeline together with other stages
- status: verified-code
- evidence: addresses listed
- source: OQ 2.2
- date: 2026-10-05
- relates: C-ISP-002

### C-TONE-024: Film tone curve for k0 (Contrast -3): black 55, white 909 (of 1023), soft S; points `[55,139,243,362,487,612,730,832,909]` at inputs 0..1023 step 128; fitted so the 64 KB block 0x5b recompresses to exactly the original 35 216 bytes; written into p3 sectors 8849-8886 (38 sectors, inside av-cam only) on 2026-10-05; read-back md5 921f2345.. matched; whole p3 = d7cca446..; original sectors md5 186bf30f.. kept as rollback
- status: verified-hw
- evidence: `dd seek=8849 count=38` to /dev/nflasha3; camera booted afterwards
- source: TC "ЗАПИСАНО в камеру"
- date: 2026-10-05
- relates: C-TONE-025, Section C

### C-TONE-025: The film k0 works on the camera: Standard c-3 (DSC09510) follows `k0film(c0)` within +-1.5 Y' up to Y' 197 (black ~12/255)
- status: verified-hw
- evidence: 09510 vs 09509 mapping: inputs 197..237 -> predicted 187..216, measured 187..233
- source: OQ 2.1(b); SYM 8.1
- date: 2026-10-05
- relates: C-TONE-024, C-TONE-026

### C-TONE-026: Above Y' ~200 (input ~511/2047, boundary of segments 5 and 6) the camera does not lower highlights below base minus 3..8 Y' even when the curve asks for it: frame 09510 top 232.7/255 vs film-k0 ceiling 226.6/255; weight of the curve falls from ~1.0 to 0.68 at 207 then 0.4..0.16; measured on a single frame (stock c-3 09420 shows no sharp threshold)
- status: verified-hw
- evidence: DSC09509/09510 vs RAW-based base; at LUT output ~213 c0 gives 214.7 but c-3 gives >=232 (and at 175: 176 vs 187), so the stage sees the base signal, not only the LUT output
- source: OQ 2.1; NE 1.4
- date: 2026-10-05
- relates: C-TONE-027, C-TONE-028

### C-TONE-027: The makernote field `0x9405a+0x68a` (11 x int16, two states A/B) is NOT linked to the tone curve; A/B alternate independent of style, contrast and WB in all 67 frames 09416-09510 (Standard c0 occurs in both states); the field is the second half of exiftool's `ChromaticAberrationCorrParams`; wedges in A and B agree within +-1 Y'
- status: refuted (earlier claim in OQ 2.3 that it switches exactly when a curve is on)
- evidence: NE 1.1
- source: NE 1.1; OQ 2.3 (superseded)
- date: 2026-10-05
- relates: C-TONE-026

### C-TONE-028: The stage that holds highlights above ~Y' 200 is not found and has no control in Backup; model "out ~ max(LUT, base - delta), delta 3..8 Y'" fits; the 13 `job_YC_ModeMain` stages (Pfr, Dg, Itp, Cas, Clp, Nr, Yap, Shd, ShdOff, Adj, Mov, Lga, Gra) contain no obvious post-LUT candidate (Clp = black clamp by OB, Lga = LightLvAdj calibration, both raw-input stages; Gra has no strings)
- status: hypothesis
- evidence: strings `PBEH:clp_*`, `lga_ave_*`, `[YC-CLP ERROR]opbData`
- source: NE 0, 1.2, 1.4
- date: 2026-10-05
- relates: C-TONE-026, C-ISP-001

### C-TONE-029: Design rule: build the film shoulder below Y' 200 (curve not lower than base - 5 above 200); a diagnostic shot (Standard c-3 at +1 and +2 EV) or the mode-1 shoulder blob can tell whether the floor depends on input (~511) or on level
- status: hypothesis
- evidence: OQ 2.5; NE 1.5
- source: OQ 2.5; NE 1.5
- date: 2026-10-05
- relates: C-TONE-026

### C-TONE-030: All tested styles pivot around grey step 128 (Y' ~114); Standard c0 wedge (DSC09419) tops at 191, v5 Standard 207, Standard c-3 186 (at that session), Standard c+3 212
- status: verified-hw
- evidence: 21-step wedge measurements (target/layout.json, `ramp.py`)
- source: TC 2
- date: 2026-10-05
- relates: C-TONE-002

### C-TONE-031: Plans for installing a custom curve: replace k0/k1 (then "Contrast -3 = film in every style") or k14 (changes Vivid/Landscape/Sunset), or append a curve in free space and repoint one RW slot (which style uses which slot not yet verified)
- status: hypothesis
- evidence: TC 3
- source: TC 3
- date: 2026-10-05
- relates: C-TONE-024

### C-TONE-032: Target numbers for the owner's refs: black (1st percentile Y') ~0.050-0.063, white (99th) ~0.903-0.907; NEX Standard 0.04/0.92; so a slightly lifted but clean black and a compressed soft shoulder is wanted
- status: hypothesis
- evidence: refs measured by the owner (not shown here)
- source: TC 4
- date: 2026-10-05
- relates: C-TONE-024

### NR: noise reduction, sharpness, vignette

### C-NR-001: Luma noise reduction has three independent stages in av-cam: YC::NR (G-NR + C-NR; calc 0x284544 `nr_gnr`, called from 0x286070 `nr_main`, from 0x2b6cb4), YKNR (`Capture::YKNR`) and KKNR
- status: verified-code
- evidence: log strings `NR:nr_gnr.*`, `NR:nr_main.*`
- source: BP 1.1
- date: 2026-10-05
- relates: C-NR-002, C-NR-007, C-NR-008

### C-NR-002: `nr_main` has 8 flag bytes per ISO range at `0x0003001b`: A (X>=0xE01, ISO 51200+, unreachable on 3N) `+0xCE..0xD5` = `01 01 01 01 01 00 02 01`; B (0x901<=X<0xE01) `+0xD6..0xDD` = `01 01 00 00 01 00 02 01`; C (X<0x901) `+0xDE..0xE5` = `01 01 00 00 01 00 03 01` (order nr_on gnr_on ghnr_on glnr_on cnr_on sk_on cdmin_flg c2rb_gsel); thresholds at `+0x6A/+0x6C`
- status: verified-code
- evidence: bytes + code
- source: BP 1.1
- date: 2026-10-05
- relates: C-NR-003, C-NR-010

### C-NR-003: GHNR/GLNR are forcibly enabled (0x28611c) when `0x00030010+0x0C != 0`, shooting mode in {1, 0x13, 0x1A, 0x1F, 0x20}, NR level != 3 and ISO not in range A; also for modes {6,7,0xB,0xC,0xD,0xF,0x11, 8/0x14 conditional}; mode numbers are not decoded (mode 1 probably = ordinary single shot)
- status: verified-code (the condition); hypothesis (mode 1 = normal shot)
- evidence: 0x28611c
- source: BP 1.1
- date: 2026-10-05
- relates: C-NR-010

### C-NR-004: The NR level (0..3) is a runtime byte `CommonRam+0x15C`, not in Backup; its mapping to the High ISO NR menu items is not established
- status: unknown
- evidence: set by code
- source: BP 1.1, 8
- date: 2026-10-05
- relates: C-NR-005

### C-NR-005: Level-dependent "high-frequency" G-NR parameters come from different tables per level (L0 from `0x3011f`; L1 from `0x30049`; L2 from `0x30014/15/16/17`; L3 from `0x30049/0x3004a`): fields `[+0xE0]`, `[+0xF4]`, `gnr_hi_cor_gainth`, `[+0x104]`, `gnr_hi_gain_cn`, `gnr_hi_gain_eg` (11-point ISO tables; hi_gain from ISO 204800 to 200: L0/L1 `F F E C C B A A A (A|D) D`, L2 `F F F E C C B A A A D`, L3 `D D C A A 9 8 8 8 B B`; clamp <0x20); the set is recomputed from level-2 tables if `[CommonRam+0x430] != 0`
- status: verified-code
- evidence: BP table in 1.1
- source: BP 1.1
- date: 2026-10-05
- relates: C-NR-006

### C-NR-006: For `picture_effect == 9` the three hi parameters are forced from `0x30015+0xDC..0xEC` (gainth 0x20, gain_cn = gain_eg = 0x10), so 0x10 probably means coefficient 1.0 (HF detail passes) and 8..F suppress HF to 50..94 %
- status: hypothesis
- evidence: only the forced values; direction of hi_gain not confirmed
- source: BP 1.1, 1.5
- date: 2026-10-05
- relates: C-NR-011

### C-NR-007: YKNR: 13 tables x 11 bytes at `0x0003004c` (meaning of fields not decoded); enabled by 0xd5760: off at NR level 0; at level 1 off in modes {1,5,0x13,0x1A,0x1F,0x20}; otherwise only if ISO falls in the window from `0x3004a`: `+0xD6/+0xD8` = 0x0AFF/0x0600, `+0xD2/+0xD4` and `+0xDA/+0xDC` = 0x0B00/0x06AA (~ISO 200..6400); YKNR axis is `obj+0x5C6`, not the G-NR axis `obj+0x14E`; whether the scales match is unchecked; whether YKNR works on luma or chroma is unknown
- status: verified-code
- evidence: 0xd5760, 0xd5854
- source: BP 1.1; FXP 1
- date: 2026-10-05
- relates: C-NR-011

### C-NR-008: KKNR (`0x00030024`, modulation `0x3004a+0xE7..0xFE`, `0x3004b`) is, by parameter names and a log `Start_Face_Nr: KKNR %d`, skin smoothing on faces (probably Soft Skin Effect), not general NR (levels 0..4 weight `0x80/0x80/0xC0/0xFF`)
- status: hypothesis
- evidence: names `kk_fm_fsize_small/big_size` (0x64/0x3E8), `kk_fm_fdist_*`
- source: BP 1.1
- date: 2026-10-05
- relates: C-NR-001

### C-NR-009: Most NR/sharpness tables are 11 points over an ISO axis `aus_X_ISO` = `0x1000,0xF00..0x700,0x600` stored at `0x3000c+0x06..0x1B`; first element = high ISO, last = low; probably 256*log2(ISO/3.125) so 0x600 = ISO 200; tables run to ISO 204800, so the ISO limit is not in processing
- status: hypothesis (axis scale); verified-code (table extent in bytes)
- evidence: bytes; gap between G-NR axis and Apacon/YKNR axis (Apacon starts at 0x700) unresolved
- source: BP 0, 5, 8
- date: 2026-10-05
- relates: C-NR-007

### C-NR-010: Experiment NR-1 (designed): `0x30010` and `0x300b4` byte `+0x0C` 01->00 should drop forced GHNR/GLNR for ISO <=25600 (luma grain finer and more visible, chroma unchanged); success = sigma L* x1.25 or more with sigma C* <= x1.15 at ISO 1600/3200
- status: hypothesis
- evidence: plan only; "NR-1 is the most precise lever" per FXP; if no effect, normal shots enable GHNR by another branch
- source: BP 1.2; FXP 1 and 5.1
- date: 2026-10-05
- relates: C-NR-003

### C-NR-011: Experiment NR-2 (designed): `0x3001b`/`0x300be` byte `+0xD7` 01->00 turns off G-NR luma in range B only (ISO 3200..25600) with ISO 1600 as built-in control; NR-3 closes the YKNR window (`0x3004a +0xD2..D3`, `+0xD6..D7`, `+0xDA..DB` -> 0); NR-4 sets hi_gain tables to 0x10 at ISO indices 5..8 (and probe at index 6)
- status: hypothesis
- evidence: plan; ISO axis hypothesis C-NR-009
- source: BP 1.3-1.5; FXP 1, 5.1
- date: 2026-10-05
- relates: C-NR-010, C-NR-012

### C-NR-012: Order of NR steps differs between notes: BP offers NR-4 as a fine step "after 1-3"; FXP treats NR-4 as a dosed alternative to NR-1 (if NR-1 is on, NR-4 probably changes nothing, since hi_gain belongs to the same GHNR)
- status: hypothesis
- evidence: reasoning
- source: BP 1.5; FXP 1
- date: 2026-10-05
- relates: C-NR-010; contradiction (c) item 14

### C-NR-013: Free reference for NR: High ISO NR menu = Low gives the same sigma L* as NR-1 would; if so NR-1 is unnecessary
- status: hypothesis
- evidence: FXP 5.1 step A0
- source: FXP 5.1
- date: 2026-10-05
- relates: C-NR-004

### C-NR-014: YAP aperture correction: `job_apc_gain_stl` (0xd4334): `apc_gain.apgain = table_ISO * k1*k2*k3 / 2^21`, clamp <0x200; k ~ 0x80 (=1.0) so apgain ~ table `0x3000c+0x1C..0x31` = 11 x `B0 00`; vapgain/hapgain = bytes `0x3000c+0x86` (8) and `+0x8B` (7), clamp <0x10; at negative sharpness steps bytes `0x3000f+0xD4..D7` / `+0xDC..DF` are subtracted (probably the Sharpness slider)
- status: verified-code
- evidence: 0xd4334; bytes in snapshot
- source: BP 2.1
- date: 2026-10-05
- relates: C-NR-015

### C-NR-015: Coring (`job_apc_coring_stl` 0xd32ce): `vcoring_p0` = `0x3000c+0xCE..0xE3`, `hcoring_p0` = `0x3000d+0x5E..0x73`, both `4 4 4 4 5 5 6 7 8 A A` (high ISO -> low ISO, i.e. LESS coring at high ISO than at low), plus mode/effect corrections (`3000e`, `3000f+0x52..`, `3001e+0x40..`); `vcoring_p1/p2` = `0x3000d+0x3C/+0x42` (0x18/0x24), `hcoring_p1/p2` = `+0xCC/+0xD2`; further tables `apc_yld/mask/lpf/zoukou` and picture-effect branches 1/4/5/9 (`3001e+0x44..0x58`) not decoded
- status: verified-code
- evidence: 0xd32ce; bytes
- source: BP 2.1; FXP 2
- date: 2026-10-05
- relates: C-NR-016

### C-NR-016: Designed sharpness experiments: SH-1 apgain `B0 -> 60` (FXP, -45 %) or `B0 -> 40` (BP, -64 %) on `0x3000c`+`0x300b0` `+0x1C..+0x31`; SH-2 coring x3 (`04->0C`, `05->0F`, `06->12`, `07->15`, `08->18`, `0A->1E`), to be applied AFTER the NR steps (weaker NR makes small grain get sharpened)
- status: hypothesis
- evidence: plan; success = overshoot -30 % at edge, 10-90 % width within +30 %
- source: BP 2.3, 2.4; FXP 2, 5.1
- date: 2026-10-05
- relates: C-NR-014, C-NR-015; contradiction (c) item 15

### C-NR-017: Apacon ("Developing", style and slider dependent) at 0x464958: 5 coefficients = `ladder[step] * ISO_multiplier * 2^11 >> 16`, clamp 0xFFF; step = signed byte `[obj+0xF2]` (probably Sharpness -3..+3) + 4, +1 for "view" 3/4, -1 for 7; ladder registers 0x78B0/0x78B2 = `0x00030106+0xAC..0xBD` (9 x u16 `2 8 16 24 [32] 80 112 144 176`), 0x78B4 = `+0xBE..0xCF` (`2 8 16 24 32 32 32 32 32`); ISO multiplier `0x00030106+0x00..0x15` (`120 x9, 100, 100`, ISO axis at `0x30108+0xA0..`); channels 0x78B2/0x78B4 have ZERO multipliers on 3N, so only 0x78B0 works; Sharpness -3 gives ladder step 1 (8 instead of 32) without any write
- status: verified-code
- evidence: 0x464958; bytes
- source: BP 2.2
- date: 2026-10-05
- relates: C-NR-018

### C-NR-018: Apacon channel 0x78B0 is not pure sharpness: the experiment of 2026-10-04 (ladder step 5, 80 -> 32) noticeably lowered Sunset saturation; the Sunset-specific function `YC_SetModeDependent_Sunset` (0x464daa) writes the Apacon registers 0x78b0..0x78bf
- status: verified-hw (the saturation drop); verified-code (the function); mechanism unknown
- evidence: experiment 04.10; symbol 0x464daa
- source: BP 2.2; SYM 4
- date: 2026-10-04
- relates: C-NR-017; contradiction (c) item 12

### C-NR-019: Camera state after that experiment is unclear: IDX says the camera currently has the Sunset ladder step in `0x00030106` changed (80->32) and the next step is an A/B; BP calls its snapshot "post-revert"
- status: unknown
- evidence: conflicting notes; need `bk r 00030106`
- source: IDX (nex3n-firmware-hacking.md line); BP header
- date: 2026-10-05
- relates: Section C, contradiction (c) item 22

### C-NR-020: NR, YAP and coring branch on the picture-effect number (9 = special hi_gain and apgain; 1/4/5/9 = coring corrections from `0x3001e+0x44..0x58`; 8/0xC = threshold `0x3000c+0xAA`); the mapping of effect numbers to menu names is not established (no enum in libObj)
- status: verified-code (branching); unknown (mapping)
- evidence: code branches
- source: BP 3 "Picture effect в коде"
- date: 2026-10-05
- relates: C-FX-015

### C-NR-021: Toy Camera vignette = a radial gain curve (function 0x24a408, string `CalcLensShdGainToy`), 32 nodes from centre to edge at `0x00030040+0xA2..+0xE1` (u16, 0x2000 = 1.0), stock linear from `2000 1F17 ...` down to `04C0 03D7` (edge 0x3D7 ~ -3.06..-3.1 EV); `+0xE0` doubles as a floor in one branch; `+0xE4` = 0x100 slope scale; two alternate curves `+0x00..+0x3F` and `+0x40..+0x7F` (currently zeros) are mixed by a runtime byte (+-16), probably Toy sub-modes
- status: verified-code
- evidence: function 0x24a408; bytes
- source: BP 3; FXP 4
- date: 2026-10-05
- relates: C-NR-022

### C-NR-022: Plan PE-1: replace the Toy curve by a quadratic fall `g_i = 1 - 0.35*(i/31)^2` (edge x0.65, -0.62 EV); the curve is separable only as data, it runs only in Toy Camera mode, which also brings Toy colour (probably one of the `0x30001` slots) and tone (k15..k19 in p3); node-to-radius mapping (node ~ r) is a hypothesis; in the output JPEG the drop may be stronger because the Toy S-curve is added
- status: hypothesis
- evidence: plan; blob `00030040_PE1.hex`
- source: BP 3; FXP 0, 4
- date: 2026-10-05
- relates: C-NR-021, C-FX-031

### C-NR-023: Lens shading correction is computed in `Camera::YC::SHD` (`CalcLensShdGain`, `GetLensShdGain`, `GetShdTblData`) from lens tables plus per-unit trim (`0x30036..38`, `0x30042/43`, attr 0x0a); there is no user "vignette strength" in Backup, only master gate `0x00030033+0x00 = 01` (if !=1, 0x24999c returns shading mode 0 = off; may also remove colour corner correction, so coloured corners possible)
- status: verified-code (gate); hypothesis (side effects)
- evidence: 0x24999c
- source: BP 4
- date: 2026-10-05
- relates: C-ISP-012

### C-NR-024: The simulator does not model distortion correction, vignetting, sharpening/NR, DRO, or auto-WB
- status: verified-code
- evidence: SIM 6
- source: SIM 6
- date: 2026-10-05
- relates: none

### FX: picture effects and creative styles

### C-FX-001: The menu hides Creative Style IDs 6..12 (Neutral, Clear, Deep, Light, Night Scene, Autumn leaves, Sepia) with an unconditional loop in `lib/viewUnified2.so` init of view `view/CAMERA_CREATIVE_STYLE` (0x44374; loop over table `{6,7,8,9,0xa,0xb,0xc}` at 0x65768, helper 0x442f0 calling menu vfunc +0x74 and +0xa0 = `setItemValid(item,false)`); the loop checks neither model, Backup, inhibit table nor av-cam; initial item state is valid=1 for all 13
- status: verified-code
- evidence: disassembly; `CmnViewMenuData::setItemValid` exported wrapper at libObj 0x5ab5db calls the same vfunc +0xa0
- source: HS 0, 1
- date: 2026-10-06
- relates: C-FX-002, C-FX-003

### C-FX-002: NEX-6 v1.03 has the same loop, table and 13-item list (function bodies equal by instruction); NEX-6 officially offers only Standard, Vivid, Portrait, Landscape, Sunset, B/W; so 3N vs NEX-6 comparison could not find a difference; 13 styles and Style Box appeared later (a6000/A7)
- status: verified-code
- evidence: NEX-6 `viewUnified2.so` 0x3158c/0x31568, table 0x5fa98; `master_rec.uxc`/`viewCameraCreativeStyle.uxc` identical byte for byte; spec quoted from two external sources
- source: HS 0, 2
- date: 2026-10-06
- relates: C-FX-001

### C-FX-003: No runtime parameter decides the hiding; the 18 flags `0x0107xxxx` set earlier on the camera (NEX-6 style values) did not unlock the styles because nobody reads them on this path; `DefInh::sm_refTbl` rows are identical for visible and hidden styles (greyout only)
- status: verified-hw (flags had no effect); verified-code (nobody reads them)
- evidence: past experiments plus code
- source: HS 0 item 4, 1; BP 6
- date: 2026-10-06
- relates: C-FX-001

### C-FX-004: Style Box, Watercolor and Illustration are not wired into any menu on 3N or NEX-6: UI strings (`Style Box` 0x9c1, Watercolor 0x10e0, Illustration 0xf66/0xf87/0x103e/0x1177) and libObj parameters (`PARAMID_WATERCOLOR_EFFECT_LEVEL`, `PARAMID_ILLUST_EFFECT_LEVEL`, `COLOR_MODE_MEMORY_NUM(_TYPE)`) exist, but no menu item structure in any `lib/*.so` references their string IDs (search of 32-bit IDs `0x0200xxxx`)
- status: verified-code
- evidence: search over all `lib/*.so` of both models
- source: HS 4
- date: 2026-10-06
- relates: C-FX-006

### C-FX-005: Menu item -> style value mapping (function 0x434e4 covers all 13): Standard 1, Vivid 2, Neutral 3, Portrait 4, Landscape 5, B&W 6, Clear 7, Deep 8, Light 9, Sunset 0xa, Night 0xb, Autumn 0xc, Sepia 0xe (0xd unused); item IDs 0..12 = Standard, Vivid, Portrait, Landscape, Sunset, B&W, Neutral, Clear, Deep, Light, Night, Autumn, Sepia
- status: verified-code
- evidence: HS 1 data tables, HS 6.3 function
- source: HS 1, 6.3; HSR 1.1
- date: 2026-10-06
- relates: C-CTRL-003

### C-FX-006: The selection call is `requestModelExecute("model/CAMERA", 0x26, {0x17f: style, 0x182, 0x185, 0x188: contrast/saturation/sharpness})` (0x448c8); the value goes through libObj `pvt_ColorModeParamApp2Obj` (0x94c51c, 15 values) to `MSGID_SET_COLOR_MODE_CMD` in av-cam; userland would pass values 3/7/8/9/0xb/0xc/0xe without model limits; what av-cam does with them is unknown
- status: verified-code (userland path); hypothesis (av-cam behaviour)
- evidence: 0x44838, 0x448c8, 0x434e4
- source: HS 6.3
- date: 2026-10-06
- relates: C-FX-007, C-FX-009

### C-FX-007: All visible entry paths lead to the same filtered view: Menu -> Brightness/Color -> Creative Style (`ViewBrightColorMenu` 0x5fb9a -> `openView("view/CAMERA_CREATIVE_STYLE")`), custom/soft key with Creative Style (`ViewStlRecClassic` libObj 0x6fb858 case 0xd -> same view, 0x6fb9f4), the Fn view `view/FNSET_CREATIVE_STYLE` is absent (no `viewFnSetCreativeStyle.so` in either rootfs); the 15-item sublist (IDs 0x99..0xa5 + 2 dashes) in `viewUnified4.so` is probably only the value display of the row, and no call opens it as a chooser (Quick Navi and POPUP layout not examined)
- status: verified-code (paths); hypothesis (sublist purpose)
- evidence: addresses listed
- source: HS 6.1-6.4
- date: 2026-10-06
- relates: C-FX-001

### C-FX-008: Greyout of menu items is separate from hiding: `getModelInfo("model/INH_WRAPPER", ...)` with feature codes 0xfa..0x108 -> `DefInh::sm_refTbl` (0x43388), `Bkup_Read(0x01070316)` (0x4345c), and `ViewBrightColorMenu::isItemGreyout/setGreyOut`
- status: verified-code
- evidence: addresses listed
- source: HS 1, 6.3
- date: 2026-10-06
- relates: C-FX-001

### C-FX-009: The 7 hidden styles have no dedicated parameters in Backup: `0x300af+0x70` gives them `ff` (no slot); the colour block has no 7 distinct matrices (C-COL-038); per-style slider defaults are neutral. Most probable result if a hidden value is forced around the menu: hardware takes a default, frame ~ Standard
- status: hypothesis (the consequence); verified-code (its premises)
- evidence: C-BK-009, C-COL-038, C-BK-012; not tested on the camera
- source: HSR 0 items 2-3, 2
- date: 2026-10-06
- relates: C-BK-009, C-COL-038; supersedes HS/BP statement "parameters for hidden styles seem to exist (17 matrices)"

### C-FX-010: Slot selection follows the menu position index (item ID) rather than the style value: slots Standard 0, Vivid 1, Portrait 2, Landscape 3, Sunset 4 equal item IDs; the sharpness table `0x300af+0x70` uses the same index
- status: hypothesis
- evidence: coincidence of measured slots with item IDs; conflicts with the colour-mode path in SE/SYM (`menu_style_to_colormode` = value-1 gives Portrait 3, Landscape 4, Sunset 9)
- source: HSR 1.1; SE; SYM 3
- date: 2026-10-06
- relates: C-CTRL-004, C-COL-029; contradiction (c) item 8

### C-FX-011: Hidden-style renders (Neutral chroma 0.72 + k1, Clear 1.06 + k14, Deep 1.30 + k15, Light 0.85 + k17, Night 0.95 + k0, Autumn 1.12 + k14 + warm, Sepia 0 + warm tone) are guess renders from published character, not 3N parameters
- status: hypothesis
- evidence: `render_hidden.py`; sheets `hidden_styles_*.jpg`
- source: HSR 3
- date: 2026-10-06
- relates: C-FX-009

### C-FX-012: The Picture Effect menu list (`viewUnified2.so` items @ 0x5aef4): Off, Toy Camera, Pop Color, Posterization Color/B&W, Retro Photo, Soft High-key, Partial Color x4, HC Mono, Soft Focus, HDR Painting, Rich-tone Mono, Miniature
- status: verified-code
- evidence: item table
- source: HS 4
- date: 2026-10-06
- relates: C-FX-013

### C-FX-013: Retro Photo, Soft High-key and Rich-tone Mono are HAPI filters (`Start_Art_Effect`, `Start_Richtone_Monochrome`) with parameters outside `0x0003`; mono effects (HC Mono, Rich-tone Mono) have no grain code
- status: verified-code (names); hypothesis (details)
- evidence: strings; not analysed
- source: BP 3; FPP "Native grain"
- date: 2026-10-05
- relates: C-ISP-008

### C-FX-014: Picture Effect and Creative Style appear mutually exclusive in the Sony menu; the exclusion is imposed in userland, not in av-cam: av-cam has no Style/Effect fork (colour stage always runs with the slot `[0xc3bad724]`; Picture Effect is a separate capture stage selected through `ctx[0x23]`); so with an effect, colour runs with the slot the menu forces (expected Standard = slot 0, matrix applied or neutral is unresolved)
- status: hypothesis
- evidence: static RE of av-cam (no fork found) plus assumed menu behaviour; "one chart shot with Soft Focus settles it"; FXP step B0 and MOR optional list ask the same test
- source: SE "Why the effect disables the style"; FXP 0 item 3, 5.2 B0; MOR "Опционально"
- date: undated
- relates: C-FX-015, C-CTRL-004

### C-FX-015: Effect picture-effect class dispatch: sequencer dispatcher (record 1, 0xc362827e) reads `sel = ctx[0x23]` (class 0..4, ~14 effects collapse to 5 classes) and jump-tables into case0 0xc37deb92, case1 0xc37dfca2, case2 0xc37ea898 (`Stage_SoftFocus`), case3 0xc37df2c0 (one family opening the same YC canvas via 0xc366eb00(2, geom)) and case4 0xc363faa0 (special, multi-frame, own 0x21-way sub-dispatcher 0xc35f8db4); the exact Picture-Effect parameter id is not pinned (camprm block 0xc3abe32c, needs a live dump while toggling the menu)
- status: verified-code
- evidence: addresses listed
- source: SE; FPP "Effect stage class map", "Per-effect vs per-style selector"
- date: undated
- relates: C-FX-014, C-CTRL-008

### C-FX-016: Soft Focus parameters in `0x0003010a`: the level (`ImageParam+0x6C`) picks bytes: level 0 -> `+6,+7,+8`; level 2 -> `+0,+1,+2`; 1 or other -> `+3,+4,+5` (0x465cf8); bytes go unscaled into the DSP param block `+0x28,+0x2C,+0x34` (`+0x30` is not written by ARM); kernels copied with fixed length: `+0x10` and `+0x30` 0x12 B (9 x u16), `+0x50` and `+0x90` 0x32 B (25 x u16); SPICA zones `+0x42..47`, `+0x84..8B` are not in the copy; the same bytes are read by the HAPI preview path; log task `job_YC_CaptureDevelopResizeSftfcs` (develop + resize before Soft Focus)
- status: verified-code
- evidence: 0x465cf8
- source: FXP 3.1
- date: 2026-10-05
- relates: C-FX-017, C-FX-018

### C-FX-017: Soft Focus kernels: 4 low-pass kernels (K1 3x3 near-box, K2 3x3 `9 65 9/10 70 10/9 65 9`, K3 5x5 near-box, K4 5x5 zero edge columns), all taps positive, each sums exactly to 256 (Q8, DC = 1.0, so the effect only redistributes light); K1/K3 probably luma, K2/K4 chroma in 4:2:2 (K2/K4 horizontal sigma ~0.57 x K1/K3)
- status: verified-code (sums, shapes); hypothesis (luma/chroma split)
- evidence: bytes; sigma/MTF numbers in the note
- source: FXP 3.1
- date: 2026-10-05
- relates: C-FX-016, C-FX-019

### C-FX-018: Level bytes in the snapshot: L0 `06 16 10`, L1 `0E 18 08`, L2 `16 1A 00`; b0 grows 6->14->22, b1 22->24->26, b2 falls 16->8->0, and b0+b2 = 22 at all levels; that L0 = menu "Low" is unconfirmed
- status: verified-code (bytes); hypothesis (mapping)
- evidence: bytes
- source: FXP 3.1, 3.4
- date: 2026-10-05
- relates: C-FX-016

### C-FX-019: DSP limits for Soft Focus (from `sony-dsp-isa.md` section 15, ma1co spec; not read here): each kernel sums to exactly 256 else error `0xeeee0008/09`; each level byte <=64 and the sum of the three <=64 else `0xeeee0004`; pass order is the 3x3 pair once, then the 5x5 pair twice (the earlier conclusion was the opposite); all designed blobs pass the check
- status: verified-code
- evidence: appendix of FXP (derived from DSP disassembly by the note author)
- source: FXP "Поправка 05.10 23:20"
- date: 2026-10-05
- relates: C-FX-017; contradiction (c) item 13

### C-FX-020: How the three level bytes mix blurred and sharp is undecided: H-A (b0 = strength, alpha ~ b0/32), H-B (b0, b2 = weights of big and small kernel, b0+b2 = 22 constant), H-T (b2 = luminance threshold above which it glows); b1 (22..26) = radius, number of passes or gain; whether the blur works on a downscaled copy and the number of passes are unknown
- status: hypothesis
- evidence: reasoning; discriminating tests proposed (loss of detail 0.81/0.56/0.31 under H-A etc.)
- source: FXP 3.2, 3.3
- date: 2026-10-05
- relates: C-FX-016

### C-FX-021: Pro-Mist plan: probe `0003010a_SFprobe.hex` writes three one-factor variants of the stock Low/Mid/High (`03 16 10`, `06 1A 10`, `06 16 00`) in one write; then `promistA` or `promistB` replaces only Low (+0x06..+0x08); Mid/High must match the baseline (built-in check)
- status: hypothesis
- evidence: plan
- source: FXP 3.4, 5.2
- date: 2026-10-05
- relates: C-FX-020

### C-FX-022: Picture effects are one-of-N menu items, so Soft Focus (haze) and Toy Camera (vignette) cannot be combined; global NR and sharpness act under all effects; vignette is only reachable inside Toy Camera
- status: verified-code
- evidence: one Picture Effect selector in the menu list
- source: FXP 0 items 1-2
- date: 2026-10-05
- relates: C-FX-012, C-NR-022

### C-FX-023: Miniature parameters live in `0x00030109` and Soft Focus parameters in `0x0003010a`; both said to be tunable via `bk w`; SA-module interface and "effect map DSP vs ISP" are in `nex3n-sa-interface.md` (not read here)
- status: hypothesis (tunability; only the Soft Focus layout is backed here, C-FX-016)
- evidence: RD and IDX summary lines only
- source: RD; IDX (nex3n-sa-interface.md line)
- date: 2026-10-05
- relates: C-FX-016

### C-FX-024: There is no native film-grain generator in av-cam or the SA modules (numeric sweep for PRNG/LCG/xorshift found only the AAC LCG; the only noise code is subtractive NR tables, audio PNS, and the H.264 SEI film-grain validator that is never baked into pixels); grain would need synthetic injection
- status: verified-code
- evidence: sweep over av-cam and all `sa_*.bin`
- source: FPP "Native grain"
- date: 2026-10-07 (banner date; text older)
- relates: C-FX-025

### C-FX-025: The ARM grain hook (wrapper on `Stage_SoftFocus`) does not reach the SOOC JPEG because the DSP owns the YC buffer (handle-addressed); reliable grain needs DSP-side injection into `idt_cam` VLIW `0xe800..0x13000` (`dsp-grain-campaign.md`, not read here); the colour half of the film-preset plan is unaffected
- status: hypothesis (stated as fact in the banner; underlying note not available to this extractor)
- evidence: warning banner of FPP dated 07.10.2026; README (older text) still says grain works via the hook
- source: FPP banner; RD "Grain"
- date: 2026-10-07
- relates: C-FX-024; contradiction (c) item 26

### C-FX-026: Plan C (recommended in SE): write the film colour matrix into the slot the menu forces under an effect (Standard, via `0x30001` + `0x30008`), then colour from Standard applies under grain; Plan B: force the slot at the builders (`movs rX,#<slot>` at 0xc3507b78/capture, 0xc35084a8/extract, monitor 0xc3507128 and 0xc35074ac; 2 bytes each, via LZPT p3 flash; stops in-camera style switching); Plan B-gated: detour at 0xc3507b78 to a stub that forces the slot only when Soft Focus is active (needs the current-effect global, candidate near 0xc3abe32c)
- status: hypothesis
- evidence: plan; nothing written
- source: SE "How to get colour + grain together"
- date: undated
- relates: C-FX-014, C-CTRL-004

### C-FX-027: Two-menu model (plan): Creative Style list = clean film colours, each Picture Effect = film colour + grain; per-effect colour via the colour-builder slot override; Soft Focus Low/Mid/High -> three presets (Phoenix 200 / UltraMax 400 / House 800) if the level is readable at the hook; Miniature has its own stage; Toy/Pop/Posterization are "ISP blocks" (colour override works, grain harder); menu renames in `string_*.uxc` on p8 (same method as "Soft Focus"->"Film Grain"); up to 13 slots only if the hidden-style loop in `viewUnified2.so` is patched
- status: hypothesis
- evidence: plan
- source: FPP
- date: 2026-10-07
- relates: C-FX-026, C-ISP-008

### C-FX-028: Toy Camera colour is probably one of the `0x30001` matrix slots and its tone one of k15..k19 in p3; finding the slot needs one frame with tag matrices
- status: hypothesis
- evidence: BP 3 "Оговорка"; FXP 0
- source: BP 3; FXP 0 item 2
- date: 2026-10-05
- relates: C-TONE-007, C-NR-022

### C-FX-029: The owner's SOOC recipe "warm film" (confirmed 2026-07-09 on DSC09256-09264): Portrait, Contrast +1, Saturation -1, Sharpness -1, WB 6000 K A+2, DRO OFF, +0.3 EV; Contrast -3 gives flat milk, Sat +1 digital zing; this was before the Backup/tone work
- status: verified-hw (visual, subjective comparison to refs)
- evidence: frames and exiftool check line in REC
- source: REC
- date: 2026-07-09
- relates: C-BK-012, C-TONE-004

### C-FX-030: NEX-3N has no Memory Recall; contrast/saturation/sharpness are remembered per style; WB, DRO and exposure compensation are global and sometimes reset (battery pull, mode change) and must be rechecked at power-on
- status: verified-hw
- evidence: owner experience
- source: REC
- date: 2026-07-09
- relates: C-BK-012

### C-FX-031: Whether a Picture Effect also disables the film matrix of the style (Soft Focus shot under a Portra style versus Standard) is an open test
- status: unknown
- evidence: listed as optional check in MOR; FXP step B0 records whether Creative Style stays selectable
- source: MOR "Опционально"; FXP 5.2 B0
- date: 2026-10-06
- relates: C-FX-014

### CTRL: parameter path menu -> Backup -> av-cam

### C-CTRL-001: Each frame, four builders (0xc60c6, 0xc6430, 0xc6b12, 0xc7452; the last called from `ExtractCaptureData` 0x2e8820, plus 18 per-mode handlers 0x2e8896..0x2e93f0, and 0x2b1b4/0x2b01e probably monitor/preview) put a pointer to the RAM copy of `0x30001` or `0x30008` into the colour descriptor; ARM does not copy the matrix
- status: verified-code
- evidence: addresses listed; SE names them `colorprm_build_capmode` 0xc3507b13, `colorprm_build_extract` 0xc3508453, `colorprm_build_A` 0xc35070c7, `colorprm_build_B` 0xc3507431 and says T[0] = RAM base (bank chosen by `[0xc3cab360+3]`)
- source: SYM 2; SE
- date: 2026-10-05
- relates: C-BK-006, C-COL-028

### C-CTRL-002: Style selection chain: menu byte `0x01070175` -> `liro_read_creative_style` (0x2a0f2a) -> `menu_style_to_colormode` (0x29dd1a; colour mode = menu value - 1) -> camera params `0x4039` (mode) and `0x403a/b/c` (sliders) -> handler 0x20fde -> `0xc3abe32c+4/+8/+9/+0xa` (the camprm picture/colour block; registry `{flag,pid,setter}` x207 at 0xc3968d08..0xc39696bc, colormode pid 0x4039 setter `camprm_set_colormode` 0xc3461fdf)
- status: verified-code
- evidence: addresses listed
- source: SYM 3; SE; FPP
- date: 2026-10-05
- relates: C-BK-013, C-CTRL-004

### C-CTRL-003: Style value -> (contrast, saturation, sharpness) BKID triple (all 13 styles present): v1 0735/0742/074f, v2 0736/0743/0750, v3 073e/074b/0758, v4 073a/0747/0754, v5 073b/0748/0755, v6 073d/-/0757, v7 073f/074c/0759, v8 0740/074d/075a, v9 0741/074e/075b, v10 073c/0749/0756, v11 0737/0744/0751, v12 0738/0745/0752, v14 0739/-/0753 (prefix `0x0107`)
- status: verified-code
- evidence: jump table; names resolved through C-FX-005
- source: SYM 3
- date: 2026-10-05
- relates: C-BK-011, C-FX-005

### C-CTRL-004: The colour slot byte used by all four builders is one global `[0xc3bad724]` -> `T[6]`; read sites capture 0xc3507b78 (`00 7a`), extract 0xc35084a8, monitor 0xc3507128 and 0xc35074ac; it is fed from the colour-mode param 0x4039 through parameter pointer tables `0xc381a6a4/0xc381aa54` (registry copy, direct writer not found). This conflicts with the measured slot map (Portrait 2, Landscape 3, Sunset 4) if the byte equals mode = value-1 (3, 4, 9): some mapping between mode and slot must exist or the global is not the mode
- status: verified-code (global and read sites); unknown (writer and mode->slot link)
- evidence: SE; HSR 1.3 states the link "mode (0xc3abe32c+4) -> slot" was not found in ARM; reads of 0x300af are data-pool only
- source: SE; HSR 1.3; SYM 3 item 3
- date: undated
- relates: C-COL-003, C-FX-010; contradiction (c) item 8

### C-CTRL-005: Tone selection chain (partial): the colour mode reaches parameter-struct fields `+0x4f` (style curve index) and `+0x48` (enable), `+0x4c` contrast 0..6, `+0x4a` base, `+0x4d/+0x4e` k7 family and one more index; 0x2d7e38 (monitor) / 0x2d7f88 (capture) copy them to `obj+0xbe1/0xbd5/0xbdb/0xbd9`; `tone_lut_build` reads the style curve from table `0xc3cb68a0[idx]`; the link "colour mode -> curve index" (between `0xc3abe32c` and `+0x4f`) is not found
- status: verified-code (copies); unknown (link)
- evidence: addresses listed
- source: SYM 0 item 4, 3
- date: 2026-10-05
- relates: C-TONE-006

### C-CTRL-006: NR level and the NR mode are runtime bytes set by code, not Backup (`CommonRam+0x15C`); the ISO used by G-NR is `obj+0x14E`, by YKNR/Apacon `obj+0x5C6`
- status: verified-code
- evidence: BP 1.1, 8
- source: BP
- date: 2026-10-05
- relates: C-NR-004, C-NR-007

### C-CTRL-007: Apacon style/mode-dependent register writers: `YC_SetModeDependent_Sunset` (0x464daa) writes `0x78b0..0x78bf`; ARM sets registers per style from the `0x00030106` ladders
- status: verified-code
- evidence: 0x464daa, 0x464958
- source: SYM 4; BP 2.2
- date: 2026-10-05
- relates: C-NR-017, C-NR-018

### C-CTRL-008: Picture effect path in av-cam: no direct Picture-Effect literal; capture path carries only the class `ctx[0x23]`; to bind per-effect behaviour a live senser dump of `0xc3abe32c..0xc3abe370` while toggling the menu is required
- status: unknown
- evidence: FPP
- source: FPP "Per-effect vs per-style selector"
- date: undated
- relates: C-FX-015

### C-CTRL-009: Menu -> Backup writes in userland use `Bkup_Read(0x01070316)` (0x4345c) and one more `Bkup_Read` at 0x449de in the Creative Style view; their role (greyout/default read) is not examined further
- status: verified-code
- evidence: addresses listed
- source: HS 1
- date: 2026-10-06
- relates: C-FX-008

### C-CTRL-010: Where Sunset AWB warmth enters the path is unknown: the colour-mode structure `0xc3abe32c` is read by `0x2001a` (`fn_1feec`, group copy) and `0x2217a`; the AWB link would pass there (guess); no `AWB` strings in av-cam; the WB strings there belong to panel/EVF (`ADJ_CMD_AVBB_*`, `PBEH:wb_r/b`)
- status: unknown
- evidence: SYM 4
- source: SYM 4
- date: 2026-10-05
- relates: C-COL-032

### ISP: hardware stages vs DSP (as far as the notes say)

### C-ISP-001: The capture YC job chain is named by the signature `Camera::YC::job_YC_ModeMain(...)`: Pfr, Dg, Itp, Cas, Clp, Nr, Yap, Shd, ShdOff, Adj, Mov, Lga, Gra; the YC pipeline starts from raw data, tone and colour go through separate hardware blocks; the notes do not say which of these jobs are fixed-function ISP and which are SA-DSP
- status: verified-code (names); unknown (placement)
- evidence: log/signature strings
- source: OQ 2.2; NE 1.2
- date: 2026-10-05
- relates: C-TONE-028

### C-ISP-002: Tone LUT: ARM (`tone_lut_build` 0x2d6996) computes 96 Y nodes, then writes them to hardware: LUT at `0xf4015300` (0x180 B) with segment params `0xf4015494..+4b4` and gamma-block registers `0xf4015480, +484, +488, +4b8` (monitor via 0x37d6d8/0x37d6ec; capture via 0x37ddb0/0x37ddc8 into an image of registers `[0xc3cbe0a4]+0x80..`); i.e. tone is a fixed-function hardware LUT programmed by ARM, node grid is shared 96 points with 9 segment params
- status: verified-code
- evidence: addresses listed
- source: NE 1.3; OQ 2.2; TC 1
- date: 2026-10-05
- relates: C-TONE-021, C-TONE-023

### C-ISP-003: A second hardware tone LUT exists (`0xf401c700` 96 x u16, `0xf401c800`), used when `obj+0xC71 == 9`
- status: verified-code
- evidence: C-TONE-022
- source: NE 1.3
- date: 2026-10-05
- relates: C-TONE-022

### C-ISP-004: Colour matrix and hue stage: the colour "develop" stage is run by the SA/DSP YC engine (VLIW, not decoded) with the descriptor built by ARM; the block pointer and slot byte T[6] are the only ARM contribution; in addition a hardware 3D LUT exists whose buffer `Create3DLUT` fills from a reference LUT scaled by Level
- status: hypothesis (DSP attribution, from absence of ARM access); verified-code (3D LUT buffer fill)
- evidence: C-COL-026, C-COL-028
- source: SE; SYM 2; SIM 4
- date: 2026-10-05
- relates: C-COL-026, C-COL-028

### C-ISP-005: Pipeline order established with RAW+JPEG pairs: raw -> white balance coefficients (SR2 RGGB levels) -> 3x3 slot matrix in linear light -> base gamma (11->10 bit, row 0 col 1) -> contrast curve and/or style curve per RGB channel -> YCbCr 601 chroma x style boost x (1+0.13*Sat) -> residual hue/sat stage (hue records, empirically modelled) -> 8-bit sRGB; placing the colour stage before or after the tone curve is indistinguishable (2.60 vs 2.61)
- status: verified-hw (matrix before tone, per-channel curves, Sat factor); hypothesis (hue-stage position and boost)
- evidence: SIM 2
- source: SIM 2, 3
- date: 2026-10-05
- relates: C-COL-006, C-TONE-009, C-TONE-011

### C-ISP-006: Highlight hold above Y' ~200 acts after the tone LUT and sees the base (standard) signal; no ISP/DSP block is identified
- status: hypothesis
- evidence: C-TONE-026
- source: NE 1.4
- date: 2026-10-05
- relates: C-TONE-026, C-TONE-028

### C-ISP-007: Soft Focus is carried out by the DSP module `sa_sftfcs` (VLIW part undecoded); ARM only fills its parameter block and the kernels (3x3 pair then 5x5 pair twice); the same Backup bytes drive the preview path
- status: verified-code (ARM side); hypothesis (what the DSP does)
- evidence: FXP 0 item 4, 3.1; FXP appendix
- source: FXP
- date: 2026-10-05
- relates: C-FX-016, C-FX-019

### C-ISP-008: Effect-to-engine map as the notes state it: Soft Focus (class case2 `Stage_SoftFocus`) and Miniature = DSP/own capture stage; Toy/Pop/Posterization etc. = "ISP blocks" (colour override works, grain harder); Retro Photo, Soft High-key, Rich-tone Mono = HAPI filters; case4 (HDR/multi-frame class) special
- status: hypothesis (ISP/DSP attribution is asserted without evidence in FPP); verified-code (class case numbering and HAPI strings)
- evidence: FPP; BP 3; the detailed DSP-vs-ISP table is in `nex3n-sa-interface.md` (not read)
- source: FPP "Two-menu model", "Effect stage class map"; BP 3
- date: 2026-10-05
- relates: C-FX-015, C-FX-027

### C-ISP-009: NR stages KKNR/YKNR are SA noise-reduction modules that consume the ADF noise table (`[ADF]...NOISE TABLE...`, subtractive); G-NR/C-NR parameters are assembled by ARM (`nr_gnr` log) and passed on
- status: hypothesis
- evidence: FPP wording "kknr/yknr NR modules consume it"; no module-level analysis in the source set
- source: FPP "Native grain"; BP 1.1
- date: 2026-10-05
- relates: C-NR-001

### C-ISP-010: Sharpness: the Apacon registers `0x78b0..0x78bf` are written by ARM per style (`YC_SetModeDependent_*`), the YAP/coring parameters are tables evaluated by ARM per ISO (`job_apc_*_stl` 0xd4334, 0xd32ce) and passed to the YC job `Yap`; hardware or DSP execution is not stated
- status: verified-code (ARM side); unknown (executor)
- evidence: addresses listed
- source: BP 2; SYM 4
- date: 2026-10-05
- relates: C-NR-014, C-NR-017

### C-ISP-011: Lens shading: ARM computes the gains (`CalcLensShdGain`, `CalcLensShdGainToy` 0x24a408, `GetShdTblData`) for `Camera::YC::SHD`/`ShdOff`; executor not stated
- status: verified-code (ARM side); unknown (executor)
- evidence: strings
- source: BP 3, 4
- date: 2026-10-05
- relates: C-NR-021, C-NR-023

### C-ISP-012: The simulator's omitted effects (distortion correction, vignetting, sharpness/NR, DRO, auto-WB) mean the offline model does not describe the JPEG engine's spatial stages at all
- status: verified-code
- evidence: SIM 6
- source: SIM 6
- date: 2026-10-05
- relates: C-NR-024

---

## Section C. Current state of the camera according to the notes (as of the latest note, 2026-10-05..07)

| item | state | basis | confidence |
|---|---|---|---|
| Backup `0x00030001` + `0x00030008` | v5 looks (Vivid=Portra 400, Portrait=House, Landscape=UltraMax 400, Sunset=Phoenix II); rollback file `00030001_v5_rollback.hex` (= `work/bk/00030001_looks_v5.hex`); v6, `v6_phoenixsky`, `v6_kodakwarm` prepared but NOT written as of 05.10 | MOR "Состояние камеры на старт", V6 header ("НЕ записан"), FXP 0 | high as of 06.10 morning; later sessions unknown (MOR Session 1 may have written v6; no result in these notes) |
| p3 av-cam tone region | film curve in k0 (Contrast -3) written 05.10: sectors 8849-8886, md5 921f2345.., whole p3 d7cca446.. (= `p3_fit.bin`); original sectors md5 186bf30f.. in `p3_orig_sect_8849.bin`; rollback = rewrite those 38 sectors and reset WBI | TC | high (read-back verified) |
| p5 sector 0 | was `WBI1...` (md5 7b671539.., copy `work/tone/p5_sector0_before.bin`), zeroed after the p3 write (fast-boot snapshot reset) | TC | high |
| `0x0003007a` (tone debug) | stock (mode 0); mode 1/2 blobs prepared, not written ("по коду проверено, на камере нет") | SYM 7-8, MOR | medium-high |
| `0x00030106` Apacon ladder | disputed: experiment 04.10 changed step 5 (80->32); IDX says it is still changed, BP calls its snapshot "post-revert" | BP 2.2, IDX | low, verify with `bk r 00030106` |
| NR (`0x30010/b4`, `0x3001b/be`, `0x3004a`, hi_gain tables), sharpness (`0x3000c/b0`, `0x3000d/b1`), vignette `0x30040`, Soft Focus `0x3010a`, `0x30033`, `0x30056` | unchanged from `Backup_post-revert.bin` (snapshot 2026-10-04 20:11); "no proposed change was tested on the camera" | BP header, FXP 0 warning | medium (relies on the claim that after the snapshot only 0x30001/08 and p3 were written) |
| calibration blocks (`0x30002`, `0x00bc*`, `0x0132*`, attr 0x0a) | untouched, by policy | all notes | medium |
| Grain hook in p3 / menu rename "Soft Focus"->"Film Grain" on p8 | UNKNOWN from this source set: README and FPP describe a hook and an in-place string rename as done operations, but `grain-hook.md`, `live-memory-and-delivery.md`, `dsp-grain-campaign.md` were not read, and the state of these flashes on the camera is not stated; FPP banner 07.10 says the ARM hook does not reach the JPEG | RD, FPP | low |
| Session summary line | "пауза 05.10: цвет v5 + плёночная k0 в камере; интерес — DSP" | MEMORY.md index entry "nex3n firmware hack status" | matches rows 1-2 |

---

## Section D. Contradictions between the notes (c)

1. Timing of Backup writes. SYM 0/2: a write is copied to the RAM cache at once, colour experiments took effect without reboot. FXP 0: after `bk w ... bk s` a reboot (leave updater) is needed because "values are read at start". Possibly both true (sync vs cache), unresolved. Claims: C-BK-002, C-BK-003.
2. Role of `0x0003007a`. TC 0 item 4 and TC 3: it is a 96-node sampling grid, "tone cannot be changed through bk w", null test expected. SYM 3 and 8.1: stock = (X+1)/2, in mode 1 it is the Y values, mode 2 overrides indices; SYM states it corrects TC. TC was not edited. Claims: C-TONE-015, C-TONE-016, C-TONE-020.
3. Tone composition and slot table. TC 1: `y = Cstyle[Cgroup2[Ccontrast[base]]]` ("order approximate"), styles in slots 14.. as `k14,k15,k16,k17,k18,k20,k19,k20..`. SYM 7.1: priority selection (k7 family > contrast > style > base; style curve not applied if contrast is on) and slots 14..27 = `k20,k14,k15,...` (style index 0 = k20, index 1 = k14). Untested against frames: that Vivid at Contrast != 0 loses its S-curve (SYM marks it a hypothesis about the menu). Claims: C-TONE-005, C-TONE-006, C-TONE-010.
4. Base gamma size. TC 1: base 1024 -> 1024; SYM 8.1: 2048 -> 1024 with a 13-value tail. Claim: C-TONE-012.
5. Highlight floor cause. OQ 2.3 proposed makernote `0x9405a+0x68a` toggling with any curve; NE 1.1 refuted it (A/B alternate independently in 67 frames; OQ's own correction banner exists). Claim: C-TONE-027.
6. Portrait curve and slider defaults. TC (measured): Portrait style curve = k1 (Contrast -2 equivalent). HSR 1.5: stock Portrait default sliders are +1/-1/-1, "consistent with k1" — but Contrast +1 is k4, not k1. Further, REC says the owner parked exactly C+1/S-1/Sh-1 on Portrait (Creative Style stores sliders per style), so the Backup values in the snapshot may be the owner's setting, not a factory default. Which setting the 09500 wedge was taken at is not stated. Claims: C-BK-012, C-TONE-004.
7. Number of matrices. BP 6 and HS 6.3: "17 matrices in `0x30001`" (parameters for hidden styles apparently exist). HSR 0 item 3: only 10 working matrices in group 1 (6/7 = Standard, 8/9 identical blurred), group 2 has 7, slots >=10 are garbage overlapping the hue zone; no 7 distinct matrices for hidden styles. Claim: C-COL-038.
8. Style slot selection. HSR 1.1: slot = menu position index (item ID), "not the style value". SE/SYM: slot byte `[0xc3bad724]` fed from colour mode = menu value - 1 (Portrait 3, Landscape 4, Sunset 9 in the CC index list OQ 3.3), while measured slots are Portrait 2, Landscape 3, Sunset 4. HSR 1.3 says the link mode->slot was not found in ARM; SE says it found the builders that read the global. The two index spaces (CC colour-mode index vs matrix slot) are not reconciled. Claims: C-COL-029, C-FX-010, C-CTRL-004.
9. Sunset warmth. RD: "a shift of the auto-WB target, not a processing stage". OQ 3: a linear per-channel multiplier applied after the AWB coefficients are recorded, inside the colour module, not visible in WB_RGBLevels. SYM 4: location not found, AWB path not walked. Claims: C-COL-030..032.
10. Consumer of hue records. HT: `Create3DLUT` receives the whole block pointer, LUT 5x9x9 "apparently built from matrix and these records". SIM 4 (emulation): `Create3DLUT` does not read `+0x100` records, only copies and scales a reference LUT. The camera nevertheless responds to the records (verified-hw), so the consumer is elsewhere. Claims: C-COL-026, C-COL-027.
11. Style chroma boost. RD: Vivid +11 %, Landscape +14 %, Sunset +14 %, Portrait none. SIM 2: Vivid x1.06, Portrait x1.11, Landscape x0.96, Sunset x1.07 (the rest is explained by native Q1 differences). Claim: C-COL-012.
12. Apacon 0x78B0. BP presents it as sharpness; the 04.10 step-5 experiment changed Sunset saturation (BP 2.2: "contradiction not resolved"); SYM 4: Sunset-specific function writes those registers. Claims: C-NR-017, C-NR-018.
13. Soft Focus pass order. FXP main text: older conclusion; FXP appendix: 3x3 pair once, 5x5 pair twice, "old conclusion was the opposite" (main text not corrected). Claim: C-FX-019.
14. NR-4 relation. BP 1.5: fine step after NR-1..3. FXP 1: dosed alternative to NR-1. Claim: C-NR-012.
15. SH-1 strength. BP 2.3: `B0 -> 40` (-64 %). FXP 2: `B0 -> 60` (-45 %), `40` only as next step. Claim: C-NR-016.
16. Hidden styles premise. BP 6 and earlier work compared 3N to NEX-6 expecting a difference; HS 0: NEX-6 also shows 6 styles and runs the same hiding loop, so the premise was wrong. Claims: C-FX-001, C-FX-002.
17. B&W slot. RD: B&W slot could not be identified from a monochrome frame; HSR 2: slot 5 "по схеме" (not measured), matrix about Standard. Claim: C-COL-004.
18. Picture Effect vs Creative Style. FXP: "probably disables Creative Style [hypothesis from other Sony manuals]" and Toy colour likely a matrix slot. SE: the exclusion is in userland, which forces colour mode Standard via 0x4039 (matrix applied or neutral unresolved). Both untested. Claims: C-FX-014, C-FX-031.
19. Contrast on Y or RGB. TC 5 lists "applied to Y or RGB" as open; SIM 0: per channel proven by RAW+JPEG. TC not updated. Claim: C-TONE-009.
20. Create3DLUT stage position. OQ 2.2 treats the 3D LUT as a post-tone colour stage "function of output colour" and excludes it as the highlight-floor source; SIM 4 says the 3D LUT is a static reference LUT whose contribution is hidden in H0/boost, source of the LUT unknown. Not a hard conflict; recorded for the pipeline diagram.
21. Grain hook status. RD: grain "works via wrapper hook plus raw flash of LZPT". FPP banner 07.10: the hook does NOT reach the SOOC JPEG. Claim: C-FX-025.
22. `0x00030106` state. See Section C: IDX says the Sunset step is still altered; BP says the snapshot is post-revert and only `0x30001/08` and p3 were written after it. Claim: C-NR-019.
23. Meaning of the ISO axis. BP 0 hypothesis `0x600 = ISO 200` for G-NR axis; Apacon axis starts at 0x700 and YKNR axis is a different runtime field; scale equivalence not checked. Claim: C-NR-009.

---

## Section E. Which stages the notes assign to fixed-function ISP vs DSP (for the pipeline diagram) (г)

The notes never contain one authoritative ISP-vs-DSP table; the detailed map is said to be in `nex3n-sa-interface.md` (not in this source set). What the sources do say:

| stage | executor according to the notes | how sure | claim |
|---|---|---|---|
| Raw input stages Pfr, Dg, Itp, Cas, Clp (black clamp by OB), Lga (LightLvAdj) | named YC jobs; executor not stated; they sit at the raw input | names only | C-ISP-001, C-TONE-028 |
| White balance gains | applied to camera RGB before the matrix; executor not stated | pairs | C-ISP-005 |
| Colour matrix (slot matrix) | DSP/HAPI side ("SA/DSP YC engine, VLIW, not decoded"); ARM only builds the descriptor | hypothesis | C-COL-028, C-ISP-004 |
| 3D LUT (5x9x9) | hardware buffer filled by ARM `Create3DLUT` from a reference LUT | code | C-COL-026 |
| Hue/sat records `+0x100` | consumer unknown (2-D LUT candidate) | unknown | C-COL-027 |
| Base gamma and contrast/style tone curves | fixed-function hardware LUT (regs `0xf4015300`, `0xf4015480..`, second LUT `0xf401c700`) programmed by ARM `tone_lut_build` | code | C-ISP-002, C-ISP-003 |
| Highlight hold after the tone LUT | unknown stage that sees base signal | hypothesis | C-ISP-006 |
| G-NR / C-NR (YC::NR) | parameters assembled by ARM (`nr_gnr`); executor not stated | code (ARM) | C-NR-001, C-ISP-009 |
| YKNR, KKNR | SA modules consuming ADF noise table | hypothesis | C-ISP-009 |
| YAP / coring / Apacon sharpening | tables and registers written by ARM; executor not stated | code (ARM) | C-ISP-010 |
| Lens shading SHD (and Toy vignette gain) | gains computed by ARM, executor not stated | code (ARM) | C-ISP-011 |
| Soft Focus | DSP module `sa_sftfcs` (develop + resize, kernels 3x3 then 5x5 x2), ARM passes params | code (ARM) / hypothesis (DSP) | C-ISP-007 |
| Miniature | its own stage, parameters `0x30109` (not read) | weak | C-FX-023, C-ISP-008 |
| Toy, Pop Color, Posterization, ... | "ISP blocks" (FPP assertion) | weak | C-ISP-008 |
| Retro Photo, Soft High-key, Rich-tone Mono | HAPI filters (`Start_Art_Effect`, `Start_Richtone_Monochrome`) | code (names) | C-FX-013 |
| HDR painting / multi-frame effects | case4 special class `0xc363faa0` | code | C-FX-015 |
| YCbCr chroma, style boost, saturation slider | measured behaviour only; executor not stated | pairs | C-COL-011, C-ISP-005 |
| JPEG encode | out of this extract's scope | | |

---

## Section F. Gaps (things the notes leave open, worth an unknown claim in the atlas)

- Which stage produces the highlight floor (C-TONE-028) and what it needs as input.
- The consumer of hue records `+0x100` and of the second table pair Q4/Q5 (C-COL-027, C-COL-019).
- The mode -> slot link for colour and for tone-curve index (C-CTRL-004, C-CTRL-005).
- Sunset's AWB warm multiplier (C-COL-032) and Sunset's unmodelled response to the hue records (C-COL-024).
- Meaning of NR level, shooting-mode numbers, picture-effect numbers (C-NR-004, C-NR-003, C-NR-020).
- Semantics of `0x3007a +0xD2..+0xD6, +0xE0..+0xE3, +0xE6` and of mode-9 second tone LUT (C-TONE-021, C-TONE-022).
- Chroma suppression by luminance (shadow/highlight) has no known mechanism (C-COL-021); Fuji-style simulation levers listed in `fuji-film-simulation-research.md` (not read) depend on it.
- Which bank (A or B) is active (C-BK-004).
- Whether a Picture Effect keeps the style matrix (C-FX-031).
- Not read here, but cited by the notes: `nex3n-firmware-hacking.md`, `nex3n-sa-interface.md`, `sony-dsp-isa.md`, `grain-hook.md`, `live-memory-and-delivery.md`, `dsp-grain-campaign.md`, `house-phoenix-looks.md`, `nex3n-safe-test-boot.md`.
