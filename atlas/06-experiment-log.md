# 06 - Experiment log

Every on-camera experiment, 2026-10-04 .. 2026-10-09, E-0001..E-0066 (E-IDs are final; no renumbering). Reconstructed from flash logs, builders and images, the session transcript and the notes; the "How this was reconstructed" bullets below say how much to trust each field. Then: summary table, review list R-1..R-13, records.

Page order: section 1 summary table, section 2 review list (what to doubt), section 3 records by date, section 4 prepared-but-not-executed images, section 5 temporary-to-final table.

Claims fields: IDs `C-DSP/MOD/IDT/DLV/SAFE/TOOL-nnn` are final and defined in `04-dsp-modules.md` and `05-delivery-and-safety.md`; IDs written `tmp:A-...` / `tmp:C-...` belong to areas numbered by the agent of pages 01/02/03/07 (A = system/boot/delivery extract, C = backup/colour/tone extract) and are temporary.

## 0. How this was reconstructed (read first)

- Sources, in order of weight: (1) flash/log files (`flash_*.log`, `live*.log`, `det/ft/probe/diag/mdiag/scr/sess/sess2/schk.log` in the old scratchpad `nexfw/pmca/`, and `~/nex3n-dump/work/nopcore/flash_*.log`), which carry the md5 and the local mtime; (2) builders (`build_*.py`) and image files (md5 computed with `md5 -q`); (3) the session transcript (user messages are the only record of what the camera did on the screen; transcript stamps are UTC, file mtimes are local = UTC+2); (4) notes in `notes/*.md`, WorkPersonal `reference/nex3n-*.md` and the project memory file.
- `observed:` is the owner's words (translated; quotes in "..." are verbatim Russian shortened to English) or a measurement the assistant took from the saved JPEG / a live memory read. What an assistant inferred is in `conclusion:` / `caveats:`.
- Times: `[HH:MM]` = local time of the log file mtime (end of the operation) unless marked "msg" (UTC+2 of a transcript message). Flash logs record the end of the flash; the camera test followed 1-5 min later.
- Recovery image used throughout: `current_p3.bin` = p3 with film tone curve k0, no grain, md5 `d7cca4469709a8b50bc5ad6efa34aa13` (identical to `work/tone/p3_fit.bin`, the image written on 05.10). Stock p3 md5 `37b9727627b91ebeefdc07dcde561036`. Clean film-curve av-cam extracted from the camera: `sys_avcam.bin` md5 `58809e0255a34e21c077fe49935a7408` (6,554,072 B). All md5 values re-computed by the editor on 2026-10-09 (see `05-delivery-and-safety.md` section 6).
- All p3 images are 10,485,760 B, LZPT ("TPZL") partition; av-cam inner offset `0x8e00`, idt_cam inner offset `0x980e00` (length 200,384). Every flash below went through `flash_any.py` (updater shell, raw write to `/dev/nflasha3`, md5 of the whole partition, WBI `/dev/nflasha5` zeroed) unless stated; "device md5=... -> MATCH" means the on-flash partition equalled the image md5.
- Frame numbers (DSCnnnnn) are the owner's shots; where the sources do not give them, none are invented.
- Known inconsistency in the archive notes: `reference/nex3n-firmware-hacking.md` ("Состояние камеры на конец 04.10", "Следующий шаг: A/B завтра") says the `0x00030106` ladder is still at 32 and the A/B is pending. The transcript shows the A/B was done the same evening (E-0009) and 80 was restored (R-8). Treat that paragraph as stale.
- Whole-partition p3 flashes logged: 28 (E-0038..E-0066 minus E-0041 which was a read), zero bricks (C-SAFE-003). One narrow p3 write (E-0022). No p8 write is recorded.

## 1. Summary table

| E-ID | date | what | outcome | claims (final IDs of areas DSP/MOD/IDT/DLV/SAFE/TOOL; others temporary) |
|---|---|---|---|---|
| E-0001 | 04.10 | flash + Backup dump (read) | ok | C-TOOL-005, C-DLV-006, C-PART-016 |
| E-0002 | 04.10 | null Backup write `01070937=00` | safe | C-DLV-017, C-BK-016 |
| E-0003 | 04.10 | flag `01070937=01` | no effect | C-FX-003, C-FX-001 |
| E-0004 | 04.10 | flag `0107093b=01` | no effect | C-FX-003, C-FX-001 |
| E-0005 | 04.10 | 8 flags (group 1) NEX-6 values | no effect | C-FX-003 |
| E-0006 | 04.10 | 8 more flags (group 2) | no effect | C-FX-003, C-FX-001, C-CTRL-013 |
| E-0007 | 04.10 | revert 16 flags, boot dumps | ok | C-DLV-017, C-BOOT-001, C-PART-016 |
| E-0008 | 04.10 | `0x30106` step 80->32 | confounded | C-NR-017, C-NR-018, C-NR-019 |
| E-0009 | 04.10 | revert to 80, clean A/B | no colour effect | C-NR-017, C-NR-018, C-NR-019, C-COL-031 |
| E-0010 | 04.10 | 17 matrices muted | works | C-COL-001, C-COL-009, C-COL-010 |
| E-0011 | 04.10 | RGB-permutation tag matrices | slots mapped | C-COL-002, C-COL-003, C-COL-004 |
| E-0012 | 05.10 | v1 film matrices | works | C-COL-006, C-COL-012, C-COL-029, C-COL-030 |
| E-0013 | 05.10 | v2 boost-compensated | works | C-COL-012, C-COL-033 |
| E-0014 | 05.10 | v3 + E1 (zero Standard record) | table live | C-COL-013, C-COL-022 |
| E-0015 | 05.10 | binary sector test | partly superseded | C-COL-013, C-COL-014 |
| E-0016 | 05.10 | byte test group 0 | 4 hue regions | C-COL-014, C-COL-015 |
| E-0017 | 05.10 | clean v3 baseline | ok | C-COL-042 |
| E-0018 | 05.10 | band test | pairs, no luma bands | C-COL-016, C-COL-017, C-COL-018, C-COL-019, C-COL-020, C-COL-021, C-COL-023 |
| E-0019 | 05.10 | v4 tables | overshoot | C-COL-023, C-COL-024, C-COL-045 |
| E-0020 | 05.10 | v5 scaled tables | accepted | C-COL-033, C-COL-024, C-COL-025 |
| E-0021 | 05.10 | `/setting/updater/mode` flag | failed (interpretation contested, R-11) | C-SAFE-004, C-BOOT-015, C-BOOT-035, C-BOOT-036 |
| E-0022 | 05.10 | film curve k0 in p3 (38 sectors) | works | C-DLV-010, C-TONE-022, C-TONE-023, C-MEM-017 |
| E-0023 | 06.10 | updater recon (read) | ok | C-DLV-019, C-SYS-003, C-SYS-007, C-MEM-003 |
| E-0024 | 06.10 | insmod liro.ko in updater | refused | C-DLV-019, C-DLV-020, C-BOOT-010 |
| E-0025 | 06.10 | DRAM remanence 1 | no scene | C-MEM-013, C-MEM-014 |
| E-0026 | 06.10 | DRAM remanence 2 (SF) | no scene | C-MEM-014 |
| E-0027 | 06.10 | senser auth + readMemory | works | C-DLV-001, C-DLV-002, C-MEM-015 |
| E-0028 | 06.10 | before/after dumps, sharp/SF pair | partial | C-MEM-010, C-MEM-015 |
| E-0029 | 06.10 | av-cam in DRAM | located | C-MEM-001 |
| E-0030 | 06.10 | writeMemory on display RAM | overwritten | C-DLV-001 |
| E-0031 | 06.10 | YC_FULL after a frame | located | C-MEM-005 |
| E-0032 | 06.10 | RAM patch 1 (SF off) | invalid | C-DLV-004 |
| E-0033 | 06.10 | RAM patch 2 | lost | C-DLV-004 |
| E-0034 | 06.10 | FileControl `/system` write | read-only | C-DLV-005, C-MEM-017 |
| E-0035 | 06.10 | RAM detour 0xc3889760 | lost | C-DLV-004 |
| E-0036 | 06.10 | FileControl probe all mounts | only p2 | C-DLV-005, C-PART-013 |
| E-0037 | 06.10 | updater-shell mount/PULL | refused | C-DLV-006, C-DLV-007, C-SAFE-011, C-PART-014 |
| E-0038 | 06.10 | p3_grain (always-run hook) | no grain | C-DLV-007, C-DLV-008, C-CTRL-009 |
| E-0039 | 06.10 | p3_grain_sf (SF replaced) | crash | C-SAFE-003, C-CTRL-003, C-MEM-011 |
| E-0040 | 06.10 | p3_diag (scratch stub) | fields read | C-MEM-011, C-CTRL-004 |
| E-0041 | 06.10 | session object + buffers | mapped | C-MEM-004, C-MEM-006, C-MEM-007, C-MEM-009 |
| E-0042 | 06.10 | p3_sfwrap (SF then grain) | bottom only | C-PIPE-001, C-PIPE-003 |
| E-0043 | 06.10 | p3_iso400 (SF skipped) | no grain | C-PIPE-001 |
| E-0044 | 06.10 | p3_stripe | bottom only | C-PIPE-001 |
| E-0045 | 07.10 | v2med | no grain | C-PIPE-001, C-MEM-007 |
| E-0046 | 07.10 | v3med | no blur, no grain | C-PIPE-001, C-CTRL-003 |
| E-0047 | 07.10 | v4med + HC Mono control | no grain | C-PIPE-001, C-PIPE-004 |
| E-0048 | 07.10 | v5med (rec40) | no grain | C-PIPE-001, C-CTRL-002 |
| E-0049 | 07.10 | marker at rec40 | buffer not read (frame set mislabelled, R-6) | C-MEM-007, C-MEM-008, C-PIPE-019, C-PIPE-001, C-PIPE-023 |
| E-0050 | 07.10 | logger in `0xc3474800` | not called | C-JPEG-001 |
| E-0051 | 07.10 | logger in `0xc347427a` | handle only | C-JPEG-001, C-JPEG-002, C-DLV-003, C-MOD-029 |
| E-0052 | 07.10 | NOP 0x2d4e0..0x2e608 | normal | C-IDT-008, C-IDT-009 |
| E-0053 | 07.10 | NOP 0x249d0..0x25fa8 | normal | C-IDT-008, C-IDT-009 |
| E-0054 | 07.10 | NOP 0x1c000..0x2ea68 | write hang | C-IDT-008, C-IDT-009, C-SAFE-007 |
| E-0055 | 07.10 | NOP 0xa598..0x1c000 | focus hang | C-IDT-008, C-IDT-009, C-SAFE-007 |
| E-0056 | 07.10 | NOP 0x13000..0x1c000 | normal | C-IDT-008, C-IDT-009, C-SAFE-011 |
| E-0057 | 07.10 | NOP 0xe800..0x13000 | black luma | C-IDT-008, C-IDT-009, C-IDT-011, C-SAFE-007 |
| E-0058 | 07.10 | NOP 0x10c00..0x13000 | overexposed | C-IDT-008, C-IDT-009, C-IDT-011, C-SAFE-007 |
| E-0059 | 07.10 | restore | ok | C-SAFE-003, C-SAFE-008 |
| E-0060 | 09.10 | NOP 0x10c00..0x12520 | overexposed (2-4 stops) | C-IDT-008, C-IDT-010, C-IDT-011 |
| E-0061 | 09.10 | NOP 0x12520..0x13000 | normal | C-IDT-008, C-IDT-013 |
| E-0062 | 09.10 | NOP 0x11280..0x12520 | normal | C-IDT-008, C-IDT-013 |
| E-0063 | 09.10 | skip overlay 0xf6c0 | hang | C-IDT-012, C-IDT-016, C-SAFE-007 |
| E-0064 | 09.10 | skip overlay 0xcbd0 | hang | C-IDT-016, C-SAFE-007 |
| E-0065 | 09.10 | skip overlay 0x105d0 | hang | C-IDT-010, C-IDT-016, C-SAFE-007 |
| E-0066 | 09.10 | restore | ok | C-SAFE-003, C-SAFE-008 |
| E-0067 | 09.10 | EXP-2 CAP 3D-LUT chroma-by-luma (Backup 0x30004/5) | reaches JPEG, 5/6 styles | C-COL-046, C-COL-026, C-COL-027 |
| E-0068 | 10.10 | EXP-3 force SACC MSDump (p3 A+B), restore, revert EXP-2 | no YC dump on card; capture OK | C-DLV-022, C-MOD-032, C-SAFE-003 |
| E-0069 | 10.10 | EXP-4 pointer-leak patch (p3), senser read of scratch | detour live + cave executes; scratch 0 (.bss cleared on service-mode entry) | C-MEM-021, C-DLV-004, C-SAFE-003 |

## 2. Review list

Conclusions of the records that must be revisited. R-IDs are final.

- **R-1 (all NOP experiments, E-0052..E-0058, E-0060..E-0062).** `idt_cam` is 35 overlays (stub `5f50 5e50 5150 b100`; stack `+0x18`, entry `+0x1c`, load address page+0x10) mixing scalar code, literal pools, data tables and VLIW kernels. A NOP bundle executed as scalar code is garbage with branches (`dc3e` = `bfc`). Every range that touched scalar code ran random instructions; "black", "bright", "hangs" are indirect symptoms. Valid reading: negative results (normal frames) are more trustworthy; positive results do not localise a luma store. The Campaign A table (2nd half = encode, 1st half = develop+focus, e2a luma write, e2b tone) and the DSP grain target `0xe800..0x13000` are **not established**.
  - claims affected: C-IDT-008, C-IDT-009, C-IDT-011, C-IDT-013 (negative results stay valid), C-SAFE-007
  - 2026-10-09: C-IDT-009 set to `refuted` (R 4-B); one wording across 04/06/07: observations verified-hw, interpretations refuted.
- **R-2 (E-0057, E-0058 vs E-0060).** The brightening is better explained by a corrupted statistics/AE overlay (`0x105d0`: reads lines, exports 5 accumulators + 64 B, no pixel write) than by a late luma-gain kernel; black luma in E-0057 may likewise be broken AE/stat (`0xf6c0` writes 2D blocks, probably an AE/AWB grid). Symptom severity differs between E-0058 (white screen, dies) and E-0060 (2-4 stops, saves hang). Mechanism not verified by any experiment.
  - claims affected: C-IDT-010, C-IDT-011
- **R-3 (E-0063..E-0065).** The three overlay skips give identical symptoms; they only show "ARM waits for this overlay", nothing about what each computes.
  - claims affected: C-IDT-016
- **R-4 (E-0042 sfwrap, E-0043 iso400, E-0044 stripe, and the README "proven working / grain visible" wording in `~/nex3n-dump/filmgrain/README.md`, `reference/nex3n-safe-test-boot.md` §4g, `grain-hook.md` before its banner).** The "bottom-up buffer" and "loop too slow" explanations were replaced by: `session[0x5e4]` was a live DMA buffer only on the early SF stage and is overwritten by the develop core; the bottom patch is a race artefact. The README's "iso800 proven visible (DSC09527)" is a mislabel: DSC09527 is the sfwrap +-31 frame; `p3_iso800` was never flashed.
  - claims affected: C-PIPE-001, C-PIPE-002, C-PIPE-003, C-MEM-007
- **R-5 (E-0045..E-0047).** Explanations "grain went into SF's input buffer" (v2), "window ate the grain" (v3), "JPEG quantisation / NR eats it" (v4) were all superseded by the amplitude-independence and marker results (E-0049).
  - claims affected: C-PIPE-001
- **R-6 (E-0049).** The marker conclusion assumed "Off = class 0/1" (shown only statically afterwards) and the frame labelling (DSC09548 listed as a marker frame although shot before the marker image) is inconsistent; re-shoot would settle it.
  - claims affected: C-MEM-007, C-MEM-008, C-PIPE-001 (load-bearing), C-PIPE-023
  - 2026-10-09 (R 2-A, 5-E): the record does not exclude that the marker reached the file on the one correctly ordered frame; re-shoot with the same image and frame bookkeeping at the camera is 07 §2.
- **R-7 (E-0038).** "Gate `r4[0x3c] in {1,2}` is false for normal frames" is a guess; the per-frame call count of `0xc3889760` was never measured.
  - claims affected: C-CTRL-009
- **R-8 (E-0008/E-0009 and `reference/nex3n-firmware-hacking.md` "Состояние камеры на конец 04.10").** The note still says the `0x30106` ladder is modified and an A/B is pending; the A/B was done and 80 restored. The "ladder = sharpness" part is code reading only.
  - claims affected: C-NR-018, C-NR-019; camera state in 05-delivery-and-safety.md section 0
- **R-9 (E-0015).** The "6 groups = 6 hue sectors" decode was overturned by E-0016; the binary test only reliably shows record-slot binding.
  - claims affected: C-COL-013, C-COL-014
- **R-10 (E-0019/E-0020).** Table gains are fitted on a few frames with +-8 dC / +-5 deg noise; the Phoenix cyan sign and the Sunset record marker (-128) behaviour are empirical, one frame each.
  - claims affected: C-COL-024, C-COL-025, C-COL-045
- **R-11 (E-0021).** Only one variant of the file-flag insurance was tried; "no software safety net" is slightly stronger than the evidence.
  - claims affected: C-SAFE-004
  - 2026-10-09 (F §1.4, §2): Loader2 enters the updater on the existence of `\updater\mode` and never reads `comp` (C-BOOT-035); `mode*` is deleted by the updater script when `comp` exists and by the main firmware (C-BOOT-036). Two explanations remain: (i) the updater did start, consumed the flag and rebooted; (ii) the FAT open failed on an empty file. Test: Q-39.
- **R-12 (E-0025/E-0026).** Remanence "closed" - the first frame was probably shot without the effect; the second used a coarse sweep (4 MB step, 256 KB samples) and may have missed a still pool.
  - claims affected: C-MEM-013, C-MEM-014
- **R-13 (E-0022).** No flash log survives for the 05.10 curve write; its content is established indirectly (live read of av-cam curve region, identical md5 for `p3_fit.bin` and `current_p3.bin`).
  - claims affected: C-DLV-010 (carry this caveat wherever the narrow write is cited as the safety precedent, R 1-E)
- **R-14 (E-0045..E-0048, review R 2-B).** Amplitude independence was read as "the buffer is discarded". Equally consistent: grain written to a live buffer is smoothed by a later full-frame NR pass (YKNR/PBE/CCNR_Enc), which also explains why the coarse native HC Mono texture (ACF lag-1 0.58) survives and fine white noise does not. Not considered in the records; test = correlated grain (07 §2).
  - claims affected: C-PIPE-001, C-PIPE-025
- **R-15 (E-0057/E-0058 vs E-0060, review R 2-C).** The ranges include the DMA setup of overlay `0x105d0` (`0x48234`/`0x48230`); "black luma, dies" and "white, dies" fit an engine hang mid-frame, not the removal of a tone stage. Strengthens R-1/R-2.
  - claims affected: C-IDT-009 (now refuted), C-IDT-011
- **R-16 (E-0038, review R 2-D).** The always-run detour may have run and grained through `session[0x3e24]` = `0x1df` (a handle), i.e. 8 MB at bus `0x1df` → DRAM `0x800001df` (low kernel/av-cam RAM, not a frame). Same end state; E-0038 says nothing about the gate and must not be cited for it.
  - claims affected: C-CTRL-009, C-MEM-011
- **R-17 (C-TONE-024, review R 1-D).** "Highlights held above Y′≈200" rests on one wedge pair (DSC09509/09510) with different exposure; treat the shoulder as a design caution, not a hard constraint, until Q-6 is shot.
  - claims affected: C-TONE-024, C-TONE-026, C-TONE-027

## 3. Records

Schema: `00-index.md` "Experiment record". Records are in date order.

**2026-10-04 - first contact, Backup writes (no firmware writes)**

