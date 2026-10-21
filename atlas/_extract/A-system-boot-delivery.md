# Extract A — system, partitions, boot chain, memory, delivery, safety, tools

Working material (not authoritative). IDs are temporary (`A-<AREA>-<NNN>`); the atlas editor renumbers to `C-*`.
Format follows `../00-index.md`. Addresses: av-cam VA (base `0xc3441000`) unless prefixed; idt_cam offsets are
file offsets inside the module (inner p3 offset `0x980e00`).

Sources (abbreviations used in `source:`):
- SB = `WorkPersonal/reference/nex3n-safe-test-boot.md`
- FH = `WorkPersonal/reference/nex3n-firmware-hacking.md`
- FA = `notes/firmware-architecture.md`
- LM = `notes/live-memory-and-delivery.md`
- GH = `notes/grain-hook.md`
- DG = `notes/dsp-grain-campaign.md`
- ST = memory `nex3n-firmware-hack-status.md`

Corrections of 09.10.2026 applied (they override older notes): (1) `idt_cam.bin` = 35 overlays, not one VLIW blob;
(2) p8 `/usr/sabin` holds ~30 more SA modules (sa_yknr, sa_kknr, sa_sftfcs, sa_tbox, sa_spica, sa_jpeg_enc_*,
sa_bdro2_bdex, sa_defect ...) besides p3 `/system/sabin` (idt_cam, sa_dfdet, ssboot); (3) ARM-side grain does not
reach the JPEG (verified-hw 07.10); (4) overlay skip is non-specific.

---

## SYS — chips and cores

### A-SYS-001: The NEX-3N SoC is Sony CXD4132 running Linux 2.6.29.6-rt24, ARMv6 SMP with 2 processors
- status: verified-code
- evidence: vmlinux strings `SMP: Total of %d processors activated`, `CPU%u: Booted secondary processor`; platform name CXD4132 in `NEX-3N.hdr`/`CXD4132.dat` (pmca fdat)
- source: SB §1 "vmlinux / initrd"; FA "CPUs and DRAM"; FH "Что выяснено / Платформа"
- date: 2026-10-04
- relates: conflicts A-SYS-003 (3 CPUs in updater kernel)

### A-SYS-002: CPU0 runs Linux/userland, CPU1 runs the av-cam RTOS (µITRON), started by liro.ko
- status: verified-code
- evidence: liro strings `resume_cpu`, `bind task_resume to cpu%d`, `cpu %d is offline`; imports `acre_tsk/act_tsk`, `osal_snd_sync_msg`
- source: SB §1 "vmlinux / initrd", §"Офлайн-дериск liro.ko"; FA "CPUs and DRAM"
- date: 2026-10-06
- relates: supports A-BOOT-007

### A-SYS-003: The updater-mode kernel is `2.6.29.6-rt24-alp_nl SMP PREEMPT RT` (2012-09-26) and reports 3 ARMv6 CPUs
- status: verified-hw
- evidence: read-only recon in the updater shell (uname/cpuinfo), 06.10.2026
- source: SB "Live-разведка окружения апдейтера"
- date: 2026-10-06
- relates: conflicts A-SYS-001 (2 processors); possibly the third CPU is only visible in the updater kernel — not explained anywhere

### A-SYS-004: The av-cam CPU is ARMv6 without Thumb-2; patches must be Thumb-1 (no movw/movt/usat/b.w), conditional branches reach +-256 B, far jumps are `ldr r3,[pc,#4]; bx r3`
- status: verified-code
- evidence: constants in av-cam built with `movs`+`adds`/shifts; assembled with keystone, checked with capstone; hook code built under this constraint executed on camera (marker `0xdeadbeef`)
- source: FA "CPUs and DRAM"; GH §1 "Code constraints"; SB §4b
- date: 2026-10-06
- relates: —

### A-SYS-005: av-cam.bin header is ARM (`e28ff028`, `add pc,...`) with signature `ORIL`/`LIRO` followed by a scatter table at `0x3c..0xc0`; the body from `0xd4` is Thumb; size 6554072 (`0x6401d8`), base `0xc3441000`, end about `0xc3a811d8`
- status: verified-code
- evidence: av-cam.bin file header; liro prints `ram %p+%p / bss / tail / limit`
- source: SB §7(d), §7(c)
- date: 2026-10-04
- relates: supports A-BOOT-014

### A-SYS-006: The SA DSP engine's internal registers (`0x40000+`, local `0x48000`) are DSP-local and not mapped into ARM physical memory, so they cannot be read from the ARM side
- status: hypothesis
- evidence: no SA MMIO range in `/proc/iomem` of the updater kernel (updater has SA disabled, so this alone is not proof); the notes state "neither /dev/mem nor senser" but no explicit failed read of `0x40000` is recorded in these sources
- source: FA "CPUs and DRAM"; SB §"Вывод по маршрутам стенда", ST ("op3 — определённый вывод")
- date: 2026-10-06
- relates: —

### A-SYS-007: iomem of the updater kernel lists MeNo (NAND) at `f2002000`, UARTs at `f2038/f203a`, `f5060000` uio0 "gpe"; no SA engine range
- status: verified-hw
- evidence: `/proc/iomem` in updater shell
- source: SB "Live-разведка окружения апдейтера"
- date: 2026-10-06
- relates: supports A-SYS-006

---

## PART — partitions, files, filesystems

### A-PART-001: The NAND is one MBR device; partitions appear as `/dev/nflasha0pN` (major 252) and also as `/dev/nflashaN`
- status: verified-hw
- evidence: `/proc/partitions` in the updater shell; `/dev/nflasha3`, `/dev/nflasha5` nodes used for raw read/write
- source: FA "Flash partitions"; LM "updater shell"
- date: 2026-10-06
- relates: —

### A-PART-002: Partition sizes (1 KiB blocks): p1 4096, p2 3072, p3 10240, p4 6144, p5 40960, p6 5120, p7 35840, p8 46080, p10 2816, p12 1024
- status: verified-hw
- evidence: `/proc/partitions` in the updater shell; full dump `nex3n_v100_nflasha.bin` is 256 MB
- source: FA "Flash partitions"; FH "Где что лежит"
- date: 2026-10-06
- relates: —

### A-PART-003: p1 holds the updater boot area / separate updater kernel + initrd
- status: hypothesis
- evidence: Loader2 strings `\boot\vmlinux`, `\boot\initrd.img` (path for the updater kernel); FA labels it "updater / boot1 area"; role never read out of p1 directly
- source: FA "Flash partitions"; FH "Что выяснено / Платформа"; SB §1
- date: 2026-10-06
- relates: —

### A-PART-004: p2 = `/setting` (vfat, rw): Backup.bin store, mode files (`/setting/mode/dmode`, `cmode`, `/setting/sen/smode`), `DmmConfig.bin`; the only filesystem writable as a file
- status: verified-hw
- evidence: updater shell mounts nflasha2 vfat rw; senser `writeFile('/setting/gtest.bin')` OK with readback MATCH, delete OK
- source: FA "Flash partitions"; LM "senser"; SB §4d
- date: 2026-10-06
- relates: —

### A-PART-005: p3 = `/system` is a raw LZPT (`TPZL`) image (10 MB, 10485760 B) wrapping an inner FAT image of about 14.4 MB; files: `av-cam.bin`, `vmlinux.bin`, `initrd.img`, `kemco.txt`, `sabin/` (idt_cam.bin ~200 KB, sa_dfdet.bin, ssboot), lens data
- status: verified-code
- evidence: fwtool/lzpt unpack of the flash dump; `lzpt_write.py` reproduces p3 byte-for-byte; Loader2 config table names `\sabin\idt_cam.bin`, `\sabin\sa_dfdet.bin`, `\av-cam.bin`, `\kemco.txt`, `\initrd.img`, `\vmlinux.bin`
- source: FA "LZPT"; SB §1; DG §3 (corrected 09.10)
- date: 2026-10-06
- relates: supersedes A-PART-009 (p3 sabin has only idt_cam + sa_dfdet — corrected to add ssboot)

### A-PART-006: Inside the p3 inner image `av-cam.bin` is contiguous at offset `0x8e00`, full size 6554072; idt_cam.bin starts at inner offset `0x980e00`
- status: verified-hw
- evidence: patched at `0x8e00`, repacked and flashed, camera booted the patched image (curve, grain hook); NOP experiments at `0x980e00` took effect
- source: FA "LZPT"; LM "Flash pipeline"; DG §4
- date: 2026-10-07
- relates: —

### A-PART-007: p8 = `/usr` is a raw LZPT image (45 MB) wrapping an ext2 rootfs; contains `im.elf`, `bootin.elf`, apps/libs (`libObj`, `libSysDef.so`, `viewUnified*.so`), `share/app/string_*.uxc` (menu strings)
- status: verified-code
- evidence: unpacked dump; `/sbin/init` mounts `/usr` ext2; test p8 "Sunset→House " built via `make_p8_mod.py` + `ext2_patch.py`
- source: FA "Flash partitions"; FH "Что выяснено"; SB §1, §3
- date: 2026-10-06
- relates: —

