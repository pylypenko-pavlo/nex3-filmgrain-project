# H — Q-31 / Q-3 (p8): data flow of `sa_yknr`, `sa_kknr`, `sa_sftfcs` from the scalar DMA code

Date: 2026-10-09. Static / offline only. Nothing was flashed, the camera was not touched.
Claim IDs here are temporary (`H-<AREA>-NNN`); `relates` points to atlas IDs. Statuses use the atlas vocabulary.
Harness and scripts: `~/nex3n-dump/work/q31/` (README.txt there). Module files: `~/nex3n-dump/safeboot/out3n/nflasha8_unpacked_unpacked/sabin/`.

## 0. Result on one screen

All numbers come from running each image's scalar code in an offline interpreter with a synthetic job
(4912 x 3264, three DRAM buffers A=job[0], B=job[4], C=job[8] placed 64 MB apart) and decoding every DMA chain at every
`str ..,[0x48230]` ("go"). The VLIW engine is **not** executed, so this is a map of DRAM traffic, not of arithmetic.

| module / image (descriptor file offset) | reads (DRAM) | writes (DRAM) | what it is | full frame? | pixel write? |
|---|---|---|---|---|---|
| **yknr y0** (0x100, "YKNR_0__0x01", 2 VLIW progs) | A: 1400 windows 128x96 px (2 B/px), all of W x H; later C planes | **C only**: 16 B x 12 rows per window into plane P0, then P1,P2 | analysis pass -> 1/8-scale maps (8x8 px per map px) | reads full frame, writes ~2.4 MB of maps | **no** |
| **yknr y1** (0x3eb0, 1 prog) | C: P0 | C: P3, P4 | map -> map | no | no |
| **yknr y2** (0x75c0, 1 prog) | C: P1..P4 | C: P5, P6 | map -> map | no | no |
| **yknr y3** (0x9e60, 1 prog) | **A: 15912 tiles 128 px x 8 rows (=39 x 408)** + per tile 2 map windows (24 B x 2 rows) from P5 and P6 | **B: same 15912 tiles at the same offsets** | per-tile apply stage, out of place A -> B | **yes, whole W x H** | **yes (YUYV tiles, both byte lanes)** |
| **kknr k0** "KKNR_PRE" (0x400) | A: 3264 rows x 9824 B | A: same 3264 rows | row filter, in place | yes | yes (in place) |
| kknr k3 (0xb080) | A tiles 512 B x 8 rows + 2 map rows from C | A same tiles | tile filter with maps, in place | emulated coverage not trustworthy | likely yes (in place) |
| **kknr k4** (0xe400) | A: 3264 rows (reverse order) | B: 3264 rows | row copy/filter A -> B | yes | yes |
| kknr k1 "KKNR_KK1" (0x1d80), k2 (0x6080) | k1: A 1632 rows; C maps | C | analysis (k1), maps only (k2) | emulation parked in idle loop; incomplete | no pixel write seen, **unverified** |
| **sftfcs s0** (0x100) | A: 7752 tiles 128 B x 32 rows | C: 3 small planes | analysis | read full, write maps | no |
| sftfcs s1 (0x2c20) | C | C | map -> map | no | no |
| **sftfcs s2** (0x6cc0) | A: 7854 tiles 128 B x 32 rows + 9 map windows per tile (C) | **B: same 7854 tiles, same offsets** | per-tile apply, out of place | **yes** | **yes (method control OK)** |

Verdicts:
- **YKNR writes full-frame pixels**, but only in its last stage (y3), out of place: reads buffer job[0], writes buffer job[4]. The three earlier stages touch only a ~2.4 MB scratch (job[8]). The fingerprint of y3 is identical to the known pixel writer `sa_sftfcs` s2 (control passes).
- Luma vs chroma is **not decided** by DMA: tiles are interleaved YUYV rows (both lanes move, both lanes are written back).
- YKNR is a candidate grain host, not a proven one (section 6): the scalar side never touches pixels (about 270 scalar steps per tile), the engine kernel is opaque, and it is not shown that stills run it or that the encoder reads its output.
- Q-26: no noise generator in any picture module's scalar code (section 7). The only classic LCG is in `sa_aaclcdec` (audio).

## 1. Method and its limits

