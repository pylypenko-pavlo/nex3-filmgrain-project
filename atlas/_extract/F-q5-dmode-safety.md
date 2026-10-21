# F — Q-5: `/setting/mode/dmode` + `/setting/env.txt` boot-steering safety (static)

Static analysis only, 2026-10-09. No camera access, nothing written, no images prepared.
Sources: `~/nex3n-dump/safeboot/out3n/` — p3 initrd `/sbin/init` (not stripped, md5 `1e63ad94…`),
p8 `bin/bootin.elf`, `bin/im.elf`, `bin/change_mode.sh`, `lib/libObj.so`, `tool/`; p1 updater initrd
(`sbin/init` shell script, `root/*.sh`); p3 initrd `lib/sonyld.so`; p3 `vmlinux.bin`;
`~/nex3n-dump/boot/boot1` (Loader2, VA = file + 0xa01e9000); Backup from `nflasha2_unpacked/Backup.bin`.
Disassembly: capstone 5.0.7 (scratch scripts, not kept). Addresses are file VAs of each ELF.

## 0. Verdict first

**C-BOOT-024 / C-DLV-015 are wrong. `dmode = "03"` does NOT give "env + full boot". It gives a
userland-less, USB-less boot with no software recovery path.** In `/sbin/init`, a `'0'` byte
anywhere in `dmode` makes `main()` skip everything after mounting: the 17 `drivers2` kmods
(including all USB gadget modules), `sen.elf`, the LD_PRELOAD tool options and **`bootin.elf`
itself**. So bootin's "last digit wins" rule never runs. The env.txt gate is not `'0'`: it is
**the presence of the `dmode` file**, with any content, including empty. The safe form is `"3\n"`,
the exact bytes Sony's own `change_mode.sh 3` writes.

### Value table

| `dmode` content | init (p3 initrd) | bootin.elf (p8) | what runs | recovery channels (a) senser/FileControl, (b) pmca updater via running FW, (c) Loader2 `\updater\mode` / jumper, (d) menu reset | risk |
|---|---|---|---|---|---|
| file absent (stock) | flag+0=0 → env.txt NOT read; normal path | stage default `"3"` | full boot (stock) | a: only after a service-mode request (smode "UU") · b: yes · c: jumper; file needs a writer (a/b) · d: yes | none |
| empty file, `"\n"`, `"\r\n"` | file opened → **env.txt parsed**; no recognised byte → normal path | no digit → default `"3"` | full boot + env.txt | a, b, d: yes (stock code path) · c: as stock | low (depends only on env.txt) |
| `"3"`, `"3\n"` (Sony default, `change_mode.sh 3`) | env.txt parsed; `'3'` ignored by init | stage 3 → `im.elf s g r u l i a &` | full boot + env.txt | same as stock | **low: the recommended form** |
| `"1"` | env.txt parsed; normal path; drivers2 loaded; sen.elf only if smode "UU" | stage 1 → `im.elf s g r` | kernel + "global infra", **no app thread (no appFw, no UI)** | a: only if smode "UU" already exists (init starts sen.elf independently of the stage) · b: **no** (the service/updater request is handled by appFw/libObj, see F-BOOT-006) · c: jumper only · d: no (no menu) | **high (effectively a brick)** |
| `"2"` | same as `"1"` | stage 2 → `im.elf s g r u l` (adds LIRO, av-cam) | as 1 + av-cam, no appFw | as `"1"` | **high** |
| `"0"`, `"03"`, `"30"`, any content containing `'0'` | flag+4 set → `main` jumps to 0x922e: **no drivers2 (no usbg_sen/usb_extcmd/usb_portMonitor/dmm/upm/mcmn_drv…), no check_oreore3/sen.elf, no bootin.elf**; mounts `/sys`, `putenv("LD_PRELOAD=")`, `/bin/ash` loop on the console (cmdline has `console=ttynull`, so the console is dead) | never started | kernel + init + an idle shell; **no USB function at all**, no UI, no power-off handling | a: no · b: no · c: jumper only (no live process can create `\updater\mode`) · d: no | **brick-level (hardware jumper/UART)** |
| contains `k`/`K` or `d`/`D` (e.g. `"3k"`, `"3d"`, the word "mode") | `LD_PRELOAD=/usr/tool/libkmcsup.so.2.0.0` or `/usr/tool/libduma.so`; **neither file exists on p8** | (k, d ignored) | sonyld: preload fails → `_rtld_die` → **bootin.elf, sh, im.elf and sen.elf all die at exec** | a, b, d: no · c: jumper only | **brick-level** |
| contains `e`/`E` | `LD_PRELOAD=/usr/tool/libsonyefence.so` (exists) | — | full boot under Electric Fence (slow, crash-prone) | probably as stock if it comes up; untested | high |
| contains `g`/`G` | init runs `system("/usr/bin/bootin.elf")` in the foreground ("GDB" branch), so sen.elf starts only after bootin returns | bootin flag 0x10 → `system("gdb --args im.elf …")`; **no gdb on p8** | no im.elf → no appFw | a: maybe (if bootin returns and smode "UU") · b, d: no · c: jumper | **brick-level** |
| contains `l`/`L`, `w`/`W`, `s`/`S` | ignored | LeakTracer preload (exists in `/usr/tool`), wfree, gdbserver prefix | debug builds of the boot | unknown | high, avoid |
| last digit ≠ 3 (`"31"`, `"32"`) | normal path, env parsed | stage 1 or 2 | as rows `"1"`/`"2"` | as `"1"` | high |
| other garbage without `0 k K d D e E g G l L w W s S` and whose last digit, if any, is 3 | env.txt parsed | stage 3 | full boot | as stock | low |

