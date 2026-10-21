# grain-shim

In-camera film grain for the Sony NEX-3N (firmware 1.00). A freestanding Linux `LD_PRELOAD` shim that
interposes `Fsys_Close` (and tracks `Fsys_Open` of DCF JPEGs). When a fresh DCF JPEG is closed, the
shim decodes it, adds grain to the luma plane, re-encodes it and rewrites the file in place, Exif
kept. The camera ends up with a grained SOOC JPEG and nothing runs on the PC.

Design constraints that shaped it:

- The hardware JPEG codec needs buffers from the DMM pool, which a userland preload cannot get, so the
  codec is a software, integer-only one (`swjpeg.c`). No FPU, no libc.
- There is about 1 MB of free RAM at capture time, so the work is streamed band by band instead of
  holding a decoded frame. The only large allocation is the output JPEG buffer.
- The noise is a pre-baked 512x512 int8 tile (rodata) shaped by a luma-dependent gain LUT. No RNG or
  filtering at run time.
- Speed: AAN "FAST" integer DCT/IDCT, and chroma passes through as unchanged coefficients (only luma is
  touched). About 16 s per shot on the camera.

## Files

| file | what |
|---|---|
| `grain_hook.c` | entry point: `__dlopen`/`__dlsym` bootstrap, `Fsys_Open`/`Fsys_Close` interposers, run the codec, land the result (Remove, Open, Write) |
| `swjpeg.c`, `swjpeg.h` | freestanding baseline JPEG decoder/encoder with band callbacks, FAST and ACCURATE transforms, chroma passthrough |
| `grain_stream.c` | per-band grain: tile sample times the gain LUT indexed by the co-located luma; chroma bands are skipped when passed through as coefficients |
| `grain_tile.S` | `.incbin "grain_tile.bin"` into rodata |
| `grain_tile.bin` | the baked 512x512 int8 noise tile |
| `grain_luts.h` | generated `GAIN_Y/CB/CR[256]` LUTs and tile constants |
| `bake_tile.py` | regenerates `grain_tile.bin` and `grain_luts.h` |
| `test_fastpt.c` | offline codec test harness |
| `tools/grain_hook_4a.c` | the harmless logger preload: the known-good `.so` that `env.txt` points at while staging |
| `tools/usb_list.py` | lists USB devices through libusb and classifies Sony updater and senser PIDs; run with sudo |
| `tools/stage_shim.py` | stages and arms `grain_hook_4c.so` in the safe order: disarm, write, verify md5, re-arm |
| `tools/disarm.py` | prints the shim log, `env.txt` and `dmode`, then reverts `env.txt` to the 4a logger |
| `tools/recover_env_via_updater.py` | recovery: reverts `env.txt` to the 4a logger from the updater shell |

## Build

Cross build, run from this directory because `grain_tile.S` includes `grain_tile.bin` from the assembler's working
directory:

```
arm-linux-gnueabi-gcc -march=armv5te -shared -fPIC -nostdlib -O2 -ffreestanding -fno-builtin \
  -fno-tree-loop-distribute-patterns -o grain_hook_4c.so grain_hook.c swjpeg.c grain_stream.c grain_tile.S
```

The logger is the same line with `tools/grain_hook_4a.c` as the only source and `grain_hook_4a.so` as the output. Each
`.so` must be self-contained: the only undefined symbols allowed are `__dlopen` and `__dlsym` (check with
`arm-linux-gnueabi-nm -u grain_hook_4c.so`). Anything else makes the loader fail on the camera, see Risks.

## Deploy

Needs a Sony-PMCA-RE checkout (`$PMCA_RE`: the directory with `config.py` and `pmca/`) with its Python requirements
(pyusb), libusb (`LIBUSB_PATH`, default `/opt/homebrew/lib/libusb-1.0.dylib`) and root. The camera is on and connected
in USB mass-storage mode. Everything goes through the Sony-PMCA-RE senser (service mode) shell, interactively
(`pmca-console serviceshell`: `push`, `pull`, `shell`) or through `tools/`, which uses the same channel and runs as
`sudo -A env PYTHONPATH=$PMCA_RE [LIBUSB_PATH=...] python3 tools/<name>.py`. `tools/usb_list.py` shows whether
libusb sees the camera and in which mode.

