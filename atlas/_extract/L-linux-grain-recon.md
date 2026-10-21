# NEX-3N — Linux-side (CPU0) grain path: offline recon

Static analysis only, 09.10.2026. No camera access, no partition writes, no flashing. Source
dumps: `~/nex3n-dump/safeboot/out3n/nflasha{2,3,7,8}_unpacked*`, full flash dump
`~/nex3n-dump/nex3n_v100_nflasha.bin`. Disassembly via a local capstone/pyelftools script
(scratch, not kept). **[OK]** = confirmed by direct disassembly/strings in this session;
**[HYP]** = plausible from code structure, not traced to certainty; **[?]** = not found.

## TL;DR

- **libmpr.so** (`/usr/lib/libmpr.so`, on p8) is confirmed to export `MprLib::DecodeStillOnMemory`
  / `MprLib::EncodeStillOnMemory` and the `MprIfMcmd` command-table wrappers around them
  (`DecodeStillOnMemorySubCmd` etc. — these are the handlers for the `MPR` text-command
  console, i.e. this is reachable today from `testcmd.elf`/`sndcmd.elf` without writing any
  new code). Their debug logging dumps `srcVirtAddr/srcSize/sizeX/sizeY` (decode) and
  `srcVirtAddr/srcSizeX/srcSizeY/dstSizeX/dstSizeY/dstBufVirtAddr/dstBufSize` (encode) —
  **confirms the API is virtual-address/size based**, i.e. userland hands it already-mapped
  buffers, not file paths. **[OK]**
- **No in-camera init hook reads a file from `/setting` or the SD card to auto-run a custom
  binary** — but there **is** a generic, already-wired mechanism to inject environment
  variables (including `LD_PRELOAD`) into the whole Linux boot tree, gated purely by a
  **p2-only** (`/setting`) write: writing the byte `'0'` anywhere into
  `/setting/mode/dmode` makes `/sbin/init` parse `/setting/env.txt` and `putenv()` every
  `KEY=VALUE` line in it, **before** forking `bootin.elf`/`im.elf`/the appFw process tree, so
  the vars propagate to all of them. **[OK, see §3]**. This is the best zero-p8-write lever
  found.
- **WriteStill completion is an internal MPR event (`WriteStillCmp`/`FlushWriteStillCmp`,
  `EV_WRITE_END_LAST_RECORDING_UNIT`), not a filesystem signal.** There is no public
  `inotify`-style hook on `/DCIM`; the kernel has `CONFIG_INOTIFY`-independent code (fat fs
  driver built in, no inotify syscalls referenced that I found), so filesystem watching from
  an injected process would need polling, not kernel notify. **[HYP — inotify absence is
  from absence of evidence, not a negative proof]**
- Toolchain: GCC 4.3.3 "Sony CE Linux 6.0.0.4", EABI5, proprietary libc/libstdc++/pthread
  (`libsonyc.so`, `libsonystdc++.so.6.0.10`, `libsonypthread.so`) and a **custom dynamic
  linker** `/lib/libsonyld.so` (not glibc's `ld.so`, but it understands standard
  `LD_PRELOAD`/`LD_LIBRARY_PATH`/`LD_BIND_NOW` env vars — confirmed by strings). Kernel is
  Linux 2.6.29.6-rt24, ARMv6 SMP (2 cores; CPU0 Linux/userland, CPU1 av-cam RTOS). **[OK]**
  Best build strategy: a **static, libc-free binary** that only makes raw Linux syscalls
  (open/read/write/mmap/ioctl) — sidesteps the proprietary libsonyc ABI entirely and only
  needs a normal arm-linux-gnueabi cross toolchain. **[recommendation, not yet tried]**
- **Risk is unchanged from what `nex3n-safe-test-boot.md`/`nex3n-firmware-hacking.md`
  already documented**: p8 is LZPT-compressed (`TPZL`), so any p8 code change still means a
  full raw-partition rewrite with the known round-trip risk (interrupted write = possible
  brick of the updater-path-independent partition); **the env.txt/dmode route needs *no*
  p8 write at all** — only p2 (`/setting/env.txt`, `/setting/mode/dmode`), which is the
  already-proven-safe `bk`/FileControl write path. This is the main practical upside of the
  finding in §3.