**Timing gate (applies to every row):** Backup `0x00510023` = `0x02` selects **ssboot** in Loader2.
While the p5 snapshot signature is valid (and `0x00510029` RestReq = 0, which is the case), every power-on
restores RAM from p5 and **init does not run**. A `dmode`/`env.txt` change therefore acts only on the
first boot after the WBI is invalidated (sector 0 zeroed, a p3 flash, LSI crash, RestReq). The consequence
cuts both ways. A bad `dmode` can sit unnoticed and turn into a brick at a later crash-induced cold boot.
A test, in turn, has to invalidate the WBI on purpose, or it observes nothing (F-BOOT-012).

## 1. Evidence

### 1.1 `/sbin/init` `check_mode_file()` @0x8c61 (struct base `.bss` 0x1257c)

```
8c76 open("/setting/mode/dmode", O_RDONLY)       ; adr → 0x8cf4
8c80 bge 8c8e ; else return -1                   ; file absent: no flag at all
8c94 read(fd, buf, 0x400) ; close
8ca8 str r6,[r7]          ; flag+0x00 = 1  ← set whenever open() succeeded, BEFORE the length test
8caa ble 8cea             ; empty file: loop skipped
8cac ldrb r1,[buf+i]
8cae cmp r1,#'0' → str [r7,#4]      ; flag+0x04
8cb6 'k'|'K'    → str [r7,#0x18]
8cc2 'g'|'G'    → str [r7,#0x24]
8cce 'd'|'D'    → str [r7,#0x20]
8cda 'e'|'E'    → str [r7,#0x1c]
```

`main()` @0x90ad, after the mounts:

```
9180 bl check_mode_file
9184 ldr r0,[r4]      ; flag+0 (file exists)
9188 beq 918e
918a bl set_oreore_env           ; env.txt
918e ldr r0,[r4,#4]   ; flag+4 ('0')
9192 bne 922e                    ; ── '0' → skip all of the below
9194 insmod_drivers(drivers2 @0x122a8, 0x11)   ; unidrv2, usb_portMonitor, usbg_sen, usb_extcmd,
                                               ; kikilog, dmm(DmmConfig=…), upm, hdmi, cec, accel,
                                               ; mag, compass, mcmn_drv, ms_drv, mmc_drv, sata_drv, msen_drv
919c bl check_oreore3            ; smode → flag+0x10
91a0 flag+0x18 (k) → putenv("LD_PRELOAD=/usr/tool/libkmcsup.so.2.0.0")      @0x94ec
91b6 flag+0x1c (e) → putenv("LD_PRELOAD=/usr/tool/libsonyefence.so")        @0x9514
91c6 flag+0x20 (d) → putenv DUMA_* x4, system("echo 1000000 > /proc/sys/vm/max_map_count"),
                     putenv("LD_PRELOAD=/usr/tool/libduma.so")              @0x953c
91f6 flag+0x24 (g) → profile "GDB"; system("/usr/bin/bootin.elf")   (foreground)
920a           else → run_bg_process("/usr/bin/bootin.elf")         @0x95f4
9210 flag+0x10      → run_bg_process("/usr/bin/sen.elf")            @0x9608
921c "<<init end>>"
922e mount_partition(/sys)  ; putenv("LD_PRELOAD=") @0x9630 ; fork → execv(/bin/ash --login) loop
```

