# NEX-3N: ARM <-> DSP module interface (`sa_*.bin`), module loading and effect parameters

Static analysis only. Nothing was written to the camera. VLIW microcode is covered separately (notes/sony-dsp-isa.md, section 10). Context: notes/sony-dsp-isa.md, notes/sony-dsp-generations.md, README.md.

Inputs: the `av-cam` application binary (Thumb-2, load base `0xc3441000`), the root filesystem, and a Backup (user-settings store) export. Addresses below are **file offsets inside av-cam** (VA = `0xc3441000` + offset). Tools in `code/sai/`:
- `avx.py`: xref helper for av-cam (literals, BL, ADR, function names recovered from `__PRETTY_FUNCTION__`);
- `scanimm.py`: search for constants in ARM/Thumb immediates.

## 0. Summary
- **Soft Focus is tunable through Backup: property `0x0003010a`** (256 B, attr `08`, same class as `0x00030106`, which has already been edited on the camera). Strength for three levels: bytes `+0..+8`. Forced level: `+9`. Four convolution kernels at `+0x10`, `+0x30`, `+0x50`, `+0x90`. Both code paths read the block: capture (`Stage_SoftFocus`) and effect preview (`HapiSFTFCS`). **These numbers are not present in av-cam's constant tables.** See section 2.
- **Miniature is also tunable through Backup: property `0x00030109`.** It holds band offsets for three modes, two 24-point blur-profile tables per mode, three fields forwarded to the DSP, and a forced-zone byte at `+0x13`. See section 3.
- **Correction to notes/sony-dsp-isa.md section 9.** The claim "av-cam references `0x00bd0000` 12 times and builds a path as prefix + name" **does not hold**. All 12 hits are unaligned bytes inside tables of sequential IDs (`...b9 00 / ba 00 / bb 00 / bc 00 / bd 00...`), not BKIDs. Searched aligned literals, ARM and Thumb immediates, `movt`, and the `movs #0xbd; lsls #16` pair. No code that builds BKID `0x00bd000x` exists in av-cam, `liro.ko` and other kernel modules, the kernel, or rootfs ELF libraries. av-cam opens a module **only by codectype** (section 1).
- **Table `0x00bd0002` decoded and verified against all files.** It maps `(owner, codectype) -> file-id`. Its `ref` field equals header byte `+9` for all 32 `sa_*.bin` modules in rootfs. For the 16 spica tables it equals the IDs av-cam places into `SPICA_START_PARAM`. Table `0x00bd0007` selects the name table by chip revision: `0x00bd0000` or `0x00bd0006`. They differ only in entry 23: `sa_apollo4.bin` vs `sa_apollo4_es10.bin`.
- **Open: where the path prefix is chosen, whether there is an integrity check, and what the size limit is.** There is no "file-id -> path" resolver in ARM code. It is either on the SA runtime side or builds IDs dynamically in a way not visible statically. `0x00bd0002` has no "directory slot" field (1.4).

## 1. Module loading

### 1.1 What av-cam does (verified)
Soft Focus chain (file offsets):

| Step | Function | Action |
|---|---|---|
| `Stage_SoftFocus` | `0x3a9898` | builds a 0x18-byte struct, calls preinit -> param copy -> start -> release |
| `sa_func_SFTFCS_preinit` | `0x1635d8` | `SaFuncDrvCmn` init -> **`ExecuteOpenMSG(obj, &chan, 0x18)`** -> gets module shared memory -> lays out sub-buffer pointers |
| `SaFuncDrvCmn::ExecuteOpenMSG` | `0x314340` | OSAL message: `[8]=0x14` (length), **`[9]=0x21` (OPEN)**, `[0xa]`=own task id, **`[0x11]`=codectype**; send `0x3322d0`, wait for reply **`0x22`**, channel returned in `*r1` |
| `sa_func_SFTFCS_start` | `0x1637ca` -> `0x163868` -> `0x3144de` | fills param block (2.2), then `ExecuteCalcStartMSG`: `[9]=0x41` (START), param address = bus(base)+0x80 |
| release | `0x1636ec` -> `0x3142ca` | `ExecuteCloseMSG` |