### A-PART-008: In addition to p3 `/system/sabin`, p8 `/usr/sabin` holds about 30 SA modules (sa_yknr, sa_kknr, sa_sftfcs, sa_tbox, sa_spica, sa_jpeg_enc_*, sa_bdro2_bdex, sa_defect, ...)
- status: verified-code
- evidence: correction of 09.10.2026 supplied by the project owner; module listing is not in the sources assigned to this extract (attach from `04-dsp-modules.md`). Indirect support in sources: Backup lists `sa_jpeg_enc_1unit/_1core`, `sa_jpeg_dec_*`, zima cores (SB §7); strings `YKNR_Debug_MSDump` (SB "находка"); `sa_func_SFTFCS_start`, Soft Focus program in sftfcs `@0x2420` (SB plan); `ExecuteCalcStartMSG` callers "SFTFCS/TBOX/..." (GH §2)
- source: correction 09.10.2026; SB §7(a), "НАХОДКА: штатный debug-дамп"; GH §2 "JPEG encode"
- date: 2026-10-09
- relates: supersedes A-PART-009, A-IDT-002; conflicts DG §3 (see Conflicts 2)

### A-PART-009: p3 `sabin/` holds only `idt_cam.bin` (200 KB) and `sa_dfdet.bin`; the 3N has no separate NR / JPEG / Soft-Focus SA modules, so the whole stills develop pipeline is `idt_cam.bin`
- status: refuted
- evidence: refuted 09.10.2026 by the existence of p8 `/usr/sabin` (~30 modules) and by the 35-overlay structure of idt_cam; the notes themselves refer to `sa_sftfcs`, `sa_jpeg_enc`, `sa_yknr`
- source: DG §3; ST (07.10 entry "весь develop/NR/YC DSP на 3N; sa_yknr/jpeg_enc отдельных у 3N НЕТ")
- date: 2026-10-07
- relates: superseded by A-PART-008, A-IDT-001

### A-PART-010: p5 = WBI, 40 MB, magic `WBI1` at offset 0 — a RAM snapshot for fast start
- status: verified-code
- evidence: dump of nflasha5; Loader2 `Check Signature of WBI` @0xa01f12ec
- source: FA "Flash partitions"; SB §2
- date: 2026-10-06
- relates: —

### A-PART-011: Roles of p4 (6 MB), p6 (5 MB), p7 (35 MB), p10 (2.75 MB), p12 (1 MB) are not established in these notes
- status: unknown
- evidence: FA lists them with an empty role column; `/android` and `/info` read-only filesystems appear in senser errors but their partitions are not mapped
- source: FA "Flash partitions"; LM "senser"
- date: 2026-10-06
- relates: —

### A-PART-012: `/system` (p3), `/usr` (p8), `/android`, `/info` are read-only through senser FileControl (error 130); only `/setting` is writable as a file
- status: verified-hw
- evidence: `writeFile('/system/av-cam.bin')` and `writeFile('/system/gtest.bin')` -> "Senser file control error 130"; `/setting/gtest.bin` OK (06.10.2026)
- source: LM "senser"; SB §4d; GH §3
- date: 2026-10-06
- relates: —

### A-PART-013: `mount -t vfat /dev/nflasha3` fails with "Invalid argument" in the updater shell because the device holds the raw LZPT image
- status: verified-hw
- evidence: updater shell test
- source: LM "updater shell"
- date: 2026-10-06
- relates: conflicts SB §1 (calls `/system` "p3 (nflasha3, vfat)" mounted by init) — resolved by the LZPT layer: init mounts the decompressed layer

### A-PART-014: The p3 LZPT layer presents the decompressed FAT inner image through a read-only axfs-style layer; format: table of contents + 64 KiB input blocks, each compressed as 16 x 4 KiB LZ77 sub-streams
- status: verified-code
- evidence: byte-exact LZPT writer `code/lzpt/lzpt_write.py` reproduces stock p3/p8; ma1co `fwtool/archive/lzpt.py`
- source: FA "LZPT compressed partitions"
- date: 2026-10-06
- relates: the "axfs-style runtime layer" part is inferred (hypothesis); the on-flash format is verified-code

### A-PART-015: Complete flash dump `~/nex3n-dump/nex3n_v100_nflasha.bin` (256 MB, fw 1.00, region CX76201_CE, md5 44606c...) plus `boot/boot1` and `boot/bootrom` exist
- status: verified-code
- evidence: dump file, SHA1SUMS
- source: FH "Где что лежит"; SB "ПЛАН: прошивка дампера"
- date: 2026-10-04
- relates: —

### A-PART-016: Sony released no firmware update for the NEX-3N (only 1.00)
- status: hypothesis
- evidence: note-only statement (official download site check not recorded)
- source: FH "Где что лежит"
- date: 2026-10-04
- relates: —

---

## BOOT — load chain

### A-BOOT-001: Loader2 is `boot/boot1` Ver.31.23.12 (Thumb, VA = file + 0xa01e9000); BOOT branch `LDR: <BOOT>` @0xa01ee3b0 does `Init DDR` -> DGU -> `Run Configurator (load file)` @0xa01ee67c -> config-table parser `normal_load` @0xa01f18a6
- status: verified-code
- evidence: disassembly/strings of boot1
- source: SB §1 "Loader2"; FH "Восстановление"
- date: 2026-10-04
- relates: —

### A-BOOT-002: Loader2 reads its load list from Backup BKID `0x00FA0080` (9216 B = 64 records x 144 B); 6 are non-empty: `\sabin\idt_cam.bin`, `\sabin\sa_dfdet.bin`, `\av-cam.bin`, `\kemco.txt`, `\initrd.img`, `\vmlinux.bin`
- status: verified-code
- evidence: Backup.bin BKID `0x00FA0080` decode
- source: SB §1; FA "Boot chain and WBI"
- date: 2026-10-04
- relates: —

### A-BOOT-003: Config record format: `+0` attr, `+4` start VA, `+8` end VA, `+0xc` flags (bits [23:20] boot-mode mask, [27:24] CPU id), `+0x10` name; `\av-cam.bin` start `0x83441000`, end `0x83cf1fff`; `\vmlinux.bin` start `0x80018000`
- status: verified-code
- evidence: BKID `0x00FA0080` records; `normal_load` loop (`entry[0xc] & (0xf<<20)` vs mode mask; CPU by `entry[0xc]>>0x1c`; `CFG: Wake up cpu` @0xa01f1e56)
- source: SB §1
- date: 2026-10-04
- relates: the note calls `0xc3441000` the "non-cacheable alias" of `0x83441000`; conflicts with SB §7(d) cache-flush requirement (see Conflicts)

### A-BOOT-004: Loader2 loads `vmlinux` + `initrd` on CPU0
- status: verified-code
- evidence: Loader2 strings `LDR: Load vmlinux and initrd`; config entries; FA states it
- source: SB §1; FA "Boot chain and WBI"
- date: 2026-10-04
- relates: —

### A-BOOT-005: In normal cold boot the av-cam config entry is gated off (mode mask / CPU field select only kernel + initrd) and av-cam is loaded by Linux instead
- status: hypothesis
- evidence: FA states it as fact; SB §1 says per-entry mask bits were not decoded one by one and calls it [HYP]; SB "Открытые проверки" lists it as unverified
- source: FA "Boot chain and WBI"; SB §1, "Открытые проверки"
- date: 2026-10-04
- relates: conflicts FA wording (stated as fact) vs SB (explicit hypothesis)

### A-BOOT-006: The cold-boot chain is Loader2 -> `vmlinux`+`initrd` -> `/sbin/init` (ELF, not a script) -> `/usr/bin/bootin.elf` -> `/usr/bin/im.elf` -> `insmod liro.ko fn=/system/av-cam.bin load=1 [debug=1]`; `/sbin/init` main @0x90ad mounts `/system` (nflasha3), `/setting`, `/usr` (ext2), runs `check_mode_file`, `set_oreore_env`, `run_bg_process("/usr/bin/bootin.elf")`, then `sen.elf`
- status: verified-code
- evidence: init mount table; strings in `im.elf` (`fn=/system/av-cam.bin load=1 debug=1` at file off 0x33c8; command build `%s adr=0x%x %s %s` in function @0xb324; flag-selected string pair @0xb37c)
- source: SB §0, §1 "Linux — реальный runtime-загрузчик av-cam"; FA "Boot chain and WBI"
- date: 2026-10-04
- relates: —

### A-BOOT-007: liro.ko is the runtime loader of av-cam; changing `/system/av-cam.bin` (p3) plus zeroing WBI and rebooting makes the camera run the changed image
- status: verified-hw
- evidence: patched p3 images (film curve k0, grain hooks, NOP experiments) flashed 06-07.10.2026 and observed running (marker `0xdeadbeef`, changed JPEG output); direct proof that the hardcoded path `/system/av-cam.bin` is the one used
- source: LM "Flash pipeline"; SB §4f; GH §1
- date: 2026-10-06
- relates: supports A-DLV-009

### A-BOOT-008: liro.ko: module parameters `fn` (path), `adr`/`adrs` (load address), `load`, `debug`, `delay`, `resume_cpu`, `liro_resume_async`, `os_thread_bind`; firmware starts on write to `/proc/liro/start`, not on insmod; checks `Magic unmatched` / `version unmatched`; `depends=` empty
- status: verified-code
- evidence: strings and pyelftools import list of `kmod/liro.ko`
- source: SB §1, "Офлайн-дериск liro.ko"
- date: 2026-10-06
- relates: SB §1 writes `adr:int`, the offline analysis writes `adrs` — naming not reconciled

### A-BOOT-009: liro.ko cannot write p3/p8: its only storage imports are `Backup_write*/Backup_sync*` (WBI in p5) and `filp_open/filp_close/vfs_read`
- status: verified-code
- evidence: import list from pyelftools; no MTD/block/erase/nflash symbols
- source: SB "Офлайн-дериск liro.ko"
- date: 2026-10-06
- relates: —

