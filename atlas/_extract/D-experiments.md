# D-experiments: reconstructed on-camera experiment log (NEX-3N, 2026-10-04 .. 2026-10-09)

Working extraction, not authoritative. Schema: `../00-index.md` ("Experiment record"). Chronological, E-0001..E-0066.

## How this was reconstructed (read first)

- Sources, in order of weight: (1) flash/log files in the scratchpad `nexfw/pmca/` (`flash_*.log`, `flash[2-6].log`, `live*.log`, `det/ft/probe/diag/mdiag/scr/sess/sess2/schk.log`) and `~/nex3n-dump/work/nopcore/flash_*.log` (these carry the md5 and the **local** mtime); (2) builders (`build_*.py`) and image files (md5 computed here with `md5 -q`); (3) the session transcript `f8f2a405-....jsonl` (user messages are the only record of what the camera actually did on the screen; transcript stamps are **UTC**, file mtimes are **local = UTC+2**); (4) notes in `notes/*.md`, WorkPersonal `reference/nex3n-*.md`, and the project memory file.
- `observed:` is the user's words (translated, quotes in "..." are verbatim Russian shortened to English) or a measurement the assistant took from the saved JPEG / a live memory read. Anything an assistant *inferred* is put in `conclusion:`/`caveats:`, not `observed:`.
- Times: `[HH:MM]` = local time of the log file mtime (end of the operation) unless marked "msg" (UTC+2 of a transcript message). Flash logs record the *end* of the flash; the camera test followed 1-5 min later.
- Recovery image used throughout: `current_p3.bin` = p3 with film tone curve k0, no grain, md5 `d7cca4469709a8b50bc5ad6efa34aa13` (identical to `work/tone/p3_fit.bin`, i.e. the image written on 05.10). Stock p3 (`out3n/nflasha3`) md5 `37b9727627b91ebeefdc07dcde561036`. Clean film-curve av-cam extracted from the camera: `sys_avcam.bin` md5 `58809e0255a34e21c077fe49935a7408` (6554072 B).
- All p3 images are 10485760 B, LZPT ("TPZL") partition; av-cam inner offset `0x8e00`, idt_cam inner offset `0x980e00` (length 200384). Every flash below went through `flash_any.py` (updater shell, raw write to `/dev/nflasha3`, md5 of the whole partition, WBI `/dev/nflasha5` zeroed) unless stated; each log line "device md5=... -> MATCH" means the on-flash partition equalled the image md5.
- `claims:` fields are `not assigned` because no C-IDs exist yet; the area of candidate claims is given.
- Frame numbers (DSCnnnnn) are the owner's shots; where the sources do not give them, none are invented.

Known inconsistency in the archive notes: `reference/nex3n-firmware-hacking.md` ("Состояние камеры на конец 04.10", and "Следующий шаг: A/B завтра") says the `0x00030106` ladder is still at 32 and the A/B is pending. The transcript shows the A/B was done the same evening (E-0009) and 80 was restored. Treat that paragraph as stale.

---

## 2026-10-04 - first contact, Backup writes (no firmware writes)

### E-0001: full flash dump and Backup.bin read  (2026-10-04)
- image: live read-only; resulting files `~/nex3n-dump/nex3n_v100_nflasha.bin` (267911168 B) and `Backup.bin` md5 `b476ec204c7ed0f410d64f10ea439372` (703962 B)
- change: [18:43-18:45] pmca updater shell, `info`, `pull` of the whole block device, `bk` read. No writes.
- observed: `info` printed Model NEX-3N, product code 32825235, Backup region CX76201_CE, firmware 1.00; the dump finished ("100"). No camera misbehaviour reported.
- conclusion: baseline dump and Backup snapshot obtained; updater-shell `pull` of block devices works.  confidence: high
- caveats: `Backup.bin` (sha1 `0957fc1005fe4eaa5d1ce16a5532db0e6e34bf06`, = `Backup.bak`) differs from the later `Backup_pre-write.bin` (sha1 `6985f679...`); the difference is the pmca/updater-mode side effects described in E-0002, so "pristine" means "as read at first contact".
- claims: not assigned (area PART / TOOL)

### E-0002: null Backup write 0x01070937 = 00 (same value)  (2026-10-04)
- image: Backup write `0x01070937` `00 -> 00`; pre-write snapshot `Backup_pre-write.bin` md5 `c0d14de75767db585948f72363f7de4d`
- change: [18:51] `bk w 01070937 00` (protected property -> pmca rewrites the whole Backup), readback "Success".
- observed: pmca reported `Success` with readback match. File diff afterwards: only the checksum and two mode flags `0x0051000f`, `0x00510014` changed. Camera reboot was checked by the owner: "all ok" (msg 16:53Z).
- conclusion: the Backup write path is safe and survives reboot; the two flags are side-effects of entering updater mode (hypothesis, "not checked" in the session).  confidence: high (write path), low (flag meaning)
- caveats: whole-file rewrite of Backup for protected properties; round-trip restore by whole file was explicitly not tested at this point.
- claims: not assigned (area BK / SAFE)

### E-0003: flag test 0x01070937 = 01 (NEX-6 value)  (2026-10-04)
- image: Backup write `0x01070937` `00 -> 01`; snapshot `Backup_pre-test1.bin` md5 `c0a052e1a5cecbc25626fe40a49d25ca`
- change: [18:56 msg] one of 18 candidate flags set to the NEX-6 value, to see whether more Creative Styles appear.
- observed: owner: "6 styles - did it really flash?" (msg 17:00Z); readback inside the session showed `01`.
- conclusion: this flag does not unlock styles.  confidence: medium
- caveats: only the style count was looked at; whether the value persisted across reboot was not checked at this step (assistant noted it).
- claims: not assigned (area BK / FX)

### E-0004: flag test 0x0107093b = 01 (937 restored to 00)  (2026-10-04)
- image: Backup write `01070937 01->00`, `0107093b 00->01`
- change: [~19:03 msg] second candidate.
- observed: owner: "nothing changed, switch on half" (msg 17:07Z).
- conclusion: second flag does not unlock styles.  confidence: medium
- caveats: as E-0003.
- claims: not assigned

### E-0005: flag test, group 1 of 8 flags  (2026-10-04)
- image: Backup write; pre-snapshot `Backup_pre-group1.bin` md5 `eae39fcfb1d8795d0dd3d15aee933e2c`
- change: [~19:09] `0107093b` back to 00; set to NEX-6 values: `01070929 02->05`, `01070928 7700->7f00`, `0107097f 00->01`, `01070980 00->01`, `0107094f 00->01`, `01070951 00->01`, `0107092c 00->01`, `01070306 00->01`. First attempt failed (camera did not enter updater within 30 s, nothing written, msg 17:08Z).
- observed: owner interrupted the next tool call twice (17:11Z, 17:15Z); no explicit quote about the menu. Assistant summary: "did not open" (msg 17:16Z).
- conclusion: no flag combination here opens the hidden styles.  confidence: medium
- caveats: the verbatim owner observation for groups 1 and 2 is not in the transcript; the summary is the assistant's.
- claims: not assigned

### E-0006: flag test, group 2 of 8 flags (on top of group 1)  (2026-10-04)
- image: Backup write; pre-snapshot `Backup_pre-group2.bin` md5 `8fe60b8941029765df4e2843a3a8233e`
- change: [~19:12] additionally `0107091d/091e/091f/0920/0923/0925/0926/0400` to NEX-6 values; group 1 left on (no rollback in between).
- observed: with all 16 set, styles still 6 (assistant statement, msg 17:16Z; owner reported no visible change).
- conclusion: none of the 18 `0x0107xxxx` flags controls the style list. Later explained by code: unconditional loop in `viewUnified2.so` hides IDs 6..12 and reads no flag (static, `notes/hidden-styles.md`).  confidence: high (combined with the static result)
- caveats: the experiment itself only shows "no menu change"; the cause comes from the later disassembly.
- claims: not assigned (candidate area FX; relates hidden-styles static claims)

### E-0007: revert of the 16 flags, read-only boot dumps  (2026-10-04)
- image: Backup writes back to 3N values; snapshots `Backup_pre-revert.bin` md5 `51850c51d0b5270bf0301d52b660d0b4`, `Backup_post-revert.bin` md5 `fb270c83a7940f5623fc8cd99f759dbf`
- change: [20:10-20:11] each flag written back individually (not a whole-file restore); in the same session `boot1` (Loader2) and `bootrom` read, style blocks read.
- observed: "All 16 flags are back to the 3N values", verified by `bk r`.
- conclusion: per-property revert works; boot loader readable (`boot/boot1`, `boot/bootrom`).  confidence: high
- caveats: `Backup_post-revert.bin` is not byte-identical to `Backup.bin` (expected: mode flags, checksum).
- claims: not assigned (area SAFE / BOOT)

### E-0008: ladder 0x00030106 step 5 (+0xb6) 80 -> 32  (2026-10-04)
- image: Backup write `0x00030106` offset `+0xb6` (uint16, ladder `0x78b0`), orig block md5 `641eeb594c76365970147df1f9af8113` (`bk/30106_orig.txt`)
- change: [~20:12-20:17] ladder `2,8,16,24,32,[80->32],112,144,176`, `bk s`.
- observed: frames DSC09409-12 (before, other scene) vs DSC09413-15 (after, different scene and light): chroma ratio Sunset/Standard 2.75 -> 1.35 and Sunset/Vivid 2.36 -> 1.12. The assistant warned the scenes differ ("floor with slipper" vs "TV stand").
- conclusion (at the time): ladder = Sunset saturation gain.  confidence: low (superseded by E-0009)
- caveats: confounded by scene change; the owner could not reshoot on the day.
- claims: not assigned