First time on a body, once, before any preload is armed:

1. `push` the built `tools/grain_hook_4a.so` to `/setting/grain_hook_4a.so`, `pull` it back and `cmp`. Every later
   step reverts to it, and `tools/stage_shim.py` and `tools/disarm.py` refuse to run without it.
2. Write `/setting/mode/dmode` containing exactly `3` and a newline: `printf '3\n' > dmode` locally,
   `push dmode /setting/mode/dmode`, `pull` it back and check the bytes are `33 0a`. `env.txt` is only parsed when `dmode` exists.
   Other content is not safe: a `0` anywhere in the file, or a last digit other than 3, leaves the camera without its
   application firmware, and without USB in the `0` case (`../../atlas/_extract/F-q5-dmode-safety.md`).
   `/setting/mode/` existed and was empty on the stock development body; if the push fails because it is missing, run
   `mkdir -p /setting/mode` in the updater shell.
3. Pre-place and test the `\updater\mode` recovery net (`../../atlas/grain-linux-stage2-runbook-2026-10-20.txt`).
   Loader2 checks for `\updater\mode` on `/setting` as its first boot check and enters the USB-reachable updater if it
   exists, before userland and so before any preload. Reach the updater shell with `pmca-console updatershell`, then
   `shell`: busybox without `printf`, `/setting` may not be mounted. Do 2a first, 2b only if 2a is inconclusive
   because the updater window was too brief to catch.

   ```
   # recon, read only. Expect comp 0 B, dat4 2 B, no mode*, no uincomp; otherwise stop
   mount -t vfat /dev/nflasha2 /setting 2>&1 ; ls -la /setting/updater ; cat /setting/updater/comp | wc -c ; umount /setting
   # 2a, comp intact: a self-clearing one-shot net. Then exit, battery-pull, with pmca polling for the device
   mount -t vfat /dev/nflasha2 /setting ; touch /setting/updater/mode ; ls -la /setting/updater ; sync ; umount /setting
   # 2b, comp removed: mode survives, so every power-on lands in the updater until comp is restored
   mount -t vfat /dev/nflasha2 /setting ; cp /setting/updater/comp /setting/updater/comp.sav
   rm -f /setting/updater/comp ; touch /setting/updater/mode ; ls -la /setting/updater ; sync ; umount /setting
   # revert 2b, in that updater shell (the only channel, the main firmware does not run). Then battery-pull
   mount -t vfat /dev/nflasha2 /setting ; rm -f /setting/updater/mode /setting/updater/mode*
   cp /setting/updater/comp.sav /setting/updater/comp ; rm -f /setting/updater/comp.sav   # or: touch /setting/updater/comp
   ls -la /setting/updater ; sync ; umount /setting
   ```

   After 2a the camera should enumerate once as the updater; since `comp` exists the updater then deletes `mode*` and
   the next boot is normal, nothing to revert. After the 2b revert, check through the senser shell that
   `/setting/updater/comp` reads back (0 B) and `mode` is gone. Create only a bare `mode`, never `mode1` or a `mode`
   with a digit: `mode1` selects the flashing path. 2b stops the shim from running, so revert it before shooting.

Every (re)stage:

4. `sudo -A env PYTHONPATH=$PMCA_RE python3 tools/stage_shim.py --so grain_hook_4c.so --md5 $(md5sum grain_hook_4c.so | cut -c1-32)`
   (`md5 -q` on macOS). In order: check `--so` locally; print `env.txt` and `dmode`;
   require `dmode` to be `3\n` and a valid `grain_hook_4a.so` on the camera; disarm (`env.txt` to the 4a logger, read
   back); write `/setting/grain_hook_4c.so` and compare the read-back md5 with `--md5` (a mismatch or USB error stops
   here, camera still on the logger); truncate `/setting/grain_hook_4c.log`; re-arm (`env.txt` to the 4c `.so`, read
   back). Never write the `.so` by another route while `env.txt` points at it.
5. Cold boot now: pull the battery. A boot that restores the warm-boot snapshot skips init and with it `env.txt`
   (`../../atlas/grain-linux-stage1-runbook-2026-10-19.txt`, STEP 2). Shoot.
6. Read the log with `tools/disarm.py`, which prints it and also disarms, or leave the shim armed. Among other
   lines each shot adds `4c: GRAIN ok ...` (hex microseconds) or `4c: SKIP <reason>`.