- **OPEN carries no path, no file-id, no BKID. Only codectype** (`0x18` = header byte `+9` of `sa_sftfcs.bin`).
- All `ExecuteOpenMSG` calls with a constant codectype: `0x01 03 04 05 06 07 0b 0d 0e 0f 10 11 16 17 19 1a 1b 1c 1e`, plus `0x18` from preinit. A separate OPEN builder at `0x4dc16e` opens `0x0a` (sweep_panorama). Another builder at `0x1321b6` has no callers.
- No builder of the `0x22` reply exists in av-cam (no `movs #0x22; strb [x,#9]` pattern). OPEN is serviced elsewhere (hypothesis: resident SA OS or a liro/Linux service).
- av-cam's service table (`*(base+0x14)` = `0xc34414d0`, file `0x4d0`) is empty in the image and filled at runtime. `Backup_read` and OSAL go through `liro.ko`, which imports `Backup_read/...` and `filp_open`.
- At startup `fn_ad0` (around `0xcba`) calls service `table+0x180` for the list of Backup subsystems, **which includes `0xbd`**. av-cam knows subsystem 0xbd, but no code reading a specific ID from it was found.

### 1.2 Subsystem `0x00bd` tables (data verified, consumer not found)
| BKID | Size | Contents |
|---|---|---|
| `0x00bd0000` | 3200 = 100x32 | base names, index = file-id (`sa_sftfcs.bin` = id 55, offset 0x6e0) |
| `0x00bd0006` | 3200 | copy, differs only at id 23: `sa_apollo4_es10.bin` |
| `0x00bd0001` | 512 = 8x64 | prefixes: 0 `/usr/sabin/`, 1 `/system/sabin/`, 2 `/system/lensbin_lensproperty/`, 3 `/usr/`, 4 `/usr/share/startbinary/`, 5 `/usr/share/dspbin-mag/`, 6 `/setting/`, 7 `/usr/sabin/` |
| `0x00bd0002` | 800 = 100x8 | `[u16 file-id][u16 owner][u16 ref][u16 x]` |
| `0x00bd0007` | 64 | `(1,3)->bd0000, (1,4)->bd0000, (0,3)->bd0006, (0,4)->bd0006`: name-table selection by revision (hypothesis: first byte = MP/ES) |
| `0x00bd0004` | 160 | `(size, id)` pairs: 4K, 32K, 64K, 96K, 128K, 192K, 256K, 320K, 512K, 640K, **1M** -> `0x1c3b...0x1c45` (hypothesis: load-buffer classes; the largest module `sa_star` is 463 KB) |
| `0x00bd0005` | 64 | `(0x50000, 0x801c4200)`, `(0x80000, 0x801c4300)` (purpose unknown) |

`owner` field in `0x00bd0002`:
- `0x93`: all `sa_*.bin`, processing and codecs. **`ref` = header byte `+9`, 32/32 match.**
- `0xb6`: spica tables, `ref` = 0x10...0x1f. `0xb6` is the SaFuncDrv log-module ID (`movs r0,#0xb6` in `sa_func_*` error paths). av-cam (`0x30576c`) puts an ID pair into `SPICA_START_PARAM` (e.g. still step1 = `0x19/0x18`) and also **a full hardcoded path `/usr/sabin/spica_...bin` (up to 0x60 bytes)**.
- `0xbf`: `logo.bin`, `startsound.bin`.
- `0x0d`: `LensAberrationData.bin`.
- `0x69`: `*_MAGIC.bin`.
- `0x13b`: `psd.bin`, `dfe/dfe.bin`.

`x` field: 1 almost everywhere, 2 for audio codecs, 3 for one unnamed entry (78).

