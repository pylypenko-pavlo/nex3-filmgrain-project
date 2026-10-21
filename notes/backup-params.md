# NEX-3N: other "look" parameters in the Backup settings store (static analysis)

Tags: **[code]** = read in the disassembly of the main camera binary (`av-cam`; addresses are file offsets, load base 0xc3441000); **[bytes]** = value in a Backup snapshot of this camera; **[hypothesis]** = inference not tested on camera. None of the proposed changes has been tested on camera. Related: `notes/hue-tables.md`, `notes/tone-curve.md`.

Tools: `code/bkparams/` — `trace.py` (Thumb disassembler that annotates "BK block+offset = value" for each read from the RAM copy of Backup), `interp.py` (extracts ISO interpolation tables), `tables.py` (prints all tables in this note), `bkw.py`/`bkh.py` (block dump), `blfind.py`/`lr.py` (call and literal search). Dependencies: numpy, capstone, pyyaml, pycryptodomex; Backup parsing via Sony-PMCA-RE.

## 0. Summary

| goal | in Backup? | main lever | confidence |
|---|---|---|---|
| Still-image luminance NR | **yes**, three independent stages | flag `0x00030010+0x0C` (GHNR/GLNR), flag `0x0003001b+0xD7` (all G-NR above ISO 1600), ISO window of stage YKNR `0x0003004a+0xD2/D6/DA` | [code], image effect untested |
| Sharpening | **yes**, two stages | YAP `apc_gain.apgain` per ISO `0x0003000c+0x1C..0x31`; Apacon: per-ISO multiplier `0x00030106+0x00..0x15` and slider ladder `+0xAC..0xBD`; coring `0x0003000c+0xCE`, `0x0003000d+0x5E` | [code] |
| Picture Effect -> vignette | **yes**: Toy Camera radial curve | `0x00030040+0xA2..+0xE1` (32 x u16, 0x2000 = 1.0) | [code]: function labelled `CalcLensShdGainToy` |
| Lens vignetting (not calibration) | master switch only | `0x00030033+0x00` = 1 (shading master gate); easier: menu item Shading Comp. | [code]/[hypothesis] |
| Hidden styles / ISO / shutter / peaking | **no** (as far as found) | limits are in userland (libObj); Bulb already exists in M | see section 6 |

Key finding: nearly all NR and sharpening tables in 0x0003 are **11 points along the axis `aus_X_ISO`** (`0x1000, 0xF00 .. 0x700, 0x600`, stored at `0x0003000c+0x06..0x1B`). First table element = high ISO, last = low ISO. The axis is likely 256*log2(ISO/3.125): 0x600 = ISO 200 (3N base), 0x900 = 1600, 0xA00 = 3200 [hypothesis, consistent with the table lower bound].

## Never touch

- `0x00030002` — this unit's WB calibration.
- `0x00bc0000`, `0x00bc0002`, `0x01320000` — defect pixel maps (and all `0x00bc*`, `0x0132*`).
- Lens and sensor shading calibration: everything with attribute **0x0a** in 0x0003 — `0x00030036/37/38` (`sjob_LightLvAdj`, `lga_ave_*`, factory level trim), `0x00030042/43`, plus `0x00030051..54, 76..78, 86, 8f, a0, ae, 0102` and anything with attributes 0x48/0x68/0xe8/0x60. Attribute 0x0a = "protected from reset", a handy way to tell per-unit data from shared tables (shared tables are 0x08).
- `0x00030056` — debug block (log switches, forced ISO for NR, etc.), read by dozens of modules. Only as a last resort (1.6).

## General write rules

