# G. Q-2: who resolves SA file-id -> path, how, what is checked

Date: 2026-10-09. Static analysis only (no camera access, nothing flashed, no image built).
Data: `~/nex3n-dump/safeboot/out3n/` (p3 `nflasha3_unpacked_unpacked`, p8 `nflasha8_unpacked_unpacked`,
p7 `nflasha7_unpacked`, p2 `nflasha2_unpacked`), Backup snapshot `~/nex3n-dump/work/sai/bk_post.txt`.
Tools: capstone 5 + pyelftools in `~/nex3n-dump/.venv` (scratch scripts, not kept).
Address conventions: `libObj.so` addresses are ELF VAs (= file offsets for `.text`; `.data` VA = file + 0x8000);
av-cam addresses are given as file offset and VA (base `0xc3441000`).

## TL;DR (first screen)

1. **Resolver = Linux userland, not av-cam/kernel.** The "On-Demand Loader" (ODL, Sony component
   `SADriver-OnDemandLoader_131H` in p7 `config.spec`) lives in **`/usr/lib/libObj.so`** (p8), class
   `InfraOnDemandLoader` / `Odl_Thread`, loaded into the appFw process **`im.elf`** (its strings name
   `libObj.so`, `libIMDB.so`). It reads all `0x00bd000x` tables with `Backup_read` (literal pool
   `0x2606c4`), looks up a request `(userid, prgid)` in `0x00bd0002`, builds
   `strncpy(prefix[slot], 64) + strncat(name[file-id], 32)`, `open()`s it, `fstat()`s the size, picks a DMM
   buffer class by size, then `open("/dev/mem")`, `mmap`s the buffer and `read()`s the file straight into it.
2. **The directory slot IS in `0x00bd0002`.** The atlas reading `[u16 file-id][u16 owner][u16 ref][u16 x]` is
   wrong in the third field: it is **`[u16 file-id][u16 userid][u8 prgid][u8 dir_slot][u8 mem_class][u8 0]`**.
   For SA modules userid = 0x93, prgid = codectype, slot = 0 (`/usr/sabin/`). Other rows use slots
   2 (`LensAberrationData.bin`), 3 (`dfe/dfe.bin`), 4 (`logo.bin`, `startsound.bin`, ...), 5 (`*_MAGIC.bin`),
   **6 (`/setting/psd.bin`, written by `CameraOnDemandSaver.so`)**, 7 (`DSC0000x.ARW`, `sanmon_input.bin`).
   Slot 1 (`/system/sabin/`) is used by no row (p3 `idt_cam`/`sa_dfdet` are loaded by Loader2, C-BOOT-002).
3. **Name table selection:** `0x00bd0007` maps the value of Backup `0x003e0003` to the name-table BKID;
   on this camera `0x003e0003 = 0x0301` -> `0x00bd0000` (not `0x00bd0006`).
