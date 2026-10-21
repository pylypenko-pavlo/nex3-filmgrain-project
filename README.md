# NEX-3N Film Grain Project

I reverse-engineered a Sony NEX-3N (fw 1.00, CXD4132 / BIONZ) to get a film look, colour, tone and
real film grain, baked into the JPEG the camera writes. Nothing on the PC side: you shoot JPEG and the
camera hands you a graded, grained frame. The joke name for it was "an X100 for the poor".

Two parts:

- Colour and tone. Colour is done through the camera's own settings store. The tone curve was written into
  the curve slot of the av-cam image, one narrow partition write (E-0022 in the experiment log). I decoded
  the colour matrices, hue tables and tone curves and designed film looks (Portra 400, UltraMax 400,
  Phoenix II and variants) that load on the stock Creative Style slots.
- Grain. An in-camera software hook that adds luma-adaptive film grain to the JPEG as it is saved. This
  worked end to end on the camera: shoot, get a grained SOOC JPEG with Exif intact, about 16 s per shot.

The repo is notes, analysis and measurement code, disassembly findings and the designed values. It ships
no firmware images, no dumps, no raw settings-store dumps (the decoded stock values are included in
`data/looks/blocks/`) and no photos; tools that need camera data read your own files (see Inputs). All of
it was done on a camera I own; legal basis at the bottom.

Status as of 2026-10-21: the colour/tone looks are done and measured, the grain hook is proven on the
camera. The development body was then bricked during a routine re-flash of the grain hook and written
off. The post-mortem and the hardware-only recovery path are in the section "The brick" below. The
pipeline itself does not depend on that body and moves to the next NEX-3N.

---

## Platform

CXD4132 (BIONZ), dual core. One core runs Linux 2.6.29-rt on ARMv5TE for the UI and userland (the
`im.elf` app framework). Image processing runs in a separate RTOS image (`av-cam`, base `0xc3441000`) on
the second core, and the pixel work is done by Sony "SA" DSP modules with their own ISA: a 16-bit scalar
RISC plus a 64-bit VLIW engine. Style parameters live in RAM, filled at boot from the settings subsystem
and interpolated over ISO. Boot chain is Loader1 (boot ROM) then Loader2 (`boot1`) then Linux; firmware
sits on NAND partitions `nflasha1..8`, the app and RTOS packed as LZPT (`TPZL`) images.

The deep disassembly (SA-DSP ISA, the VLIW engine, the boot and mode tree, the Linux app framework, the
capture pipeline) is in `atlas/`, the working research log. What follows are the results; the atlas has
the derivations, addresses and the dead ends.

---

## Results: colour

Measured on an on-screen ColorChecker target plus a 21-step grey wedge at fixed WB, every experiment
against a baseline shot in the same session (frame-to-frame noise about ±2 chroma, ±3 b*; sessions do
not compare across days).

Style parameters are in settings block `0x00030001` (mirrored in `0x00030008`, both banks must be
written), 1536 bytes:

- A 3×3 colour matrix per slot, 9×int16 LE at `+0x48 + 18*slot`, `1024 = 1.0`, applied in linear light
  (a linear-light model fits the measurements better than a gamma-space one).
- Slot map, found with RGB-permutation "tag" matrices: Standard 0 (`+0x48`), Vivid 1 (`+0x5a`),
  Portrait 2 (`+0x6c`), Landscape 3 (`+0x7e`), Sunset 4 (`+0x90`).
- Stock matrices: slots 0 and 2 are `1292,-180,-88 / -44,1340,-272 / -24,-108,1156`; slot 1 has a
  different G row (`1400/-332`); slots 3 and 4 are `1292,-220,-48 / -44,1360,-292 / -24,-108,1156`.
- A per-slot hue table, 24×int8 at `+0x100 + 24*slot`: 6 quads × 4 hue regions (red/skin, orange/yellow,
  cyan/sky, blue/violet). Quad 0 rotates hue inside its region; stock values are negative, i.e.
  desaturating. Details in `notes/hue-tables.md`.
- Vivid, Landscape and Sunset add their own chroma on top of the matrix (+11 / +14 / +14 %); Portrait
  does not. Sunset's warmth is a shift of the auto-WB target, not a processing stage; at fixed WB it
  disappears.
