# Sony DSP modules across generations: can they be moved to the NEX-3N?

Question: can DSP effect modules (`sabin/sa_*.bin`) or ISP tables from firmware newer than CXD4132 be run on the NEX-3N? Static analysis only; the camera was not connected. Context for the 3N: see the repository README.

## Summary
- **The DSP ISA is the same from CXD4132 to CXD90045** (verified): identical startup code (crt0 `0f90 cdaf 8e95 de1e eb60 ...`, string `&$kq'${y`) in every module of every generation, and 80-93 % shared 16-byte shingles between same-named modules on the 3N and a6000. The DSP local memory map in the descriptor also matches (`0x48000/0x48200/0x48100/0x48160/0x49d00/0x481c0/0x48c08`).
- **Container format is shared, but versions differ**: magic `aa0a1391`, module ID (codectype) and sum32le trailer are identical everywhere; header version 2 (4132), 4 (90014), 5 (90045); descriptor version `0x32` vs `0x34`; 24, 54 and 60 vectors/resources; core mask `0x01/0x08` vs `0x0f/0x1f`.
- **Modules were recompiled between 4132 and 90014, but not between 90014 and 90045**: bodies of `sa_tbox/sftfcs/star/frc2/defect/lfnr/nlap/motionshot` on 7M2 and 7M3 are byte-identical (only the header changed), while on 3N vs a6000 the same modules match at 0.83-0.93, not fully. So the DSP runtime and ABI changed at the 4132 -> 90014 transition.
- **Porting verdict:** a newer module cannot simply be dropped in: different header format, different descriptor version, more cores and interrupts, and different `*_START_PARAM` structures on the ARM side. Rewriting a v4 header as v2 is technically possible, but that only gets it to load, not to run: correctness depends on an undocumented runtime (interrupts, cores, parameter layout). Without on-hardware debugging that is guesswork. More importantly, **there is nothing worth porting**: none of the newer modules is a picture effect the 3N lacks (see below).
- **Watercolor/Illustration already exist in the 3N code** (verified by strings): `libObj.so` contains `PARAMID_WATERCOLOR_EFFECT_LEVEL`/`PARAMID_ILLUST_EFFECT_LEVEL` (plus `RE_` retouch variants), and av-cam has `Start_Art_Effect`/`PRM_REQ_FILTER_ART_EFFECT`. No generation has a separate SA module for them. Whether they appear in the 3N menu must be checked on the camera.
- **ISP tables (Backup, subsystem 0x0003):** block IDs were renumbered in newer generations and sizes changed. By content, the 3N style block `0x00030106` equals block `0x0003003d` on a6000, 7M2 and 7M3: the first 0xd0 bytes are **identical**, including the ladder `2,8,16,24,32,80,112,144,176` at +0xac. Newer generations only append data after 256 bytes, which the 3N never reads. There are no "richer" values to borrow: the shared part is the same.

## Firmware examined

Public Sony update packages (links only; nothing from them is included in this repository):

| Model | Chip | Version | URL | SHA-1 (exe/DAT) | fwtool unpack |
|---|---|---|---|---|---|
| NEX-3N | CXD4132 | 1.00 | own camera | - | yes |
| NEX-6 (same-chip reference) | CXD4132 | 1.03 | `https://di.update.sony.net/IMT/Update_NEX6V103.exe` | `1e91c91118a70e0b56729f2e0853776696e2b914` | yes (exe -> carve DAT at `\x89UFU`) |
| ILCE-6000 | CXD90014 | 3.21 | `https://di.update.sony.net/IMT/Update_ILCE6000V321.exe` | `b990056331e5c2c65c66c8b7c3852f8d5312936e` | yes (carved DAT) |
| ILCE-7M2 | CXD90014 | 4.01 | `https://di.update.sony.net/IMT/Update_ILCE7M2V401.exe` | `e23153c3e35e5a9fc54eb1c7122b0966f4012b37` | yes |
| ILCE-7M3 | CXD90045 | 4.01 | `https://di.update.sony.net/IMT/Update_ILCE7M3V401.exe` | `5a060cf57a8f9f21f237fe2a2b4f9921e7332ee9` | yes |
| ILCE-6400 | CXD90045 | 2.00 | `https://di.update.sony.net/IMT/Update_ILCE6400V200.exe` | `ed5324afb5c161fcace6e6f3b89505bfbf0bbc22` | yes |
| ILCE-7M4 (Creative Look) | CXD90057? | 6.02 (assumed) | `https://di.update.sony.net/NEX/YE19b5b7b3/BODYDATA.DAT` | `9df2eb3d4c690c6bb3db95ea557d9bc3f3005b8c` | no: `No decrypter found` |