`drivers1` (loaded before the dmode check) is only `/kmod/unidrv1.ko`. With `'0'`, no USB gadget
kmod is ever loaded.

`check_oreore3()` @0x8da1: `open("/setting/sen/smode")`, read 256 B, `strncmp(buf,"UU",2)`; on a match,
`open("/proc/dump_bootmode")`. If that fails, or `strncmp(.,"BIS",3)` ≠ 0, flag+0x10 = 1. It then
calls `check_cho()` (`/setting/mode/cmode` == "CC" → flag+0x14). Stock p2 has no `/setting/sen/`,
so **in a normal boot init does not start `sen.elf`**. `libObj.so` holds `mkdir -p /setting/sen; echo UU > /setting/sen/smode`,
and `im.elf` @0xa726 does its own smode/"UU" + `/proc/udm/upm_bootmode` check and contains `"sen.elf &"`.
The service mode is reached through a request handled by the running firmware.

`set_oreore_env()` @0x9c5d: `open("/setting/env.txt")` (absent → return 0) → `fstat` (size 0 → return) →
`mmap(PROT_READ, MAP_SHARED)` (fail → fprintf, return −1) → `parse_and_set_env(buf,size)`.

`parse_and_set_env()` @0x9955 grammar:
- Whitespace (ctype space: SP, TAB, CR, LF, VT, FF) separates tokens; NUL bytes are skipped between tokens.
- `#` starts a comment that runs to the next CR/LF/VT/FF.
- Each token (max 1024 B) is `malloc`'d. With `=` it goes to `putenv(token)`; without `=` it goes to **`unsetenv(token)`**.
- So `KEY=a b` sets `KEY=a` and unsets `b`. A bare word `PATH` on a line unsets PATH. Values cannot contain spaces.
- putenv errors are only printed. Nothing in the parser can crash init (bounded copies), and init itself is not re-exec'd.

### 1.2 `bootin.elf` dmode scanner (stripped, Thumb) @0x9016..0x90a4, mapping @0x92ca..0x9328

```
9016 open("/setting/mode/dmode") ; 902c read(fd, sp, 0x1e)      ; ≤30 bytes
903c '0'..'3' → [0x12390+0xc] = "0".."3"          ; last digit wins
905e 'l'|'L' → flags|=2 ; 'w'|'W' → |=8 ; 'g'|'G' → |=0x10 ; 's'|'S' → |=0x20
.data 0x1239c default = 0xa1e1 → "3 "            ; missing / empty / no digit = stage 3
92d6 '0'→"s " ; '1'→"s g r " ; '2'→"s g r u l " ; '3'→"s g r u l i a " ; other→"s "
8c9a flags&0x10 → "gdb --args im.elf " else "im.elf "     ; no gdb binary on p8
8da6 system(cmd)   ; im.elf launched via /bin/sh, inheriting init's environment
8dae "Bb clearing env": LT_CHECK_PROCESS/LD_PRELOAD only if flags&2, MALLOC_OPTIONS only if flags&8 — after the launch
```

`bin/change_mode.sh` (p8) documents the stages: 0 kernel · 1 + global infra · 2 + LIRO · 3 + appFw (default).
It writes `echo 3 > /setting/mode/dmode`, i.e. `33 0a`. Variants are `1n/2n/3n` (no unified driver), `3L`, `3w`, `3k`,
`3g`, `3s`, `3d`, `3e`. `im.elf` contains no "dmode" string and does not read the file.

### 1.3 Dynamic linker: a failed LD_PRELOAD is fatal