- Property `0x00030106` holds sharpening ladders (Apacon), not colour. The `0x66` curves are
  display/video-out gamma and do not touch the JPEG.
- Hidden Creative Styles (Neutral, Clear, Deep, Light, Night Scene, Autumn, Sepia) exist in code, but an
  unconditional loop in `viewUnified2.so` marks menu IDs 6..12 invalid, identically on the NEX-6. No
  settings flag unlocks them. See `notes/hidden-styles.md`.
- Never write `0x00030002` (this unit's WB calibration), `0x00bc0000/0002` or `0x01320000` (defect
  pixel maps).

How the levers move the image, measured against same-session baselines:

| Lever | Effect |
|---|---|
| Slot matrix, rows summing to 1024 | Neutrals and luma unchanged. A muted matrix halves mean chart chroma (43.7 to 21.7). Rows that do not sum to 1024 tint the greys. |
| Built-in style chroma | Vivid +11 %, Landscape +14 %, Sunset +14 %; Portrait none. |
| Saturation slider | Mean chroma × (1 + 0.13·s). |
| Contrast = curves k0..k6 | Per channel, gamma domain. c−3 lifts black L from 6 to 11; c+3 crushes shadows. |
| Hue rotation quads | Per unit: red −0.25°, yellow +0.20°, cyan −0.39°, blue +0.13°. +100..134 units rotate a region 20–37°. |
| Model vs camera | The camera responds up to 1.8× more than a linear per-unit model; keep steps around 10–20 units and verify. |

The designed looks (Portra 400, House, UltraMax 400, Phoenix II and variants) are in `data/looks/`. That
v6 set is what was loaded and measured on the camera; a later v7 line-up (`data/looks/lineup_v7.json`,
`atlas/colour-slots-lineup.md`) uses different slots and was never loaded. Tone can also be overridden
from the store through a debug byte (`0x3007a+0xD7`: mode 2 overrides the curve index, mode 1 loads your
own 96-point curve), read from the code and not verified on the camera. I designed a film tone curve
(black about 12/255, soft shoulder) for slot k0 (Contrast −3): `notes/tone-curve.md`,
`data/curves/film_k0.json`.

---

## Results: grain

Real film grain, added in-camera and automatically to the SOOC JPEG, tuned to actual film scans.

The grain is not done on the DSP (that route is closed, see below) but in the Linux userland that saves
the file. A freestanding shared object, preloaded through the camera's boot `env.txt`, interposes
`Fsys_Close`. When a fresh DCF JPEG is closed it

1. reads the source Exif (APP1) header,
2. decodes the JPEG straight from the file through a read callback,
3. adds luma-adaptive grain to the luma plane,
4. re-encodes and rewrites the file in place (remove, create, write; `rename` is a dead PrFILE veneer
   on this firmware), splicing the Exif back in.

Three constraints shaped it, all real on this camera:

- There is no usable hardware codec. The HW JPEG codec wants physically contiguous DMM-pool buffers and
  faults on anonymous mmap memory. So the shim carries its own integer JPEG codec
(`code/grain-shim/swjpeg.c`): no libc,
  no FPU or VFP (ARMv5TE), integer only, no variable division.
- About 1 MB of RAM is free at capture time; 448 MB is reserved for the imaging DMM pool. The codec
  streams one MCU-row band at a time (about 92 KB of scratch) with callback I/O, so it never holds the
  whole source or output. The grain is a pre-baked 512² toroidal int8 noise tile in rodata plus a
  luma-indexed gain table, so it costs almost nothing per pixel.
- Speed. AAN transforms plus chroma passthrough (chroma re-encoded as unchanged coefficients, grain on
  luma only) roughly double the codec. On the camera, from the shim's own log on two consecutive shots:
  12.5 s and 13.8 s in the codec, 0.38 s and 0.43 s to land the file, 12.9 s and 14.3 s inside the shim;
  about 16 s per shot by stopwatch, including the camera's own save. The log is in
  `atlas/grain-linux-stage4c-ONCAMERA-run-log-2026-10-21.txt`.

The look is tuned to a pack of real UltraMax 400 scans: fine (around 1 px) and luma-adaptive, strongest in
the midtones and fading in highlights and shadows the way film does, σ_Y about 3.5, with a ×1.5 variant at
σ_Y about 5 for when you want to see it without zooming. The grain is confirmed on real camera frames by
the elevated flat-patch high-frequency noise versus stock.