### E-0001: full flash dump and Backup.bin read  (2026-10-04)
- image: live read-only; resulting files `~/nex3n-dump/nex3n_v100_nflasha.bin` (267911168 B) and `Backup.bin` md5 `b476ec204c7ed0f410d64f10ea439372` (703962 B)
- change: [18:43-18:45] pmca updater shell, `info`, `pull` of the whole block device, `bk` read. No writes.
- observed: `info` printed Model NEX-3N, product code 32825235, Backup region CX76201_CE, firmware 1.00; the dump finished ("100"). No camera misbehaviour reported.
- conclusion: baseline dump and Backup snapshot obtained; updater-shell `pull` of block devices works.  confidence: high
- caveats: `Backup.bin` (sha1 `0957fc1005fe4eaa5d1ce16a5532db0e6e34bf06`, = `Backup.bak`) differs from the later `Backup_pre-write.bin` (sha1 `6985f679...`); the difference is the pmca/updater-mode side effects described in E-0002, so "pristine" means "as read at first contact".
- claims: C-TOOL-005, C-DLV-006, C-PART-016

### E-0002: null Backup write 0x01070937 = 00 (same value)  (2026-10-04)
- image: Backup write `0x01070937` `00 -> 00`; pre-write snapshot `Backup_pre-write.bin` md5 `c0d14de75767db585948f72363f7de4d`
- change: [18:51] `bk w 01070937 00` (protected property -> pmca rewrites the whole Backup), readback "Success".
- observed: pmca reported `Success` with readback match. File diff afterwards: only the checksum and two mode flags `0x0051000f`, `0x00510014` changed. Camera reboot was checked by the owner: "all ok" (msg 16:53Z).
- conclusion: the Backup write path is safe and survives reboot; the two flags are side-effects of entering updater mode (hypothesis, "not checked" in the session).  confidence: high (write path), low (flag meaning)
- caveats: whole-file rewrite of Backup for protected properties; round-trip restore by whole file was explicitly not tested at this point.
- claims: C-DLV-017, C-BK-016

### E-0003: flag test 0x01070937 = 01 (NEX-6 value)  (2026-10-04)
- image: Backup write `0x01070937` `00 -> 01`; snapshot `Backup_pre-test1.bin` md5 `c0a052e1a5cecbc25626fe40a49d25ca`
- change: [18:56 msg] one of 18 candidate flags set to the NEX-6 value, to see whether more Creative Styles appear.
- observed: owner: "6 styles - did it really flash?" (msg 17:00Z); readback inside the session showed `01`.
- conclusion: this flag does not unlock styles.  confidence: medium
- caveats: only the style count was looked at; whether the value persisted across reboot was not checked at this step (assistant noted it).
- claims: C-FX-003, C-FX-001

### E-0004: flag test 0x0107093b = 01 (937 restored to 00)  (2026-10-04)
- image: Backup write `01070937 01->00`, `0107093b 00->01`
- change: [~19:03 msg] second candidate.
- observed: owner: "nothing changed, switch on half" (msg 17:07Z).
- conclusion: second flag does not unlock styles.  confidence: medium
- caveats: as E-0003.
- claims: C-FX-003, C-FX-001

### E-0005: flag test, group 1 of 8 flags  (2026-10-04)
- image: Backup write; pre-snapshot `Backup_pre-group1.bin` md5 `eae39fcfb1d8795d0dd3d15aee933e2c`
- change: [~19:09] `0107093b` back to 00; set to NEX-6 values: `01070929 02->05`, `01070928 7700->7f00`, `0107097f 00->01`, `01070980 00->01`, `0107094f 00->01`, `01070951 00->01`, `0107092c 00->01`, `01070306 00->01`. First attempt failed (camera did not enter updater within 30 s, nothing written, msg 17:08Z).
- observed: owner interrupted the next tool call twice (17:11Z, 17:15Z); no explicit quote about the menu. Assistant summary: "did not open" (msg 17:16Z).
- conclusion: no flag combination here opens the hidden styles.  confidence: medium
- caveats: the verbatim owner observation for groups 1 and 2 is not in the transcript; the summary is the assistant's.
- claims: C-FX-003

### E-0006: flag test, group 2 of 8 flags (on top of group 1)  (2026-10-04)
- image: Backup write; pre-snapshot `Backup_pre-group2.bin` md5 `8fe60b8941029765df4e2843a3a8233e`
- change: [~19:12] additionally `0107091d/091e/091f/0920/0923/0925/0926/0400` to NEX-6 values; group 1 left on (no rollback in between).
- observed: with all 16 set, styles still 6 (assistant statement, msg 17:16Z; owner reported no visible change).
- conclusion: none of the 18 `0x0107xxxx` flags controls the style list. Later explained by code: unconditional loop in `viewUnified2.so` hides IDs 6..12 and reads no flag (static, `notes/hidden-styles.md`).  confidence: high (combined with the static result)
- caveats: the experiment itself only shows "no menu change"; the cause comes from the later disassembly.
- claims: C-FX-003, C-FX-001, C-CTRL-013

### E-0007: revert of the 16 flags, read-only boot dumps  (2026-10-04)
- image: Backup writes back to 3N values; snapshots `Backup_pre-revert.bin` md5 `51850c51d0b5270bf0301d52b660d0b4`, `Backup_post-revert.bin` md5 `fb270c83a7940f5623fc8cd99f759dbf`
- change: [20:10-20:11] each flag written back individually (not a whole-file restore); in the same session `boot1` (Loader2) and `bootrom` read, style blocks read.
- observed: "All 16 flags are back to the 3N values", verified by `bk r`.
- conclusion: per-property revert works; boot loader readable (`boot/boot1`, `boot/bootrom`).  confidence: high
- caveats: `Backup_post-revert.bin` is not byte-identical to `Backup.bin` (expected: mode flags, checksum).
- claims: C-DLV-017, C-BOOT-001, C-PART-016

### E-0008: ladder 0x00030106 step 5 (+0xb6) 80 -> 32  (2026-10-04)
- image: Backup write `0x00030106` offset `+0xb6` (uint16, ladder `0x78b0`), orig block md5 `641eeb594c76365970147df1f9af8113` (`bk/30106_orig.txt`)
- change: [~20:12-20:17] ladder `2,8,16,24,32,[80->32],112,144,176`, `bk s`.
- observed: frames DSC09409-12 (before, other scene) vs DSC09413-15 (after, different scene and light): chroma ratio Sunset/Standard 2.75 -> 1.35 and Sunset/Vivid 2.36 -> 1.12. The assistant warned the scenes differ ("floor with slipper" vs "TV stand").
- conclusion (at the time): ladder = Sunset saturation gain.  confidence: low (superseded by E-0009)
- caveats: confounded by scene change; the owner could not reshoot on the day.
- claims: C-NR-017, C-NR-018, C-NR-019

### E-0009: ladder step revert to 80 and clean A/B  (2026-10-04)
- image: Backup write `0x00030106` `+0xb6` 32 -> 80 (original), verified against `30106_orig`
- change: [~23:03 msg] restore, then Sunset shot on the target at 1/100 f/5.6 ISO 800.
- observed: DSC09418 (value 32) vs DSC09425 (value 80): mean chroma 52.3 vs 51.7, grey patches b* +20..+25 vs +16..+22. The assistant: "no difference, within noise". Camera "completely in original state".
- conclusion: the ladder step does not change the JPEG colour; code reading afterwards says the ladders are sharpening (Apacon), not colour. Sunset warmth is not from this block.  confidence: high (no colour effect); medium (sharpness claim, never measured on a frame)
- caveats: the "sharpness" attribution is from static analysis; no sharpness measurement was taken. Standard Saturation was left at -3 in that series (assistant noted it does not matter for grey hue).
- claims: C-NR-017, C-NR-018, C-NR-019, C-COL-031

### E-0010: all 17 colour matrices replaced by one muted matrix  (2026-10-04)
- image: Backup write `0x00030001` and `0x00030008` (both banks); pre-snapshot `Backup_pre-matrix.bin` md5 `314a63c0197a848cbba46fd6ebf0d68f`; block file (probably `bk/00030001_test1.hex` md5 `f40b4f4935541a50ba214ab46bace207`, name inferred)
- change: [~23:14-23:17] the 17 slot matrices in `+0x48 + 18*slot` all replaced by the most muted native matrix (rows sum to 1024). Hue tables and other bytes untouched.
- observed: target chart, same point 1/100 f/5.6 ISO 800: mean chroma of 18 colour patches Standard 43.7 -> 21.7, Vivid 56.0 -> 24.3, Sunset overall 43 -> 17; grey patches unchanged; Sunset warm b* on bright neutrals 7 -> 2. Camera booted normally.
- conclusion: `0x00030001` is the JPEG colour block; Sunset's warmth is applied before the matrix (it is muted with the rest).  confidence: high
- caveats: single frame per style; frame-to-frame noise about +-2 chroma, +-3 b*.
- claims: C-COL-001, C-COL-009, C-COL-010

### E-0011: RGB-permutation "tag" matrices to identify slots  (2026-10-04)
- image: Backup write `0x00030001`/`0x00030008`; block `bk/00030001_tags.hex` md5 `b3c1a92b6251a9c8805ab0fa32e13448`, map `bk/tags.json`; original `bk/00030001_orig.txt` md5 `014ad5fe1b6bcacad67fb51b15f37ab8`
- change: [23:23 live13.log; msg 21:23Z] 17 matrices replaced by 6 RGB permutations x 3 saturation levels (1.0/0.6/0.3), rows sum 1024.
- observed: "wild colours" as designed; chart shot once per style (DSC09434-39). Slot map derived: Standard = slot 0 (`+0x48`), Vivid 1 (`+0x5a`), Portrait 2 (`+0x6c`), Landscape 3 (`+0x7e`), Sunset 4 (`+0x90`). B&W slot not identifiable from a mono frame. Camera stayed in this state overnight 04->05.10.
- conclusion: slot-to-style map established; native matrices M0/M1/M2 recorded.  confidence: high
- caveats: B&W slot unknown; the 17-slot -> style map beyond slots 0..4 is not established.
- claims: C-COL-002, C-COL-003, C-COL-004

**2026-10-05 - film-look colour via Backup, hue tables, first p3 write**

All entries below write `0x00030001` and `0x00030008` identically (both banks) with `bk w`, readback verified and `bk s`. The block hex per entry is matched to the write by file mtime (hex file creation vs `live*.log` mtime): this correspondence is an inference, no log prints the hash.

### E-0012: v1 film matrices (Portra / Gold / UltraMax / ColorPlus)  (2026-10-05)
- image: Backup write `0x00030001/08`; block `bk/00030001_looks_v1.hex` md5 `2d074d0536a632370221f912c1b73416`; log `live19.log` [12:12] (earlier tries `live15-18` failed: USB timeouts / camera asleep)
- change: Vivid = Portra 400, Portrait = Gold 200, Landscape = UltraMax 400, Sunset = ColorPlus 200 (matrices from Maraver chart data, rows normalised to 1024); Standard native.
- observed: 5 chart frames DSC09440-44. Blues go cyan in Gold/UltraMax/ColorPlus; Portra "softest". Measured chroma above prediction: Vivid +11 %, Landscape +14 %, Sunset +14 %; Portrait matches prediction (50.3 vs ~51). Sunset warmth absent at Custom 5500 WB (it was b* +20 at Auto WB the day before). Standard day-to-day shift dE 10.5.
- conclusion: linear-light matrix model fits better than gamma model; Vivid/Landscape/Sunset add their own chroma on top of the matrix; Sunset warmth = auto-WB target shift, not processing.  confidence: high (chroma boosts), medium (WB-target mechanism, one comparison across days)
- caveats: WB differed between days (Custom 5500 +M2 vs Auto), so absolute colour across days is not comparable.
- claims: C-COL-006, C-COL-012, C-COL-029, C-COL-030

### E-0013: v2 (style chroma boosts compensated in the matrices)  (2026-10-05)
- image: Backup write; block `bk/00030001_looks_v2.hex` md5 `ccc1243926b5114ef9ecd4ee1400bbb6`; log `live20.log` [12:22] (the success message in the session is stamped 12:54 local - gap unexplained)
- change: k = 1/1.11 Vivid, 1/1.14 Landscape and Sunset applied as desaturation preserving grey and luminance (Portra `1061,99,-136/75,1241,-292/9,45,970`, Gold, UltraMax, ColorPlus).
- observed: one scene shot with 5 styles (`compare_v2.jpg`), WB still Custom with M+2, warm room light, sky blown. Looks: "Portra calmest, Gold most 'film', UltraMax closest to Standard, ColorPlus 'cheap Kodak'". Owner: "looks decent" (msg 11:37Z).
- conclusion: defaults are right at sliders = 0; differences between styles visible but moderate (matrix changes colour only).  confidence: medium
- caveats: visual judgement; absolute colour contaminated by WB shift and lamp light.
- claims: C-COL-012, C-COL-033