`/lib/sonyld.so` is a NetBSD `ld.elf_so` derivative (strings `_rtld_*`, `LD_TRACE_LOADED_OBJECTS`, `LD_WARN`).
Main @0x5ac8: `getenv("LD_PRELOAD")` → `_rtld_preload` @0x2554 (strsep loop; a load failure returns −1) →
`cmn r0,#1; beq 0x5d84` → `bl 0x56a4` = `_rtld_die` ("Fatal error", exit). An empty `LD_PRELOAD=` returns 0
(harmless). **Any dynamically linked program exec'd with a missing or unloadable preload dies before `main`.**
That covers bootin.elf, busybox `sh` used by `system()`, im.elf and sen.elf. A preload that loads but crashes
in its constructor kills the same set. Not established: whether a preload is also loaded into static binaries
(none in the boot chain).

### 1.4 Loader2: updater entry, ssboot, cmode

```
a01efe50 boot_is_updater:
  a01efe52 bl a01efe34   ; jumper: [0xa0010024]==4 && (0xf3060000>>8 &0xf)==2 → 1
  a01efe5c fat_mount(2)  ; p2
  a01efe78 adr "\updater\mode" ; bl a01f28d0 (FAT open) ; >=0 → return 1
a01f009a boot_init_mode:
  a01f00fe bl boot_is_updater → mode 3 (UPDATER)      ; FIRST check, before ssboot/warm
  a01f010a bl a01f0020 (\mode\cmode == "CC", boot_is_adjust) → mode 5
  …
  a01f051a hotboot (CA "BI flag") → mode 2
  a01f0526 boot_is_warmboot: Backup 0x00510023 == 1 && WBI sig … → mode 0xa
  a01f0532 boot_is_ssboot @a01f0630: Backup 0x00510023 == 2 && WBI sig OK (a01f12ec)
                                     && RestReq 0x00510029 == 0 → mode 0xb
```

Backup on this body (dump and all snapshots): `0x00510023 = 02`, `0x00510029 = 00`, `0x00510028 = 01`.
Loader2 never reads `dmode` or `env.txt`. It reads `\updater\mode` (existence only; `comp` is not consulted)
and `\mode\cmode`.

UPDATER branch @0xa01ee2f0: `fat_mount(1)` → `\boot\vmlinux`, `\boot\initrd.img` from **p1**. The p1 initrd
`/sbin/init` is a shell script (`export PATH/LD_LIBRARY_PATH`, `insmod.sh`, `is_valid_boot.sh`,
`UdtrMain.sh`). It reads only `/setting/updater/mode{1,2,3,6}`, `uincomp`, `debug`. `execute_ufp.sh`:
`if [ -e /setting/updater/comp ]; then rm -rf /setting/updater/mode*; fi`. **The updater does not touch
`dmode`, `env.txt` or `kemco.txt`.** `libObj.so` (main firmware) also contains `rm -f /setting/updater/mode*`.

### 1.5 kemco.txt

The p3 `vmlinux.bin` `arch/arm/kernel/setup.c` holds `"kemco"`, `"cmdline override at %p"`, and
`"setup_arch(): invalid cmdline override @ 0x%08x. Using default cmdline."`. p2 `kemco.txt` starts with `kemco\n`
and ends with `*\n`. Together with the Loader2 load-list entry `\kemco.txt` (C-BOOT-002), this means
kemco.txt is the kernel command line, validated only by its magic. No full default cmdline string
was found in `vmlinux.bin` (only fragments `root=`, `mem=`, `console=`).

## 2. Answers to the four sub-questions

