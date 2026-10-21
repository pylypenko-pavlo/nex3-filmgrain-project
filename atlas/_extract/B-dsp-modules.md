# B-dsp-modules: extraction for area B (SA-DSP, SA modules, idt_cam)

Working material, not authoritative. Temporary IDs `B-<AREA>-<NNN>` (areas used: `DSP`, `MOD`, `IDT`); the merge step assigns final `C-` IDs.
Extracted 2026-10-09. Static work only: nothing was written to or run on the camera.

## 0. Method and conventions

- Sources read in full: `WorkPersonal/reference/{sony-dsp-isa,sony-dsp-generations,nex3n-sa-interface,sony-hack-prior-art,nex3n-symbols-and-names}.md`, `nex3n-research/notes/dsp-grain-campaign.md` (section 7 of 09.10 takes precedence over sections 3-5), plus the newer English `nex3n-research/notes/sony-dsp-isa.md` (it has sections 19-25 that the WorkPersonal copy lacks), `notes/sa-interface.md` (spot checks), the p8 `kemco.txt`, and `<scratch>`.
- Re-checked against data on 2026-10-09 (these claims carry status `verified-code`): module headers, descriptors and trailers of every file in p8 and p3 `sabin/`; VLIW header/NOP counts; the Backup `0x00bd000x` tables in `work/sai/bk_post.txt`; the `ExecuteOpenMSG` call sites in `av-cam.bin`; strings in `av-cam.bin`; the idt_cam stub signature, overlay table and disassembly in `/tmp/claude-501/ov/`.
- Not re-checked: anything that depends on the on-camera experiments, on `sadis.py` semantics of individual opcodes, on the emulator (`saemu.py`) runs, or on av-cam disassembly beyond the call-site scan. Per the atlas rule these are recorded as `hypothesis` and the evidence line says "note states verified-code; not re-checked" where the note claimed more.
- Addresses: idt_cam values are **file offsets inside `idt_cam.bin`** (not the inner p3 offset `0x980e00`) unless prefixed "link". Module `+0x..` offsets are file offsets. av-cam addresses are file offsets in `av-cam.bin` (VA = `0xc3441000` + offset).
- "Mine" = the figure was recomputed from the data in this pass. Scratch scripts: `gen.py`, `gen2.py` (in the session scratchpad, not shipped).

## 1. Claims

### 1.1 Area DSP: container format, ISA, VLIW, engine, generations

### B-DSP-001: Every p8 `sa_*.bin` (32 files) and p3 `sa_dfdet.bin` starts with magic `aa0a1391`, has a u16 container version at +4 (1 for codec/zima/avc modules, 2 for processing modules and jpeg), a 12-byte tag at +0x14, and ends with a sum32le trailer that equals the sum of all preceding u32 words
- status: verified-code
- evidence: header scan of all 33 files (`gen.py`); 33/33 sum32 trailers valid; container version 1 = 12 files (aaclcdec, aaclcenc_nr, ac3dec, dd51enc_nr, bd_lpcmdec, avce x2, avcd x2, zima x3), version 2 = 20 files (the 16 processing modules and the four `sa_jpeg_*`)
- source: sony-dsp-isa.md section 1; sony-dsp-generations.md "Формат SA-модуля"
- date: 2026-10-09
- relates: B-DSP-002, B-DSP-004

### B-DSP-002: Byte +9 of the container header is the codectype and byte +8 is a class (00 = processing/effect module, 01 = codec); there are 16 processing and 16 codec modules in p8
- status: verified-code
- evidence: catalog columns "class" and "codectype"; processing: apollo4 01, dfdet 02, sweep_panorama 0a, kknr 0f, bdro2_bdex 10, fc_recog 13, defect 14, frc2 15, spica 16, tbox 17, sftfcs 18, pbe_work 19, star 1a, yknr 1c, shapep 21, test_intr_c0a 28; codec: avce 0xc0/c1, avcd 0xc8/c9, aac/ac3/dd51/lpcm 0xd3-d8, jpeg enc/dec 0xe0/e1/e8/e9, zima 0xf0-f2
- source: sony-dsp-generations.md table "+8 ID модуля"
- date: 2026-10-09
- relates: B-MOD-006 (byte +9 equals `ref` of the `0x00bd0002` map, 32/32)

### B-DSP-003: The image table at +0x30 lists only the primary image(s) of a module; per-core images exist beyond it and are found only by scanning for descriptors `3d 00 xx b0 42 VV`
- status: verified-code
- evidence: table entries vs scan hits: sftfcs 1 vs 3 (0x100, 0x2c20, 0x6cc0), tbox 1 vs 4, star 1 vs 9, yknr 1 vs 4, frc2 1 vs 3, kknr 2 vs 5, apollo4 2 entries (same offset 0x200 twice) vs 7, dfdet 2 vs 8, bdro2_bdex 2 vs 3, spica 2 vs 3; descriptor `w[2]` carries a core index in bits 8..15 (sftfcs 0x80002, 0x102, 0x202; tbox 0x80005, 0x105, 0x205, 0x305; star 0x80002, 0x10102 ... 0x10802)
- source: sony-dsp-isa.md section 1 and 13.1 (the notes name the extra images but do not say the table omits them)
- date: 2026-10-09
- relates: B-DSP-004, B-MOD-024

### B-DSP-004: The descriptor version byte `VV` (desc+5) is 0x32 for most 3N modules, 0x31 for the four `sa_jpeg_*`, `sa_fc_recog` and `sa_test_intr_c0a`, and 0x34 for `idt_cam.bin` alone
- status: verified-code
- evidence: descriptor dump of all files (`VV` column in catalog); `ssboot.bin`/`ssboot_any.bin`/`sa_dfdet` = 0x32. The generations note gives 0x34 as the CXD90014 value, so `idt_cam` on the 3N carries the later descriptor version
- source: sony-dsp-generations.md ("Версия дескриптора VV: 0x32 (jpeg 0x31) / 0x34"); dsp-grain-campaign.md section 3 ("v4 SA descriptor")
- date: 2026-10-09
- relates: B-IDT-004, B-DSP-025

### B-DSP-005: In a v2 descriptor `w[4]` is the code base (link address 0, entry at +8), `w[5]` the end of the loadable image, `w[11]` is 0x682 in every module
- status: hypothesis
- evidence: note: literal-pool pointers hit prologues exactly with base `w[4]` (sftfcs 12/25, tbox 9/46, defect 14/103; 0 with `w[12]`). `w[11]` = 0x682 re-checked on all 86 descriptors found by pattern scan in p8 and p3 `sabin/` (0 exceptions). Base/entry semantics not re-checked
- source: sony-dsp-isa.md section 1
- date: 2026-10-06
- relates: B-DSP-006

### B-DSP-006: A module text begins with zeros, an entry stub (`sp`, `r14`, `r1` loaded from literals; `jsr` init; `jmp` main), then a table of u32 `id<<24 | value` entries (id 2..0x55) passed to a function as data; the vector table at +0x7c (24 entries, all 0x76) does not point to code
- status: hypothesis
- evidence: note states verified-code (sftfcs map in section 6: stub at 0x008, config table 0x01c-0x193); not re-checked
- source: sony-dsp-isa.md sections 1 and 6
- date: 2026-10-05
- relates: B-DSP-005

### B-DSP-007: The scalar core is a proprietary 16-bit little-endian RISC with 16 registers (r15 = SP, args r4-r7, return r0, callee-saved r8-r15), no delay slots, PC-relative literals (`5iiN` = ldr, `4ddN` = ldrh), and its instruction table matches ma1co's SA-DSP SLEIGH spec; ma1co's table covers all scalar code reachable in the 3N corpus except `0009`/`000a`
- status: hypothesis
- evidence: independent external spec (github.com/ma1co/SA-DSP, commit 322bc4a, 09.08.2021) agrees with the 3N-derived fingerprints; note reports a recursive static walk (`cfg.py`): 62 v2 images, 170,915 reachable halfwords, 7 undefined, all in command tables or data. Walk not re-run. In this pass the `/tmp/claude-501/ov/` disassembly (sadis.py by ma1co table) decodes all 35 idt_cam overlay stubs cleanly (`ldr sp; ldr r14; ldr r1; bl r1; ...; wfi; b`)
- source: sony-dsp-isa.md sections 2, 14, 15.8; sony-hack-prior-art.md section 3
- date: 2026-10-06
- relates: B-DSP-008, B-DSP-009

### B-DSP-008: The first-pass reading of `C`/`D` opcodes as `bf`/`bt`, `2E` as "not equal", `01`/`0D` as 16-bit load/store and `008r` as logical shift right was wrong
- status: refuted
- evidence: sftfcs `0x1ba8`: `add r0,#2; cmp.eq r0,#18; bfc back` sums exactly 9 halfwords under ma1co semantics (`C` = `bfs`, `D` = `bfc`); `01`/`0D` = `ldrsb`/`strb` per ma1co and the 0x49002 sequence. Replaced by the ma1co table
- source: sony-dsp-isa.md section 15.8
- date: 2026-10-06
- relates: supersedes the opcode table of the WorkPersonal copy section 2; supports B-DSP-007

### B-DSP-009: Instruction `0009` starts the engine with `r0` pointing at a command table (called `run_engine` in the disassembler); `000a` is a sibling; both are absent from ma1co's spec and occur once per image wrapper (39 images)
- status: hypothesis
- evidence: structural only (wrapper = save r8-r14/lr; `mov r0,r4`; `0009`; restore). Re-check: raw `0009` halfwords in idt_cam overlays: 0x105d0 has 2, 0x2af60 has 5, 0xcbd0 2, 0x22460 3 (upper bounds; data can mimic). Emulator log (note section 20) showed `0009` firing twice per pass with r0 = 0x1c/0x98 (3x3) and 0x12c/0x1e8 (5x5); not re-run
- source: sony-dsp-isa.md sections 0, 13.5, 15.8, 20
- date: 2026-10-06
- relates: B-DSP-021

### B-DSP-010: The VLIW NOP bundle `0x1f70fb87dc3ee1f7` equals `0x1f7` in each of five slots, one 12-bit slot S0 `[63:52]` plus four 13-bit slots S1..S4
- status: verified-code
- evidence: bit arithmetic on the NOP constant (mine): `(x>>52)&0xfff`, `(x>>39)&0x1fff`, `(x>>26)&0x1fff`, `(x>>13)&0x1fff`, `x&0x1fff` all give `0x1f7`. The note's statistical derivation of the slot boundaries is not re-run
- source: sony-dsp-isa.md section 13.0, 13.3
- date: 2026-10-09
- relates: B-DSP-012, B-DSP-014

### B-DSP-011: A VLIW program starts with the qword `0x0000080000000000` immediately followed by a NOP bundle; the p8 corpus has 189 such programs
- status: verified-code
- evidence: scan of all p8 `sa_*.bin` for 8-aligned header+NOP pairs gives exactly 189 (mine; per-module counts in the catalog column "VLIW programs"; 195 raw header matches if alignment and NOP are not required). Program length measured as bundles to the first zero qword: sftfcs 255/369/321 incl. header (note: 254/368/320 excluding it), tbox 387/174/255/375/375
- source: sony-dsp-isa.md section 13.0, 13.1
- date: 2026-10-09
- relates: B-IDT-006

### B-DSP-012: There is one bundle format (12+4x13 bits, bit-0 aligned); the earlier "families B and C" and the "+1-bit shifted format with tag 0x1934" are not separate formats
- status: hypothesis
- evidence: note section 16 (re-done on unfiltered corpus; "0x1934" was decimal 0x78E, an artefact of filtering). Not re-run. Supersedes the three-family table in section 13.2
- source: sony-dsp-isa.md sections 13.2 (old), 16.0-16.2
- date: 2026-10-06
- relates: B-DSP-013

### B-DSP-013: The first-pass bundle model "four 16-bit lanes" and the section 13.2 families B (modal bundle `0xf1c78f000701c3ee`) and C (almost all ones) as distinct encodings
- status: refuted
- evidence: section 16: modal bundle is an ordinary A-bundle (loop body in sftfcs `0x2710-0x2758`), `8fff/bfff` bundles are a terminator (`7.31.31` in all slots), minimal empty program = 4 bundles identical in all five audio modules
- source: sony-dsp-isa.md section 10 (old), 13.2, 16
- date: 2026-10-06
- relates: superseded by B-DSP-012

### B-DSP-014: Slot layout `op3.a5.b5` with op3 a real opcode field; op0 = (a15, b23) is the idle slot, op7 = (a31, b31) is fill/terminator, op3 always reads r24, op4 always writes r19; destination is `b`, source `a` (favoured 95 vs 31 on one program)
- status: hypothesis
- evidence: note sections 17 and 23 (42,296 bundles; dataflow on the sftfcs blur program at text `0x2420`). Statistical, single-program evidence for dst = b. Not re-run
- source: sony-dsp-isa.md sections 13.4, 17, 23
- date: 2026-10-06
- relates: B-DSP-015, B-DSP-010

