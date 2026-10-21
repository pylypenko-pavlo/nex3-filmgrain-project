# Sony BIONZ DSP modules (`sa_*.bin`): what the processor is and how to disassemble it

Static analysis only: nothing was run on, or written to, the camera. Context: `notes/sony-dsp-generations.md` (container format, generations) and the README. Tools are in `code/isa/`. Every tool that reads module files or the camera's ARM firmware expects a user-supplied, unpacked firmware image (the ARM `av-cam` binary path via env var `NEX3N_AVCAM`; `sa_*.bin` modules extracted from the same image). No firmware or module files are shipped in this repo.

Credits: the scalar instruction set was later cross-checked against ma1co's Ghidra plugin, https://github.com/ma1co/SA-DSP (see section 15.8 and `notes/prior-art.md`). Backup parsing builds on ma1co's Sony-PMCA-RE (https://github.com/ma1co/Sony-PMCA-RE).

Status tags used below: **[verified]** = confirmed by code/corpus; **[hypothesis]** = consistent but unproven.

## 0. Summary

### 0.1 First pass
- **This is not an off-the-shelf binutils ISA.** 38 objdump target architectures were tried (mep, sh, MCore, csky, v850, ARC, xtensa, tic6x, bfin, cr16, fr30, m32r, rx, epiphany and others): none decodes the canonical prologue/epilogue into meaningful instructions. The "bad line" percentage proves nothing: on dense ISAs (fr30 1%, cris 0%, pru 0%) random bytes also decode almost error-free.
- **The scalar core is a proprietary 16-bit SuperH-like RISC, little-endian.** Semantics and ABI are almost SH: 16 registers, r15 = SP, r14 = FP, args in r4-r7, return in r0, callee-saved r8-r14, a PR/link register. Literals are loaded PC-relative with the SH formula `(PC&~3)+4+4*disp`; branches go to `PC+4+2*disp12`; calls go through a literal pool and `jsr @Rn`. **The encoding is its own, not SH**: the high byte is the opcode, the low two nibbles are Rm/Rn. No delay slots.
- **Modules contain a second code stream: 64-bit VLIW/SIMD bundles**, 8-byte aligned. NOP bundle = `0x1f70fb87dc3ee1f7`. They sit at the end of the text: sftfcs 0x2108-0x2900 (255 bundles), tbox 0x3248+ (383), yknr 0x30c8+ (315), jpeg_enc 0x1f98+ (263), defect 0x73d8+ (679). These appear to do the pixel work. **This ISA is not decoded.**
- **Same ISA on CXD4132, CXD90014 and CXD90045.** a6000 and A7 III show the same prologue/epilogue patterns, the same NOP bundle and the same start stub.
- **JPEG tables (zigzag, quantisation, Huffman) live in the ARM firmware `av-cam`, not in `sa_jpeg_*`.** So the JPEG DSP module drives a hardware encoder and ARM loads its tables. Zigzag appears only in the AVC decoders `sa_avcd_*_zma`.
- **How to disassemble:** `python3 code/isa/sadis.py <module.bin> [start end] [--img N] [--desc 0xNNNN]`. Partial disassembler: recognises literal pools, NOP bundles and known opcodes; unknown ones print as `.opXX`.

### 0.2 Second pass (module loading, grain)
- Module path/name tables exist in the Backup settings store (subsystem `0x00bd00xx`, section 9). The original conclusion that av-cam builds the load path from them turned out to be **wrong** (see the correction at the end of section 9).
- **Grain through the DSP is the hard path (structurally confirmed).** All image-processing modules (sftfcs, tbox, yknr, kknr, defect, spica, pbe, jpeg) push pixels through a hardware SIMD engine (registers `0x40000+`), configured by the module's second program from a job descriptor (width-1, height-1, strides, DMA addresses). **The scalar core never touches pixels** - it configures the engine and waits. The pixel stream is a 64-bit VLIW microprogram (section 10) that could not be decoded statically. There is no scalar module with a per-pixel loop over a Y buffer (section 11). Conclusion: grain is more practical on the Linux side via `libmpr` Decode/Encode than in the DSP.

### 0.3 Third pass (VLIW) -> section 13
- [verified] Bundle = 12 bits + 4 x 13 bits; NOP = `0x1f7` in every slot. A program starts with the header `0x0000080000000000` (189 of 189 in the corpus). VLIW code is byte-identical across generations. The scalar filter-launch function moves **9 or 25 coefficients (3x3 / 5x5)** into registers `0x40000+` and executes instruction `0009` with a command table.
- [hypothesis, later confirmed in section 15] Soft Focus coefficients come from the shared parameter block `0x12800...0x128ff`, which nothing inside the DSP writes -> set by ARM.
- Not decoded: VLIW opcode semantics. Only the field shape is known (`op3.a5.b5`, paired slots).

## 1. Module layout (header v1/v2, CXD4132)
- `+0x00` magic `aa0a1391`, `+0x04` version, `+0x08` ID.
- **`+0x30`: image table**, 16-byte entries: `u32 descriptor offset` + 12-byte name (`SFTFCS__0.02`). Multi-core modules have several entries: `kknr` (PRE/KK1), `spica` (PRE/MAP), `pbe_work` (MID/HIGH), `bdro2_bdex`, `dfdet`, `sweep_panorama`. v1 (zma/zima) has the descriptor at 0x80, v2 at 0x100 or 0x200.
- **Descriptor** (`3d 00 xx b0 42 VV ...`), u32 words from its start:
  - `w[4]` = **code base**: link address 0 here, entry point at +8 (shapep: 0). [verified] Literal-pool pointers land exactly on prologues (sftfcs 12/25, tbox 9/46, defect 14/103; with base `w[12]` the hit count is 0).
  - `w[5]` = end of loadable image; `w[6]` = image + bss; `w[8]` + `w[9]` ~ `w[12]` (crt0 and data before text); `w[10]` = 0x13800/0x15800 (memory size?); `w[11]` = 0x682 (constant in every module).
  - `w[16...]` in modules with two programs (sftfcs `0x3800`, tbox `0x2800/0x3000/0x3800/0xb000/0xb800`) are link addresses of the second programs. Then an MMIO map: `0x48000, 0x48200, 0x48100, 0x48160, 0x49d00, 0x3fffffff, 0x3ff80000, 0x481c0, 0x48c08`.
- **Before the text** (desc+0x68 ... w[4]): shared crt0 (`0f90 cdaf ...`) and 0x20-0x100 bytes of data.
- **Text** (from base `w[4]`):
  - `+0` zeros, then the **entry stub**: `mov.l @(lit),sp` (0x3800/0x2000), `mov.l @(lit),r14`, `mov.l @(lit),r1`, `jsr @r1` (init), `mov r0,r4`, `mov.l @(lit),r1`, `jmp @r1` (main). In the test module the stub first reads `r4 = *(0x481c0)`.
  - Right after the stub: a **configuration table** of u32 `id<<24 | value`, id 2...0x55. Its address is passed to a function as an argument, so it is **data, not code**.
  - Then functions with literal pools, 4-byte aligned right after `rts`.
  - Then the second program (if present) with its own stub (sp = 0x4000), linked at `w[16]`.
  - At the end: VLIW bundles and data.
- **Vector table** (`+0x7c`, 24 entries, all = 0x76) points into the configuration table. No code there; purpose unknown (maybe empty/default slots).
- Audio modules (`aaclcdec`, `ac3dec`, `lpcmdec`, `dd51enc`) differ: descriptor flags `3d 00 fd bf`, loaded at 0x45d00. Not examined.

## 2. Scalar ISA fingerprint (how it was established)
- **16-bit wide, LE.** Prologue `8f18 9f18 ... ef18 df00` = push r8...r14 and push PR. Epilogue `cf00 fe0c ... f80c 0300` = pop PR, pop r14...r8, rts. These pairs occur hundreds of times (`00cf` 220x, `00df` 196x).
- **Fields:** `[15:8]` opcode (two-register forms), `[7:4]` Rm (source or base), `[3:0]` Rn (destination; base for stores). imm8 forms: `[15:12]` opcode, `[11:4]` imm8, `[3:0]` Rn. Branches: `[15:12]` opcode, `[11:0]` disp12.
- **Literals:** `5iiN` = `mov.l @((PC&~3)+4+4*imm8),rN`. Verified across the corpus: targets are aligned, point to pools right after functions, and values make sense (MMIO 0x48xxx, masks 0x3fffffff/0x80000000, function pointers, printf string addresses).
- **Branches:** PC+4 base confirmed because targets are preceded by `bra`, `rts` or alignment nops; with PC or PC+2 bases this pattern disappears. Loops are nop-aligned.
- **No delay slots.** In `sa_test_intr_c0a`: `mov r4,"START"` -> `jsr printf` -> `mov r4,"arg = %08x"` -> `mov r9,r5` -> `jsr printf`. With a delay slot the first call would receive the wrong string.
- **Semantic anchors:**
  - `printf("\n*** START !! ***\n")` and `printf("arg = %08x\n", *(0x481c0))` in the test module;
  - sftfcs 0x1d90 is **`__divsi3`**: sign via `cmp/gt`+`neg`, shift-subtract via `cmp/hs`, `sub`, `shll #1`, `shlr`; on divide-by-zero writes 1 to 0x48250;
  - GCC/SH signed remainder idiom for `x % 64`: `shll` -> `subc r,r` -> `shlr #(16+10)` -> `add` -> `and #63` -> `sub`.

### Opcode table (final, after the ma1co cross-check in 15.8)
| Encoding (LE u16) | Mnemonic | Confidence |
|---|---|---|
| `0000` | nop | high |
| `0003` | rts / ret (via lr) | high |
| `0004` | sleep / wfi (wait for interrupt); always in a `0004; bra -4` loop | high (behaviour) |
| `0009`, `000a` | not in ma1co's spec. Appear only in the wrapper "`000a`; save r8-r14, lr; `mov r0,r4`; `0009`; restore" - one per image, 39 images. `0009` launches the engine with a command table in r0 (13.5, 15.8) | medium (structural) |
| `00ar` / `00br` | jmp @Rr / jsr @Rr | high |
| `00cr` / `00dr` | lds.l @Rr+,PR / sts.l PR,@-Rr (r = sp) | high |
| `007r` / `008r` | `lsls rd,#1` (fr = top bit) / `asrs rd,#1` (ma1co; we had `shlr`, corpus cannot distinguish) | high / per ma1co |
| `0Amn` | mov.l @Rm,Rn | high |
| `15mn` | mov.l Rm,@Rn | high |
| `0Cmn` | mov.l @Rm+,Rn (pop) | high |
| `18mn` | mov.l Rm,@-Rn (push) | high |
| `01mn` / `0Dmn` | `ldrsb` / `strb` - **byte** (ma1co; we first had 16-bit. Corpus agrees with ma1co: `ldrsb; uxtb; orr; strb` on 0x49002) | high |
| `07mn` / `09mn` | `ldrh` (signed) / `ldrh [rs],#2` (post-increment) | high (ma1co + corpus: 9/25 u16 coefficients) |
| `08mn` | `mov.w @(r0,Rm),Rn` | medium |
| `0Bmn` | `mov.l @(r0,Rm),Rn` (`mov #80,r0; 0bf1` = read from stack frame) | high |
| `16mn` | mov.l Rm,@(r0,Rn) (index in r0, as in SH) | medium |
| `1Bmn` | mov Rm,Rn | high |
| `19`/`1A`/`1C`/`1D` | `sxtb` / `sxth` / `uxtb` / `uxth` (ma1co; our earlier extu.w/exts.w reading was wrong) | high |
| `1Emn` / `20mn` / `27mn` | add / sub / neg | medium-high |
| `21mn` | subc (sign mask) | medium |
| `22mn` | `mul` (Rn <- Rn*Rm): index*12 + `0x13700` = 12-byte records | medium-high |
| `23mn` / `24mn` | and / or | medium |
| `25mn` | probably `not` (`~bit` -> clear register `0x48200`, next to `0xfffeffff`) | medium |
| `26mn` | probably `xor` (`r0 ^= 1` - double-buffer toggle) | medium |
| `29mn` | shift left by register (`1<<r2` -> masks for `0x48218`) | high |
| `2Emn`, `2F`, `30`-`33` | compares setting flag fr: `cmp.eq / geu / ges / gtu / gts / nand` | high (ma1co, 15.8) |
| `6dmn` | mov.l @(4*d,Rm),Rn | high |
| `7dmn` | mov.l Rm,@(4*d,Rn) | high |
| `8iiN` | `cmp.eq rd,#simm8` (fr = equal) | high |
| `9iiN` | mov #simm8,RN | high |
| `AiiN` | add #simm8,RN (`cfaf` = sp-4) | high |
| `4ddN` | `mov.w @(PC+4+2*d),RN`: 16-bit PC-relative constant from the pool after the function, sign-extended (d = `[11:4]`) | high (section 14) |
| `5iiN` | `mov.l @((PC&~3)+4+4*imm8),RN` | high |
| `Bddd` | bra PC+4+2*s12 | high |
| `Cddd` / `Dddd` | **`bfs` (branch if fr = 1) / `bfc` (if fr = 0)** (ma1co; our original polarity was inverted. Corpus confirms ma1co: `add #2,r0; cmp.eq r0,#18; D->back` sums exactly 9 words) | high |
| `F0/F1`, `F2/F3`, `F4/F5` | `lsl` / `lsr` / `asr rd,#imm5`, imm5 = `[8:4]` (ma1co `op7`) | high |
| others: `0x02-0x18`, `1F/21/22/25/26/28/2A/2B`, `0x34-0x39` (float), `0001/0002` (`cfr/sfr`), `002r/003r/005r/006r/009r` | full table in `code/isa/sadis.py`, per ma1co, cross-check in 15.8 | per ma1co |

Field direction for two-register forms is uniform: `[3:0]` = destination (base for stores); same in ma1co (`rd`/`rs`). The original `C/D` polarity was wrong (15.8); conclusions drawn from register-register compares were unaffected because compare meaning had been inferred from the same branches and the two errors cancelled. Conclusions using `cmp.eq #imm` + `C/D` were re-checked in 15.8.

## 3. binutils candidates
`code/isa/score.py` disassembles sftfcs text and the canonical prologue/epilogue snippet. Best case is nonsense: MCore-EL (closest field layout): `jsr r15` / `jmp r15` / `cmphs` / `rfi`; mep: `jsrv $8...`; sh: `.word`.

No ISA has its `rts` where our epilogues are: SH `000b`, MeP `7002`, Thumb `4770`, csky `783c`, ARC `7ee0`, xtensa `f00d` occur 0-67 times in 108k halfwords, while `0003` + pool ends every function here. **Conclusion:** proprietary ISA modelled on SH (probably a GCC port derived from the SH backend: same ABI and idioms). It is not a simple nibble-permuted SH either: the imm8 form differs (`5 ii N` vs SH `D N ii`).

## 4. JPEG anchors
Standard tables are in `av-cam`: zigzag @0x5f0d8c, zigzag-ordered quant table @0x54afb2, DC Huffman @0x54aa41. They are absent from `sa_jpeg_enc/dec_*`, and there are no DCT cosines in Q12/Q15 either (odd-offset matches are noise). So a hardware block encodes; the DSP module programs it and runs VLIW code (263 bundles in jpeg_enc; purpose unknown). The zigzag in `sa_avcd_*_zma` (@0x37a0/0x58a0) is not addressed via literal pools, probably base-relative.

## 5. ARM side
- Module start is passed via **four mailbox words**: av-cam strings `tbox_start_mbx.cha_mbx0..3`, `sftfcs_start_mbx.cha_mbx0..3`, `SAID / CmdCode / OsalID`, `SAIP / ParamAddress`.
- On the DSP side **mbx0 is probably at 0x481c0**: the test module reads it into r4 and prints it as `arg`.
- In sftfcs the entry receives an argument in r4 and treats it as a parameter-struct pointer (fields +4...+20 and a nested struct at +64).
- Other exchange registers: 0x49000/0x49002 (status bits 1/2/4 busy/ready), 0x49804 (wait until !=0), 0x48020/0x48024 (completion signal = 2), 0x48208/0x48030/0x48258 (final writes), 0x48250 (divide-by-zero flag), 0x49e04-0x49e64 (8-byte table scanned by 0x1d10).
- The ARM-side parameter block (`*_START_PARAM`) was reconstructed later; see `notes/sa-interface.md`.

## 6. Map of a small module: `sa_sftfcs` (Soft Focus, NEX-3N)
Addresses relative to code base = file 0x100 + 0x220.
| Address | What |
|---|---|
| 0x008 | stub: sp = r14 = 0x3800 -> `jsr 0x274` (init/job) -> `jmp 0x1c0` (main) |
| 0x01c-0x193 | configuration table `id<<24 \| val` (passed as argument) |
| 0x194/0x196 | wrapper `r0 = r4; 0009` (engine launch) |
| 0x1c0 | **main**: per-core mask (r4, `1<<n`), polls 0x48174/0x49c00, drains queue 0x48170->0x48100, waits on 0x49804, signals ready via 0x48020/24/0x48208/0x48030/0x48258 -> `sleep; bra sleep` |
| 0x274 | init: 0x1d10 (slot lookup in table 0x49e04) -> 0x16dc |
| 0x16dc | job setup: bits in 0x48004/0x48024, status 0x49000=0->0xf, 0x49002 \|= 1 -> 0x1cd4 (check; !=0 = error) -> 0x49002 \|= 2 -> **0x1118** |
| 0x1118-0x16db | **main work** (~1.5 KB): 104-byte frame, reads the param struct (r4: +12, +16, +20, nested +64), checks alignment (mod 64 / mod 32, branches on 0/16/32/48 and 0/8/16/24), block loop calling 0x498, 0x4c8, 0x628 (MMIO 0x48200/0x48218/0x48230/0x48234/0x49000) and 0x194; 0xd28 passed as a callback pointer |
| 0x1780/0x1808/0x1b28/0x1c38/0x1cd4 | helpers (0x1780 calls the divider; 0x1b28 = parameter checks, 0x1c38 = param import - section 15) |
| 0x1d90 | `__divsi3` |
| 0x1e60 | **second program** (linked at 0x3800 = `w[16]`): stub sp = 0x4000 -> `jsr 0x39d8` (= 0x2038), loop: sleep -> read job descriptor from shared memory 0x13700 (+12 = status, +20 = ...), write counters minus 1 to 0x40000/0x40004... (**VLIW engine registers**) |
| 0x2108-0x2900 | 255 64-bit VLIW bundles (blur kernel) + data |

## 7. Tools (`code/isa/`)
- `mod.py` - module parser: image table, descriptor, base `w[4]`, `lits()`.
- `sadis.py` - disassembler (rewritten to ma1co's spec; the original decoder is kept as `sadis_v1_old.py`). Examples: `python3 sadis.py sa_sftfcs.bin 0x1118 0x1660`, `python3 sadis.py <other-generation>/sa_tbox.bin`, `--img 1` for the second image, `--desc 0xNNNN [s e]` for any core image.
- `cfg.py` - recursive static control-flow walk (coverage check, 15.8).
- `br.py` (branch-base hypotheses), `score.py` (38 binutils architectures), `stats.py` (entropy, n-grams).
- VLIW: `vl.py`, `corpus.py` (collect bundles), `slots.py` (slot splitting), `vdump.py <mod> [start end]` (slot view), `rets.py`, `code.py`, `vliw.py`. Generated dumps (`out/allq.npy`, `progA.npy`, `cmdtables.pkl`, disassembly listings) are not shipped.
- Pitfalls: without `--img`/`w[4]` addresses shift by 8 bytes (in most modules `w[4] = w[12] + 8`). Configuration tables and the VLIW area print as garbage instructions (NOP bundles are marked, others are not). A spurious `5xxx` inside data can mark a code chunk as a pool.

## 8. Next steps / what would help
1. Close remaining scalar opcodes using libgcc-like functions (`__divsi3`, `__udivsi3`, memcpy/memset) shared between modules, compared to reference GCC SH code. (Largely superseded by the ma1co spec, 15.8.)
2. **VLIW:** collect all bundles, find bit fields by variability (NOP gives a fixed background), link to `0x40000+` registers via the second program.
3. Biggest helps: the core's name (absent from av-cam, kernel and `liro.ko` strings); any Sony SDK/ELF with symbols (toolchain, debug module); a DSP runtime dump (`ssboot.bin`, `idt_cam.bin` not examined - may contain loader and interrupt handlers); camera UART logs during module load.

## 9. Module name/path tables in the Backup store
Three tables in the Backup settings store (subsystem `0x00bd00xx`, all `attr 0` = unprotected; parsed with the Sony-PMCA-RE backup parser):

- **BKID `0x00bd0000` - base-name table.** 3200 bytes = **100 records of 32 bytes**, `\0`-padded file names. Copy at **`0x00bd0006`** (identical). Record index for interesting modules:

  | index | byte offset | module |
  |---|---|---|
  | 15/16 | 0x1e0/0x200 | jpeg_enc 1unit/1core |
  | 17/18 | 0x220/0x240 | jpeg_dec 1unit/1core |
  | 23 | 0x2e0 | apollo4 |
  | 30 | 0x3c0 | pbe |
  | 44 | 0x580 | kknr |
  | 51 | 0x660 | defect |
  | 53 | 0x6a0 | spica |
  | 54 | 0x6c0 | tbox (Miniature) |
  | **55** | **0x6e0** | **sftfcs (Soft Focus)** |
  | 57-88 | 0x720-0xb00 | spica_*_tap tables |
  | 71 | 0x8e0 | pbe_work |
  | 72 | 0x900 | star |
  | 74 | 0x940 | yknr |
  | 91 | 0xb60 | shapep |

- **BKID `0x00bd0001` - directory (prefix) table.** 512 bytes = **8 slots of 64 bytes**: 0 `/usr/sabin/`, 1 `/system/sabin/`, 2 `/system/lensbin_lensproperty/`, 3 `/usr/`, 4 `/usr/share/startbinary/`, 5 `/usr/share/dspbin-mag/`, 6 `/setting/`, 7 `/usr/sabin/`.
- **BKID `0x00bd0002`** - 800 bytes, 8-byte records `[u16 index][u16 0x0093][u16 ref][u16 0x0001]` (index 0,1,2...; ref 0xc0,0xc1,...): maps codectype -> file number.
- **BKID `0x00bd0007`** - TOC: `[u16][u32 BKID]` records pointing at `0x00bd0000`/`0x00bd0006`.

In av-cam there is no `/usr/sabin/` prefix string and no `sa_*.bin` base names as literals (except 18 full `spica_*_tap` paths, hard-coded separately). a6000 firmware also references `0x00bd0000` (17 times), so the scheme is probably shared.

**Correction (from `notes/sa-interface.md`):** the first-pass claim that the module path is assembled as "prefix from `0x00bd0001` + name from `0x00bd0000`" is wrong - the references found were coincidental bytes inside tables. av-cam opens a module by codectype (sftfcs = 0x18); `0x00bd0002` maps codectype -> file number. Where the prefix is chosen is not established. Since effect modules never touch pixels from scalar code (sections 10-11), replacing a module for grain would gain little anyway.

## 10. VLIW engine: second pass (partly superseded by section 13)
Corrections applied from section 13: a bundle is not "4 lanes of 16 bits" but **one 12-bit slot + four 13-bit slots**, NOP = `0x1f7` in every slot; a module holds **several images for different cores**, each with its own VLIW block, so the sizes below refer to the main image only.
- **Location.** End of text of processing modules: 8-byte-aligned 64-bit bundles; sftfcs 255, tbox 383, yknr 315, jpeg_enc 263, defect 679, pbe_work (89 NOP markers).
- **These are data for a hardware engine, not scalar code.** No scalar literal points into the area. The second program (sftfcs 0x1e60, linked at 0x3800) reads the job descriptor in shared memory `0x13700` (fields +124->+56/+60, sub-array +0..+24), subtracts 1 and writes to `0x40000, 0x40004, 0x40008 ...` - SIMD datapath configuration (width-1, height-1, strides, DMA addresses), not bundle execution. Loop: `sleep` (wait for engine interrupt) -> write next parameter block -> repeat.
- **Bundle statistics.** Across 1158 non-NOP bundles **all 64 bits vary** (bit-one frequency 0.37-0.84): no fixed bundle-level opcode field. Values cluster (dense VLIW encoding, not random coefficients). Byte entropy of the area 5.55/8.
- **Conclusion.** Adding noise to Y here would require decoding the VLIW ISA and the semantics of the `0x40000+` engine and the `0x13700` descriptor format. Not feasible statically without a DSP manual or hardware debugging. **Not done; difficulty high.**

## 11. Grain on the scalar core: no suitable module [verified]
- Modules **without** VLIW (no NOP bundle anywhere in the file): `sa_shapep`, `sa_test_intr_c0a`, `sa_zima_startup_*`. All small, **no per-pixel loop over a frame buffer**. (`sa_frc2` and `sa_star` were wrongly listed first; they have VLIW in other cores' images: 30 and 144 NOP bundles.)
- The scalar core only addresses MMIO `0x48000-0x49xxx` (engine/DMA control, status flags) and `0x40000+` (engine registers). **It never sees a flat pixel buffer** - pixels live in external DRAM and move via the engine's DMA.
- Result: neither VLIW nor scalar DSP paths give an easy place for grain. Grain remains a Linux-side job (`libmpr` `DecodeStillOnMemory`/`EncodeStillOnMemory`: decode JPEG -> noise on ARM -> encode).

## 12. Additional scalar opcodes (second pass)
Confirmed on engine-configuration functions and `__divsi3`:
- `6nmN` = `mov.l @(4*n,Rm),RN`, `7nmN` = `mov.l RN,@(4*n,Rm)` (n = `[11:8]`): bulk reads of descriptor fields `@(0,r3)...@(24,r3)` and writes to the engine.
- `AiiN` = `add #simm8,RN`: `aff1` = +(-1), `aff6` = -1 to r6, `a042` = +4 to r2, `a7c5` = +124 to r5.
- `15mN` = `mov.l Rm,@RN`, `0Amn` = `mov.l @Rm,Rn` - load/modify/store pairs on MMIO.
(`01/0D` were first read as 16-bit; corrected to byte in 15.8.)

## 13. VLIW engine: third pass
Corpus: NEX-3N `sabin` modules, cross-checked against a6000, A7 II, A7 III, a6400 and NEX-6 module sets. Tools: `vl.py`, `corpus.py`, `slots.py`, `vdump.py`, `sadis.py --desc`.

### 13.0 Summary
- [verified] **Bundle format:** 64 bits = slot S0 (12 bits, `[63:52]`) + four 13-bit slots (S1 `[51:39]`, S2 `[38:26]`, S3 `[25:13]`, S4 `[12:0]`). NOP `0x1f70fb87dc3ee1f7` is exactly **`0x1f7` in each of the five slots**.
- [verified] **A VLIW program starts with header** `0x0000080000000000`, immediately followed by a NOP. 189 headers in the 3N corpus, all followed by NOP. Each core image has its own program: sftfcs has 3 (one per core), tbox 5.
- [verified] **VLIW code is byte-identical across generations** (CXD4132 = 90014 = 90045). +/-16-bundle windows around every NOP match in 6 of 6 modules checked. It was never rebuilt or moved, so cross-generation diffing does not separate VLIW fields: only scalar code and addresses differ.
- [verified] **Filter launch protocol (scalar side):** **9** values (to `0x40024`) or **25** values (to `0x40064`) are written into engine registers from `0x40000` - exactly 3x3 or 5x5. Then a parameter into `0x40024`/`0x40064`, addresses/strides into `0x40028...`/`0x40068...`, then the wrapper `mov r4,r0; 0009` with a command-table pointer.
- [hypothesis, confirmed in 15] Soft Focus coefficients come from **four 64-byte tables in DSP shared memory `0x12800/0x12840/0x12880/0x128c0`**, pair selected by a flag. No sftfcs core writes `0x128xx` and the file has no constant 3x3/5x5 kernels, so **effect strength is data, not DSP code**.
- Not decoded: VLIW opcode semantics. Bundles have no room for 8/16-bit immediates, so filter coefficients will not be found inside bundles - they go through engine registers.

### 13.1 Where programs live [verified]
- A module has several images for different cores: descriptors `3d 00 xx b0 42` at different file offsets. sftfcs 3N: `0x100` (core 0, `w[2]=0x80002`), `0x2c20` (`0x102`), `0x6cc0` (`0x202`). tbox: 4 images, byte 1 of `w[2]` = 0,1,2,3, so `w[2]` = core mask/number. In v4 (a6000) the descriptor is shifted one word: `w[3]` = size, text base in `w[4]`.
- Each image of cores 1...N has **5 scalar subprograms** with identical layout, linked at `0x2800/0x3000/0x3800/0xb000/0xb800` (the `w[16...]` values), each starting with `bra +0x10` (`06b0`, searchable as `06b0 0000...`). Then stub (sp <- ..., jsr), command table and code. **At the end of the image: one VLIW program** (header + NOP + bundles up to a zero word).
- Lengths: sftfcs 254/368/320 bundles; tbox 386/173/254/374/374. Whole 3N corpus: 189 programs, 168,378 bundles.

### 13.2 Three bundle families
| Family | Signature | Count (3N) | Status |
|---|---|---|---|
| **A** (main code?) | at least one slot = `0x1f7` | 47,254 | slot format established |
| **B** | modal bundle `0xf1c78f000701c3ee` (4,846x) | 72,414 | 12+4x13 split is **not optimal** for it (+1 bit shift concentrates better) -> different format, not decoded |
| **C** | slots almost all ones (`0x1fff`, S0 = `0xbff`), mean popcount 58/64 | 48,710 | looks like a table of 4-bit entries where `f` = empty (permutation/routing?), hypothesis |

In sftfcs core 0 the order is A (0x000-0x298) -> B (0x2a0-0x540) -> C (0x548-0x7e8). Whether B/C are code or data referenced by A is unknown.

### 13.3 How the slot format was established [verified]
1. The most frequent XOR masks against NOP among near-NOP bundles (Hamming distance <= 10) fit in ranges `63..53`, `51..39`, `38..26`, `25..17`, `17..13`, `12..0`, `2..0` etc. **No frequent single mask crosses the 52/51, 39/38, 26/25, 13/12 boundaries.**
2. Fraction of bundles whose slot equals its NOP value with the 12+4x13 split: 0.55 / 0.53 / 0.53 / 0.54 / 0.52. Shifting boundaries by +/-1 or 2 bits drops it to 0.39-0.50; 4x16 gives 0.39-0.42.
3. All five NOP slots equal `0x1f7`; a coincidence is essentially impossible.
4. Example (`vdump.py`, sftfcs core 1, file `0x6420`), slots S1...S4 as `op3.a5.b5`:
   ```
   006438 a91ec1758be51f46  S0=a91   7.12.02   7.11.02   7.25.08   7.26.06
   006440 ad1ec1758bd55e89  S0=ad1   7.12.02   7.11.02   7.21.10   7.20.09   x6 in a row
   006470 a91ea1748bc51e06  S0=a91   7.10.02   7.09.02   7.17.08   7.16.06   x6 in a row
   ```

### 13.4 Fields inside a 13-bit slot [hypothesis]
- Split `op[12:10]` (3 bits) + `a[9:5]` (5) + `b[4:0]` (5). NOP = `0.15.23`. `a` and `b` take almost all 32 values for every op - consistent with **register numbers in a 32-entry register file**.
- **Slot pairing:** with equal op, the most common relation S1<->S2 and S3<->S4 is `a` differs by 1, `b` equal (332 and 205 cases, top in both pairs). Looks like one operation over adjacent registers (two-lane SIMD), e.g. `7.12.02 / 7.11.02`, `7.21.10 / 7.20.09`.
- A bundle repeated 6 times in a row (sftfcs core 1) resembles an unrolled loop over filter taps.
- S0 (12 bits) in active bundles takes `0xa?1/0xb?1` (`a91`, `ad1`, `b11`, `b51`...) and `0xe?8` (`e18`, `e58`): probably a control or load/store slot.

### 13.5 Link to the scalar side
Filter-launch function in sftfcs core 1 (`--desc 0x2c20`, text `0x11e4`), two branches: 3x3 and 5x5.
- `mov.l @(lit),r2 = 0x40000; mov.l @(lit),r3 = 0x40024 | 0x40064` -> loop `0951; 1512; a042; 2e32; bt` moves 9 or 25 values from `@r5+` into consecutive engine registers. **Hence opcode `0x09` = post-increment load** (`r5` is not incremented anywhere else).
- Then `0x40024/0x40064` <- field `@(12,job)`; `0x40028.../0x40068...` <- `0`, `@(48,job)`, `@(0,job+64)`, `@(4,job+64)`... (addresses and strides, hypothesis). Then `jsr 0x2b8` with `r4` = command table (`0x1c`, `0x98`, `0x12c`, `0x1e8`).
- `0x2b8` = wrapper "save r8-r14 and PR; `mov r4,r0`; **`0009`**; restore". So **`0009` launches the engine program, `r0` points to the command table** (structural; name tentative). Same wrapper in core 0 (`0x194`).
- **Command tables:** u32 `[idx:8][value:24]`. Indices run continuously across tables (`02...1f`, `1b...36`, `37...50`, `56...70`), some with bit 7 set (`97`, `98`, `ae`, `b0`, `b4`). Values: small numbers 0...0x23, `0x080000`, `0x800001`, `0xff000a`, `0x030301`.
- **Coefficient source:** array pointers come from `@(32,sp)`/`@(36,sp)`, set to `0x12880`/`0x128c0` when flag `r5 != 0`, else `0x12800`/`0x12840`. None of the three sftfcs images writes `0x128xx`; the address is just passed on. `0x12800` is a **shared area referenced by almost all modules** (tbox, yknr, kknr, star, defect, pbe_work, dfdet, apollo4, avce...). Most likely a standard job parameter block filled by an external master (ARM via `*_START_PARAM`).
- Engine register sets differ per module (from literals): tbox `0x40000, 0x40028...0x400c8`; yknr `0x40000...0x40028, 0x40038, 0x40100`; kknr `...0x40024, 0x40040, 0x40078, 0x400c0...0x40104`; star `0x40000...0x4003c`. `0x40000+` is a generic engine parameter register file with per-program layout.

### 13.6 Implication for grain
- Noise cannot be added inside a VLIW program until at least one A/B/C opcode is understood.
- **Workaround idea:** if the Soft Focus kernel comes from `0x12800-0x128ff` and is set by ARM, its shape (the convolution) can be changed through parameters. Grain is additive noise and cannot be produced by convolution, but film-like softness or halation can - without touching DSP code (see `notes/film-effects-plan.md`). Grain stays on the Linux side.

### 13.7 Scalar opcodes refined in this pass
Merged into the opcode table in section 2 (`09`, `0B`, `08`, `07`+`1D`, `22`, `29`, `26`, `25`, `0009`, `4ddN`).

### 13.8 Where it stalled
- **Without semantic anchors** statistics only give shape (slots, fields), not meaning. Would help:
  1. **The simplest VLIW program** (shortest in corpus: `sa_bd_lpcmdec` with one header, `jpeg_*` with one). If an operation is trivially known (copy, constant add), match bundles to it. Not done.
  2. **A DSP RAM dump while an effect runs** (shared memory `0x12800`, `0x13700`, registers `0x40000+`). Needs the camera.
  3. **Any Sony or Socionext/MeP SDK/ELF for this DSP.** No strings in the corpus.
  4. Command-table index <-> bundle number (done in 15.5/15.9, negative).

## 14. Opcode `4ddN`; emulator status
- [verified] **`4ddN` = `mov.w @(PC+4+2*d),RN`**: 16-bit constant from the pool right after the function, d = `[11:4]`, sign-extended. The 16-bit sibling of `5iiN`.
- Check on function `0x16dc` of the main `sa_sftfcs` image (3N); all targets fall in the pool `0x1758-0x1764` after `rts`:

  | Address | Code | Result | Meaning |
  |---|---|---|---|
  | 0x16e4 | `4381` | r1 = `0x02ac` (from 0x1758) | prologue: `sub r1,sp` - frame size |
  | 0x174c | `4047` | r7 = `0x02ac` (from 0x1758) | epilogue: `add r7,sp` - same constant |
  | 0x16e8 | `4372` | r2 = `0xfdff` -> `0xfffffdff` | clear bit 9 (`and`) |
  | 0x16ee | `4357` | r7 = `0x0200` | set bit 9 (`or`) |
  | 0x16f8 | `4310` | r0 = `0x02a4` | index for `mov.l ...,@(r0,sp)` |
  | 0x1714 | `4249` | r9 = `0x0258` | buffer offset in frame (`add sp,r9`) |
  | 0x173a / 0x1744 | `4121` / `40e1` | `0x00fd` / `0x00fe` | bit masks |

  Prologue and epilogue reading the same pool cell plus consistent `0xfdff`/`0x0200` masks confirm the format; `0xfdff` acting as a 32-bit AND mask shows sign extension. (An earlier "4-bit immediate in `[11:8]`" reading was wrong.)
- No scalar-core emulator was built, so engine setup logs, `0009` launches, command-index <-> bundle mapping and short-program decoding were not obtained.

## 15. Soft Focus: from the Backup store to engine registers (static)
Code reading only (`sadis.py --desc`). The ARM side and the layout of Backup property `0x0003010a` are in `notes/sa-interface.md` section 2. This is what the DSP does with that data (`sa_sftfcs.bin` 3N; core images `0x100` = core 0, `0x2c20` = core 1).

### 15.0 Summary
- [verified] **Full convolution-kernel path:**
  1. Backup `+0x10/+0x30/+0x50/+0x90`.
  2. ARM copies them to `base+0x100/0x140/0x180/0x1c0` and passes pointers in param block `+0x0c...+0x18`.
  3. DSP core 1 **DMA-copies 64 bytes each** from these pointers to local `0x12800/0x12840/0x12880/0x128c0`, same order.
  4. The launch function moves 9 (3x3) or 25 (5x5) values into `0x40000...` and starts the engine.
- [verified] **The DSP validates parameters** and returns `0xeeee000N` on violation (15.3). For "haze" experiments: **every kernel must sum to exactly 256**, each of the three level bytes <= 64 and their sum <= 64.
- [verified] **Core 1 runs the filter three times:** once with the 3x3 pair (`0x12800`->`0x12840`) and twice with the 5x5 pair (`0x12880`->`0x128c0`). (Corrected after the ma1co cross-check; the first version had it reversed due to inverted `bfs/bfc`.)
- [hypothesis] **The three level bytes are blend weights in 64ths** (sum <= 64; remainder presumably goes to the original). Where they enter the engine was not traced (15.4).
- Negative: `0009` command-table indices do not map to VLIW bundle numbers (15.5); the short VLIW program is not decoded (15.6).

### 15.1 Param-block import in core 0 [verified, function `0x1c38`]
`r5` = param block from ARM (`bus(base)+0x80`), `r4` = local copy J (on stack, `sp+0x258` in `0x16dc`). Address fields go through `0x1d10` (bus address -> local, via window table `0x49e04...0x49e64`).

| Param (from ARM) | -> J | Meaning (from checks in 15.3) |
|---|---|---|
| `+0x00/+0x04/+0x08` | `+64/+68/+72` (via `0x1d10`) | three image buffers (in / out / work) |
| `+0x0c/+0x10/+0x14/+0x18` | `+48/+52/+56/+60` (via `0x1d10`) | pointers to four kernels (3x3 A, 3x3 B, 5x5 A, 5x5 B) |
| `+0x1c` | `+16` | width |
| `+0x20` | `+20` | height |
| `+0x24` | `+12` | stride |
| `+0x28` | `+24` | level byte 1 |
| `+0x2c` | `+28` | level byte 2 |
| `+0x30` | `+32` | not checked, unknown |
| `+0x34` | `+36` | level byte 3 |
| - | `+4` = (width/64 + 1)*64, `+8` = (height/32 + 1)*32 | padded sizes (via signed-division idiom) |

The level bytes land exactly at `+0x28/+0x2c/+0x34` - the same offsets where, per the ARM analysis, `0x465cf8`/`HapiSFTFCS` writes the three level bytes from Backup `+0..+8`. Independent confirmation from both sides.

### 15.2 Convolution kernels: Backup -> DSP [verified]
Current values of Backup `0x0003010a` (u16):

| Backup | ARM | DSP (after DMA) | Kernel | Sum |
|---|---|---|---|---|
| `+0x10` | `base+0x100` | `0x12800` | 3x3 A: `28 28 28 / 29 30 29 / 28 28 28` (near box) | 256 |
| `+0x30` | `base+0x140` | `0x12840` | 3x3 B: `9 65 9 / 10 70 10 / 9 65 9` (weight in middle column) | 256 |
| `+0x50` | `base+0x180` | `0x12880` | 5x5 A: 10...12, near box | 256 |
| `+0x90` | `base+0x1c0` | `0x128c0` | 5x5 B: `0 16 17 16 0 / ... / 0 17 22 17 0 / ...` (outer columns 0) | 256 |

- **DMA (core 1, `0xfb8-0x106c`):** descriptor list at `0x13800`, 16 bytes each: `{src & 0x3fffffff, (dst<<2) | 0x3ff80000, 0x003f0000, 0}`. Started via `0x13840` (`1`, `0x40000000`), `0x48230 = 1`, `0x48208 = 0x10000`, then `sleep`. Sources are fields `+40/+44/+48/+52` of core 1's job struct (same order as ARM `+0x0c...+0x18`). Top address bits are checked `>>30 == 1`, else error path. How that struct derives from core 0's J is not traced; order and count match.
- **Filter launch (core 1, `0xaac` -> `0x11e4`):** argument `r5` selects the pair: `r5 = 0` -> 3x3 (`0x12800`, `0x12840`), `r5 != 0` -> 5x5 (`0x12880`, `0x128c0`) (`cmp.eq r5,#0; bfs 0xf64`). The same flag in `0x11e4` (`cmp.eq r7,#0; bfc 0x1288`) selects 9 vs 25 registers. Values move via `ldrh r1,[r5],#2` - **16-bit** coefficients, like the u16 in Backup. Kernel A is loaded into `0x40000...` and `0009` runs, then kernel B and `0009` again: **two passes, A then B**.
- **Sequence (core 1, `0x1074-0x108e`):** `0xaac(K, r5=0, r6=0)` -> `0xaac(K, 1, 1)` -> `0xaac(K, 1, 2)`: 3x3 once (step 0), 5x5 twice (steps 1, 2). `r6` = step number, probably selects buffers.
- For experiments: blur shape is set by these four kernels; **each must still sum to 256**. Weights can be redistributed (wider/narrower, anisotropic) but total kernel gain cannot change (15.3, errors 8/9).

### 15.3 DSP parameter checks [verified, function `0x1b28`]
On failure the function returns `0xeeee000N` and `0x1cd4` skips processing.

| Code | Error condition | Implication |
|---|---|---|
| `...01` | width <= `0x27f` (639) or width & 15 != 0 | width >= 640 and a multiple of 16 |
| `...02` | height <= `0x1df` (479) or height & 7 != 0 | height >= 480 and a multiple of 8 |
| `...03` | stride & 15 != 0 or stride < width | stride multiple of 16, >= width |
| `...04` | any level byte > 64 **or their sum > 64** | weights in 64ths (meaning hypothesised, condition verified) |
| `...05` | any of three buffer addresses & 7 != 0 | 8-byte alignment |
| `...06` | any of four kernel addresses & 7 != 0 | 8-byte alignment |
| `...08` | sum(3x3 A) != 256 or sum(3x3 B) != sum(3x3 A) | **each 3x3 kernel = 256** |
| `...09` | same for 5x5 (25 words) | **each 5x5 kernel = 256** |

Current levels from Backup (`+0..+8`): level 2 = `22 26 0` (sum 48), level 1 = `14 24 8` (46), level 0 = `6 22 16` (44). All pass. **Hypothesis:** the three weights correspond to the three blur passes (3x3 step 0, 5x5 step 1, 5x5 step 2) and `64 - sum` goes to the original; then "level 0" = 20/64 original, "level 2" = 16/64. Consistent with three passes and the 64 limit, but **the blending code was not found**.

### 15.4 Gaps
- After validation, level bytes (J `+24/+28/+36`) are not read explicitly in core 0's examined code (`0x1118`, `0x1780-0x1b28`); offset searches in cores 1 and 2 were inconclusive. They probably reach the engine through command tables (24-bit values) or a whole-struct copy.
- J (core 0) -> K (core 1, fields `+40...+52`) not traced: candidate locations `0x13000 + i*0x1b0`, `0x13700` are visible but layouts not compared.

### 15.5 Command tables <-> VLIW (negative result)
- sftfcs core 1 has four tables (`0x1c`, `0x98`, `0x12c`, `0x1e8`), 144 entries `[idx:8][value:24]`. 7-bit indices take **108 distinct values out of 0...112** (bit 7 set on 6 entries).
- Indices **do not single out special bundles**: the fraction of active-S0 bundles among "indexed" ones (0.53) equals that of the first 128 bundles (0.52); 10 of 108 are NOPs.
- Hypothesis: the index is an engine parameter cell number (~113 slots), not a bundle address. `0009` loads parameters and starts an already-loaded program.

### 15.6 Short VLIW program
Not decoded. Without a known input -> output pair statics only yield slot shape, and such a pair requires running hardware.

### 15.7 Scalar opcodes added in this pass
| Code | Meaning | How established |
|---|---|---|
| `F4iN`/`F5iN` | `asr rd,#imm5` (ma1co `op7=0x7a`) | signed-division idiom `shll; subc r,r; shlr #(16+k); add; shar #i` in `0x1c38` (round width to 64, height to 32) |
| `F2iN`/`F3iN` | `lsr rd,#imm5` (ma1co `op7=0x79`). `f221` = `lsr r1,#2`: `0x12800>>2 = 0x4a00`, **word address** | corrected per ma1co (first read as left shift) |
| `2Emn` | `cmp.eq rd,rs`: fr = (rd == rs) | first read as "!=" with inverted branch polarity; net meaning of the checks unchanged |
| `31mn` | `cmp.gtu rd,rs`: fr = rd > rs unsigned | `cmp.gtu r6,r2(=64); bfs err4` -> byte > 64 = error |
| `32mn` | `cmp.gts rd,rs`: fr = rd > rs signed | `cmp.gts r3(w),r1(639); bfc err1` -> width <= 639 = error |
| `33mn` | `cmp.nand rd,rs`: fr = (rd & rs) == 0 | `cmp.nand r3,r5(15); bfc err1` -> not multiple of 16 = error |
| `30mn` | `cmp.ges rd,rs` signed; `2Fmn` = `cmp.geu` | per ma1co |
| `4ddN` | `mov.w @(PC+4+2*d),RN` | section 14 |

### 15.8 Cross-check against ma1co's spec (https://github.com/ma1co/SA-DSP)
**Source:** ma1co's Ghidra processor plugin, `data/languages/dsp.slaspec` (+ `dsp.cspec`), commit `322bc4a`, 2021-08-09. Discovery context in `notes/prior-art.md`. `code/isa/sadis.py` now decodes per that table (`dis1` rewritten; old decoder kept as `sadis_v1_old.py`). Only `0009` and `000a`, missing from ma1co, were added.

**Agrees [verified]:**
- 16-bit LE words; fields `rd = [3:0]` (destination or store base), `rs = [7:4]`.
- PC literals: `5` = `ldr`, `4` = signed `ldrh` - matches section 14 exactly.
- `6/7` = `ldr/str [r,#4*imm4]`; `8/9/A` = `cmp.eq/mov/add #simm8`; `B` = branch `PC+4+2*s12`.
- `00a/00b/00c/00d` = `b/bl/ldr lr/str lr`; `0003` = `ret` (via `lr`); `0004` = `wfi`.
- No delay slots.
- ABI (`dsp.cspec`): args r4-r7, result r0, r8-r15 callee-saved - matches our inference.

**Disagreements and corpus verdict:**

| What | We had | ma1co | Corpus verdict |
|---|---|---|---|
| `C`/`D` | `bf`/`bt` | `bfs` (branch if fr = 1) / `bfc` (fr = 0) | **ma1co.** `sa_sftfcs` `0x1ba8`: `add r0,#2; cmp.eq r0,#18; bfc back` loops exactly 9 halfwords (3x3 kernel); with our polarity it would run once |
| `2E` | "T = !=" | `cmp.eq` | ma1co. Our error was cancelled by the inverted `C/D`, so 15.3 conclusions stand |
| `30/31/32/33` | ges / unsigned >= / ... / "!=0" | `cmp.ges / cmp.gtu / cmp.gts / cmp.nand`, plus `2F` = `cmp.geu` | ma1co. 15.3 thresholds re-checked and unchanged: width > 639, height > 479, level byte <= 64, sum <= 64 |
| `01`/`0D` | 16-bit load/store | `ldrsb`/`strb` (byte) | ma1co. On 0x49002: `ldrsb; uxtb; orr; strb` makes sense with bytes |
| `09` | "8/16, post-increment" | `ldrh [rs],#2` | agrees and refined: kernel coefficients are 16-bit, matching u16 in Backup |
| `1C`/`1D` | extu.w / exts.w | `uxtb` / `uxth` | ma1co (`ldrh` -> `uxth` = drop sign) |
| `F0-F5` | F0 shll, F1 shlr, F2 "left", F3 shlr+16, F4 shar | `op7`: `78` lsl, `79` lsr, `7a` asr, imm5 = `[8:4]` | ma1co. `f221` = `lsr #2`: DMA addresses in words (15.2) |
| `008r` | shlr | `asrs #1` | operand non-negative where seen; corpus cannot distinguish. Take ma1co |
| `0009`/`000a` | engine-launch wrapper | absent | gap in ma1co. In reachable code of 62 v2 images both occur exactly 39 times - one wrapper per image |

New opcodes from ma1co: `cfr/sfr` (`0001/0002`), `mov rd,fr` / `mov rd,pc` (`002r/003r`), `rlxs/rrxs` (`005r/006r`), `cmp.gts rd,#0` (`009r`), byte and halfword load/store in all modes (`02-06`, `0E-14`), `sxtb/sxth`, `adcs/sbcs/ngcs`, register `lsr/asr` (`2A/2B`), and **float: `fadd/fsub/fmul/fdiv/ftosi/fsito` (`34-39`)**.

**Corpus coverage [verified].** Recursive static control-flow walk (`code/isa/cfg.py`): entry points = stub, subprogram headers `b +0x10`, pool pointers to prologues; `bl/b rd` targets resolved from the preceding `ldr rd,[pc]`. Nothing is executed. Result: 62 v2 images, 170,915 reachable halfwords; undefined per ma1co on reachable paths: 7 (in 12 effect images), all of them inside command tables or data reached via a false entry point. **Apart from `0009/000a`, ma1co's table covers all scalar code in the corpus.**

**What changed in our conclusions:**
- 15.0 / 15.2: Soft Focus sequence is **3x3 once, then 5x5 twice**, not the reverse. Pair <-> size mapping (`0x12800/40` = 3x3, `0x12880/c0` = 5x5) unchanged.
- `0x1d10` (address translation): a tagged address `>>30 == 1` is masked `& 0xdfffffff`; others are looked up in window table `0x49e04...`. Section 6 originally had the direction reversed.
- 15.3 checks unchanged under the new disassembly (`0xeeee0001...09`).

### 15.9 `0009` command tables <-> VLIW programs on full disassembly (negative result)
- **Collection:** at calls to the `0009` wrapper the table pointer comes from `ldr r4,[pc]` near `bl`. **71 tables in 30 images** (dumped to `out/cmdtables.pkl`, not shipped). Entries `[idx:8][value:24]`; 7-bit indices take **125 values out of 0...124**. Tables of one image often start identically (`02:...`, `03:...`, `04:000400`, `04:000800`), i.e. overlapping index sets.
- **Does anything point to a VLIW program?** 8 encodings of the header `0x0000080000000000` offset within the image were tried (`off`, `off+8`, `/2`, `/4`, `/8` and combinations):
  - among 24-bit values of all 71 tables: **0 matches**;
  - among 32/16-bit literals of scalar code in 54 VLIW-bearing images: 9 scattered matches with no pattern (round numbers like `0x3200`);
  - among image descriptor fields: **0 matches**.
- **Conclusion:** no command table, scalar code or descriptor explicitly addresses the VLIW program. Most likely the module loader places the program in engine memory and the `0009` table sets parameter cells (up to 125 slots) for the already-loaded program. Hypothesis. Mapping of indices to `0x40000+` registers still not established.
- J (core 0) -> K (core 1) still not fully traced. Core 0 function `0x4c8` builds engine descriptors from byte constant tables (`0x1e18/0x1e20/0x1e28/0x1e38`) and job fields, but where kernel pointers land in K was not found.

### 15.10 Summary for "haze" experiments
- **Blur shape** is set by the kernels in Backup property `0x0003010a`: `+0x10`/`+0x30` (3x3, passes A and B) and `+0x50`/`+0x90` (5x5, A and B), u16 values. **Each kernel must sum to exactly 256**, otherwise the DSP returns `0xeeee0008/09` and the effect does not run. How that manifests on the camera (error vs skipped effect) is not known statically.
- **Strength** is three bytes per level (`+0..+8`): each <= 64, sum <= 64, else `0xeeee0004`. That the weights map to the three passes (3x3, 5x5, 5x5) with `64 - sum` going to the original is a hypothesis.
- Pass order within a launch: A then B. The 3x3 pass runs once, the 5x5 pass twice (verified from core 1 disassembly).


## 16. VLIW fourth pass: one bundle format, and a retracted mis-step (static)

A later static pass over the whole VLIW stream (tools `vl.py`, `corpus.py`, `slots.py`, `vdump.py`; corpus = NEX-3N p8 `sabin`, cross-checked against NEX-6, a6000, A7 III). It did not decode opcode semantics - that wall is unchanged (13.8/15.6: statics give shape, not meaning, without a DSP RAM dump or an SDK/ELF with symbols). Net result: the three "families" of section 13.2 are **not three formats** - there is one bundle format (the 12+4x13, bit-0-aligned A-format), and B/C are just common value-patterns of it. An intermediate hypothesis in this pass (a "+1-bit-aligned B-format with a constant tag") was **wrong and is retracted here** - recorded so it is not re-attempted.

### 16.0 What is verified
- [verified] **The minimal VLIW program is four bundles** - `f1c78f000701c000`, `f1c78f000701c3ee`, `8fffffffffffffff`, `bfffffffffffffff` - byte-identical in all five NEX-3N audio modules (`aaclcdec`, `aaclcenc_nr`, `ac3dec`, `bd_lpcmdec`, `dd51enc_nr`) and recurring across generations. An audio module that does no pixel work still carries this stub, so these particular bundles are **framing** (a two-bundle setup + a two-bundle terminator), not computation.
- [verified] **There is a single bundle alignment: bit 0** (the 12+4x13 A-format). Counting where the idle slot value `0x1f7` falls over all 44,946 non-NOP bundles in 3N p8: at **shift 0** it occurs 23,917 times spread evenly across all four 13-bit slots (5896 / 6034 / 5893 / 6094); at **shift 1** only 7,420 times and **only in the last-slot position**, zero in the other three. The last-slot shift-1 hits are an artifact: the tail value `0x3ee` equals `0x1f7 << 1`, a legitimate bit-0 slot value that merely looks like a shifted idle marker. So no second alignment exists.
- [verified] **The frequent `f1c7...` bundle (the 13.2 "family B modal", ~4800x) is an ordinary A-format compute/control bundle**, not a distinct record. Decoded at bit 0 as `op3.a5.b5` it reads cleanly, e.g. a steady-state loop body in `sa_sftfcs` (`0x2710-0x2758`) holds S0=`0xf1c`, S1=`3.24.14`, S2=`0.00.01`, S3=`7.24.13` constant while only S4 steps (`7.02.15 / .18 / .19`, `7.16.03`, `7.20.03`) - one active lane over an unrolled loop, consistent with 13.4.
- [verified] **The `8fff.../bfff...` bundle (13.2 "family C") is `7.31.31` in every slot** (all operand bits set), differing only in S0 (`0x8ff` vs `0xbff`). A uniform all-max bundle; appears as the terminator pair of the minimal program. Terminator/padding, not a separate format.
- [verified] A-format bundles form dense runs and are the compute stream (`sa_aaclcdec`: a ~1100-bundle near-pure-A program). The section-13.2 impression that A alternates with B/C markers was an `sa_sftfcs`-specific artifact and is withdrawn.

### 16.1 Retracted: the "+1-aligned B-format, tag 0x1934"
An intermediate note in this session claimed the `f1c7`-class bundles were a separate record aligned one bit higher, with a constant 11-bit tag `0x1934`. Both parts were wrong:
- The "+1 alignment" came from pre-filtering to bundles with top nibble `0xf1c`, which forces the shifted tail to `0x1f7`; the unfiltered corpus test above shows the only real alignment is bit 0.
- The "tag `0x1934`" was a value printed in **decimal** (1934 = `0x78E`) misread as hex, and it was constant only because of that same pre-filter. The leading nibble `[63:60]` actually takes all values 0-15.

Lesson: test a proposed field/alignment on the **unfiltered** corpus before naming it. The 13.2 remark that "a +1-bit shift concentrates the B field better" was measuring the same artifact and should not be pursued.

### 16.2 Standing conclusion
One VLIW bundle format (12-bit S0 + four 13-bit slots, idle `0x1f7`, bit-0 aligned). S0 is high-entropy with no clean opcode sub-field; inside each 13-bit slot the `op3.a5.b5` split is the current best guess (lane-paired, 13.4) but opcode meanings are undecoded. "Families" B and C are frequent value-patterns (a common control/loop bundle; an all-max terminator), not separate encodings. Nothing here enables writing a VLIW effect; grain stays a Linux-side job (section 11). The semantic wall still needs a DSP RAM dump taken while an effect runs, or a toolchain/ELF with symbols for this core.

## 17. VLIW fifth pass: the 13-bit slot op3 field (static)

Dug into the per-slot `op3.a5.b5` split of the one bundle format (section 16), on the unfiltered 3N p8 corpus: 42,296 non-NOP, non-terminator bundles, four 13-bit slots each. No opcode *meaning* was recovered (same wall), but op3 is validated as a real field and two of its eight values are pinned to idle/fill roles.

### 17.0 Verified
- [verified] **op3 (bits `[12:10]` of each slot) is a genuine opcode field, validated functionally.** The `(a,b)` operand distributions depend strongly on op3, even though a per-bit scan shows no fixed separator bits (the encoding is dense, every bit varies 0.34-0.84). If `[12:10]` were not a real boundary the operands would not cluster by it. Idle-type op3 values have low operand entropy (~1-3 bits); ops 1,2,4,5,6 use the full operand range (all 32 values of both `a` and `b`, entropy ~4.0-4.8) - consistent with `a`,`b` being indices into a 32-entry register file (13.4).
- [verified] **Two op3 values carry canonical idle/fill encodings:**
  - `op3=0, (a,b)=(15,23)` = 38 % of all op0 slots - this is exactly the idle slot `0x1f7`. op0 is otherwise a live opcode (the other 62 % use operands like `(31,14)`, `(0,1)`, `(8,1)`).
  - `op3=7, (a,b)=(31,31)` = 48 % of op7 slots - the all-set fill; a whole bundle of these (`7.31.31` x4) is the terminator of section 16.
- [verified] **op3=3 is a specific operation pinned to register `a=24`:** `(a,b)=(24,30)` is 57 % of all op3 slots, and within a code block `a` stays 24 while `b` steps (e.g. `sa_sftfcs` `0x26c8-0x2790`: `3.24.30 / 3.24.14 / 3.24.16 ...`). Looks like a fixed-source/accumulator op on r24; its purpose is unknown.
- [verified] **Slots have different op3 profiles** (e.g. S3 is heavy on op6/op7, S1 on op0/op3/op7), i.e. the four issue slots are heterogeneous functional units, not interchangeable lanes.
- [verified] **Cross-slot op3 coupling is moderate** (two slots share op3 36-53 % of the time; S2~S4 highest at 53 %), consistent with the lane-paired-SIMD hint in 13.4 rather than fully independent slots.

### 17.1 Tendency, not a rule
- The S0 high nibble `[63:60]` **leans toward** a slot-op pattern but does not determine it: `S0hi=f` -> `(3,0,6,0)` 32 %, `S0hi=b` -> `(7,7,7,7)` 34 %, `S0hi=1` -> `(0,0,0,0)` 25 %, but the conditional entropy of the op-pattern given the nibble is still ~5 bits. So S0 is **not** a clean template field (an earlier reading in this pass that treated it as one is not supported); it is correlated control, exact role unknown.

### 17.2 Standing gap
What each op3 computes (add / mul / mac / load / shift / ...) is still undetermined. The operand clustering gives roles (idle, fill, the r24 op, five general ops) but not arithmetic meaning. Breaking that needs a known input->output pair, i.e. a DSP RAM dump while an effect runs, or a symboled ELF/toolchain for this core - unchanged from 13.8/15.6.

## 18. Audio "Rosetta stone" feasibility (static)

Attempt to pin op3 arithmetic by matching the audio codec modules (AAC/AC3 - fully specified algorithms) to their VLIW code, without hardware.

### 18.0 What it found
- [verified] **The audio modules carry large, genuine A-bundle VLIW programs** (3N p8): `sa_aaclcdec` 1007 A-bundles, `sa_ac3dec` 1501, `sa_aaclcenc_nr` 4099 (plus the 4-bundle `[B,B,C,C]` stub each). `sa_bd_lpcmdec` has only the stub (LPCM = trivial).
- [verified] **The modules are float and do recognisable math.** Identified constant tables: `sa_ac3dec` `0xfaec` repeats `2^(-k/6)` for k=5..0 (`0.5612=2^-5/6`, `0.6300=2^-2/3`, `0.7071=2^-1/2`, `0.7937=2^-1/3`, `0.8909=2^-1/6`, `1.0`) - an AC-3 exponent/gain reconstruction table; `sa_aaclcdec` `0x18580` is a slowly rising table consistent with the AAC `x^(4/3)` inverse-quantiser. So float arithmetic and standard algorithms are present - the raw material a Rosetta approach needs.

### 18.1 Why it is not a quick win (negative results)
- The identified tables are **scalar lookup tables** (dequant / gain), not coefficients the VLIW multiplies in a recognisable loop.
- **No float cosine/twiddle table exists** in the audio modules: a scan of every `[-1,1]` float run (>=32 long) for a single-frequency cosine fit (resid < 0.05) found none in `aaclcdec`, `ac3dec`, `aaclcenc`. So the IMDCT twiddles are computed on the fly or stored in another format - there is no "find the twiddle, the next loop is the butterfly, that op3 = fmul" shortcut.
- Even with a known algorithm, linking it to a specific op3 still requires decoding **VLIW memory addressing** first (how a bundle references a data stream): float immediates do not fit in a bundle (13.0), so constants reach the datapath through engine registers, not the code.
- Whether the audio transform runs on the scalar core (which has `fadd/fmul/fdiv`) or in the VLIW is unresolved: scalar float-opcode density in the audio modules (0.08-0.27 %) is not higher than in pixel modules, so the big audio VLIW programs are plausibly the transform, but this is not proven.

### 18.2 The viable (multi-step) Rosetta chain
Still static, still safe, but several steps:
1. In a codec whose scalar setup is readable, find where the input spectrum, the coefficient/twiddle stream and the output buffer pointers are written into engine registers `0x40000+` (the scalar code is fully decodable - 13.5).
2. That labels three engine-register roles (data-in / coeff-in / data-out) for a known transform.
3. The VLIW operations that read those two streams and write the third are then the butterfly/MAC - which pins the arithmetic op3 values.
Step 1-2 are the tractable next piece; step 3 needs the VLIW addressing model, which is the same wall as before. The alternative that bypasses all of this is the on-camera harness (a known input buffer through one SA module, dump input+output - true I/O pairs), at the cost of needing the camera.

## 19. Engine memory model and what decoding op3 would take

Architecture facts (static, plus read-only observation of a running 2.6.29 BIONZ Linux via its own interfaces - no firmware modified, no flash written). This frames why op3 semantics cannot be closed statically and what the minimal missing input is.

### 19.0 Where the pixels are
- The ARM Linux runs with `mem=512M@0x80000000` but **reserves a large block for imaging**: `memrsv=448M@0x84000000` plus `memrsv=0x1270000@0x82D90000` (~19 MB). The small OS footprint lives low; the 448 MB at `0x84000000` is the imaging/DSP working DRAM - frame buffers and the engine's DMA region.
- A settings file `DmmConfig.bin` (the Dynamic Memory Manager config, ~77 KB) tabulates the pool bases as physical addresses inside that region (`0x84b80000`, `0x84c00000`, `0x85000000`, ...). So the SA engine's input/output/work buffers are ordinary ARM-physical DRAM in `0x84000000+`, not a private address space.
- The scalar-visible addresses from the module code (`0x12800`, `0x13700`, `0x40000+`, `0x48000+`, section 13-15) are the SA core's local view / MMIO aperture, distinct from these ARM-physical DRAM pools. The DSP never sees a flat pixel buffer (section 11); pixels move by DMA between `0x84000000+` DRAM and the engine.

### 19.1 The engine does not run without its RTOS
- The image pipeline (SA engine + the second-core RTOS `av-cam`) is **not up** unless `av-cam` has been started; a recovery/maintenance Linux that has multicore messaging and the Backup store up, but no imaging stack, shows the SA engine absent from the physical I/O map (not clocked/mapped). Device handles for the imaging blocks exist (`/dev/mcmn` multicore, `/dev/ldec`, `/dev/dmac`, `/dev/jet/*`) but driving them to run one SA module needs `av-cam`'s userland or a reversed ioctl ABI.
- Consequence: there is no shortcut to "run one SA module on a chosen buffer" from outside the normal firmware - the engine is configured and launched by `av-cam`, which owns the mailbox/command protocol (section 5, 13.5).

### 19.2 What would actually pin op3 arithmetic
From sections 16-18, static analysis yields the bundle format and op3 *roles* (idle, fill, the r24 op, five general ops) but not the arithmetic. The one missing input is a **known input -> known output pair for a single VLIW program**:
- Capture the engine's input and output DRAM buffers (in `0x84000000+`) around one run of a module whose transform is known (e.g. a Soft Focus convolution with a kernel we set, section 15), then differential-analyse which op3 maps to multiply/add/mac.
- This requires the engine running on controlled input - i.e. the live imaging pipeline, observed through physical memory - which is exactly the capability static-only analysis lacks.
- The audio-codec "Rosetta" alternative (section 18) is real but multi-step and has no quick float-twiddle anchor.

So the frontier is unchanged in principle (statics give shape, not meaning) but now precisely located: the engine's data path is ordinary DRAM at `0x84000000+`, and the decode needs one observed I/O pair for a known transform. (Operational details of obtaining that observation on real hardware are intentionally out of scope for this repository.)

## 20. Scalar-core emulator: engine interface mapped dynamically

Built a small interpreter for the SA-DSP scalar core (`code/isa/saemu.py`), implementing the ma1co SLEIGH semantics (all op16/op12/op8/op4/op7 forms). Pure emulation - no camera, nothing written. Validated against `__divsi3` (sftfcs main image text `0x1d90`): `divsi3(100,7)=14`, `(255,5)=51`, `(1000,33)=30`, `(-20,3)=-6` (C truncation toward zero) - the signed-division idiom executes correctly, so the interpreter is sound.

Running the Soft-Focus filter-launch (core-1 image, desc `0x2c20`, text entry `0x11e4`) with a known coefficient array and the 3x3/5x5 flag, and logging every write to engine registers `0x40000-0x4ffff`, **dynamically confirms the engine interface** (previously inferred statically in 13.5/15.2):
- **Coefficient load:** 3x3 writes **9** words to `0x40000..0x40020`; 5x5 writes **25** words to `0x40000..0x40060` - exactly the 3x3 / 5x5 kernel sizes, copied in order from the source pointer.
- **Dimension/stride registers** follow immediately: `0x40024+` (3x3) / `0x40064+` (5x5) get the padded width/height and strides from the job struct.
- **Command-table dispatch:** `run_engine` (`0009`) fires **twice per pass** (kernel A then kernel B) with `r0` = **`0x1c` then `0x98`** for the 3x3 pass and **`0x12c` then `0x1e8`** for the 5x5 pass - the exact four command-table offsets named in 13.5, now confirmed by execution.

What this buys: the scalar->engine interface for an effect is now fully and dynamically mapped (coefficient cells, dimension cells, which command table drives each pass). It does **not** decode op3 arithmetic - the emulator executes the scalar core, which only *configures and launches* the engine; the VLIW program itself runs on hardware the emulator does not model (sections 11, 19). The emulator is reusable for any module's engine setup (`saemu.py <module.bin> <desc> <entry> [--rN V]`).

## 21. Emulator maps yknr and tbox engine interfaces

Using `saemu.py` (section 20) on two more modules, with a method to separate the filter's fixed parameters from per-frame setup: run the engine-config function twice, once with an all-zero job struct and once with a job struct whose every u32 field equals its own offset, and keep the engine writes that are **identical** in both - those are input-independent (hardcoded) filter parameters.

### 21.1 yknr (luma/chroma noise reduction) - config function at text `0x1ccc`
Engine registers `0x40000+`, hardcoded (input-independent) values:
- `0x40000..0x40020` - **9 signed values**: `-8, +32, +16, +16, -2, -2, -16, -2, 0` (filter geometry / tap offsets / thresholds).
- `0x40024..0x40068` - counts/thresholds, mostly `18` and `19`.
- `0x40078..0x400e0` - a **fixed-point reciprocal (normalisation) table**: the values are `65536 * 16 / n` (`0x8000`=16/32, `0xaaab`=16/24, `0xcccd`=16/20, `0xe38e`=16/18, `0xf0f1`=16/17, ...). This is exactly the per-count normalisation a noise-reduction averager needs - divide an accumulated, max-16-weight sum by the effective sample count `n`. First concrete read of what YKNR computes at the engine level.
- `0x400f8` <- `0x3114`, `0x40100..0x40108` <- `-2, -2, +8`.

So yknr loads a fixed geometry + threshold set + a 16/n reciprocal LUT, then (per frame) strides/addresses, then launches. 5 `run_engine` sites in the module (multiple passes/planes).

### 21.2 tbox (Miniature / tilt-shift) - config function at text `0xc34`
tbox is **block-based**: it processes the frame in blocks, so the per-frame trace scales with image size (149 vs 256 `run_engine` calls at two synthetic sizes - stable structure, only the block count changes). Engine registers touched (stable across sizes):
- Param regs: `0x40030`<-`0xc`, `0x40034`<-`0x204`, `0x40038`<-`1`, `0x4003c`<-`0x800`, `0x40040`<-`0xf000`, `0x40044`<-`0xd8`, `0x40054`<-`0x2b` (hardcoded tilt/blur parameters), plus `0x40000..08`, `0x40028/2c/50/58/5c`.
- Control regs: `0x48000`<-`0x3e`, `0x48200`<-`0xfffeffff`, `0x48208`<-`0x10000`, `0x48210/18`<-`0x3e`, `0x48230`<-`1`, `0x48234`<-`0x2f00`.
- **Command-table dispatch per launch: `0x1c` (init) -> `0x68` (per block, repeated) -> `0xc4` -> `0x130`** (boundary passes).

### 21.3 Takeaway
The emulator now maps three effect modules' scalar->engine interfaces (sftfcs 20, yknr, tbox), and the zero-vs-marker method cleanly extracts each filter's **hardcoded engine parameters** - including yknr's recognisable 16/n NR-normalisation LUT. This characterises *what each filter configures*; it still does not decode the VLIW op3 arithmetic (that runs on the engine, unmodeled). Reusable for any module.

## 22. Emulator: defect, spica, apollo4, kknr, star

Five more modules through `saemu.py`. Two config styles emerged, both mappable: **hardcoded** (constant engine values, extracted by zero-vs-marker intersection) and **input-driven** (engine values read from the job struct, mapped by a marker struct where field = its own offset).

### 22.1 defect (defect-pixel correction) - hardcoded, config fn `0x1e86`
- `0x40000`<-`0x12800`, `0x40004`<-`0xf800`, `0x40008`<-`0x11000` - DSP-local buffer/table addresses (`0x12800` is the shared coefficient area used by many modules, 13.5); `0x4000c`<-`0xff`, `0x40010`<-`0x17` (threshold / count); then control regs `0x48234`<-`0x5830` and a cleared block `0x48420..0x48444`.

### 22.2 spica (lens/colour correction) - input-driven, load fn `0x5e4` (SPC_MAP image)
The engine parameters are **read per-frame from the job struct**, not hardcoded. Struct-offset -> engine-register map (word fields): `0x40014<-+0x10`, `0x40018<-+0x14`, `0x4001c<-+0x08`, `0x40020<-+0x0c`, `0x40024<-+0x24`, `0x40028<-+0x28`, `0x4002c<-+0x1c`, `0x40030<-+0x20`, `0x40038<-+0x38`, `0x4003c<-+0x3c`, `0x40040<-+0x30`, `0x40044<-+0x34`, `0x4004c<-+0x4c`, `0x40050<-+0x50`, `0x40054<-+0x44`, `0x40058<-+0x48` (plus byte fields at 0x40000/04 from struct+3/+4). SPC_MAP has six such load sites (0x5ec, 0x1864, 0x1d46, 0x2234, 0x2734, 0x2c14) - six sub-operations.

### 22.3 apollo4 - control-register only
apollo4 has **no `0x40000` coefficient aperture at all** (no literal in that range); it drives the engine purely through control registers `0x48004/20/24/30/100/160/170/174/180/188/18c/1d0/200`. It is not a coefficient-convolution filter like the others - a different class of engine job.

### 22.4 kknr (chroma NR) and star - coefficient loads are branch-gated
- **kknr** has two images (KKNR_PRE desc `0x400`, KKNR_KK1 desc `0x1d80`), each with a `0x40000` load (PRE @`0x6d2`, KK1 @`0x1d1e`) buried inside a processing loop behind conditions the synthetic harness does not satisfy; only control regs are reached cleanly (`0x48200/08/18`, PRE `0x48250`<-1). Full map needs realistic dims or branch-condition analysis.
- **star** is a large module (text ~406 KB) that uses `0x40000` across ~20 functions (from `0x42684`); its launch loop fires `run_engine` hundreds of times with command tables `0x180`, `0x1d`, `0x0`. The coefficient loads are likewise gated inside the processing loop.

### 22.5 Status
Cleanly mapped scalar->engine config for **sftfcs, yknr, tbox, defect** (hardcoded) and **spica** (input-driven struct map); **apollo4** characterised as control-only; **kknr, star** have gated coefficient loads needing realistic inputs. The emulator + zero/marker method is the reusable tool. None of this decodes the VLIW op3 arithmetic (unchanged: that executes on the engine the emulator does not model).

## 23. VLIW dataflow analysis (static) - toward op3 semantics

Attacking op3 by register dataflow on a program whose math is known: the Soft Focus blur program in `sa_sftfcs` (program @ text `0x2420`, 254 bundles) computes a 3x3/5x5 convolution (sum of coeff*pixel). Idle slots `(op0,a15,b23)` and fill `(op7,a31,b31)` are excluded.

### 23.1 Destination field resolved: dst = b (favored)
Each 13-bit slot is `op3.a5.b5` (two 5-bit register fields). Testing which field is the destination by counting ops that read a *recently produced* value (a true consumer in a dataflow):
- under **dst=b** (b=dest, a=src): op7 consumes a freshly produced value **95** times;
- under dst=a: only **31**.
The strong asymmetry favors **b = destination, a = source**. (Single-program evidence, but clear.)

### 23.2 Operation roles (from dataflow, dst=b)
- **op7** is the dominant compute op (271 active uses) and the main *consumer* of freshly produced values, writing accumulator-like registers (dest histogram top: r1, r31, r14, r5, r30). Consistent with the multiply-accumulate / main-ALU slot of a convolution.
- **op3** always has **a=24** (`3.24.xx`): it reads a fixed register r24 - a streaming source (pixel or coefficient feed).
- **op4** always has **b=19** (`4.xx.19`): it writes a fixed register r19 - a dedicated destination/accumulator.
- Source registers (a) are dominated by r31, r24, r0; destinations (b) by r1, r31, r14, r5. So the datapath cycles values through a small set of working registers with a couple of fixed-purpose ones (r24 source, r19 dest).
- op0 (with a=15) and op1/2/5/6 are lower-frequency; op-class candidates from the patent (ALU_X/Y, BSF, MOV, PACK, MPY, CMP) still map onto the eight op3 values but are not yet assigned.

### 23.3 What static analysis cannot finish
Dataflow gives field direction (dst=b) and operation *roles* (op7 main compute/accumulate, op3 = r24 source, op4 = r19 dest), but not the arithmetic identity (which op is multiply vs add vs mac). That requires fitting against a known input->output pair for this program - i.e. capturing the engine's input and output pixel buffers for a known Soft Focus kernel. The scalar emulator already maps how the kernel/dims reach the engine (sections 20-21); the remaining missing input is the pixel I/O pair, obtainable only from the running engine.

## 24. op3 decoding: the fundamental limit (conclusion)

After attacking op3 from every no-flash angle - corpus statistics (field shape, roles, 13-17), the Sony patent EP2428889 (op classes, 19), the scalar emulator (engine interface, 20-22), register dataflow (dst=b and operation roles, 23), and a DRAM-remanence capture experiment - the conclusion is a fundamental one, not a lack of effort:

- **op3 arithmetic cannot be recovered from program-level input->output.** Even a perfect I/O pair for a known transform (e.g. the Soft Focus convolution - obtainable in principle from a RAW developed by our simulator as the input and the JPEG as the output) only fixes the *net* transform, which is already known. Many different op3 assignments produce the same convolution, so the opcode semantics are not identifiable from I/O. Distinguishing multiply vs add vs mac requires observing the **per-instruction register operations during execution**.
- Instruction-level observation of the engine means running trace/dump code on the device at capture time, i.e. a firmware-partition modification (the p3/p8 boundary held throughout this project, no programmatic recovery on a single body).
- The DRAM-remanence experiment confirmed that physical DRAM survives a warm transition to the maintenance Linux and is readable via /dev/mem, but the engine's transient per-frame buffers are overwritten by continued operation before they can be dumped - and even if captured, they are program-level I/O, not an instruction trace.

**Standing result:** the VLIW is decoded as far as static analysis and no-flash observation allow - one bundle format (12+4x13, bit-0), op3 validated as a real opcode field with resolved destination (b) and operation roles (op7 main compute, op3<->r24 source, op4<->r19 dest), op-class candidates from the patent, and a complete map of the scalar->engine configuration interface. The arithmetic identity of each op3 is the one remaining unknown, and it is gated behind instruction-level tracing that requires firmware modification. This is the frontier's true location.

### 24.1 Correction - the I/O limit was overstated
The claim in 24 that op3 "cannot be recovered from program-level input->output" is **too strong and is retracted**. With the exact bundle program in hand (ops, registers, order), executing it in a simulator under different op3 semantic assignments generally yields *different* outputs, so a known input->output pair is a **strong constraint** that can pin the op semantics - potentially uniquely, given the fixed program plus the structural facts (dst=b, op roles, known kernel coefficients). An I/O pair is useful, not useless.

The real blockers are narrower:
1. **Getting the I/O pair** - shoot *with the effect active* (e.g. Soft Focus with a known kernel) so the convolution buffers actually exist, then capture them before they are overwritten (the DRAM-remanence timing problem; the earlier test shot a plain frame, so no convolution buffers existed to find).
2. **The engine execution model** - how the VLIW program iterates over pixels and how input streams into registers. Unknown, but constrainable from the per-block feeder (20-22) and the structure, and pruned hard by an I/O pair.

So op3 is **hard** without firmware, not fundamentally impossible from I/O. Firmware-level instruction tracing remains the guaranteed route, but the no-flash sim + I/O-pair approach is a legitimate avenue that was dismissed prematurely. Next concrete no-flash step: redo the remanence capture shooting *with* a known Soft Focus kernel and dumping the develop/effect pools specifically.

## 25. Data path solved + VLIW simulator (first structural pass)

Two developments.

### 25.1 The op3 data blocker is removed (service-mode live memory)
The engine's input/output buffers can be read from a running camera via the service-mode memory interface (no firmware write; reversible). Operationally: a baseline memory dump, a controlled capture, a second dump, and a diff localise the capture buffers. On this unit the develop/preview image buffer is a **1280-byte-stride raster** (found by autocorrelation; the scene renders correctly at width 1280). A Soft Focus shot and an effect-off shot of the same target give an image-level input/output pair. (Acquisition specifics are kept out of this repo; the point for the ISA work is that an I/O pair is now obtainable.)
- Caveat: an **image-level** pair only fixes the net transform (a convolution with the known kernel); it does not by itself expose op3. It is useful as a *fit target* for a simulator, and stronger constraints would come from reading the engine's intermediate register state.

### 25.2 Symbolic VLIW simulator (`code/isa/vengine.py`)
A symbolic simulator runs the Soft Focus bundle program (program @ text `0x2420`) with a pluggable op3->operation mapping and measures whether the output registers form a convolution-shaped expression (a sum of products of register leaves). Slot model: dst=b, src=a (23.1); idle `(0,15,23)` and fill `(7,31,31)` skipped.

First pass result (**hypothesis, not proof**): assuming op0/op3 = MOV and op7 = ADD (accumulate), the search prefers **op1/op2/op4 = MUL**, and then the fixed-destination register **r19** (op4's dest, 22/23) ends as a **9-leaf sum of products** (31 MUL / 23 ADD) - exactly the shape of a 3x3 convolution (9 taps); r1 is similarly an 8-leaf sum of products. So a self-consistent reading is: **op7 = accumulate (ADD), op1/op2/op4 = multiply, r19/r1 = convolution accumulators**.

**Caveats (important):** this is heuristic, not a decode. (1) The score rewards MUL+ADD counts, so it is biased toward that structure. (2) op7=ADD and op3=MOV were *assumed*; only op1/op2/op4=MUL was searched. (3) The execution model (what the registers hold at program start - which leaves are coefficients vs pixels) is unconfirmed. (4) The 2-operand/dst=b reading is assumed. Real validation needs a numeric run of the program against the captured sharp->blurred pair (requiring the execution model) and/or the engine's intermediate register state. The simulator is the framework to do that fit; this pass only shows the convolution hypothesis is structurally consistent.

### 25.3 Numeric run attempt -> the observability wall (honest conclusion)
Taking the simulator toward a numeric run against the captured sharp->blurred pair exposed a hard limit, documented here so it is not re-attempted blindly.
- The active-core **dataflow is software-pipelined with register rotation**, not a transparent 9-tap MAC. Trace (dst=b<=op(a), src origin): `op0 rX<=r15` recurs (r15 behaves like a zero/clear source); `op7 r5<=r6/r8/r10[in]` (accumulate-ish into r5 from several input regs); `op4 r19<=r10/r6/...` with `op2 r7<=r19` and `op2 r1<=r19` rotating r19 through r7/r1 - a pipeline, not 9 visible taps. The naive 2-operand model produces nested products (31 MUL for r19), confirming the model is incomplete (the MAC must use temporaries/rotation the static read does not pin).
- To run numerically we need the exact **execution model** (which registers hold which pixels/coefficients at program start, plus the pipeline semantics). This is **not recoverable statically** from the bundles, and the **image-level I/O pair cannot resolve it** (it only fixes the net transform = the known convolution).
- The one observable that would resolve it - the engine's **internal register/intermediate state** - lives in **DSP-local address space (0x40000+/0x48000+), which is not mapped into ARM physical memory** (absent from ARM `/proc/iomem`), so it is **not readable** via `/dev/mem` or service-mode `readMemory` (both read ARM physical). The accessible observable (DRAM buffers) is image-level only.

**Conclusion:** op3 numeric decode is **not achievable with the available observables** - not for lack of effort, but because the needed observation (engine-internal state) is not ARM-addressable and the image-level observable is insufficient to disambiguate the pipelined VLIW. The rigorous ceiling is the structural hypothesis (op7 = accumulate, op1/op2/op4 = multiply, r19/r1 = accumulators), which is consistent but unproven. `vengine.py` remains ready should engine-internal state ever become observable (e.g. a hardware debug port or a DSP-side dump).