- URL pattern: `support.d-imaging.sony.co.jp/download/IMT/<file>?fm=na` -> 302 to `di.update.sony.net/IMT/<file>`. Names `Update_<MODEL>V<ver>.exe` can be guessed; sony.com pages render via JS and do not expose links. Also found (not downloaded): ILCE-7RM3 3.10, ILCE-6300 2.01, ILCE-5100 3.10, ZV-E10 2.00, ILCE-7C 2.00.
- fwtool fails on these exe files with `Unknown exe file`, but the DAT carved from the signature `\x89UFU\r\n\x1a\n` unpacks fully: CXD90014 uses DoubleAes, CXD90045 uses AesCbc.
- **Creative Look cameras** (7M4, 7SM3, 7CM2, ZV-E10M2, 6700): no exe under `IMT/`. For the 7M4 Sony only provides a memory-card `BODYDATA.DAT`. Same `UFU`/`DATV`/`FDAT` container, but FDAT does not decrypt: fwtool has no CXD90057 keys. Dead end without a key.
- The comparison scripts (module similarity, backup block mapping) are not included here; GNU `binutils` (all targets) was used for disassembly.

## SA module format (header comparison)

| Field | CXD4132 (3N/NEX-6) | CXD90014 (6000/7M2) | CXD90045 (7M3/6400) |
|---|---|---|---|
| +0 magic | `aa 0a 13 91` | same | same |
| +4 header version (u16) | 2 (codecs 1) | 4 | 5 |
| +8 module ID, byte +9 (+8 = class: 00 processing, 01 codecs) | tbox `0x17`, sftfcs `0x18`, star `0x1a`, shapep `0x21`, jpeg enc `01 e1` | **same IDs** | same |
| +0xc core mask(?) | `0x01`/`0x02`/`0x08` - single core | `0x0f` (effects) | `0x1f` |
| +0x14 name tag | `SATBOX__0.40` (decimal version) | `SATBOX__0x01` (hex version) | same |
| Vector table (`0x76`) | 24 entries | 54 | 60 |
| Descriptor offset `3d 00 .. b0 42 VV` | 0x100 | 0x200 | 0x200 |
| Descriptor version VV | `0x32` (jpeg `0x31`) | `0x34` | `0x34` |
| Trailer | sum32le of all words = last word | same | same |

The checksum verified for all ~300 modules across generations. ID conflicts exist: `0x19` on 4132 is `sa_pbe_work`, from 7M2 on it is `sa_smod` (same slot in the backup name table, different code, similarity 0.02); `0x13` on 4132 is `fc_recog`, on 90045 `aes_sha2`.

## Module similarity (shared 16-byte shingles; `==` file identical, `body==` identical except header)

| Module | 3N ~ 6000 | 6000 ~ 7M2 | 7M2 ~ 7M3 | 7M3 ~ 6400 |
|---|---|---|---|---|
| sa_tbox (Miniature) | 0.93 | == | body== | == |
| sa_sftfcs (Soft Focus) | 0.83 | == | body== | == |
| sa_star | 0.84 | == | body== | == |
| sa_frc2 / sa_defect | 0.88 / 0.90 | == | body== | == |
| sa_kknr (NR) | 0.79 | == | 1.00 | == |
| sa_spica / sa_bdro2_bdex | 0.90 / 0.86 | == | 0.99-1.00 | == |
| sa_jpeg_enc_1core | 0.05 | == | body== | == |
| sa_shapep | 0.23 | == | body== | == |
| sa_apollo4 (3N) ~ sa_apollo | 0.22 | == | 0.84 | == |

NEX-6 vs 3N: 28 of 32 shared modules are byte-identical (including `pbe_work`, `tbox`, `sftfcs`, `star`, `apollo4`). Within one chip modules are portable as-is, but the NEX-6 has nothing the 3N lacks (extras are only `apollo4_es10`, `zhitomi`, `zphdefdet`).

## What the 3N lacks (added in 90014/90045)
`sa_nlap` (0x2d), `sa_smod` (0x19), `sa_motionshot`, `sa_replacer`, `sa_cecil`, `sa_dcv`, `sa_lfnr_*`, `sa_bayes_tracker(_edge)`, `sa_zphdefdet`, `sa_zoom_nr`, `sa_seg`, `sa_drt/udrt`, `sa_dtcf`, `sa_staple`, `sa_aed`, `sa_aes_sha2`, `sa_pcmcc`, `sa_rotate90`, `sa_fec_enc32`. By names and strings these are tracking, NR, lens correction, segmentation, audio and crypto. **No picture effects among them.** Hypothesis: `nlap` is a standalone "non-linear Laplacian" (edge filter) module; on the 3N its parameters (`nlap_gain`, `nlap_lm_*` ...) are passed inside `PBEH` to `sa_pbe_work`.
- `PBE` on the 3N is a noise-reduction/detail stage (`nr_ihm.*`, `PBEM_BDRO`, `PBEM_RAW_MULTI`, sub-images `PBE_MID/PBE_HIGH`), not Watercolor (inferred from strings, unverified).
- On the 7M3 the effect parameters (`watercolor_effect_level`, `illust_effect_level`, `hdr_art_effect_level`, `posterization_effect`, `miniature_focus_area`) are checked by `LiroSeq` in av-cam. No dedicated DSP module.