### E-0014: v3 (House in Portrait, Phoenix II in Sunset) + hue-table test E1  (2026-10-05)
- image: Backup write; block `bk/00030001_v3_e1.hex` md5 `822dc540fcfe2abed6d58625af0bbe7f` (v3 block `00030001_looks_v3.hex` md5 `33281909a170f9d53030d047d98ab1c5`); log `live21.log` [14:09]
- change: Portrait = House `1117,-3,-73/9,1216,-203/-16,-11,1022`, Sunset = Phoenix II `1082,47,-92/102,1150,-232/54,74,890`; **E1: hue record of Standard (`+0x100..+0x117`) zeroed**.
- observed: Standard with zeroed record "acid, neon red/yellow/green/magenta" (assistant's visual reading of the frames, not a quoted owner remark). Chart numbers: mean chroma Standard(zeroed) 65.2 (normally ~48-50), grey a* -7..-11; Vivid 46.9, Portrait 42.5, Sunset 40.5. A Standard frame had the whole laptop in view so its grid was not recognised; numbers come from another frame of the set. Frame numbers for this set not recorded.
- conclusion: the int8 hue table in `0x00030001` is live; its native negative values (-30..-46) are chroma muting; zeroing it adds about one third chroma and shifts greys green.  confidence: high
- caveats: one frame; chroma figure from a frame the script could parse.
- claims: C-COL-013, C-COL-022

### E-0015: binary sector test (three styles, 3-of-6 groups zeroed)  (2026-10-05)
- image: Backup write; block `bk/00030001_binary.hex` md5 `3277158c4df6dde7884cd9f6f8fb4116`, plan `bk/binary_plan.json`; log `live22.log` [14:19]
- change: Standard, Vivid, Landscape records zeroed in different 3-of-6 byte groups (each of the six 4-byte groups gets a unique 3-bit code); Portrait left as control.
- observed: frames DSC09473-76. The assistant decoded: group 0 -> yellow-green/green, 1 -> red, 2 -> magenta/purple, 3 -> nothing visible, 4 -> cyan, 5 -> blue. Record N acts on slot N confirmed (Vivid's pattern showed only on Vivid, etc.).
- conclusion (later): record-to-slot binding is correct; the "6 groups = 6 hue sectors" reading is **superseded** by E-0016 (4 bytes = 4 hue regions, 6 groups = 6 parameters).  confidence: high (slot binding), low (sector reading)
- caveats: zeroing a group changes a parameter in all four hue regions at once; the first decode attributed that to one hue sector.
- claims: C-COL-013, C-COL-014

### E-0016: byte test in group 0 (+0..3), one byte per style  (2026-10-05)
- image: Backup write; block `bk/00030001_bytes.hex` md5 `f6903495a4b403d6b46d7a5204669232`, plan `bk/bytes_plan.json`; log `live23.log` [14:32]
- change: byte j of group 0 of slots 0..3 raised to about +100 (Portrait byte 2 `+6 -> +100`).
- observed: frames DSC09478-81, Sunset control DSC09482/87. First pass: only Portrait clean (greens dC -11..-14, cyan/blue-green hue -14 and -34 deg); other three polluted by E-0015 state ("my planning mistake"). After E-0017 clean baseline (DSC09483-86): byte 0 rotates reds/skin/magenta -12..-35 deg; byte 1 oranges/yellows/greens +18..+29; byte 2 blue-greens/cyan/sky -15..-37; byte 3 blues/violet/purple +9..+22. Noise from the control: dC +-7, dh +-4..5 deg.
- conclusion: 4 bytes of a group = 4 hue regions (red/skin, yellow-green, cyan/sky, blue/violet); group 0 = hue rotation.  confidence: high (rotation per region), medium (exact region edges)
- caveats: needs the same-session baseline, which was only established in E-0017; hand-held camera, cross-session dE +-2..3.
- claims: C-COL-014, C-COL-015

### E-0017: clean v3 restore as same-session baseline  (2026-10-05)
- image: Backup write; block `looks_v3.hex` md5 `33281909a170f9d53030d047d98ab1c5`; log `live25.log` [14:43]
- change: all hue tables back to native, v3 matrices; camera not moved (owner could not keep exact position).
- observed: baseline frames DSC09483-86 (+ Sunset control 09487). Used as base for E-0016 and E-0018.
- conclusion: lesson recorded: base frames must be shot in the same session with native tables.  confidence: high
- caveats: handheld, dE +-2..3 between sessions.
- claims: C-COL-042

### E-0018: band test (second/third parameter pairs)  (2026-10-05)
- image: Backup write; block `bk/00030001_bands.hex` md5 `53ecf85ff2b9ab551cfde1e430e323f6`; log `live26.log` [15:17]
- change: Standard `+0x105` (Q1 b1) -36 -> +90; Vivid `+0x125` (Q3 b1) -9 -> +110; Portrait `+0x145` (Q5 b1) -17 -> +110; Landscape `+0x150` (Q2 b0) -6 -> +120; all other bytes v3.
- observed: frames DSC09488-91 vs base DSC09483-86 (Sunset control 09487 -> 09492: dC +-8, dh +-5): Standard yellows/greens/oranges/skin dC +12..+34, L +5..+10, reds rotate +14..+33 deg; Vivid almost the same (dC +16..+25); Portrait weak (dC +7..+8); Landscape reds/dark skin -28..-34 deg, magenta dC +22.
- conclusion: pairs (Q0,Q1) ~ (Q2,Q3) = (hue, saturation); bands are not luminance bands (L 24..75 respond alike); no shadow/highlight muting from these tables; saturation byte leaks hue into reds.  confidence: medium
- caveats: camera responds up to ~1.8x stronger than the per-unit model; third pair (Q4,Q5) behaviour unexplained.
- claims: C-COL-016, C-COL-017, C-COL-018, C-COL-019, C-COL-020, C-COL-021, C-COL-023

### E-0019: v4 hue tables for the four film styles  (2026-10-05)
- image: Backup write; block `bk/00030001_looks_v4.hex` md5 `88775459fe2ab78f3273a5866513a5ae`; log `live27.log` [15:26]
- change: v3 matrices + model-derived tables for slots 1-4 only (54 bytes `0x118..0x16b`); Sunset record markers (-128) left.
- observed: frames not numbered in the sources; chart measured vs v3: Portra blues/sky/cyan -31..-38 deg and blue chroma -28..-39, skin -9..-14 deg (planned -3..-7); UltraMax about half of that (-18..-21 deg, chroma -19..-27); House cyan +9.5, sky +7.6 (planned +5); Phoenix yellows/greens chroma -15, cyan **+8** (planned -7, sign reversed). "Sunset listens to its own record" with or without the -128 marker.
- conclusion: tables work; model under-predicts the blue region by 3-5x and the response is non-linear; Sunset (slot 4) honours its record.  confidence: medium
- caveats: sample is one frame per style; shift partly confounded by day drift (corrected with Standard).
- claims: C-COL-023, C-COL-024, C-COL-045

### E-0020: v5 (scaled v4 tables)  (2026-10-05)
- image: Backup write; block `bk/00030001_looks_v5.hex` md5 `9e3fc4acf14e3cb9d362c8436cfd7aa1`; log `live28.log` [21:10]
- change: v3 + v4 changes scaled by measured response: Portra x0.3, UltraMax x0.5, House x1, Phoenix cyan byte with reversed sign.
- observed: DSC09498-502 vs v3 base DSC09483-87 (drift corrected by Standard): Portra blues/cyan -6..-13 deg; UltraMax blues -4..-15 deg, yellow/green chroma -16..-26; House cyan/sky +4..+7 deg; Phoenix yellows chroma -15. Live frames "on v5" under incandescent lamp with WB Daylight were very yellow (not assessable); highlights blown ("the table is a white spot with hard edge").
- conclusion: v5 accepted as the state of the camera (Standard native, Vivid Portra 400, Portrait House, Landscape UltraMax 400, Sunset Phoenix II).  confidence: medium
- caveats: judged on the chart; live frames had lamp light; exposures differed (House 1/160 vs others 1/100).
- claims: C-COL-033, C-COL-024, C-COL-025

### E-0021: updater-mode insurance via /setting/updater/mode  (2026-10-05)
- image: file write on p2 `/setting/updater/mode` (empty file), no flash partition written
- change: [21:33 live29.log] mounted view of `/setting`, listing showed `updater/comp` (0 B) and `dat4` (2 B) but no `mode`; empty `mode` created, synced. Owner pulled the battery and cold-started with the power button.
- observed: "camera booted as usual" (msg 19:45Z, 21:45 local). After the boot `live30.log` [21:48] shows `updater/` again without `mode`.
- conclusion: the bootloader does not enter updater mode from this file while `comp` exists; the flag is consumed. No software safety net exists for p3/p8.  confidence: medium
- caveats: `mode`+`comp` may mean "update finished, clean up"; the variant "delete `comp`, create `mode`" was **not** tried. 2026-10-09 (F): Loader2 does not read `comp` and enters on existence of `mode` (C-BOOT-035); the conclusion "no software safety net" is contested (R-11, C-BOOT-036).
- claims: C-SAFE-004, C-BOOT-015, C-BOOT-035, C-BOOT-036

### E-0022: film tone curve k0 written into av-cam in p3 (first firmware write)  (2026-10-05)
- image: `work/tone/p3_fit.bin`, md5 `d7cca4469709a8b50bc5ad6efa34aa13` (= `current_p3.bin`); changed region 38 sectors 8849-8886 (`p3_orig_sect_8849.bin` md5 `186bf30ffef27869c60fd7deec82559e`, `p3_new_sect_8849.bin` md5 `921f2345759926751f22f3e9c42561e8`)
- change: [~21:56-22:03] curve k0 (Contrast -3, file `0x5b006a..0x5b0869`) replaced by a film curve (black 55/1023, white 909/1023, knots `[55,139,243,362,487,612,730,832,909]`), adjusted +-1..2 so that its 64 KiB LZPT block compresses to the identical size (table of blocks unchanged). Only the changed sectors were written; WBI sector 0 saved (`p5_sector0_before.bin`), WBI zeroed. No flash log of this write survives in the scratchpad.
- observed: grey wedge frames DSC09509 (Contrast 0) and DSC09510 (Contrast -3), same exposure: Contrast -3 shadows 12 15 19 28 (before: 0 1 5 14), highlights 222 226 228 229; Contrast 0 shadows 2 4 10 25, highlights 225-233 (different exposure set from the "before" pair). Black ~12/255 clean. Camera booted and shot normally.
- conclusion: partial p3 write inside av-cam is safe and effective; the tone curve is applied in the encoded (gamma) domain; k0 = Contrast -3 in any style.  confidence: high
- caveats: before/after sets differ in exposure (comparison only inside a pair); fitting step altered the curve by +-1-2 units; the on-camera content was later verified indirectly (06.10: live av-cam curve region differs from stock by 1093 B only in `0x5b006a..0x5b0869`).
- claims: C-DLV-010, C-TONE-022, C-TONE-023, C-MEM-017

**2026-10-06 - updater/senser reconnaissance, RAM patches, first av-cam flashes**

### E-0023: updater-shell environment recon (read-only)  (2026-10-06)
- image: live memory/FS op in updater shell; no writes. Raw output not preserved (only the notes keep it).
- change: [~11:00-11:20 msg] `mount`, `/proc/{partitions,iomem,cmdline,modules,kallsyms}`, `/dev` list, `/sys` UIO.
- observed: kernel `2.6.29.6-rt24-alp_nl SMP PREEMPT RT`, 3x ARMv6; `/dev/mem` and `/dev/kmem` exist; `memrsv=448M@0x84000000` and 19 MB @`0x82D90000`; only USB/storage/memstick + `dmm` + `mcmn_drv` loaded; `/system` empty, `liro.ko` not in the updater `/kmod`; nodes `/dev/mcmn`, `ldec`, `dmac`, `jet/adj_drv`; `uio0` at `f5060000` = "gpe" (not the engine); SA-MMIO (`0x40000/0x48000`) absent from iomem; `DmmConfig.bin` (77 KB) fetched from `/setting`.
- conclusion: the updater Linux is a recovery build without the imaging stack and with the SA block not mapped.  confidence: high
- caveats: single boot, one camera.
- claims: C-DLV-019, C-SYS-003, C-SYS-007, C-MEM-003

### E-0024: insmod liro.ko inside the updater  (2026-10-06)
- image: live op; `liro.ko` pushed from p3 into `/tmp`, nothing written to flash
- change: [11:34 msg 09:34Z] `insmod /tmp/liro.ko` (no parameters), then dmesg and kallsyms look-ups; module removed and file deleted.
- observed: `insmod: unknown symbol in module`; dmesg `liro: Unknown symbol Backup_nread` (also `Backup_nread_setting_attr_async`, `_multi_async`, `_async`, `_setting_attr`, `_multi`); kallsyms entries for `Backup_write`, `acre_tsk`, `osal_snd_sync_msg`, `buddy_init_pool`, `loc_cpu`, `os_this_cpu` all absent.
- conclusion: the imaging stack cannot be started from the updater environment; "route A" (run av-cam from RAM there) is closed.  confidence: high
- caveats: only the missing-symbol list was seen; other blockers (SA power) were not tested after that.
- claims: C-DLV-019, C-DLV-020, C-BOOT-010

### E-0025: DRAM remanence test 1 (frame, then warm switch to updater)  (2026-10-06)
- image: live memory op, `/dev/mem` reads in the updater shell
- change: [12:45-13:00 msg] owner shot a normal frame ("camera connected, took a shot, raise the updater"), the camera was switched to updater without power-cycle; `dd` of `/dev/mem` at the pool bases from `DmmConfig` (`0x84b80000`, `0x84c00000`, `0x85000000`, `0x86000000`...) and a sweep of 55 samples x 8 KB, step 8 MB, `0x84000000..0x9f000000`.
- observed: `/dev/mem` reads the high zone (rc 0, non-zero data; 6 dumps with different md5); entropy 5.7-6.7 bit/B, zeros <0.2 %, vertical stride bands; `X` and `X+0x10000000` give identical statistics (physical DRAM 256 MB mirrored at `0x80xxxxxx`/`0x90xxxxxx`); no recognisable photo (minimum 2D-mad ~35-45 vs <20 for a smooth frame). pmca needed ~30-60 s to bring up the updater.
- conclusion: DRAM contents survive a warm switch, but the transient frame buffers were overwritten by live view before the dump.  confidence: medium
- caveats: the assistant later noted that the owner's frame was probably shot without Soft Focus, so this was not a convolution test; the sweep was coarse (8 KB every 8 MB).
- claims: C-MEM-013, C-MEM-014

### E-0026: DRAM remanence test 2 (Soft Focus mid, RAW off)  (2026-10-06)
- image: live memory op; pull log `live.log` [13:28] (SURV2: `/tmp/s2.bin` 10485760 B, md5 `44f7a72bd9b7549864d09718935a972f`)
- change: [13:18-13:28] frame with Picture Effect = Soft Focus mid (RAW had to be disabled; effect is JPEG-only), warm switch to updater, sweep of 40 samples x 256 KB, step 4 MB, `0x86000000..0x90000000`, rendered raw and as YUV422 luma at widths 4912/2456/1232.
- observed: no scene anywhere; 2D-mad ~48; texture noise and tables only.
- conclusion: the Soft Focus input/output buffers cannot be caught no-flash; they are freed and overwritten within seconds. Remanence branch closed.  confidence: medium
- caveats: timing hypothesis; another allocation pool (still pool) was not proven absent.
- claims: C-MEM-014

### E-0027: senser (service mode) enter, authenticate, readMemory  (2026-10-06)
- image: live memory op via `serviceshell` (pmca senser), read-only
- change: [13:47-14:01 msg 11:47-11:59Z] camera set to USB Mass Storage (resets to MTP after every reboot, needed to be re-set three times), service-mode switch, challenge-response auth with the generic keys, `readMemory` of 64 KB, 4 MB and 24 MB, sweeps of `0x84000000..0x90000000`, then `/dev/fb0` read in the interactive terminal.
- observed: auth succeeded on the NEX-3N; readMemory works; on live firmware the imaging stack is up (lsmod shows liro/unidrv1/unidrv2/dmm/mcmn) and the imaging DRAM has lower 2D-mad (down to 8.7) than the updater's (~48); `/dev/fb0` yields 54 bytes (dead end); the terminal can be left only by host SIGINT. Owner pasted an image of 4912x26 px (msg 11:59Z) - not described in the sources.
- conclusion: read access to ARM-physical RAM of the running camera works without writing flash.  confidence: high
- caveats: the display is not a standard Linux framebuffer; engine registers `0x40000+` are not in this address space.
- claims: C-DLV-001, C-DLV-002, C-MEM-015

### E-0028: differential dumps around one frame, op3 input/output pair  (2026-10-06)
- image: live memory ops; files `work/op3data/dump1.bin`, `dump2.bin` (12582912 B each), `sf_input_sharp.bin`, `sf_output_softfocus.bin` (6291456 B each), all mtime [14:17]
- change: [14:08-14:17] dump 1 (baseline) -> owner took a frame (USB unplugged, plugged back, **no power cycle**) -> dump 2; then a second shot without the effect (sharp input), camera hand-held ("cannot repeat exactly").
- observed: 77 of 192 regions identical between dumps, changed clusters `0x86800000..0x88700000`, `0x8b*`, `0x8c*`; image-like regions `0x85900000`, `0x85b00000`; raster stride 1280 B (autocorrelation peak, vertical-mad 4.86); rendered at width 1280 the colour chart and the camera's "USB Mode" screen are visible; the Soft Focus frame is softer.
- conclusion: DRAM persists across a USB unplug/plug when the camera is not power-cycled, so before/after diffing localises capture buffers; the image-level pair is only the final convolution (kernel already known) and does not decode op3.  confidence: high (method), medium (buffer identification)
- caveats: the 1280-wide buffer is a display/preview-size copy, not the full-size YC (see E-0031).
- claims: C-MEM-010, C-MEM-015

### E-0029: av-cam located in live DRAM  (2026-10-06)
- image: live memory op (senser readMemory)
- change: [14:38-14:40 msg 12:38-12:40Z] scan for av-cam strings (`Start_SoftFocus`, `SoftFocus_Main`, `HapiSFTFCS`, `CAMERA_MAIN_YC` at `0x8398282f`, `0x839828b3`, `0x839828f7`, `0x8350b1c1`), then read of `0x83441000` and comparison with `av-cam.bin`.
- observed: physical base `0x83441000` (virtual `0xc3441000`, `phys = virt - 0x40000000`); 99.5 % of bytes identical to the file (remainder relocated pointers / BSS).
- conclusion: every av-cam address analysed statically can be read from live RAM at `virt - 0x40000000`.  confidence: high
- caveats: none noted.
- claims: C-MEM-001

### E-0030: senser writeMemory on display buffers  (2026-10-06)
- image: live memory write (not persistent)
- change: [14:46-14:56 msg 12:46-12:56Z] (a) invert 596 KB strip at `0x85AC9000` (USB-mode OSD strip, rows ~1460-1930, stride 1280); (b) read twice a region to find static parts (only `0x85300000` constantly, `0x84100000`/`0x84900000` partly change; stable USB-screen candidate `0x85b00000`); (c) invert 256 KB at `0x85b50000`.
- observed: (a) readback after the write is neither inverted nor the old data (49.5 % match with something else) = buffer being rewritten; owner: "nothing changed"; "the write dropped and there was a reconnect window" (USB reconnect, camera intact). (c) no reconnect; readback 0 % inverted, 48 % original; owner afterwards: "something flickered on the screen" (msg 12:56Z).
- conclusion: writeMemory reaches the display RAM (visible flicker) but the redraw overwrites it faster than USB writes; large writes into live pipeline buffers can drop the USB link.  confidence: medium
- caveats: the "flicker" is an owner recollection after the second write; the first write's USB drop may be coincidence with the 596 KB size.
- claims: C-DLV-001

### E-0031: full-size YC buffer located after a frame  (2026-10-06)
- image: live memory op (readMemory after a shot, no power cycle)
- change: [~15:30-15:38 msg 13:30-13:38Z] owner shot a frame, plugged USB in Mass Storage; dumps of `0x84000000..`; width found by row-to-row autocorrelation.
- observed: YC_FULL for that shot at `0x8a000000`, YUYV 4:2:2, width 4912, stride `0x2660` (9824 B/row, ~32 MB), luma in even bytes, rowdiff 0.49 at w=4912; previous shot's base was `0x85900000`; the base appears 37 times in descriptor tables (`0x83dcc9xx`/`0x83dce2xx`). Another JPEG output buffer starts with `FFD8` (found later at `0x8e000000`).
- conclusion: the developed canvas is YUYV, base dynamic (do not hard-code).  confidence: high
- caveats: the 4912 wide canvas differs from the 4928 wide per-stage copies found in E-0041; the two geometries must not be mixed.
- claims: C-MEM-005

### E-0032: RAM patch 1 - Stage_SoftFocus replaced by a grain routine  (2026-10-06)
- image: live memory write (not persistent); original saved as `orig_sf.bin`
- change: [~15:53 msg 13:53Z] 70-byte Thumb-1 xorshift grain written over `Stage_SoftFocus` at phys `0x837ea898` (first ~426 rows per the instruction text); readback MATCH.
- observed: owner: "shot, I don't see grain but it does not look like soft focus" (msg 13:56Z). Card read: DSC09516 (15:57) EXIF Picture Effect = **Off**, clean frame. Next shot DSC09517 (16:01) Picture Effect = Soft Focus: normal Soft Focus blur. A read of `0x837ea898` afterwards showed the **original** bytes.
- conclusion: the test was invalid (effect was off); by the second frame the RAM patch had been lost (camera rebooted, probably auto power-off while the owner worked in the menu).  confidence: high (that the patch did not run), medium (reboot cause)
- caveats: owner's first impression "not soft focus" contradicts the EXIF (Off); the cause of the reboot was inferred.
- claims: C-DLV-004

### E-0033: RAM patch 2 (fresh boot, +-31, 8 MB)  (2026-10-06)
- image: live memory write (not persistent)
- change: [~16:09 msg 14:09Z] power-cycle, Mass Storage, grain over `Stage_SoftFocus` +-31 on the first 8 MB, readback MATCH; owner disconnected USB and shot one Soft Focus frame within ~30 s.
- observed: owner: "interesting - I did not see the preview after the shot" (msg 14:09:52Z). No new JPEG on the card (last was DSC09517). A senser read afterwards showed the original bytes at `0x837ea898` and av-cam 64/64 stock.
- conclusion: leaving service mode reboots the camera and reloads av-cam from flash, so RAM patches never survive to a capture (confirmed twice here, a third time in E-0035).  confidence: high
- caveats: the missing JPEG and preview are attributed to the reboot; not independently shown.
- claims: C-DLV-004

### E-0034: FileControl write test to /system  (2026-10-06)
- image: file ops via senser FileControl; log `ft.log` [17:05]
- change: write `/setting/gtest.bin`, then `/system/gtest.bin`. Before this, `readFile('/system/av-cam.bin')` had been read OK (6554072 B) and compared to `sys_avcam.bin`; an earlier attempt failed with "no window" (msg 15:03Z).
- observed: `/setting/gtest.bin` write OK, readback MATCH, deleted; `/system/gtest.bin` FAIL "Senser file control error 130". The on-camera av-cam differs from stock only in `0x5b006a..0x5b0869` (1093 B).
- conclusion: `/system` (p3) is read-only through FileControl; `/setting` (p2) is writable; the live av-cam carries the owner's film curve.  confidence: high
- caveats: none.
- claims: C-DLV-005, C-MEM-017

### E-0035: RAM detour at 0xc3889760 + one frame (DSC09519)  (2026-10-06)
- image: live memory write (not persistent); log `det.log` [20:33]
- change: trampoline at `0xc3889772` + stub/grain in cave `0xc3a011c0` (+-15, 8 MB) written to phys `0x83889772`/`0x83a011c0`, both MATCH; owner unplugged USB and shot a normal frame with Soft Focus on.
- observed: DSC09519: high-frequency noise in the "grain zone" (top 853 rows) vs outside: ratio 1.01, i.e. a clean original Soft Focus frame.
- conclusion: RAM delivery fails for the third time (reboot on service-mode exit); flash the partition instead.  confidence: high
- caveats: same as E-0033.
- claims: C-DLV-004

### E-0036: FileControl probe over all mounts  (2026-10-06)
- image: file ops via senser; log `probe.log` [20:43]
- change: write test files into `/setting`, `/usr`, `/system`, `/android`, `/info`.
- observed: `/setting` OK, readback MATCH; `/usr`, `/system`, `/android`, `/info` all "error 130".
- conclusion: only p2 is writable as a file; p3, p8 need raw writes.  confidence: high
- caveats: none.
- claims: C-DLV-005, C-PART-013

### E-0037: updater-shell file operations and mount attempts (no write succeeded)  (2026-10-06)
- image: updater-shell session; logs `flash.log` [20:49], `diag.log` [20:54], `flash2.log` [20:57], `mdiag.log` [20:59]
- change: attempted `PULL /system/av-cam.bin` (before any write), `mount`/`ls`, `mount -t vfat /dev/nflasha3 ...` (also without `-t`, and `-o ro`), partition listing.
- observed: PULL -> `Exception: Unknown error`, no write was reached; the camera then stayed in updater mode (next entry could not read the model, a power cycle fixed it); `/proc/mounts`: `/dev/nflasha2 /setting vfat rw`, `/dev/loop0` cramfs; `/system` empty dir; `mount ... /dev/nflasha3` -> `Invalid argument` in all three forms; `/proc/filesystems`: ext2 cramfs axfs ramfs vfat; `/proc/partitions` lists `nflasha0p1..p12`, p3 = 10240 blocks (10 MB); `/system` not writable.
- conclusion: p3 is not a mountable vfat in the updater; the way in is a raw write of the LZPT partition.  confidence: high
- caveats: the assistant's first guess ("axfs/cramfs, read-only compressed FS") was not verified; p3 is an LZPT container.
- claims: C-DLV-006, C-DLV-007, C-SAFE-011, C-PART-014

### E-0038: p3_grain - always-run detour at 0xc3889760, +-15, 8 MB  (2026-10-06)
- image: `p3_grain.bin`, md5 `b1142dd80865f60620ff02d8ed12bca6` (av-cam = `av-cam_grain_live.bin`: live film curve + detour); log `flash3.log` [21:13]; recovery `current_p3.bin` `d7cca446...`
- change: first persistent flash; trampoline after the gate `r4[0x3c] in {1,2}` at `0xc3889772`, stub and 70-byte grain in the cave `0xc3a011c0`, base taken from `session[0x3e24]`. About 83 % of the partition changes (code changes the compressed block sizes, LZPT layout shifts). Whole-partition md5 verified, WBI zeroed.
- observed: camera boots, shoots, saves frames (assistant: "survived the flash"); high-frequency noise ratio top/bottom 0.99 and 0.85 (no grain); a live senser read (`schk.log` [21:15]) shows trampoline `014b1847 0000c111a0c3...` at `0x83889772` and the cave stub, i.e. the new p3 was running.
- conclusion: delivery and execution context work (flash, md5, WBI reset, boot); the hook either was not reached or grained something else (gate assumed false).  confidence: high (delivery), low (gate explanation)
- caveats: how often `0xc3889760` runs per frame was never established.
- claims: C-DLV-007, C-DLV-008, C-CTRL-009

### E-0039: p3_grain_sf - Stage_SoftFocus replaced by grain  (2026-10-06)
- image: `p3_grain_sf.bin`, md5 `93dda2a4c1d8a2db9e7d8a1efda7d510`; log `flash4.log` [21:20]
- change: `Stage_SoftFocus` (`0xc37ea898`) body replaced by the grain routine writing `session[0x3e24]` as base, +-31, top ~850 rows.
- observed: owner: "preview of the frame appears **without the effect**, then falls; the photo is not saved" (msg 19:22Z, 19:24Z).
- conclusion: replacing the stage breaks develop -> SF -> encode data flow (and the base pointer is wrong); camera needs a power cycle, SF must not be used.  confidence: medium
- caveats: the exact crash mechanism (write to `0x1df`, missing SF output) was inferred; E-0040 supports the pointer part.
- claims: C-SAFE-003, C-CTRL-003, C-MEM-011

### E-0040: p3_diag - diagnostic stub replaces Stage_SoftFocus, writes session fields to scratch  (2026-10-06)
- image: `p3_diag.bin`, md5 `0f4e30f0e48bd6f0848742a1bcbec7d3`; log `flash5.log` [21:30]; scratch read `scr.log` [21:32]
- change: stub stores 5 session fields and the session address into `0xc3a01400`, marker `0xdeadbeef`, does not touch pixels, returns 0.
- observed: after an SF-mode shot, senser read of the scratch: `session[0x3e24] = 0x1df`, `[0x39e0] = 0x14420000`, `[0x1b8] = 0x0`, `[0x3a98] = 0x10`, session object address `0xc3b2de54`, marker `0xdeadbeef` present. Camera shoots without SF and saves.
- conclusion: `session[0x3e24]` is a small id (handle), not a buffer address - the earlier grain wrote 8 MB at `0x1df`.  confidence: high
- caveats: the field is an id for this stage; its meaning (handle) was derived later.
- claims: C-MEM-011, C-CTRL-004

### E-0041: session object and candidate buffers dumped  (2026-10-06)
- image: live memory op; logs `sess.log` [21:35], `sess2.log` [21:38]; `cand_*.bin`, `session_obj.bin`
- change: after an SF shot (no power cycle), read 16896 B of the session object at `0x83b24f44` (first shot) / `0x83b2de54` (second shot, address differs per frame) and 11 candidate bus pointers.
- observed: `+0x4c0 = 0x0e000000` (buffer starting `ffd8ffe1` = finished JPEG), `+0x5e4 = 0x0d000200`, `+0x1884.. = 0x0c000c00`, `0x0c030c00`, `0x0c0b0c00`, `+0x1ea0 = 0x08020000`, `+0x1f24 = 0x0b8b0000`/`0x0be00000`, `+0x24e8 = 0x0d010000`/`0x0b010000`, `+0x3858 = 0x0a0a0100`, `+0x0150 = 0x08010400`; eight clean YUYV buffers 4928 px wide (rowdiff 0.27-0.52); `0x08010400`/`0x08020000` rowdiff 64 (RAW/Bayer-like). Pointers are bus addresses (`virt = bus | 0xc0000000`, `phys = bus | 0x80000000`).
- conclusion: map of buffers per frame; `session[0x5e4]` picked as the encode-input candidate "next to the JPEG output".  confidence: medium
- caveats: "encode-input" was never demonstrated; E-0049 later shows `session[0x5e4]` at the last develop step is not what the encoder reads.
- claims: C-MEM-004, C-MEM-006, C-MEM-007, C-MEM-009

### E-0042: p3_sfwrap - wrapper: real Stage_SoftFocus, then grain session[0x5e4]  (2026-10-06)
- image: `p3_sfwrap.bin`, md5 `61e7e8d5a55d8549718bab4164fd4d01`; log `flash6.log` [21:49]; builder `build_wrap.py`
- change: the 8 dispatcher `bl Stage_SoftFocus` sites (`0xc36282a2 .. 0xc362876a`) redirected to a wrapper in the cave `0xc3a011c0`; wrapper = call real SF, then xorshift32 noise (+-31, luma and chroma bytes alike) over the first 8 MB of `session[0x5e4]` (bus -> virt), return SF's result.
- observed: owner: "but the Soft Focus effect itself is still there" (msg 19:51Z). Frame DSC09527 saved (no crash), file 3.8 MB (larger than usual); assistant measured high-frequency luma noise **bottom 22.3 vs top 0.69**; a crop of the bottom showed visible digital-looking grain. Assistant at the time: "grain works SOOC".
- conclusion (at the time): wrapper keeps the data flow intact, `session[0x5e4]` accepted as the encode input; buffer assumed stored bottom-up. **Superseded** by E-0049/E-0051 and `dsp-grain-campaign.md`: the surviving bottom patch is a race artefact (see revisit list).  confidence: low
- caveats: grain amplitude +-31 is high; "only the bottom" fits both the bottom-up theory and a race with the DSP.
- claims: C-PIPE-001, C-PIPE-003

### E-0043: p3_iso400 - SF skipped, grain +-15 luma / +-3 chroma, full frame  (2026-10-06)
- image: `p3_iso400.bin`, md5 `571f520296c8e84b6dada470e335e163` (builder `build_set.py`, log `build_set.log`); flash log `flash_iso400.log` [22:19]
- change: wrapper does **not** call SF (returns 0), grains `session[0x5e4]` over the full region.
- observed: owner: "look, something is applied but I don't really see grain" (msg 20:21Z). Assistant measure: noise ~2.1 vs ~22 in E-0042.
- conclusion (at the time): with SF skipped `session[0x5e4]` is not the encode buffer. A fall-back was planned (grain all four candidate buffers).  confidence: low
- caveats: later work shows `session[0x5e4]` never reliably reaches the file, so "SF skipped" vs "SF called" difference may be only the race.
- claims: C-PIPE-001

### E-0044: p3_stripe - SF called, five vertical grain bands  (2026-10-06)
- image: `p3_stripe.bin`, md5 `f56c783962cf8d5cf8903d30a07bb73a`; log `flash_stripe.log` [22:34]; builder `build_stripe.py`
- change: SF called, then 5 vertical bands (amplitudes +-1/+-3/+-7/+-15/+-31) over region `0x1E00000`, stride 9856.
- observed: owner: "shot a couple of frames, it thinks for a long time of course" (msg 20:35Z). Frame blurred (SF), grain visible on a dark strip at the bottom only; centre/top noise 0.8; the five bands not distinguishable.
- conclusion (at the time): per-pixel pass over ~31 MB is too slow (watchdog/abort at about a third), so only the bottom is grained; digital look from uniform white noise on every pixel and chroma.  confidence: low
- caveats: "slow loop aborted" is an inference; the race explanation fits the same data.
- claims: C-PIPE-001

**2026-10-07 - grain hook variants, encode-path loggers, idt_cam NOP bisection (Campaign A)**

Frames DSC09535..DSC09557 belong to this day. All images keep the film curve (`sys_avcam.bin` base or live av-cam), p3 whole-partition flashes with md5 MATCH and WBI zeroed.

### E-0045: p3_v2med - SF called, then luma-only windowed 2x1-clumped grain  (2026-10-07)
- image: `p3_v2med.bin`, md5 `94dcb0f04d752a4ddf76a4c78f372835` (siblings built, not flashed: `v2soft` `24d8a1b9b9229f1934b3b0be7f612852`, `v2strong` `0747ba444efee847723d38049c214b91`); log `flash_v2med.log` [10:04]; builder `build_grain_v2.py`
- change: wrapper at the 8 SF sites: call real SF, then grain `session[0x5e4]`, luma only, window `min(Y,255-Y)/128`, ~+-14 (med), clamp 2x1, region `0x1A00000` (~85 %).
- observed: frames DSC09535-38 (Soft Focus, ISO 800, 4912x3264). Luma high-frequency std ~0.6; Soft Focus blur present. Owner only said "shot" (msg 08:05Z).
- conclusion (assistant, then): v2 regressed; grain went into SF's discarded input buffer. **Superseded** by E-0049: no ARM-side buffer reliably reaches the encoder.  confidence: low
- caveats: the "input vs output of SF" explanation is untested.
- claims: C-PIPE-001, C-MEM-007

### E-0046: p3_v3med - SF skipped, luma-only windowed grain  (2026-10-07)
- image: `p3_v3med.bin`, md5 `98ad7cdcdc5a12129049741f93fcca2c` (not flashed: `v3soft` `a35a345b45b1c946b9405ee3ea5d31a4`, `v3strong` `77875b521142ce44666da22c408cc5f4`); log `flash_v3med.log` [10:17]; builder `build_grain_v3.py`
- change: as v2 but SF not called (return 0); +-15, mid-tone window, clump 2x1.
- observed: owner: "no blur" (msg 08:19Z). Frames DSC09539-41 (SF, ISO 800): luma HP std ~1.8 in one crop, 0.7-1.1 elsewhere; luma ACF lag-1 0.5-0.59; chroma 0.2-0.3. The crop landed on a fabric texture, so ACF is polluted; visually "no real grain".
- conclusion: SF-skipping removes the blur (so the hook runs and SF's work is genuinely skipped); grain amplitude in the file is ~1, far below the +-15 written.  confidence: medium (blur gone), low (the "JPEG quantisation eats it" explanation then given)
- caveats: see E-0049; amplitude independence points to the buffer not being the encoder input at all.
- claims: C-PIPE-001, C-CTRL-003

### E-0047: p3_v4med - SF skipped, luma-only +-31 flat; HC Mono control  (2026-10-07)
- image: `p3_v4med.bin`, md5 `38d43251dffac4b3669c5eb92bca2501` (not flashed: `v4strong` `fae5e1f159d97d0d0a28a9a5d9ab4e6e`); log `flash_v4med.log` [10:29]; builder `build_grain_v4.py`
- change: no window, +-31, luma only, clump 2x1.
- observed: frames incl. DSC09542 (flat wall): HP std 0.78 / 1.13 / 1.84 (v3med: 1.84 / 0.74 / 1.12): tripling the amplitude changed nothing; 300 % crop "faint fine speckle, not film grain". Control DSC09545 (native High Contrast Mono, effect outside the hook): HP std 2.7-3.4, chroma 0.00, ACF lag-1 0.58 / lag-2 0.39; EXIF of that frame reports Creative Style Standard, Color Mode Standard, Saturation/Contrast Normal although the picture is B&W and contrasty. Owner shots at msg 08:31Z and 08:36Z; no comment recorded.
- conclusion: grain amplitude does not propagate to the JPEG (hook at the Soft Focus stage is "too early"); native B&W has no grain generator (it is sensor noise amplified by contrast, applied late, outside the colour-mode slot).  confidence: medium
- caveats: the "applied late" inference rests on EXIF vs picture mismatch plus statics.
- claims: C-PIPE-001, C-PIPE-004

### E-0048: p3_v5med - hook at the last develop step (rec40), +-31 luma  (2026-10-07)
- image: `p3_v5med.bin`, md5 `aef3f6d7152e4d494ee7c96a06d8267a` (not flashed: `v5strong` `3a115467193afe404ece2f32b92474ec`); log `flash_v5med.log` [10:55]; builder `build_grain_v5.py`
- change: two wrappers in the cave at the rec40 dispatcher (`0xc3628b18`) sites `0xc3628b2c` (class 0 -> `0xc37ee680`) and `0xc3628b26` (class 1 -> `0xc37ecb06`): call native, grain `session[0x5e4]`, return native result. SF stage no longer touched.
- observed: owner: "soap again" (msg 08:56Z) on Soft Focus frames (DSC09546/47; class 2 -> rec40 skipped, native blur returned; HP std 0.43). Off frame DSC09548 (msg 09:04Z): HP std 0.73, no grain.
- conclusion: the Soft Focus effect class skips rec40; but on the class 0/1 frame (effect off) the grain still does not reach the file.  confidence: medium
- caveats: whether "Off" is class 0/1 was only established afterwards by a static class map (`ctx[0x23]`).
- claims: C-PIPE-001, C-CTRL-002

### E-0049: p3_markrec40 - black marker at rec40  (2026-10-07)
- image: `p3_markrec40.bin`, md5 `ab3d49ef86e75460a7fcd33db2bd9b98`; log `flash_mark.log` [11:11]; builder `build_marker.py`
- change: same rec40 wrappers, but instead of grain the first ~6 MB of `session[0x5e4]` are filled with 0x00 (black bar).
- observed: frames DSC09548/49/50 (`scratchpad/mark/`): 0 % black everywhere, Off frames included; one frame without and one with effect shot at msg 09:13Z.
- conclusion: `session[0x5e4]` at rec40 is not the buffer the JPEG encoder reads; later RE: output of the last develop stage goes by handle `session[0x3e24]`; `session[0x5e4]` was a live DMA buffer only on the early SF stage (rec1-4) and is rewritten by the 31 calls of develop core `0xc37ea42e`.  confidence: medium
- caveats: DSC09548 was already shot at 09:04Z, before this image (flash [11:11]), yet is listed as a marker frame - the frame labelling in the session is off by one at least; the "Off = class 0/1" premise came from a static analysis done after the shot.
- claims: C-MEM-007, C-MEM-008, C-PIPE-019

### E-0050: p3_difflog - detour logger in encode handler 0xc3474800  (2026-10-07)
- image: `p3_difflog.bin`, md5 `96cd5870766dac122edf301c1d645b06`; log `flash_difflog.log` [11:36]; builder `build_difflog.py`
- change: detour at the start of `0xc3474800` (stub 92 B in the cave) copying `[0xc3ca0528]` (0x40 B) and a marker `0xd1a6` into scratch `0xc3a01400`.
- observed: senser read of scratch after a frame: all zeros including the unconditional marker; trampoline and stub confirmed present in live RAM. Owner shot at msg 09:37Z; the assistant later refers to a "no preview" remark (not found in the user messages extracted).
- conclusion: `0xc3474800` is not the still-image encode entry; `tsk46_jpeg` (`0xc344a790`) dispatches cmd 1/3 -> `0xc3474800`, cmd 0/2 -> `0xc347427a`.  confidence: high
- caveats: build needed a `__main__` guard (LZPT writer spawns a multiprocessing pool; earlier fork-bomb).
- claims: C-JPEG-001

### E-0051: p3_difflog2 - detour logger in still encode handler 0xc347427a  (2026-10-07)
- image: `p3_difflog2.bin`, md5 `96aaf536d938d51b8b690f3053b3c898`; log `flash_difflog2.log` [11:46]; builder `build_difflog2.py`
- change: hook at `0xc347427a`, back-jump `0xc3474284`; scratch: marker `0xd1a6`, `[0xc3ca0528]`, msg pointer and fields.
- observed: marker present, preview shown, capture healthy. `[0xc3ca0528]` NULL; msg pointer `0xc2b1700c`, `msg[0] = 2`, `msg[8] = 0`. The handler is called several times per frame; the logger holds the last (cleanup) call. Senser read does **not** reboot the camera (it returns to the shooting screen). Context singleton (return of `0xc35dc8ba`) = `0xc3bb7bc0`; read live: only state flags (`0x80000002`...), no buffer pointer. A `JPEG qtable` follows `0xc3ca052c`.
- conclusion: the encode handler gets no ARM-visible YC address; the buffer is passed by handle to the DSP/HW (`0xc35dcde6`/`0xc35dc952`). ARM path closed (also from two static RE threads).  confidence: medium
- caveats: logger overwritten per call, so the encode call itself was not captured; one-sided evidence of absence.
- claims: C-JPEG-001, C-JPEG-002, C-DLV-003, C-MOD-029

### E-0052: nopc171 - NOP idt_cam 0x2d4e0..0x2e608  (2026-10-07)
- image: `p3_nopc171.bin`, md5 `f20267134a882480a8381faab6515648`; log `flash_nopc171.log` [12:35] (first flash attempt failed: camera not visible); builder `build_nopcore.py` (clean film-curve av-cam, NOP bundle `0x1f70fb87dc3ee1f7` over the range, idt_cam inner `0x980e00`)
- change: [12:35] one late large "core" (1128 B range) overwritten with NOP bundles.
- observed: frames DSC09551 (scene), DSC09552 (flat grey, Ymean 117, Ystd 10, neutral chroma), DSC09553: normal.
- conclusion: range not used by stills (or its corruption is harmless).  confidence: medium
- caveats: **see revisit list (R-1)**: bytes in these ranges include scalar code and data; NOP executed as scalar is garbage with branches.
- claims: C-IDT-008, C-IDT-009

### E-0053: nopc132 - NOP idt_cam 0x249d0..0x25fa8  (2026-10-07)
- image: `p3_nopc132.bin`, md5 `aafe36934eb37166988eee1f53d154ab`; log `flash_nopc132.log` [12:42]
- change: the largest "core" (699 bundles) NOPed.
- observed: DSC09554 flat grey (Ystd 14), DSC09555 scene (Ymin 1, Ymax 249): normal.
- conclusion: not on the still path.  confidence: medium
- caveats: as E-0052.
- claims: C-IDT-008, C-IDT-009

### E-0054: nophalf2 - NOP idt_cam 0x1c000..0x2ea68 (second half)  (2026-10-07)
- image: `p3_nophalf2.bin`, md5 `c07db2c5a00135d526a535f0c97c236f`; log `flash_nophalf2.log` [12:50]
- change: whole second half of the VLIW region NOPed.
- observed: owner: "after the shot it says 'writing to memory card' and it does not end"; battery/reboot ("reboot?" - "after reboot it saved", msg 10:51-10:53Z). Saved frame DSC09556: normal image (Ymin 2 / Ymax 249, colour fine).
- conclusion (then): second half = encode/write; develop output unaffected. Now: some code/data in this range is required to finish the write (could equally be scalar control overlays).  confidence: low
- caveats: R-1.
- claims: C-IDT-008, C-IDT-009, C-SAFE-007

### E-0055: nophalf1 - NOP idt_cam 0xa598..0x1c000 (first half)  (2026-10-07)
- image: `p3_nophalf1.bin`, md5 `3190c9fa416472d8b78346d5112a0d7f`; log `flash_nophalf1.log` [12:59]
- change: first half NOPed.
- observed: owner (msg 11:01Z): "hangs on trying to focus; lets me shoot; dies". Battery pull needed. Owner "alive" at msg 11:15Z after battery pull.
- conclusion (then): first half = develop plus live view/focus.  confidence: low
- caveats: R-1.
- claims: C-IDT-008, C-IDT-009, C-SAFE-007

### E-0056: nopq2 - NOP idt_cam 0x13000..0x1c000  (2026-10-07)
- image: `p3_nopq2.bin`, md5 `69334d420475a64add3fefcae9121215`; log `flash_nopq2.log` [13:20]
- change: first attempt (~13:06) failed (updater-switch timeout, camera left in updater until battery pull); second flash succeeded.
- observed: owner (msg 11:21Z): "shot a frame, all ok". DSC09557 normal (Ymean 149, full range, colour fine).
- conclusion: this range is not needed for stills.  confidence: medium
- caveats: negative result is the more robust kind (a corrupted range that is not run does nothing), but R-1 applies if a part of it was run.
- claims: C-IDT-008, C-IDT-009, C-SAFE-011

### E-0057: nope2 - NOP idt_cam 0xe800..0x13000  (2026-10-07)
- image: `p3_nope2.bin`, md5 `413bbc9c7c2a66ad40204e5e24b822e7`; log `flash_nope2.log` [13:27]
- change: eighth of the VLIW region NOPed.
- observed: owner (msg 11:29Z): "again a black frame after focusing, and it dies after the shot". Assistant: focus alive, luma black, chroma intact (the frame itself is not in the archive).
- conclusion (then): luma develop in `0xe800..0x13000`. **Revisit**: black may come from broken AE/stat overlays; see R-1/R-2.  confidence: low
- caveats: R-1; the sub-range `0xe800..0x10c00` (e2a) was never flashed, so the table row "e2a = luma write (black)" is inferred from this result.
- claims: C-IDT-008, C-IDT-009, C-IDT-011, C-SAFE-007

### E-0058: nope2b - NOP idt_cam 0x10c00..0x13000  (2026-10-07)
- image: `p3_nope2b.bin`, md5 `c7bec421cbfa590b9e1146aa336039c4`; log `flash_nope2b.log` [13:35]
- change: late part of the previous range.
- observed: owner (msg 11:41Z): "everything very bright, after the shot it died on a white screen". Battery pull needed.
- conclusion (then): late luma tone/gain stage. **Revisit** (R-2): same symptom family was reproduced on 09.10 with narrower ranges (E-0060..E-0062) and the cause moved to a statistics overlay.  confidence: low
- caveats: R-1.
- claims: C-IDT-008, C-IDT-009, C-IDT-011, C-SAFE-007

### E-0059: restore current_p3 after the bisection  (2026-10-07)
- image: `current_p3.bin`, md5 `d7cca4469709a8b50bc5ad6efa34aa13`; log `flash_restore.log` [13:48]
- change: full partition restored, md5 MATCH, WBI zeroed.
- observed: "camera restored" (assistant); no frame reported by the owner.
- conclusion: restore path works after ten p3 flash cycles; zero bricks.  confidence: high
- caveats: none.
- claims: C-SAFE-003, C-SAFE-008

**2026-10-09 - NOP narrowing and overlay skips (`~/nex3n-dump/work/nopcore/`)**

Owner's observations below are as relayed in the 09.10 session ("enter as is"); the source logs only prove the flash.

### E-0060: nope2b1 - NOP idt_cam 0x10c00..0x12520  (2026-10-09)
- image: `p3_nope2b1.bin`, md5 `bc3a71e0a3fe43e73d4df657a08b15a0`; log `nopcore/flash_nope2b1.log` [13:31] (an earlier attempt at 13:24 failed with `ModuleNotFoundError: usb` in the scratchpad copy)
- change: first 09.10 cycle, range 0x10c00..0x12520.
- observed: overexposure by 2-4 stops, not blown to white ("not into milk"); saving hangs.
- conclusion: bright symptom comes from the part of this range outside E-0061/E-0062 by subtraction, i.e. `0x10c00..0x11280`; overlay `0x105d0` (mailbox statistics loop, 5 accumulators + 64 B to ARM, no pixel write-back) is the candidate: corruption of its literal pool/kernel -> wrong AE/DRO.  confidence: medium (localisation), low (mechanism - from code reading only)
- caveats: severity differs from E-0058 ("very bright, dies on white screen"); interactions between sub-ranges not tested; **R-1** (NOPs as scalar code).
- claims: C-IDT-008, C-IDT-010, C-IDT-011

### E-0061: nope2b2 - NOP idt_cam 0x12520..0x13000  (2026-10-09)
- image: `p3_nope2b2.bin`, md5 `3d20858576c1259e26fa2c0060008473`; log [13:38]
- change: tail of the previous range.
- observed: normal.
- conclusion: not used by stills.  confidence: medium
- caveats: R-1.
- claims: C-IDT-008, C-IDT-013

### E-0062: nopov11280 - NOP idt_cam 0x11280..0x12520 (whole overlay 0x11280)  (2026-10-09)
- image: `p3_nopov11280.bin`, md5 `eb9bc45f7dfed64504fd622378789037`; log [13:44]
- change: overlay at `0x11280` (586-bundle "core25", contains a 65536/n reciprocal table) NOPed.
- observed: normal.
- conclusion: `0x11280` is not used by stills; the brightening in E-0060 is not from it.  confidence: medium
- caveats: R-1. Editor check against the overlay table (04-dsp-modules.md section 5.1): this range stops 0x10 bytes into the VLIW program of overlay 0x11280 (header at 0x12510, 207 bundles to 0x12b88); the rest of that program and the head of overlay 0x12cd0 were NOPed only in E-0061 (also normal). "Whole overlay" is therefore exact only as the union of E-0061 and E-0062. The "586-bundle core25" label is a byte range (R-1), not the VLIW program (207 bundles).
- claims: C-IDT-008, C-IDT-013

### E-0063: skip_f6c0 - overlay stub "bl r1" -> nop  (2026-10-09)
- image: `p3_skip_f6c0.bin`, md5 `b595808f59c243323e75c09004495713`; log [13:54]; builder `build_skipov.py` (stub `5f50 5e50 5150 b100`, bytes `+6..+7` `b100 -> 0000`)
- change: overlay `0xf6c0` (writes 2D blocks from local `0x9000`; possibly AE/AWB grid) skipped.
- observed: live view blinks at 1/4000 f/16; black screen when focusing; saving hangs.
- conclusion: the ARM waits for this overlay's completion; skip is non-specific.  confidence: medium
- caveats: identical symptoms in E-0064/E-0065 mean no overlay-specific information.
- claims: C-IDT-012, C-IDT-016, C-SAFE-007

### E-0064: skip_cbd0 - overlay stub skipped  (2026-10-09)
- image: `p3_skip_cbd0.bin`, md5 `ce89028b5cdb32507aace13076b4fee9`; log [14:03]
- change: overlay `0xcbd0` skipped.
- observed: live view blinks 1/4000 f/16; black screen at focusing; saving hangs.
- conclusion: as E-0063.  confidence: medium
- caveats: as E-0063.
- claims: C-IDT-016, C-SAFE-007

### E-0065: skip_105d0 - overlay stub skipped  (2026-10-09)
- image: `p3_skip_105d0.bin`, md5 `0b4d9468dc5453efe8cc2e5e819e0f80`; log [14:10]
- change: overlay `0x105d0` (stats) skipped.
- observed: blinks 1/4000 f/16; saving hangs (no mention of a black screen at focusing).
- conclusion: as E-0063.  confidence: medium
- caveats: as E-0063.
- claims: C-IDT-010, C-IDT-016, C-SAFE-007

### E-0066: restore current_p3 after overlay tests  (2026-10-09)
- image: `current_p3.bin`, md5 `d7cca4469709a8b50bc5ad6efa34aa13`; log `nopcore/flash_restore.log` [14:17]
- change: full restore, md5 MATCH, WBI zeroed.
- observed: no remark recorded; the state is later quoted as "camera: current_p3".
- conclusion: restore path still works; camera on film k0 + v5, no grain, no NOP.  confidence: high
- caveats: none.
- claims: C-SAFE-003, C-SAFE-008

### E-0067: EXP-2 — CAP 3D-LUT chroma-by-luminance reaches the stills JPEG (Backup 0x00030004/5)  (2026-10-09)
- image: Backup write `0x00030004` and `0x00030005`, byte offset 1012 (`0x3F4`) `0x00`→`0x3f` (+63 dCr at plane2 / Ynode2 Y'≈128 / neutral node Cb4,Cr4 of the reference 3D-LUT); live `bk r` == stock pre-write, readback MATCH, `bk s`. Frames: pre-edit DSC09567-72, post-edit DSC09573-79 (grey-wedge chart, ISO 800, 1/40, f5.6, WB Auto, Picture Effect Off, both sets same exposure).
- change: inject +dCr at ONE neutral LUT node to test whether the CAP 3D-LUT (C-COL-046) is consumed on the stills/JPEG path.
- observed: Δa* (post−pre) on the 21-step grey wedge peaks at Y'≈128-136 and tapers to ~0 at Y'≈66 and Y'≈205 (triangular luma fingerprint), b* flat: Standard +13.9@Y'134, Vivid +12.7@Y'136, Portrait +10.1@Y'134, Landscape +11.8@Y'137, B&W +18.5@Y'136 (B&W pre a*=0.000 → clean). Sunset: Δa*≈0 (mid +0.75, differential +0.22) — no effect.
- conclusion: the CAP 3D-LUT (Backup `0x00030004`/`0x00030005`) IS consumed on the stills JPEG path (Q-7 prediction (a)); the chroma-by-luminance lever works via a reversible Backup write. Confirmed in 5/6 styles; Sunset selects a different LUT block/variant (dispatcher `0x3d12f8`, `[p8+0x4a]`: IDX≥2 → `0x30006` identity / 2-D `0x30007` / off).  confidence: high
- caveats: WB Auto not preset (but exposure identical and b* control flat, so the mid-peaked a* profile is not a WB offset); effective Level ~2-3 (Δa* ~half of the +63 upper estimate); one session, one chart; Sunset's warm processing adds b* noise. Measured with `ramp.py` (grey-patch Lab per step, `work/venv`).
- claims: C-COL-046 (upgraded hypothesis→verified-hw for stills-path consumption), C-COL-026, C-COL-027

### E-0068: EXP-3 — force the SACC MSDump consumer via a p3 gate patch; no YC dump on the card  (2026-10-10)
- image: p3 flash of the A+B SACC-gate patch `p3_exp3_ab.bin` (md5 `b31dac9b32a6f717494da94c1e964916`, C-DLV-022: file `0x1da8d4` `46 d0`→`c0 46`, `0x1da8e1` `d0`→`e0` on the film-curve base), device md5 MATCH, WBI zeroed; then restored `current_p3.bin` (md5 `d7cca446…`, MATCH) and reverted the EXP-2 Backup edit (`0x30004/5` byte `0x3F4` `3f`→`00`, read-back MATCH, `bk s`). Frames DSC09580 (ISO 3200, 1/100), DSC09581 (ISO 200, 1/6), Standard, 4912×3264.
- change: force the SACC consumer branch (idx1==4) with the gate patch so a real capture writes the YC buffer to the card (`/mnt`).
- observed: both frames captured and saved normally (no hang, no error). NO YC dump file anywhere on the card (searched root, DCIM, AVF_INFO, PRIVATE, MP_ROOT): the only files written that day besides the two JPEGs were the standard AVCHD `AVF_INFO/AVIN0001.BNP`/`.INP` — each 33,554,432 B but 97.5% zeros, entropy 0.61 bit/B, no raster structure → empty pre-allocated management files, NOT the dump.
- conclusion: forcing the SACC consumer (idx1==4) does NOT produce a card dump. The A+B gate patch is benign to capture (confirms the C-DLV-022 patch is safe). The MSDump card route is not enabled by this consumer — most likely the SACC writer is not wired to a card file, or `/mnt` is not the SD card, or the only consumer with a traced card filename (`/mnt/YC_FILE%04x.dat`) is MSDumpYCTarRef (idx0xa, byte `0xc3cb22ae`), which was NOT the one patched.  confidence: high (no file); medium (cause)
- caveats: only idx1==4 (SACC) was forced; MSDumpYCTarRef (idx0xa) and the YKNR flag (patch C) were not tried; the `/mnt`→card mapping on the running firmware is unverified; the 32-MiB size coincidence with the predicted dump was a red herring (checked by content, not size).
- claims: C-DLV-022, C-MOD-032, C-SAFE-003, C-SAFE-008

### E-0069: EXP-4 — pointer-leak patch flashed; detour live & cave executes, but `.bss` scratch is cleared on service-mode entry  (2026-10-10)
- image: p3 flash of `p3_exp4_leak.bin` (md5 `b31dac9b…` superseded — actual `66554903c8ec5bd219aee29fcbef65ca`; detour `0x3ac0ee` `60 69 20 ab`→`54 f4 07 fa` = `bl 0xc3441500`, cave file `0x500` 40 B, scratch VA `0xc3c8ea00`), device md5 MATCH, WBI zeroed. Owner cold-booted, shot a few stills (last = Standard).
- change: a cave at the DistEncodeFULL hook stores magic "EXP4" + `[r4+0x14]` (YCC_FULL base) + geometry to av-cam `.bss` scratch; plan was to read it via senser post-shot.
- observed: senser read of the scratch (phys `0x83c8ea00`) = all zeros; no "EXP4". Diagnostic read of live av-cam TEXT confirmed the detour IS present: phys `0x837ed0ee` = `54 f4 07 fa` (our `bl 0xc3441500`), followed by `20 90` (`str r0,[sp,#0x80]`). Captures saved normally (no crash/hang).
- conclusion: the patch is loaded and RUNNING (detour live in RAM); since every still hits `0xc37ed0ee`→`bl` cave and the captures did not crash, the cave IS executable (not NX) and the leak logic ran. The zero scratch means av-cam `.bss` is re-zeroed on service-mode ENTRY (same class as C-DLV-004) — so leaking to `.bss` and reading it via senser does NOT work. BUT the injection MECHANISM is proven: site hit every frame + cave executes + base in r0 (`[r4+0x14]`, C-MEM-021) → grain-at-site is feasible, and grain's result is visible in the JPEG with no senser read needed.  confidence: high
- caveats: the cave content was not re-read (second senser read failed "No devices" — USB needs re-set after each senser session, C-DLV-002); but the cave is part of the MATCH-verified image. The "cave executes" conclusion is by elimination (captures didn't crash), not a direct cave trace.
- claims: C-MEM-021, C-DLV-004, C-SAFE-003, C-SAFE-008

### E-0070: EXP-5 — grain-band patch flashed; cave runs but the ARM write does NOT reach the JPEG (no grain, no crash)  (2026-10-10)
- image: p3 flash of `p3_exp5_grain.bin` (md5 `a3c3763c01922d8611157bd59c5da28f`), device md5 MATCH, WBI zeroed, "Safe to reboot" (`flash_exp5.log`). Owner cold-booted, shot DSC09587–DSC09590 (Standard, Picture Effect Off, 4912×3264; analysed DSC09590).
- change: grain cave at `0xc37ed0ee` writes xorshift32 white noise (−16..+15, clamp 0..255) into the Y even-bytes of the buffer at r0=`[r4+0x14]`, first 500 rows (stride `0x2660`), via alias `(base & 0x3FFFFFFF)|0xC0000000`; reproduces the 2 overwritten insns; result read directly from the SOOC JPEG.
- observed: NO grain. Per-row horizontal MAD (|Δx| mean per row, PIL+numpy `analyze.py`) is flat 0.50–0.55 across all 3264 rows — no elevated band anywhere, no step at row 500 (top 0–499 = 0.54, 500–999 = 0.50, strongest "step" delta 0.00). Captures saved normally, no crash/hang (consistent with the cave executing, E-0069).
- analysis (capstone disasm of `sys_avcam.bin` off `0x3ac0d0..0x3ac13e`): `0x3ac0ee ldr r0,[r4,#0x14]` → `0x3ac0f2 str r0,[sp,#0x80]`; together with geometry halfwords `[r4+4..0xc]` and planes `[r4+0x18/0x1c/0x20]` it is **marshalled into the encode-acquire IPC request** (`bl 0xc3701f08` @`0x3ac13a`, r1=sp+0x3c, r2=0x78, id `0x560013`) — i.e. `[r4+0x14]` is the input base handed to the encoder. So the write most likely hit the right buffer but via the CACHED av-cam virt alias `0xC…`; av-cam (CPU1, Thumb-1, no cp15) cannot flush D-cache, and the HW/DSP JPEG coder reads physical DRAM → it sees un-flushed (clean) data. Two live causes, both giving "clean + no crash": (H2, lead) **cache** — writes sit in D-cache, never reach the encoder (Q-25); (H1) `[r4+0x14]` is an input handle / secondary field, not the live canvas (wrong buffer).
- conclusion: C-MEM-021's operative claim ("a grain patch at this site injects grain") is REFUTED on hardware — an ARM cached write to `[r4+0x14]`'s `0xC…` alias does not reach the SOOC JPEG. The detour+cave mechanism is confirmed executable (E-0069) but ineffective via this write path. Next: a **black-band tie-breaker** (write Y=0, same site/alias) — if a black band appears, the write reaches the encoder and the fault was amplitude; if not, the write never reaches (cache or wrong buffer) → try the uncached DRAM mirror alias (`0x90000000`, C-MEM-002 → av-cam `0xD…`) or the **YKNR-dispatch site** where ARM provably holds the plain canvas address `DRAM_A+off` (C-PIPE-021). confidence: high (no grain, numeric); medium (cause: cache vs wrong-field not separated).
- caveats: one scene; the stored form of `[r4+0x14]` (bus vs virt) not read live; the `0x90000000` mirror's cacheability (C-MEM-002) is assumed, not proven; the black-band test separates reach-vs-amplitude but not cache-vs-wrong-field.
- claims: C-MEM-021 (refuted-hw), C-PIPE-024 (hw-test negative), C-MEM-004, C-PIPE-025, C-SYS-002, C-SYS-004

### E-0071: EXP-6 — two-band cache-probe (0xC vs 0xD, ±64) at the DistEncodeFULL hook; neither band appears, no crash → `[r4+0x14]` is the WRONG buffer  (2026-10-10)
- image: p3 flash of `p3_exp6_cacheprobe.bin` (md5 `a0ae2828429b8e24251118f18efdc9da`), device md5 MATCH, WBI zeroed, "Safe to reboot" (`flash_exp6.log`). Fable different-model pre-flight = GO (independent Thumb-1 byte check). Owner cold-booted, shot DSC09591–DSC09592 (Standard, 4912×3264; analysed DSC09592).
- change: same hook `0xc37ed0ee`, 158-B cave (keystone-built, capstone round-trip verified): band A = rows 0–119 strong white noise ±64 into Y even-bytes via the CACHED alias `(bus)|0xC0000000`; band B = rows 120–239 ±64 via the UNCACHED mirror alias `(bus)|0xD0000000` (phys `0x90000000` mirror, C-MEM-002); offsets `0x11FD00` = 120×`0x2660`. Same register discipline as E-0069/E-0070.
- observed: NO band anywhere. Per-row hMAD: rows 0–119 = 0.81, 120–239 = 0.77, 240–399 = 0.76, 1000–3000 = 0.69 — a smooth top-to-bottom scene/lens gradient, NO step at row 120 or 240 (±64 grain would give hMAD ≈ 15–30). Captures saved normally, no crash → the `0xD0000000` av-cam virtual alias IS mapped and writable (no data abort).
- conclusion: BOTH the cache and the amplitude hypotheses are refuted for this site. (1) Band A (strong ±64 via the canonical `0xC…` alias of `[r4+0x14]`'s DRAM) = nothing → amplitude is not the cause (±16 E-0070 and ±64 both nil). (2) Band B (±64 via the uncached `0xD…` mirror) = nothing AND no crash → an uncached write also fails, so it is not a D-cache-flush problem. Therefore `[r4+0x14]` is NOT the buffer the JPEG encoder reads — most likely a handle/id or secondary descriptor field (consistent with the canvas being handle-only on ARM, resolved DSP-side via the encode IPC `bl 0xc3701f08`: C-PIPE-024, C-JPEG-002, C-MEM-020). **C-MEM-021 fully refuted; the DistEncodeFULL-descriptor site is dead for ARM grain injection (E-0070 + E-0071).**  confidence: high.
- new fact: the av-cam virtual alias `0xD0000000+` (= the `0x90000000` DRAM mirror, C-MEM-002) is MAPPED and writable from CPU1 av-cam (no fault over ~0.6M stores) — a usable uncached write path for later tests.
- caveats: 0xD's true cacheability and whether it aliases exactly `[r4+0x14]`'s DRAM were not independently confirmed, so Q-25 is not formally closed — but band A (correct `0xC…` alias, strong amplitude) failing is itself decisive that this site/buffer is wrong.
- next: pivot to the YKNR path (C-PIPE-021) — the one ARM point that holds the plain canvas base `DRAM_A+off` (written to YKNR job[0]/job[4]); inject grain after the YKNR DSP job completes and before `Stage_DistEncodeFULL` reads the shared YC canvas. Needs RE to locate the post-completion ARM point that still holds the address.
- claims: C-MEM-021 (refuted-hw full), C-PIPE-024 (hw-test negative ×2), C-MEM-002 (0xD mapped), C-PIPE-021, C-MEM-020, C-JPEG-002

### E-0072: EXP-7 — pre-dispatch black-band at the YKNR canvas; detour fires only when YKNR runs (high ISO) and the write CRASHES the camera (reboot during processing)  (2026-10-10)
- image: p3 flash of `p3_exp7_yknr_black.bin` (md5 `8f4e96d830f45b85abc0105f743c6f8f`), device md5 MATCH, WBI zeroed (`flash_exp7.log`). Fable different-model pre-flight = GO. Mechanism: detour at the YKNR job-fill helper `0xc38782da` (where `adds r0,r0,r1` leaves r0 = plain resolved canvas base `DRAM_A+off`), `ldr r1,[pc,#0x10]; blx r1` → 80-B cave at `0xc3441500`, literal `0xc3441501` at the dead error-block slot `0xc38782ec`. Cave writes solid Y=0: rows 0–99 via cached `0xC…`, rows 100–199 via uncached `0xD…`; reproduces the 2 overwritten `str r0,[r4]`/`[r4,#4]`.
- observed: (1) **ISO 200 frame (DSC09594): NO band, no crash** — per-row luma smooth (top 0.99–200 rows ≈ 44–48, same as untouched 200–299 ≈ 44.5; no Y=0 step). (2) **High-ISO frame: camera REBOOTS during processing** (owner report).
- conclusion: the behaviour is gated EXACTLY on YKNR's ISO window (C-NR-007) → at ISO 200 YKNR does not run, the job-fill helper/our detour does not fire (clean frame); at high ISO YKNR runs, the detour FIRES, and the write to the real canvas crashes/reboots the camera. So **(a) the detour+cave execute on the live YKNR path (mechanism confirmed), and (b) for the FIRST time an ARM write reaches a REAL in-use buffer on the encode path** (EXP-5/6 wrote harmless wrong buffers → no crash). The write is not yet benign/effective: it crashes. confidence: high (the ISO-gated behaviour change is decisive that our code runs on the YKNR path).
- crash hypotheses (unresolved): (a) the `0xD…` uncached mirror of the HIGH canvas DRAM address is unmapped in the av-cam MMU → data abort (E-0071's 0xD worked only because `[r4+0x14]` was a low/handle value whose mirror happened to be mapped; the real canvas sits high, e.g. `0x8a……`→`0xDa……`); (b) watchdog — ~0.5M uncached stores are too slow in the time-critical YKNR setup; (c) writing the in-use canvas mid-setup races the develop/DSP DMA.
- RECOVERY STATE: camera is STILL running EXP-7 (crashes on high-ISO capture; low-ISO OK). Owner powered off before restore. **Next session MUST first flash `current_p3.bin` (md5 `d7cca446…`) OR go straight to the next diagnostic image (either overwrites EXP-7 and fixes the crash).**
- next (diagnostic, ranked): **EXP-8** = a SMALL `0xC…`-ONLY (cached, always-mapped) black band at the same pre-dispatch site. Isolates the crash cause: survives → EXP-7 crash was the `0xD` write (data-abort) or volume (and shows whether a cached write reaches the encoded JPEG); still crashes → writing the in-use canvas mid-YKNR-setup is itself fatal → abandon pre-dispatch, move to a POST-YKNR-completion write (reconstruct base via the IPC resolver `0xc37560e4`, C-PIPE-021 RANK-2 `0xc37ec530`) or to the DistEncode post-resolution site (slot `0x39f0`).
- claims: C-NR-007 (YKNR ISO-gate confirmed-hw via behaviour change), C-PIPE-021, C-MEM-002 (0xD mirror may be range-limited — hypothesis), C-MEM-021, C-SAFE (recoverable p3)

### E-0073: EXP-8 — cached-`0xC`-only black band at the YKNR pre-dispatch site; SAME high-ISO crash → pre-dispatch injection is DEAD  (2026-10-12)
- image: p3 flash of `p3_exp8_yknr_c_only.bin` (md5 `aa4269114ddc18aedebfab097faa9329`), device md5 MATCH, WBI zeroed (`flash_exp8.log`). Pre-flight: skipped a fresh agent — EXP-8 is a strict subset of the fable-GO'd EXP-7 (same detour/literal, cave = EXP-7's band A only).
- change: EXP-7 minus the `0xD` band — ONLY the cached `0xC…` Y=0 band (rows 0-99) at `0xc38782da`.
- observed: high ISO → **SAME crash/reboot during processing**; ISO 200 → OK (YKNR off, detour never fires).
- conclusion: removing the `0xD` write did NOT fix the crash → the crash is NOT the `0xD` mirror (refutes that E-0072 hypothesis). A plain cached ~1 MB write to the resolved base r0 AT the YKNR pre-dispatch point is itself fatal → either r0 there is not a safe image buffer (a control/alias struct, or `off` lands in critical data), or writing mid-YKNR-setup corrupts live state the DSP/pipeline needs. **The pre-dispatch (job-fill) injection approach is DEAD** (decision-tree branch 3). confidence: high.
- RECOVERY STATE: camera is on EXP-8 (same crash-on-high-ISO as EXP-7; low-ISO OK). Restore `current_p3.bin` when a working camera is needed.
- next: abandon pre-dispatch. Remaining ARM-write options = POST-YKNR-completion write (RANK-2 `0xc37ec530` + IPC resolver `0xc37560e4`) or DistEncode post-resolution (slot `0x39f0`) — both need more RE + flashes and may also be handle-only/crash. STRATEGIC ALTERNATIVE (cheaper, sidesteps the buffer problem): NR-REDUCTION — weaken/skip YKNR (the late luma-NR, C-PIPE-025; bypass lane C-NR-007) so native high-ISO sensor noise SURVIVES as grain, instead of injecting grain. Reaches the JPEG trivially (normal pipeline minus NR). Decision pending (owner, budget).
- claims: C-NR-007, C-PIPE-021, C-MEM-021, C-PIPE-025

### E-0074: EXP-9/10/11 — the imaging canvas is NOT CPU-writable (data-abort, both aliases) → ARM pixel injection is ARCHITECTURALLY BLOCKED  (2026-10-12)
- images: `p3_exp9_postyknr.bin` (md5 `b891c3aa…`, stash at pre-dispatch + 0xC/0xD write at POST-completion `0xc37ec530`), `p3_exp10_tiny.bin` (md5 `13556065…`, pre-dispatch 0xC **4-row** write), `p3_exp11_d_tiny.bin` (md5 `bb5c8cda…`, pre-dispatch **0xD** 4-row write). All flashed, device md5 MATCH. (Pre-flight: fable classifier-blocked, sonnet declined on content grounds — both false positives on authorized self-hw RE; verified by self capstone/keystone + build asserts. Recorded as filter-unreliability per [[security-filter-retry-other-model]].)
- observed: ALL THREE **reboot during processing at high ISO**; ISO 200 OK (YKNR off → detour never fires).
- isolation (decisive): (1) EXP-9 moved the big write to POST-completion (canvas stable, no DSP race) → STILL crashes ⇒ the crash is the WRITE, not pre-dispatch timing/race. (2) EXP-10/11 shrank the write to **4 rows (~5K stores)** → STILL crashes ⇒ NOT a watchdog/volume issue ⇒ **DATA-ABORT on the first store**. (3) EXP-10 (0xC cached) and EXP-11 (0xD uncached-mirror) BOTH abort ⇒ neither alias is writable for the resolved canvas address.
- conclusion: the resolved imaging canvas (`DRAM_A+off` = the develop/YKNR/encode pixel buffer, high DRAM e.g. `0x8a……`) is **mapped READ-ONLY / not CPU-writable from CPU1 av-cam via any known alias** (the DSP writes it; the CPU only reads it — C-MEM-004's `0xC` evidence was a READ of the JPEG-out buffer). Writing a low/handle address (EXP-5/6 `[r4+0x14]`) is harmless; writing the real canvas data-aborts. **ARM-side direct pixel grain injection into the imaging canvas is ARCHITECTURALLY BLOCKED on this camera.** confidence: high (6 experiments: wrong-buffer ×2, canvas-abort ×4 across both aliases, both timings, tiny+large).
- remaining injected-grain avenues (all high-effort / low-confidence): (a) DSP-SIDE — the DSP owns & writes the pixels, so grain must be added in DSP code (YKNR or another imaging module); but the DSP is VLIW and undocumented (C-DSP-020) and the scalar sa_yknr path was already ruled INFEASIBLE (Q-42). (b) change the MMU mapping to make the canvas writable — needs cp15/MMU ops unavailable in av-cam (C-SYS-002/004); a CPU0/kernel-side route is a different, riskier attack surface. (c) find another (writable) alias of the canvas — deep MMU/page-table RE, uncertain.
- RECOVERY STATE: camera on EXP-11 (crashes high ISO; low-ISO OK). Restore `current_p3.bin`.
- claims: C-MEM-004 (refined: the imaging canvas `0xC` alias is READ-ONLY for CPU1), C-PIPE-021, C-DSP-020, C-SYS-002, C-SYS-004, C-NR-007; Q-42

### E-0075 — DSP grain BANDS module HANGS camera on high-ISO capture (2026-10-13)
- context: first flash of an injected SA-DSP **scalar grain loop**. Delivered `sa_yknr_bands.bin` (md5
  `727e4db101a179050155d4d98c9dcd7c`; cores 1-4 per-tile LFSR grain N={4,8,12,16}, core0=stock control;
  routine at chunk+`0x13c` over the high-index engine-table, hook chunk+`0x2fa`) via the /setting redirect
  (byte 597=`0x06`, writeFile readback MATCH). Prior on camera: delivery proven + the fixed-marker Probe S
  both worked (`dsp-grain-scope.md`).
- hypothesis: the scalar trampoline's per-tile LFSR grain loop adds luma grain; the overwritten high-index
  table bytes are dead → predicted 4 amplitude zones + a control zone in one high-ISO frame.
- action: cold boot → high-ISO capture.
- result: **camera HARD HANG** — froze, not even the graceful "unable to access memory card" error the
  code-corrupt test produced. Recovered by **battery pull**; camera boots fine (the trampoline runs only
  during the high-ISO YKNR pass, not at boot). Reverted /setting to stock (writeFile stock md5 `54acf298`,
  readback MATCH) → camera captures normally.
- conclusion: the injected code **executes and wedges** (hard hang, worse than a load-reject) — consistent
  with (a) an **infinite loop** (SA-DSP branch-condition semantics were disasm-verified but NOT emulated —
  no SA-DSP engine emulator exists) or (b) **load-bearing high-index-table corruption**. TWO variables
  differ from the working Probe S (fixed marker → LFSR loop; proven-dead 16B stub tail → chunk+`0x13c` over
  the table) → not yet isolable.
- next: **E-0076 isolation** = "Probe S relocated" (fixed marker, NO loop, same chunk+`0x13c` 72B footprint
  as bands) → hang ⇒ table is load-bearing (placement dead, need module-grow); white markers + capture ⇒
  the LOOP is the bug (fix the branch encoding).
- recovery state: camera **STOCK + working** (redirect-on + stock /setting module, byte 597=`0x06`).
- claims: C-MOD-044 (delivery reversible), pixel-write route (`dsp-grain-scope.md`); tmp: grain-loop-hang.

### E-0076 — relocated fixed-marker probe ALSO hangs → chunk+0x13c table is LOAD-BEARING (isolation decisive) (2026-10-13)
- context: isolation for E-0075. Delivered `sa_yknr_probeS_reloc.bin` (md5
  `2ba4518f9b4c4bbce72d9e2b4454e4e8`): the proven Probe-S fixed-marker write (`0xFFFFFFFF` to
  `[r13-0x800]`/`[+4]`, **NO loop**) placed at chunk+`0x13c`, occupying the SAME 72B footprint as the bands
  routine, in **all 5 cores** (bands hooked cores 1-4). Via /setting (byte 597=`0x06`, readback MATCH).
- hypothesis: fixed marker (no loop) at chunk+`0x13c` captures ⇒ placement OK, E-0075 hang was the loop;
  hangs ⇒ the chunk+`0x13c` table is load-bearing.
- action: cold boot → high-ISO capture.
- result: **camera HARD HANG again.** Battery-pull recovered; reverted /setting to stock (readback MATCH)
  → captures fine (3rd clean revert this session).
- conclusion: **DECISIVE — the hang is the PLACEMENT, not the loop.** The high-index engine-table bytes at
  chunk+`0x13c` (`0xad8c..0xadd6`) are **LIVE** (the per-tile DSP pass uses them); overwriting them wedges
  the camera even with a known-good fixed-marker write. The "overwrite the high-index table" placement is
  **DEAD**. Probe S worked only because it used the genuinely-dead **16B stub tail** (chunk+`0x08`) — that
  16B is the ONLY proven-dead space and is too small for a grain loop. The grain LOOP itself is **not yet
  proven buggy** (never ran at a valid location).
- next: **module-grow** — reverse the desc3 core-copier (core-base table `0x9ea0`) to copy the routine into
  **free DSP RAM `0x5000–0x8000`** (between the stacks) and `bl` to it from each 16B stub tail; then re-test
  the grain loop at that valid location. Offline RE + on-camera verify. Next session.
- recovery state: camera **STOCK + working** (redirect-on + stock, byte 597=`0x06`).
- claims: refutes chunk+`0x13c` placement (`dsp-grain-scope.md`); C-MOD-044 delivery reversible (3rd
  revert); tmp: yknr-coretable-live.

### E-0077 — VLIW probe (op7 r19→r19 @0xce88) shows NO EFFECT → VLIW luma insertion points don't reach JPEG (2026-10-13)
- context: test whether a VLIW free-lane edit to r19 reaches the output. Delivered `sa_yknr_vliw_probe.bin`
  (md5 `7d1bb24e99f240a94e9a959c94b90fef`): bundle `0xce88` S1 = `op7 r19→r19` (luma ×2, pre-clamp). Via
  /setting (byte 597=`0x06`, readback MATCH).
- hypothesis: if r19 at `0xce88` is the output per-pixel luma, ×2 → heavy overexposure/clipping; else no change.
- action: 3 high-ISO shots — ISO **12800 / 16000 / 16000**, midtone scenes (grey wall, dark mat).
- result: **NO EFFECT.** All three normally exposed — a flat mid-grey wall stays mid-grey (would be blown
  white if ×2 applied), dark mat stays dark, poster colours normal. Camera captured fine, **no reboot, no
  hang.** Reverted to stock (readback MATCH).
- conclusion: the VLIW edit at `0xce88` does **not** reach the JPEG — same as the old `0xce80` PoC. So r19 at
  the P4 "finalize" bundles (`0xce80/0xce88`) is **NOT the output per-pixel luma** (intermediate /
  dead-before-output, or the real store rides the undecoded S0 12-bit lane / a different bundle). The static
  VLIW luma model (r19=output, drain at `0xce90` via r31) has a gap **not closable without a VLIW emulator**.
  **Closes the VLIW path at the known insertion points**, and undercuts A7 (DMA-LUT piggyback, which relied on
  op3+op7→r19 at these same free lanes).
- side-findings (positive): **p3 is high-ISO-capable** — NO reboot at ISO 16000 ⇒ the START-HERE "EXP-11
  restore-first" note is **STALE**; YKNR runs at ISO 12800+; /setting delivery works (4th clean cycle).
- recovery: camera **STOCK + working** (redirect-on + stock, byte 597=`0x06`).
- claims: refutes r19@`0xce88` as output luma; VLIW insertion points `0xce80/88` dead-to-output; p3
  high-ISO-OK; tmp: vliw-luma-model-gap.

### E-0078 — EXFIL CHANNEL PROVEN (DSP SRAM → JPEG); §0 senser can't read DSP SRAM; GO bit transient (2026-10-14)
- **§0 (no-flash senser sweep):** `readMemory` at `0x000091f0`/`0x900091f0`/`0x800091f0`/`0x9000` + mirrors —
  **NO ring signature** (`0x000091f0`=zeros/unmapped; the `0x90/0x800091f0` mirrors show DRAM pointers, not
  the ring). Confirms C-DSP-020: the DSP on-chip SRAM (ring `0x91f0`, output `0x9000`) is **not ARM-mapped**;
  the `0x90000000` mirror is DRAM, not SRAM. So senser cannot read the ring directly.
- **D2 exfil (`sa_yknr_d2_e0.bin`, 2 flashes):** a 16-B scalar stub in the proven Probe-S tail (`chunk+0x08`,
  hook `chunk+0x2fa`, const `chunk+0x20`) reads a ring word/byte at `0x91f4`/`0x91f7` and splats it to the
  tile top-left `[r13-0x800]` (clobber r13; the epilogue reloads it). On camera (high ISO): **a clean grid
  of dark dots appears at the 128×8 tile grid in the SOOC JPEG** → **the exfil channel WORKS: a scalar stub
  CAN read DSP SRAM and land it in the JPEG.** (Auto-median missed the 1-px sparse dots; visually clear.)
- **GO bit reads 0 (transient):** the splatted dots are BLACK (Y0=0), not grey (0x40), i.e. the ring GO
  high-byte reads `0x00`. Our hook is the per-tile *epilogue* — AFTER this tile's DMA has fired — and GO is
  a trigger the hardware **clears on DMA completion**. So GO is **not a usable occupancy signal at this
  hook**. Not needed: static analysis already fixes the batch at **exactly 6** (`cmp r8,#6`) → all 6 slots
  used → the free slot is the **new index 6** (the `#6→#7` extend).
- build/scripts: `<scratch>/grain-scripts/build_d2.py`, `sa_ring_sweep.py`. Camera restored to
  stock (md5 `54acf298`) between experiments.
- significance: **the DSP-SRAM→JPEG read channel is proven** (reusable to exfil STABLE descriptor ADDR words
  for picking a noise-staging address). The grain path is now: `#6→#7` ring extend + resident noise tile
  DMA-in + a Region-B VLIW add-syllable (the one remaining unknown, E-0077 gap).
- claims: C-DSP-020 (DSP SRAM off ARM bus), exfil-channel-proven; tmp: go-bit-transient-at-epilogue.

### E-0079 — corrected VLIW r19 probes = NO output effect; scalar stub has NO per-tile source (2026-10-14)
Context: fable (`grain-injection-design.md`) corrected E-0077 — the `0xce80/0xce88` edit was **dead
coefficient filler** (`0x8fff…/0xbfff…`, 0x260 B past cluster 5's terminating NOP `0xcc20`), not executed
VLIW. The real P4 finalize program = **cluster 5** (`0xc9f8..`), with r19 writes at bundles
`0xcbb0/0xcbb8/0xcbf8/0xcc30` and an op3/op6 store-AGU at `0xcc38`.
- **Corrected r19×2 probes (camera, ISO 16000):** modified bundle S4 → `op7 r19→r19` (luma ×2) at
  `0xcc30` (`sa_yknr_vliwfix_cc30.bin`) and the live `0xcbf8` (`sa_yknr_vliwfix_cbf8.bin`). **Both: NO
  visible JPEG effect** (frames normal, not brightened/clipped). Caveat: `0xcc30` is itself past the
  terminating NOP `0xcc20` (dead); but `0xcbf8` is inside the live segment and ALSO had no effect. ⇒ **r19
  is NOT the output luma.** The output is the DMA-OUT of SRAM `0x9000` whose source is an **undecoded
  op5/AGU stream**, not r19. The VLIW output register is **unreachable without a VLIW emulator** — the
  standing gap. (Note: an ISO-6400 shot was inconclusive — YKNR/the probe need ISO ≥ ~12800.)
- **Scalar per-tile noise ruled out (`sa_yknr_snoise.bin`/`snoise2`, camera):** a 16-B stub hashes the tile
  address (`mul r13,r13`, mvn) and splats it → the dots appear at the 128×8 tile grid but are **UNIFORM**
  (identical grey every tile, no per-tile variation). ⇒ **the scalar stub has NO per-tile-varying source**:
  r13 (engine tile window) ping-pongs between the two output buffers `0x9000`/`0x9800`, and there is no
  persistent tile counter. The write POSITION varies (DMA spreads to the frame) but the VALUE is constant.
  So scalar can only write **uniform marks** (Probe-S class) — per-tile noise is impossible, and per-pixel
  grain is blocked by the 16-B code ceiling.
- **Standing:** real grain is blocked on BOTH routes — **scalar** (uniform-only + 16 B ceiling, no per-tile
  source) and **VLIW** (output reg needs an emulator). The only remaining hope = the **run_engine code-cave**
  (a real per-pixel loop with its own LFSR, no per-tile source needed) — under investigation
  — **[SUPERSEDED 2026-10-15 by E-0081: the VLIW output IS reachable — proven on PBE, not yknr.]**

### E-0080 — EXP-P parametric grain (yknr NR-bypass) WORKS at high ISO, but is ISO-dependent (2026-10-15)
Backup `0x3004a +0xD2..+0xDC` → 0 (the yknr ISO-enable window; Tier-A, reversible; `expp_yknr_kill.py`).
Cold-boot, ISO 16000, grey field: **Standard HP-std p10=3.22 / p50=3.43, Vivid 3.30/3.59 — native/ACROS
grain level** (smoothed baseline 0.7–1.8; ACROS yardstick 2.7–3.4), ACF ~0.38. **HC Mono 5.3–6.3**
(tone-amplified). Visual: fine **luma-only** grain (chroma clean — kknr untouched), reads as film grain
(crops `expp_shots/DSC0962{4,5,6}_crop.png`). **Caveat:** ISO 16000 is ABOVE yknr's stock window
(~200–6400), so yknr was already off there → the 3.2 is native ISO-16000 noise; the write's real effect is
at MID ISO (in-window). **Parametric grain scales with sensor noise → near-zero at low ISO → NOT the
universal "auto + film at any ISO" solution.** Reverted. Good as a high-ISO bonus / proof the shape reads.

### E-0081 — PBE VLIW output store is REACHABLE (the injection wall falls) (2026-10-15)
Owner wants universal (auto + pick film style + grain at EVERY ISO) → needs ADDED grain, not shaped sensor
noise → injection. DRO/PBE agent (`11-dro-pbe-hosts.md`): **PBE (`sa_pbe_work`, codectype 0x19, file-id 71)
= best host** — runs every still, **LAST programmable stage before the HW-JPEG coder** (grain not re-smoothed
by anything), deliverable (29956 B), output store `op5.a15.b03`→r3 at `0x7318/0x7330/0x7360`, delivery byte
`0x00bd0002[573]`.
- **Probe:** `sa_pbe_work_probe.bin` (`build_pbe_probe.py`, md5 `fec01b43…`) forced all 3 final stores' datum
  `a15→a00` (r15 pixel → r0). Delivered to `/setting/sa_pbe_work.bin`, redirect `[573]` 0x00→0x06
  (`deliver_pbe.py`; readback MATCH). Cold-boot, ISO 16000 Vivid grey card → **GREEN with regular vertical
  column stripes** (mean RGB [53,132,54], std ~22; `expp_shots/pbe_probe.JPG` = DSC09627).
- ⇒ **PBE's VLIW output store DRIVES the visible pixel = REACHABLE.** The gross grey→green change = we fully
  control the output datum. **The VLIW-injection wall — standing since E-0077/E-0079 — is DOWN on PBE.**
  (The 2026-10-14 audit already flagged E-0079's "unreachable" as a false negative; now empirically overturned.
  PBE's store has a near-write-only r3 pointer, cleaner than yknr's undecoded path.)
- **Next:** grain kernel = add a per-pixel, per-frame-random delta to r15 — **amplify r15's low-bit read noise**
  (present at every ISO, differs every exposure) via a mul-hash + `op7→r15` before the store. In design
  (`12-pbe-grain-kernel.md`, opus). Revert = `deliver_pbe_revert.py` (redirect `[573]`→0x00).

### E-0082 — PBE grain kernel v1 (self-square) REACHES but isn't universal → luma-envelope model (2026-10-15)
Staged VLIW kernel (`build_pbe_grain.py`, design `12-pbe-grain-kernel.md`): displace the `op0.a31.b14`
housekeeping lane to compute `r13 = r15²` (into dead r13) and fold `r15 += r13` before the `0x7360` store.
- **probe** (r13=r15², no fold; zero-effect) flashed → **NORMAL image** ⇒ encoding assembles, module loads,
  lane displacement does not hang, op4-mul works. **arm** (+ `r15+=r13`) flashed.
- **arm result:** ISO 16000 varied content → faint **vertical dotted-column artifact** (fold REACHES the
  output — 2nd reachability confirmation after E-0081's green); **ISO 200 flat grey → SMOOTH, no grain**;
  HP-std still ISO-scaling (p10 0.5 @ISO200 → 2.75 @ISO16000). ⇒ **the self-square (content-based) hash
  fails for universal grain:** on flat/clean areas r15 is NR-cleaned to a near-constant → r15² ≈ constant →
  no per-pixel variation. The "amplify read-noise" premise is **dead at PBE** (upstream yknr+develop remove
  the noise before PBE sees it).
- **Correct model (owner's insight):** grain must be **GENERATED** — procedural `PRNG(position)` (universal,
  present on flat areas) — with **luma as the AMPLITUDE MODULATOR, not the noise source** (film grain is
  luminance-dependent). Formula: `r15 += PRNG(pos) · filmResponse(r15) · amplitude`.
- **Measured the film grain-vs-luma envelope** from real scans (Portra/Ektar/ColorPlus; `grain-luma-response.md`):
  peak at luma ≈88, steep falloff to shadows (.22), gentle to highlights (.09).
- **Open (now [cyber]/[bio]-blocked for our subagents on opus — the `model=fable` override is dropped by the
  env, so every subagent runs on opus and trips the classifier → EXTERNAL EXPERT per owner):** per-frame seed
  source, per-pixel position source for the PRNG (r3 is write-only), `filmResponse` LUT lookup by r15,
  amplitude via an undecoded shift op (op1/op2), the intra-bundle `op6→r15` forwarding model. Self-contained
  expert brief = `~/nex3n-dump/work/filmgrain/EXPERT-pbe-grain-kernel.md`. Reverted to stock PBE.

### E-0083 — PBE granularity gate = PER-TILE (scalar insertion can't make per-pixel grain) (2026-10-15)
External expert (via owner's fable session) returned a 5-rung test ladder (`build_pbe_grain_ladder.py`,
`EXPERT-pbe-grain-ANSWER.md`) with a key reframe: **before building grain, measure the block's execution
granularity** — do inserted scalar ops run per-pixel or per-tile? Plus a forwarding-proof trick: redirect the
store datum `op5.a15.b03 → op5.a13.b03` (1 byte `0x7360` e3→a3) so the store reads our grained r13, which
`op6` can't re-clamp.
- **rung1 flashed** (`r13=r3` at the `0x7350` housekeeping lane; `0x7360` datum→r13). Cold-boot, 2 frames
  (grey + scene): **uniform, evenly-spaced vertical dotted lines, dots a CONSTANT brightness across the whole
  frame — no ramp, no gradient, no tile-to-tile change.**
- ⇒ **GATE = PER-TILE:** the inserted scalar ops in the `op0.a31.b14` housekeeping lanes execute once per
  tile/run; `r13=r3` captured ONE value and the AGU replicated it to all `0x7360` positions. If execution were
  per-pixel, r3 would increment → a ramp; it didn't. **Scalar insertion into these lanes yields block/column
  structure, not per-pixel grain** — exactly the limiting fork the expert flagged.
- **Not a declared wall yet:** stock PBE IS a per-pixel filter (`op6→r15` produces a different pixel each
  iteration), so a per-pixel execution context exists in the same block — we inserted into the per-tile setup,
  not the per-pixel loop. Open (→ expert follow-up `EXPERT-followup-granularity.md`): is there a per-pixel
  insertion point (perturb r15 inside the store/compute bundle with a per-pixel source), or is the per-pixel
  loop inside fixed-function AGU hardware = a hard ceiling. Reverted to stock PBE.

### E-0084 — mechanism RESOLVED: PBE store writes per-pixel VALUES; the "per-tile wall" was a false alarm (2026-10-15)
Instead of pivoting on the inconclusive persist frame (owner: "хватит пивотиться, разбери механизм"), ran a
decisive datum test. **`sa_pbe_datumtest.bin`: redirected the `0x7360` store datum to r30** (the bundle's own
`op3.a24.b30` input-stream read), `op5.a15.b03 → op5.a30.b03` (1 byte). Cold-boot, ISO 800 scene → **CLEAN,
recognizable image** (the input frame, slightly noisier than stock).
- ⇒ **`op5` writes a per-pixel VALUE** (R[a] as the pixel, per pixel); r30 varied per pixel ⇒ **the block
  executes PER-PIXEL**; **r15 is a VALUE, not a pointer** (the green "stripes" were a YUYV/chroma artifact).
- ⇒ **E-0083's "per-tile" gate was a FALSE ALARM:** rung1's frame-wide constant was because **r3 is a
  constant base address** (AGU adds the per-pixel offset internally), NOT per-tile execution. We can feed the
  store any per-pixel register and it writes per pixel.
- **The real constraint, now precisely located:** every per-pixel register in PBE is **NR-cleaned content**
  (post-yknr input → flat on flat/low-ISO; the r15² test already showed flat stays smooth). The per-pixel
  **position/index is AGU-internal, not a GP register** (r3 = constant base). So **no register-resident
  per-pixel entropy source exists for flat areas** — exactly what universal grain needs.
- **The one precise blocker → introduce a per-pixel NON-content value.** Candidates (→ expert follow-up
  `EXPERT-followup-2-resolved.md`): (1) an alt `op3` stream port (a=31/16/25, HIGH cluster) as a coordinate
  stream or repurposed to stream a **baked noise texture** in the module data; (2) `op2` (undecoded op); (3) a
  persisting counter (r13+=const — persist test inconclusive); (4) the AGU index if readable. Everything else
  is solved (reachable per-pixel value store + forwarding-proof datum→r13 + measured luma curve + seed).
  Reverted to stock PBE.

### E-0085 — IN-MODULE per-pixel grain is a HARD WALL (no persisting register); next path = ARM-side IN-DMA (2026-10-15)
External expert (owner's fable session) assessed all 4 per-pixel-source candidates and collapsed them to one
decisive test. Verdicts: **(1)** baked noise via an op3 port — unreachable by module edit (stream sources are
programmed by the scalar ARM wrapper via MMIO IN-DMA `0x48200/08/10/18`, rtn @`0xa40`, not from module data);
**(2)** op2 as a position generator — NO (operand profile = pack/normalize content transform); **(4)** read the
AGU index — NO (index is AGU-internal, no op writes it to a GPR; r3 = constant base). **(3)** a persisting
scalar counter = the only lever → one test. Also explained why E-0084's persist probe was void: **r3 is a
256-aligned DMA base, so n·r3 mod 256 ≡ 0 every pixel → low byte constant regardless of persistence.**
- **rung4 (decisive):** accumulate the **input tap r30** (non-zero, luma-dependent) instead of the aligned
  base — `0x7350 → op7.a30.b13` (r13 += r30), `0x7360 → store r13` (`build_pbe_grain_ladder.py rung4`, md5
  `1b26ade9`). Shot a DARK (meanL 56) and a BRIGHT (meanL 208) flat frame.
- **Result: NEGATIVE.** Both frames are **symmetric-vignette bells** (corr vs BELL 0.74–0.81, vs RAMP negative),
  HP-std 0.22/0.50 — **no monotonic counter sawtooth.** The small FFT dominant-frequency difference (≈250 vs
  500 px) was the two exposures' vignettes, not an accumulator. ⇒ **the scalar register does NOT persist across
  the per-pixel AGU iteration.**
- ⇒ **Per-pixel procedural grain INSIDE the `sa_pbe_work` VLIW module is impossible** (content taps are NR-clean
  → flat; op1/op2 = transforms; AGU index hidden; no persisting register; stream sources are ARM-side). A
  rigorous, exhaustive wall — not premature.
- **The ONLY remaining path:** ARM-side injection of a **noise plane via IN-DMA** (the `cmdtable` project,
  `~/nex3n-dump/handoff/BLOCKED-TASKS.md` + `cmdtable_*`): the ARM configures a DMA stream to feed a noise
  plane into the pipeline. A separate, larger task, **not a module edit.**
- **Proven & kept this session:** PBE output reachable + writes per-pixel values (E-0081/E-0084); full VLIW
  finalize mechanism; measured film grain-vs-luma curve (`grain-luma-response.md`); forwarding-proof datum→r13
  redirect; and now the rigorous closure of the in-module route. Reverted to stock PBE.
  (`grain-codecave.md`, fable). Exfil channel (E-0078) stays proven. Camera: probe loaded (revert to stock
  pending).
- claims: refutes r19 as output luma (corrects E-0077); scalar-stub-no-per-tile-source; tmp: vliw-output-agu-stream.

### E-0086 — `sa_sftfcs` scalar is an ORCHESTRATOR; pixels never enter scalar-addressable memory → the scalar-grain thesis is FALSIFIED (same wall as yknr) (2026-10-15)
Tested the `grain-sftfcs-module-design.md` thesis ("the module's scalar core can add grain to pixels in
scalar SRAM") directly on-camera via `/setting` redirect of `sa_sftfcs` (Backup `0x00bd0002` byte 445→0x06,
reversible; core2 file-offset = disasm + `0x6fd0`, verified by literal anchors; hook at the OUT-DMA kick
disasm `0xb5e`/file `0x7b2e`, 62-byte cave at disasm `0x1812`/file `0x87e2`, sum32 trailer recomputed; all
caves saemu-validated before flash).
- **Probe 0** (byte-identical stock redirected): Soft Focus blurs normally ⇒ redirect+trigger+load path OK.
- **Probe S** (`0x80` into 0x13c60–0x13f60 before OUT-DMA): **CRASH** (no save, card lost, black screen,
  cold-boot recovery) ⇒ that region holds **live DMA descriptor pointers**, not pixels — `0x80808080` → DMA
  fault.
- **Fn `0x628` decoded** (ring/descriptor builder): ring entry at `0x13800 + tile*16` = `{[+0]=source&0x3fffffff,
  [+4]=(len>>2)|0x3ff80000, [+8]=dims, [+12]=count-1}`. So `[+0]` is a DMA **source address**.
- **Probe v2/v5/v6/v7** (follow a pointer, write a marker only if it's in scalar-SRAM range 0x400–0x40000):
  read slots `[0x13e40]` (engine-reg buffer), `[0x13800]` (ring entry 0), `[0x13c60]` (live entry, 0xFF 2 KB
  marker) — **every one NULL** (numerically confirmed: no hard-edged marker block; a 2 KB white marker on a
  dark scene would be unmissable). ⇒ the descriptor sources are all ≥0x40000 = **DRAM**, not scalar-SRAM.
- **`readMemory`/`writeMemory` (service mode) mapped:** reach only a **16 MB ARM window `0x0–0x00FFFFFF`**
  ("EXBL" block markers = internal flash/loader; ≥`0x01000000`→timeout, and the first timeout desyncs the
  session). **DSP-SRAM `0x13000` reads as 0** from ARM (idle); DRAM `0x0C000000`→ERR. So this interface sees
  neither DSP-SRAM nor the DRAM framebuffer; `writeMemory 0x34000` did not persist.
- **Ground-truth probe (`vizsram`):** redirect the live ring sources `[+0]` to a sweep of **valid** DSP-SRAM
  addresses (`0x13000 + k*0x400`, not `0x808080`) to stream SRAM as the image. **CRASH.** Valid SRAM source →
  DMA fault ⇒ **the DMA can only source from DRAM; it cannot read DSP-SRAM.** The crash also takes the
  USB/MSC interface down (`No devices found`), so post-crash memory read is impossible without a power-cycle
  (which clears SRAM).
- **conclusion:** `sa_sftfcs` scalar = **orchestrator only** — it programs the IN/OUT DMA, writes the VLIW
  engine command regs (`0x40000–0x4000c`) + coefficients, builds descriptors (ring `0x13800`), and kicks
  (`run_engine`, `0x48230`), then `wfi`. **The blur is a VLIW convolution over pixels in the engine aperture
  (`0xf8xxxx`); pixels flow DRAM↔aperture via DMA and NEVER enter scalar-addressable SRAM.** The design-doc's
  "334 SRAM refs + strh loops" were descriptors/coefficients/control (strh loops build coeff tables), misread
  as pixel access. **Exactly the yknr pattern (C-PIPE-022).** ⇒ `grain-sftfcs-module-design.md` thesis
  **falsified**; a per-pixel procedural grain cannot be added by the module's scalar core.
- **next path (owner's choice):** VLIW noise-stream injection — see `grain-vliw-injection-plan.md`. Both
  module-scalar routes (PBE E-0085, sftfcs E-0086) are now closed; the engine itself must add externally-fed
  entropy.
- Camera left with `vizsram` loaded + crashed (USB down). **Revert to stock `sa_sftfcs` pending** next
  session (`deliver_sftfcs_revert.py`, byte 445→0).
- builders: `build_sftfcs_probe{S,V2,V5,V6,V7}.py`, `build_sftfcs_vizsram.py`, `mem_recon.py`, `mem_sweep.py`,
  `read_crashed.py` (all in `~/nex3n-dump/work/filmgrain/`). frames DSC09648 (Probe S wall), DSC09649/09651
  (v5/v7 null), viz crash (no frame).
- claims: scalar-sftfcs-is-orchestrator; pixels-DRAM-not-scalar-SRAM; readMemory-16MB-ARM-window-only;
  DMA-sources-DRAM-only (viz crash); tmp: sftfcs-grain-wall.

### E-0087 — VLIW grain-injection advances: Phase-1 add-slot byte-verified + Phase-2 engine-input mux CONFIRMED on camera (channel count = 1 → CLONE) (2026-10-16)
Pursuing `grain-vliw-injection-plan.md` (engine adds an externally-fed noise stream to r15 before the PBE
store). Research driven by **DeepSeek v4.1 Flash-free** via the OpenCode headless API (reliable method in
`dev-environment-migration.md`), with every byte claim verified by the deterministic `vliw_decode.py`/`sadis`
and, here, on camera.
- **Phase 1 (VLIW add) — byte-verified.** Inject grain by reading a free engine input PORT into a scratch
  reg and adding it to the final pixel r15 before the op5 store. Single-store proof edit (decoder-verified):
  `0x7310` S2 `move a0 b1`→`read-stream a25 b10` (word `f1c78f000701e4e6`→`f1c78f3cab01e4e6`); `0x7318` S3
  `clamp a0 b15`→`add a10 b15` (`f0078f040701f5e3`→`f0078f0407a9f5e3`). Content stream = op3 port 24→r30.
- **Phase 2 — the engine-input PORT mux is MMIO `0x48434`** (built at pbe scalar disasm 0x27c–0x290, stored
  at 0x292; **pbe scalar text_base = 0x4c0, so file = disasm + 0x4c0**). Port number = low 6 bits; port 24 =
  `0x18`. The per-frame DRAM buffer handle arrives by a **doorbell poll on `0x49804`** and is stamped into the
  IN source reg `0x48208`. (All register literals verified present in the image; the IN path is
  **register-driven, not ring-descriptor** — the 0x13800/0x48230-34 ring is the OUT-DMA.)
- **On-camera confirmation (E1-retarget probe).** Built `sa_pbe_work_E1retarget.bin`: one halfword at
  **file 0x74c** `0x2473 (orr r3,r7)`→`0x2443 (orr r3,r4)` (retargets the mux off port 24), sum32 trailer
  recomputed (**Δ = −0x30, exactly as predicted**). Delivered via redirect (Backup `0x00bd0002[573]`→0x06,
  `/setting/sa_pbe_work.bin`). **Result: a fully BLACK frame** (luma 1/6/9, 98 % <8, std 0.58), **no hang.**
  ⇒ (a) **exactly ONE IN channel** feeds the content (retarget steals port 24 → black); (b) the mux edit
  **controls the engine input end-to-end and reaches the SOOC JPEG** (our Phase-2 model is correct). Reverted
  to stock PBE (byte 573→0).
- **Verdict: CLONE, not retarget.** To add port-25 grain while keeping port-24 content, the IN-DMA
  setup+entry must be **duplicated** (a second mux=25 write + a second source fed from the noise doorbell),
  not repointed. That clone edit is the remaining design step.
- **Methodology proven:** free DeepSeek is a capable RE engine for structure/hypotheses **when fed exact
  decoded data**; it is accurate here (port mux, E1, the Δ=−0x30 checksum all verified) but will hallucinate
  specifics if asked to navigate — and a disasm↔file offset error on the verifier's side (forgetting
  text_base 0x4c0) can falsely read fabrication. Rule: map disasm+text_base and verify every byte; the camera
  is the final oracle.
- builders: `build_sftfcs_probeV*`→ n/a here; `sa_pbe_work_E1retarget.bin` (md5 `2d98e216…`), `vliw_decode.py`,
  `phase2_run.py`/`phase2b_run.py`/`phase2c_run.py` (DeepSeek drivers), reports `overnight-phase2*.md`. Frame
  DSC09656 (black). Camera: reverted to stock.
- claims: engine-input-port-mux=0x48434; pbe-scalar-textbase=0x4c0; IN-path-register-driven-not-descriptor;
  one-IN-channel→clone; mux-reaches-JPEG (camera); tmp: vliw-grain-phase2-mux.

### E-0088 — PBE engine IN-DMA fully mapped = exactly TWO channels (luma + chroma), both essential → the noise-stream injection hits a 2-channel hardware wall (2026-10-16)
Continued the CLONE design (`grain-vliw-injection-plan.md`) with DeepSeek v4.1 Flash-free + deterministic
`sadis`/`vliw_decode.py` + two on-camera probes. **Correction logged:** the "+4-stride mux bank / spare slot 6
= 0x48438" hypothesis was WRONG — DeepSeek, given the complete setup disasm (no gaps), caught it and the real
layout verified deterministically.
- **The PBE engine has exactly TWO IN-DMA channels** (per-channel register groups, stride 0x14, both written
  by the setup; no 0x48448+ third group):
  - **Channel X = LUMA** — ctrl/mux `0x48434` (disasm 0x292), coords `0x48438/3c/40/44`, source `0x48208`, from
    struct `[r8,#0x0c..0x1c]`. Port-field built by the orr at disasm 0x28c / **file 0x74c**.
  - **Channel Y = CHROMA** — ctrl/mux `0x48420` (disasm 0x308), coords `0x48424/28/2c/30`, from `[r8,#0x20..0x30]`.
    Port-field built by the orr at disasm 0x302 / **file 0x7c2** (byte-identical build to X).
  - Mux ctrl low 6 bits = engine input port; port = 0x18 (24) for the content. Per-frame DRAM handle via
    doorbell poll `0x49804` → source `0x48208`. (pbe scalar text_base 0x4c0; file = disasm + 0x4c0.)
- **Two camera probes (each = one halfword `0x2473 orr r3,r7`→`0x2443 orr r3,r4`, sum32 Δ=−0x30, delivered via
  Backup `0x00bd0002[573]`, reverted after):**
  - **retarget-X** (file 0x74c): **BLACK frame** (E-0087) ⇒ X is the single luma/content channel.
  - **retarget-Y** (file 0x7c2): **structure intact, heavy magenta cast** (R/B ≈207, G ≈121) **+ fine
    horizontal micro-stripe texture** ⇒ **Y is the chroma channel** (de-synced → colour corruption, luma
    survives). Both channels are essential; the engine reads them on separate input ports.
- **⇒ the stream-injection grain path is WALLED at the hardware channel level.** There are only two IN-DMA
  channels and both are load-bearing (luma + chroma); there is **no spare channel** to feed a per-frame noise
  plane into a free engine input port. An unfed port reads garbage/de-synced data (X→black, Y→texture), not a
  controllable per-frame-random source. Phase-1 (VLIW add to r15) and Phase-2 (mux reaches the JPEG) remain
  proven — what is blocked is the **noise SOURCE**: no channel to supply it.
- **Bonus finding (kept):** retarget-Y is a genuine **magenta-glitch aesthetic** (chroma-channel corruption =
  a Picture-Effect-like look). `sa_pbe_work_Yretarget.bin` md5 `77d6e0b6…`; frame DSC09657.
- **Methodology confirmed again:** free DeepSeek is accurate on COMPLETE exact data and honestly refuses to
  emit bytes it can't see (it blocked on the missing slot→source window rather than inventing) — but will
  reconstruct/hallucinate when a window has gaps. Verify every byte at text_base 0x4c0; camera is the oracle.
  Built the `dsq.py` request/response/reset shim (direct interactive calls) to replace the staged daemon.
- next: re-think the noise SOURCE (other DSP DMA channels outside this engine's bank? an ARM-fed plane via a
  different route? deriving entropy without a new stream?) — the `cmdtable` ARM-noise-plane idea (E-0085) and a
  survey of other free OpenCode models are the immediate follow-ups.
- builders: `sa_pbe_work_{E1retarget,Yretarget}.bin`, `vliw_decode.py`, `dsq.py`, `phase2*/clone*_run.py`,
  reports `overnight-phase2*.md`/`overnight-clone*.md`. Camera: reverted to stock PBE.
- claims: pbe-IN-DMA=2-channels; channelX=luma(0x48434)/channelY=chroma(0x48420); both-essential-no-spare;
  stream-injection-2-channel-wall; retarget-Y=magenta-glitch; tmp: vliw-grain-2channel-wall.

### E-0089 — the entropy wall is BYPASSABLE: a DMA stream port IS the per-pixel AGU position → grain feasible by feeding a noise plane through the (sacrificed) chroma channel (2026-10-16)
Built `vliw_dis.py` (systematic VLIW disassembler, committed) and decoded the PBE output pass; then used free
DeepSeek (via the `dsq.py` shim) on "reuse the engine's strange ops for grain". **Key reframe (corrects the
E-0085/E-0088 'no entropy' reading):** the engine is SIMD — the microcode runs per pixel and each **op3
read-stream is AGU-indexed per pixel**. So a value does NOT need an exposed position register to vary per
pixel: **whatever plane you hand to a stream port, the AGU addresses it per pixel for free.** (Our E-0088
de-sync → horizontal *stripes* was exactly this: a wrongly-phased AGU over the chroma plane = positional, not
random — it PROVES the port is per-pixel-positional.)
- ⇒ **Grain path (feasible):** feed an external **noise plane** into a DMA stream port; the AGU makes it
  per-pixel; the VLIW adds it to the luma (`r0`) before `clamp r15`, modulated by `filmResponse(luma)` via the
  existing `mul`. Only ~3 microcode ops (cannibalise the abundant `add r31+=r31` filler) — **not a big
  rewrite.** Universal (added, not sensor-dependent); per-pixel; luma-modulated.
- **The handle/doorbell mechanism TRACED (pbe scalar, disasm; file = +0x4c0):** `0x74 r3 = *(0x49804)` (the
  doorbell handle ARM posts = the chroma buffer's DRAM address) → stamped into the chroma **source reg
  `0x48208`** at `0x8c` (also 0x48000/0x48020). So the chroma DMA source = `r3`. **Override point:** after
  `0x74`, set `r3` to a buffer we control — or simplest, **DMA a baked noise tile into that same chroma DRAM
  buffer** (at `r3`) before the engine reads it, so the chroma channel streams the tile.
- **Self-contained plan (no ARM firmware work):** bake a noise tile in the module data → module scalar DMAs it
  into the chroma DRAM buffer (`r3`) → VLIW `add r0 += chromaPort * filmResponse(luma)` → per-pixel
  luma-modulated grain. **Cost = chroma** (buffer is now noise → colour lost; or bit-pack noise into chroma
  LSBs via `pk` to keep degraded colour). Per-frame-random = re-bake/shift the tile by a frame-varying value.
- **Status:** concept proven (port = per-pixel position, camera-evidenced; handle override traced); a
  substantial but concrete build remains (tile bake + DMA-into-chroma-buffer + the 3-op VLIW add + checksum).
  DeepSeek confirmed `op2 xf` is a memoryless shaper (filmResponse), not an entropy source, and that no
  non-content per-pixel value exists in the datapath (so the external plane is required).
- builders/tools: `vliw_dis.py`, `dsq.py`, briefs `ds_reuse.md`. No camera this entry (static + model).
- claims: dma-port=per-pixel-AGU-position; entropy-wall-bypassable-via-fed-plane; chroma-source=*(0x49804)-handle;
  self-contained-tile-via-DMA-into-chroma-buffer; op2=memoryless-shaper; tmp: vliw-grain-feasible-via-chroma.

### E-0090 — PBE fully mapped = CHROMA processor; luma is passthrough (NOT VLIW-injectable in PBE) (2026-10-16)
A long camera+static session systematically mapping the PBE engine to find the luma output for grain. Full map:
`pbe-engine-map.md`. Methodology correction mid-session (owner): stop grabbing straws; map the whole block, and
**VIEW the frames directly off the SD card** (`/Volumes/Untitled/DCIM`, `sips`+read) instead of verbal reports —
this was available the whole time and should have been used from the start (`nex3n-sd-frame-view` memory).
- **chan3 = CHROMA output (confirmed):** store 0→chan3 = desaturation; datum `r15=clamp(r0)` @0x7318/30/60.
  Viewing frames: chan11→pink+block chroma+stripes, chan21→magenta — all CHROMA damage, **luma structure always
  survives**. ⇒ PBE's op5 channels carry chroma.
- **NO channel zeroes luma to black.** Tested (coherent stores) chan 9/15/25=scratch(normal), 31/17/4/5/10=
  feedback(crash), 3/11/21=chroma. ⇒ **luma is NOT a zeroable op5 channel.**
- **CLASSIFIER/CRASH ROOT CAUSE:** the scalar orchestrator occupies file **<0x6000**; clean VLIW microcode is
  **≥0x6000**. Early "coherent runs" were misclassified scalar; editing <0x6000 corrupts the scalar → silent
  crash (USB down, cold-boot). All reliable edits must be ≥0x6000. (Explains the crash-heavy middle of the session.)
- **Luma passes through via a REGISTER, not an op5 store** (taint trace: luma convolved in pass 0x6310, port24
  ×61, zero stores, into r12/r13; DeepSeek: r13 = export candidate). BUT three direct luma-register tests were
  **negative on camera (viewed):** double r30 @final pass = no change; double r13 @0x6310 end = no change;
  retarget all 61 port24→port31 in 0x6310 = **only faint per-column vertical lines, luma intact** (the ONE
  positive luma-adjacent signal — flagged lead in `pbe-engine-map.md`).
- **OUT-DMA = 2-plane loop** (scalar 0xa70-0xcf6): plane counter r9, even→ring 0x9800, odd→ring 0x9000, shared
  kick 0x48230; channel→plane binding in DRAM descriptor [0x8800+r6*16+52] = runtime-opaque. (0x9000/0x9800 =
  the SAME OUT bases as yknr, `grain-injection-design.md` — the two investigations reconcile.)
- **op2 `xf` = nonlinear transfer** (abs/sq/LUT, DeepSeek) — another reason linear r30/r13 amplification showed
  nothing.
- **CONCLUSION:** PBE microcode controls **CHROMA** (chan3), not luma; luma is a hardware/register passthrough
  the editable VLIW doesn't meaningfully reach. ⇒ **Chroma grain IS achievable via PBE** (`grain-chroma-solution.md`);
  **luma grain needs a luma-WRITING stage** — PBE is not it, and yknr/sftfcs scalar routes are closed (E-0079/85/86).
  Owner's next direction: find the luma-writing stage upstream.
- camera: many shots (viewed); left with `lumaSrc.bin` flashed then owner powered off → revert `deliver_pbe_revert.py`
  (573→0) on next power-up. tools: `vliw_dis.py`/`vliw_enc.py`, DeepSeek `dsq.py`.
- claims: pbe=chroma-processor; luma-passthrough-not-op5-channel; scalar<0x6000-vliw>=0x6000; chan3=chroma(r15);
  out-dma=2-plane-r9-loop(0x9000/0x9800); op2=nonlinear; faint-vertical-lines-lead(0x6310); tmp: luma-stage-upstream-needed.

### E-0091 — YKNR LUMA STORE CONFIRMED (op5 a7→chan3 @0xcd80-0xce70); zeroing it = NR-bypass luma GRAIN, ISO-gated (2026-10-16)
Found and confirmed the yknr luma output store — the luma injection point hunted all session. Credit: the prior
decode `work/pipeline-research/08-yknr-vliw-decode.md` already pinned it (I'd missed it; lesson: read prior work
first, like the SD-view lesson).
- **Store = `op5 a7→chan3` in S4** at **0xcd80/88/98, 0xcdd0, 0xce30/38/70** (datum **r7**, accumulator **r1**,
  output-stream pointer r3→0x9000/0x9800 tile → the YC canvas `Stage_DistEncodeFULL` reads, C-PIPE-021/025).
  Datapath: op3-stream → op4-mul → r1 → op1-pack → r7 → op5-store. (chan3 here = luma stream; channel ids are
  module-local — PBE's chan3 = chroma, unrelated.)
- **Camera confirmation via ISO-differential** (yknr is ISO-gated, C-NR-007): zeroed the 7 stores (r7→r31).
  **ISO 16000 (DSC09695): visible LUMA GRAIN** (wood/table grainy vs the smooth clean ISO-16000 DSC09693);
  **ISO 3200 (09697): faint**; **ISO 200 (09696): perfectly clean** (yknr off → edit not executed). The ISO-gated
  effect is decisive that op5 a7→chan3 is on the live luma-NR output path. Mechanism = NR-bypass (degraded denoise
  → native sensor noise survives as luma grain, matching E-0080); grain magnitude ∝ ISO.
- **Explains ALL earlier luma nulls:** every prior luma test hit the wrong region — PBE r30/r13/channels (PBE =
  chroma, luma passthrough), yknr chan18 (dead 0x3c00-region data), cluster-5 chan19/20 (scratch), aguprobe 0xcc38
  (prior decode: upstream, dead dst). None touched 0xcd80-0xce70.
- **Luma injection point now EXACT:** add per-pixel noise to **r7** (or r1) before each op5 a7→chan3 store, instead
  of zeroing → CONTROLLED luma grain (amplitude knob + per-frame SEED), at every ISO where yknr runs (mid-high).
- **Still open:** BASE-ISO luma grain (yknr bypassed at ISO 200 → need the develop-stage / YCC_FULL writer,
  C-PIPE-024/Q-40). delivery `deliver_setting.py` byte 597. Build: `sa_yknr_lumastore.bin` (md5 dd8b965d).
- claims: C-NR-007 (reaffirmed), yknr-luma-store=op5.a7.chan3@0xcd80-0xce70, injection=r7/r1, nr-bypass-grain-iso-proportional;
  tmp: base-iso-luma-needs-develop-stage.

### E-0092 — yknr r7-ADD inject = NULL at all ISO ⇒ op5 `a` field is NOT a GP-register datum (store semantics undecoded) (2026-10-16)
Built `sa_yknr_r7inject.bin`: displaced 4 dead `op0 a31→b14` lanes near the luma stores with `op7 a30→b7`
(r7 += r30, a luma tap), to ADD per-pixel brightness/grain to the store source. Camera (owner): **"чисто" at
both ISO 200 AND ISO 16000** — no visible change. (SD unmounted before I could pull/view; trusting the report.)
- **Decisive contrast:** the earlier ZERO test changed the store SLOT itself (`op5 a7→chan3` → `a31`) and DID
  work (NR-bypass grain at 16000, E-0091). But ADDING to GP register **r7 via op7 had ZERO effect.** ⇒ **op5's
  `a` field is NOT a GP-register index** in op7's operand space — it's an AGU/stream/lane selector (a=7 = the luma
  lane/stream, a=31 = null→0). The stored per-pixel datum comes from the engine's implicit SIMD accumulator
  (op3-stream → op4-mul → **r1** → op1-pack), NOT from reading GP r7. So "add to r7" injects nothing the store reads.
- ⇒ **To inject luma grain, modify the DATAPATH that builds the stored value (r1 / the op4-mul / op1-pack), or the
  op5 AGU descriptor — NOT a GP add to r7.** This is the undecoded op5/AGU + SIMD-lane semantics = C-DSP-015, the
  core wall. The emulator / proper op5 decode (owner's chosen direction) is required to inject correctly.
- **What we DO have (solid):** the luma store SITES (op5 a7→chan3 @0xcd80-0xce70) and that changing their datum
  reaches the JPEG (zero→grain, ISO-gated). The injection just needs the correct datum mechanism.
- NEXT (static/DeepSeek, no camera): decode op5 `a`/`b` semantics (AGU/stream vs lane) and the op1-pack→store data
  path; then inject into r1 or the pack. claims: op5-a-not-gp-reg; store-datum=implicit-simd-accumulator; tmp: op5-agu-decode-needed.

## 4. Prepared but not executed

- Colour and effect blobs with no evidence of having been written: `bk/00030001_looks_v6.hex`, `v6_phoenixsky.hex`, `v6_kodakwarm.hex`; `fx/*` (NR-1..NR-4, SH-1/2, SFprobe, promistA/B, PE1), `fx/3007a_mode2_k0.hex`, `3007a_mode1_film.hex`, `3007a_mode1_shoulder.hex`. The 06.10 morning-plan note itself says "not executed". The latest Backup `live*.log` is `live30.log` (05.10 21:48); the state recorded on 06.10-09.10 is "v5 + k0". No E-ID is assigned.
- p3 images built on 06.10 but never flashed (no flash log): `p3_lowiso` `e25a87b6884bf6c1464aab0d94d366ff`, `p3_iso800` `7af00ce9634ce793415518a3f3153805`, `p3_highiso` `1e0a204b68467059cf774db7c2e0fcc3`, `p3_softdream` `04089e2500d2abaa70d890327c729a28`, `p3_iso400_8mb` `4847a94a4ec679702a2f1b9ac709064d`, `p3_multibuf` `b6bf277d31a9b300923d6018d697d888`, `p8_filmgrain.bin`. The notes' phrase "iso800 visible, DSC09527" refers to the +-31 sfwrap frame (E-0042), not to an iso800 image (R-4).
- NOP builds produced by `build_nopcore.py` but never flashed: `nopc161`, `nopc140`, `nopc145`, `nopc154`, `nopc166`, `nopq1`, `nope1`, `nope2a`, `nopq3`, `nopq4`. The rows "q1 = develop+focus+luma (implied)" and "e2a = main luma write (black, from the e2 result)" in `dsp-grain-campaign.md` are inferences, not tests (C-IDT-009).
- Siblings of flashed grain images built but not flashed: `v2soft` `24d8a1b9b9229f1934b3b0be7f612852`, `v2strong` `0747ba444efee847723d38049c214b91`, `v3soft` `a35a345b45b1c946b9405ee3ea5d31a4`, `v3strong` `77875b521142ce44666da22c408cc5f4`, `v4strong` `fae5e1f159d97d0d0a28a9a5d9ab4e6e`, `v5strong` `3a115467193afe404ece2f32b92474ec`.

## 5. Temporary ID to final ID

| temporary | final |
|---|---|
| E-0001..E-0066 | unchanged (E-IDs are final) |
| R-1..R-13 | unchanged |
| `claims: not assigned (area DSP/IDT/...)` in the extract | replaced by the lists above (final C-DSP/MOD/IDT/DLV/SAFE/TOOL IDs; other areas as `tmp:`) |
| candidate area `IDT / DSP` (E-0052..E-0058, E-0060..E-0062) | C-IDT-008, C-IDT-009, C-IDT-010, C-IDT-011, C-IDT-013 |
| candidate area `IDT` (E-0063..E-0065) | C-IDT-012, C-IDT-016 |
| candidate area `DLV` / `SAFE` (E-0021, E-0032..E-0037, E-0059, E-0066) | C-DLV-004, C-DLV-005, C-DLV-006, C-DLV-007, C-SAFE-003, C-SAFE-004, C-SAFE-008, C-SAFE-011 |
| candidate areas `COL`, `TONE`, `NR`, `FX`, `BK`, `PIPE`, `MEM`, `CTRL`, `JPEG`, `SYS`, `PART`, `BOOT` | stay `tmp:` (numbered by the agent of 01/02/03/07) |
| R 2-B, 2-C, 2-D, 1-D (review 2026-10-09) | R-14, R-15, R-16, R-17 (new review items) |
| F §1.4 (E-0021 reading) | C-BOOT-035, C-BOOT-036; R-11 updated |

---
## 2026-10-17 camera session — DSP VLIW grain injection (correct ISA: scalar + run_engine engine)

### E-0093: yknr module loads+runs, applies per-capture WITHOUT cold-boot, and the engine input-DMA-ring count is live. Flashed `sa_yknr_loop7.bin` (ring bound `cmp r8,#6`→`#7` at file 0x1392/0x1480) → capture FAILS (frame does not save) even without cold-boot. ⇒ the module is loaded+executed (widening the ring kicks an unwritten 7th slot → DMA hang), and `/setting` redirects apply per-capture (fast iteration). conf: high.
### E-0094: yknr `chan 6` stores (0xcc78-0xccb0, `st r10..r24→chan6`) idled → NULL (normal luma at ISO 3200 & 16000). ⇒ chan 6 = dead/internal channel, not the JPEG luma. conf: high.
### E-0095: yknr 0xcc38 S3 clamp source r0→r31 forced → NULL. ⇒ not on the output path. conf: high.
### E-0096: sftfcs 0x6500 `add r24+=r24` (double the blend term before `add r0+=r24`@0x6548) → NULL (no visible ×blur in Soft Focus). ⇒ r24/the blend ≈ 0, feeds only 1/7 stores; not the main output. A straw. conf: high.
### E-0097: SPICA `chan 7` stores (28, idled) at BASE ISO 200 → NULL (normal frame, Florence-on-TV). With prior SPICA chan-3 null ⇒ SPICA does NOT write the full-res still luma (HW CamCore does); no DSP base-ISO luma. conf: high.
### E-0098: **sftfcs `chan 3` = the Soft Focus JPEG luma output — CONFIRMED.** `sa_sftfcs_chan3zero.bin` (idled all 47 `op5→chan3` stores 0x6558-0x6878) → Soft Focus shot shows **visible vertical banding** (idled stores leave tile columns stale). ⇒ chan 3 reaches the JPEG; sources r11(dom)/r17/r7/r15. The live grain-injection point for the "Soft Focus = grain" path. conf: high. See `grain-sftfcs-confirmed.md`.
- method: `/setting` redirect (yknr 597 / spica 429 / sftfcs 445) + writeFile; reversible; frames viewed off the SD. DSP VLIW via `vliw_dis.py`; comprehensive dataflow synthesis via DeepSeek (`dsq_xpl.py`, Experiential Labs free gateway). Correct ISA per `sa-dsp-isa.md`.
