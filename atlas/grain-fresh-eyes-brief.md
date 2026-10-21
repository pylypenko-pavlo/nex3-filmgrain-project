# GRAIN — fresh-eyes brief (2026-10-19, after E-1..E-17)

Self-contained summary for an independent review. Details: `grain-RESTART.md` (experiment log),
`engine-command-table.md` (static RE of sa_sftfcs, esp. "STEP-2 CORRECTION" = authoritative), `sa-dsp-isa.md`.

## Goal
Owner's own Sony NEX-3N. Real **film grain in the straight-out-of-camera JPEG**, ideally "select Soft Focus picture
effect → get grain". Fine grain (≈2-5 px at 4912×3264), luma-dominant like film, not blotches, no artifacts.

## Platform / tooling (all working)
- Picture effects run on the BIONZ **SA-DSP**: a 16-bit-instruction scalar core (SH-like, **32-bit regs**, r0-r15,
  fr flag, `bl rX`/`b rX`, `run_engine`=op 0009) that configures and launches an undocumented **VLIW engine**.
  Effect = DSP module file `sa_sftfcs.bin` (Soft Focus, 43652 B, text 0x2900, image-0 desc @0x100, tbase 0x320).
- We can rebuild + flash the module in ~2 min (`deliver_sftfcs.py`, readback-md5 verified), no checksum. Disassembler
  `sadis.py`, scalar emulator `saemu.py` (no VLIW/DMA), patch helper `mod.py`. Camera hang on a bad module = stuck
  review screen, recoverable by power-cycle + reflash. Stock md5 c64ce8018c0fc7ed6c081eac9aca8606.
- Earlier VLIW-level route (edit engine syllables): substitution works (`spread12` = colour-error specks), VLIW
  addition exhausted (packed, shared regs). Superseded.

## The hook (proven)
- Pass1 engine launch @0x1410: `ldr r2,[pc]` (literal @0x156c = 0x194) ; `bl r2` → wrapper 0x194 (saves r8-r14,lr;
  `mov r0,r4; run_engine`). We patch the literal to 0x1e42 → our cave runs right before each pass1 launch, then
  tail-calls 0x194 (`mov r2,#101; lsl r2,#2; b r2`).
- **Cave = 30 B at 0x1e42..0x1e5f** (zero padding between LUT 0x1e10-0x1e41 and a live stub @0x1e60). It is the ONLY
  proven-executable free space: E-3 NO-OP at 0x2038 (dead code tail) HUNG; E-4 NO-OP at 0x1e42 OK; E-7 chain to
  0x1e62 HUNG (ambiguous, no no-op test). A reset stub @0x1e70 does `bl 0x39d8` (outside image-0 text) → the real
  load map / executable window is not understood.
- At the hook: **r5 = k0 input tile base − 2** (r5 = [struct+164] − 2, struct = 0x13000 + (pp^1)*0x1b0, pp toggled per
  launch @0x13a8-0x13b4). r0-r3 free; r4 = cmd table (0x1c); r8-r14 live.
- Tile = **64 px × 32 rows, UYVY row-major (128 B/row), 0x1000 B, 1:1 image scale** (measured E-14).
  fn 0x4c8 sets struct_k[+164] = LUT_A[k]<<11 → k0/k1 tiles contiguous: pp1 0x8000/0x9000, pp0 0x5000/0x6000.
- Per launch (static, loop 0x1268-0x14b4): fn 0x4c8 + fn 0x628 for k0,k1 (0x12ac-0x1306) → OUT ring 0x13800 + kick
  0x48230 (0x1310-0x1328) → IN ring 0x13700 (0x1330-0x1358) → IN-DMA kick `2→[0x48218]` @0x13aa → engine config
  ports 0x40000.. from struct (0x13b2-0x140e) → **our hook** → `bl 0x194` @0x1412 → return 0x1414: `0x10000→[0x48208]`,
  `wfi`. Nothing waits for the IN DMA before the launch. Pass2 launch @0x15ac (literal 0x16b0) after the loop.
- Static claim (fable, verified earlier): engine OUTPUT per tile = SRC1=[struct+0xC0] = a **4×2 block** (+2×2 SRC2/3),
  exported by fn 0xd28 after the launch ⇒ sftfcs computes only a LOW-RES GLOW layer; sharp+glow blend is elsewhere (HW).