- **Dual banks.** Some blocks have a "bank B" mapped to the same RAM cell: `0x3000c..0x30018 <-> 0x300b0..0x300bc`, `0x3001a/1b <-> 0x300bd/be`, `0x3001e/1f <-> 0x300c1/c2`, `0x30027..30 <-> 0x300d0..d9`, `0x3003c <-> 0x300e5`, `0x30044..47 <-> 0x300ed..f0`, `0x3011f <-> 0x30120` (and a few more 0x3011x pairs). Both banks are currently byte-identical. Which one loads is decided by a runtime flag (`0x1819ee`: table B when `[0xc3c4..+0xc]==1 && byte!=0`) [code], unknown on this camera -> **write both banks identically**, as with `0x30001/0x30008`. Blocks `0x30033`, `0x30040`, `0x30049`, `0x3004a`, `0x30106` have no bank B.
- u16 values are little-endian: 0x00B0 = bytes `B0 00`.
- Rollback = original bytes, listed below in the "was" values. Keep a full settings snapshot before any write.
- Before an experiment: shoot a base in the same session, fixed WB, M mode, same style. Chart colour noise is +-2..8 chroma, +-3..5 deg, so for NR and sharpening measure **spread, not means** (sigma L* in grey patches, edge profile). Each experiment below is designed for a large effect.

---

## 1. Still-image noise reduction

### 1.1 Structure [code]

Three stages, each with its own Backup tables:

1. **YC::NR (G-NR + C-NR)** — NR in the Bayer/G-plane domain. Compute function `0x284544` (prints `NR:nr_gnr.*`), called from `0x286070` (prints `NR:nr_main.*`), called from `0x2b6cb4`.
   - `nr_main` — 8 flag bytes for **three ISO ranges** (`0x0003001b`):

     | range (threshold at `0x3001b+0x6A/+0x6C`) | offsets | nr_on gnr_on ghnr_on glnr_on cnr_on sk_on cdmin_flg c2rb_gsel |
     |---|---|---|
     | A: X >= 0xE01 (~ISO 51200+, unreachable on 3N) | `+0xCE..0xD5` | 01 01 01 01 01 00 02 01 |
     | B: 0x901 <= X < 0xE01 (ISO > 1600 .. 25600) | `+0xD6..0xDD` | 01 01 **00 00** 01 00 02 01 |
     | C: X < 0x901 (ISO <= 1600) | `+0xDE..0xE5` | 01 01 **00 00** 01 00 03 01 |

     cnr = chroma NR, gnr = G (luminance) NR, ghnr/glnr = G-NR "high/low" sub-stages [names from strings, meaning hypothesised].
   - **Forced GHNR/GLNR** (`0x28611c`): if `0x00030010+0x0C` != 0, shooting mode in {1, 0x13, 0x1A, 0x1F, 0x20}, NR level != 3 and ISO not in range A, then ghnr_on = glnr_on = 1. They are also enabled for modes {6, 7, 0xB, 0xC, 0xD, 0xF, 0x11, 8/0x14 conditionally}. Mode numbers not decoded; mode 1 is probably a normal single frame [hypothesis]: the same set {1, 5, 0x13, 0x1A, 0x1F, 0x20} disables YKNR at level 1 (see stage 2).
   - **NR level** — runtime byte `CommonRam+0x15C` (0..3), set by code, not in Backup. Probably the High ISO NR menu item; value-to-menu mapping not established. Six "high-frequency" G-NR parameters depend on it (per-ISO tables, first element = 0x1000):

     | field | level 0 (default branch) | level 1 | level 2 | level 3 |
     |---|---|---|---|---|
     | [+0xE0] (unnamed, clamp 0x7F) | `3011f+0x6E` | `30049+0x00` | `30014+0x6A` | `30049+0x16` |
     | [+0xF4] (unnamed, clamp 0x7F) | `3011f+0x84` | `30049+0x2C` | `30015+0x52` | `30049+0x42` |
     | `gnr_hi_cor_gainth` | `3011f+0x9A` | `30049+0x58` | `30015+0x9E` | `30049+0x6E` |
     | [+0x104] (clamp 0x3FF) | `3011f+0xB0` | `30049+0x84` | `30015+0xF2` (spills into `30016`) | `30049+0x9A` |
     | **`gnr_hi_gain_cn`** | `3011f+0xC6` | `30049+0xB0` | `30016+0xD8` | `30049+0xC6` |
     | **`gnr_hi_gain_eg`** | `3011f+0xDC` | `30049+0xDC` | `30017+0x24` | `3004a+0x00` |

     hi_gain values (ISO 204800 -> ISO 200): level 0/1 `F F E C C B A A A (A|D) D`, level 2 `F F F E C C B A A A D`, level 3 `D D C A A 9 8 8 8 B B`; clamp < 0x20. If flag `[CommonRam+0x430]` != 0, the computation is repeated with level-2 tables.
     For `picture_effect == 9` all three are forced from `0x30015+0xDC..0xEC`: hi_cor_gainth = 0x20, hi_gain_cn = hi_gain_eg = **0x10**. Hence the hypothesis: 0x10 = factor 1.0 (HF detail passes unattenuated), values 8..F = HF suppressed to 50..94 %.
   - Level-independent (per-ISO tables): `gnr_gainth_cn` `30013+0x2C`, `gnr_gainth_eg` `30013+0x78` (`71 BE 101 131 1A0 240 300 3C0 500 240 300`), `gnr_ofstth_cn` `30013+0xC4`, `gnr_ofstth_eg` `30014+0x10`, `gnr_lgst` `30014+0xBA`, `gnr_lggrad` `30015+0x06`, `gnr_hi_cor_limth` `30016+0x3E`, `gnr_hi_gain_min` `30016+0x8A`. Byte fields per three ISO ranges: lpf_off/medmode/cog/cog_dison at `3000f+0x72..0x7D`, hi_limth at `3000f+0x7E/80/82`. Direction of gainth (larger = stronger?) not determinable from code; the table decreases with ISO.