The first approach was to inject grain into the SA-DSP imaging path, in the Soft Focus and YKNR stages.
I explored it fully and it is blocked by hardware: the imaging canvas is read-only to the app CPU (writes
data-abort), the Soft Focus VLIW engine has no free slots and its scratch registers are loop-carried, and
there is no scalar path to the full-resolution pixels. Soft Focus only ever touches a low-resolution glow
buffer, and YKNR luma is gated by ISO. The analysis, the VLIW substitution experiments and every dead end
are in `atlas/` (`grain-*`, `grain-RESTART.md`, `grain-sftfcs-confirmed.md`) and `notes/grain-hook.md`.

The shim, the codec and the tuning harness: `code/grain-shim/grain_hook.c`, `swjpeg.c/.h`,
`grain_stream.c`, `grain_tile.S`, `grain_luts.h`, `bake_tile.py`, `test_fastpt.c`. The build, deploy
and test steps are in `code/grain-shim/README.md`.

---

## Reverse engineering and disassembly

What the colour and grain work stands on, all in `atlas/` and `notes/`:

- SA-DSP ISA. The scalar core is a Sony 16-bit RISC (partial disassembler in `code/isa/sadis.py`); the
  pixels go through a 64-bit VLIW engine that is partly decoded (`notes/sony-dsp-isa.md`, VLIW tooling in
  `code/isa/`). The module corpus across camera generations is in `notes/sony-dsp-generations.md`.
- Capture pipeline. How `av-cam` selects and drives the SA modules, with the call graph and BL cross
  references (`code/isa/`, `notes/sa-interface.md`, the capture-orchestrator and av-cam-executors notes in
  `atlas/`).
- Firmware architecture. NAND partitions, LZPT (`TPZL`) images with a byte-exact packer in `code/lzpt/`,
  the boot and mode tree (updater, adjust, image_update, normal), WBI, the DRAM map
  (`notes/firmware-architecture.md`).
- The Linux side. The `env.txt`/`dmode` boot preload, what the `sonyld` loader accepts, the `Fsys_*` file
  API, symbol resolution through `__dlopen`/`__dlsym`, the senser (service) and updater USB shells
  (`notes/live-memory-and-delivery.md`, the stage 0 to 4 runbooks in `atlas/`).
- Settings store. The `Backup.bin` property layout, the BKID-to-RAM map, symbol and name recovery
  (`code/bkparams/`, `notes/symbols-and-names.md`).

---

## The brick

The development body is bricked and written off. I was re-staging a rebuilt grain shim and wrote the new
`.so` over the one the boot `env.txt` already pointed at. The USB write failed mid-transfer and truncated
the file. On the next cold boot the loader could not load the corrupt preload, `sonyld` killed userland,
and the camera went to a black screen with no USB.

It cannot be recovered in software. I checked this against the loader disassembly and the Sony-PMCA-RE
community agrees: every boot stage runs, but the `env.txt` preload is loaded before anything that could
intervene, there is no SD-card, key-combo or USB-window door at loader level, and the one clean software
net (a pre-placed `\updater\mode` file) cannot be created once userland is dead. The remaining door is a
hardware boot-mode strap: pull `BOOT_MODE_1` high and the loader enters the updater, which ignores
`env.txt`, and from there the camera is recoverable over USB. I traced that strap down to the board
test points (CL3005 to CL3006 next to CN3011 on the SY-1013 board), but soldering it cleanly needs a
microscope and my attempt with a bare iron did not work.

Three lessons, so the next body does not repeat this. Disarm the preload before overwriting its file,
then write, verify, and only then re-arm (`code/grain-shim/tools/stage_shim.py` does exactly this); a
failed write then leaves the camera on a known-good preload. Prove the updater door before the first
arming: a `\updater\mode` file on `/setting` makes Loader2 enter the updater on the next boot, which is
a way to test that the entry works, but that boot consumes the file, so it cannot sit there as a standing
net while the camera shoots, and a preload that loads and then kills userland has no software way back,
only the hardware strap. And on macOS detect the camera with libusb (what pmca uses), not with
`system_profiler` or `ioreg`. The full write-up is
`atlas/grain-linux-BRICK-INCIDENT-and-hw-recovery-2026-10-21.txt`.