1. **Parsing and stages.** See the table. init: presence → env.txt; `'0'` → stage-0-in-init (nothing after the mounts); `k/e/d/g` → tool hooks. bootin: digits, last wins, default 3; `l/w/g/s` → debug modes. CR/LF are ignored by both. `"03"` = kernel-only (init) and the `'3'` is never acted upon.
2. **Recovery per value.**
   - (a) Senser needs appFw to accept the request and init (or im.elf) to start `sen.elf` → available only for "full boot" rows.
   - (b) The pmca updater switch also goes through the running firmware → same rows. Hypothesis: `UpdaterWrapper::enableUpdateMode` in libObj writes the flag.
   - (c) Loader2 `\updater\mode` works by existence only, but something must create the file. When userland is dead nothing can, so only the jumper (`0xf3060000[11:8]==2`, needs opening the camera) remains. E-0021: the code gives Loader2 no reason to ignore the file; `comp` only makes the updater script delete `mode*`. Two explanations fit E-0021 and statics cannot pick one: (i) the updater kernel did start, consumed the flag at once (`comp` present) and rebooted; (ii) Loader2's FAT open failed on the empty file (0xa01f28d0 not decoded to the end). The main firmware's `rm -f /setting/updater/mode*` removes the flag on a normal boot in either case.
   - (d) Menu reset needs appFw. Whether it deletes `/setting/mode/*` or `env.txt` was not found (no such string in p8).
3. **Broken env.txt.** init never crashes: it only putenv's and continues. Every dynamically linked descendant inherits the environment: bootin.elf, `sh` from `system()`, im.elf with the appFw tree, and sen.elf. With a missing or unloadable `LD_PRELOAD`, all of them die at exec, giving no UI, no service mode and no software path to the updater. That is brick-level after a cold boot. A bad `LD_LIBRARY_PATH` has the same effect. A `PATH` without `/usr/bin`, or a bare `PATH` token (which unsets it), makes bootin's `system("im.elf …")` fail. env.txt is read only on boots where init runs, i.e. cold boots (ssboot gate above).
4. **kemco.txt.** It is the kernel cmdline override, loaded by Loader2 through the `\kemco.txt` entry of the Backup `0x00FA0080` list. It is independent of `dmode`. Without the `kemco` magic, the kernel falls back to a default cmdline that is probably unusable (memrsv/wbimem/cmpr/rootfs params are only in kemco). With valid magic but bad params, the result is arbitrary: possibly a panic and a reboot loop (`exception.reboot=1`). The updater branch loads its kernel/initrd from p1. Whether it also passes kemco is not established, because the configurator step 0xa01f1d12 was not decoded. **Treat kemco.txt as never-touch.** A broken kemco would also kill (a), (b) and (d), and probably not (c).

## 3. Claims (temporary IDs)

### F-BOOT-001: init parses `/setting/env.txt` whenever `/setting/mode/dmode` can be opened, with any content including an empty file; the byte `'0'` is not the env gate
- status: verified-code
- evidence: init `check_mode_file` 0x8ca8 `str r6,[r7]` (flag+0) before the length test; `main` 0x9184..0x918a
- source: this extract §1.1
- date: 2026-10-09
- relates: refutes the gate part of C-BOOT-022 and C-DLV-014 (the parse and putenv part stands)

### F-BOOT-002: a `'0'` anywhere in `dmode` makes init skip drivers2 (all USB gadget kmods, dmm, upm, mcmn_drv …), sen.elf, the tool preloads and bootin.elf; the boot ends at an idle console shell with no USB function
- status: verified-code
- evidence: `main` 0x918e `bne 0x922e`; drivers2 table 0x122a8 (17 entries); kemco `console=ttynull`
- source: §1.1
- date: 2026-10-09
- relates: refutes C-BOOT-024 and C-DLV-015; refines C-BOOT-012 and C-BOOT-023 (bootin never sees the '0' of a file containing '0'); answers C-SAFE-013 for stage 0 (not reachable)

### F-BOOT-003: init letter hooks are `k`→libkmcsup, `e`→libsonyefence, `d`→libduma + DUMA_* + max_map_count, `g`→bootin run in the foreground; `/usr/tool` holds only `LeakCheck`, `LeakTracer.so`, `libsonyefence.so`
- status: verified-code
- evidence: `main` 0x91a0..0x9208; p8 `tool/` listing
- source: §1.1
- date: 2026-10-09
- relates: corrects C-BOOT-022 ("g/d → libduma"); with F-LNX-001, `k`/`d` are brick-level