### A-BOOT-010: `insmod liro.ko` in the updater kernel fails ("unknown symbol", missing `Backup_nread*`); the updater kernel also lacks `Backup_write`, `acre_tsk`, `osal_snd_sync_msg`, `buddy_init_pool`, `loc_cpu`, `os_this_cpu` (kallsyms all 0)
- status: verified-hw
- evidence: push `liro.ko` to `/tmp`, `insmod`, dmesg `liro: Unknown symbol Backup_nread`; nothing loaded, file removed (06.10.2026)
- source: SB "Пункт 2 проверен на железе"
- date: 2026-10-06
- relates: refutes A-BOOT-011

### A-BOOT-011: A zero-flash test route exists: from the updater shell run `insmod liro.ko fn=/setting/av-cam.bin ...` to boot a test av-cam without touching p3/p8
- status: refuted
- evidence: A-BOOT-010 (updater kernel is a stripped recovery kernel; imaging/SA stack cannot be brought up there)
- source: SB §3 "Альтернатива без правки p8", §6, §8 point 1
- date: 2026-10-06
- relates: refuted by A-BOOT-010

### A-BOOT-012: `bootin.elf` reads `/setting/mode/dmode` (0 = kernel only, 2 = LIRO, 3 = full appFw, default) and starts `im.elf <s|g|r|u|l|i|a> &`
- status: verified-code
- evidence: strings/disassembly of `bootin.elf`
- source: SB §1
- date: 2026-10-04
- relates: dmode=2 as RTOS-isolation test is untested (hypothesis)

### A-BOOT-013: Built-in debug hooks: `im.elf` accepts `boot=`, `bootall`, `target=`, `cipa`, `qemu`, `usbj`, `test`, `debug/nodebug`, `trace`, `dummy_susres`, `imdb`, `imssi`; `bootin.elf` accepts `file=`, `dmode=`, `amode=`, `sim`, `target=`, `gdb`/`gdbs` (gdbserver), `lt`/`wfree`; `init` reads `/setting/env.txt` (`set_oreore_env` @0x9c5c, `putenv` per line); Loader2 has `CFG: Wait for trigger from ICE`, `qemu`, `cipa`
- status: verified-code
- evidence: strings at `im.elf` file off 0x41e0+, `bootin.elf`, init
- source: SB §6
- date: 2026-10-04
- relates: whether any of these can swap the av-cam path from `/setting` is unverified (hypothesis, see A-DLV-018)

### A-BOOT-014: Any av-cam edit must keep the header fields checked by liro (`Magic`, `version`) and the 4-entry load-region table `{src,dst,size,?}` at file offset `0x612268`
- status: verified-code
- evidence: liro strings; region table decoded at `0x612268`. Hardware: edits to the tone-curve region and to a code cave passed liro without error
- source: SB §7(c)
- date: 2026-10-04
- relates: —

### A-BOOT-015: Loader2 enters the updater only via hardware jumpers (`0xf3060000[11:8]==2`) or the file `\updater\mode` on p2; no button combination and no SD boot; `0x0051000f` is a boot-mode log, not a switch
- status: verified-code
- evidence: boot1 disassembly (FH "Восстановление"); `\updater\mode`, `\mode\cmode` are the only file triggers listed by SB §6
- source: FH "Восстановление"; SB §6
- date: 2026-10-04
- relates: conflicts A-SAFE-003 (hardware test: the file flag did not enter the updater)

### A-BOOT-016: Loader2 warm-boot path: `Check boot_is_warmboot` @0xa01efe8a -> Backup `0x5100xx` -> `Check Signature of WBI` @0xa01f12ec -> `Check HW reset / LSI crash / RestReq / date` -> RAM restore from p5 (`dropped wbi`, `__wbi_drop`)
- status: verified-code
- evidence: boot1 strings and disassembly
- source: SB §2
- date: 2026-10-04
- relates: —

### A-BOOT-017: liro takes part in the WBI snapshot (`liro suspend (WBI)`, `liro resume (WBI)`, `ft_backup`/`cp_backup`), so the running av-cam is part of the RAM snapshot
- status: verified-code
- evidence: liro strings; `Backup_write*` imports
- source: SB §2, "Офлайн-дериск liro.ko"
- date: 2026-10-06
- relates: —

### A-BOOT-018: First cold boot: liro reads `/system/av-cam.bin`; later warm boots restore RAM from p5 and do not re-read the file
- status: hypothesis
- evidence: SB marks it [HYP] "logical consequence of the facts"; FA states it as fact. Consistent with hardware: flashing with WBI zeroed always produced the new image
- source: FA "Boot chain and WBI"; SB §0, §2
- date: 2026-10-06
- relates: conflicts FA wording (fact) vs SB (hypothesis)

### A-BOOT-019: A new WBI snapshot is taken at power-off (suspend via `/sys/power/state` = `warm`/`mem`, `WARM(warm_count=%d)`, counter in Backup `0x00940004/5`), and creation is probably gated by Backup `0x00510023` (value 0x02 on the 3N, read in `im.elf` @0xb712); setting it to 00 would disable snapshots
- status: hypothesis
- evidence: `im.elf` @0xa918 writes `/sys/power/state`; only `upm.ko` and `im.elf` read `0x00510023`; not tested on the camera
- source: SB §2
- date: 2026-10-04
- relates: —

### A-BOOT-020: An LSI crash / watchdog event leads to a cold start on the next boot (WBI not taken), so a hang plus power-cycle returns to the stock `/system/av-cam.bin`
- status: hypothesis
- evidence: Loader2 `LSI crash`/`RestReq`/`HW reset` checks and kernel `warm.errmode`/`warm.cancel` strings; consequence not tested separately
- source: SB §4
- date: 2026-10-04
- relates: —

### A-BOOT-021: The Loader2 config table at Backup `0x00FA0080` can be written through `bk` but is bootloader data (brick risk); not attempted
- status: hypothesis
- evidence: `bk w` works on other blocks (A-DLV-015); this block was only read
- source: GH §3 "Dead ends"; SB §4d
- date: 2026-10-06
- relates: —

---

## MEM — memory map and buffers

### A-MEM-001: The av-cam image lives at virtual `0xc3441000`, physical `0x83441000` (phys = virt - 0x40000000); a senser read of phys `0x83441000` matches the image ~99%, the rest is runtime-filled tables (e.g. the service table)
- status: verified-hw
- evidence: senser `readMemory(0x83441000)` vs image, 06.10.2026
- source: FA "CPUs and DRAM"; LM "senser"; SB §4a
- date: 2026-10-06
- relates: —

### A-MEM-002: DRAM is 512 MB mapped at `0x80000000` (cmdline `mem=512M@0x80000000`), 256 MB physical, mirrored (`0x80xxxxxx` = `0x90xxxxxx`: identical dumps)
- status: verified-hw
- evidence: kernel cmdline in updater shell; paired `/dev/mem` dumps at X and X+0x10000000 identical
- source: FA "CPUs and DRAM"; SB "DRAM-remanence тест"
- date: 2026-10-06
- relates: —

### A-MEM-003: 448 MB at `0x84000000` and 19 MB at `0x82D90000` are reserved for imaging/DSP (pixel buffers, engine shared memory); `DmmConfig.bin` (77 KB, in `/setting`) is the DMM pool map with bases such as `0x84b80000`, `0x84c00000`, `0x85000000`, `0x85380000`, `0x86000000`, `0x86800000`, `0x8f800000`
- status: verified-code
- evidence: `memrsv` in cmdline (hw read); `DmmConfig.bin` pulled from `/setting` and decoded
- source: SB "Live-разведка", "ПЛАН: прошивка дампера" Step 1A
- date: 2026-10-06
- relates: —

### A-MEM-004: Buffer pointers inside av-cam structures are bus addresses (bit 31 clear); av-cam CPU sees the same DRAM at virt = bus | 0xc0000000, ARM phys = bus | 0x80000000
- status: verified-hw
- evidence: `session[+0x4c0] = 0x0e000000` read as virt `0xce000000` shows JPEG SOI `FFD8FFE1`; diagnostic av-cam build wrote session fields to a scratch address, recovered by senser
- source: FA "CPUs and DRAM"; GH §1 "Buffer"; SB §4f
- date: 2026-10-06
- relates: —

### A-MEM-005: The developed full canvas `DMM_HANDLE_YCC_FULL` is YUYV 4:2:2, width 4912, stride `0x2660` (9824 B/line), ~32 MB (4912x3264), luma in even bytes; its base is allocated dynamically (`0x8a000000` in one shot, `0x85900000` in another)
- status: verified-hw
- evidence: senser dump after a shot; width recovered by row autocorrelation (min rowdiff 0.49 at w=4912); the base appears 37 times in descriptor tables of step `0x3c` (`0x83dcc9xx`/`0x83dce2xx`)
- source: FA "CPUs and DRAM"; GH §2; SB §4a
- date: 2026-10-06
- relates: conflicts LM "Locating capture buffers" (writes width 4928 with stride `0x2660`); conflicts A-MEM-010 (same base `0x85900000` seen as stride-1280 raster)

### A-MEM-006: `session[+0x4c0]` holds the finished JPEG output pointer (`0x0e000000`, SOI found)
- status: verified-hw
- evidence: dump of `0xce000000`, `ffd8ffe1`
- source: GH §1; SB §4f
- date: 2026-10-06
- relates: —

### A-MEM-007: `session[+0x5e4]` (`0x0d000200`) points at a YUYV 4:2:2 buffer, 4928 pixels wide, next to the JPEG output; it is an early live DMA buffer on the Soft Focus stage only
- status: verified-hw
- evidence: dump + autocorrelation (width 4928), luma ~127; the zero-marker test at rec40 (07.10) did not appear in the JPEG
- source: GH §1; SB §4f; DG §1
- date: 2026-10-07
- relates: supersedes A-MEM-008