### E-0009: ladder step revert to 80 and clean A/B  (2026-10-04)
- image: Backup write `0x00030106` `+0xb6` 32 -> 80 (original), verified against `30106_orig`
- change: [~23:03 msg] restore, then Sunset shot on the target at 1/100 f/5.6 ISO 800.
- observed: DSC09418 (value 32) vs DSC09425 (value 80): mean chroma 52.3 vs 51.7, grey patches b* +20..+25 vs +16..+22. The assistant: "no difference, within noise". Camera "completely in original state".
- conclusion: the ladder step does not change the JPEG colour; code reading afterwards says the ladders are sharpening (Apacon), not colour. Sunset warmth is not from this block.  confidence: high (no colour effect); medium (sharpness claim, never measured on a frame)
- caveats: the "sharpness" attribution is from static analysis; no sharpness measurement was taken. Standard Saturation was left at -3 in that series (assistant noted it does not matter for grey hue).
- claims: not assigned (area BK / NR; relates `0x00030106` sharpening claim)

### E-0010: all 17 colour matrices replaced by one muted matrix  (2026-10-04)
- image: Backup write `0x00030001` and `0x00030008` (both banks); pre-snapshot `Backup_pre-matrix.bin` md5 `314a63c0197a848cbba46fd6ebf0d68f`; block file (probably `bk/00030001_test1.hex` md5 `f40b4f4935541a50ba214ab46bace207`, name inferred)
- change: [~23:14-23:17] the 17 slot matrices in `+0x48 + 18*slot` all replaced by the most muted native matrix (rows sum to 1024). Hue tables and other bytes untouched.
- observed: target chart, same point 1/100 f/5.6 ISO 800: mean chroma of 18 colour patches Standard 43.7 -> 21.7, Vivid 56.0 -> 24.3, Sunset overall 43 -> 17; grey patches unchanged; Sunset warm b* on bright neutrals 7 -> 2. Camera booted normally.
- conclusion: `0x00030001` is the JPEG colour block; Sunset's warmth is applied before the matrix (it is muted with the rest).  confidence: high
- caveats: single frame per style; frame-to-frame noise about +-2 chroma, +-3 b*.
- claims: not assigned (area COL / BK)

### E-0011: RGB-permutation "tag" matrices to identify slots  (2026-10-04)
- image: Backup write `0x00030001`/`0x00030008`; block `bk/00030001_tags.hex` md5 `b3c1a92b6251a9c8805ab0fa32e13448`, map `bk/tags.json`; original `bk/00030001_orig.txt` md5 `014ad5fe1b6bcacad67fb51b15f37ab8`
- change: [23:23 live13.log; msg 21:23Z] 17 matrices replaced by 6 RGB permutations x 3 saturation levels (1.0/0.6/0.3), rows sum 1024.
- observed: "wild colours" as designed; chart shot once per style (DSC09434-39). Slot map derived: Standard = slot 0 (`+0x48`), Vivid 1 (`+0x5a`), Portrait 2 (`+0x6c`), Landscape 3 (`+0x7e`), Sunset 4 (`+0x90`). B&W slot not identifiable from a mono frame. Camera stayed in this state overnight 04->05.10.
- conclusion: slot-to-style map established; native matrices M0/M1/M2 recorded.  confidence: high
- caveats: B&W slot unknown; the 17-slot -> style map beyond slots 0..4 is not established.
- claims: not assigned (area COL / BK)

---

## 2026-10-05 - film-look colour via Backup, hue tables, first p3 write

All entries below write `0x00030001` and `0x00030008` identically (both banks) with `bk w`, readback verified and `bk s`. The block hex per entry is matched to the write by file mtime (hex file creation vs `live*.log` mtime): this correspondence is an inference, no log prints the hash.

### E-0012: v1 film matrices (Portra / Gold / UltraMax / ColorPlus)  (2026-10-05)
- image: Backup write `0x00030001/08`; block `bk/00030001_looks_v1.hex` md5 `2d074d0536a632370221f912c1b73416`; log `live19.log` [12:12] (earlier tries `live15-18` failed: USB timeouts / camera asleep)
- change: Vivid = Portra 400, Portrait = Gold 200, Landscape = UltraMax 400, Sunset = ColorPlus 200 (matrices from Maraver chart data, rows normalised to 1024); Standard native.
- observed: 5 chart frames DSC09440-44. Blues go cyan in Gold/UltraMax/ColorPlus; Portra "softest". Measured chroma above prediction: Vivid +11 %, Landscape +14 %, Sunset +14 %; Portrait matches prediction (50.3 vs ~51). Sunset warmth absent at Custom 5500 WB (it was b* +20 at Auto WB the day before). Standard day-to-day shift dE 10.5.
- conclusion: linear-light matrix model fits better than gamma model; Vivid/Landscape/Sunset add their own chroma on top of the matrix; Sunset warmth = auto-WB target shift, not processing.  confidence: high (chroma boosts), medium (WB-target mechanism, one comparison across days)
- caveats: WB differed between days (Custom 5500 +M2 vs Auto), so absolute colour across days is not comparable.
- claims: not assigned (area COL)

### E-0013: v2 (style chroma boosts compensated in the matrices)  (2026-10-05)
- image: Backup write; block `bk/00030001_looks_v2.hex` md5 `ccc1243926b5114ef9ecd4ee1400bbb6`; log `live20.log` [12:22] (the success message in the session is stamped 12:54 local - gap unexplained)
- change: k = 1/1.11 Vivid, 1/1.14 Landscape and Sunset applied as desaturation preserving grey and luminance (Portra `1061,99,-136/75,1241,-292/9,45,970`, Gold, UltraMax, ColorPlus).
- observed: one scene shot with 5 styles (`compare_v2.jpg`), WB still Custom with M+2, warm room light, sky blown. Looks: "Portra calmest, Gold most 'film', UltraMax closest to Standard, ColorPlus 'cheap Kodak'". Owner: "looks decent" (msg 11:37Z).
- conclusion: defaults are right at sliders = 0; differences between styles visible but moderate (matrix changes colour only).  confidence: medium
- caveats: visual judgement; absolute colour contaminated by WB shift and lamp light.
- claims: not assigned