---

## Layout

```
atlas/   research log and single source of truth: the stage runbooks, SA-DSP/VLIW disassembly,
         boot/firmware RE, the brick post-mortem. Index: atlas/00-index.md.
notes/   topic write-ups: colour, hue, tone, SA-DSP ISA, firmware architecture, grain-hook,
         live memory and delivery, hidden styles, film-look plans, prior art.
code/
  sim/        offline JPEG pipeline model, joint fit, simulator CLI, validation
  measure/    ColorChecker patch detection and Lab measurement
  isa/        SA-DSP module parser, scalar disassembler, VLIW dumps, av-cam call graph and xref
  lzpt/       LZPT ('TPZL') partition packer (byte-exact) and parser
  grain-shim/ the in-camera film-grain shim: freestanding LD_PRELOAD hook, integer SW JPEG codec,
              tile baker, qemu test harness, staging and recovery tools
  grain/      grain preset builder and raw-partition flash tool (the earlier DSP route)
  lineup/     colour-slot line-up v7 builder (offline, writes data/looks/lineup_v7.json)
  sai/        av-cam Thumb-2 xref helpers (avx.py) and an ARM/Thumb-2 immediate-load scanner for
              ELF and kernel binaries (scanimm.py)
  bkparams/   settings-store property reader and av-cam tracing
  hidstyles/  ELF/Thumb helpers for the menu-library (hidden styles) analysis
data/
  looks/     decoded colour blocks (matrices and hue tables, stock included), look definitions
  curves/    the designed film tone curve
  fx/        effect experiments: property, offset, original and new bytes
  measurements/, filmcharts/   grey-ramp and chart data with fits
```

## Inputs (not included)

Tools that need camera data read it from your own files through environment variables; nothing
proprietary is in the repo.

| env var | what |
|---|---|
| `NEX3N_AVCAM` | your own unpacked `av-cam.bin` (xref, disassembly, tracing) |
| `NEX3N_BACKUP` | your own `Backup.bin` (property readers in `code/bkparams`) |
| `NEX3N_ADJMAP` | BKID-to-RAM map pickle built from your av-cam image |
| `NEX3N_SABIN`, `NEX3N_SABIN3`, `SONY_SABIN_ROOT` | directories with SA DSP modules |
| `PMCA_RE` | checkout of Sony-PMCA-RE |
| `NEX3N_CHARTS`, `NEX3N_PHOTOS` | your chart shots and test frames |
| `NEX3N_STRINGS` | the camera's `string_english.uxc` |

Python 3 with numpy, scipy, pillow, rawpy, capstone, pyelftools (plus unicorn for `code/sim/emu3dlut.py`), and
exiftool on PATH. The grain shim builds with `arm-linux-gnueabi-gcc -march=armv5te -nostdlib
-ffreestanding`; the exact line is in `code/grain-shim/README.md`.

## Legal basis

All reverse engineering here was done on hardware I own, for interoperability and personal study. In the
EU that is covered by Directive 2009/24/EC: Art. 5(3), a lawful user may observe, study and test a
program to determine its underlying ideas, and Art. 6, decompilation where indispensable for
interoperability of an independently created program. No firmware images or dumps are redistributed in
this repo. This is my working legal basis, not legal advice. Not affiliated with Sony.

## License

MIT, see LICENSE.

## Credits

This stands on the Sony camera hacking community, above all ma1co:

- [Sony-PMCA-RE](https://github.com/ma1co/Sony-PMCA-RE): the USB updater and service shells and the
  `Backup.bin` reader/writer this work relies on.
- [fwtool.py](https://github.com/ma1co/fwtool.py): Sony firmware unpacking.
- OpenMemories and [OpenMemories-Symbols](https://github.com/ma1co/OpenMemories-Symbols): SA-DSP notes
  and symbol names, the starting point for the DSP ISA work.
- Film ColorChecker data: published chart shots by Maraver and others, credited in
  `notes/film-colorchecker-tests.md`.

## Disclaimer

Modifying a camera, whether settings properties or a boot preload, can leave it in a bad state, up to an
unrecoverable brick. It happened here, see "The brick". Keep a copy of every original block before you
write, never touch the calibration properties listed above, and do not load a boot preload without a
tested way back. Use at your own risk.