### 1.3 Integrity, limits, failure
- **No content check of the module was found on the ARM side.** Magic `aa0a1391` (u32 `0x91130aaa`) appears as a literal once (`0x412dc`, function `0x41168`), unrelated to loading. No sum32-trailer computation tied to loading. av-cam does not read header version or core mask either: it never sees the file. **Whether checks exist is unknown**; they are done by whoever actually loads the file.
- Size limit: no direct data. Hypothesis: `0x00bd0004` (<= 1 MB).
- Failure path (verified for Soft Focus):
  - OPEN error -> `ExecuteOpenMSG` returns 1 -> preinit returns 2/6 -> `Stage_SoftFocus` (`0x3a9966` -> `0x3a9b80`) logs and returns `ESequenceResult` 2;
  - start error -> 5;
  - **no fallback to a CPU path or to "no effect" exists in this code.** What happens to the shot is up to the calling sequence (not analysed).

### 1.4 Prefix selection for `sa_sftfcs` (not established)
- From the data: file-id 55 -> name at `0x00bd0000+0x6e0` (or `0x00bd0006+0x6e0` if `0x00bd0007` selects the ES table).
- Prefix for owner `0x93` should logically be slot 0 or 7 (`/usr/sabin/`), since all such files live in rootfs `sabin`. **But no field setting it exists in `0x00bd0002` or in av-cam code.**
- Slot 1 (`/system/sabin/`): the application partition contains `sa_dfdet.bin` (md5 identical to the rootfs copy), plus `ssboot*.bin` and `idt_cam.bin`.
- **"Edit the prefix -> loads `/setting/...`" cannot be confirmed statically. Do not rely on it.**

## 2. Soft Focus: parameters and mailbox

### 2.1 Parameter source = Backup `0x0003010a` (verified)
- BKID<->RAM pair: `0x0003010a` <-> `0xc3acd7dc`, from av-cam's parallel arrays (`0x61d1dc` BKID x2, `0x61d784` RAM; the same table used for the BKID->RAM map in code/bkparams). The same mechanism was already confirmed on camera by editing `0x00030106`.
- **Two** readers:
  - `0x465cf8` (called from `Stage_SoftFocus` via `0x465d7e`, capture path);
  - `HapiSFTFCS` `0xa6b82` (ReviewEffect/HAPI path, request `0x5008`).
- Layout (stock value):

| Offset | Value | Destination |
|---|---|---|
| `+0x00..+0x02` | `16 1a 00` | level **2** -> param `+0x28`, `+0x2c`, `+0x34` |
| `+0x03..+0x05` | `0e 18 08` | level **1** |
| `+0x06..+0x08` | `06 16 10` | level **0** |
| `+0x09` | `00` | forced level: `0x10/0x11/0x12` -> 0/1/2. **Only honoured on the capture path (`0x465d30`); HAPI ignores it** |
| `+0x10..+0x21` | 9 x u16: `1c 1c 1c / 1d 1e 1d / 1c 1c 1c` | 3x3 kernel -> sub-buffer `base+0x100` |
| `+0x30..+0x41` | 9 x u16: `9 65 9 / 10 70 10 / 9 65 9` | 3x3 kernel -> `base+0x140` |
| `+0x50..+0x81` | 25 x u16, 10...12 | 5x5 kernel -> `base+0x180` |
| `+0x90..+0xc1` | 25 x u16: `0 16 17 16 0 / 0 16 19 16 0 / 0 17 22 17 0 / ...` | 5x5 kernel -> `base+0x1c0` |
| `+0x42..+0x47`, `+0x84..+0x8b` | zeros | **read by SPICA** (`0x3069b4`, `0x305f84`: resize/zoom). Not Soft Focus fields; do not touch |

- Meaning of the three level bytes ("radius", "strength", "area") and of the kernels is a **hypothesis**. The first byte grows 6 -> 14 -> 22 from level 0 to 2, so level 2 is probably "High". The level comes from byte 0 of `PRM_REQ_FILTER_SOFT_FOCUS`. In libObj, `CamMsgConv` maps PARAMID `0x297/0x298/0x299` -> 0/1/2. Low/Mid/High names are not statically bound.
- **Practical conclusion:** the best candidate for a reversible experiment, since Soft Focus changes without touching firmware. Only touch the bytes in the table above and avoid the SPICA zones. Values are loaded into RAM at boot, so (as with `0x30106`) a reboot is needed.