### B-DSP-015: The arithmetic meaning of each op3 value is unknown; a symbolic simulator reading (op7 = accumulate, op1/op2/op4 = multiply, r19/r1 = convolution accumulators) is consistent but unproven
- status: unknown
- evidence: note section 25.2-25.3: simulator `vengine.py` gives a 9-leaf sum of products in r19; the pipeline uses register rotation; engine-internal state is DSP-local (0x40000+/0x48000+) and not ARM-addressable, so image-level I/O pairs do not disambiguate. The earlier "cannot be recovered from I/O" (section 24) was retracted in 24.1
- source: sony-dsp-isa.md sections 24, 24.1, 25
- date: 2026-10-07
- relates: B-DSP-014

### B-DSP-016: VLIW bundles are byte-identical across generations (CXD4132 = CXD90014 = CXD90045)
- status: hypothesis
- evidence: note: windows +-16 bundles around each NOP agree in 6 of 6 compared modules; 90014 vs 90045 module bodies are byte-identical (tbox, sftfcs, star, frc2, defect, lfnr, nlap, motionshot). Not re-run (needs the other firmwares in `sonygen/`)
- source: sony-dsp-isa.md 13.0; sony-dsp-generations.md "Похожесть модулей"
- date: 2026-10-06
- relates: B-DSP-024

### B-DSP-017: Modules with no VLIW program at all are `sa_shapep`, the three `sa_zima_startup_*` and `sa_test_intr_c0a`; every other p8 module has at least one program
- status: verified-code
- evidence: aligned header+NOP count = 0 for those five and >= 1 for the other 27 (catalog column); `sa_test_intr_c0a` has one odd-aligned false header match and 0 NOP bundles. `sa_bd_lpcmdec`, `sa_jpeg_dec_*`, `sa_jpeg_enc_1core` have exactly 1
- source: sony-dsp-isa.md section 11
- date: 2026-10-09
- relates: B-DSP-018, B-DSP-020

### B-DSP-018: `sa_frc2` and `sa_star` have no VLIW programs
- status: refuted
- evidence: frc2 has 5 programs and star 10 (mine); the original check looked only at the first image. Note corrected itself in section 11
- source: sony-dsp-isa.md section 11 (old text)
- date: 2026-10-09
- relates: supersedes the first version of B-DSP-017

### B-DSP-019: The scalar launch function of an effect moves 9 (3x3) or 25 (5x5) 16-bit coefficients into engine registers `0x40000..0x40020` / `0x40000..0x40060`, then the dimension/stride registers (`0x40024+` / `0x40064+`), then calls `0009`; the engine register layout differs per program (yknr `0x40000..0x40028, 0x40038, 0x40100`; tbox `0x40000..0x40008, 0x40028..0x400c8`; spica reads 16 fields from the job struct; apollo4 has no 0x40000 literal)
- status: hypothesis
- evidence: static reading (section 13.5) plus `saemu.py` runs (sections 20-22) that logged the writes; not re-run. Re-check: `0x40000..0x401ff` literals appear in idt_cam overlays 0x8fd0 (46 distinct), 0xcbd0 (19), 0x105d0 (7), 0x2af60, 0x1f2d0 (10 each)
- source: sony-dsp-isa.md sections 13.5, 20, 21, 22
- date: 2026-10-07
- relates: B-DSP-009, B-MOD-021, B-MOD-024, B-MOD-026, B-MOD-027

### B-DSP-020: The scalar core never touches pixels; no module has a per-pixel scalar loop over a frame buffer; pixels move by DMA between external DRAM (`0x84000000+` pools, per `DmmConfig.bin`) and the engine, and the DSP-local view (`0x12800`, `0x13700`, `0x40000+`, `0x48000+`) is not mapped in ARM physical memory
- status: hypothesis
- evidence: note section 11 (literal survey: scalar code addresses only MMIO 0x48000-0x49xxx and 0x40000+), section 19 (DmmConfig pools, `/proc/iomem`, remanence test), 25.3. Re-check partial: the five VLIW-free modules contain no frame-sized loop is not re-verified. idt_cam overlays also contain scalar code that was not classified for per-pixel loops
- source: sony-dsp-isa.md sections 0.2, 11, 19, 25.3; dsp-grain-campaign.md section 2
- date: 2026-10-07
- relates: B-IDT-013

### B-DSP-021: Command tables referenced by `0009` are arrays of u32 `[idx:8][value:24]` (71 tables in 30 images, indices fill 125 values of 0..124) and nothing (tables, scalar literals, descriptor fields) addresses the VLIW program explicitly
- status: hypothesis
- evidence: negative result of section 15.9 (8 encodings of the header offset searched: 0 hits in tables, 9 unsystematic hits in literals, 0 in descriptors); not re-run. Probable reading: the loader places the VLIW program, the table sets parameter cells
- source: sony-dsp-isa.md sections 13.5, 15.5, 15.9
- date: 2026-10-06
- relates: B-DSP-009

### B-DSP-022: Area `0x12800..0x128ff` of DSP-local memory is a common parameter block referenced by almost all modules (tbox, yknr, kknr, star, defect, pbe_work, dfdet, apollo4, avce)
- status: hypothesis
- evidence: literal-reference survey in the note (sftfcs does not write it; defect sets `0x40000 <- 0x12800`); not re-run
- source: sony-dsp-isa.md section 13.5, 22.1
- date: 2026-10-06
- relates: B-MOD-021

### B-DSP-023: JPEG zigzag, quantisation and Huffman tables live in `av-cam.bin` (zigzag at 0x5f0d8c, quant in zigzag order at 0x54afb2, DC Huffman at 0x54aa41), not in `sa_jpeg_*`; the SA JPEG modules drive a hardware coder
- status: hypothesis
- evidence: note section 4 (searched `sa_jpeg_enc/dec_*` for the standard tables and DCT cosines: none). Not re-run. Zigzag appears only in `sa_avcd_*_zma` (0x37a0 / 0x58a0)
- source: sony-dsp-isa.md section 4
- date: 2026-10-05
- relates: B-MOD-030

### B-DSP-024: The scalar ISA, entry-stub crt0 and DSP-local memory map are the same on CXD4132, CXD90014 and CXD90045
- status: hypothesis
- evidence: 80-93 % shared 16-byte shingles for same-named modules (3N vs a6000), same crt0 bytes `0f90 cdaf 8e95 de1e eb60`, same MMIO map (0x48000/0x48200/0x48100/0x48160/0x49d00/0x481c0/0x48c08). Not re-run (other firmwares not opened in this pass)
- source: sony-dsp-generations.md section 0 and "Формат SA-модуля"
- date: 2026-10-04
- relates: B-DSP-016, B-DSP-025

### B-DSP-025: Container version is 2 on CXD4132, 4 on CXD90014 and 5 on CXD90045 (codecs 1 on 4132), descriptor version 0x32 vs 0x34, vector count 24 / 54 / 60, core mask low byte 0x01-0x08 vs 0x0f / 0x1f
- status: hypothesis
- evidence: 3N half re-checked (container ver 1/2; VV 0x31/0x32; container +0x0c = 0x1xxxx observed, low u16 in {1,2,3,4,8}); the 90014/90045 half is from the note only. The meaning of container `+0x0c` (core mask?) is not established: observed values 0x10001, 0x10002, 0x10003, 0x10004, 0x10008, 0x20001, 0x20008, 0x30001, 0x50001, 0x80001
- source: sony-dsp-generations.md section "Формат SA-модуля", hypotheses list
- date: 2026-10-09
- relates: B-DSP-004, B-DSP-024

### B-DSP-026: Between CXD4132 and CXD90014 the DSP runtime/ABI was rebuilt (same-named module bodies match only 0.83-0.93), between CXD90014 and CXD90045 it was not (bodies byte-identical except the header)
- status: hypothesis
- evidence: shingle similarity table in the note (tbox 0.93, sftfcs 0.83, star 0.84, frc2 0.88, defect 0.90, kknr 0.79, jpeg_enc_1core 0.05, shapep 0.23, apollo4 vs apollo 0.22). Not re-run
- source: sony-dsp-generations.md "Похожесть модулей"
- date: 2026-10-04
- relates: B-DSP-024

### B-DSP-027: NEX-6 and 3N share 28 of 32 common modules byte-for-byte (including pbe_work, tbox, sftfcs, star, apollo4); NEX-6 has nothing the 3N lacks except `apollo4_es10`, `zhitomi`, `zphdefdet`
- status: hypothesis
- evidence: note comparison of `out3n` vs NEX-6 1.03 unpack; not re-run
- source: sony-dsp-generations.md "Похожесть модулей"
- date: 2026-10-04
- relates: C1 in section 4 (the grain note says NEX-6 has separate NR/JPEG/SF modules the 3N lacks)

### B-DSP-028: No newer-generation module is a picture effect absent from the 3N; the modules the 3N lacks (nlap, smod, motionshot, replacer, cecil, dcv, lfnr, bayes_tracker, zphdefdet, zoom_nr, seg, drt/udrt, dtcf, staple, aed, aes_sha2, pcmcc, rotate90, fec_enc32) are tracking, NR, lens correction, segmentation, audio or crypto
- status: hypothesis
- evidence: judged from names and strings only (note). `nlap` as a separate contour-filter module whose 3N parameters travel inside `PBEH` to `sa_pbe_work` is explicitly a guess
- source: sony-dsp-generations.md "Чего у 3N нет"
- date: 2026-10-04
- relates: B-MOD-025

### B-DSP-029: Transplanting a newer-generation module into the 3N is not feasible without hardware debugging, and whether the 3N loader rejects a v4/v5 header is not known
- status: unknown
- evidence: note: av-cam never sees the file (see B-MOD-004), no header-field check found in av-cam; magic literal `0x412dc` is a message-object tag, not a header check
- source: sony-dsp-generations.md "Загрузчик (ARM-сторона)", section 0
- date: 2026-10-04
- relates: B-MOD-011

### B-DSP-030: Public prior art covers only the scalar core (ma1co/SA-DSP Ghidra plugin, ~90 opcodes incl. float ops; no VLIW); ma1co/qemu has CXD4132 but does not emulate the SA-DSP or ISP; no leaked SDK, symbols or talks for SA-DSP were found
- status: hypothesis
- evidence: search log of 05.10.2026 (GitHub API, Wayback, forums); not re-run
- source: sony-hack-prior-art.md sections 0, 3, 6
- date: 2026-10-05
- relates: B-DSP-007

### B-DSP-031: The Creative Look firmware of the a7 IV (CXD90057) cannot be unpacked with the keys in fwtool master; PR #52 (open) publishes two AES keys that would allow it, not tried
- status: unknown
- evidence: generations note says `No decrypter found`; prior-art/symbols notes say PR #52 contains the keys. The two notes disagree on whether keys are available (see C8); no attempt recorded
- source: sony-dsp-generations.md (table row 7M4); sony-hack-prior-art.md section 3; nex3n-symbols-and-names.md section 5
- date: 2026-10-05
- relates: none

### 1.2 Area MOD: SA modules, av-cam interface, Backup tables, file inventory

### B-MOD-001: p8 `sabin/` holds 52 files: 32 `sa_*.bin` modules and 20 raw `spica_*_tap_step*.bin` tables; p3 `sabin/` holds 4 files (`idt_cam.bin`, `sa_dfdet.bin`, `ssboot.bin`, `ssboot_any.bin`); `sa_dfdet.bin` in p3 and p8 is the same file; there are 35 distinct DSP binaries
- status: verified-code
- evidence: directory listings under `safeboot/out3n/nflasha{8,3}_unpacked_unpacked/sabin/`; md5 of both `sa_dfdet.bin` = `121522c4...`; 32 + idt_cam + ssboot + ssboot_any = 35. Whole-file md5 prefixes in catalog
- source: nex3n-sa-interface.md section 5 ("sa_dfdet duplicate"); dsp-grain-campaign.md section 3 (p3 contents)
- date: 2026-10-09
- relates: B-MOD-017

### B-MOD-002: The tap tables are raw 38,400-byte files without container, header or trailer; of 20 files only 12 contents are distinct: `still` = `zoom` for all four (c/y x step1/step2), `apsp` step1 = step2 and `dualrec` step1 = step2 for both c and y, the four `magnifier_plus` are all different
- status: verified-code
- evidence: md5 of all 20 (mine): e.g. `spica_still_c_tap_step1` = `spica_zoom_c_tap_step1` = 22016228...; `apsp_c` step1 = step2 = 52662d2d...; `dualrec_y` step1 = step2 = af36d8e6...; magnifier hashes 3b3be7ae, 4ae84c4f, aa9509c4, b324b95e. They have no container, so the header/sum32 checks do not apply
- source: none (new derived fact); consistent with nex3n-sa-interface.md section 1.2 (owner 0xb6 tables)
- date: 2026-10-09
- relates: B-MOD-014