### A-MEM-008: `session[+0x5e4]` is the encode-input YC buffer that the JPEG encoder reads, so writing it grains the SOOC image
- status: refuted
- evidence: 07.10.2026 on-camera tests: grain HP-std 0.7-1.8 independent of amplitude (+-15 = +-31); a build zeroing 6 MB of `session[+0x5e4]` at rec40 produced 0% black in the JPEG
- source: GH §1, §2 (marked superseded); ST ("ГЛАВНОЕ 07.10")
- date: 2026-10-07
- relates: superseded by A-MEM-007, A-PIPE-001

### A-MEM-009: Other session YC copies are bus `0x0be00000` (+0x1f24), `0x0b010000` (+0x24e8), `0x0a0a0100` (+0x3858), all YUYV 4928 wide with luma ~127; `0x08010400`/`0x08020000` look like RAW (rowdiff 64)
- status: verified-hw
- evidence: candidate dumps `cand_*.bin`, `session_obj.bin` (not individually mapped to pipeline stages); the RAW identification is a visual/statistical guess
- source: SB §4f; GH §2 table ("other YC copies")
- date: 2026-10-06
- relates: —

### A-MEM-010: A raster image buffer at `0x85900000` (about 6 MB) with stride 1280 bytes (autocorrelation peak 1280, vertical mad 4.86) shows the scene; captured sharp (no effect) and soft-focused pairs `sf_input_sharp.bin` / `sf_output_softfocus.bin`
- status: verified-hw
- evidence: diff method dump1 -> shot -> dump2 (77 of 192 regions identical); render at width 1280 shows the colour target; files in `~/nex3n-dump/work/op3data/`
- source: SB "ВЕХА" and "Пара op3 снята"
- date: 2026-10-06
- relates: conflicts A-MEM-005 (same base `0x85900000` interpreted there as the 4912-wide YC canvas); the pair is a downscaled/other-format buffer or the notes mix two shots — not clarified

### A-MEM-011: `session[+0x3e24]` is a small handle id (`0x1df`), not a buffer address; writing 8 MB through it crashed the camera
- status: verified-hw
- evidence: crash on a build using `base=*(r4+0x3e24)`; diagnostic scratch-dump build
- source: GH §3 "Dead ends"; SB §4f; DG §2
- date: 2026-10-06
- relates: refutes the earlier assumption in SB §4a/§4b that `session[0x3e24]` is the YC base

### A-MEM-012: Accessors `0xc36045fc(r4,&a,&b)` (a = u16 `[r4+0x39e2]`, b = u32 `[r4+0x3e24]`) and `0xc36046ac` do not yield the encode-input buffer; handle -> DRAM resolution is unresolved
- status: verified-code
- evidence: disassembly of accessors; failed use as buffer source (crash)
- source: GH §2, §3, §4; SB §4
- date: 2026-10-06
- relates: —

### A-MEM-013: DRAM contents survive a warm transition into the updater (reserved 448 MB region is not written by the updater kernel)
- status: verified-hw
- evidence: `/dev/mem` read of `0x84000000+` rc=0 with non-zero data after warm entry
- source: SB "DRAM-remanence тест"
- date: 2026-10-06
- relates: —

### A-MEM-014: Transient frame buffers (Soft Focus input/output, develop intermediates) are overwritten by live view within about 30-60 s, before pmca can bring up the updater; remanence capture of the pair failed twice (also with Soft Focus mid)
- status: verified-hw
- evidence: sweeps `0x84000000-0x9f000000` and `0x86000000-0x90000000` rendered at widths 4912/2456/1232, no scene (2D-mad ~48 vs <20 for a clean frame)
- source: SB "DRAM-remanence тест", "Повтор remanence СО Soft Focus"
- date: 2026-10-06
- relates: —

### A-MEM-015: In service mode the camera app is suspended and live view is inactive, so live-view-time buffers are stale/partial; a shot taken without power-cycle (USB unplug, shoot, replug) leaves capture buffers readable by senser (diff method)
- status: verified-hw
- evidence: 2D-mad up to 8.7 in a sweep of `0x84000000-0x90000000`; dump1/dump2 diff isolates changed regions (cluster `0x86800000-0x88700000`, `0x8b*`, `0x8c*`)
- source: SB "Разметка живой imaging-DRAM", "ВЕХА"
- date: 2026-10-06
- relates: —

### A-MEM-016: Code caves (zero fill) in av-cam: `0xc3a011bd` length 3442 (used from `0xc3a011c0`) and `0xc397d4f0` length 1280
- status: verified-code
- evidence: zero-run scan of av-cam; the first was used for wrapper/stub and executed on camera
- source: GH §2 "Code caves"; SB §4b, §4c
- date: 2026-10-06
- relates: —

### A-MEM-017: The live `/system/av-cam.bin` on the camera differs from the stock image only in the tone-curve region `0x5b006a..0x5b0869` (1093 B, owner's film curve k0); patches must be built on the live file
- status: verified-hw
- evidence: senser `readFile('/system/av-cam.bin')` (6554072 B) compared with stock, 06.10.2026
- source: SB §4d; LM "Flash pipeline" step 1
- date: 2026-10-06
- relates: —

---

## CTRL — sequencer and dispatch

### A-CTRL-001: The capture sequencer is a step table at `0xc3629aa4` (file off `0x1e8aa4`): ~58 records of 8 B `{dispatcher_fn (Thumb), descriptor_ptr}`; dispatchers are called indirectly (`ldr fn,[tbl+step*8]; blx fn`); it is a state machine visited by mode, not a linear pipeline
- status: verified-code
- evidence: table decode; xref tool (30k targets / 168k call sites) shows no direct BL callers
- source: GH §2 "Capture sequencer"; SB §4
- date: 2026-10-06
- relates: —

### A-CTRL-002: Each dispatcher is a jump table on context byte `ctx[0x23]` (picture-effect class 0..4; Soft Focus = case 2); record 1 `0xc362827e`: case0 `0xc37deb92`, case1 `0xc37dfca2`, case2 `0xc37ea898` (Stage_SoftFocus), case3 `0xc37df2c0`, case4 `0xc363faa0`, default `movs r0,#5`
- status: verified-code
- evidence: disassembly of record 1
- source: GH §2; SB §4
- date: 2026-10-06
- relates: —

### A-CTRL-003: Stage_SoftFocus (`0xc37ea898`) is called from 8 dispatcher `bl` sites in the thunk block `0x1e72a2..0x1e776a`, one per mode variant; step records 49, 53-57 call the "always-run candidate" stage `0xc3889760`; rec40 `0xc3628b18` dispatches class0 -> `0xc37ee680`, class1 -> `0xc37ecb06`
- status: verified-code
- evidence: xref listing
- source: GH §1; SB §4c; ST ("ГЛАВНОЕ 07.10")
- date: 2026-10-07
- relates: —

### A-CTRL-004: Stages take `r0 = ctx`, `r4 = *ctx` (develop-session object); a family shares a prologue (gate on a session field; geometry `r4[0x1b8]<<16 | r4[0x3a98]&0xffff`; `movs r0,#2; bl 0xc366eb00`)
- status: verified-code
- evidence: disassembly of Stage_SoftFocus and `0xc3889760`
- source: GH §2 "Stage convention"
- date: 2026-10-06
- relates: —

### A-CTRL-005: `0xc366eb00(2, packed_geometry)` locks/prepares the YC canvas
- status: refuted
- evidence: 07.10 analysis: it is a command-send primitive (descriptors posted to DSP/HW through queues), not a canvas allocator
- source: GH §2 (old reading); DG §2 (correction)
- date: 2026-10-07
- relates: superseded by DG §2 statement (see A-CTRL-006)

### A-CTRL-006: The capture pipeline is descriptor/handle-driven: av-cam assembles descriptors and posts them to the DSP/HW through queues; pixel buffers are addressed by handle plus geometry (`session[+0x1b8]` etc.); the DSP owns both the writes and the scheduling of the YC buffer
- status: hypothesis
- evidence: inferred from the failed grain tests, the zero-marker test, and the diagnostic logger; no ARM instruction found in the "buffer finalised -> encoder reads it" window
- source: DG §2; ST ("ГЛАВНОЕ 07.10")
- date: 2026-10-07
- relates: supports A-PIPE-001

### A-CTRL-007: Descriptors (`0xc3bf17xx`, stride 0x14) are runtime addresses outside the image, so step names cannot be derived statically; log strings (`DistEncodeFULL`, `CamCoreDevelopStart`, `ENCODE_JPEG`, `enc_param`, `DMM_HANDLE_YCC_FULL`) have 0 literal-pool references (indexed through a message table `MSG_ID_*`)
- status: verified-code
- evidence: xref/avgraph run
- source: GH §2 "Strings do not locate functions"; SB §4
- date: 2026-10-06
- relates: —

### A-CTRL-008: Still JPEG encode: `tsk46_jpeg` (`0xc344a790`) is a message loop; `msg[0]` = command -> `0xc347427a` (cmd 0/2, stills) or `0xc3474800` (cmd 1/3); the detour logger marker `0xd1a6` fired in `0xc347427a`
- status: verified-hw
- evidence: loop by disassembly; logger build `build_difflog2.py` flashed and marker read via senser (07.10)
- source: GH §2; DG §2
- date: 2026-10-07
- relates: —

