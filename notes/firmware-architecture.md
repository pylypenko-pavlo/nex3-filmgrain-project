# NEX-3N firmware architecture: partitions, LZPT, boot, DRAM

Static analysis of the flash dump plus live confirmation. This is the layout the
grain work (`grain-hook.md`) and the delivery method (`live-memory-and-delivery.md`)
sit on top of. Firmware images/dumps are not shipped; supply your own.

## Flash partitions

The camera's NAND is one MBR device. In the updater kernel its partitions appear as
`/dev/nflasha0pN` (major 252); in the normal Linux they are also reachable as
`/dev/nflashaN`. Sizes (1 KiB blocks, from `/proc/partitions` in the updater shell):

| part | blocks | ~size | role |
|---|---|---|---|
| nflasha0p1 | 4096  | 4 MB  | updater / boot1 area |
| nflasha0p2 | 3072  | 3 MB  | `/setting` (vfat, **rw**) — the Backup property store lives here |
| nflasha0p3 | 10240 | 10 MB | `/system` — **LZPT-packed**, holds `av-cam.bin`, `vmlinux.bin`, `initrd.img`, `sabin/`, lens data |
| nflasha0p4 | 6144  | 6 MB  | |
| nflasha0p5 | 40960 | 40 MB | **WBI** — fast-boot RAM snapshot (`WBI1` magic at offset 0) |
| nflasha0p6 | 5120  | 5 MB  | |
| nflasha0p7 | 35840 | 35 MB | |
| nflasha0p8 | 46080 | 45 MB | `/usr` — **LZPT-packed**, holds `im.elf`, `bootin.elf`, apps, `share/app/string_*.uxc` (menu strings) |
| nflasha0p10/12 | 2816/1024 | | |

What is writable (observed): only `/setting` (p2) is writable as a filesystem (via the
senser `FileControl` or the updater shell). `/system` (p3), `/usr` (p8), `/android`,
`/info` are read-only filesystems (they are compressed images). To modify p3/p8 you
rewrite the **raw partition** (see `live-memory-and-delivery.md`), not files.

## LZPT ('TPZL') compressed partitions

p3 and p8 are not plain filesystems on flash — each raw partition is an **LZPT image**
(magic `TPZL`): a table of contents followed by 64 KiB input blocks, each independently
compressed into 16 x 4 KiB LZ77 sub-streams. A read-only `axfs`-style layer presents the
decompressed filesystem at runtime, which is why the fs is read-only.

- Layering: raw partition (LZPT, e.g. p3 = 10 MB) → decompressed inner image (a FAT
  filesystem image, p3 ≈ 14.4 MB) → files. `av-cam.bin` sits at a fixed offset in the
  p3 inner image (offset `0x8e00`, contiguous, full size 6554072).
- The format and a **byte-exact writer** are in `code/lzpt/lzpt_write.py` (fwtool only
  reads LZPT; the writer is this project's, reverse-engineered from the Sony images and
  verified to reproduce the stock p3/p8 byte-for-byte). To change `av-cam.bin`: patch it
  in the inner image, `lzpt_write` → raw partition image, pad with `0xFF` to the
  partition size, write the raw device.
- Reference reader/analysis: ma1co `fwtool.py` (`fwtool/archive/lzpt.py`).

## Boot chain and WBI

Cold boot: Loader2 (`boot/boot1`, Ver.31.23.12) reads a **config table from Backup**
(BKID `0x00FA0080`, 64 x 144-byte records; non-empty: `\sabin\idt_cam.bin`,
`\sabin\sa_dfdet.bin`, `\av-cam.bin`, `\kemco.txt`, `\initrd.img`, `\vmlinux.bin`). Each
record has start/end VA, a boot-mode mask and a CPU id. Loader2 loads `vmlinux`+`initrd`
on CPU0; the config entry for av-cam is gated off in normal cold boot.

The RTOS image `av-cam.bin` is loaded at **runtime by Linux**, not Loader2:
`/sbin/init` → `bootin.elf` → `im.elf` (on p8) runs
`insmod liro.ko fn=/system/av-cam.bin load=1` — `liro.ko` reads the file from p3 and
starts the RTOS on CPU1. (`/system/av-cam.bin` string is hard-coded in `im.elf`.)

**WBI (p5)** is a RAM snapshot for fast start. On the first cold boot `liro` reads
av-cam from the file; on subsequent warm boots Loader2 restores RAM from p5 and the file
is not re-read. So after changing `av-cam.bin` on flash you must **invalidate WBI**
(`dd if=/dev/zero of=/dev/nflasha5 bs=512 count=1`) or the old image is restored from
the snapshot. `liro` participates in the snapshot (`[LIRO]: liro resume/suspend (WBI)`).

## CPUs and DRAM

Linux 2.6.29-rt, ARMv6 SMP, 2 cores: CPU0 = Linux/userland, CPU1 = av-cam RTOS (µITRON).
The av-cam CPU is **ARMv6 without Thumb-2** (constants are built with `movs`+`adds`/shifts,
never `movw/movt`; no `usat`) — patches must be plain 16-bit Thumb-1 (`+ bl`/`blx` which
are the only legal 4-byte encodings). See `grain-hook.md`.

DRAM is 512 MB mapped at `0x80000000` (256 MB physical, mirrored: `0x80x…` ≡ `0x90x…`).

- av-cam image: virtual base `0xc3441000`, loaded in physical DRAM at `0x83441000`
  (**phys = virt − 0x40000000**, confirmed live: a senser read of phys `0x83441000`
  matches the image 99%, the ~1% being runtime-filled tables such as the service table).
- Imaging buffers live in the reserve from `0x84000000`. The developed YC canvas
  (`DMM_HANDLE_YCC_FULL`) is a dynamically-allocated YUYV 4:2:2 buffer ~4912 wide (stride
  `0x2660`); its base moves between captures. Buffer pointers inside av-cam structures are
  **bus addresses** (bit 31 clear, e.g. `0x0a000000`); the av-cam CPU accesses the same
  DRAM at virtual `bus | 0xc0000000`.
- The SA DSP engine's internal registers (`0x40000+`) are DSP-local and **not mapped into
  ARM physical memory** — they cannot be read from the ARM side (neither `/dev/mem` nor
  senser), which is the observability wall for the VLIW/op3 work (`sony-dsp-isa.md`).