## Camera experiments (all Soft Focus, SOOC JPEG measured by script; frames in work/filmgrain/results/)
| # | payload @0x1e42 (pass1 hook unless noted) | result |
|---|---|---|
| E-1/2 | const writes via cave @0x2038 | HUNG |
| E-3 | NO-OP @0x2038 | HUNG → 0x2038 not executable |
| E-4 | NO-OP @0x1e42 | OK |
| E-5 | U/V := 0x40, 0x1000 B | green, **vertical stripes** period 128 px |
| E-7 | additive loop chained to 0x1e62 | HUNG (ambiguous) |
| E-8 | const U/V inside fn 0x628 (earlier in loop) | stock look → fn 0x628 writes are overwritten later |
| E-9 | additive chroma noise ±4 (30 B: r3 state, eor pos, mul r3,r3, asr #29) | no visible grain (σ 2.3 → ≥15× attenuated) |
| E-10 | same, ±64 | no blotches; weak signature (chroma hp-var ~2×, stripe-correlated) |
| E-11 | same loop, store const 0x40 | = E-5 exactly → loop runs, writes land |
| E-12 | Y := 0x10, hooks pass1+pass2 | **luma lands** (wall Y 95 vs 189), chroma unchanged; stripes same as E-11 |
| E-13 | Y := 0x10, pass2 hook only | no visible effect / no structure |
| E-14 | ruler Y = byte>>4 (k0) | ladder: vertical period 32.1 px, band ~58-64 px of every 128; sawtooth → triangle (rise ~17, fall ~13 rows) ⇒ ~14-16 px low-pass |
| E-15 | ruler over 0x2000 (k0+k1), descending | stripes remain; between-columns ripple energy 5-8 vs 1-2 (E-14), bands ~60 |
| E-16 | Y = (tile base>>7): 0x8000→0, 0x5000→0xa0 | **checkerboard of 64×32 tiles**: in a band, 0x8000/0x5000 alternate every 32 rows; adjacent bands staggered 32 rows |
| E-17 | Y := 0x10 over k0+k1, ASCENDING (k1 last) | stripes unchanged (depth ~40 = E-12) |

Quantities: DC fill weight in output ≈ 0.62 (band) / 0.36 (between) for Y; chroma 0.48 / 0.28; stripe/between ratio
0.58 in both. Fine noise (±4, ±64 per pixel) essentially vanishes. Capture timing is fine up to ~29k instr per hook.

## Current interpretation (mine — challenge it)
1. The hooked tile feeds the Soft Focus **blur/glow branch** (4×2 output per 64×32 tile ⇒ 16× down, then upsampled),
   so anything injected here is low-passed ~16 px ⇒ **fine grain is impossible inside sftfcs**; only glow mottling.
2. Stripes: only every other 64-px column carries our k0 data. Hypothesis "between columns = k1 tile, lost to an IN-DMA
   race" is NOT supported (E-15 weak, E-17 no change). Origin of the between columns is unexplained; the between
   columns still get ~58 % of a DC change (upsampling/interpolation from neighbours?).

## Open questions for the reviewer
- Q1: Is interpretation 1 right? Any way to get FULL-RES fine grain from within sftfcs (e.g. the engine's output
  path, blend weights, a full-res operand we missed), or is sftfcs a dead end for fine grain?
- Q2: What actually produces the between-columns (stripes), given E-15/E-16/E-17? What single test settles it?
- Q3: Step back: is "inject noise into a DSP effect module" the right strategy at all for film grain on this camera?
  What would a fresh approach be (other module carrying full-res luma e.g. yknr = luma NR whose chan-3 output reaches
  stills at high ISO; NR/sharpening/tone parameter tables; other picture effects; anything simpler)?
- Q4: What are we wasting time on? Rank the next 3 experiments by information gained per camera flash.

## REVIEW VERDICTS (2026-10-19) — DeepSeek + fable, both independent
Full text: `grain-review-deepseek-2026-10-19.txt`, `grain-review-fable-2026-10-19.txt`.
**Consensus: sftfcs is a dead end for grain** (no full-res output buffer; nothing < ~40 px survives — fable verified
in disasm; DeepSeek + my 16× averaging sim agree). STOP the 30 B cave / stripe / coarse work here.
**THE missed result (fable, verified in atlas START-HERE 133-135):** E-0080 yknr NR-bypass (Backup `0x3004a`
+0xD2..+0xDC → 0) already produced fine luma film-grain (HP-std 3.2-3.4, "reads as film"), shelved as ISO-dependent
but **only shot at ISO 16000 = ABOVE the ~200-6400 window**, so the in-window deliverable is UNMEASURED. All Backup,
reversible, no code. Atlas calls it "⭐ THE recommended shippable move, not yet shot."
**Next (both reviewers):** (1) measure yknr window-kill at ISO 1600/3200/6400 vs stock [1-2 flashes, Backup not module];
(2) static-trace `sa_jpeg_enc_1unit` for a full-res pixel path [0 flashes]; (3) sftfcs stripe test E-18 only if coarse
SF mottle is still wanted [1 flash].
**fable corrections to the log (verified):** E-8 fn 0x628 = border synthesizer (mode-gated, not "overwritten later");
0x2038-0x20d0 = a real coherent function (not dead code); I-mem/load window likely ends at 0x2000 (8 KB) → explains
E-3; stripe transition ~40 px (not 12-20); launch @0x15ac = per-strip DRAIN (not "pass2") → E-13 null expected;
E-17 premise inverted — k1 (between columns) is consumed EARLY via the IN-DMA kick @0x13aa, write-later = worse.

## FULL-RES HOST TRACE (2026-10-19, fable, static, verified) — `grain-jpegenc-yknr-trace-2026-10-19.txt`
- **yknr injection = DEAD (two blockers).** B1: no sftfcs-shape SRAM input tile — scalar makes 0 pixel accesses to
  the tile buffers (C-PIPE-022); pixels live in DRAM aperture 0xf81400. B2 (the owner's ISO concern, VERIFIED):
  a yknr hook does NOT run at base ISO — E-0091 camera-proof (zeroing yknr stores → grain at ISO3200 but CLEAN frame
  at ISO200) + predicate 0xd5760 gates on the ~ISO200-6400 window. Widening the window to force a base-ISO pixel pass
  is untested AND would run a denoiser at base ISO (smooths detail) AND still hits B1. Drop yknr.
- **sa_jpeg_enc = pixels NOT in scalar SRAM.** Luma/chroma stream DRAM→HW engine via DMA descriptors the scalar only
  builds (luma base 0x60000000+off, chroma 0x68000000, written as 8-B entries @SRAM 0x93c0; 24-B desc @0x1f18). No
  full-res luma plane to strb into. The 0x3200-0x3db0 "byte stores" are misdecoded inline VLIW microcode, not pixel loops.
- **The one remaining SA-DSP lever (weak, OPINION):** at the jpeg descriptor-build site (~0x7ec/0x816) the luma DRAM
  addr 0x60000000+off is LIVE in r1 before the DMA GO. A DSP-side DRAM pre-write (strb const into those DRAM bytes
  before the kick) MIGHT reach the encoder. Same class as the camera-refuted ARM canvas write (C-MEM-021/C-PIPE-001)
  but DSP-side at a different time. **Decisive 1-flash test at BASE ISO:** mark appears → jpeg_enc DSP-DRAM pre-write
  is the UNIVERSAL every-pixel/every-ISO hook (the grail). Clean → SA-DSP injection fully closed → grain must move to
  the Linux decode/re-encode route (C-LNX-011).
- **Still pending (parallel):** DeepSeek asked whether the sftfcs engine 16× downsample is a CONFIGURABLE geometry
  field (ports 0x40008..0x40020) that could be set to full-res — which would revive the already-proven sftfcs tile hook.

## sftfcs 120B-before-hook (2026-10-19, DeepSeek via agent) — `grain-sftfcs-120b-deepseek-2026-10-19.txt`
VERDICT: the 16× downsample is **NOT** a scalar-configurable field. The 9 words written to engine ports
0x40000..0x40020 (from struct+0xb4..+0xd4, each −1) are FIXED engine-local SRAM addresses/bounds derived only from the
stage index (0/1) + constants — a buffer-cascade/pyramid, e.g. T=0x17 → offsets 0x000,0x200,0x300,0x3FF,0x41F,0x42F,
0x43F,0x447,0x44B above T<<11. r5 input tile = engine-local SRAM (0x4FFE/5FFE/7FFE/8FFE), not a DRAM full-res pointer.
No blend/gain/full-res-operand lever here. The downsample ratio is baked into the VLIW microprogram selected by
r4=0x1c (not in scalar text). ⇒ **sftfcs cannot be made full-res without editing the opaque VLIW engine (exhausted).
sftfcs is fully closed for fine grain.**

## BOTTOM LINE (all SA-DSP scalar injection paths assessed)
1. sftfcs tile hook — works, but engine downsamples 16× (VLIW-baked, not configurable) → ≥~40px glow only. DEAD for fine grain.
2. yknr injection — DEAD (no SRAM tile + ISO-gated, clean at base ISO E-0091).
3. sa_jpeg_enc — pixels DMA-streamed DRAM→HW past scalar; only residual = DSP-side DRAM pre-write at descriptor-build
   (luma 0x60000000+off live in r1 @~0x7ec/0x816), UNTESTED, weak. **This is the last SA-DSP card.**
⇒ Decisive endgame: 1-flash jpeg_enc DSP-DRAM-prewrite CONSTANT test at base ISO. Mark appears → universal every-pixel
   every-ISO hook (grail). Clean → SA-DSP injection fully closed → grain moves to Linux decode/re-encode (C-LNX-011).

## jpeg_enc DRAM-prewrite = NO-GO (2026-10-19, fable, emulated) — `grain-jpegenc-prewrite-NOGO-2026-10-19.txt`
VERIFIED: emulated the entire jpeg_enc scalar (10808 stores) — EVERY store is SRAM/stack/MMIO, ZERO to DRAM. The
scalar core cannot address the DRAM pixel pool; 0x60000000 is only a value written into a DMA descriptor, never a
store base. No scalar-visible DRAM aperture (no yknr-0xf81400 analog). ⇒ the constant-write test cannot be built.
**ALL SA-DSP scalar injection is now closed (sftfcs glow-only, yknr no-tile+ISO-gate, jpeg_enc no-DRAM-reach).**
Delivery params captured for the future: sa_jpeg_enc_1unit.bin 17412 B, file-id 16, Backup 0x00bd0002 byte 133
(0x00→0x06 redirect), checksum sum32 of body[:-4]. (Encoder is capture-critical — a bad copy is likely fatal.)

### ⚠ CORRECTION to fable's recommendation: the Linux re-encode route is NOT a safe pivot
fable recommended C-LNX-011 (env.txt + LD_PRELOAD decode/grain/re-encode). The atlas marks this **FROZEN / Tier-C
forbidden** (START-HERE 53/69; Q-1; C-LNX-012): a failed LD_PRELOAD kills init/bootin/im.elf/sen.elf = **brick,
jumper-only recovery**; only safe dmode = "3\n". Do NOT pursue without explicit owner acceptance of brick risk.

### REMAINING OPTIONS for universal (all-ISO) fine grain — all compromised
- yknr NR-bypass E-0080: works, safe, reversible — but HIGH-ISO only (owner rejected ISO-locked).
- DSP-programmed DMA-OUT (SRAM noise tile → DRAM luma, racing the encode read): uncertain, multi-step, same class as
  the camera-refuted ARM canvas write (C-MEM-021). No quick proof.
- Linux re-encode: full-res/every-ISO but brick-level/forbidden.
⇒ No safe, verified path to universal fine grain remains. Honest verdict: either accept ISO-dependent grain (E-0080)
  or pause the universal goal pending a new idea. The day's work exhaustively closed the SA-DSP injection strategy.

## LINUX ROUTE — SAFETY ASSESSMENT (2026-10-19, fable, static) — `grain-linux-route-safety-2026-10-19.txt`
Owner chose the Linux route accepting brick risk. Static trace CORRECTS the risk upward:
- **RECOVERABILITY = POTENTIALLY PERMANENT (VERIFIED).** env.txt LD_PRELOAD is global (putenv before bootin, init
  @0x90ad/0x918a/0x920a) → a failed .so kills init/bootin/sh/im.elf/sen.elf (sonyld _rtld_die @0x56a4). No software
  recovery: senser/updater/menu-reset all need the appFw that just died. Loader2 `\updater\mode` net helps ONLY if
  pre-placed AND is UNPROVEN (Q-39); the jumper is code-only, never tested, location undocumented. Bad env.txt = a
  dormant brick that re-fires every cold boot. The "28 flashes 0 bricks" precedent does NOT apply (those kept USB-updater reachable).
- **Decode/encode primitive REAL (VERIFIED):** libmpr DecodeStillOnMemory @0x5d52bd / EncodeStillOnMemory @0x5d53f9,
  same-address-space VA API. But the trigger needs interposing Fsys_Close/close = the dangerous global interposition.
  Codec backend unresolved (Q-11, /dev/ldec 252:200 maybe HW).
- **STAGED PLAN (recovery NOT established → hard stop before any preload):**
  Stage 0 offline (0 risk): prove the .so vs sonyld loader; disasm DecodeStillOnMemory (settle Q-11).
  Stage 1 camera harmless: dmode="3\n" + env.txt benign TESTVAR, NO preload (C-SAFE-015 safe); confirm boots + var visible; revert = rm files.
  Stage 2 camera GATE (Q-39): pre-place `\updater\mode` (del comp, create mode), cold boot. Enters updater → recovery net EXISTS. Boots normal → STOP, no net, no preload ever w/o documented jumper. Revert from updater shell.
  Stage 3 first preload (only if Stage 2 passed): raw-syscall no-op .so logging a line, with the net pre-placed.
  Stage 4+ grain shim.
  **Stage 2 is make-or-break. Hold at Stage 1 until it passes.**

## LINUX ROUTE — STAGE 0 DONE (2026-10-19, fable, offline) — `grain-linux-stage0-2026-10-19.txt`
- **sonyld load contract (VERIFIED from die-strings @0x251cc):** checks magic, EV_CURRENT, ET_DYN, EM_ARM, PT_DYNAMIC,
  EXACTLY 2 PT_LOAD, mmap ok; EABI/e_flags NOT checked. Fatal path _rtld_preload@0x2554 → -1 → _rtld_die@0x56a4.
- **Candidate built: `grain_probe.so`** (488 B, md5 8cae1085…, in <scratch>/lnx/) — exports `close()` raw-syscall passthrough
  + ctor logging one line; zero DT_NEEDED/relocs, PC-relative; passes all 12 contract checks. Load-safety STRUCTURAL
  only (more minimal than any known-accepted object; no sonyld emulator run yet) — not claimed beyond structural.
- **Fail-safe lever (VERIFIED):** sonyld exports __dlsym → shim keeps DT_NEEDED empty, resolves Fsys_Close/Decode/Encode
  at runtime → a missing dep cannot _rtld_die at load.
- **Codec (VERIFIED signatures):** DecodeStillOnMemory@0x5d52bc / EncodeStillOnMemory@0x5d53f8 are in-process VA/size
  APIs (no IPC); trigger = interpose Fsys_Close on *.JPG → decode→grain on Y→encode→rewrite→real Fsys_Close via __dlsym.
  GAPS (don't block Stage 0): decoded-plane format (planar Y?) needs 1 more disasm hop; backend HW/SW (Q-11) open.
- **NEXT (offline de-risk, 0 camera):** qemu-arm run of sonyld loading grain_probe.so (prove load-safety before any
  camera preload) + close the Y-plane format. THEN Stage 1 (harmless env.txt test) on owner approval. Stage-2 Q-39
  gate unchanged: no preload until the recovery net is proven.

## LINUX ROUTE — STAGE 0.5 (2026-10-19, fable, offline) — appended to stage0 report
- **qemu load-proof NOT RUNNABLE here** (no qemu-arm/Docker; arm64 host) — agent did NOT fake it. Instead closed the
  gap statically: `_rtld_digest_dynamic` @0x1a60-0x22c4 is a dispatch over PRESENT tags only; absent tags stay 0 and
  every use is 0-guarded → no omitted tag is dereferenced. SysV DT_HASH case fully implemented; libmpr.so (SysV-hash)
  is loaded by this same sonyld ⇒ SysV-hash objects provably load. grain_probe.so trips nothing. [VERIFIED]
- **Residual (OPINION):** grain_probe.so has zero relocations + no DT_PLTGOT (unique). Loops are count/NULL-guarded but
  the combo is empirically unproven. **FIX before Stage 3: rebuild to mirror libsonyefence.so — add DT_INIT_ARRAY(1) +
  one R_ARM_RELATIVE** (relocation-bearing like every proven-accepted preload). Final proof only on-camera or via qemu.
- **Y-plane RESOLVED:** decode → single contiguous YUV buffer; full still = 4:2:2 (thumbnail is 420). Convention
  (C-MEM-005, hw): packed YUYV, luma = even bytes, stride 2×w. Grain = dst[2k]+=signed noise, clamp, odd untouched.
  Runtime-robust: Size==2wh→4:2:2 (luma even); ==1.5wh→4:2:0 (luma first wh). Format does NOT block the write. [VERIFIED/OPINION]
- **Offline certainty is now maxed.** Empirical load-safety can only come from the on-camera Stage 3 probe (gated by
  Stage 2 / Q-39) or a qemu setup we lack. NEXT camera step = Stage 1 (harmless env.txt test, no preload), on approval.

## LINUX ROUTE — STAGE 0.5 QEMU EMPIRICAL = PASS (2026-10-19, fable, offline in lima VM)
Built an ARMv5TE/EABI5 armel rig (lima Debian-12 VM + qemu-arm-static + arm-linux-gnueabi-gcc) and ran the camera's
OWN sonyld (`.../nflasha3/initrd/lib/sonyld.so`, md5 df94859e) under qemu against our preload objects:
- **CONTROL** junk.so → sonyld prints the EXACT die-string from static analysis (`unrecognized file format2 [d1 != 1]`),
  exit 1 ⇒ the rig faithfully drives _rtld_map_object/_rtld_die; a reject is loud. [VERIFIED]
- **grain_probe_fs.so** (gold: zero DT_NEEDED + DT_INIT_ARRAY + 1× R_ARM_RELATIVE, matches proven libsonyefence shape)
  → exit 0, no die-string, init_array ctor LOG LINE written ⇒ sonyld maps, relocates, parses hash/symtab, runs the ctor. [VERIFIED]
- **grain_probe.so** (488 B hand-built, zero-reloc) → exit 0, ctor ran too. [VERIFIED]
⇒ **sonyld ACCEPTS the preload shape. The Stage-0 residual (zero-reloc only structural) is empirically CLOSED. The
single biggest load-time brick cause is removed.** Use `grain_probe_fs.so` shape for the Stage-3 camera probe.
Caveats (stated): qemu emulates CPU+syscall ABI not the exact camera rootfs/TLS (but ELF-acceptance is format parsing,
and the faithful control backs it); a PLT-interposition micro-test was not completed (not needed — the shim resolves
its hook lazily via sonyld's exported __dlsym). **Stage-2 gate (Q-39) still must pass before ANY camera step.**

## LINUX ROUTE — STAGE 1 DONE = PASS (2026-10-19, on-camera, owner-driven)
Executed the env.txt mechanism test on the real camera (updater busybox shell; senser for the sftfcs revert):
- Pre: reverted sftfcs to stock (Backup 445→0x00). STEP 0 recon (read-only): /setting rw (nflasha2), /setting/mode/
  exists & EMPTY, no dmode, no env.txt ⇒ stock. (busybox has no `od`/`printf` — used `echo`/`wc`/`cat`/`ls`.)
- STEP 1: `echo 3 > /setting/mode/dmode` (2 B, "3\n") + `echo TESTVAR=grainprobe > /setting/env.txt` (19 B), verified.
  (First attempt made them EMPTY via missing `printf`; fixed with `echo` BEFORE any cold boot — empty dmode is still
  boot-safe: C-BOOT-029 only stops on a literal '0', C-BOOT-031 defaults to 3 on no digit.)
- STEP 2: WBI-zero `dd if=/dev/zero of=/dev/nflasha5 bs=512 count=1` (forces init to run; no Backup write).
- STEP 3: **owner cold-booted → camera boots normally and SHOOTS** ⇒ dmode="3\n" + env.txt parse + WBI-zero are
  boot-safe. (Positive TESTVAR read not achievable with current tooling — updater boot ignores env.txt, senser reads
  the service processor not the appFw env; env-parse is proven transitively at Stage 3. Not a brick concern.)
- STEP 4: deleted both files (verified gone) + WBI-zero ⇒ **clean revert to stock proven.**
⇒ **The env.txt delivery + revert loop is SAFE and WORKS on the live camera.** Load-safety (sonyld accepts the .so,
  Stage 0.5) + boot-safety (Stage 1) both established. The remaining gate before ANY preload is **Stage 2 (Q-39):
  does a pre-placed `\updater\mode` force a firmware-independent updater boot = a recovery net.** Make-or-break.

## RECIPE LAB (recipelab.io / voxivoid/recipe-lab-sony-pmca) — assessed 2026-10-19
What it is: open-source film-emulation "recipes" distributed as **PlayMemories Camera Apps**, built on the SAME base
we use (ma1co OpenMemories + Sony-PMCA-RE). **Verdict for grain: not a missed path, no help.**
- **Settings-only, NO software processing (VERIFIED from its docs):** "only camera settings you could set by hand" —
  Creative Style + saturation/contrast/sharpness sliders, WB + fine-tune, EV, DRO, Picture Effect. It does NOT decode/
  process/re-encode the image. Any "grain" = the camera's OWN built-in Picture Effect = the DSP we PROVED can't do
  fine grain (sftfcs 16× glow). So even on a supported body it cannot deliver real film grain.
- **NEX-3N not listed** (confirmed: NEX-5R/5T/6 are, 3N is absent). NEX-3N is a 2013 entry model whose PMCA app
  support is undocumented/absent — which is exactly WHY this project never targeted it and why we are at the DSP/
  Backup/Linux level, not the app layer.
- **Useful extract:** (1) its per-film → Creative-Style/slider/WB recipe table is a cross-check reference for our own
  film-stock parameter mappings in `colour-slots-lineup.md` (the colour/tone half the atlas already solves via Backup).
  (2) It INDEPENDENTLY CONFIRMS that fine grain is NOT available through the native settings layer on these cameras —
  validating that the DSP/firmware route was necessary, not a detour. Nothing here changes the grain plan.

## SESSION SUMMARY (2026-10-19) — where we are
- **SA-DSP grain injection fully closed:** sftfcs = 16× glow only (VLIW-baked, not configurable); yknr = no SRAM tile +
  ISO-gated (clean at base ISO); jpeg_enc = pixels DMA-streamed from DRAM, scalar can't reach them (emulated, 0 DRAM
  stores). All verified.
- **Only full-res/all-ISO path = the Linux decode/re-encode route** (libmpr DecodeStillOnMemory/EncodeStillOnMemory,
  trigger = interpose Fsys_Close). Brick risk is **potentially PERMANENT** (global LD_PRELOAD, no proven software
  recovery, jumper untested). Pursued via a staged, gated plan.
- **Done today:** Stage 0 (sonyld load contract + grain_probe.so) ✓; Stage 0.5 (qemu: camera sonyld EMPIRICALLY
  ACCEPTS our preload — gold grain_probe_fs.so + minimal — biggest load-time brick cause removed) ✓; **Stage 1 PASS
  on-camera** (dmode="3\n"+env.txt → boots normally & shoots; clean revert proven) ✓. Camera reverted to STOCK.
- **NEXT = Stage 2 (Q-39 gate), MAKE-OR-BREAK:** does a pre-placed `\updater\mode` (delete `comp`, create `mode`)
  force a firmware-independent updater boot = a recovery net. Enters updater → net exists, may proceed to Stage 3
  (first preload). Boots normal → STOP, no preload without a documented jumper. NO preload is loaded until Stage 2 passes.
- **Infra:** lima VM `armgrain` (Debian-12 aarch64) + qemu-arm-static + arm-linux-gnueabi; `grain_probe_fs.so` built
  (init_array + R_ARM_RELATIVE, zero DT_NEEDED) = the Stage-3 preload shape. VM stopped at end of session; restart to continue.

## LINUX ROUTE — STAGE 2 / Q-39 = PASS (2026-10-20, on-camera) ★ RECOVERY NET PROVEN
The make-or-break recovery-net gate, executed on the real camera:
- STEP 0 recon (read-only): /setting/updater = comp (0B) + dat4 (2B), no mode*. Stock.
- 2a (comp intact, touch mode): cold boot → NORMAL both times, mode consumed → inconclusive (can't tell Loader2-entry
  from libObj cleanup externally; no observable updater with comp present).
- **Recovery linchpin resolved (pmca code + ma1co precedent):** a camera ALREADY in the Loader2 updater presents as
  SonyMscUpdaterDevice; `updaterShellCommand(model='NEX-3N')` attaches DIRECTLY via the `else: Writing firmware` branch
  (skips switchMode — the earlier "Cannot determine camera model" was only the missing-model step). ma1co: updatershell
  IS the documented stuck-camera recovery.
- **2b (comp REMOVED, comp.sav kept, mode present) → cold boot → camera entered the PERSISTENT Loader2 updater**
  (black screen; USB enumerated as "Sony USB Device" / "camera in updater mode", NOT mass-storage). = net works.
- **RECOVERED:** `updaterShellCommand(model='NEX-3N')` attached ("camera in updater mode" → Writing firmware → shell),
  restored comp + deleted mode; cold boot → **camera back to NORMAL, shoots.** ⇒ the persistent `\updater\mode` net
  (comp absent) IS reachable and recoverable via pmca. **Q-39 CLOSED: the recovery net exists and is proven.**
⇒ All three safety pillars established ON THE CAMERA: load-safety (0.5 qemu), boot-safety (Stage 1), recovery-net
  (Stage 2). **Stage 3 (first preload) is now protected** — pre-place the net {rm comp (comp.sav kept), touch mode}
  BEFORE loading the preload; if the preload bricks userland, every boot lands in the pmca-recoverable updater.
  Scripts: stage2b_arm.py / stage2b_recover.py. Leftover: harmless 0-byte /setting/updater/comp.sav.

### Stage 3 plan (next, FIRST brick-capable step — prep required)
1. Pre-place the recovery net: `cp comp comp.sav; rm comp; touch mode` (camera now boots to updater — recoverable).
2. Deploy `grain_probe_fs.so` to /setting (senser writeFile) + `env.txt` = `LD_PRELOAD=/setting/grain_probe_fs.so` (the
   gold reloc-bearing object, qemu-proven to load). WBI-zero. Cold boot.
3. Boots normally + /tmp (or /setting) ctor log line written → preload LOADS on the real camera (Stage 3 PASS). Then
   remove comp-net (restore comp) and iterate toward the real Fsys_Close grain shim (Stage 4).
   Bricks → recover via updatershell (restore comp, delete env.txt + preload). Net makes this recoverable.

## ⚠ CORRECTION (2026-10-20): the `\updater\mode` net does NOT protect the Stage-3 preload test
Realized + empirically confirmed (2b): Loader2 checks `\updater\mode` FIRST, before init. So:
- mode present → Loader2 diverts to the updater → init/env.txt/preload NEVER run (2b: camera went to updater, black
  screen, no normal boot). 
- mode absent → normal boot → preload loads → but NO net active.
These are mutually exclusive at boot. And `\updater\mode` CANNOT be placed AFTER a brick (userland dead = no /setting
write). ⇒ Stage 2's net proves the recovery MECHANISM works, but it canNOT insure the Stage-3 preload test itself.
What actually de-risks Stage 3: the qemu load-proof (sonyld accepts grain_probe_fs.so) + fail-safe ctor. Residual:
if the preload unexpectedly fails to load on the real camera, init's children die → brick recoverable ONLY by a
userland-independent path (jumper/USB-ROM/official-updater), which is UNVERIFIED. Owner chose: establish that
brick-recovery path BEFORE any Stage-3 preload (task in progress). Web: bricked Sony NEX are often recovered by the
official Sony firmware updater over USB (PC) — implies a bootloader USB-ROM mode may exist; being verified for a
userland-brick. No public NEX-3N hardware jumper found.

## ⛔ STAGE 3 BLOCKER — preload-brick is NOT software-recoverable (2026-10-20, fable, VERIFIED) — grain-linux-brick-recovery-2026-10-20.txt
- No auto USB-download mode on power-on (Loader1 bootrom has no usb/download/recovery strings; Loader2 USB transport
  only inside updater/adjust, behind jumper/trigger). [VERIFIED]
- No boot-fail/watchdog escalation to recovery (boot_init_mode tree has no "N failures → updater"; preload-brick loops;
  init pid1 survives). [VERIFIED]
- Jumper GPIO mapped (`[0xa0010024]==4 && ([0xf3060000]>>8&0xf)==2`) but physical pads UNDOCUMENTED (needs opening the
  camera + PCB probing) AND never tested to recover a userland-dead unit. [VERIFIED/OPINION]
- Official Sony updater needs a live firmware to set the update flag → useless on a userland-brick. [VERIFIED]
⇒ **A preload-brick = PERMANENT (no software/USB recovery). The only door is the undocumented, unproven hardware
  jumper.** Stage 3 (normal-boot env.txt LD_PRELOAD) therefore risks permanent camera loss; qemu PASS lowers but can't
  eliminate on-camera load-failure probability. **Options: (A) hardware-RE + validate the jumper first (invasive,
  uncertain); (B) owner accepts possible permanent loss and runs on the qemu-proof; (C) abandon the Linux route.**
  Recommendation: do NOT gamble the camera for a nice-to-have; gate on (A) or an explicit (B).

## QEMU VALIDATED + ISOLATED ON-CAMERA SILICON TEST FEASIBLE (2026-10-20, fable) — grain-linux-qemu-validation-silicon-test-2026-10-20.txt
- **qemu faithful [VERIFIED]:** under qemu + the real normal sonyld df94859e, the camera's OWN provably-loaded preloads
  load clean (libsonyefence.so, LeakTracer.so → exit 0); grain_probe_fs.so → exit 0 + ctor; malformed objects rejected
  with the EXACT static die-strings (ET_REL → "unsupported file type"). The qemu load-proof is trustworthy.
- **Isolated silicon test FEASIBLE, ZERO brick risk [VERIFIED]:** the updater busybox is dynamic; mount normal sonyld
  (df94859e) on /setting, run a dynamic dyntest (interp→that sonyld) with LD_PRELOAD=grain_probe_fs.so IN THE UPDATER
  SHELL. A load failure kills only that child process, never the boot path. Proves the exact brick cause (sonyld
  load/relocate/ctor of OUR object) on real silicon. Sequence: mount /dev/nflasha2 /setting; cp sonyld+dyntest+so to
  /ramdsk; LD_PRELOAD=/ramdsk/grain_probe_fs.so /ramdsk/dyntest; read ctor log. EXIT=0+no die-string → real sonyld
  accepts our .so on silicon.
- **Plan:** run the isolated silicon test FIRST (zero risk). PASS → Stage-3 load-failure risk nearly eliminated →
  proceed to the boot-path preload. FAIL → do not proceed. Honesty: the test LOWERS the load-failure probability; it
  does NOT create a recovery net — a Stage-3 load failure is still unrecoverable (no jumper). But residual becomes small.

## ISOLATED SILICON LOAD-TEST = PASS ON THE REAL CAMERA (2026-10-20) ★ Stage-3 load-brick risk nearly eliminated
Deployed grain_probe_fs.so (md5 7d528da4, max-safe: ctor logs to /setting, exports only a dummy symbol — no
interposition), dyntest (interp=/ramdsk/sonyld.so), and the normal p3 sonyld sonyld_norm.so (df94859e) to /setting via
senser (readback MATCH). Then in the UPDATER BUSYBOX SHELL (isolated from boot, zero brick risk):
- `LD_PRELOAD=/ramdsk/grain_probe_fs.so /ramdsk/dyntest` → **DYNTEST_EXIT=0** + ctor log "sonyld loaded the preload on
  silicon" ⇒ the camera's REAL normal sonyld (the exact loader the Stage-3 boot-path preload uses) LOADS + relocates +
  runs the ctor of OUR object, on silicon.
- control (non-ELF) → "unrecognized file format" EXIT=1 (rejects are loud ⇒ the test is live).
- bonus: loads under the updater sonyld too (BUSYBOX_PRELOAD_OK). All isolated; boot path untouched.
⇒ **The Stage-3 brick cause (a sonyld LOAD FAILURE, C-LNX-012) is directly tested on the real hardware and PASSES.**
  map_object is per-object/host-independent, so a load that succeeds here succeeds identically in im.elf at boot. The
  qemu proof is now confirmed on silicon. Residual: still NO recovery net (a failure remains jumper-only), but the
  load-failure probability for grain_probe_fs.so is now very small. grain_probe_fs.so is already on /setting for Stage 3.

## LINUX ROUTE — STAGE 3 = PASS ON THE REAL CAMERA (2026-10-20) ★★ boot-path preload WORKS
Set dmode="3\n" + env.txt="LD_PRELOAD=/setting/grain_probe_fs.so" + WBI-zero; owner cold-booted.
- **Camera booted NORMALLY and shot a frame.** (A load failure would have killed init's children = brick/no-boot.)
- `/setting/grain_probe_fs.log` = **6 ctor lines** ⇒ the global LD_PRELOAD loaded grain_probe_fs.so into ~6 firmware
  boot processes (bootin/im.elf/sen.elf/…), each ran the init_array ctor, and the camera stayed fully functional.
⇒ **A custom LD_PRELOAD shim loads into the camera's firmware on the boot path with no brick.** End-to-end validated:
  Stage 0/0.5 (qemu) → Stage 1 (env.txt boots) → Stage 2 (recovery-net mechanism) → silicon test (real sonyld loads
  our .so isolated) → **Stage 3 (boot-path preload loads, camera boots+shoots)**. Foundation for the real grain shim.
- Camera currently runs the no-op preload (harmless: ctor logs, exports a dummy symbol, no interposition). Leftover
  inert files on /setting: grain_probe_fs.so, dyntest, sonyld_norm.so, comp.sav.
### Stage 4 (next) — the real grain shim
Build a preload that interposes `Fsys_Close` (libInfraFsys) on a DCF `*.JPG`: `DecodeStillOnMemory` → add signed
noise to luma (even bytes, 4:2:2, runtime-detect 2wh vs 1.5wh) → `EncodeStillOnMemory` → overwrite → real Fsys_Close
via __dlsym(RTLD_NEXT). Resolve hook symbols lazily (zero DT_NEEDED) so load stays fail-safe. Hook misbehavior is NOT
a boot-brick (at worst a corrupted JPEG / app-process crash, recoverable) — distinct from the load-failure brick,
which Stage 3 already cleared. qemu-prove each shim build (VM `armgrain`) + run the isolated silicon test before any
boot-path deploy, same as Stage 3.

## LINUX ROUTE — STAGE 4a DESIGNED (2026-10-20, fable) — grain-linux-stage4a-design-2026-10-20.txt
The real grain shim, built incrementally. 4a = interpose Fsys_Close/Open, LOG DCF-JPG closes, passthrough otherwise.
- **Fsys_Close @0x11d01** = 1 opaque-handle arg, no path. **Fsys_Open @0x143fd** = arg0 path, arg1 out-handle. ⇒ record
  handle→path at Open, match at Close. Both are PLT imports in libmpr.so + libObj.so (the still-save path) ⇒ LD_PRELOAD
  interposes them. [VERIFIED]
- **KEY (changes every future hook): RTLD_NEXT does NOT work on the camera sonyld** (__dlsym(-1/0/-2/-3)→NULL). Use
  **`__dlopen("<lib>.so",1) + __dlsym(h,"sym")`** — resolves the real symbol AND bypasses our own interposer (qemu-verified:
  real close 0x3f728208 vs our 0x3f7bf438). A preload with UND __dlopen/__dlsym + zero DT_NEEDED loads fine (lazy PLT). [VERIFIED]
- **4a source** (grain_hook_4a.c, builds clean, proven ELF shape, zero DT_NEEDED, fail-safe: real fn first, return
  unchanged, additive log). NEW RISK: the interposer is global; if real-Fsys_Close resolution returns NULL in a boot
  process the close breaks → brick. MUST prove in the isolated updater-shell test that __dlopen("libInfraFsys.so")+
  __dlsym resolves (non-NULL) + the *outH deref is safe, BEFORE any boot-path deploy.
- **4b/4c flow:** after real close, re-open/read JPG → DecodeStillOnMemory(@0x5d52bc) → single YUV buf → signed noise to
  luma (runtime 2wh→4:2:2 even bytes / 1.5wh→4:2:0 first wh) → EncodeStillOnMemory(@0x5d53f8) → overwrite. Alloc: ~32 MB
  dst via mmap(MAP_ANON) on demand (parse SOF0 for w,h first); NOT static BSS (×6 processes). Grain is SYNCHRONOUS in
  Fsys_Close (~100-300 ms if HW codec). Prototype 4b in the ZERO-BRICK isolation harness on a sample JPG first (measure
  codec time + prove the chain) before grain touches the boot path.

## STAGE 4a — qemu interposer validation = GO (2026-10-20, fable)
With the REAL libInfraFsys.so + its 5 deps under qemu + camera sonyld:
- **Resolution [VERIFIED]:** __dlopen("libInfraFsys.so",1)=0x3f7c4800; __dlsym→real Fsys_Close 0x3f73cd01 / Fsys_Open
  0x3f73f3fd (= base+0x11d00/0x143fc), distinct from our own exports ⇒ the ensure_resolved() `return -1` path is NOT
  reachable ⇒ the global interposer cannot break Fsys_Close in the firmware (even safer there: libInfraFsys pre-loaded).
- **Passthrough+deref+log [VERIFIED]:** a caller Fsys_Open("/DCIM/100MSDCF/DSC00001.JPG",&h,..)+Fsys_Close(h) under
  LD_PRELOAD=grain_hook_4a.so → log "resolved Fsys_Close OK" + "CLOSE JPG ... 4096"; non-JPG close = pure passthrough
  (no log), exit 0, no crash. The *(long*)a1 deref is safe (a1 = valid out-ptr per API). Both brick-capable paths closed.
- Residual (boot-only, all fail-safe = at worst a wrong/missing LOG line, never behavior): exact Open↔Close handle token
  identity; table concurrency across ~6 processes. **GO: boot-test grain_hook_4a.so** (md5 f7779258). Plan: isolated
  silicon load-test ("4a: hook loaded") → arm env.txt→grain_hook_4a.so + WBI-zero → cold boot → read log for CLOSE JPG.

## STAGE 4a — BOOT TEST = PASS ON THE REAL CAMERA (2026-10-20) ★★ Fsys_Close interposition WORKS
env.txt→grain_hook_4a.so, cold boot, owner shot a frame. Camera boots + shoots normally with the global Fsys_Open/Close
interposer. Log /setting/grain_hook_4a.log:
- "4a: hook loaded" ×3 (ctor ran in the Fsys-using processes) + "4a: resolved Fsys_Close OK" ⇒ the __dlopen+__dlsym
  resolution SUCCEEDS in the firmware (the -1 brick path is NOT taken — confirmed on silicon). ✅
- "CLOSE JPG A:\DCIM\100MSDCF\DSC09786.JPG 0" etc ⇒ the hook fires exactly on DCF-still closes, PATH captured. ✅
**The SOOC-JPEG save point is interposable and we have the path. Foundation for the grain shim.**
### Key findings for 4b/4c (VERIFIED on camera):
1. **Path is Fsys namespace "A:\DCIM\100MSDCF\DSC#####.JPG"** (drive letter + backslashes), NOT a Unix path → raw
   open() fails (size logged as 0). ⇒ the grain shim must read/write the JPG via **Fsys_Open/Read/Lseek/Write**
   (resolve each via __dlopen("libInfraFsys.so")+__dlsym), not raw syscalls. Or find the SD Unix mount that "A:\" maps to.
2. **The hook fires on EVERY JPG close, incl. the firmware RE-READING old frames** (boot indexing / playback / thumbs —
   DSC09779..85 reappeared). ⇒ grain ONLY the fresh capture, not every close. Distinguish by Fsys_Open flags: a new
   capture opens O_CREAT/O_WRONLY; re-reads are O_RDONLY. Record+grain only write-opened DCF JPGs (and once each).
3. Multiple CLOSE lines per file (e.g. DSC09786 ×4) = several opens/closes per save (main + thumb + processes) — the
   grain pass must be idempotent / gated to run once on the final full-res write.
Camera currently runs the no-op-logging 4a hook (harmless; log grows per JPG close). Next: 4b = Fsys-based read →
DecodeStillOnMemory → re-encode → Fsys write-back (no grain yet), gated to the fresh full-res capture, prototyped in
the zero-brick isolation harness first (measure codec time).

## STAGE 4b — DESIGN LANDED (2026-10-20, lnx agent) — grain-linux-stage4b-design-2026-10-20.txt
Source <scratch>/lnx/vm/grain_hook_4b.c (builds, qemu-loads "4b: hook loaded"; same proven ELF shape; exports
Fsys_Open/Write/Close). SOLID: Fsys I/O prototypes (Open/Close/Read/Write/Rename/Remove, resolve via
__dlopen+__dlsym); fresh-capture gate = "handle was WRITTEN" (Open records handle→path, Write marks written,
Close processes only written DCF-JPGs once via an 8-entry done-ring — solves 4a's every-close/multi-per-file);
fail-safe (real Close first + unchanged, roundtrip after, write to ".TMP" then atomic Fsys_Rename, ANY error →
original untouched + temp removed + mmaps freed); mmap-anon alloc, SOF0 W,H parse.
KEY FACT: the decode→encode roundtrip CANNOT be isolation/qemu-tested — updater has no imaging stack, qemu no
HW codec; Decode/EncodeStillOnMemory only run inside the booted appFw → the roundtrip is BOOT-tested (fail-safe
makes the first boot safe; codec time logged via gettimeofday "4b: ROUNDTRIP ok dec_us=.. enc_us=.. bytes=..").
TWO BLOCKERS (resolving by static RE, zero camera): (1) Fsys WRITE/READ flag values (both #defined 0 now;
WRITE=0 → no O_CREAT → no-op) from Fsys_Open normalization @0x14452 + the appFw DSC*.JPG create call site;
(2) libmpr Mcmd codec argv order + return conv + decoder output format (only SetDecodeStillOnMemorySetSrc
@0x5d59df verified = srcVA,srcSize,sizeX,sizeY). DECISION (owner): full static-RE of both first, then build →
qemu-prove → isolation harness → boot-test. lnx agent ae85f0e7b60777ef5 doing the disasm now. Codec struct-API
migration (MprIf::EncodeStill @0x16f4b7 / PlayStillImage @0x16ff81) DEFERRED to 4c. Camera still on the 4a hook.

## STAGE 4b — RE RESOLVED + BUILD + ISOLATION = PASS (2026-10-20) ★ codec roundtrip proven in-harness
Both blockers pinned by static disasm: Fsys flags bit0=READ/bit1=WRITE/bit4=TRUNC/bit5=CREATE → READ=0x01,
WRITE=0x32 (hook now logs the firmware's own flags for ground-truth); codec Mcmd argv = BARE hex (addr/size)
+ BARE decimal (dims) — a "0x" prefix makes the parser return 0!; SetEncodeSetDst = dstSizeX,dstSizeY,
dstTgtSize,dstBufVA,dstBufSize; BOTH Decode/EncodeStillOnMemory handlers RETURN 1 ALWAYS → success+size by
OUTPUT validation (SOI+EOI scan), never the return. grain_hook_4b.c rewritten; build md5 e4cde800 (host
<scratch>/lnx/grain_hook_4b.so), same proven ELF shape. QEMU LOAD-PROOF: real df94859e sonyld loads it, exit 0,
ctor logs, no die-string (controls reject junk/.o). FAKE-Fsys+FAKE-codec ISOLATION (<scratch>/lnx/vm/fake*4b.c,
caller4b.c): Fsys+codec resolve non-null; fresh write → "ROUNDTRIP ok bytes=0x416" and the untouched path's
file on disk = 1046 B FFD8..FFD9 ⇒ read→(decode)→encode→.TMP→atomic Fsys_Rename END-TO-END; recently_done
ring + "written" gate both skip correctly (exactly 2 roundtrips for 2 fresh writes); no .TMP leftover.
HARNESS CAUGHT A REAL BUG that would have no-op'd 4b on camera too: xmmap used a SIGNED return compare (r>0)
→ a high mmap address (negative as signed long) was rejected; fixed to unsigned (r<0xfffff000). The REAL
codec can't run off-camera (no imaging stack in updater, no HW codec in qemu) → the roundtrip's codec step
is boot-tested; fail-safe + rich logging make the first boot test safe and informative. NEXT GATES (need
camera + owner, shown for approval): (1) silicon test (zero brick, real sonyld loads 4b in updater shell);
(2) boot test (accepted brick risk) — deploy as env.txt preload, cold boot, shoot 1 frame, read the log.

## STAGE 4b — BOOT TEST ON REAL CAMERA (2026-10-20): MECHANISM PASS, CODEC CRASH, FAIL-SAFE HELD ★★
Silicon PASS + armed; owner cold-booted (camera boots + shoots normally), shot DSC09787. Log:
load into ~10 procs, Fsys+codec resolved, GATE PERFECT (old-frame re-reads open READ 0x1 → skipped; the
fresh capture opens WRITE 0x7 → roundtrip once), full-res SOF parse "RT got=0x390000 W=4912 H=3264" — then
the process CRASHED (no "ROUNDTRIP ok", no "SKIP") inside the decode/encode Mcmd call. That crash during
save finalization caused the camera's "memory-card write not completed / recover?" prompt (owner recovered
= DB rebuild, no loss). FAIL-SAFE HELD THROUGH THE CRASH: it happened before step-6 writeback, so DSC09787
on the card is the INTACT original (3,735,552 B == the read size, PIL-valid 4912×3264 MPO, no .TMP).
GROUND-TRUTH FLAGS CAPTURED: write-open=0x7 (NOT the inferred 0x32!), read-open=0x1 → READ_FLAGS=0x01 right,
WRITE_FLAGS should be 0x7. DISARMED: env.txt reverted to grain_hook_4a.so (next boot = harmless logger).
Codec-crash suspects (RE next, static/zero-camera): (a) Mcmd handlers may be NON-static C++ methods needing
`this` in r0 (our fn(argc,argv) passes argc as this → crash); (b) DispParam required; (c) the HW codec needs
a physically-contiguous/coherent DMA buffer from a specific pool, not an anon mmap VA; (d) decode output >
W*H*2. PLAN: trace the FIRMWARE'S OWN decode/encode call site + its pixel-buffer source and replicate exactly
(or adopt the struct API MprIf::EncodeStill @0x16f4b7) instead of guessing the text-handler convention.

### CRASH ROOT-CAUSED (2026-10-20) — it's the BUFFER, not our call
RE verdict: our calling convention was CORRECT (static handlers, r0=argc/r1=argv, no `this`); DispParam is a
no-op stub (skip was right); the Mcmd on-memory path is a DEBUG-console path the real capture never uses. THE
CRASH = the codec needs **DMM-pool buffers** (physically-contiguous / DMA-coherent, reserved imaging DRAM;
allocators mcmn_dmm_alloc @libInfraMediaCommon 0x94cd, DmmAccess::DmmAllocate @libmprctrl 0x19d71). Our
mmap(MAP_ANON) VA has scattered physical pages / no bus mapping → the HW codec's DMA hit a bogus physical
address → SIGSEGV. The struct API (EncodeStill @0x16f4b7) still requires DMM buffers, so it doesn't fix it.
STRATEGIC FORK for the grain shim: (1) **SW JPEG codec embedded in the shim** [agent-rec] — pure CPU, plain
mmap, no DMM/HW/DMA, and FULLY off-camera-testable on the real DSC09787.JPG; cost ~800-1500 lines + ~1-3s/
save, preserve EXIF by splicing APPn, luma-only grain. (2) HW codec + DMM-pool buffers + struct API — fast/
native but allocates ~64MB from the LIVE imaging pool during save (contention/exhaustion risk), not off-camera
testable. (3) DCT-coefficient-domain grain — least code, fast, testable, but coarser/blockier. WRITE_FLAGS
fixed 0x32→0x07 (camera-confirmed).

### STAGE 4c = SW JPEG CODEC IN THE SHIM (owner chose Option 1, 2026-10-20)
Plan: 4c-1 freestanding INTEGER baseline-JPEG decoder+encoder (YCbCr domain, no HW/DMM, plain mmap) proven by
a no-grain roundtrip of a real 16MP SOOC frame fully in qemu; 4c-2 add luma grain, tune visually on the frame;
4c-3 integrate into the hook roundtrip (replace the Mcmd codec) + splice EXIF/APPn; 4c-4 camera boot test.
Key constraint: camera build is `-nostdlib` → NO libc/libgcc → INTEGER-ONLY (no float helpers), own mem fns.
BIG WIN: the SW codec is fully OFF-CAMERA testable — grain is perfected on the real frame with zero camera
risk before any boot test. FIXTURES saved (real NEX-3N SOOC, this camera): <scratch>/lnx/fixtures/DSC09580.JPG +
DSC09581.JPG (4912×3264 MPO) + E8_stockSF_DSC09770.JPG; also VM /tmp/4bh/DSC09580.JPG (md5 920ab0e9). The
real boot-test frame DSC09787.JPG was left on the SD only (not copied before disconnect). 4c-1 codec build
delegated to a sonnet agent (verified roundtrip acceptance). Camera idle on the harmless 4a logger.

## ON-CAMERA CONTROL IDEA (2026-10-20, owner) — repurpose a menu setting as the grain toggle
The preload runs INSIDE the appFw (im.elf), so the grain hook can READ a user-facing menu setting at capture time and
gate grain on it — giving on-camera control with NO menu-UI modification (flip an existing setting to toggle grain).
Best candidate: **Picture Effect = Soft Focus** (matches the original "select Soft Focus → get grain" vision), or a
Creative Style slot. Need: the cleanest way to read the current setting value from within the hook (a libObj getter,
a Backup/shared-property read, or shared memory). Under investigation. This is the UX layer on top of the 4b/4c grain shim.

## BACKLOG (post-Stage-4) — on-camera grain toggle [VERIFIED recipe] — grain-linux-oncamera-control-BACKLOG-2026-10-20.txt
Deferred until the grain shim works. Gate grain on the **Creative Style** (global Backup property, readable from the hook):
`__dlopen("libbackup.so",1) + Backup_read_4Byte(0x01070175) & 0xFF` → style value (ColorMode+1: Standard=1, Vivid=2,
Portrait=4, Landscape=5, B&W=6, …). grain ON iff value == owner's chosen style; **default OFF on any failure** (never
grain on doubt). Backup id + exported reader VERIFIED; exact byte + chosen value need one read-only confirm. The owner
flips it via the normal Creative Style menu — on-camera control, no UI change. (Picture Effect=Soft Focus UX is LOW
readability from Linux — av-cam CPU1, no confirmed Backup id; needs a makernote parse or a probe for 0x01070316. Optional.)