### A-CTRL-009: The encode handler takes the YC buffer by handle, not as an ARM address; enc-config global `[0xc3ca0528]` is NULL at idle (qtables nearby); JPEG context singleton `0xc3bb7bc0` (returned by `0xc35dc8ba`) holds only state flags, no buffer pointer
- status: hypothesis
- evidence: logger observations (handler reached, globals read); "by handle" is an inference from the absence of any pointer
- source: DG §2
- date: 2026-10-07
- relates: —

### A-CTRL-010: `ExecuteCalcStartMSG` (`0xc37554de`, 24 callers, SFTFCS/TBOX/... modules) is not reachable from `tsk46_jpeg`; JPEG is driven through the `0xc35dcxxx` subsystem (hardware encoder), `enc_param.address==0` guard lives there
- status: verified-code
- evidence: call graph; strings `JPEG_ENCODE_ERR: enc_param.address == 0`, `src/dgi_jpeg_qtable.c`
- source: GH §2 "JPEG encode is not via the SA-start mechanism"; SB §7(a)
- date: 2026-10-06
- relates: conflicts SB §7(a) ("JPEG is done by DSP sa_ cores / sa_jpeg_enc") and A-PART-008 (sa_jpeg_enc_* exist) — see Conflicts

### A-CTRL-011: The hook candidate `0xc3889760` (gate `r4[0x3c]` in {1,2}) is an always-run encode-input stage
- status: unknown
- evidence: detour built and verified offline, but it grained via the wrong pointer `session[0x3e24]`; per-capture invocation count never established; hypothesis not confirmed
- source: GH §3 "Dead ends"; SB §4c
- date: 2026-10-06
- relates: —

### A-CTRL-012: The develop core `0xc37ea42e` is called 31 times per capture and overwrites `session[+0x5e4]` after the Soft Focus stage, so earlier grain survives only on tiles written after the DSP finished (explains the "noise quadrat bottom-left")
- status: hypothesis
- evidence: explanation fitted to the marker and grain tests; not directly observed
- source: DG §1
- date: 2026-10-07
- relates: —

---

## PIPE — capture pipeline findings that bear on delivery

### A-PIPE-001: ARM-side grain (wrapper on the Soft Focus sites, or at the last develop step rec40) does not reliably reach the SOOC JPEG: luma HP-std 0.7-1.8 in all builds (v2/v3/v4/v5), amplitude-independent; a zero marker over 6 MB of `session[+0x5e4]` gave 0% black
- status: verified-hw
- evidence: builds `p3_v2..v5`, `p3_markrec40`; HP-std measured on saved JPEGs (07.10.2026)
- source: DG §1; GH header; ST ("ГЛАВНОЕ 07.10")
- date: 2026-10-07
- relates: supersedes A-PIPE-002

### A-PIPE-002: The ARM hook gives working, verified film grain in saved JPEGs, reboot-persistent and stable (06.10 night)
- status: refuted
- evidence: the 07.10 measurements (A-PIPE-001); the earlier "verified" was premature (visible noise and enlarged file size were observed, but the metric shows base sensor noise only)
- source: GH §status (06.10); SB §4g; ST ("ЗЕРНО РАБОТАЕТ SOOC")
- date: 2026-10-06
- relates: refuted by A-PIPE-001; the mechanism parts of GH (hook, delivery) remain valid (A-PIPE-003)

### A-PIPE-003: The wrapper hook itself executes on the camera: 8 `bl Stage_SoftFocus` sites redirected to a wrapper at cave `0xc3a011c0`, which optionally calls the real stage, writes the buffer, and returns the stage result; replacing Stage_SoftFocus wholesale breaks develop -> SF -> encode (crash after preview)
- status: verified-hw
- evidence: marker `0xdeadbeef` read from scratch; whole-stage replacement crashed after preview; wrapper version stable
- source: GH §1, §3; SB §4f, §4g
- date: 2026-10-06
- relates: —

### A-PIPE-004: No native grain generator exists in the firmware (mono effects = contrast-amplified sensor noise, HP~3; only subtractive NR, AAC audio noise, unused H.264 SEI)
- status: hypothesis
- evidence: static searches in av-cam and SA modules; HC Mono measurement (verified-hw part: no native grain, HP~3). Searches covered idt_cam/p3 modules; the ~30 modules of p8 `/usr/sabin` were probably not all searched
- source: DG §6; ST (07.10 entries); FH "Зерно"
- date: 2026-10-07
- relates: scope weakened by A-PART-008

### A-PIPE-005: The JPEG still encoder is a separate hardware encoder driven from `0xc35dcxxx`
- status: hypothesis
- evidence: call-graph reading (A-CTRL-010); contradicted in spirit by SB §7(a) ("JPEG does the DSP, sa_jpeg_enc") and the 09.10 module list (sa_jpeg_enc_* modules)
- source: GH §2; SB §7(a)
- date: 2026-10-06
- relates: conflicts A-CTRL-010 statement in SB; see Conflicts

---

## IDT / MOD — idt_cam overlays and SA modules (only as far as the delivery/boot sources state them)

### A-IDT-001: `idt_cam.bin` is 35 loadable overlays; each begins with the stub `5f50 5e50 5150 b100 ...` (`ldr sp; ldr r14; ldr r1,=entry; bl r1; str 0->[0x48208]; wfi`), header word `+0x18` = stack, `+0x1c` = entry, load address = page + 0x10; each overlay mixes scalar code, literal pools, data tables (e.g. 65536/n reciprocal table in `0x11280`) and VLIW kernels
- status: verified-code
- evidence: correction 09.10.2026; overlay `0x105d0` read in full (base `0x2010`, entry `0x21cc`)
- source: DG §7; ST (09.10 correction)
- date: 2026-10-09
- relates: supersedes A-IDT-002

### A-IDT-002: `idt_cam` is a v4 SA descriptor with scalar code `~0x820..0xa598` (control only) and one contiguous VLIW region `0xa598..0x2ea68` (~148 KB) holding the pixel math; the whole stills develop pipeline (demosaic/WB/colour/NR/sharpen/tone -> YC) is idt_cam
- status: refuted
- evidence: superseded by the 35-overlay structure (A-IDT-001); the "cores" at `0xf6c0`, `0x105d0`, `0x11280`, `0x12cd0`, `0x249d0`, `0x2d4e0` are overlays; NOP bundles executed as scalar code are branching garbage; overlay `0x105d0` is a statistics stage with no pixel write-back
- source: DG §3
- date: 2026-10-09
- relates: superseded by A-IDT-001, A-PART-008

### A-IDT-003: NOP-fill experiments on idt_cam ranges (build_nopcore.py, flashed with `current_p3` recovery) produced these observations: `0x1c000..0x2ea68` image normal but save hangs; `0xa598..0x1c000` focus hangs and dies on shot; `0x13000..0x1c000` normal; `0xe800..0x13000` black luma with focus OK; `0xe800..0x10c00` black; `0x10c00..0x13000` very bright then dies; single `0x2d4e0` and `0x249d0` no effect
- status: verified-hw
- evidence: on-camera observations 07.10.2026 (observations only; the stage interpretations "encode", "develop+live view", "luma write", "luma tone" are retracted, see A-IDT-004)
- source: DG §4
- date: 2026-10-07
- relates: interpretation refuted by A-IDT-004

### A-IDT-004: Campaign A interpretation: `0xe800..0x13000` of idt_cam is the late luma write/tone stage and the grain target
- status: refuted
- evidence: NOP bundles run as scalar code are garbage with branches (`dc3e` = `bfc`); the symptoms are indirect; overlay `0x105d0` is a statistics stage and the 2-4 stop overexposure came from a corrupted literal pool / kernel -> wrong AE/DRO; overlay skip is non-specific (A-IDT-006); `0x11280` and `0x12520..0x13000` are not used by stills
- source: DG §4 (original), §7 (correction); ST (09.10 correction)
- date: 2026-10-09
- relates: refuted by A-IDT-001, A-IDT-006

### A-IDT-005: Overlay `0x105d0` (base `0x2010`, entry `0x21cc`) is a mailbox service loop (DMA desc `0x48234`, go `0x48230`, irq `0x48208`; param check `+0x348`, handler `+0x3c8`) that DMA-reads lines into double buffer `0x8000/0x8800`, loads engine regs `0x40000..0x40058`, runs a VLIW kernel per line, exports 5 accumulators (`0x40078..`) + 64 B to ARM (`0x80380000` write desc); no pixel write-back — a statistics stage
- status: verified-code
- evidence: full read of the overlay (09.10)
- source: DG §7
- date: 2026-10-09
- relates: —

### A-IDT-006: Skipping an overlay (stub `bl r1` -> nop; `build_skipov.py`) is non-specific: skipping `0xf6c0`, `0xcbd0` or `0x105d0` gives the same symptom (live view blinks 1/4000 f/16, save hangs); it only proves "ARM waits for this overlay"
- status: verified-hw
- evidence: three skip builds flashed and observed (09.10)
- source: DG §7; ST (09.10 correction)
- date: 2026-10-09
- relates: —

### A-IDT-007: Overlay `0xf6c0` writes 2D blocks from local `0x9000` (looks like an AE/AWB grid); overlay `0x11280` is not used by stills (NOP whole overlay -> normal); `0x12520..0x13000` NOP -> normal
- status: verified-hw
- evidence: NOP result on camera for the last two; the "writes 2D blocks" reading from code (verified-code), the AE/AWB-grid interpretation is hypothesis
- source: DG §7
- date: 2026-10-09
- relates: —