2. **YKNR** — separate stage of the capture chain (`Capture::YKNR`). Parameters: 13 tables of 11 bytes in `0x0003004c` (`+0x00, +0x16, +0x21, +0x2C, +0x42 .. +0x9A`, `+0xBC`, `+0xCC`, `+0xE4`) [code, field meanings not decoded]. Enabled by function `0xd5760` [code]: **off at NR level 0**; at level 1 off in modes {1, 5, 0x13, 0x1A, 0x1F, 0x20}; otherwise active only when ISO falls in the window from `0x3004a`: `+0xD6/+0xD8` = 0x0AFF/0x0600, `+0xD2/+0xD4` and `+0xDA/+0xDC` = 0x0B00/0x06AA, i.e. roughly ISO 200..6400. The axis here is runtime field `obj+0x5C6`, not the G-NR one (`obj+0x14E`); whether scales match is unverified.
3. **KKNR** (`0x00030024`, modulation `0x3004a+0xE7..0xFE`, `0x3004b`) — by all signs **face skin smoothing**, not general NR: parameters `kk_fm_fsize_small/big_size` (0x64/0x3E8), `kk_fm_fdist_near/far_*`, log `Start_Face_Nr: KKNR %d`; levels 0..4 differ by weights `0x80/0x80/0xC0/0xFF` [code + hypothesis: Soft Skin Effect]. Not needed for a film look; not proposed for changes.

### 1.2 Experiment NR-1 (one byte): drop forced GHNR/GLNR