### B-MOD-003: `av-cam.bin` contains 20 call sites of `SaFuncDrvCmn::ExecuteOpenMSG` (function at file 0x314340) that pass a constant codectype: 0x01, 0x03, 0x04, 0x05, 0x06, 0x07, 0x0b, 0x0d, 0x0e, 0x0f, 0x10, 0x11, 0x16, 0x17, 0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1e; codectype 0x0a (sweep_panorama) is opened by a separate builder at 0x4dc16e
- status: verified-code
- evidence: BL table of `avx.py` (cache `litref.pkl`): 20 callers of 0x314340 at 0x1617c2, 0x161e32, 0x1626e6, 0x162eca, 0x163604, 0x38098c, 0x380f7e, 0x38191a, 0x3822c6, 0x382d86, 0x434dd6, 0x4355ea, 0x435af6, 0x436286, 0x4368ea, 0x4370ca, 0x43764e, 0x4ad66a, 0x4addfa, 0x4ae5be; the codectype read by a back-scan for `movs r2,#imm` within 60 bytes gives exactly the list above (mine, heuristic). The 0x4dc16e builder is from the note only
- source: nex3n-sa-interface.md section 1.1
- date: 2026-10-09
- relates: B-MOD-013, B-MOD-014

### B-MOD-004: The OPEN request carries only a codectype: message word [9] = 0x21 (OPEN), [8] = 0x14 (length), [0x11] = codectype, reply 0x22; there is no path, file-id or BKID in the message, and the code that answers OPEN (and loads the file) is not in av-cam
- status: hypothesis
- evidence: note: reading of `ExecuteOpenMSG` (0x314340); av-cam strings confirm the class and signature `ExecuteOpenMSG(unsigned char *, unsigned char)`, also `ExecuteCalcStartMSG`, `ExecuteCloseMSG` and `FUNCID_SA_LOAD`/`FUNCID_CORE_SA_LOAD ... codectype = %x` log strings (audio managers). Message layout and absence of a 0x22 builder not re-checked
- source: nex3n-sa-interface.md section 1.1
- date: 2026-10-05
- relates: B-MOD-009, B-MOD-010

### B-MOD-005: `av-cam.bin` carries `sa_func_*` wrapper strings for BDEX, BFNR, BOKS, CONTP, DCV, GOLFSHOT, KDZ, KKNR, LAXO, NFLASH, PBE, SFTFCS, SPICA, STAR, TBOX, YKNR (acquire/start/release/exit/preinit/init variants), `*_START_PARAM` types for BAYER, BDEX, BFNR, BGEST, BOKS, CLEARVID, GOLFSHOT, KDZ, KKNR, PBE, SPICA, SSP, STAR, YKNR, and `*_start_mbx.cha_mbx0..3` log strings for bdex, bfnr, boks, contp, dcv, DUALREC_BAYER, DUALREC_CLEARVID, kdz, laxo, pbe, sftfcs, spica, star, tbox; there are no such strings for apollo4, defect, frc2, shapep, fc_recog, dfdet, test_intr, bdro2 (other than BDEX), sweep_panorama
- status: verified-code
- evidence: `strings av-cam.bin` with regexes `sa_func_[A-Za-z0-9]+_[a-z]+`, `[A-Za-z0-9]+_START_PARAM`, `[A-Za-z0-9_]+_start_mbx.cha_mbx0` (mine). yknr has `sa_func_YKNR_*` and `YKNR_START_PARAM` but no `yknr_start_mbx` string
- source: sony-dsp-generations.md "Загрузчик" (wrapper list, 18 for 3N); sony-dsp-isa.md section 5 (mbx strings)
- date: 2026-10-09
- relates: B-MOD-003

### B-MOD-006: Backup property `0x00bd0002` (800 B = 100 x `[u16 file-id][u16 owner][u16 ref][u16 x]`) maps codectype to file-id: for owner 0x93 the `ref` field equals byte +9 of the module header for all 32 `sa_*.bin` present in p8; 60 entries have owner 0x93: 32 have a file in p8, 27 name a file absent from 3N flash, and one (file-id 78, ref 0xc4) has an empty name slot
- status: verified-code
- evidence: parsed `work/sai/bk_post.txt` (BKIDs `00bd0000`..`00bd0007`) and compared with p8 headers (mine): 32/32 match, 0 mismatches; the 27 absent names are sa_camdsp_clearvid (ref 3), camdsp_bayer (4), dcv (5), one_shot_3d (6), kdz (7), pbe (8), dm_af_dirdet (9), nflash (0xc), boks (0xd), ssp (0xe), bfnr (0xb), contplus (0x11), deblurring (0x12), nflash2 (0x1b), dm_af_movie (0x1d), ddt (0x1e), zphdefdet (0x1f), zhitomi (0x20) and 9 codecs (mpeg2e/mpeg2d/dd51enc/aaclcenc/bd_lpcmenc/mp3dec/ac3enc_ac3dec/linear_phase). Other owners: 0xb6 (17 entries: dcv_psf_table + 16 spica taps with ref 0x10..0x1f), 0xbf (3: startsound, logo, wireless_power_logo), 0x69 (3 `*_MAGIC.bin`), 0x13b (psd.bin, dfe/dfe.bin), 0x3 (2 `DSC0000x.ARW`), 0xd (LensAberrationData), 0xd1 (sanmon_input), 11 empty (0xffff)
- source: nex3n-sa-interface.md section 1.2
- date: 2026-10-09
- relates: B-DSP-002, B-MOD-007

### B-MOD-007: Backup `0x00bd0000` is a table of 100 x 32-byte base file names with 88 non-empty slots (empty: 70, 78-80, 92-99); file-id equals the slot index (kknr 44, defect 51, frc2 52, spica 53, tbox 54, sftfcs 55, pbe_work 71, star 72, yknr 74, shapep 91, jpeg_enc 15/16, apollo4 23, dfdet 24, test_intr_c0a 37); `0x00bd0006` is identical except slot 23 (`sa_apollo4_es10.bin`)
- status: verified-code
- evidence: parsed table (mine). The WorkPersonal copy of the ISA note says "86 base names" in section 0-bis; the table has 88 (see C6). Its section 9 byte offsets (kknr 0x580, sftfcs 0x6e0, yknr 0x940, shapep 0xb60) match 32 x file-id
- source: sony-dsp-isa.md section 0-bis and 9; nex3n-sa-interface.md section 1.2
- date: 2026-10-09
- relates: B-MOD-006, B-MOD-009

### B-MOD-008: Backup `0x00bd0001` holds 8 directory prefixes of 64 bytes: `/usr/sabin/`, `/system/sabin/`, `/system/lensbin_lensproperty/`, `/usr/`, `/usr/share/startbinary/`, `/usr/share/dspbin-mag/`, `/setting/`, `/usr/sabin/`; `0x00bd0007` (64 B) = records `(1,3)->bd0000, (1,4)->bd0000, (0,3)->bd0006, (0,4)->bd0006`; `0x00bd0004` (160 B) = (size, id) pairs 4K..1M; `0x00bd0005` (64 B) = two (size, address) pairs
- status: verified-code
- evidence: parsed values (mine) for `bd0001` and `bd0007` bytes (`01 03 .. bd00 | 01 04 .. bd00 | 00 03 00 00 06 00 bd00 | 00 04 ...`). The meanings (revision selector for bd0007; load-buffer size classes for bd0004; purpose of bd0005) are the note's guesses
- source: nex3n-sa-interface.md section 1.2
- date: 2026-10-09
- relates: B-MOD-009

### B-MOD-009: The claim that av-cam builds the module path as `prefix (bd0001) + base name (bd0000)` is false: av-cam contains no code that reads any `0x00bd000x` BKID
- status: refuted
- evidence: this pass: no 4-aligned u32 in `av-cam.bin` has a value in `0x00bd0000..0x00bd0007` (14 unaligned byte coincidences, 0 aligned; the note counts 12 unaligned). The note additionally searched Thumb/ARM immediates, `movt`, `movs #0xbd; lsls #16`, `liro.ko` and the kernel with no hit; those searches were not repeated
- source: nex3n-sa-interface.md section 0 (correction); sony-dsp-isa.md section 9 and the footnote after section 14
- date: 2026-10-09
- relates: supersedes the first part of sony-dsp-isa.md section 0-bis and 9; conflicts with C5

### B-MOD-010: Which component resolves file-id to path and chooses the directory slot is unknown, and so is whether pointing slot 6 (`/setting/`) at a user file would load it
- status: unknown
- evidence: no resolver in av-cam, `liro.ko`, other kmods, kernel or p8 ELF libraries (note); `bd0002` has no directory-slot field; all owner-0x93 files live in `/usr/sabin`
- source: nex3n-sa-interface.md sections 0 and 1.4
- date: 2026-10-05
- relates: B-MOD-009, B-MOD-011

### B-MOD-011: There is no sum32, header-version or core-mask check on the ARM side, a size limit may be 1 MB (`bd0004`), and on OPEN failure av-cam logs and returns sequence result 2 (or 5 on START failure) with no CPU fallback; whether the real loader enforces any of this is unknown
- status: hypothesis
- evidence: note: failure path traced for Soft Focus (`Stage_SoftFocus` 0x3a9966 -> 0x3a9b80); magic literal at 0x412dc is a message-object tag. Not re-checked
- source: nex3n-sa-interface.md section 1.3
- date: 2026-10-05
- relates: B-DSP-029, B-MOD-010

### B-MOD-012: The 9 present p8 effect modules with a constant OPEN site are apollo4 (0x01), kknr (0x0f), bdro2_bdex (0x10), spica (0x16), tbox (0x17), sftfcs (0x18), pbe_work (0x19), star (0x1a), yknr (0x1c), and sweep_panorama (0x0a) via the separate builder
- status: verified-code
- evidence: intersection of B-MOD-003 (OPEN list) with the codectype column of the catalog (mine)
- source: nex3n-sa-interface.md section 5 (reverse picture)
- date: 2026-10-09
- relates: B-MOD-003, B-MOD-013

### B-MOD-013: Six present p8 processing modules have no constant OPEN site in av-cam: dfdet (0x02), fc_recog (0x13), defect (0x14), frc2 (0x15), shapep (0x21), test_intr_c0a (0x28); the note says dfdet/defect use their own managers (`ZIT_SaOpen`, ZIMA/EncPin managers) so "no static OPEN" does not mean unused; the 16 codec-class files have no constant OPEN site either
- status: verified-code
- evidence: my OPEN list contains none of these codectypes (the 3-level check: B-MOD-003). The "own manager" part is from the note and is hypothesis; for frc2 the note says nothing
- source: nex3n-sa-interface.md section 5
- date: 2026-10-09
- relates: B-MOD-014, B-MOD-016

### B-MOD-014: av-cam opens eleven codectypes whose files are absent from 3N flash: 0x03 clearvid, 0x04 bayer, 0x05 dcv, 0x06 one_shot_3d, 0x07 kdz, 0x0b bfnr, 0x0d boks, 0x0e ssp, 0x11 contplus, 0x1b nflash2, 0x1e ddt; those wrapper paths are dead on the 3N
- status: verified-code
- evidence: OPEN list (B-MOD-003) minus codectypes present in p8; names from `bd0002`/`bd0000` (B-MOD-006); av-cam still has `sa_func_{DCV,KDZ,BFNR,BOKS,NFLASH,...}` wrappers (B-MOD-005). "Dead" is an inference, hypothesis-level
- source: nex3n-sa-interface.md section 5
- date: 2026-10-09
- relates: B-MOD-003, B-MOD-006

### B-MOD-015: `sa_test_intr_c0a.bin` (codectype 0x28, 3,588 B) is the best candidate for a module that is never loaded: it prints `*** START !! ***` and `arg = %08x` of `*(0x481c0)`, has no OPEN site, no wrapper and no VLIW
- status: hypothesis
- evidence: structural (this pass: VLIW count 0, no OPEN site 0x28, no wrapper strings; note: printf strings in the module). "Never loaded" cannot be proven statically
- source: nex3n-sa-interface.md section 5; sony-dsp-isa.md section 2 (semantic anchors)
- date: 2026-10-05
- relates: B-MOD-013

### B-MOD-016: `sa_dfdet.bin` is the same file in p3 (`/system/sabin`) and p8 (`/usr/sabin`) and is used for ZIT detection (face detection); it must not be touched
- status: hypothesis
- evidence: identical md5 re-checked (B-MOD-001); the "used" and "face detection" part is the note's inference (ZIT string, own manager); unproven
- source: nex3n-sa-interface.md section 5
- date: 2026-10-05
- relates: B-MOD-001