## Loader (ARM side, av-cam)
- In all generations av-cam itself loads `/usr/sabin/*.bin` using the name table in the Backup store. Strings `FUNCID_SA_LOAD` / `FUNCID_CORE_SA_LOAD ... codectype` are the same; 90014+ adds `memory=%x, usecase=%x`, i.e. the load message gained fields.
- The Backup name table has a common origin: same order, newer generations append at the end, and `pbe_work` -> `smod` occupies the same slot. Table index != codectype.
- `sa_func_X_acquire/start/release` wrappers: 3N has 18 (`PBE`, `TBOX`, `SFTFCS`, `STAR`, `KKNR`, `YKNR`, `SPICA`, `CONTP`, `BOKS`, `BFNR`, `BDEX`, `DCV`, `KDZ`, `LAXO`, `NFLASH`, `GOLFSHOT`, `DUALREC`), a6000 17 (no `PBE`/`KDZ`/`LAXO`, adds `DECOMP`/`LFNR`/`PreDCV`), 7M2/7M3 20 (`NLAP`, `MOTIONSHOT`). The 3N has no ARM wrapper for a new module: besides the module itself, av-cam code that builds `*_START_PARAM` and sends the command would be needed.
- Magic `aa0a1391` appears as a literal in 3N av-cam (0x412dc), but there it tags a message object. No check of header fields (versions) was found: **unknown** whether the 3N loader rejects a v4/v5 header.

## ISP tables (Backup, subsystem 0x0003)
| | 3N | a6000 | 7M2 | 7M3 |
|---|---|---|---|---|
| blocks in 0x0003 | 251 | 190 | 192 | 222 |
| IDs shared with 3N / same size / identical | - | 177 / 118 / 47 | - | 177 / 104 / 39 |

- Many 3N blocks are 256-byte slots. In newer generations the same IDs have other sizes (up to 12 KB), so tables **do not correspond by ID**. Content matching: of 208 3N blocks >= 64 bytes, only 20 match a6000 at >= 90 %, 17 more partially; vs 7M3, 15 and 10.
- Content matches found: `30106`->`3003d` (styles, shared 0xd0-byte prefix), `30109`->`30046` (0.99), `30104`->`30027` (0.97), `300ab`(1280)->`3012c`(320, 1.00), `30075`->`3013c` (1.00), `3004b`->`30048` (0.95).
- Conclusion: the style ladders on 90014/90045 are the same. Picture Profile and other new tables lie beyond what the 3N reads, or in blocks of another format. "Peeking richer values" from these blocks did not work. Not checked: 3N blocks `0x0003002c...0x3b` (256 B) vs the newer `0x3002c...0x3b` (up to 7.7 KB). They look like the same tables in extended form (e.g. PP gamma curves); decoding needs RAM-reference comparison in newer av-cam, as was done for the 3N (see notes/backup-params.md).

## Verified vs hypotheses
**Verified:** URLs and SHA-1, unpacking; shared magic, IDs and trailer; header and descriptor versions; shared crt0 and DSP memory map; byte identity of bodies 90014<->90045 and 3N<->NEX-6; module and `sa_func_*` lists; Watercolor/Illustration in 3N code; style block match `30106`<->`3003d`; Creative Look firmware (7M4) does not decrypt with fwtool.

**Hypotheses:** field +0xc is a mask of allowed DSP cores (4132 has fewer or hard-pinned cores); the larger vector table means more interrupts/resources on newer SoCs; `PBE` is NR, not an art effect; a 90014 module could only run on 4132 after rewrapping with a v2 header and `0x32` descriptor, and even then the runtime ABI likely differs (Sony recompiled rather than repacked).

## Next steps (if any)
1. Check on the camera whether Picture Effect offers Watercolor/Illustration. If not, it is the same menu filter as for hidden Creative Styles (code and IDs are present on the 3N).
2. Porting modules is not worth it. Grain and a custom style are still only reachable via the Linux-side path (`libmpr`) or via the Backup settings store.

See also: notes/sony-dsp-isa.md, notes/sa-interface.md, notes/prior-art.md.
