# In-camera grain: the real verdict — ARM is closed, grain lives in the DSP (07.10.2026)

This supersedes the "working solution" framing in `grain-hook.md`. After a full day of
on-camera testing, the honest result is: **synthetic film grain written from the ARM side
(av-cam) does not reliably reach the SOOC JPEG.** The developed YC buffer is owned and
scheduled by the SA DSP; the only durable injection point is inside the DSP module
`idt_cam.bin`. Below is what was measured, why the ARM path is closed, and the DSP map we
reverse-engineered by black-box bisection (which localises grain to a ~18 KB window).

All addresses are for the NEX-3N `av-cam.bin` (VA base `0xc3441000`) and `idt_cam.bin`
unless noted. Firmware images are not shipped.

## 1. ARM-side grain does not reach the JPEG (measured)

The `grain-hook.md` hook (wrapper on the Soft Focus dispatch sites, graining
`session[+0x5e4]`) was tested with several amplitudes and, later, at the last develop
sequencer step. In every case the grain in the saved JPEG was negligible:

| build | hook | luma HP-std in JPEG (mid-tones) |
|---|---|---|
| v2/v3 (SF stage, ±15, mid-tone window) | Soft Focus stage | ~0.7–1.8 |
| v4 (SF stage, ±31, flat, luma-only) | Soft Focus stage | ~0.8–1.8 |
| v5 (last develop step rec40, ±31) | rec40 dispatcher | ~0.7–1.8 |

**Amplitude-independent** (±15 ≈ ±31) → what the metric sees is base sensor noise, not our
grain. A clinching test: a build that **zeroed 6 MB of `session[+0x5e4]`** at rec40 (a
black-bar marker) produced **no black** in the JPEG at all (0 %), on an Off-frame whose
class makes the hooked stage run. So `session[+0x5e4]` at these stages is **not** the
buffer the encoder reads — it is overwritten by later DSP writes before encode.

The old "quadrat of grain, sometimes, bottom-left" was a **race artefact**: `session[+0x5e4]`
is a live DMA buffer only on the early Soft-Focus stage (sequencer rec1–4); the 31 calls of
the develop core `0xc37ea42e` overwrite it afterwards, so grain only survived on whichever
bottom tiles happened to be written after the DSP finished and before encode.

## 2. Why there is no ARM window

The capture pipeline is **descriptor/handle-driven**. av-cam only assembles descriptors and
posts them to the DSP/HW through queues; `0xc366eb00` is a command-send primitive, not a
canvas allocator. Pixel buffers are addressed **by handle** (`session[+0x3e24]` — a small id,
the "0x1df", not an address) plus geometry (`session[+0x1b8]` etc.). The DSP owns both the
writing and the scheduling of the YC buffer.

JPEG encode (stills): `tsk46_jpeg` (`0xc344a790`) is a message loop; `msg[0]`=command →
`0xc347427a` (cmd 0/2, the stills encoder) or `0xc3474800` (cmd 1/3). Confirmed live with a
detour-logger (marker `0xd1a6` fired in `0xc347427a`): the encode handler takes the YC buffer
**by handle**, not as an ARM address. The enc-config global `[0xc3ca0528]` is NULL at idle and
holds qtables nearby; the JPEG context singleton `0xc3bb7bc0` (returned by `0xc35dc8ba`) holds
only state flags, no buffer pointer. There is **no ARM instruction executing in the window
"buffer finalised → encoder reads it"** — that whole interval is inside the DSP domain, and the
DSP engine registers (`0x40000+`) are not in ARM physical memory (the observability wall).

→ Reliable SOOC grain is only reachable **inside the DSP**.

## 3. The DSP module and the grain target

On the NEX-3N, p3 `sabin/` holds only `idt_cam.bin` (200 KB) and `sa_dfdet.bin`; there are no
separate NR / JPEG / Soft-Focus SA modules (unlike NEX-6/a7). So the **entire stills develop
pipeline (demosaic/WB/colour/NR/sharpen/tone → YC) is `idt_cam.bin`.** It is a v4 SA descriptor:
scalar code `~0x820..0xa598` (control/config only — no full-frame per-pixel luma loop), and
**VLIW `0xa598..0x2ea68` (~148 KB, the pixel math)**. Grain must go into the VLIW.

Bundle format (verified): 64-bit = 12-bit S0 + 4×13-bit slots; slot = `op3.a5.b5` (a=src,
b=dst); NOP bundle = `0x1f70fb87dc3ee1f7`. 8 op3 codes, all active. The op3→operation map,
the datapath (register file indexing), and which VLIW core writes luma **cannot be recovered
offline** — the only ground-truth oracle (a Soft-Focus sharp→blur image pair) is a convolution,
so it exercises only mul/add/mov; shift/xor never appear, and engine state is unobservable.

**Workaround that avoids decoding op-codes:** bake random values into a small table offline,
then inject `load noise[i]` + `add` to luma. Both ops are already present in the convolution
cores, so their slot encodings can be **copied verbatim** from a known core (copy, not decode).

## 4. Campaign A — DSP map by on-camera NOP bisection (idt_cam)

Method: `build_nopcore.py` rebuilds p3 with a clean (film-curve) av-cam and a chosen byte
range of `idt_cam` (inner offset `0x980e00`) overwritten with NOP bundles; flash via the
updater shell with `current_p3` as recovery. NOP is recoverable; a broken luma hangs the
"writing to memory card" step, cleared by a battery-pull reboot (which flushes the pending
frame). Results, each observed on the camera:

