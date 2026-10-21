> SUPERSEDED (2026-10-21). The DSP-side grain route described here is closed: it is blocked by hardware
> (see the root README, 'Results: grain'). The route that shipped is the Linux LD_PRELOAD shim in
> `../code/grain-shim/`, runbooks `../atlas/grain-linux-*`. This page is kept for the engine/VLIW
> findings; its 'next steps' and 'active path' wording is historical.

# In-camera film grain: the av-cam hook

> **⚠️ SUPERSEDED (07.10.2026) — this ARM hook does NOT reliably reach the SOOC JPEG.**
> On-camera testing showed the grain is amplitude-independent and a zero-marker in
> `session[+0x5e4]` never appears in the file: the developed YC buffer is owned/scheduled by
> the DSP and addressed by handle, so writing it from av-cam is overwritten before encode.
> The "working, verified" status below was premature. The real verdict and the DSP grain
> target (`idt_cam` VLIW `0xe800..0x13000`) are in **`dsp-grain-campaign.md`**. The
> mechanism notes below (sequencer, buffers, cave, Thumb constraints, delivery) remain
> accurate and useful; only the "grain reaches the JPEG" conclusion is wrong.

Goal: synthesise film grain (high-frequency luma + weaker chroma noise) into the
developed image **in camera, SOOC**, at any ISO. None of the SA DSP modules add noise
(they blur or denoise), so grain needs new ARM code in the capture path of `av-cam.bin`
(NEX-3N, load base `0xc3441000`, VA; file offset = VA - `0xc3441000`).

Status (06.10.2026): working, flashed, verified in saved JPEGs, reboot-persistent,
camera stable. Firmware images are not shipped; every tool below needs your own.

## 1. The working solution

**Hook: wrapper on the Soft Focus dispatch sites.** `Stage_SoftFocus` (`0xc37ea898`)
is called from 8 dispatcher `bl` sites (all in the thunk block `0x1e72a2..0x1e776a`,
one per mode variant). Each of those 8 `bl` is redirected to a wrapper in a zero-fill
code cave at `0xc3a011c0`. The wrapper:

1. optionally calls the real `Stage_SoftFocus` (keeps the develop -> SF -> encode
   dataflow intact),
2. grains the **encode-input YC buffer**,
3. returns the SF result code.

Shoot with Picture Effect = Soft Focus to trigger it. The menu label is renamed the
same way as the code (p8, "Soft Focus" -> "Film Grain" in `string_english.uxc`).

**Buffer.** The encode-input YC buffer is `session[+0x5e4]`, where `session = *ctx`.
It holds a **bus** address (e.g. `0x0d000200`); av-cam reaches DRAM at
`virtual = bus | 0xc0000000`. Format YUYV 4:2:2, **4928 pixels wide**: luma = even
bytes (grained hardest), chroma = odd bytes (kept lower). Neighbouring field
`session[+0x4c0]` = JPEG-output pointer (`0x0e000000`; JPEG SOI found there).

**Code constraints.** ARMv6 (ARM11): Thumb-1 only, no `movw/movt/usat/b.w`; conditional
branches reach +-256 B; far jumps are `ldr r3,[pc,#4]; bx r3`. Noise = xorshift32
additive on the bytes, manual clamp to [0,255]. Assembled with keystone, checked
with capstone.

**Delivery** (the only path that worked):

1. p3 is an LZPT (`TPZL`) raw partition holding an inner image (`av-cam` at inner
   offset `0x8e00`). Patch av-cam in the inner image, re-pack with `lzpt_write`
   (byte-exact round trip), pad to the partition size.
2. Write the partition raw to `/dev/nflasha3` through the OpenMemories updater shell.
3. md5-verify the **whole** partition; restore the original on mismatch.
4. Zero WBI (`/dev/nflasha5`) so the next boot re-reads av-cam instead of restoring the
   RAM snapshot. Reboot.

Build on the **live** av-cam, not the stock image: the on-camera file already contains
the owner's film tone curve (region `0x5b006a..0x5b0869`) and would lose it otherwise.

**Tools.**

| tool | role |
|---|---|
| `code/isa/avgraph.py` | recursive Thumb call graph from task entries |
| `code/isa/xref.py` | full-image BL cross-reference (30k targets / 168k callsites); `xref.py <va>` lists callers |
| `code/grain/build_set.py` | builds grain preset images (needs your av-cam, the LZPT writer, keystone) |
| `code/grain/flash_any.py` | updater-shell raw flash with md5 verify + restore |

Earlier experiments: `code/isa/build_detour.py` (single-site detour of `0xc3889760`,
see dead ends) and `code/isa/grain_thumb.py` (first grain routine).

## 2. Technical facts

**Strings do not locate functions.** Log/message strings (`DistEncodeFULL`,
`CamCoreDevelopStart`, `ENCODE_JPEG`, `enc_param`, `DMM_HANDLE_YCC_FULL`, ...) have 0
literal-pool references: they are addressed by index into a string/message table
(`MSG_ID_*`). Find functions through the call graph / structure.

**Capture sequencer.** Step table at `0xc3629aa4` (off `0x1e8aa4`): ~58 records
`{dispatcher_fn (Thumb), descriptor_ptr}`, 8 bytes each. Descriptors (`0xc3bf17xx`,
+0x14 stride) are runtime addresses outside the image, so step names are not static.
It is a **state machine** visited by mode, not a linear pipeline. Dispatchers are
called indirectly (`ldr fn,[tbl+step*8]; blx fn`), so they have no direct BL callers.
Each is a jump table on a context byte; record 1 (`0xc362827e`):