1. Disassembly with `sadis.py --desc <off>`; call sites by a crude literal-tracking call graph (`cg.py`).
2. Interpreter = `saemu.py` core, wrapped (`trace.py`): hooks stores to `0x48234` (chain pointer) and `0x48230` (go), then decodes the 16-byte descriptors in local memory until `w1 == 0x40000000`.
3. Entry points per image were found from the loader stub (`bl 0xd0` / `b 0x1c`) and the framework (`bl validate; bl main`). The job struct is built to pass the module's own validation (all range checks listed in H-MOD-001).
4. Limits (all of them matter): float ops, `wfi`, `0009` are no-ops; MMIO reads return 0; the VLIW engine and the other cores are not run, so inter-core handshakes (`0x94e0` flags) are not exercised; images y1..y3 and s1, s2 were started from their main function with a parameter block copied from y0's validation (YKNR) or from a fresh job (sftfcs); geometry (counts, offsets, row lengths) is data-independent in every case I varied (strength fields all zero -> identical DMA stream; frame 1448x640 -> 12 x 80 = 960 write tiles).
5. Tooling defect found on the way (H-TOOL-001): `saemu.py` does not map the module text into data memory, so byte jump tables (`ldrsb r1,[r4,r0]; add r1,r0; b r1`, e.g. yknr y0 0x7de, y1 0x20e, y3 0x906) read zeros. With text mapped the same code runs to completion.

DMA descriptor, as observed (16 bytes, local memory, chain ended by `{1, 0x40000000}` in every module and image run here; the `{2, 0x40000000}` of the 0x105d0 note was not seen):

```
w0 = ext & 0x3fffffff               (job pointer after the module's translate function)
w1 = flags | (local_byte_addr >> 2)  bit31 = write; read flags 0x3ff8xxxx (1-D) or 0x00f8/0x0078/0x0038..xxxx (2-D)
w2 = ((row_bytes - 1) << 16) | ext_row_stride_bytes / 8        (2-D)   |   (nwords-1)<<16, w3 = 0 (1-D, kknr)
w3 = 0x01 00 RR RR  (2-D)         RR = rows - 1 in both low bytes (0x0707 = 8 rows, 0x5f5f = 96, 0x1f1f = 32, 0x0b0b = 12)
```

Check of the 2-D reading: yknr y3 apply tile 256 B x 8 rows (`0xff`, `0x07`), stride field 0x0500 = 10240/8 for stride 5120 px; y0 first window 168 B x 52 rows (84 px x 52 rows = 128-44 px by 96-44 rows, the clipped corner window). KKNR rows: 0x265f+1 = 9824 B = 4912 x 2 (matches C-MEM-005 stride 0x2660).

## 2. sa_yknr, image by image

### 2.1 Job struct (validation function, image y0, text 0x1c8..0x3c6, called from framework 0x122)