### A-IDT-008: SA bundle format (verified in `vliw/slots` decoders): 64-bit bundle = 12-bit S0 + 4 x 13-bit slots, slot = `op3.a5.b5`; NOP bundle `0x1f70fb87dc3ee1f7`; 8 op3 codes all used; a zero zone of ~543 B near `0x2e606` is a candidate for baked tables
- status: verified-code
- evidence: `sonygen/isa/{vliw,vdump,vengine,slots}.py` decodes
- source: DG §3, §5
- date: 2026-10-07
- relates: the zero-zone usefulness is moot after A-IDT-001 (overlays, not one VLIW blob)

### A-IDT-009: The op3 -> operation map, register-file indexing, and which VLIW core writes luma cannot be recovered offline; the only oracle (Soft-Focus sharp/blur pair) exercises only mul/add/mov
- status: hypothesis
- evidence: argued in DG §3 and ST ("op3 — определённый вывод"); not demonstrated beyond the attempt
- source: DG §3; ST
- date: 2026-10-07
- relates: —

### A-IDT-010: Does any idt_cam overlay write image pixels at all, or is idt_cam on the 3N purely a 3A/statistics engine with the pixels done by fixed-function ISP / other SA modules?
- status: unknown
- evidence: next step recorded: offline classification of all 35 overlays by DMA pattern (per-line read + per-line write = pixel); tools `~/nex3n-dump/work/nopcore/`
- source: DG §7
- date: 2026-10-09
- relates: now has to be asked together with the p8 modules (A-PART-008)

### A-MOD-001: The 3N SA module `.bin` format/ISA is shared with other Sony bodies; `sa_*.bin` use their own undocumented ISA; scalar core is documented in `sony-dsp-isa.md`
- status: hypothesis
- evidence: only referenced as context in these sources (FH "DSP", ST); full evidence belongs to other extracts
- source: FH "ИТОГ 05.10"; ST
- date: 2026-10-05
- relates: —

### A-MOD-002: av-cam opens an SA module by codectype; a "prefix + name from Backup swapped through `/setting/`" route for replacing a module does not exist (the `0x00bd0000` references were random bytes)
- status: refuted
- evidence: refuted 05.10 in `nex3n-sa-interface.md` (not in the assigned sources; statement is quoted in FH)
- source: FH "ИТОГ 05.10 / DSP"
- date: 2026-10-05
- relates: —

### A-MOD-003: av-cam contains a built-in buffer-dump subsystem to the card gated by a debug switch: `MSDumpYCTarRef`, `MSDumpSAAPL`, `STAR_Debug_MSDump`, `YKNR_Debug_MSDump`, `RAWDEV_DEBUG_MSDump`, `BDRO_Debug_MSDump`, `InitialMsDebug`; paths `/mnt/YC_FILE%04x.dat`, `/mnt/FILE%04x.dat`, `/mnt/cc_ms_log*.dat`; gate `Camera::...Senser::camdebug_get_file_switch_info` (log "off" when disabled); string xrefs: YKNR @0xc3a0eb4d, MSDumpYCTarRef @0xc3a0d2b5 (pool near file 0x3982ac/0x398488), STAR @0xc3a0eaea
- status: verified-code
- evidence: string xrefs in av-cam; the gate source (Backup block `0x00030056`? or a debug command) was not resolved
- source: SB "НАХОДКА: штатный debug-дамп буферов на карту"
- date: 2026-10-06
- relates: the existence of YKNR/STAR/BDRO dump names supports A-PART-008 (separate NR/BDRO modules)

### A-MOD-004: The gate of the MSDump subsystem is controlled by a Backup bit (probably block `0x00030056`) and could be enabled with `bk w` to dump YC buffers to the card
- status: hypothesis
- evidence: note-only; "next step" was to disassemble `camdebug_get_file_switch_info`; no result recorded in these sources
- source: SB "НАХОДКА: штатный debug-дамп"
- date: 2026-10-06
- relates: —

---

## DLV — delivery and flashing

### A-DLV-001: Senser / service mode (PMCA-RE `serviceshell`) authenticates on the NEX-3N with the generic keys and gives live `readMemory(base,size)` / `writeMemory(base,data)` (PFUNC MemoryDump `0xff03`) on ARM physical memory, `FileControl` (`0xff01`: readFile/writeFile/deleteFile), Backup read/write/save (AdjustControl `0x603`), and a terminal
- status: verified-hw
- evidence: `smem.py <base> <size> <out>`, `ssurvey2.py`, readbacks (64 KB, 4 MB, 24 MB sweeps); writeMemory readback MATCH
- source: LM "senser"; SB "ПРОРЫВ", "ПОДТВЕРЖДЕНО ОПЕРАБЕЛЬНО"
- date: 2026-10-06
- relates: —

### A-DLV-002: Entering service mode requires USB = Mass Storage set explicitly (the USB mode resets to MTP/Auto after a reboot); after a session a clean re-entry needs a power-cycle
- status: verified-hw
- evidence: session practice 06.10.2026
- source: SB "ПОДТВЕРЖДЕНО ОПЕРАБЕЛЬНО"
- date: 2026-10-06
- relates: —

### A-DLV-003: senser `readMemory` does not reboot the camera (it returned to the shooting screen); the interactive terminal exits only host-side by SIGINT (Ctrl-C byte is not forwarded)
- status: verified-hw
- evidence: session observations
- source: ST (06.10 entry); SB "ПОДТВЕРЖДЕНО ОПЕРАБЕЛЬНО"
- date: 2026-10-06
- relates: —

### A-DLV-004: A senser RAM patch (writeMemory over `Stage_SoftFocus`, or detour cave `0x83a011c0` + trampoline `0x83889772`) never survives to a capture: writing requires service mode, and leaving service mode (or auto power-off) reboots the camera, reloading the stock av-cam; confirmed three times (DSC09519 HF noise top/bottom ratio 1.01)
- status: verified-hw
- evidence: post-shot region equals the original, av-cam base 64/64; numeric HF ratio 1.01 on DSC09519
- source: GH §3; SB §4b, §4e; LM "senser"
- date: 2026-10-06
- relates: supersedes the early note in ST ("RAM-доставка — только правка файла через FileControl")

### A-DLV-005: Senser `writeFile('/setting/...')` works (readback MATCH), `writeFile('/system/...')` fails with error 130; direct replacement of `/system/av-cam.bin` through FileControl is impossible
- status: verified-hw
- evidence: `/setting/gtest.bin` OK and deleted; `/system/av-cam.bin` and `/system/gtest.bin` error 130 (06.10.2026)
- source: SB §4d; LM "senser"; GH §3
- date: 2026-10-06
- relates: refutes SB §4b/§4c "delivery = senser FileControl writeFile of av-cam"; refutes ST ("Доставка — только правка файла `/system/av-cam.bin` через senser FileControl") — see Conflicts

### A-DLV-006: The updater shell (OpenMemories `updaterShellCommand`, model fdat `NEX-3N.hdr`/`CXD4132.dat`) switches the camera to updater mode (on-screen confirmation) and gives a BusyBox-like root shell with `writeFile` (PUSH), `readFile` (PULL), `shell`, `info`, `bk`, `bootloader`, `bootrom`; `dd`, `md5sum`, `mount`, `cp` present, `od`, `head`, `id` absent
- status: verified-hw
- evidence: sessions 04-07.10.2026; pull of the block device produced the dump
- source: LM "updater shell"; FH "Как подключаться к камере"
- date: 2026-10-06
- relates: —

### A-DLV-007: Raw partition write works: `writeFile('/dev/nflasha3', image)` flashes p3 despite the read-only filesystem layer
- status: verified-hw
- evidence: multiple flashes with md5 verification of the whole partition
- source: LM "updater shell"; SB §4f
- date: 2026-10-06
- relates: —

### A-DLV-008: Flash pipeline (`code/grain/flash_any.py <img> <device> <recovery>`): (1) read live `/system/av-cam.bin`, (2) patch in the p3 inner image at `0x8e00`, `lzpt_write`, pad `0xFF` to 10485760, verify offline by decompress+compare, (3) updater `writeFile('/dev/nflasha3', img)` then md5 of whole partition (`dd if=/dev/nflasha3 bs=65536 count=160 | md5sum`), restore recovery on mismatch, (4) zero WBI (`dd if=/dev/zero of=/dev/nflasha5 bs=512 count=1`), reboot
- status: verified-hw
- evidence: md5 verification passed; 10+ NOP/patch cycles
- source: LM "Flash pipeline"; SB §4f, §4g; DG §4, §6
- date: 2026-10-07
- relates: —

### A-DLV-009: Zeroing the first sector of p5 (WBI) after a p3/p8 write is mandatory: otherwise the old image is restored from the snapshot instead of re-reading `/system/av-cam.bin`
- status: hypothesis
- evidence: every successful flash zeroed WBI first; no run without zeroing is recorded as a control
- source: FA "Boot chain and WBI"; SB §2; LM "Flash pipeline"
- date: 2026-10-06
- relates: supports A-BOOT-018

### A-DLV-010: A narrow p3 write (only inside av-cam; LZPT block table unchanged; 38 sectors from sector 8849) is safe and works; the k0 film curve was written that way (rollback `work/tone/p3_orig_sect_8849.bin` + WBI reset); k14 straddles two 64 KiB blocks (`k0 + 14 x 0x800`)
- status: verified-hw
- evidence: gray scale DSC09509 vs 09510 (05.10)
- source: FH "ИТОГ 05.10"
- date: 2026-10-05
- relates: —

### A-DLV-011: A full p3 rewrite as flashed by `flash_any.py` touches the whole partition including vmlinux/initrd, so an interrupted write is the real risk; mitigation is verify-before-reboot and restore in the same session
- status: hypothesis
- evidence: reasoning; no interrupted write occurred in 10+ cycles
- source: LM "Flash pipeline"; SB §4f
- date: 2026-10-06
- relates: —