---

## 1. libmpr.so: JPEG decode/encode entry points

File: `nflasha8_unpacked_unpacked/lib/libmpr.so` (ELF32 ARM EABI, `DT_SONAME libmpr.so`;
deployed at `/usr/lib/libmpr.so` at runtime, loaded by the appFw process tree spawned from
`im.elf`'s `a` target). **[OK]**

Exported (`.dynsym`, demangled) **[OK, confirmed by symbol table]**:

```
MprLib::DecodeStillOnMemory(...)                 0x5d52bd
MprLib::DecodeStillOnMemoryToRegion(...)         0x5d5367
MprLib::EncodeStillOnMemory(...)                 0x5d53f9
MprIfMcmd::DecodeStillOnMemory(long,char**)       (text-console cmd handler)
MprIfMcmd::EncodeStillOnMemory(long,char**)       (text-console cmd handler)
MprIfMcmd::SetDecodeStillOnMemorySetSrc/SetDst(...)
MprIfMcmd::SetEncodeStillOnMemorySetSrc/SetDst(...)
MprIf::EncodeStill(MprIf::EncodeStillParam*)      0x16f4b7 — thin wrapper, logs then calls MprIfLog::EncodeStill + a sibling at +0x10 in a vtable-ish object (indirect, not resolved)
MprIf::WriteStill / FlushWriteStill / MakeWriteStillImage
FeaIf::EncodeStill / WriteStill / FlushWriteStill / PlayStillSingleByAddress
```

Disassembly of `MprLib::DecodeStillOnMemory` (0x5d52bd) and `EncodeStillOnMemory` (0x5d53f9)
**[OK]**: both build an 8-field parameter block on the stack from *already-set* static/TLS
fields (populated earlier by `MprIfMcmd::SetDecodeStillOnMemorySetSrc/SetDst`, which is how
the text-console path assembles the call), then do `blx` through an **internal import
veneer** (`ldr ip,[pc,#4]; add ip,ip,pc; bx ip`, not a `.plt` entry — these are
intra-library indirections, likely for a vtable/interface-pointer call) to
`MprLibCore::...` implementations, and log:

```
DecodeStillOnMemory : dstVirtAddr / maxDstSize / srcVirtAddr / srcSize / sizeX / sizeY /
                       resultWidth / resultHeight
EncodeStillOnMemory : srcVirtAddr / srcSizeX / srcSizeY / dstSizeX / dstSizeY / dstTgtSize /
                       dstBufVirtAddr / dstBufSize
```

**[OK — confirmed, these are the real field names from `.rodata` strings, directly
following the call in the disassembly]**. This confirms the API shape (**not** a file-path
API: it takes process-mapped virtual addresses and sizes for src/dst), matching
`live-memory-and-delivery.md`'s plan to decode→noise→encode.

I did not reach the actual hardware/codec call inside `MprLibCore::DecodeStillOnMemory`
(0x5f...-range, not resolved this session — the call graph fans out through
`MemInfo::GetUnitInfo()` and region/unit-handle helpers that are large and un-named).
**[?]** Whether the codec work happens via a software JPEG codec on CPU0, or via a hardware
block reachable from Linux, is **not resolved**. One concrete lead not yet chased: a live
recon of the *updater* kernel (recorded in `nex3n-safe-test-boot.md` §"Live-разведка
окружения апдейтера") found a device node **`/dev/ldec` (major 252, minor 200)** present
in the device list even in the stripped-down recovery Linux — a name consistent with
"local/linux decoder", i.e. **a hardware JPEG/video decode path that may be exposed to
Linux independently of av-cam's SA DSP engine**. If real, `DecodeStillOnMemory` likely
drives this via `ioctl()`, not a software decode loop — worth probing with `strace`-style
tracing (`ltrace`/senser-based read of `/proc/<pid>/maps` + `/dev/ldec` ioctl numbers) on
the live camera, which is out of scope for this offline pass. **[HYP]**

Who calls `WriteStill`/`EncodeStill`/`FlushWriteStill` (the actual still-recording state
machine) lives in **`libObj.so`** (`ObjStillRecorder`/`ObjPlayer` classes), not in libmpr
itself — libmpr is the lower-level MPR-interface layer; `libObj.so` is the appFw object that
drives the capture pipeline end-to-end and that libmpr.so's `MprIf`/`FeaIf`/`FeaCore`
classes serve. **[OK, from DT_NEEDED graph + symbol overlap: libObj.so needs/exports
EncodeStill/WriteStill/FlushWriteStill/MakeWriteStillImage, and is the only consumer other
than libmpr itself]**.

## 2. Frame-ready signal / who writes the JPEG to card

**[?] No direct file-path write call was traced to completion** (e.g. an `open()`/`write()`
on a `DCIM/.../DSC*.JPG` path) inside libmpr or libObj in the time available — the write
path almost certainly goes through `Fsys_*` (libInfraFsys.so: `Fsys_Open/Write/Close`,
confirmed exported, backed by `mcmn_drv_*`/`mcmn_dmm_*` primitives) rather than a raw
POSIX `write()`, consistent with the camera's layered media-manager design (`AviMMgr`,
`MMgrIf`), not a flat filesystem call. The DCF path template string
`\DCIM\101MSDCF\DSC0%04ld.JPG` is confirmed present in libmpr.so. **[OK string, HYP call
site]**

What **is** confirmed: the completion of a still-recording cycle is an **internal MPR
event message**, not a filesystem notification:

- `libObj.so` strings: `WriteStill :`, `WriteStillCmp :`, `FlushWriteStill :`,
  `FlushWriteStillCmp :`, `PreWriteStill :`, `MakeStillRecInfo :` — these read as a
  state-machine trace (`ObjStillRecorder`), each with a paired "Cmp" (complete) event.
  **[OK]**
- `libmpr.so` event-name tables (`EV_*`) are mostly for movie/audio dubbing (`EV_REC_COMPLETE`,
  `EV_STREAM_END`, `EV_WRITE_END_LAST_RECORDING_UNIT`) — no still-specific `EV_STILL_*`
  completion constant was found as a bare string; still completion appears to be
  signalled through the numeric `MprIf`/`FeaIf` callback mechanism
  (`MprIf::SetCallbackFunc`, confirmed exported in `libmprctrl.so`) rather than a named
  event enum. **[HYP]**
- No `inotify_init`/`inotify_add_watch` import was found in any `.so`/`.elf` on p8 or in the
  p3 initrd (checked `libInfraMediaMount.so`, `libObj.so`, `CameraOnDemandSaver.so`,
  `libJiritsu.so`, `im.elf`, `bootin.elf` — only `mount`/`umount` are imported, never
  `inotify_*`). **[OK absence in checked binaries]**. Kernel support for inotify was not
  checked (would need a `.config`/symbol dump of `vmlinux.bin`, not attempted this
  session) — so this is **not a proof the kernel lacks inotify**, only that no userland
  binary examined uses it. **[? on kernel side]**

**Practical implication for a hook**: there is no cheap "watch the file land" hook without
either (a) polling `/DCIM` from an injected process, or (b) intercepting the `MprIf`
callback (`SetCallbackFunc`) or the `Fsys_Write`/`Fsys_Close` call from inside the appFw
process via `LD_PRELOAD` (see §3) — i.e. *wrap* `Fsys_Close` (or `close()` on the matching
fd) in a shim library, check the path, and on a JPEG re-encode it through
`libmpr`'s own `DecodeStillOnMemory`/`EncodeStillOnMemory` (same address space, so no IPC
needed) before the handle is actually released. This is a cleaner hook than trying to
locate the completion event by name.