### E-0014: v3 (House in Portrait, Phoenix II in Sunset) + hue-table test E1  (2026-10-05)
- image: Backup write; block `bk/00030001_v3_e1.hex` md5 `822dc540fcfe2abed6d58625af0bbe7f` (v3 block `00030001_looks_v3.hex` md5 `33281909a170f9d53030d047d98ab1c5`); log `live21.log` [14:09]
- change: Portrait = House `1117,-3,-73/9,1216,-203/-16,-11,1022`, Sunset = Phoenix II `1082,47,-92/102,1150,-232/54,74,890`; **E1: hue record of Standard (`+0x100..+0x117`) zeroed**.
- observed: Standard with zeroed record "acid, neon red/yellow/green/magenta" (assistant's visual reading of the frames, not a quoted owner remark). Chart numbers: mean chroma Standard(zeroed) 65.2 (normally ~48-50), grey a* -7..-11; Vivid 46.9, Portrait 42.5, Sunset 40.5. A Standard frame had the whole laptop in view so its grid was not recognised; numbers come from another frame of the set. Frame numbers for this set not recorded.
- conclusion: the int8 hue table in `0x00030001` is live; its native negative values (-30..-46) are chroma muting; zeroing it adds about one third chroma and shifts greys green.  confidence: high
- caveats: one frame; chroma figure from a frame the script could parse.
- claims: not assigned (area COL / BK)

### E-0015: binary sector test (three styles, 3-of-6 groups zeroed)  (2026-10-05)
- image: Backup write; block `bk/00030001_binary.hex` md5 `3277158c4df6dde7884cd9f6f8fb4116`, plan `bk/binary_plan.json`; log `live22.log` [14:19]
- change: Standard, Vivid, Landscape records zeroed in different 3-of-6 byte groups (each of the six 4-byte groups gets a unique 3-bit code); Portrait left as control.
- observed: frames DSC09473-76. The assistant decoded: group 0 -> yellow-green/green, 1 -> red, 2 -> magenta/purple, 3 -> nothing visible, 4 -> cyan, 5 -> blue. Record N acts on slot N confirmed (Vivid's pattern showed only on Vivid, etc.).
- conclusion (later): record-to-slot binding is correct; the "6 groups = 6 hue sectors" reading is **superseded** by E-0016 (4 bytes = 4 hue regions, 6 groups = 6 parameters).  confidence: high (slot binding), low (sector reading)
- caveats: zeroing a group changes a parameter in all four hue regions at once; the first decode attributed that to one hue sector.
- claims: not assigned

### E-0016: byte test in group 0 (+0..3), one byte per style  (2026-10-05)
- image: Backup write; block `bk/00030001_bytes.hex` md5 `f6903495a4b403d6b46d7a5204669232`, plan `bk/bytes_plan.json`; log `live23.log` [14:32]
- change: byte j of group 0 of slots 0..3 raised to about +100 (Portrait byte 2 `+6 -> +100`).
- observed: frames DSC09478-81, Sunset control DSC09482/87. First pass: only Portrait clean (greens dC -11..-14, cyan/blue-green hue -14 and -34 deg); other three polluted by E-0015 state ("my planning mistake"). After E-0017 clean baseline (DSC09483-86): byte 0 rotates reds/skin/magenta -12..-35 deg; byte 1 oranges/yellows/greens +18..+29; byte 2 blue-greens/cyan/sky -15..-37; byte 3 blues/violet/purple +9..+22. Noise from the control: dC +-7, dh +-4..5 deg.
- conclusion: 4 bytes of a group = 4 hue regions (red/skin, yellow-green, cyan/sky, blue/violet); group 0 = hue rotation.  confidence: high (rotation per region), medium (exact region edges)
- caveats: needs the same-session baseline, which was only established in E-0017; hand-held camera, cross-session dE +-2..3.
- claims: not assigned (area COL; `notes/hue-tables.md`)

### E-0017: clean v3 restore as same-session baseline  (2026-10-05)
- image: Backup write; block `looks_v3.hex` md5 `33281909a170f9d53030d047d98ab1c5`; log `live25.log` [14:43]
- change: all hue tables back to native, v3 matrices; camera not moved (owner could not keep exact position).
- observed: baseline frames DSC09483-86 (+ Sunset control 09487). Used as base for E-0016 and E-0018.
- conclusion: lesson recorded: base frames must be shot in the same session with native tables.  confidence: high
- caveats: handheld, dE +-2..3 between sessions.
- claims: not assigned

### E-0018: band test (second/third parameter pairs)  (2026-10-05)
- image: Backup write; block `bk/00030001_bands.hex` md5 `53ecf85ff2b9ab551cfde1e430e323f6`; log `live26.log` [15:17]
- change: Standard `+0x105` (Q1 b1) -36 -> +90; Vivid `+0x125` (Q3 b1) -9 -> +110; Portrait `+0x145` (Q5 b1) -17 -> +110; Landscape `+0x150` (Q2 b0) -6 -> +120; all other bytes v3.
- observed: frames DSC09488-91 vs base DSC09483-86 (Sunset control 09487 -> 09492: dC +-8, dh +-5): Standard yellows/greens/oranges/skin dC +12..+34, L +5..+10, reds rotate +14..+33 deg; Vivid almost the same (dC +16..+25); Portrait weak (dC +7..+8); Landscape reds/dark skin -28..-34 deg, magenta dC +22.
- conclusion: pairs (Q0,Q1) ~ (Q2,Q3) = (hue, saturation); bands are not luminance bands (L 24..75 respond alike); no shadow/highlight muting from these tables; saturation byte leaks hue into reds.  confidence: medium
- caveats: camera responds up to ~1.8x stronger than the per-unit model; third pair (Q4,Q5) behaviour unexplained.
- claims: not assigned

### E-0019: v4 hue tables for the four film styles  (2026-10-05)
- image: Backup write; block `bk/00030001_looks_v4.hex` md5 `88775459fe2ab78f3273a5866513a5ae`; log `live27.log` [15:26]
- change: v3 matrices + model-derived tables for slots 1-4 only (54 bytes `0x118..0x16b`); Sunset record markers (-128) left.
- observed: frames not numbered in the sources; chart measured vs v3: Portra blues/sky/cyan -31..-38 deg and blue chroma -28..-39, skin -9..-14 deg (planned -3..-7); UltraMax about half of that (-18..-21 deg, chroma -19..-27); House cyan +9.5, sky +7.6 (planned +5); Phoenix yellows/greens chroma -15, cyan **+8** (planned -7, sign reversed). "Sunset listens to its own record" with or without the -128 marker.
- conclusion: tables work; model under-predicts the blue region by 3-5x and the response is non-linear; Sunset (slot 4) honours its record.  confidence: medium
- caveats: sample is one frame per style; shift partly confounded by day drift (corrected with Standard).
- claims: not assigned

### E-0020: v5 (scaled v4 tables)  (2026-10-05)
- image: Backup write; block `bk/00030001_looks_v5.hex` md5 `9e3fc4acf14e3cb9d362c8436cfd7aa1`; log `live28.log` [21:10]
- change: v3 + v4 changes scaled by measured response: Portra x0.3, UltraMax x0.5, House x1, Phoenix cyan byte with reversed sign.
- observed: DSC09498-502 vs v3 base DSC09483-87 (drift corrected by Standard): Portra blues/cyan -6..-13 deg; UltraMax blues -4..-15 deg, yellow/green chroma -16..-26; House cyan/sky +4..+7 deg; Phoenix yellows chroma -15. Live frames "on v5" under incandescent lamp with WB Daylight were very yellow (not assessable); highlights blown ("the table is a white spot with hard edge").
- conclusion: v5 accepted as the state of the camera (Standard native, Vivid Portra 400, Portrait House, Landscape UltraMax 400, Sunset Phoenix II).  confidence: medium
- caveats: judged on the chart; live frames had lamp light; exposures differed (House 1/160 vs others 1/100).
- claims: not assigned

### E-0021: updater-mode insurance via /setting/updater/mode  (2026-10-05)
- image: file write on p2 `/setting/updater/mode` (empty file), no flash partition written
- change: [21:33 live29.log] mounted view of `/setting`, listing showed `updater/comp` (0 B) and `dat4` (2 B) but no `mode`; empty `mode` created, synced. Owner pulled the battery and cold-started with the power button.
- observed: "camera booted as usual" (msg 19:45Z, 21:45 local). After the boot `live30.log` [21:48] shows `updater/` again without `mode`.
- conclusion: the bootloader does not enter updater mode from this file while `comp` exists; the flag is consumed. No software safety net exists for p3/p8.  confidence: medium
- caveats: `mode`+`comp` may mean "update finished, clean up"; the variant "delete `comp`, create `mode`" was **not** tried.
- claims: not assigned (area SAFE / BOOT)

### E-0022: film tone curve k0 written into av-cam in p3 (first firmware write)  (2026-10-05)
- image: `work/tone/p3_fit.bin`, md5 `d7cca4469709a8b50bc5ad6efa34aa13` (= `current_p3.bin`); changed region 38 sectors 8849-8886 (`p3_orig_sect_8849.bin` md5 `186bf30ffef27869c60fd7deec82559e`, `p3_new_sect_8849.bin` md5 `921f2345759926751f22f3e9c42561e8`)
- change: [~21:56-22:03] curve k0 (Contrast -3, file `0x5b006a..0x5b0869`) replaced by a film curve (black 55/1023, white 909/1023, knots `[55,139,243,362,487,612,730,832,909]`), adjusted +-1..2 so that its 64 KiB LZPT block compresses to the identical size (table of blocks unchanged). Only the changed sectors were written; WBI sector 0 saved (`p5_sector0_before.bin`), WBI zeroed. No flash log of this write survives in the scratchpad.
- observed: grey wedge frames DSC09509 (Contrast 0) and DSC09510 (Contrast -3), same exposure: Contrast -3 shadows 12 15 19 28 (before: 0 1 5 14), highlights 222 226 228 229; Contrast 0 shadows 2 4 10 25, highlights 225-233 (different exposure set from the "before" pair). Black ~12/255 clean. Camera booted and shot normally.
- conclusion: partial p3 write inside av-cam is safe and effective; the tone curve is applied in the encoded (gamma) domain; k0 = Contrast -3 in any style.  confidence: high
- caveats: before/after sets differ in exposure (comparison only inside a pair); fitting step altered the curve by +-1-2 units; the on-camera content was later verified indirectly (06.10: live av-cam curve region differs from stock by 1093 B only in `0x5b006a..0x5b0869`).
- claims: not assigned (area TONE / DLV)

### Prepared but with no evidence of having been executed on the camera
The following blobs exist but neither a `live*.log`, a flash log nor a transcript message shows them written: `bk/00030001_looks_v6.hex`, `v6_phoenixsky.hex`, `v6_kodakwarm.hex`; `fx/*` (NR-1..NR-4, SH-1/2, SFprobe, promistA/B, PE1), `fx/3007a_mode2_k0.hex`, `3007a_mode1_film.hex`, `3007a_mode1_shoulder.hex`. The 06.10 morning-plan note itself says "not executed". The latest Backup `live*.log` is `live30.log` (05.10 21:48) and the state recorded on 06.10-09.10 is "v5 + k0". No E-ID is assigned.

---

## 2026-10-06 - updater/senser reconnaissance, RAM patches, first av-cam flashes

### E-0023: updater-shell environment recon (read-only)  (2026-10-06)
- image: live memory/FS op in updater shell; no writes. Raw output not preserved (only the notes keep it).
- change: [~11:00-11:20 msg] `mount`, `/proc/{partitions,iomem,cmdline,modules,kallsyms}`, `/dev` list, `/sys` UIO.
- observed: kernel `2.6.29.6-rt24-alp_nl SMP PREEMPT RT`, 3x ARMv6; `/dev/mem` and `/dev/kmem` exist; `memrsv=448M@0x84000000` and 19 MB @`0x82D90000`; only USB/storage/memstick + `dmm` + `mcmn_drv` loaded; `/system` empty, `liro.ko` not in the updater `/kmod`; nodes `/dev/mcmn`, `ldec`, `dmac`, `jet/adj_drv`; `uio0` at `f5060000` = "gpe" (not the engine); SA-MMIO (`0x40000/0x48000`) absent from iomem; `DmmConfig.bin` (77 KB) fetched from `/setting`.
- conclusion: the updater Linux is a recovery build without the imaging stack and with the SA block not mapped.  confidence: high
- caveats: single boot, one camera.
- claims: not assigned (area SYS / MEM / LNX)

### E-0024: insmod liro.ko inside the updater  (2026-10-06)
- image: live op; `liro.ko` pushed from p3 into `/tmp`, nothing written to flash
- change: [11:34 msg 09:34Z] `insmod /tmp/liro.ko` (no parameters), then dmesg and kallsyms look-ups; module removed and file deleted.
- observed: `insmod: unknown symbol in module`; dmesg `liro: Unknown symbol Backup_nread` (also `Backup_nread_setting_attr_async`, `_multi_async`, `_async`, `_setting_attr`, `_multi`); kallsyms entries for `Backup_write`, `acre_tsk`, `osal_snd_sync_msg`, `buddy_init_pool`, `loc_cpu`, `os_this_cpu` all absent.
- conclusion: the imaging stack cannot be started from the updater environment; "route A" (run av-cam from RAM there) is closed.  confidence: high
- caveats: only the missing-symbol list was seen; other blockers (SA power) were not tested after that.
- claims: not assigned (area LNX / DLV)

### E-0025: DRAM remanence test 1 (frame, then warm switch to updater)  (2026-10-06)
- image: live memory op, `/dev/mem` reads in the updater shell
- change: [12:45-13:00 msg] owner shot a normal frame ("camera connected, took a shot, raise the updater"), the camera was switched to updater without power-cycle; `dd` of `/dev/mem` at the pool bases from `DmmConfig` (`0x84b80000`, `0x84c00000`, `0x85000000`, `0x86000000`...) and a sweep of 55 samples x 8 KB, step 8 MB, `0x84000000..0x9f000000`.
- observed: `/dev/mem` reads the high zone (rc 0, non-zero data; 6 dumps with different md5); entropy 5.7-6.7 bit/B, zeros <0.2 %, vertical stride bands; `X` and `X+0x10000000` give identical statistics (physical DRAM 256 MB mirrored at `0x80xxxxxx`/`0x90xxxxxx`); no recognisable photo (minimum 2D-mad ~35-45 vs <20 for a smooth frame). pmca needed ~30-60 s to bring up the updater.
- conclusion: DRAM contents survive a warm switch, but the transient frame buffers were overwritten by live view before the dump.  confidence: medium
- caveats: the assistant later noted that the owner's frame was probably shot without Soft Focus, so this was not a convolution test; the sweep was coarse (8 KB every 8 MB).
- claims: not assigned (area MEM)

### E-0026: DRAM remanence test 2 (Soft Focus mid, RAW off)  (2026-10-06)
- image: live memory op; pull log `live.log` [13:28] (SURV2: `/tmp/s2.bin` 10485760 B, md5 `44f7a72bd9b7549864d09718935a972f`)
- change: [13:18-13:28] frame with Picture Effect = Soft Focus mid (RAW had to be disabled; effect is JPEG-only), warm switch to updater, sweep of 40 samples x 256 KB, step 4 MB, `0x86000000..0x90000000`, rendered raw and as YUV422 luma at widths 4912/2456/1232.
- observed: no scene anywhere; 2D-mad ~48; texture noise and tables only.
- conclusion: the Soft Focus input/output buffers cannot be caught no-flash; they are freed and overwritten within seconds. Remanence branch closed.  confidence: medium
- caveats: timing hypothesis; another allocation pool (still pool) was not proven absent.
- claims: not assigned (area MEM / DSP)

### E-0027: senser (service mode) enter, authenticate, readMemory  (2026-10-06)
- image: live memory op via `serviceshell` (pmca senser), read-only
- change: [13:47-14:01 msg 11:47-11:59Z] camera set to USB Mass Storage (resets to MTP after every reboot, needed to be re-set three times), service-mode switch, challenge-response auth with the generic keys, `readMemory` of 64 KB, 4 MB and 24 MB, sweeps of `0x84000000..0x90000000`, then `/dev/fb0` read in the interactive terminal.
- observed: auth succeeded on the NEX-3N; readMemory works; on live firmware the imaging stack is up (lsmod shows liro/unidrv1/unidrv2/dmm/mcmn) and the imaging DRAM has lower 2D-mad (down to 8.7) than the updater's (~48); `/dev/fb0` yields 54 bytes (dead end); the terminal can be left only by host SIGINT. Owner pasted an image of 4912x26 px (msg 11:59Z) - not described in the sources.
- conclusion: read access to ARM-physical RAM of the running camera works without writing flash.  confidence: high
- caveats: the display is not a standard Linux framebuffer; engine registers `0x40000+` are not in this address space.
- claims: not assigned (area MEM / DLV)

### E-0028: differential dumps around one frame, op3 input/output pair  (2026-10-06)
- image: live memory ops; files `work/op3data/dump1.bin`, `dump2.bin` (12582912 B each), `sf_input_sharp.bin`, `sf_output_softfocus.bin` (6291456 B each), all mtime [14:17]
- change: [14:08-14:17] dump 1 (baseline) -> owner took a frame (USB unplugged, plugged back, **no power cycle**) -> dump 2; then a second shot without the effect (sharp input), camera hand-held ("cannot repeat exactly").
- observed: 77 of 192 regions identical between dumps, changed clusters `0x86800000..0x88700000`, `0x8b*`, `0x8c*`; image-like regions `0x85900000`, `0x85b00000`; raster stride 1280 B (autocorrelation peak, vertical-mad 4.86); rendered at width 1280 the colour chart and the camera's "USB Mode" screen are visible; the Soft Focus frame is softer.
- conclusion: DRAM persists across a USB unplug/plug when the camera is not power-cycled, so before/after diffing localises capture buffers; the image-level pair is only the final convolution (kernel already known) and does not decode op3.  confidence: high (method), medium (buffer identification)
- caveats: the 1280-wide buffer is a display/preview-size copy, not the full-size YC (see E-0031).
- claims: not assigned (area MEM / DSP)

### E-0029: av-cam located in live DRAM  (2026-10-06)
- image: live memory op (senser readMemory)
- change: [14:38-14:40 msg 12:38-12:40Z] scan for av-cam strings (`Start_SoftFocus`, `SoftFocus_Main`, `HapiSFTFCS`, `CAMERA_MAIN_YC` at `0x8398282f`, `0x839828b3`, `0x839828f7`, `0x8350b1c1`), then read of `0x83441000` and comparison with `av-cam.bin`.
- observed: physical base `0x83441000` (virtual `0xc3441000`, `phys = virt - 0x40000000`); 99.5 % of bytes identical to the file (remainder relocated pointers / BSS).
- conclusion: every av-cam address analysed statically can be read from live RAM at `virt - 0x40000000`.  confidence: high
- caveats: none noted.
- claims: not assigned (area MEM / SYS)

### E-0030: senser writeMemory on display buffers  (2026-10-06)
- image: live memory write (not persistent)
- change: [14:46-14:56 msg 12:46-12:56Z] (a) invert 596 KB strip at `0x85AC9000` (USB-mode OSD strip, rows ~1460-1930, stride 1280); (b) read twice a region to find static parts (only `0x85300000` constantly, `0x84100000`/`0x84900000` partly change; stable USB-screen candidate `0x85b00000`); (c) invert 256 KB at `0x85b50000`.
- observed: (a) readback after the write is neither inverted nor the old data (49.5 % match with something else) = buffer being rewritten; owner: "nothing changed"; "the write dropped and there was a reconnect window" (USB reconnect, camera intact). (c) no reconnect; readback 0 % inverted, 48 % original; owner afterwards: "something flickered on the screen" (msg 12:56Z).
- conclusion: writeMemory reaches the display RAM (visible flicker) but the redraw overwrites it faster than USB writes; large writes into live pipeline buffers can drop the USB link.  confidence: medium
- caveats: the "flicker" is an owner recollection after the second write; the first write's USB drop may be coincidence with the 596 KB size.
- claims: not assigned (area MEM)

### E-0031: full-size YC buffer located after a frame  (2026-10-06)
- image: live memory op (readMemory after a shot, no power cycle)
- change: [~15:30-15:38 msg 13:30-13:38Z] owner shot a frame, plugged USB in Mass Storage; dumps of `0x84000000..`; width found by row-to-row autocorrelation.
- observed: YC_FULL for that shot at `0x8a000000`, YUYV 4:2:2, width 4912, stride `0x2660` (9824 B/row, ~32 MB), luma in even bytes, rowdiff 0.49 at w=4912; previous shot's base was `0x85900000`; the base appears 37 times in descriptor tables (`0x83dcc9xx`/`0x83dce2xx`). Another JPEG output buffer starts with `FFD8` (found later at `0x8e000000`).
- conclusion: the developed canvas is YUYV, base dynamic (do not hard-code).  confidence: high
- caveats: the 4912 wide canvas differs from the 4928 wide per-stage copies found in E-0041; the two geometries must not be mixed.
- claims: not assigned (area MEM / PIPE)

### E-0032: RAM patch 1 - Stage_SoftFocus replaced by a grain routine  (2026-10-06)
- image: live memory write (not persistent); original saved as `orig_sf.bin`
- change: [~15:53 msg 13:53Z] 70-byte Thumb-1 xorshift grain written over `Stage_SoftFocus` at phys `0x837ea898` (first ~426 rows per the instruction text); readback MATCH.
- observed: owner: "shot, I don't see grain but it does not look like soft focus" (msg 13:56Z). Card read: DSC09516 (15:57) EXIF Picture Effect = **Off**, clean frame. Next shot DSC09517 (16:01) Picture Effect = Soft Focus: normal Soft Focus blur. A read of `0x837ea898` afterwards showed the **original** bytes.
- conclusion: the test was invalid (effect was off); by the second frame the RAM patch had been lost (camera rebooted, probably auto power-off while the owner worked in the menu).  confidence: high (that the patch did not run), medium (reboot cause)
- caveats: owner's first impression "not soft focus" contradicts the EXIF (Off); the cause of the reboot was inferred.
- claims: not assigned (area DLV)

### E-0033: RAM patch 2 (fresh boot, +-31, 8 MB)  (2026-10-06)
- image: live memory write (not persistent)
- change: [~16:09 msg 14:09Z] power-cycle, Mass Storage, grain over `Stage_SoftFocus` +-31 on the first 8 MB, readback MATCH; owner disconnected USB and shot one Soft Focus frame within ~30 s.
- observed: owner: "interesting - I did not see the preview after the shot" (msg 14:09:52Z). No new JPEG on the card (last was DSC09517). A senser read afterwards showed the original bytes at `0x837ea898` and av-cam 64/64 stock.
- conclusion: leaving service mode reboots the camera and reloads av-cam from flash, so RAM patches never survive to a capture (confirmed twice here, a third time in E-0035).  confidence: high
- caveats: the missing JPEG and preview are attributed to the reboot; not independently shown.
- claims: not assigned (area DLV / SAFE)

### E-0034: FileControl write test to /system  (2026-10-06)
- image: file ops via senser FileControl; log `ft.log` [17:05]
- change: write `/setting/gtest.bin`, then `/system/gtest.bin`. Before this, `readFile('/system/av-cam.bin')` had been read OK (6554072 B) and compared to `sys_avcam.bin`; an earlier attempt failed with "no window" (msg 15:03Z).
- observed: `/setting/gtest.bin` write OK, readback MATCH, deleted; `/system/gtest.bin` FAIL "Senser file control error 130". The on-camera av-cam differs from stock only in `0x5b006a..0x5b0869` (1093 B).
- conclusion: `/system` (p3) is read-only through FileControl; `/setting` (p2) is writable; the live av-cam carries the owner's film curve.  confidence: high
- caveats: none.
- claims: not assigned (area PART / DLV)

### E-0035: RAM detour at 0xc3889760 + one frame (DSC09519)  (2026-10-06)
- image: live memory write (not persistent); log `det.log` [20:33]
- change: trampoline at `0xc3889772` + stub/grain in cave `0xc3a011c0` (+-15, 8 MB) written to phys `0x83889772`/`0x83a011c0`, both MATCH; owner unplugged USB and shot a normal frame with Soft Focus on.
- observed: DSC09519: high-frequency noise in the "grain zone" (top 853 rows) vs outside: ratio 1.01, i.e. a clean original Soft Focus frame.
- conclusion: RAM delivery fails for the third time (reboot on service-mode exit); flash the partition instead.  confidence: high
- caveats: same as E-0033.
- claims: not assigned (area DLV)

### E-0036: FileControl probe over all mounts  (2026-10-06)
- image: file ops via senser; log `probe.log` [20:43]
- change: write test files into `/setting`, `/usr`, `/system`, `/android`, `/info`.
- observed: `/setting` OK, readback MATCH; `/usr`, `/system`, `/android`, `/info` all "error 130".
- conclusion: only p2 is writable as a file; p3, p8 need raw writes.  confidence: high
- caveats: none.
- claims: not assigned (area PART)

### E-0037: updater-shell file operations and mount attempts (no write succeeded)  (2026-10-06)
- image: updater-shell session; logs `flash.log` [20:49], `diag.log` [20:54], `flash2.log` [20:57], `mdiag.log` [20:59]
- change: attempted `PULL /system/av-cam.bin` (before any write), `mount`/`ls`, `mount -t vfat /dev/nflasha3 ...` (also without `-t`, and `-o ro`), partition listing.
- observed: PULL -> `Exception: Unknown error`, no write was reached; the camera then stayed in updater mode (next entry could not read the model, a power cycle fixed it); `/proc/mounts`: `/dev/nflasha2 /setting vfat rw`, `/dev/loop0` cramfs; `/system` empty dir; `mount ... /dev/nflasha3` -> `Invalid argument` in all three forms; `/proc/filesystems`: ext2 cramfs axfs ramfs vfat; `/proc/partitions` lists `nflasha0p1..p12`, p3 = 10240 blocks (10 MB); `/system` not writable.
- conclusion: p3 is not a mountable vfat in the updater; the way in is a raw write of the LZPT partition.  confidence: high
- caveats: the assistant's first guess ("axfs/cramfs, read-only compressed FS") was not verified; p3 is an LZPT container.
- claims: not assigned (area PART / DLV)

### E-0038: p3_grain - always-run detour at 0xc3889760, +-15, 8 MB  (2026-10-06)
- image: `p3_grain.bin`, md5 `b1142dd80865f60620ff02d8ed12bca6` (av-cam = `av-cam_grain_live.bin`: live film curve + detour); log `flash3.log` [21:13]; recovery `current_p3.bin` `d7cca446...`
- change: first persistent flash; trampoline after the gate `r4[0x3c] in {1,2}` at `0xc3889772`, stub and 70-byte grain in the cave `0xc3a011c0`, base taken from `session[0x3e24]`. About 83 % of the partition changes (code changes the compressed block sizes, LZPT layout shifts). Whole-partition md5 verified, WBI zeroed.
- observed: camera boots, shoots, saves frames (assistant: "survived the flash"); high-frequency noise ratio top/bottom 0.99 and 0.85 (no grain); a live senser read (`schk.log` [21:15]) shows trampoline `014b1847 0000c111a0c3...` at `0x83889772` and the cave stub, i.e. the new p3 was running.
- conclusion: delivery and execution context work (flash, md5, WBI reset, boot); the hook either was not reached or grained something else (gate assumed false).  confidence: high (delivery), low (gate explanation)
- caveats: how often `0xc3889760` runs per frame was never established.
- claims: not assigned (area DLV / PIPE)

### E-0039: p3_grain_sf - Stage_SoftFocus replaced by grain  (2026-10-06)
- image: `p3_grain_sf.bin`, md5 `93dda2a4c1d8a2db9e7d8a1efda7d510`; log `flash4.log` [21:20]
- change: `Stage_SoftFocus` (`0xc37ea898`) body replaced by the grain routine writing `session[0x3e24]` as base, +-31, top ~850 rows.
- observed: owner: "preview of the frame appears **without the effect**, then falls; the photo is not saved" (msg 19:22Z, 19:24Z).
- conclusion: replacing the stage breaks develop -> SF -> encode data flow (and the base pointer is wrong); camera needs a power cycle, SF must not be used.  confidence: medium
- caveats: the exact crash mechanism (write to `0x1df`, missing SF output) was inferred; E-0040 supports the pointer part.
- claims: not assigned (area PIPE)

### E-0040: p3_diag - diagnostic stub replaces Stage_SoftFocus, writes session fields to scratch  (2026-10-06)
- image: `p3_diag.bin`, md5 `0f4e30f0e48bd6f0848742a1bcbec7d3`; log `flash5.log` [21:30]; scratch read `scr.log` [21:32]
- change: stub stores 5 session fields and the session address into `0xc3a01400`, marker `0xdeadbeef`, does not touch pixels, returns 0.
- observed: after an SF-mode shot, senser read of the scratch: `session[0x3e24] = 0x1df`, `[0x39e0] = 0x14420000`, `[0x1b8] = 0x0`, `[0x3a98] = 0x10`, session object address `0xc3b2de54`, marker `0xdeadbeef` present. Camera shoots without SF and saves.
- conclusion: `session[0x3e24]` is a small id (handle), not a buffer address - the earlier grain wrote 8 MB at `0x1df`.  confidence: high
- caveats: the field is an id for this stage; its meaning (handle) was derived later.
- claims: not assigned (area PIPE / MEM)

### E-0041: session object and candidate buffers dumped  (2026-10-06)
- image: live memory op; logs `sess.log` [21:35], `sess2.log` [21:38]; `cand_*.bin`, `session_obj.bin`
- change: after an SF shot (no power cycle), read 16896 B of the session object at `0x83b24f44` (first shot) / `0x83b2de54` (second shot, address differs per frame) and 11 candidate bus pointers.
- observed: `+0x4c0 = 0x0e000000` (buffer starting `ffd8ffe1` = finished JPEG), `+0x5e4 = 0x0d000200`, `+0x1884.. = 0x0c000c00`, `0x0c030c00`, `0x0c0b0c00`, `+0x1ea0 = 0x08020000`, `+0x1f24 = 0x0b8b0000`/`0x0be00000`, `+0x24e8 = 0x0d010000`/`0x0b010000`, `+0x3858 = 0x0a0a0100`, `+0x0150 = 0x08010400`; eight clean YUYV buffers 4928 px wide (rowdiff 0.27-0.52); `0x08010400`/`0x08020000` rowdiff 64 (RAW/Bayer-like). Pointers are bus addresses (`virt = bus | 0xc0000000`, `phys = bus | 0x80000000`).
- conclusion: map of buffers per frame; `session[0x5e4]` picked as the encode-input candidate "next to the JPEG output".  confidence: medium
- caveats: "encode-input" was never demonstrated; E-0049 later shows `session[0x5e4]` at the last develop step is not what the encoder reads.
- claims: not assigned (area MEM / PIPE)

### E-0042: p3_sfwrap - wrapper: real Stage_SoftFocus, then grain session[0x5e4]  (2026-10-06)
- image: `p3_sfwrap.bin`, md5 `61e7e8d5a55d8549718bab4164fd4d01`; log `flash6.log` [21:49]; builder `build_wrap.py`
- change: the 8 dispatcher `bl Stage_SoftFocus` sites (`0xc36282a2 .. 0xc362876a`) redirected to a wrapper in the cave `0xc3a011c0`; wrapper = call real SF, then xorshift32 noise (+-31, luma and chroma bytes alike) over the first 8 MB of `session[0x5e4]` (bus -> virt), return SF's result.
- observed: owner: "but the Soft Focus effect itself is still there" (msg 19:51Z). Frame DSC09527 saved (no crash), file 3.8 MB (larger than usual); assistant measured high-frequency luma noise **bottom 22.3 vs top 0.69**; a crop of the bottom showed visible digital-looking grain. Assistant at the time: "grain works SOOC".
- conclusion (at the time): wrapper keeps the data flow intact, `session[0x5e4]` accepted as the encode input; buffer assumed stored bottom-up. **Superseded** by E-0049/E-0051 and `dsp-grain-campaign.md`: the surviving bottom patch is a race artefact (see revisit list).  confidence: low
- caveats: grain amplitude +-31 is high; "only the bottom" fits both the bottom-up theory and a race with the DSP.
- claims: not assigned (area PIPE / DLV)

### E-0043: p3_iso400 - SF skipped, grain +-15 luma / +-3 chroma, full frame  (2026-10-06)
- image: `p3_iso400.bin`, md5 `571f520296c8e84b6dada470e335e163` (builder `build_set.py`, log `build_set.log`); flash log `flash_iso400.log` [22:19]
- change: wrapper does **not** call SF (returns 0), grains `session[0x5e4]` over the full region.
- observed: owner: "look, something is applied but I don't really see grain" (msg 20:21Z). Assistant measure: noise ~2.1 vs ~22 in E-0042.
- conclusion (at the time): with SF skipped `session[0x5e4]` is not the encode buffer. A fall-back was planned (grain all four candidate buffers).  confidence: low
- caveats: later work shows `session[0x5e4]` never reliably reaches the file, so "SF skipped" vs "SF called" difference may be only the race.
- claims: not assigned (area PIPE)

### E-0044: p3_stripe - SF called, five vertical grain bands  (2026-10-06)
- image: `p3_stripe.bin`, md5 `f56c783962cf8d5cf8903d30a07bb73a`; log `flash_stripe.log` [22:34]; builder `build_stripe.py`
- change: SF called, then 5 vertical bands (amplitudes +-1/+-3/+-7/+-15/+-31) over region `0x1E00000`, stride 9856.
- observed: owner: "shot a couple of frames, it thinks for a long time of course" (msg 20:35Z). Frame blurred (SF), grain visible on a dark strip at the bottom only; centre/top noise 0.8; the five bands not distinguishable.
- conclusion (at the time): per-pixel pass over ~31 MB is too slow (watchdog/abort at about a third), so only the bottom is grained; digital look from uniform white noise on every pixel and chroma.  confidence: low
- caveats: "slow loop aborted" is an inference; the race explanation fits the same data.
- claims: not assigned (area PIPE)

### Built on 06.10 but not flashed (no flash log): `p3_lowiso` `e25a87b6884bf6c1464aab0d94d366ff`, `p3_iso800` `7af00ce9634ce793415518a3f3153805`, `p3_highiso` `1e0a204b68467059cf774db7c2e0fcc3`, `p3_softdream` `04089e2500d2abaa70d890327c729a28`, `p3_iso400_8mb` `4847a94a4ec679702a2f1b9ac709064d`, `p3_multibuf` `b6bf277d31a9b300923d6018d697d888`, `p8_filmgrain.bin`. The notes' phrase "iso800 visible, DSC09527" refers to the +-31 sfwrap frame (E-0042), not to an iso800 image.

---

## 2026-10-07 - grain hook variants, encode-path loggers, idt_cam NOP bisection (Campaign A)

Frames DSC09535..DSC09557 belong to this day. All images keep the film curve (`sys_avcam.bin` base or live av-cam), p3 whole-partition flashes with md5 MATCH and WBI zeroed.

### E-0045: p3_v2med - SF called, then luma-only windowed 2x1-clumped grain  (2026-10-07)
- image: `p3_v2med.bin`, md5 `94dcb0f04d752a4ddf76a4c78f372835` (siblings built, not flashed: `v2soft` `24d8a1b9b9229f1934b3b0be7f612852`, `v2strong` `0747ba444efee847723d38049c214b91`); log `flash_v2med.log` [10:04]; builder `build_grain_v2.py`
- change: wrapper at the 8 SF sites: call real SF, then grain `session[0x5e4]`, luma only, window `min(Y,255-Y)/128`, ~+-14 (med), clamp 2x1, region `0x1A00000` (~85 %).
- observed: frames DSC09535-38 (Soft Focus, ISO 800, 4912x3264). Luma high-frequency std ~0.6; Soft Focus blur present. Owner only said "shot" (msg 08:05Z).
- conclusion (assistant, then): v2 regressed; grain went into SF's discarded input buffer. **Superseded** by E-0049: no ARM-side buffer reliably reaches the encoder.  confidence: low
- caveats: the "input vs output of SF" explanation is untested.
- claims: not assigned

### E-0046: p3_v3med - SF skipped, luma-only windowed grain  (2026-10-07)
- image: `p3_v3med.bin`, md5 `98ad7cdcdc5a12129049741f93fcca2c` (not flashed: `v3soft` `a35a345b45b1c946b9405ee3ea5d31a4`, `v3strong` `77875b521142ce44666da22c408cc5f4`); log `flash_v3med.log` [10:17]; builder `build_grain_v3.py`
- change: as v2 but SF not called (return 0); +-15, mid-tone window, clump 2x1.
- observed: owner: "no blur" (msg 08:19Z). Frames DSC09539-41 (SF, ISO 800): luma HP std ~1.8 in one crop, 0.7-1.1 elsewhere; luma ACF lag-1 0.5-0.59; chroma 0.2-0.3. The crop landed on a fabric texture, so ACF is polluted; visually "no real grain".
- conclusion: SF-skipping removes the blur (so the hook runs and SF's work is genuinely skipped); grain amplitude in the file is ~1, far below the +-15 written.  confidence: medium (blur gone), low (the "JPEG quantisation eats it" explanation then given)
- caveats: see E-0049; amplitude independence points to the buffer not being the encoder input at all.
- claims: not assigned

### E-0047: p3_v4med - SF skipped, luma-only +-31 flat; HC Mono control  (2026-10-07)
- image: `p3_v4med.bin`, md5 `38d43251dffac4b3669c5eb92bca2501` (not flashed: `v4strong` `fae5e1f159d97d0d0a28a9a5d9ab4e6e`); log `flash_v4med.log` [10:29]; builder `build_grain_v4.py`
- change: no window, +-31, luma only, clump 2x1.
- observed: frames incl. DSC09542 (flat wall): HP std 0.78 / 1.13 / 1.84 (v3med: 1.84 / 0.74 / 1.12): tripling the amplitude changed nothing; 300 % crop "faint fine speckle, not film grain". Control DSC09545 (native High Contrast Mono, effect outside the hook): HP std 2.7-3.4, chroma 0.00, ACF lag-1 0.58 / lag-2 0.39; EXIF of that frame reports Creative Style Standard, Color Mode Standard, Saturation/Contrast Normal although the picture is B&W and contrasty. Owner shots at msg 08:31Z and 08:36Z; no comment recorded.
- conclusion: grain amplitude does not propagate to the JPEG (hook at the Soft Focus stage is "too early"); native B&W has no grain generator (it is sensor noise amplified by contrast, applied late, outside the colour-mode slot).  confidence: medium
- caveats: the "applied late" inference rests on EXIF vs picture mismatch plus statics.
- claims: not assigned

### E-0048: p3_v5med - hook at the last develop step (rec40), +-31 luma  (2026-10-07)
- image: `p3_v5med.bin`, md5 `aef3f6d7152e4d494ee7c96a06d8267a` (not flashed: `v5strong` `3a115467193afe404ece2f32b92474ec`); log `flash_v5med.log` [10:55]; builder `build_grain_v5.py`
- change: two wrappers in the cave at the rec40 dispatcher (`0xc3628b18`) sites `0xc3628b2c` (class 0 -> `0xc37ee680`) and `0xc3628b26` (class 1 -> `0xc37ecb06`): call native, grain `session[0x5e4]`, return native result. SF stage no longer touched.
- observed: owner: "soap again" (msg 08:56Z) on Soft Focus frames (DSC09546/47; class 2 -> rec40 skipped, native blur returned; HP std 0.43). Off frame DSC09548 (msg 09:04Z): HP std 0.73, no grain.
- conclusion: the Soft Focus effect class skips rec40; but on the class 0/1 frame (effect off) the grain still does not reach the file.  confidence: medium
- caveats: whether "Off" is class 0/1 was only established afterwards by a static class map (`ctx[0x23]`).
- claims: not assigned

### E-0049: p3_markrec40 - black marker at rec40  (2026-10-07)
- image: `p3_markrec40.bin`, md5 `ab3d49ef86e75460a7fcd33db2bd9b98`; log `flash_mark.log` [11:11]; builder `build_marker.py`
- change: same rec40 wrappers, but instead of grain the first ~6 MB of `session[0x5e4]` are filled with 0x00 (black bar).
- observed: frames DSC09548/49/50 (`scratchpad/mark/`): 0 % black everywhere, Off frames included; one frame without and one with effect shot at msg 09:13Z.
- conclusion: `session[0x5e4]` at rec40 is not the buffer the JPEG encoder reads; later RE: output of the last develop stage goes by handle `session[0x3e24]`; `session[0x5e4]` was a live DMA buffer only on the early SF stage (rec1-4) and is rewritten by the 31 calls of develop core `0xc37ea42e`.  confidence: medium
- caveats: DSC09548 was already shot at 09:04Z, before this image (flash [11:11]), yet is listed as a marker frame - the frame labelling in the session is off by one at least; the "Off = class 0/1" premise came from a static analysis done after the shot.
- claims: not assigned (area PIPE / MEM)

### E-0050: p3_difflog - detour logger in encode handler 0xc3474800  (2026-10-07)
- image: `p3_difflog.bin`, md5 `96cd5870766dac122edf301c1d645b06`; log `flash_difflog.log` [11:36]; builder `build_difflog.py`
- change: detour at the start of `0xc3474800` (stub 92 B in the cave) copying `[0xc3ca0528]` (0x40 B) and a marker `0xd1a6` into scratch `0xc3a01400`.
- observed: senser read of scratch after a frame: all zeros including the unconditional marker; trampoline and stub confirmed present in live RAM. Owner shot at msg 09:37Z; the assistant later refers to a "no preview" remark (not found in the user messages extracted).
- conclusion: `0xc3474800` is not the still-image encode entry; `tsk46_jpeg` (`0xc344a790`) dispatches cmd 1/3 -> `0xc3474800`, cmd 0/2 -> `0xc347427a`.  confidence: high
- caveats: build needed a `__main__` guard (LZPT writer spawns a multiprocessing pool; earlier fork-bomb).
- claims: not assigned (area JPEG / PIPE)

### E-0051: p3_difflog2 - detour logger in still encode handler 0xc347427a  (2026-10-07)
- image: `p3_difflog2.bin`, md5 `96aaf536d938d51b8b690f3053b3c898`; log `flash_difflog2.log` [11:46]; builder `build_difflog2.py`
- change: hook at `0xc347427a`, back-jump `0xc3474284`; scratch: marker `0xd1a6`, `[0xc3ca0528]`, msg pointer and fields.
- observed: marker present, preview shown, capture healthy. `[0xc3ca0528]` NULL; msg pointer `0xc2b1700c`, `msg[0] = 2`, `msg[8] = 0`. The handler is called several times per frame; the logger holds the last (cleanup) call. Senser read does **not** reboot the camera (it returns to the shooting screen). Context singleton (return of `0xc35dc8ba`) = `0xc3bb7bc0`; read live: only state flags (`0x80000002`...), no buffer pointer. A `JPEG qtable` follows `0xc3ca052c`.
- conclusion: the encode handler gets no ARM-visible YC address; the buffer is passed by handle to the DSP/HW (`0xc35dcde6`/`0xc35dc952`). ARM path closed (also from two static RE threads).  confidence: medium
- caveats: logger overwritten per call, so the encode call itself was not captured; one-sided evidence of absence.
- claims: not assigned (area JPEG / PIPE)

### E-0052: nopc171 - NOP idt_cam 0x2d4e0..0x2e608  (2026-10-07)
- image: `p3_nopc171.bin`, md5 `f20267134a882480a8381faab6515648`; log `flash_nopc171.log` [12:35] (first flash attempt failed: camera not visible); builder `build_nopcore.py` (clean film-curve av-cam, NOP bundle `0x1f70fb87dc3ee1f7` over the range, idt_cam inner `0x980e00`)
- change: [12:35] one late large "core" (1128 B range) overwritten with NOP bundles.
- observed: frames DSC09551 (scene), DSC09552 (flat grey, Ymean 117, Ystd 10, neutral chroma), DSC09553: normal.
- conclusion: range not used by stills (or its corruption is harmless).  confidence: medium
- caveats: **see revisit list (R-1)**: bytes in these ranges include scalar code and data; NOP executed as scalar is garbage with branches.
- claims: not assigned (area IDT / DSP)

### E-0053: nopc132 - NOP idt_cam 0x249d0..0x25fa8  (2026-10-07)
- image: `p3_nopc132.bin`, md5 `aafe36934eb37166988eee1f53d154ab`; log `flash_nopc132.log` [12:42]
- change: the largest "core" (699 bundles) NOPed.
- observed: DSC09554 flat grey (Ystd 14), DSC09555 scene (Ymin 1, Ymax 249): normal.
- conclusion: not on the still path.  confidence: medium
- caveats: as E-0052.
- claims: not assigned

### E-0054: nophalf2 - NOP idt_cam 0x1c000..0x2ea68 (second half)  (2026-10-07)
- image: `p3_nophalf2.bin`, md5 `c07db2c5a00135d526a535f0c97c236f`; log `flash_nophalf2.log` [12:50]
- change: whole second half of the VLIW region NOPed.
- observed: owner: "after the shot it says 'writing to memory card' and it does not end"; battery/reboot ("reboot?" - "after reboot it saved", msg 10:51-10:53Z). Saved frame DSC09556: normal image (Ymin 2 / Ymax 249, colour fine).
- conclusion (then): second half = encode/write; develop output unaffected. Now: some code/data in this range is required to finish the write (could equally be scalar control overlays).  confidence: low
- caveats: R-1.
- claims: not assigned

### E-0055: nophalf1 - NOP idt_cam 0xa598..0x1c000 (first half)  (2026-10-07)
- image: `p3_nophalf1.bin`, md5 `3190c9fa416472d8b78346d5112a0d7f`; log `flash_nophalf1.log` [12:59]
- change: first half NOPed.
- observed: owner (msg 11:01Z): "hangs on trying to focus; lets me shoot; dies". Battery pull needed. Owner "alive" at msg 11:15Z after battery pull.
- conclusion (then): first half = develop plus live view/focus.  confidence: low
- caveats: R-1.
- claims: not assigned

### E-0056: nopq2 - NOP idt_cam 0x13000..0x1c000  (2026-10-07)
- image: `p3_nopq2.bin`, md5 `69334d420475a64add3fefcae9121215`; log `flash_nopq2.log` [13:20]
- change: first attempt (~13:06) failed (updater-switch timeout, camera left in updater until battery pull); second flash succeeded.
- observed: owner (msg 11:21Z): "shot a frame, all ok". DSC09557 normal (Ymean 149, full range, colour fine).
- conclusion: this range is not needed for stills.  confidence: medium
- caveats: negative result is the more robust kind (a corrupted range that is not run does nothing), but R-1 applies if a part of it was run.
- claims: not assigned

### E-0057: nope2 - NOP idt_cam 0xe800..0x13000  (2026-10-07)
- image: `p3_nope2.bin`, md5 `413bbc9c7c2a66ad40204e5e24b822e7`; log `flash_nope2.log` [13:27]
- change: eighth of the VLIW region NOPed.
- observed: owner (msg 11:29Z): "again a black frame after focusing, and it dies after the shot". Assistant: focus alive, luma black, chroma intact (the frame itself is not in the archive).
- conclusion (then): luma develop in `0xe800..0x13000`. **Revisit**: black may come from broken AE/stat overlays; see R-1/R-2.  confidence: low
- caveats: R-1; the sub-range `0xe800..0x10c00` (e2a) was never flashed, so the table row "e2a = luma write (black)" is inferred from this result.
- claims: not assigned

### E-0058: nope2b - NOP idt_cam 0x10c00..0x13000  (2026-10-07)
- image: `p3_nope2b.bin`, md5 `c7bec421cbfa590b9e1146aa336039c4`; log `flash_nope2b.log` [13:35]
- change: late part of the previous range.
- observed: owner (msg 11:41Z): "everything very bright, after the shot it died on a white screen". Battery pull needed.
- conclusion (then): late luma tone/gain stage. **Revisit** (R-2): same symptom family was reproduced on 09.10 with narrower ranges (E-0060..E-0062) and the cause moved to a statistics overlay.  confidence: low
- caveats: R-1.
- claims: not assigned

### E-0059: restore current_p3 after the bisection  (2026-10-07)
- image: `current_p3.bin`, md5 `d7cca4469709a8b50bc5ad6efa34aa13`; log `flash_restore.log` [13:48]
- change: full partition restored, md5 MATCH, WBI zeroed.
- observed: "camera restored" (assistant); no frame reported by the owner.
- conclusion: restore path works after ten p3 flash cycles; zero bricks.  confidence: high
- caveats: none.
- claims: not assigned (area SAFE / DLV)

Built from `build_nopcore.py` but never flashed (no image, no log): `nopc161`, `nopc140`, `nopc145`, `nopc154`, `nopc166`, `nopq1`, `nope1`, `nope2a`, `nopq3`, `nopq4`. The rows "q1 = develop+focus+luma (implied)" and "e2a = main luma write (black, from the e2 result)" in `dsp-grain-campaign.md` are inferences, not tests.

---

## 2026-10-09 - NOP narrowing and overlay skips (`~/nex3n-dump/work/nopcore/`)

Owner's observations below are as relayed in the 09.10 session ("enter as is"); the source logs only prove the flash.

### E-0060: nope2b1 - NOP idt_cam 0x10c00..0x12520  (2026-10-09)
- image: `p3_nope2b1.bin`, md5 `bc3a71e0a3fe43e73d4df657a08b15a0`; log `nopcore/flash_nope2b1.log` [13:31] (an earlier attempt at 13:24 failed with `ModuleNotFoundError: usb` in the scratchpad copy)
- change: first 09.10 cycle, range 0x10c00..0x12520.
- observed: overexposure by 2-4 stops, not blown to white ("not into milk"); saving hangs.
- conclusion: bright symptom comes from the part of this range outside E-0061/E-0062 by subtraction, i.e. `0x10c00..0x11280`; overlay `0x105d0` (mailbox statistics loop, 5 accumulators + 64 B to ARM, no pixel write-back) is the candidate: corruption of its literal pool/kernel -> wrong AE/DRO.  confidence: medium (localisation), low (mechanism - from code reading only)
- caveats: severity differs from E-0058 ("very bright, dies on white screen"); interactions between sub-ranges not tested; **R-1** (NOPs as scalar code).
- claims: not assigned

### E-0061: nope2b2 - NOP idt_cam 0x12520..0x13000  (2026-10-09)
- image: `p3_nope2b2.bin`, md5 `3d20858576c1259e26fa2c0060008473`; log [13:38]
- change: tail of the previous range.
- observed: normal.
- conclusion: not used by stills.  confidence: medium
- caveats: R-1.
- claims: not assigned

### E-0062: nopov11280 - NOP idt_cam 0x11280..0x12520 (whole overlay 0x11280)  (2026-10-09)
- image: `p3_nopov11280.bin`, md5 `eb9bc45f7dfed64504fd622378789037`; log [13:44]
- change: overlay at `0x11280` (586-bundle "core25", contains a 65536/n reciprocal table) NOPed.
- observed: normal.
- conclusion: `0x11280` is not used by stills; the brightening in E-0060 is not from it.  confidence: medium
- caveats: R-1.
- claims: not assigned (area IDT)

### E-0063: skip_f6c0 - overlay stub "bl r1" -> nop  (2026-10-09)
- image: `p3_skip_f6c0.bin`, md5 `b595808f59c243323e75c09004495713`; log [13:54]; builder `build_skipov.py` (stub `5f50 5e50 5150 b100`, bytes `+6..+7` `b100 -> 0000`)
- change: overlay `0xf6c0` (writes 2D blocks from local `0x9000`; possibly AE/AWB grid) skipped.
- observed: live view blinks at 1/4000 f/16; black screen when focusing; saving hangs.
- conclusion: the ARM waits for this overlay's completion; skip is non-specific.  confidence: medium
- caveats: identical symptoms in E-0064/E-0065 mean no overlay-specific information.
- claims: not assigned

### E-0064: skip_cbd0 - overlay stub skipped  (2026-10-09)
- image: `p3_skip_cbd0.bin`, md5 `ce89028b5cdb32507aace13076b4fee9`; log [14:03]
- change: overlay `0xcbd0` skipped.
- observed: live view blinks 1/4000 f/16; black screen at focusing; saving hangs.
- conclusion: as E-0063.  confidence: medium
- caveats: as E-0063.
- claims: not assigned

### E-0065: skip_105d0 - overlay stub skipped  (2026-10-09)
- image: `p3_skip_105d0.bin`, md5 `0b4d9468dc5453efe8cc2e5e819e0f80`; log [14:10]
- change: overlay `0x105d0` (stats) skipped.
- observed: blinks 1/4000 f/16; saving hangs (no mention of a black screen at focusing).
- conclusion: as E-0063.  confidence: medium
- caveats: as E-0063.
- claims: not assigned

### E-0066: restore current_p3 after overlay tests  (2026-10-09)
- image: `current_p3.bin`, md5 `d7cca4469709a8b50bc5ad6efa34aa13`; log `nopcore/flash_restore.log` [14:17]
- change: full restore, md5 MATCH, WBI zeroed.
- observed: no remark recorded; the state is later quoted as "camera: current_p3".
- conclusion: restore path still works; camera on film k0 + v5, no grain, no NOP.  confidence: high
- caveats: none.
- claims: not assigned

---

## Summary table

| E-ID | date | what | outcome |
|---|---|---|---|
| E-0001 | 04.10 | flash + Backup dump (read) | ok |
| E-0002 | 04.10 | null Backup write `01070937=00` | safe |
| E-0003 | 04.10 | flag `01070937=01` | no effect |
| E-0004 | 04.10 | flag `0107093b=01` | no effect |
| E-0005 | 04.10 | 8 flags (group 1) NEX-6 values | no effect |
| E-0006 | 04.10 | 8 more flags (group 2) | no effect |
| E-0007 | 04.10 | revert 16 flags, boot dumps | ok |
| E-0008 | 04.10 | `0x30106` step 80->32 | confounded |
| E-0009 | 04.10 | revert to 80, clean A/B | no colour effect |
| E-0010 | 04.10 | 17 matrices muted | works |
| E-0011 | 04.10 | RGB-permutation tag matrices | slots mapped |
| E-0012 | 05.10 | v1 film matrices | works |
| E-0013 | 05.10 | v2 boost-compensated | works |
| E-0014 | 05.10 | v3 + E1 (zero Standard record) | table live |
| E-0015 | 05.10 | binary sector test | partly superseded |
| E-0016 | 05.10 | byte test group 0 | 4 hue regions |
| E-0017 | 05.10 | clean v3 baseline | ok |
| E-0018 | 05.10 | band test | pairs, no luma bands |
| E-0019 | 05.10 | v4 tables | overshoot |
| E-0020 | 05.10 | v5 scaled tables | accepted |
| E-0021 | 05.10 | `/setting/updater/mode` flag | failed |
| E-0022 | 05.10 | film curve k0 in p3 (38 sectors) | works |
| E-0023 | 06.10 | updater recon (read) | ok |
| E-0024 | 06.10 | insmod liro.ko in updater | refused |
| E-0025 | 06.10 | DRAM remanence 1 | no scene |
| E-0026 | 06.10 | DRAM remanence 2 (SF) | no scene |
| E-0027 | 06.10 | senser auth + readMemory | works |
| E-0028 | 06.10 | before/after dumps, sharp/SF pair | partial |
| E-0029 | 06.10 | av-cam in DRAM | located |
| E-0030 | 06.10 | writeMemory on display RAM | overwritten |
| E-0031 | 06.10 | YC_FULL after a frame | located |
| E-0032 | 06.10 | RAM patch 1 (SF off) | invalid |
| E-0033 | 06.10 | RAM patch 2 | lost |
| E-0034 | 06.10 | FileControl `/system` write | read-only |
| E-0035 | 06.10 | RAM detour 0xc3889760 | lost |
| E-0036 | 06.10 | FileControl probe all mounts | only p2 |
| E-0037 | 06.10 | updater-shell mount/PULL | refused |
| E-0038 | 06.10 | p3_grain (always-run hook) | no grain |
| E-0039 | 06.10 | p3_grain_sf (SF replaced) | crash |
| E-0040 | 06.10 | p3_diag (scratch stub) | fields read |
| E-0041 | 06.10 | session object + buffers | mapped |
| E-0042 | 06.10 | p3_sfwrap (SF then grain) | bottom only |
| E-0043 | 06.10 | p3_iso400 (SF skipped) | no grain |
| E-0044 | 06.10 | p3_stripe | bottom only |
| E-0045 | 07.10 | v2med | no grain |
| E-0046 | 07.10 | v3med | no blur, no grain |
| E-0047 | 07.10 | v4med + HC Mono control | no grain |
| E-0048 | 07.10 | v5med (rec40) | no grain |
| E-0049 | 07.10 | marker at rec40 | buffer not read |
| E-0050 | 07.10 | logger in `0xc3474800` | not called |
| E-0051 | 07.10 | logger in `0xc347427a` | handle only |
| E-0052 | 07.10 | NOP 0x2d4e0..0x2e608 | normal |
| E-0053 | 07.10 | NOP 0x249d0..0x25fa8 | normal |
| E-0054 | 07.10 | NOP 0x1c000..0x2ea68 | write hang |
| E-0055 | 07.10 | NOP 0xa598..0x1c000 | focus hang |
| E-0056 | 07.10 | NOP 0x13000..0x1c000 | normal |
| E-0057 | 07.10 | NOP 0xe800..0x13000 | black luma |
| E-0058 | 07.10 | NOP 0x10c00..0x13000 | overexposed |
| E-0059 | 07.10 | restore | ok |
| E-0060 | 09.10 | NOP 0x10c00..0x12520 | overexposed (2-4 stops) |
| E-0061 | 09.10 | NOP 0x12520..0x13000 | normal |
| E-0062 | 09.10 | NOP 0x11280..0x12520 | normal |
| E-0063 | 09.10 | skip overlay 0xf6c0 | hang |
| E-0064 | 09.10 | skip overlay 0xcbd0 | hang |
| E-0065 | 09.10 | skip overlay 0x105d0 | hang |
| E-0066 | 09.10 | restore | ok |

## Experiments whose conclusions must be revisited

- **R-1 (all NOP experiments, E-0052..E-0058, E-0060..E-0062).** `idt_cam` is 35 overlays (stub `5f50 5e50 5150 b100`; stack `+0x18`, entry `+0x1c`, load address page+0x10) mixing scalar code, literal pools, data tables and VLIW kernels. A NOP bundle executed as scalar code is garbage with branches (`dc3e` = `bfc`). Every range that touched scalar code ran random instructions; "black", "bright", "hangs" are indirect symptoms. Valid reading: negative results (normal frames) are more trustworthy; positive results do not localise a luma store. The Campaign A table (2nd half = encode, 1st half = develop+focus, e2a luma write, e2b tone) and the DSP grain target `0xe800..0x13000` are **not established**.
- **R-2 (E-0057, E-0058 vs E-0060).** The brightening is better explained by a corrupted statistics/AE overlay (`0x105d0`: reads lines, exports 5 accumulators + 64 B, no pixel write) than by a late luma-gain kernel; black luma in E-0057 may likewise be broken AE/stat (`0xf6c0` writes 2D blocks, probably an AE/AWB grid). Symptom severity differs between E-0058 (white screen, dies) and E-0060 (2-4 stops, saves hang). Mechanism not verified by any experiment.
- **R-3 (E-0063..E-0065).** The three overlay skips give identical symptoms; they only show "ARM waits for this overlay", nothing about what each computes.
- **R-4 (E-0042 sfwrap, E-0043 iso400, E-0044 stripe, and the README "proven working / grain visible" wording in `~/nex3n-dump/filmgrain/README.md`, `reference/nex3n-safe-test-boot.md` §4g, `grain-hook.md` before its banner).** The "bottom-up buffer" and "loop too slow" explanations were replaced by: `session[0x5e4]` was a live DMA buffer only on the early SF stage and is overwritten by the develop core; the bottom patch is a race artefact. The README's "iso800 proven visible (DSC09527)" is a mislabel: DSC09527 is the sfwrap +-31 frame; `p3_iso800` was never flashed.
- **R-5 (E-0045..E-0047).** Explanations "grain went into SF's input buffer" (v2), "window ate the grain" (v3), "JPEG quantisation / NR eats it" (v4) were all superseded by the amplitude-independence and marker results (E-0049).
- **R-6 (E-0049).** The marker conclusion assumed "Off = class 0/1" (shown only statically afterwards) and the frame labelling (DSC09548 listed as a marker frame although shot before the marker image) is inconsistent; re-shoot would settle it.
- **R-7 (E-0038).** "Gate `r4[0x3c] in {1,2}` is false for normal frames" is a guess; the per-frame call count of `0xc3889760` was never measured.
- **R-8 (E-0008/E-0009 and `reference/nex3n-firmware-hacking.md` "Состояние камеры на конец 04.10").** The note still says the `0x30106` ladder is modified and an A/B is pending; the A/B was done and 80 restored. The "ladder = sharpness" part is code reading only.
- **R-9 (E-0015).** The "6 groups = 6 hue sectors" decode was overturned by E-0016; the binary test only reliably shows record-slot binding.
- **R-10 (E-0019/E-0020).** Table gains are fitted on a few frames with +-8 dC / +-5 deg noise; the Phoenix cyan sign and the Sunset record marker (-128) behaviour are empirical, one frame each.
- **R-11 (E-0021).** Only one variant of the file-flag insurance was tried; "no software safety net" is slightly stronger than the evidence.
- **R-12 (E-0025/E-0026).** Remanence "closed" - the first frame was probably shot without the effect; the second used a coarse sweep (4 MB step, 256 KB samples) and may have missed a still pool.
- **R-13 (E-0022).** No flash log survives for the 05.10 curve write; its content is established indirectly (live read of av-cam curve region, identical md5 for `p3_fit.bin` and `current_p3.bin`).
