# Live memory access and firmware delivery (NEX-3N)

Two USB back doors (both from ma1co's Sony-PMCA-RE) and how they were used to read the
running camera and to flash a modified `av-cam`. Bring-up specifics (USB mode, auth) are
device-level and kept out of this repo; the method and findings are below.

## senser / service mode — live RAM read/write

Entered from USB mass-storage; the generic reversed service keys authenticate on the
NEX-3N. Gives, as the camera, over `SONY_PFUNC_*`:

- `readMemory(base, size)` / `writeMemory(base, data)` (PFUNC MemoryDump `0xff03`) —
  **ARM physical** memory of the running camera. Confirmed: phys `0x83441000` = live
  av-cam (= image, 99%); writing works (readback matches).
- `FileControl` (`0xff01`): `readFile` / `writeFile` / `deleteFile`. Only `/setting`
  (p2) is writable; `/system`, `/usr`, `/android`, `/info` return error 130 (read-only).
- Backup read/write; an interactive terminal.

Uses:
- **Locating capture buffers by diffing** — baseline dump → take a shot (disconnect USB,
  keep power, no power-cycle so DRAM persists) → second dump → changed regions are the
  capture buffers. Found the developed YC canvas (YUYV 4:2:2, width recovered by
  row-autocorrelation = 4928, stride `0x2660`) and the JPEG output buffer (starts `FFD8`).
- **Reading structures live** — e.g. a diagnostic av-cam build wrote the develop-session
  object fields to a scratch address, which a senser read then recovered, giving the real
  encode-input buffer field (`grain-hook.md`).

Limit: a senser write to av-cam **does not survive to a capture** — the write needs
service mode, and leaving service mode reboots the camera, which reloads the stock
`av-cam.bin` from flash. So senser is for reading and for transient probes, not for
delivering a persistent patch. (DSP engine registers `0x40000+` are also unreadable — not
in ARM physical space.)

## updater shell — raw partition write

The OpenMemories custom-firmware updater (`updaterShellCommand`): a model `fdat`
(CXD4132 / `NEX-3N.hdr`) switches the camera to updater mode (confirm on screen) and
drops into a BusyBox-ish root shell with `writeFile` (PUSH), `readFile` (PULL), an
interactive shell, Backup and bootloader access. In this environment:

- `/proc/partitions` shows `nflasha0pN`; `/dev/nflashaN` nodes also work. `/setting`
  (nflasha2) is mounted vfat rw; `/system` (nflasha3) is **not** mounted (it is the LZPT
  raw image) and `mount -t vfat /dev/nflasha3` fails ("Invalid argument").
- **Raw partition write works**: `writeFile('/dev/nflasha3', image)` writes the raw
  device. This is how a modified p3 (or p8) is flashed, bypassing the read-only fs.
- The shell is minimal (`od`, `head`, `id` absent; `dd`, `md5sum`, `mount`, `cp` present).

## Flash pipeline (deliver a modified av-cam)

Proven, reboot-persistent, recoverable (`code/grain/flash_any.py`):

1. Read the current `/system/av-cam.bin` (senser `readFile`) — the on-camera file already
   carries the owner's edits (e.g. the film tone curve), so patch **on top of the live
   file**, not the stock image.
2. Patch av-cam in the p3 inner image at offset `0x8e00`; `lzpt_write` → raw p3; pad
   `0xFF` to 10 MB. Verify offline by decompressing the result and comparing av-cam.
3. Updater shell: `writeFile('/dev/nflasha3', p3_image)`; **md5-verify the whole
   partition** (`dd if=/dev/nflasha3 bs=65536 count=160 | md5sum`); on mismatch write the
   recovery image back and abort.
4. On match: invalidate WBI (`dd if=/dev/zero of=/dev/nflasha5 bs=512 count=1`), then
   reboot.

Recovery: keep the pre-change p3 image and `writeFile` it back. A bad av-cam does not
brick — Linux + the updater path are on other partitions, so the updater shell is still
reachable to restore. Caveat: p3 also holds `vmlinux`/`initrd`, so an **interrupted**
raw write of p3 is the real risk — always md5-verify before rebooting, and restore in the
same session if it fails. The menu label was renamed the same way on p8
("Soft Focus" → "Film Grain" in `share/app/string_english.uxc`).

Gotcha: `lzpt_write` uses a multiprocessing Pool, so any script that calls it must guard
the call under `if __name__ == "__main__"` or it fork-bombs on spawn platforms (macOS).