### F-BOOT-004: bootin reads ≤30 bytes of `dmode`; digits 0-3, last wins, default "3" when the file is missing, empty or has no digit; `l/w/g/s` set LeakTracer/wfree/gdb/gdbserver; stage → im.elf targets 0 "s", 1 "s g r", 2 "s g r u l", 3 "s g r u l i a"; `g` runs `gdb --args im.elf`, and gdb is absent
- status: verified-code
- evidence: bootin 0x9016..0x90a4, 0x92ca..0x9328, `.data` 0x1239c → "3 ", 0x8c9a
- source: §1.2
- date: 2026-10-09
- relates: confirms C-BOOT-023; refines C-BOOT-012 (bootin stage 0 still starts `im.elf s`)

### F-BOOT-005: Sony's own `change_mode.sh` writes `"3\n"` for the default mode; this is the reference content for a `dmode` that keeps a full boot
- status: verified-code
- evidence: p8 `bin/change_mode.sh`
- source: §1.2
- date: 2026-10-09
- relates: replaces the "03" recipe of C-BOOT-024 / C-DLV-015 / Q-1

### F-BOOT-006: in a normal boot init does not start sen.elf; it does so only when `/setting/sen/smode` starts with "UU" (written by libObj on a service-mode request) and `/proc/dump_bootmode` ≠ "BIS"; im.elf has its own smode check and `sen.elf &`
- status: verified-code (init, strings); the im.elf path is hypothesis
- evidence: init `check_oreore3` 0x8da1; libObj string; im.elf 0xa726
- source: §1.1
- date: 2026-10-09
- relates: refines C-BOOT-006 ("init starts sen.elf"); C-DLV-001, C-DLV-002; Q-5(a)

### F-BOOT-007: `env.txt` grammar: tokens split on any whitespace, `#` comments to end of line, `KEY=VAL` → putenv, a token without `=` → unsetenv, ≤1024 B per token; missing file, size 0 or mmap failure → no-op
- status: verified-code
- evidence: init `parse_and_set_env` 0x9955, `set_oreore_env` 0x9c5d
- source: §1.1
- date: 2026-10-09
- relates: C-BOOT-022, C-DLV-016

### F-LNX-001: sonyld treats a failed `LD_PRELOAD` load as fatal (`_rtld_preload` −1 → `_rtld_die`), so a bad preload in env.txt kills every dynamically linked process exec'd after init (bootin, sh, im.elf, sen.elf)
- status: verified-code
- evidence: sonyld 0x5ac8..0x5adc → 0x5d84 → 0x56a4; 0x2554
- source: §1.3
- date: 2026-10-09
- relates: refines C-DLV-016 and C-LNX-006 (in 02); worsens the Q-1 step-2 risk

### F-BOOT-008: Loader2 enters the updater when the jumper is set or when `\updater\mode` on p2 can be opened; `comp` is not read; this is the first check of `boot_init_mode`, before ssboot/warm boot
- status: verified-code
- evidence: boot1 0xa01efe50..0xa01efe88, 0xa01f00fe
- source: §1.4
- date: 2026-10-09
- relates: confirms C-BOOT-015; contests the conclusion of C-SAFE-004 / E-0021 (see F-BOOT-009)

### F-BOOT-009: `/setting/updater/mode*` has two consumers: the updater's `execute_ufp.sh` (deletes it when `comp` exists) and the main firmware (`libObj.so` "rm -f /setting/updater/mode*"); so E-0021 does not show that Loader2 ignores the file
- status: verified-code (strings, scripts); the E-0021 explanation is hypothesis
- evidence: p1 initrd `root/execute_ufp.sh`; libObj strings
- source: §1.4
- date: 2026-10-09
- relates: E-0021, C-SAFE-004, C-SAFE-005 (the "only firmware can create it" part holds: in practice the writers are appFw, senser or the updater)

### F-BOOT-010: the updater boot is independent of `dmode`, `env.txt` and `smode`: Loader2 loads p1 `\boot\vmlinux` + `\boot\initrd.img`, and the updater init is a shell script reading only `/setting/updater/*`
- status: verified-code; whether the updater kernel also gets `kemco.txt` is unknown (configurator 0xa01f1d12 not decoded)
- evidence: boot1 0xa01ee2f0..0xa01ee380; p1 initrd `sbin/init`, `UdtrMain.sh`
- source: §1.4
- date: 2026-10-09
- relates: C-SAFE-006, C-DLV-019