- `0x00030010` **and** `0x000300b4`: byte `+0x0C`: `01 -> 00`.
- Expectation [hypothesis]: in normal shooting (if that's mode 1) at NR level 0-2 the GHNR/GLNR sub-stages turn off at all ISO <= 25600. Luminance grain finer and more visible; chroma unchanged since cnr_on is untouched.
- Frames: chart + grey scale, ISO 3200 and ISO 800, Standard, Daylight WB; base and test in one session. Measure sigma L* in 6 grey patches and sigma a*/b* separately. Success: sigma L* up noticeably (x1.3+), sigma a*b* within noise.
- If no effect: normal frames enable GHNR via another branch (modes 6/7/0xB..), go to NR-2.

### 1.3 Experiment NR-2 (one byte): disable all G-NR above ISO 1600

- `0x0003001b` **and** `0x000300be`: byte `+0xD7` (gnr_on, range B): `01 -> 00`.
- Expectation [code -> image hypothesis]: at ISO 3200..25600 the YC::NR luminance NR is off entirely; chroma NR (cnr_on `+0xDA` = 01) stays. ISO <= 1600 falls into range C and is unchanged. **ISO 1600 and 3200 in one session = built-in control**: only the ISO 3200 frame should move.

### 1.4 Experiment NR-3 (three u16): disable YKNR

- `0x0003004a` (single bank): `+0xD2..D3` `00 0B -> 00 00`; `+0xD6..D7` `FF 0A -> 00 00`; `+0xDA..DB` `00 0B -> 00 00`.
- Logic: upper window bound = 0 -> condition "ISO <= bound" never holds, `0xd5760`/`0xd5854` return "off" [code]. Only the bounds change; neighbouring tables are untouched.
- Frames as in NR-1, ISO 800 and 3200. What YKNR does (luma/chroma) is unknown: check both sigma L* and sigma a*b*.

### 1.5 Experiment NR-4 (fine tuning, after 1-3): weaken HF suppression at all levels

- In all six hi_gain tables from 1.1 (levels 0-3) set `10` (u16 `10 00`) at elements 5..7 (ISO 6400/3200/1600 = indices 5, 6, 7 from the start). For `30016/30017/3011f` also write bank B (`300ba/300bb/30120`).
- Expectation [hypothesis "0x10 = 1.0"]: HF detail/grain returns at ISO 1600-6400, otherwise unchanged. If the opposite happens (smoother), the scale is inverted; try `04`.

### 1.6 For reference, not recommended

`0x00030056+0x0A = 02` + `+0x04 = <X>` — debug ISO override for all NR (`0x2b6ce8`) [code]: "denoise as if ISO 200" at any ISO. The block is shared by many modules' debug; `+0x20` selects which module logs (3 = NR, 4 = YAP, 6 = KKNR).

---

## 2. Sharpening

### 2.1 YAP stage (aperture correction in YC, stills) [code]

- `job_apc_gain_stl` (`0xd4334`): `apc_gain.apgain = ISO_table * k1 * k2 * k3 / 2^21`, clamp < 0x200. Currently k ~ 0x80 (= 1.0), so **apgain ~ table**: `0x0003000c+0x1C..0x31` (11 x u16) = `B0` at all ISO. vapgain/hapgain = bytes `0x3000c+0x86` (8) and `+0x8B` (7), clamp < 0x10; for negative sharpness steps bytes `0x3000f+0xD4..D7` / `+0xDC..DF` are subtracted [code; that this is the Sharpness slider is a hypothesis].
- `job_apc_coring_stl` (`0xd32ce`): coring (threshold below which small transitions are not boosted). `vcoring_p0` = `0x3000c+0xCE..0xE3`, `hcoring_p0` = `0x3000d+0x5E..0x73` (both `4 4 4 4 5 5 6 7 8 A A`, high ISO -> low), plus per-mode and per-effect corrections (`3000e`, `3000f+0x52..`, `3001e+0x40..`). Also `vcoring_p1/p2` = `0x3000d+0x3C/+0x42` (0x18/0x24), `hcoring_p1/p2` = `+0xCC/+0xD2`; clamp < 0x200.
- Also `apc_yld` (luminance dependence), `apc_mask`, `apc_lpf`, `apc_zoukou` (distance from centre), and branches for picture effect 1/4/5/9 (`3001e+0x44..0x58`). Tables not analysed.

### 2.2 Apacon stage ("Developing", depends on style and slider) [code]

- `0x464958`: 5 coefficients = `ladder[step] * ISO_multiplier * 2^11 >> 16`, clamp 0xFFF.
- Step = `[obj+0xF2]` (signed byte, likely Sharpness slider -3..+3) + 4, with +1 for "kind" 3/4 and -1 for 7 (kind depends on style/scene, `0x3f4936`).
- Ladder for registers 0x78B0/0x78B2 = `0x00030106+0xAC..0xBD` (9 x u16): `2 8 16 24 [32] 80 112 144 176`. Ladder 0x78B4 = `+0xBE..0xCF`: `2 8 16 24 32 32 32 32 32`.
- ISO multiplier (axis `0x30108+0xA0..`, `0x1100..0x700`) = `0x00030106+0x00..0x15`: `120 x9, 100, 100`. Channels 0x78B2 and 0x78B4 have **zero** multipliers (`+0x2C..`, `+0x58..`), so on 3N only 0x78B0 is active.
- Caveat: an earlier test (step 5: 80 -> 32) noticeably lowered Sunset saturation. So 0x78B0 is not pure sharpening, or the slider also affects colour [unresolved contradiction].

### 2.3 Experiment SH-1: weaken apgain (YAP)

- `0x0003000c` **and** `0x000300b0`: `+0x1C..+0x31` — 11 x `B0 00` -> 11 x `40 00` (176 -> 64, -64 %).
- Frame: black/white edge and fine chart text, ISO 200 and 1600, Standard, Sharpness 0. Measure edge overshoot and 10-90 % transition width. Expectation: overshoot drops several-fold, much less halo.

### 2.4 Experiment SH-2: coring x3 (grain less "crunchy", large edges unchanged)

- `0x0003000c`/`0x000300b0` `+0xCE..+0xE3` and `0x0003000d`/`0x000300b1` `+0x5E..+0x73`: each u16 x3 (`04 00 -> 0C 00`, `05 -> 0F`, `06 -> 12`, `07 -> 15`, `08 -> 18`, `0A -> 1E`).
- Expectation [hypothesis about p0]: less fine "salt" on flat patches and ISO 1600 noise, large-edge overshoot nearly unchanged.

### 2.5 Experiment SH-3: Apacon globally (only after SH-1)

- `0x00030106` (single bank) `+0x00..+0x15`: `20 01` x9 and `00 01` x2 -> 11 x `80 00` (half). Leave the ladder alone.
- Shoot Standard **and Sunset**: because of the 2.2 contradiction, measure both sharpness and chroma. If chroma moves, 0x78B0 is mixed with colour and unusable as a look lever.

Practical tip without any write: Sharpness -3 in a style already selects ladder step 1 (8 instead of 32) [code].

The proposed byte changes for these experiments are collected in `data/fx/changes.json`.

---

## 3. Picture Effect

- **Toy Camera vignette lives in Backup [code].** Function `0x24a408` contains the string `CalcLensShdGainToy`. Radial gain curve, 32 nodes centre -> edge: `0x00030040+0xA2..+0xE1` (u16, 0x2000 = 1.0). Currently a linear falloff `2000 1F17 .. 4C0 3D7`, edge 0x3D7 ~ **-3.1 EV**. `+0xE0` (last node) also serves as a floor in one branch; `+0xE4` = 0x100 = slope scale. Two alternative curves `+0x00..+0x3F` and `+0x40..+0x7F` (currently zeros) are mixed in with strength from a runtime byte (+-16) — probably Toy sub-modes (Normal/Cool/Warm/Green/Magenta) [hypothesis].
- **Experiment PE-1 (soft film vignette):** `0x00030040+0xA2..+0xE1` <- `2000 1FFD 1FF4 1FE5 1FD0 1FB5 1F95 1F6E 1F41 1F0E 1ED6 1E97 1E52 1E08 1DB7 1D61 1D04 1CA2 1C39 1BCB 1B57 1ADC 1A5C 19D6 1949 18B7 181F 1781 16DD 1633 1583 14CD` (quadratic falloff, edge ~ -0.6 EV; each value u16 LE). Frame: Toy Camera (Normal) on a flat white chart screen, compare corner/centre ratio with a pre-write frame. Expectation: vignette from -3 EV to -0.6 EV.
  Caveat: Toy Camera brings its own colour and tone (probably one of the 17 matrices in `0x30001`, tone curve k15..k19). To turn Toy into "film with vignette" its matrix slot must be found, with the same tagging method as for styles (`data/looks/tag_matrices.json`): one Toy Camera frame with tag matrices written.
- **Picture effect in code.** NR, YAP and coring branch on the effect number: 9 = special hi_gain in NR and apgain; 1/4/5/9 = coring corrections from `0x3001e+0x44..0x58`; 8/0xC = threshold `0x3000c+0xAA`. Number-to-name mapping **not established** (enum table not found in libObj). Blocks `0x3000d/0e/1e/1f/55` tagged `YAP:picture_effect`/`bdro_sequence` are per-effect coring/sharpening gain (`job_apc_coring_stl`), not effect parameters. Retro / Soft High-key / Rich-tone Mono are HAPI filters (`Start_Art_Effect`, `Start_Richtone_Monochrome`) with parameters outside 0x0003. Not analysed.

## 4. Lens shading (vignette)

- Shading correction is computed in `Camera::YC::SHD` (`CalcLensShdGain`, `GetLensShdGain`, `GetShdTblData`): lens tables plus per-unit trim (`0x30036..38`, `0x30042/43` with attribute 0x0a — **do not touch**).
- There is no user "vignette strength" in Backup. Only the master gate `0x00030033+0x00` = 01: when != 1, `0x24999c` returns shading mode 0 (off) [code]. This probably also disables colour correction in the corners, so colour fringing at edges is possible [hypothesis]. The safer route is the menu item "Shading Comp.: Off" (check whether the 3N menu has it): natural lens vignetting is already a film-like trait.
- If tried anyway: `0x00030033+0x00` `01 -> 00`, flat white frame, lens wide open, compare corner/centre and corner colour.

## 5. Found along the way

- NR and sharpening tables extend to ISO 204800 (X = 0x1000) [bytes], so the ISO limit is not in processing.
- `0x00030056` — debug block (see 1.6).
- Bank B of NR/YAP blocks is selected at `0x1819ee` by a runtime flag; both banks are currently identical [bytes].

## 6. Hidden features: Backup or code

| what | conclusion | evidence |
|---|---|---|
| Creative Style menu filter | **code (userland), not Backup** | Earlier tests: the 18 `0107xxxx` flags in NEX-6 style values unlocked nothing; `DefInh::sm_refTbl` is the same on 3N and NEX-6. 0x0003 holds only processing parameters: 17 matrices in `0x30001`, so parameters for hidden styles seem to exist but the menu doesn't show them. Filter location (libObj/viewUnified) not found. |
| ISO range | **not Backup** (as far as found) | Processing tables go up to X = 0x1000; ISO lists in av-cam are identical on 3N and NEX-6. Limit is somewhere in the menu layer; not found. |
| Shutter > 30 s | not needed | M mode has Bulb (per the NEX-3N manual). |
| Peaking (colour/level) | **menu setting, colours not found** | libObj: `PARAMID_DATA_PEAKING`, `_LEVEL`, `_COLOR`, `_OUT`; renderer `DefObjRenderer::MSGID_SET_PEAKING_CMD`. YCbCr colour values and threshold do not appear in 0x0003; not located in code. |

## 7. Suggested experiment order

1. NR-2 (one byte, built-in ISO 1600 vs 3200 control) -> NR-1 -> NR-3. Shows which stage produces the "plasticine" look.
2. SH-1, then SH-2. SH-3 only if YAP isn't enough.
3. PE-1 if "Toy = vignette" is attractive; then tags to find Toy's colour slot.

Each experiment is a separate write, base and test in the same session, rollback to the "was" values.

## 8. Open questions

- Mapping of NR level 0..3 to High ISO NR menu items; shooting mode numbers (1, 0x13, 0x1A..); picture effect numbers.
- `aus_X_ISO` scale (hypothesis 0x600 = ISO 200) and offset between G-NR axis (`obj+0x14E`) and Apacon/YKNR axis (`obj+0x5C6`; Apacon axis starts at 0x700).
- Meaning of YKNR fields (`0x3004c`), unnamed G-NR fields ([+0xE0], [+0xF4], [+0x104]), direction of gainth/hi_gain.
- Which bank (A/B) is active.