### 2.2 SFTFCS module param block (verified from ARM code)
`base` = module shared memory (`fn_330514`); the DSP receives `bus(base)+0x80`.

| Field (from `base+0x80`) | Writer | Contents |
|---|---|---|
| `+0x00/+0x04/+0x08` | start `0x163868` | bus addresses of three image buffers (from three u16 handles). 128-byte alignment check (`lsls #0x19`), else error 6 |
| `+0x0c/+0x10/+0x14/+0x18` | preinit (`base+0x100/140/180/1c0`), converted to bus addresses by start | pointers to the four kernels (2.1) |
| `+0x1c` | start | word from input struct `+8`, 16-byte alignment check |
| `+0x28/+0x2c/+0x34` | `0x465cf8` / HAPI | the three level bytes |

preinit input struct (0x18 bytes, `Stage_SoftFocus`):
- `+0`: u8;
- `+4/+6/+8`: u16 handles in/out/work;
- `+0xc` = `ctx+0x3e60`, `+0x10` = `ctx+0x3e64` (width and height, used the same way by TBOX);
- `+0x14` = `ctx+0x3e50` (hypothesis: line stride).

Outgoing mailbox: `SA_MBX_0123`; four words logged as `sftfcs_start_mbx.cha_mbx0..3`. Meaning (SAID/CmdCode/OsalID/ParamAddress) inferred from log strings, not verified field by field.

## 3. Miniature (TBOX): parameters (verified)
- HAPI request `0x5007`, wrapper `Start_Miniature` `0xa275c`, `HapiTBOX` `0xa2852`, param fill `0xa2efc`. Codectype `0x17` is opened at `0x1626e6`.
- Source: **Backup `0x00030109`** <-> RAM `0xc3acd6dc`. Also read by `0x308020` and `0x3085ae` (possibly LiveView preview; not analysed).

| Offset | Value | Meaning |
|---|---|---|
| `+0x00/+0x02` | `0x333/0x333` | band offset (horiz./vert.) for mode 2 (`ImageParam+0x34` != 0, 1) |
| `+0x04/+0x06` | `0x333/0x333` | mode 0 |
| `+0x08/+0x0a` | `0x333/0x333` | mode 1 |
| `+0x0c/+0x0e` | 242 / 166 | -> param `+0x52/+0x54` (u16) |
| `+0x10` | `0x80` | -> param `+0x56` |
| `+0x11/+0x12` | `0x28/0x3c` | -> param `+0x1a/+0x1e` |
| `+0x13` | `00` | forced zone: `0x11...0x16` -> internal code 4, 5, 6, 1, 2, 3 |
| `+0x20/+0x38` | 2 x 24 bytes | blur profile for mode 2 (horiz./vert.) |
| `+0x50/+0x68` | 2 x 24 | mode 0 |
| `+0x80/+0x98` | 2 x 24 | mode 1 |
| `+0xb0..+0xff` | 5 x 16 | not read by this function |

- Boundary computation: `pos[i] = clamp((tbl[i]*dim + 128) >> 8 +/- offset, 0, dim)` for i = 0...23. First 12 points as is, second 12 reversed, giving 24 u16 at param `+0x20..+0x4f`. Orientation (0 = horizontal band across height, 1 = vertical across width) -> `+0x50`.
- Zone from `PRM +0x12`: 1 -> horizontal centre, 2 -> vertical centre, 3/4 -> vertical -/+ offset, 5/6 -> horizontal -/+ offset, 0 = auto (by `ctx+0x2336`). Mapping to menu items not established.
- Conclusion: Miniature's transition "width" and "softness" come from tables `+0x20...+0xaf`; zone shift from `+0x00...+0x0b`. Also a Backup-edit candidate.

## 4. Picture Effect map
Effect index order in av-cam comes from libObj `CamMsgConv` (`0x953de8`), which maps PARAMID to index:

| PARAMID | Index |
|---|---|
| `0x279...0x27f` | 0...6 |
| `0x280` | 7 |
| `0x281...0x284` | 8...0xb |
| `0x327` | 0xc |
| `0x328` | 0xd |