### A-DLV-012: A p8 string patch (`share/app/string_english.uxc`, e.g. "Sunset" -> "House " same-length, or "Soft Focus" -> "Film Grain") differs from stock in about 140 sectors (9215-9354) because of LZPT repacking; string entry format `[u16 id][00][1e] UTF-8 \0` aligned to 4 B, offsets in 4-byte words, no checksum; "Sunset" id `0x69`, offset `0x2a8c`, 7-char slot
- status: verified-code
- evidence: built test p8 `work/mod/`; whether a modified p8 was ever flashed to the camera is not stated consistently (LM says the label "was renamed", FH/SB describe only a built image, ST says "завтра флешить")
- source: FH "Что выяснено"; LM "Flash pipeline"; GH §1
- date: 2026-10-05
- relates: see Conflicts / open questions on whether p8 has been written on hardware

### A-DLV-013: Not done and judged riskier: patch `im.elf` to load `/setting/av-cam.bin` (flag `/setting/avtest`, unlink+sync before load, zero p5, new string needs a code cave because `/setting/av-cam.bin` is 19 chars vs 18), redirect the Loader2 table at Backup `0x00FA0080`, serviceshell remount rw
- status: hypothesis
- evidence: design only (SB §3, §8); never built; p8 is read-only through FileControl (checked for `/system`; `/usr/bin/im.elf` write not recorded)
- source: SB §3, §4d, §8; GH §3
- date: 2026-10-06
- relates: —

### A-DLV-014: The `/setting/env.txt` mechanism (init `putenv`) can pass variables to bootin/im and thereby influence target/dmode
- status: hypothesis
- evidence: init reads the file (A-BOOT-013); whether `im.elf`/`bootin.elf` read a relevant variable is unchecked
- source: SB §6, "Открытые проверки"
- date: 2026-10-04
- relates: —

### A-DLV-015: Backup writes (`bk w` / `bk patch`) return Success with readback verification and survive reboot; protected (attribute 01) blocks go only through `bk patch` (rewrites the whole Backup); both banks must be written (`0x00030001` and `0x00030008`), then `bk s`
- status: verified-hw
- evidence: sessions 04-05.10.2026 (matrix tags v1..v5 written and observed)
- source: FH "Как подключаться к камере", "Состояние камеры на ночь 04→05.10"
- date: 2026-10-05
- relates: —

### A-DLV-016: Entering the updater from the running firmware asks for confirmation on the camera screen; if not pressed within 30 s the script gives up but the camera still goes to updater, after which pmca cannot read the model and needs `-m NEX-3N`
- status: verified-hw
- evidence: session behaviour 04.10.2026
- source: FH "Как подключаться к камере"
- date: 2026-10-04
- relates: —

### A-DLV-017: The updater-mode Linux is a recovery environment: only USB/storage/memstick + `dmm` + `mcmn_drv` and the MCMND daemon (Backup works) are up; imaging/SA engine and av-cam are not up, `/system` is empty, `liro.ko` is absent from `/kmod`; `/dev/mem` and `/dev/kmem` exist; nodes `/dev/mcmn` (249,18), `/dev/ldec` (252,200), `/dev/dmac` (241,0), `/dev/jet/adj_drv` (248,22); modules of p3 are version-compatible (vermagic `2.6.29.6-rt24-alp_nl SMP preempt mod_unload ARMv6`)
- status: verified-hw
- evidence: read-only recon in the updater shell (06.10.2026); vermagic compare offline
- source: SB "Live-разведка окружения апдейтера"
- date: 2026-10-06
- relates: —

### A-DLV-018: Delivering code needs a normal-firmware run (the SA engine only runs under the full firmware: kernel symbols + av-cam RTOS), which means a write of p3/p8
- status: verified-hw
- evidence: A-BOOT-010 and A-DLV-017
- source: SB "Итог по стенду (решающий)"
- date: 2026-10-06
- relates: note: "write of p3/p8 = irreversible brick" in ST is contradicted by A-SAFE-002

---

## SAFE — safety and rollback

### A-SAFE-001: Never-touch Backup blocks: `0x00030002` (white-balance calibration of this body), `0x00bc0000/0002`, `0x01320000` (bad-pixel maps)
- status: hypothesis
- evidence: owner's rule from block analysis; no experiment
- source: FH "Состояние камеры на ночь 04→05.10"
- date: 2026-10-04
- relates: —

### A-SAFE-002: A bad av-cam does not brick the camera: Linux and the updater path are on other partitions; a broken av-cam (SF stage replaced wholesale -> crash after preview; diag build; hung NOP builds) was always recovered by flashing the previous p3 image, 10+ NOP/patch cycles with zero bricks
- status: verified-hw
- evidence: sessions 06-09.10.2026; recovery images `current_p3.bin`
- source: LM "Flash pipeline"; DG §6; GH §3
- date: 2026-10-07
- relates: conflicts ST ("запись p3/p8 = необратимый кирпич") and FH "Восстановление"

### A-SAFE-003: The file flag `/setting/updater/mode` does not enter the updater: an empty `mode` with an existing `comp` + reboot -> camera boots normally and the flag is consumed
- status: verified-hw
- evidence: test of 05.10.2026
- source: FH "05.10 — страховка через /setting/updater/mode НЕ работает"
- date: 2026-10-05
- relates: conflicts A-BOOT-015 (code reading says the file triggers updater; maybe the file content/format was wrong)

### A-SAFE-004: If p8 breaks, the camera cannot be recovered programmatically (updater is reached only by jumpers or the `\updater\mode` file, which only the main firmware or the updater can create) — only opening the camera (jumper/UART)
- status: hypothesis
- evidence: code reading of Loader2 (A-BOOT-015) + failed file-flag test (A-SAFE-003)
- source: FH "Восстановление", "ИТОГ 05.10"
- date: 2026-10-05
- relates: conflicts SB §5 ("USB/updater on p1+p3-initrd stays even if p8 is broken"); conflicts A-SAFE-005

### A-SAFE-005: A broken p8 `im.elf` patch keeps USB/updater access, since entering the updater is decided by Loader2 and the updater kernel lives on p1; p8 would be repaired by flashing p8 from the updater; fatal only for corruption of p1/p3 (updater kernel+initrd) or Loader2
- status: hypothesis
- evidence: reasoning only, no p8 failure test
- source: SB §5
- date: 2026-10-04
- relates: conflicts A-SAFE-004; also in tension with A-SAFE-002 (p3 was rewritten 10+ times without trouble, yet is listed as "fatal")

### A-SAFE-006: A hung build (NOP'd/broken luma in idt_cam) stalls the "writing to memory card" step; a battery-pull reboot clears it and flushes the pending frame; NOP/skip images are recoverable
- status: verified-hw
- evidence: Campaign A runs 07.10.2026
- source: DG §4
- date: 2026-10-07
- relates: —

### A-SAFE-007: Recovery images and hashes: stock p3 `sonygen/out3n/nflasha3` md5 `37b9727627b91ebeefdc07dcde561036`; current camera p3 `current_p3` md5 `d7cca446...` (film curve, no grain); full dump md5 `44606c...`; 8 Backup snapshots `Backup*.bin`; `Backup.bak` on the device; originals `00030001_orig.txt`, `30106_orig.txt`
- status: verified-code
- evidence: file hashes recorded in notes
- source: SB "ПЛАН: прошивка дампера" Страховка; ST (09.10 entry); FH
- date: 2026-10-09
- relates: —

### A-SAFE-008: A one-shot test-boot harness (flag file `/setting/avtest` consumed with `unlink`+`sync` before loading, zero p5, `fn=/setting/av-cam.bin`; dmode=2 isolation; `bk w 00510023 00` to stop snapshots) would limit crash-loop risk
- status: hypothesis
- evidence: design only (never implemented); depends on unverified A-BOOT-019, A-DLV-013
- source: SB §3, §4, §8
- date: 2026-10-04
- relates: —

### A-SAFE-009: Write only with a charged battery (flat batteries stopped the 05.10 session; Power Save set to 30 min; `pkill -9 -f ptpcamerad` before MTP calls)
- status: hypothesis
- evidence: session anecdote
- source: FH "Пауза 05.10"
- date: 2026-10-05
- relates: —

---

## TOOL — tools and environment

### A-TOOL-001: `code/lzpt/lzpt_write.py` is a byte-exact LZPT writer that reproduces stock p3 and p8; fwtool (ma1co) only reads LZPT. It uses a multiprocessing Pool, so any caller must be under `if __name__ == "__main__":` or it fork-bombs on macOS/Windows (spawn)
- status: verified-code
- evidence: round-trip comparison with stock images; fork-bomb observed on macOS/py3.14
- source: FA "LZPT"; LM "Flash pipeline" gotcha; SB §4g
- date: 2026-10-06
- relates: —

### A-TOOL-002: `flash_any.py` (updater raw flash + md5 verification + restore + WBI zero) and `build_set.py` (grain preset images) are the delivery scripts; run via pmca with `SUDO_ASKPASS=./askpass.sh sudo -A env DYLD_LIBRARY_PATH=/opt/homebrew/lib venv/bin/python flash_any.py <img> /dev/nflasha3 current_p3.bin`; keystone from brew + `DYLD_LIBRARY_PATH`; the Python binding on 3.14 needs `setuptools`
- status: verified-hw
- evidence: used 06-09.10.2026
- source: SB §4g; GH "Tools"; ST
- date: 2026-10-06
- relates: —