4. **Debug block `0x00bd0003`** (all zero on this camera): byte 0 must be `0xbd` to enable any flag; byte 4 bit 0 =
   "mount `/dev/ms1` (vfat, the card) on the slot-7 path for slot-7 files"; byte 0xa bit 4 (+ byte 4 bit 0) =
   force **every** ODL file to slot 7 (Sony's "load all sabin from the card" route); byte 0xa bit 0 = ignore userid
   when matching; byte 9 bit 0 = load-time measurement. Slot 7 = `/usr/sabin/` so the card shadows the stock dir.
5. **Checks.** ODL (libObj): row must exist, `open` must succeed, `size + offset <= DMM unit size`
   (largest class in `0x00bd0004` = 1 MiB for mem_class 1), `read()` count must equal file size. **No magic,
   sum32, version, codectype or signature check in the ODL path.** av-cam (after load, on the buffer):
   function file `0x41168` (VA `0xc3482168`) checks **magic `aa0a1391` and container version byte +4 in {1,2,3}**
   (4 accepted only if byte +0xc < 0x50; anything else rejected, caller returns 0xd). **No sum32 check was found**
   in the code read (see "where searched").
6. **Verdict on "copy into `/setting/` + change a prefix":** changing the `/setting/` prefix (slot 6) does nothing
   for modules; changing slot 0 to `/setting/` redirects all 77 slot-0 files (every SA module + spica taps) and
   would break everything. **The narrow route is one byte: `0x00bd0002` row of the target file-id, byte +5
   (dir_slot) 0 -> 6.** For `sa_yknr` (file-id 74) that is byte offset **597** of `0x00bd0002`
   (row `4a00 9300 1c 00 01 00` -> `4a00 9300 1c 06 01 00`), path becomes `/setting/sa_yknr.bin`. A stock copy
   (53,508 B) fits p2 (~1.4 MB free). The module must keep `aa0a1391` + container version 2; sum32 apparently
   need not be fixed (not proven). Unknowns that matter before a test: when libObj re-reads `0x00bd0002`
   (table-loader call site not found; `odl_res` = WBI resume re-runs ODL init) -> plan a cold boot with WBI
   cleared; whether YKNR is in every still path (a missing file = ODL error -> YKNR OPEN fails -> capture
   sequence error, revertable by writing the byte back).

## 1. Evidence: ODL in libObj.so

File: `nflasha8_unpacked_unpacked/lib/libObj.so` (17,111,524 B, stripped ARM ELF, interpreter `/lib/libsonyld.so`;
imports `Backup_read`, `open`, `read`, `fstat`, `mmap`, `munmap`, `mount`, `umount`, `strncpy`, `strncat`).
Strings: `19InfraOnDemandLoader` (0xeb287e), `10Odl_Thread` (0xeb0397),
`[ODL][LOAD_PROG] <<< userid:0x%04x / prgid:0x%02x (Count 0x%02x) >>>` (0xe1933c), exports `odl_init`/`odl_res`/`odl_sus`
(0xca551d/25/2d). `im.elf` strings list `libObj.so` and `libIMDB.so`; `libIMDB.so` references `odl_init/odl_res/odl_sus`.

### 1.1 Table loader (0x260674, Thumb)
```
0x26067a ldr r0,=0xbd0002 ; Backup_read(0x00bd0002, obj+0x000)   800 B  rows
0x260686 ldr r0,=0xbd0001 ; Backup_read(0x00bd0001, obj+0x320)   512 B  prefixes
0x260692 movs r0,#0xbd; lsls r0,#16 ; Backup_read(0x00bd0000, obj+0x520) 3200 B names
0x2606a0 ldr r0,=0xbd0003 ; Backup_read(0x00bd0003, obj+0x11a0)   64 B debug flags
0x2606ac ldr r0,=0xbd0004 ; Backup_read(0x00bd0004, obj+0x11e0)  160 B size classes
0x2606b8 ldr r0,=0xbd0005 ; Backup_read(0x00bd0005, obj+0x1280)   64 B size classes (mem_class 2)
```
A second loader at 0x2605b0: `Backup_read(0x003e0003, sp)`; `0x26047e(obj, value)` reads `0x00bd0007`
(`movs r5,#0xbd; lsls #16; adds r0,r5,#7`), scans 8 records `[u32 match][u32 bkid]`, returns bkid of the matching
record, default `0x00bd0000`; then `Backup_read(that bkid, obj+0x520)` (names) and re-reads `0x00bd0003`.
`0x003e0003` in the snapshot = `01 03 00 00` = 0x0301 -> record `(01 03 00 00, 0x00bd0000)`.
Neither loader has a static caller (no BL/B.W/ARM BL/literal/PC-relative reference found) -> called indirectly.

Accessors (all take the table object): `0x26061e` name = obj+0x520+32*id; `0x26062a` prefix = obj+0x320+64*slot;
`0x2604f4/0x260502` bd0004[i].size/.unit; `0x260602/0x260610` bd0005[i].size/.unit; `0x3c0344` returns
`obj[0x11a0] == 0xbd` (debug gate) and guards every `0x00bd0003` flag accessor (0x260460, 0x2604b0, 0x2604d4,
0x260510..0x260590, 0x2605e4, 0x260636, 0x260654, 0x4d067c).

### 1.2 Row lookup (0x4a8160) - defines the row layout
```
loop r6 = 0..99: r5 = rows + 8*r6               (0x87fb3c)
  if bd0003 dbg && [0xa] bit0 : r7 = row.userid  (ignore userid)
  match: u16[r5]   != 0xffff
         u8 [r5+4] == prgid   (arg r2)
         u16[r5+2] == userid  (arg r1)
  -> copy row into the request (0x3e644c), log "Find! FILE_ID : %d"
     if bd0003 dbg && [4] bit0 && [0xa] bit4 : request.slot(+5) = 7
not found -> "!! Error: Not Found File_ID !!"
```
Request accessors: `0x4a8144` -> name(row.fid), `0x4a8150` -> prefix(row byte +5), `0x4a815c` -> row byte +6
(logged as `toMEM:`), `0x4a8220` -> (row byte +5 == 7).

### 1.3 Path build and open (0x4a7ac0, state 1 of the ODL state machine at 0x783a92)
Three request kinds, decided from the message:
- `[ DESIGNATE FILE LOAD ]` (message flag): `strncpy(buf, path_from_message, 0x60)` - full path in the message
  (this is how av-cam's hard-coded `/usr/sabin/spica_*_tap_step*.bin`, C-MOD-017, can be loaded).
- `[ MS_FILENAME LOAD ]` (kind 0x11): if bd0003 MS flag, `mount("/dev/ms1", prefix[7], "vfat")`, then
  `strncat(prefix[7], name_from_message)`.
- `[ LOAD PROG ID ]`: `0x4a8160(userid, prgid)`; `strncpy(buf, prefix[row.slot], 0x40)`; if bd0003 MS flag and
  slot == 7: `mount("/dev/ms1", buf, "vfat")`; `strncat(buf, name[row.fid], 0x20)`; mem_class = row byte +6.
Then `open(buf, 0x1000)` -> `file open OK/ERR` (err 0xfb33), `fstat` -> `FILE_SIZE:` (err 0xfb34/35), close and
`umount` on error. Error codes 0xfb31..0xfb37 belong to this function.

### 1.4 Buffer selection (0x4337d8, called at 0x783ada) and load (0x4a74bc, state 5)
- mem_class 1: first `0x00bd0004` entry with size >= file size (classes 4K, 32K, 64K, 96K, 128K, 192K, 256K,
  320K, 512K, 640K, 1M -> DMM units 0x1c3b..0x1c45); mem_class 2: `0x00bd0005` (320K -> 0x80001c42,
  512K -> 0x80001c43; the 10 audio codec rows); mem_class 3: unit 0x285 if size <= 256K. Larger -> `!! Error: Not Found
  UnitType !!` (0xfc21). Logs `Fix 1ST/2ND UNIT_TYPE`, then `DMM_OPEN UnitHandle`.
- `0x4a74bc`: `ProgramLoadAddress`/`ProgramLoadOffset`; `if size + offset > unit size -> "file size over!!"` (0xfc31);
  `open("/dev/mem", O_RDWR|O_SYNC)`; `mmap(.., PROT_READ|PROT_WRITE, MAP_SHARED, memfd, phys - pageoff)`;
  `read(fd, logicalAddr, size)`; `<< LOAD_DONE!! >>` if count == size else `<< LOAD_ERROR!! >>` (0xfb36);
  `munmap`, close, umount if mounted. No byte of the file is inspected.
- `check for replace: prgid=` (0x4a79a8, from the dispatcher 0x59d296 when a message flag bit 3 is set) only
  re-opens prefix+name to test existence ("file open OK/ERR for replace").

### 1.5 Corroboration
- `CameraOnDemandSaver.so` contains `/setting/psd.bin` and `/setting/` -> row 68 `psd.bin`, slot 6 = a real
  "save to /setting, load back through ODL" path; `/setting/` is a production ODL source, not only debug.
- av-cam strings: `Camera::Lens::ODL::LoadLensAberrationData` (row 56, userid 0xd, slot 2),
  `***** ARW File -> RAW, Copy Error!! (ODL %x Err) *****` (rows 47/48 `DSC0000x.ARW`, slot 7 = card),
  `Camera::HAPI::LoadBinary(ODL_HDL_CMD_MSG *)`, `Camera::Capture::ODL_LoadBinary(ODL_DESIGN_FILE_LOAD_CMD)`,
  `ODL_RES_MSG {err_code,msg_code,option,prg_num,timeout,prg_id,usr_unq_id,offset,unit_type} err`,
  `[CDIAG][CTRLCORE]memIdx[%d] fileId[%02d:%02d] unitHandle ... unitType ...`.
- All 89 non-empty rows decoded with the corrected layout:

| slot | prefix (`0x00bd0001`) | rows |
|---|---|---|
| 0 | `/usr/sabin/` | 60 x userid 0x93 (SA modules, prgid = codectype), 17 x userid 0xb6 (`dcv_psf_table`, 16 spica taps) |
| 1 | `/system/sabin/` | none |
| 2 | `/system/lensbin_lensproperty/` | 56 `LensAberrationData.bin` (0xd) |
| 3 | `/usr/` | 69 `dfe/dfe.bin` (0x13b, prgid 1) |
| 4 | `/usr/share/startbinary/` | 45 `startsound.bin`, 46 `logo.bin`, 77 `wireless_power_logo.bin` (0xbf) |
| 5 | `/usr/share/dspbin-mag/` | 65-67 `ba/os/proc_MAGIC.bin` (0x69) |
| 6 | `/setting/` | 68 `psd.bin` (0x13b, prgid 0) |
| 7 | `/usr/sabin/` (card mount point) | 47/48 `DSC00001/2.ARW` (0x3), 49 `sanmon_input.bin` (0xd1) |

mem_class (byte +6): 1 for 89 rows, 2 for the 10 audio codecs (dd51enc, aaclcenc, bd_lpcmenc, ac3dec, aaclcdec,
bd_lpcmdec, mp3dec, ac3enc_ac3dec, dd51enc_nr, aaclcenc_nr), 3 for row 78 (empty name, prgid 0xc4).
Files actually present: `logo.bin` in p8 `/usr/share/startbinary/`, `LensAberrationData.bin` in p3; `psd.bin`,
`startsound.bin`, `*_MAGIC.bin`, `dfe.bin`, `sanmon_input.bin`, `dcv_psf_table.bin` absent from the dumps.

## 2. Evidence: av-cam post-load header check

`av-cam.bin` (p3) file 0x41168 (VA 0xc3482168), Thumb:
```
ldr r2,[pc,#0x16c]     ; literal at file 0x412dc = bytes aa 0a 13 91 (module magic)
bics r0,(1<<30)        ; strip uncached alias bit
ldr r1,[r0]; cmp r1,r2 ; magic
ldrb r2,[r0,#4]        ; container version: 1,2,3 -> ok; 4 -> ok only if hdr(+0xc) < 0x50 (via 0x41260); else fail
```
Callers 0x499c8 and 0x49a82 (VA 0xc348a9c8/0xc348aa82): resolve a buffer handle (`0x16e568`), store it in a
32-entry table, call the check, on failure return 0xd. The per-version descriptor parsers sit at 0x40fb6/0x41090
(dispatch on byte +4: 2 -> 0x40d66/0x40e1e/0x40ee0, 3 -> 0x409fe/0x40b0c/0x40c30, 4 -> 0x40712/0x4083c/0x40916);
they copy image-table fields, no summing loop. This contradicts the note behind C-MOD-011 ("magic literal at
0x412dc is a message-object tag").

## 3. Claims

### G-MOD-001: The SA file-id -> path resolver is the On-Demand Loader in `/usr/lib/libObj.so` (Linux userland, appFw process `im.elf`): it reads `0x00bd0000..0x00bd0005` with `Backup_read`, builds `prefix[slot] + name[file-id]` with `strncpy`/`strncat`, and `open()`s the result
- status: verified-code
- evidence: libObj.so literal pool 0x2606c4..0x2606d7 (`0x00bd0002,1,3,4,5`) used by 0x260674; path build 0x4a7ba0..0x4a7c32 and 0x4a79ce..0x4a79fc; strings `InfraOnDemandLoader`, `[ODL][LOAD_PROG] <<< userid / prgid`; component `SADriver-OnDemandLoader_131H` in p7 `config.spec`; `im.elf` names `libObj.so`
- source: this extract §1
- date: 2026-10-09
- relates: supersedes C-MOD-010 (unknown); conflicts with C-MOD-010 evidence "no resolver in p8 ELF libraries"; supports C-MOD-009 (av-cam has no path builder)

### G-MOD-002: `0x00bd0002` rows are `[u16 file-id][u16 userid][u8 prgid][u8 dir_slot][u8 mem_class][u8 pad]`; row index = file-id; for SA modules userid = 0x93, prgid = codectype, dir_slot = 0
- status: verified-code
- evidence: lookup 0x4a8160 compares `u8[row+4]` with prgid and `u16[row+2]` with userid; `0x4a8150` passes `u8[row+5]` to the prefix accessor 0x26062a; `0x4a815c` returns `u8[row+6]` (used as buffer class at 0x783ada -> 0x4337d8); decoded slots in §1.5 match real file locations (`logo.bin` -> slot 4, `LensAberrationData.bin` -> slot 2)
- source: §1.2, §1.5
- date: 2026-10-09
- relates: corrects the field layout of C-MOD-006 (`ref` = prgid | slot<<8, `x` = mem_class); supports C-MOD-006 codectype match

### G-MOD-003: `0x00bd0007` maps Backup `0x003e0003` to the name-table BKID; this camera has `0x003e0003 = 0x0301`, so names come from `0x00bd0000` (slot 23 = `sa_apollo4.bin`), not `0x00bd0006`
- status: verified-code
- evidence: libObj 0x2605b0 / 0x26047e; snapshot `003e0003 = 01030000`
- source: §1.1
- date: 2026-10-09
- relates: makes C-MOD-008 "revision selector" meaning verified; C-MOD-007

### G-MOD-004: `0x00bd0003` is an ODL debug block gated by byte 0 == 0xbd: byte 4 bit 0 mounts `/dev/ms1` (vfat) on the slot-7 path for slot-7 loads; byte 0xa bit 4 (with byte 4 bit 0) forces every ODL file to slot 7; byte 0xa bit 0 ignores userid in the match; byte 9 bit 0 enables load-time statistics; other bits unknown. Snapshot value is all zero (off)
- status: verified-code (flags 4.0, 0xa.0, 0xa.4, 9.0); unknown (others)
- evidence: gate 0x3c0344; 0x4d067c (byte 4 bit 0) -> mount at 0x4a7bd8/0x4a7b58, umount 0x4a7cd4/0x4a7768; 0x2604b0 -> `strb 7,[req+5]` at 0x4a81ae; 0x260590 at 0x4a817a; 0x260654 around `read` at 0x4a75e0/0x4a7620 with `Load Time`/`Load Count` logs
- source: §1.1-1.4
- date: 2026-10-09
- relates: C-MOD-008

### G-MOD-005: Slot 7 (`/usr/sabin/`) is the card mount point; slot 6 (`/setting/`) is a production ODL source used by `psd.bin`, which `CameraOnDemandSaver.so` writes to `/setting/psd.bin`
- status: verified-code
- evidence: 0x4d069a returns prefix[7] as mount target; rows 47-49 slot 7; row 68 slot 6; `CameraOnDemandSaver.so` strings
- source: §1.3, §1.5
- date: 2026-10-09
- relates: C-PART-004, C-PART-013

### G-MOD-006: The ODL load path does no content check: it requires a matching row, a successful `open`, `size + offset <= DMM unit size` (max class 1 MiB for mem_class 1, 512 KiB for mem_class 2, 256 KiB for mem_class 3) and a full `read()`; it reads the file through `/dev/mem` directly into the DMM buffer
- status: verified-code
- evidence: 0x4337d8 (class choice, error 0xfc21), 0x4a74bc (`file size over!!` 0xfc31, `/dev/mem`, `mmap`, `read`, `LOAD_DONE/LOAD_ERROR`)
- source: §1.4
- date: 2026-10-09
- relates: makes the size part of C-MOD-011 verified; C-MEM-003

### G-MOD-007: av-cam validates a loaded SA image by magic `aa0a1391` and container version byte (+4 in {1,2,3}; 4 only with byte +0xc < 0x50; others rejected with result 0xd); no sum32 check was found in this path
- status: verified-code (magic/version); hypothesis (no sum32 anywhere)
- evidence: av-cam file 0x41168 (VA 0xc3482168), literal 0x412dc, callers 0x499c8/0x49a82; version dispatch 0x40fb6/0x41090
- source: §2
- date: 2026-10-09
- relates: conflicts with C-MOD-011 ("no ... header-version check on the ARM side", "magic literal is a message-object tag"); narrows C-DSP-029 (v5 header is rejected by this check, v4 conditionally accepted)

### G-MOD-008: Requests also carry full paths (`[ DESIGNATE FILE LOAD ]`) or card file names (`[ MS_FILENAME LOAD ]`); the hard-coded spica tap paths in av-cam fit the designated-path kind
- status: verified-code (kinds in libObj); hypothesis (spica uses it)
- evidence: 0x4a7b00..0x4a7b90 strings and `strncpy(buf, msg_path, 0x60)`
- source: §1.3
- date: 2026-10-09
- relates: C-MOD-017

### G-MOD-009: An av-cam OPEN of codectype N reaches ODL as a `LOAD PROG ID` request (userid 0x93, prgid N)
- status: hypothesis
- evidence: 60 owner-0x93 rows with prgid = header codectype (32/32 present files); the ODL log prints userid/prgid; av-cam `ExecuteOpenMSG` (0x314340) sends codectype only to another task (0x3322d0); the hop from that task to the ODL message was not traced
- source: §1.5; C-MOD-004
- date: 2026-10-09
- relates: C-MOD-003, C-MOD-004

### G-MOD-010: Pointing one module at `/setting/` needs one Backup byte: `0x00bd0002` offset `8*file-id + 5` set to 6 (for `sa_yknr`, file-id 74: offset 597, `00` -> `06`); changing a prefix in `0x00bd0001` is either useless (slot 6) or redirects every slot-0 file (slot 0)
- status: hypothesis (derived from G-MOD-001/002/006/007; not run)
- evidence: §1.2-1.4; p2 has ~1.4 MB free (dump 1.5 MB used of 3 MB); `sa_yknr.bin` = 53,508 B
- source: this extract, TL;DR 6
- date: 2026-10-09
- relates: answers Q-2 route; C-MOD-010; C-SAFE-*

### G-MOD-011: When libObj (re)reads the `0x00bd000x` tables is unknown: the loaders 0x260674/0x2605b0 have no static caller; `odl_init` and `odl_res` (WBI resume) both enter the ODL init at 0x783ce0
- status: unknown
- evidence: BL/B.W/ARM-BL/literal/PC-relative scans of libObj for 0x260674/0x2605b0 = 0 hits; `odl_init`/`odl_res` -> 0xabe0c4 -> 0x12d073 -> 0x3283cc -> 0x783ce1, `odl_sus` -> 0x783a11
- source: §1.1
- date: 2026-10-09
- relates: C-BOOT-017..019 (WBI), Q-19

## 4. Verdict for "copy the module to /setting and repoint"

- Will it be picked up: by the code read, yes, if `0x00bd0002` row byte +5 of that file-id is 6 and
  `/setting/<name from 0x00bd0000>` exists, is <= the size classes, starts with `aa0a1391` and container
  version 2 (3N processing modules). Nothing checks sum32/codectype/signature on the way that was found.
- Which slot to change: none of the prefixes. Change the row's dir_slot byte (narrowest, one file-id).
  Optional extra isolation: also rename `0x00bd0000[file-id]` (e.g. `sa_yknr_t.bin`) so a stray stock file is never
  matched; not needed since the directory differs.
- What breaks along the way: only loads of that file-id. If the file is missing or rejected, ODL/av-cam errors
  (0xfb33 / 0xd) -> that effect's OPEN fails -> capture sequence error (C-MOD-011 failure path). Writing the byte
  back from the updater (`bk w`) reverts it; the stock `/usr/sabin` copy is untouched.
- Do not: set `0x00bd0001` slot 0 to `/setting/` (all 77 slot-0 files; the present p8 `/usr/sabin` set is 3.9 MB, exceeds p2); enable
  `0x00bd0003` byte 0xa bit 4 (everything from the card); use slot 7 with the card unless needed (mounts the
  card over `/usr/sabin/` during the load; behaviour with the media stack holding the card is unknown).
- Before a test: (a) find when the table is read (G-MOD-011) or plan a cold boot with WBI zeroed after the
  `bk w` + sync; (b) first test with a byte-identical stock copy (as Q-2 proposes); (c) confirm the YKNR OPEN is
  actually exercised by the test shot (C-MOD-012 lists yknr as having an OPEN site).

## 5. Where searched (for the negative results)

- Byte search for aligned/unaligned LE and BE `0x00bd0000..0x00bd0007` over every file in p3 (incl. `vmlinux.bin`,
  `initrd.img` and all 33 initrd `kmod/*.ko`: liro, unidrv1/2, mcmn_drv, dmm, upm, ...), p8 (`bin/`, `lib/`,
  `scenario/`, `share/`, `sabin/`) and p1 initrd: the only aligned hits that form a table loader are in
  `libObj.so`; other hits are noise (fonts, spica tap data, single unaligned bytes).
- `grep -a sabin`: only `av-cam.bin`, `Backup.bin/.bak`, `kemco.txt`, p7 `config.spec`; no kmod, no kernel.
- `grep -a 'ODL_|OnDemand|odl_'`: `av-cam.bin`, `libObj.so`, `libIMDB.so`, `CameraOnDemandSaver.so`; nothing in kmods.
- `liro.ko` strings: only av-cam loader + `API support list: OSAL, Backup 2` service table; no file-id logic.
- Magic `aa0a1391` (both byte orders) in all non-sabin files: only av-cam file 0x412dc.
- sum32: not searched exhaustively in av-cam; absent from the ODL path and from the av-cam check/dispatch
  functions listed in §2. SA-DSP runtime (`idt_cam`, `ssboot*`) not examined for a self-check.
- Not traced: the av-cam task that turns an OPEN (C-MOD-004) into the ODL request (G-MOD-009); the indirect caller
  of the libObj table loaders (G-MOD-011); unknown `0x00bd0003` bits.