```
movs r1,#0x23 ; ldrb r1,[r1,r0]   ; sel = ctx[0x23] (picture-effect selector)
cmp r1,#5 ; bhs default ; adr r3,#4 ; ldrb r3,[r3,r1] ; adds r3,r3,r3 ; add pc,r3
 case0 bl 0xc37deb92 | case1 bl 0xc37dfca2 | case2 bl 0xc37ea898 (Stage_SoftFocus)
 case3 bl 0xc37df2c0 | case4 bl 0xc363faa0 | default movs r0,#5
```

**Stage convention.** `void Stage(ctx)`, `r0 = ctx`, `r4 = *ctx` = develop-session
object. Many YC stages share one prologue: `r5=ctx; r4=*ctx; <gate on a session field>;
r0 = r4[0x1b8]<<16 | (r4[0x3a98]&0xffff); movs r0,#2; bl 0xc366eb00`
(`0xc366eb00(2, packed_geometry)` = lock/prepare the YC canvas). Members include
`Stage_SoftFocus` and `0xc3889760`. Accessor `0xc36045fc(r4,&a,&b)` returns
`a = u16 [r4+0x39e2]`, `b = u32 [r4+0x3e24]`; `0xc36046ac` is a status-returning twin.
Neither yields the encode-input buffer (see dead ends).

**Session buffer map (known).**

| field | meaning |
|---|---|
| `session[+0x5e4]` | encode-input YC buffer (bus addr), grain target |
| `session[+0x4c0]` | JPEG output pointer |
| other YC copies | per-stage YC copies of the image; also bus addresses (not individually mapped here) |

Full developed canvas (`DMM_HANDLE_YCC_FULL`), measured live with a senser dump:
YUYV 4:2:2, width 4912, stride `0x2660` (9824 B/line, ~32 MB), base allocated
dynamically (`0x8a000000` in one shot, `0x85900000` in another). Width from row-to-row
autocorrelation. `phys = virt - 0x40000000` holds live (`0x83441000` = av-cam, 99%
match with the image; the rest is runtime-filled data). The encode-input buffer is
4928 wide; do not mix the two geometries.

**JPEG encode is not via the SA-start mechanism.** `0xc37554de` (`ExecuteCalcStartMSG`,
24 callers, the SFTFCS/TBOX/... modules) is unreachable from `tsk46_jpeg`. JPEG is the
separate hardware encoder, driven through the `0xc35dcxxx` subsystem via `tsk46_jpeg`
-> handlers `0xc3474800` / `0xc347427a`. The YC buffer -> `enc_param` hand-off (the
`enc_param.address==0` check) lives there; not pinned to an instruction (the wrapper
makes that unnecessary for the Soft Focus path).

**Code caves** (zero fill): `0xc3a011bd` len 3442 (used from `0xc3a011c0`),
`0xc397d4f0` len 1280, others.

**Delivery facts.** `av-cam.bin` is loaded at runtime by `liro.ko` (`im.elf` passes
`fn=/system/av-cam.bin load=1`), so a bad av-cam does not take down Linux/USB and the
recovery channel stays up. `/setting` (p2) is the only filesystem writable via
senser `FileControl`; `/system` (p3) and `/usr` are read-only (error 130), p3 is
writable only as a raw device.

## 3. Dead ends and lessons

- **RAM patch does not survive.** A senser memory write needs service mode, and
  exiting service mode reboots the camera, which reloads av-cam from storage (auto
  power-off does the same). Writing over `Stage_SoftFocus` in live DRAM verified
  fine but never reached a capture. No "resume without reboot" command was found.
- **File replace via FileControl is impossible.** `writeFile('/setting/x')` works;
  `/system/av-cam.bin` and `/system/x` fail with error 130. Hence raw partition write
  through the updater shell. Other ideas (patch `im.elf` to load `/setting/av-cam.bin`,
  redirect the Loader2 table at Backup `0x00FA0080`) were judged riskier (bootloader
  data, brick risk) and not needed.
- **`session[+0x3e24]` is not the buffer** (value `0x1df`, not a pointer; writing
  through it crashed). The accessor `0xc36045fc` output was a misleading lead; the
  real buffer was found with a diagnostic build that dumped session fields to a
  scratch address, then testing each pointer (autocorrelation width, JPEG SOI at
  `0x0e000000`).
- **Replacing `Stage_SoftFocus` wholesale breaks the dataflow** develop -> SF ->
  encode (crash after preview). Wrap it, do not replace it.
- **Always-run hook `0xc3889760` (gate `r4[0x3c]` in {1,2}) did not pan out** as the
  encode-input stage: the detour (`build_detour.py`, trampoline after the gate, stub
  in the cave) was built and verified offline, but the hypothesis that it is the
  encode-input stage was not confirmed (it grained via the wrong `session[0x3e24]`
  pointer and its per-capture invocation count was never established). An always-run hook
  (no Picture Effect needed) is still open.
- **`lzpt_write` uses a multiprocessing Pool**: on spawn platforms (macOS/Windows) any
  script calling it must be under `if __name__ == "__main__":` or it fork-bombs.
- Always md5-verify the entire flashed partition and keep the original for restore.

## 4. Open items

- Single develop -> encode chokepoint (one hook for all modes, no Picture Effect
  needed): pin the `0xc35dcxxx` enc hand-off or find a stage that always runs.
- Resolve the YC-handle -> DRAM accessors (`0xc36045fc` / `0xc36046ac`) to get base
  and stride generically at any hook point.