### A-TOOL-003: NOP/skip experiment builders: `build_nopcore.py` (p3 with clean/film-curve av-cam and a NOP'd idt_cam range), `build_skipov.py` (stub `bl r1` -> nop), `build_difflog2.py` (encode-handler detour logger); dir `~/nex3n-dump/work/nopcore/`; the pmca environment is `~/nex3n-dump/work/pmca/venv` + `flash_any.py` (old scratchpad cleaned)
- status: verified-hw
- evidence: used on the camera 07-09.10.2026
- source: DG §5, §7; ST (09.10 entry)
- date: 2026-10-09
- relates: —

### A-TOOL-004: Static RE tools: `avgraph.py` (recursive Thumb call graph from task entries), `xref.py` (full-image BL xref; 30k targets, 168k call sites; `xref.py <va>` lists callers), venv `~/nex3n-dump/.venv` with capstone 5.0.7; DSP side `sonygen/isa/{sadis,vliw,vdump,vengine,slots}.py`
- status: verified-code
- evidence: tools in repo `code/isa/`
- source: GH "Tools"; SB §4; DG §5; FH
- date: 2026-10-06
- relates: —

### A-TOOL-005: senser scripts: `smem.py <base> <size> <out>` (one readMemory), `ssurvey2.py <out>` (64 KB x 1 MB sweep), `sread.py`, `sdump_multi.py`, `find_devsession.py`, `sfileread.py`/`swritefile.py`/`sfiletest.py`; pmca is run from source through libusb (`/opt/homebrew/lib/libusb-1.0.dylib` injected into pyusb) with sudo, because the Sony macOS driver does not install; venv packages `pyusb pycryptodomex pyyaml asn1crypto certifi tlslite-ng axmlparserpy==0.0.4` (+ `numpy pillow scipy`); `session.sh` drives updatershell via FIFO and `live.log`
- status: verified-hw
- evidence: sessions on macOS 27
- source: FH "Как подключаться к камере", "Уборка 05.10"; SB §4a, "ПОДТВЕРЖДЕНО ОПЕРАБЕЛЬНО"
- date: 2026-10-06
- relates: —

### A-TOOL-006: Reference firmware for comparison: official NEX-F3 v1.01 and NEX-6 v1.03 (`support.d-imaging.sony.co.jp/download/IMT/Update_NEXF3V101.exe`, `Update_NEX6V103.exe`; DAT is stored raw in the exe, cut from the signature `\x89UFU\r\n\x1a\n`); unpack with `fwtool unpack -f nex3n_v100_nflasha.bin -o out3n`; 05.10 cleanup removed downloaded firmware, unpacked trees and venvs (~12 GB), to be re-downloaded
- status: verified-code
- evidence: notes; files deleted 05.10
- source: FH "Где что лежит", "Уборка 05.10"
- date: 2026-10-05
- relates: —

### A-TOOL-007: The SD card mounts on the Mac as `/Volumes/Untitled` (`DCIM/100MSDCF`); MTP via gphoto2 needs `pkill -9 -f ptpcamerad` before each call; listing the current day's folder fails with `-103 File exists` (unsolved)
- status: verified-hw
- evidence: sessions 04-05.10.2026
- source: FH "Состояние камеры на ночь 04→05.10", "05.10 — плёночные стили"
- date: 2026-10-05
- relates: —

---

# Conflicts

1. **Where is the cold-boot load of av-cam decided?** FA states as fact that the av-cam config entry is gated off in normal cold boot; SB §1 explicitly calls this [HYP] (mask bits not decoded per entry) and lists it among unverified checks. Likewise FA states "later warm boots restore RAM from p5 without re-reading the file" as fact while SB marks it [HYP]. (A-BOOT-005, A-BOOT-018)
2. **Which sabin modules exist and what does idt_cam do.** DG §3/ST (07.10) say the 3N has only `idt_cam` + `sa_dfdet` and that "the entire develop pipeline is idt_cam" — refuted 09.10 (35 overlays; p8 `/usr/sabin` with ~30 modules). Internal inconsistency inside the old notes: SB itself uses `sa_func_SFTFCS_start`, the sftfcs program at `@0x2420`, `sa_jpeg_enc_*`, `YKNR_Debug_MSDump`, and GH §2 names SFTFCS/TBOX callers of `ExecuteCalcStartMSG`. (A-PART-008/009, A-IDT-001/002, A-MOD-003)
3. **Who encodes the JPEG?** SB §7 says the DSP (`sa_jpeg_enc`, zima cores) encodes under CamCore control; GH §2 says it is a separate hardware encoder reached via `tsk46_jpeg` -> `0xc35dcxxx` and unreachable through the SA-start mechanism; the 09.10 module list contains `sa_jpeg_enc_*`. Unresolved whether `sa_jpeg_enc_*` modules drive the hardware encoder (mailbox). (A-CTRL-010, A-PIPE-005)
4. **Delivery route and what survives.** ST (early 06.10 entries) says "only a file edit of `/system/av-cam.bin` through senser FileControl" and SB §4b/§4c plan `writeFile('/system/av-cam.bin')`; SB §4d and LM show `/system` is read-only (error 130) and the real route is raw p3 write through the updater shell. ST's header line "ЗЕРНО РАБОТАЕТ SOOC" and GH's status line "working, flashed, verified" are refuted by DG §1 (07.10). (A-DLV-004/005/007, A-PIPE-001/002)
5. **Brick risk of writing p3/p8.** ST (op3 section): "run code under normal firmware = write p3/p8 = irreversible brick, boundary holds"; SB §5: p8 is repairable via updater, fatal only for p1/p3/Loader2; FH: if p8 breaks, no programmatic recovery; LM/DG: p3 rewritten 10+ times, zero bricks, recovery restore works. Also: Loader2 code reading (jumper or `\updater\mode` file) vs hardware test where the `/setting/updater/mode` flag did not enter the updater. (A-SAFE-002..005, A-BOOT-015)
6. **Width of the YC canvas and the 0x85900000 buffer.** LM writes width 4928 with stride `0x2660` (= 4912 x 2); FA/GH/SB/ST write 4912 for `DMM_HANDLE_YCC_FULL` and 4928 for the session buffers (`session[+0x5e4]`, YC copies). The same base `0x85900000` is reported as the 4912-wide YC_FULL of one shot (SB §4a) and as the stride-1280 raster (6 MB) holding the Soft Focus pair (SB "ВЕХА"). (A-MEM-005, A-MEM-010)
7. **CPU count.** Normal kernel: 2 processors (SB §1, FA); updater kernel: 3 ARMv6 (SB recon). (A-SYS-001/003)
8. **Cache coherency vs alias.** SB §1 describes `0xc3441000` as the non-cacheable alias of `0x83441000`, while SB §7(d) requires a D-cache flush after modifying buffers before the DSP reads them. Not reconciled. (A-BOOT-003)
9. **Was the modified p8 ever written to the camera?** LM: "The menu label was renamed the same way on p8 (Soft Focus -> Film Grain)"; FH/SB describe only a built test image ("House"); ST says the p8 filmgrain image was to be flashed "tomorrow"; FH 05.10: "Claude no longer prepares writes to firmware partitions". (A-DLV-012)
10. **liro load address parameter:** `adr` (SB §1, im.elf command `adr=0x%x`) vs `adrs` (SB offline analysis of liro.ko). (A-BOOT-008)
11. **Scope of "no native grain / SA modules do not add noise":** statements in GH/DG/FH/ST were made when only p3 modules were known; need re-check against the p8 modules. (A-PIPE-004, A-PART-008)

# Open questions

1. Which of the ~30 p8 `/usr/sabin` modules write image pixels, and does any `idt_cam` overlay (of 35) write pixels at all? (A-IDT-010, A-PART-008)
2. How does a `sa_jpeg_enc_*` module relate to the hardware JPEG encoder at `0xc35dcxxx`; where is the "buffer -> encoder" hand-off (enc_param address)? (A-CTRL-009/010)
3. What is the real mode mask of every Loader2 config entry (is av-cam loaded by Loader2 in any boot mode)? (A-BOOT-005)
4. Does the camera re-read `/system/av-cam.bin` on every boot, or restore from WBI; is a WBI zero strictly required (no control run without zeroing)? What gates snapshot creation (`0x00510023`)? (A-BOOT-018/019, A-DLV-009)
5. Why does a senser RAM patch not survive — file reload or WBI restore of an unpatched snapshot? The notes assume "reloaded from file". (A-DLV-004)
6. What are the exact trigger conditions of the updater entry (file `\updater\mode` content/format vs jumpers) and is the updater reachable if p8 is broken? (A-BOOT-015, A-SAFE-003/004/005)
7. Roles of p4, p6, p7, p10, p12, and of `/android`, `/info`. (A-PART-011)
8. Is the third CPU of the updater kernel real, and does it matter for the main firmware? (A-SYS-003)
9. Does the MSDump debug-to-card gate (`camdebug_get_file_switch_info`, maybe Backup `0x00030056`) exist as a Backup switch; was it ever tried? (A-MOD-003/004)
10. Handle -> DRAM accessors (`0xc36045fc`, `0xc36046ac`) unresolved: how to get base and stride generically. (A-MEM-012)
11. Does a modified p8 / `im.elf` write get through (FileControl read-only for `/usr`; updater raw write of `/dev/nflasha8` not recorded as tested)? (A-DLV-012/013)
12. Is the SA engine register space truly unreachable from ARM (explicit read of `0x40000+` not recorded)? (A-SYS-006)
13. Which YC copy in the session object feeds the JPEG encoder, and what is the stride-1280 buffer at `0x85900000`? (A-MEM-005/009/010)
