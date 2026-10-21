# E. Web research: prior art for NEX-3N (CXD4132) SA-DSP / av-cam / Backup work

Date: 2026-10-09. Scope: public sources only, read-only. Builds on `reference/sony-hack-prior-art.md` (05.10.2026), so ma1co/SA-DSP, ma1co/qemu, OpenMemories-Symbols, OpenMemories-CI, steelcnn/nex-hack, EOSHD a7 IV, Magic Lantern, CHDK, fwtool PR #52/#55 are NOT repeated here.
Every link below was actually opened (WebFetch, `gh` API or a local clone). Search-engine snippets alone were not trusted (see "Corrections").
Web search itself is weak for this niche: the useful hits came from the GitHub API and from cloning sources.

## TOP 5

1. **GPL kernel source of the NEX-3N itself contains a working example of "firmware file -> coprocessor via mailbox"** (`arch/arm/mach-cxd4132/cmpr.c` + `include/mach/cmpr.h`). Same pattern as `liro.ko` and the SA-DSP engine: module param `path=` names a firmware file, `cmpr_load_file()` reads it into a reserved RAM area, its physical address is written to the `CMPR_CMN_IPC` register, arguments go through mailbox registers `MBX0..3`, status through `IMSR`/`IENR`, clock/reset through `CKEN`/`XRST`. Relevance: high. See finding A1.
2. **Sony-PMCA-RE issue #597 (RomanHargrave, 10.02.2025): description of how `liro.ko` loads `av-cam.bin`**, including the `av-cam.bin` header structure, the sysfs parameter with the load address and the claim that `Backup_read` is a thunk through a table outside the image. Relevance: high. See B1.
3. **A published 010 Editor template of the Backup.bin container** (gist `RomanHargrave/9b7a194ee166972b3c21b892df126bf5`, `ILCE-BK4.bt`): header fields (magic, cookie, revision, numSubsystems, dataOffset, dataSize, **checksum**), subsystem table, property flags, `SS_SENSER_UDTR = 0x004B`, `0x00BD0006 = "MYSTERY_BIN_LIST_2"`. Relevance: high for the 0x00bd question. See B2.
4. **Backup defaults live in the firmware installer and are re-applied on factory reset** (mungewell in issue #249, 22.07.2021) plus the RAM-only semantics of `Backup_write` (ma1co, fwtool #6, already known). Together this is a recovery path for experiments on 0x0003xxxx: a factory reset should restore the stock colour tables. Relevance: high (safety). See B5. Not verified on the 3N.
5. **NEX-3N does NOT support PlayMemories Camera Apps, verified from the source.** `fwtool.py/devices.yml` has `NEX-3N: arch: CXD4132, model: 0x31030022` with NO `apps` key, while NEX-5R/5T/6 have `apps: '1.1'`. Sony's own list (support article 00289030) also names NEX-5R/5T/6, not the 3N, but that page returned 403 to WebFetch, so that half comes from a search snippet only. Relevance: high (closes a whole branch). See D1.

---

## A. SA modules, liro, zima/spica, loader of SA modules

### A1. GPL source: `cmpr.c` (compressor coprocessor driver) in the NEX-3N kernel
- URL: https://prodgpl.blob.core.windows.net/download/DI/NEX-3N/linux-kernel.tar.gz (linked from oss.sony.net/Products/Linux/DI/NEX-3N.html). 33.5 MB, I downloaded and unpacked it. Files: `linux/arch/arm/mach-cxd4132/cmpr.c`, `linux/arch/arm/mach-cxd4132/include/mach/cmpr.h`.
- What is there:
  - Three compressor cores. Per-core clock/reset registers `0xf50000b0/0xf50002b0` (CMPR1), `0xf50000c0/0xf50002c0` (CMPR2), `0xf5000130/0xf5000330` (CMPR3). Common block `0xf50a0000`, `0xf50b0000`, `0xf50c0000`; core block = common + 0x100.
  - Two firmware images selected by `firmid`, loaded from files named by module parameters `path` and `path2` (`cmpr_load_file`), placed in a region given by `mem=`. The log message "ERROR:WBI:cmpr.path is not specified" shows the files come from the WBI snapshot boot path.
  - Start sequence (`cmpr_deflate`): fill a 128-byte-aligned `struct cmpr_parg {src_adr, dst_adr, work_adr, input_size, blk_bits, index_len}`; write `0x80000000 | (addr & 0x3fffffff)` of the firmware binary into `CMN_IPC`; write the physical address of `parg` into `COR_MBX(0)`; clear MBX1 and MBX3; write `0xff` to `IMSR`, `0xff` to `IENR`; set `CKEN` and `XRST` to 1. Cancel = `MBX3 = 1`. Done flag = `IMSR & 1`.
  - It handles `LZPT` ("TPZL"/`CMPR_LZPART_MAGIC`) with 64 KiB (`blkbits 16`) default 17 and a 10-entry index. So the **LZPT compressor/decompressor is itself a firmware-driven hardware core** (relevant to our LZPT repack work: the writer for blocks is in hardware, the 512-alignment rule from lzpt-tools applies to a different driver, `mumin_lzp.c` on CXD90014).
- Relevance: HIGH as a template. This is the only GPL-published code on this SoC that starts a Sony coprocessor with a file-loaded program. It is not the SA-DSP, but the register/mailbox conventions (CKEN, XRST, IPC base, MBXn, IMSR/IENR) are the likely family. Compare with the SA-DSP registers we found at `0x40000+`, DMA descriptors `0x48230/0x48234`, interrupt `0x48208`: different address window (0xf5xxxxxx is CMPR; our DSP block is elsewhere), but check whether the DSP launch in av-cam has the same IPC-base / mailbox / CKEN-XRST shape.
- What it changes: (1) a way to test the register-protocol hypothesis offline by diffing against our decoded DSP start sequence; (2) confirms that `insmod ... path=<file>` is the normal Sony idiom, consistent with `insmod liro.ko fn=/system/av-cam.bin`; (3) `module_param_string` params are writable via sysfs (S_IWUSR), so `/sys/module/cmpr/parameters/*` exists at runtime on the camera, same likely for liro.

### A2. GPL source: nothing for liro, sabin, zima, spica
- I grepped the whole unpacked 3N kernel tree (`*.c *.h Kconfig Makefile`) for the whole words `liro`, `sabin`, `zima`: zero hits. `drivers/udif` (cdev/bdev/irq/io/malloc only) and `mach-cxd4132` contain no DSP or ISP driver. Conclusion: `liro.ko`, the SA-DSP driver and the av-cam loader are proprietary modules, not GPL source.
- Same negative result for the a7 IV GPL tree (https://github.com/DavidBuchanan314/Sony-ILCE-7M4-Linux, file list of 43,967 paths): no `liro`/`mumin`/`sabin` in the tree outside generic Ubuntu drivers. Relevance: low, but it saves time: do not look for SA-DSP sources in Sony GPL dumps.

### A3. Searches for `sa_yknr`, `sa_sftfcs`, `spica_still_y_tap_step1`, `0x00bd0001`, `liro.ko` on GitHub code search
- Zero relevant hits (only unrelated repos for `spica_still`: an anime-game checker). Within `ma1co/Sony-PMCA-RE`, `ma1co/fwtool.py`, `LAK132/Sony-PMCA-RE` code search for `sabin`/`liro`/`0x00bd` returns nothing (some later queries were rate-limited, so the `ma1co/OpenMemories-*` and `nex-hack` repos were only checked partly).
- So: the names `sa_yknr`, `sa_kknr`, `sa_sftfcs`, `sa_tbox`, `sa_spica`, `zima` do not occur in any public repository I could reach. The only public statement about `sabin` is the OpenMemories hardware page below.

### A4. OpenMemories hardware page
- https://openmemories.readthedocs.io/hardware.html (opened). Text: "The SA DSP core is integrated into the BIONZ SoC and shares memory with the ARM cores. It executes 'sabin' programs", 32-bit CPU, 16 registers, custom instruction set. CXD4132 = Opal/Avip, 3x ARM11 MPCore, Jan 2011 (TX100, RX100, NEX-6). DFE with its own ARM core (`dfe.bin`) only starts with CXD90016. Some cameras have a secondary image processor between sensor and BIONZ running uITRON.
- Relevance: medium, no new facts vs. prior-art §3, but it is the only place where the word `sabin` is written publicly. Matches our model.

---

## B. av-cam, liro, Backup subsystem

### B1. Sony-PMCA-RE #597 "Research into further settings"
- https://github.com/ma1co/Sony-PMCA-RE/issues/597 (RomanHargrave, 07.02.2025 and 10.02.2025; ILCE-6000 fw 3.20, later a7R II). Quoted facts:
  - `av-cam.bin` is loaded by `liro.ko`. `rbasefind` finds the base, but the base is available directly from `/sys/module/liro/parameters/adr`. LIRO maps av-cam.bin into kernel memory and **spawns a kernel thread pinned to a specific core** which runs the entry point.
  - Header at the start of the image (his reconstruction; names are his): `avcam_fw_hdr_t {unk0; magic; version; preEntryAddr; entryAddr; memMap*}` and `avcam_mem_map_t {ramBase, ramLen, bssBase, bssLen, tailBase, tailLen, limitBase, limitLen}`.
  - `Backup_read` in av-cam is "a fairly complex thunk which appears to use an address table somewhere outside of av-cam.bin bounds", presumably set up by an OSAL/kernel module. This answers one of our open points: "who resolves file-id to a path is not in av-cam ARM code" fits, the lookup may go through that same external table/IPC.
  - Backup `0x00FA0080` "appears to contain some kind of table which references av-cam.bin plus 32-bit integers offset from the base by powers of 2".
  - Later comment: property changes made through the menu go through an IPC path that the serviceshell `bk w` does not replicate; "turn the camera off and back on, removing the battery" is needed for some settings (his IR-remote example `0x01070C7B`).
- Relevance: HIGH. Gives (a) a header layout to cross-check with our av-cam 3N header, (b) a runtime way to read the load address, (c) a lead on `0x00FA0080` (compare with our `0x00bd...` tables: both may be file/overlay lists), (d) a warning about IPC-cached settings. Applicability to CXD4132: it is stated for ILCE-6000 (CXD90014); unverified on 3N, but our own `insmod liro.ko fn=/system/av-cam.bin` evidence says the mechanism is shared.
- What it changes: ask whether our 3N av-cam header matches `{unk0, magic, version, preEntry, entry, memMap*}`; if yes, `memMap` gives the exact RAM/BSS extents needed for Ghidra segment setup and for sizing a patched image.

### B2. Backup.bin container template (010 Editor)
- https://gist.github.com/RomanHargrave/9b7a194ee166972b3c21b892df126bf5 (file `ILCE-BK4.bt`, linked from #597). I fetched all 371 lines with `gh gist view`.
- Contents: header `{magic, cookie, revision[4], numSubsystems, dataOffset, dataSize, checksum, ..., version[128], region[64]}`; subsystem entries `{pteCount (u16), pteStart}`; property entries with a 24-bit address, size, flags (`PF_ARRAY=0x80`, "resetable" = `0b01110100`), `defaultValue` stored beside the data (confirms the defaults/reset mechanism of B5); key = `(subsystem<<16) | property`. Named subsystems: 0x29 ObjRenderer, 0x2A ObjDisplay, **0x35 ObjEffect**, 0x3E device info, **0x4B SENSER_UDTR**, 0x7A..0x7D infra (input, touch, hotshoe, SIRCS), 0x81 font, 0x90 UDATE, 0xA1/0xA2/0xA4 PSM, **0xBD "mystery bin list" (`0x00BD0006 = P_MYSTERY_BIN_LIST_2`)**, 0xCA registration, 0xFD network send limits, 0x105 test, 0x107 user params, 0x112 configs/kikilog, 0x119, 0x11B dial, 0x138 facial recognition, 0x169 remote net.
- It names `libObj.so::ExecCommandInitParam` as the place where the ~hundreds of `ObjRenderer` PARAM_IDs are listed, and `ModelIdSoTable` with `BKID_UNIFIED_SO` (`0x003E000B`), the key selecting `viewUnified*.so`. That matches our "viewUnified2.so" finding.
- Relevance: HIGH for 0x00bd (his `0x00BD0006` = a second list in the same subsystem as our `0x00bd0001/0002`, i.e. `0x00bd0001` prefixes, `0x00bd0002` (owner,codectype)->file-id map, and likely `0x00bd0003..0x00bd0006` more lists). Neither 0x0003 (colour) nor 0x0035 styles are named in the template; the only styling-ish items are `0x35` ObjEffect paint/zoom params (UI, not ISP).
- The `checksum` field in the header and the `PF_*` flags are in a 6000/7RM2/a7 IV template, not 3N: validate against our `bkdump.py` layout before trusting field order.

### B3. Sony-PMCA-RE #512 (uncompressed RAW, a6000)
- https://github.com/ma1co/Sony-PMCA-RE/issues/512 (RomanHargrave, 07-09.02.2025). Text: a "processing ticket" model: parameters travel with the image buffer through a pipeline with internal names "HAPI", "STM"; a6000/a7R II `av-cam.bin` carry nearly all engineering logging; the author located the still-capture pipeline and "the bit where JPEG encoding happens (89% certain)"; the imager side may delta-compress RAW itself and be configured via IPC.
- Relevance: medium. Supports our view that per-stage parameters are handed to modules with a ticket and that logging strings in av-cam name stages. Suggest grepping 3N av-cam for the same "HAPI"/"STM" strings and for log format strings around `Capture::YKNR`. Already partly in prior-art table (that table lists #512), the new content is the ticket/pipeline description and the 89%-certain JPEG location claim.

### B4. Sony-PMCA-RE #468 "Question about documentation and further development"
- https://github.com/ma1co/Sony-PMCA-RE/issues/468 (Tooniis, oexler, 12.2023). Pointer to a Matrix room "#sony-bionz-re:matrix.org" for boot-chain and bare-metal work; the same person maintains the fork `Tooniis/OpenMemories-CI` (qemu CI, last update 28.09.2023, found via `gh repo list`). Relevance: medium (community to ask); no technical content.

### B5. Backup defaults and reset (mungewell, issue #249, NEX-6 clean HDMI thread)
- https://github.com/ma1co/Sony-PMCA-RE/issues/249 (comment 22.07.2021). Facts: factory defaults are stored in the firmware installer; once on camera the body keeps a "reset" value per key and re-applies it on factory reset; he "has not yet had a problem a factory reset couldn't fix". `bk.elf` exists both under the Tweak telnet shell and inside `pmca-console serviceshell` (interactive, effect visible without restart for some keys). Method to find keys: extract `viewUnified4.so`, find the little-endian 4-byte patterns that equal known keys (e.g. `0x0107088e`), sort them, match against Backup.bin; he published `nex6_view4_targets.txt` (attachment on issue #249, https://github.com/ma1co/Sony-PMCA-RE/files/6859412/nex6_view4_targets.txt, not downloaded).
- Relevance: HIGH for safety (reset is the undo for 0x0003xxxx writes, confirm on the 3N by writing a harmless 0x0003 byte, factory reset, re-reading) and medium for method (scan `.so` and av-cam for literal key constants is what we did for `0x00030001`).

### B6. Other Backup items seen (no colour keys)
- Sony-PMCA-RE #717 (backup dump request, LAK132 fork `bk dump-txt`), #733 (a6400 per-property USB opcodes), already in prior-art. New detail from #717: the a7 IV dump commenter notes `pull`, `bootrom`, `bootloader` fail with "Senser ..." errors on that body; "Senser" is Sony's own name for service-mode access (`SS_SENSER_UDTR = 0x4B`). Issue #466 (a7R III) also hits "Senser adjust Control error 129". Relevance: low for 3N, informative about the service-mode naming. Search term "Senser" yields only these two.
- OpenMemories-Tweak #268 (2018): the NEX-3N support request. I read it: ma1co asked the 3N owner (user `nex3n`) to run `pmca-console guess_firmware -f 0x31030000.zip` to brute-force the model id, so the 3N was a "first time" model there. The result is the `0x31030022` entry now in devices.yml. Relevance: low (history), but it shows the 3N firmware image is accepted by fwtool's model table.

---

## C. Architecture / patents

No document found that describes the ISP pipeline or SA module list of CXD4132. Patents give algorithm-level context only (all verified on Google Patents):

| Patent | Assignee, priority | Content | Relevance |
|---|---|---|---|
| US8363123B2 (https://patents.google.com/patent/US8363123B2/en) | Sony, 21.12.2007 | Colour NR inside demosaic: separate luminance (G) and chroma paths, epsilon filters at interpolation points. | medium: a model for a separate luma NR (`YKNR`) vs chroma NR (`KKNR`?) split, the naming `YKNR`/`KKNR` is ours, not in the patent |
| US8081239B2 (https://patents.google.com/patent/US8081239) | Sony, 29.10.2007 | Scales the NR parameter by the local gradation-correction gain (WDR/DRO); one low-pass filter with adjusted characteristics for NR and skin smoothing. | medium: explains why NR strength is coupled to DRO (`sa_bdro2_bdex`) and to tone curve; relevant if a custom tone curve (our `0x3007a` mode) changes NR behaviour |
| US9123102B2 (https://patents.google.com/patent/US9123102) | Sony, 06.04.2012 | Chroma-noise removal via representative pixels + smoothed image (improvement over bilateral). Timeline matches the 2012-13 NEX generation. | medium-low |
| US8013910B2 (https://patents.google.com/patent/US8013910) | Sony, 24.05.2007 | Block compression of RAW before SDRAM and decompression before processing, to cut bus bandwidth. Single-pass streaming. | low-medium: likely the origin of the "compression offloaded to hardware" idea in #512 |
| EP2424228A2 (https://patents.google.com/patent/EP2424228) | Sony, 31.08.2010 | Memory I/O differs by mode: normal = store after correction; WDR = store before correction. | low |

Not claimed: I did not find any Sony patent for "toy camera" / "soft focus" / "miniature" / "film grain" effect internals. Results that look like they are Sony via the search summaries were NOT Sony (see Corrections).

## D. PMCA / in-camera processing apps

### D1. NEX-3N and PlayMemories Camera Apps (checked precisely)
- Source of truth in code: https://raw.githubusercontent.com/ma1co/fwtool.py/master/devices.yml (opened): `NEX-3N: arch CXD4132, model 0x31030022` with no `apps` key; `NEX-5R 0x22030014`, `NEX-5T 0x22030020`, `NEX-6 0x22030018` have `apps: '1.1'`; `ILCE-5000 0x41030012` `apps '2.3'`, `ILCE-6000 0x41030035` `apps '2.4'` (CXD90014).
- Sony support article 00289030 (https://www.sony.ca/en/electronics/support/e-mount-body-nex-6-series/nex-6/articles/00289030): WebFetch got 403; a search snippet says the compatible ILC list includes NEX-5R/5T/6 and not NEX-3N, and the PlayMemories Camera Apps download service ended 31.08.2025. Treat the Sony-page half as unverified.
- Consequence: no Android (PMCA) app route on the 3N. The only code-execution routes are updatershell/serviceshell (pmca-console), and the Linux side. Matches prior-art §4.

### D2. In-camera grain apps
- None for Sony found. OpenMemories AppList (see prior-art) has no grain/LUT app. The only Sony-official image-effect app I met in search results is "Digital Filter" (graduated ND, a7R II era, PetaPixel 14.03.2017: https://petapixel.com/2017/03/14/sony-unveils-cool-digital-filter-app-camera-graduated-nd-filter/), it needs a camera with apps support. Relevance: low.
- For context only: Nikon Zf/Z5II and Fuji have official in-camera grain (onecameraonelens.com 04.09.2025); no Sony camera in the search results.

## E. Forums

- personal-view / dpreview / 4pda: web search returned nothing on hacking NEX-3N/NEX-6 colour, NR, or DSP files (only manuals and firmware news). I did not manage to query the forums' own search (Cloudflare / no tool for it this session).
- The most active current venue is GitHub: `ma1co/Sony-PMCA-RE` issues (recent 2026 activity: #717, #730 "Calibration in Service Mode", #733, #738, #740) and the Matrix room from #468. #730 "Calibration In Service Mode" (05.08.2026) I did not open; it may touch the `Senser` service commands.
- Developers active on RE of newer Sony bodies right now: LAK132 (fork with `bk dump-txt`, 07.10.2026 push), DavidBuchanan314 (ILCE-7M4-RE, push 09.10.2026, fwtool PR #52), Gimmer268 (lzpt-tools, fwtool PR #55), RomanHargrave (a6000 / a7R II av-cam analysis, 2025).

## F. ILCE-7M4-RE repository content
- https://github.com/DavidBuchanan314/ILCE-7M4-RE (cloned and grepped). Contents: bootrom dumps for CXD90057 "Mira" and CXD90058 "Cetus" (`0xFFFF0000`), eMMC boot0 and eSRAM dumps, fastboot payloads for both cores, UART bootloader tools. No mention of `sabin`, `liro`, `zima`, `spica`, `yknr`, `DSP`, `av-cam` or Backup in any text file (only binary matches in boot images). Relevance: low for colour/DSP, medium for the "no decryption key for CXD90057" blocker (consistent with prior-art §3).

---

## Corrections / things the search summaries got wrong (for the record)
- Web search summary claimed "Toy photo" patents US8792018, US9277125, US8957982, US9088722, US9866796, US8896726 are Sony. Verified: **US8792018B2 is Olympus (now OM Digital Solutions)**; its text does define "toy photo" as shading + white balance + contrast + hue/chroma processing, which is useful as a description of the effect but not of Sony's. **US9332194B2 is Canon** (diorama effect). Do not cite these as Sony.
- US7710470 (Olympus) was returned in a Sony NR query; ignore.
- Search summary said the joeording3 fork is "ma1co's"; it is a fork. The primary is `ma1co/fwtool.py`.

## Searched but not found
- Any public analysis of `sa_*.bin` modules by name (`sa_yknr`, `sa_kknr`, `sa_sftfcs`, `sa_tbox`, `sa_spica`, `sa_bdro2_bdex`, `sa_defect`, `sa_jpeg_enc_*`, `sa_pbe_work`, `sa_star`, `sa_zima_startup_*`, `spica_still_y_tap_step1.bin`, `idt_cam.bin`): GitHub code search and web search return nothing.
- Any public write-up of `liro` beyond issue #597; no source for liro (not in GPL tarballs of the 3N or the a7 IV).
- Anyone replacing or patching an SA module or `av-cam.bin` on any Sony camera (path, sum32, integrity): nothing. fwtool issues #22/#50/#55 cover repack of LZPT/tar/FDAT only (four levels: LZPT container, tar header checksum, per-file CRC32 `*_sum/*.sum` manifests, FDAT CRC + encryption), not individual module checks. Our own sum32 on `.bin` modules stays undocumented publicly.
- Backup `0x00bd0001` prefix list and `0x00bd0002` (owner, codectype) -> file-id map: only `0x00BD0006` is named (as "mystery"). No resolver of file-id to path is described anywhere.
- Colour/tone/NR/Creative Style keys in subsystem 0x0003 (and 0x0035 as styles): not named in any public template or issue.
- Film-grain / picture-effect apps or hacks for Sony via OpenMemories or PMCA: none.
- Sony patents on the SA-DSP architecture, the sabin loader, or the internals of Toy Camera / Soft Focus / Miniature / film grain: not found (only generic NR patents in section C).
- Forum threads on personal-view, dpreview, 4pda about NEX-3N/NEX-6 ISP or NR hacks: none surfaced.
- Independent dump of 3N `idt_cam.bin` or its overlays: none.

## Suggested follow-ups (derived, not from sources)
1. Diff the 3N `liro.ko` start sequence and the SA-DSP launch code in av-cam against `cmpr.c` conventions (IPC base, MBX0..3, IMSR/IENR, CKEN/XRST).
2. Check the 3N av-cam header against RomanHargrave's `{unk0, magic, version, preEntry, entry, memMap*}` layout, and read `/sys/module/liro/parameters/adr` over telnet/serviceshell if a shell is available.
3. Look in 3N Backup for `0x00BD0003..0x00BD0006` and `0x00FA0080`; compare with our `0x00bd0001/2`.
4. Before any further 0x0003 writes: test once that a factory reset restores a deliberately changed 0x0003 byte (defaults are stored beside the data per the template).
5. Ask in the Sony-PMCA-RE Matrix room or Discord about the file-id resolver and SA-DSP VLIW only after we have a precise question.