## Offline test

`test_fastpt.c` runs the same decode, grain, encode path without the `Fsys` shim: a hosted build (libc), linked
statically and run under `qemu-arm-static`, from this directory:

```
arm-linux-gnueabi-gcc -O2 -march=armv5te -fno-builtin -static -o test_fastpt test_fastpt.c swjpeg.c grain_stream.c grain_tile.S
qemu-arm-static ./test_fastpt in.jpg out.jpg fast
```

`fast` (default) is FAST transform plus chroma passthrough, `accurate` is the ACCURATE transform with full chroma. It
prints the return code of each codec stage, the first band's coefficient flags and the codec time, and writes the
grained JPEG to `out.jpg`. The input must be a baseline (non-progressive) JPEG. It has only been exercised on the
NEX-3N's 4912x3264 4:2:2 frames, and none are shipped.

## Tuning the grain

`python3 bake_tile.py` writes `grain_tile.bin` and `grain_luts.h` into the current directory (copy
them here afterwards). The tile is a toroidal [1,4,1]/6 blurred hash noise normalised to int8. The
amplitude is the `STRENGTH` constant at the top of `bake_tile.py`, applied to the `SY`, `SCB` and `SCR`
luma-response curves. `1.0`, the committed value and what the committed `grain_luts.h` was baked with,
gives sigma_Y about 3.5 on the camera, matched to UltraMax 400 scans; this is the look that was proven
on the camera. `1.5` gives sigma_Y about 5, grain you can see without zooming; it was validated offline
only. Rebuild the `.so` after regenerating.

## Evidence

Measured on the camera with the x1.0 build on two consecutive shots, from the shim's own log: codec
12.5 s and 13.8 s, landing 0.38 s and 0.43 s, 12.9 s and 14.3 s inside the shim; about 16 s per shot by
stopwatch including the camera's own save; free RAM at capture 1.1 MB and 3.0 MB. The log is in
`../../atlas/grain-linux-stage4c-ONCAMERA-run-log-2026-10-21.txt`.

## Risks

- The original JPEG is removed before the rewrite, so a create or write failure, or a power loss, in that window
  loses the shot. This was chosen for speed and there is no `.TMP` backup. The codec itself runs with the original
  intact; only the final landing window, about 0.4 s, is exposed.
- The shim is always on for every `DSC*.JPG`. There is no on/off switch; a toggle was designed, not built.
- It appends to `/setting/grain_hook_4c.log` on every shot, with no size bound, on NAND.
- The codec handles baseline JPEG only. Progressive input returns an error and the file is left as it is. Only 4:2:2
  has been exercised.
- Arming a boot preload can brick the camera: the preload is loaded before anything that could intervene, and a
  missing or truncated `.so` kills userland. Never overwrite the `.so` that `env.txt` points at. Disarm `env.txt` to a
  known-good preload first, write and verify the new `.so`, then re-arm; `tools/stage_shim.py` does this. The
  development body was lost to exactly this: a USB write failed half way and left a truncated armed `.so`. The
  post-mortem is in `../../atlas/grain-linux-BRICK-INCIDENT-and-hw-recovery-2026-10-21.txt`.
- The `\updater\mode` net in Deploy comes from the stage-2 analysis (Loader2 disassembly and the updater scripts).
  The atlas records no camera run that confirms it, and the body that was lost never had it.

## Recovery

- The camera still boots: `tools/disarm.py` reverts `env.txt` to the 4a logger through the senser shell.
- The camera is in updater mode, through the `\updater\mode` net or the BOOT_MODE_1 strap:
  `tools/recover_env_via_updater.py` mounts `/setting`, prints `env.txt` and the preload files, then rewrites
  `env.txt` to `LD_PRELOAD=/setting/grain_hook_4a.so` so the next normal boot does not load the bad preload. It needs
  a Sony-PMCA-RE checkout on `PYTHONPATH` and libusb, as in Deploy.
- Userland dead and no net in place: nothing enumerates on USB, so software cannot reach it. The only route found is
  the hardware strap (bridge CL3005 to CL3006 on SY-1013 side B), described in the post-mortem. It failed on the
  soldering when tried on the development body, so it was never exercised.