### B-MOD-017: av-cam hardcodes 18 full paths `/usr/sabin/spica_*_tap_step*.bin` (zoom, dualrec, still, magnifier_plus x c/y x step1/step2, but only `apsp` step2); these tables are not loaded through the codectype mechanism: `bd0002` lists only the 16 non-magnifier tables with owner 0xb6, ref 0x10..0x1f, and SPICA_START_PARAM receives the id pair (e.g. still step1 = 0x19/0x18)
- status: verified-code
- evidence: `strings av-cam.bin | grep ^/usr/sabin/spica_` = 18 strings (mine; the two missing of 20 files are `apsp_c_tap_step1` and `apsp_y_tap_step1`, whose contents equal step2); `bd0002` listing (B-MOD-006). The id pair passed in START_PARAM and the 0xff id for magnifier come from the note
- source: nex3n-sa-interface.md sections 1.2, 5
- date: 2026-10-09
- relates: B-MOD-002, B-MOD-006

### B-MOD-018: `ssboot.bin` (11,216 B) and `ssboot_any.bin` (9,552 B) in p3 are bare DSP images (no `aa0a1391` container, no image table, no sum32) with descriptor VV 0x32 and `w[2]` = 0x80001 / 0x80005; the 3N kernel command line names them `cmpr.path=/system/sabin/ssboot.bin cmpr.path2=/system/sabin/ssboot_any.bin` next to `wbi_cmpr.*` and `wbimem=` parameters
- status: verified-code
- evidence: file headers and descriptor dump (mine); `nflasha2_unpacked/kemco.txt` lines `cmpr.path=...`, `wbi_cmpr.waddr=0xc7100000 wbi_cmpr.wsize=0x100000`, `wbimem=` list (mine). Both files and `idt_cam.bin` contain the same crt0 string `&$kq'${y` that the generations note gives for the shared module crt0
- source: dsp-grain-campaign.md section 3 (p3 contents); nex3n-sa-interface.md section 1.4 (kemco quote); sony-dsp-isa.md section 9
- date: 2026-10-09
- relates: B-MOD-019

### B-MOD-019: `ssboot*` are DSP code used by the kernel to compress the warm-boot image (WBI snapshot in p5) and are not part of the picture pipeline
- status: hypothesis
- evidence: the `cmpr.path` naming and the `wbi_cmpr` / `wbimem` parameters in `kemco.txt` (B-MOD-018); no note states this role. No firmware code was read to confirm what loads them
- source: none (derived from kemco.txt)
- date: 2026-10-09
- relates: B-MOD-018

### B-MOD-020: The Soft Focus path is `Stage_SoftFocus` (0x3a9898) / `HapiSFTFCS` (0xa6b82) -> `sa_func_SFTFCS_preinit` (0x1635d8, OPEN 0x18 at 0x163604) -> `sa_func_sftfcs_start` (0x1637ca) -> `ExecuteCalcStartMSG` ([9] = 0x41), with the param block at `bus(base)+0x80` holding three image-buffer addresses (+0x00/04/08), four kernel pointers (+0x0c..0x18), width +0x1c, height +0x20, stride +0x24, three level bytes +0x28/+0x2c/+0x34, and the DSP side imports them into a job struct J with the same fields
- status: hypothesis
- evidence: note: av-cam reading (strings `Stage_SoftFocus`, `HapiSFTFCS`, `sa_func_sftfcs_*`, `SFTFCS_preinit` re-confirmed in `strings`, OPEN 0x18 at 0x163604 re-confirmed) and DSP function `0x1c38` reading; layout not re-checked
- source: nex3n-sa-interface.md section 2.2; sony-dsp-isa.md section 15.1
- date: 2026-10-06
- relates: B-MOD-021

### B-MOD-021: sftfcs DSP side checks its parameters and returns `0xeeee0001..09` on violation: width > 639 and a multiple of 16, height > 479 and a multiple of 8, stride a multiple of 16 and >= width, each of three level bytes <= 64 and their sum <= 64, buffer and kernel addresses 8-aligned, each 3x3 kernel sums to 256 (kernel B equals kernel A sum), each 5x5 kernel sums to 256
- status: hypothesis
- evidence: note: function `0x1b28` read with the ma1co table (`cmp.gtu`, `cmp.gts`, `cmp.nand`), thresholds re-derived in 15.8; not re-checked. Effect of a violation on the camera is unknown
- source: sony-dsp-isa.md section 15.3, 15.10
- date: 2026-10-06
- relates: B-MOD-020, B-DSP-022

### B-MOD-022: The Soft Focus run order is 3x3 once (kernels at 0x12800 then 0x12840, flag r5 = 0) and 5x5 twice (0x12880 then 0x128c0)
- status: hypothesis
- evidence: sequence of three calls `0xaac(K,0,0)`, `0xaac(K,1,1)`, `0xaac(K,1,2)` in image 1 (desc 0x2c20); an earlier version had it the other way round (polarity error, B-DSP-008); not re-checked
- source: sony-dsp-isa.md sections 15.0, 15.2, 15.8
- date: 2026-10-06
- relates: B-DSP-008

### B-MOD-023: The three level bytes of Soft Focus are blend weights in 64ths (sum <= 64, rest = original) mapped to the three passes
- status: hypothesis
- evidence: only consistent with the <= 64 check and the pass count; the blend code was not found (note section 15.4)
- source: sony-dsp-isa.md sections 15.3, 15.4
- date: 2026-10-06
- relates: B-MOD-021

### B-MOD-024: `sa_tbox` (0x17) is the Miniature effect: it processes the frame in blocks (149 vs 256 `run_engine` calls at two synthetic sizes), its hard-coded engine registers are 0x40030..0x40054 with command-table dispatch `0x1c -> 0x68 (per block) -> 0xc4 -> 0x130`, and its params come from Backup `0x00030109` via `HapiTBOX` (0xa2852)
- status: hypothesis
- evidence: emulator runs (section 21.2) and the HAPI reading (sa-interface section 3); descriptor scan re-checked: 4 images (w[2] 0x80005, 0x105, 0x205, 0x305), 5 VLIW programs. Mapping name `TBOX` -> Miniature rests on `Start_Miniature`/`HapiTBOX` strings (both present in av-cam strings, re-checked) and codectype 0x17 opened at 0x1626e6 (re-checked)
- source: nex3n-sa-interface.md section 3; sony-dsp-isa.md section 21.2
- date: 2026-10-07
- relates: B-DSP-019

### B-MOD-025: `sa_pbe_work` (0x19, images PBE_MID and PBE_HIGH) is the PBE stage (noise reduction / detail, parameters `nr_ihm.*`, `PBEM_BDRO`, `PBEM_RAW_MULTI` inside `PBEH`), not an art effect; in newer generations the same slot becomes `sa_smod`
- status: hypothesis
- evidence: strings-based inference in the note (`PBE_START_PARAM`, `pbe_start_mbx` strings re-confirmed to exist); role not tested. Slot conflict 0x19 pbe_work (4132) vs smod (7M2) from the generations note
- source: sony-dsp-generations.md "Чего у 3N нет", ID conflicts
- date: 2026-10-04
- relates: B-DSP-028

### B-MOD-026: `sa_yknr` (0x1c, 4 images, 5 VLIW programs, wrapper `sa_func_YKNR_*`, `YKNR_START_PARAM`) is a noise-reduction module: its engine config loads 9 signed values (-8, 32, 16, 16, -2, -2, -16, -2, 0), counts/thresholds mostly 18/19, and a reciprocal LUT `65536*16/n` at `0x40078..0x400e0`; whether it works on luma or chroma is not established
- status: hypothesis
- evidence: emulator runs (note section 21.1, config function at text `0x1ccc`), not re-run; wrapper strings and OPEN 0x1c re-confirmed (B-MOD-003, B-MOD-005). The notes disagree on luma/chroma: section 21.1 says "luma/chroma", `film-effects-plan.md` says unknown, `backup-params.md` says YKNR is a luma-noise stage gated by NR level (see C7)
- source: sony-dsp-isa.md section 21.1; film-effects-plan.md lines 38-44, 211; backup-params.md section 1.1
- date: 2026-10-07
- relates: C1, C7

### B-MOD-027: `sa_kknr` (0x0f) has two named images KKNR_PRE and KKNR_KK1 plus three more core images (5 descriptors, 6 programs); `sa_apollo4` (0x01) has no 0x40000 coefficient aperture and only control-register writes (7 descriptors, 13 programs); `sa_defect` (0x14) has hard-coded engine parameters (`0x40000 <- 0x12800`, `0x4000c <- 0xff`, `0x40010 <- 0x17`); `sa_spica` (0x16, SPC_PRE/SPC_MAP) takes engine values from the job struct (16 word fields mapped); `sa_star` (0x1a) and kknr have branch-gated coefficient loads that the synthetic emulator harness did not reach
- status: hypothesis
- evidence: counts of descriptors and programs re-checked (catalog); engine-write maps from the note's emulator runs (sections 22.1-22.4), not re-run. Roles: KKNR = chroma NR is by name and the note's NR text; apollo4, star, frc2, shapep roles unknown
- source: sony-dsp-isa.md section 22
- date: 2026-10-07
- relates: B-DSP-019

### B-MOD-028: The roles of `sa_star` (473,732 B, 9 core images, 10 VLIW programs), `sa_frc2` (3 images), `sa_shapep` (2,308 B, no VLIW), `sa_fc_recog`, `sa_bdro2_bdex` (BDEX_0/BDEX_1 images, wrapper `sa_func_BDEX_*`) and `sa_apollo4` are not established; only names (STAR, FRC2, SHAPEP, FC_RECOG, BDRO2/BDEX, APOLLO_4) exist
- status: unknown
- evidence: no note assigns a function; for star the command tables 0x180/0x1d/0x0 and engine regs `0x40000..0x4003c` are the only facts
- source: sony-dsp-isa.md section 22.4; nex3n-sa-interface.md section 5
- date: 2026-10-09
- relates: B-MOD-027

### B-MOD-029: The four `sa_jpeg_*` modules (enc/dec x 1unit/1core, 0xe0/0xe1/0xe8/0xe9) have a single VLIW program each (enc_1unit has 2), descriptor VV 0x31, and no constant OPEN site; whether the still-image encoder uses them is not known, because the stills JPEG path in av-cam is a handle-based message loop (`tsk46_jpeg`, handler 0xc347427a)
- status: unknown
- evidence: catalog (VLIW counts, VV, OPEN column); dsp-grain-campaign.md section 2 describes `tsk46_jpeg` taking the YC buffer by handle. No note says whether `sa_jpeg_enc_*` is called for stills
- source: dsp-grain-campaign.md section 2; sony-dsp-isa.md section 4
- date: 2026-10-09
- relates: B-DSP-023, C1

### B-MOD-030: Picture effects map to modules only for Soft Focus (`sa_sftfcs`, Backup `0x0003010a`) and Miniature (`sa_tbox`, `0x00030109`); HDR Painting and Rich-tone Mono go through `Start_Art_Effect` (0xa52b8) and `Start_Richtone_Monochrome` (0xa5ffa) with no direct `sa_func_*` call; Toy, Pop, Posterization, Retro, Soft High-key, Partial Color, HC Mono have no SA module or wrapper (probably ISP/YC only); Watercolor and Illustration have PARAMIDs but no module
- status: hypothesis
- evidence: note's reading of `libObj` `CamMsgConv` and the HAPI functions; effect names by menu order are explicitly a guess. Strings `Start_Miniature`, `HapiTBOX`, `HapiSFTFCS` re-confirmed present
- source: nex3n-sa-interface.md section 4; sony-dsp-generations.md "Проверено и гипотезы"
- date: 2026-10-05
- relates: B-MOD-020, B-MOD-024

### B-MOD-031: The 16 codec-class modules (AAC-LC dec / enc_nr, AC-3 dec, DD5.1 enc_nr, BD LPCM dec, AVC enc performance/quality, AVC dec performance/compatible, jpeg x4, zima x3) were not analysed beyond headers; audio modules use descriptor flags `3d 00 fd bf` and load address 0x45d00 per the note, which this pass did not confirm (their image tables are empty: no `3d 00 xx b0 42` pattern in the five audio files)
- status: unknown
- evidence: descriptor scan found 0 matches in `sa_aaclcdec`, `aaclcenc_nr`, `ac3dec`, `bd_lpcmdec`, `dd51enc_nr`, consistent with a different descriptor form; layout not parsed further
- source: sony-dsp-isa.md section 1 (last bullet)
- date: 2026-10-09
- relates: B-DSP-001