`r9` = job (local address, after the framework's translate). A failed check returns -11..-16 for the pointer/size fields and `0xffffff75 ..` / `0xffffff00`-style negative codes for the rest.

| offset | check in code | meaning (mine) |
|---|---|---|
| +0x00, +0x04, +0x08 | `(v & 7) == 0` (0x1f4-0x20c) | three DRAM buffer addresses A (in), B (out), C (scratch); translated by 0x189c at 0x3ce/0x3d6/0x3de |
| +0x0c | none; copied raw to param[0x0c] | unknown (not read by any path I ran) |
| +0x10 | `> 639` (cmp 0x27f at 0x210), `& 7 == 0` | width in px |
| +0x14 | `> 479` (0x1df at 0x220), `& 7 == 0` | height in px |
| +0x18 | `& 7 == 0` (0x226) | **row stride in px** (descriptor stride = 2 x this); changing it moves ext offsets 5120 -> 6000 px exactly as predicted (33.35 MB -> 39.08 MB) |
| +0x1c, +0x20, +0x24 | `<= 0xff`, `<= 0x100`, `<= 0x100` | parameters (strength-like) |
| +0x28 | `<= 0x7ff` | parameter |
| +0x2c, +0x30 | `<= 0xff`; and `+0x2c <= +0x30` (0xff01) | low/high pair |
| +0x34 | `<= 0x7ff` | parameter |
| +0x38, +0x3c | `<= 0xff` | parameters |
| +0x40 .. +0x7f | second block: bytes <= 0xff / 0x100, two indices <= 25 with `[+0x64] >= [+0x68]`, two signed offsets in -1024..-1 (+0x6c, +0x74), two values <= 0x3fff (+0x70, +0x78), one flag <= 1 (+0x7c) | tables, probably from Backup `0x0003004c` (not tied) |

Struct fields flow into a derived parameter array at local `0x93e0` (`PAR`); `PAR+0x7c` holds the plane table (H-MEM-001).

### 2.2 y0 (core image 0; text 0x410..0x3eb0 in the file)

Evidence (text-relative addresses):
- validation 0x1c8-0x3c6; derive/translate 0x3c8-0x550 (`bl 0x189c` x3 at 0x3ce, 0x3d6, 0x3de; plane base arithmetic 0x40c-0x4a2);
- main `0x998` (called at 0x176, `r4 = 0x93e0`); read builder `0x56c`, strip builder `0x714`; first DMA go 0xa5a; steady goes 0xb00 (1400x); second pass goes 0x103c, 0x10cc (44x); final 0x167e; descriptor lists alternate between local 0x9000 and 0x91f0 (ping-pong, 724 + 724 goes).
- Write builder (only one family): `ldr r8,[pc]=0x80001600` at 0xba0, `0x80001400` at 0x13fc, `0x80300000` at 0x111a. Every write base comes from plane pointers in PAR (C), never from PAR[0] (A) or the B pointer.

Chain examples (emulated, run `t2.py`):

```
go#0   pc=0xa5a  R A+0x0     w2=00a70500 w3=01003333      ; 168 B x 52 rows, clipped corner window
go#2   pc=0xb00  R A+0x1a8   w2=00ff0500 w3=01003333      ; 256 B per row
                 W C+0x0     w1=80081400 w2=000f004f w3=00100b0b   ; 16 B x 12 rows into P0, ext stride 632
go#1100 ...      R A+0x18e33a8 w3=01005f5f (96 rows)  W C+0x32100
```

Totals: A read 1400 windows (40 x 35), offsets 0 .. 0x1f74658 (full frame at stride 10240 B); C write 1832 chains, offsets 0 .. 0xbf9e8 (P0..P2 only), C read 216; **no write to A or B**; **0 executions of `0009`** in this flow (engine launches live in other code, see H-DSP-002).

### 2.3 y1 (desc 0x3eb0) and y2 (desc 0x75c0)

Same framework and builders at different addresses (y1 write builder `0x80380000` at 0x616; y2 `0x80300000` at 0x812). Entry points used: y1 main 0x288 (called at 0xfe), y2 main 0x428.
- y1: 62 goes; reads C 0x278..0x3cc98 (P0); writes C 0xc1f80..0x1bb040 (P3, P4: two writes per tile, bases `[PAR+0x7c+48]` and `[...+52]`).
- y2: 93 goes; reads C 0x40a80..0x1bd6e0 (P1..P4); writes C 0x1c4980..0x2418b0 (P5, P6).
These stages never address A or B.

### 2.4 y3 (desc 0x9e60, text 0xa170..0xd0d0 in the file) — the pixel stage

Code: framework stub 0xd0 loads `r4 = 0x93e0` and calls `0x3f4` (call at 0xfa). Main loop 0x768-0x90c. Write-chain builder (all text-relative):

```
 798: 61e3  ldr r3,[r14,#4]        ; r14 = PAR -> job[4] = B (translated)
 79c: 66e0  ldr r0,[r14,#24]       ; stride (px) = job[0x18]
 7aa: 5668  ldr r8,[pc]=0x80000000 ; write flag
 7ae: f072  lsl r2,#7              ; col * 128 px
 7bc/7be:   r5=0xf80000  r6=0xff0000   ; w1 / w2 templates (row bytes - 1 = 0xff)
 7c8: 66f7 ldr r7,[sp,#24]  f012 lsl r2,#1   ; stride, byte offset = 2 B/px
 7ce: f017 lsl r7,#1               ; row stride in bytes = 2 * stride
 7d0: 2273 mul r3,r7  7d2/7d4 add  ; ext = B + row8 * 2*stride + col128 * 2
 7e0: ldr r4,[pc]=0x01000707       ; w3: 8 rows
 7e6-7f8: w0 = ext & 0x3fffffff ; w1 = 0x80f8xxxx | local ; w2 = 0xff0000 | (2*stride >> 3) ; w3
```

Observed chain pattern (steady state, goes at pc 0x77e, 3183x, lists alternate 0x9000 / 0x91f0):

```
go#2  W B+0x0..0x400   5 tiles, w1=80f81400,80f82800,80f83400,80f84000,80f84c00   (local 0x5000,0xa000,0xd000,0x10000,0x13000)
      R C+0x1c4a20  w1=00101600 w2=0017004d w3=00180101      ; P5 window 24 B x 2 rows -> local 0x5800
      R C+0x2054a0  w1=00101700 w2=0017004d w3=00180101      ; P6 window            -> local 0x5c00
      R A+0xa00     w1=00f81400 w2=00ff0500 w3=01000707      ; next tile into the SAME local buffer
      ... (x5)
```

The write source local buffer equals the read destination of the previous tile (`w1` low 16 bits identical): read -> engine (other core, in place) -> write. Two sets of five tile buffers alternate (set 2: local 0x6800, 0xb800, 0xe800, 0x11800, 0x14800).

Totals: A read 15912, **B write 15912 at identical offsets** (0 .. 0x1fce600 for stride 5120 px), C read 31824 (2 per tile, only P5 and P6 at C+0x1c4980.., C+0x205400..). Never writes A or C. Scalar cost: 4 254 419 emulated steps for 15 912 tiles = **267 steps per 2 KB tile**, i.e. no per-pixel scalar loop anywhere in the path.

Sensitivity runs (`t8.py`, `t10.py`): job[0x0c] changed -> no effect; job[0x18] 5120 -> 6000 moves offsets; strength fields (+0x1c..+0x3c) all zero -> identical 47 736 reads / 15 912 writes (no skip-on-zero); 1448 x 640 -> 960 write tiles (12 x 80).

## 3. sa_kknr (5 images; job parsed by `0x23c` into a frame at local 0x2e40)

Job: +0x00, +0x04 = buffers (translated at 0x25a/0x262), +0x08/+0x0a/+0x0c = u16 width / height / row stride in **bytes**, +0x10.. small u8/u16 parameters (face-map fields `kk_fm_*` by name), +0x14 = pointer (translated at 0x29e, a third buffer). Per-image mains: k0 0xdc4, k1 0xee8, k2 0x1074, k3 0xe64, k4 0xc2c.

- **k0 (KKNR_PRE)**: 1-D transfers of whole rows (`w2 = 265f0000` = 9824 B, `w3 = 0`). Chain order: read row n, read row n+1, then write row n (`W A+0x0`, flags `a6583000`) to the same offset. 3264 reads + 3264 writes, identical offsets in A: in place with a one-row delay. Go sites 0xf5a (read), 0x1038 (write). 333 298 steps (about 100 per row).
- **k4**: reads A rows in reverse order (`A+0xf490d0`, `+0xf47da0` ... at a 4912 B step because job stride was set to 4912), writes B rows (`W B+0xf490d0`, flags `a6583400`): A -> B, 3264 rows, go sites 0xde0 / 0xe9e.
- k3: 2-D tiles 512 B x 8 rows, four reads then four writes of the same A tile (flags `01f8xxxx`/`81f8xxxx`, `w3 = 02080303/0707`) plus 2 map rows (80/132 B x 2) from C per tile; in my run the tile coordinate did not advance (same `A+0xf3bdc0` repeated), so the coverage number (4090) is not trustworthy. Direction (in-place A) is solid.
- k1 / k2: run ended in the framework idle loop (`wfi; b` at 0x98..0x9c) after 3368 / 5712 goes; k1 reads A rows (1632) and writes C; some descriptors carry uninitialised fields (`w2 = ffff0266`). Treated as unresolved.

## 4. sa_sftfcs, control (known pair sharp -> blurred)

Job (matches C-MOD-020/021): +0..+8 buffers, +0x0c/+0x10 3x3 kernels, +0x14/+0x18 5x5 kernels, +0x1c width, +0x20 height, +0x24 stride (px), +0x28, +0x2c, +0x34 levels. Entry `0x16dc` (validate `0x1cd4` -> `0x1b28`, derive `0x1c38`, plan `0x1808`, work `0x1118`).
- s0: 4080 goes (pc 0x1328, 0x1636), 3978 `0009` with `r0 = 0x1c`: reads A 7752 tiles (128 B x 32 rows), writes three small planes to C (16 B / 8 B rows, ext strides 1272 / 656): analysis.
- s1: 427 goes, `0009` tables 0x1c, 0x98, 0x12c, 0x1e8 (matches the 3x3 / 5x5 pairs of C-MOD-022): C -> C.
- **s2: 4120 goes, 12 051 `0009` (tables 0x1c, 0xac, 0x11c, 4017 each), reads A 7854 tiles + 9 map windows per tile from C, writes B 7854 tiles at the same offsets** (e.g. go#100: `W B+0x9aa00`, `W B+0x9aa80`, then nine C reads and `R A+0x9ac00`): a full out-of-place tile pass, as expected for Soft Focus. So "R tile from X, R maps, W same tile to Y != X, tile count = ceil(W/64) x ceil(H/32)" is what a pixel stage looks like in this method; yknr y3 and kknr k0/k4 match it, y0..y2 do not.

## 5. Claims

### H-MOD-001: The `sa_yknr` job struct (local pointer in r9 at `0x1c8`) holds three DRAM buffer pointers A/B/C at +0/+4/+8, width +0x10 (> 639, multiple of 8), height +0x14 (> 479, multiple of 8), row stride in pixels +0x18 (multiple of 8, descriptor stride = 2 x), and about 40 range-checked parameter words; +0x0c is copied but unused in all paths run
- status: verified-code
- evidence: y0 text 0x1c8-0x3c6 (each check read: 0x1f4/0x1fc/0x204/0x20c alignment, 0x210/0x212 `cmp.gts r3,0x27f`, 0x220 `0x1df`, 0x226, 0x230-0x2ae limits, 0x354-0x3a8 second block); stage-1 emulation returns 0 for the synthetic job; varying +0x18 moves every ext offset (5120 -> 6000 px: 33 351 168 -> 39 081 728 B) and varying +0x0c does not
- source: this extraction (`t1.py`, `t8.py`)
- date: 2026-10-09
- relates: C-MOD-026, C-MOD-021 (same checking style as sftfcs), C-DSP-022

### H-MOD-002: `sa_yknr` is a four-stage tile pipeline: y0 analysis of A into 1/8-scale maps in C, y1 and y2 map-to-map stages, y3 per-tile apply that reads A plus maps P5/P6 and writes B
- status: verified-code (stage contents from the scalar DMA code); hypothesis (that the four images are scheduled in this order by the loader; the order follows from map data dependencies: y3 reads exactly the planes y2 writes, y2 reads what y0/y1 write)
- evidence: emulated DMA totals in section 2 (y0 C W 0..0xbf9e8; y1 C R 0x278.., W 0xc1f80..0x1bb040; y2 C R 0x40a80.., W 0x1c4980..0x2418b0; y3 C R 0x1c4980.. and 0x205400..); descriptor dumps `an4.py`
- source: this extraction
- date: 2026-10-09
- relates: C-MOD-026, C-DSP-003 (per-core images), C-MOD-005

### H-MOD-003: Image y3 of `sa_yknr` writes the whole frame as 128 px x 8 row YUYV tiles into buffer job[4] (B), reading the same tiles from job[0] (A); for 4912 x 3264 that is 15 912 = 39 x 408 write chains, offsets identical to the reads
- status: verified-code
- evidence: builder at y3 0x790-0x7f8 (listing in 2.4); go sites 0x6fe, 0x77e (3183 x), 0x9ee; `an3.py y3`: `A R 15912, B W 15912, off 0..0x1fce600`; 1448 x 640 gives 960 tiles; strength fields do not gate the writes
- source: this extraction (`t5.py 0x9e60 0x3f4`)
- date: 2026-10-09
- relates: C-MOD-026, C-DSP-020, C-MEM-005, C-ISP-006

### H-MOD-004: Images y0, y1, y2 of `sa_yknr` never write A or B; their only DRAM writes go to the scratch buffer C (seven maps of about 2.4 MB in total for 4912 x 3264)
- status: verified-code
- evidence: `an3.py`/`an5.py` on y0 (C W 1832, A W 0, B W 0), y1 (C W 600), y2 (C W 902); write builders `0x80001600/0x80001400/0x80300000` (y0), `0x80380000` (y1), `0x80300000` (y2) take their base only from the plane table at PAR+0x7c
- source: this extraction
- date: 2026-10-09
- relates: C-MOD-026, C-IDT-010 (same "statistics, no pixel write-back" signature)

### H-MEM-001: The scratch buffer C of `sa_yknr` is a table of seven planes at 1/8 scale; for width W, height H: mw = W/8 + 1, mh = H/8 + 1, padded width mw + 10 rounded up to 8 (= row stride in bytes), plane size = stride x (mh + 10) rounded up to 128, planes P0, P1, P2, P3 (2 units), P4 (2 units), P5, P6 in that order
- status: verified-code
- evidence: derive code 0x3c8-0x4aa; four geometries run (`t11.py`): 4912 x 3264 -> mw 615, mh 409, stride 632, unit 0x40a80, plane offsets 0, 0x40a80, 0x81500, 0xc1f80, 0x143480, 0x1c4980, 0x205400 (end 0x245e80); 1448 x 640 -> mw 182, mh 81, stride 192, unit 0x4480; 2456 x 1632 -> 308 x 205, stride 320; 4928 x 3264 -> 617 x 409, stride 632
- source: this extraction
- date: 2026-10-09
- relates: C-MOD-026, C-DSP-022

### H-DSP-001: The 2-D DMA descriptors of the SA modules carry bytes-per-row in w2[31:16], external row stride / 8 in w2[15:0] and rows - 1 in both low bytes of w3; w1 bit 31 selects write; 1-D transfers (kknr) use w3 = 0
- status: hypothesis (consistent in all four modules, not hardware-verified)
- evidence: apply tile `w2=00ff0500 w3=01000707` = 256 B x 8 rows at stride 10240 B; clipped corner window `00a70500 / 01003333` = 168 B x 52 rows (84 x 52 px); P0 write `000f004f / 00100b0b` = 16 B x 12 rows at map stride 632 (0x4f x 8); sftfcs `007f04cc / 00801f1f` = 128 B x 32 rows at 9824 B; kknr `265f0000` = 9824 B
- source: this extraction (descriptor dumps)
- date: 2026-10-09
- relates: C-DSP-033, C-IDT-010, C-IDT-017

### H-NR-001: Whether `sa_yknr` filters luma, chroma or both is not decided by its DMA traffic: tiles are interleaved YUYV (2 B/px), both byte lanes are read and written back
- status: unknown
- evidence: y3 tile = 256 B/row for 128 px (`0xff`, stride x 2); the write returns the full tile; map resolution is one value per 8 x 8 luma px (P5/P6 windows 24 B = 16 + 8 margin, 2 rows) which fits luma but does not exclude chroma. Not usable: names (`YKNR`, `kk_fm_*`), engine constants (-8, 32, 16, 16, -2, ...), reciprocal LUT. Still open: Backup NR-3 (close the `0x3004a` window) and look at sigma(L*) versus sigma(a*b*), or an `YKNR_Debug_MSDump` of buffers A and B
- source: this extraction; C-MOD-026 notes
- date: 2026-10-09
- relates: C-MOD-026, C-NR-007, C-NR-011, Q-31 (07)

### H-MOD-005: `sa_kknr` image 0 (KKNR_PRE) filters whole 9824-byte rows in place in job buffer 0 (3264 reads, 3264 writes at identical offsets, one-row delay), image 4 copies rows buffer 0 -> buffer 1 in reverse order; image 3 is an in-place tile pass with two map windows per tile; images 1 and 2 are analysis/map stages whose emulation did not complete
- status: verified-code (k0, k4 direction and count); hypothesis (k3 coverage); unknown (k1, k2)
- evidence: section 3; go sites k0 0xf5a/0x1038, k4 0xde0/0xe9e, k3 0x10ac/0x10ec/0x11b0/0x1364; job parse `0x23c` copies `[0]`/`[4]` translated, u16 width/height/stride at +8/+10/+12
- source: this extraction (`k2.py`)
- date: 2026-10-09
- relates: C-MOD-027, C-NR-008

### H-MOD-006: Control: `sa_sftfcs` image 2 shows the same fingerprint as yknr y3 (A tiles + map windows read, same tiles written to B, 7854 = 77 x 102 tiles), images 0 and 1 write only small planes in C
- status: verified-code
- evidence: `an5.py s2`: A R 7854, B W 7854, offsets 0..0x1e4a200; s0: C W only; s1: C only; `0009` tables 0x1c/0x98/0x12c/0x1e8 as in C-MOD-022
- source: this extraction (`t6.py`, `t9.py`)
- date: 2026-10-09
- relates: C-MOD-020, C-MOD-021, C-MOD-022, C-MOD-023

### H-DSP-002: Scalar code calls into the body of the VLIW program directly (`bl r` with literals 0x3180, 0x31b8, 0x3260, 0x32b8, 0x3408 inside yknr y0's program 0x30c0..0x36c0, most of them 8-byte aligned on the bundle grid), besides the `0009` command-table launch
- status: hypothesis
- evidence: y0 call sites 0x19b6 (`bl 0x31b8` from a per-core entry stub that sets `sp = 0x4000`), 0x1b94/0x1bbc (`0x3260`), 0x1bb4/0x1bce (`0x32b8`), 0x1d7a and 0x1f5e (`0x3180`, right after the engine-register stores 0x1d10-0x1d54), 0x1cac (`0x3408`); program headers found at y0 0x30c0 and 0x36c0, y1 0x2ab0, y2 0x2170, y3 0x2880 (5 programs); `0009` wrappers at y0 0x1b22, 0x20d6, 0x2516, 0x2956, 0x2d96 (5 per image except y1: 10). Other cross-image targets (0x414c, 0x4114, 0x814c ...) do not resolve to any text of the files and are unexplained
- source: this extraction (`cg.py`)
- date: 2026-10-09
- relates: C-DSP-009, C-DSP-021 (claims that nothing addresses the VLIW program), C-DSP-019

### H-DSP-003: The scalar side of yknr y3 spends about 267 steps per tile (2 KB), of kknr k0 about 100 steps per 9.8 KB row, so no per-pixel scalar loop exists in these paths
- status: verified-code (emulated step counts)
- evidence: y3 4 254 419 steps / 15 912 tiles; k0 333 298 steps / 3264 rows; s2 10 472 213 steps / 7854 tiles incl. `0009` bookkeeping
- source: this extraction
- date: 2026-10-09
- relates: C-DSP-020

### H-PIPE-001: In the stage order drawn in 02, YKNR (10b) is followed by sharpening (11), DRO (12), picture effects (13) and resize (14), so anything written by y3 can still be altered before the YUYV canvas that the encoder reads; that order is not measured
- status: hypothesis
- evidence: 02 stage table rows 10b, 11, 12, 13, 14, 15 and the "Order note" (C-PIPE-007); DMA data here only shows the sink buffer B of YKNR, not who consumes it
- source: 02-capture-pipeline.md
- date: 2026-10-09
- relates: C-PIPE-001, C-PIPE-007, C-ISP-006, C-NR-007

### H-PIPE-002: Technical slot for "add a noise table to Y before the write": inside y3's tile loop between the engine pass and the write-chain build, on the local tile buffers (set 1 at 0x5000, 0xa000, 0xd000, 0x10000, 0x13000; set 2 at 0x6800, 0xb800, 0xe800, 0x11800, 0x14800; 2 KB each, Y in even bytes if YUYV holds), as a scalar loop; a VLIW change is not feasible because the VLIW semantics are unknown
- status: hypothesis
- evidence: read destination = later write source (same `w1` low bits); the build loop at y3 0x790-0x806 and the go at 0x77e are the only scalar points between engine and DMA; 1024 px x 15 912 tiles = 16.3 M pixels per frame against the present 267 steps per tile; cross-core handshake (`0x94e0`, `wfi` at 0x748/0x854/0x9f8) must be preserved; C-DSP-015 (VLIW op meanings unknown)
- source: this extraction
- date: 2026-10-09
- relates: C-DSP-015, C-DSP-020, C-IDT-010, C-MOD-011 (loader checks unknown)

### H-TOOL-001: `saemu.py` leaves the module text out of data memory; loads from code addresses (byte jump tables, `ldrsb r1,[r4,r0]`) return 0
- status: verified-code
- evidence: first y0 run took the table branch to 0x804 and executed the undefined halfword `0x0008`; with text preloaded (`trace.py`, one line) the same run completes; affected sites include y0 0x7de, 0x153c, y1 0x20e, 0x754, y3 0x906
- source: this extraction
- date: 2026-10-09
- relates: C-DSP-019 (emulator-derived register maps were produced with this interpreter and are not re-run)

## 6. Is `sa_yknr` a grain host? (question 4)

For:
- The only p8 NR module shown to write the full YUYV frame tile by tile with scalar-controlled DMA in and out and a small, scalar-visible tile buffer in between (H-MOD-003, H-PIPE-002).
- B is distinct from A in the DSP code, so inserting a term in y3 does not need to preserve a read-after-write order across tiles; the analysis stages have finished before y3 starts (they feed it through P5/P6).
- A data-only lever exists: P5 and P6 are plain 8-bit maps in C at C+0x1c4980 and C+0x205400; changing how y2 builds them (or the parameters that feed y0..y2) changes what y3 does without touching VLIW. That is NR strength, not grain.

Against / open:
1. Not shown that stills run it: av-cam opens it (0x1c), enable function `0xd5760` is off at NR level 0, off in several modes, and gated by the ISO window of `0x3004a` (C-NR-007). A grain host that vanishes at low ISO or with NR off is a poor host unless the window is widened first.
2. Not shown that B is the buffer the JPEG encoder reads; ARM may pass A = B (in place is safe for this algorithm, because all analysis precedes the apply stage) or a temporary.
3. Stages after it (sharpen, DRO, effects, resize, H-PIPE-001) can change or remove a noise term.
4. VLIW kernels cannot be edited; a scalar per-pixel loop adds ~10x scalar work per tile and may break the timing contract with the other cores.
5. kknr k0 and k4 are comparable candidates by the same fingerprint, but KKNR runs only with faces (`Start_Face_Nr`, C-NR-008) -> worse host.

Verdict: plausible and the best candidate among the three analysed modules, **unproven**. Cheapest discriminating steps: (a) NR-3 experiment (close the YKNR window, measure sigma of L* and a*b* at ISO 800/3200); (b) `YKNR_Debug_MSDump` path (C-MOD-032/033) to dump A and B and compare; both are low risk.

## 7. Q-26 — noise generator in the 32 p8 modules (scalar code)

Sweep (`prng.py`, `prng2.py`): 14 canonical constants (1103515245, 1812433253, 1664525, 1013904223, 214013, 2531011, 134775813, 0x9e3779b9, 0x4c957f2d, 0x5851f42d, 69069, 0x2545f491, LFSR taps 0xd0000001/0x80200003/0xa3000000/0xb400) over every byte offset of all 32 `sa_*.bin`; xorshift shift triples (13,17,5), (13,7,17), (7,9,8) in a 40-byte window with an `eor` in each scalar image; every scalar literal > 0xffff that is later multiplied.

### H-NR-002: No picture-processing module contains a classic PRNG in its scalar code; the only match is `sa_aaclcdec.bin` with the Numerical-Recipes pair `0x0019660d`, `0x3c6ef35f` adjacent in a literal pool at file 0xef18/0xef1c (audio decoder, probably noise substitution), and no xorshift shift pattern occurs in any module
- status: verified-code (for the scalar code and the constants listed); unknown (VLIW bundles, MMIO noise sources)
- evidence: the `LFSR32` hits (apollo4, avce_quality, dfdet, tbox, star, ...) sit in bundle/data regions with a probability consistent with chance; the one that looked like code, `sa_defect` image 0x100 `ldr r12,[pc]=0x69f165f7` then `mul` at 0xfac, reads its "literal" from the middle of an instruction run (0xfc8: `65f7 69f1`) and is a decoding artefact; `0xb400` in `sa_pbe_work` 0x5ca is a local buffer address (0xa400, 0xb400, ...)
- source: this extraction
- date: 2026-10-09
- relates: Q-26, C-PIPE-004

## 8. What this does not settle (kept for 07)

- Q-31: luma/chroma of YKNR and chroma role of KKNR remain open (H-NR-001); KKNR is more likely face-map driven than chroma-only, but no new evidence.
- Q-3 for p8: only yknr, kknr (partial), sftfcs classified; pbe_work, star, spica, tbox, bdro2_bdex, apollo4, defect, frc2, shapep, fc_recog, dfdet, sweep_panorama are not. The harness now exists (`~/nex3n-dump/work/q31/`), the per-module cost is finding the main function and a job that passes validation.
- Who starts y1..y3 and when, and whether `0x94e0` flags order them: not read.
- av-cam side (`YKNR_START_PARAM` field names, which `Image` planes are passed, whether A == B) was not resolved; the string xrefs exist (C-MOD-032) but the code that fills the struct was not located.