| NOP range (idt_cam) | on-camera effect | conclusion |
|---|---|---|
| `0x1c000..0x2ea68` (2nd half) | image normal, **write hangs** | 2nd half = **encode/write** |
| `0xa598..0x1c000` (1st half) | focus hangs, dies on shot | 1st half = **develop + live-view** |
| `0x13000..0x1c000` (q2) | image **normal** | q2 not used by stills |
| `0xa598..0x13000` (q1) | (implied essential) | q1 = develop+focus+**luma** |
| `0xe800..0x13000` (e2) | **black luma**, focus OK | e2 = **luma stages** |
| `0xe800..0x10c00` (e2a) | black (from e2 result) | e2a = main luma **write** |
| `0x10c00..0x13000` (e2b) | **very bright**, dies | e2b = late luma **tone/gain** |
| single late cores `0x2d4e0`, `0x249d0` | no effect | not on stills path |

**Grain target: `idt_cam` VLIW `0xe800..0x13000`** — the late luma write (e2a) and tone (e2b).
Big cores inside: core17 `0xeea0`, core19 `0xf6c0` (450 bundles), core22 `0x105d0`, core23
`0x10ca0`, core25 `0x11280` (586), core30 `0x12650`, core33 `0x12cd0`. e2b (bright-when-gone)
is the latest luma op → the best place for grain to survive to the JPEG.

## 5. What remains (Campaign C — datapath)

To actually inject grain, still needed (all black-box on camera, each miss = a hang + reboot):

1. Narrow e2a/e2b to the single luma-store core (1–2 more NOP cycles).
2. Inside it, identify the luma register and its store slot, and a usable idle slot
   (Campaign C: vary a/b of a slot, observe the flat-gray output, recover the register file).
3. Copy the `load`+`add` slot encodings from a convolution core; point them at a baked noise
   table (space is scarce — candidate zero zone near `0x2e606`, ~543 B) and the luma register.
4. Offline-verify the rebuilt bundle, flash with recovery, shoot.

Tooling (scratchpad, not shipped): `build_nopcore.py` (p3 rebuild with NOP'd idt_cam ranges),
`build_difflog2.py` (encode-handler detour logger), `sonygen/isa/{vliw,vdump,vengine,slots}.py`
(bundle decode). The LZPT writer and flash pipeline are in `code/lzpt/` and
`live-memory-and-delivery.md`.

## 6. Net

- ARM-side SOOC grain: **closed** (DSP-owned, handle-addressed buffer; observability wall).
- No native grain generator anywhere in the firmware (mono effects = contrast-amplified sensor
  noise; only subtractive NR, AAC audio noise, unused H.264 SEI).
- DSP grain: **feasible in principle**, localised to `idt_cam` VLIW `0xe800..0x13000`, but needs
  the datapath campaign above — a separate, slow, uncertain black-box effort.
- The flash/recovery path is robust: 10+ NOP/patch cycles, zero bricks.

## 7. Correction (09.10.2026): idt_cam is a set of overlays; Campaign A over-read the NOP results

- `idt_cam` is **35 loadable overlays**, each starting with the stub `5f50 5e50 5150 b100 …`
  (`ldr sp; ldr r14; ldr r1,=entry; bl r1; str 0→[0x48208]; wfi`), header words `+0x18`=stack,
  `+0x1c`=entry; load address = page + 0x10. The "cores" of §4 (`0xf6c0`, `0x105d0`, `0x11280`,
  `0x12cd0`, `0x249d0`, `0x2d4e0` …) are these overlays. Each mixes scalar code, literal pools,
  data tables (e.g. a 65536/n reciprocal table in `0x11280`) and VLIW kernels.
- **NOP bundles executed as scalar code are garbage with branches** (`dc3e` = `bfc`), so every
  §4 range that hit scalar code ran random code; "black"/"bright" there are indirect symptoms.
- Overlay `0x105d0` (base `0x2010`, entry `0x21cc`) read in full: a mailbox service loop
  (DMA desc `0x48234`, go `0x48230`, irq `0x48208`), param check `+0x348`, handler `+0x3c8`:
  DMA-reads lines into double buffer `0x8000/0x8800`, loads engine regs `0x40000..0x40058`,
  runs a VLIW kernel per line, then exports 5 accumulators (`0x40078..`) + 64 B to ARM
  (`0x80380000` write desc). **No pixel write-back → statistics stage.** The 2–4 stop overexposure
  of `nope2b1` (`0x10c00..0x12520`) came from corrupting its literal pool / kernel → wrong AE/DRO.
- `0x105d0`'s neighbour `0x11280` is not used by stills (NOP whole overlay → normal);
  `0x12520..0x13000` NOP → normal.
- `0xf6c0` writes 2D blocks from local `0x9000` (looks like an AE/AWB grid).
- **Overlay-skip test** (stub `bl r1`→`nop`): skipping `0xf6c0`, `0xcbd0` or `0x105d0` all give the
  *same* symptom (live view blinks 1/4000 f/16, save hangs) → skip is **non-specific**: it only
  proves "the ARM waits for this overlay", not what it computes.

Open question that decides the DSP route: **does any overlay write image pixels at all**, or is
idt_cam on the 3N purely a 3A/statistics engine with pixels done by fixed-function ISP?
Next: offline classification of all overlays by DMA pattern (per-line read + per-line write = pixel).
Tools: `~/nex3n-dump/work/nopcore/` (build_nopcore.py, build_skipov.py, images, logs).