### 1.3 Area IDT: `idt_cam.bin` and its overlays

### B-IDT-001: `idt_cam.bin` (200,384 B = 0x30ec0) contains exactly 35 occurrences of the stub bytes `5f50 5e50 5150 b100` at file offsets 0x5a0, 0x670, 0x740, 0x8dc0, 0x8fd0, 0xb250, 0xcbd0, 0xf6c0, 0x105d0, 0x11280, 0x12cd0, 0x13b50, 0x14c40, 0x153c0, 0x15850, 0x173d0, 0x17dd0, 0x18650, 0x19d50, 0x1a770, 0x1c7f0, 0x1eec0, 0x1f2d0, 0x20ce0, 0x22460, 0x23b50, 0x249d0, 0x26650, 0x27e50, 0x299d0, 0x2af60, 0x2d1c0, 0x2d4e0, 0x2f140, 0x302c0
- status: verified-code
- evidence: byte scan of the file (mine); file size = descriptor word `w[6]` = 0x30ec0
- source: dsp-grain-campaign.md section 7 (the note says 35 overlays)
- date: 2026-10-09
- relates: B-IDT-002

### B-IDT-002: Each overlay starts with the stub `ldr sp; ldr r14; ldr r1,=entry; bl r1; ldr r1,=0x48208; mov r2,#0; str r2,[r1]; nop; wfi; b -` followed by words +0x18 = stack top and +0x1c = entry (link address), +0x20 = 0x48208; the link base of the overlay is `(entry & ~0xfff) + 0x10`, and the entry lies at base + 0x24 for nine overlays (0x5a0, 0x670, 0x740, 0x8dc0, 0x153c0, 0x1eec0, 0x23b50, 0x2d1c0, 0x302c0) and later for the rest
- status: verified-code
- evidence: for all 35 overlays the first address printed by the disassembly in `/tmp/claude-501/ov/ov_<off>.txt` equals `(entry & ~0xfff)+0x10` (mine, 35/35; groups: base 0x2010, 0x5010, 0x6010, 0x7010); stub text in e.g. `ov_105d0.txt` lines 1-12; entry file offsets in the overlay table below
- source: dsp-grain-campaign.md section 7; memory note (`nex3n-firmware-hack-status.md`) "база = страница+0x10"
- date: 2026-10-09
- relates: B-IDT-001

### B-IDT-003: Stack tops and entries cluster by group: 0x5a0/0x670 (stack 0x4000/0x7000), 0x8dc0-0xcbd0 and 0xf6c0-0x105d0 (stack 0x2800-0x4000, base 0x2010), 0x11280-0x14c40 (stack 0x12000, base 0x7010), 0x153c0-0x19d50 (stack 0x8000), 0x1a770-0x1c7f0 (0xf000), 0x1eec0-0x1f2d0 (0x7fc0/0x7fb0), 0x20ce0-0x23b50 (0xe800), 0x249d0-0x299d0 (0xe000/0xdfa0, base 0x5010 or 0x6010), 0x2af60-0x302c0 (0x7000/0xb800); for 7 overlays (0x740, 0x8fd0, 0xcbd0, 0x15850, 0x18650, 0x1f2d0, 0x2af60) the overlay's own link range (base + length) extends above its stack top, so either the stack lies inside the image or the tail is not loaded contiguously
- status: verified-code
- evidence: values read from the file (table below); the "extends above its stack" flag is arithmetic on base + length-to-next-signature and may be an artefact of the length rule (length = distance to next stub, not a recorded size). The meaning is not established
- source: none (derived from the file)
- date: 2026-10-09
- relates: B-IDT-005

### B-IDT-004: `idt_cam.bin` has no `aa0a1391` container header and no sum32 trailer; it begins with a bare descriptor (`3d 00 39 b0 42 34 0f 00`, `w[2]` = 4, `w[3]` = 0x820, `w[4]` = 0x260, `w[5]` = 0x820, `w[6]` = 0x30ec0, `w[7]` = 0x30e00, `w[11]` = 0x682, `w[16..18]` = 0x2000, 0x7000, 0x6000) and holds seven SA descriptors at 0x0, 0x880, 0xc80, 0x2700, 0x4600, 0x5b80, 0x7380 with `w[2]` = 0x4, 0x104, 0x404, 0x504, 0x604, 0x704, 0x804 (core index in bits 8..15; indices 2 and 3 absent)
- status: verified-code
- evidence: header and descriptor scan (mine); the six helper descriptors have `w[3]` = 0x3f0, 0x1a50, 0x1ef0, 0x1510, 0x17a0, 0x1970 and the standard MMIO tail 0x48000/0x48200/0x48100, like the small modules. All six lie inside the byte range 0x740..0x8dc0 that the next-signature rule attributes to a single "overlay 0x740". How the helper images relate to the 35 stub overlays is not established
- source: none new (dsp-grain-campaign.md section 3 only says "a v4 SA descriptor")
- date: 2026-10-09
- relates: B-DSP-004, B-IDT-005

### B-IDT-005: The overlay at 0x740 (0x8680 B by the next-signature rule, 34 KB, entropy 6.65, no VLIW program) is not a single overlay: it contains six core descriptors (B-IDT-004) and its link range exceeds its own stack top; its true extent and role are unknown
- status: hypothesis
- evidence: arithmetic and descriptor positions (B-IDT-003, B-IDT-004); nothing in the notes describes 0x740 beyond "the 0x740 overlay" in the table of stubs
- source: none
- date: 2026-10-09
- relates: B-IDT-001, B-IDT-004

### B-IDT-006: 22 of the 35 overlays contain exactly one VLIW program (header `0x0000080000000000` + NOP, to the first zero qword) and 13 contain none; the 22 programs hold 4,974 bundles (39,792 B, about 40 KB), the longest being 0x8fd0+0x15c0 (385), 0x2af60+0x1550 (397) and 0x15850+0xf10 (357)
- status: verified-code
- evidence: header+NOP scan inside each overlay's byte range (mine; table below lists file offset and bundle count per program). Overlays without VLIW: 0x5a0, 0x670, 0x740, 0x8dc0, 0xf6c0, 0x13b50, 0x14c40, 0x153c0, 0x1eec0, 0x23b50, 0x2d1c0, 0x2f140, 0x302c0
- source: none new (dsp-grain-campaign.md section 7 says overlays "mix scalar code, literal pools, data tables and VLIW kernels")
- date: 2026-10-09
- relates: B-DSP-011, C2

### B-IDT-007: The VLIW share of `idt_cam` is about 40 KB, not ~148 KB; the section 3 claim that scalar code is `~0x820..0xa598` and VLIW is `0xa598..0x2ea68` ("the pixel math") is refuted: the first VLIW program header sits at file 0xa590 (inside overlay 0x8fd0), but programs are separated by scalar code, literal pools and tables of 13 overlays that contain no VLIW at all
- status: refuted
- evidence: B-IDT-006 (program offsets and counts); the first program at 0x8fd0+0x15c0 = 0xa590 matches the note's `0xa598` start; the note's end 0x2ea68 lies inside the last program region (0x2d4e0+0x1340 = 0x2e820, 255 bundles to 0x2f018)
- source: dsp-grain-campaign.md section 3; superseded by section 7
- date: 2026-10-09
- relates: B-IDT-006, C2

### B-IDT-008: The Campaign A (07.10) interpretations "second half 0x1c000-0x2ea68 = encode/write", "first half = develop + live view", "e2a 0xe800-0x10c00 = main luma write", "e2b 0x10c00-0x13000 = late luma tone/gain", "core19 0xf6c0 (450 bundles)", "core25 0x11280 (586 bundles)" are refuted as stated; the observed symptoms (hang, black frame, 2-4 stop overexposure) remain observations but were produced by NOPs executed as scalar code (`dc3e` = `bfc`) in overlays that mix code, pools and data
- status: refuted
- evidence: note section 7 argument; re-check: overlay 0xf6c0 contains no VLIW program at all (0 bundles), overlay 0x11280 has one program of 207 bundles, so the "450 / 586 bundle cores" were byte ranges (scalar+data+VLIW), not VLIW cores. The camera experiments themselves are not re-run
- source: dsp-grain-campaign.md sections 4 and 7
- date: 2026-10-09
- relates: B-IDT-007, B-IDT-009

### B-IDT-009: Overlay 0x105d0 (base 0x2010, entry 0x21cc, stack 0x3800) is a statistics service: a mailbox loop (DMA descriptor register 0x48234, go 0x48230, irq 0x48208), a parameter check at +0x348 and handler at +0x3c8 that DMA-reads lines into a double buffer (0x8000/0x8800), loads engine registers 0x40000..0x40058, runs a VLIW kernel per line, and exports five accumulators (0x40078..) plus 64 B to ARM through a write descriptor `0x80380000`; no pixel write-back
- status: verified-code
- evidence: full-read finding in note section 7. Structural pieces re-checked in `ov_105d0.txt`: stub and entry, literal `0x80380000` present in this overlay only, literals 0x48234/0x3ff80000/0x40000000/0x48230 repeated around the DMA setup, 0x8000 and 0x40014/28/2c/30/50/78, two `0009` calls (lines 39 and 212), one VLIW program of 163 bundles at file 0x10c80. "Statistics, no pixel write-back" is an interpretation of that reading; the note records it as read in full by the author
- source: dsp-grain-campaign.md section 7
- date: 2026-10-09
- relates: B-IDT-010, B-IDT-008

### B-IDT-010: The 2-4 stop overexposure of the NOP test `nope2b1` (0x10c00..0x12520) was caused by corrupting the literal pool or kernel of the 0x105d0 statistics overlay (wrong AE/DRO), not by removing a luma-write stage
- status: hypothesis
- evidence: note's explanation; consistent with B-IDT-009 (the range 0x10c00..0x12520 starts at the VLIW program of 0x105d0 (0x10c80) and covers its tail plus the head of 0x11280); the experiment logs `flash_nope2b1.log` exist but outcome and image were not re-read
- source: dsp-grain-campaign.md section 7
- date: 2026-10-09
- relates: B-IDT-009, B-IDT-008

### B-IDT-011: Overlay 0xf6c0 (3,856 B, base 0x2010, entry 0x20b8, stack 0x4000, no VLIW program) writes 2D blocks from local memory 0x9000; whether those blocks are an AE/AWB grid is a guess
- status: hypothesis
- evidence: note section 7 plus re-check: literal `0x9000` appears 6 times, `0x9005`, `0x9014` once; DMA-descriptor construction `0x80280000 | (x>>2)` with `0x2f0000`/`0x300000` at file 0xff8e and 0x10130; `0x80100000` once. The write direction of `0x80xx0000` descriptors is inferred from the 0x105d0 export descriptor `0x80380000`
- source: dsp-grain-campaign.md section 7
- date: 2026-10-09
- relates: B-IDT-009

### B-IDT-012: Overlay 0x11280 (6,736 B, base 0x7010, entry 0x7408, stack 0x12000) is not used by stills: NOP-ing the whole overlay gives a normal image, and NOP-ing `0x12520..0x13000` is also normal; it contains a u16 reciprocal table `round(65536/n)` for n = 1 (65535), 2 (32768), 3 (21845)... of at least 199 entries at file 0x12272, and identical tables sit in overlay 0x299d0 (file 0x2a6e4) and overlay 0x2af60 (file 0x2c224)
- status: hypothesis
- evidence: reciprocal table re-checked (first 199 entries match `round(65536/n)` within 1; three copies by byte search, mine) is verified-code on its own; the "not used by stills" camera result is the note's (`flash_nopov11280.log`, `p3_nopov11280.bin` exist, result not re-read). Skipping other overlays is non-specific (B-IDT-014)
- source: dsp-grain-campaign.md section 7
- date: 2026-10-09
- relates: B-IDT-013

### B-IDT-013: The question whether any idt_cam overlay writes image pixels, or idt_cam on the 3N is purely a 3A/statistics engine with pixels produced by fixed-function ISP blocks, is open; the planned next step is an offline classification of all overlays by DMA pattern (per-line read + per-line write = pixel)
- status: unknown
- evidence: note section 7; no overlay has been classified in this pass beyond 0x105d0 (statistics), 0xf6c0 and 0x299d0 (see their claims). Counted `0x3ff80000` DMA-descriptor literals per overlay (read-descriptor tag) range 1-8 (largest 0x1c7f0 = 6 literal copies, 0x20ce0 5); not a classifier
- source: dsp-grain-campaign.md section 7; memory note `nex3n-firmware-hack-status.md`
- date: 2026-10-09
- relates: B-DSP-020, B-IDT-014