### F-BOOT-011: Backup `0x00510023` selects the snapshot flavour in Loader2 (1 = warmboot, mode 0xa; 2 = ssboot, mode 0xb); the 3N has 0x02, so every power-on with a valid p5 signature and RestReq `0x00510029` = 0 restores RAM and init does not run
- status: verified-code (Loader2 checks; Backup values); "init does not run on ssboot" is hypothesis
- evidence: boot1 0xa01efe94 (warm, ==1), 0xa01f0630 (ssboot, ==2), 0xa01f0660 (RestReq)
- source: §1.4
- date: 2026-10-09
- relates: refines C-BOOT-016 and C-BOOT-019 (0x00510023 is a mode selector, not just a gate); supports C-BOOT-018 and C-DLV-009; answers part of Q-19

### F-BOOT-012: `dmode`/`env.txt` act only on a boot without a valid WBI, so a bad `dmode` can stay dormant and brick at a later cold boot (crash, p3 flash, WBI zero)
- status: hypothesis (derived from F-BOOT-002 and F-BOOT-011)
- evidence: —
- source: §0
- date: 2026-10-09
- relates: C-SAFE-013, Q-1, Q-19

### F-BOOT-013: `kemco.txt` is the kernel command line: the kernel accepts the RAM copy only if it starts with the magic `kemco`, else it uses a built-in default; Loader2 does not read `dmode`, but reads `\mode\cmode` ("CC" → boot_is_adjust, mode 5)
- status: verified-code (kernel strings, file framing, Loader2); that the default cmdline cannot boot the camera is hypothesis
- evidence: vmlinux.bin 0x17dcb1..; kemco.txt `kemco\n … *\n`; boot1 0xa01f0054
- source: §1.5
- date: 2026-10-09
- relates: upgrades C-BOOT-025 to verified-code for "is the cmdline"; Q-16

### F-SAFE-001: the only `dmode` contents that keep all four recovery channels are "file absent" and a full-boot form free of `0 k K d D e E g G l L w W s S` with no last digit other than 3; recommended `"3\n"` (`33 0a`)
- status: verified-code (per F-BOOT-001..004)
- evidence: —
- source: §0
- date: 2026-10-09
- relates: replaces the C-SAFE-013 blanket ban by a whitelist; C-DLV-015 refuted

## 4. Verdict on Q-1 (dry run with a harmless env.txt)

**Safe enough to run, but not with "03".** With `dmode = "3\n"` and `env.txt = "TESTVAR=hello\n"`, the boot is the
stock code path plus one `putenv`. Static residual risk is low; recovery by a jumper is still the only net if
something unforeseen happens on a cold boot.

Conditions:
1. Write the files **from the updater shell** (`/setting` is mounted rw there, C-DLV-019). The updater does not depend on these files, and in the same session the WBI sector 0 can be zeroed. Without the zeroing, ssboot restores the old RAM and the test sees nothing.
2. Byte-check both files before leaving the updater:
   - `dmode` is exactly `33 0a` (2 bytes);
   - `env.txt` is only `TESTVAR=hello\n`, with no `LD_*`, `PATH`, `MALLOC*` or bare words;
   - neither file contains a `0`, `k`, `d`, `e`, `g`, `l`, `w` or `s` in `dmode`.
3. Save the stock state: `/setting/mode/` was empty, so the rollback is `rm /setting/mode/dmode /setting/env.txt`.
4. Charged battery (C-SAFE-010).

Minimal first test, in order:
- (a) env.txt alone. Inert: without `dmode`, init never opens it.
- (b) `dmode = "3\n"` + WBI zero, cold boot. Pass: camera boots normally, USB service and updater entry still work.
- (c) Read `/proc/<pid>/environ` of bootin.elf or im.elf via the senser terminal and look for `TESTVAR`.
- (d) Delete both files, zero WBI, boot again.

Step 2 of Q-1 (`LD_PRELOAD=/setting/noop.so`) is **brick-level on any load failure** (F-LNX-001), and the env also
reaches sen.elf. Do not try it until a way back that does not need userland is confirmed: for example, the
`\updater\mode` file route (resolve E-0021 by test: create `mode` with `comp` removed, from the updater).
Q-1 step 2 also deserves its own static check of the shim against sonyld's loader (ELF flags, DT_NEEDED,
symbol versioning).