## 3. Autostart / injection surface without touching p8 — the real find

Traced `/sbin/init` (p3 initrd, ELF, not a script — confirmed `not stripped`,
`.symtab` present) function by function: `main`, `check_mode_file`, `check_oreore3`,
`check_qemu`, `check_nfs`, `parse_and_set_env`, `set_oreore_env`, `run_bg_process`,
`mount_partition`, `insmod_drivers`. **[OK, full symbol table available, disassembled all
of them]**.

**Mount table is hard-coded** in `.data` (pairs of device/mountpoint/fstype/flags strings
at file offset `0x1229c`+) — `/setting`←`nflasha2` (vfat), `/system`←`nflasha3` (vfat,
LZPT-backed), `/usr`←`nflasha8` (ext2, fallback cramfs, fallback vfat), `/tmp`←`nflasha7`,
`/log`←several. **Nothing here is read from a file; it's static in the init binary.**
**[OK]**

**`check_mode_file()`** (0x8c61) reads `/setting/mode/dmode` (p2, writable) into a 1KB
buffer and does a **byte-by-byte scan** (not a strict parse), setting one flag per
recognized character, independent of position or count:

| byte | flag offset (in global struct @`0x1257c`) | effect |
|---|---|---|
| `0`/`0`(0x30) | `+0x0` | **gates `set_oreore_env()`** (env.txt parsing) — see below |
| `k`/`K` | `+0x18` | sets `LD_PRELOAD=/usr/tool/libkmcsup.so.2.0.0` later in `main()` |
| `g`/`G` | `+0x24` | sets `LD_PRELOAD=/usr/tool/libduma.so` + DUMA_* env vars |
| `d`/`D` | `+0x20` | (DUMA path, same branch as above in this binary's layout) |
| `e`/`E` | `+0x1c` | sets `LD_PRELOAD=/usr/tool/libsonyefence.so` |

**[OK, direct disassembly, hex comparisons `cmp r1,#0x30` etc. against ASCII]**

**`main()`** (0x90ad), after mounting partitions: reads flag `+0x0` (the `'0'` flag) —
**if set, calls `set_oreore_env()` BEFORE forking any child** (`bootin.elf`/`sen.elf` are
only forked later, via `run_bg_process`). **[OK, instruction order confirmed:
`bl set_oreore_env` at 0x918a precedes `run_bg_process("/usr/bin/bootin.elf")` at 0x920c]**

**`set_oreore_env()`** (0x9c5d): opens **`/setting/env.txt`** (p2, writable, confirmed
literal string at file offset referenced from this function), `mmap`s it, and for each
line calls `parse_and_set_env()` → `putenv()` on every `KEY=VALUE` pair found (splits on
`=`, skips blank/`#`-comment lines — confirmed by the `#` char-compare in
`parse_and_set_env`). **[OK]**

Separately, `bootin.elf` **re-reads the same `/setting/mode/dmode` file independently**
with its own byte-scanner (confirmed in `bin/bootin.elf` disassembly, function at
0x9004-0x92c2): each digit `0`–`3` sets a "boot stage" string pointer (**last matching
digit in the file wins**, since each match overwrites the same memory slot and the scan
does not stop); letters `l/L` (LeakTracer), `w/W`/`s/S` (wfree/sslibc flags) OR into a
separate bitmask instead of overwriting. **[OK, confirmed in bootin_dis.txt]**.

**Consequence (derived, not yet tested on hardware — [HYP]):** because `init`'s scan is
presence-only and `bootin.elf`'s scan is last-match-wins *and runs independently*, a
`/setting/mode/dmode` file containing the two bytes **`"03"`** (zero then three) should:
1. make `init` see the `'0'` byte → parse `/setting/env.txt` → `putenv()` every var →
   fork `bootin.elf` with that environment already set;
2. make `bootin.elf`'s own parser see `'0'` first (kernel-only stage) then `'3'` last
   (full appFw stage) → net result: **normal full boot**, not kernel-only — because `'3'`
   is scanned after `'0'` and overwrites the stage pointer.

If this holds, **`/setting/env.txt` + `/setting/mode/dmode = "03"` is a p2-only,
no-p8-write way to set arbitrary environment variables — including `LD_PRELOAD` — for the
entire boot tree**, confirmed to include `im.elf` and whatever it forks (`s/g/r/u/l/i/a`
targets, i.e. the appFw process that loads `libObj.so`/`libmpr.so`). The custom dynamic
linker `libsonyld.so` **does honor `LD_PRELOAD`** (confirmed: the same mechanism is used
deliberately for `libsonyefence.so`/`libduma.so`/LeakTracer, and `LD_PRELOAD` appears in
`libsonyld.so`'s own string table alongside `LD_LIBRARY_PATH`/`LD_BIND_NOW`/`LD_DEBUG`,
i.e. it's a real rtld feature, not a stub). **[OK that the mechanism exists and is used
elsewhere; HYP that the exact `"03"` byte trick avoids the stage conflict — needs an
on-camera dry run with something harmless, e.g. an env var that only prints to a log, before
trusting it for anything real]**

This is strictly better than the `im.elf` p8-patch plan already on file in
`nex3n-safe-test-boot.md` §3 for a **first experiment**: no LZPT repack, no raw-partition
write, no WBI invalidation needed for *this* mechanism (WBI only snapshots RAM state, and
since this changes boot-time environment before the RTOS/appFw comes up fresh each cold
boot anyway, env.txt is reread every cold boot — though if WBI warm-restores before
`set_oreore_env` would even run, the whole init sequence wouldn't re-execute, so a WBI
warm-restore would skip this entirely, same as it skips re-reading `av-cam.bin`; **[HYP]**
needs the same WBI-zero precaution as any other boot-chain experiment).

**What I could not find**: any mechanism where init, bootin.elf, or im.elf read a script or
binary path **from the SD card** directly (no `AUTORUN.INF`-style hook in any of
init/bootin/im; the one `AUTORUN.INF` string found is inside `libObj.so` and is about
*GPS log* autorun data association, not code execution — confirmed by surrounding context
`/PRIVATE/SONY/GPS`). **[OK absence]**

## 4. Toolchain / ABI

- Compiler: **GCC 4.3.3** branded "Sony CE Linux 6.0.0.4" (confirmed `.comment`/strings in
  every `.so`/`.elf` checked). **[OK]**
- `.ARM.attributes`: `TAG_CPU_NAME=ARM926EJ-S`, `TAG_CPU_ARCH=5` (ARMv5TE baseline),
  Thumb+ARM ISA both used, soft-float-ish FP model (`TAG_ABI_FP_NUMBER_MODEL=3`, no VFP
  attribute tag seen). **[OK, read directly from ELF attributes on `libsonyc.so`,
  `sbin/init`]**. This is the **compile target baseline**, not necessarily the real CPU —
  the kernel strings confirm **ARMv6 SMP, 2 cores** (ARM11-class, matches
  `firmware-architecture.md`), so userland is built conservatively for ARMv5TE compatibility
  even though it runs on ARMv6 hardware. **[OK on kernel side, from existing
  `firmware-architecture.md` + confirmed again via `Linux version 2.6.29.6-rt24-alp_nl` +
  `SMP: Total of %d processors activated` strings in `vmlinux.bin` this session]**.
- ELF type: `EABI4` (older tools like `busybox`, `ps`, `chattr`) and `EABI5` (newer, e.g.
  `init`, `libmpr.so`, most camera-specific code) — mixed within the same rootfs, both
  load fine under the same `libsonyld.so`. **[OK]**
- libc/runtime: **not glibc, not uClibc** — a proprietary Sony libc (`libsonyc.so`),
  libstdc++ (`libsonystdc++.so.6.0.10`), pthread (`libsonypthread.so`), unwinder
  (`libsonygcc_s.so.1`), and a **custom ELF interpreter** `/lib/libsonyld.so` (every
  dynamically-linked binary's `PT_INTERP` points here, not to a standard `ld-linux.so`).
  **[OK]**
- Kernel: Linux **2.6.29.6-rt24-alp_nl**, SMP PREEMPT RT, built 2013-01-26. **[OK]**

**Recommendation for building a new binary** (not attempted, no build environment set up
this session): don't try to match the proprietary libc/rtld. Write a **statically linked,
libc-free** binary (direct Linux syscalls only — `open`/`read`/`write`/`mmap`/`ioctl`/`exit`
via `svc #0`), built with any standard `arm-linux-gnueabi-gcc` (or even raw assembly +
manual minimal ELF header) targeting ARMv5TE/soft-float to match the attribute baseline.
This avoids needing Sony's `libsonyc.so`/`libsonyld.so` symbol versions entirely, and the
Linux syscall ABI for arm is stable across the 2.6.29→now range for the calls needed here.
A `LD_PRELOAD`-delivered `.so` (for the §3 hook), by contrast, **does** need to link against
the camera's own `libsonyc.so`/`libsonystdc++.so` if it calls any libc function — or, same
trick, keep it a tiny raw-syscall shim with no libc dependency, exporting only the specific
symbol being interposed (e.g. a wrapped `close()`), which sidesteps the ABI question too.

## 5. Risk

No change to the existing assessment in `nex3n-safe-test-boot.md` / `nex3n-firmware-hacking.md`
for anything that touches p3 or p8: both are **LZPT (`TPZL`)-compressed raw partitions**,
so any binary patch to `im.elf`/`av-cam.bin` still means decompress → patch → `lzpt_write`
repack (byte-exact round-trip already verified for stock images) → raw-partition write via
the updater shell → **md5-verify the whole partition before reboot** → zero WBI
(`/dev/nflasha5`). The already-documented safety net holds: Linux + the updater path live on
partitions independent of `av-cam`/the appFw rootfs, so a bad `av-cam.bin` or a bad
`im.elf` patch does not brick the updater route — **only p1 (updater kernel+initrd) or
Loader2 itself is unrecoverable without hardware access** (per
`nex3n-safe-test-boot.md` §5 and `nex3n-firmware-hacking.md` §"Восстановление").

**What's new here**: the §3 mechanism (`/setting/env.txt` + `dmode="03"`) needs **no p8/p3
write at all** — both files it touches are on **p2**, the partition already proven safe to
write via `bk`/FileControl (vfat, not LZPT, not involved in the updater-recovery argument
at all). This makes it strictly lower-risk than the `im.elf`-patch plan for a **first**
experiment: worst case if it misbehaves is a boot that doesn't come up to appFw (per the
`dmode` digit semantics, a wrong byte combination could accidentally select kernel-only
boot) — recoverable by deleting/overwriting `/setting/mode/dmode` via the same p2 write
path (FileControl/`bk`), no reflash needed.

---

## Recommended path / what to check first

1. **Zero-risk dry run (no code, pure observation):** via the updater shell or senser
   `FileControl`, write a **harmless** `/setting/env.txt` (e.g. a single `TESTVAR=hello`
   line, no `LD_PRELOAD`) and `/setting/mode/dmode = "03"`, power-cycle, then read back
   whether the camera boots normally to a usable state (menus responsive, USB/updater
   still reachable) — confirms the `"03"` byte-order trick doesn't break boot depth before
   anything riskier is tried. This directly tests the §3 [HYP].
2. **If (1) is clean:** try `LD_PRELOAD=/setting/noop.so` with a trivial, syscall-only
   `.so` (one exported symbol, returns immediately) placed on p2, to confirm the custom
   rtld actually loads a preload target from `/setting` at runtime (not just from
   `/usr/tool/`) — this was assumed from the string evidence in `libsonyld.so` but never
   directly exercised in this offline pass.
3. **Only after (1)+(2) succeed:** build the actual grain shim — a small `.so` that wraps
   one `Fsys_*`/`close`-family call (interposed via the same `LD_PRELOAD` mechanism),
   detects a just-written still JPEG, and round-trips it through `libmpr`'s own
   `DecodeStillOnMemory`→(grain on Y plane)→`EncodeStillOnMemory`, writing the result back
   over the same file before the camera's own write handle is released (or immediately
   after, if timing makes in-place safer). This stays entirely inside the already-running
   appFw process, so no new process/thread scheduling questions and no IPC to av-cam.
4. **Chase the `/dev/ldec` lead** (§1) only if (3)'s software path turns out too slow for
   single-shot use — i.e. confirm whether `DecodeStillOnMemory`/`EncodeStillOnMemory`
   actually drive a hardware codec via that device node, which would need either an on-camera
   `ioctl()`-tracing session or deeper disassembly of `MprLibCore::DecodeStillOnMemory`'s
   callees (not reached this session).

Everything above is derived from the dumps already on disk; nothing here required or used
camera access.