### B-IDT-014: The overlay-skip test (stub `bl r1` replaced by `nop`) for 0xf6c0, 0xcbd0 and 0x105d0 gives the same symptom each time (live view blinks at 1/4000 f/16, saving hangs), so a skip proves only that the ARM waits for the overlay, not what it computes; single-core NOP tests of 0x2d4e0 and 0x249d0 had no effect
- status: hypothesis
- evidence: note section 7 and section 4 (camera results, not re-read); build scripts and images exist in `~/nex3n-dump/work/nopcore/` (`build_skipov.py`, `p3_skip_*.bin`, `flash_skip_*.log`)
- source: dsp-grain-campaign.md sections 4 and 7
- date: 2026-10-09
- relates: B-IDT-013

### B-IDT-015: Overlay 0x299d0 (5,520 B, base 0x5010, entry 0x5aa4, stack 0xdfa0) contains one VLIW program of 141 bundles (header at file 0x2aa10), a DMA setup loop of four 16-byte descriptors per pass with row length field `0x27f0000`, source step 0x4b00 and local step 0x280 (640), and the reciprocal table of B-IDT-012 at file 0x2a6e4
- status: verified-code
- evidence: `ov_299d0.txt` file 0x2a14e-0x2a208 (the loop adds r4 = ldrh 0x4b00 to the source and r5 = ldrh 0x0280 to the local address, 4 descriptors, then `0x48234`/`0x48230`/`0x48208` writes), literals 0x980000, 0x27f0000, 0xa00300; ldrh constants 0x0280 (640), 0x0140 (320), 0x00a0 (160), 0x00f0 (240), 0x0780, 0x0f00, 0x4b00, 0x04b0 appear in the same overlay (mine)
- source: none (task brief: "0x299d0 writes a picture 640 px wide")
- date: 2026-10-09
- relates: B-IDT-016

### B-IDT-016: Overlay 0x299d0 writes an image that is 640 pixels wide
- status: hypothesis
- evidence: the claim comes from the task brief, no note contains it. Supported: 640-based geometry constants and a 640-byte row DMA in B-IDT-015. Not supported: the transfer direction (the descriptors carry the bus address masked with `0x3fffffff` first and a local address second, the same shape as the sftfcs read descriptors), the sample size (640 bytes per row is 640 px at 8 bit or 320 px at 16 bit) and what picture it is (preview / thumbnail / downscale)
- source: task brief, 2026-10-09
- date: 2026-10-09
- relates: B-IDT-015

### B-IDT-017: All 22 VLIW-bearing overlays contain at least one raw `0009` halfword (engine launch) and none of the 13 VLIW-free overlays does; the scalar part of an overlay is control/config only
- status: hypothesis
- evidence: raw `0009` halfwords per overlay: 0 in the 13 programless overlays, 1-5 in each of the 22 VLIW overlays (mine; upper bounds, data can mimic the halfword); the "scalar part is config only" is the note's view for sa modules (B-DSP-020) and has not been checked per overlay
- source: dsp-grain-campaign.md section 3 (old) and section 7
- date: 2026-10-09
- relates: B-DSP-009, B-DSP-020

### B-IDT-018: Nothing in the notes says who loads the idt_cam overlays or how, nor how the seven descriptors and the 35 stubs fit together; the ARM-side route is a mailbox with SAID/CmdCode/OsalID/ParamAddress
- status: unknown
- evidence: note section 7 describes only the overlay stub and one handler; `idt_cam.bin` is named in the Backup file table `0x00FA0080` (non-empty records `\sabin\idt_cam.bin`, `\sabin\sa_dfdet.bin`, ...) per `firmware-architecture.md`; no av-cam strings `idt_cam` were found by `strings av-cam.bin | grep idt_cam` (mine: 0 hits)
- source: dsp-grain-campaign.md section 7; firmware-architecture.md lines 50-51
- date: 2026-10-09
- relates: B-IDT-001

## 2. Catalog of SA modules

Columns come from the files (mine, 2026-10-09) except "role", which comes from names, strings and notes (status in the last column). "VLIW programs" = header `0x0000080000000000` + NOP at 8-aligned offsets (p8 total = 189). "Descriptors by scan" = number of `3d 00 xx b0 42 VV` hits with the `w[2]` word of each. "av-cam OPEN site" = is the codectype in the 20-site list of B-MOD-003 (codec-class files are not expected there). `VV` = descriptor version byte. `sum32` = trailer check of B-DSP-001. Counts: p8 has 32 modules (16 processing + 16 codec-class) and 20 raw tap tables; p3 has idt_cam, sa_dfdet (same file as p8), ssboot, ssboot_any.

Processing-class modules with a confirmed av-cam OPEN site and pixel-engine work (candidates for full-frame processing; none is verified on the camera as the stage that writes the final picture): `sa_sftfcs` (Soft Focus), `sa_tbox` (Miniature), `sa_yknr`, `sa_kknr`, `sa_pbe_work` (NR/detail), `sa_spica` (scaler/correction with tap tables), `sa_bdro2_bdex`, `sa_star` (role unknown), `sa_apollo4` (control only), `sa_sweep_panorama` (stitch). Present but without a constant OPEN site: `sa_defect` (defect pixels, own manager per note), `sa_dfdet` (detection), `sa_frc2`, `sa_fc_recog`, `sa_shapep`, `sa_test_intr_c0a`.

| part | file | size B | container ver | class(+8) | codectype(+9) | +0x0c | tag(+0x14) | images in +0x30 table | descriptors by scan (w[2] list) | VV | VLIW programs (aligned hdr+NOP) | sum32 trailer | md5[:8] | av-cam OPEN site for codectype | role (from names/notes) | role status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| p8 | sa_aaclcdec.bin | 286212 | 1 | 01 | 0xd7 | 0x10002 | ZM_AACD_0x00 | - | 0:  |  | 7 | ok | 1f246658 | no constant OPEN site (codec; own manager per note) | AAC-LC decoder | hypothesis |
| p8 | sa_aaclcenc_nr.bin | 302596 | 1 | 01 | 0xd4 | 0x10002 | ZM_AACNR0x00 | - | 0:  |  | 16 | ok | a3312768 | no constant OPEN site (codec; own manager per note) | AAC-LC encoder (NR variant) | hypothesis |
| p8 | sa_ac3dec.bin | 327172 | 1 | 01 | 0xd6 | 0x10002 | ZM_AC3D_0x00 | - | 0:  |  | 8 | ok | e2a39846 | no constant OPEN site (codec; own manager per note) | AC-3 decoder | hypothesis |
| p8 | sa_apollo4.bin | 250372 | 2 | 00 | 0x01 | 0x20001 | SAAPOLLO0x05 | APOLLO_40x05@0x200, APOLLO_40x05@0x200 | 7: 0x2 0x102 0x202 0x302 0x402 0x502 0x602 | 32 | 13 | ok | 83670dac | yes (0x01) | control-register-only engine job (no 0x40000 coefficient aperture); role unknown | hypothesis |
| p8 | sa_avcd_compatible_zma.bin | 56452 | 1 | 01 | 0xc9 | 0x10004 | ZM_AVCDC0x00 | Z_AVCDC00x00@0x80 | 1: 0x2 | 32 | 8 | ok | 276fbe53 | no constant OPEN site (codec; own manager per note) | AVC decoder (ZMA), compatible | hypothesis |
| p8 | sa_avcd_performance_zma.bin | 37892 | 1 | 01 | 0xc8 | 0x10004 | ZM_AVCDP0x00 | Z_AVCDP00x00@0x80 | 1: 0x2 | 32 | 6 | ok | 7da7eb22 | no constant OPEN site (codec; own manager per note) | AVC decoder (ZMA), performance | hypothesis |
| p8 | sa_avce_performance_zma.bin | 178052 | 1 | 01 | 0xc0 | 0x10004 | ZM_AVCEP0x00 | Z_AVCEP00x00@0x80 | 1: 0x2 | 32 | 12 | ok | 9b21c282 | no constant OPEN site (codec; own manager per note) | AVC encoder (ZMA), performance | hypothesis |
| p8 | sa_avce_quality_zma.bin | 193156 | 1 | 01 | 0xc1 | 0x10004 | ZM_AVCEQ0x00 | Z_AVCEQ00x00@0x80 | 1: 0x2 | 32 | 12 | ok | 91eecade | no constant OPEN site (codec; own manager per note) | AVC encoder (ZMA), quality | hypothesis |
| p8 | sa_bd_lpcmdec.bin | 130564 | 1 | 01 | 0xd8 | 0x10002 | ZM_LPCMD0x00 | - | 0:  |  | 1 | ok | e9c33b03 | no constant OPEN site (codec; own manager per note) | BD LPCM decoder | hypothesis |
| p8 | sa_bdro2_bdex.bin | 52484 | 2 | 00 | 0x10 | 0x30001 | SA_BDRO20x00 | BDEX_0__0x00@0x280, BDEX_1__0x00@0x6c80 | 3: 0x80002 0x80002 0x80002 | 32 | 3 | ok | e55dfd66 | yes (0x10) | BDRO2/BDEX (dynamic-range related; exact role unknown) | hypothesis |
| p8 | sa_dd51enc_nr.bin | 302596 | 1 | 01 | 0xd3 | 0x10002 | ZM_AC3NR0x00 | - | 0:  |  | 20 | ok | 8965cea9 | no constant OPEN site (codec; own manager per note) | Dolby Digital 5.1 encoder (NR variant) | hypothesis |
| p8 | sa_defect.bin | 36356 | 2 | 00 | 0x14 | 0x10008 | SADEFECT0.03 | DEFECT__0.03@0x100 | 1: 0x80002 | 32 | 5 | ok | 23fd26a9 | no constant OPEN site (0x14) | defect-pixel correction; engine params hardcoded (emulator) | hypothesis |
| p8 | sa_dfdet.bin | 146052 | 2 | 00 | 0x02 | 0x80001 | ZITTOOLS1.10 | ZIT_HIST1.00@0x680, ZIT__DET1.00@0x6b00 | 8: 0x80002 0x80002 0x2 0x2 0x2 0x2 0x80002 0x80002 | 32 | 23 | ok | 121522c4 | no constant OPEN site (0x02; note: own ZIT manager) | ZIT tools: histogram + detection (face detection per note); two images listed | hypothesis |
| p8 | sa_fc_recog.bin | 18820 | 2 | 00 | 0x13 | 0x10008 | SAFRC___0.01 | FC_RECOG0.01@0x100 | 1: 0x5 | 31 | 4 | ok | d5547700 | no constant OPEN site (0x13) | face recognition by name; no OPEN, no wrapper | hypothesis |
| p8 | sa_frc2.bin | 61188 | 2 | 00 | 0x15 | 0x10008 | SAFRC2__0.04 | FRC2____0.04@0x100 | 3: 0x2 0x102 0x202 | 32 | 5 | ok | 5835de18 | no constant OPEN site (0x15) | unknown (name FRC2); no OPEN site, no sa_func wrapper string | unknown |
| p8 | sa_jpeg_dec_1core.bin | 11268 | 2 | 01 | 0xe9 | 0x10002 | SAJPGD_CLF4_ | JPGDEC_CLF4_@0x100 | 1: 0x3 | 31 | 1 | ok | b4cca72c | no constant OPEN site (codec; own manager per note) | JPEG decoder driver, 1-core variant; use unknown | hypothesis |
| p8 | sa_jpeg_dec_1unit.bin | 11652 | 2 | 01 | 0xe8 | 0x10002 | SAJPGD_ULF4_ | JPGDEC_ULF4_@0x100 | 1: 0x3 | 31 | 1 | ok | 533ace6b | no constant OPEN site (codec; own manager per note) | JPEG decoder driver; use unknown | hypothesis |
| p8 | sa_jpeg_enc_1core.bin | 10884 | 2 | 01 | 0xe1 | 0x10002 | SAJPGE_CLF4_ | JPGENC_CLF4_@0x100 | 1: 0x3 | 31 | 1 | ok | 622f5811 | no constant OPEN site (codec; own manager per note) | JPEG encoder driver, 1-core variant; use unknown | hypothesis |
| p8 | sa_jpeg_enc_1unit.bin | 17412 | 2 | 01 | 0xe0 | 0x10002 | SAJPGE_ULF4_ | JPGENC_ULF4_@0x100 | 1: 0x3 | 31 | 2 | ok | 7ca24704 | no constant OPEN site (codec; own manager per note) | JPEG encoder driver (HW encoder; tables live in av-cam); use for stills unknown | hypothesis |
| p8 | sa_kknr.bin | 64260 | 2 | 00 | 0x0f | 0x50001 | SA_KKNR_0x01 | KKNR_PRE0x00@0x400, KKNR_KK10x00@0x1d80 | 5: 0x80002 0x80002 0x80002 0x80002 0x80002 | 32 | 6 | ok | d2662f2c | yes (0x0f) | chroma NR (name KKNR; luma/chroma split per note film-effects-plan) | hypothesis |
| p8 | sa_pbe_work.bin | 29956 | 2 | 00 | 0x19 | 0x20001 | SA_PBE__0x02 | PBE_MID_0x00@0x200, PBE_HIGH0x00@0x3780 | 2: 0x80002 0x80002 | 32 | 7 | ok | 234b70d9 | yes (0x19) | PBE stage (NR/detail; not an art effect), params in PBEH | hypothesis |
| p8 | sa_sftfcs.bin | 43652 | 2 | 00 | 0x18 | 0x10001 | SASFTFCS0.02 | SFTFCS__0.02@0x100 | 3: 0x80002 0x102 0x202 | 32 | 3 | ok | c64ce801 | yes (0x18) | Soft Focus convolution; kernels from Backup 0x0003010a via ARM | hypothesis |
| p8 | sa_shapep.bin | 2308 | 2 | 00 | 0x21 | 0x10008 | SA_SHAPE0.02 | SHAPEP__0.02@0x100 | 1: 0x5 | 32 | 0 | ok | 57f32828 | no constant OPEN site (0x21) | unknown; no VLIW, no OPEN, no wrapper | unknown |
| p8 | sa_spica.bin | 22404 | 2 | 00 | 0x16 | 0x30001 | SA_SPICA0.90 | SPC_PRE_0.90@0x280, SPC_MAP_0.90@0x1000 | 3: 0x80005 0x80005 0x80005 | 32 | 3 | ok | e5907a0e | yes (0x16) | SPICA: scaler/lens-colour correction with tap tables (resize/zoom fields); input-driven engine config | hypothesis |
| p8 | sa_star.bin | 473732 | 2 | 00 | 0x1a | 0x10001 | SA_STAR_0x03 | STAR____0x03@0x100 | 9: 0x80002 0x10102 0x10202 0x10302 0x10402 0x10502 0x10602 0x10702 0x10802 | 32 | 10 | ok | ce46c698 | yes (0x1a) | unknown role; largest module (473,732 B); 9 core images; command tables 0x180/0x1d/0x0 | unknown |
| p8 | sa_sweep_panorama.bin | 18436 | 2 | 00 | 0x0a | 0x20008 | SAPANORM0.01 | STITCH__0.01@0x200, SROTATE_0.01@0x3480 | 2: 0x80005 0x80005 | 32 | 2 | ok | 8f93cfad | yes via separate builder 0x4dc16e (per note, not re-checked) | sweep panorama stitch + rotate | hypothesis |
| p8 | sa_tbox.bin | 77444 | 2 | 00 | 0x17 | 0x10001 | SATBOX__0.40 | TBOX____0.40@0x100 | 4: 0x80005 0x105 0x205 0x305 | 32 | 5 | ok | 1c783c3c | yes (0x17) | Miniature (tilt-shift) block processing; params Backup 0x00030109 | hypothesis |
| p8 | sa_test_intr_c0a.bin | 3588 | 2 | 00 | 0x28 | 0x20008 | TEST_INT0x00 | TEST_Z0_0x00@0x200, TEST_Z0_0x00@0x800 | 2: 0x20004 0x20004 | 31 | 0 | ok | d5ceefbb | no constant OPEN site (0x28) | test module printing "*** START !! ***" and *(0x481c0); likely never loaded | hypothesis |
| p8 | sa_yknr.bin | 53508 | 2 | 00 | 0x1c | 0x10001 | SA_YKNR_0x02 | YKNR_0__0x01@0x100 | 4: 0x80002 0x80002 0x80002 0x80002 | 32 | 5 | ok | 54acf298 | yes (0x1c) | noise reduction (YKNR); engine config has 16/n reciprocal LUT; luma-vs-chroma not settled | hypothesis |
| p8 | sa_zima_startup_minna.bin | 2692 | 1 | 01 | 0xf2 | 0x10003 | SA_Z_MNS0x00 | ZIMA_STM0x00@0x80 | 1: 0x1 | 32 | 0 | ok | b5e31285 | no constant OPEN site (codec; own manager per note) | ZIMA startup stub "minna" | hypothesis |
| p8 | sa_zima_startup_zma0.bin | 2692 | 1 | 01 | 0xf0 | 0x10001 | SA_Z_ST00x00 | ZIMA_ST00x00@0x80 | 1: 0x2 | 32 | 0 | ok | 3cfc2162 | no constant OPEN site (codec; own manager per note) | ZIMA startup stub core 0 (2,692 B) | hypothesis |
| p8 | sa_zima_startup_zma1.bin | 2692 | 1 | 01 | 0xf1 | 0x10002 | SA_Z_ST10x00 | ZIMA_ST10x00@0x80 | 1: 0x3 | 32 | 0 | ok | 82d9abe4 | no constant OPEN site (codec; own manager per note) | ZIMA startup stub core 1 | hypothesis |
| p3 | idt_cam.bin | 200384 | - | - | - | - | - | - | 7: 0x4 0x104 0x404 0x504 0x604 0x704 0x804 | 34 | 22 | n/a | 20b38683 | n/a (no container) | see overlay section | see B-IDT claims |
| p3 | sa_dfdet.bin | 146052 | 2 | 00 | 0x02 | 0x80001 | ZITTOOLS1.10 | ZIT_HIST1.00@0x680, ZIT__DET1.00@0x6b00 | 8: 0x80002 0x80002 0x2 0x2 0x2 0x2 0x80002 0x80002 | 32 | 23 | ok | 121522c4 | no constant OPEN site (0x02; note: own ZIT manager) | ZIT tools: histogram + detection (face detection per note); two images listed | hypothesis |
| p3 | ssboot.bin | 11216 | - | - | - | - | - | - | 1: 0x80001 | 32 | 1 | n/a | 38f21730 | n/a (no container) | bare DSP image listed in kemco.txt as cmpr.path/cmpr.path2 (WBI compression); role guess | hypothesis |
| p3 | ssboot_any.bin | 9552 | - | - | - | - | - | - | 1: 0x80005 | 32 | 1 | n/a | 12c01607 | n/a (no container) | bare DSP image listed in kemco.txt as cmpr.path/cmpr.path2 (WBI compression); role guess | hypothesis |



