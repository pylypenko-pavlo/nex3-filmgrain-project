> SUPERSEDED (2026-10-21). The DSP-side grain route described here is closed: it is blocked by hardware
> (see the root README, 'Results: grain'). The route that shipped is the Linux LD_PRELOAD shim in
> `code/grain-shim/`, runbooks `atlas/grain-linux-*`. This page is kept for the engine/VLIW
> findings; its 'next steps' and 'active path' wording is historical.

# GRAIN — RESTART POINT
> **2026-10-19 late: stuck → fresh-eyes review. Read `grain-fresh-eyes-brief.md` first (whole picture E-1..E-17).**
> (updated 2026-10-19 evening) — read this to resume the grain work

Goal unchanged: real film **colour grain** in the SOOC JPEG via the **Soft Focus** effect ("select Soft Focus →
get grain"). Authoritative detail: `engine-command-table.md` sections "sftfcs STEP-1 … STEP-3 / E-8" (in order).

## TL;DR — where we are
- **INJECTION WORKS (camera-proven, E-5):** a scalar write to the engine's UYVY input tile, done **right before the
  engine launch** (`bl 0x194` @0x1412, pass1), reaches the SOOC JPEG as chroma. E-5 (`sa_sftfcs_grain1e42.bin`,
  bd5fd653) = const 0x40 into all even (U/V) bytes → **green vertical stripes** (pass1 only; pass2 @0x15ac does the
  interleaved alternate columns). Frame: `work/filmgrain/results/E5_grain1e42_const40_pass1_greenstripes.JPG`.
- **Hook mechanism:** patch the launch literal at text 0x156c `0x194 → 0x1e42` (pass2 literal = 0x16b0); cave at
  0x1e42 runs, then `ldr r2,=0x194; b r2` tail-calls the real wrapper (lr=0x1414 preserved). r5 = tilebase-2 live.
- **THE BLOCKER = executable space.** Only **30 B at 0x1e42** is proven executable (padding between the LUT table
  0x1e10-0x1e41 and the reset stub 0x1e60). Enough for a flat constant, NOT for additive per-pixel noise
  (`grain_loop.s` = 52-62 B; minimal additive loop ~36 B).
- **Ready algorithm:** `work/filmgrain/grain_loop.s` (xorshift32 13/17/5 without mul + luma modulation via shift
  table), built with `saasm.py`, checked in `saemu.py` (assembler + emulator EXIST — old "no assembler" note is
  dead). UYVY adaptation: step +2 (even = chroma), luma for modulation from the neighbour byte [r1+1]. Seed =
  per-tile from r5 (owner accepted per-tile; per-frame = stretch).

## Camera results today (E-1..E-8) — the facts that constrain the next step
| # | module (md5) | what | result | meaning |
|---|---|---|---|---|
| E-1 | graintest (549059bb) | cave @0x2038, const write 0x1000 B | HUNG | — |
| E-2 | graintest2 (7e9b8dae) | same, 0x20 B | HUNG | not volume |
| E-3 | noop (cbbdb35e) | NO-OP cave @0x2038 | HUNG | **0x2038 not executable** |
| E-4 | noop1e42 (d60770e5) | NO-OP cave @0x1e42 | OK | 0x1e42 executable, trampoline OK |
| E-5 | grain1e42 (bd5fd653) | const 0x40 to U/V @0x1e42 | **GREEN stripes** | **injection proven** |
| E-7 | grainadd (914d568f) | additive, chain 0x1e42 → `b 0x1e62` | HUNG | see ⚠ below |
| E-8 | 628test (37764849) | const U/V inside fn 0x628 synth loop (4 B) | stock SF, no green | fn 0x628 too early / dead path |
| E-9 | grain30 (a8f0aceb) | additive grain ±4, 30 B @0x1e42 (item 3 below), `build_grain30.py`; saemu OK | captured OK, **NO visible grain** | 20k-instr loop timing OK; noise not detectable (see ⚠ E-9) |

- **⚠ E-9 analysis (DSC09771/09772 vs stock-look DSC09770, flat wall, 7×7 high-pass):** chroma hp-std 0.10-0.16 vs
  stock 0.06-0.14 (exposure differs, not attributable); injected uniform −4..3 has σ≈2.3 → attenuated ≥15× or not
  run. Stripe-mask test (E-5 stripes: period 128 px, ~52 px wide, pass1 columns): E-9 chroma hp-var in stripe vs
  other columns ratio 0.82-1.08 (stock 0.99-1.01) → **no signature**. Cannot distinguish "ran but blurred away" from
  "didn't run". (Corrected after E-11: E-5/E-11 const 0x40 = Cb+Cr −128 vs neutral tints the WHOLE frame: wall
  Cb+Cr −36 in non-stripe columns, −61 in pass1-stripe columns ⇒ DC passes at ~28-48 % weight, stripe edges soft
  ~6-8 px ⇒ strong spatial low-pass between the tile and the JPEG; per-pixel white noise is averaged away.) Frames: `work/filmgrain/results/E9_grain30_DSC0977{1,2}.JPG`.
- **E-10 `grain30_asr25` (be3dcf73, delta ±64) → captured OK, NO visible blotches (DSC09773).** Weak signature only:
  chroma hp-var ~2× E-9 (Cb 0.044-0.051, Cr 0.032-0.041 vs stock 0.019/0.008) and E-5-stripe/other ratio Cb 1.16,
  Cr 1.28 (Y control 1.01). Suggests the loop runs but ±64 arrives attenuated ~100×+; not decisive (exposure differs).
- **E-11 `grain30_fill` (7c127531) = SAME loop, `add r2,r1` → `mov r2,#0x40` → GREEN, identical to E-5** (DSC09774:
  wall Cb 104.7 / Cr 104.3 vs E-5 103.3 / 104.8; same 128 px stripe period and column profile). ⇒ **the E-9 loop
  RUNS on hardware and its writes LAND.** E-9/E-10 invisibility = the downstream low-pass (blur/blend) kills
  per-pixel noise (±64 → ~1/100+ residue, consistent with E-10's weak signature). Fine white chroma noise in this
  tile cannot become visible grain; grain must be at/above the low-pass scale (~8 px) or injected elsewhere.
- **E-12 `lumafill_both` (707a154b) → LUMA PASSES, STRIPES UNCHANGED (DSC09775):** wall Y 95 vs stock 189 (dark runs 82,
  between 126 ⇒ tile weight 0.62 / 0.36 for Y=0x10); chroma untouched (Cb+Cr 254 vs stock 253). Stripes: period 128,
  SAME phase and SAME stripe/between weight ratio (0.58) as E-11 (pass1 only, chroma 0.48/0.28) ⇒ **the pass2 hook
  added nothing** (pass2 not executed in this mode, or its tile does not feed the output); the stripes are how the
  pass1 tile maps to the output, not "unhooked pass2 columns". Stripe edge transition ~16-20 px (blur or cross-fade).
- **E-13 `lumafill_pass2` (c87107ae, Y=0x10, hook ONLY pass2) → looks like stock SF (DSC09776).** No stripes (AC@128
  0.02 vs E-12 0.91), column/row hp-std 0.18/0.13 = stock 0.19/0.08 (only JPEG 8-px block peaks) ⇒ **no tile-scale
  signature from pass2**; together with E-12 = E-11 ratio ⇒ pass2 most likely not executed / not used in this capture
  mode; the 128 px stripes come from pass1 alone. Wall Y 131 vs stock 189 is NOT evidence: t/ISO pinned (1/60, 3200)
  but aperture varies F2.8-F4 with zoom and scene light changed (E-9 wall darker than stock with luma untouched) —
  absolute brightness across these shots is not comparable; a uniform pass2 effect is not strictly excluded.
- **E-14 `ruler` (9f96e8c2, pass1 hook, Y = tile byte>>4) → TILE GEOMETRY MEASURED (DSC09777 flat wall, DSC09778):**
  - **Tile = 64 px wide × 32 rows, UYVY row-major (128 B/row × 32 = 0x1000), 1:1 scale** (vertical ramp period
    32.12 px by FFT; ripple band ~58-64 px wide out of every 128 px column period).
  - **The hooked pass1 launches cover only every OTHER 64-px column** → that IS the 128 px stripe pattern. The other
    64-px columns come from launches/buffers we don't reach (pass2 hook E-13 showed nothing). Atlas: pass1 tile base
    alternates 0x8000/0x9000 (ping-pong) — which buffer maps to which column is unknown → buffer-identity test next.
  - **Low-pass:** the 32-row sawtooth comes out as a triangle (rise ~17-18 rows, fall ~13-14 rows) ⇒ ~14 px
    box-equivalent vertical blur; band edges ~12-16 px horizontally; between-band columns get ~0.2 leakage.
  - **Meaning:** this tile is the input of the Soft Focus BLUR branch (sharp image comes from elsewhere). Anything
    injected here is blurred ~14 px by design ⇒ fine film grain is impossible at this hook; only ≥~16 px blotches
    survive. Fine grain needs a post-blur point (e.g. engine OUTPUT buffer right after `bl 0x194` returns at 0x1414,
    before the output kick `str 0x10000→[0x48208]` @0x1418 + `wfi`) — needs static analysis + more code space.
  - **Post-blur point: DOES NOT EXIST in sftfcs** (static, from the AUTHORITATIVE "STEP-2 CORRECTION" in
    engine-command-table.md): the engine output per 64×32 tile is SRC1=[struct+0xC0] = a **4×2 block** (16× down per
    axis; fn 0xd28 exports it after `bl 0x194`). sftfcs computes only the LOW-RES GLOW layer; the sharp full-res image
    never passes through this DSP, the sharp+glow blend is HW elsewhere. Matches E-14 (2 samples per 32 rows →
    upsampled triangle, ~14-16 px blur) and E-11/E-12 weights. ⇒ **fine film grain cannot be made in sftfcs at all**;
    only ~16 px glow mottling. Fine grain needs a module that carries full-res pixels (candidate: yknr, luma NR,
    chan-3 reaches still luma at high ISO per grain-sftfcs-confirmed.md) — new investigation.
  - **Stripe explanation (hypothesis, static):** each pass has TWO adjacent tiles k0/k1 = LUT_A pair (pp1 0x8000/0x9000,
    pp0 0x5000/0x6000, contiguous). Hook fills 0x1000 from r5 = only k0 ⇒ every other 64-px column. Test: fill 0x2000.
    Static check: pass1 struct base = 0x13000+(pp^1)*0x1b0 (0x13a8-0x13bc), r5 = [base+164] = the FIRST (k0) struct;
    fn 0x4c8 @0x4fa-0x506 writes struct[+164] = LUT_A[k]<<11 ⇒ k1 = k0+0x1000 in both pp pairs.
- **E-15 `ruler_k01` (2a3ff217) → STRIPES REMAIN (DSC09779), k1 hypothesis mostly FALSIFIED:** E-14 with `lsl r0,#9` → fills 0x2000 (k0+k1), k1 ramp = k0 ramp;
  `build_ruler.py k01`; saemu OK for r5=0x7ffe and 0x4ffe (28.7k instr). Expect: ladder in ALL columns, no stripes.
  Result: band ripple energy ~55-64 (same as E-14), between-columns 5-8 (E-14: 1-2) ⇒ k1 adds only a weak (~1/3
  amplitude) contribution to the between columns; column AC@128 0.93 (E-14 0.92). The other 64-px columns are NOT
  produced from the k1 tile at this launch. Capture OK with 28.7k-instr cave.
- **E-16 `bufid` (ff9cd400, k0 Y = (base>>7)) → CHECKERBOARD of 64×32 tiles (DSC09780/81):** inside each band, dark
  (0x8000, Y=0) and light (0x5000, Y=0xa0 ≈ wall level) tiles alternate every 32 rows; neighbouring bands (128 px
  apart) are staggered by 32 rows. ⇒ both pp launches land; pp toggles per launch in a RASTER order of 128-px-wide
  launches, each launch = k0 (left 64 px, ours) + k1 (right 64 px). Between columns = k1.
- **Why k1 was weak in E-15 (static, 0x1268-0x13aa):** per launch fn 0x4c8/0x628 prepare k0,k1 (0x12ac-0x1306), OUT
  ring + kick 0x48230 (0x1310-0x1328), IN ring 0x13700 (0x1330-0x1358), **IN DMA kick `2→0x48218` @0x13aa**, config,
  launch @0x1412 — **nothing waits for the IN DMA** ⇒ our writes race it. E-15 wrote DESCENDING (k1 first) → k1
  mostly overwritten by the still-running DMA.
- **E-17 `fill2k_asc` (21b95863) → STRIPES UNCHANGED (DSC09782/83, depth 42/37 vs E-12 39) ⇒ DMA-race hypothesis NOT supported.** Was: Y=0x10 into k0+k1 ASCENDING (k0 first, k1 last, 16.4k
  instr), `build_fill2k_asc.py`, saemu OK. Expect between columns as dark as bands ⇒ race confirmed, stripes fixable.
  Original plan text: ODD (Y) bytes = 0x10, chroma untouched, `build_lumafill.py
  both`; hooks BOTH passes (literals 0x156c AND 0x16b0 → 0x1e42). Pass2 static check: `ldr r5,[r5,#40]; add r5,#-2`
  @0x1538/0x1540, r5 untouched to `bl r1` @0x15ac; after 0x15ae r0-r3 all reloaded before use; wrapper 0x194 reads only
  r4 ⇒ safe. saemu from 0x1410 and 0x15aa: via cave, lr 0x1414/0x15ae, Y=0x10, chroma + r4-r14 intact. Readout:
  uniform dark ⇒ luma passes + pass2 covers the stripes; dark stripes only ⇒ pass2 hook ineffective; no darkening ⇒
  luma doesn't pass via this tile (pass2 then untested → chroma-fill both); hang ⇒ pass2 hook issue.

## COARSE-GRAIN FEASIBILITY (2026-10-19, saemu + numpy sim, NO flash) ★
The engine downsamples each 64×32 input tile to a **4×2 output block** (16×16 average per output sample; static
"STEP-2 CORRECTION"). So any per-pixel write is averaged by ~1/16 in std before it reaches the JPEG. Simulated
coarse-mottle std at the output (after 16×16 avg + the measured ~0.5 blend weight):
- per-pixel ±4 (E-9) → 0.07 levels; ±64 (E-10) → 1.0; **±128 (max byte) → 2.1 levels (0.8%) — the hard ceiling.**
- block-constant (one value per 16×16): ±16 → 4.4; ±32 → 8.6; ±64 → 17 levels — i.e. 4–8× stronger, visible.
**⇒ Strong coarse grain needs BLOCK-CONSTANT random writes, not per-pixel.** A block-constant loop needs 2D block
indexing (row>>4, col>>4) + centred hash ≈ 10+ loop instr; the 30 B cave holds ≤8 loop instr ⇒ **does not fit.**
`build_lumanoise.py` (per-pixel luma ±128, k0+k1) was built but is pointless to flash (ceiling 2 levels) AND had an
amplitude bug (`asr r3,#24` collapsed the state → delta 0..9); not flashed. "Coarse structure survives" is already
proven by E-14 (32 px sawtooth → triangle), so no new per-pixel flash is warranted.
**⇒ Real coarse/fine grain both require either out-of-cave executable space (open) or a full-res module (yknr).**
This is exactly the fresh-eyes question (see `grain-fresh-eyes-brief.md`).

- **⚠ E-7 is AMBIGUOUS** (re-read 2026-10-19 evening): concluded "0x1e62 not executable", but **no NO-OP test was
  done at 0x1e62** — the hang could equally be a payload bug in the additive loop. Our own lesson (E-3/E-4) says:
  NO-OP first. Before writing off 0x1e62, either verify the E-7 payload in `saemu` or flash a no-op chain.
- **E-8:** writes inside fn 0x628 (@0x12fa, earlier in the per-tile loop) do NOT reach the output; the same tile
  written at launch time does. ⇒ the effective write must happen AT LAUNCH (after the tile is (re)loaded).
  fable's "fn 0x628 = injection site, ~1590 B" falsified (and fn 0x628 is 0x628-0x6d8 = 176 B, not 1590).

## OPEN TASK — find executable space for the noise routine ("поиск места")
Requirement: code that runs at launch time (called from the 0x1e42 cave via `bl rX`, register = no range limit),
r5 live, lives in genuinely executable memory, and whose normal role is not needed for capture (or neutralised).
Candidates / leads:
1. **Reset stub clue (NEW, 2026-10-19 evening):** 0x1e60 `b 0x1e70` → 0x1e70 sets sp=r14=0x4000, `bl 0x39d8`,
   then writes 0 to 0x48208 and loops on `wfi`. **0x39d8 is OUTSIDE image-0 text (text len = 0x2900)** and it
   runs. ⇒ the executable address space is NOT just "image-0 text from 0". To check: where 0x39d8 lives (second
   image @raw 0x2c20? crt0 / shared module code?), what the real load map is (descriptor w[8]=0x188, w[9]=0x90,
   w[10]=0x15800, w[11]=0x682, w[12..15]=0x218), and from that WHY 0x1e62/0x2038 fail while 0x1e42 works. If the
   load map is known, the free executable space is known.
2. **Clean-out:** overwrite an executed but capture-irrelevant scalar routine. sonnet flagged a parameter validator
   ~fn 0x1c38; needs verification (called at launch time? safe to drop?). The routine at 0x1d90-0x1e04 is a
   signed divide (called from where?) — not a candidate unless unused.
3. **Squeeze into 30 B — CANDIDATE FOUND (2026-10-19, static + Python sim only, NOT in saemu, NOT on camera).**
   DeepSeek (v4.1-flash, 600 s) answered "11 impossible, min 14 instr = 28 B" — **its loop is broken for our 32-bit
   regs**: `lsr r3,#13` → byte delta is full-range −128..127 (chroma garbage, not ±4); with `lsr #29` it collapses
   to constant −4 (state overwritten each iter). Our prompt also under-described the ISA: `cmp.eq rd,#imm8` (op4=8)
   and `asr rd,#imm` exist. Fix = keep state in r3, delta via copy+asr; build 0x194 with mov+lsl instead of a
   literal (tail 6 B instead of 8 B, no pool/alignment) → **exactly 30 B, 0x1e42..0x1e60**:
   ```
   1e42 mov r0,#0x10 ; 1e44 lsl r0,#8          ; r0=0x1000, counts down by 2
   1e46 loop: ldrb r2,[r5,r0]                   ; tile[r0-2], even (chroma) offsets 0xffe..0
   1e48 eor r3,r0 ; 1e4a mul r3,r3              ; state r3 (entry value = seed, any value OK)
   1e4c mov r1,r3 ; 1e4e asr r1,#29             ; signed delta -4..+3
   1e50 add r2,r1 ; 1e52 strb r2,[r5,r0]
   1e54 add r0,#-2 ; 1e56 cmp.eq r0,#0 ; 1e58 bfc loop
   1e5a mov r2,#101 ; 1e5c lsl r2,#2 ; 1e5e b r2  ; tail-call 0x194, lr intact
   ```
   Sim (32-bit, 7 seeds incl. 0): uniform −4..3 (bins 206..282 of 2048), adjacent-equal ≈ 0.12 (ideal 1/8), no
   collapse. Caveats: no seed init → if r3 is the same at every hook entry, every tile gets the SAME pattern
   (tile-periodic grain); chroma wraps at 0/255 (no saturation). Next: assemble (`saasm.py`), round-trip `sadis`,
   run in `saemu`, then flash. Scripts: `<scratch>`.

## Camera / tooling / state
- **Camera currently has `628test` (E-8) on it** — Soft Focus = stock look, capture OK. Fully stock: flash stock
  `sa_sftfcs.bin` (md5 `c64ce8018c0fc7ed6c081eac9aca8606`) or revert byte 445→0x00 (`deliver_sftfcs_revert.py`).
- **Flash flow:** `diskutil unmount /dev/disk5s1; diskutil unmount /dev/disk6s1;` then from `~/nex3n-dump`:
  `env SUDO_ASKPASS=work/filmgrain/askpass.sh sudo -A env PYTHONPATH=work/pmca work/pmca/venv/bin/python3
  work/filmgrain/deliver_sftfcs.py <module.bin>`. A hang = stuck review screen / card-not-ready, NOT a brick:
  power-cycle, reconnect USB, reflash. **Always view SOOC frames yourself** from `/Volumes/Untitled/DCIM/100MSDCF/`.
- **Build:** patch via `Mod` (`sonygen/isa/mod.py`, tbase+text addr), no checksum in module; **round-trip every patched
  module through `sadis.py`** (caught a wrong `ldr [pc]` offset once). Stock source:
  `sonygen/out3n/nflasha8_unpacked_unpacked/sabin/sa_sftfcs.bin`.
- **Rules learned:** NO-OP trampoline first for any new code location; the camera (not static reachability) decides
  what reaches the output — test injection TIMING too; verify RE address math with an independent pass (fable
  out-found opus, but was also wrong twice: 0x2038 cave, fn 0x628).
- DeepSeek = `work/filmgrain/dsq_xpl.py` (small prompts; it times out on long generations).

## Superseded (kept for history)
- VLIW route: substitution works (`sa_sftfcs_spread12.bin` = fallback deliverable, colour-error specks,
  anisotropic); VLIW addition EXHAUSTED (engine packed, shared regs) — do not retry. See `grain-sftfcs-confirmed.md`.
- Old step-3 design (trampoline into dead code 0x2038) — falsified by E-3.

Cross-refs: `grain-sftfcs-confirmed.md`, `engine-command-table.md`, `sa-dsp-isa.md`, `grain-codecave.md`
(older yknr code-cave analysis: chaining via `b`, ±0x1000 range), `06-experiment-log.md`.