Names in menu order **(hypothesis)**: 0 Off, 1 Toy, 2 Pop, 3 Posterization, 4 Retro, 5 Soft High-key, 6 Partial Color, 7 HC Mono, 8 Soft Focus, 9 HDR Painting, 0xa Rich-tone Mono, 0xb Miniature, 0xc Watercolor, 0xd Illustration. Watercolor and Illustration sit in a separate range, as later additions.

| Effect | Path | Parameters | Status |
|---|---|---|---|
| Soft Focus | **DSP `sa_sftfcs` (0x18)**: `Stage_SoftFocus` / `HapiSFTFCS` | Backup `0x0003010a` | verified |
| Miniature | **DSP `sa_tbox` (0x17)**: `HapiTBOX` | Backup `0x00030109` | verified |
| HDR Painting | `Start_Art_Effect` `0xa52b8` (request `0x500c`, 3 frames: target + 2 ref, `effectLevel`) | not found | no direct `sa_func_*` calls in the wrapper; executor unknown |
| Rich-tone Mono | `Start_Richtone_Monochrome` `0xa5ffa` (`0x500d`, 3 frames) | not found | same |
| Toy, Pop, Posterization, Retro, Soft High-key, Partial Color, HC Mono | no SA wrappers, modules or strings of their own; YC stages log `picture_effect` (`YAP:`, `NR:`) | probably YC/ISP blocks of subsystem 0x0003, not located | hypothesis: pure ISP/YC |
| Watercolor, Illustration | indices 0xc/0xd exist, no module | - | not checked in the 3N menu |

## 5. Unused and duplicate modules
| File | Codectype | Evidence | Conclusion |
|---|---|---|---|
| `sa_test_intr_c0a.bin` (3.5 KB) | `0x28` | no OPEN with 0x28, no strings or wrapper; the module prints `*** START !! ***` | **best "never loaded" candidate** |
| `sa_fc_recog.bin` | `0x13` | no OPEN with 0x13, no `fc_recog` strings; av-cam contains source name `recog_sa_drv.cpp` but no references | probably unused (medium confidence) |
| `sa_shapep.bin` | `0x21` | no OPEN, no strings | probably unused (medium) |
| `sa_dfdet.bin` | `0x02` | **duplicate**: `/system/sabin` and `/usr/sabin`, identical md5 | used (ZIT/face detection) |
| `spica_magnifier_plus_*` (4) | - | not in `0x00bd0002`; av-cam loads them by path with ID `0xff` | used (magnifier) |
| `sa_defect` (0x14), `sa_zima_*`, codecs | - | no static OPEN, but they have their own managers (`ZIT_SaOpen`, `EncPinSaMgr`, `ZIMA`) | treat as used |

- Conversely, av-cam opens codectypes `0x03 04 05 06 07 0b 0d 0e 11 1b 1e` (clearvid, bayer, dcv, one_shot_3d, kdz, bfnr, boks, ssp, contplus, nflash2, ddt). **No files exist for them in rootfs**; these features are dead on the 3N.

## 6. Verified / hypotheses / not done
**Verified:**
- OPEN/START/CLOSE path in av-cam and OPEN message format;
- opening by codectype only;
- semantics of `0x00bd0002` (32/32 modules + 16 tap tables), `0x00bd0006`/`0x00bd0007`;
- absence of `0x00bd000x` constants in the code of all ARM binaries;
- layout and consumers of `0x0003010a` and `0x00030109`, including SPICA fields inside `0x0003010a`;
- PARAMID -> effect index in libObj.

**Hypotheses:**
- who resolves file-id -> path and selects the prefix;
- whether a sum32 check and a 1 MB limit exist;
- meaning of the three level bytes and the kernels;
- mapping of levels 0/1/2 to Low/Mid/High;
- effect index names;
- "pure ISP" for the seven effects.

**Next steps (static):**
- find the `picture_effect` stages in YC (`0xd4334`, the function with `NR:picture_effect`) and tie indices 1...7 to `0x0003...` blocks;
- analyse the capture-sequence step table at `0x1e8aa4`: it calls `Stage_SoftFocus` and other per-effect capture stages.