### 2.1 Raw spica tap tables (p8, 20 files)

| file | size B | md5[:8] | bd0002 (file-id, ref) | hardcoded `/usr/sabin/` path in av-cam |
|---|---|---|---|---|
| spica_apsp_c_tap_step1.bin | 38400 | 52662d2d | 85, 0x1c | no |
| spica_apsp_c_tap_step2.bin | 38400 | 52662d2d | 87, 0x1e | yes |
| spica_apsp_y_tap_step1.bin | 38400 | 746f1f54 | 86, 0x1d | no |
| spica_apsp_y_tap_step2.bin | 38400 | 746f1f54 | 88, 0x1f | yes |
| spica_dualrec_c_tap_step1.bin | 38400 | b125cc81 | 61, 0x14 | yes |
| spica_dualrec_c_tap_step2.bin | 38400 | b125cc81 | 63, 0x16 | yes |
| spica_dualrec_y_tap_step1.bin | 38400 | af36d8e6 | 62, 0x15 | yes |
| spica_dualrec_y_tap_step2.bin | 38400 | af36d8e6 | 64, 0x17 | yes |
| spica_magnifier_plus_c_tap_step1.bin | 38400 | b324b95e | not listed | yes |
| spica_magnifier_plus_c_tap_step2.bin | 38400 | 3b3be7ae | not listed | yes |
| spica_magnifier_plus_y_tap_step1.bin | 38400 | aa9509c4 | not listed | yes |
| spica_magnifier_plus_y_tap_step2.bin | 38400 | 4ae84c4f | not listed | yes |
| spica_still_c_tap_step1.bin | 38400 | 22016228 | 81, 0x18 | yes |
| spica_still_c_tap_step2.bin | 38400 | e7c496b9 | 83, 0x1a | yes |
| spica_still_y_tap_step1.bin | 38400 | 178a2cc9 | 82, 0x19 | yes |
| spica_still_y_tap_step2.bin | 38400 | 83082512 | 84, 0x1b | yes |
| spica_zoom_c_tap_step1.bin | 38400 | 22016228 | 57, 0x10 | yes |
| spica_zoom_c_tap_step2.bin | 38400 | e7c496b9 | 59, 0x12 | yes |
| spica_zoom_y_tap_step1.bin | 38400 | 178a2cc9 | 58, 0x11 | yes |
| spica_zoom_y_tap_step2.bin | 38400 | 83082512 | 60, 0x13 | yes |


## 3. `idt_cam.bin` overlay table (35 stub overlays)

All offsets are file offsets in `idt_cam.bin` (200,384 B). "Length" is the distance to the next stub (or end of file), not a recorded size. "Load base" is `(entry & ~0xfff) + 0x10`, verified against the disassembly first address for 35/35. A VLIW program is listed as `header file offset (bundles including header)`. Role is `unknown` unless stated; see the B-IDT claims for the evidence.

| # | file off | len to next sig (hex / dec) | stack +0x18 | entry +0x1c | load base (=entry&~0xfff+0x10) | entry file off | VLIW program: hdr file off (bundles incl. hdr) | raw 0009 halfwords | known / notes |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 0x5a0 | 0xd0 / 208 | 0x4000 | 0x2034 | 0x2010 | 0x5c4 | none | 0 | tiny (208 B); entry right after header (+0x24); role unknown |
| 1 | 0x670 | 0xd0 / 208 | 0x7000 | 0x6034 | 0x6010 | 0x694 | none | 0 | tiny (208 B); entry right after header (+0x24); role unknown |
| 2 | 0x740 | 0x8680 / 34432 | 0x8000 | 0x7034 | 0x7010 | 0x764 | none | 0 | 0x8680 B by next-signature rule, but link end 0xf690 exceeds its own stack top 0x8000 and the byte range contains 6 helper-core descriptors (0x880..0x7380); true extent and role unknown |
| 3 | 0x8dc0 | 0x210 / 528 | 0x2800 | 0x2034 | 0x2010 | 0x8de4 | none | 0 | 528 B, small; role unknown |
| 4 | 0x8fd0 | 0x2280 / 8832 | 0x3800 | 0x2504 | 0x2010 | 0x94c4 | 0xa590 (385) | 1 | unknown |
| 5 | 0xb250 | 0x1980 / 6528 | 0x4000 | 0x223c | 0x2010 | 0xb47c | 0xc260 (279) | 1 | unknown |
| 6 | 0xcbd0 | 0x2af0 / 10992 | 0x4000 | 0x22a4 | 0x2010 | 0xce64 | 0xeb20 (351) | 2 | skip test (bl r1->nop): same symptom as 0xf6c0 and 0x105d0 (live view blinks 1/4000 f/16, save hangs) - non-specific (note); role unknown |
| 7 | 0xf6c0 | 0xf10 / 3856 | 0x4000 | 0x20b8 | 0x2010 | 0xf768 | none | 0 | no VLIW program (re-checked); writes 2D blocks from local 0x9000 (note; literals 0x80280000 x2, 0x80100000 consistent with DMA descriptors); AE/AWB grid is a hypothesis; skip test non-specific |
| 8 | 0x105d0 | 0xcb0 / 3248 | 0x3800 | 0x21cc | 0x2010 | 0x1078c | 0x10c80 (163) | 2 | statistics service loop (note: full read; no pixel write-back): DMA-reads lines into 0x8000/0x8800, loads engine regs 0x40000..0x40058, runs VLIW kernel per line, exports 5 accumulators (0x40078..) + 64 B to ARM via desc 0x80380000 (literal unique to this overlay, re-checked); skip test non-specific |
| 9 | 0x11280 | 0x1a50 / 6736 | 0x12000 | 0x7408 | 0x7010 | 0x11678 | 0x12510 (207) | 1 | not used by stills (NOP whole overlay -> normal, note); contains u16 reciprocal table 65536/n (re-checked, file 0x12272) |
| 10 | 0x12cd0 | 0xe80 / 3712 | 0x12000 | 0x729c | 0x7010 | 0x12f5c | 0x135d0 (141) | 1 | unknown |
| 11 | 0x13b50 | 0x10f0 / 4336 | 0x12000 | 0x7150 | 0x7010 | 0x13c90 | none | 0 | unknown |
| 12 | 0x14c40 | 0x780 / 1920 | 0x12000 | 0x72b4 | 0x7010 | 0x14ee4 | none | 0 | unknown |
| 13 | 0x153c0 | 0x490 / 1168 | 0x8000 | 0x7034 | 0x7010 | 0x153e4 | none | 0 | unknown |
| 14 | 0x15850 | 0x1b80 / 7040 | 0x8000 | 0x7316 | 0x7010 | 0x15b56 | 0x16760 (357) | 1 | unknown |
| 15 | 0x173d0 | 0xa00 / 2560 | 0x8000 | 0x716c | 0x7010 | 0x1752c | 0x179a0 (99) | 1 | unknown |
| 16 | 0x17dd0 | 0x880 / 2176 | 0x8000 | 0x70e8 | 0x7010 | 0x17ea8 | 0x183e0 (51) | 1 | unknown |
| 17 | 0x18650 | 0x1700 / 5888 | 0x8000 | 0x7254 | 0x7010 | 0x18894 | 0x19440 (249) | 1 | unknown |
| 18 | 0x19d50 | 0xa20 / 2592 | 0x8000 | 0x7164 | 0x7010 | 0x19ea4 | 0x1a320 (99) | 1 | unknown |
| 19 | 0x1a770 | 0x2080 / 8320 | 0xf000 | 0x7138 | 0x7010 | 0x1a898 | 0x1c2d0 (137) | 2 | unknown |
| 20 | 0x1c7f0 | 0x26d0 / 9936 | 0xf000 | 0x7280 | 0x7010 | 0x1ca60 | 0x1e3c0 (327) | 2 | unknown |
| 21 | 0x1eec0 | 0x410 / 1040 | 0x7fc0 | 0x7034 | 0x7010 | 0x1eee4 | none | 0 | unknown |
| 22 | 0x1f2d0 | 0x1a10 / 6672 | 0x7fb0 | 0x72dc | 0x7010 | 0x1f59c | 0x20170 (341) | 2 | unknown |
| 23 | 0x20ce0 | 0x1780 / 6016 | 0xe800 | 0x7194 | 0x7010 | 0x20e64 | 0x21d60 (183) | 1 | unknown |
| 24 | 0x22460 | 0x16f0 / 5872 | 0xe800 | 0x7144 | 0x7010 | 0x22594 | 0x23500 (165) | 3 | unknown |
| 25 | 0x23b50 | 0xe80 / 3712 | 0xe800 | 0x7034 | 0x7010 | 0x23b74 | none | 0 | unknown |
| 26 | 0x249d0 | 0x1c80 / 7296 | 0xe000 | 0x5988 | 0x5010 | 0x25348 | 0x26030 (173) | 1 | single-core NOP test: no effect (Campaign A note); not on stills path (hypothesis) |
| 27 | 0x26650 | 0x1800 / 6144 | 0xe000 | 0x5910 | 0x5010 | 0x26f50 | 0x276b0 (123) | 1 | unknown |
| 28 | 0x27e50 | 0x1b80 / 7040 | 0xdfa0 | 0x613c | 0x6010 | 0x27f7c | 0x28dd0 (351) | 1 | unknown |
| 29 | 0x299d0 | 0x1590 / 5520 | 0xdfa0 | 0x5aa4 | 0x5010 | 0x2a464 | 0x2aa10 (141) | 1 | DMA loop of 4 descriptors, row length 0x27f (=640 B?) , src stride 0x4b00, local stride 0x280 (re-checked); also holds u16 reciprocal table at file 0x2a6e4; "writes a 640-px-wide picture" = unverified claim from task brief |
| 30 | 0x2af60 | 0x2260 / 8800 | 0x7000 | 0x5bc0 | 0x5010 | 0x2bb10 | 0x2c4b0 (397) | 5 | holds u16 reciprocal table 65536/n at file 0x2c224 (re-checked); 5 raw 0009 halfwords; role unknown |
| 31 | 0x2d1c0 | 0x320 / 800 | 0x7000 | 0x6034 | 0x6010 | 0x2d1e4 | none | 0 | unknown |
| 32 | 0x2d4e0 | 0x1c60 / 7264 | 0x7000 | 0x5fe0 | 0x5010 | 0x2e4b0 | 0x2e820 (255) | 1 | single-core NOP test: no effect (Campaign A note); not on stills path (hypothesis) |
| 33 | 0x2f140 | 0x1180 / 4480 | 0xb800 | 0x5834 | 0x5010 | 0x2f964 | none | 0 | unknown |
| 34 | 0x302c0 | 0xc00 / 3072 | 0x7000 | 0x6034 | 0x6010 | 0x302e4 | none | 0 | unknown |

TOTAL VLIW bundles (22 programs): 4974 bytes 39792


## 4. Contradictions and inconsistencies between sources

- **C1: "the 3N has no separate NR / JPEG / Soft Focus SA modules; the whole stills develop pipeline is `idt_cam.bin`" vs the p8 `sabin/` contents.**
  - Says no: `dsp-grain-campaign.md` section 3 ("On the NEX-3N, p3 `sabin/` holds only `idt_cam.bin` and `sa_dfdet.bin`; there are no separate NR / JPEG / Soft-Focus SA modules (unlike NEX-6/a7). So the entire stills develop pipeline ... is `idt_cam.bin`"); memory note `nex3n-firmware-hack-status.md` (07.10: "sa_yknr/jpeg_enc отдельных у 3N НЕТ"). The task brief also quotes "sa_yknr у 3N нет".
  - Says yes: p8 `sabin/` contains `sa_yknr.bin` (53,508 B), `sa_kknr.bin`, `sa_sftfcs.bin`, `sa_tbox.bin`, `sa_pbe_work.bin`, `sa_star.bin`, `sa_spica.bin`, `sa_defect.bin`, `sa_jpeg_enc/dec_*` (B-MOD-001, catalog); av-cam opens codectypes 0x1c (yknr), 0x0f (kknr), 0x18 (sftfcs), 0x17 (tbox), 0x19 (pbe_work), 0x1a (star), 0x16 (spica) (B-MOD-003); `sa_func_YKNR_*`, `KKNR`, `SFTFCS`, `TBOX`, `PBE`, `STAR`, `SPICA` wrapper strings exist (B-MOD-005); `nex3n-sa-interface.md` and `sony-dsp-generations.md` list them as 3N modules, and the latter says 28 of 32 common modules are byte-identical between NEX-6 and 3N (B-DSP-027).
  - Reading: the statement is true only for p3 `sabin/`. The campaign's premise that `idt_cam` is the whole stills DSP pipeline is not supported, and the NR (`yknr`, `kknr`, `pbe_work`) and JPEG stages are separate SA modules in p8. Whether stills use `sa_jpeg_enc_*` is unknown (B-MOD-029).
- **C2: size and layout of the `idt_cam` VLIW region.** `dsp-grain-campaign.md` section 3: scalar `~0x820..0xa598` (control only) and VLIW `0xa598..0x2ea68` (~148 KB, "the pixel math"). Sections 7 and this pass: 35 stub overlays, 22 contain one VLIW program each, 4,974 bundles in total (about 40 KB), 13 overlays have none (B-IDT-006, B-IDT-007). Also "idt_cam is a v4 SA descriptor" (section 3) vs seven descriptors in the file (B-IDT-004).
- **C3: Campaign A (section 4) vs section 7.** Section 4 treats ranges as "cores" with a role (decode/encode half, e2a luma write, e2b tone) and names `core19 0xf6c0 (450 bundles)`, `core25 0x11280 (586)`. Section 7 says these are overlays and that NOP bundles run as scalar code. Re-check: 0xf6c0 has no VLIW program, 0x11280 has 207 bundles (B-IDT-008). Section 4 and the old table remain in the same file without a pointer from each row; the memory note carries both the old "CAMPAIGN A — карта локализована" paragraph and the 09.10 correction.
- **C4: 0x299d0 "writes a picture 640 px wide".** Not in any note. In the data, a 640-byte-row DMA with local stride 0x280 and several 640-based constants exist; the direction (write vs read) and sample size are not established (B-IDT-015, B-IDT-016). Status `hypothesis`.
- **C5: how av-cam finds a module.** `sony-dsp-isa.md` section 0-bis (headline "Путь и имя модуля — это редактируемые данные в Backup ... самый ценный результат для проекта") and section 9 say the path is built as prefix (`bd0001`) + name (`bd0000`) and that this allows substitution without flashing; `nex3n-sa-interface.md` section 0 and the footnote after section 14 of the ISA note say this is wrong (OPEN carries only a codectype; no code reads `0x00bd000x`; B-MOD-009). The WorkPersonal copy of the ISA note still has the refuted claim in its first-screen summary and in section 9's "Практический вывод", with the correction only as a footnote. The `/setting/` slot idea is untested (B-MOD-010). The Backup map `bd0002` (codectype to file-id) is correct (B-MOD-006).
- **C6: small counts.** `sony-dsp-isa.md` 0-bis says `bd0000` has "86 base names", section 9 says "100 entries" (it has 100 slots, 88 non-empty). Section 9 table labels file-ids "57-88" as spica taps, but 65-69, 71-77 in that range are other files (MAGIC, psd, dfe, pbe_work, star, nflash2, yknr, dm_af_movie, ddt, wireless_power_logo); the spica tap ids are 57-64 and 81-88 (B-MOD-006). The note counts 12 unaligned `0x00bd000x` byte coincidences in av-cam, this pass 14 (B-MOD-009; not material).
- **C7: YKNR / KKNR role.** `sony-dsp-isa.md` 21.1 calls yknr a "luma/chroma noise reduction" averager; `film-effects-plan.md` says YKNR's meaning (luma or chroma) is unknown and plans an experiment; `backup-params.md` calls YKNR/G-NR the luma-noise stages and KKNR chroma; `sony-dsp-isa.md` 22.4 calls kknr "chroma NR". Unresolved (B-MOD-026).
- **C8: CXD90057 keys.** `sony-dsp-generations.md` says no decrypter, no keys, dead end; `sony-hack-prior-art.md` and `nex3n-symbols-and-names.md` section 5 say the keys are in fwtool PR #52 and the unpack is feasible but not done (B-DSP-031).
- **C9: what `+0x0c` / `w[2]` mean.** `sony-dsp-generations.md`: `+0xc` = core mask, "one core" for 4132 (0x01/0x02/0x08); data: `+0x0c` high u16 and low u16 vary (0x10001, 0x50001, 0x80001, ...) and modules have up to 9 core images with distinct `w[2]` (B-DSP-003, B-DSP-025). "One core" conflicts with star (9 images) and apollo4 (7).
- **C10: image count vs image table.** The notes speak of "several images in multi-core modules" taken from the `+0x30` table (kknr PRE/KK1, spica PRE/MAP, pbe_work MID/HIGH, bdro2_bdex, dfdet, sweep_panorama); the table is a subset of the images (B-DSP-003), so statements about "the images of a module" that rely on it undercount (sftfcs 1 vs 3, tbox 1 vs 4, star 1 vs 9, yknr 1 vs 4).
- **C11: internal corrections still present in the WorkPersonal ISA copy.** Section 2 opcode table (C/D polarity, `008r`, `01`/`0D`, `1C`/`1D`, `F0-F5`), section 10 bundle model (4 lanes), section 11 (frc2/star "without VLIW") and section 13.2 (families A/B/C) are superseded by sections 15.8, 13/16 and 11 (inline corrections); a reader of the top-down text meets the wrong versions first (B-DSP-008, B-DSP-012, B-DSP-013, B-DSP-018).
- **C12: source copies differ.** `nex3n-research/notes/sony-dsp-isa.md` (605 lines, English, sections 19-25: engine memory model, emulator maps, dataflow, simulator) is newer than `WorkPersonal/reference/sony-dsp-isa.md` (460 lines, ends at "Аудио-Rosetta"). In the newer copy section 24 ("fundamental limit") is retracted by 24.1 and then by 25 ("data path solved"), and 25.3 reverts to "observability wall"; take 25.3 as current.

## 5. Open questions recorded as unknown (area B)

1. Arithmetic meaning of every op3 value (B-DSP-015).
2. Who loads modules and idt_cam overlays and how the path/directory is chosen; any integrity or size check (B-MOD-010, B-MOD-011, B-IDT-018).
3. Whether any idt_cam overlay writes image pixels (B-IDT-013); direction and content of 0x299d0's DMA (B-IDT-016); extent and role of the 0x740 range and its six helper-core descriptors (B-IDT-004, B-IDT-005).
4. Roles of star, frc2, shapep, fc_recog, bdro2_bdex, apollo4 (B-MOD-028); whether `sa_jpeg_enc_*` is used for stills (B-MOD-029); role of `ssboot*` (B-MOD-019).
5. Meaning of container `+0x0c` and of descriptor words `w[3]..w[10]` (B-DSP-025).
6. Whether the 3N loader would accept a v4/v5 module (B-DSP-029).
7. Which idt_cam overlays run on the stills path at all (only the NOP/skip experiments, B-IDT-014).
8. Confirm that none of the 11 codectypes opened by av-cam without a file in p8 is reachable at runtime (B-MOD-014 "dead" is an inference).
